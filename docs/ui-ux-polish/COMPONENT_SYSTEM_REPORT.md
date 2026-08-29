# 组件系统审计报告（Task C）

> **Sprint 定位**：Xiao6 UI / UX Polish Sprint v1.0 — 组件系统审计
> **执行模式**：Audit → Analyze → Plan → Review → STOP（**仅分析、仅审计、仅设计、仅规划，不修改任何代码/CSS/JS/Python/Electron/Runtime/Memory/EventBus/Planner/Tool/数据库/配置/资源**）
> **审计立场**：成熟商业产品标准（非个人 Demo 标准）
> **语言纪律**：报告全中文；代码/API/文件名/类名/命令/英文技术术语保持英文
> **实证来源**：`ui2.css` / `premium.css` / `styles.css` / `runtime-viz.css` / `companion.css` / `command-palette.js` / `settings.js` / `onboarding.js` / `index.html`（均只读）

---

## 0. 审计范围与本报告结构

本报告聚焦**组件层（Component Layer）**，即用户可直接感知、可重复使用的界面构件：

- 基础构件：Button / Input / Toggle·Switch / Card / Panel / Dialog·Modal·Overlay / Menu / Sidebar / Header / Toolbar / Icon
- 复合构件：Theme Picker / Command Palette / Onboarding / Capability Matrix / Timeline / Dock / Notification / Avatar / Empty State / Progress / Badge / Tabs / Tooltip
- 缺失构件：Breadcrumb / Pagination / Accordion / Table / Skeleton / Segmented Control / Stepper 等
- 特殊视图：Workspace（工作台）

每条问题按 **P0（必须改）/ P1（建议优先）/ P2（可优化）** 三级，含 **问题描述 / 原因分析 / 用户影响 / 修改建议（仅方案，不涉及代码）/ 优先级**，并与 Task A（`UX_AUDIT_REPORT.md`）、Task B（`VISUAL_SYSTEM_REPORT.md`）的对应发现交叉引用。

---

## 1. 核心判断：存在 5–6 套平行组件体系，无统一组件库

成熟商业产品必有**单一组件库（Component Library / Design System）**作为所有界面的唯一构件来源。Xiao6 当前**不存在这样的统一层**——每个功能模块各自带一套视觉语言，令牌、圆角、边框、阴影、动效各不相同。

下表为实证确认的平行体系：

| 体系 | 主要文件 | 代表构件 | 设计令牌来源 | 主要问题 |
|------|----------|----------|--------------|----------|
| ① 遗留聊天 `.app` | `styles.css` | `.rail` `.panel-tab` `.hud-bar` `.btn-new` `.mic-btn` `.send-btn` `.input-shell` `.chip` `.msg` `.toast` `.modal-mask` `.modal-card` | LEGACY（`--void/--cyan/--txt/--dim`） | 固定 1920×1080 + `transform: scale()` 缩放；令牌旧 |
| ② Premium 浮层 | `premium.css` | `.glass-card` `.glass-panel` `.cp-*` `.onb-*` `.btn-new`(重定义) | NEW + 字面量混合 | 与 ① 中 `.btn-new`/`.cp-*` **双定义冲突** |
| ③ 新 OS Shell `.os-shell` | `ui2.css` | `.os-hud` `.os-panel` `.os-cap` `.os-timeline` `.os-dock` `.os-dock-btn` `.os-theme-picker` `.os-chat-fab` | NEW（`--bg/--surface/--accent/--text`） | 自成一套，未与 ①② 统一 |
| ④ Runtime Viz | `runtime-viz.css` | `.rv-bar` `.rv-toggle` `.rv-step` `.rv-dot` `.rv-*` | **硬编码色**（`#34d8ff`/`#3ad29a`/`#ff6b6b`） | 完全不接 Design Token |
| ⑤ Companion 桌宠 | `companion.css` | `.companion-*` `.avatar-*` `.quick-menu` `.status-bubble` | 独立变量（`--avatar-color` 等） | 独立体系，仅 Presentation |
| ⑥ 功能内联 chrome | `index.html`+`styles.css` | `.mem-*` `.settings-*` `.quick-chip` `.more-item` `.wx-open-btn` `.hs-open-btn` `.profile-open-btn` `.uv-close` `.input-eye` | 混合 | 每个功能一套，无统一基类 |

