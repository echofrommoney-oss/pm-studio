"""PM 工作台 · 開發服務（第一階段：Supabase 後端）。

由 pm_console.py 載入。負責：
  · 啟動／停止本機 Supabase，收集輸出當日誌
  · 讀取本機 Supabase 的網址與金鑰（金鑰只留在伺服器端，不送到瀏覽器）
  · 測試帳號、目前身分、API 代理（避免瀏覽器跨來源問題）
  · 對照技術規格 manifest 顯示建置進度
所有對外連線只打本機 Supabase（127.0.0.1／localhost）。
"""
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = None
DATA = None
LOCK = threading.Lock()
LOGS = {}            # service -> [ {i, t, text} ]
BUSY = {}            # service -> 動作名稱（start/stop/reset）
_STATUS = {"at": 0, "data": None}
_TOKENS = {}         # email -> (token, expires_at)
ALLOWED_PREFIXES = ("/rest/v1/", "/rest/v1", "/functions/v1/", "/auth/v1/", "/storage/v1/", "/graphql/v1")


def init(root, data):
    global ROOT, DATA
    ROOT, DATA = Path(root), Path(data)


# ───────────── 小工具 ─────────────

def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def log(service, text):
    with LOCK:
        buf = LOGS.setdefault(service, [])
        for line in str(text).rstrip().splitlines() or [""]:
            buf.append({"i": len(buf), "t": time.time(), "text": line[:2000]})
        if len(buf) > 4000:
            del buf[:1000]
            for n, item in enumerate(buf):
                item["i"] = n


def logs(service, start=0):
    with LOCK:
        buf = LOGS.get(service, [])
        return [x for x in buf if x["i"] >= start][-1500:], len(buf)


COMMON_DIRS = ["~/development/flutter/bin", "~/flutter/bin", "~/fvm/default/bin", "~/.pub-cache/bin",
               "/opt/homebrew/bin", "/usr/local/bin", "~/.local/bin", "~/Library/Android/sdk/platform-tools",
               "~/.npm-global/bin", "~/.volta/bin", "/Applications/Docker.app/Contents/Resources/bin"]


def augment_path(extra=None):
    """工作台可能不是從設定好的終端機啟動，讀不到 .zshrc 裡加的路徑（Flutter 常見）。
    啟動時向使用者的登入 shell 要一次 PATH，再補上常見安裝位置；只加存在的資料夾，不改使用者設定。"""
    if os.name == "nt":
        return []
    found = []
    shell = os.environ.get("SHELL") or "/bin/zsh"
    try:
        r = subprocess.run([shell, "-lic", 'printf "__PM_PATH__%s__END__" "$PATH"'], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15, stdin=subprocess.DEVNULL)
        m = re.search(r"__PM_PATH__(.*?)__END__", r.stdout, re.S)
        if m:
            found += m.group(1).split(":")
    except (OSError, subprocess.TimeoutExpired):
        pass
    found += [os.path.expanduser(d) for d in (extra or []) + COMMON_DIRS]
    current = os.environ.get("PATH", "").split(":")
    added = []
    for d in found:
        d = d.strip()
        if d and d not in current and d not in added and os.path.isdir(d):
            added.append(d)
    if added:
        os.environ["PATH"] = ":".join(current + added)
    return added


def which(cmd):
    return shutil.which(cmd) or next((str(p) for p in (Path("/opt/homebrew/bin") / cmd, Path("/usr/local/bin") / cmd)
                                      if p.is_file()), None)


