$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $projectDir "browsers"
$env:CRAWL4_AI_BASE_DIRECTORY = $projectDir
& (Join-Path $projectDir ".venv\Scripts\Activate.ps1")
