# Webscrape CLI Tools

Minimal CLI tools to scrape web pages to Markdown and search the web using DuckDuckGo ([DDGS](https://github.com/deedy5/ddgs)) plus an anti-bot stealth engine ([invisible_playwright](https://github.com/feder-cr/invisible_playwright), a patched anti-detect Firefox).

## Setup

Run the setup script once:

```powershell
.\scripts\install.ps1
```

## Quick Usage (No Venv Activation Required!)

You can run the `.bat` scripts directly from PowerShell or Command Prompt — they automatically use the `.venv` Python environment for you.

IMPORTANT NOTE - If a page still can't be scraped, don't try anything else (no ad-hoc Python scripts or curl commands): it means the site is genuinely unavailable, not that the tool needs a different approach. Bot-protected pages are handled automatically by the stealth tier described below.

### 🔍 Search the Web (`websearch.bat`)

**Basic search:**
```powershell
.\websearch.bat "python asyncio tutorial"
.\websearch.bat "machine learning" 5
```

**Output formats:**
- **Clean formatted list (default):**
  ```powershell
  .\websearch.bat "fastapi" -n 5
  ```
- **Markdown list:**
  ```powershell
  .\websearch.bat "fastapi" -n 5 --markdown
  ```
- **JSON:**
  ```powershell
  .\websearch.bat "fastapi" -n 5 --json
  ```

---

### 🕷️ Scrape a Page (`scrapepage.bat`)

**Scrape page to Markdown:**
```powershell
.\scrapepage.bat https://example.com
```

**Force a specific rendering tier:**
```powershell
.\scrapepage.bat https://example.com --stealth   # force the anti-bot stealth browser
.\scrapepage.bat https://example.com --no-cache  # bypass the local cache
.\scrapepage.bat https://example.com https://example.org   # several URLs in parallel
```

### How scraping picks a tier

Each URL walks down a ladder, stopping at the first tier that returns real content:

1. **Cache** — a previous result younger than 2 hours (instant).
2. **Micro-daemon** — if `daemon.bat start` is running, a warm process with pooled connections serves the request.
3. **Fast HTTP** (`primp`) — impersonated browser TLS, no JS. Handles most sites in well under a second.
4. **Stealth Firefox** (`invisible_playwright`) — the anti-bot engine and the only browser tier. A patched Firefox whose fingerprint is produced inside the engine and whose pointer motion is humanized; it renders JS and gets past Cloudflare / DataDome / PerimeterX walls.

If the fast tier can't get real content (no JS, a bot wall, or an empty shell) the request escalates to the stealth browser automatically. A page that still fails is genuinely unavailable — or waiting on interactive human verification, such as a press-and-hold captcha.

> **First run downloads the stealth engine.** `.\scripts\install.ps1` runs this for you; to do it by hand:
> ```powershell
> .\.venv\Scripts\invisible-playwright.exe fetch   # ~250 MB, one-time, sha256-verified
> ```
> If the engine is absent, there is no browser fallback — the fast HTTP tier still works.

### Keeping it fast

```powershell
.\daemon.bat start     # warm process: pooled HTTP client + one reused stealth browser
.\daemon.bat status
.\daemon.bat stop
```

The stealth tier is a real browser, so a cold render costs ~10 s. With the daemon running the browser is reused and the same page comes back in about **1–4 s**. For a handful of pages the extra speed matters; for one-off scrapes it's fine without the daemon.

