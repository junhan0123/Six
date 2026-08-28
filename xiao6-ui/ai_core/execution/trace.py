# -*- coding: utf-8 -*-
"""ai_core.execution.trace — Unified Execution Trace Recorder (R8-P1)

纯观测层：把每次工具执行的事实落盘到 logs/execution_trace/，供 R8-P1 benchmark
与可靠性分析消费。

设计纪律（R8-P1 §任务1）：
- **不改变执行逻辑**：所有 trace 写入均用 try/except 包裹，任何 IO/序列化失败
  都被静默吞掉，绝不冒泡到执行主链路、绝不影响返回值或控制流。
- **单一记录出口**：本模块是 Execution Trace 的唯一写入者；不新建第二 EventBus、
  不复制 ExecutionEvent 语义，仅复用既有的 execution_id / goal_id 等上下文。
- **零执行依赖**：trace 模块导入期不依赖任何可执行模块；record() 的入参均为
  纯数据，调用方传入即可。

记录字段（任务1 要求）：
  goal_id / task_id / step_id / tool_name / args摘要 / start_time / end_time /
  duration_ms / status / error / recovery_action / execution_id / attempt
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

_TRACE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "execution_trace",
)
_TRACE_LOCK = threading.Lock()

# status 词汇（与执行链返回值语义对齐）
STATUS_RUNNING = "running"
STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_BLOCKED = "blocked"        # policy block / 注入阻断 / 预算耗尽
STATUS_REJECTED = "rejected"      # confirm 审批被拒
STATUS_UNKNOWN = "unknown"

# recovery_action 词汇（与 agent_runtime._execute_task 恢复路由对齐）
RECOVERY_NONE = "none"
RECOVERY_RETRY_BACKOFF = "retry_with_backoff"          # network 类：短退避重试
RECOVERY_RETRY_ALTERNATIVE = "retry_alternative_tool"  # file 类：换替代工具重试
RECOVERY_FAIL_CLOSED = "fail_closed_no_retry"          # fatal 类：标记退出不重试
RECOVERY_POLICY_BLOCKED = "policy_blocked"             # Policy block
RECOVERY_BUDGET_EXHAUSTED = "budget_exhausted"         # 预算闸门拒绝
RECOVERY_DEPTH_EXCEEDED = "depth_exceeded"             # 嵌套深度超限


def _ensure_dir() -> None:
    try:
        os.makedirs(_TRACE_DIR, exist_ok=True)
    except Exception:
        pass


def _summarize_args(args: Any, limit: int = 200) -> str:
    """把 args 压缩为可落盘的摘要（脱敏 + 截断），避免凭证/大对象落盘。"""
    try:
        if args is None:
            return ""
        if not isinstance(args, (dict, list, tuple)):
            return str(args)[:limit]
        s = json.dumps(args, ensure_ascii=False, default=str)
        # 脱敏：与 server_globals._ACCESS_LOG_REDACT_RE 同词汇的敏感键置 ***
        try:
            import re as _re

            s = _re.sub(
                r"(\"(?:token|access[_-]?token|auth[_-]?token|secret|password|passwd|api[_-]?key|apikey)\"\s*:\s*)\"[^\"]*\"",
                r"\1\"***\"", s, flags=_re.IGNORECASE,
            )
        except Exception:
            pass
        return s[:limit]
    except Exception:
        return "<unserializable>"


def record(
    *,
    goal_id: Optional[int] = None,
    task_id: Optional[int] = None,
    step_id: Optional[str] = None,
    tool_name: str = "",
    args: Any = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    status: str = STATUS_UNKNOWN,
    error: Optional[str] = None,
    recovery_action: str = RECOVERY_NONE,
    execution_id: Optional[str] = None,
    attempt: int = 0,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """写一条 Execution Trace 记录（JSONL）。返回 execution_id（供调用方串联）。

    本函数对任何异常都静默吞掉——观测层绝不影响执行主链路。
    """
    try:
        _ensure_dir()
        ts = time.time()
        if execution_id is None:
            execution_id = uuid.uuid4().hex[:8]
        duration_ms = None
        if start_time is not None and end_time is not None:
            try:
                duration_ms = round((end_time - start_time) * 1000.0, 2)
            except Exception:
                duration_ms = None
        rec = {
            "execution_id": execution_id,
            "goal_id": goal_id,
            "task_id": task_id,
            "step_id": step_id,
            "tool_name": tool_name,
            "args_summary": _summarize_args(args),
            "start_time": datetime.fromtimestamp(start_time).isoformat(timespec="milliseconds") if start_time else None,
            "end_time": datetime.fromtimestamp(end_time).isoformat(timespec="milliseconds") if end_time else None,
            "start_epoch": round(start_time, 3) if start_time else None,
            "end_epoch": round(end_time, 3) if end_time else None,
            "duration_ms": duration_ms,
            "status": status,
            "error": (str(error)[:500] if error else None),
            "recovery_action": recovery_action,
            "attempt": attempt,
            "recorded_at": datetime.fromtimestamp(ts).isoformat(timespec="milliseconds"),
        }
        if extra:
            for k, v in (extra or {}).items():
                rec.setdefault(k, v)
        line = json.dumps(rec, ensure_ascii=False)
        fname = "trace_%s.jsonl" % datetime.fromtimestamp(ts).strftime("%Y%m%d")
        with _TRACE_LOCK:
            with open(os.path.join(_TRACE_DIR, fname), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return execution_id
    except Exception:
        return execution_id or ""


def begin(**kwargs) -> Dict[str, Any]:
    """便捷入口：记录一条 status=running 的起始记录，返回句柄供 end() 复用。

    典型用法：
        h = trace.begin(goal_id=g, task_id=t, tool_name="get_time", args={})
        ... 执行 ...
        trace.end(h, status="ok")
    """
    now = time.time()
    eid = kwargs.pop("execution_id", None) or uuid.uuid4().hex[:8]
    record(start_time=now, end_time=now, status=STATUS_RUNNING, execution_id=eid, **kwargs)
    h = dict(kwargs)
    h["execution_id"] = eid
    h["start_time"] = now
    return h


def end(handle: Dict[str, Any], *, status: str, error: Optional[str] = None,
        recovery_action: str = RECOVERY_NONE, attempt: int = 0,
        extra: Optional[Dict[str, Any]] = None) -> None:
    """配合 begin()：用同一 execution_id 写一条终态记录（含 duration）。"""
    if not isinstance(handle, dict):
        return
    now = time.time()
    record(
        goal_id=handle.get("goal_id"),
        task_id=handle.get("task_id"),
        step_id=handle.get("step_id"),
        tool_name=handle.get("tool_name", ""),
        args=handle.get("args"),
        start_time=handle.get("start_time", now),
        end_time=now,
        status=status,
        error=error,
        recovery_action=recovery_action,
        execution_id=handle.get("execution_id"),
        attempt=attempt,
        extra=extra,
    )


def recent(limit: int = 50) -> list:
    """读取最近的 trace 记录（供报告/测试断言）。失败返回 []。"""
    try:
        files = sorted(
            (f for f in os.listdir(_TRACE_DIR) if f.startswith("trace_") and f.endswith(".jsonl")),
            reverse=True,
        )
        out = []
        for fn in files:
            with open(os.path.join(_TRACE_DIR, fn), encoding="utf-8") as f:
                lines = f.readlines()
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
                if len(out) >= limit:
                    return out
        return out
    except Exception:
        return []


def clear() -> None:
    """测试辅助：清空 trace 目录（仅测试用，生产不调用）。"""
    try:
        for fn in os.listdir(_TRACE_DIR):
            if fn.startswith("trace_") and fn.endswith(".jsonl"):
                os.remove(os.path.join(_TRACE_DIR, fn))
    except Exception:
        pass
