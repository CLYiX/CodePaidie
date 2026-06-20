@echo off
chcp 65001 >nul 2>nul
title CodeF
echo.
echo ========================================
echo   CodeF
echo ========================================
echo.

:: Add ngrok to PATH
set "PATH=%USERPROFILE%\tools;%PATH%"

:: Check ngrok installed
where ngrok >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ngrok not found, running setup first...
    call "%~dp0setup.bat"
)

:: Check authtoken
ngrok config check >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] authtoken not set, running setup first...
    call "%~dp0setup.bat"
)

:: Start server
echo [1/2] Starting server...
cd /d "%~dp0"
start "CodeF" /min python run.py
timeout /t 2 /nobreak >nul

:: Read config and build ngrok command
set "NGROK_CMD=ngrok http 8000"
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$c = Get-Content '%~dp0config.json' -Raw | ConvertFrom-Json; if ($c.ngrok_user -and $c.ngrok_pass) { Write-Output ('--basic-auth=' + $c.ngrok_user + ':' + $c.ngrok_pass) }"`) do set "NGROK_AUTH=%%i"

if defined NGROK_AUTH (
    set "NGROK_CMD=ngrok http %NGROK_AUTH% 8000"
)

:: Start ngrok
echo [2/2] Starting ngrok tunnel...
echo.
%NGROK_CMD%

pause
