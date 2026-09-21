"""PM 工作台 · 開發服務層（技術中立）。

服務清單來自 ARCHITECTURE.md 開頭的 services（系統設計討論後寫下）；沒有時依專案資料夾自動偵測。
每個服務有一個 adapter：
  · 專屬面板：supabase（後端分頁）、flutter（APP 分頁）、nextjs（前端，自動判斷頁面進度）
  · 內建預設：vite、expo（知道怎麼啟動，其餘同通用）
  · generic：任何能在本機用指令啟動的服務，照 services 寫的 install／run／url 執行
工作台負責啟動與停止；Claude 不自己跑開發伺服器。
"""
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import pm_dev

ROOT = None
DATA = None
RUNS = {}
DEEP = {"supabase", "flutter", "nextjs"}
ROLE_LABEL = {"app": "APP", "web": "前端", "backend": "後端"}
SRC_EXT = {".dart", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".py", ".go", ".rb", ".php", ".java", ".kt",
           ".swift", ".cs", ".rs", ".astro", ".mdx"}
MARK = {"app": re.compile(r"pm-screen:\s*([\w\-/\[\]]+)"),
        "web": re.compile(r"pm-page:\s*(/[\w\-/\[\]\.:]*)"),
        "backend": re.compile(r"pm-endpoint:\s*([A-Z]+\s+/[\w\-/\{\}\[\]:\.]*)")}
PAGE_FILE = re.compile(r"^page\.(tsx|ts|jsx|js|mdx)$")


def init(root, data):
    global ROOT, DATA
    ROOT, DATA = Path(root), Path(data)


def _pm_sync():
    import pm_sync  # 與工作台同在 scripts/
    return pm_sync


# ───────────── 服務清單 ─────────────

def _pkg_manager(folder):
    for d in [folder, *folder.parents]:
        if (d / "pnpm-lock.yaml").is_file() or (d / "pnpm-workspace.yaml").is_file():
            return "pnpm"
        if (d / "yarn.lock").is_file():
            return "yarn"
        if (d / "bun.lockb").is_file() or (d / "bun.lock").is_file():
            return "bun"
        if (d / "package-lock.json").is_file():
            return "npm"
        if d == ROOT:
            break
    return "pnpm" if pm_dev.which("pnpm") else "npm"


def _exec(pm):
    return {"npm": "npx", "pnpm": "pnpm exec", "yarn": "yarn", "bun": "bunx"}[pm]


def _detect():
    found = []
    if (ROOT / "supabase/config.toml").is_file():
        found.append({"id": "supabase", "role": "backend", "adapter": "supabase", "label": "Supabase"})
    if (ROOT / "app/pubspec.yaml").is_file():
        found.append({"id": "app", "role": "app", "adapter": "flutter", "dir": "app", "label": "APP"})
    web = ROOT / "web"
    for pkg in sorted(web.glob("*/package.json")) if web.is_dir() else []:
        try:
            deps = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**deps.get("dependencies", {}), **deps.get("devDependencies", {})}
        except (OSError, ValueError):
            deps = {}
        adapter = "nextjs" if "next" in deps else "vite" if "vite" in deps else None
        if adapter:
            found.append({"id": pkg.parent.name, "role": "web", "adapter": adapter,
                          "dir": pkg.parent.relative_to(ROOT).as_posix(), "label": pkg.parent.name})
    return found


def _port(pid, sid):
    return 21000 + int(hashlib.sha256(f"{pid}:svc:{sid}".encode()).hexdigest()[:6], 16) % 11000


