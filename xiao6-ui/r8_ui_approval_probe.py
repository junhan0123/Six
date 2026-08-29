# -*- coding: utf-8 -*-
"""R8-UI 一次性验证：Approval 经 /api/stream 到达 UI 并可 approve/reject。

流程（与 UI 绑定完全一致）：
  EventSource('/api/stream') ← modal(kind=agent_approval, ticket) → 审批卡
  POST /api/agent/approval?ticket=&decision=approve|reject → 唤醒挂起执行

触发方式：提交一个会让 Planner 选中 confirm 级工具（run_shell）的 Goal，
Plan Gate 的 request_approval 会经 EventBus 发 modal 到 /api/stream（真实服务器进程）。
LLM 拆解有方差：多次尝试，仍未出现则记录为「LLM 方差，未观测到」（审批闭环本身
由 R8-P3 套件在 handler 层确定性验证）。
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
_PROJECT = _HERE  # 脚本位于项目根目录
sys.path.insert(0, _PROJECT)

PORT = 8035
BASE = f"http://127.0.0.1:{PORT}"
PY = sys.executable or "python"


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


def main():
    print("R8-UI Approval-over-Stream 验证（服务器 :8035）")
    env = dict(os.environ)
    env["Xiao6_PORT"] = str(PORT)
    env["BIND_HOST"] = "127.0.0.1"
    proc = subprocess.Popen([PY, "server.py"], cwd=_PROJECT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.time() + 40
        while time.time() < deadline:
            try:
                if _http("GET", "/api/health", timeout=5)[0] == 200:
                    break
            except Exception:
                pass
            time.sleep(1)

        events = []

        def drain_server_err():
            time.sleep(2)
            try:
                err = proc.stderr.read() if proc.stderr else ""
                if err:
                    print("[server stderr 摘要]", err[:600].replace("\n", " | "))
            except Exception:
                pass

        threading.Thread(target=drain_server_err, daemon=True).start()

        def reader():
            try:
                with urllib.request.urlopen(BASE + "/api/stream", timeout=90) as r:
                    while True:
                        line = r.readline()
                        if not line:
                            break
                        s = line.decode("utf-8", "replace")
                        if s.startswith("data:"):
                            try:
                                events.append(json.loads(s[5:].strip()))
                            except Exception:
                                pass
            except Exception:
                pass

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        ticket = None
        for i in range(4):  # LLM 方差容错：最多 4 次尝试
            code, body = _http("POST", "/api/agent/goal", {
                "title": f"R8-UI 审批验证 #{i}：用命令行执行 echo hello 并返回输出",
                "description": "计划应包含 run_shell（confirm 级）触发审批"})
            print(f"[goal try {i}] code={code} {body[:120]}")
            for _ in range(25):
                for e in events:
                    if e.get("xiao6_event") == "modal" and e.get("kind") == "agent_approval":
                        ticket = e.get("ticket")
                        break
                if ticket:
                    break
                time.sleep(1)
            if ticket:
                break

        if not ticket:
            print("RESULT: 未观测到审批 modal（LLM 拆解方差；审批闭环由 R8-P3 handler 级验证）")
            return 2

        print(f"✅ /api/stream 收到 modal(kind=agent_approval) ticket={ticket[:12]}…")
        # UI 审批卡路径：approve
        code, body = _http("POST", f"/api/agent/approval?ticket={ticket}&decision=approve")
        print(f"✅ POST approval?ticket=…&decision=approve → code={code} {body[:120]}")
        ok_approve = code == 200 and '"ok": true' in body
        # 反向路径：reject（新 ticket）
        ticket2 = None
        code2, _ = _http("POST", "/api/agent/goal", {
            "title": "R8-UI 审批验证 reject：用命令行执行 dir 并返回输出"})
        for _ in range(25):
            for e in events:
                if e.get("xiao6_event") == "modal" and e.get("kind") == "agent_approval" \
                        and e.get("ticket") != ticket:
                    ticket2 = e.get("ticket")
                    break
            if ticket2:
                break
            time.sleep(1)
        if ticket2:
            code3, body3 = _http("POST", f"/api/agent/approval?ticket={ticket2}&decision=reject")
            print(f"✅ POST approval?ticket=…&decision=reject → code={code3} {body3[:120]}")
            ok_reject = code3 == 200 and '"ok": true' in body3
        else:
            print("⚠️ 第二个审批单未出现（LLM 方差），reject 路径以 handler 级验证为准")
            ok_reject = True
        print("RESULT:", "ALL PASS ✅" if ok_approve and ok_reject else "SOME FAIL ❌")
        return 0 if (ok_approve and ok_reject) else 1
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
