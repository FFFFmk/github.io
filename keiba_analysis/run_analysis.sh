#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
python3 -m src.main
if [ $? -ne 0 ]; then
    echo ""
    echo "[エラー] プログラムの実行に失敗しました。"
    echo "まずは ./setup.sh を実行してセットアップを完了してください。"
    echo ""
fi