**结论（C-00，观察级）**：组件层的碎片化是 Task B 所指「令牌双命名空间 / 两套缩放 / 两套图标语言」在**构件层面**的必然投影。不先收敛组件层，视觉系统（Task B）的令牌统一将无处落地。

---

## 2. 组件维度逐项审计

### 2.1 Panel / Chrome（面板外壳）—— 碎片化最严重

**C-01（P0）：至少 6 套面板 Chrome 并存**
- **问题描述**：面板外壳（容器外观：背景/边框/圆角/玻璃/层级）至少存在 6 种实现：
  1. 遗留 `.panel` / `.hud-bar`（`styles.css`）
  2. Premium `.glass-panel` / `.glass-card`（`premium.css`）
  3. 新 OS `.os-panel`（`ui2.css`）
  4. 遗留弹层 `.modal-card` / `.modal-mask`（`styles.css`）
  5. 指令中心 `.cp-box`（**`styles.css` 与 `premium.css` 双定义**，内容接近但不一致）
  6. Runtime Viz `.rv-*`（`runtime-viz.css`，硬编码色）
  7. 设置面板 `.settings-card`（`.settings-card-title` 在 `index.html`，样式零散）
- **原因分析**：历史迭代逐模块叠加，每阶段选用当时的「当前最佳」写法，无统一 Panel 原语约束；Phase 10 引入 os-shell 时新建 `.os-panel` 而非收敛旧体系。
- **用户影响**：同一产品内「卡片」长相不一，用户无法建立稳定的「可点击容器」心智模型；玻璃质感/圆角/描边在不同面板跳变，降低「成熟感」。
- **修改建议（仅方案）**：建立**单一 Panel 原语**——`Panel`(base) + 变体 `Panel--glass` / `Panel--solid` / `Panel--elevated`，统一圆角（`--r-*`）、边框（`--border`）、玻璃（`backdrop-filter` 标准值）、阴影（`--elev-*`）、内距（Space 令牌）。所有面板引用同一原语，旧 6 套逐步替换。
- **优先级**：**P0**

**C-02（P1）：Runtime Viz 完全不接 Design Token**
- **问题描述**：`runtime-viz.css` 中 `.rv-step.rv-active::before{background:#34d8ff}`、`.rv-done` 用 `#3ad29a`、`.rv-error` 用 `#ff6b6b`，全部硬编码，未使用 `--accent/--ok/--warn`。
- **原因分析**：Runtime Viz 作为调试/开发者面板早期独立开发，绕过了 Token 体系。
- **用户影响**：切换主题（尤其 Light）时 Runtime Viz 颜色不变，与全局脱节；破坏「主题一致性」承诺。
- **修改建议（仅方案）**：将所有硬编码色改为 Token 引用；`--ok/--warn/--accent` 已在 `ui2.css` 定义，直接复用。
- **优先级**：**P1**

**C-03（P1）：设置面板 `.settings-card` 自成体系**
- **问题描述**：设置中心用 `.settings-card-title`（带 emoji 前缀，见 C-22）与自有内距/边框，与 `.glass-panel`/`.os-panel` 视觉不统一。
- **修改建议（仅方案）**：设置面板复用统一 `Panel` 原语；卡片标题用统一 `SectionTitle` 组件（无 emoji）。
- **优先级**：**P1**

---

### 2.2 Button（按钮）

**C-04（P0）：按钮至少 5–6 套视觉**
- **问题描述**：按钮样式分散在多处，无统一基类：
  - `.btn-new`（`styles.css` + `premium.css` 双定义）
  - `.settings-save-btn`（含 `.danger` 变体）
  - `.os-dock-btn`（`ui2.css`）
  - `.onb-next` / `.onb-skip` / `.onb-back`（`premium.css`）
  - `.quick-chip`（首页快捷指令，自带 chrome）
  - `.more-item`（「更多」菜单项）
  - `.mem-btn`（记忆面板按钮）
  - `.input-eye`（设置内密码显隐）
  - 图标按钮 `.mic-btn` / `.send-btn` / `.speak-btn` / `#btnImage` / `#btnMedia` / `#btnScreen`
