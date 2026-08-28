"""context.budget — Context Budget Manager (stub for S79.7)
Minimal compatibility layer to allow server startup.
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
    """Stub budget manager for context window management."""
    
    def __init__(self, max_tokens: int = 8000, default_tier: str = BudgetTier.MEDIUM):
        self.max_tokens = max_tokens
        self.default_tier = default_tier
    
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
