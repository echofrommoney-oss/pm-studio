#!/usr/bin/env python3
"""一次把三層裝進一個產品專案：工作流 → 設計層 → 工作台。

  python3 install.py --project /路徑/產品A
  （Windows：py -3 install.py --project D:\\專案\\產品A）

一個產品專案裝一套。可重複執行更新；對話紀錄、PRODUCT.md、DESIGN.md、你改過的工作流檔都會保留。
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    ("工作流", HERE / "workflow/scripts/initialize.py"),
    ("設計層", HERE / "design-layer/install_design_layer.py"),
    ("工作台", HERE / "console/install_pm_console.py"),
]


def register(root):
    """登記到專案總覽清單（~/.pm-studio/projects.json）。"""
    import json, os, time
    home = Path(os.environ.get("PM_STUDIO_HOME") or (Path.home() / ".pm-studio"))
    path = home / "projects.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data.get("projects"), list)
    except Exception:
        data = {"projects": []}
    if str(root) not in [p.get("path") for p in data["projects"] if isinstance(p, dict)]:
        data["projects"].append({"path": str(root), "added": time.time()})
        home.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def setup_git(root):
    """專案不是 git 儲存庫就初始化；已經是就不動（包括它在別的儲存庫裡面）。
    文件只留最新版，歷史由 git 保存；每次工作完成 Claude 會以 pm_sync.py commit 提交。"""
    print("\n══ git ══")
    try:
        inside = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True).stdout.strip() == "true"
    except OSError:
        print("⚠️  找不到 git，略過。安裝 git 後重跑本安裝器即可（macOS：xcode-select --install；Windows：git-scm.com）。")
        return
    if inside:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True).stdout.strip()
        print(f"✅ 已在 git 儲存庫中（{top}），不重複初始化")
        return
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=False)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=False)
    r = subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "初始化 PM Studio 工作流"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print("✅ 已初始化 git 並完成第一次提交")
    else:
        print("✅ 已初始化 git；第一次提交沒有完成，多半是還沒設定作者：")
        print('     git config --global user.name "你的名字"')
        print('     git config --global user.email "你的信箱"')
        print("   設定好後在專案資料夾執行：git add -A && git commit -m \"初始化 PM Studio 工作流\"")
    print("   要推到 GitHub：git remote add origin <網址> && git push -u origin main（建議私人儲存庫）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--skip", nargs="*", default=[], choices=["工作流", "設計層", "工作台"])
    args = ap.parse_args()
    root = Path(args.project).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name, script in STEPS:
        if name in args.skip:
            continue
        print(f"\n══ {name} ══")
        code = subprocess.call([sys.executable, str(script), "--project", str(root)])
        if code != 0:
            raise SystemExit(f"{name} 安裝失敗（代碼 {code}），先解決上面的錯誤再重跑。")
    register(root)
    setup_git(root)
    print(f"\n全部裝好：{root}")
    print("下一步：雙擊專案裡的「開啟PM工作台」，先按「設計方向」定這個產品的 PRODUCT.md 與 DESIGN.md。")
    print("        所有專案的進度：雙擊本套件裡的「開啟專案總覽」。")


if __name__ == "__main__":
    sys.exit(main())
