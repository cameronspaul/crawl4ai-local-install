import argparse
import io
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Fast local cross-agent cache
try:
    from cache import get_cached_scrape, set_cached_scrape, make_markdown_cache_key
except ImportError:
    try:
        from src.cache import get_cached_scrape, set_cached_scrape, make_markdown_cache_key
    except ImportError:
        get_cached_scrape = lambda url, ttl=7200: None
        set_cached_scrape = lambda url, content: None
        make_markdown_cache_key = lambda url: url

# Persistent micro-daemon client
try:
    from daemon_client import is_daemon_alive, daemon_scrape
except ImportError:
    try:
        from src.daemon_client import is_daemon_alive, daemon_scrape
    except ImportError:
        is_daemon_alive = lambda: False
        daemon_scrape = lambda *args, **kwargs: None

CHALLENGE_PATTERNS = [
    re.compile(r"cf-browser-verification", re.I),
    re.compile(r"cloudflare ray id", re.I),
    re.compile(r"enable javascript and cookies to continue", re.I),
    re.compile(r"<title>Just a moment\.\.\.</title>", re.I),
    re.compile(r"<title>Access Denied</title>", re.I),
    re.compile(r"<title>Attention Required! \| Cloudflare</title>", re.I),
]

#: A browser-tier result shorter than this is treated as an unrendered shell
#: rather than real content (matches the threshold the fast HTTP tier uses).
MIN_CONTENT = 40

# Optional anti-bot stealth tier (invisible_playwright / patched Firefox).
# Stdlib-only import; the browser package itself is imported lazily on use.
try:
    import stealth as stealth_tier
except ImportError:
    try:
        from src import stealth as stealth_tier
    except ImportError:
        stealth_tier = None

if stealth_tier is not None:
    looks_like_challenge = stealth_tier.looks_like_challenge
    looks_like_consent = stealth_tier.looks_like_consent
else:
    def looks_like_challenge(text: str) -> bool:
        if not text or len(text) > 9000:
            return False
        return any(pat.search(text) for pat in CHALLENGE_PATTERNS)

    def looks_like_consent(text: str) -> bool:
        return False


#: Optional override installed by the daemon so the stealth tier reuses a warm
#: browser instead of launching one per request.
_stealth_backend = None


def set_stealth_backend(fn) -> None:
    """Install a custom stealth renderer, e.g. the daemon's warm browser."""
    global _stealth_backend
    _stealth_backend = fn


def _try_stealth(url: str, verbose: bool, timeout: int, readable: bool = True, raw_out: list | None = None) -> str:
    """Render a URL with the patched-Firefox stealth engine, or None."""
    if stealth_tier is None or not stealth_tier.available():
        if verbose:
            print("[scrapepage] Stealth tier unavailable (invisible_playwright engine not installed)", file=sys.stderr)
        return None

    if _stealth_backend is not None:
        if verbose:
            print(f"[scrapepage] Warm stealth browser render for '{url}'", file=sys.stderr)
        try:
            return _stealth_backend(url, timeout, readable=readable)
        except TypeError:
            # Backwards compatibility with backends that only take (url, timeout).
            return _stealth_backend(url, timeout)

    if verbose:
        print(f"[scrapepage] Stealth tier rendering '{url}' with patched Firefox...", file=sys.stderr)
    convert = fast_html_to_markdown
    if not readable or raw_out is not None:
        convert = lambda html, base: fast_html_to_markdown(html, base, readable=readable, raw_out=raw_out)
    return stealth_tier.scrape(url, convert, timeout=max(timeout, 20), verbose=verbose)



def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape a webpage and convert it to clean Markdown with tiered fast-fetch & anti-bot stealth fallback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  scrapepage https://example.com
  scrapepage https://example.com https://docs.python.org/3/
  scrapepage https://example.com --stealth
  scrapepage https://example.com --html
  scrapepage https://example.com --no-cache
