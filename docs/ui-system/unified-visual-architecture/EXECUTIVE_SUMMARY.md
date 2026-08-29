# Xiao6 AI OS Visual Blueprint v1.0 · 最终报告（Executive Summary）

> **文档类型**：统一视觉架构设计 · 总报告（Master Report）
> **阶段**：Unified Visual Architecture Design Phase v1.0 · **只设计，不实现**
> **代码改动**：**0**（未修改任何 CSS / HTML / JS / 后端 / Galaxy / Runtime / AppState / EventBus）
> **生成日期**：2026-08-09
> **本阶段纪律**：完成后 **STOP**，不提交 Git，不进入 Visual Redesign，等待人工 Review。
> **配套文档**：`00_DESIGN_PRINCIPLES` · `01_GLOBAL_LAYOUT_ARCHITECTURE` · `02_GALAXY_WORKSPACE_INTEGRATION` · `03_PANEL_VISUAL_LANGUAGE` · `04_ENTRY_AND_NAVIGATION` · `05_SETTINGS_EVOLUTION` · `06_DESIGN_SYSTEM_NEXT_STAGE`（均位于 `docs/ui-system/unified-visual-architecture/`）。

---

## 1. Executive Summary（执行摘要）

小6是**本地个人 AI 操作系统**（Local Personal AI Operating System v1.0，冻结于 Golden State），不是聊天软件。本轮 **Unified Visual Architecture Design** 在不触碰任何代码、不违反任何架构红线的前提下，形成了 **Xiao6 AI OS Visual Blueprint v1.0**——下一阶段 Visual Redesign 的**唯一设计依据**。

蓝图的核心主张：**把小6从「一个聊天界面」重新定义为「一个可进入的 AI 控制空间（AI Control Space）」**。通过 7 份分册，我们解决了当前 7 大产品问题的根因，并给出可落地的融合方案、面板语言、导航重设计、Settings 演化路径与设计系统下一阶段补完方向。

所有方案均严格限定在 **「表现层 + 受控交互层」** 内：
- Galaxy 永远**只读投影、零可写状态、不改 `solar-system.js` 本体**（DECISION_004 + L0 红线-5）。
- 令牌体系只「激活 + 归类 + 补齐」，**不重建第二套 Token**（Golden State 红线）。
- 聊天仅为**平级入口**，不独占中央（INFORMATION_ARCHITECTURE）。

---

## 2. Current Problems（当前问题）

用户提出的 7 大核心问题，及其根因（来自真实读盘与 Final Convergence Audit）：

| # | 问题 | 根因（证据） |
|---|---|---|
| 1 | 主界面视觉普通 | 缺乏统一空间语法；Galaxy 被当背景，Workspace 孤立 |
| 2 | 太阳系 Galaxy 与主界面割裂 | Galaxy=背景图、Workspace=另一界面，二者语法不同、互不连通 |
| 3 | AI OS 世界观未形成 | 无「进入空间」的心智；聊天框主导认知 |
| 4 | 功能入口分散 | Memory/Tasks/Goals/Search/Tools/Settings/Agent 分散，发现成本高 |
| 5 | Settings 属旧时代 UI | 全 Legacy `.settings-*`、硬编码色（F8）、未接 `zz-*` 原语 |
| 6 | 面板系统缺统一空间语言 | 缺 `.zz-input`（F1）、`.zz-panel` 位置矛盾（F3）、领域面板本地 CSS（F7） |
| 7 | 科技感/高级感不足 | 玻璃/网格/动效未系统化；状态四态缺失（UI_SYSTEM v1.0 §1.7：hover 152 vs focus-visible 12） |

---

## 3. Design Direction（设计方向）

以 5 条哲学统领（详见 `00` §3）：
1. **空间即操作系统**——整个屏幕是 AI 的认知空间。
2. **银河为常驻世界，非背景图**——状态活体可视化。
3. **玻璃拟态的精密秩序**——深空 + 毛玻璃 + 网格 + 宽字距。
4. **克制而明确的动效**——动效是注意力与状态的语言。
5. **意识核心可见**——AI Presence 显式呈现在场/思考/计划/执行。

核心视觉关键词：深空 · 玻璃拟态 · 精密 · 冷静 · 未来主义 · 控制甲板（Command Deck）· 认知宇宙 · 可进入的空间。

---

## 4. Architecture Proposal（架构提案）

