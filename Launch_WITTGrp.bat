@echo off
setlocal enabledelayedexpansion
title WITTGrp Download Manager v2

echo ============================================
echo   WITTGrp Download Manager v2.0
echo ============================================
cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo Python is not installed or not in PATH.
    echo Downloading stable version of Python ^(3.11.8^)...
    curl -# -o python_installer.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    if !errorlevel! neq 0 (
        echo Failed to download Python. Please check your internet connection.
        pause
        exit /b 1
    )
    
    echo Installing Python silently... This may take a few minutes.
    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    
    if !errorlevel! neq 0 (
        echo Python installation failed.
        pause
        exit /b 1
    )
    echo Python installation finished successfully.
    del python_installer.exe
    
    :: Add Python to current session PATH
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python311\;%LOCALAPPDATA%\Programs\Python\Python311\Scripts\;!PATH!"
)

:: Verify python is now accessible
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo Python could not be found even after installation.
    echo Please restart your computer or run this script again.
    pause
    exit /b 1
)

echo Installing required stable dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo.
    echo Error installing dependencies. Please check your internet connection or requirements.txt
    pause
    exit /b 1
)

echo.
echo Starting WITTGrp Download Manager...
python main.py
if !errorlevel! neq 0 (
    echo.
    echo Error starting WITTGrp. Press any key to exit.
    pause > nul
)
