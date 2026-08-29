import io, sys

p = 'G:/xiao6/xiao6-ui/styles.css'
with io.open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

orig = len(lines)

# 断言锚点（1-based），确保删对位置
def assert_at(n, frag):
    got = lines[n - 1]
    if frag not in got:
        print('ANCHOR FAIL line %d expect %r got %r' % (n, frag, got[:90]))
        sys.exit(1)

assert_at(3278, 'zzNotifyIn')
assert_at(3056, '语音球附近通知气泡')
assert_at(3079, 'zz-notify-body')
assert_at(2282, 'sm-open-btn')
assert_at(2285, 'cap-open-btn')
assert_at(2121, '世界时钟 + 指令面板')
assert_at(2198, 'wc-cd-done')

# 自底向上删除，保持行号有效
ranges = [
    (3278, 3278),   # @keyframes zzNotifyIn（zz-notify 删除后孤立）
    (3056, 3079),   # zz-notify 族（代码注释已自标「已弃用」，0 消费者）
    (2282, 2285),   # 4 个孤儿 HUD 入口按钮色变量（对应按钮已不存在于 DOM）
    (2121, 2199),   # 世界时钟 wc-* 族（0 消费者，且整块重复定义两次）
]
removed = 0
for a, b in ranges:
    removed += (b - a + 1)
    del lines[a - 1:b]

with io.open(p, 'w', encoding='utf-8', newline='') as f:
    f.writelines(lines)

print('styles.css: %d -> %d 行（移除 %d 行确认死代码）' % (orig, len(lines), removed))
