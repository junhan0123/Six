#!/usr/bin/env python3
"""庄周 · ComputerAction 数据模型 —— Phase 7 Order 2

纯数据结构：承载一次电脑动作的全部元数据 + 权限裁决结果 + 执行结果。
不依赖 OS / 网络 / UI。后端 Permission Guard 与前端 permission-guard 共用同一字段契约。

字段（任务硬要求）：
  actionId            唯一动作 id
  capability          能力 id（必须已在 Capability Registry 注册）
  target              目标（window/app/process/file/browser/screen id 或路径）
  parameters          动作参数（dict）
  risk                风险等级 LOW/MEDIUM/HIGH/CRITICAL（由 capability 推导）
  expectedEffect      预期效果描述（由 capability 推导）
  permissionDecision  权限裁决 auto|confirm|block|deny
  result              执行结果或错误信息
"""

from __future__ import annotations

import time
import uuid


class ComputerAction:
    def __init__(self, capability, target="", parameters=None, *,
                 action_id=None, risk=None, expected_effect=None,
                 permission_decision=None, result=None, goal_id=None):
        from capability_os.registry import get_capability, risk_of

        if not capability:
            raise ValueError("capability 必填")
        cap = get_capability(capability)
        if cap is None:
            raise ValueError(f"未知能力（未注册到 Capability Registry）: {capability}")

        self.actionId = action_id or uuid.uuid4().hex
        self.capability = capability
        self.target = target
        self.parameters = parameters or {}
        self.risk = risk or cap.risk
        self.expectedEffect = expected_effect or cap.description
        self.permissionDecision = permission_decision  # auto|confirm|block|deny|None
        self.result = result
        self.goalId = goal_id
        self.status = "planned"          # planned|called|done|failed|denied
        self.decisionReason = None
        self.verified = None             # True|False|None（Order 3 Verification Layer 回填）
        self.verificationDetail = None   # 验证说明
        self.createdAt = time.time()

    def to_dict(self):
        return {
            "actionId": self.actionId,
            "capability": self.capability,
            "target": self.target,
            "parameters": self.parameters,
            "risk": self.risk,
            "expectedEffect": self.expectedEffect,
            "permissionDecision": self.permissionDecision,
            "result": self.result,
            "goalId": self.goalId,
            "status": self.status,
            "decisionReason": self.decisionReason,
            "verified": self.verified,
            "verificationDetail": self.verificationDetail,
            "createdAt": self.createdAt,
        }

    @classmethod
    def from_dict(cls, d):
        a = cls(
            d["capability"], d.get("target", ""), d.get("parameters"),
            action_id=d.get("actionId"),
            risk=d.get("risk"),
            expected_effect=d.get("expectedEffect"),
            permission_decision=d.get("permissionDecision"),
            result=d.get("result"),
            goal_id=d.get("goalId"),
        )
        a.status = d.get("status", "planned")
        a.decisionReason = d.get("decisionReason")
        a.verified = d.get("verified", None)
        a.verificationDetail = d.get("verificationDetail", None)
        a.createdAt = d.get("createdAt", a.createdAt)
        return a
