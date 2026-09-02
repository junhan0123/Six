# -*- coding: utf-8 -*-
"""DOM + JS 层 UI 盘点（只读）：提取 index.html 结构骨架与 JS 的 UI 生产者。"""
import re, os, json, collections

UI = r"G:\Xiao6\xiao6-ui"
html = open(os.path.join(UI, "index.html"), encoding="utf-8", errors="replace").read()

# 去注释
h = re.sub(r"<!--.*?-->", "", html, flags=re.S)

# 1) 所有 id
ids = re.findall(r'\bid="([^"]+)"', h)
# 2) 所有 class token
classes = []
for m in re.finditer(r'\bclass="([^"]+)"', h):
    classes.extend(m.group(1).split())
cls_count = collections.Counter(classes)

# 3) 顶层结构（缩进 <= 4 的块级标签）
skeleton = []
for i, line in enumerate(h.split("\n"), 1):
    m = re.match(r'^(\s*)<(section|aside|main|header|footer|nav|div|dialog)\b([^>]*)>', line)
    if m and len(m.group(1)) <= 4:
        attrs = m.group(3)
        _id = re.search(r'id="([^"]+)"', attrs)
        _cl = re.search(r'class="([^"]+)"', attrs)
        skeleton.append((i, len(m.group(1)), m.group(2),
                         _id.group(1) if _id else "", (_cl.group(1) if _cl else "")[:60]))

# 4) 内联 style=（DESIGN.md §7 Don'ts 禁项）
inline_style = [(i, ln.strip()[:100]) for i, ln in enumerate(h.split("\n"), 1) if ' style="' in ln]

# 5) JS 层 UI 生产者
js_files = [f for f in os.listdir(UI) if f.endswith(".js") and not f.startswith("_")]
js_stat = []
for f in sorted(js_files):
    p = os.path.join(UI, f)
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    n_inner = len(re.findall(r"\.innerHTML\s*=", t))
    n_create = len(re.findall(r"createElement\(", t))
    n_cls = len(re.findall(r"classList\.(add|remove|toggle)\(", t))
    n_style = len(re.findall(r"\.style\.[a-zA-Z]", t)) + len(re.findall(r"setProperty\(", t))
    n_insert = len(re.findall(r"insertAdjacentHTML\(", t))
    total = n_inner + n_create + n_cls + n_style + n_insert
    if total >= 8:
        js_stat.append({
            "file": f, "lines": t.count("\n") + 1, "innerHTML": n_inner,
            "createElement": n_create, "classList": n_cls, "styleWrite": n_style,
            "insertAdjacentHTML": n_insert, "uiScore": total,
        })
js_stat.sort(key=lambda x: -x["uiScore"])

print("=" * 104)
print(f"index.html 结构骨架（顶层容器，共 {len(skeleton)} 个）")
print("=" * 104)
for ln, ind, tag, _id, cl in skeleton:
    print(f"  L{ln:<5} {' ' * ind}<{tag}{(' #' + _id) if _id else ''}{('  .' + cl) if cl else ''}")

print(f"\n总 id 数: {len(ids)}   唯一 class token: {len(cls_count)}   内联 style= 出现行数: {len(inline_style)}")

print("\n" + "=" * 104)
print("JS 层 UI 生产者（uiScore = innerHTML + createElement + classList + style写 + insertAdjacentHTML）")
print("=" * 104)
print(f"{'file':34s}{'lines':>7}{'innerHTML':>11}{'createEl':>10}{'classList':>11}{'style写':>9}{'score':>8}")
for s in js_stat[:30]:
    print(f"{s['file']:34s}{s['lines']:>7}{s['innerHTML']:>11}{s['createElement']:>10}{s['classList']:>11}{s['styleWrite']:>9}{s['uiScore']:>8}")

print(f"\nJS 文件总数 {len(js_files)}，其中 UI 生产者（score>=8）{len(js_stat)} 个")
print(f"innerHTML 写入总计 {sum(s['innerHTML'] for s in js_stat)} 处")
print(f"JS 直接写 style 总计 {sum(s['styleWrite'] for s in js_stat)} 处  ← 绕过 CSS 令牌的风险点")

json.dump({
    "skeleton": skeleton, "id_count": len(ids), "unique_classes": len(cls_count),
    "top_classes": cls_count.most_common(60), "inline_style_lines": inline_style,
    "js_ui_producers": js_stat, "js_total": len(js_files),
}, open(os.path.join(r"G:\Xiao6\docs\ui-system", "_dom_audit.json"), "w", encoding="utf-8"),
    ensure_ascii=False, indent=2)
print("\nWROTE _dom_audit.json")