def run(cmd, timeout=30, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


# ───────────── 環境檢查 ─────────────

_ENV = {"at": 0, "data": None}


def env_check(force=False):
    if not force and _ENV["data"] and time.time() - _ENV["at"] < 10:
        return dict(_ENV["data"], initialized=(ROOT / "supabase/config.toml").is_file(),
                    architecture=(ROOT / "ARCHITECTURE.md").is_file())
    _ENV.update(at=time.time(), data=_env_check())
    return _ENV["data"]


def _env_check():
    docker = which("docker")
    docker_ok = False
    if docker:
        code, _, _ = run([docker, "info", "--format", "{{.ServerVersion}}"], timeout=8)
        docker_ok = code == 0
    sb = which("supabase")
    sb_version = ""
    if sb:
        code, out, _ = run([sb, "--version"], timeout=8)
        sb_version = out.strip() if code == 0 else ""
    return {
        "docker": bool(docker), "docker_running": docker_ok,
        "supabase_cli": bool(sb), "supabase_version": sb_version,
        "initialized": (ROOT / "supabase/config.toml").is_file(),
        "architecture": (ROOT / "ARCHITECTURE.md").is_file(),
    }


# ───────────── Supabase 狀態 ─────────────

def _pick(d, *names):
    for n in names:
        for k, v in d.items():
            if k.upper() == n and v:
                return v
    return ""


def supabase_status(force=False):
    """回傳 {running, api, studio, mail, db, anon, service}；anon/service 只在伺服器端使用。"""
    if not force and _STATUS["data"] is not None and time.time() - _STATUS["at"] < 4:
        return _STATUS["data"]
    data = {"running": False}
    sb = which("supabase")
    if sb and (ROOT / "supabase/config.toml").is_file():
        code, out, _ = run([sb, "status", "-o", "json"], timeout=20)
        if code == 0 and "{" in out:
            try:
                raw = json.loads(out[out.index("{"):])
                data = {
                    "running": True,
                    "api": _pick(raw, "API_URL"),
                    "studio": _pick(raw, "STUDIO_URL"),
                    "mail": _pick(raw, "MAILPIT_URL", "INBUCKET_URL"),
                    "db": _pick(raw, "DB_URL"),
                    "anon": _pick(raw, "ANON_KEY", "PUBLISHABLE_KEY"),
                    "service": _pick(raw, "SERVICE_ROLE_KEY", "SECRET_KEY"),
                }
            except ValueError:
                pass
    _STATUS.update(at=time.time(), data=data)
    return data


def public_status():
    st = supabase_status()
    return {k: v for k, v in st.items() if k not in ("anon", "service", "db")}


# ───────────── 啟動／停止／重置 ─────────────

def _patch_config(project_id):
    """讓每個產品專案的本機 Supabase 用不同連接埠與容器名，同時開好幾個專案也不衝突。"""
    cfg = ROOT / "supabase/config.toml"
    text = cfg.read_text(encoding="utf-8")
    k = 1 + int(hashlib.sha256(f"{project_id}:supabase".encode()).hexdigest()[:6], 16) % 80
    offset = k * 100
    out = []
    for line in text.splitlines():
        m = re.match(r'^(\s*)(port|shadow_port|inspector_port)(\s*=\s*)(\d+)(.*)$', line)
        if m and 54000 <= int(m.group(4)) < 55000:
            line = f"{m.group(1)}{m.group(2)}{m.group(3)}{int(m.group(4)) + offset}{m.group(5)}"
        elif re.match(r'^\s*project_id\s*=', line):
            line = f'project_id = "pm-{project_id[:10]}"'
        out.append(line)
    cfg.write_text("\n".join(out) + "\n", encoding="utf-8")
    log("supabase", f"已設定本專案專用的連接埠（原預設值 +{offset}）與容器名稱 pm-{project_id[:10]}。")


def _stream(service, cmd, timeout=900):
    log(service, "$ " + " ".join(Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd)))
    try:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
    except OSError as e:
        log(service, f"無法執行：{e}")
        return -1
    deadline = time.time() + timeout
    for raw in proc.stdout:
        text = raw.decode("utf-8", "replace").rstrip()
        # 啟動輸出會印出金鑰，日誌裡遮掉
        text = re.sub(r"(eyJ[\w-]{3,}\.[\w-]+\.[\w-]+|sb_(secret|publishable)_[\w-]+)", "［金鑰已隱藏］", text)
        text = re.sub(r"(?i)((?:key|secret|password)\s*[:=]\s*)\S+", r"\1［已隱藏］", text)
        if text:
            log(service, text)
        if time.time() > deadline:
            proc.kill()
            log(service, "逾時，已中止。")
            break
    return proc.wait()


def service_action(service, action, project_id):
    if service != "supabase":
        raise ValueError("第一階段只有 Supabase")
    if BUSY.get(service):
        raise RuntimeError(f"Supabase 正在{BUSY[service]}，請稍候。")
    env = env_check(force=True)
    if not env["supabase_cli"]:
        raise RuntimeError("找不到 supabase 指令。請在終端機執行：brew install supabase/tap/supabase")
    if action in ("start", "reset") and not env["docker_running"]:
        raise RuntimeError("Docker 沒在執行。請先打開 Docker Desktop，等它顯示執行中再試。")
    sb = which("supabase")
    labels = {"start": "啟動", "stop": "停止", "reset": "重置測試資料"}

    def job():
        BUSY[service] = labels[action]
        try:
            if action == "start":
                if not (ROOT / "supabase/config.toml").is_file():
                    log(service, "第一次使用，建立 supabase/ 設定…")
                    code = _stream(service, [sb, "init"], timeout=120)
                    if code != 0:
                        log(service, "初始化失敗。")
                        return
                    _patch_config(project_id)
                log(service, "啟動中，第一次會下載映像檔，可能要好幾分鐘…")
                code = _stream(service, [sb, "start"])
                log(service, "✓ Supabase 已啟動。" if code == 0 else f"啟動失敗（代碼 {code}），看上面的訊息。")
            elif action == "stop":
                code = _stream(service, [sb, "stop"], timeout=180)
                log(service, "✓ 已停止（資料保留）。" if code == 0 else f"停止失敗（代碼 {code}）。")
            elif action == "reset":
                code = _stream(service, [sb, "db", "reset"], timeout=600)
                if code == 0:
                    _write_json(DATA / "test-accounts.json", [])
                    set_identity({"type": "anon"})
                    _TOKENS.clear()
                    log(service, "✓ 已依遷移檔與 seed.sql 重建本機資料庫；工作台建立的測試帳號已清空。")
                else:
                    log(service, f"重置失敗（代碼 {code}）。")
        finally:
            BUSY.pop(service, None)
            supabase_status(force=True)

    threading.Thread(target=job, daemon=True).start()
    return labels[action]


