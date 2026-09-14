@echo off
setlocal
set "ROOT_DIR=%~dp0"
set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found at "%ROOT_DIR%.venv".
    exit /b 1
)

if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="status" goto status
if "%1"=="restart" goto restart

echo Usage: daemon.bat {start^|stop^|status^|restart}
exit /b 1

:start
echo [INFO] Starting persistent scraping daemon...
powershell -NoProfile -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '-u -X utf8 \"%ROOT_DIR%src\daemon.py\"' -WorkingDirectory '%ROOT_DIR%' -WindowStyle Hidden"
powershell -NoProfile -Command "Start-Sleep -Seconds 2"
"%PYTHON_EXE%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/ping', timeout=2); print('[OK] Daemon active on http://127.0.0.1:8765')" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start daemon.
    exit /b 1
)
exit /b 0

:stop
echo [INFO] Stopping persistent scraping daemon...
"%PYTHON_EXE%" -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/shutdown', data=b'{}', headers={'Content-Type': 'application/json'}))" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Daemon stopped successfully.
) else (
    echo [INFO] Daemon was not running.
)
exit /b 0

:status
"%PYTHON_EXE%" -c "import urllib.request, json; resp = json.loads(urllib.request.urlopen('http://127.0.0.1:8765/ping', timeout=1).read().decode()); print(f'[ONLINE] Daemon status: {resp.get(\"status\")} (uptime: {resp.get(\"uptime\", 0):.1f}s)')" 2>nul
if %errorlevel% neq 0 (
    echo [OFFLINE] Daemon is not running.
)
exit /b 0

:restart
call :stop
powershell -NoProfile -Command "Start-Sleep -Milliseconds 500"
goto start
