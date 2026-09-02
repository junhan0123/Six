# -*- coding: utf-8 -*-
"""Spacing 激活 · 实施（修正版）：注释感知，统计【声明数】替换。零视觉变化。"""
import re
UI = r"G:\Xiao6\xiao6-ui"
SP = {f"{n}px": f"var(--sp-{n})" for n in
      [2,4,6,8,10,12,14,16,18,20,22,24,26,28,32,34,40,48]}

src = open(f"{UI}/ui2.css", encoding="utf-8", errors="replace").read()
before_braces = src.count("{") - src.count("}")

prop_re = re.compile(r'(?P<prop>[-a-z]*(?:padding|margin|gap)[-a-z]*)\s*:\s*(?P<val>[^;{}]+);')

replaced_decl = 0
def transform(seg):
    global replaced_decl
    def repl(m):
        global replaced_decl
        val = m.group("val").strip()
        if any(k in val for k in ("calc", "var(", "%", "min(", "max(", "vw", "vh", "em", "rem")):
            return m.group(0)
        toks = val.split()
        if not toks or not all(t in SP for t in toks):
            return m.group(0)
        replaced_decl += 1
        newval = " ".join(SP[t] for t in toks)
        return f"{m.group('prop')}: {newval};"
    return prop_re.sub(repl, seg)

parts = re.split(r'(/\*.*?\*/)', src, flags=re.S)
out = []
for part in parts:
    if part.startswith("/*") and part.endswith("*/"):
        out.append(part)
    else:
        out.append(transform(part))
result = "".join(out)

after_braces = result.count("{") - result.count("}")

assert after_braces == before_braces, f"花括号失衡! {before_braces} vs {after_braces}"

open(f"{UI}/ui2.css", "w", encoding="utf-8").write(result)
print(f"OK · 替换声明数: {replaced_decl} · 注释块原样保留 · 花括号平衡: {after_braces}（不变）")
