# Xiao6 Formal Radius Scale v1.0
# 纪律：阶梯锚定既有冻结 Token（--radius-sm:9 / --radius-md:14 / --radius-lg:22），
#       仅新增 --radius-xs:4 与 --radius-pill:999 两个补齐级，不建立第二套体系。
# 单值声明改写为 var()（真正的 Token 收口）；多值声明仅做数值归一。
import io, re, os, collections

LADDER = [4, 9, 14, 22, 999]
TOKEN = {4: '--radius-xs', 9: '--radius-sm', 14: '--radius-md',
         22: '--radius-lg', 999: '--radius-pill'}

def snap(v):
    return min(LADDER, key=lambda s: abs(s - v))

d = 'G:/xiao6/xiao6-ui'
# 单值：border-radius: 12px;  /  border-radius:12px}
single = re.compile(r'(border-radius:\s*)([0-9]+(?:\.[0-9]+)?)px(\s*[;}])')
# 多值：border-radius: 14px 14px 0 0
multi = re.compile(r'([0-9]+(?:\.[0-9]+)?)px')

tot_s = tot_m = 0
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.css'):
        continue
    p = os.path.join(d, fn)
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()
    c = [0, 0]

    def rep_single(m):
        v = snap(float(m.group(2)))
        c[0] += 1
        return m.group(1) + 'var(' + TOKEN[v] + ')' + m.group(3)

    out = single.sub(rep_single, src)

    # 处理残余的多值 border-radius 声明
    def rep_decl(m):
        body = m.group(2)

        def rp(mm):
            c[1] += 1
            return str(snap(float(mm.group(1)))) + 'px'
        return m.group(1) + multi.sub(rp, body) + m.group(3)

    out = re.sub(r'(border-radius:\s*)([^;}]*?[0-9]px[^;}]*?)(\s*[;}])', rep_decl, out)

    if c[0] or c[1]:
        with io.open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(out)
        print('%-24s 单值->Token %d 处，多值归一 %d 处' % (fn, c[0], c[1]))
        tot_s += c[0]
        tot_m += c[1]

print('\n合计：单值 Token 化 %d 处，多值归一 %d 处' % (tot_s, tot_m))

cnt = collections.Counter()
for fn in os.listdir(d):
    if not fn.endswith('.css'):
        continue
    with io.open(os.path.join(d, fn), 'r', encoding='utf-8') as f:
        for m in re.finditer(r'border-radius:[^;}]*', f.read()):
            for mm in re.finditer(r'([0-9]+(?:\.[0-9]+)?)px', m.group(0)):
                cnt[mm.group(1)] += 1
print('归一后残留字面圆角值：', dict(cnt) if cnt else '无（全部 Token 化）')
