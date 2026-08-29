#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小6 · Scheduler（Phase 9 Order 1）—— 周期任务调度基础层

职责：
  - 注册/取消/调度任务
  - 支持单次延迟、周期执行、事件驱动三种模式
  - 到期触发时通过 EventBus 发布 SYSTEM 事件（不直接执行业务逻辑）
  - 管理任务生命周期：created → scheduled → triggered → completed/cancelled

纪律（最高约束）：
  - 本模块不直接调用 AgentRuntime / Memory / Goal / PermissionGuard
  - 本模块不执行任何工具
  - 所有业务逻辑由订阅者（ProactiveEngine / 其他）经 EventBus 事件驱动
  - 仅通过 publish_system() 发事件，不发 DOMAIN 事件
  - 单 Runtime 纪律：不新建线程池，复用 threading.Timer / ThreadPoolExecutor

架构位置：
  Scheduler → EventBus → ProactiveEngine（Phase 9 Order 2+）
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional

from eventbus import publish_system


class TaskStatus(str, Enum):
    CREATED = "created"
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class ScheduledTask:
    """调度任务数据模型"""
    task_id: str
    callback: Callable[..., None]
    status: TaskStatus = TaskStatus.CREATED
    # 单次延迟任务字段
    delay_seconds: Optional[float] = None
    run_at: Optional[float] = None  # 绝对触发时间
    # 周期任务字段
    interval_seconds: Optional[float] = None
    max_runs: Optional[int] = None  # None = 无限
    run_count: int = 0
    # 事件驱动任务字段
    event_name: Optional[str] = None
    # 元数据
    created_at: float = field(default_factory=time.time)
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None
    error: Optional[str] = None

    @property
    def is_periodic(self) -> bool:
        return self.interval_seconds is not None

    @property
    def is_event_driven(self) -> bool:
        return self.event_name is not None

    @property
    def is_single(self) -> bool:
        return not self.is_periodic and not self.is_event_driven


