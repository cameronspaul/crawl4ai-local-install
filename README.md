# Webscrape Test

Minimal CLI tools to scrape URLs and search the web using [DDGS](https://github.com/deedy5/ddgs).

## Setup

```powershell
.\install.ps1
```

## Usage

Activate the venv first:

```powershell
.venv\Scripts\Activate.ps1
```

### Search the web - query amount of results you want

```powershell
python websearch.py "live free or die" 20
```

### Scrape a page to markdown

```powershell
python scrapepage.py https://example.com
```
