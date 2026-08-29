# -*- coding: utf-8 -*-
"""
PHASE 5.9-P0-1 · STEP 8 TRACE D 复测（AFTER，真实 HTTP 链路）
流程：POST /api/chat（prompt 要求 run_shell echo XIAO6_CONFIRM_TEST）
      → 流式读 SSE
      → 捕获 xiao6_event:"approval"（F3 转发，关键验证点：审批卡事件到达聊天流）
      → 自动 POST /api/agent/approval?ticket=&decision=approve（模拟用户批准）
      → 继续读到 tool_end / choices / [DONE]
判定：APPROVAL 事件出现 + 批准后工具执行 + 正常收尾。
"""
import json
import http.client

HOST, PORT = "127.0.0.1", 8010


def post_approval(ticket, decision):
    c = http.client.HTTPConnection(HOST, PORT, timeout=10)
    c.request("POST", "/api/agent/approval?ticket=%s&decision=%s" % (ticket, decision))
    r = c.getresponse()
    body = r.read().decode("utf-8", "replace")
    c.close()
    return r.status, body


payload = {
    "messages": [{"role": "user",
                  "content": "请调用 run_shell 工具执行命令 echo XIAO6_CONFIRM_TEST，然后把命令输出告诉我。"}],
    "session_id": "p01_trace_d_after",
}
body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

conn = http.client.HTTPConnection(HOST, PORT, timeout=180)
conn.request("POST", "/api/chat", body=body,
             headers={"Content-Type": "application/json"})
resp = conn.getresponse()
print("HTTP status:", resp.status)

events = []
approved = False
while True:
    raw = resp.readline()
    if not raw:
        break
    line = raw.decode("utf-8", "replace").strip()
    if not line.startswith("data:"):
        continue
    data = line[5:].strip()
    if data == "[DONE]":
        events.append(("done",))
        break
    try:
        m = json.loads(data)
    except Exception:
        events.append(("raw", data[:80]))
        continue
    if m == "[DONE]":
        events.append(("done",))
        break
    if not isinstance(m, dict):
        continue
    ev = m.get("xiao6_event")
    if ev == "approval":
        ticket = m.get("ticket")
        events.append(("approval", ticket, m.get("prompt")))
        if ticket and not approved:
            st, b2 = post_approval(ticket, "approve")
            approved = True
            events.append(("approval_post", st, b2[:80]))
    elif ev == "tool_start":
        events.append(("tool_start", m.get("tool"), str(m.get("args"))[:80]))
    elif ev == "tool_end":
        events.append(("tool_end", m.get("tool"), str(m.get("result"))[:120]))
    elif m.get("choices"):
        dc = (m.get("choices") or [{}])[0].get("delta", {}).get("content", "")
        if dc:
            events.append(("delta", dc[:120]))
    else:
        events.append((ev or "other", str(m)[:100]))

conn.close()

for e in events:
    print("EVENT:", json.dumps(e, ensure_ascii=False))

approval_seen = any(e[0] == "approval" for e in events)
tool_end_seen = any(e[0] == "tool_end" and e[1] == "run_shell" for e in events)
done_seen = any(e[0] == "done" for e in events)
result = {
    "approval_event_seen": approval_seen,
    "run_shell_tool_end_seen": tool_end_seen,
    "done_seen": done_seen,
    "passed": bool(approval_seen and tool_end_seen and done_seen),
}
with open("G:/xiao6/_ui_archive/step8_trace_d_after.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("STEP8 结论:", "PASS" if result["passed"] else "FAIL",
      "| approval_seen=%s tool_end_seen=%s done_seen=%s" % (approval_seen, tool_end_seen, done_seen))
