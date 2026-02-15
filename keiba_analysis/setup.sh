#!/bin/bash
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  競馬自動分析システム セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Pythonの確認
if ! command -v python3 &> /dev/null; then
    echo "[エラー] Python3がインストールされていません。"
    echo ""
    echo "以下のコマンドでインストールしてください:"
    echo ""
    echo "  macOS:  brew install python3"
    echo "  Ubuntu: sudo apt install python3 python3-pip"
    echo ""
    exit 1
fi

echo "[1/3] Pythonが見つかりました。"
python3 --version
echo ""

# 必要なライブラリのインストール
echo "[2/3] 必要なライブラリをインストールしています..."
echo ""
pip3 install -r "$SCRIPT_DIR/requirements.txt"
if [ $? -ne 0 ]; then
    echo ""
    echo "[エラー] ライブラリのインストールに失敗しました。"
    echo "pip を最新版に更新してみてください:"
    echo "  python3 -m pip install --upgrade pip"
    echo ""
    exit 1
fi
echo ""
echo "ライブラリのインストールが完了しました。"
echo ""

# データベース初期化
echo "[3/3] データベースを初期化しています..."
cd "$SCRIPT_DIR"
python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from src.database import init_database; init_database()"
if [ $? -ne 0 ]; then
    echo "[エラー] データベースの初期化に失敗しました。"
    exit 1
fi
echo "データベースの初期化が完了しました。"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  セットアップが完了しました！"
echo ""
echo "  実行方法:"
echo "    ./run_analysis.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
