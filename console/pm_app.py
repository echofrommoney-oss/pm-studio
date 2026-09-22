"""PM 工作台 · APP（第二階段：Flutter）。

由 pm_console.py 載入。用 `flutter run --machine`（IDE 接 Flutter 的同一種方式）執行 APP：
  · web：網頁版，嵌在右欄的手機外框裡
  · device：Android 模擬器／iOS 模擬器／實機
熱重載、重新啟動、停止都透過機器模式的 JSON 指令，比模擬鍵盤可靠。
Supabase 網址會依執行目標自動調整（Android 模擬器要用 10.0.2.2 才連得到你的電腦）。
"""
import hashlib
import json
import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path

import pm_dev

ROOT = None
DATA = None
PID = ""
RUNS = {}          # "web" / "device" -> FlutterRun
_DEVTOOLS = {"proc": None, "url": ""}
SCREEN_MARK = re.compile(r"//\s*pm-screen:\s*([\w\-/\[\]]+)")
DEVTOOLS_URL = re.compile(r"(https?://(?:127\.0\.0\.1|localhost):\d+/\S*devtools/\?uri=\S+)")


def init(root, data, project_id=""):
    global ROOT, DATA, PID
    ROOT, DATA, PID = Path(root), Path(data), project_id


def flutter_service():
    import pm_services
    return next((s for s in pm_services.services(PID) if s["adapter"] == "flutter"), None)


def app_dir():
    svc = flutter_service()
    return ROOT / (svc["dir"] if svc and svc["dir"] else "app")


def has_app():
    return (app_dir() / "pubspec.yaml").is_file()


def flutter():
    return pm_dev.which("flutter")


def web_port(project_id):
    return 21000 + int(hashlib.sha256(f"{project_id}:flutter-web".encode()).hexdigest()[:6], 16) % 9000


# ───────────── 裝置 ─────────────

def devices():
    """已連線的裝置與可啟動的模擬器。"""
    fl = flutter()
    if not fl:
        return {"devices": [], "emulators": []}
    code, out, _ = pm_dev.run([fl, "devices", "--machine"], timeout=40)
    devs = []
    if code == 0 and "[" in out:
        try:
            for d in json.loads(out[out.index("["):]):
                plat = d.get("targetPlatform", "")
                if plat.startswith(("android", "ios")):
                    devs.append({"id": d.get("id"), "name": d.get("name"), "platform": "android" if plat.startswith("android") else "ios",
                                 "emulator": bool(d.get("emulator"))})
        except ValueError:
            pass
    emus = []
    code, out, _ = pm_dev.run([fl, "emulators"], timeout=40)
    for line in out.splitlines():
        parts = [p.strip() for p in line.split("•")]
        if len(parts) >= 4 and parts[0] and parts[0] != "Id":
            emus.append({"id": parts[0], "name": parts[1], "platform": parts[3].lower()})
    return {"devices": devs, "emulators": emus}


