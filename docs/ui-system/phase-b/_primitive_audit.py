# -*- coding: utf-8 -*-
"""
Formal UI System v1.0 · Phase B — Primitive Consolidation 取证脚本
真实读盘解析全部 CSS，对第一优先级 8 类原语逐条列出定义位置与声明内容。
只读，不修改任何源文件。
"""
import re, os, json, collections

UI = r"G:\Xiao6\xiao6-ui"
OUT = r"G:\Xiao6\docs\ui-system\phase-b"
FILES = [
    "styles.css",
    "premium.css",
    "runtime-viz.css",
    "execution-channel.css",
    "ui2.css",
    "companion.css",
]

# 加载顺序（index.html 实测），companion.html 独立文档
LOAD_ORDER = {
    "styles.css": 1,
    "premium.css": 2,
    "runtime-viz.css": 3,
    "execution-channel.css": 4,
    "ui2.css": 5,
    "companion.css": 99,
}

# 第一优先级 8 类原语：名称 -> 匹配用的 class token 正则
PRIMITIVES = {
    "P1_button":      r"\.(btn|btn-new|zz-btn)\b",
    "P2_glass_panel": r"\.glass-panel\b",
    "P3_card":        r"\.[a-z0-9-]*card\b",
    "P4_input":       r"\.[a-z0-9-]*input\b|\.zz-select\b|\.settings-textarea\b",
    "P5_chip":        r"\.[a-z0-9-]*chip\b",
    "P6_badge":       r"\.[a-z0-9-]*badge\b",
    "P7_modal":       r"\.[a-z0-9-]*(modal|dialog)\b",
    "P8_icon":        r"\.(ic|zz-icon)\b|\.ic-[a-z0-9-]+\b|\.[a-z0-9-]*icon\b",
}


def strip_comments(text):
    def repl(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r"/\*.*?\*/", repl, text, flags=re.S)


