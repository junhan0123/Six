# UI-4C-1 · Visible Experience Upgrade v1.0 — 实施报告

> 阶段定位：**纯表现层升级**。目标是让用户肉眼明显感到 Xiao6 = AI Operating System，**不是治理、不是审计、不新增功能**。
> 完成状态：V1–V4 全部实现、三档 + 三面板截图落地、CSS 语法/红线校验通过、AI Presence 三唯一受保护。
> **纪律：本报告完成后 STOP，等待 Review。不擅自扩展功能、不提交 Git。**

---

## 0. 验收四问（直接回答 brief 要求）

| # | 问题 | 回答 |
|---|------|------|
| ① | **第一眼最明显的变化是什么？** | 主工作区底部出现一条玻璃「操作甲板」把 Timeline 与 Command Dock 连成整体控制面；Command Dock 左上角出现 **「AI INTENT」徽记**、整体玻璃化；HUD 四角出现 L 型定位标，整屏从「网页浮在星空上」变成「飞船 HUD 观察窗 + 连续操作空间」。 |
| ② | **哪三个区域提升最大？** | **(1) Command Dock（V2）**——从普通输入框升级为全局 AI 意图入口，玻璃面板 + 渐变描边 + 状态微光；**(2) 主工作区底部甲板 / 侧栏玻璃（V1）**——Rail、HUD、Hero、侧栏统一磨砂玻璃语言；**(3) 三大高频面板（V3）**——weather / briefing / agent-profile 统一为同一套玻璃卡片语言，不再各自为政。 |
| ③ | **它看起来还像一个网页吗？** | **不像。** 连续 HUD 空间感（四角标 + 径向晕影）、磨砂玻璃材质分层、主题强调色全程跟随（9 主题 `--accent`），以及底部甲板把操作收拢为一个控制面——这些是 OS HUD 而非 Web Page 的视觉语法。 |
| ④ | **它体现「AI Operating System」了吗？** | **体现了。** AI Presence 状态（EXECUTING 呼吸光、THINKING/PLANNING 微光）直接驱动 Command Dock 与发送键的视觉，系统状态可见、可感，而非隐藏在后台逻辑里。 |

---

## 1. Changed Files（改动文件）

| 文件 | 动作 | 说明 |
|------|------|------|
| `xiao6-ui/ui4c-visible-upgrade.css` | **新建** | 核心交付物，623 行。分 V1/V2/V3/V4 + 细节 + 响应式。作为 **最高层覆盖** 加载。 |
| `xiao6-ui/index.html` | **改 1 行** | 第 19–20 行新增 1 条 `<link>`，位于 `ui4b-explore-transition.css` 之后、所有 UI CSS 最末尾（保证覆盖优先级）。 |
| （临时脚本 `_shot_*.js` / `_panel_debug*.js` / `_edge_test.js` / `_presence_check.js`） | **已删除** | 仅用于无头截图与 DOM 校验，交付前 `rm -f` 清理，不入库。 |

**index.html 新增内容（第 19–20 行）：**
```html
  <!-- UI-4C-1 · Visible Experience Upgrade v1.0（纯表现层；必须位于所有 UI CSS 之后） -->
  <link rel="stylesheet" href="ui4c-visible-upgrade.css?v=20260810a1" />
```

> **加载顺序（冻结约束下的最高层）：**
> `styles.css → premium.css → runtime-viz.css → execution-channel.css → ui2.css → spatial-runtime.css → ui4b-first-screen.css → ui4b-explore-transition.css → ui4c-visible-upgrade.css`

---

## 2. Visual Changes（逐版视觉变更）

### V1 · 主工作区视觉升级（Main Workspace）
- `.os-shell`：叠加极淡**径向晕影**，让星系与界面处于同一连续空间。
- **HUD 四角定位标**：`.os-shell::before` 用 8 个 `linear-gradient` 背景模拟四角 L 型标，把主视图像飞船观察窗。
- **左侧 Rail**：半透明磨砂玻璃导航立柱（材质区别于星空）；`.rail::after` 右侧 HUD 扫描线；品牌区微光。
- **顶部 HUD 栏**：玻璃化状态条；状态徽章小光点。
- **Hero 徽章**：进一步降重，像系统水印（沿用 P9 小徽章方向，未改结构）。
- **右侧能力矩阵/洞察面板**：统一玻璃语言。
- **底部操作甲板** `.os-bottom`：渐变甲板，把 Timeline + Dock 连成整体控制面。
- 宇宙视图材质与 Operation Layer 连续。

### V2 · Command Dock 体验升级（保持全局 AI 意图入口，不变聊天框）
- `.os-dock`：玻璃面板 + 渐变描边（`.os-dock::before` 用 `mask-composite` 挖空）。
- **「AI INTENT」徽记**：`.os-dock::after` 左上角极小身份徽记，明示这是 AI 意图入口而非聊天框。
- `.zz-command-dock` 玻璃化；`:focus-within` 扩展 glow（不是输入框蓝框）。
- 输入框更像「指令接收器」；工具按钮统一图标按钮；发送/主行动键高亮强调。
- **执行状态表达**：`body[data-presence="EXECUTING"]` 时 Dock 顶部呼吸光（`zzcDockPulse`）；`THINKING/PLANNING` 较慢微弱呼吸（`zzcDockGlow`）。