def services(project_id):
    stack = _pm_sync().read_stack(ROOT)
    raw = stack["services"] if stack else _detect()
    out = []
    has_supabase = any(s.get("adapter") == "supabase" for s in raw)
    for s in raw:
        s = dict(s)
        sid = re.sub(r"[^\w\-]", "-", str(s["id"]))
        adapter = str(s.get("adapter") or "generic").lower()
        role = s.get("role") or {"supabase": "backend", "flutter": "app", "nextjs": "web", "vite": "web", "expo": "app"}.get(adapter, "backend")
        d = str(s.get("dir") or ("app" if adapter == "flutter" else "")).strip("/")
        folder = ROOT / d if d else ROOT
        port = int(s.get("port") or _port(project_id, sid))
        pm = _pkg_manager(folder) if adapter in ("nextjs", "vite", "expo") else ""
        preset = {}
        if adapter == "nextjs":
            preset = {"install": f"{pm} install", "run": f"{_exec(pm)} next dev -p {{port}} -H 127.0.0.1",
                      "ready": r"Ready in|✓ Ready|Local:\s+http", "url": "http://127.0.0.1:{port}", "env_file": ".env.local",
                      "env": ({"NEXT_PUBLIC_SUPABASE_URL": "{SUPABASE_URL}", "NEXT_PUBLIC_SUPABASE_ANON_KEY": "{SUPABASE_ANON_KEY}"}
                              if has_supabase else {"NEXT_PUBLIC_API_URL": "{BACKEND_URL}"})}
        elif adapter == "vite":
            preset = {"install": f"{pm} install", "run": f"{_exec(pm)} vite --port {{port}} --host 127.0.0.1 --strictPort",
                      "ready": r"Local:\s+http|ready in", "url": "http://127.0.0.1:{port}", "env_file": ".env.local",
                      "env": ({"VITE_SUPABASE_URL": "{SUPABASE_URL}", "VITE_SUPABASE_ANON_KEY": "{SUPABASE_ANON_KEY}"}
                              if has_supabase else {"VITE_API_URL": "{BACKEND_URL}"})}
        elif adapter == "expo":
            preset = {"install": f"{pm} install", "run": f"{_exec(pm)} expo start --web --port {{port}}",
                      "ready": r"Web is waiting|Waiting on http|Metro waiting", "url": "http://127.0.0.1:{port}",
                      "env_file": ".env.local",
                      "env": ({"EXPO_PUBLIC_SUPABASE_URL": "{SUPABASE_URL}", "EXPO_PUBLIC_SUPABASE_ANON_KEY": "{SUPABASE_ANON_KEY}"}
                              if has_supabase else {"EXPO_PUBLIC_API_URL": "{BACKEND_URL}"})}
        merged = {**preset, **{k: v for k, v in s.items() if v not in (None, "")}}
        if "env" in preset and isinstance(s.get("env"), dict):
            merged["env"] = {**preset["env"], **s["env"]}
        out.append({
            "id": sid, "role": role, "adapter": adapter, "label": s.get("label") or sid, "dir": d,
            "port": port, "pm": pm, "support": "deep" if adapter in DEEP else "general",
            "install": merged.get("install", ""), "run": merged.get("run", ""), "ready": merged.get("ready", ""),
            "url": str(merged.get("url", "")).replace("{port}", str(port)),
            "openapi": merged.get("openapi", ""), "env": merged.get("env") or {}, "env_file": merged.get("env_file", ""),
            "tools": merged.get("tools") or [],
        })
    return out


def find(project_id, sid):
    svc = next((s for s in services(project_id) if s["id"] == sid), None)
    if not svc:
        raise ValueError("ARCHITECTURE.md 裡沒有這個服務")
    return svc


# ───────────── 變數與環境 ─────────────

def variables(project_id, target=""):
    """給 env 範本用的變數。target=android 時把本機網址換成 10.0.2.2。"""
    st = pm_dev.supabase_status() if (ROOT / "supabase/config.toml").is_file() else {"running": False}
    v = {"SUPABASE_URL": st.get("api", "") if st.get("running") else "",
         "SUPABASE_ANON_KEY": st.get("anon", "") if st.get("running") else "",
         "SUPABASE_DB_URL": st.get("db", "") if st.get("running") else ""}
    svcs = services(project_id)
    backend_url = ""
    for s in svcs:
        v[re.sub(r"\W", "_", s["id"]).upper() + "_URL"] = s["url"]
        if s["role"] == "backend" and s["adapter"] != "supabase" and s["url"] and not backend_url:
            backend_url = s["url"]
    v["BACKEND_URL"] = v["API_URL"] = backend_url or v["SUPABASE_URL"]
    if target == "android":
        v = {k: (x.replace("127.0.0.1", "10.0.2.2").replace("localhost", "10.0.2.2") if isinstance(x, str) and x.startswith("http") else x)
             for k, x in v.items()}
    return v


def render(template, vars_):
    return re.sub(r"\{([A-Z0-9_]+)\}", lambda m: str(vars_.get(m.group(1), "")), str(template))


# ───────────── 執行 ─────────────

