import argparse
import asyncio
import io
import os
import sys
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(PROJECT_DIR, "browsers"))
os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", PROJECT_DIR)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape a webpage and convert it to clean Markdown using Crawl4AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  scrapepage https://example.com
  scrapepage https://example.com -o example.md
"""
    )
    parser.add_argument("url", nargs="?", help="URL of the webpage to scrape")
    parser.add_argument(
        "-o", "--output",
        help="Save markdown output to the specified file path",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose crawler logs",
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


async def scrape(url: str, output_file: str = None, verbose: bool = False):
    browser_config = BrowserConfig(verbose=verbose)
    run_config = CrawlerRunConfig(verbose=verbose)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

        if not result.success:
            err_detail = format_error(result.error_message)
            print(f"Error: Page doesn't seem to exist. Failed to scrape. Don't attempt again. '{url}': {err_detail}", file=sys.stderr)
            if verbose and result.error_message:
                print(f"\nFull error details:\n{result.error_message}", file=sys.stderr)
            sys.exit(1)

        content = result.markdown or ""

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Scraped content saved to: {output_file}")
        else:
            print(content)


def main():
    args = parse_args()
    if not args.url:
        print("Error: URL is required.\nUsage: scrapepage <url> [-o output.md]", file=sys.stderr)
        sys.exit(1)

    if not args.url.startswith("http://") and not args.url.startswith("https://"):
        args.url = "https://" + args.url

    try:
        asyncio.run(scrape(args.url, args.output, verbose=args.verbose))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Scraping failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
