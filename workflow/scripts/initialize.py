#!/usr/bin/env python3
"""把 skill 的資產安裝進專案目錄——Mac 和 Windows 共用的唯一入口。

三類檔案，三種策略：

  RUNTIME  服務執行時程式碼。**永遠覆蓋**（帶時間戳備份）。
           使用者本來就不該手改這些；而「發現本地有改動就保留」恰恰是上一版
           最嚴重的升級缺陷：舊專案升級時 installed.json 是空的，於是每個
           既有檔案都被判為使用者定製而保留，服務程式碼永遠停在舊版本，
           表現就是「雙擊啟動腳本沒反應 / 匯出服務未啟動」。

  CUSTOM   使用者會主動編輯的（workflow 說明書、PRD 骨架、繪圖提示詞）。
           內容等於任何一個歷史發布版 → 視為沒改過，直接升級；
           否則保留使用者的檔案，新版本寫進 .pm-workflow/updates/ 供對照合併。

  ONCE     只在缺失時建立。.mcp.json.example 是樣例，不該被 skill 反覆覆蓋。

不用 bash：Windows 上沒有。所有邏輯都在 Python 裡。
"""
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE / "assets/scripts"))
from pm_runtime import VERSION, atomic_write, ensure_config  # noqa: E402

RUNTIME, CUSTOM, ONCE = "runtime", "custom", "once"

# 顯式對映，不靠「目錄元組 + 特例鏈」推導。
# 目標路徑是被 workflow 文件硬編碼引用的（例如 PRD 流程裡寫死了 scripts/prd-content.html），
# 所以它必須是這裡一眼可見、可 grep 的常量，而不是迴圈裡湧現出來的結果。
MAPPING = [
    # ── 服務執行時：缺任何一個，匯出/截圖就起不來 ──
    ("scripts/pm_runtime.py",              "scripts/pm_runtime.py",              RUNTIME),
    ("scripts/pm_bootstrap.py",            "scripts/pm_bootstrap.py",            RUNTIME),
    ("scripts/start_service.py",           "scripts/start_service.py",           RUNTIME),
    ("scripts/prototype_server.py",        "scripts/prototype_server.py",        RUNTIME),
    ("scripts/prototype_launcher.py",      "scripts/prototype_launcher.py",      RUNTIME),
    ("scripts/pm_launchagent.py",          "scripts/pm_launchagent.py",          RUNTIME),
    ("scripts/prototype-export-client.js", "scripts/prototype-export-client.js", RUNTIME),
    ("scripts/validate_prd.py",            "scripts/validate_prd.py",            RUNTIME),
    ("scripts/pm_sync.py",                 "scripts/pm_sync.py",                 RUNTIME),
    ("scripts/pm_tokens.py",               "scripts/pm_tokens.py",               RUNTIME),
    ("scripts/install_launcher.sh",        "scripts/install_launcher.sh",        RUNTIME),
    ("scripts/啟動原型匯出服務.command",     "啟動原型匯出服務.command",             RUNTIME),
    ("scripts/啟動原型匯出服務.bat",         "啟動原型匯出服務.bat",                 RUNTIME),
    # ── 使用者會改的 ──
    ("workflows/pm-prd.md",            ".agents/workflows/pm-prd.md",            CUSTOM),
    ("workflows/pm-demand.md",         ".agents/workflows/pm-demand.md",         CUSTOM),
    ("workflows/pm-acceptance.md",     ".agents/workflows/pm-acceptance.md",     CUSTOM),
    ("workflows/pm-data-analysis.md",  ".agents/workflows/pm-data-analysis.md",  CUSTOM),
    ("workflows/pm-design.md",         ".agents/workflows/pm-design.md",         CUSTOM),
    ("workflows/pm-change.md",         ".agents/workflows/pm-change.md",         CUSTOM),
    ("workflows/pm-spec.md",           ".agents/workflows/pm-spec.md",           CUSTOM),
    ("workflows/pm-sysdesign.md",      ".agents/workflows/pm-sysdesign.md",      CUSTOM),
    ("workflows/pm-backend.md",        ".agents/workflows/pm-backend.md",        CUSTOM),
    ("workflows/pm-app.md",            ".agents/workflows/pm-app.md",            CUSTOM),
    ("workflows/pm-frontend.md",       ".agents/workflows/pm-frontend.md",       CUSTOM),
    ("workflows/pm-qa.md",             ".agents/workflows/pm-qa.md",             CUSTOM),
    ("workflows/pm-debug.md",          ".agents/workflows/pm-debug.md",          CUSTOM),
    ("workflows/pm-validate.md",       ".agents/workflows/pm-validate.md",       CUSTOM),
    ("workflows/pm-launch.md",         ".agents/workflows/pm-launch.md",         CUSTOM),
    ("templates/prd-content.html",         "scripts/prd-content.html",                   CUSTOM),
    ("templates/pencil-draw-prompt.md",    "scripts/pencil-draw-prompt.md",              CUSTOM),
    # ── 只建立一次 ──
    ("config/mcp.json.example",            ".mcp.json.example",                          ONCE),
]

