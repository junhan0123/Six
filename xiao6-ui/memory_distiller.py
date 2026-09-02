#!/usr/bin/env python3
"""小6 · 长期记忆蒸馏器（Phase 12 · P12-1）

目标：定期从对话中提取结构化长期记忆，写入 memories 表，更新用户模型。
提取类型（spec 定义）：
  - habit           用户习惯（如「每天早上查天气」）
  - preference      用户偏好（如「不喜欢甜食」）
  - important_event 重要事件（如「生日 3月15日」）
  - relationship    人际关系（如「母亲姓李」）

设计要点：
  - distill(session_id, messages) -> list[dict]，纯函数式入口，绝不抛错；
  - 启发式提取为优先路径（离线、零成本、确定性，保证单测与无网环境可用）；
  - LLM 蒸馏为增强路径：仅当消息数 >= 2（真实多轮对话）时尝试，失败静默降级；
  - 去重（同 type+content 不重复）+ 置信度评分；
  - 持久化到既有 memories 表（event_type=type），best-effort；
  - important_event 命中日期时，顺便 upsert 到 important_dates 表，打通 P12-3 情感联结。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

VALID_TYPES = ("habit", "preference", "important_event", "relationship")

# ---- 启发式规则（离线、确定、零成本）---------------------------------------

_RELATIONSHIP = re.compile(
    r"(母亲|妈妈|父亲|爸爸|老婆|老公|妻子|丈夫|儿子|女儿|弟弟|妹妹|哥哥|姐姐|"
    r"兄弟|姐妹|朋友|同事|老板|领导|爷爷|奶奶|外公|外婆|岳父|岳母)"
)
_EVENT_KEYWORD = re.compile(r"(生日|纪念日|结婚|结婚纪念|考试|面试|毕业|搬家|入职|退休|忌日|产检|预产期)")
_DATE = re.compile(r"(\d{4}[-年/]\d{1,2}[-月/]\d{1,2}|\d{1,2}月\d{1,2}日?)")
_HABIT = re.compile(
    r"(每天|天天|经常|每日|习惯|定时|每周|周末|工作日|早上|晚上|起床|提醒我|"
    r"睡前|饭后|锻炼|运动|喝水|吃药|查天气|看新闻|通勤|复盘)"
)
_PREFERENCE = re.compile(
    r"(不喜欢|不爱|不吃|不喝|不想要|不要喝|讨厌|反感|偏好|喜欢|爱|更爱|"
    r"更愿意|想.*?一点|口味|偏甜|偏咸|偏辣|忌口|过敏)"
)


def _detect_type(text: str) -> str | None:
    """单条文本的类型判定（优先级：事件 > 关系 > 习惯 > 偏好）。"""
    if _EVENT_KEYWORD.search(text) and _DATE.search(text):
        return "important_event"
    if _RELATIONSHIP.search(text):
        return "relationship"
    if _HABIT.search(text):
        return "habit"
    if _PREFERENCE.search(text):
        return "preference"
    return None


def _heuristic(messages: list) -> list[dict]:
    out: list[dict] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        c = (m.get("content") or "").strip()
        if not c:
            continue
        t = _detect_type(c)
        if t:
            out.append({
                "type": t,
                "content": c,
                "confidence": 0.7,
                "source": "heuristic",
            })
    return out


# ---- LLM 增强（仅多轮真实对话尝试，失败静默降级）---------------------------

def _parse_llm(text: str) -> list[dict]:
    """把 LLM 返回的多行 `type|content` 解析为记忆列表。"""
    out: list[dict] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        t, content = line.split("|", 1)
        t, content = t.strip().lower(), content.strip()
        if t not in VALID_TYPES or not content:
            continue
        out.append({
            "type": t,
            "content": content,
            "confidence": 0.85,
            "source": "llm",
        })
    return out


def _llm_extract(messages: list) -> list[dict]:
    from llm import agnes_completion

    convo = "\n".join(
        f"{( '用户' if (m.get('role')=='user') else '小6' )}：{(m.get('content') or '').strip()}"
        for m in messages if isinstance(m, dict)
    )
    prompt = (
        "从以下对话中提取可长期记住的用户事实，每行一条，格式严格为：\n"
        "类型|内容\n"
        "类型取值：habit(习惯) / preference(偏好) / important_event(重要事件,含日期) / relationship(人际关系)。\n"
        "只输出这些行，不要解释、不要编号。没有值得记的则输出空。\n\n对话：\n" + convo
    )
    with agnes_completion([{"role": "user", "content": prompt}], tools=[], stream=False, timeout=60) as resp:
        import json as _json
        d = _json.loads(resp.read().decode("utf-8"))
    return _parse_llm(d["choices"][0]["message"]["content"].strip())


# ---- 去重 + 持久化 ----------------------------------------------------------

def _dedup(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for it in items:
        key = (it.get("type"), (it.get("content") or "").strip())
        if not key[1] or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _persist(items: list[dict], session_id: str) -> None:
    """写入 memories 表（best-effort）；important_event 带日期时顺带 upsert important_dates。"""
    if not items:
        return
    try:
        import memory

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for it in items:
            content = (it.get("content") or "").strip()
            if not content:
                continue
            # P4.2 修正：经 Canonical Memory API 写入，confidence/source 落真实列（不再塞 tags）
            memory.create_memory(
                content,
                event_type=it.get("type"),
                title=it.get("type"),
                confidence=it.get("confidence", 0.7),
                source=it.get("source", "heuristic"),
                tags={"session_id": session_id, "type": it.get("type")},
            )
            # important_event 命中日期 → 打通 P12-3 重要日期提醒
            if it.get("type") == "important_event":
                from db import db_conn

                conn = db_conn()
                try:
                    _maybe_upsert_date(conn, content, now)
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
    except Exception:
        pass


_DATE_ONLY = re.compile(r"(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})")


def _maybe_upsert_date(conn, content: str, now: str) -> None:
    try:
        m = _DATE_ONLY.search(content)
        if not m:
            return
        y, mo, da = m.group(1), int(m.group(2)), int(m.group(3))
        date_str = f"{y}-{mo:02d}-{da:02d}"
        dtype = "birthday" if "生日" in content else "event"
        desc = content[:60]
        # 避免重复：同 date+type 已存在则跳过
        row = conn.execute(
            "SELECT id FROM important_dates WHERE date=? AND type=?", (date_str, dtype)
        ).fetchone()
        if row:
            return
        conn.execute(
            "INSERT INTO important_dates(date, type, description, reminder_days, created) "
            "VALUES(?,?,?,?,?)",
            (date_str, dtype, desc, 3, now),
        )
    except Exception:
        pass


# ---- 公开入口 ---------------------------------------------------------------

def distill(session_id: str, messages: list, use_llm: bool | None = None) -> list[dict]:
    """从一段对话中提取结构化长期记忆。

    Args:
        session_id: 会话标识（仅作元数据）。
        messages:   [{"role": "user"/"assistant", "content": "..."}, ...]
        use_llm:    None=自动（消息数>=2 时尝试 LLM）；True/False 强制。
    Returns:
        记忆字典列表，每项含 type/content/confidence/source。永不抛错。
    """
    try:
        out = _heuristic(messages)
        if use_llm is None:
            use_llm = len(messages or []) >= 2
        if use_llm:
            try:
                out.extend(_llm_extract(messages))
            except Exception:
                pass
        out = _dedup(out)
        _persist(out, session_id)
        return out
    except Exception:
        return []
