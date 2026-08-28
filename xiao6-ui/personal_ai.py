#!/usr/bin/env python3
"""庄周 · Personal AI Deepening（Phase 37.2 · Personalization Layer）

统一「让庄周更懂我」的个性化学习层。严格增量、零侵入：
- 零改 Memory V2 核心 schema / memory_distiller / memory_intelligence 写路径；
- 零改 Agent Runtime / Planner / Executor / EventBus / Tool Registry；
- 确认/纠正/忽略 走 **append-only notes 账本**（folder="记忆确认"），绝不写 memories.status；
- CONFIRMED 必须有真实用户来源（profile / user_model L1 / learnings 显式 / 账本显式动作）；
- 绝不让 AI 把 inference 自动标成 confirmed（红线）；
- 结构化蒸馏进 user_model 仅来自 CONFIRMED 来源，绝不来自原始 inference 记忆；
- 双源（user_model vs personal_context）按 SOURCE PRIORITY 解析，保证单一一致输出；
- personalization 合并为统一 Personal Context，短/稳定/可控/可解释，服从 token budget。

全部函数 best-effort、异常隔离，任何失败返回安全默认值，绝不阻塞对话主链路。
"""

from __future__ import annotations

import json
from datetime import datetime

__all__ = [
    "CONFIRM_FOLDER", "SOURCE_PRIORITY",
    "record_confirmation", "confirm_memory", "correct_memory", "ignore_memory",
    "get_confirmation_ledger", "get_memory_projection",
    "distill_user_model_proposal", "apply_user_model_distillation",
    "resolve_identity", "build_unified_personal_context",
    "sync_corrections_to_user_model", "get_personal_ai_view",
]

# ── 常量 ─────────────────────────────────────────────────────────────────────

# 确认账本（append-only）：记录用户对某条记忆的 confirm/correct/ignore 动作。
CONFIRM_FOLDER = "记忆确认"

# 来源优先级（六层）：数值越大越可信。
# 用户明确 > 用户纠正 > confirmed memory/feedback > user_model distilled >
# personal_context inference > 会话推断
SOURCE_PRIORITY = {
    "user_explicit": 100,    # 用户用 profile_set / 显式声明
    "user_correction": 90,   # 用户纠正（别再/不要再/改掉）
    "confirmed_memory": 80,  # 账本 confirm / learnings 显式反馈
    "user_model_distilled": 60,  # user_model 结构化蒸馏（已确认来源）
    "personal_context_inference": 40,  # os_bridge 实时推断
    "session_inference": 20,  # 当轮会话推断
}

# 标记：🟢用户确认 / 🟡AI推断 / ⚪系统事实（诚实区分推断与事实）
MARK_CONFIRMED = "🟢"
MARK_INFERENCE = "🟡"
MARK_SYSTEM = "⚪"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_user_model() -> dict:
    try:
        from cognitive.user_model import load_user_model
        return load_user_model()
    except Exception:
        return {}


def _load_profile() -> list:
    """读取 profile 表（用户显式确认的长期事实，key-value）。"""
    try:
        from db import db_conn
        conn = db_conn()
        rows = conn.execute("SELECT key,value FROM profile ORDER BY key").fetchall()
        conn.close()
        return [(r[0], r[1]) for r in rows]
    except Exception:
        return []


# ── Task 1：Memory Confirmation Loop（append-only 账本）──────────────────────

def record_confirmation(memory_id, action: str, text: str = "", source: str = "user") -> int:
    """追加一条确认账本（append-only note）。action ∈ confirm|correct|ignore。

    设计要点：
    - 只读 memories 表用于关联，绝不写 memories.status / source / confidence；
    - 账本 = notes 表 folder="记忆确认"，结构化 markdown 含 memory_id/action/source/timestamp/text；
    - 返回新建 note 的 id（失败返回 0）。
    """
    from notes import create_note

    action = action if action in ("confirm", "correct", "ignore") else "ignore"
    try:
        mid = int(memory_id)
    except (TypeError, ValueError):
        mid = 0
    md = (
        "# 记忆确认账本\n\n"
        f"- memory_id: {mid}\n"
        f"- action: {action}\n"
        f"- source: {source}\n"
        f"- timestamp: {_now()}\n"
        f"- text: {(text or '').strip()}\n"
    )
    title = "记忆确认#%d:%s" % (mid, action)
    try:
        return create_note(title=title, markdown=md, tags="记忆确认", folder=CONFIRM_FOLDER)
    except Exception as e:
        print(f"[personal_ai] record_confirmation 忽略: {e}")
        return 0


