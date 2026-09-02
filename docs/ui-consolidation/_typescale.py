# Xiao6 Formal Typography Scale v1.0 —— 字号归一
# 纪律：只改写 font-size 字面值，不改选择器、不改其他属性。
# 最大位移 0.5px（视觉不可察），目的是消除「多个差不多的尺寸」。
import io, re, os

SNAP = {
    '8': '9',        # 折叠极小号
    '9.5': '10', '10.5': '10',
    '11.5': '12', '12.5': '13',
    '13.5': '14', '14.5': '14',
    '15.5': '16',
    '17': '18', '19': '18',
    '21': '22', '25': '26',
    '42': '44', '46': '44',
    '62': '64',
}

SCALE = [9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26, 28, 34, 44, 56, 64]

d = 'G:/xiao6/xiao6-ui'
pat = re.compile(r'(font-size:\s*)([0-9]+(?:\.[0-9]+)?)px')

total = 0
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.css'):
        continue
    p = os.path.join(d, fn)
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()

    hits = [0]

    def rep(m):
        val = m.group(2)
        # 去掉无意义尾零，如 "12.0" -> "12"
        norm = val[:-2] if val.endswith('.0') else val
        if norm in SNAP:
            hits[0] += 1
            return m.group(1) + SNAP[norm] + 'px'
        return m.group(0)

    out = pat.sub(rep, src)
    if hits[0]:
        with io.open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(out)
        print('%-24s 归一 %d 处' % (fn, hits[0]))
        total += hits[0]

print('\n合计归一 %d 处 font-size' % total)

# 复核：输出归一后的字号分布
import collections
cnt = collections.Counter()
for fn in os.listdir(d):
    if not fn.endswith('.css'):
        continue
    with io.open(os.path.join(d, fn), 'r', encoding='utf-8') as f:
        for m in pat.finditer(f.read()):
            cnt[m.group(2)] += 1

vals = sorted(cnt, key=lambda x: float(x))
print('\n归一后字号种类 = %d' % len(vals))
off = [v for v in vals if float(v) not in SCALE]
print('不在正式 Scale 内的残留：', off if off else '无')
