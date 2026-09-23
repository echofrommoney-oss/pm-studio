"""PM 工作台 · QA（第四階段）。

每個服務怎麼跑測試：
  · flutter：flutter test --machine（讀它的 JSON 事件）
  · supabase：supabase test db（讀 TAP 輸出）
  · 其他任何技術：ARCHITECTURE.md services 的 test（測試指令）＋ test_report（JUnit XML 報告位置）
JUnit XML 是幾乎所有測試工具都能輸出的共通格式，工作台只要讀它就能顯示任何技術的結果。

測試名稱帶驗收標記就能對到驗收清單：
  [驗收 需求名:驗收項ID]      例如 [驗收 疫苗提醒:提醒-新增-1]
結果只保留最新一次，存在 .pm-console/qa/（歷史由 git 與 CI 負責）。
"""
import glob
import json
import os
import re
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pm_dev

ROOT = None
DATA = None
RUNNING = {}
TAG = re.compile(r"\[驗收\s+([^:\]]+):([^\]]+)\]")
ATTACH = re.compile(r"\[\[ATTACHMENT\|([^\]]+)\]\]")


def init(root, data):
    global ROOT, DATA
    ROOT, DATA = Path(root), Path(data)


def _svc(project_id, sid):
    import pm_services
    return next((s for s in pm_services.services(project_id) if s["id"] == sid), None)


def testable(svc):
    return svc["adapter"] in ("flutter", "supabase") or bool(svc.get("test"))


def _tags(name):
    return [{"req": r.strip(), "id": i.strip()} for r, i in TAG.findall(name or "")]


# ───────────── 解析 ─────────────

def parse_junit(paths):
    tests = []
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        for case in root.iter("testcase"):
            name = case.get("name", "")
            cls = case.get("classname", "")
            status, message, details = "passed", "", ""
            for tag, st in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
                el = case.find(tag)
                if el is not None:
                    status = st
                    message = (el.get("message") or "").strip()
                    details = (el.text or "").strip()
                    break
            out = " ".join((x.text or "") for x in case.findall("system-out")) + " " + details
            shots = [a.strip() for a in ATTACH.findall(out)]
            tests.append({"name": name, "suite": cls, "file": case.get("file", ""), "status": status,
                          "duration": float(case.get("time") or 0), "message": message[:2000],
                          "details": details[:6000], "screenshots": shots[:4], "acceptance": _tags(f"{cls} {name}")})
    return tests


def parse_flutter(lines):
    names, tests = {}, {}
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        t = ev.get("type")
        if t == "testStart":
            test = ev.get("test", {})
            names[test.get("id")] = (test.get("name", ""), test.get("url") or test.get("root_url") or "")
        elif t == "error":
            tid = ev.get("testID")
            tests.setdefault(tid, {}).setdefault("errors", []).append((ev.get("error") or "") + "\n" + (ev.get("stackTrace") or ""))
        elif t == "testDone" and not ev.get("hidden"):
            tid = ev.get("testID")
            rec = tests.setdefault(tid, {})
            res = ev.get("result")
            rec["status"] = "skipped" if ev.get("skipped") else {"success": "passed", "failure": "failed", "error": "error"}.get(res, "error")
            rec["done"] = True
    out = []
    for tid, rec in tests.items():
        if not rec.get("done"):
            continue
        name, url = names.get(tid, ("", ""))
        errs = "\n".join(rec.get("errors", []))
        out.append({"name": name, "suite": "", "file": url.replace("file://", "").replace(str(ROOT) + "/", ""),
                    "status": rec["status"], "duration": 0, "message": errs.split("\n")[0][:2000], "details": errs[:6000],
                    "screenshots": [], "acceptance": _tags(name)})
    return out


def parse_tap(lines):
    out = []
    for line in lines:
        m = re.match(r"^\s*(not ok|ok)\s+\d+\s*-?\s*(.*?)(\s+#\s*(SKIP|TODO).*)?$", line)
        if m:
            status = "skipped" if m.group(4) else ("passed" if m.group(1) == "ok" else "failed")
            out.append({"name": m.group(2), "suite": "資料庫", "file": "supabase/tests", "status": status, "duration": 0,
                        "message": "", "details": "", "screenshots": [], "acceptance": _tags(m.group(2))})
    return out


# ───────────── 執行 ─────────────