- **原因分析**：各模块独立实现按钮，无 `Button` 原语（primary/ghost/icon/danger + size S/M/L）。
- **用户影响**：同一「主操作」在不同界面外观不同（圆形图标按钮 vs 直角文字按钮 vs 圆角胶囊），操作可预测性下降。
- **修改建议（仅方案）**：建立 `Button` 原语：`Button--primary/ghost/icon/danger` × `Button--sm/md/lg`；所有按钮引用；图标按钮统一 `.ic` 规范（见 C-22）。
- **优先级**：**P0**

**C-05（P1）：`.btn-new` 双定义且不一致**
- **问题描述**：`styles.css` 中 `.btn-new` 有完整定义（含 `:hover{box-shadow:var(--glow);transform:translateY(-1px)}`），而 `premium.css` 中 `.btn-new` 仅定义 `transition`、无背景/边框；两者对同一类名给出不同样式，加载顺序决定最终表现，脆弱。
- **修改建议（仅方案）**：删除重复定义，归一到 `Button` 原语一处定义。
- **优先级**：**P1**

**C-06（P1）：图标按钮无统一规范**
- **问题描述**：`.mic-btn .ic{fill:var(--txt)}`、`.send-btn .ic{fill:#03121a}`、`#btnImage .ic{fill:none;stroke:var(--txt)}`——fill/stroke/尺寸各写各的，颜色硬编码（`#03121a`）。
- **修改建议（仅方案）**：图标按钮统一 `Button--icon` + `.ic` 标准（尺寸/描边/激活色用 Token）。
- **优先级**：**P1**

---

### 2.3 Input（输入框）

**C-07（P1）：输入框 4 套**
- **问题描述**：`.input-shell`（聊天输入）、`.settings-input`/`.settings-select`（设置）、`.onb-input`（引导）、`.cp-input`（指令中心，且 `styles.css` 与 `premium.css` 双定义）。
- **修改建议（仅方案）**：统一 `Input` 原语（含 `Input--select` / `Input--password`），focus 态统一 `--focus-ring`（`--accent` 描边 + glow），四套替换为同一原语。
- **优先级**：**P1**（关联 Task B V-16）

**C-08（P2）：密码显隐复用通用按钮 `.input-eye`**
- **问题描述**：`.input-eye` 在设置中多处复制（`settingsLlmKeyToggle`/`settingsMinimaxKeyToggle`/…共 8+ 处），非独立 `InputPassword` 控件。
- **修改建议（仅方案）**：提取 `Input--password` 复合控件，内嵌显隐切换，消除重复。
- **优先级**：**P2**

---

### 2.4 Toggle / Switch（开关）—— 关联 Task A S-01

**C-09（P0）：两套开关并存**
- **问题描述**：
  - `.settings-switch` + `.settings-switch-slider`（42×24，用于沙箱开关）
  - `.zz-toggle` + `.zz-toggle-track`（40×22，用于外观/语音开关）
  - 两者尺寸、圆角、轨道色、滑块动效、未选中态背景均不同；且均**缺少 `:focus-visible` 可达性样式**（关联 RC 审计发现的全局 focus 缺口）。
- **原因分析**：开关在不同时期由不同模块实现，未收敛。
- **用户影响**：设置中心内同一类「开/关」控件外观跳变，且键盘用户无法看到焦点指示。
- **修改建议（仅方案）**：合并为单一 `Toggle` 原语（`Toggle--sm/md`，含 `:focus-visible` 焦点环）；两处调用统一替换。
- **优先级**：**P0**

---

### 2.5 Dialog / Modal / Overlay（弹层）