"""
    )
    parser.add_argument("urls", nargs="*", help="URL(s) of the webpage(s) to scrape")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose crawler logs",
    )
    parser.add_argument(
        "-s", "--stealth",
        action="store_true",
        help="Force the anti-bot stealth engine (patched Firefox) for this URL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Request timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--no-cache", "--fresh",
        dest="no_cache",
        action="store_true",
        help="Bypass local cache and force fresh network scrape",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Print raw rendered HTML instead of Markdown (useful for structured extraction)",
    )
    parser.add_argument(
        "--raw-markdown",
        action="store_true",
        help="Keep the old unformatted Markdown output instead of the readable layout",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print a before/after comparison of the raw and readable Markdown",
    )
    return parser.parse_args()


def format_error(error_msg: str) -> str:
    if not error_msg:
        return "Unknown error occurred during scraping."
    lines = [line.strip() for line in error_msg.strip().splitlines() if line.strip()]
    for line in lines:
        if line.startswith("Page.goto:"):
            return line
        if line.startswith("Blocked by"):
            return line
    for line in lines:
        if line.startswith("Error:") and not line.startswith("Error: Failed on navigating"):
            return line
    return lines[0] if lines else error_msg


def remove_long_chunks(text: str, max_length: int = 1000) -> str:
    """Remove any unbroken non-whitespace tokens (e.g. giant base64 data, tracking URLs) exceeding max_length characters."""
    if not text:
        return ""
    return re.sub(rf"\S{{{max_length},}}", "", text)


#: Internal marker placed on appendix lines before final line numbering.
#: NUL bytes cannot occur in the Markdown we generate, so it cannot collide.
_LINE_MARKER = "\x00LINE\x00"
_HEADER_SECTION = "## Header & footer links"
_IMAGE_SECTION = "## Images"


def normalize_markdown_whitespace(markdown_text: str) -> str:
    """De-gap Markdown without touching a single visible character.

    Removes the BOM and trailing spaces and collapses any run of blank lines
    to one. This is the only destructive step in the readable layout.
    """
    if not markdown_text:
        return ""
    kept: list[str] = []
    for raw_line in markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.lstrip("\ufeff").rstrip()
        if line.strip():
            kept.append(line)
        elif kept and kept[-1] != "":
            kept.append("")
    while kept and kept[-1] == "":
        kept.pop()
    return "\n".join(kept)


def _line_key(line: str) -> str:
    """Comparison key used to match a Markdown line to a DOM fragment."""
    text = line.strip()
    text = re.sub(r"^L\d+\s+", "", text)  # ignore numbering from a previous pass
    text = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+|>\s*)", "", text)
    return re.sub(r"\s+", " ", text)


def _fragment_lines(node) -> list[str]:
    """Render one DOM subtree with the same settings as the full page."""
    from lxml import html as lxml_html
    from markdownify import markdownify

    try:
        fragment = lxml_html.tostring(node, encoding="utf-8").decode("utf-8")
        rendered = markdownify(
            fragment,
            heading_style="ATX",
            strip=["script", "style", "noscript"],
            wrap=False,
        )
    except Exception:
        return []
    return [line for line in rendered.splitlines() if line.strip()]


def _dom_bucket_keys(tree) -> tuple[set[str], set[str]]:
    """Collect line keys for image and nav/footer fragments.

    The DOM is only used to *classify* lines. The text itself always comes
    from the single full-page markdownify pass, so no content is re-rendered
    or lost here.
    """
    image_keys: set[str] = set()
    nav_keys: set[str] = set()

    for node in tree.xpath("//img | //picture | //a[.//img]"):
        for line in _fragment_lines(node):
            image_keys.add(_line_key(line))

    nav_xpath = (
        "//header | //nav | //footer | "
        "//*[@role='navigation' or @role='banner' or @role='contentinfo'] | "
        "//a[starts-with(normalize-space(.), 'Skip to')]"
    )
    candidates = []
    for node in tree.xpath(nav_xpath):
        # Keep article titles/bodies in the main section.
        if node.xpath(
            "ancestor::article | ancestor::main | "
            "ancestor::*[@role='main'] | ancestor::*[@role='article']"
        ):
            continue
        if node.xpath(".//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6"):
            continue
        if len(" ".join(node.itertext()).strip()) > 4000:
            continue
        candidates.append(node)

    # Sites without semantic tags: recognise a small footer container.
    for node in tree.xpath("//div | //section | //ul"):
        names = " ".join([node.get("class") or "", node.get("id") or ""]).lower()
        if not re.search(r"(?:^|[\s_-])footer(?:[\s_-]|$)", names):
            continue
        if len(node.xpath(".//a")) < 2:
            continue
        if len(" ".join(node.itertext()).strip()) > 4000:
            continue
        candidates.append(node)

    for node in candidates:
        for line in _fragment_lines(node):
            nav_keys.add(_line_key(line))

    return nav_keys, image_keys


def format_readable_markdown(
    markdown_text: str,
    nav_keys: set[str] | None = None,
    image_keys: set[str] | None = None,
    verbose: bool = False,
) -> str:
    """Reorder Markdown into body -> nav/footer links -> images.

    Every non-blank source line is emitted exactly once, in source order
    within its section. Only blank lines and trailing whitespace are dropped.
    An internal assertion falls back to de-gapped Markdown if that invariant
    is ever broken.
    """
    nav_keys = nav_keys or set()
    image_keys = image_keys or set()
    normalized = normalize_markdown_whitespace(markdown_text)
    if not normalized:
        return ""

    source_lines = [line for line in normalized.splitlines() if line.strip()]
    main_lines: list[str] = []
    nav_lines: list[str] = []
    image_lines: list[str] = []

    for line in normalized.splitlines():
        if not line.strip():
            if main_lines and main_lines[-1] != "":
                main_lines.append("")
            continue
        key = _line_key(line)
        if key in image_keys:
            image_lines.append(line)
        elif key in nav_keys:
            nav_lines.append(line)
        else:
            main_lines.append(line)

    # Removing a block from the middle can leave two adjacent blanks.
    collapsed_main: list[str] = []
    for line in main_lines:
        if not line.strip() and collapsed_main and not collapsed_main[-1].strip():
            continue
        collapsed_main.append(line)
    main_lines = collapsed_main
    while main_lines and not main_lines[0].strip():
        main_lines.pop(0)
    while main_lines and not main_lines[-1].strip():
        main_lines.pop()

    # Lossless guarantee: the reordered data lines must be an exact
    # permutation of the cleaned source lines.
    rearranged = [line for line in main_lines + nav_lines + image_lines if line.strip()]
    if Counter(rearranged) != Counter(source_lines):
        if verbose:
            print("[scrapepage] Readable layout would lose content; using de-gapped Markdown", file=sys.stderr)
        return normalized

    display: list[str] = list(main_lines)
    if nav_lines:
        display += ["", _HEADER_SECTION, ""] + [_LINE_MARKER + line for line in nav_lines]
    if image_lines:
        display += ["", _IMAGE_SECTION, ""] + [_LINE_MARKER + line for line in image_lines]

    numbered: list[str] = []
    for number, line in enumerate(display, 1):
        if line.startswith(_LINE_MARKER):
            numbered.append(f"L{number:<5} {line[len(_LINE_MARKER):]}")
        else:
            numbered.append(line)
    return "\n".join(numbered)


def fast_html_to_markdown(
    html_content: str,
    base_url: str,
    readable: bool = True,
    raw_out: list | None = None,
) -> str:
    """Strip non-content tags, resolve links, and convert HTML to Markdown.

    With ``readable=True`` (the default) the result is de-gapped and ordered
    as body, header/footer links, then images. ``raw_out``, when supplied,
    receives the untouched markdownify result for ``--preview``.
    """
    from lxml import html as lxml_html
    from markdownify import markdownify

    tree = lxml_html.fromstring(html_content)
    for bad in tree.xpath("//script | //style | //noscript"):
        bad.drop_tree()
    try:
        # Rewrite relative href/src against the page URL (what baseurl did before).
        tree.make_links_absolute(base_url)
    except Exception:
        pass
    cleaned = lxml_html.tostring(tree, encoding="utf-8").decode("utf-8")
    md = markdownify(cleaned, heading_style="ATX", strip=["script", "style", "noscript"], wrap=False)
    md = remove_long_chunks(md)
    if raw_out is not None:
        raw_out.append(md)
    if not readable:
        return md
    nav_keys, image_keys = _dom_bucket_keys(tree)
    return format_readable_markdown(md, nav_keys, image_keys)


def try_fast_html(url: str, timeout: int = 10, min_chars: int = 200) -> tuple[bool, str]:
    """Fetch raw HTML with primp (Rust HTTP client, browser TLS impersonation).

    Returns ``(True, html)`` only for a real 200 response that does not look
    like a bot challenge or consent wall. A 202 is specifically rejected:
    some sites return it for an anti-bot shell rather than real content.
    """
    try:
        import primp
        client = primp.Client(impersonate="random", follow_redirects=True, timeout=timeout)
        resp = client.get(url)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        text = resp.text
        if not text or len(text.strip()) < min_chars:
            return False, "Response body too short"

        for pat in CHALLENGE_PATTERNS:
            if pat.search(text[:3000]):
                return False, "Bot challenge detected"

        if looks_like_consent(text):
            return False, "Consent wall"

        return True, text
    except Exception as e:
        return False, str(e)


def try_fast_scrape(url: str, timeout: int = 10, readable: bool = True, raw_out: list | None = None) -> tuple[bool, str]:
    """Attempt ultra-fast HTTP scrape using primp (Rust HTTP client with browser TLS impersonation)."""
    ok, text = try_fast_html(url, timeout=timeout, min_chars=80)
    if not ok:
        return False, text

    try:
        md = fast_html_to_markdown(text, url, readable=readable, raw_out=raw_out)
        if len(md.strip()) < 40:
            return False, "Insufficient markdown extracted"

        return True, md
    except Exception as e:
        return False, str(e)


def scrape_html(
    url: str,
    force_stealth: bool = False,
    verbose: bool = False,
    timeout: int = 30,
    no_cache: bool = False,
    ready_markers: tuple[str, ...] | None = None,
    settle_wait: float = 10.0,
) -> str:
    """Return raw HTML, escalating to the stealth browser when needed.

    This is the structured-extraction sibling of :func:`scrape_single`. It is
    deliberately not stored in the markdown cache, because HTML and Markdown
    share a cache key. The warm daemon may still serve it when it was started
    from this version of the code.

    ``ready_markers`` are strings that must appear in the rendered content
    before it is accepted, so a client-rendered app shell is not mistaken for a
    finished page.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Warm daemon: pooled primp client + reused stealth browser.
    daemon_warm = False
    if not os.environ.get("INSIDE_DAEMON") and is_daemon_alive():
        daemon_warm = True
        daemon_res = daemon_scrape(
            url,
            timeout=timeout,
            no_cache=no_cache,
            force_stealth=force_stealth,
            raw=True,
            ready_markers=ready_markers,
            settle_wait=settle_wait,
            verbose=verbose,
        )
        # Older daemons ignore the raw flag and return Markdown; only accept a
        # response that actually looks like HTML.
        if daemon_res and daemon_res.lstrip()[:1] == "<":
            if verbose:
                print(f"[scrapepage] Micro-daemon served raw HTML for '{url}'", file=sys.stderr)
            return daemon_res

    if not force_stealth:
        ok, result = try_fast_html(url, timeout=min(timeout, 12))
        if ok:
            if verbose:
                print(f"[scrapepage] Fast HTTP tier returned HTML for '{url}'", file=sys.stderr)
            return result
        if verbose:
            print(f"[scrapepage] Fast HTTP tier bypassed ({result}) for '{url}'", file=sys.stderr)

    # A live daemon already owns the warm browser. Launching a second cold
    # browser here would double the wait and usually fail the same way, so
    # report the failure instead.
    if daemon_warm:
        raise RuntimeError(
            f"Error: the warm daemon could not render '{url}'. "
            "Try 'daemon.bat stop && daemon.bat start' and run the command again."
        )

    if verbose:
        print(f"[scrapepage] Escalating to stealth tier for raw HTML '{url}'", file=sys.stderr)

    if stealth_tier is None or not stealth_tier.available():
        raise RuntimeError(
            "Error: The stealth engine is not installed, so this page cannot be "
            f"rendered. Run '.\\scripts\\install.ps1'. '{url}'"
        )

    if _stealth_backend is not None:
        # Daemon backend converts to Markdown, so it cannot serve raw HTML.
        content = None
    else:
        content = stealth_tier.scrape(
            url,
            None,
            timeout=max(timeout, 30),
            settle_wait=settle_wait,
            verbose=verbose,
            ready_markers=ready_markers,
        )

    if content and len(content.strip()) >= 200:
        return content

    raise RuntimeError(
        f"Error: Could not fetch HTML from '{url}'. The page may need interactive verification."
    )


