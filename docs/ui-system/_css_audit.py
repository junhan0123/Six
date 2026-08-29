# -*- coding: utf-8 -*-
"""
Formal UI System Consolidation v1.0 — Section 2 取证脚本
真实读盘解析全部 CSS，产出选择器/令牌/硬编码/分叉证据。
只读，不修改任何源文件。
"""
import re, os, json, collections

UI = r"G:\Xiao6\xiao6-ui"
FILES = [
    "styles.css",
    "premium.css",
    "runtime-viz.css",
    "execution-channel.css",
    "ui2.css",
    "companion.css",
]

def strip_comments(text):
    # 保留位置：把注释替换为等长空白，保证行号不偏移
    def repl(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r"/\*.*?\*/", repl, text, flags=re.S)

def parse(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    text = strip_comments(raw)
    lines = text.split("\n")
    # 记录每个字符偏移对应行号
    offs, acc = [], 0
    for ln in lines:
        offs.append(acc)
        acc += len(ln) + 1
    def line_of(pos):
        lo, hi = 0, len(offs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offs[mid] <= pos: lo = mid
            else: hi = mid - 1
        return lo + 1

    rules = []          # (selector_text, line, body, media)
    media_stack = []
    i, n = 0, len(text)
    buf_start = 0
    while i < n:
        ch = text[i]
        if ch == "{":
            head = text[buf_start:i].strip()
            if head.startswith("@"):
                # at-rule with block
                at = head.split("{")[0].strip()
                if at.lower().startswith(("@media", "@supports", "@container")):
                    media_stack.append((at, i))
                    i += 1; buf_start = i
                    continue
                else:
                    # @keyframes / @font-face 等：整块跳过但记录
                    depth = 1; j = i + 1
                    while j < n and depth:
                        if text[j] == "{": depth += 1
                        elif text[j] == "}": depth -= 1
                        j += 1
                    rules.append((at, line_of(i), text[i+1:j-1], " ".join(a for a, _ in media_stack)))
                    i = j; buf_start = i
                    continue
            # 普通规则
            depth = 1; j = i + 1
            while j < n and depth:
                if text[j] == "{": depth += 1
                elif text[j] == "}": depth -= 1
                j += 1
            body = text[i+1:j-1]
            rules.append((head, line_of(i), body, " ".join(a for a, _ in media_stack)))
            i = j; buf_start = i
            continue
        elif ch == "}":
            if media_stack: media_stack.pop()
            i += 1; buf_start = i
            continue
        i += 1
    return raw, rules

report = {}
all_sel = collections.defaultdict(list)   # 单个选择器 -> [(file, line, media)]
token_defs = collections.defaultdict(list)  # --var -> [(file, line, value)]
hardcode = collections.defaultdict(lambda: collections.Counter())

COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)")
PROP_RE = re.compile(r"(^|;)\s*([-a-zA-Z]+)\s*:\s*([^;]+)", re.S)

for f in FILES:
    p = os.path.join(UI, f)
    if not os.path.exists(p):
        report[f] = {"missing": True}; continue
    raw, rules = parse(p)
    sel_count = 0
    props = collections.Counter()
    file_hard = collections.Counter()
    kf = []
    for head, line, body, media in rules:
        if head.startswith("@keyframes") or head.startswith("@-webkit-keyframes"):
            kf.append((head.split()[-1], line)); continue
        if head.startswith("@"):
            continue
        for s in head.split(","):
            s = " ".join(s.split())
            if not s: continue
            sel_count += 1
            all_sel[s].append((f, line, media))
            if s == ":root" or s.startswith(":root"):
                for m in PROP_RE.finditer(body):
                    name, val = m.group(2), m.group(3).strip()
                    if name.startswith("--"):
                        token_defs[name].append((f, line, " ".join(val.split())))
        # 硬编码统计（排除 :root 变量声明本身）
        for m in PROP_RE.finditer(body):
            name, val = m.group(2), " ".join(m.group(3).split())
            props[name] += 1
            if name.startswith("--"):
                continue
            if "var(" in val:
                continue
            for c in COLOR_RE.findall(val):
                file_hard["color:" + c.lower()] += 1
            if name in ("border-radius", "font-family", "box-shadow", "font-size",
                        "font-weight", "transition", "letter-spacing", "z-index"):
                file_hard[name + " = " + val[:60]] += 1
    hardcode[f] = file_hard
    report[f] = {
        "bytes": os.path.getsize(p),
        "lines": raw.count("\n") + 1,
        "rule_blocks": len(rules),
        "selectors": sel_count,
        "keyframes": kf,
        "top_props": props.most_common(15),
        "hardcode_total": sum(file_hard.values()),
    }

# 跨文件重复选择器
dupes = {}
for s, locs in all_sel.items():
    files = {l[0] for l in locs}
    if len(files) > 1:
        dupes[s] = locs

# 同文件重复（>=3 次，可能是散落定义）
same_file_multi = {}
for s, locs in all_sel.items():
    c = collections.Counter(l[0] for l in locs)
    for f, k in c.items():
        if k >= 3:
            same_file_multi.setdefault(s, []).append((f, k))

# 令牌多处定义
token_conflicts = {k: v for k, v in token_defs.items() if len({x[0] for x in v}) > 1 or len(v) > 1}

out = {
    "files": report,
    "total_selectors": sum(len(v) for v in all_sel.values()),
    "unique_selectors": len(all_sel),
    "cross_file_dupes": len(dupes),
    "token_count_by_file": {f: sum(1 for k, v in token_defs.items() if any(x[0] == f for x in v)) for f in FILES},
}
print(json.dumps(out, ensure_ascii=False, indent=2))

with open(os.path.join(r"G:\Xiao6\docs\ui-system", "_css_audit.json"), "w", encoding="utf-8") as fh:
    json.dump({
        "summary": out,
        "cross_file_dupes": {k: v for k, v in sorted(dupes.items())},
        "same_file_multi": same_file_multi,
        "token_defs": token_defs,
        "token_conflicts": token_conflicts,
        "hardcode": {f: dict(c.most_common(80)) for f, c in hardcode.items()},
    }, fh, ensure_ascii=False, indent=2)
print("\nWROTE _css_audit.json")