**C-10（P1）：弹层 3+ 套且无统一交互规范**
- **问题描述**：
  - 遗留 `.modal-mask` / `.modal-card` / `.modal-close`（`styles.css`）
  - 指令中心 `.cp-overlay` / `.cp-box`（`styles.css` + `premium.css` 双定义）
  - 引导 `.onb-overlay` / `.onb-card`（`premium.css`）
  - 宇宙视图 `.uv-*`（开发者）
  - 无统一「关闭/ESC/点击遮罩关闭/焦点陷阱/返回焦点」规范，各弹层自行实现。
- **修改建议（仅方案）**：建立 `Dialog`/`Overlay` 原语，内建 ESC 关闭、焦点陷阱、遮罩点击关闭、关闭后焦点归还触发元素；三套弹层统一引用。
- **优先级**：**P1**

**C-11（P2）：无统一 Toast / Notification 容器**
- **问题描述**：`.toast`（`styles.css`）仅服务聊天；Companion 通知走独立 JS 渲染；两者样式/位置/动效不一致，无统一通知队列。
- **修改建议（仅方案）**：建立统一 `Toast`/`Notification` 服务 + 组件，全局单一容器，分级（info/success/warn/error）。
- **优先级**：**P2**

---

### 2.6 Menu / Sidebar / Header / Toolbar

**C-12（P1）：侧边栏 3 套**
- **问题描述**：遗留 `.rail`（聊天左栏）、新 `.os-side`（OS 侧栏）、记忆面板 `.mem-*`（第三套独立侧栏）。
- **修改建议（仅方案）**：统一 `Sidebar` 原语（可折叠、统一宽度/分隔/激活态）。
- **优先级**：**P1**

**C-13（P1）：顶栏 2 套且双模式下共存于 DOM**
- **问题描述**：遗留 `.hud-bar`（聊天 HUD）与新 `.os-hud`（OS 顶栏）在双模式切换时**均存在于 DOM**（`body:not(.chat-mode) #app{visibility:hidden;pointer-events:none}` 仅隐藏不卸载）。两套顶栏结构、令牌、图标语言均不同，存在视觉重叠/维护双份的风险。
- **修改建议（仅方案）**：明确「单一可见顶栏」策略——按当前模式只渲染/只显示其一；统一 `Header` 原语后两者共用骨架。
- **优先级**：**P1**

**C-14（P2）：菜单无统一组件**
- **问题描述**：`.more-item` 即点即建（「更多」菜单）；Companion 右键菜单在 `companion.css`（`.quick-menu`）；上下文菜单无统一 `Menu`/`ContextMenu` 原语（定位、键盘导航、关闭逻辑各写）。
- **修改建议（仅方案）**：建立 `Menu`/`ContextMenu` 原语（键盘可达、ESC 关闭、点击外部关闭）。
- **优先级**：**P2**

**C-15（P2）：Toolbar 概念分散**
- **问题描述**：指令坞 `.os-dock`、HUD 工具区 `.hud-tools`、聊天左栏 `.rail-section` 均承担「工具栏」职责但各自实现。
- **修改建议（仅方案）**：定义 `Toolbar` 原语（横向/纵向、分组、溢出），三处复用。
- **优先级**：**P2**

---

### 2.7 缺失或不统一的「小构件」

**C-16（P2）：无统一 Tabs**
- **问题描述**：仅遗留 `.panel-tab`（聊天面板标签），且在 `hotspot-mode` 下被隐藏；OS 界面无 Tab 组件。
- **修改建议**：建立 `Tabs` 原语（含键盘方向键导航、下划线/填充指示）。

**C-17（P2）：无统一 Tooltip**
- **问题描述**：全产品 tooltip 依赖原生 `title` 属性（`.btn-new`/`.os-dock-btn`/各 `open-btn` 等），样式不可控、无显示时延、无可达性、暗色下阅读差。
- **修改建议**：建立 `Tooltip` 原语（可控时延/位置/主题适配/支持键盘聚焦触发）。

