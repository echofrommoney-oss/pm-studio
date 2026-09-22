#!/usr/bin/env python3
"""把畫面截圖存成 PNG，讓 Claude 用「看」的方式檢查設計，而不是只讀程式碼。

  python3 scripts/pm_shot.py <網址或 HTML 路徑> <輸出.png> [--size mobile|tablet|desktop] [--full] [--wait 秒]

例：
  python3 scripts/pm_shot.py 課程收藏/原型/課程收藏-prototype.html .pm-console/shots/proto.png --size mobile --full
  python3 scripts/pm_shot.py http://127.0.0.1:23456/pets .pm-console/shots/admin-pets.png --size desktop

用的是匯出服務已經裝好的瀏覽器（Playwright）。Flutter 網頁版要等畫面畫完，預設多等 3 秒。
截完用 Read 工具打開 PNG 就能看到畫面。截圖放 .pm-console/shots/（不進 git）。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = {"mobile": (390, 844, 3), "tablet": (834, 1112, 2), "desktop": (1440, 900, 1)}

SNIPPET = r'''
import sys, time
from playwright.sync_api import sync_playwright
url, out, w, h, scale, full, wait = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6] == "1", float(sys.argv[7])
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=min(scale, 2))
    pg.goto(url, wait_until="networkidle", timeout=60000)
    time.sleep(wait)
    pg.screenshot(path=out, full_page=full)
    b.close()
'''


def python_with_playwright():
    """優先用匯出服務的虛擬環境（裡面已裝 Playwright 與瀏覽器）。"""
    for cand in (ROOT / "scripts/.venv/bin/python", ROOT / "scripts/.venv/Scripts/python.exe"):
        if cand.is_file():
            return str(cand)
    try:
        import playwright  # noqa: F401
        return sys.executable
    except ImportError:
        return None


def main():
    ap = argparse.ArgumentParser(description="截圖給 Claude 看")
    ap.add_argument("target", help="網址（http://…）或專案裡的 HTML 路徑")
    ap.add_argument("out", help="輸出 PNG 路徑")
    ap.add_argument("--size", choices=SIZES, default="mobile")
    ap.add_argument("--full", action="store_true", help="整頁截圖（含捲動區域）")
    ap.add_argument("--wait", type=float, default=None, help="載入後多等幾秒（Flutter 網頁版預設 3）")
    args = ap.parse_args()

    target = args.target
    if not target.startswith(("http://", "https://")):
        path = (ROOT / target).resolve()
        if not path.is_file():
            print(f"找不到檔案：{target}")
            return 1
        target = path.as_uri()
    elif not any(h in target for h in ("//127.0.0.1", "//localhost")):
        print("只截本機畫面（127.0.0.1／localhost）。")
        return 1
    py = python_with_playwright()
    if not py:
        print("找不到 Playwright。請先在工作台啟動一次匯出服務（它會自動安裝），再重試。")
        return 1
    out = (ROOT / args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    w, h, scale = SIZES[args.size]
    wait = args.wait if args.wait is not None else 3.0
    r = subprocess.run([py, "-c", SNIPPET, target, str(out), str(w), str(h), str(scale), "1" if args.full else "0", str(wait)],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        print("截圖失敗：" + (r.stderr.strip().splitlines() or ["未知錯誤"])[-1])
        return 1
    print(f"已存成 {out.relative_to(ROOT)}（{args.size} {w}×{h}）。用 Read 工具打開它來看畫面。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
