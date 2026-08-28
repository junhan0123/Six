"""context.models — Context Models (stub for S79.7)
Minimal compatibility layer for context data structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class BudgetTier:
    """Budget tier for context window management."""
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


@dataclass
class ContextItem:
    """A single item in the context."""
    id: str
    source: str
    content: str
    relevance_score: float = 0.0
    timestamp: Optional[float] = None


@dataclass
class ContextBundle:
    """A bundle of context items."""
    items: List[ContextItem] = field(default_factory=list)
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildContext:
    """Build context for prompt generation."""
    session_id: str
    history: List[Dict[str, str]] = field(default_factory=list)
    memory: List[ContextItem] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    user_model: Optional[Dict[str, Any]] = None


class ContextSource:
    """Context source base class."""
    NAME: str = "base"
    
    def collect(self, ctx: BuildContext) -> List[ContextItem]:
        return []
