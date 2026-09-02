# 01 · AI OS UI Audit — Phase 0

> 程序：**AI OS UI Alpha Program v1.0**
> 阶段身份：CPO + CDO + Senior Frontend Architect + Senior Interaction Designer + AI OS Experience Lead
> 阶段产出：**UI Inventory + 冲突清单（仅审计，零代码改动）**
> 日期：2026-08-06
> 状态：**STOP · 移交 Phase 1**

---

## 0. 审计边界与基线声明（关键治理前提）

本程序**不是从零设计一套 UI**。在动手前必须先确立 Single Source 基线——否则 Phase 1 设计语言会重复造轮、与既有冻结令牌冲突。

### 0.1 已存在的冻结/收敛设计真相（本程序必须建于其上）

| 真相层 | 文件 | 状态 | 对本程序的约束 |
|--------|------|------|----------------|
| Design Canon（解释层 ×8） | `docs/design/frozen/`（AI_OS_DESIGN_PRINCIPLES / DESIGN_SYSTEM_SPEC / GALAXY_INTERACTION_SPEC / INTERACTION_SYSTEM_SPEC / INFORMATION_ARCHITECTURE / PRODUCT_CONSTITUTION / DOMAIN_MODEL / EXPERIENTIAL_PROTOTYPE_SPEC） | FROZEN | 视觉风格→实现令牌；Galaxy 语义 100% 保留；交互无可写业务状态。 |
| 令牌权威源 | `xiao6-ui/ui2.css`（`:root` + `[data-theme]`，NEW+LEGACY 双命名空间，最后加载增量覆盖） | 已落地 | 所有颜色/间距/阴影/层级/动效走令牌，禁硬编码。 |
| 设计真相文档 | `xiao6-ui/DESIGN.md`（26KB，Component System Sprint 收敛） | STOP·待 Review | `.zz-*` 前缀、`.btn`/`.glass-panel`/`.os-panel` 原语、9 份缺失组件仅命名不实现。 |
| UI Foundation Sprint（P0 统一） | `docs/ui-foundation/`（9 份） | STOP·待 Review | 字体离线、焦点环、品牌统一、面板/按钮/开关收敛、`.zz-icon` 基线已立。 |
| OS Experience Sprint | `docs/ui-foundation/OS_EXPERIENCE_REPORT.md` | STOP·待 Review | 左侧导航脊柱 `.os-nav`、首屏英雄区 `.os-hero`、Command Palette 分段 `MODES` 已落地。 |

> **结论**：UI Foundation + OS Experience 已把"设计语言/组件/导航/首屏"框架收口。本程序的 Phase 1–9 **必须消费而非重建**上述基线；新增工作定位在**框架之上的体验升华与残差统一**，严禁与 `ui2.css`/`DESIGN.md` 令牌冲突或新建第二套组件类。

### 0.2 本程序纪律红线（继承自用户指令，不可逾越）

- **禁止**：新增业务能力 / Tool / API / Runtime / Agent / Planner / Workflow / Memory / Knowledge / Capability；修改 Prompt 行为 / Golden State / Constitution / Architecture / Capability Platform / Product Constitution / DB / Permission / EventBus；进入 Electron / Mobile / Voice / Perception / Automation。
- **允许**：HTML / CSS / 前端 JS / Three.js UI / Workspace / Panel / Overlay / Command Palette / Galaxy / Companion / Loading / Animation / Icon / Typography / Color / Spacing / Transition / 视觉重构 / 交互优化。
- Galaxy 本体（`solar-system.js` 自转/公转/星空/点击聚焦）**受 L0 红线-5 + DECISION_004 保护，100% 保留，仅可加受控交互层**。

---

## 1. UI Inventory（资产全量登记）

### 1.1 入口页面（5 个 HTML context）

