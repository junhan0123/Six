# INTERACTION_SYSTEM_SPEC — Design Canon（设计解释层）

> 性质：**设计解释层**，**不属于 L0/L1 权威层**。不覆盖/替代 Golden State / Decision / Governance。本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结规范 + 来源引用 + 权威映射（方案 1）。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **交互实现语料**：`docs/design/chat-window-final.md`（整窗收起 hover 展开）、`docs/design/chat-panel-overview.md`（🧠 画像侧栏）。
- **命令面板**：前端 `command-palette.js`（历史 memory：Ctrl/Cmd+K 瞬时能力）。
- **后端事件契约**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（DOMAIN=71 / SYSTEM=8 前后端逐字对齐）。
- **降级原则**：`docs/design/Xiao6-v2-Phase2-设计方案.md` §3.2 降级原则（单源失败不影响整体）。

## Related Documents（关联文档）
- `docs/design/chat-window-final.md` / `chat-panel-overview.md`
- `docs/design/frozen/GALAXY_INTERACTION_SPEC.md`
- `docs/design/frozen/DESIGN_SYSTEM_SPEC.md`（兄弟文档）
- `ARCHITECTURE_MAP.md`

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN**。
- 引用权威：前端交互为**已实现形态**；事件契约冻结于 Golden State（L0）。

## Scope（范围）
- 解释小6前端**交互系统**的通用模式与约定（hover 滑出、钉住、命令面板、状态驱动渲染）。
- 把分散的交互实现收敛为可引用的解释索引。

## Non-goals（非目标）
- **不创造新的交互范式**（用户约束 3）。
- 不重定义事件契约（权威在 Golden State / EventBus）。
- 不把实现细节提升为冻结规范。

## Design Interpretation（设计解释）

### 1. 通用交互模式（来自已实现前端）
| 模式 | 行为 | 来源 |
|---|---|---|
| 整窗收起 + hover 展开 | 聊天窗默认收起为底部细条，hover 升起；移开 0.8s 收回；图钉固定 | `chat-window-final.md` |
| 保护态 | 流式回复中 / 输入聚焦时绝不自动收起；新消息到达自动展开 | `chat-window-final.md` |
| 侧栏滑出 | 点击 rail chip → 侧栏平滑滑出；空态友好提示 | `chat-panel-overview.md` |
| 命令面板 | Ctrl/Cmd+K 唤起瞬时能力 | 前端 `command-palette.js` |
| 缓动曲线 | `0.5s cubic-bezier(.16,1,.3,1)`（高级感缓动） | `chat-window-final.md` |

### 2. 状态驱动渲染（来自架构）
- 前端渲染由 `AppState` 投影 + 系统事件（SYSTEM_EVENT_NAMES）驱动，非轮询业务状态。
- 任一数据来源（如 🧠 画像 API）失败 → 单源隔离、不阻断对话（v2 §3.2 降级原则）。

### 3. 权威映射
- 交互模式争议 → 以「已实现前端 + Golden State 状态唯一入口」为准；新交互不得让前端持有业务状态。
