import argparse
import io
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from ddgs import DDGS

# Persistent micro-daemon client
try:
    from daemon_client import is_daemon_alive, daemon_search
except ImportError:
    try:
        from src.daemon_client import is_daemon_alive, daemon_search
    except ImportError:
        is_daemon_alive = lambda: False
        daemon_search = lambda *args, **kwargs: None

# Fast local cross-agent cache
try:
    from cache import get_cached_search, set_cached_search, make_search_key
except ImportError:
    try:
        from src.cache import get_cached_search, set_cached_search, make_search_key
    except ImportError:
        get_cached_search = lambda key, ttl=1800: None
        set_cached_search = lambda key, results: None
        make_search_key = lambda *args: ""

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# Fast web search backends (skips Wikipedia/Grokipedia sequential bottleneck in auto mode)
FAST_TEXT_BACKENDS = "yahoo,yandex,brave,duckduckgo,startpage,mojeek"

# Regex to capture leading dates in search snippets (e.g. "Aug 3, 2026 ·", "2 days ago ·", "2024-05-12 ·")
DATE_PREFIX_REGEX = re.compile(
    r'^((?:\d{1,2}\s+(?:secs?|seconds?|mins?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago)|'
    r'(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})|'
    r'(?:\d{4}-\d{2}-\d{2}))\s*[·•\-\uFFFD\u00B7\s]\s*',
    re.IGNORECASE,
)


def extract_date_and_clean_body(body: str, raw_date: str = None) -> tuple[str, str]:
    """Extract published date if present and clean it from the body snippet."""
    date = raw_date or ""
    clean_body = body or ""

    if date:
        # If ISO format from news API (e.g., 2026-08-16T12:00:00+00:00)
        date = date.split("T")[0] if "T" in date else date
    elif clean_body:
        match = DATE_PREFIX_REGEX.search(clean_body)
        if match:
            date = match.group(1).strip()
            clean_body = DATE_PREFIX_REGEX.sub("", clean_body).strip()

    return date, clean_body


def search(
    query: str,
    max_results: int = 10,
    search_type: str = "text",
    region: str = None,
    timelimit: str = None,
    backend: str = "fast",
    no_cache: bool = False,
):
    cache_key = make_search_key(query, search_type, max_results, region, backend)
    if not no_cache:
        cached = get_cached_search(cache_key)
        if cached:
            return cached

    # Persistent micro-daemon path (warm pooled HTTP client)
    if not os.environ.get("INSIDE_DAEMON") and is_daemon_alive() and not timelimit:
        daemon_res = daemon_search(
            query=query,
            max_results=max_results,
            search_type=search_type,
            region=region,
            backend=backend,
            no_cache=no_cache,
        )
        if daemon_res is not None:
            return daemon_res

    ddgs = DDGS()
    kwargs = {"max_results": max_results}
    # Only pass region if non-default to prevent unnecessary DDGS region-routing delay
    if region and region != "wt-wt":
        kwargs["region"] = region
    if timelimit:
        kwargs["timelimit"] = timelimit

    if search_type == "news":
        raw_results = list(ddgs.news(query, **kwargs))
        for r in raw_results:
            if "url" in r and "href" not in r:
                r["href"] = r["url"]
    else:
        # Fast path for text search: prioritize general web engines over Wikipedia/Grokipedia
        raw_results = []
        target_backend = FAST_TEXT_BACKENDS if backend == "fast" else backend

        if target_backend:
            try:
                raw_results = list(ddgs.text(query, backend=target_backend, **kwargs))
            except Exception:
                raw_results = []

        # Automatic fallback to 'auto' if fast backends didn't yield results
        if not raw_results and (backend == "fast" or not target_backend):
            try:
                raw_results = list(ddgs.text(query, backend="auto", **kwargs))
            except Exception:
                raw_results = []

    # Process results with cleaned dates and metadata
    processed_results = []
    for r in raw_results:
        url = r.get("href", "").strip()
        body = r.get("body", "").strip()
        raw_date = r.get("date", "")
        date, clean_body = extract_date_and_clean_body(body, raw_date)

        domain = ""
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
            except Exception:
                domain = ""

        processed_results.append({
            "title": r.get("title", "").strip(),
            "url": url,
            "site": domain,
            "date": date if date else None,
            "source": r.get("source", ""),
            "snippet": clean_body,
        })

    if processed_results and not no_cache:
        set_cached_search(cache_key, processed_results)

    return processed_results


