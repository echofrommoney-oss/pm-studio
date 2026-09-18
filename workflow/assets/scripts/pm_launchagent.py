#!/usr/bin/env python3
"""macOS 按需啟動器的 LaunchAgent 註冊（socket 啟用版）。

為什麼不用 RunAtLoad + KeepAlive
--------------------------------
上一版裝的是一個真常駐程序：開機就起、退出就重拉，每個專案一個。給自己用尚可，
但這個 skill 是要分享出去的——在別人機器上悄悄留下常駐程序是不合適的，所以當初
把它設成了「預設不裝」。結果是**自動啟動這條鏈路等於沒有**：瀏覽器點匯出時
去叫 launcher_port，那兒沒人應答，於是永遠彈「請雙擊啟動腳本」。

socket 啟用解決的正是這個兩難。plist 裡只給 Sockets，不給 RunAtLoad、不給
KeepAlive：**連接埠由 launchd 自己持有**。空閒時本專案沒有任何程序在跑，但連接埠照樣
是通的；瀏覽器一連上來，launchd 才把 prototype_launcher.py 拉起來，它起完服務就
自退。既是自動啟動，又沒有常駐程序，所以可以預設裝。

plist 裡寫死了連接埠，而連接埠是會自愈的（bind 衝突時換一對），所以 sync() 必須在
連接埠變化後被呼叫，否則 launchd 會守著一個沒人用的舊連接埠。
"""
import os
import plistlib
import subprocess
import sys
from pathlib import Path

SOCKET_NAME = "Listeners"
# 空閒多久自退。給足冗餘吸收客戶端重試（它啟動後會輪詢健康檢查最多 45s），
# 又短到「用完即走」仍然成立。
IDLE_EXIT_SECONDS = 120

# 由 prototype_launcher 在 socket 啟用分支裡置 True。
# 重新註冊要先 launchctl bootout，而 bootout 會殺掉這個 job 的程序——如果那正是
# 當前程序，就等於自殺：請求得不到回應，註冊也留在半路（bootout 成功、bootstrap
# 沒跑成），「點匯出自動起服務」從此徹底失效，只能手動重灌。實測過一次，故有此標誌。
IN_LAUNCHD_JOB = False


def supported():
    return sys.platform == "darwin"


def label(config):
    # 按專案區分：3.0 用全域性唯一 label，一台機器只能服務一個專案，後裝的頂掉先裝的。
    return "com.pm-workflow.launcher." + config["project_id"]


def plist_path(config):
    return Path.home() / "Library/LaunchAgents" / (label(config) + ".plist")


def _domain():
    return "gui/" + str(os.getuid())


def _interpreter(explicit=None):
    """選一個寫進 plist 的直譯器路徑。

    不能用共享 venv 裡的那個：venv 會被 --install 重建，路徑失效後 launchd 只會
    反覆拉起失敗。挑系統級的 python3。
    """
    if explicit:
        return str(explicit)
    exe = Path(sys.executable)
    in_venv = (exe.parent.parent / "pyvenv.cfg").is_file() or "pm-workflow" in exe.parts
    if in_venv:
        for candidate in ("/opt/homebrew/bin/python3", "/usr/local/bin/python3",
                          "/usr/bin/python3"):
            if Path(candidate).is_file():
                return candidate
    return str(exe)


def registered_port(config):
    """plist 裡當前登記的連接埠；未註冊返回 None。"""
    path = plist_path(config)
    if not path.is_file():
        return None
    try:
        data = plistlib.loads(path.read_bytes())
        sock = (data.get("Sockets") or {}).get(SOCKET_NAME) or {}
        return int(sock.get("SockServiceName"))
    except (OSError, ValueError, TypeError, KeyError):
        return None


def installed(config):
    return plist_path(config).is_file()


def install(root, config, python=None):
    """寫 plist 並註冊。返回 (ok, 說明文字)。"""
    if not supported():
        return False, "常駐啟動器只支援 macOS"
    root = Path(root).resolve()
    launcher = root / "scripts/prototype_launcher.py"
    if not launcher.is_file():
        return False, f"找不到 {launcher}"

    path = plist_path(config)
    logs = Path.home() / "Library/Logs/pm-workflow" / config["project_id"]
    try:
        logs.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    settings = {
        "Label": label(config),
        # 直接指向專案裡的腳本，不復制副本：副本在 skill 升級後不會同步，
        # 會變成一份悄悄跑著的舊程式碼。
        "ProgramArguments": [_interpreter(python), str(launcher)],
        "EnvironmentVariables": {
            "PROTOTYPE_PROJECT_DIR": str(root),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
        },
        # 沒有 RunAtLoad、沒有 KeepAlive：完全靠下面這個套接字按需拉起。
        "Sockets": {
            SOCKET_NAME: {
                "SockNodeName": "127.0.0.1",
                "SockServiceName": str(config["launcher_port"]),
                "SockType": "stream",
                "SockFamily": "IPv4",
            }
        },
        # 無 KeepAlive 時不存在崩潰自旋的風險，所以把節流壓到最低，
        # 保證連續兩次點匯出都能立刻被拉起。
        "ThrottleInterval": 1,
        "StandardOutPath": str(logs / "launcher.log"),
        "StandardErrorPath": str(logs / "launcher-error.log"),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(plistlib.dumps(settings))
    except OSError as error:
        return False, f"寫 plist 失敗：{error}"

    subprocess.run(["launchctl", "bootout", _domain(), str(path)], capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", _domain(), str(path)],
                            capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[:200]
        return False, f"launchctl bootstrap 失敗：{detail}"
    return True, f"{label(config)} 連接埠 {config['launcher_port']}"


def uninstall(config):
    if not supported():
        return False, "常駐啟動器只支援 macOS"
    path = plist_path(config)
    subprocess.run(["launchctl", "bootout", _domain(), str(path)], capture_output=True)
    try:
        if path.is_file():
            path.unlink()
    except OSError as error:
        return False, f"刪除 plist 失敗：{error}"
    return True, label(config)


def sync(root, config, python=None):
    """連接埠變化後把註冊對齊。**從不主動安裝**——沒註冊過就什麼都不做。

    正常情況下不該被觸發：啟動器連接埠已改成不隨 salt 漂移（見 derive_ports）。
    留著是為了兜住歷史配置——3.2 之前重抽過連接埠的專案，升級後登記連接埠可能對不上。
    """
    if not supported() or not installed(config) or IN_LAUNCHD_JOB:
        return None
    if registered_port(config) == int(config["launcher_port"]):
        return None
    ok, detail = install(root, config, python=python)
    return ok, detail


def running_pid(config):
    """當前是否有啟動器程序在跑，問 launchd 而不是探連接埠。

    探連接埠會**觸發**一次 socket 啟用——即把要觀測的程序親手拉起來，然後
    報告「它在跑」。而且啟動器只認 POST /api/launch，沒有健康檢查介面。
    """
    if not supported():
        return None
    result = subprocess.run(["launchctl", "list", label(config)],
                            capture_output=True, text=True)
    if result.returncode:
        return None
    for line in result.stdout.splitlines():
        if '"PID"' in line:
            digits = "".join(ch for ch in line.split("=")[-1] if ch.isdigit())
            return int(digits) if digits else None
    return None


def status(config):
    """給 --doctor 用：(已註冊?, 登記連接埠, 連接埠是否與配置一致, 當前 PID)"""
    if not supported():
        return False, None, True, None
    port = registered_port(config)
    return (installed(config), port, port == int(config["launcher_port"]),
            running_pid(config))
