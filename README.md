# Webscrape Test

Minimal CLI to scrape a single URL to markdown using [Crawl4AI](https://github.com/unclecode/crawl4ai) with a local Playwright browser.

## Setup

```powershell
.\install.ps1
```

## Usage

```powershell
.venv\Scripts\python.exe test_crawl.py https://example.com
```

Or activate the venv first:

```powershell
.venv\Scripts\Activate.ps1
python test_crawl.py https://example.com
```

The script automatically uses the local Playwright browsers in `browsers/` — no global installs needed.