# 參考資料是可選的：老版本倉庫裡沒有 assets/references/，缺了不影響功能。
REFERENCE_DIR = "references"
REFERENCE_TARGET = ".agents/references"

# 需要可執行位。copy2 只保留原始檔的模式，而 zip 分發、網盤中轉、
# Windows 檢出再傳回 Mac 都會丟權限位——丟了就是「雙擊沒反應」。
EXECUTABLE = {
    "啟動原型匯出服務.command",
    "scripts/install_launcher.sh",
    "scripts/start_service.py",
    "scripts/prototype_launcher.py",
}

# 這一項必須排在 MAPPING 的執行時段裡，但單獨列出來做個說明：
# 註冊 LaunchAgent 時 plist 指向的是專案裡的 prototype_launcher.py，
# 所以檔案必須先落地、再註冊，順序不能顛倒。
LAUNCHER_SCRIPT = "scripts/prototype_launcher.py"

# 上一代留下的檔案：留著會誤導使用者去跑一個裝「全域性唯一 label」LaunchAgent 的舊腳本
# （那會讓一台機器只能服務一個專案）。移走而不是直接刪，放進備份目錄。
STALE = ["scripts/setup_prototype_export_watcher.sh"]

GITIGNORE = ["/.pm-workflow/", "/scripts/pm-runtime-config.js", "/scripts/.venv/", "/.handoff/", "__pycache__/", ".DS_Store",
             "/supabase/.temp/", "/supabase/.branches/", "/supabase/functions/.env", ".env", ".env.local",
             "/app/.pm/", ".pm/", "node_modules/", ".next/"]