class Scheduler:
    """周期任务调度器（Phase 9 Order 1）

    用法示例：
        scheduler = Scheduler()
        scheduler.start()

        # 单次延迟任务
        scheduler.schedule_once(
            delay_seconds=60,
            callback=lambda: None,
            task_id="once_task"
        )

        # 周期任务
        scheduler.schedule_interval(
            interval_seconds=300,
            callback=lambda: None,
            task_id="periodic_task",
            max_runs=10
        )

        # 事件驱动任务
        scheduler.schedule_event(
            event_name="PROACTIVE_SCENE_DETECTED",
            callback=lambda event: handle_event(event),
            task_id="event_task"
        )

        # 取消任务
        scheduler.cancel("once_task")

        # 关闭
        scheduler.shutdown()
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._event_subscribers: Dict[str, list] = {}  # event_name → [task_id, ...]
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._condition = threading.Condition(self._lock)
        self._shutdown_event = threading.Event()

    def start(self) -> None:
        """启动调度器后台线程"""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._shutdown_event.clear()
            self._thread = threading.Thread(
                target=self._monitor_loop,
                name="zz-scheduler",
                daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        """停止调度器后台线程（不取消已注册任务）"""
        with self._lock:
            self._running = False
            self._condition.notify_all()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def shutdown(self) -> None:
        """关闭调度器并取消所有任务"""
        self.stop()
        with self._lock:
            for task in self._tasks.values():
                if task.status in (TaskStatus.CREATED, TaskStatus.SCHEDULED):
                    task.status = TaskStatus.CANCELLED
            self._tasks.clear()
            self._event_subscribers.clear()

    # ── 任务注册 ──

    def schedule_once(
        self,
        delay_seconds: float,
        callback: Callable[..., None],
        task_id: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> str:
        """注册单次延迟任务

        Args:
            delay_seconds: 延迟秒数
            callback: 触发时调用的回调（接收 task 参数）
            task_id: 任务 ID（自动生成）
            meta: 元数据

        Returns:
            task_id
        """
        task_id = task_id or f"once_{uuid.uuid4().hex[:8]}"
        run_at = time.time() + delay_seconds

        task = ScheduledTask(
            task_id=task_id,
            callback=callback,
            delay_seconds=delay_seconds,
            run_at=run_at,
            next_run_at=run_at,
        )
        if meta:
            task.meta = meta  # type: ignore

        with self._lock:
            self._tasks[task_id] = task
            task.status = TaskStatus.SCHEDULED
            self._condition.notify_all()

        return task_id

    def schedule_interval(
        self,
        interval_seconds: float,
        callback: Callable[..., None],
        task_id: Optional[str] = None,
        max_runs: Optional[int] = None,
        meta: Optional[dict] = None,
    ) -> str:
        """注册周期任务

        Args:
            interval_seconds: 执行间隔（秒）
            callback: 触发时调用的回调（接收 task 参数）
            task_id: 任务 ID
            max_runs: 最大执行次数（None = 无限）
            meta: 元数据

        Returns:
            task_id
        """
        task_id = task_id or f"interval_{uuid.uuid4().hex[:8]}"
        now = time.time()

        task = ScheduledTask(
            task_id=task_id,
            callback=callback,
            interval_seconds=interval_seconds,
            max_runs=max_runs,
            next_run_at=now + interval_seconds,
        )
        if meta:
            task.meta = meta  # type: ignore

        with self._lock:
            self._tasks[task_id] = task
            task.status = TaskStatus.SCHEDULED
            self._condition.notify_all()

        return task_id

    def schedule_event(
        self,
        event_name: str,
        callback: Callable[[dict], None],
        task_id: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> str:
        """注册事件驱动任务（当 EventBus 发布指定事件时触发）

        Args:
            event_name: 监听的事件名（SYSTEM 事件）
            callback: 触发时调用的回调（接收 event_payload 参数）
            task_id: 任务 ID
            meta: 元数据

        Returns:
            task_id
        """
        task_id = task_id or f"event_{uuid.uuid4().hex[:8]}"

        task = ScheduledTask(
            task_id=task_id,
            callback=callback,
            event_name=event_name,
        )
        if meta:
            task.meta = meta  # type: ignore

        with self._lock:
            self._tasks[task_id] = task
            task.status = TaskStatus.SCHEDULED
            self._event_subscribers.setdefault(event_name, []).append(task_id)

        return task_id

    # ── 任务管理 ──

    def cancel(self, task_id: str) -> bool:
        """取消任务

        Returns:
            True 如果成功取消，False 如果任务不存在或已终止
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
                return False
            task.status = TaskStatus.CANCELLED
            # 从事件订阅中移除
            if task.event_name and task.event_name in self._event_subscribers:
                subs = self._event_subscribers[task.event_name]
                if task_id in subs:
                    subs.remove(task_id)
            self._condition.notify_all()
            return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务状态"""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> Dict[str, ScheduledTask]:
        """列出所有任务"""
        with self._lock:
            return dict(self._tasks)

    def clear_completed(self) -> int:
        """清理已完成/已取消的任务

        Returns:
            清理的任务数量
        """
        with self._lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED)
            ]
            for tid in to_remove:
                del self._tasks[tid]
                if self._tasks[tid].event_name in self._event_subscribers:
                    subs = self._event_subscribers[self._tasks[tid].event_name]  # type: ignore
                    if tid in subs:
                        subs.remove(tid)
            return len(to_remove)

    # ── 后台监控循环 ──

    def _monitor_loop(self) -> None:
        """后台监控线程主循环"""
        while not self._shutdown_event.is_set():
            with self._condition:
                now = time.time()
                triggered = []

                # 检查到期任务
                for task in list(self._tasks.values()):
                    if task.status != TaskStatus.SCHEDULED:
                        continue
                    if task.next_run_at and now >= task.next_run_at:
                        triggered.append(task)

                # 触发到期任务
                for task in triggered:
                    self._trigger_task(task)

                # 计算下次检查时间
                next_check = 1.0  # 默认 1 秒
                for task in self._tasks.values():
                    if task.status == TaskStatus.SCHEDULED and task.next_run_at:
                        remaining = task.next_run_at - time.time()
                        if 0 < remaining < next_check:
                            next_check = remaining

                # 等待下一次检查
                self._condition.wait(timeout=next_check)

    def _trigger_task(self, task: ScheduledTask) -> None:
        """触发任务执行"""
        task.status = TaskStatus.TRIGGERED
        task.last_run_at = time.time()

        # 发布 TRIGGERED 事件
        try:
            publish_system("scheduler_triggered", {
                "task_id": task.task_id,
                "type": "once" if task.is_single else ("interval" if task.is_periodic else "event"),
                "timestamp": task.last_run_at,
            })
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            return

        # 执行回调
        try:
            task.callback(task)
            task.status = TaskStatus.COMPLETED

            # 发布 COMPLETED 事件
            publish_system("scheduler_completed", {
                "task_id": task.task_id,
                "run_count": task.run_count,
                "timestamp": time.time(),
            })
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED

            # 发布 FAILED 事件
            publish_system("scheduler_failed", {
                "task_id": task.task_id,
                "error": str(e),
                "timestamp": time.time(),
            })
            return

        # 更新下次执行时间（周期任务）
        if task.is_periodic and task.status == TaskStatus.COMPLETED:
            task.run_count += 1
            if task.max_runs and task.run_count >= task.max_runs:
                task.status = TaskStatus.COMPLETED
                return
            task.next_run_at = time.time() + task.interval_seconds
            task.status = TaskStatus.SCHEDULED

    # ── 事件分发（由 EventBus 订阅者调用） ──

    def on_system_event(self, event_name: str, payload: dict) -> None:
        """处理系统事件，触发事件驱动任务

        此方法由 EventBus 订阅者调用，不在 Scheduler 内部调用。
        """
        with self._lock:
            task_ids = self._event_subscribers.get(event_name, [])
            for tid in task_ids:
                task = self._tasks.get(tid)
                if task and task.status == TaskStatus.SCHEDULED:
                    # 触发事件驱动任务
                    task.status = TaskStatus.TRIGGERED
                    task.last_run_at = time.time()
                    try:
                        task.callback(payload)
                        task.status = TaskStatus.COMPLETED
                    except Exception as e:
                        task.error = str(e)
                        task.status = TaskStatus.FAILED

    # ── 状态查询 ──

    @property
    def task_count(self) -> int:
        with self._lock:
            return len(self._tasks)

    @property
    def running(self) -> bool:
        return self._running


# ── 模块级单例（可选）──

_default_scheduler: Optional[Scheduler] = None
_default_scheduler_lock = threading.Lock()


def get_scheduler() -> Scheduler:
    """获取全局调度器单例"""
    global _default_scheduler
    with _default_scheduler_lock:
        if _default_scheduler is None:
            _default_scheduler = Scheduler()
        return _default_scheduler


def reset_scheduler() -> None:
    """重置全局调度器单例（测试用）"""
    global _default_scheduler
    with _default_scheduler_lock:
        if _default_scheduler:
            _default_scheduler.shutdown()
        _default_scheduler = None
