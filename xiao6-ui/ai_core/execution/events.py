"""ExecutionEvent — 统一执行事件（Milestone 6）。

继续复用唯一 EventBus（eventbus.bus / publish_system）。禁止第二 EventBus。

设计决策（已写入 EXECUTION_DECISIONS.md）：
- spec 的 8 个执行事件名（PascalCase）映射为 eventbus.SYSTEM_EVENT_NAMES 的
  snake_case 系统事件（风格对齐现有 SYSTEM 事件如 scheduler_triggered）。
- 理由：DOMAIN_EVENT_NAMES 须与前端 zz-events.js 逐字一致（eventbus.py 硬纪律，
  『禁止新增同义事件名』）；新增 DOMAIN 名需改前端 = 违反『禁新增 UI』红线。
  而 SYSTEM 通道本就承载 telemetry / 工具进度，前端对未知 system 事件忽略，
  因此经 SYSTEM 通道扇出既复用单 EventBus、又不触碰 UI / DOMAIN 契约。
- Chat SSE 保持兼容：chat 路径仍经 server.py 的 emit 闭包直推 tool_start/tool_end；
  Execution 事件经 EventBus SYSTEM 通道，两者互不干扰。

事件信封：publish_system 自动包成 {"zhuangzhou_event": <name>, ...fields}。
"""

from __future__ import annotations

from typing import Any, Dict

# 8 个执行事件名（已登记到 eventbus.SYSTEM_EVENT_NAMES，单一来源）
EVENT_EXECUTION_STARTED = "execution_started"
EVENT_EXECUTION_UPDATED = "execution_updated"
EVENT_EXECUTION_COMPLETED = "execution_completed"
EVENT_EXECUTION_CANCELLED = "execution_cancelled"
EVENT_TOOL_STARTED = "tool_started"
EVENT_TOOL_FINISHED = "tool_finished"
EVENT_RETRY_STARTED = "retry_started"
EVENT_RETRY_FINISHED = "retry_finished"

ALL_EXECUTION_EVENTS = (
    EVENT_EXECUTION_STARTED, EVENT_EXECUTION_UPDATED, EVENT_EXECUTION_COMPLETED,
    EVENT_EXECUTION_CANCELLED, EVENT_TOOL_STARTED, EVENT_TOOL_FINISHED,
    EVENT_RETRY_STARTED, EVENT_RETRY_FINISHED,
)

# spec PascalCase → 实现 snake_case 映射（供文档与调试）
SPEC_TO_IMPL = {
    "ExecutionStarted": EVENT_EXECUTION_STARTED,
    "ExecutionUpdated": EVENT_EXECUTION_UPDATED,
    "ExecutionCompleted": EVENT_EXECUTION_COMPLETED,
    "ExecutionCancelled": EVENT_EXECUTION_CANCELLED,
    "ToolStarted": EVENT_TOOL_STARTED,
    "ToolFinished": EVENT_TOOL_FINISHED,
    "RetryStarted": EVENT_RETRY_STARTED,
    "RetryFinished": EVENT_RETRY_FINISHED,
}


class ExecutionEvent:
    """统一执行事件发布器（单例）。"""

    _instance = None

    @classmethod
    def get(cls) -> "ExecutionEvent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish(self, name: str, fields: Dict[str, Any]) -> None:
        if name not in ALL_EXECUTION_EVENTS:
            return
        try:
            from eventbus import publish_system
            payload = {"execution": True}
            if fields:
                payload.update(fields)
            publish_system(name, payload, source="execution")
        except Exception:
            # 事件发布失败绝不冒泡到执行主链路（Behavior Never Change）
            pass

    def execution_started(self, session) -> None:
        self.publish(EVENT_EXECUTION_STARTED, session.as_dict())

    def execution_updated(self, session, **extra) -> None:
        d = session.as_dict()
        d.update(extra)
        self.publish(EVENT_EXECUTION_UPDATED, d)

    def execution_completed(self, session) -> None:
        self.publish(EVENT_EXECUTION_COMPLETED, session.as_dict())

    def execution_cancelled(self, session) -> None:
        self.publish(EVENT_EXECUTION_CANCELLED, session.as_dict())

    def tool_started(self, session) -> None:
        self.publish(EVENT_TOOL_STARTED, {
            "execution_id": session.execution_id,
            "goal_id": getattr(session, 'goal_id', None),
            "task": session.task,
        })

    def tool_finished(self, session, ok: bool = True) -> None:
        self.publish(EVENT_TOOL_FINISHED, {
            "execution_id": session.execution_id,
            "goal_id": getattr(session, 'goal_id', None),
            "task": session.task,
            "ok": ok,
        })

    def retry_started(self, session) -> None:
        self.publish(EVENT_RETRY_STARTED, session.as_dict())

    def retry_finished(self, session, ok: bool = True) -> None:
        self.publish(EVENT_RETRY_FINISHED, {
            "execution_id": session.execution_id,
            "ok": ok,
        })


class ExecutionSession:
    """Execution session state machine for events."""

    def __init__(self, execution_id: str, task: str, context=None, goal_id: int = None):
        self.execution_id = execution_id
        self.task = task
        self.context = context
        self.goal_id = goal_id
        self.state = "pending"
        self.created_at = None
        self.completed_at = None
        self.result = None
        self.error = None

    def set_state(self, state: str):
        self.state = state
        if state in ("completed", "failed"):
            import time
            self.completed_at = time.time()

    def as_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "task": self.task,
            "session_id": getattr(getattr(self, 'context', None), 'session_id', 'default') if self.context else 'default',
            "goal_id": getattr(self, 'goal_id', None),
            "state": self.state,
        }
