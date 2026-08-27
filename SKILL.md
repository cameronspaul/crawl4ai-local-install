---
name: web-research
description: Use when the user wants to research a topic, find up-to-date information, answer a factual question about current events, compare data across multiple websites, or gather sources from the web. Performs live web searches and then reads (scrapes) the most relevant pages to pull out details. Do NOT use for purely local/code questions that don't need outside information.
---

# Web Research

This skill finds **current, real-world information** by searching the web and then **reading the actual pages** that look most relevant. It is designed for research: scan multiple websites, pick the best sources, and pull concrete details from them.

It uses the CLI tools in this repo:
- `websearch.bat` — live web search (DuckDuckGo). Returns titles, URLs, sites, dates, and snippets.
- `scrapepage.bat` — reads a full page and converts it to clean Markdown.

## Workflow

Follow this order for every research task.

### 1. Search broadly first

Run one or more searches with `websearch.bat`. Search more than once with different phrasings/keywords to cover different angles.

```powershell
.\websearch.bat "your topic query"
```

Useful options:
- `-n <N>` — number of results (default 10).
- `--news` — get news results with published dates (great for "what's the latest").
- `-t w` — time filter: `d` (day), `w` (week), `m` (month), `y` (year). Use for up-to-date data.
- `--markdown` — markdown-formatted list; `--json` for structured JSON.
- `-r <region>` — region, e.g. `us-en`, `uk-en`.

For "latest/current" questions, combine `--news` with a time filter:
```powershell
.\websearch.bat "latest <topic> 2026" --news -n 10 -t w
```

### 2. Pick the best sources

Look at the search results (titles, sites, dates, snippets). Choose the 3-6 most authoritative and relevant pages. Prefer primary sources (official docs, the actual company/product site, reputable outlets) and recent dates over blog spam and ad-heavy aggregators.

### 3. Read the pages

For each chosen source, scrape it to read the full content:

```powershell
.\scrapepage.bat https://example.com/article
```

Run several scrapes (they can be done in parallel). Read the scraped content to extract the specific facts, numbers, quotes, or details the user needs.

### 4. Synthesize

Combine what you found across sources into a clear, sourced answer. Note where sources agree or conflict. Reference which site/URL each claim came from.

## Rules

- **Always verify with real data.** Don't guess or rely on memory for current facts, prices, versions, or events — search and scrape instead.
- **Prefer multiple sources** for any factual claim. Cross-check by reading at least 2-3 pages for important facts.
- **Use time filters for anything time-sensitive** ("latest", "now", "this week", prices, versions).
- **If a page fails to scrape** (`scrapepage.bat` prints an error), treat it as unavailable and move on to another source. Do NOT try alternative curl/Python workarounds — a failure means the site is not accessible.
- Keep the final answer concise and organized, with the source URL next to each key claim.

## Example

User: "What are the latest 2026 features of FastAPI?"

1. `.\websearch.bat "FastAPI 2026 features" -n 10 -t m`
2. `.\websearch.bat "FastAPI release notes 2026" --news -n 10`
3. Read the official FastAPI docs/changelog and the top articles via `scrapepage.bat`.
4. Summarize with source URLs for each new feature.