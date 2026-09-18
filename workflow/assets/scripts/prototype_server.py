#!/usr/bin/env python3
"""
通用 HTML 原型匯出伺服器
================================
功能：
  1. 在專案獨立的本機連接埠提供產物預覽
  2. 提供 /api/screenshot 介面，供 HTML 裡的匯出按鈕觸發
  3. 提供 /api/save-html 介面，供 PRD HTML 將瀏覽器內編輯內容寫回本地檔案
  4. 提供 /api/snapshot 介面，按單個原型頁返回 base64 PNG，供 PRD「一鍵複製全文」把
     iframe 換成圖片（依賴內容、視口和縮放一致時沿用，否則重渲）
  5. 使用 Playwright/Chromium 擷取瀏覽器真實渲染後的 .device，避免 html-to-image 重繪差異

使用方法：雙擊專案根目錄的「啟動原型匯出服務」（macOS 為 .command，Windows 為 .bat）。

注意：不要直接跑這個檔案——它需要共享 venv 裡的 playwright 才能截圖。
正確的入口是 start_service.py，由它準備好環境後再拉起本檔案。
"""

import asyncio
import base64
import hashlib
import shutil
import tempfile
import uuid
import json
import os
import re
import sys
import threading
import time
import webbrowser
from html import unescape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pm_bootstrap import launch_engine  # noqa: E402
from pm_runtime import (VERSION, atomic_write, cors_response_origin, ensure_config,  # noqa: E402
                        origin_allowed, probe_health, reroll_ports, valid_token)


PROJECT_DIR = Path(os.environ.get("PROTOTYPE_PROJECT_DIR")
                   or Path(__file__).resolve().parent.parent).resolve()
# ensure_config 而不是 load_config：配置缺失時建立而不是拋 FileNotFoundError。
# .pm-workflow/ 是 gitignore 的，任何人 clone 一個專案倉都會缺這個檔案。
CONFIG = ensure_config(PROJECT_DIR)
PORT = int(CONFIG["port"])
READ_ONLY = os.environ.get("PM_READ_ONLY") == "1"
BIND_HOST = os.environ.get("PM_SERVER_HOST", "127.0.0.1")
if BIND_HOST not in ("127.0.0.1", "localhost", "::1") and not READ_ONLY:
    raise RuntimeError("區域網監聽只允許只讀模式")
# 產物按「需求名」分資料夾後，原型/流程圖位於 [需求名]/原型/、[需求名]/流程圖/；
# 舊的扁平結構 原型/、流程圖/ 仍相容。截圖輸出到原型/流程圖所在需求目錄下的
# 原型截圖/、流程圖截圖/（舊扁平結構回退到專案根的對應目錄）。
SERVER_URL = f"http://127.0.0.1:{PORT}"
DEFAULT_VIEWPORT = {"width": 1440, "height": 900}
EXPORT_DEVICE_SCALE = 2

# 截圖目錄下的頁面清單檔名（點號開頭，不汙染 PM 看到的截圖目錄）。
# 記錄 page_id → 檔名 的對映，供 /api/snapshot 用 hash 定位 PNG。
MANIFEST_NAME = ".export-manifest.json"
# /api/asset 放行的圖片型別（詳細方案「原型」列的截圖版 <img> 要內聯成 base64 才能粘出去）
ASSET_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
ASSET_MAX_BYTES = 12 * 1024 * 1024

# 允許瀏覽器內編輯寫回的產物子目錄名（任意需求目錄下的這些子目錄，或專案根下的同名舊目錄）
WRITABLE_SUBDIR_NAMES = {"原型", "流程圖", "需求文件", "需求挖掘", "驗收清單", "資料分析", "原型驗證", "技術規格", "上線"}


async def _open_browser_engine(playwright):
    """優先用安裝時探測到的系統瀏覽器（Windows 上是自帶 Edge，macOS 上是 Chrome），
    省掉 150MB 的 Chromium 下載。系統瀏覽器事後被解除安裝時自動回落自帶 Chromium。"""
    channel = launch_engine()
    if channel:
        try:
            return await playwright.chromium.launch(headless=True, channel=channel)
        except Exception as error:
            print(f"  ⚠️  系統瀏覽器 {channel} 啟動失敗，回落自帶 Chromium：{error}", flush=True)
    return await playwright.chromium.launch(headless=True)


def _all_html_under(subdir_name):
    """收集專案內某類產物的所有 HTML：新巢狀 [需求名]/<subdir>/*.html + 舊扁平 <subdir>/*.html。"""
    found = {}
    for pattern in (f"*/{subdir_name}/*.html", f"{subdir_name}/*.html"):
        for path in PROJECT_DIR.glob(pattern):
            if path.is_file():
                found[path.resolve()] = path
    return sorted(found.values(), key=lambda p: p.as_posix())


def _all_prototype_htmls():
    return _all_html_under("原型")


def _output_root_for(html_path):
    """根據原型/流程圖 HTML 的位置推導截圖輸出根目錄。

    新巢狀：[需求名]/原型/x.html  → [需求名]/原型截圖/
            [需求名]/流程圖/x.html → [需求名]/流程圖截圖/
    舊扁平：原型/x.html / 流程圖/x.html → 專案根 原型截圖/ / 流程圖截圖/
    """
    parent = html_path.resolve().parent          # .../原型 或 .../流程圖
    kind = parent.name                            # "原型" / "流程圖"
    out_name = "流程圖截圖" if kind == "流程圖" else "原型截圖"
    requirement_dir = parent.parent               # 新結構=[需求名]/，舊結構=專案根
    if (
        kind in ("原型", "流程圖")
        and _is_under(requirement_dir, PROJECT_DIR)
        and requirement_dir != PROJECT_DIR.resolve()
    ):
        return requirement_dir / out_name
    return PROJECT_DIR / out_name


_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current": "",
    "done": False,
    "error": None,
    "success_count": 0,
    "output_dir": "",
    "html": "",
    "files": [],
    "failed_pages": [], "job_id": "",
}
_state_lock = threading.Lock()

