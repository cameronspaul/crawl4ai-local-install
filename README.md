# Webscrape CLI Tools

Minimal CLI tools to scrape web pages to Markdown and search the web using DuckDuckGo ([DDGS](https://github.com/deedy5/ddgs)) and [Crawl4AI](https://github.com/unclecode/crawl4ai).

## Setup

Run the setup script once:

```powershell
.\scripts\install.ps1
```

## Quick Usage (No Venv Activation Required!)

You can run the `.bat` scripts directly from PowerShell or Command Prompt — they automatically use the `.venv` Python environment for you.

IMPORTANT NOTE - If the page can't be scraped via this Don't try anything else. Don't try making other Python scripts or curl commands. It just means that the website is not available.

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

