#!/usr/bin/env python3
"""庄周 · Phase 9 主动智能配置 + 通知策略（NotificationPolicy）

B1/B2 单一配置与通知裁决中心。
- 纯标准库，无新依赖。
- 不创建第二 Runtime / Memory / EventBus / State：只读 os.environ（由 config.load_env 播种）+ 经 db.meta 持久化 DND 开关。
- NotificationPolicy：DND / quiet hours / importance 裁决；普通遵守 DND，Critical 突破。
- ProactiveConfig 函数：能力开关 / 建议模式 / 允许时段 / 允许主动类型 / 静默时间（全部从 os.environ 实时读取，零缓存状态）。

设计纪律（Phase 9 红线）：
- 引擎只决策、不执行；执行一律经 Goal System → Agent Runtime → Policy Guard。
- 通知裁决集中在本模块，前端 companion 仅展示，不再各自实现 DND 逻辑（避免双来源）。
"""

from __future__ import annotations

import os
from datetime import datetime

# ── 能力开关 ────────────────────────────────────────────────────────────────
# 引擎总开关：false 时仅放行 critical（系统级），其余交回既有规则通知（B2 退化路径）。
def feature_proactive_engine() -> bool:
    return os.environ.get("FEATURE_PROACTIVE_ENGINE", "true").lower() in ("1", "true", "yes")

# ── 建议模式 ────────────────────────────────────────────────────────────────
# auto = 引擎可自动建 Goal（CREATE_GOAL）；
# ask  = 引擎只建议（SUGGEST/NOTIFY），等用户确认；
# off  = 引擎不决策，交回既有规则通知（IGNORE）。
def suggestion_mode() -> str:
    return os.environ.get("PROACTIVE_SUGGESTION_MODE", "ask").lower()

# ── 允许主动时段（非 quiet）──
def proactive_window() -> tuple[int, int]:
    start = int(os.environ.get("PROACTIVE_WINDOW_START", "8"))
    end = int(os.environ.get("PROACTIVE_WINDOW_END", "22"))
    return start, end

# ── 静默时间（DND 加强：此区间内仅 critical 突破）──
def proactive_quiet() -> tuple[int, int]:
    start = int(os.environ.get("PROACTIVE_QUIET_START", "23"))
    end = int(os.environ.get("PROACTIVE_QUIET_END", "7"))
    return start, end

# ── 允许的主动类型白名单（kind）──
def allowed_types() -> set[str]:
    raw = os.environ.get(
        "PROACTIVE_ALLOWED_TYPES",
        "reminder,goal,hotspot,weather,alert,review,rule,rule_panel,anomaly,error,long_running,system,completed",
    )
    return {t.strip().lower() for t in raw.split(",") if t.strip()}

# ── 重要度等级 ──────────────────────────────────────────────────────────────
# low(0) < normal(1) < high(2) < critical(3)
IMPORTANCE_LEVELS = {"low": 0, "normal": 1, "high": 2, "critical": 3}


def importance_rank(level: str) -> int:
    return IMPORTANCE_LEVELS.get((level or "normal").lower(), 1)


# kind → 默认重要度映射（proactive.py 各 push_proactive 可选覆盖）
_KIND_IMPORTANCE = {
    "reminder": "normal",
    "goal": "normal",
    "hotspot": "low",
    "weather": "low",
    "alert": "high",
    "review": "normal",
    "rule": "normal",
    "rule_panel": "normal",
    "anomaly": "high",
    "error": "high",
    "long_running": "high",
    "system": "high",
    "completed": "normal",
}


def kind_importance(kind: str) -> str:
    return _KIND_IMPORTANCE.get((kind or "").lower(), "normal")


# 停滞阈值（天）——与 proactive.collect_today_suggestions / _check_goal_stalled 对齐
def stall_days() -> int:
    try:
        return int(os.environ.get("PROACTIVE_STALL_DAYS", "5"))
    except Exception:
        return 5


def long_running_minutes() -> int:
    """单目标/任务最长运行阈值（分钟），超时触发 LONG_RUNNING 看门狗。"""
    try:
        return int(os.environ.get("PROACTIVE_LONG_RUNNING_MIN", "30"))
    except Exception:
        return 30


class NotificationPolicy:
    """后端化通知裁决：DND / quiet hours / importance / 类型白名单。

    纪律：
    - 普通消息遵守 DND 与 quiet hours；critical 永远突破。
    - 不持有任何持久状态（除经 db.meta 的 DND 开关），不构成第二 Runtime/State。
    - should_deliver 接受 now 参数，便于确定性测试（不依赖真实时钟）。
    """

    META_KEY = "proactive_dnd"

    # ── DND 开关（经 db.meta 持久化，单一来源）──
    @staticmethod
    def is_dnd_enabled() -> bool:
        try:
            from db import db_conn

            conn = db_conn()
            row = conn.execute(
                "SELECT value FROM meta WHERE key=?", (NotificationPolicy.META_KEY,)
            ).fetchone()
            conn.close()
            return bool(row and str(row[0]).lower() in ("1", "true", "yes"))
        except Exception:
            return False

    @staticmethod
    def set_dnd(enabled: bool) -> None:
        try:
            from db import db_conn

            conn = db_conn()
            conn.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (NotificationPolicy.META_KEY, "1" if enabled else "0"),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    # ── 时段工具 ──
    @staticmethod
    def _in_window(hour: int, start: int, end: int) -> bool:
        if start <= end:
            return start <= hour < end
        # 跨午夜窗口（如 23→7）
        return hour >= start or hour < end

    # ── 核心裁决 ──
    @classmethod
    def should_deliver(cls, kind: str, importance: str = None, *, now: datetime = None) -> bool:
        """裁决一条主动消息是否投递。

        返回 True=投递；False=抑制。
        规则优先级：
          1. critical → 永远投递（突破 DND / quiet）。
          2. 引擎关闭 → 仅放行 critical（其余交回既有规则，由调用方决定）。
          3. DND 开启 → 抑制非 critical。
          4. quiet hours → 抑制 high 以下。
          5. 允许时段外（非 quiet）→ 仅 high+ 投递。
          6. 类型白名单 → 不在名单内抑制。
        """
        importance = importance or kind_importance(kind)
        rank = importance_rank(importance)

        now = now or datetime.now()
        hour = now.hour

        # 1) critical 永远突破
        if rank >= importance_rank("critical"):
            return True

        # 2) 引擎关闭：仅 critical 放行（其余交回既有规则）
        if not feature_proactive_engine():
            return False

        # 3) DND：抑制非 critical
        if cls.is_dnd_enabled() and rank < importance_rank("critical"):
            return False

        # 4) quiet hours：high 以下抑制
        qs, qe = proactive_quiet()
        if cls._in_window(hour, qs, qe) and rank < importance_rank("high"):
            return False

        # 5) 允许时段外（非 quiet）：仅 high+ 投递
        ws, we = proactive_window()
        if not cls._in_window(hour, ws, we) and rank < importance_rank("high"):
            return False

        # 6) 类型白名单
        if kind and kind.lower() not in allowed_types():
            return False

        return True


# 模块级单例（无状态，仅方法；不构成第二 Runtime/State）
policy = NotificationPolicy()


def reload() -> None:
    """占位：本模块全部从 os.environ 实时读取，无需缓存刷新。

    保留签名以与 config.reload() 调用惯例对齐（server.py 重载配置时一并调用，幂等）。
    """
    return
