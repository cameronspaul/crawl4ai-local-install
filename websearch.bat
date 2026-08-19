@echo off
setlocal
set "ROOT_DIR=%~dp0"
set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found at "%ROOT_DIR%.venv".
    echo Please run .\install.ps1 first.
    exit /b 1
)

"%PYTHON_EXE%" "%ROOT_DIR%websearch.py" %*
