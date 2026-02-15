@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
python -m src.main
if %errorlevel% neq 0 (
    echo.
    echo [エラー] プログラムの実行に失敗しました。
    echo まずは setup.bat を実行してセットアップを完了してください。
    echo.
    pause
)
