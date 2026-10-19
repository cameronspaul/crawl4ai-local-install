import argparse
import io
import os
import re
import sys
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
    from cache import get_cached_scrape, set_cached_scrape
except ImportError:
    try:
        from src.cache import get_cached_scrape, set_cached_scrape
    except ImportError:
        get_cached_scrape = lambda url, ttl=7200: None
        set_cached_scrape = lambda url, content: None

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


def _try_stealth(url: str, verbose: bool, timeout: int) -> str:
    """Render a URL with the patched-Firefox stealth engine, or None."""
    if stealth_tier is None or not stealth_tier.available():
        if verbose:
            print("[scrapepage] Stealth tier unavailable (invisible_playwright engine not installed)", file=sys.stderr)
        return None

    if _stealth_backend is not None:
        if verbose:
            print(f"[scrapepage] Warm stealth browser render for '{url}'", file=sys.stderr)
        return _stealth_backend(url, timeout)

    if verbose:
        print(f"[scrapepage] Stealth tier rendering '{url}' with patched Firefox...", file=sys.stderr)
    return stealth_tier.scrape(url, fast_html_to_markdown, timeout=max(timeout, 20), verbose=verbose)



def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape a webpage and convert it to clean Markdown with tiered fast-fetch & anti-bot stealth fallback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  scrapepage https://example.com
  scrapepage https://example.com https://docs.python.org/3/
  scrapepage https://example.com --stealth
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


def fast_html_to_markdown(html_content: str, base_url: str) -> str:
    """Strip non-content tags, resolve links, and convert HTML to Markdown."""
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
    return markdownify(cleaned, heading_style="ATX", strip=["script", "style", "noscript"], wrap=False)


def try_fast_scrape(url: str, timeout: int = 10) -> tuple[bool, str]:
    """Attempt ultra-fast HTTP scrape using primp (Rust HTTP client with browser TLS impersonation)."""
    try:
        import primp
        client = primp.Client(impersonate="random", follow_redirects=True, timeout=timeout)
        resp = client.get(url)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        text = resp.text
        if not text or len(text.strip()) < 80:
            return False, "Response body too short"

        # Detect bot challenge or JS wall
        for pat in CHALLENGE_PATTERNS:
            if pat.search(text[:3000]):
                return False, "Bot challenge detected"

        # A consent wall is a JS interstitial the HTTP tier can't clear
        if looks_like_consent(text):
            return False, "Consent wall"

        md = fast_html_to_markdown(text, url)
        md = remove_long_chunks(md)
        if len(md.strip()) < 40:
            return False, "Insufficient markdown extracted"

        return True, md
    except Exception as e:
        return False, str(e)


def scrape_single(url: str, force_stealth: bool = False, verbose: bool = False, timeout: int = 20, no_cache: bool = False) -> str:
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Tier 0: Fast Cross-Agent Shared Cache (< 2ms)
    if not no_cache and not force_stealth:
        cached = get_cached_scrape(url)
        if cached:
            if verbose:
                print(f"[scrapepage] Cache hit for '{url}'", file=sys.stderr)
            return cached

    # Tier 0.5: Persistent Micro-Daemon (warm connection pool & warm stealth browser)
    if not os.environ.get("INSIDE_DAEMON") and is_daemon_alive():
        daemon_res = daemon_scrape(url, timeout=timeout, no_cache=no_cache, force_stealth=force_stealth)
        if daemon_res:
            if verbose:
                print(f"[scrapepage] Micro-daemon served '{url}'", file=sys.stderr)
            return daemon_res

    # Tier 1: Fast HTTP Path (Rust primp: browser TLS impersonation, no JS)
    if not force_stealth:
        fast_timeout = min(timeout, 8)
        ok, result = try_fast_scrape(url, timeout=fast_timeout)
        if ok:
            if verbose:
                print(f"[scrapepage] Fast HTTP tier succeeded for '{url}'", file=sys.stderr)
            set_cached_scrape(url, result)
            return result
        if verbose:
            print(f"[scrapepage] Fast HTTP tier bypassed ({result}) for '{url}'", file=sys.stderr)

    # Tier 2: Anti-bot stealth engine (patched Firefox) — renders JS and clears
    # anti-bot walls that the HTTP tier cannot. Last and only browser tier.
    if verbose:
        print(f"[scrapepage] Escalating to stealth tier for '{url}'", file=sys.stderr)
    error = None
    try:
        content = _try_stealth(url, verbose, timeout)
    except Exception as e:
        content = None
        error = format_error(str(e))
        if verbose:
            print(f"[scrapepage] Stealth tier failed for '{url}': {error}", file=sys.stderr)

    if content and len(content.strip()) >= MIN_CONTENT:
        set_cached_scrape(url, content)
        return content

    if stealth_tier is None or not stealth_tier.available():
        raise RuntimeError(
            "Error: The stealth engine is not installed, so there is no browser fallback. "
            f"Run '.\\scripts\\install.ps1' (or 'invisible-playwright fetch'). '{url}'"
        )
    detail = f": {error}" if error else ""
    raise RuntimeError(f"Error: Page doesn't seem to exist. Failed to scrape. Don't attempt again. '{url}'{detail}")


def main():
    args = parse_args()
    if not args.urls:
        print("Error: URL is required.\nUsage: scrapepage <url> [url2 ...]", file=sys.stderr)
        sys.exit(1)

    urls = args.urls

    # Single URL: output directly without headers for seamless piping and backwards compatibility
    if len(urls) == 1:
        try:
            content = scrape_single(
                urls[0],
                force_stealth=args.stealth,
                verbose=args.verbose,
                timeout=args.timeout,
                no_cache=args.no_cache,
            )
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
            return (
                u,
                scrape_single(
                    u,
                    force_stealth=args.stealth,
                    verbose=args.verbose,
                    timeout=args.timeout,
                    no_cache=args.no_cache,
                ),
                None,
            )
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