**C-18（P2）：无统一 Badge / Status 指示**
- **问题描述**：状态点三处各写——`.os-cap-vit`（能力矩阵呼吸点）、`.cp-state`（指令中心状态文字）、`.rv-dot`（Runtime Viz 点）；语义（在线/忙碌/警告）与配色不统一。
- **修改建议**：建立 `Badge`/`StatusDot` 原语（`StatusDot--online/busy/warn/offline` 用 `--ok/--accent/--warn`）。

**C-19（P2）：无统一 Progress**
- **问题描述**：进度条两处各写——`.os-cap-bar`（能力卡片底部 3px）、`.os-tl-phase`（时间线分段）；无统一 `Progress`/`Stepper`。
- **修改建议**：建立 `Progress`（线性/环形）与 `Stepper` 原语。

**C-20（P2）：无统一 Empty State**
- **问题描述**：空态三处各写——`.cp-empty`、`.rv-empty`、首页空面板（Task A H-01）。文案/图标/布局无统一。
- **修改建议**：建立 `EmptyState` 原语（图标+标题+说明+操作）。

**C-21（P2）：无统一 Avatar**
- **问题描述**：Companion `.avatar-*`（自绘 SVG 八态）独立；HUD/档案头像未与统一 `Avatar` 规范对齐。
- **修改建议**：建立 `Avatar` 原语（尺寸/状态环/离线态），Companion 可在此基础上扩展表情动画。

---

### 2.8 Icon System（图标语言分裂）—— 关联 Task B V-14

**C-22（P0）：SVG 线性图标 `.ic` 与 emoji 大规模混用**
- **问题描述**：
  - **SVG 线性图标**：`.ic{fill:none;stroke:currentColor;stroke-width:1.7}`（`styles.css`），用于聊天/遗留按钮（`#btnImage`/`#btnMedia`/`#btnScreen`/`.send-btn` 等）。
  - **emoji 图标**：`index.html` 中 **40+ 处** 使用 emoji 作为功能图标，例如：
    - 顶栏/切换：`💬`(osChatToggle)、`🌌`(osUniverseBtn)、`✕`(uvClose)、`☰`(memSideToggle)
    - 首页快捷：`🕐` `📝` `🧑‍🚀` `💡` `🧠` `📅`
    - HUD 开放按钮：`🌤️`(天气) `📡`(热点) `🧿`(档案) `⚙️`(设置)
    - 「更多」菜单：`🖥️` `📜` `🧾` `🧩`
    - 设置卡片标题：`🧠 记忆 Vault` `📡 实时热点` `🌤️ 天气观测` `🩺 系统自检` `💾 导出` `📥 导入` `🗄️ 导出全部` `♻️ 导入全部`
    - 密码显隐：`👁`
  - 新 OS 能力矩阵 `.os-cap-ico{font-size:18px}` 推测亦为 emoji 占位。
- **原因分析**：emoji 开发成本极低、即写即显，早期被广泛用于「快速占位」；`.ic` SVG 体系仅覆盖聊天/输入区，未扩展至全产品。
- **用户影响**：
  1. **离线优先产品却依赖系统 emoji 字体**渲染——不同 OS/字体下字形、粗细、对齐跳变，暗色主题下彩色 emoji 破坏「克制科技美学」。
  2. emoji 不可控描边/尺寸/对齐，与 SVG 线性图标并置时**视觉权重失衡**（彩色块 vs 细线）。
  3. 部分 emoji（如 `🧿` `♻️`）语义模糊，用户难秒懂。
  4. 违反 WCAG 对比/可达性（emoji 非标准可访问图标，屏幕阅读器读法不可控）。
- **修改建议（仅方案）**：
  - 制定**统一图标规范**：功能图标一律使用 SVG 线性图标（扩展 `.ic` 体系，或引入图标字体/雪碧图，离线自托管）；emoji **仅限**装饰性/表情对话场景且受限使用。
  - 清理 `index.html` 中 40+ 处功能 emoji，替换为 SVG 线性图标（建立图标映射表：天气/热点/档案/设置/记忆/导出/导入/时钟/笔记/建议/关于 等）。
  - 能力矩阵 `.os-cap-ico` 改为 SVG 图标。