| 页面 | 角色 | 状态 | 备注 |
|------|------|------|------|
| `index.html` | **主 OS 工作区**（Workspace + Galaxy 背景 + HUD + 导航脊柱 + Command + 16+ 面板挂载点） | 主战场 | 91KB，含 `bootOS()`/`fit()` 内联脚本；24 处 `style=` 内联（见 §3.3-L）。 |
| `companion.html` | Companion（伴侣）独立/共生视图 | 主战场 | 与 `companion.js`(29KB) + `companion.css`(18KB) 配套。 |
| `mobile-app.html` | 移动端壳（**红线：Mobile 禁入，仅登记不触碰**） | 冻结·不碰 | `mobile-app.js` 同源。 |
| `selfcheck.html` | 自检/诊断视图 | 外围 | 仅诊断用途。 |
| `weather-modal-preview.html` | 天气模态预览（开发期产物） | 外围 | 疑似预览稿，非线上主路径。 |

### 1.2 样式层（6 个 CSS，共 5832 行）

| 文件 | 行数 | 角色 | 风险等级 |
|------|------|------|----------|
| `styles.css` | 3764 | **遗留单体**（202KB，旧 `.app`/`.settings`/各 feature 样式） | 🔴 高（518 处硬编码 `rgba`、散落缓动、旧双值令牌） |
| `ui2.css` | 1015 | **令牌权威 + 新组件天花板**（最后加载，增量覆盖） | 🟢 基线 |
| `premium.css` | 265 | Feature 专属容器（`.onb-card` 等） | 🟡 中（保留独立，需核对令牌引用） |
| `companion.css` | 484 | Companion 专属 | 🟡 中（58 处硬编码颜色值） |
| `execution-channel.css` | 143 | 执行时间线/通道 | 🟢 低 |
| `runtime-viz.css` | 161 | 运行时可视化 | 🟢 低 |

### 1.3 前端 JS 模块（86 个，关键分层）

| 层 | 模块（节选） | 与本程序关联 |
|----|--------------|--------------|
| 导航/Workspace | `panel-manager.js`(13KB, REG 17 面板) · `command-dock.js` · `command-palette.js`(17KB) · `capability-exposure.js` · `capabilities-view.js` · `focus-manager.js` · `keyboard-manager.js` · `overlay-manager.js`(20KB) · `overlay-runtime.js` | **Phase 2/5/6 主战场** |
| Galaxy/AI 存在 | `galaxy-runtime.js` · `galaxy-state.js` · `solar-system.js`(29KB，本体) · `scene.js` · `main-orb.js` · `main-cognitive.js` · `avatar.js`(19KB) + `avatar-*.js`(5) · `consciousness-core.js` · `voice-orb-simple.js` · `hud-ring.js` · `companion.js`(29KB) | **Phase 3/4/8 主战场**（Galaxy 本体禁改） |
| 执行/状态 | `execution-channel.js` · `execution-timeline.js` · `app-state.js` · `computer-state.js` · `perception-state.js` · `zz-events.js` | Phase 6/8（仅表现层） |
| 面板内容（17 个 REG 挂载） | `memory.js`(30KB) · `memory-panel.js` · `memory-query.js` · `settings.js`(40KB) · `weather.js`(20KB) · `hotspot.js`(83KB) · `map.js` · `doc.js` · `video.js` · `tasks.js` · `review.js` · `sysprompt.js` · `userprofile.js` · `insight-panel.js` · `glance-card.js` · `sysmon.js` · `terminal-stream.js` | **Phase 6 面板统一** |
| 其他/老旧 | `china_regions.js`(47KB) · `kws.js` · `sw.js` · `device-client.js` · `sse-manager.js` | 外围 |

### 1.4 Panel / Overlay 注册清单（`panel-manager.js` REG）

