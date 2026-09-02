# 小6 AI OS 2.0 — Phase A 任务五：Capability Registry（CAPABILITY_REGISTRY_REPORT）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务五（Capability Registry）→ 输出本报告
> 上游: `CORE_AUDIT.md`（发现 F2 直接驱动）、ADR-007（统一 Extension）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：按 ADR-007（统一 Extension），把小6**分散的能力/工具声明收敛为单一 Capability Registry**，消除审计 F2 的双注册表碎片化。

**现状（F2）**：
- **注册表 A** `capabilities.py`：上下文增强型（`hotspot`/`prefetch`），`build_context` 注入系统上下文，无风险/权限语义。
- **注册表 B** `capability_registry.py`：电脑能力（`read_file`…`delete`…），含 `risk∈{LOW,MEDIUM,HIGH,CRITICAL}` → Policy 层级映射，复用 `policy_engine.AUTO/CONFIRM`。
- **隐含第三处** `tools.TOOL_FUNCS` / `tools.READONLY_TOOLS`：实际可执行工具函数表，与上述两套 ID 空间无统一约束。

**设计方针**：单一元模型 + 单一注册表 + 旧模块作适配器（增量演进，不破坏性迁移）。

---

## 2. 统一元模型（Unified Capability）

```python
@dataclass(frozen=True)
class Capability:
    id: str                      # 全局唯一（跨 kind 不撞名）
    label: str
    kind: CapabilityKind         # CONTEXT_ENHANCEMENT | COMPUTER_ACTION | TOOL
    risk: RiskTier               # LOW | MEDIUM | HIGH | CRITICAL
    group: str = "其他"
    description: str = ""
    triggers: tuple[str, ...] = ()
    implemented: bool = True
    # 行为钩子（按 kind 选填，不持有执行逻辑本体）
    build_context: Optional[Callable] = None   # kind=CONTEXT_ENHANCEMENT
    execute: Optional[Callable] = None         # kind=COMPUTER_ACTION | TOOL（委托 guard/tools）
```

- `CapabilityKind`：`CONTEXT_ENHANCEMENT`(A) / `COMPUTER_ACTION`(B) / `TOOL`(tools)。
- `RiskTier` → Policy 层级：`RISK_TO_TIER = {LOW:AUTO, MEDIUM:CONFIRM, HIGH:NEVER, CRITICAL:NEVER}`（复用 `policy_engine` 词汇，零新增权限逻辑，符合 ADR-001）。

---

## 3. 架构：Catalog 单例 + 适配器

```
            ┌──────────────────────────────────────┐
            │   CapabilityRegistry（唯一目录）        │  ai_core/capability_catalog.py
            │   register / get / all / by_kind /    │
            │   risk_of / tier_of / is_implemented  │
            └───────────────┬──────────────────────┘
                ▲      ▲      ▲
      适配器注册 │      │      │ 适配器注册
                │      │      │
   ┌────────────┴─┐ ┌──┴───────────┐ ┌──────────────┴──────┐
   │ capabilities  │ │capability_   │ │ tools.TOOL_FUNCS    │
   │ .py (A)       │ │registry.py(B)│ │ (可执行工具)         │
   │ 迁移为适配器  │ │ 迁移为适配器  │ │ 启动时登记 kind=TOOL │
   └──────────────┘ └──────────────┘ └─────────────────────┘
```

- **`ai_core/capability_catalog.py`**：唯一真相源。进程级单例 `capability_catalog`。
- **A/B 适配器**：`capabilities.py` / `capability_registry.py` 保留对外 API（`active_capability_blocks`、`get_capability`、`risk_of` 等），但实现改为"从 catalog 取数据 / 启动时把自身条目 `register` 进 catalog"。旧调用方零改动。
- **TOOL 登记**：启动时把 `tools.TOOL_FUNCS` 条目以 `kind=TOOL` 登记进 catalog（仅元数据，执行仍走 `tools.execute_tool`）。

---

## 4. 关键 API（统一）

```python
capability_catalog.register(cap)                 # 注册（含 ID 唯一校验）
capability_catalog.get(cap_id) -> Capability|None
capability_catalog.all() -> list[Capability]
capability_catalog.by_kind(kind) -> list[Capability]
capability_catalog.risk_of(cap_id) -> RiskTier
capability_catalog.tier_of(cap_id) -> str         # AUTO/CONFIRM/NEVER（委托 PolicyEngine）
capability_catalog.is_implemented(cap_id) -> bool
capability_catalog.context_blocks(user_text) -> list[str]   # 汇集 CONTEXT_ENHANCEMENT 的 build_context
```

- `context_blocks` 替代原 `capabilities.active_capability_blocks`（任务三 `CapabilitySource` 直接调它）。
- `tier_of` 复用 `RISK_TO_TIER`，HIGH/CRITICAL 默认 `NEVER`（与 `capability_registry.py:53-64` 占位一致）。

---

## 5. 迁移策略（增量演进）

1. 新增 `ai_core/capability_catalog.py`（Catalog + 元模型）。
2. `capability_registry.py`：其 `_CAPABILITIES` 改为"构造 `Capability(kind=COMPUTER_ACTION)` 并 `register` 进 catalog"；对外函数改从 catalog 读取。
3. `capabilities.py`：其 `_register` 改为"构造 `Capability(kind=CONTEXT_ENHANCEMENT, build_context=…)` 并 `register`"；`active_capability_blocks` 委托 `catalog.context_blocks`。
4. `tools` 启动钩子：登记 `TOOL_FUNCS` 为 `kind=TOOL`（仅元数据）。
5. **不改**任何既有调用 `get_capability`/`risk_of`/`active_capability_blocks` 的代码（适配器保兼容）。

---

## 6. 红线合规

| 红线 | 合规性 | 说明 |
|------|--------|------|
| 单 Runtime | ✅ | Catalog 单例同进程 |
| 单 Permission | ✅ | 风险→层级全委托 `policy_engine`，零新增权限逻辑 |
| ADR-007 统一 Extension | ✅ | 单一 Registry 收敛 MCP/Tool/Connector/Plugin 雏形 |
| No God Module | ✅ | Catalog 只存元数据+路由，不含执行/编排 |
| 增量演进 | ✅ | 旧模块作适配器，调用方零改动 |
| 单 EventBus | ✅（无关） | Registry 不发射事件 |

---

## 7. 实现清单

1. 新增 `ai_core/capability_catalog.py`（元模型 + Catalog 单例 + API）。
2. 改造 `capability_registry.py` → 适配器（register 进 catalog）。
3. 改造 `capabilities.py` → 适配器（`context_blocks` 委托 catalog）。
4. `tools` 启动登记 `kind=TOOL`。
5. 单测：ID 唯一校验、跨 kind 撞名检测、风险→层级映射、适配器兼容旧 API。

**本任务为设计交付；代码落地待 Phase A 实现阶段（经 Review 批准）。**

**STOP**：任务五设计完成。待 Review 批准后进入任务六（Health Check）。未经批不得修改代码、不得扩大范围。
