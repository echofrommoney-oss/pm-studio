#!/usr/bin/env python3
"""把「確保服務可用」收斂成唯一程式碼路徑，供 mac .command / Windows .bat / 後台 launcher 共用。

對外只有四個入口：
  ensure_config(root)                      讀不到配置就建立（在 pm_runtime 裡）
  ensure_runtime(...)   -> (python, engine)  共享 venv + 瀏覽器引擎，冪等
  ensure_serving(root, ...)                 前台佔用當前視窗 / 後台脫離終端機
  doctor(root)                              一次列印全部環境事實，用於遠端排查

跨平台注意點（都是踩過的）：
  * Windows 沒有 python3 命令；py -3 是官方啟動器，但微軟商店的 alias stub 會
    開啟商店且不可靠地返回 0，所以直譯器探測只認正向哨兵輸出，不看退出碼。
  * 不用 os.execve：Windows 上它是 CreateProcess + 父程序立即退出，會讓 .bat
    視窗一閃即關，也讓 launcher 的 poll() 判活永久失效。改成顯式兩段式 spawn。
  * 子程序一律強制 UTF-8：服務端列印中文橫幅，stdout 被重定向到日誌檔案後
    Python 會改用 locale 編碼，英文區 Windows 是 cp1252，啟動即 UnicodeEncodeError。
  * venv 放使用者目錄而非專案目錄：專案常在 OneDrive/iCloud 裡，會引發同步風暴、
    os.replace 的 PermissionError，以及 Windows MAX_PATH 260 超限。
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pm_runtime import (VERSION, atomic_write, ensure_config, probe_health,  # noqa: E402
                        reroll_ports)

PLAYWRIGHT_VERSION = os.environ.get("PM_PLAYWRIGHT_VERSION", "1.60.0")
MIN_PYTHON = (3, 9)
SENTINEL = "PMPY-OK"
_PROBE = "import sys;print('{}',sys.version_info[0],sys.version_info[1])".format(SENTINEL)
# 引擎優先順序：優先沿用系統已裝的瀏覽器（零下載），都沒有才回落 Playwright 自帶 Chromium。
# None 代表自帶 Chromium。Windows 上 Edge 是系統自帶，命中率最高。
_ENGINE_ORDER = {"nt": ["msedge", "chrome", None], "darwin": ["chrome", "msedge", None]}
_ENGINE_PROBE = """
import sys
from playwright.sync_api import sync_playwright
channel = sys.argv[1] or None
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=channel) if channel \\
        else p.chromium.launch(headless=True)
    browser.close()
