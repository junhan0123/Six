# DESIGN_SYSTEM_SPEC — Design Canon（设计解释层）

> 性质：**设计解释层**，**不属于 L0/L1 权威层**。不覆盖/替代 Golden State / Decision / Governance。本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结规范 + 来源引用 + 权威映射（方案 1）。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **视觉令牌实现语料**：`docs/design/chat-panel-overview.md`（「沿用 `--cyan`/`--teal`/`--txt` token 与玻璃拟态」）、`docs/design/chat-window-final.md`（缓动 `cubic-bezier(.16,1,.3,1)`）。
- **实现文件**：前端 `xiao6-ui/styles.css`（令牌与玻璃拟态样式的**实际定义处**）。
- **设计系统意图**：历史 memory 记录「Phase 4 Design System 冻结」为设计意图，但**无落盘冻结文件**（GOVERNANCE_AUTHORITY_HIERARCHY 已确认设计层零命中）。

## Related Documents（关联文档）
- `docs/design/chat-panel-overview.md` / `chat-window-final.md`
- `xiao6-ui/styles.css`（实现令牌源）
- `docs/design/frozen/INTERACTION_SYSTEM_SPEC.md`（兄弟文档）
- `docs/audits/GOVERNANCE_AUTHORITY_HIERARCHY.md`（设计层零命中声明）

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN（解释层）**。
- **重要**：正式的「设计系统令牌规范」**尚未冻结**（无落盘文件）。本文件仅索引现有实现令牌，不进行令牌重定义。

## Scope（范围）
- 索引小6前端**实际使用的视觉令牌与表现手法**（玻璃拟态、青绿/teal 文本 token、缓动曲线）。
- 提供「视觉风格 → 实现文件（styles.css）」的可追溯映射。

## Non-goals（非目标）
- **不创造新的设计令牌或新视觉语言**（用户约束 3）。
- 不重定义 `styles.css` 中的令牌值（权威在实现文件）。
- 不把未冻结的「Phase 4 Design System」提升为规范。

## Design Interpretation（设计解释）

### 1. 已观察的实现令牌（来自前端文档，定义于 styles.css）
| 类别 | 观察值（索引） | 来源 |
|---|---|---|
| 色彩 token | `--cyan` / `--teal` / `--txt`（青绿/teal/文本，暗色基底） | `chat-panel-overview.md` |
| 材质 | 玻璃拟态（`.zz-panel-*` / `.chat-panel*` 半透明 + 模糊） | `chat-panel-overview.md` / `chat-window-final.md` |
| 缓动 | `cubic-bezier(.16,1,.3,1)`（0.5s 面板展开） | `chat-window-final.md` |
| 触发条 | 极淡青色细线（`chat-trigger`） | `chat-window-final.md` |

### 2. 正式令牌规范状态
- 确切 hex 值与完整令牌表存在于实现文件 `xiao6-ui/styles.css`，**本文件不复制**。
- 若需冻结正式 Design System，须由主理人发起、经 `GOVERNANCE_CHANGE_CONTROL.md`，从 styles.css 提炼为独立规范——非本解释层职责。

### 3. 权威映射
- 视觉风格争议 → 以 `styles.css` 实际令牌为主；本文件仅解释与索引。
