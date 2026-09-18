"""Project-scoped configuration shared by the preview server, launcher and bootstrap.

設計要點：
  * 連接埠由 project_id 確定性推導到 20000-32767，避開 OS 臨時連接埠段（49152+），
    那一段既會被系統派給出站連線，在 Windows 上還有 Hyper-V/WSL/Docker 的保留塊。
  * 連接埠可自愈：bind 失敗時換 salt 重新推導並回寫配置，不會永久佔坑。
  * ensure_config() 是 create-or-load，缺配置時建立而不是拋錯——任何人 clone 一個
    專案倉（.pm-workflow/ 被 gitignore）都不該看到 traceback。
"""
import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

VERSION = "3.3.0"
PORTS_SCHEME = "deterministic-v2"
PORT_FLOOR = 20000
PORT_SPAN = 12767  # 20000..32766，+1 後仍不超過 32767


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def config_path(root):
    return Path(root).resolve() / ".pm-workflow/runtime.json"


def derive_ports(project_id, salt=0):
    """由專案標識確定性推導服務連接埠與啟動器連接埠；salt 用於 bind 衝突時換一個。

    **salt 只作用於服務連接埠，啟動器連接埠固定不變。** 後者被寫死在 macOS 的
    LaunchAgent plist 裡，而換 plist 連接埠只能 bootout + bootstrap——bootout 會
    連帶殺掉正在處理這次請求的啟動器程序自己。讓它永不漂移，這個競態就不存在。
    真正會跟別的應用撞車的本來也只有服務連接埠。
    """
    launcher = PORT_FLOOR + int.from_bytes(
        hashlib.sha256(f"{project_id}:0".encode()).digest()[:4], "big") % PORT_SPAN + 1
    seed = hashlib.sha256(f"{project_id}:{salt}".encode()).digest()
    port = PORT_FLOOR + int.from_bytes(seed[:4], "big") % PORT_SPAN
    if port == launcher:  # 重抽時正好撞上固定的啟動器連接埠，往後挪一格
        port = PORT_FLOOR + (port + 1 - PORT_FLOOR) % PORT_SPAN
    return port, launcher


def _browser_config(config):
    return {
        "projectId": config["project_id"],
        "token": config["token"],
        "server": "http://127.0.0.1:" + str(config["port"]),
        "launcher": "http://127.0.0.1:" + str(config["launcher_port"]),
    }


def write_browser_config(root, config):
    """瀏覽器側配置，隨連接埠變化重寫，被 prototype-export-client.js 動態載入。"""
    atomic_write(Path(root).resolve() / "scripts/pm-runtime-config.js",
                 "window.PM_RUNTIME = " + json.dumps(_browser_config(config)) + ";\n")


def save_config(root, config):
    root = Path(root).resolve()
    path = config_path(root)
    config["version"] = VERSION
    atomic_write(path, json.dumps(config, ensure_ascii=False, indent=2))
    try:
        path.chmod(0o600)  # 內含專案 token；Windows 上該位無意義，失敗不阻斷
    except OSError:
        pass
    write_browser_config(root, config)
    return config


def ensure_config(root):
    """讀不到就建立；結構過期就就地升級。永不因缺檔案拋錯。"""
    root = Path(root).resolve()
    path = config_path(root)
    config = {}
    if path.is_file():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            config = {}  # 配置損壞時重建，比讓每個入口都 traceback 好
    if not isinstance(config, dict):
        config = {}

    moved = config.get("root") != str(root)
    if moved or not config.get("project_id"):
        # 目錄被移動過：project_id 由絕對路徑派生，必須重算，否則連接埠/身份都對不上
        config["root"] = str(root)
        config["project_id"] = hashlib.sha256(str(root).encode()).hexdigest()[:16]
        config.pop("ports_scheme", None)
    if not config.get("token"):
        config["token"] = secrets.token_urlsafe(32)
    if config.get("ports_scheme") != PORTS_SCHEME or not config.get("port"):
        # 老配置的連接埠抽自 OS 臨時連接埠段，遷到確定性區間
        config["port"], config["launcher_port"] = derive_ports(config["project_id"])
        config["port_salt"] = 0
        config["ports_scheme"] = PORTS_SCHEME
    return save_config(root, config)


def load_config(root):
    """只讀載入；供已初始化的場景使用，缺檔案時給出可執行的指引而非裸 traceback。"""
    path = config_path(root)
    if not path.is_file():
        raise RuntimeError(
            "尚未初始化專案執行配置。請雙擊專案根目錄的「啟動原型匯出服務」"
            "（Windows 為 .bat），它會自動建立配置並啟動服務。")
    config = json.loads(path.read_text(encoding="utf-8"))
    if Path(config["root"]).resolve() != Path(root).resolve():
        raise RuntimeError(
            "專案目錄已移動。請雙擊專案根目錄的「啟動原型匯出服務」（Windows 為 .bat）重新初始化。")
    return config


def reroll_ports(root, config):
    """bind 衝突後換一對連接埠並回寫，返回新配置。

    這裡是全域性唯一改動連接埠的地方，所以 LaunchAgent 的同步也放在這裡：plist 裡的
    連接埠是寫死的，漏同步一次，launchd 就會守著一個沒人訪問的舊連接埠，
    「點匯出自動起服務」靜默失效。放在呼叫點上同步的話，每新增一條自愈路徑
    都得記得補一次——遲早漏。
    """
    config["port_salt"] = int(config.get("port_salt", 0)) + 1
    config["port"], config["launcher_port"] = derive_ports(config["project_id"], config["port_salt"])
    config["ports_scheme"] = PORTS_SCHEME
    config = save_config(root, config)
    try:
        import pm_launchagent
        pm_launchagent.sync(root, config)  # 沒註冊過則什麼都不做
    except Exception:  # noqa: BLE001 — 同步失敗不該拖垮啟動，doctor 會報錯位
        pass
    return config


def local_opener():
    """127.0.0.1 的健康檢查必須繞開代理——urllib 預設也會走 HTTP_PROXY，
    代理返回的 HTML 會讓 json 解析失敗，從而誤判“服務沒在跑”並重復啟動。"""
    return build_opener(ProxyHandler({}))


def probe_health(port, timeout=1.5):
    """返回服務自報的狀態；連不上或不是本服務時返回 None。"""
    try:
        with local_opener().open(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as response:
            state = json.load(response)
        return state if isinstance(state, dict) else None
    except Exception:
        return None


def origin_allowed(origin, port):
    # Chrome can serialize a request from a local file page as the loopback
    # site origin without the service port.
    return origin in (
        None,
        "null",
        "http://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1:" + str(port),
        "http://localhost:" + str(port),
    )


def cors_response_origin(origin):
    # Chrome reports local file pages as an opaque null origin while sending
    # the loopback site origin in the HTTP request header.
    if origin in ("http://127.0.0.1", "http://localhost"):
        return "null"
    return origin


def valid_token(headers, config):
    return (headers.get("X-PM-Project") == config["project_id"] and
            secrets.compare_digest(headers.get("X-PM-Token", ""), config["token"]))
