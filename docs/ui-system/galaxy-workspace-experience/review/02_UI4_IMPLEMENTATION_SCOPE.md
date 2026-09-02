# 02 · UI-4 实现范围（UI-4 Implementation Scope）
### Xiao6 UI-3B · Galaxy × Workspace Experience Design v1.1 → UI-4 交接

> **阶段**：UI-3B v1.1 Refinement 已完成（Design Only）→ 本文定义 UI-4 实现范围
> **用途**：人工决策是否启动 UI-4 时的范围基线
> **生成日期**：2026-08-09

---

## 0. 前置条件（满足方可启动 UI-4）

- [x] UI-3B v1.0 六份 Blueprint 已落盘并 STOP。
- [x] UI-3B v1.1 四处文档增强已完成（03 §6/§7、04 §2.4/§13、01 §7）。
- [x] Review 三文档已落盘（`review/00`/`01`/`02`）。
- [x] 全部决策已冻结（`review/01_DESIGN_DECISIONS_FREEZE.md`）。
- [ ] 人工确认启动 UI-4（**当前未触发**，仍处 STOP）。

---

## 1. UI-4 目标

将 UI-3B v1.1 冻结的「Galaxy × Workspace 单一连续空间」体验，落地为可运行的前端表现层：
- 启动即见暗化银河世界层 + 工作台 + 永驻 Command Dock。
- 五大核心交互流端到端可用，无 surface 硬切换。
- 注意力预算与面板生命周期在运行时被强制约束。

---

## 2. In Scope（应实现项）

### 2.1 第一屏与布局（依据 03）
- 启动即呈现银河暗化世界层 + 前景玻璃操作台 + 永驻 Dock（验收 `03 §5`）。
- 首启渐进式披露（1s/5s/30s）；回流四要素（当前状态/任务/上下文/快捷）。
- 响应式：>980px 完整控制甲板；≤980px 单列重排，银河降为氛围但不消失。

### 2.2 Command Dock（依据 04 §2.2 / §2.4）
- 永驻所有 surface 底部（修正 S7）。
- 语义为 `# Global AI Intent Entry`：五模态统一为「意图→目标→执行」入口。
- 单输入语法：与银河受控交互共享命令语言与后端入口（修正 S3）。

### 2.3 五大交互流（依据 04 §2–§6）
- 输入任务 / 查看执行 / 查看状态 / 进入功能 / 返回空间，均经浮层叠加实现，无页面跳转。
- 进入功能 = `PanelManager.openCapability(id)` 浮层（修正 S2，废除 `#universeView` 独占）。

### 2.4 探索态切换（依据 04 §7）
- 连续亮度/透明度缓动（`--ease-premium`），非 `body` class 硬切。
- 触发控件待 UI-4 抉择（候选 A/B/C，推荐 B 或 A+B）。

### 2.5 Attention Budget 强制（依据 01 §7 / review 01 §5）
- 运行时约束：≤1 Primary + ≤2 Secondary；超预算对象强制 Dormant/Peripheral。
- 适用操作态与探索态。

### 2.6 Panel Lifecycle 状态机（依据 04 §13）
- PanelManager 内部实现 `Dormant → Attention → Active` 三态。
- 唯一入口 `openCapability(id)`；复用现有 OverlayManager（z 60-83/90/9000）。

### 2.7 AI Presence 同源（依据 03 §2.4 / 04 §3.2）
- HUD 状态点 + Companion 化身均从 `avatar-state.js` 单一派生，永不分裂。

---

## 3. Out of Scope（明确不做）

- ❌ **不**改动 `solar-system.js` 本体（渲染/状态语义维持）。
- ❌ **不**让 Galaxy 持有可写状态或写 AppState（DECISION_004）。
- ❌ **不**扩张事件合约（DOMAIN=71/SYSTEM=8 维持）。
- ❌ **不**新增 Runtime/Memory/Permission/Design System/Token 体系。
- ❌ **不**改动后端 `server.py`（纯前端表现层）。
- ❌ **不**实现 Galaxy 状态节点着色（Order 8，列为 Phase C 可选专项，非 UI-4 必交付）。
- ❌ **不**引入 Vision 控电脑、云同步、第二 Provider 切换 UI（属其他阶段）。
- ❌ **不**做 Electron / Mobile / Voice / Automation 外壳（属其他阶段）。

---

## 4. 实现约束（必须遵守）

1. **单入口分发**：所有面板经 `PanelManager.openCapability(id)`，不得新增独立 surface。
2. **受控银河**：银河任何交互经 `galaxy-experience.js`，不直接触 AppState。
3. **预算硬约束**：任何新控件上第一屏前，须先回收等量 Primary/Secondary 预算。
4. **连续性**：所有态过渡用 Motion Token 缓动，无硬切。
5. **红线校验**：每步自测 `04 §11` / `review/01 §8` 红线清单。

---

## 5. 验收标准映射

| 来源 | 验收点 | UI-4 验收方式 |
|---|---|---|
| `03 §5` | 启动即见银河+工作台+Dock 永驻+无模态遮挡+右栏收起 | 启动快照 + 交互探针 |
| `04 §12` | Dock 永驻/共享语法/执行常驻/面板浮层/ESC 返回/探索连续/AI Presence 同源 | E2E 流测试 |
| `01 §6` | 银河全态可见/指令后不消失/无需离开工作看银河/Dock 永驻/单入口/≤1 次发现 | 指标对照 |
| `01 §7` | 任一时刻 ≤1 Primary + ≤2 Secondary | 运行时预算探针 |
| `04 §13` | 面板三态 Dormant→Attention→Active 正确流转 | PanelManager 单测 |
| `03 §6/§7` | 首启渐进披露 / 回流四要素恢复 | 两类用户路径测试 |

---

## 6. 风险与开放问题

| 风险/问题 | 说明 | 处置 |
|---|---|---|
| 探索态触发控件未定 | A/B/C 候选待 UX 决策 | UI-4 启动前由人工拍板（推荐 B 或 A+B） |
| Galaxy 着色未做 | Order 8 属 Phase C 专项 | UI-4 不阻塞；状态节点保持占位色仍可成立 |
| 预算强制的边界 | 「Peripheral 不含密集控件」需明确像素/字数阈值 | UI-4 实现时定具体阈值，不突破语义 |
| 回流恢复持久化 | 「恢复到 Attention 态」需本地存上次面板态 | 复用现有 AppState 投影，不新增存储体系 |

---

## 7. STOP / Handoff

> **🛑 当前状态**：UI-3B v1.1 处于 Design Only + STOP。本文仅为 UI-4 范围基线。
> **下一步**：人工 Review 本 refinement → 决定是否启动 UI-4 → 若启动，以本文 `§2 In Scope` 为范围、`§3 Out of Scope` 为边界、`§5 验收` 为出口标准。
> **不**在本阶段进行任何 UI-4 代码实现。
