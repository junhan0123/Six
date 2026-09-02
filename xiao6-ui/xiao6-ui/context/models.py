"""Context Engine 数据模型（P0）

定义上下文的来源、单项、完整集合与预算档位。
所有类型均为不可变值对象（frozen dataclass）或枚举，便于缓存与比较。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique

# COND-A3（GAP-X1 D3 / F-SRC-06）：补充源去重范围契约的规范键。
# 来源在 ContextItem.metadata 中以该键声明其注入内容的「知识域 scope」（如 "memory"）。
# Builder 在 Bundle 阶段对同一 scope 内的**重复事实**（逐字节一致的内容）做去重，
# 把「靠约定不重复」升级为「机器可校验的去重边界」，从设计上消除 F-SRC-06 重叠风险。
# 同域多来源（如 MemorySource / MemoryRecallSource / MemoryV2Source）声明同一 scope 即触发去重；
# 不同域（memory / identity / goal …）须保持 scope 不相交，避免误删。
DEDUP_SCOPE_KEY = "dedup_scope"


@unique
class ContextSource(Enum):
    """上下文来源枚举。LEGACY_DELEGATE 仅用于 Adapter 阶段的兼容兜底。"""

    IDENTITY = "identity"
    MEMORY = "memory"
    GOAL = "goal"
    WORLD = "world"
    WEATHER = "weather"
    SYSTEM = "system"
    USER = "user"
    EPISODIC = "episodic"
    PERSONALITY = "personality"
    WORKFLOW = "workflow"
    KNOWLEDGE = "knowledge"
    TOOL = "tool"
    CONVERSATION = "conversation"
    LEGACY_DELEGATE = "legacy_delegate"
    CURRENT_TASK = "current_task"
    MEMORY_V2 = "memory_v2"
    RUNTIME_STATE = "runtime_state"


@unique
class BudgetTier(Enum):
    """Token 预算档位，与 LLM 上下文窗口对齐。"""

    T16K = 16384
    T32K = 32768
    T64K = 65536
    T96K = 98304


@dataclass(frozen=True)
class ContextItem:
    """单个上下文片段。

    Attributes:
        source: 来源类型，决定排序与裁剪策略。
        content: 文本内容。
        priority: 重要性分数，范围 [-1.0, 1.0]；越高越难被裁剪。
        recency: 时效性分数，范围 [0.0, 1.0]；越高越新近。
        importance: 片段核心度，范围 [0.0, 1.0]；越高越核心。
        user_relevance: 与当前用户输入的相关度，范围 [0.0, 1.0]。
        token_est: 预估 token 数，用于预算计算。
        metadata: 来源相关的受限元数据（键值均为字符串，避免 Any 滥用）。
            来源须以 ``DEDUP_SCOPE_KEY``（"dedup_scope"）声明其注入内容的
            知识域 scope，供 Builder 在 Bundle 阶段做同域去重（COND-A3 / F-SRC-06）。
    """

    source: ContextSource
    content: str
    priority: float = 0.0
    recency: float = 0.0
    importance: float = 0.0
    user_relevance: float = 0.0
    token_est: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source, ContextSource):
            raise TypeError(f"source must be ContextSource, got {type(self.source)}")
        if not isinstance(self.content, str):
            raise TypeError(f"content must be str, got {type(self.content)}")
        if not -1.0 <= self.priority <= 1.0:
            raise ValueError(f"priority must be in [-1.0, 1.0], got {self.priority}")
        for field_name, value in (
            ("recency", self.recency),
            ("importance", self.importance),
            ("user_relevance", self.user_relevance),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be in [0.0, 1.0], got {value}")
        if self.token_est < 0:
            raise ValueError(f"token_est must be >= 0, got {self.token_est}")


def dedup_items_by_scope(items: list[ContextItem]) -> list[ContextItem]:
    """COND-A3（GAP-X1 D3 / F-SRC-06）：按 ``dedup_scope`` 契约去重。

    规则：
    - 未声明 scope（``metadata`` 不含 ``DEDUP_SCOPE_KEY``）的片段直接透传，行为不变；
    - 同一 scope 内，逐字节一致的内容只保留首次出现者（去除重复事实），
      不同内容各自保留（不误删异质事实）；
    - 顺序稳定：保留首次出现的相对次序。

    该契约把「各 Source 靠约定不重复」升级为「机器可校验的去重边界」，
    从设计上消除记忆多源（MemorySource / MemoryRecallSource / MemoryV2Source）
    对同一事实的重叠注入，且对默认单源路径零回归。
    """
    seen: dict[tuple[str, str], int] = {}
    out: list[ContextItem] = []
    for it in items:
        scope = it.metadata.get(DEDUP_SCOPE_KEY)
        if not scope:
            out.append(it)
            continue
        key = (scope, it.content)
        if key in seen:
            continue  # 同 scope 内重复事实，去重
        seen[key] = 1
        out.append(it)
    return out


@dataclass(frozen=True)
class ContextBundle:
    """Context Engine 最终输出的完整上下文集合。

    Attributes:
        prompt_text: 可直接送入 LLM 的 Prompt 文本。
        items: 组成该 Prompt 的上下文片段有序列表（元组保证不可变）。
        tier: 生成时使用的预算档位。
        total_tokens: 总预估 token 数。
        metadata: 生成过程的受限元数据。
    """

    prompt_text: str
    items: tuple[ContextItem, ...]
    tier: BudgetTier = BudgetTier.T32K
    total_tokens: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.prompt_text, str):
            raise TypeError(f"prompt_text must be str, got {type(self.prompt_text)}")
        if not isinstance(self.items, tuple):
            raise TypeError(f"items must be tuple, got {type(self.items)}")
        if not isinstance(self.tier, BudgetTier):
            raise TypeError(f"tier must be BudgetTier, got {type(self.tier)}")
        if self.total_tokens < 0:
            raise ValueError(f"total_tokens must be >= 0, got {self.total_tokens}")


@dataclass(frozen=True)
class BuildContext:
    """Builder 入参上下文。

    Attributes:
        user_text: 当前用户输入文本。
        tier: 本次请求的预算档位。
        extra: 扩展参数字典（如当前项目、会话 ID 等）。
    """

    user_text: str = ""
    tier: BudgetTier = BudgetTier.T32K
    extra: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.user_text, str):
            raise TypeError(f"user_text must be str, got {type(self.user_text)}")
        if not isinstance(self.tier, BudgetTier):
            raise TypeError(f"tier must be BudgetTier, got {type(self.tier)}")


@dataclass(frozen=True)
class ImportantDate:
    """重要日期（生日 / 纪念日 / 节日等），用于提前提醒（Phase 12 · P12-3）。"""

    date: str  # "2026-03-15"
    type: str  # birthday / anniversary / holiday / event
    description: str
    reminder_days: int = 3  # 提前几天提醒


@dataclass(frozen=True)
class ConversationMemory:
    """一次对话的沉淀摘要（Phase 12 · P12-3），让Xiao6「记得你上周说的事」。"""

    date: str  # "2026-08-02"
    topic: str  # 对话主题
    key_points: list[str]  # 关键要点
    sentiment: str = "neutral"  # positive / neutral / negative
