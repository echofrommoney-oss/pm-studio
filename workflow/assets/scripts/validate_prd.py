#!/usr/bin/env python3
"""PRD 格式校驗（v2.9 工作流 §5.2 的第一步）。

用法：
    python3 validate_prd.py [需求名/需求文件/需求名-PRD.html ...]
    py -3 validate_prd.py …            # Windows 上沒有 python3 命令

不帶參數時，從當前目錄向下查詢所有 *-PRD.html 逐個校驗。
退出碼 0 = 全部通過；1 = 有檔案未通過；2 = 沒找到檔案。

校驗的是「機械可判定」的部分：章節獨立性、固定表頭與列數、
埋點命名、描述列分塊與逐條換行、data-preview 覆蓋、
文件級 style 位置、章節編號連續性。
視覺類檢查（遮擋、字號、配色統一）仍需人工按 §4.3 / §4.6 核對。
"""
import sys
import re
from pathlib import Path
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}

CORE_SECTIONS = ["專案資訊", "需求背景", "需求目標", "詳細方案"]

SCHEMAS = {
    "scheme-table":   ["一級模組", "二級功能", "原型", "描述"],
    "overview-table": ["模組", "一級功能", "說明"],
    "tracking-table": ["序號", "埋點名", "埋點中文名", "埋點型別", "埋點參數", "參數值"],
}

CN_NUM = "一二三四五六七八九十"


class Node:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def text(self):
        return "".join(x.text() if isinstance(x, Node) else x for x in self.children)

    def find(self, tag=None, css_class=None):
        result = []
        for child in self.children:
            if not isinstance(child, Node):
                continue
            if (tag is None or child.tag == tag) and (
                css_class is None or css_class in child.attrs.get("class", "").split()
            ):
                result.append(child)
            result.extend(child.find(tag, css_class))
        return result

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()