def launch_emulator(emu_id, timeout=240):
    fl = flutter()
    before = {d["id"] for d in devices()["devices"]}
    pm_dev.log("app", f"啟動模擬器 {emu_id}…（第一次開機要一兩分鐘）")
    subprocess.Popen([fl, "emulators", "--launch", emu_id], cwd=str(ROOT), stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(4)
        for d in devices()["devices"]:
            if d["emulator"] and d["id"] not in before:
                pm_dev.log("app", f"模擬器已就緒：{d['name']}（{d['id']}）")
                return d
    raise RuntimeError("模擬器沒有在時間內開好。可以先手動打開它，再選擇已開啟的裝置。")


# ───────────── 設定：後端網址 ─────────────

def write_defines(target):
    """依執行目標寫後端設定，給 --dart-define-from-file 用；檔案在 <APP 資料夾>/.pm/（不進 git）。
    Android 模擬器連不到 127.0.0.1，網址會自動換成 10.0.2.2。"""
    import pm_services
    v = pm_services.variables(PID, "android" if target == "android" else "")
    folder = app_dir() / ".pm"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"defines-{target}.json"
    data = {"SUPABASE_URL": v.get("SUPABASE_URL", ""), "SUPABASE_ANON_KEY": v.get("SUPABASE_ANON_KEY", ""),
            "BACKEND_URL": v.get("BACKEND_URL", ""), "API_URL": v.get("API_URL", ""), "APP_ENV": "local"}
    svc = flutter_service()
    for k, tmpl in ((svc or {}).get("env") or {}).items():   # ARCHITECTURE.md 為 APP 設定的變數，例如 API_BASE_URL
        data[str(k)] = pm_services.render(tmpl, v)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    gi = folder / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n", encoding="utf-8")
    if not data["BACKEND_URL"]:
        pm_dev.log("app", "⚠️ 沒有執行中的後端，APP 會拿不到後端網址；需要資料時先啟動後端再按重新啟動。")
    return path


# ───────────── flutter run --machine ─────────────

class FlutterRun:
    def __init__(self, kind, label):
        self.kind, self.label = kind, label
        self.proc = None
        self.app_id = None
        self.url = ""          # web：網頁網址
        self.ws = ""           # VM service，DevTools 用
        self.devtools = ""     # Flutter 自帶的 DevTools 網址（新版會印在輸出裡）
        self.state = "starting"
        self.device_id = ""
        self.platform = ""
        self._req = 0
        self._lock = threading.Lock()

    def send(self, method, params):
        with self._lock:
            self._req += 1
            msg = json.dumps([{"id": self._req, "method": method, "params": params}]) + "\n"
            try:
                self.proc.stdin.write(msg.encode("utf-8"))
                self.proc.stdin.flush()
            except (OSError, AttributeError):
                raise RuntimeError("APP 已經停止")

    def _read(self):
        svc = "app-" + self.kind
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").rstrip()
            if not line:
                continue
            if line.startswith("[{"):
                try:
                    events = json.loads(line)
                except ValueError:
                    pm_dev.log(svc, line)
                    continue
                for ev in events:
                    self._event(svc, ev)
            else:
                pm_dev.log(svc, line)
                self._devtools(line)
        code = self.proc.wait()
        self.state = "stopped"
        pm_dev.log(svc, f"APP 已結束（代碼 {code}）。")

    def _event(self, svc, ev):
        name, p = ev.get("event"), ev.get("params") or {}
        if name == "app.start":
            self.app_id = p.get("appId")
            self.device_id = p.get("deviceId", self.device_id)
        elif name == "app.webLaunchUrl":
            self.url = p.get("url", "")
        elif name == "app.debugPort":
            self.ws = p.get("wsUri", "")
        elif name == "app.started":
            self.state = "running"
            pm_dev.log(svc, "✓ APP 已啟動" + (f"：{self.url}" if self.url else "") + "。")
        elif name == "app.log":
            pm_dev.log(svc, p.get("log", ""))
            self._devtools(p.get("log", ""))
        elif name == "daemon.logMessage":
            pm_dev.log(svc, p.get("message", ""))
            self._devtools(p.get("message", ""))
        elif name == "app.progress" and p.get("message"):
            pm_dev.log(svc, p["message"])
        elif name == "app.stop":
            self.state = "stopped"
        elif "error" in ev:
            pm_dev.log(svc, "指令失敗：" + str(ev.get("error"))[:300])

    def _devtools(self, text):
        m = DEVTOOLS_URL.search(text or "")
        if m and not self.devtools:
            self.devtools = m.group(1)

    def start(self, args):
        cmd = [flutter(), "run", "--machine"] + args
        pm_dev.log("app-" + self.kind, "$ flutter " + " ".join(cmd[1:]))
        kwargs = {"cwd": str(app_dir()), "stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
                  "stderr": subprocess.STDOUT}
        if os.name != "nt":
            kwargs["start_new_session"] = True
        self.proc = subprocess.Popen(cmd, **kwargs)
        threading.Thread(target=self._read, daemon=True).start()

    def reload(self, full=False):
        if not self.app_id or self.state != "running":
            raise RuntimeError("APP 還沒啟動完成")
        self.send("app.restart", {"appId": self.app_id, "fullRestart": bool(full), "pause": False,
                                  "reason": "manual"})
        pm_dev.log("app-" + self.kind, "↻ " + ("重新啟動" if full else "熱重載"))

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                if self.app_id:
                    self.send("app.stop", {"appId": self.app_id})
                    self.proc.wait(timeout=8)
            except Exception:
                pass
            if self.proc.poll() is None:
                try:
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM) if os.name != "nt" else self.proc.kill()
                except OSError:
                    pass
        self.state = "stopped"


