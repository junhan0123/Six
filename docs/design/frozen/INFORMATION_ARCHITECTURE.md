# INFORMATION_ARCHITECTURE — Design Canon（设计解释层）

> 性质：**设计解释层**，**不属于 L0/L1 权威层**。不覆盖/替代 Golden State / Decision / Governance。本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结规范 + 来源引用 + 权威映射（方案 1）。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **L0 架构**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` §冻结状态总览（AppState 唯一写入口 + 4 只读投影）。
- **架构地图**：`ARCHITECTURE_MAP.md`（模块职责 / 数据流 / 红线速查）。
- **IA 实现语料**：`docs/design/chat-panel-overview.md`、`docs/design/chat-window-final.md`、`docs/design/Xiao6-v2-架构升级设计文档.md` §1.5 前端架构。
- **Galaxy 边界**：`docs/decisions/DECISION_004_GALAXY_BOUNDARY.md`。

## Related Documents（关联文档）
- `ARCHITECTURE_MAP.md`
- `docs/design/chat-panel-overview.md` / `chat-window-final.md`
- `docs/frozen/Xiao6-v2-架构升级设计文档.md`
- `docs/decisions/DECISION_004_GALAXY_BOUNDARY.md`
- `docs/design/frozen/GALAXY_INTERACTION_SPEC.md`（兄弟文档）

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN**。
- 引用权威：AppState 单一写入口 FROZEN（L0）；前端 IA 为**已实现形态**（前端文件），非独立冻结规范。

## Scope（范围）
- 解释小6前端「信息架构」：常驻能力、瞬时能力、状态可视化、对话入口四者的共生关系与布局约定。
- 映射「前端面板 ↔ 后端状态/事件」的来源依据。

## Non-goals（非目标）
- **不创造新的 IA 方向**（用户约束 3）。
- 不重定义 AppState 子树（权威在 Golden State / ARCHITECTURE_MAP）。
- 不把前端实现细节提升为冻结规范（仅索引现有实现）。

## Design Interpretation（设计解释）

### 1. 三支柱导航共生（来自前端实现 + Galaxy 决策，非二选一）
| 支柱 | 角色 | 来源 |
|---|---|---|
| 左栏（rail chip-row） | 常驻能力入口（如「🧠 画像」chip） | `chat-panel-overview.md` §Phase2 |
| 命令面板（Ctrl/Cmd+K） | 瞬时能力（历史 memory 记录 `command-palette.js`） | 前端 `command-palette.js` |
| 银河（Galaxy 背景） | 状态可视化（太阳=核心、轨道=Goal、星球=能力域） | `DECISION_004` |

### 2. 聊天入口定位（关键澄清）
- 聊天**仅是左栏/面板平级入口之一**，不独占中央区（来自 Galaxy 决策「聊天只是平级入口」）。
- 当前实现：聊天窗口默认收起为底部细触发条「💬 对话」，hover/钉住展开（`chat-window-final.md`）。
- 这是 Agent UI 阶段的**正确态**，非「前端像聊天软件」的偏差。

### 3. 状态映射（前端只读投影来源）
- 所有面板数据经 `AppState` 唯一写入口 → 只读投影层（GalaxyState / OverlayRuntime / ComputerState / PerceptionState）。
- 前端不得持有业务状态（Golden State 红线 + DECISION_004）。

### 4. 权威映射
- IA 争议（如「聊天是否应独占中央」）→ 以 `DECISION_004` + Golden State「AppState 唯一写入口」为准。