def print_clean_list(results, query: str):
    if not results:
        print(f"\nNo results found for: \"{query}\"\n")
        return

    print(f"\nSearch results for \"{query}\" ({len(results)} results):\n")

    for idx, r in enumerate(results, 1):
        print(f"[{idx}]")
        print(f"Title:   {r['title']}")
        print(f"URL:     {r['url']}")
        if r.get("site"):
            print(f"Site:    {r['site']}")
        if r.get("source"):
            print(f"Source:  {r['source']}")
        if r.get("date"):
            print(f"Date:    {r['date']}")
        if r.get("snippet"):
            print(f"Snippet: {r['snippet']}")
        print()  # Blank line separator between items


def print_markdown_results(results, query: str):
    print(f"# Search Results: {query}\n")
    for idx, r in enumerate(results, 1):
        print(f"### {idx}. [{r['title']}]({r['url']})")
        if r.get("date") or r.get("site"):
            meta = []
            if r.get("site"):
                meta.append(f"**Site:** {r['site']}")
            if r.get("date"):
                meta.append(f"**Date:** {r['date']}")
            print(f"- {' | '.join(meta)}")
        if r.get("snippet"):
            print(f"> {r['snippet']}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search the web with clean, structured formatted results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  websearch "python asyncio tutorial"
  websearch "crawl4ai documentation" 5
  websearch "ai technology" --news
  websearch "fastapi" --json
"""
    )
    parser.add_argument("queries", nargs="*", help="Search query string(s) (supports multiple for parallel batch search)")
    parser.add_argument(
        "-n", "--num",
        dest="max_results",
        type=int,
        default=10,
        help="Maximum number of results to fetch (default: 10)",
    )
    parser.add_argument(
        "--news",
        action="store_true",
        help="Search news specifically (includes date and news source)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["list", "markdown", "json"],
        default="list",
        help="Output format: list (default), markdown, json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for JSON output format",
    )
    parser.add_argument(
        "--markdown", "--md",
        action="store_true",
        dest="markdown",
        help="Shortcut for Markdown output format",
    )
    parser.add_argument(
        "-r", "--region",
        default=None,
        help="Search region (e.g. us-en, uk-en, wt-wt; default: wt-wt)",
    )
    parser.add_argument(
        "-t", "--time",
        choices=["d", "w", "m", "y"],
        default=None,
        help="Time filter (d=day, w=week, m=month, y=year)",
    )
    parser.add_argument(
        "-b", "--backend",
        default="fast",
        help="Search backend: 'fast' (default, optimized web engines), 'auto', or comma-separated engine names",
    )
    parser.add_argument(
        "--no-cache", "--fresh",
        dest="no_cache",
        action="store_true",
        help="Bypass local cache and perform live search",
    )

    args = parser.parse_args()

    raw_queries = args.queries
    if not raw_queries:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    # Check if the last positional argument is an integer max_results (e.g. websearch "foo bar" 5)
    if len(raw_queries) > 1 and raw_queries[-1].isdigit() and args.max_results == 10:
        args.max_results = int(raw_queries[-1])
        queries = raw_queries[:-1]
    else:
        queries = raw_queries

    args.queries = queries

    if args.json:
        args.format = "json"
    elif args.markdown:
        args.format = "markdown"

    return args


def main():
    args = parse_args()
    search_type = "news" if args.news else "text"

    if len(args.queries) == 1:
        query = args.queries[0]
        try:
            results = search(
                query=query,
                max_results=args.max_results,
                search_type=search_type,
                region=args.region,
                timelimit=args.time,
                backend=args.backend,
                no_cache=args.no_cache,
            )
        except Exception as e:
            print(f"Search failed: {e}", file=sys.stderr)
            sys.exit(1)

        # Standard console output
        if args.format == "json":
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif args.format == "markdown":
            print_markdown_results(results, query)
        else:
            print_clean_list(results, query)
        return

    # Multi-query batch parallel execution (Option D)
    def run_one(q):
        try:
            return q, search(
                query=q,
                max_results=args.max_results,
                search_type=search_type,
                region=args.region,
                timelimit=args.time,
                backend=args.backend,
                no_cache=args.no_cache,
            ), None
        except Exception as err:
            return q, [], str(err)

    max_workers = min(len(args.queries), 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        batch_results = list(executor.map(run_one, args.queries))

    if args.format == "json":
        out = {q: res for q, res, err in batch_results}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.format == "markdown":
        for idx, (q, res, err) in enumerate(batch_results):
            if idx > 0:
                print("\n---\n")
            if err:
                print(f"# Search Results: {q}\n\n*Failed: {err}*\n")
            else:
                print_markdown_results(res, q)
    else:
        for idx, (q, res, err) in enumerate(batch_results):
            if idx > 0:
                print("\n" + "=" * 80 + "\n")
            if err:
                print(f"\nSearch failed for \"{q}\": {err}\n")
            else:
                print_clean_list(res, q)


if __name__ == "__main__":
    main()
