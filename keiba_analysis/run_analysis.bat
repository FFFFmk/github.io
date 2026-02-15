@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
python -m src.main
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to run the program.
    echo Please run setup.bat first.
    echo.
    pause
)