| id | 挂载方式 | overlayId | 备注 |
|----|----------|-----------|------|
| weather | btnId `wxOpenBtn` | `zz-panel` | ⚠️ 共享宿主（Alpha-Stab BUG-002 根因） |
| briefing | btnId `btnBriefing` | `zz-panel` | ⚠️ 同上，closeAll 孤儿 |
| agent-profile | `openAgentProfile` | `zz-panel` | 唯一真正使用 `zz-panel` 宿主 |
| memory / ai-memory / memory-query / settings / hotspot / doc / map / capabilities / sysprompt / review / video / tasks | module 挂载 | 各自独立 overlay | 形态正确 |

> **发现**：`weather`/`briefing` 误配 `zz-panel` 共享宿主，与 `agent-profile` 冲突——这是 Alpha Stabilization BUG-002 的精确位置（P6 修复由 Alpha-Stab 专项负责，本程序登记但不重复修）。

---

## 2. 冲突识别（风格 / 颜色 / 字体 / 间距 / 动画）

### 2.1 颜色冲突

| # | 冲突 | 证据 | 严重度 | 归属 Phase |
|---|------|------|--------|------------|
| C1 | **遗留 `styles.css` 518 处硬编码 `rgba()`** 绕开令牌系统 | `styles.css` `grep -cE "rgba\("` = 518；`ui2.css` 仅 62（含令牌定义本身） | 🔴 高 | P1/P9 |
| C2 | **Companion 58 处硬编码颜色**（`companion.css`）未走 `--accent`/`--surface` | `companion.css` 硬编码计数 = 58 | 🟡 中 | P4 |
| C3 | 主题变体（dark-cyan/dark-green/dark-purple 等 5 个 accent 变体）**未经统一验收**，`light` 主题对比度需复核 | `DESIGN.md` §2.1 8 主题 | 🟡 中 | P9 |

### 2.2 字体冲突

| # | 冲突 | 证据 | 严重度 | 归属 |
|---|------|------|--------|------|
| F1 | 字体 CDN 已移除（✅ 合规），但 `Orbitron`/`Rajdhani`/`Share Tech Mono` **依赖本地 webfont，未核实 `fonts/` 实际落地** | `index.html:7` 注释声明；`DESIGN.md` §3.1 | 🟡 中 | P1 验收 |

### 2.3 间距冲突

| # | 冲突 | 证据 | 严重度 | 归属 |
|---|------|------|--------|------|
| S1 | 间距基数非标准 8 倍数（`--space-2:14`/`--space-3:22`/`--space-4:34`），**散布在 legacy 中的裸 padding/margin 未统一** | `DESIGN.md` §5；`styles.css` 含 5 处裸 `transition` 时长同逻辑 | 🟡 中 | P1/P6 |
| S2 | 面板内 padding 不统一（`.os-panel` 22px vs `.glass-panel` 无显式 padding vs feature 容器各自定义） | `DESIGN.md` §4.2 | 🟡 中 | P6 |

### 2.4 动画 / 运动冲突（**最显著的"不像 AI OS"根因**）

| # | 冲突 | 证据（实测缓动曲线） | 严重度 | 归属 |
|---|------|----------------------|--------|------|
| M1 | **全仓 6 套不同 `cubic-bezier` 缓动**，未统一到 `--ease-premium` | `ui2.css`: `.22,.61,.36,1` / `0.16,1,0.3,1` / `0.34,1.56,0.64,1` / `0.4,0,0.2,1`；`styles.css`: `0.2,0.9,0.2,1`（×2，格式不一致） | 🔴 高 | P7 |
| M2 | **时长令牌 `--motion-*` 未在 legacy 落地**，`styles.css` 仍有 5 处裸 `0.3s/0.5s` 过渡 | `grep transition...[0-9]s` | 🟡 中 | P7 |
| M3 | Galaxy 本体（`solar-system.js`）缓动**受 L0 红线保护不可动**；但其与 OS 面板动效曲线缺乏"家族感"关联设计 | `solar-system.js` 仅 `#9a9a9a` 等少量硬编码 | 🟢 已知约束 | P3/P7 |

### 2.5 组件 / 结构冲突

