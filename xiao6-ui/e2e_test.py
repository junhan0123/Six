"""Xiao6 端到端测试：工具闭环 + 普通对话 + TTS。"""

import json
import urllib.error
import urllib.request

BASE = "http://localhost:8000"


def post_chat(text):
    body = json.dumps({"messages": [{"role": "user", "content": text}]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/api/chat", data=body, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode("utf-8", "replace")
    events, content = [], ""
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
        if obj.get("xiao6_event"):
            events.append(obj)
        else:
            c = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if c:
                content += c
    return events, content


def post_speak(text):
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/api/speak", data=body, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        ctype = r.headers.get("Content-Type", "")
        data = r.read()
    return ctype, len(data)


def run(name, text, expect_tool=None):
    print("\n=== %s ===" % name)
    print("问: %s" % text)
    try:
        events, content = post_chat(text)
    except Exception as e:
        print("  [ERROR] %s" % e)
        return False
    for ev in events:
        if ev.get("xiao6_event") == "tool_start":
            print("  工具启动: %s  args=%s" % (ev.get("tool"), ev.get("args")))
        elif ev.get("xiao6_event") == "tool_end":
            print("  工具结果: %s -> %s" % (ev.get("tool"), str(ev.get("result"))[:80]))
    print("  回复: %s" % content[:200])
    ok = True
    if expect_tool:
        tools = [e.get("tool") for e in events if e.get("xiao6_event") == "tool_end"]
        if expect_tool not in tools:
            print("  [FAIL] 期望触发工具 %s，实际 %s" % (expect_tool, tools))
            ok = False
    if not content.strip():
        print("  [FAIL] 无回复内容")
        ok = False
    print("  结果: " + ("PASS" if ok else "FAIL"))
    return ok


if __name__ == "__main__":
    results = []
    results.append(run("时间工具", "现在几点了？今天星期几", expect_tool="get_time"))
    results.append(run("计算器", "帮我算一下 123 乘以 456 等于多少", expect_tool="calculator"))
    results.append(run("记笔记", "记一下：明天上午十点提交周报", expect_tool="note_save"))
    results.append(run("查笔记", "我之前记了哪些笔记？", expect_tool="note_list"))
    results.append(run("普通对话", "用一句话介绍你是谁", expect_tool=None))

    print("\n=== TTS 语音合成 ===")
    try:
        ctype, size = post_speak("你好，我是 Xiao6，您的智能副驾。")
        print("  Content-Type: %s" % ctype)
        print("  音频字节数: %d" % size)
        tts_ok = ("audio/mpeg" in ctype) and size > 1000
        print("  结果: " + ("PASS" if tts_ok else "FAIL"))
    except Exception as e:
        print("  [ERROR] %s" % e)
        tts_ok = False

    print("\n========== 总结 ==========")
    print("工具/对话用例: %d/%d 通过" % (sum(results), len(results)))
    print("TTS: %s" % ("PASS" if tts_ok else "FAIL"))
    print("总评: " + ("ALL PASS ✅" if (all(results) and tts_ok) else "存在失败 ❌"))
