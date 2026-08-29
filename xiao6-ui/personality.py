#!/usr/bin/env python3
"""小6 · 人格引擎（Personality）—— 五维动态人格参数

宪法 §19：人格须动态生成、不得写死；§4.1 将 Personality 列为 Context 来源。
本模块：PersonalityParams（五维 0~1）+ generate（默认 = 当前行为等价）+ render_prompt + 发布 PersonalityChanged。

过渡期（D4）：默认参数映射回现状（config.SYSTEM_PROMPT 基线：冷静高效简洁有分寸），
故开启 Flag 与现状无感一致；并复用 P1 已抽取的 user_model.communication_style 做轻量种子，
使已抽取的画像生效。设置面板多 Profile 调参（§19.3）留作 Phase 2.5。

依赖方向单向：personality → eventbus（发布 PersonalityChanged）；不反向依赖 context。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Optional


@dataclass
class PersonalityParams:
    """五维人格参数（0~1）。"""

    professionalism: float = 0.8   # 专业可靠度
    proactivity: float = 0.2       # 主动展开度（低=被动回应）
    technical_depth: float = 0.6   # 技术深度（高=给可执行方案）
    verbosity: float = 0.4         # 解释长度（低=简洁，对齐现状"简洁"基线）
    seriousness: float = 0.8       # 严肃度（高=就事论事，低=可带幽默）


def _clamp(v: float) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return 0.5


def generate(
    user_model: Optional[dict] = None,
    world: Optional[object] = None,
    goals: Optional[object] = None,
    override: Optional[PersonalityParams] = None,
) -> PersonalityParams:
    """生成人格参数。

    - 默认参数 = 当前行为等价（D4）。
    - override：外部（设置面板/上下文）覆盖个别维度。
    - 种子：P1 user_model.communication_style（verbosity/humor 映射）。
    """
    p = PersonalityParams()
    if override is not None:
        for f in fields(PersonalityParams):
            v = getattr(override, f.name, None)
            if v is not None:
                setattr(p, f.name, _clamp(v))
    cs = ((user_model or {}).get("communication_style") or {}) if isinstance(user_model, dict) else {}
    vm = cs.get("verbosity")
    if vm == "concise":
        p.verbosity = min(p.verbosity, 0.35)
    elif vm == "verbose":
        p.verbosity = max(p.verbosity, 0.7)
    hum = cs.get("humor")
    if hum == "avoid":
        p.seriousness = max(p.seriousness, 0.9)
    elif hum == "welcome":
        p.seriousness = min(p.seriousness, 0.6)
    return p


def render_prompt(p: PersonalityParams) -> str:
    """渲染人格指令块（供 Context Engine 注入）。默认产出与现状基线一致。"""
    parts = []
    parts.append("专业且可靠" if p.professionalism >= 0.7 else "随和亲切")
    parts.append("技术准确、优先给出可执行方案" if p.technical_depth >= 0.5 else "偏概念性解释")
    parts.append("回答简洁直接、不啰嗦" if p.verbosity < 0.5 else "回答详尽、适当展开")
    parts.append("语气严肃、就事论事" if p.seriousness >= 0.7 else "语气轻松、可带一点幽默")
    if p.proactivity < 0.3:
        parts.append("被动回应、不主动展开无关内容")
    return "【人格】" + "；".join(parts) + "。"


def publish_changed(p: PersonalityParams) -> None:
    """发布 PersonalityChanged（供 Dashboard 订阅，§21.2）。"""
    try:
        from eventbus import bus

        bus.publish("PersonalityChanged", asdict(p), source="personality")
    except Exception:
        pass
