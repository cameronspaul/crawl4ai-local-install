import sys
from ddgs import DDGS


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else None
    if not query:
        print("Usage: python websearch.py <query> [max_results]", file=sys.stderr)
        sys.exit(1)

    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    results = DDGS().text(query, max_results=max_results)
    for r in results:
        print(f"{r['title']}\n{r['href']}\n{r['body']}\n")


if __name__ == "__main__":
    main()
