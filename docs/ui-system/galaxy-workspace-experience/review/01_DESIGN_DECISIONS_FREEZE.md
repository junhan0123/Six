# 01 · 设计决策冻结（Design Decisions Freeze）
### Xiao6 UI-3B · Galaxy × Workspace Experience Design v1.1

> **阶段**：Design Only（冻结，供 UI-4 实现遵循）
> **性质**：本文档所列决策均为**冻结态**，非实现临时方案
> **生成日期**：2026-08-09

---

## 0. 冻结声明

> **🔒 FROZEN**：以下决策自 UI-3B v1.0 + v1.1 起冻结。任何后续实现（UI-4 及以后）**不得推翻**，除非经治理流程（`AI_OPERATING_SYSTEM_GOVERNANCE.md`）显式复审并留痕。

所有决策均落在「表现层 + 设计约束」边界内，**不引入新的架构实体**（无新 Runtime/Memory/Permission/EventBus/Design System）。

---

## 1. 空间模型冻结（Dual-Layer Spatial Model / 方案 C）

- Xiao6 OS = **单一连续空间** = World Layer + Operation Layer，不是「A 页面 → B 页面」。
- 取消现状 home / chat-mode / universe-mode 三态硬切换（`#universeView` 独占视图废除）。
- 层与层之间只通过 **z 层叠加 + 亮度/透明度插值** 过渡，无 surface class 互斥。

---

## 2. 层定义冻结

### 2.1 World Layer（世界层）= Galaxy
- 位置：z 0–4。
- 角色：AI 世界的**表现层 + 受控交互层**。
- 约束（DECISION_004 / L0 红线-5）：
  - **绝不持有可写状态**；所有交互经 `galaxy-experience.js` 受控层。
  - **绝不改动 `solar-system.js` 本体**；状态→颜色映射属 Order 8 渲染层（Phase C 可选专项），不触碰 AppState 写入口。
  - GalaxyState 为只读投影（`pull()`），数据链正确但视觉着色不强制。

### 2.2 Operation Layer（操作层）= Workspace + Dock + Panels + AI Presence
- 位置：z 18+（HUD `--z-hud` 20；AI Presence `--z-companion` 9999 常驻最高层）。
- 角色：用户在 AI 世界中的工作台，统一主入口与功能浮层。

---

## 3. 注意力模型冻结（两档连续态）

| 态 | 触发 | World Layer | Operation Layer | 用途 |
|---|---|---|---|---|
| **操作态 Operate** | 默认 / 输入焦点 / 面板展开 | 暗化 ~30% 亮度 | 全亮、玻璃悬浮 | 日常指令、执行、阅读 |
| **探索态 Explore** | 聚焦银河手势 / 点星球 | 提亮 ~80% | 半透明退后（仍可交互） | 浏览状态世界、理解 AI 宇宙 |

- 两态间**连续缓动**（`--ease-premium`），无硬切闪烁。
- 探索态**不是**独立视图，仅世界层亮度 + 操作层透明度调节。
- 实现仅表现层：前景玻璃透明度/模糊 + 世界层遮罩亮度 + `body` 加 `explore-mode` 类；**不碰 solar-system.js**。

---

## 4. Command Dock 语义冻结（# Global AI Intent Entry）

> **🔒 FROZEN DEFINITION**：Command Dock = `# Global AI Intent Entry`（全局 AI 意图入口）。

- **不是** Chat Input（聊天框）、**不是** Search Box（搜索框）。
- **是** Intent → Goal → Execution 的统一入口：用户表达意图，系统解析为可执行目标并进入执行。
- 五模态（文本/语音/文件/截图/快捷）共享同一语义「我要让小6去做一件事」。
- 与银河受控交互共享同一命令语言与同一后端入口（单输入语法）。
- 永驻所有 surface 底部；探索态下半透明退后仍可达（不消失）。

---

## 5. Attention Budget Principle 冻结（注意力预算）

| 焦点等级 | 同时允许数量 | 典型承载 |
|---|---|---|
| **Primary Focus** | **1**（唯一） | 激活 Panel / 正在执行的任务 / 展开对话焦点 |
| **Secondary Focus** | **≤ 2** | Execution Timeline / 右栏上下文抽屉 / 至多两个唤起态 Panel |
| **Peripheral** | **无限** | Galaxy 暗化世界层 / HUD 状态点 / AI Presence Companion / Dock 待命 |

- Primary 唯一；升新 Primary 须先回收旧 Primary。
- Secondary 超 2 须降级为 Peripheral/Dormant。
- Peripheral 不限额，但每个元素须「存在即可、不需主动注意」（不含需阅读文字块/密集控件）。
- 预算在「操作态」与「探索态」下均生效。

---

## 6. Panel Lifecycle Model 冻结（面板生命周期）

| 态 | 视觉表现 | 用户触发 | 信息密度 |
|---|---|---|---|
| **Dormant** | 完全不可见，不占 z/注意力 | 系统默认态 | 0 |
| **Attention** | 半透明/缩略/标题态，占一个 Secondary | 点星球 / 快捷键 / Dock 快捷 / 右栏入口 | 中 |
| **Active** | 完全展开浮层（OverlayManager z 60-83/90/9000），占 Primary；银河退至暗化背景仍在场 | 从 Attention 进一步聚焦 | 高（受 1 Primary/≤2 Secondary 约束） |

- 主路径 `Dormant → Attention → Active`；关闭回 Dormant，可经 Attention 中转。
- 与 Attention Budget 联动（§5）；与探索态正交（可共存）。
- 唯一入口 = `PanelManager.openCapability(id)`（单分发器）。
- 三态为 PanelManager 内部状态机，不新增事件合约。

---

## 7. 首启 / 回流用户体验冻结

### 7.1 首启（First Launch）
- 渐进式披露，三段时间轴（1s/5s/30s，见 `01 §1`），**严禁一次性堆叠引导信息**。
- 核心纪律：用世界本身说话，不用引导层说话。
- 首启三十秒体验 = 回流日常操作流，不分裂。

### 7.2 回流（Returning User）
- 同一布局，重心从「世界感知」转向「当前上下文」。
- 四要素：当前状态 / 当前任务 / AI 上下文 / 快速操作（见 `03 §7`）。
- 恢复而非重置：可恢复到 Attention 态，但不自动跳 Active 抢 Primary。
- 永不弹首启 onboarding。

---

## 8. 红线（不可违反，违反即事故）

- 无第二 Runtime / Memory / EventBus / Permission / Design System / Token 体系。
- PolicyEngine 唯一权限；AppState 唯一状态写入口（必经 `applyEvent`→reducers）。
- 事件契约未扩张（DOMAIN=71/SYSTEM=8）。
- Local First（禁云同步/联网）；禁改 Galaxy 语义；禁 Vision 控电脑。
- 禁改 Planner/Workflow/Agent/Memory/LLM 固定架构。
- 禁新增 God Module。

---

## 9. 冻结范围与例外

- **冻结范围**：空间模型、层定义、注意力两态、Dock 语义、Attention Budget、Panel Lifecycle、首启/回流框架、红线。
- **未冻结（待 UI-4 抉择）**：探索态的具体触发控件（候选 A/B/C，见 `04 §7.2`）；银河状态节点着色（Order 8，Phase C 专项）。
- **所有例外均不突破本冻结的语义边界**，仅填补「表现层实现细节」。
