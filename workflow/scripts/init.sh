#!/bin/bash
# 把 PM Workflow 安裝進當前目錄（macOS / Linux）。
#
#   在專案目錄裡執行：bash /路徑/到/studio-pm-workflow/scripts/init.sh
#
# 這裡只做兩件事：找到一個能用的 python、把活交給 initialize.py。
# 所有安裝邏輯都在 initialize.py 裡，Windows 的 init.bat 走的是同一份程式碼——
# 兩套並行的安裝腳本一定會各自腐爛，這是上一版踩過的坑。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 用「列印出哨兵」判定直譯器可用，不看退出碼：macOS 12.3 起系統不自帶 python3，
# /usr/bin/python3 是 Command Line Tools 的墊片，會彈 GUI 安裝框。
for PY in python3 python; do
  if command -v "$PY" >/dev/null 2>&1 &&
     [ "$("$PY" -c 'print("PMPYOK")' 2>/dev/null)" = "PMPYOK" ]; then
    exec "$PY" "${SCRIPT_DIR}/initialize.py" --project "$(pwd)"
  fi
done

echo "❌ 沒找到可用的 Python 3.9+。" >&2
echo "" >&2
echo "請二選一安裝後重試：" >&2
echo "  1. 開啟 https://www.python.org/downloads/ 下載安裝包" >&2
echo "  2. 已裝 Homebrew 的話，執行：brew install python" >&2
exit 1