def scrape_single(
    url: str,
    force_stealth: bool = False,
    verbose: bool = False,
    timeout: int = 20,
    no_cache: bool = False,
    readable: bool = True,
    raw_out: list | None = None,
    use_daemon: bool = True,
) -> str:
    """Scrape a page to Markdown, optionally in the readable layout.

    ``readable=False`` reproduces the old unformatted markdownify output.
    ``raw_out`` receives that raw output for ``--preview``; ``use_daemon=False``
    bypasses the daemon so the preview always sees the freshly converted text.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    cache_key = make_markdown_cache_key(url)

    # Tier 0: Fast Cross-Agent Shared Cache (< 2ms). Raw output is never
    # cached, so an opt-out request cannot be served a formatted entry.
    if readable and not no_cache and not force_stealth:
        cached = get_cached_scrape(cache_key)
        if cached:
            if verbose:
                print(f"[scrapepage] Cache hit for '{url}'", file=sys.stderr)
            return cached

    # Tier 0.5: Persistent Micro-Daemon (warm connection pool & warm stealth browser)
    if use_daemon and not os.environ.get("INSIDE_DAEMON") and is_daemon_alive():
        daemon_res = daemon_scrape(
            url, timeout=timeout, no_cache=no_cache, force_stealth=force_stealth, readable=readable
        )
        if daemon_res:
            if verbose:
                print(f"[scrapepage] Micro-daemon served '{url}'", file=sys.stderr)
            return daemon_res

    # Tier 1: Fast HTTP Path (Rust primp: browser TLS impersonation, no JS)
    if not force_stealth:
        fast_timeout = min(timeout, 8)
        ok, result = try_fast_scrape(url, timeout=fast_timeout, readable=readable, raw_out=raw_out)
        if ok:
            if verbose:
                print(f"[scrapepage] Fast HTTP tier succeeded for '{url}'", file=sys.stderr)
            if readable:
                set_cached_scrape(cache_key, result)
            return result
        if verbose:
            print(f"[scrapepage] Fast HTTP tier bypassed ({result}) for '{url}'", file=sys.stderr)

    # Tier 2: Anti-bot stealth engine (patched Firefox) — renders JS and clears
    # anti-bot walls that the HTTP tier cannot. Last and only browser tier.
    if verbose:
        print(f"[scrapepage] Escalating to stealth tier for '{url}'", file=sys.stderr)
    error = None
    try:
        content = _try_stealth(url, verbose, timeout, readable=readable, raw_out=raw_out)
    except Exception as e:
        content = None
        error = format_error(str(e))
        if verbose:
            print(f"[scrapepage] Stealth tier failed for '{url}': {error}", file=sys.stderr)

    if content and len(content.strip()) >= MIN_CONTENT:
        if readable:
            set_cached_scrape(cache_key, content)
        return content

    if stealth_tier is None or not stealth_tier.available():
        raise RuntimeError(
            "Error: The stealth engine is not installed, so there is no browser fallback. "
            f"Run '.\\scripts\\install.ps1' (or 'invisible-playwright fetch'). '{url}'"
        )
    detail = f": {error}" if error else ""
    raise RuntimeError(f"Error: Page doesn't seem to exist. Failed to scrape. Don't attempt again. '{url}'{detail}")


def _preview_excerpt(text: str, limit: int = 30) -> list[str]:
    """Compress blank runs for a compact before/after display."""
    excerpt: list[str] = []
    blanks = 0
    for line in text.splitlines():
        if not line.strip():
            blanks += 1
            continue
        if blanks:
            excerpt.append(f"    ... {blanks} blank line(s) ...")
            blanks = 0
        excerpt.append(line)
        if len(excerpt) >= limit:
            break
    return excerpt


def format_preview(raw: str, readable: str) -> str:
    """Build a short before/after comparison for ``--preview``."""
    raw_lines = raw.splitlines()
    blank_runs: list[int] = []
    run = 0
    for line in raw_lines:
        if not line.strip():
            run += 1
        elif run:
            blank_runs.append(run)
            run = 0
    if run:
        blank_runs.append(run)

    stats = [
        f"raw lines:       {len(raw_lines)}",
        f"blank lines:     {sum(1 for line in raw_lines if not line.strip())}",
        f"longest gap:     {max(blank_runs) if blank_runs else 0} blank lines",
        f"readable lines:  {len(readable.splitlines())}",
    ]
    out = ["=" * 78, "BEFORE - raw markdownify output", "=" * 78, *stats, ""]
    out += _preview_excerpt(raw)
    out += ["", "=" * 78, "AFTER - readable layout (start)", "=" * 78]
    out += _preview_excerpt(readable, 26)
    out += ["", "    ...", "=" * 78, "AFTER - readable layout (end: appendices)", "=" * 78]
    out += readable.splitlines()[-14:]
    return "\n".join(out)


def main():
    args = parse_args()
    if not args.urls:
        print("Error: URL is required.\nUsage: scrapepage <url> [url2 ...]", file=sys.stderr)
        sys.exit(1)

    urls = args.urls

    # cmd.exe splits an unquoted URL query on '&' before Python sees it, so a
    # pasted dated URL can arrive as "…?from=…", "to=…", "guests=1". Re-join
    # those fragments instead of treating them as separate pages.
    joined: list[str] = []
    for arg in urls:
        looks_like_url = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", arg))
        if (
            joined
            and not looks_like_url
            and not os.path.exists(arg)
            and "=" in arg
            and "?" in joined[-1]
        ):
            joined[-1] = joined[-1] + "&" + arg
        else:
            joined.append(arg)
    urls = joined

    if args.preview and (len(urls) != 1 or args.html):
        print(
            "[scrapepage] --preview only applies to a single Markdown page; ignoring it here.",
            file=sys.stderr,
        )

    def fetch(u: str) -> str:
        if args.html:
            return scrape_html(
                u,
                force_stealth=args.stealth,
                verbose=args.verbose,
                timeout=args.timeout,
                no_cache=args.no_cache,
            )
        return scrape_single(
            u,
            force_stealth=args.stealth,
            verbose=args.verbose,
            timeout=args.timeout,
            no_cache=args.no_cache,
            readable=not args.raw_markdown,
        )

    # Single URL: output directly without headers for seamless piping and backwards compatibility
    if len(urls) == 1:
        try:
            if args.preview and not args.html:
                raw_out: list[str] = []
                content = scrape_single(
                    urls[0],
                    force_stealth=args.stealth,
                    verbose=args.verbose,
                    timeout=args.timeout,
                    no_cache=True,
                    readable=True,
                    raw_out=raw_out,
                    use_daemon=False,
                )
                raw = raw_out[0] if raw_out else None
                print(format_preview(raw, content) if raw is not None else content)
            else:
                content = fetch(urls[0])
                print(content)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(130)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Scraping failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Multiple URLs: scrape concurrently in parallel
    def run_scrape(u):
        try:
            return (u, fetch(u), None)
        except Exception as err:
            return u, None, str(err)

    max_workers = min(len(urls), 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(run_scrape, urls))

    has_errors = False
    for idx, (u, content, err) in enumerate(results):
        if idx > 0:
            print("\n" + "=" * 80 + "\n")
        print(f"# Source: {u}\n")
        if err:
            print(f"Failed to scrape: {err}", file=sys.stderr)
            has_errors = True
        else:
            print(content)

    if has_errors and all(res[1] is None for res in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
