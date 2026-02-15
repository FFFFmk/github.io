@echo off
chcp 65001 >nul 2>&1
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   競馬自動分析システム セットアップ
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Pythonの確認
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Pythonがインストールされていません。
    echo.
    echo 以下のURLからPythonをダウンロードしてインストールしてください:
    echo https://www.python.org/downloads/
    echo.
    echo ※ インストール時に「Add Python to PATH」にチェックを入れてください。
    echo.
    pause
    exit /b 1
)

echo [1/3] Pythonが見つかりました。
python --version
echo.

REM 必要なライブラリのインストール
echo [2/3] 必要なライブラリをインストールしています...
echo.
pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo [エラー] ライブラリのインストールに失敗しました。
    echo pip を最新版に更新してみてください:
    echo   python -m pip install --upgrade pip
    echo.
    pause
    exit /b 1
)
echo.
echo ライブラリのインストールが完了しました。
echo.

REM データベース初期化
echo [3/3] データベースを初期化しています...
python -c "import sys; sys.path.insert(0, '%~dp0'); from src.database import init_database; init_database()"
if %errorlevel% neq 0 (
    echo [エラー] データベースの初期化に失敗しました。
    pause
    exit /b 1
)
echo データベースの初期化が完了しました。
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   セットアップが完了しました！
echo.
echo   実行方法:
echo     run_analysis.bat をダブルクリック
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
pause
