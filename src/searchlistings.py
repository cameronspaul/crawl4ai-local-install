"""Scrape retailer search results and print them as neat, uniform listings.

This builds on the tiered fetch engine in :mod:`scrapepage` (cache -> fast HTTP
-> anti-bot stealth browser) and the per-site parsers in :mod:`src.listings`.

Examples:
    python src/searchlistings.py "power supply"
    python src/searchlistings.py "rtx 3060" -s scan -s ccl -n 10
    python src/searchlistings.py --url "https://www.ebuyer.com/search?q=motherboard+am4"
    python src/searchlistings.py "ram ddr4" --format json > listings.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Ensure UTF-8 output on the Windows console (prices contain £ etc.).
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from scrapepage import scrape_html  # noqa: E402

try:
    from listings import SITES, detect_site, parse_listings  # noqa: E402
except ImportError:  # pragma: no cover - running as a script from src/
    from src.listings import SITES, detect_site, parse_listings  # noqa: E402


FORMATS = ("text", "md", "json", "csv")
WIDTH = 72


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Scrape PC-part retailer searches into a clean, readable list of listings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  searchlistings "power supply"
  searchlistings "rtx 3060" -s scan -s ccl -s gpused -n 10
  searchlistings --url "https://www.scan.co.uk/search?q=power+supply"
  searchlistings "motherboard am4" --format json > listings.json
""",
    )
    parser.add_argument("query", nargs="?", help="Search terms, e.g. 'power supply 850w'")
    parser.add_argument(
        "-s", "--site",
        action="append",
        metavar="NAME",
        help="Retailer to search (repeatable). Default: all. "
             "Choices: " + ", ".join(SITES),
    )
    parser.add_argument(
        "--url",
        action="append",
        metavar="URL",
        help="Use a full search URL directly instead of building one (repeatable).",
    )
    parser.add_argument(
        "-f", "--format",
        choices=FORMATS,
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=20,
        help="Maximum listings per retailer (default: 20).",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Fetch timeout in seconds.")
    parser.add_argument(
        "--no-cache", "--fresh",
        action="store_true",
        dest="no_cache",
        help="Bypass the local scrape cache (use for fresh prices/stock).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show fetch tier diagnostics.")
    return parser.parse_args(argv)


def _resolve_sites(names: list[str] | None) -> list:
    """Turn user-supplied site names/domains into parser modules."""
    if not names:
        return list(SITES.values())
    chosen = []
    for name in names:
        module = detect_site(name)
        if module is None:
            raise ValueError(
                f"Unknown site '{name}'. Available: {', '.join(SITES)}"
            )
        if module not in chosen:
            chosen.append(module)
    return chosen


def _query_from_url(url: str) -> str:
    """Pull the search terms out of a retailer URL for display purposes."""
    from urllib.parse import parse_qs, unquote_plus, urlparse

    values = parse_qs(urlparse(url).query)
    for key in ("q", "k", "stext", "query", "search"):
        if values.get(key):
            return unquote_plus(values[key][0]).replace("+", " ").strip()
    return ""


def _jobs(args) -> list[tuple[object, str, str, str]]:
    """Build (module, url, label, query) jobs from --url values or a query."""
    jobs: list[tuple[object, str, str, str]] = []
    if args.url:
        for url in args.url:
            module = detect_site(url)
            if module is None:
                raise ValueError(f"Could not identify the retailer for URL: {url}")
            jobs.append(
                (module, url, getattr(module, "SITE_NAME", "?"), _query_from_url(url))
            )
        return jobs

    if not args.query or not args.query.strip():
        raise ValueError("Provide a search query or use --url. See --help.")

    query = args.query.strip()
    for module in _resolve_sites(args.site):
        jobs.append(
            (
                module,
                module.build_search_url(query),
                getattr(module, "SITE_NAME", "?"),
                query,
            )
        )
    return jobs


def _scrape_job(job, args):
    module, url, label, query = job
    try:
        html = scrape_html(
            url,
            force_stealth=bool(getattr(module, "FORCE_STEALTH", False)),
            verbose=args.verbose,
            timeout=args.timeout,
            no_cache=args.no_cache,
        )
        listings = parse_listings(module, html, url)
        listings = listings[: max(0, args.limit)] if args.limit > 0 else listings
        return {"site": label, "query": query or "", "url": url, "listings": listings, "error": ""}
    except Exception as exc:  # one bad retailer must not kill the whole run
        message = str(exc).strip() or exc.__class__.__name__
        return {"site": label, "query": query or "", "url": url, "listings": [], "error": message}


def collect(args) -> list[dict]:
    jobs = _jobs(args)
    if len(jobs) == 1:
        return [_scrape_job(jobs[0], args)]
    with ThreadPoolExecutor(max_workers=min(len(jobs), 4)) as pool:
        return list(pool.map(lambda j: _scrape_job(j, args), jobs))


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _md_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def format_text(results: list[dict]) -> str:
    chunks: list[str] = []
    for block in results:
        header = f"{block['site']}  |  {block['query'] or 'search'}"
        if block["error"]:
            header += "  |  FAILED"
        elif block["listings"]:
            header += f"  |  {len(block['listings'])} listings"
        else:
            header += "  |  no listings"
        chunks.append("=" * WIDTH)
        chunks.append(header)
        chunks.append("=" * WIDTH)

        if block["error"]:
            chunks.append(f"  {block['error']}")
        else:
            for index, item in enumerate(block["listings"], 1):
                chunks.append(f" {index:>2}. {item['title'] or '(untitled)'}")
                detail = "   ".join(
                    part for part in (item["price"], item["note"]) if part
                )
                if detail:
                    chunks.append(f"     {detail}")
                if item["url"]:
                    chunks.append(f"     {item['url']}")
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def format_markdown(results: list[dict]) -> str:
    chunks: list[str] = []
    for block in results:
        title = f"## {block['site']} — {block['query'] or 'search'}"
        if block["error"]:
            title += f" (failed: {block['error']})"
        chunks.append(title)
        chunks.append("")
        if block["listings"]:
            chunks.append("| # | Product | Price | Note |")
            chunks.append("|---|---------|------:|------|")
            for index, item in enumerate(block["listings"], 1):
                link = f"[{_md_cell(item['title'])}]({item['url']})" if item["url"] else _md_cell(item["title"])
                chunks.append(
                    f"| {index} | {link} | {_md_cell(item['price'])} | {_md_cell(item['note'])} |"
                )
        else:
            chunks.append("_No listings found._")
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def format_json(results: list[dict]) -> str:
    payload = []
    for block in results:
        payload.append(
            {
                "site": block["site"],
                "query": block["query"],
                "search_url": block["url"],
                "count": len(block["listings"]),
                "error": block["error"],
                "listings": block["listings"],
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def format_csv(results: list[dict]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["site", "query", "title", "price", "url", "note"])
    for block in results:
        for item in block["listings"]:
            writer.writerow(
                [
                    block["site"],
                    block["query"],
                    item["title"],
                    item["price"],
                    item["url"],
                    item["note"],
                ]
            )
    return out.getvalue()


FORMATTERS = {
    "text": format_text,
    "md": format_markdown,
    "json": format_json,
    "csv": format_csv,
}


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        results = collect(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(FORMATTERS[args.format](results))

    if not any(block["listings"] for block in results):
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(130)