# ───────────── 對 Supabase 發請求 ─────────────

def _auth_headers(key):
    h = {"apikey": key}
    if key.startswith("eyJ"):
        h["Authorization"] = "Bearer " + key
    return h


def _http(method, url, headers=None, body=None, timeout=20):
    data = None
    headers = dict(headers or {})
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(400_000)
            return resp.status, dict(resp.headers), raw, int((time.time() - t0) * 1000)
    except HTTPError as e:
        return e.code, dict(e.headers or {}), e.read(400_000), int((time.time() - t0) * 1000)


def _require_running():
    st = supabase_status()
    if not st.get("running") or not st.get("api"):
        raise RuntimeError("本機 Supabase 沒在執行，先按上方的「Supabase」啟動。")
    host = urlparse(st["api"]).hostname
    if host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("Supabase 網址不是本機，為了安全拒絕連線。")
    return st


def _json(raw):
    try:
        return json.loads(raw.decode("utf-8") or "null")
    except (ValueError, UnicodeDecodeError):
        return None


# ───────────── 測試帳號與身分 ─────────────

def accounts():
    return _read_json(DATA / "test-accounts.json", [])


def identity():
    return _read_json(DATA / "dev-identity.json", {"type": "anon"})


def set_identity(ident):
    if ident.get("type") == "user":
        if not any(a["email"] == ident.get("email") for a in accounts()):
            raise ValueError("只能切換成工作台建立的測試帳號")
    elif ident.get("type") not in ("anon", "service"):
        raise ValueError("身分類型不正確")
    _write_json(DATA / "dev-identity.json", {"type": ident["type"], "email": ident.get("email", "")})
    return identity()


def list_users():
    st = _require_running()
    code, _, raw, _ = _http("GET", st["api"] + "/auth/v1/admin/users?per_page=200", _auth_headers(st["service"]))
    data = _json(raw) or {}
    users = data.get("users", data if isinstance(data, list) else [])
    mine = {a["email"] for a in accounts()}
    return [{"id": u.get("id"), "email": u.get("email") or u.get("phone") or "（無信箱）",
             "role": (u.get("user_metadata") or {}).get("role", ""),
             "confirmed": bool(u.get("email_confirmed_at") or u.get("confirmed_at")),
             "created": u.get("created_at", ""), "last_sign_in": u.get("last_sign_in_at") or "",
             "test_account": u.get("email") in mine} for u in users if isinstance(u, dict)]


