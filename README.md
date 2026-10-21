# Webscrape CLI Tools

Minimal CLI tools to scrape web pages to Markdown (or raw HTML) and search the web using DuckDuckGo ([DDGS](https://github.com/deedy5/ddgs)) plus an anti-bot stealth engine ([invisible_playwright](https://github.com/feder-cr/invisible_playwright), a patched anti-detect Firefox).

## Setup

Run the setup script once:

```powershell
.\scripts\install.ps1
```

## Quick Usage (No Venv Activation Required!)

You can run the `.bat` scripts directly from PowerShell or Command Prompt — they automatically use the `.venv` Python environment for you.

IMPORTANT NOTE - If a page still can't be scraped, don't try anything else (no ad-hoc Python scripts or curl commands): it means the site is genuinely unavailable, not that the tool needs a different approach. Bot-protected pages are handled automatically by the stealth tier described below.

### 🔍 Search the Web (`websearch.bat`)

```powershell
.\websearch.bat "python asyncio tutorial"
.\websearch.bat "machine learning" 5
.\websearch.bat "fastapi" -n 5 --markdown
.\websearch.bat "fastapi" -n 5 --json
.\websearch.bat "latest travel rule" --news -t w
```

Search options: `-n <N>` (default 10), `--news`, `-t d|w|m|y`, `--markdown` / `--json`, `-r <region>` (e.g. `uk-en`), `--no-cache` / `--fresh`.

### 🕷️ Scrape a Page (`scrapepage.bat`)

**Scrape page to Markdown:**

```powershell
.\scrapepage.bat https://example.com
```

**Options:**

```powershell
.\scrapepage.bat https://example.com --stealth    # force the anti-bot stealth browser
.\scrapepage.bat https://example.com --no-cache   # bypass the local cache
.\scrapepage.bat https://example.com --html       # raw rendered HTML instead of Markdown
.\scrapepage.bat https://example.com https://example.org   # several URLs in parallel
```

`--html` is useful when you want to run your own structured extraction (regex, an HTML parser, a JSON-LD reader) instead of reading the Markdown. Raw HTML is cached separately from Markdown for 15 minutes, so repeated structured reads stay fast; pass `--no-cache` for fresh prices or availability.

### How scraping picks a tier

Each URL stops at the first tier that returns real content:

1. **Cache** — a previous result younger than 2 hours (instant).
2. **Micro-daemon** — if `daemon.bat start` is running, a warm process with pooled connections serves the request.
3. **Fast HTTP** (`primp`) — impersonated browser TLS, no JS. Handles most sites in well under a second.
4. **Stealth Firefox** (`invisible_playwright`) — the anti-bot engine and the only browser tier. A patched Firefox whose fingerprint is produced inside the engine and whose pointer motion is humanized; it renders JS and gets past Cloudflare / DataDome / PerimeterX walls.

If the fast tier can't get real content (no JS, a bot wall, an empty shell, or an anti-bot `202`) the request escalates to the stealth browser automatically. A page that still fails is genuinely unavailable — or waiting on interactive human verification, such as a press-and-hold captcha.

### Keeping it fast

```powershell
.\daemon.bat start     # warm process: pooled HTTP client + one reused stealth browser
.\daemon.bat status
.\daemon.bat stop
.\daemon.bat restart   # reload code changes and recreate the warm browser
```

`start` is idempotent: it reports an already-running daemon instead of starting a second one. `stop` also terminates a wedged daemon process if the HTTP shutdown request cannot get through.

The stealth tier is a real browser, so a cold render costs ~10 s. With the daemon running the browser is reused and the same page comes back in about **1–4 s**. For a handful of pages the extra speed matters; for one-off scrapes it's fine without the daemon.

> **First run downloads the stealth engine.** `.\scripts\install.ps1` runs this for you; to do it by hand:
> ```powershell
> .\.venv\Scripts\invisible-playwright.exe fetch   # ~250 MB, one-time, sha256-verified
> ```
> If the engine is absent, there is no browser fallback — the fast HTTP tier still works.

### Programmatic use

`src/scrapepage.py` exposes two functions:

- `scrape_single(url, ...)` → clean Markdown (what the CLI prints by default).
- `scrape_html(url, ..., ready_markers=(...), settle_wait=...)` → raw rendered HTML (what `--html` uses).

`ready_markers` lets an integration wait for a specific client-rendered block (for example a results panel) instead of accepting a long app shell, and skips the fixed network-idle delay. The warm daemon accepts the same options over HTTP.

### Other platforms

The `.bat` wrappers are Windows-only. On macOS/Linux run the Python scripts directly with the venv interpreter, e.g. `python src/scrapepage.py <url>` and `python src/websearch.py <query>`.
