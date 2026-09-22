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
            "test": merged.get("test", ""), "test_report": merged.get("test_report", ""),
            "auth": merged.get("auth") if isinstance(merged.get("auth"), dict) else None,
            "depends_on": [str(x) for x in (merged.get("depends_on") or [])] if isinstance(merged.get("depends_on"), list)
                          else ([str(merged["depends_on"])] if merged.get("depends_on") else []),
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
    """替換 {變數}；大小寫都認得（{port} 與 {PORT} 相同）。不認得的變數保留原樣，方便看出寫錯。"""
    def sub(m):
        key = m.group(1)
        for k in (key, key.upper()):
            if k in vars_:
                return str(vars_[k])
        return m.group(0)
    return re.sub(r"\{([A-Za-z][A-Za-z0-9_]*)\}", sub, str(template))


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
            if not _start_deps(project_id, svc, key):
                run.state = "stopped"
                return
            vars_ = dict(variables(project_id), PORT=str(svc["port"]))
            env = dict(os.environ, BROWSER="none", NEXT_TELEMETRY_DISABLED="1", PORT=str(svc["port"]),
                       FORCE_COLOR="0")
            port = str(svc["port"])
            rendered = {k: render(str(v).replace("{port}", port), vars_) for k, v in svc["env"].items()}
            if svc["env_file"]:
                lines = ["# 由 PM 工作台在啟動時產生，請勿手改；指向本機開發環境。"] + [f"{k}={v}" for k, v in rendered.items()]
                (folder / svc["env_file"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
            env.update(rendered)
            for k, v in rendered.items():
                if re.search(r"\{\w+\}", v):
                    pm_dev.log(key, f"⚠️ 環境變數 {k} 裡有工作台不認得的變數：{v}（可用的見 pm-sysdesign.md）")
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
            run.proc = _shell_run(key, render(svc["run"], vars_), folder, env)
            if not svc.get("ready"):
                run.state = "running"
            threading.Thread(target=run._read, daemon=True).start()
        except Exception as e:
            run.state = "stopped"
            pm_dev.log(key, f"啟動失敗：{e}")

    threading.Thread(target=job, daemon=True).start()
    return run


def _wait(check, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check():
            return True
        time.sleep(2)
    return False


def _start_deps(project_id, svc, key, seen=None):
    """依 depends_on 先把需要的服務開好（例如 api 要等 db）。"""
    seen = seen or {svc["id"]}
    for dep_id in svc.get("depends_on") or []:
        if dep_id in seen:
            continue
        seen.add(dep_id)
        dep = next((x for x in services(project_id) if x["id"] == dep_id), None)
        if not dep:
            pm_dev.log(key, f"⚠️ depends_on 寫了 {dep_id}，但 ARCHITECTURE.md 沒有這個服務，略過。")
            continue
        if dep["adapter"] == "supabase":
            if pm_dev.supabase_status(force=True).get("running"):
                continue
            pm_dev.log(key, f"先啟動依賴的「{dep['label']}」…")
            try:
                pm_dev.service_action("supabase", "start", project_id)
            except RuntimeError as e:
                pm_dev.log(key, f"無法啟動「{dep['label']}」：{e}")
                return False
            if not _wait(lambda: not pm_dev.BUSY.get("supabase") and pm_dev.supabase_status(force=True).get("running"), 900):
                pm_dev.log(key, f"「{dep['label']}」沒有啟動成功，看後端分頁的日誌。")
                return False
        elif dep["adapter"] == "flutter":
            continue
        else:
            cur = RUNS.get(dep_id)
            if cur and cur.state == "running":
                continue
            if not (cur and cur.state == "starting"):
                pm_dev.log(key, f"先啟動依賴的「{dep['label']}」…")
                try:
                    start(project_id, dep_id)
                except (RuntimeError, ValueError) as e:
                    pm_dev.log(key, f"無法啟動「{dep['label']}」：{e}")
                    return False
            if not _wait(lambda: RUNS.get(dep_id) is not None and RUNS[dep_id].state in ("running", "stopped"), 300) \
                    or RUNS[dep_id].state != "running":
                pm_dev.log(key, f"「{dep['label']}」沒有啟動成功，看它的日誌。")
                return False
        pm_dev.log(key, f"✓ 依賴的「{dep['label']}」已就緒。")
    return True


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
    who = "未登入"
    ident = svc_identity(sid)
    manual = any(k.lower() in ("authorization", "cookie") for k in h)
    if ident and svc.get("auth") and not manual:
        hdr = _auth_header(project_id, svc, ident)
        h.update(hdr)
        who = ident
    elif manual:
        who = "（使用你填的標頭）"
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
        if code == 401 and ident and svc.get("auth") and not manual:
            _TOKENS.pop((sid, ident), None)          # token 過期：重新登入一次
            h.update(_auth_header(project_id, svc, ident))
            code, rh, raw, ms = pm_dev._http(method, svc["url"].rstrip("/") + path, h, body)
    except OSError as e:
        raise RuntimeError(f"連不上 {svc['label']}：{e}（服務啟動了嗎？）")
    parsed = pm_dev._json(raw)
    text = json.dumps(parsed, ensure_ascii=False, indent=2) if parsed is not None else raw.decode("utf-8", "replace")
    pm_dev.log("svc-" + sid, f"[API 測試] {method} {path} → {code}（{ms} ms）")
    keep = {k: v for k, v in rh.items() if k.lower() in ("content-type", "location", "x-request-id")}
    return {"status": code, "ms": ms, "identity": who, "headers": keep, "body": text[:200_000]}


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
                    "depends_on": s["depends_on"], "testable": s["adapter"] in ("flutter", "supabase") or bool(s["test"]),
                    "run": {"state": r.state} if r else None})
    return {"services": out, "architecture": (ROOT / "ARCHITECTURE.md").is_file(),
            "declared": _pm_sync().read_stack(ROOT) is not None, "tools": tools}


def permission_rules(project_id):
    """依服務設定補權限：tools 列的指令允許；各服務的啟動指令禁止（由工作台負責）。"""
    allow, deny = [], []
    for s in services(project_id):
        for t in s["tools"]:
            allow.append(f"Bash({t}:*)")
        if s.get("test"):
            words = s["test"].split("{")[0].split()
            if words:
                allow.append(f"Bash({' '.join(words[:3])}:*)")
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


# ───────────── 建置進度的明細：規格 vs 實作 ─────────────

HEAD = re.compile(r"^(#{1,6})\s+(.*)$")


def _spec_text(req):
    folder = ROOT / req / "技術規格"
    specs = sorted(folder.glob("*.md")) if folder.is_dir() else []
    return specs[0].read_text(encoding="utf-8", errors="replace").replace("\r", "") if specs else ""


def _norm_path(p):
    """/pets/:id、/pets/{id}、/pets/[id] 視為相同。"""
    p = "/" + str(p).strip().strip("/")
    return re.sub(r"(:\w+|\{[^}]+\}|\[[^\]]+\]|<\w+>)", "{}", p).lower()


def _spec_section(text, kind, name):
    """在技術規格裡找講這張表／這支 API 的段落；找不到標題就找表格裡的那幾列。"""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
        lines = lines[end + 1:]
    if kind == "endpoints":
        method, _, path = name.partition(" ")
        if not path:
            method, path = "", name
        target = _norm_path(path)

        def match(t):
            t = t.replace("`", "")
            paths = re.findall(r"/[\w\-/:{}\[\]]*", t)
            return any(_norm_path(x) == target for x in paths) and (not method or method.upper() in t.upper())
    else:
        word = re.compile(r"(^|[^\w])" + re.escape(name) + r"([^\w]|$)", re.I)

        def match(t):
            return bool(word.search(t.replace("`", "")))
    for i, line in enumerate(lines):
        m = HEAD.match(line)
        if m and match(m.group(2)):
            level = len(m.group(1))
            j = i + 1
            while j < len(lines):
                n = HEAD.match(lines[j])
                if n and len(n.group(1)) <= level:
                    break
                j += 1
            return "\n".join(lines[i:j]).strip()
    # 退而求其次：表格裡提到它的列（連同表頭）
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and match(line):
            k = i
            while k > 0 and lines[k - 1].strip().startswith("|"):
                k -= 1
            head = lines[k:k + 2] if k + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[k + 1]) else []
            rows = [l for l in lines[k:] if l.strip().startswith("|")]
            hits = [l for l in rows if match(l) and l not in head]
            return "\n".join(head + hits)
    return ""


