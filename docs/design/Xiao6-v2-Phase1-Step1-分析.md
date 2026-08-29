# Xiao6 v2 · Phase 1 · Step 1 实施分析（修订版 · 对齐最终 Master Implementation Prompt）

> **修订说明**：本文件依据《Xiao6 v2 实施总 Prompt（最终版）》修订。相对初版三处合规修正：
> 1. Feature Flag 命名 `CONTEXT_ENGINE_ENABLED` → **`FEATURE_CONTEXT_ENGINE`**（禁止 `XXX_ENABLED` 零散命名）。
> 2. 目录由单文件 `context_engine.py`（未来 God File）→ **`context/` 包目录**（符合目录规则）。
> 3. 分析项 10 → **12**（新增 ⑫ 是否符合 Architecture Constitution）；明确 P0 数据模型+接口优先，Builder（P1）拆到 Step 2。
>
> 本文件为 **Stage A 分析 + Stage B 设计**产出，**仅分析/设计，不含任何项目代码修改**。待 Stage C 批准后再进入 D 实现。

---

## Stage A · Analysis（12 项）

### ① 当前目标
在 `context/` 包内建立 Context Engine 的**数据模型与接口骨架（P0）**：
- 定义 `ContextSource` / `ContextItem` / `BuiltContext` dataclass；
- 定义 `ContextSourceType` / `BudgetTier` Enum；
- 声明 `ContextSourceProtocol` / `ContextRanker` / `ContextBudget` / `ContextSerializer` / `ContextCache` Protocol。

**零业务逻辑、零行为变化、Feature Flag 默认关闭。**

### ② 为什么现在做
- P0 是 Context 第一优先级；数据模型+接口是后续所有迁移（P1 Builder 委托、排序、裁剪、缓存）的**唯一挂载点**。
- 先立类型地基，未来五年无需推翻；严格符合"数据模型优先、接口优先、实现最后"。
- 本步无运行时副作用，是风险最低、价值最高的起点。

### ③ 当前代码分析
现有 System Prompt 生成路径（前期《Phase 1 实施分析》已核实真实代码）：
- `memory.build_system_prompt` / `build_context_prefix` / `build_memory_block`
- `server._handle_chat` 内 `personalization.summary()` 追加个性化画像
- `weather._LAST` 全局变异注入天气摘要（全局耦合，待 World Model 消除）

本步**不触碰**上述任何函数，仅定义"未来将被 Context Engine 接管"的**类型契约**。

### ④ 影响范围
仅新增 `context/` 包与对应测试；`config.py` 增加一行 Flag；不触发任何运行时路径变化（Flag 关）。

### ⑤ 修改文件
`config.py`：+1 行 `FEATURE_CONTEXT_ENGINE: bool = False`。**仅 1 个已有文件，≤3。**

### ⑥ 新增文件
`context/__init__.py`、`context/models.py`、`tests/test_context_models.py`。**共 3 个，≤5。** 新增代码预计 ≤150 行（远低于 500）。

### ⑦ 不修改哪些文件
`server.py` / `memory.py` / `tools.py` / `llm.py` / `weather.py` / `geo_weather.py` / `hotspots.py` / `personalization.py` / `prefetch.py` **全部不动**；**数据库零改动**；现有 API 零改动；现有 Prompt 路径零改动。

### ⑧ 风险
极低。纯类型定义无运行时副作用；Flag 默认关；无循环依赖（`context` 仅依赖 `config` 与标准库）。

### ⑨ Rollback
- 新增 3 文件整体删除；
- `config.py` 1 行 revert；
- 无 DB 迁移、无数据风险；
- 单笔 commit `git revert` 即时回退。

### ⑩ 测试方案
`tests/test_context_models.py`：
- **一致性**：dataclass 字段齐全、`ContextSourceType` / `BudgetTier` 枚举值完整。
- **异常**：构造非法 `BudgetTier` / 负 `priority` 应被拒绝或归一化。
- **回归**：`FEATURE_CONTEXT_ENGINE is False`（默认关闭，确保零行为影响）。
- **A/B**：本步无输出物，A/B 在 Step 2（Builder 委托）执行；此处仅校验模型可实例化且 Flag 状态正确。

