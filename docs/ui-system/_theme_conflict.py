# -*- coding: utf-8 -*-
"""主题令牌分叉取证：ui2.css [data-theme] vs styles.css body[data-theme]（只读）"""
import re, os
UI = r"G:\Xiao6\xiao6-ui"

def load(f):
    t = open(os.path.join(UI, f), encoding="utf-8", errors="replace").read()
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)

ui2 = load("ui2.css")
sty = load("styles.css")

def blocks(text, pat):
    out = {}
    for m in re.finditer(pat, text):
        theme = m.group(1)
        vs = dict((k, " ".join(v.split()))
                  for k, v in re.findall(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+)", m.group(2)))
        if vs:
            out.setdefault(theme, {}).update(vs)
    return out

ui2_t = blocks(ui2, r'\[data-theme="([a-z-]+)"\]\s*\{([^{}]*)\}')
sty_t = blocks(sty, r'body\[data-theme="([a-z-]+)"\]\s*\{([^{}]*)\}')

# ui2 :root 基线（用于解析别名）
root = dict((k, " ".join(v.split()))
            for k, v in re.findall(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+)",
                                   re.search(r":root\s*\{(.*?)\n\}", ui2, re.S).group(1)))

def resolve(val, table, depth=0):
    if depth > 6: return val
    m = re.fullmatch(r"var\((--[a-zA-Z0-9-]+)\)", val.strip())
    if m:
        nxt = table.get(m.group(1), root.get(m.group(1)))
        if nxt: return resolve(nxt, table, depth + 1)
    return val

print("ui2.css 主题:", sorted(ui2_t))
print("styles.css 主题:", sorted(sty_t))
print()
print("=" * 100)
print("跨文件同名变量冲突（styles.css body[...] 特异性 0,1,1 > ui2.css [...] 0,1,0 → styles.css 生效）")
print("=" * 100)
total = 0; real = 0
for theme in sorted(set(ui2_t) & set(sty_t)):
    a, b = ui2_t[theme], sty_t[theme]
    common = sorted(set(a) & set(b))
    if not common: continue
    print(f"\n--- [{theme}] 冲突 {len(common)} 个 ---")
    for k in common:
        total += 1
        va, vb = resolve(a[k], a), b[k]
        same = va.lower().replace(" ", "") == vb.lower().replace(" ", "")
        flag = "同值(无视觉差)" if same else ">>> 值不同 <<<"
        if not same: real += 1
        print(f"  {k:16s} ui2解析={va[:44]:46s} styles={vb[:40]:42s} {flag}")

print("\n" + "=" * 100)
print(f"冲突变量总数 {total}，其中真实值不同 {real}")
# styles.css 独有（ui2 未覆盖，即 ui2 主题切换管不到的）
print("\n=== styles.css 定义但 ui2.css 同主题未定义的变量（ui2 主题体系覆盖不到） ===")
for theme in sorted(sty_t):
    only = sorted(set(sty_t[theme]) - set(ui2_t.get(theme, {})))
    if only:
        print(f"  [{theme}] {only}")