def _spec_fields(section):
    """段落裡第一張表格的第一欄，當作規格列的欄位名。"""
    rows = [l for l in section.split("\n") if l.strip().startswith("|")]
    if len(rows) < 3:
        return []
    out = []
    for r in rows[2:]:
        cell = r.strip().strip("|").split("|")[0].strip().strip("`").strip()
        cell = re.sub(r"[（(].*$", "", cell).strip()
        if cell and re.match(r"^[A-Za-z_][\w]*$", cell):
            out.append(cell)
    return out


def _resolve(schema, doc, depth=0):
    if not isinstance(schema, dict) or depth > 4:
        return schema
    ref = schema.get("$ref")
    if ref and ref.startswith("#/"):
        node = doc
        for part in ref[2:].split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return _resolve(node, doc, depth + 1)
    return schema


def _props(schema, doc):
    schema = _resolve(schema, doc)
    if not isinstance(schema, dict):
        return []
    if schema.get("type") == "array" and "items" in schema:
        schema = _resolve(schema["items"], doc)
    req = set(schema.get("required") or [])
    out = []
    for k, v in (schema.get("properties") or {}).items():
        v = _resolve(v, doc)
        desc = str(v.get("description") or "").replace("\n", " ")
        out.append({"name": k, "type": v.get("format") or v.get("type") or ("參照" if "$ref" in v else ""),
                    "required": k in req, "default": v.get("default", ""),
                    "note": ("主鍵 " if "Primary Key" in desc else "") + ("外鍵 " if "Foreign Key" in desc else "")
                            + re.sub(r"Note:.*", "", desc).strip()})
    return out


