#!/bin/bash
# 雙擊此檔案啟動原型匯出服務，然後保持這個視窗開著。
# 開啟任意 [需求名]/原型/*.html 或 [需求名]/流程圖/*.html，點匯出即可存 PNG。
#
# 所有實際邏輯都在 scripts/start_service.py 裡（Mac 和 Windows 共用同一套），
# 這裡只負責：切到專案目錄、找到可用的 python、出錯時別把視窗關掉。

cd "$(dirname "$0")" || exit 1

for PY in python3 python; do
  if command -v "$PY" >/dev/null 2>&1; then
    "$PY" scripts/start_service.py --serve
    STATUS=$?
    # 0 = 正常退出（使用者按了 ⌃C）。非 0 才需要停下來讓人看清提示。
    if [ $STATUS -ne 0 ]; then
      echo ""
      echo "按回車鍵關閉視窗。"
      read -r _
    fi
    exit $STATUS
  fi
done

echo "❌ 沒找到 python3。"
echo ""
echo "請安裝 Python 3.9 以上版本，二選一："
echo "  1. 開啟 https://www.python.org/downloads/ 下載安裝包"
echo "  2. 已裝 Homebrew 的話，在終端機執行：brew install python"
echo ""
echo "裝完後再雙擊本檔案。按回車鍵關閉視窗。"
read -r _
exit 1
