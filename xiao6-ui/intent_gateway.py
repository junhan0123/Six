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

import time
import uuid
from typing import Optional

from eventbus import publish_domain

INTENT_NAMES = {
    "INTENT_RECEIVED", "INTENT_ANALYZING", "INTENT_CLASSIFIED",
    "INTENT_ACCEPTED", "INTENT_REJECTED", "INTENT_CONVERTED_TO_GOAL",
}


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
