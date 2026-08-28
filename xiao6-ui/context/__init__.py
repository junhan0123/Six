"""context.__init__ — Context Engine Package (S79.7 minimal compat + R8-P4 facade)
Minimal compatibility layer to allow server startup.
"""

from __future__ import annotations

from .budget import ContextBudget, BudgetTier
from .facade import build_cognitive_context
from .models import (
    BudgetTier,
    BuildContext,
    ContextBundle,
    ContextItem,
    ContextSource,
)

# Stub functions for server startup
def build_context_prompt(session_id: str, history: list = None, **kwargs) -> str:
    """Build context prompt for a session.
    Stub implementation that returns empty string.
    """
    return ""

# Export all
__all__ = [
    "BudgetTier",
    "BuildContext",
    "ContextBundle",
    "ContextItem",
    "ContextSource",
    "ContextBudget",
    "build_context_prompt",
    "build_cognitive_context",
]

# Feature flag
try:
    import config
    FEATURE_CONTEXT_ENGINE: bool = getattr(config, "FEATURE_CONTEXT_ENGINE", False)
except Exception:
    FEATURE_CONTEXT_ENGINE = False