采用 **单一连续空间模型（Single Continuous Space）**（详见 `01`）：
- **世界层（World Layer）= Galaxy**（z 0–4，常驻暗化）。
- **操作层（Operation Layer）= Workspace + Command Dock + Panels + AI Presence**（z 18+，玻璃元件）。
- 二者**共享同一空间语法**（depth / glass / grid / glow / motion），由**注意力模型**调节显隐（非硬切模式）。
- 七大 Surface（Galaxy / Workspace / Command Dock / Panel / Settings / Overlay / AI Presence）按 `--z-*` 语义档共存，互不冲突。
- **第一分钟体验**：抵达（进入 AI 空间，无遮挡）→ 定向（rail + 银河在场）→ 行动（Command Dock 主入口）→ 探索（银河点击/命令面板发现）——世界观在 60 秒内成立。

---

## 5. Galaxy Integration Decision（Galaxy 融合决策）

对 4 个候选方案比较（详见 `02`）：
- **A Galaxy-Dominant**：中央争夺，诱导越界 → 不推荐。
- **B Embedded-in-3D**：要求 Galaxy 渲染 UI，违反 DECISION_004 → **否决**。
- **C Dual-Layer Spatial（世界层/操作层）** → **⭐ 推荐**。
- **D Mode-Toggle**：强化割裂，违背世界观 → 不推荐。

**推荐 C**：银河作为常驻世界层（暗化在场），Workspace 作为前景操作层，共享语法；用**注意力模型**调节银河显隐（操作态 ~30% / 探索态 ~80%，连续缓动）。银河交互（点击行星→能力面板、拖轨道→Goal、工具光点流转、流星推送）**全经 `galaxy-overlay`**，零可写状态、不改本体、完全满足 DECISION_004。

---

## 6. Workspace Decision（Workspace 决策）

- Workspace 是**操作层主体**，不独占为聊天框（采纳 INFORMATION_ARCHITECTURE「聊天平级入口」）。
- 继承 `.os-shell` 三区结构（56px HUD / 1fr 380px / 188px 侧栏 / 底部时间线+Dock），**不改布局代码**，只在空间语义上强化为「控制甲板」。
- 默认「操作态」：银河暗化常驻其后，消除割裂感；用户可经注意力机制进入「探索态」聚焦银河。
- 面板、Command Dock、Execution Timeline 是其Foreground 元件，统一走 `03` 面板语言。

---

## 7. Panel System Decision（面板系统决策）

确立**统一面板视觉语言**（详见 `03`，规则非 CSS）：
- 五原则：统一容器语法保留领域个性 / 层级靠透明度与 blur / 深度 ladder 单一令牌 / 状态四态强制 / 密度靠网格不靠压缩留白。
- depth ladder（`--z-*`）、三档阴影（`--elev-*` 含内高光）、玻璃材质（blur 26 + 1px border + 内高光）、边框与 glow（克制，仅 Presence/激活/品牌）、动效（`--ease-premium` + 降级）、排版角色、状态契约（hover/focus-visible/disabled/loading/error **强制**，修复键盘「失明」）。
- 领域面板保留内容个性，但容器统一消费 `--surface`/`--radius`/`--ease-*`/`--panel-*` 令牌（修复 F7）。

---

## 8. Navigation Decision（导航决策）

基于 **三支柱共生模型**重设计入口（详见 `04`）：
- **左栏 rail**：统一「能力导航 rail」（Memory/Goals/Tasks/Search/Tools/Settings/Agent），图标+标签，点击滑出面板。
- **命令面板（Ctrl/Cmd+K）**：定义为「统一能力目录」，模糊搜索跨一切功能，发现成本=一次搜索。
- **银河**：点击行星/轨道/太阳/记忆环即导航到对应能力/状态面板。
- **Command Dock**：定位为「主行动入口」**非聊天框**，配 micro-hint 引导「操作系统」心智。
- 功能发现矩阵：每项功能≥2 条发现路径（常驻+搜索），核心状态另有银河路径。

---

## 9. Settings Evolution（Settings 演化）

