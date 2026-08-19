import argparse
import io
import json
import os
import re
import sys
from urllib.parse import urlparse
from ddgs import DDGS

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

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


def search(query: str, max_results: int = 10, search_type: str = "text", region: str = "wt-wt", timelimit: str = None):
    ddgs = DDGS()
    kwargs = {"max_results": max_results}
    if region:
        kwargs["region"] = region
    if timelimit:
        kwargs["timelimit"] = timelimit

    if search_type == "news":
        raw_results = list(ddgs.news(query, **kwargs))
        for r in raw_results:
            if "url" in r and "href" not in r:
                r["href"] = r["url"]
    else:
        raw_results = list(ddgs.text(query, **kwargs))

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
    parser.add_argument("query", nargs="?", help="Search query string")
    parser.add_argument(
        "max_results_pos",
        nargs="?",
        type=int,
        default=None,
        help="Maximum results to return (positional)",
    )
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
        "-o", "--output",
        help="Save output to a specified file path",
    )
    parser.add_argument(
        "-r", "--region",
        default="wt-wt",
        help="Search region (e.g. us-en, uk-en, wt-wt; default: wt-wt)",
    )
    parser.add_argument(
        "-t", "--time",
        choices=["d", "w", "m", "y"],
        default=None,
        help="Time filter (d=day, w=week, m=month, y=year)",
    )

    args = parser.parse_args()

    if not args.query:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    if args.max_results_pos is not None:
        args.max_results = args.max_results_pos

    if args.json:
        args.format = "json"
    elif args.markdown:
        args.format = "markdown"

    return args


def main():
    args = parse_args()
    search_type = "news" if args.news else "text"

    try:
        results = search(
            query=args.query,
            max_results=args.max_results,
            search_type=search_type,
            region=args.region,
            timelimit=args.time,
        )
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle saving to file if requested
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                if args.format == "json":
                    json.dump(results, f, indent=2, ensure_ascii=False)
                elif args.format == "markdown":
                    f.write(f"# Search Results: {args.query}\n\n")
                    for idx, r in enumerate(results, 1):
                        f.write(f"### {idx}. [{r['title']}]({r['url']})\n")
                        if r.get("date"):
                            f.write(f"- **Date:** {r['date']}\n")
                        f.write(f"> {r['snippet']}\n\n")
                else:
                    for idx, r in enumerate(results, 1):
                        f.write(f"[{idx}]\nTitle:   {r['title']}\nURL:     {r['url']}\n")
                        if r.get("site"):
                            f.write(f"Site:    {r['site']}\n")
                        if r.get("date"):
                            f.write(f"Date:    {r['date']}\n")
                        if r.get("snippet"):
                            f.write(f"Snippet: {r['snippet']}\n")
                        f.write("\n")
            print(f"Results saved to: {args.output}")
        except Exception as e:
            print(f"Error saving to {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Standard console output
    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.format == "markdown":
        print_markdown_results(results, args.query)
    else:
        print_clean_list(results, args.query)


if __name__ == "__main__":
    main()
