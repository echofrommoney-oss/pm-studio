#!/usr/bin/env python3
"""把 PM 工作台裝進一個產品專案（每個專案各裝一套）。

  python3 install_pm_console.py --project /路徑/到/產品專案
  （Windows：py -3 install_pm_console.py --project D:\\專案\\產品A）

建議先在同一個專案裝好 edu-pm-workflow，再裝工作台。可重複執行，會覆蓋成最新版；
你的對話紀錄與設定（.pm-console/）不會被動到。
"""
import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["pm_console.py", "pm_console.html"]


def write(path, text, crlf=False, exe=False):
    data = text.replace("\n", "\r\n") if crlf else text
    path.write_bytes(data.encode("utf-8"))
    if exe:
        path.chmod(0o755)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="產品專案資料夾")
    args = ap.parse_args()
    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"找不到資料夾：{root}")

    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    for name in FILES:
        shutil.copy2(HERE / name, scripts / name)

    for name in ("開啟PM工作台.command", "開啟PM工作台.bat"):
        src = HERE / "launchers" / name
        text = src.read_text(encoding="utf-8")
        write(root / name, text, crlf=name.endswith(".bat"), exe=name.endswith(".command"))

    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if ".pm-console/" not in lines:
        lines.append(".pm-console/")
        gi.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"✅ PM 工作台已裝到 {root}")
    if not (root / ".agents/workflows").is_dir():
        print("⚠️  這個專案還沒裝 edu-pm-workflow，先執行它的 scripts/initialize.py --project 同一個資料夾。")
    print("啟動：macOS 雙擊「開啟PM工作台.command」，Windows 雙擊「開啟PM工作台.bat」。")


if __name__ == "__main__":
    sys.exit(main())