def create_account(email, password, role):
    st = _require_running()
    email = (email or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError("信箱格式不正確")
    password = password or ("Test-" + secrets.token_urlsafe(6))
    body = {"email": email, "password": password, "email_confirm": True,
            "user_metadata": {"role": role} if role else {}}
    code, _, raw, _ = _http("POST", st["api"] + "/auth/v1/admin/users", _auth_headers(st["service"]), body)
    data = _json(raw) or {}
    if code >= 300:
        raise RuntimeError(data.get("msg") or data.get("message") or data.get("error_description") or f"建立失敗（{code}）")
    items = [a for a in accounts() if a["email"] != email]
    items.append({"email": email, "password": password, "role": role, "id": data.get("id"), "created": time.time()})
    _write_json(DATA / "test-accounts.json", items)
    return {"email": email, "password": password, "role": role}


def _user_token(st, email):
    tok = _TOKENS.get(email)
    if tok and tok[1] > time.time() + 30:
        return tok[0]
    acc = next((a for a in accounts() if a["email"] == email), None)
    if not acc:
        raise RuntimeError("找不到這個測試帳號")
    code, _, raw, _ = _http("POST", st["api"] + "/auth/v1/token?grant_type=password",
                            {"apikey": st["anon"]}, {"email": acc["email"], "password": acc["password"]})
    data = _json(raw) or {}
    if code >= 300 or not data.get("access_token"):
        raise RuntimeError("測試帳號登入失敗：" + str(data.get("error_description") or data.get("msg") or code))
    _TOKENS[email] = (data["access_token"], time.time() + int(data.get("expires_in") or 3600))
    return data["access_token"]


def _identity_headers(st):
    ident = identity()
    if ident["type"] == "service":
        return _auth_headers(st["service"]), "管理權限（service role）"
    if ident["type"] == "user":
        return {"apikey": st["anon"], "Authorization": "Bearer " + _user_token(st, ident["email"])}, ident["email"]
    return _auth_headers(st["anon"]), "匿名（未登入）"


# ───────────── API 測試台與函式 ─────────────

def proxy(method, path, body_text="", extra_headers=None):
    st = _require_running()
    method = (method or "GET").upper()
    if method not in ("GET", "POST", "PATCH", "PUT", "DELETE"):
        raise ValueError("不支援的方法")
    path = "/" + (path or "").lstrip("/")
    if not path.startswith(ALLOWED_PREFIXES) or ".." in path:
        raise ValueError("路徑要以 /rest/v1/、/functions/v1/、/auth/v1/ 或 /storage/v1/ 開頭")
    headers, who = _identity_headers(st)
    for k, v in (extra_headers or {}).items():
        if k.lower() not in ("apikey", "authorization", "host") and isinstance(v, str):
            headers[k] = v
    body = None
    if body_text and method != "GET":
        try:
            json.loads(body_text)
        except ValueError:
            raise ValueError("內容不是有效的 JSON")
        body = body_text.encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    code, resp_headers, raw, ms = _http(method, st["api"] + path, headers, body)
    parsed = _json(raw)
    text = json.dumps(parsed, ensure_ascii=False, indent=2) if parsed is not None else raw.decode("utf-8", "replace")
    log("api", f"{method} {path} → {code}（{ms} ms，身分：{who}）")
    keep = {k: v for k, v in resp_headers.items() if k.lower() in ("content-type", "content-range", "location", "x-request-id")}
    return {"status": code, "ms": ms, "identity": who, "headers": keep, "body": text[:200_000]}


def openapi():
    st = _require_running()
    code, _, raw, _ = _http("GET", st["api"] + "/rest/v1/", _auth_headers(st["service"]))
    doc = _json(raw) or {}
    paths = doc.get("paths", {}) if isinstance(doc, dict) else {}
    tables = sorted(p[1:] for p in paths if p.count("/") == 1 and p != "/")
    rpc = sorted(p.split("/rpc/", 1)[1] for p in paths if p.startswith("/rpc/"))
    return {"tables": tables, "rpc": rpc}


def functions():
    folder = ROOT / "supabase/functions"
    if not folder.is_dir():
        return []
    return sorted(d.name for d in folder.iterdir() if d.is_dir() and not d.name.startswith(("_", ".")))


def buckets():
    st = _require_running()
    code, _, raw, _ = _http("GET", st["api"] + "/storage/v1/bucket", _auth_headers(st["service"]))
    data = _json(raw)
    return sorted(b.get("id") or b.get("name") for b in data) if isinstance(data, list) else []


def migrations():
    folder = ROOT / "supabase/migrations"
    return sorted(f.name for f in folder.glob("*.sql")) if folder.is_dir() else []


def progress(req, read_manifest, app_screens=None):
    manifest = read_manifest(ROOT, req)
    result = {"req": req, "manifest": manifest is not None, "items": [], "migrations": migrations()}
    if manifest is None:
        return result
    running = supabase_status().get("running")
    have = {"tables": set(), "rpc": set(), "buckets": set()}
    if running:
        try:
            api = openapi()
            have["tables"], have["rpc"] = set(api["tables"]), set(api["rpc"])
            have["buckets"] = set(buckets())
        except Exception as e:
            result["error"] = str(e)
    fn = set(functions())
    labels = {"tables": "資料表", "rpc": "資料庫函式", "functions": "後端函式", "buckets": "檔案儲存",
              "app_screens": "APP 畫面", "web_admin": "管理後台頁面", "web_partner": "合作夥伴頁面", "web_site": "官網頁面"}
    for key, names in manifest.items():
        for name in names:
            if key == "functions":
                state = "done" if name in fn else "todo"
            elif key == "app_screens" and app_screens is not None:
                state = "done" if name in app_screens else "todo"
            elif key in have:
                state = ("done" if name in have[key] else "todo") if running else "unknown"
            else:
                state = "later"  # 網站：第三階段
            result["items"].append({"kind": key, "label": labels[key], "name": name, "state": state})
    result["running"] = bool(running)
    return result


def run_function(name, body_text):
    if name not in functions():
        raise ValueError("沒有這個後端函式")
    return proxy("POST", f"/functions/v1/{name}", body_text or "{}")


def state():
    env = env_check()
    st = public_status() if env["initialized"] else {"running": False}
    return {"env": env, "supabase": st, "busy": BUSY.get("supabase", ""), "identity": identity(),
            "accounts": [{"email": a["email"], "role": a.get("role", ""), "password": a.get("password", "")}
                         for a in accounts()],
            "functions": functions()}
