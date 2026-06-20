@echo off
chcp 65001 >nul 2>nul
title CodePaidie - Install
echo.
echo ========================================
echo   CodePaidie - Install
echo ========================================
echo.

cd /d "%~dp0"

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python not found. Install: https://python.org
    pause
    exit /b 1
)

:: Install deps
echo [1/2] Installing dependencies...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [X] pip install failed
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

:: Setup ngrok
echo [2/2] Setting up ngrok...
call "%~dp0setup.bat"

echo.
echo ========================================
echo   Install complete!
echo   Run start.bat to launch.
echo ========================================
pause
