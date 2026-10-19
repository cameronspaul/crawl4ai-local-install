param(
    [string]$ProjectDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path $ProjectDir).Path

Write-Host "=== Setting up in: $ProjectDir ===" -ForegroundColor Cyan

# 1. Create virtual environment
Write-Host "`n[1/6] Creating virtual environment..." -ForegroundColor Yellow
python -m venv "$ProjectDir\.venv"
$python = "$ProjectDir\.venv\Scripts\python.exe"
$pip = "$ProjectDir\.venv\Scripts\pip.exe"

# 2. Install dependencies from requirements.txt
Write-Host "[2/6] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $pip install -r "$ProjectDir\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# 3. Run setup with local paths
Write-Host "[3/6] Running crawl4ai-setup (local only)..." -ForegroundColor Yellow
$env:PLAYWRIGHT_BROWSERS_PATH = "$ProjectDir\browsers"
$env:CRAWL4_AI_BASE_DIRECTORY = $ProjectDir
& "$ProjectDir\.venv\Scripts\crawl4ai-setup.exe"
if ($LASTEXITCODE -ne 0) { throw "crawl4ai-setup failed" }

# 3b. Fetch the anti-bot stealth engine (patched Firefox) used by the stealth
#     tier. One-time download (~250 MB); the tier is simply skipped if missing.
Write-Host "[3b/6] Fetching anti-bot stealth engine (patched Firefox, ~250 MB one-time)..." -ForegroundColor Yellow
& "$ProjectDir\.venv\Scripts\invisible-playwright.exe" fetch
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Stealth engine fetch returned a non-zero status; the stealth tier stays disabled until 'invisible-playwright fetch' succeeds."
}

# 4. Create activation scripts (relative-path, so folder is movable)
Write-Host "[4/6] Creating activation scripts..." -ForegroundColor Yellow
@"
`$projectDir = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path `$projectDir "browsers"
`$env:CRAWL4_AI_BASE_DIRECTORY = `$projectDir
& (Join-Path `$projectDir ".venv\Scripts\Activate.ps1")
"@ | Set-Content -Path "$ProjectDir\activate.ps1"

@"
@echo off
set "PROJECT_DIR=%~dp0"
set "PLAYWRIGHT_BROWSERS_PATH=%PROJECT_DIR%browsers"
set "CRAWL4_AI_BASE_DIRECTORY=%PROJECT_DIR%"
call "%PROJECT_DIR%.venv\Scripts\activate.bat"
"@ | Set-Content -Path "$ProjectDir\activate.bat"

# 5. Create .gitignore
Write-Host "[5/6] Creating .gitignore..." -ForegroundColor Yellow
@"
# Virtual environment
.venv/

# Playwright / Patchright browser binaries
browsers/

# Crawl4AI data (cache, screenshots, db)
.crawl4ai/

# Python cache
__pycache__/
*.pyc

# Local job search / notes
jobs/
"@ | Set-Content -Path "$ProjectDir\.gitignore" -Encoding ASCII

# Done
Write-Host "`n=== Setup complete! ===" -ForegroundColor Green
Write-Host "Run: .\activate.ps1   (to activate venv with local paths)" -ForegroundColor Green
