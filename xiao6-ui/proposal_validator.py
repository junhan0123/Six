#!/usr/bin/env python3
"""PHASE 132 — Proposal Validator

检查 Proposal 合法性，调用 Policy Engine 只读验证。

规则：
1. 字段完整性：title, description, steps, risk
2. Policy Engine 只读检查
3. Risk Gate：low=允许, medium=确认, high=二次确认
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


# ============================================================
# ValidationResult
# ============================================================

@dataclass
class ValidationResult:
    """验证结果。"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    risk_level: str
    requires_approval: bool


# ============================================================
# Proposal Validator
# ============================================================

class ProposalValidator:
    """提案验证器。"""

    # 必需字段
    REQUIRED_FIELDS = ["title", "description", "steps", "risk"]

    # Risk 级别映射
    RISK_LEVELS = {
        "low": {"requires_approval": False, "confidence": 0.9},
        "medium": {"requires_approval": True, "confidence": 0.7},
        "high": {"requires_approval": True, "needs_second_confirmation": True, "confidence": 0.5},
    }

    def validate(self, proposal: Dict[str, Any]) -> ValidationResult:
        """
        验证提案。
        
        Args:
            proposal: 提案字典
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        # 1. 字段完整性检查
        errors.extend(self._check_required_fields(proposal))
        
        # 2. Steps 格式检查
        if "steps" in proposal:
            errors.extend(self._check_steps_format(proposal["steps"]))
        
        # 3. Risk 级别检查
        risk_level = self._check_risk(proposal.get("risk", "low"))
        
        # 4. Policy Engine 只读检查（如果可用）
        policy_result = self._check_policy(proposal)
        if policy_result:
            warnings.extend(policy_result.get("warnings", []))
            if not policy_result.get("allowed", True):
                errors.append(policy_result.get("reason", "Policy check failed"))
        
        # 5. 综合判断
        requires_approval = risk_level in ["medium", "high"]
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            risk_level=risk_level,
            requires_approval=requires_approval
        )

    def _check_required_fields(self, proposal: Dict) -> List[str]:
        """检查必需字段。"""
        errors = []
        for field in self.REQUIRED_FIELDS:
            value = proposal.get(field)
            if not value:
                errors.append(f"Missing required field: {field}")
            elif field == "title" and isinstance(value, str) and len(value.strip()) < 2:
                errors.append(f"Field '{field}' is too short")
        return errors

    def _check_steps_format(self, steps) -> List[str]:
        """检查 steps 格式。"""
        if not isinstance(steps, list):
            return ["'steps' must be a list"]
        
        errors = []
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {i} must be a dict")
                continue
            
            if "title" not in step:
                errors.append(f"Step {i} missing 'title'")
            if "action" not in step:
                errors.append(f"Step {i} missing 'action'")
        
        return errors

    def _check_risk(self, risk: str) -> str:
        """检查风险级别。"""
        risk = risk.lower() if risk else "low"
        if risk in self.RISK_LEVELS:
            return risk
        return "low"  # 默认低危

    def _check_policy(self, proposal: Dict) -> Optional[Dict]:
        """
        调用 Policy Engine（只读）。
        
        Returns:
            Policy 检查结果或 None（如果不可用）
        """
        try:
            from policy_engine import PolicyEngine
            engine = PolicyEngine()
            result = engine.check(proposal)
            return result
        except ImportError:
            return None
        except Exception as e:
            return {"warnings": [f"Policy check failed: {e}"]}

    def get_approval_config(self, risk_level: str) -> Dict:
        """获取审批配置。"""
        return self.RISK_LEVELS.get(risk_level, self.RISK_LEVELS["low"])


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== PHASE 132 Proposal Validator Tests ===\n")
    
    validator = ProposalValidator()
    
    # Test 1: 正常 Proposal
    print("Test 1: Valid proposal")
    valid_proposal = {
        "id": "test-1",
        "title": "恢复停滞任务",
        "description": "检查任务状态并重新执行",
        "steps": [
            {"title": "检查状态", "action": "GET /api/tasks/{id}"},
            {"title": "分析原因", "action": "READ task.log"},
            {"title": "修复问题", "action": "FIX issue"},
            {"title": "重新执行", "action": "POST /api/tasks/{id}/resume"}
        ],
        "risk": "medium"
    }
    result = validator.validate(valid_proposal)
    assert result.valid == True
    assert result.risk_level == "medium"
    assert result.requires_approval == True
    print(f"  PASS: valid={result.valid}, risk={result.risk_level}, approval={result.requires_approval}")
    
    # Test 2: 缺少必需字段
    print("\nTest 2: Missing required fields")
    invalid_proposal = {
        "id": "test-2",
        "title": ""
    }
    result = validator.validate(invalid_proposal)
    assert result.valid == False
    assert len(result.errors) >= 2  # description and steps missing
    print(f"  PASS: valid={result.valid}, errors={len(result.errors)}")
    
    # Test 3: 高风险 Proposal
    print("\nTest 3: High risk proposal")
    high_risk = {
        "title": "删除所有任务",
        "description": "清理旧数据",
        "steps": [{"title": "清空", "action": "DELETE /api/tasks"}],
        "risk": "high"
    }
    result = validator.validate(high_risk)
    assert result.valid == True
    assert result.risk_level == "high"
    assert result.requires_approval == True
    config = validator.get_approval_config("high")
    assert config.get("needs_second_confirmation") == True
    print(f"  PASS: valid={result.valid}, risk={result.risk_level}, needs_second_confirmation={config.get('needs_second_confirmation')}")
    
    # Test 4: Steps 格式错误
    print("\nTest 4: Invalid steps format")
    bad_steps = {
        "title": "测试",
        "description": "描述",
        "steps": "not a list",  # 应该是列表
        "risk": "low"
    }
    result = validator.validate(bad_steps)
    assert result.valid == False
    assert any("steps" in e for e in result.errors)
    print(f"  PASS: valid={result.valid}, errors={[e for e in result.errors if 'steps' in e]}")
    
    print("\n=== All Tests Complete ===")