def detail(project_id, req, kind, name, render_md):
    svcs = services(project_id)
    supa = any(s["adapter"] == "supabase" for s in svcs)
    text = _spec_text(req)
    section = _spec_section(text, kind, name) if text else ""
    out = {"kind": kind, "name": name, "spec_html": render_md(section) if section else "",
           "spec_found": bool(section), "actual": None, "actual_note": "", "diff": None, "try": None}
    spec_fields = _spec_fields(section) if section else []

    if kind == "tables":
        cols = None
        if supa:
            try:
                doc = pm_dev.openapi_doc()
                d = (doc.get("definitions") or {}).get(name)
                cols = _props(d, doc) if d else []
                if not d:
                    out["actual_note"] = "本機資料庫還沒有這張表。"
                out["try"] = {"target": "supabase", "method": "GET", "path": f"/rest/v1/{name}?select=*&limit=20"}
            except RuntimeError as e:
                out["actual_note"] = str(e)
        else:
            for s in svcs:
                if s["role"] == "backend" and s["openapi"] and RUNS.get(s["id"]) and RUNS[s["id"]].state == "running":
                    try:
                        code, _, raw, _ = pm_dev._http("GET", s["url"].rstrip("/") + "/" + s["openapi"].lstrip("/"), {})
                        doc = pm_dev._json(raw) or {}
                    except OSError:
                        continue
                    schemas = {k.lower(): v for k, v in ((doc.get("components") or {}).get("schemas") or {}).items()}
                    cand = [name.lower(), name.lower().rstrip("s"), name.lower().rstrip("es")]
                    hit = next((schemas[c] for c in cand if c in schemas), None)
                    if hit:
                        cols = _props(hit, doc)
                        out["actual_note"] = f"取自「{s['label']}」OpenAPI 的資料結構定義（不一定等於資料庫欄位）。"
                        break
            if cols is None and not out["actual_note"]:
                out["actual_note"] = "後端不是 Supabase，工作台無法直接讀資料庫欄位；API 服務啟動且 OpenAPI 有同名的資料結構時會顯示在這裡。"
        if cols is not None:
            out["actual"] = {"type": "columns", "columns": cols}
            if spec_fields:
                have = {c["name"] for c in cols}
                out["diff"] = {"spec_only": [f for f in spec_fields if f not in have],
                               "actual_only": [c for c in have if c not in set(spec_fields)]}

    elif kind == "endpoints":
        method, _, path = name.partition(" ")
        target = _norm_path(path)
        backends = [s for s in svcs if s["role"] == "backend" and s["adapter"] != "supabase"]
        # 有 OpenAPI 的服務才可能有 API 定義；都沒有時用第一個自建後端
        candidates = [s for s in backends if s["openapi"]] or backends[:1]
        for s in candidates:
            if not out["try"]:
                out["try"] = {"target": s["id"], "method": method.upper(), "path": path}
            if not (s["openapi"] and RUNS.get(s["id"]) and RUNS[s["id"]].state == "running"):
                out["actual_note"] = f"啟動「{s['label']}」" + ("後，會從 OpenAPI 讀出這支 API 的實際定義。" if s["openapi"] else
                                                          "並在 ARCHITECTURE.md 設定 openapi 路徑，才能讀出實際定義。")
                continue
            try:
                code, _, raw, _ = pm_dev._http("GET", s["url"].rstrip("/") + "/" + s["openapi"].lstrip("/"), {})
                doc = pm_dev._json(raw) or {}
            except OSError as e:
                out["actual_note"] = f"讀不到 OpenAPI：{e}"
                continue
            for p, ops in (doc.get("paths") or {}).items():
                if _norm_path(p) == target and isinstance(ops, dict) and method.lower() in ops:
                    op = ops[method.lower()]
                    params = [{"name": x.get("name"), "in": {"path": "路徑", "query": "查詢", "header": "標頭"}.get(x.get("in"), x.get("in")),
                               "required": bool(x.get("required")), "type": (_resolve(x.get("schema", {}), doc) or {}).get("type", "")}
                              for x in (_resolve(x, doc) for x in op.get("parameters") or [])]
                    body = None
                    rb = _resolve(op.get("requestBody") or {}, doc)
                    for ct, media in (rb.get("content") or {}).items():
                        body = _props(media.get("schema"), doc)
                        break
                    responses = []
                    for codev, r in (op.get("responses") or {}).items():
                        r = _resolve(r, doc)
                        fields = []
                        for ct, media in (r.get("content") or {}).items():
                            fields = _props(media.get("schema"), doc)
                            break
                        responses.append({"code": codev, "description": r.get("description", ""), "fields": fields})
                    out["actual"] = {"type": "operation", "path": p, "method": method.upper(), "summary": op.get("summary") or op.get("description") or "",
                                     "params": params, "body": body, "responses": responses, "service": s["label"]}
                    out["actual_note"] = ""
                    break
            if out["actual"]:
                out["try"]["target"] = s["id"]
                break
            out["actual_note"] = f"「{s['label']}」的 OpenAPI 裡還沒有這支 API。"
        if not backends:
            out["actual_note"] = "這個專案沒有自建後端服務。"

    elif kind == "rpc" and supa:
        try:
            doc = pm_dev.openapi_doc()
            op = ((doc.get("paths") or {}).get(f"/rpc/{name}") or {}).get("post")
            if op:
                params = []
                for x in op.get("parameters") or []:
                    x = _resolve(x, doc)
                    if x.get("in") == "body":
                        params += _props(x.get("schema"), doc)
                out["actual"] = {"type": "columns", "columns": params, "caption": "參數"}
            else:
                out["actual_note"] = "本機資料庫還沒有這個函式。"
            args = {c["name"]: (1 if c["type"] in ("integer", "bigint", "numeric") else False if c["type"] == "boolean" else "")
                    for c in (out["actual"] or {}).get("columns", [])} if out.get("actual") else {}
            out["try"] = {"target": "supabase", "method": "POST", "path": f"/rest/v1/rpc/{name}",
                          "body": json.dumps(args, ensure_ascii=False, indent=2) if args else ""}
        except RuntimeError as e:
            out["actual_note"] = str(e)
    else:
        out["actual_note"] = "這一類項目只顯示技術規格。"
    if not section:
        out["spec_note"] = "技術規格裡找不到專門講它的段落或表格列。建議在 Spec 的資料模型或介面章節用它的名稱當小標題。"
    return out


