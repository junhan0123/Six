# 05 · Settings 演化：从 Legacy 页面到 AI OS Configuration Center

> **文档类型**：统一视觉架构设计 · Settings 演化层
> **阶段**：Unified Visual Architecture Design Phase v1.0 · 只设计，不实现 · **0 代码改动**
> **上游依据**：`00_DESIGN_PRINCIPLES.md` · `final-convergence/00_AUDIT.md`（F8 / §2 / §8）· `DESIGN.md` §4.3/§7 · `UI_SYSTEM_v1.0.md`
> **生成日期**：2026-08-09

---

## 0. 问题陈述

用户 7 大问题之五：「Settings 属旧时代 UI」。Final Convergence Audit 证据：
- Settings 全部为 Legacy `.settings-*` 类（styles.css 内聚），**未接入 `.zz-*` 正式原语**（§2 结论）。
- **F8**：`.settings-open-btn.active`(styles:2626) 用 `#061018` + `linear-gradient(...var(--cyan),var(--teal))`；`.settings-switch-slider` 未选中态(styles:2681) 用 `rgba(255,255,255,.12)` —— **硬编码色，主题切换时不跟随**。
- §6-3：Settings 整体为 Legacy 外观，`.settings-section-label` 用 `--font-mono` 而非面板标题语言（Orbitron），与 OS 其他 Surface 不同调。

**核心立场**：**演化，非重写**（Evolution, not Rewrite）。沿用 Minimal Convergence 已定原则「Legacy Surface 开始用统一 Design Language」，不推倒重做、不删功能、不新增功能。

---

## 1. 演化目标：AI OS Configuration Center

把 Settings 从一个「旧时代设置页」提升为**AI OS 的一等配置 Surface（Configuration Center）**：

- 它是 AI OS 的「系统设置」，与 Workspace / Galaxy 共享同一空间语法（玻璃 / 网格 / 深度 / glow / 动效）。
- 它是**可被命令面板搜索**的配置中心（`04` 功能发现矩阵中的 `Settings` 项）。
- 它是**本地优先 / 隐私优先**价值的集中体现（Provider 选择、Memory 边界、感知开关均在此透明呈现）。

---

## 2. 信息架构重分类（重组，非新增）

当前 Settings 按「能力 Tab」平铺（Provider / Media / Social / Search / Sandbox / Location / Data / Feature）。演化后按 **AI OS 心智**重分类为分组（仅重组顺序与命名，不新增设置项）：

| 新分组 | 含义 | 包含（现有项，重组） |
|---|---|---|
| **Identity & Agent** | 你的 AI 身份与状态 | 名称 / 头像 / Agent 状态展示偏好 |
| **Provider & Models** | 模型与计算渠道 | Provider(`settingsLlm*`) / 本地模型探测 |
| **Memory & Knowledge** | 记忆边界 | Memory 清理(`settingsClearSession*`) / 知识源 |
| **Capabilities & Permissions** | 能力闸门 | Sandbox(`settingsSandbox*`) / 工具权限 |
| **Privacy & Local-First** | 隐私与本地优先 | 感知开关 / 零密钥优先 / 数据落本地 |
| **Appearance & Presence** | 外观与在场 | 主题（9 主题）/ AI Presence 表现 |
| **Data & Maintenance** | 数据与维护 | Data(`settingsClearSession*`) / 导入导出 |

> 不新增任何设置项；仅把**已有 8 类 Tab**重组为 7 个 AI OS 语义分组，降低「这是旧软件设置页」的观感。

---

## 3. 视觉演化要求（消除 F8 + 统一语言）

| # | 演化项 | 当前（F8 / §6-3） | 目标（遵循 `03` 面板语言） |
|---|---|---|---|
| 1 | **接入正式原语** | 全部 `.settings-*` Legacy | 容器走 `.zz-panel`/`.os-panel` 玻璃语法；控件走 `.zz-input`/`.zz-toggle`/`.btn` |
| 2 | **移除硬编码色（F8）** | `#061018` / `rgba(255,255,255,.12)` / 裸 `linear-gradient` | 全部路由到 `--accent`/`--surface`/`--bg-2`/`--glow`/`--shadow-glow`，9 主题跟随 |
| 3 | **分区标题语言** | `.settings-section-label` 用 `--font-mono` | 统一为面板 H3 语言（`--font-display` 12px `.20em` uppercase，Orbitron） |
| 4 | **间距对齐** | 与系统面板不同调 | `.settings-panel`/`.settings-section`/`.settings-row` 对齐 `--panel-*` / `--space-3`(22px) |
| 5 | **Toggle 统一** | `.settings-switch` 双 markup | 维持 `ui2.css:1051` 别名到 `.zz-toggle`（不机械替换 markup，仅补 Disabled/Error 令牌） |
| 6 | **按钮统一** | `.settings-save-btn`/`.settings-row-btn` 各自样式 | 评估迁移到 `.btn`（保留尺寸差异，F5 修复方向） |

---

## 4. 容器形态演化（保持 right-drawer 结构）

- 保持现有 **right drawer 560px** 结构（不重写布局），但容器视觉升级为玻璃 + 统一深度（`--z-panel`(81)）。
- 遮罩 `.settings-overlay` 走 `--bg` 半透明 + `blur(26px)`（DESIGN.md §4.7）。
- 焦点治理：抽屉显隐须 `inert` / `visibility` 管理，消除当前 17 个焦点陷阱（UI_SYSTEM v1.0 §1.9）。

---

## 5. 与命令面板 / 导航的连接

- Settings 作为 `04` 功能发现矩阵的「Settings」项：rail ⚙ chip + 命令面板 `设置` 均可直达。
- Configuration Center 内分组可作为命令面板的可搜索节点（如「设置 → Privacy」），降低深层设置发现成本。

---

## 6. 演化纪律（红线）

- ❌ **不重写** Settings（Minimal Convergence 原则：Legacy Surface 开始用统一 Design Language，非推倒）。
- ❌ 不新增设置项 / 不删功能（Golden State「不推翻 34 项功能」）。
- ❌ 不改 Runtime / AppState / EventBus / Provider 后端逻辑。
- ✅ 仅做**视觉令牌化 + 分组重组 + 接入正式原语**，全部走既有 `--*` 令牌与 `zz-` 组件。
- ✅ 硬编码色（F8）必须清除，确保 9 主题一致。

---

## 7. 对齐声明

- 承接 Final Convergence F8 / §2 / §6-3，逐条转化为 §3 演化要求。
- 遵守 DESIGN.md §7 Don'ts（禁硬编码 rgba / 禁第二套 class / 禁改变视觉方向）。
- 遵守 Golden State「禁第二套 Token 体系」—— 只引用既有令牌，不新建。
- 与 `03` 面板语言、`04` 导航发现矩阵一致。

> **🛑 STOP 声明**：本章为纯 Settings 演化设计，0 代码改动，待 Review。
