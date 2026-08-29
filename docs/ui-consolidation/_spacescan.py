# -*- coding: utf-8 -*-
"""Formal UI System v1.0 — Spacing 散值扫描（只读，不改文件）
统计 padding / margin / gap / row-gap / column-gap 的 px 实值分布，
用于判断是否存在「非 4px 网格」的离散间距。
"""
import re, os, collections

BASE = r"G:/xiao6/xiao6-ui"
FILES = ["styles.css", "ui2.css", "companion.css", "premium.css",
         "runtime-viz.css", "execution-channel.css"]

PROP = re.compile(
    r"(?<![\w-])(padding|margin|gap|row-gap|column-gap|"
    r"padding-top|padding-right|padding-bottom|padding-left|"
    r"margin-top|margin-right|margin-bottom|margin-left)\s*:\s*([^;{}]+);",
    re.I)
PX = re.compile(r"(-?\d+(?:\.\d+)?)px")

vals = collections.Counter()
per_file = collections.Counter()
offgrid_sites = []

for f in FILES:
    p = os.path.join(BASE, f)
    if not os.path.exists(p):
        continue
    src = open(p, encoding="utf-8").read()
    lines = src.split("\n")
    for i, line in enumerate(lines, 1):
        for m in PROP.finditer(line):
            body = m.group(2)
            if "var(" in body and not PX.search(body):
                continue
            for pv in PX.finditer(body):
                v = float(pv.group(1))
                av = abs(v)
                vals[av] += 1
                per_file[f] += 1
                # 4px 网格 + 常见半档 (2/6/10/14/18/22...) 判定
                if av != 0 and av % 2 != 0:
                    offgrid_sites.append((f, i, m.group(1), body.strip(), av))

print("=== Spacing px 实值分布（按出现次数）===")
for v, c in sorted(vals.items(), key=lambda x: -x[1]):
    grid = "" if (v % 2 == 0 or v == 0) else "  <-- 非偶数(off-grid)"
    print(f"  {v:>7}px : {c:>4} 处{grid}")

print(f"\n实值种类 = {len(vals)}   总声明点 = {sum(vals.values())}")
print("\n=== 各文件间距声明数 ===")
for f, c in per_file.most_common():
    print(f"  {f:<24} {c}")

print(f"\n=== 非偶数(off-grid) 间距站点 = {len(offgrid_sites)} 处 ===")
agg = collections.Counter(s[4] for s in offgrid_sites)
for v, c in sorted(agg.items(), key=lambda x: -x[1]):
    print(f"  {v}px : {c} 处")
print("\n前 40 个站点：")
for s in offgrid_sites[:40]:
    print(f"  {s[0]}:{s[1]}  {s[2]}: {s[3]}")
