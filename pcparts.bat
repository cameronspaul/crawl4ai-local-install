@echo off
setlocal
set "ROOT_DIR=%~dp0"
set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found at "%ROOT_DIR%.venv".
    echo Please run .\scripts\install.ps1 first.
    exit /b 1
)

rem Convenience run of all seven example searches in one neat, readable list.
rem Extra arguments are passed through, e.g. pcparts.bat --format md -n 10
"%PYTHON_EXE%" -O -X utf8 "%ROOT_DIR%src\searchlistings.py" ^
  --url "https://www.scan.co.uk/search?q=power+supply" ^
  --url "https://www.overclockers.co.uk/search?q=ram+ddr4&search-button=&lang=en_GB" ^
  --url "https://www.ebuyer.com/search?q=motherboard+am4" ^
  --url "https://www.amazon.co.uk/s?k=power+supply+850w&crid=34EUWHD0CEJWU&sprefix=power+su%2Caps%2C116&ref=nb_sb_ss_mvt-t11-ranker_2_8" ^
  --url "https://uk.webuy.com/search?stext=rtx%203060" ^
  --url "https://www.gpused.co.uk/collections/everything" ^
  --url "https://www.cclonline.com/search?query=rtx+3060" ^
  %*
