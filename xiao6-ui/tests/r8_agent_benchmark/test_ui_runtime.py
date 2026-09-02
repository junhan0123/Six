# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.test_ui_runtime — R8-UI Recovery 验证

覆盖（自启服务器 :8034，真实 HTTP/SSE）：
  1) 静态资源：/ → 200（redirect 入口）；/zz-space/index.html、css、js → 200
  2) Chat SSE：POST /api/chat（"你好，介绍一下自己"）→ 200 且含内容增量
  3) 工具事件：POST /api/chat（"帮我查询当前时间"）→ SSE 含 tool_start / tool_end
  4) Goal 创建：POST /api/agent/goal → ok + goalId
  5) 实时通道：连接 /api/stream → POST /api/agent/goal → 收到 GOAL_CREATED（goal 状态实时）
  6) Agent State：GET /api/agent/state → enabled + state（fetchSnapshot 数据源）

与 UI 绑定同路径：UI 的 zz-workspace.js 使用相同端点（POST /api/chat、/api/agent/goal、
EventSource('/api/stream')、GET /api/agent/state）。
"""

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, _HERE)

from _fixture import check, section  # noqa: E402

PORT = 8034
BASE = f"http://127.0.0.1:{PORT}"
PY = sys.executable or "python"

_SERVER = None


def _http(method, path, body=None, timeout=60):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def _start():
    global _SERVER
    env = dict(os.environ)
    env["Xiao6_PORT"] = str(PORT)
    env["BIND_HOST"] = "127.0.0.1"
    _SERVER = subprocess.Popen([PY, "server.py"], cwd=_PROJECT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 40
    while time.time() < deadline:
        try:
            code, _ = _http("GET", "/api/health", timeout=5)
            if code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _stop():
    global _SERVER
    if _SERVER is not None:
        try:
            _SERVER.terminate()
            _SERVER.wait(timeout=10)
        except Exception:
            try:
                _SERVER.kill()
            except Exception:
                pass
        _SERVER = None


def _stream_once(timeout=20):
    """打开 /api/stream，收集事件并返回 (events, conn_fail)。"""
    events = []
    fail = [False]

    def reader():
        try:
            with urllib.request.urlopen(BASE + "/api/stream", timeout=timeout + 5) as r:
                while True:
                    line = r.readline()
                    if not line:
                        break
                    s = line.decode("utf-8", "replace")
                    if s.startswith("data:"):
                        p = s[5:].strip()
                        try:
                            events.append(json.loads(p))
                        except Exception:
                            pass
        except Exception:
            fail[0] = True

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    return events, fail, t


def run_ui_runtime():
    section("R8-UI Recovery 验证（静态资源 / Chat SSE / 工具事件 / Goal / 实时通道）")

    ok = []
    ok.append(check("服务器启动 :8034", _start(), ""))

    # 1) 静态资源
    for p, name in [("/", "入口 /"), ("/zz-space/index.html", "index.html"),
                    ("/zz-space/css/zz-workspace.css", "css"),
                    ("/zz-space/js/zz-workspace.js", "js")]:
        code, _ = _http("GET", p)
        ok.append(check(f"静态资源 {name} → 200", code == 200, f"code={code}"))

    # 2) Agent State（UI fetchSnapshot 数据源）
    code, body = _http("GET", "/api/agent/state")
    ok.append(check("GET /api/agent/state → enabled+state", code == 200 and '"enabled"' in body,
                    f"code={code}"))

    # 3) Chat SSE：普通聊天
    code, body = _http("POST", "/api/chat",
                       {"messages": [{"role": "user", "content": "你好，介绍一下自己"}]})
    has_content = ("choices" in body or "[DONE]" in body) and code == 200
    ok.append(check("Chat 普通聊天（SSE 流）", has_content, f"code={code}"))

    # 4) Chat SSE：工具事件（tool_start / tool_end）
    code2, body2 = _http("POST", "/api/chat",
                         {"messages": [{"role": "user", "content": "帮我查询当前时间"}]})
    has_tool = '"tool_start"' in body2 and '"tool_end"' in body2
    ok.append(check("Chat 工具调用事件（tool_start/tool_end）", code2 == 200 and has_tool,
                    f"code={code2}"))

    # 5) Goal 创建（UI 目标表单同路径）
    code3, body3 = _http("POST", "/api/agent/goal",
                         {"title": "R8-UI 验证目标", "description": "UI 恢复验证"})
    try:
        gid = json.loads(body3).get("goalId")
    except Exception:
        gid = None
    ok.append(check("Goal 创建 → goalId 生成", code3 == 200 and bool(gid),
                    f"code={code3} goalId={gid}"))

    # 6) 实时通道：/api/stream 收到 GOAL_CREATED（UI EventSource 同路径）
    events, fail, t = _stream_once(timeout=25)
    code4, body4 = _http("POST", "/api/agent/goal", {"title": "R8-UI 实时通道验证目标"})
    goal_ev = None
    deadline = time.time() + 25
    while time.time() < deadline and goal_ev is None:
        for e in events:
            if (e.get("xiao6_event") == "GOAL_CREATED"
                    or (e.get("payload") or {}).get("goalId")):
                goal_ev = e
                break
        time.sleep(1)
    ok.append(check("/api/stream 实时收到 GOAL_CREATED（goal 状态）",
                    goal_ev is not None and not fail[0],
                    f"conn_fail={fail[0]} code={code4}"))

    _stop()
    return all(ok)


if __name__ == "__main__":
    sys.exit(0 if run_ui_runtime() else 1)