# Windows 的 core.autocrlf=true 檢出後再傳回 Mac，.command 會帶上 CRLF，
# bash 報 `$'\r': command not found`；.bat 反過來需要 CRLF 才可靠。
GITATTRIBUTES = [
    "* text=auto",
    "*.command text eol=lf",
    "*.sh text eol=lf",
    "*.bat text eol=crlf",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def load_known_hashes():
    """歷代已發布版本的內容 hash：讓「檔案等於某個舊版本」被認成沒改過而直接升級，
    而不是誤判成使用者定製。缺這個檔案不致命，只是升級時更容易報衝突。"""
    path = Path(__file__).resolve().parent / "known_hashes.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def make_executable(path):
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass  # Windows 上沒有可執行位，失敗不算問題


def setup_launcher(root, config, say):
    """在 macOS 上註冊按需啟動器，讓點匯出能自動起服務。

    預設就做，因為它不是常駐程序：連接埠歸 launchd 持有，空閒時專案裡沒有任何
    程序在跑（詳見 pm_launchagent.py 頂部說明）。

    **任何失敗都只警告、不阻斷安裝。** 裝 skill 的人可能沒權限寫
    ~/Library/LaunchAgents、可能在沒有 launchctl 的沙箱裡、可能根本不是 macOS——
    這些都不該讓「檔案裝好了」這件事失敗。丟了它只是回退到手動雙擊啟動。
    """
    if not sys.platform == "darwin":
        return
    try:
        sys.path.insert(0, str(root / "scripts"))
        import pm_launchagent
        ok, detail = pm_launchagent.install(root, config)
    except Exception as error:  # noqa: BLE001 — 見上：絕不阻斷安裝
        say(f"   ⚠️  按需啟動器註冊失敗（{error}）")
        say("      不影響匯出：雙擊「啟動原型匯出服務.command」照常可用。")
        return
    if ok:
        say(f"   ✅ 按需啟動器已註冊：點匯出/一鍵複製全文會自動起服務，無需先雙擊")
        say(f"      空閒時不佔程序；不想要就跑 bash scripts/install_launcher.sh --uninstall")
    else:
        say(f"   ⚠️  按需啟動器註冊失敗（{detail}）")
        say("      不影響匯出：雙擊「啟動原型匯出服務.command」照常可用。")


def install(root, quiet=False, with_launcher=True):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    say = (lambda *a: None) if quiet else print

    manifest_path = root / ".pm-workflow/installed.json"
    try:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    tracked = previous.get("files", {}) if isinstance(previous, dict) else {}
    known = load_known_hashes()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = root / ".handoff/skill-backups" / f"init-{stamp}"

    entries = list(MAPPING)
    # Path.glob 對不存在的目錄返回空列表，所以這裡不需要額外的存在性判斷。
    for path in sorted((SOURCE / "assets" / REFERENCE_DIR).glob("*")):
        if path.is_file():
            entries.append((f"{REFERENCE_DIR}/{path.name}",
                            f"{REFERENCE_TARGET}/{path.name}", CUSTOM))

    for name in ("scripts", ".handoff"):
        (root / name).mkdir(parents=True, exist_ok=True)

    created, updated, current, skipped, conflicts, missing = [], [], [], [], [], []

    for source_rel, dest_rel, kind in entries:
        source = SOURCE / "assets" / source_rel
        if not source.is_file():
            missing.append(source_rel)
            continue
        dest = root / dest_rel
        incoming, existing = digest(source), digest(dest)

        if existing == incoming:
            tracked[dest_rel] = incoming
            current.append(dest_rel)
            if dest_rel in EXECUTABLE:
                make_executable(dest)
            continue

        if existing is not None:
            if kind == ONCE:
                skipped.append(dest_rel)
                continue
            if kind == CUSTOM:
                # 認得出是某個歷史發布版 → 使用者沒改過 → 照常升級
                unchanged = existing == tracked.get(dest_rel) or existing in known.get(source_rel, [])
                if not unchanged:
                    proposal = root / ".pm-workflow/updates" / dest_rel
                    proposal.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, proposal)
                    conflicts.append(dest_rel)
                    continue
            backup = backup_root / dest_rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, backup)

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        if dest_rel in EXECUTABLE:
            make_executable(dest)
        (updated if existing is not None else created).append(dest_rel)
        tracked[dest_rel] = incoming

    retired = []
    for rel in STALE:
        path = root / rel
        if path.is_file():
            target = backup_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target))
            tracked.pop(rel, None)
            retired.append(rel)

    atomic_write(manifest_path, json.dumps(
        {"version": VERSION, "files": tracked, "pending_updates": conflicts},
        ensure_ascii=False, indent=2))

    _write_lines(root / ".gitignore", GITIGNORE)
    _write_lines(root / ".gitattributes", GITATTRIBUTES)
    keep = root / ".handoff/.gitkeep"
    if not any(root.joinpath(".handoff").iterdir()):
        keep.touch()

    config = ensure_config(root)

    say(f"✅ PM Workflow {VERSION} 已安裝到 {root}")
    say(f"   專案標識 {config['project_id']}，服務連接埠 {config['port']}")
    for label, items in (("新增", created), ("更新", updated), ("已是最新", current),
                         ("已存在未覆蓋", skipped), ("移入備份", retired)):
        if items:
            say(f"   {label} {len(items)} 項" + ("：" + "、".join(items) if len(items) <= 4 else ""))
    if missing:
        say(f"   ⚠️  skill 裡缺少 {len(missing)} 個資產檔案：{'、'.join(missing)}")
    if conflicts:
        say("   ⚠️  以下檔案你改過，已保留你的版本；新版放在 .pm-workflow/updates/ 供對照：")
        for item in conflicts:
            say("        " + item)
    if (root / "scripts/.venv").is_dir():
        say("   💡 scripts/.venv 是舊版留下的（約 150MB），現在執行環境放在使用者目錄共享，可以刪掉")

    launcher_ready = False
    if with_launcher:
        setup_launcher(root, config, say)
        launcher_ready = _launcher_ready(root, config)

    say("")
    if os.name == "nt":
        say("下一步：雙擊專案根目錄的「啟動原型匯出服務.bat」，保持視窗開著")
        say("排查問題：py -3 scripts\\start_service.py --doctor")
    elif launcher_ready:
        say("下一步：直接開啟原型或 PRD 點匯出即可——服務會自動啟動。")
        say("        （也可以雙擊「啟動原型匯出服務.command」手動起，效果一樣）")
        say("排查問題：python3 scripts/start_service.py --doctor")
    else:
        say("下一步：雙擊專案根目錄的「啟動原型匯出服務.command」，保持視窗開著")
        say("排查問題：python3 scripts/start_service.py --doctor")
    return 0


def _launcher_ready(root, config):
    try:
        sys.path.insert(0, str(root / "scripts"))
        import pm_launchagent
        registered, _port, matched, _pid = pm_launchagent.status(config)
        return registered and matched
    except Exception:  # noqa: BLE001
        return False


def _write_lines(path, entries):
    """逐行補齊，不覆蓋使用者已有內容。"""
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = text.splitlines()
    added = [entry for entry in entries if entry not in lines]
    if not added:
        return
    body = text.rstrip("\n")
    atomic_write(path, (body + "\n" if body else "") + "\n".join(added) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="把 PM Workflow 安裝進專案目錄")
    parser.add_argument("--project", default=".", help="專案目錄，預設當前目錄")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-launcher", action="store_true",
                        help="不註冊 macOS 按需啟動器（那樣點匯出前需手動雙擊啟動入口）")
    args = parser.parse_args()
    sys.exit(install(args.project, quiet=args.quiet,
                     with_launcher=not args.no_launcher))