def _target_args():
    svc = flutter_service() or {}
    target = str(svc.get("target") or "").strip()
    return ["-t", target] if target else []


def start(kind, project_id, device=None):
    if not flutter():
        raise RuntimeError("找不到 flutter 指令，請先安裝 Flutter SDK。")
    if not has_app():
        raise RuntimeError(f"還沒有 Flutter 專案。先選「開發」→「APP」讓 Claude 建立 {app_dir().relative_to(ROOT).as_posix()}/。")
    cur = RUNS.get(kind)
    if cur and cur.state in ("starting", "running"):
        raise RuntimeError("已經在執行了")
    if kind == "web":
        run = FlutterRun("web", "網頁預覽")
        run.platform = "web"
        defines = write_defines("web")
        run.start(["-d", "web-server", "--web-hostname", "127.0.0.1", "--web-port", str(web_port(project_id)),
                   f"--dart-define-from-file={defines}"] + _target_args())
        RUNS["web"] = run
        return run
    # 裝置：可以是已開啟的裝置，或要先啟動的模擬器
    run = FlutterRun("device", "裝置")
    RUNS["device"] = run

    def job():
        try:
            target = device or {}
            if target.get("type") == "emulator":
                d = launch_emulator(target["id"])
            else:
                d = next((x for x in devices()["devices"] if x["id"] == target.get("id")), None)
                if not d:
                    raise RuntimeError("找不到這個裝置，重新整理清單再試。")
            run.device_id, run.platform, run.label = d["id"], d["platform"], d["name"]
            defines = write_defines(d["platform"])
            run.start(["-d", d["id"], f"--dart-define-from-file={defines}"] + _target_args())
        except Exception as e:
            run.state = "stopped"
            pm_dev.log("app-device", f"啟動失敗：{e}")

    threading.Thread(target=job, daemon=True).start()
    return run


def stop(kind):
    run = RUNS.get(kind)
    if run:
        run.stop()


def stop_all():
    for run in list(RUNS.values()):
        run.stop()
    p = _DEVTOOLS.get("proc")
    if p and p.poll() is None:
        p.terminate()


def reload(full):
    done = 0
    for run in RUNS.values():
        if run.state == "running":
            try:
                run.reload(full)
                done += 1
            except RuntimeError:
                pass
    if not done:
        raise RuntimeError("沒有執行中的 APP")
    return done


# ───────────── 截圖與 DevTools ─────────────

def _adb():
    found = pm_dev.which("adb")
    if found:
        return found
    cands = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"), str(Path.home() / "Library/Android/sdk")]
    fl = flutter()
    if fl:
        code, out, _ = pm_dev.run([fl, "config", "--machine"], timeout=30)
        if code == 0 and "{" in out:
            try:
                cands.insert(0, json.loads(out[out.index("{"):]).get("android-sdk"))
            except ValueError:
                pass
    for c in cands:
        if c and (Path(c) / "platform-tools/adb").is_file():
            return str(Path(c) / "platform-tools/adb")
    return None