| # | 冲突 | 证据 | 严重度 | 归属 |
|---|------|------|--------|------|
| P1 | **`index.html` 24 处内联 `style=`**，`DESIGN.md` Don't #3 明文禁止 | `grep -cE "style=" index.html` = 24 | 🟡 中 | P2/P6 |
| P2 | `weather`/`briefing` 共享 `zz-panel` 宿主（见 §1.4） | `panel-manager.js:92-93` | 🟡 中（已由 Alpha-Stab BUG-002 跟踪） | 移交 Alpha-Stab |
| P3 | 面板类 6+ 命名并存（`.zz-panel`×43 / `.os-panel`×4 / `.glass-panel`×3 / `.settings-panel`×4 / `.onb-card`×3 / `.modal-card`×2 / `.cap-overlay`×2…）**语义合法但缺乏统一 Header/Toolbar/Footer 骨架** | `grep -rhoE` 计数 | 🟡 中 | P6 |
| P4 | 图标系统 `.zz-icon` 基线已立，但 emoji 残留与旧 `.ic` 类迁移**待 Review 门控未执行** | `DESIGN.md` Do #7 | 🟡 中 | P9 |

---

## 3. 体验层诊断（"像 Web Dashboard" vs "像 AI OS"）

> 这是本次 Phase 0 的**核心交付**：不止列出视觉冲突，更定位"为何仍像网页控制台而非 AI 操作系统"。

### 3.1 已实现的正面资产（必须保住）
- ✅ 深空玻璃拟态基调 + 青蓝强调（DESIGN.md §1）。
- ✅ 左侧 `.os-nav` 导航脊柱 + 首屏 `.os-hero` 身份英雄区（OS Experience Sprint）。
- ✅ Galaxy 太阳系作为状态可视化本体（DECISION_004 隐喻完整）。
- ✅ Command Palette 分段 `MODES`（搜索/命令/Agent/工作流）。
- ✅ 全局 `:focus-visible` 环（WCAG AA）。

### 3.2 "不像 AI OS" 的 6 个体验缺口（Gap）

| Gap | 现象 | 根因 | 归属 Phase |
|-----|------|------|------------|
| G1 **AI 不存在感** | 系统启动后"小6"作为 AI 的存在感弱——除了 Companion 弹窗外，屏幕没有持续、克制的"AI 在"信号（思考/执行/等待态散落在各模块，无统一 Presence 语言） | 缺统一 AI Presence 系统（Thinking/Executing/Waiting/Listening/Reminder/Suggestion/Feedback） | **P8** |
| G2 **面板各自为政** | 17 个面板 Header/Toolbar/Loading/Empty/Skeleton/Error/Footer 形态不一，打开一个面板像打开一个独立网页 | 无统一 Panel 骨架规范（§2.5-P3） | **P6** |
| G3 **Galaxy 仍是背景装饰** | 用户感知 Galaxy = 星空壁纸，而非"导航核心/状态中枢"；点击行星→能力面板路径未形成肌肉记忆 | 受控交互层（DECISION_004 §2）未设计成"Navigation Core"体验 | **P3** |
| G4 **动效不家族** | 面板展开、Hover、导航高亮、加载、Toast 各用各的缓动/时长，整体缺乏"高级感一致性" | 6 套缓动 + 裸时长（§2.4-M1/M2） | **P7** |
| G5 **Command Center 未真正统一** | Command Palette / Dock / Search / Quick Action 各有一套触发与视觉，用户心智未合并为"唯一命令中心" | 分段已做但未收口 Dock/Search 视觉与快捷键 | **P5** |
| G6 **Companion 工具感** | Companion 仍有菜单/网页感，未完全去工具化、强化 AI Identity | `companion.css` 硬编码 + 布局偏面板化 | **P4** |

