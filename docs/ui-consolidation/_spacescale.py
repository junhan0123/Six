# -*- coding: utf-8 -*-
"""Formal UI System v1.0 — Spacing 网格归一
把 padding / margin / gap 的奇数 px 值吸附到 2px 网格（最大位移 1px，视觉不可察）。
纪律：
  · 仅改 padding/margin/gap 系属性的字面数值，不动选择器、不动其他属性。
  · 1px 保留（hairline 补偿，不属于间距体系）。
  · 含 calc() 的声明整体跳过（精确对齐依赖）。
  · 负值保留符号。
"""
import re, os, collections

BASE = r"G:/xiao6/xiao6-ui"
FILES = ["styles.css", "ui2.css", "companion.css", "premium.css",
         "runtime-viz.css", "execution-channel.css"]

PROP = re.compile(
    r"(?<![\w-])(padding|margin|gap|row-gap|column-gap|"
    r"padding-top|padding-right|padding-bottom|padding-left|"
    r"margin-top|margin-right|margin-bottom|margin-left)(\s*:\s*)([^;{}]+)(;)",
    re.I)
PX = re.compile(r"(-?)(\d+(?:\.\d+)?)px")

# 奇数 → 最近偶数（向上吸附，位移 +1px）；1px 不动
SNAP = {3: 4, 5: 6, 7: 8, 9: 10, 11: 12, 13: 14, 15: 16,
        17: 18, 19: 20, 21: 22, 23: 24, 25: 26, 27: 28, 29: 30}

total = 0
per_file = collections.Counter()
changes = collections.Counter()

for f in FILES:
    p = os.path.join(BASE, f)
    if not os.path.exists(p):
        continue
    src = open(p, encoding="utf-8").read()
    orig = src

    def fix(m):
        global total
        prop, sep, body, semi = m.group(1), m.group(2), m.group(3), m.group(4)
        if "calc(" in body:
            return m.group(0)

        def px(pm):
            global total
            sign, num = pm.group(1), float(pm.group(2))
            if num != int(num):
                return pm.group(0)
            n = int(num)
            if n in SNAP:
                total += 1
                changes[f"{n}->{SNAP[n]}"] += 1
                per_file[f] += 1
                return f"{sign}{SNAP[n]}px"
            return pm.group(0)

        return prop + sep + PX.sub(px, body) + semi

    src = PROP.sub(fix, src)
    if src != orig:
        open(p, "w", encoding="utf-8").write(src)

print("=== Spacing 网格归一结果 ===")
for k, v in sorted(changes.items(), key=lambda x: -x[1]):
    print(f"  {k+'px':<12} {v} 处")
print(f"\n合计归一 {total} 处间距值")
print("\n各文件：")
for f, c in per_file.most_common():
    print(f"  {f:<24} {c}")