# /api/snapshot 用獨立鎖序列化單頁重渲，不佔用 /api/screenshot 的 _state 狀態機，
# 避免「一鍵複製全文」把「一鍵匯出所有截圖」的進度條攪亂。
_snapshot_lock = threading.RLock()
_save_lock = threading.Lock()


def _update_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


def _get_state():
    with _state_lock:
        return dict(_state)


def _is_under(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _first_prototype_html():
    files = _all_prototype_htmls()
    return files[0] if files else None


def _is_flow_html(html_path):
    try:
        return html_path.resolve().parent.name == "流程圖"
    except OSError:
        return False


def _resolve_html_path(raw_path):
    if not raw_path:
        raise ValueError("必須提供明確的 HTML 路徑")

    if raw_path.startswith(("http://", "https://", "file://")):
        raw_path = urlparse(raw_path).path

    raw_path = unquote(raw_path).split("?", 1)[0].split("#", 1)[0]
    candidates = []

    if raw_path:
        incoming = Path(raw_path)
        if incoming.is_absolute() and _is_under(incoming, PROJECT_DIR):
            candidates.append(incoming)
        candidates.append(PROJECT_DIR / raw_path.lstrip("/"))
        candidates.append(PROJECT_DIR / raw_path)

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if (
            resolved.exists()
            and resolved.is_file()
            and resolved.suffix.lower() == ".html"
            and _is_under(resolved, PROJECT_DIR)
        ):
            return resolved

    raise FileNotFoundError(f"找不到原型 HTML：{raw_path or '(empty)'}")


def _split_ref(raw):
    """把 `../流程圖/x.html?only=a#p1` 拆成 (路徑, query, page_id)。

    query 必須留著：PRD 裡的流程圖 iframe 常帶 `?only=flow-main` 決定渲染哪一張，
    丟掉它取出來的圖就和 PRD 裡看到的不是同一張。
    """
    raw = raw or ""
    if raw.startswith(("http://", "https://", "file://")):
        parsed = urlparse(raw)
        return unquote(parsed.path), parsed.query, unquote(parsed.fragment)
    path_part, _, hash_part = raw.partition("#")
    path_only, _, query = path_part.partition("?")
    return unquote(path_only), query, unquote(hash_part)


def _split_hash(raw):
    path_part, _query, hash_part = _split_ref(raw)
    return path_part, hash_part


def _pick_existing_html(candidates):
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if (
            resolved.exists()
            and resolved.is_file()
            and resolved.suffix.lower() == ".html"
            and _is_under(resolved, PROJECT_DIR)
        ):
            return resolved
    return None


def _resolve_base_html(base):
    """解析發起頁（PRD）的路徑，用來給相對 src 定位。找不到就返回 None，不兜底。

    兩種 base 都要認：file:// 開啟時 location.pathname 是磁碟絕對路徑；PRD 被推到內網、
    用 http:// 開啟時它是站點根下的路徑（/需求名/需求文件/x.html），在磁碟上並不存在，
    必須再按專案目錄相對解一次，否則內網訪客點「一鍵複製全文」全程取不到原型圖。
    """
    base_path, _ = _split_hash(base)
    if not base_path:
        return None
    incoming = Path(base_path)
    candidates = [incoming] if incoming.is_absolute() else []
    candidates.append(PROJECT_DIR / base_path.lstrip("/"))
    return _pick_existing_html(candidates)


def _resolve_ref_html(src, base=None):
    """解析 PRD 裡 iframe 的 src。

    與 _resolve_html_path 的區別：支援 `../原型/x.html#p1` 這類相對發起頁的路徑，
    且**不做**「找不到就退回第一個原型」的兜底——取錯頁比取不到更糟。
    返回 (絕對 HTML 路徑, page_id, query)。
    """
    src_path, query, page_id = _split_ref(src)
    if not src_path:
        raise FileNotFoundError("iframe src 為空")

    candidates = []
    incoming = Path(src_path)
    if incoming.is_absolute():
        candidates.append(incoming)
    else:
        base_html = _resolve_base_html(base)
        if base_html:
            candidates.append(base_html.parent / src_path)
    # http:// 開啟時 src 可能是站點根路徑，磁碟上不存在，按專案目錄再解一次
    candidates.append(PROJECT_DIR / src_path.lstrip("/"))

    resolved = _pick_existing_html(candidates)
    if not resolved:
        raise FileNotFoundError(f"找不到原型 HTML：{src}")
    return resolved, page_id, query


def _resolve_ref_asset(src, base=None):
    """解析 PRD 裡 <img> 的本地 src（詳細方案「原型」列的截圖版）。

    與 _resolve_ref_html 同樣的相對路徑規則，但只放行圖片字尾，且必須落在專案目錄內
    ——這個介面會把檔案原樣 base64 吐出去，不能變成任意檔案讀取。
    """
    src_path, _query, _hash = _split_ref(src)
    if not src_path:
        raise FileNotFoundError("img src 為空")

    suffix = Path(src_path).suffix.lower()
    if suffix not in ASSET_MIME:
        raise ValueError(f"不支援的圖片型別：{suffix or src_path}")

    candidates = []
    incoming = Path(src_path)
    if incoming.is_absolute():
        candidates.append(incoming)     # file:// 下就是磁碟絕對路徑
    else:
        base_html = _resolve_base_html(base)
        if base_html:
            candidates.append(base_html.parent / src_path)
    # http:// 開啟時 src 可能是站點根路徑，磁碟上不存在，按專案目錄再解一次
    candidates.append(PROJECT_DIR / src_path.lstrip("/"))

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file() and _is_under(resolved, PROJECT_DIR):
            return resolved, ASSET_MIME[suffix]
    raise FileNotFoundError(f"找不到圖片：{src}")


def _manifest_path(html_path):
    return _output_root_for(html_path) / MANIFEST_NAME


def _manifest_key(html_path):
    try:
        return html_path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return html_path.name


def _read_manifest(html_path):
    """讀出該 HTML 在截圖目錄清單裡的條目：{page_id/tab → 檔名}。

    清單按 HTML 相對路徑分組，因為同一個 流程圖截圖/ 目錄可能被多份流程圖共用。
    """
    path = _manifest_path(html_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    entry = data.get(_manifest_key(html_path))
    return entry if isinstance(entry, dict) else {}


def _write_manifest(html_path, items):
    """把本輪頁面清單寫回截圖目錄（合併式，不動其他 HTML 的條目）。"""
    path = _manifest_path(html_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}

    data[_manifest_key(html_path)] = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))
    except OSError:
        raise


