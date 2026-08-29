# -*- coding: utf-8 -*-
"""Spacing 激活 · 干跑：扫描 ui2.css 中 spacing 属性（padding/margin/gap 及方向）
的声明，仅当声明内【全部】长度值都属于 --sp-* 网格时才候选替换（零视觉变化）。"""
import re
UI = r"G:\Xiao6\xiao6-ui"
SP = {f"{n}px": f"--sp-{n}" for n in
      [2,4,6,8,10,12,14,16,18,20,22,24,26,28,32,34,40,48]}

text = open(f"{UI}/ui2.css", encoding="utf-8", errors="replace").read()

# 仅匹配 spacing 类属性
prop_re = re.compile(r'(?P<prop>[-a-z]*(?:padding|margin|gap)[-a-z]*)\s*:\s*(?P<val>[^;{}]+);')
cands = []
for m in prop_re.finditer(text):
    prop, val = m.group("prop"), m.group("val").strip()
    # 跳过含 calc/var/百分比/min/max 等非纯 px 的声明
    if any(k in val for k in ("calc", "var(", "%", "min(", "max(", "vw", "vh", "em", "rem")):
        continue
    toks = val.split()
    if not toks:
        continue
    if all(t in SP for t in toks):
        cands.append((m.start(), prop, val, " ".join(SP[t] for t in toks)))

print(f"候选替换声明数: {len(cands)}")
print(f"将激活的 --sp-* 种类: {{ {', '.join(sorted({c[3] for c in cands}))} }}")
print("-" * 90)
for i, (pos, prop, val, repl) in enumerate(cands):
    line = text.count("\n", 0, pos) + 1
    print(f"L{line:4d}  {prop}: {val}  ->  {repl}")