### ⑪ 验收标准
1. `py_compile` + `pytest` 通过；
2. Flag 默认关，聊天行为逐字节不变；
3. 无 God File（已用包目录）、无循环依赖；
4. 单笔小步提交，commit message 带 `feat(context):` 前缀，可独立 `git revert`。

### ⑫ 是否符合 Architecture Constitution
**是，无冲突。** 对照宪法铁律：
- 禁止 God Module → 改用品目录，单一职责；
- EventBus 是唯一模块通信方式 → 本步无跨模块调用，仅定义类型；
- Context 必须由 Context Engine 生成 → 类型即为未来 Context Engine 而生；
- 所有升级必须向后兼容 → Flag 关无影响；
- 所有新模块必须可独立测试 → 有 `test_context_models.py`。

---

## Stage B · Design（数据模型 + 接口契约，仅规格描述，不落地代码）

### 目录结构
```
xiao6-ui/
├── context/                  # Context Engine 包（P0 起逐步填充）
│   ├── __init__.py           # 重导出类型 + 读取 FEATURE_CONTEXT_ENGINE
│   └── models.py             # P0：数据模型 + 接口（本协议步仅此文件含类型）
├── config.py                 # + FEATURE_CONTEXT_ENGINE = False
└── tests/
    └── test_context_models.py
```

### 数据模型（`context/models.py` 规格）
- `class ContextSourceType(Enum)`：`IDENTITY, MEMORY, GOAL, WORLD, USER, WORKFLOW, KNOWLEDGE, TOOL, CONVERSATION, LEGACY_DELEGATE`
- `class BudgetTier(Enum)`：`T16K, T32K, T64K, T96K`（对应 16/32/64/96K Token 预算）
- `@dataclass class ContextItem`：`source: ContextSourceType; priority: float; content: str; token_est: int; metadata: dict[str, str]`（metadata 用受限 `dict[str, str]`，避免 `Any` 滥用；确需结构化时改 `TypedDict`）
- `@dataclass class BuiltContext`：`tier: BudgetTier; items: list[ContextItem]; prompt_text: str; total_tokens: int`
- `@dataclass class BuildContext`：`user_text: str; tier: BudgetTier; extra: dict[str, str]`（Builder 入参，供未来 source 采集使用）

### 接口契约（Protocol，本步仅声明签名，无实现）
- `class ContextSourceProtocol(Protocol)`：`def collect(self, ctx: BuildContext) -> list[ContextItem]: ...`
- `class ContextRanker(Protocol)`：`def rank(self, items: list[ContextItem]) -> list[ContextItem]: ...`
- `class ContextBudget(Protocol)`：`def fit(self, items: list[ContextItem], tier: BudgetTier) -> list[ContextItem]: ...`
- `class ContextSerializer(Protocol)`：`def serialize(self, items: list[ContextItem]) -> str: ...`
- `class ContextCache(Protocol)`：`def get(self, key: str) -> BuiltContext | None: ...`；`def set(self, key: str, value: BuiltContext, ttl: int) -> None: ...`

### Feature Flag
统一置于 `config.py`：`FEATURE_CONTEXT_ENGINE: bool = False`。`context/__init__.py` 仅读取，不在别处散落开关（符合"禁止 XXX_ENABLED / YYY_SWITCH 零散命名"）。

---

## 后续子步骤（仅规划，本轮不实现）
- **Step 2（P1 Builder + 适配器 + A/B）**：新增 `context/builder.py`（`ContextBuilder` 委托 `memory.build_system_prompt`，输出逐字节一致）+ `context/sources.py` 空注册表骨架；Flag 开启时走 Builder，关闭时等价原路径；A/B 单测比对。
- **Step 3（P2 排序/预算接口落地）**：`context/ranker.py` + `context/budget.py` 默认"透传/不裁剪"，保持等价。
- **Step 4（序列化/缓存）**：`context/serializer.py` + `context/cache.py`。
- **Step 5（切主路径）**：`FEATURE_CONTEXT_ENGINE` 默认开启，保留原实现可瞬切回。

每一步重复 12 项分析并**等待 Stage C 批准**。