# ───────────── 自建後端的測試帳號與登入 ─────────────

_TOKENS = {}   # (服務, 信箱) -> (標頭 dict, 到期時間)


def _json_path(data, path):
    cur = data
    for part in str(path or "").split("."):
        if not part:
            continue
        if isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)] if int(part) < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def svc_accounts(project_id, sid):
    svc = find(project_id, sid)
    auth = svc.get("auth") or {}
    out = []
    for a in auth.get("accounts") or []:
        if isinstance(a, dict) and a.get("email"):
            out.append({"email": str(a["email"]), "password": str(a.get("password", "")), "role": str(a.get("role", "")),
                        "source": "ARCHITECTURE.md"})
    local = pm_dev._read_json(DATA / "svc-accounts" / f"{sid}.json", [])
    for a in local:
        if a.get("email") and a["email"] not in [x["email"] for x in out]:
            out.append({**a, "source": "工作台"})
    return out


def add_svc_account(project_id, sid, email, password, role):
    find(project_id, sid)
    email = (email or "").strip()
    if not email or not password:
        raise ValueError("帳號與密碼都要填")
    path = DATA / "svc-accounts" / f"{sid}.json"
    items = [a for a in pm_dev._read_json(path, []) if a.get("email") != email]
    items.append({"email": email, "password": password, "role": role or ""})
    pm_dev._write_json(path, items)
    return {"ok": True}


