#!/usr/bin/env python3
"""Xiao6 D 期（主动智能）端到端测试：SSE 推送 + 到期提醒 + 每日简报 + ACI 预判注入。"""

import json
import sys
import threading
import time
import urllib.request as U

sys.path.insert(0, "G:/Xiao6/xiao6-ui")
import memory  # build_context_prefix 已迁移至 memory 模块
import server as S

BASE = "http://localhost:8000"
events: list = []


def open_stream():
    try:
        resp = U.urlopen(BASE + "/api/stream", timeout=40)
        while True:
            line = resp.readline()
            if not line:
                break
            s = line.decode("utf-8", "replace")
            if s.startswith("data:"):
                payload = s[5:].strip()
                try:
                    ev = json.loads(payload)
                except Exception:
                    continue
                events.append(ev)
                print("  [STREAM]", ev.get("kind"), "->", str(ev.get("content", ""))[:50])
    except Exception as e:
        print("  [STREAM-ERR]", e)


print("===== 0) 重置每日简报标记（保证可重复运行）=====")
c = S.db_conn()
c.execute("DELETE FROM meta WHERE key='last_briefing_date'")
c.commit()
c.close()

print("===== 1) 打开 SSE 主动推送通道 =====")
t = threading.Thread(target=open_stream, daemon=True)
t.start()
time.sleep(1.5)  # 等待连接 + flush pending + 每日简报

print("===== 2) 设置「立刻」提醒（TICK 应在 15s 内主动推送）=====")
body = json.dumps({"messages": [{"role": "user", "content": "提醒我 立刻 去倒杯水"}]}).encode()
req = U.Request(BASE + "/api/chat", data=body, headers={"Content-Type": "application/json"})
with U.urlopen(req, timeout=60) as r:
    chat = r.read().decode("utf-8", "replace")
print("  chat 回复尾段:", chat[-100:].replace("\n", " "))

print("===== 3) 等待 TICK 心跳触发提醒推送（≤18s）=====")
time.sleep(18)

print("===== 4) ACI 预判注入：system prompt 含当前时间 =====")
ctx = memory.build_context_prefix()
today = __import__("datetime").datetime.now().strftime("%Y年%m月%d日")
aci_ok = today in ctx

print("===== 5) /api/memory 含提醒记录 =====")
with U.urlopen(BASE + "/api/memory", timeout=10) as r:
    mem = json.loads(r.read().decode("utf-8"))
reminders = mem.get("reminders", [])
print("  reminders:", reminders)

# 汇总
kinds = [e.get("kind") for e in events]
briefing_ok = any(e.get("kind") == "briefing" for e in events)
reminder_ok = any(e.get("kind") == "reminder" for e in events)

print("\n===== 结果 =====")
print("每日简报推送 :", "PASS" if briefing_ok else "FAIL")
print("到期提醒推送 :", "PASS" if reminder_ok else "FAIL")
print("ACI 预判注入 :", "PASS" if aci_ok else "FAIL")
print("提醒入库     :", "PASS" if reminders else "FAIL")
print("事件总数     :", len(events), kinds)
ok = briefing_ok and reminder_ok and aci_ok and bool(reminders)
print("\nD 期总体:", "ALL PASS ✅" if ok else "SOME FAIL ❌")
sys.exit(0 if ok else 1)
