#!/usr/bin/env python3
"""PM 工作台：每個產品專案一套的本機前台。

在瀏覽器裡對話、下指令，後端以無頭模式呼叫 Claude Code（`claude -p`），
在「這個專案資料夾」裡執行 studio-pm-workflow 的工作流，產出即時預覽。

  python3 scripts/pm_console.py --open      啟動並開啟瀏覽器
  python3 scripts/pm_console.py --check     只檢查環境

只綁 127.0.0.1；所有寫入類請求都要帶頁面內的 token，且必須來自本頁。
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import urlopen

VERSION = "1.1.0"
SCRIPTS = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("PM_CONSOLE_ROOT") or SCRIPTS.parent).resolve()
DATA = ROOT / ".pm-console"
UI_FILE = SCRIPTS / "pm_console.html"
sys.path.insert(0, str(SCRIPTS))
import pm_dev  # noqa: E402  與工作台同在 scripts/
import pm_app  # noqa: E402
import pm_services  # noqa: E402
import pm_qa  # noqa: E402
pm_dev.init(ROOT, DATA)
pm_qa.init(ROOT, DATA)
pm_app.init(ROOT, DATA)
pm_services.init(ROOT, DATA)

# 產物子資料夾名稱，須與 studio-pm-workflow匯出服務的 WRITABLE_SUBDIR_NAMES 一致。
ARTIFACT_DIRS = ["需求挖掘", "需求文件", "原型", "流程圖", "原型驗證", "技術規格", "驗收清單", "資料分析", "上線",
                 "原型截圖", "流程圖截圖"]
# 匯出服務能直接提供（並支援其存檔與截圖功能）的子資料夾
EXPORT_SERVED = {"需求文件", "原型", "流程圖", "需求挖掘", "驗收清單", "資料分析", "原型驗證", "技術規格", "上線"}
PREVIEW_EXT = {".html", ".md", ".png", ".jpg", ".jpeg", ".svg", ".webp"}
STATIC_EXT = PREVIEW_EXT | {".css", ".js", ".gif", ".woff", ".woff2", ".json"}
SKIP_TOP = {"scripts", "node_modules", "assets", "templates"}
BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

DEFAULT_CONFIG = {
    "project_name": "",
    "claude_command": "claude",
    "model": "",
    "permission_mode": "acceptEdits",
    "allowed_tools": [
        "Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "TodoWrite",
        "Bash(python3:*)", "Bash(python:*)", "Bash(py:*)",
        "Bash(ls:*)", "Bash(mkdir:*)", "Bash(cp:*)", "Bash(mv:*)",
        "Bash(sh:*)", "Bash(npx impeccable:*)", "Bash(.claude/skills/impeccable/scripts/impeccable:*)",
        "Bash(*/.claude/skills/impeccable/scripts/impeccable:*)", "Bash(grep:*)", "Bash(rm:*)",
        "Bash(git status:*)", "Bash(git log:*)", "Bash(git show:*)", "Bash(git diff:*)",
        "Task", "WebSearch", "WebFetch",
        "Bash(supabase status:*)", "Bash(supabase migration:*)", "Bash(supabase functions new:*)",
        "Bash(supabase gen types:*)", "Bash(supabase db lint:*)", "Bash(supabase db diff:*)",
        "Bash(supabase test db:*)", "Bash(supabase init:*)", "Bash(deno:*)",
        "Bash(flutter create:*)", "Bash(flutter pub:*)", "Bash(flutter analyze:*)", "Bash(flutter test:*)",
        "Bash(flutter gen-l10n:*)", "Bash(flutter --version:*)", "Bash(flutter doctor:*)", "Bash(flutter devices:*)",
        "Bash(dart format:*)", "Bash(dart fix:*)", "Bash(dart analyze:*)", "Bash(dart run build_runner:*)",
    ],
    "use_subscription": True,
    # 工作台找不到某個工具時，把它所在的資料夾加在這裡，例如 ["~/development/flutter/bin"]
    "extra_path": [],
    "auto_start_export_service": True,
    "language_rule": "文件正文、原型介面文案與給使用者的回覆一律使用繁體中文（台灣用語）。",
    "workflows": [
        {"id": "prd", "group": "產品", "label": "PRD＋原型", "file": ".agents/workflows/pm-prd.md"},
        {"id": "demand", "group": "產品", "label": "需求挖掘", "file": ".agents/workflows/pm-demand.md"},
        {"id": "data", "group": "產品", "label": "資料分析", "file": ".agents/workflows/pm-data-analysis.md"},
        {"id": "launch", "group": "產品", "label": "上線包", "file": ".agents/workflows/pm-launch.md"},
        {"id": "design", "group": "設計", "label": "設計方向", "file": ".agents/workflows/pm-design.md",
         "instruction": "走流程 A：檢查並建立或修改 PRODUCT.md 與 DESIGN.md。使用者若貼了網址或截圖，用 hallmark study。"},
        {"id": "review", "group": "設計", "label": "檢查原型", "file": ".agents/workflows/pm-design.md",
         "instruction": "走流程 C：對本需求的原型 HTML 先 hallmark audit，違反 DESIGN.md 的直接修並再 audit；使用者要求時再 impeccable critique 或分項命令。"},
        {"id": "validate", "group": "設計", "label": "原型驗證", "file": ".agents/workflows/pm-validate.md"},
        {"id": "motion", "group": "設計", "label": "加動效", "file": ".agents/workflows/pm-design.md",
         "instruction": "走流程 B 第 5 步：用 gsap-* skill 為本需求原型加動效，強度依 DESIGN.md，尊重 prefers-reduced-motion。"},
        {"id": "hifi", "group": "設計", "label": "高保真", "file": ".agents/workflows/pm-design.md",
         "instruction": "走流程 D：pencilplaybook + Pencil，token 從 DESIGN.md 取值；Pencil 未安裝則說明並停止。"},
        {"id": "sysdesign", "group": "系統", "label": "系統設計", "file": ".agents/workflows/pm-sysdesign.md"},
        {"id": "spec", "group": "系統", "label": "技術規格", "file": ".agents/workflows/pm-spec.md"},
        {"id": "backend", "group": "開發", "label": "後端", "file": ".agents/workflows/pm-backend.md"},
        {"id": "app", "group": "開發", "label": "APP", "file": ".agents/workflows/pm-app.md"},
        {"id": "frontend", "group": "開發", "label": "前端", "file": ".agents/workflows/pm-frontend.md"},
        {"id": "qa", "group": "QA", "label": "自動測試", "file": ".agents/workflows/pm-qa.md"},
        {"id": "debug", "group": "QA", "label": "除錯", "file": ".agents/workflows/pm-debug.md"},
        {"id": "acceptance", "group": "QA", "label": "驗收清單", "file": ".agents/workflows/pm-acceptance.md"},
        {"id": "change", "group": "調整", "label": "變更", "file": ".agents/workflows/pm-change.md"},
        {"id": "free", "group": "調整", "label": "自由指令", "file": ""},
    ],
    # 這兩組的每一輪執行前會自動 git 快照，執行後可「退回這一輪」
    "snapshot_groups": ["系統", "開發", "QA"],
    "denied_tools": [
        "Bash(supabase link:*)", "Bash(supabase db push:*)", "Bash(supabase functions deploy:*)",
        "Bash(supabase secrets set:*)", "Bash(supabase projects:*)", "Bash(supabase login:*)",
        "Bash(git push:*)", "Bash(git reset:*)", "Bash(git checkout:*)", "Bash(git clean:*)",
        "Bash(flutter run:*)", "Bash(flutter emulators --launch:*)",
    ],
}


# ───────────────────────── 基礎工具 ─────────────────────────

def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + "." + uuid.uuid4().hex[:6])
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_config():
    path = DATA / "config.json"
    cfg = read_json(path, None)
    if not isinstance(cfg, dict):
        cfg = {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    changed = cfg.keys() != merged.keys()
    # 舊版設定遷移：edu-pm-*.md → pm-*.md；補上設計層按鈕
    wfs = merged.get("workflows") or []
    for w in wfs:
        if isinstance(w, dict) and str(w.get("file", "")).startswith(".agents/workflows/edu-pm-"):
            w["file"] = w["file"].replace("/edu-pm-", "/pm-"); changed = True
    defaults = {w["id"]: w for w in DEFAULT_CONFIG["workflows"]}
    by_id = {w.get("id"): w for w in wfs if isinstance(w, dict)}
    ordered = []
    for wid, dw in defaults.items():
        w = by_id.pop(wid, None)
        if w is None:
            w = dict(dw); changed = True
        if w.get("group") != dw["group"]:
            w["group"] = dw["group"]; changed = True
        ordered.append(w)
    for w in by_id.values():  # 使用者自訂的按鈕
        if isinstance(w, dict):
            w.setdefault("group", "自訂"); ordered.append(w)
    if [w.get("id") for w in ordered] != [w.get("id") for w in wfs if isinstance(w, dict)]:
        changed = True
    merged["workflows"] = ordered
    tools = merged.get("allowed_tools") or []
    for t in DEFAULT_CONFIG["allowed_tools"]:
        if t not in tools:
            tools.append(t); changed = True
    merged["allowed_tools"] = tools
    denied = merged.get("denied_tools") or []
    for t in DEFAULT_CONFIG["denied_tools"]:
        if t not in denied:
            denied.append(t); changed = True
    merged["denied_tools"] = denied
    if changed:
        atomic_write(path, json.dumps(merged, ensure_ascii=False, indent=2))
    return merged


def project_id():
    runtime = read_json(ROOT / ".pm-workflow/runtime.json", {})
    return runtime.get("project_id") or hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]


def export_service_port():
    return read_json(ROOT / ".pm-workflow/runtime.json", {}).get("port")


def derive_console_port(pid, salt=0):
    seed = hashlib.sha256(f"{pid}:console:{salt}".encode()).digest()
    return 20000 + int.from_bytes(seed[:4], "big") % 12767


def project_color(pid):
    hue = int(hashlib.sha256(f"{pid}:hue".encode()).hexdigest()[:4], 16) % 360
    return hue


def is_under(path, base):
    try:
        Path(path).resolve().relative_to(Path(base).resolve())
        return True
    except ValueError:
        return False


def valid_req_name(name):
    name = (name or "").strip()
    if not name or len(name) > 60 or name.startswith(".") or BAD_NAME.search(name):
        return None
    if name in SKIP_TOP or name in ARTIFACT_DIRS or name == "素材":
        return None
    return name


def chat_file(req):
    return DATA / "chats" / (hashlib.sha1(req.encode()).hexdigest()[:16] + ".json")


def find_claude(cfg):
    cmd = cfg.get("claude_command") or "claude"
    found = shutil.which(cmd)
    if found:
        return found
    home = Path.home()
    for cand in (home / ".local/bin/claude", home / ".claude/local/claude",
                 home / "AppData/Roaming/npm/claude.cmd", home / ".local/bin/claude.exe"):
        if cand.is_file():
            return str(cand)
    return None


# ───────────────────────── 需求與產物 ─────────────────────────

def sync_status(req):
    try:
        sys.path.insert(0, str(SCRIPTS))
        import pm_sync  # noqa: E402  與工作台同在 scripts/
        return pm_sync.status(ROOT, req)
    except Exception:
        return {"stale": []}


def list_requirements():
    sessions = read_json(DATA / "sessions.json", {})
    created = set(read_json(DATA / "requirements.json", []))
    out = []
    for d in ROOT.iterdir():
        if not d.is_dir() or d.name.startswith(".") or d.name in SKIP_TOP:
            continue
        subs = [s for s in ARTIFACT_DIRS if (d / s).is_dir()]
        has_inputs = (d / "素材").is_dir()
        if not subs and d.name not in created and d.name not in sessions \
                and not has_inputs:
            continue
        latest = d.stat().st_mtime
        count = 0
        for s in subs:
            for f in (d / s).rglob("*"):
                if f.is_file() and f.suffix.lower() in PREVIEW_EXT:
                    count += 1
                    latest = max(latest, f.stat().st_mtime)
        out.append({"name": d.name, "updated": latest, "count": count,
                    "stale": len(sync_status(d.name).get("stale", []))})
    out.sort(key=lambda r: r["updated"], reverse=True)
    return out


def list_artifacts(req):
    base = ROOT / req
    items = []
    for sub in ARTIFACT_DIRS:
        folder = base / sub
        if not folder.is_dir():
            continue
        for f in sorted(folder.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in PREVIEW_EXT or f.name.startswith("."):
                continue
            items.append({
                "group": sub,
                "name": str(f.relative_to(folder)).replace("\\", "/"),
                "rel": f.relative_to(ROOT).as_posix(),
                "kind": f.suffix.lower().lstrip("."),
                "mtime": f.stat().st_mtime,
            })
    for name in ("DESIGN.md", "PRODUCT.md"):
        f = ROOT / name
        if f.is_file():
            items.append({"group": "設計", "name": name, "rel": name, "kind": "md", "mtime": f.stat().st_mtime})
    return items


# ───────────────────────── 匯出服務 ─────────────────────────

def export_service_alive():
    port = export_service_port()
    if not port:
        return False
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.8) as resp:
            return resp.status == 200
    except Exception:
        return False


_export_starting = threading.Event()


def start_export_service():
    starter = SCRIPTS / "start_service.py"
    if not starter.is_file() or _export_starting.is_set():
        return False
    _export_starting.set()
    DATA.mkdir(parents=True, exist_ok=True)
    log = open(DATA / "export-service.log", "ab")
    kwargs = {"cwd": str(ROOT), "stdout": log, "stderr": log, "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen([sys.executable, str(starter), "--serve", "--background"], **kwargs)
    except OSError:
        _export_starting.clear()
        return False

    def _watch():
        try:
            proc.wait(timeout=240)
        except subprocess.TimeoutExpired:
            pass
        _export_starting.clear()
    threading.Thread(target=_watch, daemon=True).start()
    return True


# ───────────────────────── Claude 執行 ─────────────────────────

class Run:
    def __init__(self, req, workflow):
        self.id = uuid.uuid4().hex[:12]
        self.req = req
        self.workflow = workflow
        self.proc = None
        self.events = []
        self.done = False
        self.stopped = False
        self.cond = threading.Condition()
        self.started = time.time()

    def emit(self, event):
        with self.cond:
            event["i"] = len(self.events)
            self.events.append(event)
            self.cond.notify_all()


RUN_LOCK = threading.Lock()
CURRENT = {"run": None}


def tool_summary(name, inp):
    inp = inp or {}
    path = inp.get("file_path") or inp.get("path") or inp.get("notebook_path")
    if path:
        try:
            path = Path(path).resolve().relative_to(ROOT).as_posix()
        except (ValueError, OSError):
            pass
        return path
    if inp.get("command"):
        return str(inp["command"])[:160]
    if inp.get("pattern"):
        return str(inp["pattern"])[:120]
    if inp.get("todos"):
        return f"{len(inp['todos'])} 項待辦"
    return ""


def compose_prompt(cfg, req, workflow, message, first_turn):
    lines = [
        "［PM 工作台背景說明］",
        f"- 你在產品專案「{cfg.get('project_name') or ROOT.name}」的根目錄，以無頭模式執行；使用者透過網頁對話框和你溝通。",
        f"- 目前的需求名稱是「{req}」。所有產出放在專案根目錄的「{req}/」資料夾中，"
        "子資料夾名稱依工作流規定（需求挖掘、需求文件、原型、流程圖、原型驗證、技術規格、驗收清單、資料分析、上線），不可自行更改。",
        f"- {cfg.get('language_rule', '')}",
        "- 你無法在執行中等待回答。需要使用者確認時，把問題整理成編號清單作為本輪最後的回覆並結束，使用者會在下一則訊息回答。",
        "- 不要啟動常駐服務，也不要執行 install_launcher.sh；截圖匯出由使用者在預覽中操作。",
        "- 需要跑超過一行的 Python 時，先用 Write 寫成 .pm-console/tmp/ 底下的 .py 檔再用 python3 執行，不要用 python3 -c \"多行程式\"：無頭模式下 Claude Code 的內建安全檢查會把含換行與 # 的引號指令擋掉，而且無法用 allowed_tools 放行。指令也不要用 cd 開頭，你已經在專案根目錄。",
        "- 畫任何原型前先讀專案根目錄 DESIGN.md；沒有就先走 pm-design.md 流程 A2。設計工具分工見 .agents/workflows/pm-design.md，同一件事不要跑兩套。",
        "- 交付物只留最新版：不寫版本記錄或修改紀錄、不留刪除線與「已修改」標記、不另存舊檔。任何調整都把受影響的文件一起改到一致（規則見 .agents/workflows/pm-change.md）。",
        f"- 使用者提供的原始材料（訪談逐字稿、客戶檔案、測試筆記）放在「{req}/素材/」；續接所需的現況寫在隱藏檔 .pm-workflow/context/{req}.md（覆寫，不累積）。",
        "- 本輪寫了檔案就在結束前執行 python3 scripts/pm_sync.py status 需求名；沒有落後項才執行 mark，有落後項就在回覆中說明。",
        "- 接著一律執行 python3 scripts/pm_sync.py commit 需求名 -m \"[需求名] 動作：改了什麼（為什麼）\"。修改的理由寫在 commit 訊息，不寫進文件；不要 push，不要改 git 設定。使用者問起過去的修改，用 git log / git show 查。",
        "- 本輪結束時，用兩三句話說明做了什麼、產出了哪些檔案。",
    ]
    if workflow.get("file"):
        lines.append(f"- 本輪工作流：{workflow['label']}。請依照 `{workflow['file']}` 的規範執行"
                     + ("（開始前先完整閱讀它）。" if first_turn else "（若本對話已讀過可不必重讀）。"))
    if workflow.get("group") in ("開發", "系統"):
        try:
            st = pm_services.state(project_id())
        except Exception:
            st = {"services": [], "declared": False}
        if not st["declared"]:
            lines.append("- 技術選型：ARCHITECTURE.md 還沒有 stack／services 設定。開發前必須先走 pm-sysdesign.md 和使用者討論選型，不可自行假設技術。")
        parts = []
        for svc in st["services"]:
            if svc["adapter"] == "supabase":
                sb = pm_dev.public_status() if (ROOT / "supabase/config.toml").is_file() else {"running": False}
                parts.append(f"{svc['label']}（Supabase，{'執行中，API ' + str(sb.get('api')) if sb.get('running') else '未啟動'}）")
            elif svc["adapter"] == "flutter":
                live = [r["label"] for r in pm_app.state()["runs"].values() if r["state"] in ("starting", "running")]
                parts.append(f"{svc['label']}（Flutter，{'執行中：' + '、'.join(live) if live else '未啟動'}）")
            else:
                run = svc.get("run") or {}
                parts.append(f"{svc['label']}（{svc['adapter']}，{svc['dir'] or '根目錄'}，{'執行中 ' + svc['url'] if run.get('state') == 'running' else '未啟動'}）")
        if parts:
            lines.append("- 開發服務：" + "；".join(parts) + "。")
        lines.append("- 開發伺服器、模擬器、本機後端一律由工作台啟動與停止，你不要自己執行它們；需要時請使用者在右欄按啟動。"
                     "只准操作本機，禁止連到任何遠端或正式環境。本輪開始前工作台已做 git 快照，使用者可以一鍵退回。")
    if workflow.get("instruction"):
        lines.append(f"- 補充指示：{workflow['instruction']}")
    lines += ["", "［使用者訊息］", message.strip()]
    return "\n".join(lines)


def _svc_rules():
    try:
        return pm_services.permission_rules(project_id())
    except Exception:
        return [], []


def build_command(cfg, exe, session_id):
    settings = DATA / "claude-settings.json"
    atomic_write(settings, json.dumps({
        "disableAllHooks": bool(cfg.get("disable_hooks", True)),
        "permissions": {"allow": sorted(set((cfg.get("allowed_tools") or []) + _svc_rules()[0])),
                        "deny": sorted(set((cfg.get("denied_tools") or []) + _svc_rules()[1])),
                        "defaultMode": cfg.get("permission_mode") or "acceptEdits"}
    }, ensure_ascii=False, indent=2))
    cmd = [exe, "-p", "--output-format", "stream-json", "--verbose",
           "--permission-mode", cfg.get("permission_mode") or "acceptEdits",
           "--settings", ".pm-console/claude-settings.json"]
    if cfg.get("model"):
        cmd += ["--model", cfg["model"]]
    if session_id:
        cmd += ["--resume", session_id]
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c"] + cmd
    return cmd


def append_chat(req, entry):
    path = chat_file(req)
    log = read_json(path, {"req": req, "messages": []})
    log["messages"].append(entry)
    atomic_write(path, json.dumps(log, ensure_ascii=False, indent=1))


def set_session(req, session_id):
    path = DATA / "sessions.json"
    sessions = read_json(path, {})
    if session_id:
        sessions[req] = session_id
    else:
        sessions.pop(req, None)
    atomic_write(path, json.dumps(sessions, ensure_ascii=False, indent=2))


def kill_tree(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            proc.kill()
        except OSError:
            pass


def git(*args, timeout=60):
    try:
        r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def git_snapshot(label):
    """開發類工作前：工作區有未提交的變動就先提交一次，記下起點。回傳起點 commit 或 None。"""
    if git("rev-parse", "--is-inside-work-tree")[1] != "true":
        return None
    if git("status", "--porcelain")[1]:
        git("add", "-A")
        code, _, err = git("commit", "-q", "-m", f"工作台自動快照（{label}前）")
        if code != 0:
            return None  # 多半是 git 還沒設定作者；不快照就不提供退回
    code, head, _ = git("rev-parse", "HEAD")
    return head if code == 0 else None


def revert_last(req):
    cur = CURRENT["run"]
    if cur and not cur.done:
        raise RuntimeError("還有工作在執行，等它結束再退回。")
    path = chat_file(req)
    log = read_json(path, {"req": req, "messages": []})
    msgs = log["messages"]
    if not msgs or msgs[-1].get("role") != "assistant" or not msgs[-1].get("base") or msgs[-1].get("reverted"):
        raise RuntimeError("只能退回這個需求最近一輪的開發，而且那一輪之後沒有其他對話。")
    base = msgs[-1]["base"]
    _, head, _ = git("rev-parse", "HEAD")
    _, changed, _ = git("diff", "--name-only", base)
    commits = git("rev-list", f"{base}..HEAD")[1].split()
    if commits:
        code, _, err = git("revert", "--no-edit", f"{base}..HEAD", timeout=120)
        if code != 0:
            git("revert", "--abort")
            raise RuntimeError("自動退回失敗（和之後的修改衝突），沒有變動任何檔案：" + err[:300])
    git("checkout", "--", ".")
    git("clean", "-fdq")
    touched_db = any(f.startswith("supabase/migrations/") or f == "supabase/seed.sql" for f in changed.splitlines())
    msgs[-1]["reverted"] = True
    note = f"已退回上一輪（{len(commits)} 個提交以還原提交抵銷，git 歷史保留）。"
    if touched_db:
        note += "這一輪改過資料庫遷移或示範資料：到「後端」分頁按「重置測試資料」，本機資料庫才會回到退回後的狀態。"
    msgs.append({"role": "divider", "text": note, "time": time.time()})
    atomic_write(path, json.dumps(log, ensure_ascii=False, indent=1))
    return {"ok": True, "note": note, "touched_db": touched_db}


def start_run(cfg, req, workflow, message):
    exe = find_claude(cfg)
    if not exe:
        raise RuntimeError("找不到 claude 指令。請確認已安裝 Claude Code，並能在終端機執行 claude。")
    sessions = read_json(DATA / "sessions.json", {})
    session_id = sessions.get(req)
    prompt = compose_prompt(cfg, req, workflow, message, first_turn=not session_id)

    run = Run(req, workflow)
    run.base = git_snapshot(workflow["label"]) if workflow.get("group") in (cfg.get("snapshot_groups") or []) else None
    append_chat(req, {"role": "user", "text": message.strip(), "workflow": workflow["label"],
                      "time": time.time()})

    env = dict(os.environ)
    env["PM_CONSOLE"] = "1"
    if cfg.get("use_subscription", True):
        env.pop("ANTHROPIC_API_KEY", None)  # 避免改走 API 計費
    kwargs = {"cwd": str(ROOT), "env": env, "stdin": subprocess.PIPE,
              "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000200 | 0x08000000  # NEW_PROCESS_GROUP | NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    run.proc = subprocess.Popen(build_command(cfg, exe, session_id), **kwargs)
    run.emit({"t": "start", "req": req, "workflow": workflow["label"], "resumed": bool(session_id)})

    def feed():
        try:
            run.proc.stdin.write(prompt.encode("utf-8"))
            run.proc.stdin.close()
        except OSError:
            pass

    def read_err():
        for raw in run.proc.stderr:
            text = raw.decode("utf-8", "replace").rstrip()
            if text:
                run.emit({"t": "log", "text": text[:500]})

    def read_out():
        texts, tools, final = [], [], None
        for raw in run.proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                run.emit({"t": "log", "text": line[:500]})
                continue
            kind = ev.get("type")
            if kind == "system" and ev.get("subtype") == "init":
                if ev.get("session_id"):
                    set_session(req, ev["session_id"])
                run.emit({"t": "init", "model": ev.get("model", "")})
            elif kind == "assistant":
                for block in (ev.get("message") or {}).get("content") or []:
                    if block.get("type") == "text" and block.get("text", "").strip():
                        texts.append(block["text"])
                        run.emit({"t": "text", "text": block["text"]})
                    elif block.get("type") == "tool_use":
                        summary = tool_summary(block.get("name"), block.get("input"))
                        tools.append({"name": block.get("name"), "summary": summary})
                        run.emit({"t": "tool", "name": block.get("name"), "summary": summary})
                        if block.get("name") in ("Write", "Edit", "MultiEdit") and summary.startswith(req + "/"):
                            run.emit({"t": "file", "rel": summary})
            elif kind == "user":
                for block in (ev.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error"):
                        content = block.get("content")
                        if isinstance(content, list):
                            content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                        run.emit({"t": "tool_error", "text": str(content)[:400]})
            elif kind == "result":
                if ev.get("session_id"):
                    set_session(req, ev["session_id"])
                denials = [d.get("tool_name", "") + (" " + tool_summary(d.get("tool_name"), d.get("tool_input"))
                                                     if d.get("tool_input") else "")
                           for d in ev.get("permission_denials") or [] if isinstance(d, dict)]
                final = {"t": "result", "ok": not ev.get("is_error") and ev.get("subtype") == "success",
                         "text": ev.get("result") or "", "cost": ev.get("total_cost_usd"),
                         "turns": ev.get("num_turns"), "duration": ev.get("duration_ms"),
                         "denials": denials}
                run.emit(final)
        code = run.proc.wait()
        if final is None:
            msg = "已停止。" if run.stopped else f"Claude Code 非正常結束（代碼 {code}）。請看上方紀錄，或在終端機執行 claude 確認已登入。"
            final = {"t": "result", "ok": False, "text": msg, "denials": []}
            run.emit(final)
        answer = final.get("text") or ("\n\n".join(texts[-1:]) if texts else "")
        append_chat(req, {"role": "assistant", "text": answer, "ok": final.get("ok"),
                          "tools": tools[-60:], "denials": final.get("denials", []),
                          "cost": final.get("cost"), "time": time.time(),
                          "seconds": round(time.time() - run.started),
                          **({"base": run.base} if getattr(run, "base", None) else {})})
        with run.cond:
            run.done = True
            run.events.append({"t": "end", "i": len(run.events)})
            run.cond.notify_all()

    threading.Thread(target=feed, daemon=True).start()
    threading.Thread(target=read_err, daemon=True).start()
    threading.Thread(target=read_out, daemon=True).start()
    return run


# ───────────────────────── Markdown 預覽 ─────────────────────────

def _md_inline(text):
    import html as _h
    t = _h.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t


def render_markdown_page(title, src):
    """夠用的 Markdown → HTML：標題、段落、清單、表格、引用、程式碼區塊、frontmatter。"""
    import html as _h
    lines = src.replace("\r", "").split("\n")
    out, i = [], 0
    if lines and lines[0].strip() == "---":
        j = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), None)
        if j:
            out.append('<pre class="front">' + _h.escape("\n".join(lines[1:j])) + "</pre>")
            i = j + 1
    lst = None
    def close():
        nonlocal lst
        if lst:
            out.append(f"</{lst}>"); lst = None
    while i < len(lines):
        line = lines[i]
        st = line.strip()
        if st.startswith("```"):
            close(); buf = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            out.append("<pre><code>" + _h.escape("\n".join(buf)) + "</code></pre>"); i += 1; continue
        if st.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            close()
            def cells(row):
                return [c.strip() for c in row.strip().strip("|").split("|")]
            head = cells(line); i += 2; rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i])); i += 1
            out.append('<div class="tw"><table><thead><tr>' + "".join(f"<th>{_md_inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{_md_inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                       + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", st)
        if m:
            close(); n = len(m.group(1)); out.append(f"<h{n}>{_md_inline(m.group(2))}</h{n}>"); i += 1; continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            if lst != "ul": close(); out.append("<ul>"); lst = "ul"
            out.append(f"<li>{_md_inline(m.group(1))}</li>"); i += 1; continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)", line)
        if m:
            if lst != "ol": close(); out.append("<ol>"); lst = "ol"
            out.append(f"<li>{_md_inline(m.group(1))}</li>"); i += 1; continue
        if st.startswith(">"):
            close(); out.append(f"<blockquote>{_md_inline(st.lstrip('> '))}</blockquote>"); i += 1; continue
        if not st:
            close(); i += 1; continue
        close(); out.append(f"<p>{_md_inline(st)}</p>"); i += 1
    close()
    css = ("body{margin:0;background:#fff;color:#24223a;font:15px/1.75 'PingFang TC','Noto Sans TC','Microsoft JhengHei',system-ui,sans-serif}"
           "main{max-width:78ch;padding:32px 40px 60px}h1{font-size:24px;line-height:1.3;margin:0 0 16px}h2{font-size:19px;margin:32px 0 10px}"
           "h3{font-size:16px;margin:24px 0 8px}h4{font-size:15px;margin:18px 0 6px}p{margin:0 0 12px}ul,ol{margin:0 0 12px;padding-left:1.5em}"
           "blockquote{margin:0 0 14px;padding:4px 14px;border-left:3px solid #d8d5e3;color:#6c6983}"
           "code{background:#f2f1f6;border-radius:4px;padding:0 4px;font-size:.92em}pre{background:#f6f5f9;border-radius:8px;padding:12px 14px;overflow:auto;font-size:13px;line-height:1.55}"
           "pre code{background:none;padding:0}pre.front{color:#6c6983}.tw{overflow-x:auto;margin:0 0 16px}"
           "table{border-collapse:collapse;font-size:14px;min-width:60%}th,td{border:1px solid #e1dfe9;padding:6px 10px;text-align:left;vertical-align:top}th{background:#f6f5f9;font-weight:600}"
           "a{color:#4b3fa0}")
    return ("<!DOCTYPE html><html lang='zh-Hant'><meta charset='utf-8'><title>" + _h.escape(title) + "</title><style>" + css
            + "</style><main>" + "\n".join(out) + "</main></html>")


# ───────────────────────── 跨專案總覽登記 ─────────────────────────

HUB_HOME = Path(os.environ.get("PM_STUDIO_HOME") or (Path.home() / ".pm-studio"))


def register_project():
    """把本專案登記到使用者層級的清單，讓「專案總覽」找得到。失敗不影響工作台。"""
    try:
        path = HUB_HOME / "projects.json"
        data = read_json(path, {"projects": []})
        if not isinstance(data, dict) or not isinstance(data.get("projects"), list):
            data = {"projects": []}
        if str(ROOT) not in [p.get("path") for p in data["projects"] if isinstance(p, dict)]:
            data["projects"].append({"path": str(ROOT), "added": time.time()})
            atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2))
    except OSError:
        pass


def write_runtime(port):
    atomic_write(DATA / "runtime.json", json.dumps({"port": port, "pid": os.getpid(),
                                                     "started": time.time(), "version": VERSION}))


def clear_runtime():
    try:
        (DATA / "runtime.json").unlink()
    except OSError:
        pass


# ───────────────────────── HTTP ─────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "PMConsole/" + VERSION

    def log_message(self, fmt, *args):
        if os.environ.get("PM_CONSOLE_DEBUG"):
            sys.stderr.write("  " + fmt % args + "\n")

    # -- 安全檢查 --
    def _host_ok(self):
        return self.headers.get("Host", "") in {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}

    def _write_ok(self):
        origin = self.headers.get("Origin")
        return (self._host_ok()
                and origin in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}")
                and secrets.compare_digest(self.headers.get("X-Console-Token", ""), TOKEN))

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 200_000:
            raise ValueError("內容太長")
        return json.loads(self.rfile.read(length) or b"{}")

    # -- GET --
    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "host not allowed"})
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        path = url.path
        if path == "/":
            return self._index()
        if path == "/api/state":
            return self._send(200, state_payload())
        if path == "/api/req":
            req = valid_req_name(q.get("name"))
            if not req:
                return self._send(400, {"error": "需求名稱不正確"})
            return self._send(200, req_payload(req))
        if path == "/api/stream":
            if not secrets.compare_digest(q.get("token", ""), TOKEN):
                return self._send(403, {"error": "token"})
            return self._stream(q.get("run", ""), int(q.get("from") or 0))
        if path.startswith("/api/dev/"):
            return self._dev_get(path[len("/api/dev/"):], q)
        if path.startswith("/api/app/"):
            return self._app_get(path[len("/api/app/"):], q)
        if path == "/api/qa/state":
            req = valid_req_name(q.get("req")) if q.get("req") else None
            try:
                return self._send(200, pm_qa.results(project_id(), req))
            except Exception as e:
                return self._send(409, {"error": str(e)})
        if path == "/api/qa/file":
            try:
                data, ctype = pm_qa.file_bytes(unquote(q.get("path", "")))
                return self._send(200, data, ctype)
            except (ValueError, OSError):
                return self._send(404, {"error": "not found"})
        if path == "/api/stack":
            try:
                return self._send(200, pm_services.state(project_id()))
            except Exception as e:
                return self._send(500, {"error": f"讀取 ARCHITECTURE.md 的服務設定失敗：{e}"})
        if path == "/api/progress":
            req = valid_req_name(q.get("req"))
            if not req:
                return self._send(200, {"items": [], "manifest": False})
            try:
                return self._send(200, pm_services.progress(project_id(), req))
            except Exception as e:
                return self._send(409, {"error": str(e)})
        if path == "/api/svc/openapi":
            try:
                return self._send(200, {"paths": pm_services.openapi_paths(project_id(), q.get("id", ""))})
            except (ValueError, RuntimeError) as e:
                return self._send(409, {"error": str(e)})
        if path.startswith("/files/"):
            return self._file(unquote(path[len("/files/"):]))
        return self._send(404, {"error": "not found"})

    def _dev_get(self, name, q):
        try:
            if name == "state":
                return self._send(200, pm_dev.state())
            if name == "logs":
                items, total = pm_dev.logs(q.get("service", "supabase"), int(q.get("from") or 0))
                return self._send(200, {"items": items, "total": total})
            if name == "progress":
                req = valid_req_name(q.get("req"))
                import pm_sync  # noqa: E402
                return self._send(200, pm_services.progress(project_id(), req) if req else {"items": []})
            if name == "users":
                return self._send(200, {"users": pm_dev.list_users()})
            if name == "catalog":
                api = pm_dev.openapi()
                return self._send(200, {**api, "functions": pm_dev.functions()})
        except (RuntimeError, ValueError, OSError) as e:
            return self._send(409, {"error": str(e)})
        return self._send(404, {"error": "not found"})

    def _app_get(self, name, q):
        try:
            if name == "state":
                return self._send(200, pm_app.state(force=q.get("refresh") == "1"))
            if name == "devices":
                return self._send(200, pm_app.devices())
            if name == "screens":
                return self._send(200, {"screens": pm_app.screens()})
            if name == "screenshot":
                return self._send(200, pm_app.screenshot(), "image/png")
            if name == "devtools":
                return self._send(200, {"url": pm_app.devtools_url()})
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as e:
            return self._send(409, {"error": str(e)})
        return self._send(404, {"error": "not found"})

    def _index(self):
        cfg = load_config()
        pid = project_id()
        boot = {
            "token": TOKEN, "project": cfg.get("project_name") or ROOT.name, "root": str(ROOT),
            "hue": project_color(pid), "port": PORT, "version": VERSION,
            "workflows": [{"id": w["id"], "label": w["label"], "group": w.get("group", "自訂")} for w in cfg["workflows"]],
        }
        html = UI_FILE.read_text(encoding="utf-8").replace(
            "/*__BOOT__*/null", json.dumps(boot, ensure_ascii=False).replace("</", "<\\/"))
        self._send(200, html, "text/html; charset=utf-8", {
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-src 'self' http://127.0.0.1:* http://localhost:*; "
            "connect-src 'self'"})

    def _file(self, rel):
        target = (ROOT / rel).resolve()
        parts = Path(rel).parts
        ok = (target.is_file() and is_under(target, ROOT) and target.suffix.lower() in STATIC_EXT
              and not any(p.startswith(".") for p in parts)
              and (set(parts) & set(ARTIFACT_DIRS) or (parts and parts[0] == "scripts" and target.suffix == ".js")
                   or (len(parts) == 1 and target.name in ("DESIGN.md", "PRODUCT.md"))))
        if not ok:
            return self._send(404, {"error": "not found"})
        ctype = {".html": "text/html; charset=utf-8", ".md": "text/plain; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml",
                 ".webp": "image/webp", ".gif": "image/gif", ".woff2": "font/woff2", ".woff": "font/woff",
                 ".json": "application/json"}.get(target.suffix.lower(), "application/octet-stream")
        if target.suffix.lower() == ".md":
            page = render_markdown_page(target.name, target.read_text(encoding="utf-8", errors="replace"))
            return self._send(200, page, "text/html; charset=utf-8")
        self._send(200, target.read_bytes(), ctype)

    def _stream(self, run_id, start):
        run = CURRENT["run"]
        if not run or run.id != run_id:
            return self._send(404, {"error": "沒有這個執行"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        idx = max(0, start)
        try:
            while True:
                with run.cond:
                    if idx >= len(run.events) and not run.done:
                        run.cond.wait(timeout=15)
                    batch = run.events[idx:]
                if not batch:
                    if run.done:
                        break
                    self.wfile.write(b": ping\n\n")
                for ev in batch:
                    self.wfile.write(("data: " + json.dumps(ev, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
                idx += len(batch)
                if any(e.get("t") == "end" for e in batch):
                    break
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    # -- POST --
    def do_POST(self):
        if not self._write_ok():
            return self._send(403, {"error": "請從工作台頁面操作"})
        try:
            body = self._body()
        except (ValueError, json.JSONDecodeError) as e:
            return self._send(400, {"error": str(e)})
        path = urlparse(self.path).path
        cfg = load_config()
        if path == "/api/req/create":
            req = valid_req_name(body.get("name"))
            if not req:
                return self._send(400, {"error": "需求名稱不可空白、不可含 \\ / : * ? \" < > |，也不能以 . 開頭。"})
            target = ROOT / req
            if target.exists() and not target.is_dir():
                return self._send(400, {"error": "專案裡已有同名檔案"})
            target.mkdir(exist_ok=True)
            created = read_json(DATA / "requirements.json", [])
            if req not in created:
                created.append(req)
                atomic_write(DATA / "requirements.json", json.dumps(created, ensure_ascii=False, indent=2))
            return self._send(200, {"ok": True, "name": req})
        if path == "/api/req/reset":
            req = valid_req_name(body.get("name"))
            if not req:
                return self._send(400, {"error": "需求名稱不正確"})
            set_session(req, None)
            append_chat(req, {"role": "divider", "text": "開始新對話（Claude 不再記得上面的內容，產出檔案保留）",
                              "time": time.time()})
            return self._send(200, {"ok": True})
        if path == "/api/run":
            req = valid_req_name(body.get("req"))
            message = (body.get("message") or "").strip()
            wf = next((w for w in cfg["workflows"] if w["id"] == body.get("workflow")), None)
            if not req or not message or not wf:
                return self._send(400, {"error": "缺少需求、訊息或工作流"})
            if not (ROOT / req).is_dir():
                return self._send(400, {"error": "這個需求資料夾不存在"})
            with RUN_LOCK:
                cur = CURRENT["run"]
                if cur and not cur.done:
                    return self._send(409, {"error": f"「{cur.req}」還在執行中，等它結束或先停止。"})
                try:
                    run = start_run(cfg, req, wf, message)
                except (RuntimeError, OSError) as e:
                    return self._send(500, {"error": str(e)})
                CURRENT["run"] = run
            return self._send(200, {"ok": True, "run": run.id})
        if path == "/api/stop":
            run = CURRENT["run"]
            if run and not run.done:
                run.stopped = True
                kill_tree(run.proc)
            return self._send(200, {"ok": True})
        if path == "/api/revert":
            req = valid_req_name(body.get("req"))
            if not req:
                return self._send(400, {"error": "需求名稱不正確"})
            try:
                return self._send(200, revert_last(req))
            except RuntimeError as e:
                return self._send(409, {"error": str(e)})
        if path == "/api/qa/run":
            try:
                ids = body.get("ids") or []
                if body.get("all"):
                    ids = [s["id"] for s in pm_services.services(project_id()) if pm_qa.testable(s)]
                if not ids:
                    return self._send(400, {"error": "沒有可以跑測試的服務。請在「系統設計」替服務補上測試設定。"})
                started = []
                for sid in ids:
                    try:
                        pm_qa.run(project_id(), sid)
                        started.append(sid)
                    except RuntimeError as e:
                        if len(ids) == 1:
                            raise
                        pm_dev.log("qa-" + sid, str(e))
                return self._send(200, {"ok": True, "started": started})
            except (RuntimeError, ValueError) as e:
                return self._send(409, {"error": str(e)})
        if path.startswith("/api/svc/"):
            name = path[len("/api/svc/"):]
            try:
                if name == "start":
                    pm_services.start(project_id(), body.get("id", ""), bool(body.get("reinstall")))
                    return self._send(200, {"ok": True})
                if name == "stop":
                    pm_services.stop(body.get("id", ""))
                    return self._send(200, {"ok": True})
                if name == "request":
                    return self._send(200, pm_services.request(project_id(), body.get("id", ""), body.get("method"),
                                                               body.get("path"), body.get("body", ""), body.get("headers") or {}))
            except (RuntimeError, ValueError, OSError) as e:
                return self._send(409, {"error": str(e)})
            return self._send(404, {"error": "not found"})
        if path.startswith("/api/app/"):
            name = path[len("/api/app/"):]
            try:
                if name == "start":
                    run = pm_app.start(body.get("kind", "web"), project_id(), body.get("device"))
                    return self._send(200, {"ok": True, "kind": run.kind})
                if name == "stop":
                    pm_app.stop(body.get("kind", "web"))
                    return self._send(200, {"ok": True})
                if name == "reload":
                    return self._send(200, {"ok": True, "count": pm_app.reload(bool(body.get("full")))})
            except (RuntimeError, ValueError, OSError) as e:
                return self._send(409, {"error": str(e)})
            return self._send(404, {"error": "not found"})
        if path.startswith("/api/dev/"):
            name = path[len("/api/dev/"):]
            try:
                if name == "service":
                    return self._send(200, {"ok": True, "action": pm_dev.service_action(
                        body.get("service", ""), body.get("action", ""), project_id())})
                if name == "account":
                    return self._send(200, pm_dev.create_account(body.get("email"), body.get("password"), body.get("role", "")))
                if name == "identity":
                    return self._send(200, pm_dev.set_identity(body))
                if name == "request":
                    return self._send(200, pm_dev.proxy(body.get("method"), body.get("path"), body.get("body", ""),
                                                        body.get("headers") or {}))
                if name == "function":
                    return self._send(200, pm_dev.run_function(body.get("name", ""), body.get("body", "")))
            except (RuntimeError, ValueError, OSError) as e:
                return self._send(409, {"error": str(e)})
            return self._send(404, {"error": "not found"})
        if path == "/api/export/start":
            if export_service_alive():
                return self._send(200, {"ok": True, "status": "running"})
            started = start_export_service()
            return self._send(200, {"ok": started, "status": "starting" if started else "unavailable"})
        return self._send(404, {"error": "not found"})


def state_payload():
    cfg = load_config()
    run = CURRENT["run"]
    alive = export_service_alive()
    return {
        "project": cfg.get("project_name") or ROOT.name,
        "claude": bool(find_claude(cfg)),
        "workflow_installed": (ROOT / ".agents/workflows").is_dir(),
        "design_installed": (ROOT / ".claude/skills/hallmark").is_dir(),
        "has_design_md": (ROOT / "DESIGN.md").is_file(),
        "export": {"alive": alive, "starting": _export_starting.is_set() and not alive,
                   "installed": (SCRIPTS / "start_service.py").is_file(), "port": export_service_port()},
        "run": ({"id": run.id, "req": run.req, "done": run.done, "workflow": run.workflow["label"]}
                if run else None),
        "reqs": list_requirements(),
    }


def req_payload(req):
    sessions = read_json(DATA / "sessions.json", {})
    port = export_service_port()
    alive = export_service_alive()
    items = list_artifacts(req)
    for it in items:
        local = "/files/" + quote(it["rel"])
        it["local"] = local
        it["full"] = (f"http://127.0.0.1:{port}/" + quote(it["rel"])) \
            if alive and port and it["kind"] == "html" and it["group"] in EXPORT_SERVED else local
    return {"name": req, "exists": (ROOT / req).is_dir(), "has_session": req in sessions,
            "stale": sync_status(req).get("stale", []),
            "messages": read_json(chat_file(req), {"messages": []})["messages"], "artifacts": items}


# ───────────────────────── 啟動 ─────────────────────────

def check():
    cfg = load_config()
    ok = True
    print(f"專案：{ROOT}")
    exe = find_claude(cfg)
    print(("✅" if exe else "❌") + f" Claude Code：{exe or '找不到 claude 指令'}")
    ok &= bool(exe)
    wf = (ROOT / ".agents/workflows").is_dir()
    print(("✅" if wf else "⚠️ ") + " studio-pm-workflow：" + ("已安裝" if wf else "未安裝（工作流按鈕會找不到規範檔）"))
    print(("✅" if UI_FILE.is_file() else "❌") + f" 介面檔：{UI_FILE.name}")
    return 0 if ok and UI_FILE.is_file() else 1


def main():
    global PORT, TOKEN
    ap = argparse.ArgumentParser(description="PM 工作台")
    ap.add_argument("--open", action="store_true", help="啟動後開啟瀏覽器")
    ap.add_argument("--check", action="store_true", help="只檢查環境")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    if sys.version_info < (3, 9):
        raise SystemExit("需要 Python 3.9 以上")
    DATA.mkdir(parents=True, exist_ok=True)
    if args.check:
        return check()
    cfg = load_config()
    added = pm_dev.augment_path(cfg.get("extra_path") or [])
    if added:
        print("  已從你的終端機設定補上工具路徑：" + "、".join(added))
    pid = project_id()
    TOKEN = secrets.token_urlsafe(24)
    server = None
    for salt in range(8):
        PORT = args.port or derive_console_port(pid, salt)
        try:
            server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
            break
        except OSError:
            if args.port:
                raise SystemExit(f"連接埠 {PORT} 已被占用")
    if server is None:
        raise SystemExit("找不到可用的連接埠")
    server.daemon_threads = True
    pm_app.PID = pid
    write_runtime(PORT)
    register_project()
    url = f"http://127.0.0.1:{PORT}/"
    print(f"\n  PM 工作台 · {cfg.get('project_name') or ROOT.name}")
    print(f"  {url}\n  關閉這個視窗就會停止工作台。\n")
    if not find_claude(cfg):
        print("  ⚠️  找不到 claude 指令，請先安裝 Claude Code 並登入。\n")
    if cfg.get("auto_start_export_service") and not export_service_alive():
        start_export_service()
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    if os.name != "nt":
        def _term(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, _term)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        run = CURRENT["run"]
        if run and not run.done:
            kill_tree(run.proc)
        pm_app.stop_all()
        pm_services.stop_all()
        clear_runtime()
    return 0


PORT = 0
TOKEN = ""

if __name__ == "__main__":
    sys.exit(main())