def confirm_memory(memory_id, note: str = "") -> int:
    """用户确认某条记忆为真实事实（CONFIRMED）。仅记录账本，不改 memories。"""
    return record_confirmation(
        memory_id, "confirm",
        note or "用户确认该记忆为真实事实", "user",
    )


def correct_memory(memory_id, correction: str, note: str = "") -> int:
    """用户纠正某条记忆。写账本（correct）+ 同步进 learnings(correction) + user_model.feedback。

    让纠正真实影响行为（Task 5 纠正闭环），且全程 append-only、可追踪、可回放。
    绝不自动改写 memories 原文，绝不自动替用户确认。
    """
    rid = record_confirmation(memory_id, "correct", (correction or note), "user")
    corr = (correction or "").strip()
    # 同步进自我学习经验（Phase 36.2 已有 record_learning；显式纠正同落库，权重更高）
    if corr:
        try:
            from memory import record_learning
            record_learning(corr, "correction")
        except Exception:
            pass
        # 同步进 user_model.feedback（append-only，不覆盖已有）
        try:
            from cognitive.user_model import upsert_user_model
            um = _load_user_model()
            fb = list(um.get("feedback") or [])
            entry = "纠正：" + corr
            if entry not in fb:
                fb.append(entry)
                upsert_user_model({"feedback": fb}, bump_confidence=False)
        except Exception:
            pass
    return rid


def ignore_memory(memory_id, note: str = "") -> int:
    """用户忽略某条记忆（暂不处理，留作推断）。仅记录账本。"""
    return record_confirmation(
        memory_id, "ignore",
        note or "用户忽略（暂不处理，保留为推断）", "user",
    )


def get_confirmation_ledger() -> list:
    """读取确认账本（notes folder=记忆确认），解析为结构化列表。"""
    try:
        from notes import get_notes
        rows = get_notes(folder=CONFIRM_FOLDER, limit=500)
    except Exception:
        return []
    out = []
    for r in rows or []:
        md = r.get("markdown") or ""
        rec = {
            "id": r.get("id"), "ts": r.get("ts"), "memory_id": 0,
            "action": "ignore", "source": "user", "text": "",
        }
        for line in md.splitlines():
            line = line.strip()
            if line.startswith("- memory_id:"):
                try:
                    rec["memory_id"] = int(line.split(":", 1)[1].strip())
                except Exception:
                    pass
            elif line.startswith("- action:"):
                rec["action"] = line.split(":", 1)[1].strip()
            elif line.startswith("- source:"):
                rec["source"] = line.split(":", 1)[1].strip()
            elif line.startswith("- text:"):
                rec["text"] = line.split(":", 1)[1].strip()
        out.append(rec)
    return out


# ── Task 1：记忆投影（标注 INFERENCE / CONFIRMED / SYSTEM）────────────────────

def _is_system_fact(event_type: str, body: str) -> bool:
    """系统级事实（硬编码/真相层，非推断）。仅 tags/source 明确标记为 SYSTEM 才算。"""
    et = (event_type or "").lower()
    if et in ("system", "identity"):
        return True
    b = (body or "").upper()
    return "SYSTEM" in b


def get_memory_projection(limit: int = 200) -> list:
    """读取 memories，叠加确认账本 / profile / learnings，标注每条记忆的可信层级。

    返回：[{id,type,content,label,confidence,source,status}]
    label ∈ INFERENCE | CONFIRMED | CORRECTED | SYSTEM
    注：全部来自只读聚合，绝不修改 memories 表。
    """
    try:
        from db import db_conn
        conn = db_conn()
        rows = conn.execute(
            "SELECT id,event_type,content,title,confidence,source,status,tags "
            "FROM memories WHERE archived=0 ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[personal_ai] get_memory_projection 忽略: {e}")
        return []

    ledger = get_confirmation_ledger()
    confirmed_ids = {r["memory_id"] for r in ledger if r["action"] == "confirm"}
    corrected_ids = {r["memory_id"] for r in ledger if r["action"] == "correct"}

    out = []
    for r in rows:
        mid, et, content, title, conf, src, status, tags = r
        body = (content or title or "").strip()
        if mid in confirmed_ids:
            label = "CONFIRMED"
        elif mid in corrected_ids:
            label = "CORRECTED"
        elif _is_system_fact(et, body):
            label = "SYSTEM"
        else:
            label = "INFERENCE"
        out.append({
            "id": mid,
            "type": et,
            "content": body[:140],
            "label": label,
            "confidence": round(float(conf or 0.5), 3),
            "source": src or "inference",
            "status": status or "active",
        })
    return out


# ── Task 2：User Model Distillation（只读提案 + 显式应用）──────────────────────

