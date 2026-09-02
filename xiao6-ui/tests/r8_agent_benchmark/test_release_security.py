# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.test_release_security — R8 Release Closure 安全验证

Phase 3 静态文件安全（_serve_file realpath 校验）：
  - 正常静态文件 200
  - /.env、/../.env、/zz-space/../.env、路径穿越变体（含 URL 编码）→ 全部 404
  - 目录外文件（/zz-space/../server.py 等含 ".." 分量）→ 404

Phase 5 API 基础安全（POST Content-Type + Origin）：
  - text/plain POST /api/agent/goal → 415
  - 跨站 Origin POST → 403
  - application/json + 无 Origin → 放行（200）
  - /api/chat、/api/agent/intent 同规则
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, _HERE)

from _fixture import check, section  # noqa: E402

PORT = 8037
BASE = f"http://127.0.0.1:{PORT}"
PY = sys.executable or "python"
_SERVER = None


def _req(method, path, body=None, ctype=None, origin=None, timeout=20):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8") if isinstance(body, (dict, list)) else body
        headers["Content-Type"] = ctype or "application/json"
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except Exception as e:
        return 0, str(e)[:200]


def run_release_security():
    section("R8 Release Closure 安全验证（静态文件 + POST 收口）")

    env = dict(os.environ)
    env["XIAO6_PORT"] = str(PORT)
    env["BIND_HOST"] = "127.0.0.1"
    global _SERVER
    _SERVER = subprocess.Popen([PY, "server.py"], cwd=_PROJECT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 40
    while time.time() < deadline:
        try:
            if _req("GET", "/api/health")[0] == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    ok = []

    # ---- Phase 3：静态文件安全 ----
    ok.append(check("正常静态文件 /zz-space/index.html → 200",
                    _req("GET", "/zz-space/index.html")[0] == 200, ""))
    for p in ["/.env", "/..%2F.env", "/%2e%2e/%2e%2e/.env", "/zz-space/../.env",
              "/../.env", "/zz-space/../server.py", "/%2e%2e/env%2e"]:
        code, _ = _req("GET", p)
        ok.append(check(f"路径穿越 {p} → 404", code == 404, f"code={code}"))
    ok.append(check("缺失文件 /no-such-file.js → 404",
                    _req("GET", "/no-such-file.js")[0] == 404, ""))

    # ---- Phase 5：POST Content-Type / Origin ----
    c1, _ = _req("POST", "/api/agent/goal", body=b"title=x", ctype="text/plain")
    ok.append(check("text/plain POST /api/agent/goal → 415", c1 == 415, f"code={c1}"))
    c2, _ = _req("POST", "/api/agent/intent", body=b"text=x", ctype="text/plain")
    ok.append(check("text/plain POST /api/agent/intent → 415", c2 == 415, f"code={c2}"))
    c3, _ = _req("POST", "/api/chat", body=b"{}", ctype="text/plain")
    ok.append(check("text/plain POST /api/chat → 415", c3 == 415, f"code={c3}"))
    c4, _ = _req("POST", "/api/agent/goal", body={"title": "x"},
                 ctype="application/json", origin="http://evil.example.com")
    ok.append(check("跨站 Origin POST /api/agent/goal → 403", c4 == 403, f"code={c4}"))
    c5, body5 = _req("POST", "/api/agent/goal", body={"title": "Release Security 验证目标"},
                     ctype="application/json")
    try:
        gid = json.loads(body5).get("goalId")
    except Exception:
        gid = None
    ok.append(check("application/json + 无 Origin → 放行（200 + goalId）",
                    c5 == 200 and bool(gid), f"code={c5} goalId={gid}"))
    c6, _ = _req("POST", "/api/agent/approval?ticket=deadbeef&decision=approve")
    ok.append(check("approval 端点（无 body）不受影响 → 404（未知 ticket）", c6 == 404, f"code={c6}"))

    try:
        _SERVER.terminate()
        _SERVER.wait(timeout=10)
    except Exception:
        try:
            _SERVER.kill()
        except Exception:
            pass
    _SERVER = None

    passed = sum(1 for x in ok if x)
    print(f"\n  Release Security 套件：{passed}/{len(ok)} 项通过")
    return all(ok)


if __name__ == "__main__":
    sys.exit(0 if run_release_security() else 1)
