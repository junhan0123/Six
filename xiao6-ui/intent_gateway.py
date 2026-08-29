#!/usr/bin/env python3
"""庄周 · Command Intent Gateway（Phase 6 Order 5）—— 统一意图入口

职责（极瘦红线，违反即实现失败）：
- 把「用户 Command 输入」升级为真正的 Intent Gateway，而非聊天框 / UI 美化 / Prompt 增加。
- 真实链路：User Intent → Intent Recognition(GDE) → Goal Decision Engine → Goal Created → Order 2 生命周期。
- 不复制 Goal 创建逻辑：复用 GoalDecisionEngine.ingest / .submit 与 runtime.submit_goal / goals.create_goal。
- 不替代 Planner / Executor：本模块只做「意图识别 + 是否建 Goal 的决策门」，后续编排仍走 AgentRuntime。
- 所有 Intent 生命周期事件经 publish_domain() 单一来源发出（禁字符串硬编码、禁第二套事件）。
- Ordering 铁律：INTENT_CONVERTED_TO_GOAL 必须在 GOAL_CREATED 之前发出
  （GOAL_CREATED 在 goals.create_goal 内部同步发出，故转换事件须在 submit_goal 调用前发）。
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Optional

from eventbus import publish_domain

INTENT_NAMES = {
    "INTENT_RECEIVED", "INTENT_ANALYZING", "INTENT_CLASSIFIED",
    "INTENT_ACCEPTED", "INTENT_REJECTED", "INTENT_CONVERTED_TO_GOAL",
}

# ---------------------------------------------------------------------------
# Phase 6 · Intent Routing：能力标签解析 + 意图分类（最小修改，不改 GDE 架构）
# ---------------------------------------------------------------------------
CAP_TAGS = {
    "深度思考": "thinking_mode",
    "联网搜索": "web_enabled",
    "代码执行": "code_enabled",
}
_CAP_RE = re.compile(r"【(深度思考|联网搜索|代码执行)】")

CASUAL_RE = re.compile(
    r"^(你好|您好|嗨|哈喽|hello|hi|在吗|在么|在不在|早上好|晚上好|下午好|谢谢|多谢|辛苦|"
    r"测试|试一下|试试|你是谁|介绍一下自己|自我介绍|你好呀|您好呀|你好啊)[\s!！。，,？?~～]*$",
    re.IGNORECASE,
)

# GoalSystem 只能由「明确长期目标意图」进入；命中才允许 GDE create，否则禁止自动建 Goal
GOAL_TRIGGERS = (
    "创建任务", "制定计划", "长期跟踪", "持续管理", "建立目标",
    "长期", "持续", "坚持", "养成", "每天", "每周",
)

KNOWLEDGE_VERBS = ("搜索", "查询", "查", "天气", "新闻", "热点", "介绍", "解释", "什么是", "怎么样", "多少", "几点")
EXEC_VERBS = ("写", "创建", "生成", "开发", "实现", "修复", "重构", "优化", "部署", "搭建", "整理", "分析", "总结", "翻译", "计算")


def parse_cap_tags(text: str) -> tuple:
    """解析并剥离【深度思考】【联网搜索】【代码执行】标签。

    标签仅作为 metadata（thinking_mode / web_enabled / code_enabled），
    影响模型参数 / 工具权限 / 回复策略，**不改变 intent 分类**。
    返回 (clean_text, flags)。
    """
    flags = {"thinking_mode": False, "web_enabled": False, "code_enabled": False}
    src = (text or "").strip()
    for tag, flag in CAP_TAGS.items():
        if f"【{tag}】" in src:
            flags[flag] = True
    clean = _CAP_RE.sub("", src).strip()
    return (clean or src), flags


def classify_intent(text: str) -> str:
    """Phase 6 · 意图分类：casual_chat | knowledge_query | execution_task | long_term_goal。

    - casual_chat：问候/寒暄 → LLM 直接回复（禁 Tool/Planner/Goal/Memory）
    - knowledge_query：搜索/查询 → Search/RAG
    - execution_task：执行动作 → Planner → Tools
    - long_term_goal：长期目标 → GoalSystem
    """
    t = (text or "").strip()
    if CASUAL_RE.match(t):
        return "casual_chat"
    if any(g in t for g in GOAL_TRIGGERS):
        return "long_term_goal"
    if any(k in t for k in KNOWLEDGE_VERBS) and not any(v in t for v in EXEC_VERBS):
        return "knowledge_query"
    return "execution_task"


def _emit(name: str, payload: dict, source: str = "intent_gateway") -> None:
    """发一条 Intent 生命周期领域事件（单一来源纪律，未知名由 publish_domain 拒绝）。"""
    try:
        if name not in INTENT_NAMES:
            return
        publish_domain(name, payload, source=source)
    except Exception as e:
        print(f"[IntentGateway] 领域事件发布失败（已忽略）: {e}")


def run_intent_gateway(text: str, *, source: str = "command_palette") -> dict:
    """执行一次完整意图网关流程，返回决策结果（不修改任何冻结设计 / 不新增 Goal 架构）。

    返回 dict：{ intentId, action, classification, confidence, title, goalId, reason }
    - action=create 且 submit 成功 → goalId 由 submit_goal 内部 create_goal 分配；
      INTENT_CONVERTED_TO_GOAL 在 submit 前发出（goalId 暂空），真实 goalId 由随后
      GOAL_CREATED(intentId) 携带，前端 AppState 据此把 Intent.targetGoal 关联上 Goal。
    """
    intent_id = "int_" + uuid.uuid4().hex[:12]
    user_text = (text or "").strip()

    # 1) 收到意图
    _emit("INTENT_RECEIVED", {
        "intentId": intent_id,
        "text": user_text,
        "source": source,
        "ts": time.time(),
    })

    # 2) 识别中
    _emit("INTENT_ANALYZING", {"intentId": intent_id})

    # 3) 意图识别（复用 Goal Decision Engine，零新增决策逻辑）
    from goal_decision_engine import GoalDecisionEngine
    engine = GoalDecisionEngine()
    dec = engine.ingest(user_text)

    # 4) 分类结果
    _emit("INTENT_CLASSIFIED", {
        "intentId": intent_id,
        "classification": dec.classification,
        "action": dec.action,
        "confidence": dec.confidence,
        "title": dec.title,
        "reason": dec.reason,
    })

    result: dict = {
        "intentId": intent_id,
        "action": dec.action,
        "classification": dec.classification,
        "confidence": dec.confidence,
        "title": dec.title,
        "goalId": None,
        "reason": dec.reason,
    }

    if dec.action == "create":
        # 5a) 接受意图
        _emit("INTENT_ACCEPTED", {
            "intentId": intent_id,
            "classification": dec.classification,
            "confidence": dec.confidence,
            "title": dec.title,
        })
        # 5b) 转换中（必须在 GOAL_CREATED 之前；goalId 由随后 GOAL_CREATED 补全）
        _emit("INTENT_CONVERTED_TO_GOAL", {
            "intentId": intent_id,
            "title": dec.title,
            "goalId": None,
        })
        # 6) 复用已有写出口：GDE.submit → runtime.submit_goal → goals.create_goal
        #    （create_goal 内 GOAL_CREATED 携带 intentId，供前端关联 targetGoal）
        gid = engine.submit(dec, intent_id=intent_id)
        if gid is not None:
            result["goalId"] = gid
        else:
            result["action"] = "rejected"
            _emit("INTENT_REJECTED", {
                "intentId": intent_id,
                "classification": dec.classification,
                "confidence": dec.confidence,
                "title": dec.title,
                "reason": "submit_goal 失败",
            })
    elif dec.action in ("propose", "resume"):
        # 接受但需确认（不自动建 Goal，交由用户确认流程 / 正常聊天继续）
        _emit("INTENT_ACCEPTED", {
            "intentId": intent_id,
            "classification": dec.classification,
            "confidence": dec.confidence,
            "title": dec.title,
            "needsConfirm": True,
            "goalId": dec.goal_id,
        })
    else:  # skip
        _emit("INTENT_REJECTED", {
            "intentId": intent_id,
            "classification": dec.classification,
            "confidence": dec.confidence,
            "title": dec.title,
            "reason": dec.reason,
        })

    return result