def screenshot():
    run = RUNS.get("device")
    if not run or run.state not in ("starting", "running") or not run.device_id:
        raise RuntimeError("裝置上沒有執行中的 APP")
    if run.platform == "android":
        adb = _adb()
        if not adb:
            raise RuntimeError("找不到 adb")
        r = subprocess.run([adb, "-s", run.device_id, "exec-out", "screencap", "-p"], capture_output=True, timeout=20)
        if r.returncode != 0 or not r.stdout.startswith(b"\x89PNG"):
            raise RuntimeError("截圖失敗")
        return r.stdout
    if run.platform == "ios":
        out = DATA / "tmp" / "ios-shot.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["xcrun", "simctl", "io", run.device_id, "screenshot", str(out)], capture_output=True, timeout=20)
        if r.returncode != 0:
            raise RuntimeError("截圖失敗（實機不支援，只有 iOS 模擬器可以）")
        return out.read_bytes()
    raise RuntimeError("這個裝置不支援截圖")


def devtools_url():
    ready = [r for r in RUNS.values() if r.state == "running"]
    own = next((r.devtools for r in ready if r.devtools), "")
    if own:   # 新版 Flutter 自帶 DevTools，直接用它印出的網址
        return own
    run = next((r for r in ready if r.ws), None)
    if not run:
        raise RuntimeError("先啟動 APP，DevTools 才有東西可以看。")
    p = _DEVTOOLS.get("proc")
    if not p or p.poll() is not None:
        dart = pm_dev.which("dart")
        if not dart:
            raise RuntimeError("找不到 dart 指令（Flutter SDK 內附，確認 flutter/bin 在 PATH）")
        proc = subprocess.Popen([dart, "devtools", "--no-launch-browser", "--machine"], cwd=str(ROOT),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True)
        _DEVTOOLS.update(proc=proc, url="")

        def read():
            for raw in proc.stdout:
                line = raw.decode("utf-8", "replace").strip()
                m = re.search(r"https?://127\.0\.0\.1:\d+", line) or re.search(r"https?://localhost:\d+", line)
                if m and not _DEVTOOLS["url"]:
                    _DEVTOOLS["url"] = m.group(0)
        threading.Thread(target=read, daemon=True).start()
    deadline = time.time() + 30
    while not _DEVTOOLS["url"] and time.time() < deadline:
        time.sleep(0.3)
    if not _DEVTOOLS["url"]:
        raise RuntimeError("DevTools 沒有啟動成功")
    from urllib.parse import quote
    return f"{_DEVTOOLS['url']}/?uri={quote(run.ws, safe='')}"


# ───────────── 進度與狀態 ─────────────

def screens():
    """掃描 app/lib 裡的 `// pm-screen: 代號` 標記。"""
    lib = app_dir() / "lib"
    found = {}
    if lib.is_dir():
        for f in lib.rglob("*.dart"):
            try:
                for m in SCREEN_MARK.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                    found.setdefault(m.group(1), f.relative_to(ROOT).as_posix())
            except OSError:
                pass
    return found


def env():
    fl = flutter()
    version = ""
    if fl:
        code, out, err = pm_dev.run([fl, "--version", "--machine"], timeout=60)
        if code == 0 and "{" in out:
            try:
                version = json.loads(out[out.index("{"):]).get("frameworkVersion", "")
            except ValueError:
                pass
    return {"flutter": bool(fl), "version": version, "app": has_app(),
            "xcode": pm_dev.which("xcodebuild") is not None and pm_dev.run(["xcodebuild", "-version"], timeout=15)[0] == 0}


_ENV = {"at": 0, "data": None}


def state(force=False):
    if force or not _ENV["data"] or time.time() - _ENV["at"] > 60:
        _ENV.update(at=time.time(), data=env())
    e = dict(_ENV["data"], app=has_app())
    runs = {k: {"state": r.state, "label": r.label, "url": r.url, "platform": r.platform,
                "device_id": r.device_id, "devtools": bool(r.ws)} for k, r in RUNS.items()}
    return {"env": e, "runs": runs}