def svc_identity(sid):
    return pm_dev._read_json(DATA / "svc-identity.json", {}).get(sid, "")


def set_svc_identity(project_id, sid, email):
    if email and email not in [a["email"] for a in svc_accounts(project_id, sid)]:
        raise ValueError("沒有這個測試帳號")
    data = pm_dev._read_json(DATA / "svc-identity.json", {})
    data[sid] = email or ""
    pm_dev._write_json(DATA / "svc-identity.json", data)
    return {"ok": True, "identity": data[sid]}


def _auth_header(project_id, svc, email):
    key = (svc["id"], email)
    cached = _TOKENS.get(key)
    if cached and cached[1] > time.time():
        return dict(cached[0])
    auth = svc["auth"]
    acc = next((a for a in svc_accounts(project_id, svc["id"]) if a["email"] == email), None)
    if not acc:
        raise RuntimeError("找不到這個測試帳號")
    method, _, lpath = str(auth.get("login") or "POST /auth/login").partition(" ")
    if not lpath:
        method, lpath = "POST", method
    tmpl = str(auth.get("body") or '{"email": "{email}", "password": "{password}"}')
    body = tmpl.replace("{email}", json.dumps(acc["email"])[1:-1]).replace("{password}", json.dumps(acc["password"])[1:-1])
    try:
        json.loads(body)
    except ValueError:
        raise RuntimeError("ARCHITECTURE.md 的 auth.body 不是有效的 JSON 範本")
    try:
        code, rh, raw, _ = pm_dev._http(method.upper(), svc["url"].rstrip("/") + "/" + lpath.lstrip("/"),
                                        {"Content-Type": "application/json"}, body.encode("utf-8"))
    except OSError as e:
        raise RuntimeError(f"登入時連不上 {svc['label']}：{e}")
    data = pm_dev._json(raw)
    if code >= 300:
        msg = (data or {}).get("message") if isinstance(data, dict) else ""
        raise RuntimeError(f"測試帳號 {email} 登入失敗（{code}）{('：' + msg) if msg else ''}。帳密或 auth 設定可能不對。")
    token_path = str(auth.get("token") or "token")
    if token_path == "cookie":
        cookie = "; ".join(v.split(";")[0] for k, v in rh.items() if k.lower() == "set-cookie")
        if not cookie:
            raise RuntimeError("登入成功，但回應沒有 Set-Cookie")
        header = {"Cookie": cookie}
    else:
        token = _json_path(data, token_path)
        if not token:
            raise RuntimeError(f"登入成功，但在回應的「{token_path}」找不到 token。請檢查 ARCHITECTURE.md 的 auth.token。")
        name, _, value = str(auth.get("header") or "Authorization: Bearer {token}").partition(":")
        header = {name.strip(): value.strip().replace("{token}", str(token))}
    _TOKENS[key] = (header, time.time() + int(auth.get("ttl") or 1500))
    pm_dev.log("svc-" + svc["id"], f"[API 測試] 已用測試帳號 {email} 登入")
    return dict(header)


def auth_state(project_id, sid):
    svc = find(project_id, sid)
    return {"configured": bool(svc.get("auth")), "identity": svc_identity(sid),
            "accounts": [{k: a[k] for k in ("email", "role", "source")} for a in svc_accounts(project_id, sid)],
            "login": (svc.get("auth") or {}).get("login", "")}


# ───────────── 範例請求：從 OpenAPI 帶入參數與內容 ─────────────