**演化，非重写**（详见 `05`）：
- 目标：从 Legacy 页面 → **AI OS Configuration Center**（一等配置 Surface，可被命令面板搜索，集中体现本地优先/隐私优先）。
- 信息架构重分类为 7 个 AI OS 语义分组（Identity&Agent / Provider&Models / Memory&Knowledge / Capabilities&Permissions / Privacy&Local-First / Appearance&Presence / Data&Maintenance）——仅重组，不新增设置项。
- 视觉演化：接入 `zz-*` 原语、清除硬编码色（F8）、分区标题统一为面板语言、间距对齐 `--panel-*`、Toggle 维持别名、按钮评估迁移 `.btn`。
- 纪律：不重写、不删功能、不改后端；只做视觉令牌化+分组重组+接入正式原语。

---

## 10. Next Implementation Roadmap（下一阶段实施路线图）

> 以下为 **Visual Redesign 阶段的建议执行序**，不在本设计阶段执行。每项须先有设计令牌/契约落地，再写代码；严守 Golden State 红线与 DESIGN.md Don'ts。

| 阶段 | 主题 | 关键动作 | 对应文档 |
|---|---|---|---|
| **R1** | 令牌激活 | 激活死 `--fs-*`(504 处字号) / `--sp-*`(18 档间距)；固化 `--presence-*`/`--tier-*`；WCAG AA 守门 | `06` §2/§1 |
| **R2** | `.zz-input` 落地 | 定义 `.zz-input` 状态契约，让 Command Dock/Legacy/Settings/领域 4 套输入引用同一组令牌（消除 F1） | `03` §8 / `06` §6 |
| **R3** | 面板语言统一 | 领域面板消费 `--panel-*`/`--surface`/`--radius`/`--ease-*`；补齐 focus-visible/disabled/loading/error（消除 F7 + 键盘失明） | `03` §8/§9 |
| **R4** | Galaxy 双层空间 | 实现注意力模型（操作态/探索态连续缓动）；银河点击行星→`galaxy-overlay` 能力面板；世界层暗化常驻 | `02` §4 / `06` §5.3 |
| **R5** | 导航重组 | rail 能力导航统一语言；命令面板定义为能力目录；Command Dock micro-hint | `04` §3/§4/§6 |
| **R6** | Settings 演化 | 接入 `zz-*` 原语、清硬编码色(F8)、7 分组重组、焦点 `inert` 治理 | `05` §3/§4 |
| **R7** | 缺失原语补齐 | `zz-dropdown`/`zz-menu`/`zz-tabs`/`zz-tooltip`/`zz-modal-card` 契约落地；Toast/Modal 收口(F4/F6) | `06` §6 |
| **R8** | Motion 形式化 | 承接 Phase 7 `07_MOTION_SYSTEM.md`；在场脉动令牌；注意力态缓动 | `06` §3 |
| **R9** | GUI 验收 | 6 尺寸 + 9 主题视觉门禁；红线回归（无第二 Token/无改 Galaxy 本体/无改布局） | 全阶段 |

---

## 验收与 STOP 声明

- ✅ 本阶段产出 **8 份设计文档**（7 分册 + 本报告），0 行代码改动。
- ✅ 所有方案均不违反 Golden State L0 红线、DECISION_004、DESIGN.md、UI_SYSTEM v1.0。
- ✅ 形成 **Xiao6 AI OS Visual Blueprint v1.0**，可作为下一阶段 Visual Redesign 唯一设计依据。
- 🛑 **STOP**：不提交 Git，不进入 Visual Redesign 实现，等待人工 Review 与裁决。

---

## 附录 · 文档索引

| 文件 | 主题 |
|---|---|
| `00_DESIGN_PRINCIPLES.md` | 原则层：纪律红线 / 哲学 / 关键词 / 12 原则 |
| `01_GLOBAL_LAYOUT_ARCHITECTURE.md` | 全局布局：七大 Surface 关系 + 第一分钟体验 |
| `02_GALAXY_WORKSPACE_INTEGRATION.md` | Galaxy 融合：方案 A–D 比较 + 推荐 C |
| `03_PANEL_VISUAL_LANGUAGE.md` | 面板语言：层级/深度/玻璃/边框/glow/动效/密度/状态 |
| `04_ENTRY_AND_NAVIGATION.md` | 入口导航：三支柱 + 功能发现矩阵 |
| `05_SETTINGS_EVOLUTION.md` | Settings：Legacy → Configuration Center 演化 |
| `06_DESIGN_SYSTEM_NEXT_STAGE.md` | 设计系统下一阶段：Color/Typography/Motion/Depth/Spatial/Component |
| `EXECUTIVE_SUMMARY.md` | 本报告 |
