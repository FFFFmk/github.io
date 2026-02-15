@echo off
echo.
echo ==============================
echo   Keiba Analysis - Setup
echo ==============================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    echo.
    echo Please download Python from:
    echo   https://www.python.org/downloads/
    echo.
    echo * Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/3] Python found.
python --version
echo.

REM Install libraries
echo [2/3] Installing libraries...
echo.
pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install libraries.
    echo Try updating pip:
    echo   python -m pip install --upgrade pip
    echo.
    pause
    exit /b 1
)
echo.
echo Libraries installed successfully.
echo.

REM Initialize database
echo [3/3] Initializing database...
cd /d "%~dp0"
python -c "from src.database import init_database; init_database()"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to initialize database.
    pause
    exit /b 1
)
echo Database initialized.
echo.

echo ==============================
echo   Setup complete!
echo.
echo   Next: double-click
echo     run_analysis.bat
echo ==============================
echo.
pause
