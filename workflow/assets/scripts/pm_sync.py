#!/usr/bin/env python3
"""交付物同步狀態：判斷一個需求裡哪些文件落後於它的上游，並可觸發截圖重新匯出。

  python3 scripts/pm_sync.py status [需求名]        列出落後的文件（不帶需求名 = 全部需求）
  python3 scripts/pm_sync.py status [需求名] --json
  python3 scripts/pm_sync.py mark 需求名            變更完成後執行：記下「此刻全部一致」
  python3 scripts/pm_sync.py export 需求名          透過匯出服務重新截圖原型與流程圖
  python3 scripts/pm_sync.py commit 需求名 -m "訊息"  把這個需求與專案設計檔的變動提交到 git

判斷方式：
  · 有 mark 紀錄時：上游在 mark 之後改過、而下游沒改過 → 下游落後。順序無關，最準。
  · 沒有 mark 紀錄時：上游比下游新超過 90 秒 → 下游落後（粗略判斷）。
紀錄存在隱藏的 .pm-workflow/sync/，不是交付物。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

TOLERANCE = 90
STAGES = [
    # (代號, 顯示名稱, 子資料夾, 副檔名)
    ("demand", "需求挖掘", "需求挖掘", (".html", ".md")),
    ("prd", "PRD", "需求文件", (".html",)),
    ("proto", "原型", "原型", (".html",)),
    ("flow", "流程圖", "流程圖", (".html",)),
    ("proto_shots", "原型截圖", "原型截圖", (".png",)),
    ("flow_shots", "流程圖截圖", "流程圖截圖", (".png",)),
    ("validate", "原型驗證腳本", "原型驗證", (".md", ".html")),
    ("spec", "技術規格", "技術規格", (".md",)),
    ("accept", "驗收清單", "驗收清單", (".html",)),
    ("launch", "上線文件", "上線", (".md", ".html")),
]
# 下游 ← 上游
DEPENDS = {
    "proto": ["prd", "design"],
    "flow": ["prd"],
    "proto_shots": ["proto"],
    "flow_shots": ["flow"],
    "validate": ["prd", "proto"],
    "spec": ["prd", "arch"],
    "accept": ["prd"],
    "launch": ["prd", "design"],
}
LABEL = {code: label for code, label, _, _ in STAGES}
LABEL["design"] = "DESIGN.md"
LABEL["arch"] = "ARCHITECTURE.md"
SKIP_TOP = {"scripts", "node_modules", "assets", "templates"}
ARTIFACT_DIRS = {sub for _, _, sub, _ in STAGES}


def stage_files(req_dir, code):
    for c, _, sub, exts in STAGES:
        if c != code:
            continue
        folder = req_dir / sub
        if not folder.is_dir():
            return []
        files = [f for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in exts
                 and not f.name.startswith(".")]
        if code == "validate":  # 只有測試腳本會落後；驗證結果是當次產出
            files = [f for f in files if "腳本" in f.name]
        return files
    return []


def sync_path(root, req):
    return Path(root) / ".pm-workflow/sync" / (hashlib.sha1(req.encode()).hexdigest()[:16] + ".json")


def latest(files):
    return max((f.stat().st_mtime for f in files), default=None)


def requirements(root):
    root = Path(root)
    out = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and d.name not in SKIP_TOP \
                and any((d / s).is_dir() for s in ARTIFACT_DIRS | {"素材"}):
            out.append(d.name)
    return out


def status(root, req):
    """回傳 {'stages': {代號: {'label','files','mtime'}}, 'stale': [{'stage','label','behind':[...]}]}"""
    root = Path(root)
    req_dir = root / req
    design = root / "DESIGN.md"
    arch = root / "ARCHITECTURE.md"
    groups = {code: stage_files(req_dir, code) for code, *_ in STAGES}
    groups["design"] = [design] if design.is_file() else []
    groups["arch"] = [arch] if arch.is_file() else []
    mt = {code: latest(files) for code, files in groups.items()}

    mark = {}
    try:
        mark = json.loads(sync_path(root, req).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    marked = mark.get("mtimes", {})

    stale = []
    for down, ups in DEPENDS.items():
        if mt.get(down) is None:
            continue
        behind = []
        for up in ups:
            if mt.get(up) is None:
                continue
            if marked.get(up) is not None and marked.get(down) is not None:
                up_changed = mt[up] > marked[up] + 1
                down_changed = mt[down] > marked[down] + 1
                if up_changed and not down_changed:
                    behind.append(LABEL[up])
            elif mt[up] > mt[down] + TOLERANCE:
                behind.append(LABEL[up])
        if behind:
            stale.append({"stage": down, "label": LABEL[down], "behind": behind})

    stages = {code: {"label": LABEL[code], "files": len(groups[code]), "mtime": mt[code]}
              for code in groups if code not in ("design", "arch")}
    return {"req": req, "stages": stages, "stale": stale,
            "marked_at": mark.get("at"), "has_design": bool(groups["design"])}


MANIFEST_KEYS = ("tables", "functions", "rpc", "buckets", "app_screens", "web_admin", "web_partner", "web_site")


def read_manifest(root, req):
    """讀技術規格開頭的 manifest（單行中括號清單）。沒有 Spec 或沒有 manifest 回傳 None。"""
    folder = Path(root) / req / "技術規格"
    specs = sorted(folder.glob("*.md")) if folder.is_dir() else []
    if not specs:
        return None
    text = specs[0].read_text(encoding="utf-8", errors="replace").replace("\r", "")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    out = {}
    for line in text[3:end].splitlines():
        key, sep, value = line.strip().partition(":")
        if not sep or key not in MANIFEST_KEYS:
            continue
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            out[key] = [v for v in items if v]
    return {k: out.get(k, []) for k in MANIFEST_KEYS} if out else None


def mark(root, req):
    root = Path(root)
    req_dir = root / req
    mtimes = {code: latest(stage_files(req_dir, code)) for code, *_ in STAGES}
    for key, name in (("design", "DESIGN.md"), ("arch", "ARCHITECTURE.md")):
        f = root / name
        mtimes[key] = f.stat().st_mtime if f.is_file() else None
    path = sync_path(root, req)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"req": req, "at": time.time(),
                                "mtimes": {k: v for k, v in mtimes.items() if v is not None}},
                               ensure_ascii=False, indent=1), encoding="utf-8")


def export(root, req):
    root = Path(root)
    try:
        cfg = json.loads((root / ".pm-workflow/runtime.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("找不到 .pm-workflow/runtime.json，這個專案還沒裝工作流。")
        return 1
    base = f"http://127.0.0.1:{cfg['port']}"
    headers = {"Content-Type": "application/json", "X-PM-Token": cfg["token"],
               "X-PM-Project": cfg["project_id"], "Origin": base}

    def call(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req_ = Request(base + path, data=data, headers=headers, method="POST" if body is not None else "GET")
        with urlopen(req_, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        call("/api/health")
    except Exception:
        print("匯出服務沒在運作。請在工作台標題列按「啟動」，或雙擊「啟動原型匯出服務」後再執行一次。")
        return 1

    targets = sorted((root / req / "原型").glob("*.html")) + sorted((root / req / "流程圖").glob("*.html"))
    if not targets:
        print("這個需求沒有原型或流程圖 HTML，不需要匯出。")
        return 0
    failed = 0
    for html in targets:
        rel = html.relative_to(root).as_posix()
        try:
            job = call("/api/screenshot", {"path": rel, "viewport": {"width": 1440, "height": 900}})
        except Exception as e:
            print(f"✗ {rel}：{e}")
            failed += 1
            continue
        if not job.get("started"):
            print(f"✗ {rel}：{job.get('error')}")
            failed += 1
            continue
        deadline = time.time() + 300
        while time.time() < deadline:
            time.sleep(1.5)
            st = call("/api/status")
            if st.get("job_id") == job["job_id"] and st.get("done"):
                if st.get("error"):
                    print(f"✗ {rel}：{st['error']}")
                    failed += 1
                else:
                    print(f"✓ {rel}：{st.get('success_count', 0)} 張")
                break
        else:
            print(f"✗ {rel}：逾時")
            failed += 1
    return 1 if failed else 0


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def git_ready(root):
    try:
        return git(root, "rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    except OSError:
        return False


def uncommitted(root):
    """未提交的檔案數；不是 git 專案回傳 None。"""
    if not git_ready(root):
        return None
    out = git(root, "status", "--porcelain").stdout
    return len([l for l in out.splitlines() if l.strip()])


def commit(root, req, message):
    """只提交本需求資料夾、專案級文件（PRODUCT／DESIGN／ARCHITECTURE）與程式資料夾（supabase、app、web），不碰使用者其他檔案。"""
    root = Path(root)
    if not git_ready(root):
        print("這個專案還不是 git 儲存庫，略過提交（重新執行 install.py 會自動初始化）。")
        return 0
    # 存在的、或曾被追蹤過的（整個需求被刪除時也要記錄刪除）
    paths = [p for p in (req, "PRODUCT.md", "DESIGN.md", "ARCHITECTURE.md", "supabase", "app", "web")
             if p and ((root / p).exists() or git(root, "ls-files", "--", p).stdout.strip())]
    if not paths:
        print("沒有變動需要提交。")
        return 0
    r = git(root, "add", "-A", "--", *paths)
    if r.returncode != 0:
        print("git add 失敗：" + r.stderr.strip())
        return 1
    if not git(root, "diff", "--cached", "--name-only").stdout.strip():
        print("沒有變動需要提交。")
        return 0
    r = git(root, "commit", "-m", message)
    if r.returncode != 0:
        err = r.stderr.strip() or r.stdout.strip()
        if "user.email" in err or "user.name" in err or "identity" in err.lower():
            print("git 還沒設定作者，請在終端機執行：\n"
                  "  git config --global user.name \"你的名字\"\n"
                  "  git config --global user.email \"你的信箱\"")
        else:
            print("git commit 失敗：" + err)
        return 1
    print("已提交：" + git(root, "log", "-1", "--pretty=%h %s").stdout.strip())
    return 0


def main():
    ap = argparse.ArgumentParser(description="交付物同步狀態")
    ap.add_argument("action", choices=["status", "mark", "export", "commit"])
    ap.add_argument("req", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-m", "--message", default="")
    ap.add_argument("--root", default=os.environ.get("PROTOTYPE_PROJECT_DIR") or str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if args.action in ("mark", "export", "commit") and not args.req:
        ap.error("需要需求名")
    if args.action == "commit":
        return commit(root, args.req, args.message or f"[{args.req}] 更新")
    if args.action == "mark":
        mark(root, args.req)
        print(f"已記錄「{args.req}」目前全部一致。")
        return 0
    if args.action == "export":
        return export(root, args.req)

    reqs = [args.req] if args.req else requirements(root)
    results = [status(root, r) for r in reqs if (root / r).is_dir()]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0
    any_stale = False
    for r in results:
        if r["stale"]:
            any_stale = True
            print(f"「{r['req']}」")
            for s in r["stale"]:
                print(f"  ⚠ {s['label']} 落後於 {'、'.join(s['behind'])}")
    if not any_stale:
        print("全部一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