def distill_user_model_proposal() -> dict:
    """只读蒸馏：从 CONFIRMED 来源（profile / learnings correction|feedback / 账本 confirm）
    提出 user_model 结构化增量建议。绝不自动写入。

    返回：{preferences, working_style, communication_style, expertise, values, feedback}
    每条均带 source/confidence，便于审计与显式应用。
    """
    prop = {
        "preferences": {}, "working_style": {}, "communication_style": {},
        "expertise": [], "values": [], "feedback": [],
    }
    prof = _load_profile()
    for k, v in prof:
        kl = (k or "").lower()
        if any(w in kl for w in ("偏好", "喜欢", "风格", "pref", "style")):
            prop["preferences"][k] = {"value": v, "source": "user_explicit", "confidence": 1.0}
        elif any(w in kl for w in ("习惯", "工作", "work", "habit")):
            prop["working_style"][k] = {"value": v, "source": "user_explicit", "confidence": 1.0}
        elif any(w in kl for w in ("称呼", "称", "call")):
            prop["communication_style"]["称呼"] = {"value": v, "source": "user_explicit", "confidence": 1.0}
        elif any(w in kl for w in ("领域", "专业", "擅长", "expert", "domain")):
            prop["expertise"].append({"value": f"{k}:{v}", "source": "user_explicit", "confidence": 1.0})
        elif any(w in kl for w in ("价值观", "原则", "value", "principle")):
            prop["values"].append({"value": f"{k}:{v}", "source": "user_explicit", "confidence": 1.0})

    # learnings：correction → feedback；feedback → preferences
    try:
        from memory import get_learnings
        for it in get_learnings(limit=50):
            if it["type"] == "correction":
                prop["feedback"].append({"value": "纠正：" + it["content"], "source": "user_correction", "confidence": 1.0})
            elif it["type"] == "feedback":
                prop["preferences"].setdefault(
                    "用户偏好", {"value": it["content"], "source": "confirmed_memory", "confidence": 0.8}
                )
    except Exception:
        pass
    return prop


def apply_user_model_distillation() -> dict:
    """仅把 CONFIRMED 来源提案写入 user_model（不来自原始 inference 记忆）。

    幂等、增量、append-only 语义（use user_model.upsert 的合并逻辑，不覆盖高可信事实）。
    返回写入后的 user_model。
    """
    prop = distill_user_model_proposal()
    delta = {}
    if prop["preferences"]:
        delta["preferences"] = {k: v["value"] for k, v in prop["preferences"].items()}
    if prop["working_style"]:
        delta["working_style"] = {k: v["value"] for k, v in prop["working_style"].items()}
    if prop["communication_style"]:
        delta["communication_style"] = {k: v["value"] for k, v in prop["communication_style"].items()}
    if prop["expertise"]:
        delta["expertise"] = [v["value"] for v in prop["expertise"]]
    if prop["values"]:
        delta["values"] = [v["value"] for v in prop["values"]]
    if prop["feedback"]:
        delta["feedback"] = [v["value"] for v in prop["feedback"]]
    if not delta:
        return _load_user_model()
    try:
        from cognitive.user_model import upsert_user_model
        return upsert_user_model(delta, bump_confidence=False)
    except Exception as e:
        print(f"[personal_ai] apply_user_model_distillation 忽略: {e}")
        return _load_user_model()


def sync_corrections_to_user_model() -> dict:
    """Task 5：把 learnings 中的显式纠正（type=correction）同步进 user_model.feedback。

    append-only，不覆盖、不去重外的已有项。让纠正真实影响个性化输出。
    """
    try:
        from memory import get_learnings
        from cognitive.user_model import upsert_user_model
        items = get_learnings(limit=50, ltype="correction")
        if not items:
            return _load_user_model()
        um = _load_user_model()
        fb = list(um.get("feedback") or [])
        changed = False
        for it in items:
            entry = "纠正：" + it["content"]
            if entry not in fb:
                fb.append(entry)
                changed = True
        if changed:
            upsert_user_model({"feedback": fb}, bump_confidence=False)
        return um
    except Exception as e:
        print(f"[personal_ai] sync_corrections_to_user_model 忽略: {e}")
        return _load_user_model()


# ── Task 3：双源对齐（SOURCE PRIORITY 解析）──────────────────────────────────