def parse(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    text = strip_comments(raw)
    lines = text.split("\n")
    offs, acc = [], 0
    for ln in lines:
        offs.append(acc)
        acc += len(ln) + 1

    def line_of(pos):
        lo, hi = 0, len(offs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offs[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    rules = []
    media_stack = []
    i, n = 0, len(text)
    buf_start = 0
    while i < n:
        ch = text[i]
        if ch == "{":
            head = text[buf_start:i].strip()
            if head.startswith("@"):
                at = head.split("{")[0].strip()
                if at.lower().startswith(("@media", "@supports", "@container")):
                    media_stack.append((at, i))
                    i += 1
                    buf_start = i
                    continue
                depth = 1
                j = i + 1
                while j < n and depth:
                    if text[j] == "{":
                        depth += 1
                    elif text[j] == "}":
                        depth -= 1
                    j += 1
                rules.append((at, line_of(i), text[i + 1:j - 1],
                              " ".join(a for a, _ in media_stack)))
                i = j
                buf_start = i
                continue
            depth = 1
            j = i + 1
            while j < n and depth:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            body = text[i + 1:j - 1]
            rules.append((head, line_of(i), body,
                          " ".join(a for a, _ in media_stack)))
            i = j
            buf_start = i
            continue
        elif ch == "}":
            if media_stack:
                media_stack.pop()
            i += 1
            buf_start = i
            continue
        i += 1
    return raw, rules


PROP_RE = re.compile(r"(^|;)\s*([-a-zA-Z]+)\s*:\s*([^;]+)", re.S)
# 结构性属性（D-03 约束：premium.css 不得覆盖）
STRUCTURAL = {
    "display", "position", "top", "right", "bottom", "left", "width", "height",
    "min-width", "min-height", "max-width", "max-height", "flex", "flex-direction",
    "grid", "grid-template-columns", "grid-template-rows", "float", "box-sizing",
    "overflow", "overflow-x", "overflow-y", "z-index", "inset",
}


def decls(body):
    out = []
    for m in PROP_RE.finditer(body):
        name = m.group(2).strip()
        val = " ".join(m.group(3).split())
        out.append((name, val))
    return out


parsed = {}
for f in FILES:
    p = os.path.join(UI, f)
    if not os.path.exists(p):
        continue
    parsed[f] = parse(p)

# ---------- 1. 8 类原语逐条取证 ----------
prim_report = {}
for pname, pat in PRIMITIVES.items():
    rx = re.compile(pat)
    hits = []
    for f, (raw, rules) in parsed.items():
        for head, line, body, media in rules:
            if head.startswith("@"):
                continue
            for s in head.split(","):
                s = " ".join(s.split())
                if not s:
                    continue
                if rx.search(s):
                    d = decls(body)
                    hits.append({
                        "file": f,
                        "load": LOAD_ORDER.get(f, 0),
                        "line": line,
                        "selector": s,
                        "media": media,
                        "decl_count": len(d),
                        "decls": d,
                        "structural": sorted({k for k, _ in d} & STRUCTURAL),
                        "hardcoded": [f"{k}:{v}" for k, v in d
                                      if "var(" not in v and not k.startswith("--")
                                      and re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|\d+px|\d+em|\d+rem", v)],
                    })
    # 按 selector 分组，找真重复
    by_sel = collections.defaultdict(list)
    for h in hits:
        by_sel[h["selector"]].append(h)
    cross = {s: v for s, v in by_sel.items() if len({x["file"] for x in v}) > 1}
    same = {s: v for s, v in by_sel.items()
            if len(v) > 1 and len({x["file"] for x in v}) == 1}
    prim_report[pname] = {
        "pattern": pat,
        "total_rules": len(hits),
        "by_file": dict(collections.Counter(h["file"] for h in hits)),
        "unique_selectors": len(by_sel),
        "cross_file_dupe_selectors": sorted(cross.keys()),
        "cross_file_dupes": cross,
        "same_file_dupe_selectors": sorted(same.keys()),
        "hits": hits,
    }

# ---------- 2. 全仓跨文件重复选择器（Phase B 验收口径：≤5 组） ----------
all_sel = collections.defaultdict(list)
for f, (raw, rules) in parsed.items():
    for head, line, body, media in rules:
        if head.startswith("@"):
            continue
        for s in head.split(","):
            s = " ".join(s.split())
            if s:
                all_sel[s].append({"file": f, "line": line, "media": media})

cross_all = {s: v for s, v in all_sel.items() if len({x["file"] for x in v}) > 1}

# ---------- 3. premium.css 三条约束核查 ----------
prem_tokens = []
prem_structural_overrides = []
ui2_selectors = set()
for f, (raw, rules) in parsed.items():
    if f != "ui2.css":
        continue
    for head, line, body, media in rules:
        if head.startswith("@"):
            continue
        for s in head.split(","):
            s = " ".join(s.split())
            if s:
                ui2_selectors.add(s)

if "premium.css" in parsed:
    raw, rules = parsed["premium.css"]
    for head, line, body, media in rules:
        if head.startswith("@"):
            continue
        d = decls(body)
        for k, v in d:
            if k.startswith("--"):
                prem_tokens.append({"line": line, "sel": head, "token": k, "value": v})
        st = sorted({k for k, _ in d} & STRUCTURAL)
        if st:
            for s in head.split(","):
                s = " ".join(s.split())
                if s in ui2_selectors:
                    prem_structural_overrides.append(
                        {"line": line, "selector": s, "structural_props": st})

summary = {
    "generated": "phase-b primitive audit",
    "files_parsed": {f: {"rules": len(r[1]),
                         "bytes": os.path.getsize(os.path.join(UI, f))}
                     for f, r in parsed.items()},
    "cross_file_dupe_groups_total": len(cross_all),
    "premium_token_count": len(prem_tokens),
    "premium_structural_overrides_on_ui2_selectors": len(prem_structural_overrides),
    "primitives": {k: {"total_rules": v["total_rules"],
                       "by_file": v["by_file"],
                       "unique_selectors": v["unique_selectors"],
                       "cross_file_dupe_count": len(v["cross_file_dupe_selectors"]),
                       "cross_file_dupe_selectors": v["cross_file_dupe_selectors"]}
                   for k, v in prim_report.items()},
}

print(json.dumps(summary, ensure_ascii=False, indent=2))

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "_primitive_audit.json"), "w", encoding="utf-8") as fh:
    json.dump({
        "summary": summary,
        "primitives": prim_report,
        "cross_file_dupes_all": {k: v for k, v in sorted(cross_all.items())},
        "premium_tokens": prem_tokens,
        "premium_structural_overrides": prem_structural_overrides,
    }, fh, ensure_ascii=False, indent=2)
print("\nWROTE phase-b/_primitive_audit.json")
