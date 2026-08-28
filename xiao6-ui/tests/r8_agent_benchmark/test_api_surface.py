# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.test_api_surface — R8-P3 Agent API Surface 测试

覆盖（真实 Handler / 真实系统，不 mock Runtime 内核）：
  A. approval 流程（进程内）：
     - policy_engine.request_approval 挂起 → POST /api/agent/approval?ticket=&decision=approve
       → resolve 唤醒 → 挂起线程返回 "approve" → per-goal 批准生效
     - 错误返回：非法 decision → 400；未知/过期 ticket → 404
  B. HTTP（自启服务器子进程，端口 8033）：
     - intent 提交：create（长任务文本）→ goalId；skip（一次性文本）→ action=skip
     - goal 创建：POST /api/agent/goal → ok+goalId；GET /api/goals/<id> 可查
     - 错误返回：goal 缺 title → 400；非法 JSON → 400；intent 缺 text → 400；
       approval 未知 ticket → 404；缺参数 → 400

约束遵守：所有路径经 GoalSystem / IntentGateway / Approval 流程，禁止直连工具。
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

PORT = 8033
BASE = f"http://127.0.0.1:{PORT}"
PY = sys.executable or "python"


def _http(method, path, body=None, timeout=60, raw_body=None, raw_ctype=None):
    data = raw_body
    headers = {}
    if raw_body is None and body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    elif raw_body is not None:
        # R8 Release Closure：API 已加 Content-Type 校验；raw 载荷须显式携带 JSON 头
        headers["Content-Type"] = raw_ctype or "application/json; charset=utf-8"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


# ---------------------------------------------------------------- 进程内 -----

class _FakeHandler:
    """最小 self 桩：只实现 _handle_agent_approval 所需的 path/_send。"""

    def __init__(self, path):
        self.path = path
        self._responses = []

    def _send(self, code, body, ctype=None, headers=None):
        self._responses.append((code, json.loads(body) if isinstance(body, str) else body))
        return None


def test_approval_flow_inprocess():
    """真实 Approval 闭环：挂起审批单 → Handler resolve → approve。"""
    import policy_engine
    from server_handlers_system import SystemMixin

    GID = 900000 + int(time.time()) % 10000
    results = {}

    def waiter():
        results["verdict"] = policy_engine.request_approval(
            "get_time", {}, summary="R8-P3 测试审批", goal_id=GID, default_deny=True)

    t = threading.Thread(target=waiter, daemon=True)
    t.start()
    ticket = None
    deadline = time.time() + 5
    while time.time() < deadline and ticket is None:
        with policy_engine._lock:
            if policy_engine._pending:
                ticket = next(iter(policy_engine._pending))
        time.sleep(0.05)
    check("审批单已生成（request_approval 挂起）", ticket is not None,
          f"ticket={str(ticket)[:8] if ticket else '无'}")

    h = _FakeHandler("/api/agent/approval?ticket=%s&decision=approve" % ticket)
    SystemMixin._handle_agent_approval(h)
    code, resp = h._responses[0]
    check("Handler 返回 200 ok:True", code == 200 and resp.get("ok") is True,
          f"code={code} resp={resp}")

    t.join(8)
    check("挂起线程被唤醒且返回 approve", results.get("verdict") == "approve",
          f"verdict={results.get('verdict')}")
    with policy_engine._lock:
        approved = "get_time" in policy_engine._session_approved.get(GID, set())
    check("per-goal 批准生效（approve_in_goal）", approved)
    return (ticket is not None) and results.get("verdict") == "approve" and approved


def test_approval_errors_inprocess():
    from server_handlers_system import SystemMixin

    h1 = _FakeHandler("/api/agent/approval?ticket=deadbeef&decision=approve")
    SystemMixin._handle_agent_approval(h1)
    c1 = h1._responses[0]
    check("未知/过期 ticket → 404", c1[0] == 404 and c1[1].get("ok") is False,
          f"code={c1[0]} resp={c1[1]}")

    h2 = _FakeHandler("/api/agent/approval?ticket=x&decision=maybe")
    SystemMixin._handle_agent_approval(h2)
    c2 = h2._responses[0]
    check("非法 decision → 400", c2[0] == 400, f"code={c2[0]} resp={c2[1]}")

    h3 = _FakeHandler("/api/agent/approval?decision=approve")
    SystemMixin._handle_agent_approval(h3)
    c3 = h3._responses[0]
    check("缺 ticket → 400", c3[0] == 400, f"code={c3[0]}")
    return c1[0] == 404 and c2[0] == 400 and c3[0] == 400


