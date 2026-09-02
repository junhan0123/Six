#!/usr/bin/env python3
"""小6 · 事件总线（EventBus）—— 模块间唯一通信脊柱

宪法 §15 铁律：取代 proactive.SUBSCRIBERS 全局可变队列与跨模块直发。
纯标准库实现，无新依赖。所有状态变更经本总线发布，订阅者按 topic 解耦接收。

约束（§15.5 / §12）：
- payload 仅允许 dict（禁止不可序列化对象入总线）。
- 同步订阅者须 <100ms，否则用 async_=True 投入线程池。
- 订阅者异常按重试策略处理，耗尽进入 Dead-Letter（内存列表 + 计数）。
- 日志禁打密钥 / PII。

SSE 迁移由 config.FEATURE_EVENTBUS 门控（默认 ON）；关闭即回退 SUBSCRIBERS 旧路径。
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Optional

# SSE 实时推送统一汇聚主题（proactive / scene 均发布到此，SSE 桥订阅扇出）
TOPIC_SSE = "xiao6.sse"

# Phase 11 全息 HUD：常驻状态光环 / 情境 glance 卡订阅的状态机事件主题
TOPIC_HUD_STATE = "xiao6.hud.state"
# 目标更新主题（goals.py 已向 "xiao6.goal" 发布；此处提供语义化别名，避免重复造事件）
TOPIC_GOAL_UPDATE = "xiao6.goal"
# Phase 13-1 移动伴随端：移动端 ↔ 桌面的轻量同步事件主题
TOPIC_MOBILE_SYNC = "xiao6.mobile.sync"
# Phase 9-3 剪贴板：剪贴板内容变化的同步事件主题
TOPIC_CLIPBOARD = "xiao6.clipboard"

# 重试上限（与 priority 无关，统一 2 次；超过即进死信）
_MAX_RETRIES = 2
# 异步订阅者线程池规模（标准库，无新依赖）
_ASYNC_WORKERS = 4


@dataclass
class Event:
    """总线事件。payload 必须为 dict（§15.5）。"""

    event_id: str
    topic: str
    timestamp: float
    source: str
    payload: dict
    priority: int = 5
    correlation_id: Optional[str] = None


class EventBus:
    """进程级事件总线：topic 维度的 pub/sub。

    订阅者分两类：
    - sync（默认）：publish 时内联执行，必须快速（<100ms）。
    - async_：投入线程池，publish 立即返回，不阻塞发布方。
    """

    def __init__(self) -> None:
        self._subs: dict[str, list[dict]] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=_ASYNC_WORKERS, thread_name_prefix="zz-bus"
        )
        self.dead_letters: list[dict] = []  # 重试耗尽的事件（含错误快照）
        self._dl_lock = threading.Lock()

    # ---- 订阅 / 退订 ----
    def subscribe(
        self,
        topic: str,
        cb: Callable[[Event], None],
        *,
        async_: bool = False,
        priority: int = 5,
    ) -> str:
        """订阅某 topic，返回 token（供 unsubscribe）。"""
        token = uuid.uuid4().hex
        with self._lock:
            self._subs.setdefault(topic, []).append(
                {"token": token, "cb": cb, "async": async_, "priority": priority}
            )
        return token

    def unsubscribe(self, token: str) -> bool:
        with self._lock:
            for topic, lst in self._subs.items():
                for i, sub in enumerate(lst):
                    if sub["token"] == token:
                        lst.pop(i)
                        return True
        return False

    def subscribers(self, topic: str) -> list[dict]:
        with self._lock:
            return list(self._subs.get(topic, []))

    # ---- 发布 ----
    def publish(
        self,
        topic: str,
        payload: dict,
        *,
        source: str = "",
        correlation_id: Optional[str] = None,
        priority: int = 5,
    ) -> None:
        if not isinstance(payload, dict):
            raise TypeError(
                f"[EventBus] payload 必须为 dict（§15.5 禁不可序列化对象），收到 {type(payload)}"
            )
        event = Event(
            event_id=uuid.uuid4().hex,
            topic=topic,
            timestamp=time.time(),
            source=source,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
        )
        for sub in sorted(self.subscribers(topic), key=lambda s: -s["priority"]):
            if sub["async"]:
                self._executor.submit(self._dispatch, sub, event)
            else:
                self._dispatch(sub, event)

    # ---- 派发 + 重试 + 死信 ----
    def _dispatch(self, sub: dict, event: Event) -> None:
        last_err: Optional[BaseException] = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                sub["cb"](event)
                return
            except Exception as e:  # 订阅者抛错：重试，耗尽进死信
                last_err = e
                if attempt < _MAX_RETRIES:
                    continue
        with self._dl_lock:
            self.dead_letters.append(
                {
                    "event_id": event.event_id,
                    "topic": event.topic,
                    "source": event.source,
                    "error": f"{type(last_err).__name__}: {last_err}",
                    "ts": time.time(),
                }
            )


# 进程级单例（基础设施，常驻）
bus = EventBus()


def enabled() -> bool:
    """SSE 迁移是否走 EventBus（默认 ON，可经 config.FEATURE_EVENTBUS 瞬切回 SUBSCRIBERS）。"""
    try:
        import config

        return bool(getattr(config, "FEATURE_EVENTBUS", False))
    except Exception:
        return False


def publish_sse(payload: dict, source: str = "") -> None:
    """经总线发布一条 SSE 推送事件（proactive / scene 共用入口）。"""
    bus.publish(TOPIC_SSE, payload, source=source or "eventbus")


# ── Phase 6 Order 1：领域事件合约信封 ───────────────────────────────────────
# 这些名字必须与前端 zz-events.js 逐字一致（单一事件名来源纪律，readiness §5）。
# 修改须同步两端，禁止新增同义事件名。
DOMAIN_EVENT_NAMES = {
    "GOAL_CREATED", "GOAL_UPDATED", "GOAL_PLANNED", "GOAL_STARTED", "GOAL_RUNNING",
    "GOAL_COMPLETED", "GOAL_FAILED",
    "AGENT_CREATED", "AGENT_STARTED", "AGENT_THINKING", "AGENT_WORKING",
    "AGENT_WAITING", "AGENT_COMPLETED", "AGENT_FAILED",
    "TASK_CREATED", "TASK_STARTED", "TASK_RUNNING", "TASK_COMPLETED", "TASK_FAILED",
    "TOOL_CALLED", "TOOL_DONE", "MEMORY_UPDATED", "MEMORY_CREATED",
    "MEMORY_STORED", "MEMORY_LINKED", "MEMORY_ARCHIVED",
    "MEMORY_RETRIEVED", "MEMORY_CONSOLIDATED", "MEMORY_DECAYED",
    # —— P4.4 Context Engine 生命周期（构建成功 / 预算裁剪 / 同域去重）——
    "CONTEXT_BUILT", "CONTEXT_TRUNCATED", "CONTEXT_DEDUPED",
    "NOTIFICATION_RAISED", "REFLECTING", "ERROR_OCCURRED", "WORKSPACE_SWITCHED",
    "FOCUS_CHANGED", "STATE_SYNC",
    # —— Order 5：Intent Gateway 生命周期（User Intent → Goal Decision Engine → Goal）——
    "INTENT_RECEIVED", "INTENT_ANALYZING", "INTENT_CLASSIFIED",
    "INTENT_ACCEPTED", "INTENT_REJECTED", "INTENT_CONVERTED_TO_GOAL",
    # —— Phase 7 · Agent Trust Layer（执行意图透明化 + 工具风险分级）——
    "AGENT_INTENT_ANALYZED",
    "TOOL_RISK_CHECKED",
    # —— Phase 7 Order 1：Computer World Model（只读世界观测事件；动作能力在 Order 2+）——
    "COMPUTER_WORLD_SYNC",
    "WINDOW_OPENED", "WINDOW_CLOSED", "WINDOW_FOCUSED",
    "APP_LAUNCHED", "APP_EXITED",
    "PROCESS_SPAWNED", "PROCESS_TERMINATED",
    "FILE_CREATED", "FILE_MODIFIED", "FILE_DELETED",
    "PROJECT_DETECTED", "PROJECT_UPDATED",
    "BROWSER_NAVIGATED", "BROWSER_TAB_OPENED", "BROWSER_TAB_CLOSED",
    "TERMINAL_SPAWNED", "TERMINAL_EXITED",
    "DEVICE_STATE_CHANGED",
    # —— Phase 7 Order 2：Computer Action 生命周期（动作能力执行安全层；经 Policy Engine 裁决）——
    #     仅声明动作事件，授权裁决全部委托既有 Policy Engine（evaluate / request_approval）。
    "COMPUTER_ACTION_PLANNED",
    "COMPUTER_ACTION_CALLED",
    "COMPUTER_ACTION_DONE",
    "COMPUTER_ACTION_FAILED",
    "COMPUTER_ACTION_DENIED",
    "COMPUTER_ACTION_VERIFIED",
    "COMPUTER_ACTION_UNVERIFIED",
    # —— Phase 21：四态相位（观察/规划/执行/验证），供 AI Core 状态表达 ——
    "COMPUTER_ACTION_PHASE",
    # —— Phase 8 Order 1：Screen Capture Foundation（仅采集，不含任何理解/识别）——
    "SCREEN_CAPTURED",
    "SCREEN_CAPTURE_FAILED",
    # —— Phase 8 MVP：Computer Perception（观察层；Vision 绝不控制）——
    #     注：PERCEPTION_FOCUS_CHANGED 为 UIA accessibility focus，与 Phase 6 既有
    #     FOCUS_CHANGED（银河节点聚焦态）命名不同、互不冲突，均为 DOMAIN 单一来源。
    "PERCEPTION_SYNC",
    "PERCEPTION_UI_UPDATED",
    "PERCEPTION_OCR_UPDATED",
    "PERCEPTION_VISION_FACT",
    "PERCEPTION_FOCUS_CHANGED",
}


def publish_domain(name: str, payload: dict, source: str = "") -> None:
    """发布一条领域事件到 SSE 扇出（前端 AppState 合约入口）。

    信封格式（与前端 event-bridge.js 约定）：
        {"xiao6_event": <name>, "payload": <payload>, "ts": <unix>}

    纪律（readiness §4 R1 / §5.2）：
    - name 必须是 DOMAIN_EVENT_NAMES（与前端 zz-events.js 单一来源对齐），否则拒绝。
    - UI 永不直接读后端内部数据；只经此信封消费事件。
    - payload 必须为 dict（§15.5）。
    """
    if name not in DOMAIN_EVENT_NAMES:
        raise ValueError(f"[EventBus] 未知领域事件名（须对齐前端 zz-events.js）: {name}")
    if not isinstance(payload, dict):
        raise TypeError("[EventBus] payload 必须为 dict（§15.5 禁不可序列化对象）")
    bus.publish(
        TOPIC_SSE,
        {"xiao6_event": name, "payload": payload, "ts": time.time()},
        source=source or "domain",
    )


# ── Phase 6 Hotfix：系统事件命名空间（与领域事件合约并列的第二条 SSE 通道）──
# 这些事件由前端独立 SSE 监听器（app.js / glance-card.js）消费，承载 telemetry /
# 主动推送 / 输入信号 / 工具进度 / 面板控制，不属于领域生命周期状态（不进 AppState）。
# 纪律：同样须登记到 SYSTEM_EVENT_NAMES 单一来源，经 publish_system 校验，禁止裸 bus.publish。
# 与 DOMAIN_EVENT_NAMES 互斥：同一语义只可属于其一，禁止在两条通道间同义漂移。
SYSTEM_EVENT_NAMES = {
    "proactive",          # 主动智能推送（proactive.py）
    "scene",              # 世界态势场景卡（scene.py）
    "memory_reminder",    # 重要日期/记忆提醒（agent_runtime，push_proactive 失败回退）
    "agent_state",        # Agent 编排态快照（agent_runtime，另发 agent:state 主题）
    "modal",              # 审批/天气/热点弹窗（policy_engine / server）
    "wakeword_detected",  # 语音唤醒词命中（server KWS）
    # —— Phase 8 MVP：Perception telemetry / 主动感知提示（类 scene / agent_state）——
    "perception_alert",   # 感知到值得主动告知用户的状态（错误弹窗/登录界面/验证码）
    "perception_health",  # 引擎健康/采集帧率/缓存命中 telemetry
    # —— Phase 9 Order 1：Scheduler 调度事件（周期任务生命周期）——
    "scheduler_triggered",   # 任务到期触发
    "scheduler_completed",   # 任务执行完成
    "scheduler_failed",      # 任务执行失败
    # —— Phase 9 B1/B3：Proactive Engine 决策与执行结果（薄决策层 → enacter 落地）——
    "proactive_decision",    # 引擎决策结果（IGNORE/SUGGEST/NOTIFY/CREATE_GOAL）
    "proactive_result",      # 决策落地结果（如 CREATE_GOAL 实际建出的 goal_id）
    "long_running",          # 任务/目标长时间运行看门狗告警
    # —— Phase 3 Execution Platform：统一执行事件（经单 EventBus SYSTEM 通道扇出）——
    #     前端对未知 system 事件忽略（不触碰 DOMAIN/zz-events.js 契约，禁新增 UI）。
    #     语义对齐 spec 的 ExecutionStarted/Updated/Completed/Cancelled/
    #     ToolStarted/ToolFinished/RetryStarted/RetryFinished（snake_case 风格）。
    "execution_started",
    "execution_updated",
    "execution_completed",
    "execution_cancelled",
    "tool_started",
    "tool_finished",
    "retry_started",
    "retry_finished",
}


def publish_system(name: str, fields: dict, source: str = "") -> None:
    """发布一条系统事件到 SSE（与 publish_domain 平行的校验纪律，单一来源 SYSTEM_EVENT_NAMES）。

    信封保持扁平结构 {"xiao6_event": <name>, ...fields}，与前端独立监听器（app.js /
    glance-card.js）既有解析约定一致（字段在顶层，不由 payload 包裹）。
    """
    if name not in SYSTEM_EVENT_NAMES:
        raise ValueError(f"[EventBus] 未知系统事件名（须登记到 SYSTEM_EVENT_NAMES）: {name}")
    if not isinstance(fields, dict):
        raise TypeError("[EventBus] fields 必须为 dict")
    payload = {"xiao6_event": name}
    payload.update(fields)
    bus.publish(TOPIC_SSE, payload, source=source or "system")


# 别名定义（提升代码可读性）
publish_user = lambda name, payload, source="": publish_domain(name, payload, source)
publish_agent = lambda name, payload, source="": publish_domain(name, payload, source)

