import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
SID = "e2e_multiturn_%d" % int(time.time())


def post_chat(messages):
    body = json.dumps({"messages": messages, "session_id": SID}).encode("utf-8")
    req = urllib.request.Request(BASE + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read().decode("utf-8", "replace")
    # 解析 SSE：累加 content，忽略 xiao6_event
    full = ""
    for line in data.split("\n"):
        s = line.strip()
        if not s.startswith("data:"):
            continue
        payload = s[5:].strip()
        if payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        if obj.get("xiao6_event"):
            continue
        delta = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if delta:
            full += delta
    return full


def memory():
    with urllib.request.urlopen(BASE + "/api/memory", timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


print("===== 1) 连续 5 轮对话（复现“只能发一次”bug）=====")
msgs = []
turns = [
    "你好，我叫老板。",
    "帮我算一下 12 乘以 34。",
    "现在几点了？",
    "记一下：明天上午十点交周报。",
    "我刚才让你记住了什么？",
]
ok = True
for i, t in enumerate(turns, 1):
    msgs.append({"role": "user", "content": t})
    t0 = time.time()
    try:
        reply = post_chat(msgs)
    except Exception as e:
        print(f"  [轮 {i}] 异常: {e!r}")
        ok = False
        break
    msgs.append({"role": "xiao6", "content": reply})
    dt = time.time() - t0
    print(f"  [轮 {i}] {dt:5.1f}s  用户: {t[:18]!r}  ->  Xiao6: {reply[:40]!r}")
    if not reply.strip():
        ok = False
print("  连续对话:", "PASS ✅" if ok else "FAIL ❌")

print("\n===== 2) 记忆自动压缩 =====")
# 直接往 chat_log 灌 50 条历史，跨过阈值(MEM_THRESHOLD=40)
import os
import sqlite3

db = os.path.join(os.path.dirname(__file__), "xiao6.db")
con = sqlite3.connect(db)
con.execute("DELETE FROM chat_log")
from datetime import datetime

rows = [
    (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        SID,
        "user" if k % 2 == 0 else "xiao6",
        f"历史对话第{k}轮：用户提出需求{k}，Xiao6 给出了方案{k}。",
    )
    for k in range(50)
]
con.executemany("INSERT INTO chat_log(ts,session,role,content) VALUES(?,?,?,?)", rows)
con.commit()
before = con.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
con.close()
print(f"  注入前 chat_log 轮次: {before}")

# 发一条消息触发压缩（回复后 compress_memory 执行）
post_chat([{"role": "user", "content": "总结一下我们之前聊过什么"}])
mem = memory()
after = mem.get("log_count", -1)
summary = mem.get("summary", "").strip()
print(f"  压缩后 chat_log 轮次: {after}  (应 <= 24+1)")
print(f"  长期记忆摘要长度: {len(summary)} 字")
print(f"  摘要预览: {summary[:120]!r}")
comp_ok = (after <= 26) and bool(summary)
print("  自动压缩:", "PASS ✅" if comp_ok else "FAIL ❌")

print("\n===== 总览 =====")
print("连续对话:", "PASS" if ok else "FAIL", "| 自动压缩:", "PASS" if comp_ok else "FAIL")
