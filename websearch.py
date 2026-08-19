import argparse
import io
import json
import os
import sys
from ddgs import DDGS

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def search(query: str, max_results: int = 10, region: str = "wt-wt", timelimit: str = None):
    ddgs = DDGS()
    kwargs = {"max_results": max_results}
    if region:
        kwargs["region"] = region
    if timelimit:
        kwargs["timelimit"] = timelimit
    return list(ddgs.text(query, **kwargs))


def print_rich_results(results, query: str):
    console = Console()
    
    console.print()
    console.print(
        Rule(
            f"[bold cyan]🔍 Web Search Results[/bold cyan] [dim]({len(results)} found)[/dim]",
            style="cyan",
        )
    )
    console.print(f"[dim]Query:[/dim] [bold yellow]\"{query}\"[/bold yellow]\n")

    if not results:
        console.print("[bold red]No results found.[/bold red]\n")
        return

    for idx, r in enumerate(results, 1):
        title = r.get("title", "No Title").strip()
        url = r.get("href", "").strip()
        body = r.get("body", "").strip()

        content = Text()
        content.append(f"🔗 {url}\n", style="bold underline blue")
        if body:
            content.append(f"\n{body}", style="bright_white")

        panel = Panel(
            content,
            title=f"[bold green]#{idx}[/bold green] [bold white]{title}[/bold white]",
            title_align="left",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        console.print(panel)
        console.print()


def print_simple_results(results):
    for r in results:
        line = f"{r.get('title')}\n{r.get('href')}\n{r.get('body')}\n\n"
        sys.stdout.write(line)


def print_markdown_results(results, query: str):
    print(f"# Search Results: {query}\n")
    for idx, r in enumerate(results, 1):
        print(f"### {idx}. [{r.get('title')}]({r.get('href')})")
        print(f"> {r.get('body')}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search DuckDuckGo with clean, formatted output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  websearch "python asyncio tutorial"
  websearch "crawl4ai documentation" 5
  websearch "latest tech news" --format markdown
  websearch "fastapi" -n 5 --json
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
        "-f", "--format",
        choices=["rich", "simple", "markdown", "json"],
        default="rich",
        help="Output format (default: rich)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for --format json",
    )
    parser.add_argument(
        "--markdown", "--md",
        action="store_true",
        dest="markdown",
        help="Shortcut for --format markdown",
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

    try:
        results = search(
            query=args.query,
            max_results=args.max_results,
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
                        f.write(f"### {idx}. [{r.get('title')}]({r.get('href')})\n")
                        f.write(f"> {r.get('body')}\n\n")
                else:
                    for r in results:
                        f.write(f"{r.get('title')}\n{r.get('href')}\n{r.get('body')}\n\n")
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
    elif args.format == "simple" or not HAS_RICH:
        print_simple_results(results)
    else:
        print_rich_results(results, args.query)


if __name__ == "__main__":
    main()
