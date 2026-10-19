param(
    [string]$ProjectDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path $ProjectDir).Path

Write-Host "=== Setting up in: $ProjectDir ===" -ForegroundColor Cyan

# 1. Create virtual environment
Write-Host "`n[1/5] Creating virtual environment..." -ForegroundColor Yellow
python -m venv "$ProjectDir\.venv"
$python = "$ProjectDir\.venv\Scripts\python.exe"
$pip = "$ProjectDir\.venv\Scripts\pip.exe"

# 2. Install dependencies from requirements.txt
Write-Host "[2/5] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $pip install -r "$ProjectDir\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# 3. Fetch the anti-bot stealth engine (patched Firefox) used by the browser
#    tier. One-time download (~250 MB); the tier is simply skipped if missing.
Write-Host "[3/5] Fetching anti-bot stealth engine (patched Firefox, ~250 MB one-time)..." -ForegroundColor Yellow
& "$ProjectDir\.venv\Scripts\invisible-playwright.exe" fetch
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Stealth engine fetch returned a non-zero status; the browser tier stays disabled until 'invisible-playwright fetch' succeeds."
}

# 4. Create activation scripts (relative-path, so folder is movable)
Write-Host "[4/5] Creating activation scripts..." -ForegroundColor Yellow
@"
`$projectDir = Split-Path -Parent `$MyInvocation.MyCommand.Path
& (Join-Path `$projectDir ".venv\Scripts\Activate.ps1")
"@ | Set-Content -Path "$ProjectDir\activate.ps1"

@"
@echo off
set "PROJECT_DIR=%~dp0"
call "%PROJECT_DIR%.venv\Scripts\activate.bat"
"@ | Set-Content -Path "$ProjectDir\activate.bat"

# 5. Create .gitignore
Write-Host "[5/5] Creating .gitignore..." -ForegroundColor Yellow
@"
# Virtual environment
.venv/

# Python cache
__pycache__/
*.pyc

# Local data
.cache/
*_cache/
jobs/
"@ | Set-Content -Path "$ProjectDir\.gitignore" -Encoding ASCII

# Done
Write-Host "`n=== Setup complete! ===" -ForegroundColor Green
Write-Host "Run: .\activate.ps1   (to activate venv)" -ForegroundColor Green
