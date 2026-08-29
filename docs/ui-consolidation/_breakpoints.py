# -*- coding: utf-8 -*-
"""Formal UI System v1.0 — 响应式断点归一（四模式）
正式断点（全系统唯一）：
  Desktop   >= 1200px  （基础样式，无 media query）
  Compact   <= 1199px  （侧栏转抽屉、Hero 收缩、多列降密）
  Narrow    <= 980px   （单列、导航横排、浮层全宽）
  Companion 独立文档（companion.css，不参与主窗断点）

归并前存在 9 个断点（1199/1080/980/900/820/760/720/680/640）+ 书写格式不一致。
纪律：只改 @media 条件字面值与书写格式，不移动任何规则块、不改选择器、不改声明，
      故 CSS 层叠顺序完全不变。
"""
import re, os, collections

BASE = r"G:/xiao6/xiao6-ui"
FILES = ["styles.css", "ui2.css", "premium.css",
         "runtime-viz.css", "execution-channel.css"]

MAP = {1199: 1199, 1080: 1199, 980: 980, 900: 1199,
       820: 980, 760: 980, 720: 980, 680: 980, 640: 980}

MQ = re.compile(r"@media\s*\(\s*max-width\s*:\s*(\d+)px\s*\)")

# 注释区间（跳过，避免改动被注释掉的历史块）
def comment_spans(src):
    return [(m.start(), m.end()) for m in re.finditer(r"/\*.*?\*/", src, re.S)]

total = 0
detail = collections.Counter()
for f in FILES:
    p = os.path.join(BASE, f)
    src = open(p, encoding="utf-8").read()
    spans = comment_spans(src)

    def in_comment(i):
        return any(a <= i < b for a, b in spans)

    out, last = [], 0
    for m in MQ.finditer(src):
        if in_comment(m.start()):
            continue
        old = int(m.group(1))
        new = MAP.get(old, old)
        out.append(src[last:m.start()])
        out.append(f"@media (max-width: {new}px)")
        last = m.end()
        if new != old:
            total += 1
            detail[f"{f}: {old} -> {new}"] += 1
        else:
            detail[f"{f}: {old} (格式统一)"] += 1
    out.append(src[last:])
    new_src = "".join(out)
    if new_src != src:
        open(p, "w", encoding="utf-8").write(new_src)

print("=== 断点归一明细 ===")
for k, v in sorted(detail.items()):
    print(f"  {k}  x{v}")
print(f"\n断点值改写 {total} 处；书写格式全部统一为 `@media (max-width: Npx)`")
