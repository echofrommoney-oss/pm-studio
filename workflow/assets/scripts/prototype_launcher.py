#!/usr/bin/env python3
"""按專案的按需啟動器：收到瀏覽器請求後在後台拉起匯出服務。

這是「點一鍵匯出/一鍵複製全文就自動起服務」背後的那一環。瀏覽器自己沒法啟動
程序，所以必須有個東西在 launcher_port 上應答——而那個東西就是 launchd 本身。

兩種執行形態：
  * **socket 啟用（macOS，預設）**：launchd 持有監聽套接字，本程序只在真有請求
    時被拉起，處理完空閒一會兒就自退。空閒時專案沒有任何常駐程序，連接埠卻照樣通。
    套接字由 launch_activate_socket() 交過來，所以這種形態下**不能自己 bind**。
  * **獨立執行（回退）**：手動 `python3 scripts/prototype_launcher.py` 時拿不到
    launchd 的套接字，就自己 bind launcher_port，行為與舊版一致。

與 3.0 的關鍵差別：
  * label 按專案區分（com.pm-workflow.launcher.<project_id>），一台機器可同時
    服務多個專案；3.0 用的是全域性唯一 label，後裝的會頂掉先裝的。
  * 配置按請求讀取而不是模組匯入期讀取，因此專案未初始化時不會整個程序起不來。
"""
import ctypes
import ctypes.util
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pm_launchagent  # noqa: E402
from pm_bootstrap import ensure_serving  # noqa: E402
from pm_launchagent import IDLE_EXIT_SECONDS, SOCKET_NAME  # noqa: E402
from pm_runtime import cors_response_origin, ensure_config, origin_allowed, probe_health, valid_token  # noqa: E402

PROJECT_DIR = Path(os.environ.get("PROTOTYPE_PROJECT_DIR")
                   or Path(__file__).resolve().parent.parent).resolve()


def launch(config):
    state = probe_health(config["port"])
    if state:
        if state.get("project_id") != config["project_id"]:
            raise RuntimeError("連接埠被其他專案的服務佔用")
        if state.get("read_only"):
            raise RuntimeError("當前服務為只讀模式")
        return "already-running"
    result, _config = ensure_serving(PROJECT_DIR, background=True, verbose=False)
    return "launched" if result == "launched" else str(result)


class Handler(BaseHTTPRequestHandler):
    def config(self):
        # 每次請求都重讀：連接埠可能因衝突自愈換過，token 可能被重新初始化過。
        if not hasattr(self, "_config"):
            self._config = ensure_config(PROJECT_DIR)
        return self._config

    def allowed_origin(self, config):
        origin = self.headers.get("Origin")
        return origin_allowed(origin, config["launcher_port"]) or origin in (
            f"http://127.0.0.1:{config['port']}", f"http://localhost:{config['port']}")

    def reply(self, data, code=200, config=None):
        raw = json.dumps(data).encode()
        self.send_response(code)
        origin = self.headers.get("Origin")
        if origin and config and self.allowed_origin(config):
            self.send_header("Access-Control-Allow-Origin", cors_response_origin(origin))
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-PM-Project, X-PM-Token")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        try:
            config = self.config()
        except Exception:
            self.reply({}, 403)
            return
        self.reply({}, 200 if self.allowed_origin(config) else 403, config)

    def do_POST(self):
        try:
            config = self.config()
        except Exception as error:
            self.reply({"error": str(error)}, 400)
            return
        if (self.path != "/api/launch" or not self.allowed_origin(config)
                or not valid_token(self.headers, config)):
            self.reply({"error": "專案身份校驗失敗"}, 403, config)
            return
        try:
            self.reply({"ok": True, "status": launch(config),
                        "project_id": config["project_id"]}, 200, config)
        except Exception as error:
            self.reply({"error": str(error)}, 400, config)

    def log_message(self, fmt, *args):  # 降噪：常駐程序不需要逐條 access log
        pass


def launchd_socket(name=SOCKET_NAME):
    """取 launchd 交過來的監聽套接字 fd；不在 launchd 下執行時返回 None。

    非 launchd 環境下 launch_activate_socket 返回 ESRCH(3)，屬於預期情況，
    不是錯誤——呼叫方據此回退到自己 bind。
    """
    try:
        lib = ctypes.CDLL(ctypes.util.find_library("System") or "/usr/lib/libSystem.dylib")
        fn = lib.launch_activate_socket
    except (OSError, AttributeError):
        return None  # 非 macOS，或系統不提供該符號
    fn.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_int)),
                   ctypes.POINTER(ctypes.c_size_t)]
    fn.restype = ctypes.c_int
    fds = ctypes.POINTER(ctypes.c_int)()
    count = ctypes.c_size_t(0)
    if fn(name.encode(), ctypes.byref(fds), ctypes.byref(count)) != 0 or count.value < 1:
        return None
    return fds[0]


class InheritedServer(HTTPServer):
    """用 launchd 已建好的套接字，跳過 bind/listen。

    自己 bind 會直接撞 EADDRINUSE——那個連接埠正被 launchd 佔著。
    """

    def __init__(self, fd, handler):
        super().__init__(("127.0.0.1", 0), handler, bind_and_activate=False)
        self.socket.close()
        # dup 一份：原 fd 的所有權在 launchd 那邊，不該被 Python 的 GC 關掉。
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, fileno=os.dup(fd))
        self.server_address = self.socket.getsockname()


if __name__ == "__main__":
    try:
        CONFIG = ensure_config(PROJECT_DIR)
    except Exception as error:
        print(f"啟動器無法讀取專案配置，已退出：{error}", file=sys.stderr)
        sys.exit(0)  # 不用非 0 退出，否則 launchd 的 KeepAlive 會無限重啟

    INHERITED = launchd_socket()
    if INHERITED is None:
        # 獨立執行：自己 bind，長駐不自退（使用者是手動起的，退了會讓人意外）
        HTTPServer(("127.0.0.1", int(CONFIG["launcher_port"])), Handler).serve_forever()
    else:
        # 本程序就是那個 launchd job：任何路徑都不許再去重新註冊它（會自殺，詳見
        # pm_launchagent.IN_LAUNCHD_JOB）。必須趕在起服務之前置上。
        pm_launchagent.IN_LAUNCHD_JOB = True
        SERVER = InheritedServer(INHERITED, Handler)
        # 空閒即退，這樣「零常駐」才成立；下次請求由 launchd 再拉起。
        SERVER.timeout = IDLE_EXIT_SECONDS
        SERVER.handle_timeout = lambda: sys.exit(0)
        while True:
            SERVER.handle_request()