def run(project_id, sid):
    import pm_services
    svc = _svc(project_id, sid)
    if not svc:
        raise ValueError("沒有這個服務")
    if not testable(svc):
        raise RuntimeError(f"「{svc['label']}」還沒設定怎麼跑測試：在 ARCHITECTURE.md 的 services 補 test 與 test_report（請按「系統設計」）。")
    if RUNNING.get(sid):
        raise RuntimeError("這個服務的測試正在跑")
    RUNNING[sid] = True
    key = "qa-" + sid

    def job():
        started = time.time()
        folder = ROOT / svc["dir"] if svc["dir"] else ROOT
        env = dict(os.environ, CI="1", FORCE_COLOR="0", NO_COLOR="1")
        vars_ = pm_services.variables(project_id)
        env.update({k: pm_services.render(str(v).replace("{port}", str(svc["port"])), vars_) for k, v in svc["env"].items()})
        env.update({k: v for k, v in vars_.items() if isinstance(v, str)})
        lines, tests, code = [], [], -1
        try:
            if svc.get("depends_on") and not pm_services._start_deps(project_id, svc, key):
                pm_dev.log(key, "依賴的服務沒有就緒，測試不執行。")
                RUNNING.pop(sid, None)
                return
            if svc["adapter"] == "flutter" and not svc.get("test"):
                cmd = [pm_dev.which("flutter") or "flutter", "test", "--machine"]
                shell = False
            elif svc["adapter"] == "supabase" and not svc.get("test"):
                cmd = [pm_dev.which("supabase") or "supabase", "test", "db"]
                shell = False
            else:
                cmd = pm_services.render(svc["test"].replace("{port}", str(svc["port"])), vars_)
                shell = True
                report = svc.get("test_report") or ""
                for old in glob.glob(str(folder / report)) if report else []:
                    try:
                        if old.endswith(".xml"):
                            os.remove(old)
                    except OSError:
                        pass
            pm_dev.log(key, "$ " + (cmd if isinstance(cmd, str) else " ".join(Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd))))
            proc = subprocess.Popen(cmd, cwd=str(folder), env=env, shell=shell, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=(os.name != "nt"))
            for raw in proc.stdout:
                text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", raw.decode("utf-8", "replace")).rstrip()
                lines.append(text)
                if not (svc["adapter"] == "flutter" and text.startswith("{")):
                    pm_dev.log(key, text)
            code = proc.wait()
            if svc["adapter"] == "flutter" and not svc.get("test"):
                tests = parse_flutter(lines)
            elif svc["adapter"] == "supabase" and not svc.get("test"):
                tests = parse_tap(lines)
            else:
                report = svc.get("test_report") or ""
                paths = sorted(glob.glob(str(folder / report))) if report else []
                if report and not paths:
                    paths = sorted(glob.glob(str(folder / report / "*.xml")))
                tests = parse_junit(paths)
                if not paths:
                    pm_dev.log(key, f"⚠️ 找不到測試報告 {report or '（沒有設定 test_report）'}，請確認測試工具有輸出 JUnit XML。")
            for t in tests:
                t["service"], t["service_label"] = sid, svc["label"]
                t["screenshots"] = [_rel(folder, s) for s in t["screenshots"] if _rel(folder, s)]
        except Exception as e:
            pm_dev.log(key, f"測試執行失敗：{e}")
        result = {"service": sid, "label": svc["label"], "started": started, "finished": time.time(), "exit_code": code,
                  "tests": tests, "summary": _summary(tests)}
        (DATA / "qa").mkdir(parents=True, exist_ok=True)
        (DATA / "qa" / f"{sid}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        s = result["summary"]
        pm_dev.log(key, f"完成：通過 {s['passed']}、失敗 {s['failed']}、略過 {s['skipped']}（結束代碼 {code}）")
        RUNNING.pop(sid, None)

    threading.Thread(target=job, daemon=True).start()


def _rel(folder, path):
    p = Path(path)
    p = p if p.is_absolute() else (folder / p)
    try:
        p = p.resolve()
        return p.relative_to(ROOT).as_posix() if p.is_file() else ""
    except (ValueError, OSError):
        return ""


def _summary(tests):
    s = {"passed": 0, "failed": 0, "skipped": 0, "total": len(tests)}
    for t in tests:
        s["failed" if t["status"] in ("failed", "error") else t["status"]] += 1
    return s


# ───────────── 驗收清單對照 ─────────────

ID_ATTR = re.compile(r'<(\w+)([^>]*?\b(?:data-id|data-ac|data-item|data-acceptance)\s*=\s*"([^"]+)"[^>]*)>', re.I)


def _inner_text(html, tag, start):
    """從開始標籤之後取到對應的結束標籤（會處理同名標籤的巢狀）。"""
    depth, i = 1, start
    open_tag = re.compile(r"<" + tag + r"\b", re.I)
    close_tag = re.compile(r"</" + tag + r"\s*>", re.I)
    while depth and i < len(html):
        o, c = open_tag.search(html, i), close_tag.search(html, i)
        if not c:
            break
        if o and o.start() < c.start():
            depth += 1
            i = o.end()
        else:
            depth -= 1
            i = c.end()
            if not depth:
                text = html[start:c.start()]
                text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
                return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
    return ""


def acceptance_files(req):
    folder = ROOT / req / "驗收清單"
    return sorted(folder.glob("*.html")) if folder.is_dir() else []


JS_ID = re.compile(r"""['"]?(?:id|acId|dataId|data_id)['"]?\s*:\s*(['"])(?P<id>[^'"]+)\1""")
JS_TEXT = re.compile(r"""['"]?(?:title|text|name|desc|description|item|label|檢查項目|驗收項|說明)['"]?\s*:\s*(['"`])(?P<t>(?:\\.|(?!\1).)*)\1""")


def _js_objects(html):
    """把原始碼裡看起來像驗收項的物件抓出來，連巢狀的也要（模組底下才是驗收項）。
    回傳 [(巢狀深度, 編號, 描述)]。"""
    out = []
    for m in JS_ID.finditer(html):
        ac_id = m.group("id").strip()
        if not ac_id or "${" in ac_id or not re.search(r"[\w\u4e00-\u9fff]", ac_id):
            continue
        start = html.rfind("{", 0, m.start())
        if start < 0:
            continue
        depth, i = 1, start + 1
        while depth and i < len(html) and i - start < 20000:
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
            i += 1
        obj = html[start:i]
        # 這個物件裡面還有帶 id 的子物件 → 它是分類（模組），不是驗收項
        inner = [x for x in JS_ID.finditer(obj) if x.start() != m.start() - start]
        t = JS_TEXT.search(obj)
        text = re.sub(r"\s+", " ", (t.group("t") if t else "")).strip()
        out.append({"id": ac_id, "text": text[:120], "container": bool(inner)})
    return out


def acceptance_items(req):
    """從驗收清單讀出驗收項（編號與文字）。
    先讀 HTML 裡的 data-id（也認 data-ac / data-item / data-acceptance）；
    項目是用 JavaScript 動態產生時，改從原始碼的資料陣列讀。"""
    items, seen = [], set()
    for f in acceptance_files(req):
        html = f.read_text(encoding="utf-8", errors="ignore")
        found = []
        for m in ID_ATTR.finditer(html):
            ac_id = m.group(3).strip()
            if "${" in ac_id or "{{" in ac_id:     # 樣板變數，不是真的編號
                continue
            found.append({"id": ac_id, "text": _inner_text(html, m.group(1), m.end())})
        if len(found) <= 1:                        # 靜態幾乎沒有 → 多半是動態產生
            objs = _js_objects(html)
            leaves = [o for o in objs if not o["container"]]
            found = leaves or objs or found        # 只取最內層：模組標題不是驗收項
        for it in found:
            if it["id"] and it["id"] not in seen:
                seen.add(it["id"])
                items.append({"id": it["id"], "text": it["text"][:120]})
    return items


def results(project_id, req=None):
    import pm_services
    svcs = pm_services.services(project_id)
    runs = []
    for s in svcs:
        data = None
        try:
            data = json.loads((DATA / "qa" / f"{s['id']}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        runs.append({"id": s["id"], "label": s["label"], "adapter": s["adapter"], "testable": testable(s),
                     "running": bool(RUNNING.get(s["id"])), "last": ({k: data[k] for k in ("started", "finished", "exit_code", "summary")}
                                                                    if data else None),
                     "tests": data["tests"] if data else []})
    out = {"services": [{k: v for k, v in r.items() if k != "tests"} for r in runs]}
    all_tests = [t for r in runs for t in r["tests"]]
    if req:
        mine = [t for t in all_tests if any(a["req"] == req for a in t["acceptance"])]
        items = acceptance_items(req)
        out["acceptance_files"] = [f.relative_to(ROOT).as_posix() for f in acceptance_files(req)]
        cover = []
        for it in items:
            linked = [t for t in mine if any(a["req"] == req and a["id"] == it["id"] for a in t["acceptance"])]
            st = "none" if not linked else ("failed" if any(t["status"] in ("failed", "error") for t in linked)
                                             else "passed" if all(t["status"] == "passed" for t in linked) else "partial")
            cover.append({**it, "state": st, "tests": [t["name"] for t in linked]})
        known = {it["id"] for it in items}
        orphan = sorted({a["id"] for t in mine for a in t["acceptance"] if a["req"] == req and a["id"] not in known})
        out.update({"acceptance": cover, "req_tests": mine, "orphan_tags": orphan,
                    "other_failed": [t for t in all_tests if t not in mine and t["status"] in ("failed", "error")]})
        # 規格比測試結果新 → 提醒結果可能過時
        spec = [f for f in (ROOT / req / "技術規格").glob("*.md")] if (ROOT / req / "技術規格").is_dir() else []
        prd = [f for f in (ROOT / req / "需求文件").glob("*.html")] if (ROOT / req / "需求文件").is_dir() else []
        newest_doc = max([f.stat().st_mtime for f in spec + prd] or [0])
        finished = [r["last"]["finished"] for r in runs if r["last"]]
        out["stale"] = bool(finished) and newest_doc > max(finished)
    return out


def file_bytes(rel):
    p = (ROOT / rel).resolve()
    if not str(p).startswith(str(ROOT)) or p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp") or not p.is_file():
        raise ValueError("不允許的檔案")
    return p.read_bytes(), "image/png" if p.suffix.lower() == ".png" else "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/webp"
