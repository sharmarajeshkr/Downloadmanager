@echo off
echo ============================================
echo   WITTGrp Download Manager v1.0
echo ============================================
cd /d d:\idm
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Error starting WITTGrp. Press any key to exit.
    pause > nul
)
