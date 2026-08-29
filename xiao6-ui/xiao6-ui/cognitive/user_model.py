#!/usr/bin/env python3
"""庄周 · 认知层 · 用户模型（User Model）—— Phase 20.5 Bootstrap + 可信治理

结构化、本地优先、带来源(source)与置信度(confidence)的长期用户认知。
- 既支持 LLM 自动演化（upsert_user_model），也支持**可信引导播种**（bootstrap_user_model）；
- 每条事实带 source/confidence（L1 用户确认 1.0 > L2 项目状态 0.9 > L3 行为统计 0.6–0.8 > L4 推断 ≤0.5）；
- **合并铁律**：低可信不得覆盖高可信（防旧错误项目污染当前认知）。
- 单行 JSON 存于 user_model 表，读取 O(1)。仅依赖 db / config，不依赖 context（单向依赖）。
"""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime

from db import db_conn

# ── 来源可信度等级（L1–L4）──
SRC_USER_CONFIRMED = "user_confirmed"   # L1 用户明确声明
SRC_PROJECT_STATE = "project_state"     # L2 项目真实状态（Git/工作区）
SRC_CONVERSATION = "conversation"       # L3 长期对话沉淀
SRC_INFERENCE = "inference"             # L4 模型推断

CONF_BY_SOURCE = {
    SRC_USER_CONFIRMED: 1.0,
    SRC_PROJECT_STATE: 0.9,
    SRC_CONVERSATION: 0.7,
    SRC_INFERENCE: 0.4,
}

# 新（不同名）项目纳入用户模型核心列表的最低可信门槛：L4 推断(≤0.5)不得
# 作为核心项目污染认知；仅高可信来源(user_confirmed/project_state)或 conf>0.5 才准入。
MIN_NEW_PROJECT_CONF = 0.5
_TRUSTED_HIGH_SRC = (SRC_USER_CONFIRMED, SRC_PROJECT_STATE)


