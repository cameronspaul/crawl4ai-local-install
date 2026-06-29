import asyncio
import io
import os
import sys
from crawl4ai import *

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(PROJECT_DIR, "browsers"))
os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", PROJECT_DIR)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        print("Usage: python scrapepage.py <url>", file=sys.stderr)
        sys.exit(1)
    if not url.startswith("http"):
        print(f"Invalid URL: {url}", file=sys.stderr)
        sys.exit(1)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        print(result.markdown or "")


if __name__ == "__main__":
    asyncio.run(main())
