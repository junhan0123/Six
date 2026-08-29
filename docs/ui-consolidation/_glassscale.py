# Xiao6 Formal Glass Scale v1.0
# 20+ 种 backdrop-filter 配方 -> 3 级正式阶梯（纯视觉属性，无布局影响）
#   --glass-1  轻：内联小面/状态丸        blur(8px)  saturate(140%)
#   --glass-2  中：面板/抽屉/卡片          blur(14px) saturate(160%)
#   --glass-3  重：模态/遮罩/全屏浮层      blur(26px) saturate(180%)   26px = --blur-glass
import io, re, os, collections

d = 'G:/xiao6/xiao6-ui'
decl = re.compile(r'backdrop-filter:\s*([^;}]+)')

# 保留：显式使用既有语义令牌的写法（已是收口态）
KEEP_TOKENS = ('--ws-overlay-blur', '--ws-secondary-blur', '--ws-context-blur',
               '--ws-primary-blur', '--ws-assistant-blur')


def tier_of(px):
    if px < 10:
        return '--glass-1'
    if px < 20:
        return '--glass-2'
    return '--glass-3'


tot = 0
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.css'):
        continue
    p = os.path.join(d, fn)
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()
    c = [0]

    def rep(m):
        body = m.group(1).strip()
        if any(t in body for t in KEEP_TOKENS):
            return m.group(0)
        if 'calc(' in body:                       # 刻意的比例模糊，保留
            return m.group(0)
        if body.startswith('var(--glass-'):       # 已收口
            return m.group(0)
        if 'var(--blur-glass)' in body:
            px = 26.0
        else:
            mm = re.search(r'blur\(\s*([0-9.]+)px', body)
            if not mm:
                return m.group(0)
            px = float(mm.group(1))
        c[0] += 1
        return 'backdrop-filter: var(' + tier_of(px) + ')'

    out = decl.sub(rep, src)
    if c[0]:
        with io.open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(out)
        print('%-24s 收口 %d 处' % (fn, c[0]))
        tot += c[0]

print('\n合计收口 %d 处 backdrop-filter' % tot)

cnt = collections.Counter()
for fn in os.listdir(d):
    if not fn.endswith('.css'):
        continue
    with io.open(os.path.join(d, fn), 'r', encoding='utf-8') as f:
        for m in decl.finditer(f.read()):
            cnt[m.group(1).strip()] += 1
print('\n收口后配方种类 = %d' % len(cnt))
for k, v in cnt.most_common():
    print('  %-46s %d' % (k, v))
