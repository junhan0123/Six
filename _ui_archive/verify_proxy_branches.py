# PHASE 5.1-HOTFIX 分支验证：直接抽取 server.py 真实源码片段执行，验证三条代理决策分支。
# 不启动服务、不修改任何文件。
import io
import os
import re
import sys
import textwrap
import contextlib

SERVER = r"G:\xiao6\xiao6-ui\server.py"

src_lines = open(SERVER, encoding="utf-8").read().splitlines()

# 定位改动段：从 "# 出站代理支持" 注释起，到 "不可达，已改为直连" 打印行为止
start = None
end = None
for i, ln in enumerate(src_lines):
    if start is None and "出站代理支持" in ln:
        start = i
    if "不可达，已改为直连" in ln:
        end = i
        break

assert start is not None and end is not None, "未定位到代理决策段"
segment = textwrap.dedent("\n".join(src_lines[start:end + 1]))
print(f"[抽取] server.py L{start+1}-L{end+1}，共 {end-start+1} 行真实源码")
print("-" * 70)


def run_branch(name, env_patch, expect_substr, expect_proxy_cleared):
    # 隔离环境
    saved = {}
    keys = ("XIAO6_PROXY_URL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy")
    for k in keys:
        saved[k] = os.environ.get(k)
        os.environ.pop(k, None)
    os.environ.update(env_patch)

    # 隔离 urllib 全局 opener，避免污染本验证进程
    import urllib.request as ur
    saved_opener = ur._opener

    buf = io.StringIO()
    ns = {"os": os, "__name__": "verify"}
    try:
        with contextlib.redirect_stdout(buf):
            exec(segment, ns)
        out = buf.getvalue().strip()
        installed = ur._opener is not saved_opener
        cleared = not any(os.environ.get(k) for k in
                          ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                           "http_proxy", "https_proxy", "all_proxy"))
        ok_msg = expect_substr in out
        ok_clear = (cleared == expect_proxy_cleared)
        verdict = "PASS" if (ok_msg and ok_clear) else "FAIL"
        print(f"[{verdict}] {name}")
        print(f"      输入 env: { {k: v for k, v in env_patch.items()} }")
        print(f"      打印    : {out}")
        print(f"      opener已安装={installed}  进程内代理变量已清除={cleared}（期望 {expect_proxy_cleared}）")
        return verdict == "PASS"
    finally:
        ur._opener = saved_opener
        for k in keys:
            os.environ.pop(k, None)
            if saved[k] is not None:
                os.environ[k] = saved[k]


results = []

# 分支 1：继承的环境代理，且代理存活（当前 FlClash 在跑 → 7890 LISTENING）
results.append(run_branch(
    "分支1 继承环境代理 + 代理存活(7890) → 应照常启用全局代理",
    {"HTTPS_PROXY": "http://127.0.0.1:7890/", "HTTP_PROXY": "http://127.0.0.1:7890/"},
    "已启用全局代理",
    expect_proxy_cleared=False,
))
print("-" * 70)

# 分支 2：继承的环境代理，但代理已死（模拟 FlClash 未启动）
results.append(run_branch(
    "分支2 继承环境代理 + 代理死亡(59999) → 应 fallback 直连并清除进程内代理变量",
    {"HTTPS_PROXY": "http://127.0.0.1:59999/", "HTTP_PROXY": "http://127.0.0.1:59999/"},
    "不可达，已改为直连",
    expect_proxy_cleared=True,
))
print("-" * 70)

# 分支 3：显式配置 XIAO6_PROXY_URL 优先于环境继承，且即便不可达也无条件尊重用户意图
# （同时设置存活的环境代理 7890，用于验证「显式优先」：最终应选用显式的 59999 而非 7890）
results.append(run_branch(
    "分支3 显式 XIAO6_PROXY_URL(不可达) + 环境代理(存活) → 显式优先且无条件启用，不被探活否决",
    {"XIAO6_PROXY_URL": "http://127.0.0.1:59999/",
     "HTTPS_PROXY": "http://127.0.0.1:7890/"},
    "已启用全局代理 -> http://127.0.0.1:59999/",
    expect_proxy_cleared=False,
))
print("-" * 70)

# 分支 4：无任何代理 → 不应有任何代理打印
saved = {k: os.environ.pop(k, None) for k in
         ("XIAO6_PROXY_URL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
          "http_proxy", "https_proxy", "all_proxy")}
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        exec(segment, {"os": os, "__name__": "verify"})
    out = buf.getvalue().strip()
    ok = (out == "")
    print(f"[{'PASS' if ok else 'FAIL'}] 分支4 无代理环境 → 静默直连（无打印）")
    print(f"      打印: {out!r}")
    results.append(ok)
finally:
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v

print("=" * 70)
print(f"BRANCH VERIFY: {sum(results)}/{len(results)} PASS")
sys.exit(0 if all(results) else 1)
