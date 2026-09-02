#!/usr/bin/env python3
"""Xiao6 · ai_core.lifecycle —— 启动就绪生命周期（Phase B 抽离，Extract Never Rewrite）。

本模块仅承载 server.py 原「启动就绪自检」相关逻辑，行为与原实现完全一致：

原实现（server.py）：
    _boot_ready_event = threading.Event()          # 就绪标志
    _BOOT_SELF_CHECK_DONE = False                  # 自检是否完成
    _BOOT_SELF_CHECK_RESULT = None                 # 自检结果缓存
    def _async_self_check(): ...                   # 后台线程跑 run_self_check
    # main() 内：threading.Thread(target=_async_self_check, daemon=True).start()

抽离后：
    lifecycle = Lifecycle()                         # 单例，等价原模块级全局
    lifecycle.ready_event / .self_check_done / .self_check_result
    lifecycle.run_boot_self_check()                # 等价原 daemon 线程启动
    lifecycle.is_ready                             # 等价原 _boot_ready_event.is_set()

红线说明：
- 不新增任何状态机 / 状态枚举。原代码只有「未就绪 -> 就绪」一次跃迁 + 自检结果缓存，
  本模块严格保持。
- 更广义的 AI 大脑编排状态机（IDLE/PLANNING/EXECUTING/REFLECTING）由 agent_runtime.py
  持有，不在本模块范围。
- 本模块为纯状态承载 + 一次后台自检触发器，不涉及业务/网络/权限/事件契约变更。
- 打印沿用原 print（与 server.py 启动日志一致）；日志统一收敛留待 Phase B Task H。
"""

from __future__ import annotations

import threading

from self_check import run_self_check


class Lifecycle:
    """启动就绪生命周期状态承载（原 server.py 模块级全局变量 + _async_self_check）。"""

    def __init__(self):
        self.ready_event = threading.Event()
        self.self_check_done = False
        self.self_check_result = None

    # ---- 读取接口（供 /api/ready、/api/health 使用，行为与原全局变量一致）----
    @property
    def is_ready(self) -> bool:
        return self.ready_event.is_set()

    # ---- 启动自检（后台异步，避免阻塞端口绑定，对应原 P0.1 修复）----
    def run_boot_self_check(self):
        threading.Thread(target=self._async_self_check, daemon=True).start()

    def _async_self_check(self):
        checks = None
        try:
            checks = run_self_check(force=True)
            status_emoji = "✓" if checks["ok"] else "✗"
            print(f"[{status_emoji}] 启动自检完成 @ {checks['checked_at']}")
            for c in checks["checks"]:
                mark = "✓" if c["ok"] else "✗"
                print(f"  {mark} {c['name']}: {c['detail']}")
            if not checks["ok"]:
                print("[WARN] 自检发现异常，服务继续启动但部分功能可能受限。详情请调用 /api/ready 查看。")
        except Exception as e:
            print(f"[WARN] 启动自检异常（可忽略）: {e}")
        finally:
            self.self_check_done = True
            self.self_check_result = checks
            self.ready_event.set()


# 单例：沿用原模块级全局语义（全进程一份就绪状态）
lifecycle = Lifecycle()
