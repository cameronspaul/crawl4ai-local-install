# Webscrape CLI Tools

Minimal CLI tools to scrape web pages to Markdown and search the web using DuckDuckGo ([DDGS](https://github.com/deedy5/ddgs)) and [Crawl4AI](https://github.com/unclecode/crawl4ai).

## Setup

Run the setup script once:

```powershell
.\install.ps1
```

## Quick Usage (No Venv Activation Required!)

You can run the `.bat` scripts directly from PowerShell or Command Prompt — they automatically use the `.venv` Python environment for you.

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
- **Save results to a file:**
  ```powershell
  .\websearch.bat "fastapi" -n 10 --markdown -o results.md
  ```

---

### 🕷️ Scrape a Page (`scrapepage.bat`)

**Scrape page to Markdown in terminal:**
```powershell
.\scrapepage.bat https://example.com
```

**Scrape and save directly to file:**
```powershell
.\scrapepage.bat https://example.com -o page.md
```

