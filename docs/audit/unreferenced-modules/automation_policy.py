#!/usr/bin/env python3
"""PHASE 133 — Automation Policy Layer

判断 TaskProposal / Task 是否允许自动化执行。

规则：
- 允许：low risk, 重复性任务, 无危险操作
- 禁止：删除, 权限修改, 系统修改, 敏感操作
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class AutomationDecision(Enum):
    """自动化决策结果。"""
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class AutomationPolicyResult:
    """自动化策略评估结果。"""
    decision: AutomationDecision
    reason: str
    risk: str
    details: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "risk": self.risk,
            "details": self.details
        }


class AutomationPolicy:
    """自动化策略引擎。"""
    
    # 禁止的操作类型
    FORBIDDEN_OPERATIONS = {
        "delete",
        "remove", 
        "drop",
        "truncate",
        "kill",
        "shutdown",
        "reboot",
        "format",
        "wipe"
    }
    
    # 敏感操作关键词
    SENSITIVE_KEYWORDS = [
        "权限", "授权", "admin", "root", "sudo",
        "系统配置", "修改配置", "防火墙", "网络"
    ]
    
    # 允许自动化的 risk 级别
    AUTO_ALLOWED_RISKS = {"low"}
    
    # 需要确认的 risk 级别
    APPROVAL_NEEDED_RISKS = {"medium"}
    
    # 高风险，直接阻止
    BLOCKED_RISKS = {"high", "critical"}
    
    def evaluate(
        self,
        proposal: Dict[str, Any],
        task_type: Optional[str] = None,
        operations: Optional[List[str]] = None
    ) -> AutomationPolicyResult:
        """
        评估是否允许自动化执行。
        
        Args:
            proposal: 提案数据
            task_type: 任务类型
            operations: 操作列表
            
        Returns:
            AutomationPolicyResult
        """
        risk = proposal.get("risk", "low")
        steps = proposal.get("steps", [])
        title = proposal.get("title", "")
        description = proposal.get("description", "")
        
        details = []
        
        # 1. 检查 Risk 级别
        if risk in self.BLOCKED_RISKS:
            return AutomationPolicyResult(
                decision=AutomationDecision.BLOCKED,
                reason=f"风险级别 {risk} 过高，不允许自动化执行",
                risk=risk,
                details=[f"风险级别: {risk}"]
            )
        
        # 2. 检查操作类型
        if operations:
            for op in operations:
                if op.lower() in self.FORBIDDEN_OPERATIONS:
                    return AutomationPolicyResult(
                        decision=AutomationDecision.BLOCKED,
                        reason=f"禁止的自动化操作: {op}",
                        risk="high",
                        details=[f"禁止操作: {op}"]
                    )
        
        # 3. 检查步骤内容
        for step in steps:
            step_text = str(step)
            for keyword in self.SENSITIVE_KEYWORDS:
                if keyword in step_text:
                    return AutomationPolicyResult(
                        decision=AutomationDecision.BLOCKED,
                        reason=f"步骤包含敏感操作: {keyword}",
                        risk="high",
                        details=[f"敏感关键词: {keyword}"]
                    )
        
        # 4. 根据 risk 级别决定
        if risk in self.AUTO_ALLOWED_RISKS:
            return AutomationPolicyResult(
                decision=AutomationDecision.ALLOWED,
                reason="低风险任务，允许自动化执行",
                risk=risk,
                details=["风险级别: low", "无禁止操作"]
            )
        
        if risk in self.APPROVAL_NEEDED_RISKS:
            return AutomationPolicyResult(
                decision=AutomationDecision.NEEDS_APPROVAL,
                reason="中等风险任务，需要人工确认",
                risk=risk,
                details=["风险级别: medium", "需要用户确认"]
            )
        
        # 默认允许（保守策略）
        return AutomationPolicyResult(
            decision=AutomationDecision.ALLOWED,
            reason="默认允许（保守策略）",
            risk="low",
            details=["未明确风险级别，保守处理"]
        )
    
    def is_safe_operation(self, operation: str) -> bool:
        """检查操作是否安全。"""
        return operation.lower() not in self.FORBIDDEN_OPERATIONS
    
    def get_risk_level(self, proposal: Dict[str, Any]) -> str:
        """获取提案风险级别。"""
        return proposal.get("risk", "low")


# 全局单例
_instance: Optional[AutomationPolicy] = None


def get_automation_policy() -> AutomationPolicy:
    """获取全局自动化策略单例。"""
    global _instance
    if _instance is None:
        _instance = AutomationPolicy()
    return _instance