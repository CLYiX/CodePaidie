@echo off
chcp 65001 >nul 2>nul
title ngrok Setup
echo.
echo ========================================
echo   ngrok Setup
echo ========================================
echo.

:: Add ngrok to PATH
set "PATH=%USERPROFILE%\tools;%PATH%"

:: Check ngrok
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ngrok not found, installing...
    winget install --id Ngrok.Ngrok --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo [X] Install failed. Download manually: https://ngrok.com/download
        pause
        exit /b 1
    )
    echo [OK] ngrok installed
    echo.
)

:: Check if authtoken already set
ngrok config check >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] authtoken already configured
    echo.
    pause
    exit /b 0
)

:: Prompt for token
echo Go to: https://dashboard.ngrok.com/get-started/your-authtoken
echo Copy your authtoken and paste below.
echo.
set /p TOKEN="Paste authtoken: "

if "%TOKEN%"=="" (
    echo [X] No token entered
    pause
    exit /b 1
)

ngrok config add-authtoken %TOKEN%
echo.
echo [OK] authtoken saved
echo.
pause
