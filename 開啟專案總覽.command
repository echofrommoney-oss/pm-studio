#!/bin/bash
# PM 專案總覽（macOS）：雙擊開啟，保持這個視窗開著；關掉視窗就停止總覽。
cd "$(dirname "$0")" || exit 1
PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "找不到 python3。請先安裝 Python 3.9 以上：https://www.python.org/downloads/"
  read -n 1 -s -r -p "按任意鍵關閉"; exit 1
fi
"$PY" hub/pm_hub.py --open
echo
read -n 1 -s -r -p "總覽已停止，按任意鍵關閉視窗"