### 3.3 结构/可维护性负债（影响"OS 级精致感"）
- `styles.css` 3764 行遗留单体是最大技术债，所有视觉统一都要在"不重写 legacy、仅经 `ui2.css` 增量覆盖"的约束下完成。
- `index.html` 24 处内联 `style=` 与 `bootOS()`/`fit()` 6741+462 字内联脚本，使首屏视觉难以令牌化管控。

---

## 4. 红线合规自检（Phase 0 审计动作本身）

| 禁止项 | 是否触碰 | 说明 |
|--------|----------|------|
| 新增业务能力/Tool/Runtime/Agent/… | 否 | 纯读文档 + `grep` 量化，零编辑 |
| 修改 Golden State/Constitution/Architecture/… | 否 | 仅引用冻结层，未改任何权威文件 |
| 进入 Electron/Mobile/Voice/Perception/Automation | 否 | `mobile-app.*` 仅登记不碰 |
| 修改 Galaxy 本体 | 否 | §2.4-M3 / §3.2-G3 仅作为观察，未改 `solar-system.js` |

> Phase 0 = **审计 + 文档**，本文件为零代码改动产物。

---

## 5. Phase 0 → Phase 1 交接（可执行清单）

### 5.1 Phase 1（AI OS Design Language）输入基线
1. 消费 `ui2.css` 令牌（NEW+LEGACY 双命名空间）+ `DESIGN.md` §2–§6，**不新建第二套令牌**。
2. 把 §2.1-C1 / §2.4-M1 / §2.4-M2 列为 Phase 1 必须"收口"项：
   - 缓动统一：确立 `--ease-premium`(0.16,1,0.3,1) 为唯一主曲线，`--ease-soft`/`--ease-spring` 为辅助，legacy 中其余 3 套经 `ui2.css` 别名或覆盖消歧。
   - 时长统一：所有过渡引用 `--motion-fast/.18s` / `--motion-base/.28s` / `--motion-slow/.45s`。
   - 颜色：legacy `styles.css` 的 518 处 `rgba` 通过 `--surface/-2`/`--border`/`--glow` 令牌别名逐步替换（零视觉变化原则）。
3. 字体：核实 `fonts/` 本地 webfont 落地（Orbitron/Rajdhani/Share Tech Mono），否则 Phase 1 须给出降级栈验收。

### 5.2 Phase 2–9 体验升华映射（来自 §3.2 Gap）
- **P2 Workspace Visual**：统一 Top Layer / Primary / Secondary / Assistant / Context / Background / Overlay / Loading / Skeleton 九层；消 `index.html` 内联 `style=`（§2.5-P1）。
- **P3 Galaxy Navigation Core**：把 Galaxy 从"壁纸"升为"Navigation Core"，设计受控交互层体验（不碰本体）。
- **P4 Companion Upgrade**：去工具感、强化 AI Identity；消 `companion.css` 58 处硬编码（§2.1-C2）。
- **P5 Command Center**：收口 Palette/Dock/Search/Quick Action 为唯一命令中心。
- **P6 Panel Polish**：17 面板统一 Header/Toolbar/Scroll/Loading/Empty/Skeleton/Error/Footer 骨架（§2.5-P3/S2）。
- **P7 Motion System**：统一 6 套缓动 + 时长到令牌（§2.4-M1/M2）。
- **P8 AI Presence**：建立统一 AI 存在语言（G1）。
- **P9 Release Polish**：8 主题对比度（§2.1-C3）、图标 emoji 迁移（§2.5-P4）、Accessibility。

### 5.3 移交 Alpha Stabilization 专项的缺陷（不重复修）
- `panel-manager.js:92-93` 共享 `zz-panel` 宿主 → Alpha-Stab BUG-002（P6 修复）。
- 其余 P3-F6/F7/F8/F9、P4-EXP-1~7 已由 Alpha Stabilization Phase 5 建清单（见 `docs/releases/alpha-v1/06_UX_BUG_BASH.md`）。

---

**STOP — Phase 0 审计完成。零代码改动。等待人工 Review 后进入 Phase 1（Design Language）。**
