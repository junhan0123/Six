"""context.budget — Context Budget Manager（R8-P0 恢复 agent_runtime 所需接口）

S79.7 stub 补齐：agent_runtime 依赖 `ContextBudget(max_calls=...)` + `consume_call()`
（Phase C · G2 能力调用预算闸门）。保留既有 max_tokens/check/get_budget API 不破坏兼容。
"""

from __future__ import annotations

class BudgetTier:
    """Budget tier for context window management."""
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class ContextBudget:
    """Budget manager for context window management.

    max_calls：能力调用次数预算（0/None=无限）；consume_call() FAIL CLOSED——
    耗尽即返回 False，由调用方（agent_runtime）拒绝执行。
    """

    def __init__(self, max_tokens: int = 8000, default_tier: str = BudgetTier.MEDIUM,
                 max_calls: int = None):
        self.max_tokens = max_tokens
        self.default_tier = default_tier
        self.max_calls = max_calls or 0          # 0 = 无限
        self._calls_used = 0

    def consume_call(self) -> bool:
        """消耗一次能力调用额度；无额度（无限）恒 True；耗尽返回 False。"""
        if not self.max_calls:
            return True
        if self._calls_used >= self.max_calls:
            return False
        self._calls_used += 1
        return True

    def remaining_calls(self) -> int:
        """剩余调用额度；无限返回 -1。"""
        if not self.max_calls:
            return -1
        return max(0, self.max_calls - self._calls_used)

    def check(self, tokens: int) -> bool:
        """Check if token count is within budget."""
        return tokens <= self.max_tokens

    def get_budget(self, tier: str = None) -> int:
        """Get budget for a given tier."""
        budgets = {
            BudgetTier.TINY: 1000,
            BudgetTier.SMALL: 2000,
            BudgetTier.MEDIUM: 4000,
            BudgetTier.LARGE: 8000,
            BudgetTier.XLARGE: 16000,
        }
        return budgets.get(tier or self.default_tier, self.max_tokens)