- **优先级**：**P0**

---

### 2.9 Theme Picker（主题选择器）—— 关联 Task B V-03

**C-23（P1）：三处主题选择 UI 不一致且未对齐 11 套主题**
- **问题描述**：
  - `.os-theme-picker`（`ui2.css`）：仅写死 3 项（`t-dark`/`t-quantum`/`t-midnight`，渐变方块）。
  - `.onb-theme`（`premium.css`）：引导页主题选择，另一种视觉。
  - 设置页主题选择：又一套（`.settings-select` 或下拉）。
  - 三者均与 `ui2.css` 中 **11 套 `[data-theme]`**（dark/quantum/midnight/dark-cyan/dark-green/dark-purple/dark-amber/dark-rose/light）**不完整对齐**——HUD picker 只能选 3 套，用户无法从界面触达其余 8 套。
- **修改建议（仅方案）**：建立统一 `ThemePicker` 组件，数据源驱动（读取可用主题清单），三处共用；补齐 11 套主题的可达入口（或明确精简主题数量，见 Task B V-01）。
- **优先级**：**P1**

---

### 2.10 Workspace（工作台）

**C-24（P1）：代码库无独立 Workspace 视图**
- **问题描述**：grep `[Ww]orkspace` 仅命中 `app-state.js` 数据层（WorkspaceState），**无独立 UI 视图/组件**。OS 首页的「能力矩阵/执行时间线/洞察」并非成熟产品意义上的 Workspace（任务/笔记/文件/日程聚合工作台）。
- **修改建议（仅方案）**：若产品定位需要 Workspace，应在组件层新增 `Workspace` 复合视图（基于统一 `Panel`/`Sidebar`/`Tabs` 原语），聚合记忆/任务/笔记/文件；否则在 Arch/PRD 层面明确「小6无传统 Workspace，OS 首页即其形态」，避免概念歧义。
- **优先级**：**P1**（关联 Task A W-01）

---

## 3. 组件完备性缺口（相对成熟商业产品）

以下成熟产品常见构件在小6中**缺失或无统一实现**，需在组件库规划中补齐：

| 构件 | 现状 | 建议 |
|------|------|------|
| Dialog（统一） | 3 套分裂 | 建 `Dialog` 原语（C-10） |
| Tooltip | 仅原生 `title` | 建 `Tooltip`（C-17） |
| Menu / ContextMenu | 即点即建 | 建 `Menu`（C-14） |
| Tabs | 仅遗留 `.panel-tab` | 建 `Tabs`（C-16） |
| Badge / StatusDot | 3 处各写 | 建 `Badge`/`StatusDot`（C-18） |
| Progress / Stepper | 2 处各写 | 建 `Progress`/`Stepper`（C-19） |
| EmptyState | 3 处各写 | 建 `EmptyState`（C-20） |
| Avatar | Companion 独立 | 建 `Avatar`（C-21） |
| SegmentedControl | 无 | 新增（用于模式/视图切换） |
| Breadcrumb | 无 | 新增（若有多级导航） |
| Pagination | 无 | 新增（列表/记忆归档） |
| Accordion | 无 | 新增（设置分组） |
| Table | 无 | 新增（能力清单/系统监控） |
| Skeleton / Loading | 无统一 | 新增（首屏/加载占位） |

---

## 4. P0 / P1 / P2 汇总

### P0（必须改）
- **C-01** 至少 6 套面板 Chrome 并存 → 建单一 `Panel` 原语
- **C-04** 按钮 5–6 套视觉 → 建 `Button` 原语
- **C-09** 两套开关并存且缺 focus → 合并 `Toggle` 原语（= Task A S-01）
- **C-22** SVG 与 emoji 图标大规模混用 → 统一图标规范，清理 40+ emoji（= Task B V-14）