def _skeleton(schema, doc, depth=0):
    schema = _resolve(schema, doc)
    if not isinstance(schema, dict) or depth > 4:
        return None
    for k in ("example", "default"):
        if k in schema:
            return schema[k]
    if schema.get("enum"):
        return schema["enum"][0]
    if schema.get("oneOf") or schema.get("anyOf"):
        return _skeleton((schema.get("oneOf") or schema.get("anyOf"))[0], doc, depth + 1)
    t, fmt = schema.get("type"), schema.get("format")
    if t == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        req = set(schema.get("required") or [])
        keys = [k for k in props if k in req] or list(props)[:8]
        return {k: _skeleton(props[k], doc, depth + 1) for k in keys}
    if t == "array":
        return [_skeleton(schema.get("items") or {}, doc, depth + 1)]
    if t in ("integer", "number"):
        return schema.get("minimum", 1)
    if t == "boolean":
        return False
    return {"email": "demo@example.com", "date-time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "date": time.strftime("%Y-%m-%d"), "uuid": "00000000-0000-0000-0000-000000000000"}.get(fmt, "")


def example(project_id, sid, method, path):
    svc = find(project_id, sid)
    method = (method or "GET").upper()
    out = {"method": method, "path": path, "body": "", "notes": []}
    doc = {}
    if svc["openapi"] and svc["url"]:
        try:
            code, _, raw, _ = pm_dev._http("GET", svc["url"].rstrip("/") + "/" + svc["openapi"].lstrip("/"), {})
            doc = pm_dev._json(raw) or {}
        except OSError:
            doc = {}
    target = _norm_path(path.split("?")[0])
    concrete = [x for x in target.strip("/").split("/")]

    def seg_match(tpl):
        t = _norm_path(tpl).strip("/").split("/")
        return len(t) == len(concrete) and all(a == b or a == "{}" for a, b in zip(t, concrete))

    op, oppath, exact = None, path, False
    for p, ops in (doc.get("paths") or {}).items():
        if isinstance(ops, dict) and method.lower() in ops and _norm_path(p) == target:
            op, oppath, exact = ops[method.lower()], p, True
            break
    if not op:
        for p, ops in (doc.get("paths") or {}).items():
            if isinstance(ops, dict) and method.lower() in ops and seg_match(p):
                op, oppath = ops[method.lower()], path.split("?")[0]   # 使用者填的是實際值，保留
                break
    if not op:
        out["notes"].append("OpenAPI 裡找不到這支 API，參數請自行填寫。" if doc else "讀不到 OpenAPI，參數請自行填寫。")
        return out
    # 路徑參數：先找同一資源的清單 API，拿第一筆資料的值
    names = re.findall(r"\{(\w+)\}|:(\w+)", oppath) if exact else []
    names = [a or b for a, b in names]
    filled = oppath
    if names:
        first_param = re.search(r"/(\{\w+\}|:\w+)", oppath)
        collection = oppath[:first_param.start()] if first_param else ""
        item = None
        if collection and "get" in ((doc.get("paths") or {}).get(collection) or {}):
            try:
                r = request(project_id, sid, "GET", collection)
                data = json.loads(r["body"]) if r["status"] < 300 else None
                rows = data if isinstance(data, list) else next((data[k] for k in ("data", "items", "results", "rows")
                                                                 if isinstance(data, dict) and isinstance(data.get(k), list)), [])
                item = rows[0] if rows else None
                if r["status"] >= 300:
                    out["notes"].append(f"查 {collection} 取得範例編號時回了 {r['status']}，可能要先選一個有權限的身分。")
            except (RuntimeError, ValueError):
                pass
        for n in names:
            value = (item or {}).get(n) or (item or {}).get("id") if isinstance(item, dict) else None
            if value is not None:
                out["notes"].append(f"路徑參數 {n} 用了 {collection} 清單第一筆的值。")
            else:
                param = next((x for x in (op.get("parameters") or []) if _resolve(x, doc).get("name") == n), {})
                value = _skeleton(_resolve(param, doc).get("schema", {}), doc) or f"<{n}>"
                out["notes"].append(f"路徑參數 {n} 找不到真實資料，先填了範例值，請改成存在的編號。")
            filled = filled.replace("{" + n + "}", str(value)).replace(":" + n, str(value))
    # 必填的查詢參數
    q = []
    for x in op.get("parameters") or []:
        x = _resolve(x, doc)
        if x.get("in") == "query" and x.get("required"):
            q.append(f"{x.get('name')}={_skeleton(x.get('schema', {}), doc)}")
    out["path"] = filled + (("?" + "&".join(q)) if q else "")
    # 請求內容
    rb = _resolve(op.get("requestBody") or {}, doc)
    for ct, media in (rb.get("content") or {}).items():
        ex = media.get("example")
        if ex is None and isinstance(media.get("examples"), dict) and media["examples"]:
            ex = _resolve(next(iter(media["examples"].values())), doc).get("value")
        if ex is None:
            ex = _skeleton(media.get("schema") or {}, doc)
        if ex is not None:
            out["body"] = json.dumps(ex, ensure_ascii=False, indent=2)
            out["notes"].append("請求內容是依 OpenAPI 產生的範例，送出前確認值是否合理。")
        break
    if svc.get("auth") and not svc_identity(sid) and op.get("security", doc.get("security")):
        out["notes"].append("這支 API 需要登入：在上方「身分」選一個測試帳號。")
    return out
