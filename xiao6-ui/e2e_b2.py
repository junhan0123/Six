import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000"


def post_json(path, obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8")


def chat(text, session="s1"):
    raw = post_json("/api/chat", {"messages": [{"role": "user", "content": text}], "session_id": session})
    events = []
    final = ""
    for line in raw.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        if obj.get("zhuangzhou_event"):
            events.append(obj)
        elif obj.get("choices"):
            d = obj["choices"][0].get("delta", {}).get("content", "")
            if d:
                final += d
    return events, final


def get_memory():
    with urllib.request.urlopen(BASE + "/api/memory", timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + ("  " + extra if extra else ""))


print("=== ZhuangZhou B2 长期记忆 端到端测试 ===")
t0 = time.time()

# 1) 记住称呼
ev, rep = chat("叫我老板")
tool = next((e for e in ev if e.get("zhuangzhou_event") == "tool_end"), None)
check("profile_set(称呼) 触发", tool and tool.get("tool") == "profile_set", "reply=" + rep[:40].replace("\n", " "))
mem = get_memory()
prof = {p["key"]: p["value"] for p in mem.get("profile", [])}
check("记忆画像含 称呼=老板", prof.get("称呼") == "老板", "profile=" + str(prof))

# 2) 记住偏好
ev, rep = chat("我喜欢用一句话回答，别啰嗦")
tool = next((e for e in ev if e.get("zhuangzhou_event") == "tool_end"), None)
check(
    "profile_set(偏好) 触发",
    tool and tool.get("tool") == "profile_get" or (tool and tool.get("tool") == "profile_set"),
    "reply=" + rep[:40].replace("\n", " "),
)
mem = get_memory()
prof = {p["key"]: p["value"] for p in mem.get("profile", [])}
check("记忆画像含 偏好", "偏好" in prof, "profile=" + str(prof))

# 3) 回忆称呼（同一会话）
ev, rep = chat("你记得我叫什么吗？")
check("profile_get 回忆称呼", "老板" in rep, "reply=" + rep[:50].replace("\n", " "))

# 4) 跨会话记忆注入：新 session，不触发工具，靠 system prompt 里的画像
ev, rep = chat("我是谁？你一般怎么称呼我？", session="brand_new_session_xyz")
check(
    "跨会话记忆注入生效（回复含 老板）",
    "老板" in rep,
    "events=" + str([e.get("tool") for e in ev]) + " reply=" + rep[:50].replace("\n", " "),
)

# 5) 计算器仍正常（回归）
ev, rep = chat("帮我算一下 99 乘以 99 等于多少")
check("calculator 回归正常", "9801" in rep, "reply=" + rep[:50].replace("\n", " "))

# 6) 记忆统计
mem = get_memory()
check(
    "记忆统计 log_count>0",
    mem.get("log_count", 0) > 0,
    "profile=%d note=%d log=%d" % (len(mem.get("profile", [])), mem.get("note_count", 0), mem.get("log_count", 0)),
)

print("=== 用时 %.1fs ===" % (time.time() - t0))
