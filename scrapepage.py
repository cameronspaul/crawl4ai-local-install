import sys
from ddgs import DDGS


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        print("Usage: python scrapepage.py <url>", file=sys.stderr)
        sys.exit(1)

    result = DDGS().extract(url, fmt="text_markdown")
    content = result.get("content", "")
    print(content)


if __name__ == "__main__":
    main()
