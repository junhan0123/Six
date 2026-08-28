#!/usr/bin/env python3
"""庄周 · Permission Guard（Phase 7 Order 2 · 电脑动作权限闸门）

流程（严格）：
    Task
      ↓
    Capability
      ↓
    Policy Engine（policy_engine.evaluate / request_approval）
      ↓
    Decision（auto | confirm | block）
      ↓
    Execute / Confirm / Deny
      ↓
    computer_executor（唯一允许触碰执行的地方）
      ↓
    Verification Layer（执行后复核 → VERIFIED / UNVERIFIED）

纪律：
- Agent / Runtime 严禁直接调用 executor；只能通过本 Guard 的 run() 入口。
- 授权裁决 100% 委托既有 Policy Engine（policy_engine.evaluate），无第二权限系统。
- 每次状态转变都发布领域事件（COMPUTER_ACTION_*），前端 AppState 合约消费。
- Order 3 起 executor 默认仍为 MockComputerExecutor（安全）；生产应使用
  PermissionGuard(RealComputerExecutor(), VerificationLayer(RealObserver()))。
- 真实执行器仅实现 LOW / MEDIUM；HIGH / CRITICAL 在 Guard 层即拒，绝不绕过。
"""

from __future__ import annotations

from capability_os.registry import is_known, is_implemented, risk_of
from computer_action import ComputerAction
from computer_executor import MockComputerExecutor, RealComputerExecutor
from verification import VerificationLayer
from eventbus import publish_domain


class PermissionGuard:
    def __init__(self, executor=None, verifier=None):
        # 执行器是唯一可被调用执行的地方（默认 mock，安全）
        self.executor = executor or MockComputerExecutor()
        # 验证层：执行后复核（默认无观察者，仅验证 result 自证的能力）
        self.verifier = verifier or VerificationLayer(observer=None)

    # —— 入口 1：规划（Task → Capability）——
    def plan(self, capability, target="", parameters=None, *, goal_id=None, action_id=None):
        if not is_known(capability):
            raise ValueError(f"未知能力，拒绝规划: {capability}")
        action = ComputerAction(capability, target, parameters,
                                action_id=action_id, goal_id=goal_id)
        action.status = "planned"
        publish_domain("COMPUTER_ACTION_PLANNED", _planned_payload(action))
        return action

    # —— 入口 2：裁决（Capability → Policy Engine → Decision）——
    def decide(self, action, goal_id=None, default_deny=True):
        if not is_known(action.capability):
            action.permissionDecision = "deny"
            action.decisionReason = "能力未注册"
            publish_domain("COMPUTER_ACTION_DENIED", _denied_payload(action, "能力未注册"))
            return {"decision": "deny", "reason": "能力未注册"}
        # HIGH/CRITICAL 本 Order 拒绝（暂不实现）
        r = risk_of(action.capability)
        if r in ("HIGH", "CRITICAL"):
            action.permissionDecision = "deny"
            action.decisionReason = f"风险等级 {r} 在 Order 2 未实现"
            action.status = "denied"
            publish_domain("COMPUTER_ACTION_DENIED", _denied_payload(action, action.decisionReason))
            return {"decision": "deny", "reason": action.decisionReason}
        # 委托既有 Policy Engine 裁决（复用，无第二权限系统）
        from policy_engine import evaluate
        dec = evaluate(action.capability, action.parameters, goal_id=goal_id, default_deny=default_deny)
        action.permissionDecision = dec["decision"]
        action.decisionReason = dec["reason"]
        if dec["decision"] == "block":
            action.status = "denied"
            publish_domain("COMPUTER_ACTION_DENIED", _denied_payload(action, dec["reason"]))
        return dec

    # —— 入口 3：执行（仅经本 Guard；Agent 不得直调 executor）——
    def run(self, action, goal_id=None, default_deny=True, auto_approve=False):
        """完整链路：plan 之后 → decide → (confirm?approve) → execute → 事件。

        返回 action（含最终 status / result）。Agent / Runtime 只调用本方法，
        绝不直接调用 self.executor。
        """
        dec = self.decide(action, goal_id=goal_id, default_deny=default_deny)
        d = dec["decision"]
        if d == "block" or d == "deny":
            return action  # DENIED 事件已在 decide 发出
        if d == "confirm":
            if not auto_approve:
                from policy_engine import request_approval
                # 无 goal 上下文或用户拒绝 → request_approval 返回 reject/timeout
                verdict = request_approval(
                    action.capability, action.parameters,
                    summary=f"请求执行电脑能力 {action.capability}",
                    goal_id=goal_id, default_deny=default_deny,
                )
                if verdict != "approve":
                    action.permissionDecision = "deny"
                    action.status = "denied"
                    reason = "用户拒绝 / 超时 / 无 Goal 上下文"
                    publish_domain("COMPUTER_ACTION_DENIED", _denied_payload(action, reason))
                    return action
            # approve：继续
        # auto 或 confirm+approve → 执行
        action.status = "called"
        publish_domain("COMPUTER_ACTION_CALLED", _called_payload(action))
        try:
            result = self.executor.execute(action)
            action.result = result
            action.status = "done"
            publish_domain("COMPUTER_ACTION_DONE", _done_payload(action, result))
            # —— Order 3：Verification（执行后复核 Observation → Action → Verification 闭环）——
            verified, detail = self.verifier.verify(action, result)
            action.verified = verified
            action.verificationDetail = detail
            if verified:
                publish_domain("COMPUTER_ACTION_VERIFIED", _verified_payload(action, detail))
            else:
                publish_domain("COMPUTER_ACTION_UNVERIFIED", _unverified_payload(action, detail))
        except Exception as e:
            action.result = {"error": str(e)}
            action.status = "failed"
            publish_domain("COMPUTER_ACTION_FAILED", _failed_payload(action, str(e)))
        return action


# —— 事件载荷（与前端 zz-events.js 合约一致）——
def _planned_payload(a):
    return {"actionId": a.actionId, "capability": a.capability, "target": a.target,
            "risk": a.risk, "expectedEffect": a.expectedEffect,
            "parameters": a.parameters, "goalId": a.goalId}


def _called_payload(a):
    return {"actionId": a.actionId, "capability": a.capability,
            "permissionDecision": a.permissionDecision, "goalId": a.goalId}


def _done_payload(a, result):
    return {"actionId": a.actionId, "capability": a.capability, "result": result, "goalId": a.goalId}


def _failed_payload(a, error):
    return {"actionId": a.actionId, "capability": a.capability, "error": error, "goalId": a.goalId}


def _denied_payload(a, reason):
    return {"actionId": a.actionId, "capability": a.capability, "risk": a.risk,
            "reason": reason, "goalId": a.goalId}


def _verified_payload(a, detail):
    return {"actionId": a.actionId, "capability": a.capability, "verified": True,
            "detail": detail, "goalId": a.goalId}


def _unverified_payload(a, detail):
    return {"actionId": a.actionId, "capability": a.capability, "verified": False,
            "detail": detail, "goalId": a.goalId}


# 进程级单例（后端运行时经此入口；Agent 不直接触 executor）
guard = PermissionGuard()
