@echo off
set "PROJECT_DIR=%~dp0"
set "PLAYWRIGHT_BROWSERS_PATH=%PROJECT_DIR%browsers"
set "CRAWL4_AI_BASE_DIRECTORY=%PROJECT_DIR%"
call "%PROJECT_DIR%.venv\Scripts\activate.bat"