def _render_signature(html_path, page_id="", query="", scale=2, viewport=None):
    """Conservative content fingerprint, including nested prototypes and local assets."""
    files = {html_path.resolve()}
    scope = html_path.parent.parent
    if scope == PROJECT_DIR:
        roots = [html_path.parent, PROJECT_DIR / "scripts", PROJECT_DIR / "assets"]
    else:
        roots = [scope, PROJECT_DIR / "scripts", PROJECT_DIR / "assets"]
    excluded = {"原型截圖", "流程圖截圖", ".git", ".handoff", ".venv", ".pm-workflow", "__pycache__"}
    extensions = {".html", ".css", ".js", ".mjs", ".json", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".woff", ".woff2"}
    for root in roots:
        if root.exists():
            files.update(p.resolve() for p in root.rglob("*")
                         if p.is_file() and p.suffix.lower() in extensions and not excluded.intersection(p.parts)
                         and _is_under(p, PROJECT_DIR))
    # Follow literal references outside the requirement directory as well.
    queue, seen = list(files), set()
    remote = False
    while queue:
        path = queue.pop()
        if path in seen or path.suffix.lower() not in {".html", ".css", ".js", ".mjs"}: continue
        seen.add(path)
        content = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r'(?:src|href)\s*=\s*["\x27]https?://', content): remote = True
        for ref in re.findall(r'["\x27(]([^"\x27()\s<>]+\.(?:html|css|js|mjs|json|png|jpe?g|webp|svg|gif|woff2?)(?:[?#][^"\x27()\s<>]*)?)', content):
            clean = unquote(ref.split("?")[0].split("#")[0])
            dep = (PROJECT_DIR / clean.lstrip("/") if clean.startswith("/") else path.parent / clean).resolve()
            if dep.is_file() and _is_under(dep, PROJECT_DIR) and dep not in files:
                files.add(dep); queue.append(dep)
    h = hashlib.sha256()
    h.update(json.dumps([VERSION, page_id, query, scale, viewport or DEFAULT_VIEWPORT], sort_keys=True).encode())
    for path in sorted(files):
        h.update(str(path.relative_to(PROJECT_DIR)).encode())
        h.update(path.read_bytes())
    # Remote resources cannot be validated without reloading them.
    if remote: h.update(uuid.uuid4().hex.encode())
    return h.hexdigest()


def _lookup_cached_png(html_path, page_id, query="", scale=2, viewport=None):
    key = _snapshot_cache_key(page_id, query)
    items = _read_manifest(html_path).get("items") or []
    match = next((it for it in items if it.get("page_id") == key), None)
    if match is None and not page_id and not query:
        match = next((it for it in items if not str(it.get("page_id", "")).startswith("q:")), None)
    if not match: return None
    name = match.get("file", "")
    if not name or Path(name).name != name: return None
    png_path = _output_root_for(html_path) / name
    fingerprint_page = page_id or match.get("source_page", match.get("page_id", ""))
    signature = _render_signature(html_path, fingerprint_page, query, scale, viewport)
    if not png_path.is_file() or match.get("signature") != signature: return None
    return png_path


def _owned_filename(html_path, label, variant=""):
    owner = hashlib.sha256(_manifest_key(html_path).encode()).hexdigest()[:8]
    suffix = ("-" + hashlib.sha256(variant.encode()).hexdigest()[:10]) if variant else ""
    return f"{_safe_filename(html_path.stem)}-{owner}-{_safe_filename(label)}{suffix}.png"


def _publish_batch(html_path, stage, items):
    """Back up overwritten files and roll back a failed publication."""
    output = _output_root_for(html_path)
    backup = PROJECT_DIR / ".handoff/export-backups" / uuid.uuid4().hex
    backup.mkdir(parents=True, exist_ok=True)
    changed = []
    try:
        for item in items:
            name = item["file"]
            if Path(name).name != name: raise ValueError("無效截圖檔名")
            dest = output / name
            if not (stage / name).exists(): continue
            if dest.is_symlink(): raise PermissionError("截圖目標不能是符號連結")
            exists = dest.exists()
            if exists: shutil.copy2(dest, backup / name)
            changed.append((dest, exists))
            os.replace(stage / name, dest)
        _write_manifest(html_path, items)
    except Exception:
        for dest, exists in reversed(changed):
            if exists: os.replace(backup / dest.name, dest)
            elif dest.exists(): dest.unlink()
        raise


def _resolve_writable_html_path(raw_path):
    html_path = _resolve_html_path(raw_path)
    parent = html_path.parent.resolve()
    # 放行：專案內任意位置的「可寫產物子目錄」（如 [需求名]/需求文件/、原型/ 等），
    # 同時相容舊扁平結構（專案根下的同名目錄）。父目錄名需在白名單內且位於專案目錄內。
    if not (_is_under(parent, PROJECT_DIR) and parent.name in WRITABLE_SUBDIR_NAMES):
        raise PermissionError(f"不允許儲存到該目錄：{html_path.parent}")
    return html_path


def _atomic_write_text(path, content):
    atomic_write(path, content)


