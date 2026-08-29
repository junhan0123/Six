"""Xiao6 v2 · Context Engine 包

提供统一的上下文模型、接口、来源、排序、预算与 Builder 入口。
当前为 P0 数据模型 + P1 来源/Builder 骨架阶段；Builder 经 SourceRegistry 聚合来源
（当前仅 MemorySource 接入 memory.build_system_prompt），并经五阶段管线
（Collect → Rank → Budget → Bundle → Build）产出 Prompt。默认无限预算下输出逐字节一致。
"""

from __future__ import annotations

from .budget import ContextBudget
from .builder import LegacyContextBuilder
from .cache import ContextCache
from .facade import build_context_prompt
from .interfaces import ContextBuilderProtocol, ContextSourceProvider
from .models import (
    BudgetTier,
    BuildContext,
    ContextBundle,
    ContextItem,
    ContextSource,
)
from .ranker import ContextRanker
from .serializer import (
    bundle_from_json,
    bundle_to_dict,
    bundle_to_json,
    dict_to_bundle,
)
from .sources import (
    ConversationSource,
    MemorySource,
    SourceRegistry,
    SystemSource,
    WeatherSource,
)

__all__ = [
    "BudgetTier",
    "BuildContext",
    "ContextBundle",
    "ContextItem",
    "ContextSource",
    "ContextBuilderProtocol",
    "ContextSourceProvider",
    "LegacyContextBuilder",
    "SourceRegistry",
    "MemorySource",
    "WeatherSource",
    "ConversationSource",
    "SystemSource",
    "ContextRanker",
    "ContextBudget",
    "ContextCache",
    "build_context_prompt",
    "bundle_to_dict",
    "dict_to_bundle",
    "bundle_to_json",
    "bundle_from_json",
]

# 从统一配置读取开关；配置不存在或导入失败时安全回退为 False。
try:  # pragma: no cover - 导入期容错
    import config

    FEATURE_CONTEXT_ENGINE: bool = getattr(config, "FEATURE_CONTEXT_ENGINE", False)
except Exception:  # pragma: no cover - 极端隔离失败场景
    FEATURE_CONTEXT_ENGINE = False
