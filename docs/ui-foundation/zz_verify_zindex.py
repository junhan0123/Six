#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overlay Sprint · Step[1] z-index 令牌化 — 静态验收脚本（可回滚前置校验）

验收四项：
  (1) styles.css / premium.css 中不允许残留裸数字 z-index（必须全部走 var(--z-*)）
  (2) 所有被引用的 --z-* 令牌必须在 ui2.css :root 中定义（无悬空引用）
  (3) 三个 CSS 文件花括号平衡（结构完整）
  (4) index.html 中 ui2.css 必须在 styles.css / premium.css 之后加载（cascade 胜出）

退出码 0 = 全部 PASS；非 0 = 存在 FAIL（阻断合并）。
用法：python zz_verify_zindex.py
"""
import re
import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "xiao6-ui"))
CSS_MAIN = ["styles.css", "premium.css"]
CSS_TOKEN = "ui2.css"
INDEX = "index.html"

fails = 0


def check(label, ok, detail=""):
    global fails
    mark = "PASS" if ok else "FAIL"
    if not ok:
        fails += 1
    print(f"[{mark}] {label}{(' — ' + detail) if detail else ''}")


# (1) 残留裸数字 z-index
for f in CSS_MAIN:
    p = os.path.join(BASE, f)
    s = open(p, encoding="utf-8").read()
    raw = re.findall(r'z-index\s*:\s*\d+', s)
    check(f"无裸数字 z-index（{f}）", len(raw) == 0, f"残留 {len(raw)} 处" if raw else "0 处")

# (2) 令牌定义覆盖
ui = open(os.path.join(BASE, CSS_TOKEN), encoding="utf-8").read()
defined = set(re.findall(r'(--z-[a-z-]+)\s*:', ui))
refs = set()
for f in CSS_MAIN:
    refs |= set(re.findall(r'var\((--z-[a-z-]+)\)', open(os.path.join(BASE, f), encoding="utf-8").read()))
missing = refs - defined
check("所有引用令牌均已定义", len(missing) == 0, ("缺失: " + ", ".join(sorted(missing))) if missing else f"{len(refs)} 个引用全覆盖")

# (3) 花括号平衡
for f in CSS_MAIN + [CSS_TOKEN]:
    s = open(os.path.join(BASE, f), encoding="utf-8").read()
    ok = s.count("{") == s.count("}")
    check(f"花括号平衡（{f}）", ok, f"{{={s.count('{')} }}={s.count('}')}")

# (4) cascade 顺序（锚定 <link href="..."> 而非裸文件名，避免命中注释）
idx = open(os.path.join(BASE, INDEX), encoding="utf-8").read()
def link_pos(fname):
    m = re.search(r'href="%s' % re.escape(fname), idx)
    return m.start() if m else -1
pos = {f: link_pos(f) for f in CSS_MAIN + [CSS_TOKEN]}
order_ok = pos[CSS_TOKEN] > pos["styles.css"] > 0 and pos[CSS_TOKEN] > pos["premium.css"] > 0
check("ui2.css 最后加载（cascade 胜出）", order_ok,
      f"styles={pos['styles.css']} premium={pos['premium.css']} ui2={pos[CSS_TOKEN]}")

print("\n" + ("✅ 全部 PASS — Step[1] 静态验收通过" if fails == 0 else f"❌ {fails} 项 FAIL — 阻断"))
sys.exit(1 if fails else 0)