### V3 · 首批三面板视觉迁移（高频：weather / briefing / agent-profile）
- **统一三大面板容器语言**：内层卡片 `.zz-panel-card` / `.wx-inner` / `.briefing-card` 统一玻璃卡片样式（**不碰外层 overlay 的 fixed 定位**）。
- 顶部微光条（`::before`）；**Active 态**主题色边缘 + 提升阴影。
  - Active 选择器：`#zzPanel[aria-hidden="false"] .zz-panel-card` / `body.weather-mode .wx-inner` / `.briefing-overlay.show .briefing-card`。
- 统一标题区 / 内容区 / 关闭按钮；weather、briefing、agent-profile 各自标题高亮以区分语义但保持同一套卡片语法。
- 响应式：`.zz-panel` 仅在小屏加 `border-radius`/`max-width`（**不触碰 position**）。

### V4 · AI Presence 视觉整合（保护 Phase 8 三唯一）
- 仅**消费** `body[data-presence]` 与 `--presence-color` / `--accent`，**不重定义**颜色映射。
- `body[data-presence="EXECUTING"] .os-dock::after` / `.zz-command-dock .cd-send` 用 `--presence-color` 增强。
- `ERROR` 态红框提示。

---

## 3. Before / After（截图证据）

截图位于 `docs/ui-system/ui4c-visible-upgrade/screenshots/`，共 12 张：

**主工作区三档（before/ vs after/）**
- `shot_1920x1080.png` — 桌面大屏
- `shot_1440x900.png` — 笔记本常见分辨率
- `shot_720x1280.png` — 窄屏 / 竖屏

**三面板（before_panels/ vs after_panels/）**
- `weather.png` — 天气面板
- `briefing.png` — 简报面板
- `agent_profile.png` — Agent 档案面板

> 说明：因模型侧无法肉眼读取 PNG（Content filtered），本次**视觉验收以无头 Edge + 计算样式 (getComputedStyle) + DOM 探测 + 控制台输出**替代肉眼比对；截图已落盘供人工 Review 时肉眼复核。

---

## 4. Regression（回归与红线确认）

### 4.1 红线（不可逾越，全部遵守）
- ✅ **零逻辑改动**：未动 Backend / Agent / AppState / EventBus / Galaxy 数据逻辑 / `solar-system.js`；未新增任何功能。
- ✅ **仅 CSS + 1 行 link**：唯一结构性改动是 index.html 第 20 行新增 1 条 `<link>`。
- ✅ **三面板外层 fixed 定位未触碰**：V3 只改内层卡片（`.zz-panel-card`/`.wx-inner`/`.briefing-card`），未覆盖 `styles.css` 中 `.zz-panel-card`(2996) / `.wx-inner`(1686) / `.briefing-overlay`(1449) 的 `position:fixed`。
- ✅ **AI Presence 三唯一受保护**（Phase 8，20/0 测试）：
  - 唯一状态权威：`avatar-state.js` `AvatarState.deriveFromGlobals()`（未动）。
  - 唯一写入点：`index.html` `refreshHud()` 单处 `setAttribute('data-presence')`（未动）。
  - 唯一颜色权威：`ui2.css body[data-presence]` → `--presence-color`（未重定义；V4 只消费）。

### 4.2 语法与一致性
- ✅ 大括号平衡：`{` 68 / `}` 68。
- ✅ 圆括号平衡校验通过（前序验证 218/218）。
- ✅ 无 `--rgb-accent` 残留（项目仅有 `--accent`；已全部用 `color-mix(in srgb, var(--accent) X%, transparent)` 替代，37 处）。
- ✅ 强调色全部跟随主题变量，9 主题 `--accent` 自然生效。

### 4.3 依赖与兼容性
- ✅ 仅用标准 CSS（`backdrop-filter` / `mask-composite` / `color-mix` / `@media`），无 JS、无新依赖。
- ✅ 加载顺序保证覆盖优先级，不影响既有 `ui2.css` 令牌体系（CSS 加载顺序权威未变）。

### 4.4 已知限制 / 待人工 Review 项
- ⚠️ **GUI 视觉验收未做肉眼确认**：受模型看图限制，采用 DOM 计算样式 + 无头截图替代；12 张截图已落盘，请在浏览器/Review 时肉眼复核 Before/After 差异是否符合预期。
- ⚠️ 未跑 P8 AI Presence 20/0 全量测试（属前端单测，需要测试环境；本次以 `_presence_check.js` 探针确认 `data-presence` 联动与三唯一未被破坏）。
- ⚠️ 未提交 Git（按纪律 STOP 等 Review）。

---

## 5. 交付清单（Checklist）

- [x] V1 主工作区视觉升级
- [x] V2 Command Dock 体验升级（保持全局 AI 意图入口）
- [x] V3 三面板视觉迁移（weather/briefing/agent-profile）
- [x] V4 AI Presence 视觉整合（保护三唯一）
- [x] 主工作区三档截图（1920×1080 / 1440×900 / 720×1280）
- [x] 三面板截图（before/after）
- [x] CSS 语法校验 + 红线校验
- [x] AI Presence 三唯一保护验证
- [x] `00_IMPLEMENTATION_REPORT.md`（本报告）
- [x] 临时脚本清理
- [ ] **等待 Review / 不扩展功能 / 不提交 Git**

---

*生成时间：2026-08-10 · 阶段：UI-4C-1 Visible Experience Upgrade v1.0 · 状态：STOP 等 Review*
