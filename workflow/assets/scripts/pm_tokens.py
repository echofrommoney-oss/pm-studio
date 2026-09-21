#!/usr/bin/env python3
"""把 DESIGN.md 開頭的設計 token 轉成程式用的檔案，讓設計只有一個來源。

  python3 scripts/pm_tokens.py dart --out app/lib/theme/tokens.dart      Flutter
  python3 scripts/pm_tokens.py css  --out web/admin/styles/tokens.css    網站（CSS 變數）
  python3 scripts/pm_tokens.py ts   --out mobile/src/theme/tokens.ts     React Native／TypeScript
  python3 scripts/pm_tokens.py show                                      只列出讀到的 token
不帶 --out 時：dart → app/lib/theme/tokens.dart、css → web/shared/tokens.css、ts → src/theme/tokens.ts。

支援的 DESIGN.md frontmatter 寫法：
  colors: { primary: "#1F3A5F", surface: "#FBFAF7" }     單行
  radius:                                                多行（縮排一層）
    sm: 4px
  density: 5                                             單一值
產生的檔案開頭會註明「請勿手改」；DESIGN.md 改了就重跑。
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _scalar(v):
    v = v.strip().strip(",").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _inline_map(text):
    body = text.strip()[1:-1]
    out, buf, quote = {}, "", None
    parts = []
    for ch in body:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf)
    for part in parts:
        k, sep, v = part.partition(":")
        if sep:
            out[k.strip()] = _scalar(v)
    return out


def read_tokens(path=None):
    path = Path(path or ROOT / "DESIGN.md")
    text = path.read_text(encoding="utf-8").replace("\r", "")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    lines = text[3:end].splitlines() if end > 0 else []
    tokens, current = {}, None
    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        indented = line[:1] in (" ", "\t")
        key, sep, value = line.strip().partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if indented and current is not None:
            tokens[current][key] = _scalar(value)
        elif value.startswith("{") and value.endswith("}"):
            tokens[key] = _inline_map(value)
            current = None
        elif value == "":
            tokens[key] = {}
            current = key
        else:
            tokens[key] = _scalar(value)
            current = None
    return tokens


def _camel(*parts):
    words = [w for p in parts for w in re.split(r"[-_\s.]+", str(p)) if w]
    if not words:
        return "token"
    name = words[0].lower() + "".join(w[:1].upper() + w[1:] for w in words[1:])
    if not re.match(r"^[A-Za-z_]", name):
        name = "t" + name
    return re.sub(r"[^A-Za-z0-9_]", "", name)


def _color(v):
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", v.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        h = "FF" + h
    else:  # RRGGBBAA → AARRGGBB
        h = h[6:] + h[:6]
    return f"Color(0x{h.upper()})"


def _number(v):
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(px|dp|ms)?", v.strip())
    return float(m.group(1)) if m else None


def flatten(tokens):
    for key, value in tokens.items():
        if key in ("name", "theme", "macrostructure"):
            continue
        if isinstance(value, dict):
            for sub, v in value.items():
                yield key, sub, v
        else:
            yield key, "", value


def to_dart(tokens):
    lines = ["// 由 scripts/pm_tokens.py 依 DESIGN.md 產生，請勿手改；DESIGN.md 改了就重跑。",
             "// ignore_for_file: constant_identifier_names", "",
             "import 'package:flutter/material.dart';", "",
             "class AppTokens {", "  AppTokens._();"]
    for group, sub, v in flatten(tokens):
        name = _camel(group, sub) if sub else _camel(group)
        color = _color(v) if isinstance(v, str) else None
        num = _number(v) if isinstance(v, str) else None
        if color:
            lines.append(f"  static const Color {name} = {color};")
        elif num is not None:
            lines.append(f"  static const double {name} = {num};")
        else:
            safe = str(v).replace("\\", "\\\\").replace("'", "\\'")
            lines.append(f"  static const String {name} = '{safe}';")
    lines += ["}", ""]
    return "\n".join(lines)


def to_css(tokens):
    lines = ["/* 由 scripts/pm_tokens.py 依 DESIGN.md 產生，請勿手改；DESIGN.md 改了就重跑。 */", ":root {"]
    for group, sub, v in flatten(tokens):
        name = "--" + "-".join(p for p in (group, sub) if p).replace("_", "-").lower()
        val = str(v)
        if group.lower().startswith("font") and "," not in val and not val.startswith(("'", '"')):
            val = f"'{val}', 'PingFang TC', 'Noto Sans TC', system-ui, sans-serif"
        lines.append(f"  {name}: {val};")
    lines += ["}", ""]
    return "\n".join(lines)


def to_ts(tokens):
    lines = ["// 由 scripts/pm_tokens.py 依 DESIGN.md 產生，請勿手改；DESIGN.md 改了就重跑。", "export const tokens = {"]
    groups = {}
    for group, sub, v in flatten(tokens):
        groups.setdefault(group, []).append((sub, v))
    for group, items in groups.items():
        if len(items) == 1 and not items[0][0]:
            v = items[0][1]
            num = _number(v) if isinstance(v, str) else None
            lines.append(f"  {_camel(group)}: {num if num is not None else json.dumps(str(v), ensure_ascii=False)},")
            continue
        lines.append(f"  {_camel(group)}: {{")
        for sub, v in items:
            num = _number(v) if isinstance(v, str) and not str(v).startswith("#") else None
            lines.append(f"    {_camel(sub)}: {num if num is not None else json.dumps(str(v), ensure_ascii=False)},")
        lines.append("  },")
    lines += ["} as const;", "", "export type Tokens = typeof tokens;", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="DESIGN.md → 設計 token")
    ap.add_argument("target", choices=["dart", "css", "ts", "show"])
    ap.add_argument("--design", default=str(ROOT / "DESIGN.md"))
    ap.add_argument("--out", help="輸出路徑（相對專案根目錄）")
    args = ap.parse_args()
    if not Path(args.design).is_file():
        print("找不到 DESIGN.md，先走「設計方向」建立。")
        return 1
    tokens = read_tokens(args.design)
    if not tokens:
        print("DESIGN.md 開頭沒有 --- 包起來的 token 區塊。")
        return 1
    if args.target == "show":
        for group, sub, v in flatten(tokens):
            print(f"{group}{'.' + sub if sub else ''} = {v}")
        return 0
    default = {"dart": "app/lib/theme/tokens.dart", "css": "web/shared/tokens.css", "ts": "src/theme/tokens.ts"}[args.target]
    out = (ROOT / args.out) if args.out else ROOT / default
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text({"dart": to_dart, "css": to_css, "ts": to_ts}[args.target](tokens), encoding="utf-8")
    print(f"已產生 {out.relative_to(ROOT)}（{sum(1 for _ in flatten(tokens))} 個 token）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
