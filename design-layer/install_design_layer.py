#!/usr/bin/env python3
"""把設計層裝進一個產品專案：.claude/skills/ 下放六組上游 skill，.claude/agents/ 放 impeccable 子代理。

  python3 install_design_layer.py --project /路徑/產品A
  （Windows：py -3 install_design_layer.py --project D:\\專案\\產品A）

可重複執行（覆蓋成本套件版本）；專案自己的 PRODUCT.md / DESIGN.md 不會被動到。
上游 skill 保持原文（英文），接線說明在 .agents/workflows/pm-design.md（繁體中文）。
"""
import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = ["impeccable", "hallmark", "pencilplaybook", "ui-ux-pro-max",
          "gsap-core", "gsap-timeline", "gsap-scrolltrigger", "gsap-performance",
          "gsap-plugins", "gsap-utils", "gsap-react", "gsap-frameworks"]


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--no-gsap-frameworks", action="store_true",
                    help="不裝 gsap-react / gsap-frameworks（原型是純 HTML 時用不到）")
    args = ap.parse_args()
    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"找不到資料夾：{root}")

    skills_dir = root / ".claude/skills"
    agents_dir = root / ".claude/agents"
    skills_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    wanted = [s for s in SKILLS if not (args.no_gsap_frameworks and s in ("gsap-react", "gsap-frameworks"))]
    for name in wanted:
        src = HERE / "skills" / name
        if not src.is_dir():
            print(f"⚠️  套件缺少 {name}，略過")
            continue
        copy_tree(src, skills_dir / name)
        launcher = skills_dir / name / "scripts" / "impeccable"
        if launcher.is_file():
            launcher.chmod(0o755)
        print(f"✅ {name}")

    for agent in sorted((HERE / "agents").glob("*.md")):
        shutil.copy2(agent, agents_dir / agent.name)
    print(f"✅ impeccable 子代理 ×{len(list((HERE / 'agents').glob('*.md')))}")

    (root / "設計層說明.md").write_text((HERE / "設計層說明.md").read_text(encoding="utf-8"), encoding="utf-8")

    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    for entry in (".impeccable/", "*.pen.lock"):
        if entry not in lines:
            lines.append(entry)
    gi.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n設計層已裝到 {root}")
    print("  · Chrome 擴充功能（design-md-chrome）要手動載入，步驟在「設計層說明.md」")
    print("  · impeccable 第一次執行 context/detect 時會下載它的引擎二進位檔，需要網路")
    print("  · 接下來在工作台或 Claude Code 說「設計方向」，建立這個產品的 PRODUCT.md 與 DESIGN.md")


if __name__ == "__main__":
    sys.exit(main())