### P1（建议优先）
- **C-02** Runtime Viz 硬编码色不接 Token
- **C-03** 设置面板 `.settings-card` 自成体系
- **C-05** `.btn-new` 双定义不一致
- **C-06** 图标按钮无统一规范
- **C-07** 输入框 4 套（= Task B V-16）
- **C-10** 弹层 3+ 套无统一交互规范
- **C-12** 侧边栏 3 套
- **C-13** 顶栏 2 套且双模式共存 DOM
- **C-23** 主题选择器 3 处不一致且未对齐 11 套（= Task B V-03）
- **C-24** 无独立 Workspace 视图（= Task A W-01）

### P2（可优化）
- **C-08** 密码显隐复用通用按钮
- **C-11** 无统一 Toast/Notification
- **C-14** 菜单无统一组件
- **C-15** Toolbar 概念分散
- **C-16** 无统一 Tabs
- **C-17** 无统一 Tooltip
- **C-18** 无统一 Badge/Status
- **C-19** 无统一 Progress
- **C-20** 无统一 EmptyState
- **C-21** 无统一 Avatar

---

## 5. 组件系统统一路线（仅方案，不实现）

> 本节为**设计建议**，不在本 Sprint 落地；落地应在后续「UI 实施 Sprint」按 Roadmap（Task G）顺序执行。

1. **建立 Component Library 三层结构**
   - 基础令牌层（已由 Task B / RC Polish 收口：`ui2.css` 为权威源）
   - 基础组件层：`Button` `Input` `Toggle` `Panel` `Card` `Dialog` `Menu` `Tooltip` `Badge` `Progress` `Tabs` `Avatar` `EmptyState` `Icon`
   - 复合组件层：`Header(HUD)` `Sidebar` `Toolbar(Dock)` `CommandPalette` `Onboarding` `CapabilityMatrix` `Timeline` `ThemePicker` `Notification`
2. **收敛规则（硬约束）**
   - 一个组件一类源码，禁止同名词类在 `styles.css` 与 `premium.css` 双定义（先清 `.btn-new` / `.cp-*`）。
   - Runtime Viz 必须接入 Token（消 C-02）。
   - 所有功能图标走 SVG 体系（消 C-22），emoji 受限。
   - 所有开关/输入/弹层引用原语（消 C-09/C-07/C-10）。
3. **迁移策略**
   - 优先统一「高频、跨界面」构件：Panel / Button / Toggle / Input / Icon / Dialog（P0）。
   - 新界面（OS Shell）先行采用原语，遗留聊天界面在下一轮逐步替换，避免一次性大规模回归风险。
4. **交付物配套**
   - 组件库需配 Figma 设计稿 + 前端实现 + 使用示例 + 无障碍说明（WCAG 2.1 AA，`--focus-ring` 全覆盖）。

---

## 6. 与 Task A / Task B 的交叉引用

| 本报告编号 | 关联 Task A | 关联 Task B |
|-----------|-------------|-------------|
| C-01 面板 Chrome | — | V-11（五套面板 Chrome） |
| C-04/C-05/C-06 按钮 | — | V-15（按钮多套） |
| C-07/C-08 输入框 | — | V-16（输入框多套） |
| C-09 开关 | S-01（两套 Toggle） | — |
| C-13 顶栏双套 | C-01（双界面并存） | — |
| C-22 图标分裂 | — | V-14（emoji vs SVG 分裂） |
| C-23 主题选择器 | — | V-03（picker 写死 3 项） |
| C-24 Workspace | W-01（无 Workspace 视图） | — |
| C-02 硬编码色 | — | V-07（z-index/色值字面量）相关 |

---

## 7. 审计结论（一句话）

> 小6的**视觉令牌已收口（Task B / RC Polish），但组件层尚未收敛**——至少 5–6 套平行组件体系、P0 级四项（面板/按钮/开关/图标）碎片化直接侵蚀「成熟商业产品」观感；组件系统统一应作为 UI Roadmap 的**第一优先级基座工作**，否则上层视觉与交互优化将缺乏可落地的构件载体。

---

*本报告为只读审计产物，未修改任何应用代码/CSS/JS/Python/Electron/Runtime/Memory/EventBus/Planner/Tool/数据库/配置/资源。下一步：Task D 交互体验审计（`INTERACTION_REVIEW.md`）。*
