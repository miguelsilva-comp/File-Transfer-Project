@echo off
setlocal

echo.
echo ==================================
echo   File Transfer Hub
echo ==================================
echo.

set "PY_EXE=%~dp0.venv\Scripts\python.exe"

REM Prefer the project venv; fallback to PATH python if missing.
if exist "%PY_EXE%" (
    echo Using project Python: %PY_EXE%
) else (
    set "PY_EXE=python"
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH
        echo Please install Python from https://www.python.org/
        pause
        exit /b 1
    )
)

REM Check if requirements are installed
"%PY_EXE%" -c "import flask, zeroconf" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    "%PY_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting File Transfer Hub...
echo.
"%PY_EXE%" app.py

pause