# ---------------------------------------------------------------- HTTP ------

_SERVER_PROC = None


def _start_server():
    global _SERVER_PROC
    env = dict(os.environ)
    env["ZhuangZhou_PORT"] = str(PORT)
    env["BIND_HOST"] = "127.0.0.1"
    _SERVER_PROC = subprocess.Popen(
        [PY, "server.py"], cwd=_PROJECT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
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


def _stop_server():
    global _SERVER_PROC
    if _SERVER_PROC is not None:
        try:
            _SERVER_PROC.terminate()
            _SERVER_PROC.wait(timeout=10)
        except Exception:
            try:
                _SERVER_PROC.kill()
            except Exception:
                pass
        _SERVER_PROC = None


def run_http_suite():
    section("HTTP 测试（自启服务器 :8033 → 真实 Handler 路由）")
    ok = []
    ok.append(check("服务器启动 /api/health 200", _start_server(), ""))

    # ---- intent 提交 ----
    code, r = _http("POST", "/api/agent/intent",
                    {"text": "帮我整理一份本周工作周报并总结项目进展", "source": "r8p3_test"})
    ok.append(check("intent 提交（长任务）→ 200", code == 200 and r.get("ok") is True,
                    f"code={code} action={r.get('action')}"))
    ok.append(check("intent create → goalId 非空", r.get("action") == "create" and bool(r.get("goalId")),
                    f"action={r.get('action')} goalId={r.get('goalId')} intentId={str(r.get('intentId'))[:12]}"))
    ok.append(check("intent 响应含意图字段", all(k in r for k in ("intentId", "classification", "confidence", "title", "reason")), ""))

    code2, r2 = _http("POST", "/api/agent/intent", {"text": "查一下天气", "source": "r8p3_test"})
    ok.append(check("intent 一次性文本 → skip（不建目标）", code2 == 200 and r2.get("action") == "skip",
                    f"action={r2.get('action')} reason={r2.get('reason')}"))

    # ---- goal 创建 ----
    code3, r3 = _http("POST", "/api/agent/goal",
                      {"title": "R8-P3 API 测试目标", "description": "验证 API → Agent Runtime 控制链"})
    ok.append(check("goal 创建 → 200 ok:True + goalId", code3 == 200 and r3.get("ok") is True and bool(r3.get("goalId")),
                    f"code={code3} goalId={r3.get('goalId')}"))
    gid = r3.get("goalId")
    if gid:
        code4, r4 = _http("GET", f"/api/goals/{gid}")
        ok.append(check("GET /api/goals/<id> 可查（GoalSystem 落库）", code4 == 200,
                        f"code={code4} title={r4.get('title') if isinstance(r4, dict) else '?'}"))

    # ---- 错误返回 ----
    code5, _ = _http("POST", "/api/agent/goal", {})
    ok.append(check("goal 缺 title → 400", code5 == 400, f"code={code5}"))

    code6, _ = _http("POST", "/api/agent/goal", raw_body=b"{bad json")
    ok.append(check("goal 非法 JSON → 400", code6 == 400, f"code={code6}"))

    code7, _ = _http("POST", "/api/agent/intent", {})
    ok.append(check("intent 缺 text → 400", code7 == 400, f"code={code7}"))

    code8, r8 = _http("POST", "/api/agent/approval?ticket=deadbeef&decision=approve")
    ok.append(check("approval 未知 ticket（HTTP）→ 404", code8 == 404, f"code={code8} resp={r8}"))

    code9, _ = _http("POST", "/api/agent/approval?decision=approve")
    ok.append(check("approval 缺 ticket（HTTP）→ 400", code9 == 400, f"code={code9}"))

    _stop_server()
    return all(ok)


# ------------------------------------------------------------------- main -----

def run_api_surface():
    print("=" * 70)
    print("R8-P3 Agent API Surface 测试")
    print("=" * 70)

    section("A. Approval 流程（进程内，真实 Handler + policy_engine）")
    ok_a1 = test_approval_flow_inprocess()
    ok_a2 = test_approval_errors_inprocess()

    ok_b = run_http_suite()

    results = [ok_a1, ok_a2, ok_b]
    print("\n  R8-P3 API 套件：" + ("ALL PASS ✅" if all(results) else "SOME FAIL ❌"))
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if run_api_surface() else 1)
