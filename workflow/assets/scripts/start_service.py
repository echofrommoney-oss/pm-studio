#!/usr/bin/env python3
"""匯出服務的命令列入口——所有實際策略都在 pm_bootstrap 裡，這裡只做參數解析。

常用：
  --serve      啟動服務並佔用當前視窗（雙擊啟動腳本走的就是這條）
  --doctor     列印環境體檢結果，排查問題時先跑這個
  --check      只檢查依賴是否就緒，不啟動
  --install    顯式重灌共享執行環境（平時不需要，--serve 會自動準備）
"""
import argparse
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pm_bootstrap import doctor, ensure_runtime, ensure_serving  # noqa: E402
from pm_runtime import ensure_config  # noqa: E402

ROOT = Path(os.environ.get("PROTOTYPE_PROJECT_DIR")
            or Path(__file__).resolve().parent.parent).resolve()
HINT = "排查辦法：在專案目錄執行  python3 scripts/start_service.py --doctor" \
    if os.name != "nt" else \
    "排查辦法：在專案目錄執行  py -3 scripts\\start_service.py --doctor"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只檢查依賴")
    parser.add_argument("--install", action="store_true", help="強制重灌共享執行環境")
    parser.add_argument("--serve", action="store_true", help="啟動服務並佔用當前視窗")
    parser.add_argument("--doctor", action="store_true", help="列印環境體檢結果")
    parser.add_argument("--background", action="store_true", help="脫離終端機在後台啟動")
    parser.add_argument("--open-browser", action="store_true", help="啟動後開啟首個原型頁")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-download", action="store_true",
                        help="不允許下載 Chromium（沒有可沿用的系統瀏覽器時直接報錯）")
    args = parser.parse_args()

    if sys.version_info < (3, 9):
        raise SystemExit(f"需要 Python 3.9 或更高版本，當前是 {sys.version.split()[0]}")

    if args.doctor:
        return doctor(ROOT)

    if args.install:
        ensure_config(ROOT)
        ensure_runtime(allow_download=not args.no_download, force_install=True)
        print("✅ 共享執行環境已就緒")
        if not args.serve:
            return 0

    if args.check:
        ensure_config(ROOT)
        ensure_runtime(allow_download=not args.no_download)
        print("✅ 環境檢查通過：Python、playwright、瀏覽器引擎均可執行")
        return 0

    if not args.serve:
        parser.print_help()
        return 0

    result, config = ensure_serving(
        ROOT, background=args.background, read_only=args.read_only, host=args.host,
        open_browser=args.open_browser, allow_download=not args.no_download)
    if args.background and result == "launched":
        print(f"✅ 服務已在後台啟動：http://127.0.0.1:{config['port']}")
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as error:
        # 雙擊啟動的場景裡使用者看不到 traceback 之外的東西，所以先說人話，再給排查入口。
        print(f"\n❌ {error}\n", file=sys.stderr)
        if os.environ.get("PM_DEBUG"):
            traceback.print_exc()
        print(HINT, file=sys.stderr)
        sys.exit(1)