print("PMENGINE-OK")
"""


# ---------------------------------------------------------------- 共享目錄

def shared_dir():
    """跨專案共享的執行時目錄——裡面沒有任何專案相關內容。"""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    return Path(base) / "pm-workflow"


def venv_dir():
    return shared_dir() / "venv"


def venv_python():
    sub = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    return venv_dir() / sub


def _state_path():
    return shared_dir() / "state.json"


def read_state():
    """引擎/版本等與機器繫結、與專案無關的事實，跟著共享 venv 一起存。"""
    try:
        state = json.loads(_state_path().read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(**updates):
    state = read_state()
    state.update(updates)
    atomic_write(_state_path(), json.dumps(state, ensure_ascii=False, indent=2))
    return state


def launch_engine():
    """服務端截圖時用的 channel；None 表示 Playwright 自帶 Chromium。"""
    return read_state().get("engine") or None


# ---------------------------------------------------------------- 直譯器

def _probe_interpreter(command):
    """只認正向哨兵輸出：商店 stub 會返回 0 但不列印任何東西。"""
    try:
        result = subprocess.run(list(command) + ["-c", _PROBE],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in (result.stdout or "").splitlines():
        parts = line.strip().split()
        if len(parts) == 3 and parts[0] == SENTINEL:
            try:
                version = (int(parts[1]), int(parts[2]))
            except ValueError:
                continue
            if version >= MIN_PYTHON:
                return list(command), version
    return None


def interpreter_candidates():
    if os.name == "nt":
        return [["py", "-3"], ["python"], ["python3"]]
    return [["python3"], ["python"]]


def find_python(include_self=True):
    """返回 (命令列表, 版本元組)；找不到返回 None。"""
    if include_self:
        found = _probe_interpreter([sys.executable])
        if found:
            return found
    for candidate in interpreter_candidates():
        found = _probe_interpreter(candidate)
        if found:
            return found
    return None


# ---------------------------------------------------------------- 子程序環境

def child_env(**extra):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # stdout 重定向進 service.log 後會變成塊緩衝（~8KB），程序被 kill 時整段丟失——
    # 也就是「詳見 service.log」最需要它的時候日誌恰好是空的。
    env["PYTHONUNBUFFERED"] = "1"
    for key, value in extra.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = str(value)
    return env


def _spawn_kwargs(background):
    """後台模式脫離當前終端機：POSIX 用新會話，Windows 用無視窗 + 獨立程序組。"""
    if not background:
        return {}
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        return {"creationflags": flags}
    return {"start_new_session": True}


# ---------------------------------------------------------------- 執行時安裝

def _run(command, description, env=None):
    result = subprocess.run(command, env=env or child_env())
    if result.returncode:
        raise RuntimeError(f"{description}失敗（退出碼 {result.returncode}）")


_VERSION_PROBE = ("from importlib.metadata import version;"
                  "import playwright;print(version('playwright'))")


def _playwright_installed(python):
    """playwright 包沒有 __version__ 屬性，只能問包後設資料。

    這裡一併 import playwright：光有後設資料不代表能 import（裝到一半、
    site-packages 被清過等情況都會後設資料在、模組不在）。
    """
    result = subprocess.run([str(python), "-c", _VERSION_PROBE],
                            capture_output=True, text=True, env=child_env())
    return (result.stdout or "").strip() if result.returncode == 0 else None


def _probe_engine(python, channel):
    result = subprocess.run([str(python), "-c", _ENGINE_PROBE, channel or ""],
                            capture_output=True, text=True, env=child_env(), timeout=180)
    return "PMENGINE-OK" in (result.stdout or ""), (result.stderr or "").strip()


def detect_engine(python, allow_download=True, verbose=True):
    """按平台優先順序探測可用引擎；系統瀏覽器都不可用時才下載自帶 Chromium。"""
    order = _ENGINE_ORDER.get("nt" if os.name == "nt" else sys.platform, ["chrome", None])
    last_error = ""
    for channel in order:
        if channel is None:
            continue
        ok, error = _probe_engine(python, channel)
        if ok:
            if verbose:
                print(f"  ✅ 沿用系統已裝瀏覽器：{channel}（無需下載）")
            return channel
        last_error = error
    # 自帶 Chromium：可能已經下載過，先直接試
    ok, error = _probe_engine(python, None)
    if ok:
        if verbose:
            print("  ✅ 使用 Playwright 自帶 Chromium")
        return None
    if not allow_download:
        raise RuntimeError("沒有可用的瀏覽器引擎，且當前不允許下載。"
                           f"最後一次錯誤：{(error or last_error)[:200]}")
    if verbose:
        print("  ⬇️  未發現可沿用的系統瀏覽器，正在下載 Chromium（約 150MB，僅首次）…", flush=True)
    _run([str(python), "-m", "playwright", "install", "chromium"], "下載 Chromium")
    ok, error = _probe_engine(python, None)
    if not ok:
        raise RuntimeError("Chromium 下載後仍無法啟動。"
                           "Linux 可能缺系統依賴（playwright install-deps）。"
                           f"錯誤：{error[:200]}")
    return None


def ensure_runtime(allow_download=True, verbose=True, force_install=False):
    """確保共享 venv + playwright + 可用引擎就位。冪等，返回 (venv_python, engine)。"""
    python = venv_python()
    if force_install or not python.exists():
        found = find_python()
        if not found:
            raise RuntimeError(
                "找不到可用的 Python 3.9+。\n"
                "  macOS：從 https://www.python.org/downloads/ 安裝，或執行 brew install python\n"
                "  Windows：在應用商店或 https://www.python.org/downloads/ 安裝，"
                "安裝時請勾選「Add python.exe to PATH」")
        host_command = found[0]
        if not python.exists():
            if verbose:
                print(f"  📦 正在建立共享執行環境：{venv_dir()}", flush=True)
            venv_dir().parent.mkdir(parents=True, exist_ok=True)
            _run(host_command + ["-m", "venv", str(venv_dir())], "建立虛擬環境")
    if not python.exists():
        raise RuntimeError(f"虛擬環境建立後仍找不到直譯器：{python}")

    installed = _playwright_installed(python)
    if force_install or installed != PLAYWRIGHT_VERSION:
        if verbose:
            print(f"  📦 正在安裝 playwright=={PLAYWRIGHT_VERSION}", flush=True)
        try:
            _run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                  "playwright==" + PLAYWRIGHT_VERSION], "安裝 playwright")
        except RuntimeError:
            raise RuntimeError(
                "安裝 playwright 失敗。若公司網路需要代理，請先設定後重試：\n"
                "  macOS：export HTTPS_PROXY=http://代理地址:連接埠\n"
                "  Windows：set HTTPS_PROXY=http://代理地址:連接埠")

    engine = read_state().get("engine", "__unset__")
    if force_install or engine == "__unset__" or not _probe_engine(python, engine or None)[0]:
        engine = detect_engine(python, allow_download=allow_download, verbose=verbose)
        write_state(engine=engine, playwright=PLAYWRIGHT_VERSION, version=VERSION,
                    python=str(python))
    return python, engine


# ---------------------------------------------------------------- 啟動服務

def _server_script():
    return Path(__file__).resolve().parent / "prototype_server.py"


def held_by_own_launcher(config, port):
    """launcher_port bind 不上，但佔用者是本專案自己的 LaunchAgent——這是正常狀態。

    socket 啟用下這個連接埠由 launchd 長期持有，那正是「空閒零程序、連接埠仍然通」的
    實現方式。只給 --doctor 用，用來把這種情況和真衝突區分開。
    """
    if sys.platform != "darwin":
        return False
    try:
        import pm_launchagent
        return pm_launchagent.registered_port(config) == int(port)
    except Exception:  # noqa: BLE001
        return False


def reserve_ports(root, config, attempts=8):
    """確認服務連接埠可 bind；被佔則重推並回寫配置，不永久佔坑。

    **只看服務連接埠。** launcher_port 不歸這裡管，而且探它必然出錯：它要麼被
    launchd 長期持有（socket 啟用），要麼被獨立執行的啟動器自己持有——兩種情況下
    「bind 不上」都是正常狀態。更要命的是它已改成不隨 salt 漂移（見 derive_ports），
    重抽根本換不掉它，一旦把它判成衝突就是 8 次空轉後報「沒抽到可用連接埠」。
    它真被外人佔了的話，由啟動器自己 bind 時報錯，或註冊時 bootstrap 失敗暴露。
    """
    import socket
    for _ in range(attempts):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", int(config["port"])))
                return config
            except OSError:
                pass
        config = reroll_ports(root, config)
    raise RuntimeError("連續多次都沒抽到可用連接埠，請檢查本機連接埠占用情況")


def ensure_serving(root, background=False, read_only=False, host="127.0.0.1",
                   open_browser=False, verbose=True, allow_download=True):
    """確保當前專案的服務在跑。

    前台：佔用當前視窗，服務本體就是前台程序，⌃C 可停。
    後台：脫離終端機，日誌進 .pm-workflow/service.log。
    """
    root = Path(root).resolve()
    config = ensure_config(root)

    state = probe_health(config["port"])
    if state:
        if state.get("project_id") != config["project_id"]:
            raise RuntimeError(f"連接埠 {config['port']} 被其他專案的服務佔用，請先停止它")
        if bool(state.get("read_only")) != bool(read_only):
            raise RuntimeError("已有服務的讀寫模式與本次請求不一致，請先停止它")
        if verbose:
            print(f"  ✅ 當前專案服務已在執行：http://127.0.0.1:{config['port']}")
        return "already-running", config

    if host not in ("127.0.0.1", "localhost", "::1") and not read_only:
        raise RuntimeError("區域網監聽只允許 --read-only 模式")

    python, _engine = ensure_runtime(allow_download=allow_download, verbose=verbose)
    config = reserve_ports(root, config)

    env = child_env(PM_SERVER_HOST=host,
                    PM_READ_ONLY="1" if read_only else "0",
                    PM_OPEN_BROWSER="1" if (open_browser and not background) else None,
                    PROTOTYPE_PROJECT_DIR=str(root))
    command = [str(python), str(_server_script())]

    if not background:
        try:
            return subprocess.run(command, cwd=str(root), env=env).returncode, config
        except KeyboardInterrupt:
            return 0, config

    log_path = root / ".pm-workflow/service.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as stream:
        process = subprocess.Popen(command, cwd=str(root), env=env, stdout=stream,
                                   stderr=stream, stdin=subprocess.DEVNULL,
                                   **_spawn_kwargs(True))
    deadline = time.time() + 45
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"服務啟動失敗（退出碼 {process.returncode}），"
                               f"詳見 {log_path}")
        if probe_health(config["port"]):
            return "launched", config
        time.sleep(0.4)
    raise RuntimeError(f"服務啟動超時，詳見 {log_path}")


# ---------------------------------------------------------------- 體檢

def _mark(ok):
    return "✅" if ok else "❌"


def doctor(root):
    """一次列印全部環境事實——遠端排查時讓對方截這一張圖就夠。"""
    root = Path(root).resolve()
    print("=" * 60)
    print(f"  PM Workflow 環境體檢  v{VERSION}")
    print("=" * 60)
    print(f"  平台：{sys.platform} / os.name={os.name}")
    print(f"  專案：{root}")

    found = find_python()
    print(f"\n  {_mark(bool(found))} 直譯器：" +
          (f"{' '.join(found[0])}  → Python {found[1][0]}.{found[1][1]}" if found
           else f"未找到 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+"))
    print(f"      當前程序：{sys.executable}  ({sys.version.split()[0]})")

    python = venv_python()
    print(f"  {_mark(python.exists())} 共享執行環境：{venv_dir()}")
    if python.exists():
        installed = _playwright_installed(python)
        want = PLAYWRIGHT_VERSION
        print(f"  {_mark(installed == want)} playwright：{installed or '未安裝'}（期望 {want}）")
        state = read_state()
        engine = state.get("engine", "__unset__")
        if engine == "__unset__":
            print("  ❌ 瀏覽器引擎：尚未探測")
        else:
            ok, error = _probe_engine(python, engine or None)
            label = engine or "Playwright 自帶 Chromium"
            print(f"  {_mark(ok)} 瀏覽器引擎：{label}" + ("" if ok else f" — {error.splitlines()[0][:80]}"))
    else:
        print("  ❌ playwright：共享環境未建立，無法檢查")

    config_file = root / ".pm-workflow/runtime.json"
    existed = config_file.is_file()
    try:
        config = ensure_config(root)  # 缺失時就地建立，所以下面的 ✅ 永遠成立
    except Exception as error:
        print(f"\n  ❌ 執行配置不可用：{config_file}\n      {error}")
        return 1
    print(f"\n  ✅ 執行配置：{config_file}" + ("" if existed else "（本次新建）"))
    print(f"      專案標識：{config['project_id']}")
    import socket
    for key, label in (("port", "服務連接埠"), ("launcher_port", "啟動器連接埠")):
        port = int(config[key])
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
                free = True
            except OSError as error:
                free = False
                reason = str(error)
        if free:
            print(f"  ✅ {label} {port}：可用")
        elif held_by_own_launcher(config, port):
            # 不是衝突：socket 啟用就是靠 launchd 長期佔著這個連接埠實現的。
            print(f"  ✅ {label} {port}：由 launchd 持有（按需啟動器正常工作中）")
        else:
            state = probe_health(port)
            if state and state.get("project_id") == config["project_id"]:
                print(f"  ✅ {label} {port}：本專案服務正在使用")
            elif key == "launcher_port":
                # 這個連接埠不會自愈（它固定不變），所以不能說「啟動時會自動換連接埠」。
                print(f"  ⚠️  {label} {port}：被別的程式佔用（{reason}）")
                print("      影響：點匯出不會自動起服務。停掉佔用方後重跑 "
                      "bash scripts/install_launcher.sh；期間雙擊啟動入口照常可用。")
            else:
                print(f"  ⚠️  {label} {port}：被佔用（{reason}）；啟動時會自動換連接埠")

    entries = [("啟動原型匯出服務.command", os.name != "nt"),
               ("啟動原型匯出服務.bat", os.name == "nt")]
    print()
    for name, relevant in entries:
        path = root / name
        if not path.exists():
            print(f"  {'❌' if relevant else '  '} 啟動入口 {name}：不存在")
        elif os.name != "nt" and name.endswith(".command"):
            executable = os.access(path, os.X_OK)
            print(f"  {_mark(executable)} 啟動入口 {name}：" +
                  ("可執行" if executable else "缺少可執行權限，請執行 chmod +x"))
        else:
            print(f"  ✅ 啟動入口 {name}：存在")

    if sys.platform == "darwin":
        import pm_launchagent
        registered, agent_port, matched, pid = pm_launchagent.status(config)
        if not registered:
            print("  ⚠️  按需啟動器：未註冊——點匯出不會自動起服務，需要先雙擊啟動入口。")
            print("      註冊：bash scripts/install_launcher.sh")
        elif not matched:
            # plist 裡的連接埠是寫死的，連接埠自愈過就會錯位。
            print(f"  ⚠️  按需啟動器：登記的是連接埠 {agent_port}，當前配置是 "
                  f"{config['launcher_port']}——已錯位，自動啟動不生效。")
            print("      重新註冊：bash scripts/install_launcher.sh")
        else:
            print(f"  ✅ 按需啟動器：已註冊（連接埠 {agent_port}，由 launchd 持有）")
            print("      啟動器程序：" +
                  (f"PID {pid}" if pid else "無（空閒即退，屬正常——連接埠仍然通）"))

    proxies = {k: v for k, v in os.environ.items()
               if k.upper() in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")}
    print(f"\n  代理環境變數：{proxies or '（無）'}")
    if proxies and not any(k.upper() == "NO_PROXY" for k in proxies):
        print("      提示：已設定代理但沒有 NO_PROXY；本服務的本機請求已強制繞過代理。")
    print("=" * 60)
    return 0
