@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
title Publish to GitHub
echo.
echo ========================================
echo   Publish to GitHub
echo ========================================
echo.

:: Check git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] git not found. Install: https://git-scm.com
    pause
    exit /b 1
)

cd /d "%~dp0"

:: Init if needed
if not exist ".git" (
    echo [1/5] Initializing git repo...
    git init
    echo.
)

:: Check remote
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo Enter your GitHub repo URL:
    echo   Example: https://github.com/YOUR_USERNAME/chatgpt-local-bridge.git
    echo.
    set /p REPO_URL="URL: "
    if "!REPO_URL!"=="" (
        echo [X] No URL entered
        pause
        exit /b 1
    )
    git remote add origin !REPO_URL!
    echo [OK] Remote added
    echo.
)

:: Stage
echo [2/5] Staging files...
git add -A
echo.

:: Status
echo [3/5] Changes:
git status --short
echo.

:: Commit
set /p MSG="Commit message (default: initial release): "
if "%MSG%"=="" set "MSG=initial release"
echo.
echo [4/5] Committing...
git commit -m "%MSG%"
echo.

:: Push
echo [5/5] Pushing to GitHub...
git push -u origin main 2>nul || git push -u origin master
echo.

echo ========================================
echo   Done!
echo ========================================
pause