def _feature_name(html_path):
    name = html_path.stem
    for suffix in ("-prototype", "_prototype", "-原型", " · 互動原型", " - 原型"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return _safe_filename(name, fallback="prototype")


def _strip_markup(value):
    value = re.sub(r"<[^>]+>", "", value or "", flags=re.S)
    return unescape(value).strip()


def _safe_filename(name, fallback="prototype"):
    name = _strip_markup(name)
    name = re.sub(r"[/\\:*?\"<>|]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(". ")
    return name or fallback


def _normalize_viewport(value):
    if not isinstance(value, dict):
        return dict(DEFAULT_VIEWPORT)

    def _num(key, fallback):
        try:
            number = int(float(value.get(key, fallback)))
        except (TypeError, ValueError):
            return fallback
        return max(320, min(number, 4096))

    return {
        "width": _num("width", DEFAULT_VIEWPORT["width"]),
        "height": _num("height", DEFAULT_VIEWPORT["height"]),
    }


def _clean_comment_label(value):
    value = _strip_markup(value)
    value = re.sub(r"^[=\-\s_#]+|[=\-\s_#]+$", "", value)
    value = re.sub(r"^[-\s]*", "", value).strip()
    if not value:
        return ""
    if not re.search(r"[\w\u4e00-\u9fff]", value):
        return ""
    return value


def _parse_attrs(attrs):
    parsed = {}
    for match in re.finditer(r"([:\w-]+)\s*=\s*(['\"])(.*?)\2", attrs, re.S):
        parsed[match.group(1)] = unescape(match.group(3))
    return parsed


def _extract_source_labels(html_path):
    content = html_path.read_text(encoding="utf-8")
    devices = []

    for match in re.finditer(r"(?P<prefix>(?:\s*<!--.*?-->\s*){0,8})<div\b(?P<attrs>[^>]*?)>", content, re.S):
        attrs = _parse_attrs(match.group("attrs"))
        classes = attrs.get("class", "").split()
        if "device" not in classes or not attrs.get("id"):
            continue
        devices.append(
            {
                "id": attrs["id"],
                "attrs": attrs,
                "prefix": match.group("prefix") or "",
                "start": match.end(),
            }
        )

    labels = {}
    for index, device in enumerate(devices):
        next_start = devices[index + 1]["start"] if index + 1 < len(devices) else len(content)
        segment = content[device["start"] : next_start]
        label = (
            device["attrs"].get("data-export-name")
            or device["attrs"].get("data-name")
            or device["attrs"].get("data-title")
            or device["attrs"].get("aria-label")
            or device["attrs"].get("title")
            or ""
        )

        if not label:
            label_match = re.search(r'<div\s+class=["\']device-label["\'][^>]*>(.*?)</div>', segment, re.S)
            if label_match:
                label = label_match.group(1)

        if not label:
            title_match = re.search(r'class=["\'][^"\']*\bpage-title\b[^"\']*["\'][^>]*>(.*?)</', segment, re.S)
            if title_match:
                label = title_match.group(1)

        if not label:
            comments = re.findall(r"<!--(.*?)-->", device["prefix"], re.S)
            for comment in reversed(comments):
                cleaned = _clean_comment_label(comment)
                if cleaned:
                    label = cleaned
                    break

        labels[device["id"]] = _safe_filename(label, fallback=device["id"])

    return labels


def _relative_url_path(html_path):
    rel = html_path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    return "/" + quote(rel, safe="/")


def _dedupe_filename(filename, used):
    stem = filename[:-4] if filename.lower().endswith(".png") else filename
    candidate = f"{stem}.png"
    index = 2
    while candidate in used:
        candidate = f"{stem}-{index}.png"
        index += 1
    used.add(candidate)
    return candidate


async def _discover_pages(page, html_path, source_labels):
    base_url = f"{SERVER_URL}{_relative_url_path(html_path)}"
    await page.goto(base_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(500)

    dom_pages = await page.evaluate(
        """
        () => Array.from(document.querySelectorAll('.device[id]')).map(device => {
          const wrapper = device.closest('.device-wrapper');
          const labelNode = wrapper ? wrapper.querySelector('.device-label') : null;
          const pageTitle = device.querySelector('.page-title');
          const tabs = Array.from(device.querySelectorAll('.report-seg[data-tab], [data-export-tab]')).map(seg => ({
            tab: seg.dataset.tab || seg.dataset.exportTab || '',
            label: seg.dataset.exportName || seg.dataset.name || seg.textContent.trim()
          })).filter(item => item.tab);
          return {
            id: device.id,
            label: device.dataset.exportName || device.dataset.name || device.dataset.title ||
              device.getAttribute('aria-label') || (labelNode && labelNode.textContent.trim()) ||
              (pageTitle && pageTitle.textContent.trim()) || '',
            tabs
          };
        })
        """
    )

    pages = []
    for item in dom_pages:
        page_id = item["id"]
        base_label = _safe_filename(item.get("label") or source_labels.get(page_id) or page_id, fallback=page_id)
        tabs = item.get("tabs") or []

        if len(tabs) > 1:
            for tab_index, tab in enumerate(tabs):
                tab_id = tab["tab"]
                tab_label = _safe_filename(tab.get("label"), fallback=tab_id)
                if tab_index == 0:
                    label = base_label
                elif "·" in base_label:
                    parts = [part.strip() for part in base_label.split("·")]
                    parts[-1] = tab_label
                    label = " · ".join(parts)
                else:
                    label = f"{base_label}-{tab_label}"
                pages.append({"hash": page_id, "page_id": page_id, "tab": tab_id, "label": label})
        else:
            pages.append({"hash": page_id, "page_id": page_id, "tab": None, "label": base_label})

    if not pages:
        raise RuntimeError("未找到可匯出的 .device 原型節點")

    return pages


async def _wait_for_visible_device(page, page_id):
    await page.wait_for_function(
        """
        id => {
          const el = document.getElementById(id);
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        }
        """,
        arg=page_id,
        timeout=7000,
    )
    handle = await page.evaluate_handle("id => document.getElementById(id)", arg=page_id)
    element = handle.as_element()
    if not element:
        raise RuntimeError(f"找不到頁面節點：{page_id}")
    return element


async def _set_tab(page, tab_id):
    if not tab_id:
        return

    await page.evaluate(
        """
        tabId => {
          if (typeof window.switchTab === 'function') {
            window.switchTab(tabId);
            return;
          }
          document.querySelectorAll('.report-seg[data-tab], [data-export-tab]').forEach(seg => {
            const segTab = seg.dataset.tab || seg.dataset.exportTab;
            seg.classList.toggle('active', segTab === tabId);
          });
          document.querySelectorAll('.report-panel').forEach(panel => {
            panel.style.display = panel.id === tabId ? '' : 'none';
          });
        }
        """,
        tab_id,
    )
    await page.wait_for_timeout(300)


async def _force_tiled_mode(page):
    await page.evaluate(
        """
        () => {
          let exportStyle = document.getElementById('prototype-export-hide-ui-style');
          if (!exportStyle) {
            exportStyle = document.createElement('style');
            exportStyle.id = 'prototype-export-hide-ui-style';
            document.head.appendChild(exportStyle);
          }
          exportStyle.textContent = '.export-btn, #exportFab, [data-export-ui="true"] { display: none !important; }';
          document.body.classList.remove('single');
          document.body.classList.add('tiled');
          document.querySelectorAll('.device-wrapper').forEach(wrapper => wrapper.classList.remove('active'));
        }
        """
    )


async def _wait_for_export_ready(page):
    await page.evaluate(
        """
        async () => {
          if (document.fonts && document.fonts.ready) {
            try { await document.fonts.ready; } catch (_) {}
          }
          const images = Array.from(document.images || []);
          await Promise.all(images.map(img => {
            if (img.complete) return Promise.resolve();
            if (typeof img.decode === 'function') return img.decode().catch(() => undefined);
            return new Promise(resolve => {
              img.addEventListener('load', resolve, { once: true });
              img.addEventListener('error', resolve, { once: true });
            });
          }));
          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
          if (window.PMDiagram) {
            const result = window.PMDiagram.audit();
            if (!result.ok) throw new Error('流程圖存在遮擋或越界：' + result.errors.join('；'));
          }
        }
        """
    )


async def _run_screenshots(html_path, options=None):
    options = options or {}
    viewport = _normalize_viewport(options.get("viewport"))
    output = _output_root_for(html_path)
    output.mkdir(parents=True, exist_ok=True)
    failures, items = [], []
    _update_state(output_dir=str(output), html=str(html_path), files=[], failed_pages=[])
    try:
        from playwright.async_api import async_playwright
        with tempfile.TemporaryDirectory(prefix=".export-", dir=output) as temp:
            stage = Path(temp)
            async with async_playwright() as p:
                browser = await _open_browser_engine(p)
                try:
                    page = await browser.new_page(viewport=viewport, device_scale_factor=EXPORT_DEVICE_SCALE)
                    base_url = f"{SERVER_URL}{_relative_url_path(html_path)}"
                    if _is_flow_html(html_path):
                        await page.goto(base_url, wait_until="networkidle")
                        targets = [{"page_id": f"chart-{i}", "label": f"圖{i}", "element": e}
                                   for i, e in enumerate(await page.locator(".chart-container").element_handles(), 1)]
                    else:
                        targets = await _discover_pages(page, html_path, _extract_source_labels(html_path))
                        await _force_tiled_mode(page)
                    if not targets: raise RuntimeError("未找到可匯出的頁面")
                    _update_state(total=len(targets))
                    used = set()
                    for i, target in enumerate(targets):
                        label = target["label"]
                        _update_state(progress=i, current=label)
                        try:
                            if "element" in target:
                                element = target["element"]
                            else:
                                await _force_tiled_mode(page)
                                await _set_tab(page, target.get("tab"))
                                element = await _wait_for_visible_device(page, target["page_id"])
                            await _wait_for_export_ready(page)
                            name = _dedupe_filename(_owned_filename(html_path, label), used)
                            signature = _render_signature(html_path, target["page_id"], scale=EXPORT_DEVICE_SCALE, viewport=viewport)
                            await element.screenshot(path=str(stage / name), type="png")
                            items.append({"page_id": target["page_id"], "tab": target.get("tab"),
                                          "label": label, "file": name, "signature": signature})
                        except Exception as exc:
                            failures.append({"page": label, "error": str(exc)})
                finally:
                    await browser.close()
            if failures:
                _update_state(running=False, done=True, current="匯出失敗，保留上輪截圖",
                              error="部分頁面生成失敗，本輪未替換舊圖", failed_pages=failures,
                              success_count=0, rendered_count=len(items))
                return
            _publish_batch(html_path, stage, items)
        _update_state(running=False, done=True, error=None, current="完成", progress=len(items),
                      success_count=len(items), files=[str(output / it["file"]) for it in items])
    except Exception as exc:
        _update_state(running=False, done=True, error=str(exc), current="匯出失敗，保留上輪截圖",
                      success_count=0, failed_pages=failures)


def _screenshot_thread(html_path, options=None):
    with _snapshot_lock:
        asyncio.run(_run_screenshots(html_path, options))


def _snapshot_cache_key(page_id, query):
    """帶 query 的 iframe（如 `?only=flow-main`）自成一檔快取，不與整輪匯出的頁混用。"""
    if query:
        return f"q:{query}" + (f"#{page_id}" if page_id else "")
    return page_id or ""


async def _pick_snapshot_element(page, page_id):
    """兜底取圖：優先指定 id，其次頁面裡最像"一屏內容"的容器，最後整個 body。

    PRD 裡的 iframe 並不都是平鋪原型——單屏頁（.screen）、流程圖（.chart-container）、
    甚至純排版頁都有，所以不能假設一定存在 .device[id]。
    """
    handle = await page.evaluate_handle(
        """
        id => {
          if (id) {
            const byId = document.getElementById(id);
            if (byId) return byId;
            throw new Error('找不到指定頁面狀態：' + id);
          }
          return document.querySelector('.chart-container, .device, .screen, .phone, main') || document.body;
        }
        """,
        page_id,
    )
    element = handle.as_element()
    if not element:
        raise RuntimeError("頁面裡找不到可截圖的節點")
    return element


async def _run_single_snapshot(html_path, page_id, query, scale, viewport=None):
    """只渲染一頁並落盤，返回 (PNG 路徑, 頁面清單, 命中項索引)。

    命名分三檔：
      A. 平鋪原型的 .device[id] / B. 流程圖的 .chart-container
         → 沿用整輪匯出的命名與去重順序，單頁重渲的產物能被整輪匯出與快取查詢認得。
      C. 其餘（單屏頁、帶 query 的流程圖片段等）
         → 用 `HTML 名[-page_id]` 獨立命名，不與 A/B 搶檔名。
    """
    from playwright.async_api import async_playwright

    output_dir = _output_root_for(html_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    url = f"{SERVER_URL}{_relative_url_path(html_path)}"
    if query:
        url += "?" + query
    if page_id:
        url += "#" + quote(page_id, safe="")

    cache_key = _snapshot_cache_key(page_id, query)

    async with async_playwright() as p:
        browser = await _open_browser_engine(p)
        context = await browser.new_context(
            viewport=viewport or dict(DEFAULT_VIEWPORT),
            device_scale_factor=scale,
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await _wait_for_export_ready(page)

            items, target, element = None, 0, None

            # ── A/B 檔：無 query 時才走整輪匯出同款命名（帶 query 的片段是另一張圖）──
            if not query and _is_flow_html(html_path):
                containers = await page.locator(".chart-container").element_handles()
                if containers:
                    used = set()
                    items = [
                        {
                            "page_id": f"chart-{i}", "tab": None,
                            "label": f"{_feature_name(html_path)}-圖{i}",
                            "file": _dedupe_filename(f"{_feature_name(html_path)}-圖{i}.png", used),
                        }
                        for i in range(1, len(containers) + 1)
                    ]
                    matched = [i for i, it in enumerate(items) if it["page_id"] == page_id]
                    if page_id and not matched:
                        items = None  # 給的不是 chart-N，落到 C 檔按 id 取元素
                    else:
                        target = matched[0] if matched else 0
                        element = containers[target]

            if items is None and not query and not _is_flow_html(html_path):
                try:
                    pages = await _discover_pages(page, html_path, _extract_source_labels(html_path))
                except Exception:
                    pages = []  # 單屏頁沒有 .device[id]，交給下面的 C 檔兜底
                if pages:
                    used = set()
                    candidates = []
                    for item in pages:
                        label = _safe_filename(item["label"], fallback=item["page_id"])
                        candidates.append({
                            "page_id": item["page_id"], "tab": item.get("tab"), "label": label,
                            "file": _dedupe_filename(f"{label}.png", used),
                        })
                    matched = [i for i, it in enumerate(candidates) if it["page_id"] == page_id]
                    if not page_id or matched:
                        items, target = candidates, (matched[0] if matched else 0)
                        await _force_tiled_mode(page)
                        await _set_tab(page, items[target].get("tab"))
                        await _wait_for_export_ready(page)
                        element = await _wait_for_visible_device(page, items[target]["page_id"])

            # ── C 檔兜底：單屏頁 / 帶 query 的片段 / 給了非頁面 id ──
            if element is None:
                label = _safe_filename(html_path.stem, fallback="snapshot")
                if page_id:
                    label = f"{label}-{_safe_filename(page_id, fallback='page')}"
                elif query:
                    label = f"{label}-{_safe_filename(query, fallback='q')}"
                items = [{"page_id": cache_key, "tab": None, "label": label, "file": f"{label}.png"}]
                target = 0
                element = await _pick_snapshot_element(page, page_id)

            selected = dict(items[target])
            variant = json.dumps([page_id, query, scale, viewport or DEFAULT_VIEWPORT], sort_keys=True)
            selected["file"] = _owned_filename(html_path, selected["label"], variant)
            selected["page_id"] = cache_key
            selected["signature"] = _render_signature(html_path, page_id, query, scale, viewport)
            out_path = output_dir / selected["file"]
            await element.scroll_into_view_if_needed(timeout=3000)
            await page.wait_for_timeout(150)
            with tempfile.TemporaryDirectory(prefix=".snapshot-", dir=output_dir) as temp:
                stage = Path(temp)
                await element.screenshot(path=str(stage / selected["file"]), type="png", scale="device")
                previous = [it for it in _read_manifest(html_path).get("items", [])
                            if it.get("page_id") != cache_key]
                _publish_batch(html_path, stage, previous + [selected])
            items, target = [selected], 0
        finally:
            await browser.close()

    return out_path, items, target


def _snapshot_png(html_path, page_id, query, scale, viewport=None, force=False):
    with _snapshot_lock:
        cached = None if force else _lookup_cached_png(html_path, page_id, query, scale, viewport)
        if cached: return cached, True
        path, _, _ = asyncio.run(_run_single_snapshot(html_path, page_id, query, scale, viewport))
        return path, False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{time.strftime('%H:%M:%S')}] {fmt % args}")

    def _local_referer(self):
        raw = self.headers.get("Referer", "")
        if not raw:
            return False
        try:
            parsed = urlparse(raw)
            return (parsed.scheme == "http"
                    and parsed.hostname in {"127.0.0.1", "localhost"}
                    and parsed.port == PORT)
        except (TypeError, ValueError):
            return False

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin_allowed(origin, PORT) and origin:
            self.send_header("Access-Control-Allow-Origin", cors_response_origin(origin))
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-PM-Token, X-PM-Project")
        self.send_header("Cache-Control", "no-store")

    def _authorized(self):
        host = self.headers.get("Host", "")
        return (host in {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
                and origin_allowed(self.headers.get("Origin"), PORT)
                and valid_token(self.headers, CONFIG))

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        if not origin_allowed(self.headers.get("Origin"), PORT):
            self._json({"error": "來源不允許"}, 403)
            return
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        if path == "/api/health":
            self._json({"project_id": CONFIG["project_id"], "version": VERSION, "read_only": READ_ONLY})
        elif path == "/api/status":
            if READ_ONLY or not self._authorized():
                self._json({"error": "專案身份校驗失敗"}, 403)
                return
            self._json(_get_state())
        else:
            self._serve_file(path)

    def do_POST(self):
        if READ_ONLY or not self._authorized():
            self._json({"error": "只讀模式或專案身份校驗失敗"}, 403)
            return
        path = unquote(self.path.split("?", 1)[0])
        if path == "/api/screenshot":
            self._handle_screenshot()
        elif path == "/api/snapshot":
            self._handle_snapshot()
        elif path == "/api/asset":
            self._handle_asset()
        elif path == "/api/save-html":
            self._handle_save_html()
        elif path == "/api/revision":
            try:
                target = _resolve_writable_html_path(self._read_json_body().get("path"))
                self._json({"ok": True, "revision": hashlib.sha256(target.read_bytes()).hexdigest()})
            except Exception as error:
                self._json({"ok": False, "error": str(error)}, 400)
        else:
            self._json({"error": "not found"}, 404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 24 * 1024 * 1024:
            raise ValueError("請求過大")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def _handle_screenshot(self):
        state = _get_state()
        if state["running"]:
            self._json({"started": False, "error": "截圖已在進行中，請等待"}, 409)
            return

        try:
            payload = self._read_json_body()
            html_path = _resolve_html_path(payload.get("path") or payload.get("html") or payload.get("url"))
            options = {
                "viewport": _normalize_viewport(payload.get("viewport")),
            }
        except Exception as error:
            self._json({"started": False, "error": str(error)}, 400)
            return

        job_id = uuid.uuid4().hex
        with _state_lock:
            if _state["running"]:
                self._json({"started": False, "error": "已有匯出任務"}, 409)
                return
            _state["running"] = True
        _update_state(
            running=True,
            job_id=job_id,
            progress=0,
            total=0,
            current="啟動瀏覽器...",
            done=False,
            error=None,
            success_count=0,
            output_dir=str(_output_root_for(html_path) / _feature_name(html_path)),
            html=str(html_path),
            files=[],
        )

        thread = threading.Thread(target=_screenshot_thread, args=(html_path, options), daemon=True)
        thread.start()
        # 截圖直接落在 [需求名]/原型截圖|流程圖截圖/ 一級目錄，不再按 HTML 名多封一層子資料夾；
        # 這裡曾多拼一個 _feature_name()，報出來的路徑和真正的輸出目錄不一致，排障時很誤導。
        self._json({"started": True, "job_id": job_id, "html": str(html_path), "output_dir": str(_output_root_for(html_path))})

    def _handle_snapshot(self):
        """按 iframe src 返回單頁 base64 PNG，供 PRD「一鍵複製全文」把 iframe 換成圖片。

        file:// 下瀏覽器既不能 fetch 本地 PNG、canvas 也會被汙染，所以 base64 只能由本服務下發。
        """
        try:
            payload = self._read_json_body()
            src = payload.get("src") or payload.get("url") or payload.get("path")
            html_path, page_id, query = _resolve_ref_html(src, payload.get("base"))
            try:
                scale = int(payload.get("scale") or EXPORT_DEVICE_SCALE)
            except (TypeError, ValueError):
                scale = EXPORT_DEVICE_SCALE
            scale = max(1, min(3, scale))
        except Exception as error:
            self._json({"ok": False, "error": str(error)}, 400)
            return

        try:
            png_path, cached = _snapshot_png(html_path, page_id, query, scale,
                _normalize_viewport(payload.get("viewport")), bool(payload.get("force")))
            raw = png_path.read_bytes()
        except ImportError:
            # 走到這裡說明服務不是由 start_service.py 拉起的（它會先備好共享 venv）。
            self._json({
                "ok": False,
                "error": "截圖依賴未就緒。請關掉當前服務視窗，改為雙擊專案根目錄的"
                         "「啟動原型匯出服務」（Windows 為 .bat）重新啟動。",
            }, 500)
            return
        except Exception as error:
            self._json({"ok": False, "error": str(error)}, 500)
            return

        self._json({
            "ok": True,
            "cached": cached,
            "src": src,
            "html": str(html_path),
            "page_id": page_id,
            "file": str(png_path),
            "bytes": len(raw),
            "dataUrl": "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
        })

    def _handle_asset(self):
        """把 PRD 裡本地路徑的 <img>（原型列截圖）讀成 base64。

        和 /api/snapshot 同一個理由：file:// 下 fetch 本地檔案被攔、canvas 也讀不回來，
        不內聯的話粘到Notion/Google 文件裡就是一堆裂圖。
        """
        try:
            payload = self._read_json_body()
            src = payload.get("src") or payload.get("url") or payload.get("path")
            asset_path, mime = _resolve_ref_asset(src, payload.get("base"))
        except Exception as error:
            self._json({"ok": False, "error": str(error)}, 400)
            return

        try:
            size = asset_path.stat().st_size
            if size > ASSET_MAX_BYTES:
                self._json({
                    "ok": False,
                    "error": f"圖片過大（{size // 1024} KB > {ASSET_MAX_BYTES // 1024} KB），已跳過內聯",
                }, 413)
                return
            raw = asset_path.read_bytes()
        except Exception as error:
            self._json({"ok": False, "error": str(error)}, 500)
            return

        self._json({
            "ok": True,
            "src": src,
            "file": str(asset_path),
            "bytes": len(raw),
            "dataUrl": "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii"),
        })

    def _handle_save_html(self):
        try:
            payload = self._read_json_body()
            html_path = _resolve_writable_html_path(payload.get("path") or payload.get("html") or payload.get("url"))
            content = payload.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("儲存內容為空")
            if not content.lstrip().lower().startswith("<!doctype html"):
                content = "<!DOCTYPE html>\n" + content
            with _save_lock:
                raw = html_path.read_bytes()
                current_revision = hashlib.sha256(raw).hexdigest()
                if payload.get("revision") != current_revision:
                    self._json({"ok": False, "error": "檔案已變化或缺少版本，請重新載入後合併修改"}, 409)
                    return
                backup = PROJECT_DIR / ".handoff/html-backups" / uuid.uuid4().hex / html_path.name
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(raw)
                _atomic_write_text(html_path, content)
        except Exception as error:
            self._json({"ok": False, "error": str(error)}, 400)
            return

        self._json({
            "ok": True,
            "path": str(html_path),
            "revision": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "backup": str(backup.relative_to(PROJECT_DIR)),
            "bytes": len(content.encode("utf-8")),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def _serve_file(self, url_path):
        if url_path == "/":
            first = _first_prototype_html()
            if not first:
                self._json({"error": "原型目錄中沒有 HTML 檔案"}, 404)
                return
            url_path = _relative_url_path(first)

        file_path = (PROJECT_DIR / url_path.lstrip("/")).resolve()
        rel = Path(url_path.lstrip("/"))
        allowed_dirs = WRITABLE_SUBDIR_NAMES | {"原型截圖", "流程圖截圖", "assets", "scripts", "templates"}
        allowed_ext = {".html", ".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".woff", ".woff2"}
        allowed = (not any(part.startswith(".") for part in rel.parts)
                   and bool(allowed_dirs.intersection(rel.parts)) and file_path.suffix.lower() in allowed_ext)
        if not allowed or not _is_under(file_path, PROJECT_DIR) or not file_path.is_file():
            self.send_response(404)
            self._cors()
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        if not origin_allowed(self.headers.get("Origin"), PORT):
            self._json({"error": "來源不允許"}, 403)
            return
        if file_path.name == "pm-runtime-config.js":
            if (self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none")
                    and not self._local_referer()):
                self._json({"error": "配置僅供當前專案頁面使用"}, 403)
                return
            if READ_ONLY:
                body = b'window.PM_RUNTIME = {readOnly:true};'
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._cors(); self.end_headers(); self.wfile.write(body)
                return

        mime = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".json": "application/json; charset=utf-8",
            ".webp": "image/webp",
        }.get(file_path.suffix.lower(), "application/octet-stream")

        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)


class ThreadedHTTPServer(HTTPServer):
    def process_request(self, request, client_address):
        thread = threading.Thread(
            target=self._process_request_thread,
            args=(request, client_address),
            daemon=True,
        )
        thread.start()

    def _process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


class _AlreadyRunning(Exception):
    """本專案的服務已經在跑——不是故障，正常退出即可。"""


def _bind_server(attempts=8):
    """繫結連接埠；連接埠不可用就換一對重新推導並回寫配置，不永久佔坑。

    這裡按 OSError 統一兜底而不是匹配 "Address already in use"：
    Windows 上被 Hyper-V/WSL/Docker 保留的連接埠拋的是 WSAEACCES(10013)，
    表現為 PermissionError，錯誤文字里根本沒有那句英文。
    """
    global CONFIG, PORT, SERVER_URL
    for remaining in range(attempts, 0, -1):
        try:
            return ThreadedHTTPServer((BIND_HOST, PORT), Handler)
        except OSError as error:
            # 佔用者是本專案自己的服務時換連接埠毫無意義，會起出第二個服務。
            state = probe_health(PORT)
            if state and state.get("project_id") == CONFIG["project_id"]:
                raise _AlreadyRunning(PORT) from error
            if remaining == 1:
                raise
            print(f"  ⚠️  連接埠 {PORT} 不可用（{error}），正在換一個連接埠重試…", flush=True)
            # reroll_ports 內部會一併同步 LaunchAgent 登記的連接埠，這裡不用再管。
            CONFIG = reroll_ports(PROJECT_DIR, CONFIG)
            PORT = int(CONFIG["port"])
            SERVER_URL = f"http://127.0.0.1:{PORT}"


def main():
    os.chdir(PROJECT_DIR)
    server = _bind_server()

    first = _first_prototype_html()
    first_url = f"{SERVER_URL}{_relative_url_path(first)}" if first else SERVER_URL

    print(f"\n{'─' * 56}")
    print("  🚀 原型匯出服務已啟動")
    print(f"{'─' * 56}")
    print(f"  專案路徑：{PROJECT_DIR}")
    print(f"  原型預覽：{first_url}")
    print("  截圖輸出：")
    print("    [需求名]/原型/*.html  → [需求名]/原型截圖/")
    print("    [需求名]/流程圖/*.html → [需求名]/流程圖截圖/")
    print("    （舊扁平結構 原型/、流程圖/ 回退到專案根的 原型截圖/、流程圖截圖/）")
    print(f"{'─' * 56}")
    print("  👉 在瀏覽器裡開啟任一 [需求名]/原型/*.html 或 [需求名]/流程圖/*.html，點選匯出即可")
    print("  ⌃C  停止伺服器\n")

    # 改成顯式開啟：預設不再自動彈窗。此前每次啟動都會開啟「字典序第一」的那個
    # 原型頁，而那通常不是使用者正在做的需求。後台啟動的服務永遠不該彈瀏覽器。
    if os.environ.get("PM_OPEN_BROWSER") == "1" and first:
        def _open_browser():
            time.sleep(0.8)
            print("  🌐 正在開啟瀏覽器...\n")
            webbrowser.open(first_url)

        threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  ✅ 伺服器已停止\n")
        server.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except _AlreadyRunning as error:
        print(f"  ✅ 本專案的匯出服務已在執行：http://127.0.0.1:{error}")
