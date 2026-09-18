#!/bin/bash
# 「點匯出自動起服務」的按需啟動器（僅 macOS）。
#
# 裝了它之後，點原型頁的匯出按鈕或 PRD 的「一鍵複製全文」時服務會自動起來，
# 不用先雙擊啟動腳本。
#
# 它**不是**常駐程序：連接埠由 launchd 持有，空閒時本專案沒有任何程序在跑，
# 瀏覽器一連上來才拉起，起完服務就自退。所以 init 時預設就會裝上。
#
#   安裝/重新註冊：bash scripts/install_launcher.sh
#   解除安裝：        bash scripts/install_launcher.sh --uninstall
#   看狀態：      python3 scripts/start_service.py --doctor
#
# 真正寫 plist 的邏輯在 scripts/pm_launchagent.py（唯一來源），這裡只是個殼，
# 方便不想記 Python 命令的人直接跑。
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

if [ "$(uname -s)" != "Darwin" ]; then
  echo "按需啟動器只支援 macOS。"
  echo "Windows 上不需要它：服務本體就是你雙擊「啟動原型匯出服務.bat」後開著的那個視窗。"
  exit 0
fi

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
done
if [ -z "$PY" ]; then
  echo "❌ 沒找到 python3，請先安裝 Python 3.9+（https://www.python.org/downloads/）"
  exit 1
fi

"$PY" - "$PWD" "${1:-}" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
action = sys.argv[2] if len(sys.argv) > 2 else ""

sys.path.insert(0, str(root / "scripts"))
try:
    import pm_launchagent
    from pm_runtime import ensure_config
except ImportError as error:
    sys.exit(f"❌ 這個目錄還沒安裝 PM Workflow（{error}）。請先在專案目錄跑一次 init。")

config = ensure_config(root)

if action in ("--uninstall", "-u", "uninstall"):
    ok, detail = pm_launchagent.uninstall(config)
    if not ok:
        sys.exit(f"❌ 解除安裝失敗：{detail}")
    print(f"✅ 已解除安裝本專案的按需啟動器（{detail}）")
    print("   匯出功能不受影響：雙擊「啟動原型匯出服務.command」照樣能用。")
    sys.exit(0)

ok, detail = pm_launchagent.install(root, config)
if not ok:
    sys.exit(f"❌ 註冊失敗：{detail}")
print(f"✅ 已為本專案註冊按需啟動器：{detail}")
print("   空閒時不佔程序；點匯出時由 launchd 拉起，起完服務自退。")
print("   解除安裝：bash scripts/install_launcher.sh --uninstall")
PY