DEFAULT_MODEL = {
    "identity": {"name": "", "role": "", "org": ""},
    # 项目列表（带可信治理）；与旧 recurring_projects 并存以兼容历史写入
    "projects": [],
    "preferences": {},
    "working_style": {},
    "interaction_pattern": {},
    "expertise": [],
    "communication_style": {"verbosity": "", "formality": "", "humor": ""},
    "recurring_projects": [],
    "values": [],
    "feedback": [],
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conf_of(source: str) -> float:
    return CONF_BY_SOURCE.get(source, CONF_BY_SOURCE[SRC_INFERENCE])


def load_user_model() -> dict:
    """读取用户模型；空返回默认骨架（并 best-effort 引导播种以打破死锁）。"""
    conn = db_conn()
    try:
        row = conn.execute("SELECT data, confidence, updated FROM user_model WHERE id=1").fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        merged = copy.deepcopy(DEFAULT_MODEL)
        # 死锁修复：表空时 best-effort 播种可靠信号（失败静默，不阻塞读取）
        try:
            if is_empty(merged):
                seeded = bootstrap_user_model()
                if seeded:
                    return seeded
        except Exception:
            pass
        return merged
    try:
        data = json.loads(row[0])
    except Exception:
        return copy.deepcopy(DEFAULT_MODEL)
    merged = copy.deepcopy(DEFAULT_MODEL)
    if isinstance(data, dict):
        for k, v in data.items():
            merged[k] = v
    return merged


def _dedupe(arr):
    seen = set()
    out = []
    for x in arr or []:
        if isinstance(x, (str, int, float, bool)):
            key = str(x)
        else:
            key = json.dumps(x, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def merge_project(existing: list, incoming: dict) -> list:
    """合并一个项目事实，遵守「低可信不得覆盖高可信」铁律。

    incoming: {"name","source","confidence"?,"updated"?}
    若同名项目已存在且置信度更高 → 保留旧值（仅补充 updated）；否则写入/更新。
    """
    name = (incoming.get("name") or "").strip()
    if not name:
        return existing
    inc_conf = float(incoming.get("confidence") or _conf_of(incoming.get("source", "")))
    incoming_src = incoming.get("source", SRC_INFERENCE)
    # 防污染铁律（跨名）：新项目名若为低可信推断且未达门槛，直接丢弃，不写入核心列表。
    # 这避免旧错误/猜测项目与已建立的高可信项目并列污染用户认知。
    if inc_conf <= MIN_NEW_PROJECT_CONF and incoming_src not in _TRUSTED_HIGH_SRC:
        return existing
    for p in existing:
        if isinstance(p, dict) and (p.get("name") or "").strip() == name:
            old_conf = float(p.get("confidence") or _conf_of(p.get("source", "")))
            if inc_conf <= old_conf:
                # 低可信/等可信：不覆盖高可信；仅当旧值无来源时补充
                if not p.get("source") and incoming.get("source"):
                    p["source"] = incoming["source"]
                    p["confidence"] = inc_conf
                    p["updated"] = incoming.get("updated", _now())
                return existing
            # 高可信覆盖低可信：更新
            p["source"] = incoming.get("source", p.get("source"))
            p["confidence"] = inc_conf
            p["updated"] = incoming.get("updated", _now())
            return existing
    existing.append({
        "name": name,
        "source": incoming.get("source", SRC_INFERENCE),
        "confidence": inc_conf,
        "updated": incoming.get("updated", _now()),
    })
    return existing


def upsert_user_model(delta: dict, bump_confidence: bool = True) -> dict:
    """浅合并 + 数组去重后写回；projects 走可信合并；同步 updated / confidence。"""
    cur = load_user_model()
    if isinstance(delta, dict):
        for k, v in delta.items():
            if k == "projects" and isinstance(v, list):
                proj = list(cur.get("projects") or [])
                for inc in v:
                    if isinstance(inc, dict):
                        proj = merge_project(proj, inc)
                cur["projects"] = proj
            elif isinstance(v, list):
                base = cur.get(k, [])
                if not isinstance(base, list):
                    base = [base]
                cur[k] = _dedupe(base + v)
            elif isinstance(v, dict):
                base = cur.get(k, {})
                if not isinstance(base, dict):
                    base = {}
                base.update(v)
                cur[k] = base
            else:
                cur[k] = v
    # P5.2 · Canonical Memory Integration：写入不再由本模块直连 DB，统一经
    # cognitive.memory_adapter → memory.py Canonical Memory API（唯一写入权威），
    # user_model 表退化为 adapter 维护的兼容投影（O(1) 读模型）。
    from cognitive.memory_adapter import record_user_model

    record_user_model(
        cur,
        content=render_user_model_block(cur),
        confidence=None,
        bump_confidence=bump_confidence,
        updated=_now(),
    )
    return cur


def _detect_project_from_repo() -> str | None:
    """从仓库目录名推导项目（L2 项目真实状态，零外部调用、零伪造）。

    例：DB 父目录 'xiao6-ui' → 'Xiao6'。
    """
    try:
        db_path = None
        try:
            import config
            db_path = getattr(config, "DB_PATH", None)
        except Exception:
            db_path = None
        if not db_path:
            db_path = os.path.join(os.getcwd(), "xiao6.db")
        repo_dir = os.path.basename(os.path.dirname(os.path.abspath(db_path)))
        name = repo_dir.lower()
        for suf in ("-ui", "-app", "-web", ".ui", ".app"):
            if name.endswith(suf):
                name = name[: -len(suf)]
                break
        name = name.strip()
        if not name:
            return None
        # 驼峰/连字符转可读：首字母大写
        parts = name.replace("_", " ").replace("-", " ").split()
        proj = "".join(p[:1].upper() + p[1:] for p in parts) if parts else None
        # 对外展示名统一：仓库 Xiao6 → Six
        if proj and proj.lower() == "xiao6":
            proj = "Six"
        return proj
    except Exception:
        return None


def bootstrap_user_model(force: bool = False) -> dict | None:
    """可信引导播种：仅从可靠信号（项目真实状态）填充，不覆盖已有高可信事实。

    返回播种后的模型；若无可靠信号可播种返回 None。幂等（重复调用安全）。
    """
    cur = load_user_model()
    # 已有 L2+ 项目则不重复播种项目（避免抖动）
    has_strong = any(
        float(p.get("confidence", 0) or 0) >= 0.9
        for p in (cur.get("projects") or []) if isinstance(p, dict)
    )
    changed = False
    if not has_strong:
        proj = _detect_project_from_repo()
        if proj:
            before = list(cur.get("projects") or [])
            cur["projects"] = merge_project(before, {
                "name": proj, "source": SRC_PROJECT_STATE, "confidence": 0.9,
            })
            changed = True
    # 默认身份（低可信补充，不覆盖用户已有声明）
    idn = cur.get("identity") or {}
    if isinstance(idn, dict):
        if not idn.get("name"):
            idn["name"] = "小6"
            changed = True
        if not idn.get("role"):
            idn["role"] = "owner"
            changed = True
    if changed or force:
        upsert_user_model(cur, bump_confidence=False)
    return cur if changed else (cur if not is_empty(cur) else None)


def canonical_project() -> tuple[str | None, float]:
    """返回当前最可信项目名与置信度（供 Context / profile 交叉校验）。

    P5.2 §12：纯选择逻辑已下沉到 Memory 层中性 helper
    `memory_projection.select_canonical_project`（零重复实现）；本函数保留
    cognitive 侧语义（经 load_user_model，含空表引导播种），供既有调用方沿用。
    """
    from memory_projection import select_canonical_project

    return select_canonical_project(load_user_model())


def render_user_model_block(data: dict) -> str:
    """渲染紧凑【用户模型】文本（含可信度标注），硬上限约 400 token。"""
    parts = []
    idn = data.get("identity") or {}
    if isinstance(idn, dict):
        bits = [str(idn.get("name", "")), str(idn.get("role", "")), str(idn.get("org", ""))]
        bits = [b for b in bits if b]
        if bits:
            parts.append("身份：" + " / ".join(bits))
    # 项目（可信治理）：展示名称 + 来源 + 置信度
    projs = data.get("projects") or []
    if projs:
        items = []
        for p in projs[:10]:
            if isinstance(p, dict):
                nm = p.get("name", "")
                src = p.get("source", "")
                cf = float(p.get("confidence", 0) or 0)
                tag = "可信%.1f" % cf if cf >= 0.7 else ("推断%.1f" % cf)
                items.append("%s（%s,%s）" % (nm, src, tag))
            elif isinstance(p, str):
                items.append(p)
        if items:
            parts.append("长期项目：" + "、".join(items))
    exp = data.get("expertise") or []
    if exp:
        parts.append("专长：" + "、".join(str(x) for x in exp[:12]))
    cs = data.get("communication_style") or {}
    if isinstance(cs, dict):
        bits = [str(cs.get("verbosity", "")), str(cs.get("formality", "")), str(cs.get("humor", ""))]
        bits = [b for b in bits if b]
        if bits:
            parts.append("沟通风格：" + " / ".join(bits))
    prefs = data.get("preferences") or {}
    if isinstance(prefs, dict) and prefs:
        lines = []
        for k, v in list(prefs.items())[:6]:
            lines.append("%s=%s" % (k, ",".join(map(str, v)) if isinstance(v, list) else v))
        if lines:
            parts.append("偏好：" + "；".join(lines))
    ws = data.get("working_style") or {}
    if isinstance(ws, dict) and ws:
        lines = ["%s=%s" % (k, ",".join(map(str, v)) if isinstance(v, list) else v)
                 for k, v in list(ws.items())[:6]]
        if lines:
            parts.append("工作风格：" + "；".join(lines))
    ip = data.get("interaction_pattern") or {}
    if isinstance(ip, dict) and ip:
        lines = ["%s=%s" % (k, ",".join(map(str, v)) if isinstance(v, list) else v)
                 for k, v in list(ip.items())[:6]]
        if lines:
            parts.append("交互模式：" + "；".join(lines))
    rp = data.get("recurring_projects") or []
    if rp and not projs:
        parts.append("长期项目：" + "、".join(str(x) for x in rp[:10]))
    vals = data.get("values") or []
    if vals:
        parts.append("价值观：" + "、".join(str(x) for x in vals[:10]))
    fb = data.get("feedback") or []
    if fb:
        parts.append("被纠正/偏好反馈：" + "；".join(str(x) for x in fb[:12]))
    if not parts:
        return ""
    return "【用户模型】\n" + "\n".join(parts)


def _is_blank(v) -> bool:
    """递归判断值是否为「空」（空字符串/None/空容器/全空嵌套容器）。"""
    if v is None or v == "":
        return True
    if isinstance(v, (list, tuple, set)):
        return all(_is_blank(x) for x in v)
    if isinstance(v, dict):
        return all(_is_blank(x) for x in v.values())
    return False


def is_empty(data: dict) -> bool:
    """判断用户模型是否仍是空骨架（无有效信息，含全空嵌套结构）。"""
    return all(_is_blank(v) for v in data.values())
