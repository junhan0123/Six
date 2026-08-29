# Project Knowledge Graph

> 项目知识关联图 | 描述**知识之间的关联**（非系统结构；系统结构见 `ARCHITECTURE_MAP.md`）。
> 主轴：`Decision → Architecture → Module → Event → State → Memory → Test → Documentation`

## 关联主轴说明

每个节点向上挂接到 Decision（架构决策），向下串联到代码、事件、状态、测试与文档。任何新模块必须能挂到某条 Decision 之下，否则属「未决议」，须先走 Decision 流程。

## 节点关系示例

### DECISION_001_EVENTBUS（EventBus 单一来源）
- **Architecture**: 事件单一通信机制
- **Module**: `eventbus.py`（后端）/ `zz-events.js`（前端）
- **Event**: `DOMAIN_EVENT_NAMES` = 71 / `SYSTEM_EVENT_NAMES` = 8
- **Test**: `tests/phase6-order1.backend.test.py` + `phase6-order1.frontend.test.js`（契约对齐）
- **Documentation**: `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`、`docs/audits/ARCHITECTURE_DRIFT_CHECK.md`（Event Drift）

### DECISION_002_NO_SECOND_RUNTIME（无第二 Runtime）
- **Architecture**: 单一决策运行时
- **Module**: `agent_runtime.py`（唯一决策运行时）
- **Producers**: `capture_runtime.py` / `perception_runtime.py`（仅生产者，非决策）
- **Drift check**: `docs/audits/ARCHITECTURE_DRIFT_CHECK.md` → Runtime Drift

### DECISION_003_MEMORY_SINGLE_SOURCE（Memory 单一来源）
- **Module**: `memory.py`
- **State**: AppState 记忆投影（`state.memory`）
- **Drift check**: Memory Drift 段

### DECISION_004_GALAXY_BOUNDARY（Galaxy 边界）
- **Module**: `galaxy-state.js`（只读投影）
- **红线**: 银河本体视觉资产 100% 保留，语义不可改
- **Drift check**: State Drift / 永久禁止清单

### DECISION_005_PERMISSION_POLICY（Permission 唯一权限）
- **Module**: `permission_guard.py` / `policy_engine.py`
- **Runtime**: Executor 执行前必经校验
- **Drift check**: Policy Drift 段

### DECISION_006_LANGCHAIN_POSITION（LangChain 借鉴不引入）
- **范围**: Phase 9 可借鉴 Tool Registry / Chain / Memory 思想，禁止引入 LangChain / AnythingLLM 运行时
- **关联**: `capability_registry.py`（统一能力目录升级）

## 知识关联规则

1. 新模块 → 必须能挂到某 DECISION（否则先写 Decision）。
2. 事件变更 → 必须关联 `DOMAIN`/`SYSTEM` 契约 + 对应测试。
3. 文档与代码双向引用；`docs/DOCUMENT_INVENTORY.md` 为总索引。
4. 红线命中 → 关联 `AI_HANDOFF_PROTOCOL.md` 永久禁止清单 + Drift Check。

## 检索入口

- 文档索引: `docs/DOCUMENT_INVENTORY.md`
- 架构决策: `docs/decisions/`（DECISION_001..006 + AI_CHANGE_REVIEW_TEMPLATE）
- 系统结构: `ARCHITECTURE_MAP.md`
- 黄金基线: `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`
- 漂移检测: `docs/audits/ARCHITECTURE_DRIFT_CHECK.md`
- 入职自测: `docs/reference/AI_ONBOARDING_TEST.md`
