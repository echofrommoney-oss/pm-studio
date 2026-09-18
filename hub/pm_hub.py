#!/usr/bin/env python3
"""專案總覽：一頁看所有產品專案的需求進度、待同步文件，並從這裡開啟各專案的工作台。

  python3 hub/pm_hub.py --open

只綁 127.0.0.1。專案清單在 ~/.pm-studio/projects.json（安裝器與工作台啟動時自動登記）。
"""
import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
for cand in (HERE, HERE.parent / "workflow/assets/scripts"):
    if (cand / "pm_sync.py").is_file():
        sys.path.insert(0, str(cand))
        break
import pm_sync  # noqa: E402

HOME = Path(os.environ.get("PM_STUDIO_HOME") or (Path.home() / ".pm-studio"))
REGISTRY = HOME / "projects.json"
UI_FILE = HERE / "pm_hub.html"
PIPELINE = [("demand", "挖掘"), ("prd", "PRD"), ("proto", "原型"), ("validate", "驗證"),
            ("spec", "Spec"), ("accept", "驗收"), ("launch", "上線")]
PORT = 0
TOKEN = ""


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def registry():
    data = read_json(REGISTRY, {"projects": []})
    if not isinstance(data, dict) or not isinstance(data.get("projects"), list):
        data = {"projects": []}
    return data


def project_id(root):
    rt = read_json(root / ".pm-workflow/runtime.json", {})
    return rt.get("project_id") or hashlib.sha256(str(root).encode()).hexdigest()[:16]


def hue(pid):
    return int(hashlib.sha256(f"{pid}:hue".encode()).hexdigest()[:4], 16) % 360


def console_url(root):
    rt = read_json(root / ".pm-console/runtime.json", {})
    port = rt.get("port")
    if not port:
        return None
    try:
        req = Request(f"http://127.0.0.1:{port}/api/state", headers={"Host": f"127.0.0.1:{port}"})
        with urlopen(req, timeout=0.8) as resp:
            if resp.status == 200:
                return f"http://127.0.0.1:{port}/"
    except Exception:
        pass
    return None


def project_info(path):
    root = Path(path)
    if not root.is_dir():
        return {"path": str(root), "missing": True, "name": root.name}
    cfg = read_json(root / ".pm-console/config.json", {})
    pid = project_id(root)
    reqs = []
    latest = 0.0
    for name in pm_sync.requirements(root):
        st = pm_sync.status(root, name)
        present = [code for code, _ in PIPELINE if st["stages"].get(code, {}).get("files")]
        mt = max([v["mtime"] for v in st["stages"].values() if v.get("mtime")] or [(root / name).stat().st_mtime])
        latest = max(latest, mt)
        reqs.append({"name": name, "present": present, "stale": st["stale"], "updated": mt})
    reqs.sort(key=lambda r: r["updated"], reverse=True)
    return {
        "path": str(root), "name": cfg.get("project_name") or root.name, "hue": hue(pid),
        "has_product": (root / "PRODUCT.md").is_file(), "has_design": (root / "DESIGN.md").is_file(),
        "has_console": (root / "scripts/pm_console.py").is_file(),
        "console": console_url(root), "reqs": reqs, "updated": latest or root.stat().st_mtime,
        "stale": sum(len(r["stale"]) for r in reqs),
        "uncommitted": pm_sync.uncommitted(root),
    }


def launch_console(root):
    url = console_url(root)
    if url:
        return url
    script = root / "scripts/pm_console.py"
    if not script.is_file():
        raise RuntimeError("這個專案沒有安裝工作台，先執行 install.py。")
    log = open(root / ".pm-console/launch.log", "ab") if (root / ".pm-console").is_dir() else subprocess.DEVNULL
    kwargs = {"cwd": str(root), "stdin": subprocess.DEVNULL, "stdout": log, "stderr": log}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, str(script)], **kwargs)
    deadline = time.time() + 10
    while time.time() < deadline:
        time.sleep(0.4)
        url = console_url(root)
        if url:
            return url
    raise RuntimeError("工作台沒有在 10 秒內啟動，請看專案裡的 .pm-console/launch.log。")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_ok(self):
        return self.headers.get("Host", "") in {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}

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

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "host"})
        path = urlparse(self.path).path
        if path == "/":
            html = UI_FILE.read_text(encoding="utf-8").replace(
                "/*__BOOT__*/null", json.dumps({"token": TOKEN, "pipeline": PIPELINE}, ensure_ascii=False))
            return self._send(200, html, "text/html; charset=utf-8", {
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                                           "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"})
        if path == "/api/projects":
            items = [project_info(p["path"]) for p in registry()["projects"] if isinstance(p, dict) and p.get("path")]
            items.sort(key=lambda x: (x.get("missing", False), -(x.get("updated") or 0)))
            return self._send(200, {"projects": items})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not (self._host_ok() and origin in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}")
                and secrets.compare_digest(self.headers.get("X-Hub-Token", ""), TOKEN)):
            return self._send(403, {"error": "請從總覽頁面操作"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            return self._send(400, {"error": "格式錯誤"})
        path = urlparse(self.path).path
        known = [p.get("path") for p in registry()["projects"] if isinstance(p, dict)]
        target = str(Path(str(body.get("path", ""))).expanduser().resolve()) if body.get("path") else ""
        if path == "/api/open":
            if target not in known:
                return self._send(400, {"error": "不在清單裡的專案"})
            try:
                return self._send(200, {"url": launch_console(Path(target))})
            except (RuntimeError, OSError) as e:
                return self._send(500, {"error": str(e)})
        if path == "/api/add":
            root = Path(target)
            if not root.is_dir() or not (root / ".pm-workflow").is_dir():
                return self._send(400, {"error": "這個資料夾不是已安裝工作流的專案（找不到 .pm-workflow/）。"})
            if target not in known:
                data = registry()
                data["projects"].append({"path": target, "added": time.time()})
                write_json(REGISTRY, data)
            return self._send(200, {"ok": True})
        if path == "/api/remove":
            data = registry()
            data["projects"] = [p for p in data["projects"] if not (isinstance(p, dict) and p.get("path") == target)]
            write_json(REGISTRY, data)
            return self._send(200, {"ok": True})
        return self._send(404, {"error": "not found"})


def main():
    global PORT, TOKEN
    ap = argparse.ArgumentParser(description="PM 專案總覽")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    TOKEN = secrets.token_urlsafe(24)
    server = None
    for salt in range(8):
        seed = hashlib.sha256(f"pm-studio-hub:{salt}".encode()).digest()
        PORT = args.port or 20000 + int.from_bytes(seed[:4], "big") % 12767
        try:
            server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
            break
        except OSError:
            if args.port:
                raise SystemExit(f"連接埠 {PORT} 已被占用")
    if server is None:
        raise SystemExit("找不到可用的連接埠")
    server.daemon_threads = True
    url = f"http://127.0.0.1:{PORT}/"
    print(f"\n  PM 專案總覽\n  {url}\n  關閉這個視窗就會停止總覽（各專案的工作台不受影響）。\n")
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