class Tree(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.current = self.root
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        node = self.current
        while node.parent and node.tag != tag:
            node = node.parent
        if node.parent:
            self.current = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


def _section_of(root):
    """Return a function mapping a node to the nearest preceding h2/h3 heading text."""
    heads = [(n, n.text().strip()) for n in root.walk() if n.tag in ("h2", "h3")]

    def lookup(node):
        found = ""
        for n, txt in heads:
            if n is node:
                break
            if n.tag == "h2":
                found = txt
        return found

    return lookup


def validate_prd(content):
    root = Tree(content).root
    h2 = [n.text().strip() for n in root.find("h2")]
    errors = []

    # ---- 1. 核心章節與獨立性 ----
    for name in CORE_SECTIONS:
        if not any(h.endswith(name) for h in h2):
            errors.append("缺少獨立章節：" + name)
    if any(("版本記錄" in h or "版本紀錄" in h or "修訂紀錄" in h or "變更紀錄" in h) for h in h2):
        errors.append("PRD 只保留最新版本，不設版本／修訂紀錄章節；最後更新日期寫在專案資訊")
    if any(("邊界" in h or "異常處理" in h) for h in h2):
        errors.append("不設獨立的異常/邊界章節；邊界情況寫進詳細方案描述列的【邊界說明】")

    # ---- 2. 章節編號連續性 ----
    numbered = []
    for h in h2:
        m = re.match(r"^([一二三四五六七八九十]+)、", h)
        if m:
            numbered.append((m.group(1), h))
    expected = list(CN_NUM[: len(numbered)])
    actual = [n for n, _ in numbered]
    if actual and actual != expected:
        errors.append("章節編號不連續（應從 一 開始順排）：實際為 " + "、".join(actual))

    # ---- 3. 固定表頭與列數 ----
    for css, expect in SCHEMAS.items():
        tables = root.find("table", css)
        required = css in {"scheme-table"} or any(
            ("資料埋點" in h if css == "tracking-table"
             else "需求概述" in h if css == "overview-table" else False)
            for h in h2
        )
        if required and not tables:
            errors.append("缺少規範表格：" + css)
        for table in tables:
            rows = table.find("tr")
            if not rows:
                errors.append(css + " 沒有表頭行")
                continue
            heads = [c.text().strip() for c in rows[0].children
                     if isinstance(c, Node) and c.tag == "th"]
            if heads != expect:
                errors.append(css + " 表頭必須為：" + "、".join(expect) + "（實際：" + "、".join(heads) + "）")

    # ---- 3.5 只留最新版：不得殘留修改痕跡 ----
    body_text = root.text()
    if root.find("del") or root.find("s") or root.find("strike"):
        errors.append("正文有刪除線（del/s/strike）；舊內容應直接刪除，不留痕跡")
    for mark in ("（已修改）", "（已刪除）", "（新增）", "（已更新）", "【已修改】", "【新增】", "原為：", "舊版：", "修改前："):
        if mark in body_text:
            errors.append("正文殘留修改標記「" + mark + "」；只寫最新結論")
            break
    if "已確認：" in body_text:
        errors.append("待確認清單殘留「已確認：」條目；確認後把結論寫進正文並刪除該條")

    # ---- 4. 專案資訊必須獨立雙列表 ----
    meta = root.find("table", "meta-table")
    if not meta:
        errors.append("專案資訊應使用獨立 meta-table")
    else:
        for table in meta:
            for row in table.find("tr"):
                cells = [c for c in row.children if isinstance(c, Node) and c.tag in ("td", "th")]
                if len(cells) != 2:
                    errors.append("專案資訊應為雙列（欄位 | 值）")
                    break

    # ---- 5. 詳細方案：data-preview / 原型列 / 描述列 ----
    for table in root.find("table", "scheme-table"):
        rows = table.find("tr")
        for row in rows[1:]:
            cells = [c for c in row.children if isinstance(c, Node) and c.tag == "td"]
            if not cells:
                continue
            if "data-preview" not in row.attrs:
                errors.append("詳細方案每行必須帶 data-preview（供雙欄滾動聯動）")
            if len(cells) >= 3:
                proto = cells[-2]
                has_media = bool(proto.find("img") or proto.find("iframe"))
                if not has_media:
                    errors.append("原型列必須有內容（img.proto-shot 或可互動 iframe）")
            if "desc" not in cells[-1].attrs.get("class", "").split():
                errors.append("功能行末列應為 desc 描述單元格")
        for cell in table.find("td", "desc"):
            text = cell.text()
            if not all(label in text for label in ("【頁面元素】", "【互動說明】")):
                errors.append("每個描述單元格必須包含【頁面元素】和【互動說明】")
            if not cell.find(css_class="desc-block"):
                errors.append("描述應使用 desc-block 分塊並逐條換行（不要用 <br> 硬換行）")
            for block in cell.find(css_class="desc-block"):
                items = [n for n in block.children
                         if isinstance(n, Node) and n.tag in ("p", "ol", "ul")]
                if not items:
                    errors.append("描述分塊需要獨立段落或列表")
            for line in cell.find("p") + cell.find("li"):
                if len(re.findall(r"(?:^|\s|[；;])\d+[、．.]", line.text())) > 1:
                    errors.append("每個元素或互動必須獨立成段（多個編號不能擠在一句裡）")
            if cell.find("br"):
                errors.append("描述列不要用 <br> 硬換行，改用獨立 <p>")

    # ---- 6. 埋點命名與列數 ----
    for table in root.find("table", "tracking-table"):
        rows = table.find("tr")
        for row in rows[1:]:
            cells = [c for c in row.children if isinstance(c, Node) and c.tag == "td"]
            if not cells:
                continue
            if len(cells) != 6:
                errors.append("埋點表每行必須有六列（缺的格寫「待確認（使用者提供參考）」，不要留空）")
                continue
            event = cells[1].text().strip()
            if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", event) or len(event) > 48:
                errors.append("埋點名需要簡短英文 snake_case：" + event)

    # ---- 7. 文件級 style 必須在 #prdContent 內（一鍵複製全文才帶得走樣式）----
    # 只做"存在性"判定：<head> 放公共骨架樣式、正文樣式放 <main> 內是正常分工，
    # 但 #prdContent 內必須至少有一份正文樣式，否則複製出去的正文會掉格式。
    main_nodes = [m for m in root.find("main") if m.attrs.get("id") == "prdContent"]
    if not main_nodes:
        errors.append("缺少 <main id=\"prdContent\"> 正文容器")
    elif not any(m.find("style") for m in main_nodes):
        errors.append("#prdContent 內沒有正文 <style>；一鍵複製全文會丟掉正文排版樣式")

    # ---- 8. 需求目標不應是任務清單 ----
    goal_tables = root.find("table", "goal-table")
    for tbl in goal_tables:
        rows = tbl.find("tr")
        heads = [c.text().strip() for c in rows[0].children
                 if isinstance(c, Node) and c.tag == "th"] if rows else []
        if heads != ["使用者結果", "衡量指標", "統計口徑", "預期方向", "目標值"]:
            errors.append("goal-table 表頭必須為：使用者結果、衡量指標、統計口徑、預期方向、目標值")

    if errors:
        raise ValueError("PRD 格式檢查未通過：\n" + "\n".join(dict.fromkeys(errors)))
    return True


def main(argv):
    if len(argv) > 1:
        files = [Path(p) for p in argv[1:]]
    else:
        # 預設只掃 `[需求名]/需求文件/*-PRD.html`——專案裡的歷史 PRD / 分享原始檔 /
        # 需求挖掘目錄下的舊稿不按本規範撰寫，掃進來只會製造噪音。
        files = sorted(Path.cwd().glob("*/需求文件/*-PRD.html"))
        if not files:
            files = sorted(Path.cwd().glob("*-PRD.html"))
    if not files:
        print("沒有找到 *-PRD.html（可顯式傳入路徑，或在本專案根目錄執行）")
        return 2

    failed = 0
    for path in files:
        try:
            validate_prd(path.read_text(encoding="utf-8"))
            print("PASS  " + str(path))
        except ValueError as exc:
            failed += 1
            print("FAIL  " + str(path))
            for line in str(exc).splitlines()[1:]:
                print("      " + line)
        except OSError as exc:
            failed += 1
            print("ERROR " + str(path) + " —— " + str(exc))
    print("\n共 %d 個檔案，%d 個未通過。" % (len(files), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
