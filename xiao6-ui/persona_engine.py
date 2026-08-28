#!/usr/bin/env python3
"""庄周 · 人格一致性引擎（Phase 12 · P12-2）

目标：让庄周的语气/风格/边界/小习惯跨会话稳定不变。
设计：
  - 读 config 的 PERSONA_TONE / PERSONA_STYLE / PERSONA_BOUNDARIES / PERSONA_QUIRKS；
  - 支持 user_model 覆盖（user_model["tone"] / user_model["style"] 等）；
  - get_persona_prompt(user_model) 返回稳定的人格指令块，供 llm/memory 注入系统提示第一段。
与既有 personality.py（五维动态参数，供 Context Engine 注入）并存不冲突：
  persona_engine 是 spec 要求的「稳定人格基线」，优先级最高、最先注入。
纯函数、零网络依赖、导入安全；任何异常回退到默认 warm 人格。
"""

from __future__ import annotations

# 语气映射：键 -> 自然语言描述（同时保留英文键，便于单测断言 "warm" in prompt）
_TONE_MAP = {
    "warm": "友好、有温度、像老朋友一样自然",
    "formal": "正式、礼貌、专业克制",
    "funny": "轻松幽默、适当玩梗、气氛活跃",
}

# 风格映射
_STYLE_MAP = {
    "concise": "回答简洁直接、多用要点、不啰嗦",
    "detailed": "回答详尽、适当展开背景与理由",
    "storytelling": "用故事化、场景化的方式表达",
}

# 边界映射（拒绝敏感/高风险话题时的标准话术）
_BOUNDARY_MAP = {
    "no_politics": "不主动讨论政治敏感话题",
    "no_medical_advice": "不提供医疗诊断建议（可建议就医或咨询专业人士）",
    "no_illegal": "不协助任何违法或有害行为",
    "no_financial_advice": "不提供具体投资建议（可科普概念）",
}

# 小习惯映射
_QUIRK_MAP = {
    "use_emoji": "适当使用 emoji 增强表达温度",
    "end_with_question": "结尾常以一个自然的问题延续对话、保持互动",
    "use_honorific": "称呼用户时自然、尊重",
    "concise_ack": "先简短确认再展开，不绕弯子",
}


def _resolve(user_model: dict | None):
    """合并 显式 user_model 参数 → identity.json 默认 → config 默认值，返回四要素元组。

    优先级（高到低）：
      1. 显式调用参数 user_model["tone"] / user_model["style"]（调用方明确指定，必须生效）；
      2. Identity & Self Model Layer 的 identity.json（behavior_style）作为人格默认基线；
      3. config.PERSONA_* 作为系统级兜底默认值。
    不含任何硬编码身份/人格文本——身份由 IdentitySource 统一注入。
    """
    import config

    um = user_model if isinstance(user_model, dict) else {}
    # 1) 显式调用参数优先（调用方明确指定 style/tone 必须生效）
    tone = um.get("tone")
    style = um.get("style")
    # 2) 未显式指定时，回退到 identity.json 默认行为风格基线
    if tone is None or style is None:
        try:
            from identity.provider import get_provider

            bs = get_provider().get_behavior_style()
            if tone is None:
                tone = bs.get("tone")
            if style is None:
                style = bs.get("style")
        except Exception:
            pass
    # 3) 系统级兜底默认值
    if not tone:
        tone = getattr(config, "PERSONA_TONE", "warm") or "warm"
    if not style:
        style = getattr(config, "PERSONA_STYLE", "concise") or "concise"
    boundaries = getattr(config, "PERSONA_BOUNDARIES", "no_politics,no_medical_advice") or ""
    quirks = getattr(config, "PERSONA_QUIRKS", "use_emoji,end_with_question") or ""
    return tone, style, boundaries, quirks


def get_persona_prompt(user_model: dict | None = None) -> str:
    """生成稳定【行为风格】指令块。

    身份（你是谁）已由 Identity & Self Model Layer 的 identity.json 单一来源提供，
    并经 Context Engine IdentitySource 注入；本函数只负责「行为风格」（语气/风格/边界/小习惯）。
    行为参数优先级：显式调用参数 user_model > identity.json behavior_style 默认基线 > config.PERSONA_* 兜底。
    任何异常回退默认 warm 行为风格，绝不抛错、绝不包含硬编码身份文本。
    """
    try:
        tone, style, boundaries, quirks = _resolve(user_model)
    except Exception:
        tone, style, boundaries, quirks = "warm", "concise", "no_politics,no_medical_advice", "use_emoji,end_with_question"

    lines = ["【行为风格】"]
    # 语气：同时给出英文键与原生描述，保证单测 "warm" in prompt 与中文可读性
    lines.append(f"· 语气（tone={tone}）：{_TONE_MAP.get(tone, _TONE_MAP['warm'])}")
    lines.append(f"· 风格（style={style}）：{_STYLE_MAP.get(style, _STYLE_MAP['concise'])}")

    bl = [b.strip() for b in boundaries.split(",") if b.strip()]
    if bl:
        desc = "；".join(_BOUNDARY_MAP.get(b, b) for b in bl)
        lines.append(f"· 边界：{desc}")

    ql = [q.strip() for q in quirks.split(",") if q.strip()]
    if ql:
        qdesc = "；".join(_QUIRK_MAP.get(q, q) for q in ql)
        lines.append(f"· 小习惯：{qdesc}")

    lines.append("· 一致性：跨会话记住自己说过的话与承诺，人格与边界不要前后矛盾。")
    return "\n".join(lines) + "\n"


def get_persona_config() -> dict:
    """返回当前人格配置快照（供前端设置面板回填）。"""
    try:
        tone, style, boundaries, quirks = _resolve(None)
        return {
            "tone": tone,
            "style": style,
            "boundaries": boundaries,
            "quirks": quirks,
        }
    except Exception:
        return {
            "tone": "warm",
            "style": "concise",
            "boundaries": "no_politics,no_medical_advice",
            "quirks": "use_emoji,end_with_question",
        }