class Run:
    def __init__(self, svc):
        self.svc = svc
        self.proc = None
        self.state = "starting"

    def _read(self):
        key = "svc-" + self.svc["id"]
        ready = re.compile(self.svc["ready"]) if self.svc.get("ready") else None
        for raw in self.proc.stdout:
            text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", raw.decode("utf-8", "replace")).rstrip()
            if not text:
                continue
            pm_dev.log(key, text)
            if self.state == "starting" and ready and ready.search(text):
                self.state = "running"
                pm_dev.log(key, f"✓ {self.svc['label']}已啟動" + (f"：{self.svc['url']}" if self.svc["url"] else "") + "。")
        code = self.proc.wait()
        if self.state != "stopped":
            pm_dev.log(key, f"服務已結束（代碼 {code}）。")
        self.state = "stopped"

    def stop(self):
        self.state = "stopped"
        if self.proc and self.proc.poll() is None:
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
                else:
                    self.proc.kill()
                self.proc.wait(timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.proc.kill()
                except OSError:
                    pass


def _shell_run(key, cmd, cwd, env):
    pm_dev.log(key, "$ " + cmd)
    kwargs = {"cwd": str(cwd), "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
              "stdin": subprocess.DEVNULL, "env": env, "shell": True}
    if os.name != "nt":
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def _needs_install(svc, folder):
    if not svc.get("install"):
        return False
    if (folder / "package.json").is_file():
        return not (folder / "node_modules").is_dir()
    return not (DATA / "installed" / svc["id"]).is_file()


def start(project_id, sid, reinstall=False):
    svc = find(project_id, sid)
    if svc["adapter"] in ("supabase", "flutter"):
        raise ValueError("這個服務在專屬分頁啟動")
    if not svc["run"]:
        raise RuntimeError(f"ARCHITECTURE.md 沒寫「{svc['label']}」怎麼啟動（run）。請在「系統設計」補上。")
    folder = ROOT / svc["dir"] if svc["dir"] else ROOT
    if not folder.is_dir():
        raise RuntimeError(f"找不到 {svc['dir']}/。選「開發」讓 Claude 先建立程式。")
    cur = RUNS.get(sid)
    if cur and cur.state in ("starting", "running"):
        raise RuntimeError("已經在執行了")
    run = Run(svc)
    RUNS[sid] = run
    key = "svc-" + sid

    def job():
        try:
            vars_ = variables(project_id)
            env = dict(os.environ, BROWSER="none", NEXT_TELEMETRY_DISABLED="1", PORT=str(svc["port"]),
                       FORCE_COLOR="0")
            rendered = {k: render(v, vars_) for k, v in svc["env"].items()}
            if svc["env_file"]:
                lines = ["# 由 PM 工作台在啟動時產生，請勿手改；指向本機開發環境。"] + [f"{k}={v}" for k, v in rendered.items()]
                (folder / svc["env_file"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
            env.update(rendered)
            if not vars_.get("BACKEND_URL") and svc["role"] != "backend":
                pm_dev.log(key, "⚠️ 沒有執行中的後端，需要資料的畫面會拿不到東西。")
            if reinstall or _needs_install(svc, folder):
                pm_dev.log(key, "安裝套件中（第一次會比較久）…")
                p = _shell_run(key, svc["install"], folder, env)
                for raw in p.stdout:
                    t = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", raw.decode("utf-8", "replace")).rstrip()
                    if t:
                        pm_dev.log(key, t)
                if p.wait() != 0:
                    run.state = "stopped"
                    pm_dev.log(key, "套件安裝失敗，看上面的訊息。")
                    return
                (DATA / "installed").mkdir(parents=True, exist_ok=True)
                (DATA / "installed" / sid).write_text(str(time.time()), encoding="utf-8")
            run.proc = _shell_run(key, render(svc["run"].replace("{port}", str(svc["port"])), vars_), folder, env)
            if not svc.get("ready"):
                run.state = "running"
            threading.Thread(target=run._read, daemon=True).start()
        except Exception as e:
            run.state = "stopped"
            pm_dev.log(key, f"啟動失敗：{e}")

    threading.Thread(target=job, daemon=True).start()
    return run


def stop(sid):
    run = RUNS.get(sid)
    if run:
        run.stop()


def stop_all():
    for run in list(RUNS.values()):
        run.stop()


# ───────────── 自訂後端的 API 測試台 ─────────────

def request(project_id, sid, method, path, body_text="", headers=None):
    svc = find(project_id, sid)
    if not svc["url"]:
        raise RuntimeError("這個服務沒有網址")
    host = urlparse(svc["url"]).hostname
    if host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("只允許連到本機服務")
    method = (method or "GET").upper()
    if method not in ("GET", "POST", "PATCH", "PUT", "DELETE"):
        raise ValueError("不支援的方法")
    path = "/" + (path or "").lstrip("/")
    if ".." in path or path.startswith("//"):
        raise ValueError("路徑不正確")
    h = {k: v for k, v in (headers or {}).items() if isinstance(v, str) and k.lower() not in ("host",)}
    body = None
    if body_text and method != "GET":
        try:
            json.loads(body_text)
        except ValueError:
            raise ValueError("內容不是有效的 JSON")
        body = body_text.encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    try:
        code, rh, raw, ms = pm_dev._http(method, svc["url"].rstrip("/") + path, h, body)
    except OSError as e:
        raise RuntimeError(f"連不上 {svc['label']}：{e}（服務啟動了嗎？）")
    parsed = pm_dev._json(raw)
    text = json.dumps(parsed, ensure_ascii=False, indent=2) if parsed is not None else raw.decode("utf-8", "replace")
    pm_dev.log("svc-" + sid, f"[API 測試] {method} {path} → {code}（{ms} ms）")
    keep = {k: v for k, v in rh.items() if k.lower() in ("content-type", "location", "x-request-id")}
    return {"status": code, "ms": ms, "identity": "（自訂後端，身分請自行帶 Authorization 標頭）", "headers": keep,
            "body": text[:200_000]}


def openapi_paths(project_id, sid):
    svc = find(project_id, sid)
    if not svc["openapi"] or not svc["url"]:
        return []
    try:
        code, _, raw, _ = pm_dev._http("GET", svc["url"].rstrip("/") + "/" + svc["openapi"].lstrip("/"), {})
    except OSError:
        return []
    doc = pm_dev._json(raw) or {}
    out = []
    for path, ops in (doc.get("paths") or {}).items():
        for m in (ops or {}):
            if m.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                out.append(f"{m.upper()} {path}")
    return out


# ───────────── 建置進度 ─────────────

def _markers(folder, role):
    found = {}
    if not folder.is_dir():
        return found
    for f in folder.rglob("*"):
        if f.suffix not in SRC_EXT or not f.is_file():
            continue
        parts = f.relative_to(folder).parts
        if any(p in ("node_modules", "build", ".dart_tool", ".next", "dist", ".venv", "Pods") or p.startswith(".") for p in parts):
            continue
        try:
            for m in MARK[role].finditer(f.read_text(encoding="utf-8", errors="ignore")):
                found.setdefault(re.sub(r"\s+", " ", m.group(1)).strip(), f.relative_to(ROOT).as_posix())
        except OSError:
            pass
    return found


def next_pages(folder):
    found = {}
    for app_root in (folder / "app", folder / "src/app"):
        if app_root.is_dir():
            for f in app_root.rglob("*"):
                if f.is_file() and PAGE_FILE.match(f.name) and "node_modules" not in f.parts:
                    parts = [p for p in f.parent.relative_to(app_root).parts
                             if not (p.startswith("(") and p.endswith(")")) and not p.startswith("@")]
                    found.setdefault("/" + "/".join(parts), f.relative_to(ROOT).as_posix())
    for pages_root in (folder / "pages", folder / "src/pages"):
        if pages_root.is_dir():
            for f in pages_root.rglob("*"):
                if f.is_file() and f.suffix in (".tsx", ".ts", ".jsx", ".js") and not f.name.startswith("_") \
                        and f.relative_to(pages_root).parts[0] != "api":
                    rel = f.relative_to(pages_root).with_suffix("").as_posix()
                    route = "/" + (rel[:-5] if rel.endswith("index") else rel).strip("/")
                    found.setdefault(route, f.relative_to(ROOT).as_posix())
    return found


def _norm_route(r):
    return "/" + str(r).strip().strip("/")


def progress(project_id, req):
    manifest = _pm_sync().read_manifest(ROOT, req)
    svcs = services(project_id)
    result = {"req": req, "manifest": manifest is not None, "items": [], "migrations": pm_dev.migrations(),
              "services": [{"id": s["id"], "label": s["label"], "role": s["role"], "adapter": s["adapter"]} for s in svcs]}
    if manifest is None:
        return result
    supa = any(s["adapter"] == "supabase" for s in svcs)
    running = supa and pm_dev.supabase_status().get("running")
    have = {"tables": set(), "rpc": set(), "buckets": set()}
    if running:
        try:
            api = pm_dev.openapi()
            have["tables"], have["rpc"] = set(api["tables"]), set(api["rpc"])
            have["buckets"] = set(pm_dev.buckets())
        except Exception as e:
            result["error"] = str(e)
    fn = set(pm_dev.functions())
    app_marks, endpoint_marks = {}, {}
    for s in svcs:
        folder = ROOT / s["dir"] if s["dir"] else None
        if s["role"] == "app" and folder:
            app_marks.update(_markers(folder, "app"))
        if s["role"] == "backend" and s["adapter"] != "supabase" and folder:
            endpoint_marks.update(_markers(folder, "backend"))
            for ep in (openapi_paths(project_id, s["id"]) if s["id"] in RUNS and RUNS[s["id"]].state == "running" else []):
                endpoint_marks.setdefault(ep, s["label"] + "（OpenAPI）")
    labels = {"tables": "資料表", "rpc": "資料庫函式", "functions": "後端函式", "buckets": "檔案儲存",
              "endpoints": "API", "app_screens": "APP 畫面"}
    for key, names in manifest.items():
        for name in names:
            where, state, role = "", "todo", "backend"
            if key in ("tables", "rpc", "buckets"):
                if supa:
                    state = ("done" if name in have[key] else "todo") if running else "unknown"
                else:
                    state = "manual"
            elif key == "functions":
                state = "done" if name in fn else ("todo" if supa else "manual")
            elif key == "endpoints":
                k = re.sub(r"\s+", " ", name).strip()
                where = endpoint_marks.get(k, "")
                state = "done" if where else "todo"
            elif key == "app_screens":
                role = "app"
                where = app_marks.get(name, "")
                state = "done" if where else "todo"
            elif key.startswith("pages."):
                role = "web"
                sid = key.split(".", 1)[1]
                svc = next((s for s in svcs if s["id"] == sid), None)
                if not svc:
                    state = "unknown"
                else:
                    folder = ROOT / svc["dir"] if svc["dir"] else ROOT
                    found = {_norm_route(r): f for r, f in (next_pages(folder) if svc["adapter"] == "nextjs" else {}).items()}
                    found.update({_norm_route(r): f for r, f in _markers(folder, "web").items()})
                    where = found.get(_norm_route(name), "")
                    state = "done" if where else "todo"
            label = labels.get(key) or ("頁面：" + next((s["label"] for s in svcs if s["id"] == key.split(".", 1)[1]), key.split(".", 1)[1]))
            result["items"].append({"kind": key, "label": label, "name": name, "state": state, "where": where, "role": role})
    result["running"] = bool(running)
    return result


# ───────────── 狀態 ─────────────

def state(project_id):
    svcs = services(project_id)
    tools = {"node": bool(pm_dev.which("node")), "pnpm": bool(pm_dev.which("pnpm")), "npm": bool(pm_dev.which("npm"))}
    out = []
    for s in svcs:
        r = RUNS.get(s["id"])
        out.append({**{k: s[k] for k in ("id", "role", "adapter", "label", "dir", "url", "support", "openapi", "port")},
                    "exists": (ROOT / s["dir"]).is_dir() if s["dir"] else True,
                    "can_run": bool(s["run"]) or s["adapter"] in ("supabase", "flutter"),
                    "run": {"state": r.state} if r else None})
    return {"services": out, "architecture": (ROOT / "ARCHITECTURE.md").is_file(),
            "declared": _pm_sync().read_stack(ROOT) is not None, "tools": tools}


def permission_rules(project_id):
    """依服務設定補權限：tools 列的指令允許；各服務的啟動指令禁止（由工作台負責）。"""
    allow, deny = [], []
    for s in services(project_id):
        for t in s["tools"]:
            allow.append(f"Bash({t}:*)")
        if s["run"]:
            head = s["run"].split("{")[0].strip()
            words = head.split()
            if words:
                deny.append(f"Bash({' '.join(words[:4])}:*)")
        if s["install"] and s["adapter"] in ("nextjs", "vite", "expo"):
            pm = s["pm"]
            allow += [f"Bash({pm} install:*)", f"Bash({pm} add:*)", f"Bash({pm} remove:*)", f"Bash({pm} run lint:*)",
                      f"Bash({pm} run test:*)", f"Bash({pm} run build:*)", f"Bash({_exec(pm)} tsc:*)"]
            deny += [f"Bash({pm} run dev:*)", f"Bash({pm} dev:*)", f"Bash({pm} start:*)"]
    return sorted(set(allow)), sorted(set(deny))
