import argparse
import asyncio
import io
import os
import sys
from crawl4ai import AsyncWebCrawler

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
    return parser.parse_args()


async def scrape(url: str, output_file: str = None):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
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
        asyncio.run(scrape(args.url, args.output))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Scraping failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