def resolve_identity() -> dict:
    """双源对齐：canonical identity 取 user_model（稳定结构化真相），
    personal_context（os_bridge）作 enrichment。冲突按 SOURCE PRIORITY 解析。

    冲突事实：user_model.identity.role="owner"（bootstrap 默认，低可信推断级）
              vs personal_context.identity.role="老板的个人 AI 副驾"（硬编码推断）。
    解析：user_model 优先级(60) > personal_context inference(40) → canonical 取 user_model；
          personal_context 的 role/偏好/边界 作为 enrichment 保留，不丢失。
    """
    um = _load_user_model()
    idn = um.get("identity") or {}
    name = (idn.get("name") or "").strip() or "庄周"  # 系统事实兜底（AI 名称固定）
    role_um = (idn.get("role") or "").strip()          # "owner"

    pc_role = ""
    pc_prefs = []
    pc_boundaries = []
    try:
        import os_bridge
        pc = os_bridge.personal_context() or {}
        pidn = pc.get("identity") or {}
        pc_role = (pidn.get("role") or "").strip()      # "老板的个人 AI 副驾"
        pc_prefs = pidn.get("prefs") or []
        pc_boundaries = pidn.get("boundaries") or []
    except Exception:
        pass

    role = role_um if role_um else pc_role
    role_source = ("user_model" if role_um else ("personal_context" if pc_role else "system"))
    conflict = bool(role_um and pc_role and role_um != pc_role)
    return {
        "name": name,
        "role": role,
        "role_source": role_source,
        "pc_role": pc_role,
        "pc_prefs": pc_prefs,
        "pc_boundaries": pc_boundaries,
        "conflict": conflict,
        "resolution": (
            "user_model(优先级60) > personal_context_inference(40)；canonical 取 user_model，"
            "personal_context 作 enrichment" if conflict else "无冲突"
        ),
    }


# ── Task 4：Personalization 合并（统一 Personal Context 块）────────────────────

def build_unified_personal_context(max_tokens: int = 700) -> str:
    """合并 confirmed + user_model + personal_context + memory(高价值,capped) + correction，
    产出统一 Personal Context 块。短/稳定/可控/可解释，服从 token budget。

    标记：🟢用户确认 / 🟡AI推断 / ⚪系统事实。诚实：推断≠事实。
    硬约束：绝不把 54 条 inference 记忆全塞进 system prompt（高价值仅取 top-5）。
    """
    idr = resolve_identity()
    parts = ["【个性化 · 统一画像】"]
    parts.append(f"· 身份：{idr['name']}（{idr['role']}）{MARK_SYSTEM}")

    # 已确认事实（profile 表）
    for k, v in _load_profile():
        parts.append(f"· 已确认：{k} = {v} {MARK_CONFIRMED}")

    # user_model 结构化非空字段（蒸馏自确认来源）
    um = _load_user_model()
    for fld in ("preferences", "working_style", "communication_style", "expertise", "values"):
        val = um.get(fld)
        if not val:
            continue
        if isinstance(val, dict):
            for kk, vv in val.items():
                if vv:
                    parts.append(f"· {kk}：{vv} {MARK_CONFIRMED}")
        elif isinstance(val, list):
            for x in val:
                if x:
                    parts.append(f"· {x} {MARK_CONFIRMED}")

    # 纠正（corrections，已确认来源，最高优先级）
    try:
        from memory import get_learnings
        for it in get_learnings(limit=20, ltype="correction"):
            parts.append(f"· 纠正：{it['content']} {MARK_CONFIRMED}")
    except Exception:
        pass

    # 高价值记忆（capped，避免 54 条全塞；低价值推断显式标注待确认）
    proj = get_memory_projection(limit=200)
    inferred = [m for m in proj if m["label"] == "INFERENCE"]
    inferred.sort(key=lambda m: m["confidence"], reverse=True)
    for m in inferred[:5]:
        parts.append(
            f"· 推断：{m['content']} {MARK_INFERENCE}"
            f"（置信 {m['confidence']:.2f}，待你确认）"
        )

    # personal_context enrichment（偏好/边界，推断级）
    for p in idr.get("pc_prefs") or []:
        if p:
            parts.append(f"· 推断偏好：{p} {MARK_INFERENCE}")
    for b in idr.get("pc_boundaries") or []:
        if b:
            parts.append(f"· 边界：{b} {MARK_INFERENCE}")

    block = "\n".join(parts)
    # token budget 裁剪（中文约 2 字符/token 的粗略估计）
    cap = max_tokens * 2
    if len(block) > cap:
        block = block[:cap] + "\n· …（已达 token 上限，低价值项已省略）"
    return block


# ── 聚合视图（供 API / UI 使用）───────────────────────────────────────────────

def get_personal_ai_view() -> dict:
    """聚合视图：供 /api/personal_ai 返回。"""
    try:
        proj = get_memory_projection()
        labels = {}
        for m in proj:
            labels[m["label"]] = labels.get(m["label"], 0) + 1
        return {
            "ok": True,
            "identity": resolve_identity(),
            "projection": proj,
            "label_stats": labels,
            "unified_context": build_unified_personal_context(),
            "user_model_proposal": distill_user_model_proposal(),
            "ledger_count": len(get_confirmation_ledger()),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
