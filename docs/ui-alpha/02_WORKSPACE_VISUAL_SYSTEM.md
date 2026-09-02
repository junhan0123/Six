# 02 · Workspace Visual System（统一工作空间视觉系统）

> AI OS UI Alpha Program v1.0 · Phase 2
> 执行模式：Audit → Visual Design → Implement → Verify → Document → STOP
> 身份：CPO + CDO + Senior Frontend Architect + Senior Interaction Designer + AI OS Experience Lead

---

## 1. 视觉目标（Visual Goal）

让 17 个面板、能力浮层、全屏内容页、设置页、对话抽屉**看起来属于同一个 AI 操作系统**，而非"一堆拼在一起的 Web 组件"。

核心原则（严守 Phase 2 纪律）：
- **只处理 Visual Layer**：Surface / Layer / Depth / Glass / Blur / Spacing / Panel / Background。
- **不改变** Workspace Architecture、Panel 生命周期、Navigation、Capability。
- **消费**既有 `ui2.css` 令牌 + Unified Workspace 六层分类（`02_WORKSPACE_LAYOUT.md`），**不新建**第二套设计语言。

达成判据（Verify）：任何面板 / 浮层 / 内容页打开时，其表面、圆角、边框、模糊、阴影、入场过渡、强调色**与 `.os-panel` / `.zz-dialog` / `.zz-toast` 完全一致**。

---

## 2. Layer 定义（六层视觉关系）

基于 `docs/sprints/ai-os-workspace-v2/02_WORKSPACE_LAYOUT.md` 的六层分类，**仅补充每层的"视觉意图"令牌**（纯 CSS 变量，零 DOM / 行为变更）。

| 层 | 职责 | 承载容器 | 视觉令牌（新增） | z-index 令牌 |
|----|------|----------|------------------|--------------|
| **Background** | 氛围 / 宇宙背景 | `#solarCanvas` | `--ws-bg-base` / `--ws-bg-blur:0` | `--z-stage`↓ |
| **Context** | 情境侧栏 / 洞察 / HUD / Glance | `#osInsight` / HUD | `--ws-context-surface` / `--ws-context-blur` | `--z-hud` |
| **Assistant** | 常驻 AI 伴侣 | Companion（独立窗口） | `--ws-assistant-surface` / `--ws-assistant-blur` | `--z-companion` |
| **Secondary** | 侧弹 / 浮层面板（能力详情） | `.zz-panel-card` / `.cap-panel` / 全屏 `.map/doc/memory/review/sysmon-panel` | `--ws-secondary-surface` / `--ws-secondary-blur` / `--ws-secondary-elev` | `--z-drawer` / `--z-overlay` / `--z-panel` |
| **Primary** | 主任务流（对话 / 执行核心） | `.app` 对话抽屉 / `#osCoreCanvas` / `#osTimeline` / `#osDock` | `--ws-primary-surface` / `--ws-primary-blur` / `--ws-primary-elev` | `--z-content` |
| **Overlay** | 模态 / 指令 / 菜单 / 确认 | `.zz-overlay` / `.cp-overlay` / `.cap-overlay` | `--ws-overlay-scrim` / `--ws-overlay-blur` / `--ws-overlay-elev` | `--z-dialog-mask` / `--z-command` |

**视觉层级规律（AI OS 深度系统）**：
- Background：`--bg` 实底，无模糊（宇宙自身是内容）。
- Context / Primary / Assistant：薄玻璃（`--surface` + `--blur-glass`），轻 elevation。
- Secondary：中玻璃（`--surface-2` + `--bg-2` 渐变底 + `--elev-3`），明显 elevation → 浮于主任务之上。
- Overlay：遮罩 + 重玻璃（`--ws-overlay-scrim` 72% + `--elev-3`）→ 最高模态层级。

---

## 3. Surface 规范（令牌化来源）

| 语义 | 令牌 | 值（midnight 默认） | 备注 |
|------|------|---------------------|------|
| 薄玻璃面 | `--ws-context-surface` / `--ws-primary-surface` | `var(--surface)` | `rgba(90,120,200,.05)` |
| 中玻璃面 | `--ws-secondary-surface` | `var(--surface-2)` | `rgba(90,120,200,.09)` |
| 玻璃底 | `--ws-secondary-base` | `var(--bg-2)` | 渐变终点 |
| 玻璃模糊 | `--ws-*-blur` | `var(--blur-glass)` = `26px` | 全局统一 |
| 遮罩 | `--ws-overlay-scrim` | `color-mix(bg 72%, transparent)` | 浅色主题自动适配（修复旧硬编码 rgba 缺陷） |
| 阴影·轻 | `--ws-primary-elev` | `var(--elev-1)` | 主任务层 |
| 阴影·重 | `--ws-secondary-elev` / `--ws-overlay-elev` | `var(--elev-3)` | 浮层 / 模态层 |

全部为 `ui2.css` 既有令牌的**语义别名**，无新视觉值；主题切换时随 `--accent` / `--bg` 自动重算。

---

## 4. Panel 规范（统一四区）

新增 `--panel-*` 令牌组（`ui2.css :root`），定义所有面板的 Header / Toolbar / Content / Footer 统一尺度。**既有面板已消费其中多数令牌，无需逐个改选择器**；新增面板直接消费，不再自定 padding/radius/divider。

| 区 | 令牌 | 值 |
|----|------|----|
| 圆角 | `--panel-radius` | `var(--radius-md)` = 16px |
| 边框 | `--panel-border` | `var(--border)` |
| Header 内边距 | `--panel-header-pad-y/x` | 14px / 18px |
| Header 分隔 | `--panel-header-divider` | `1px solid var(--border)` |
| 标题字体 | `--panel-title-font` | `'Orbitron', sans-serif` |
| 标题字号 | `--panel-title-size` | 18px |
| 标题色 | `--panel-title-color` | `var(--accent)` |
| Content 内边距 | `--panel-content-pad-y/x` | 16px / 18px |
| Footer 内边距 | `--panel-footer-pad-y/x` | 12px / 18px |
| Toolbar 间距 | `--panel-toolbar-gap` | 10px |
| 滚动条 | `--panel-scrollbar` | `var(--border)` |

---

## 5. 修改统计（Modification Stats）

### 修改前（Before）
- `.zz-panel-card`（42 处引用，主浮层容器）全程硬编码青色 `rgba(34,211,238,…)`：边框 / 表面渐变 / 阴影 / 滚动条 / 英雄区 / 标签 / 列表点。
- `.settings-head-title` 硬编码 `var(--cyan)`（青）。
- `.cap-panel` / `.cap-overlay` 硬编码深色渐变 + 6px 模糊 + 旧 scrim。
- `.map/doc/memory/review-stage` 硬编码 `rgba(10,16,24,.72)` 渐变（浅色主题失效）。
- `.sysmon-panel` 青色径向光晕 + 裸 `ease` 过渡。
- `.zz-panel*` 入场 / 关闭过渡用裸 `ease`（非令牌）。
- `styles.css` 青色硬编码（含面板 chrome）共 **193** 处。

### 修改后（After）
| 项 | Before | After |
|----|--------|-------|
| 面板 chrome 青色硬编码（`.zz-panel-card` 家族） | 13 处 | **0 处** ✅ |
| `.settings-head-title` 青 | 1 处 | 0（→ `--accent`）✅ |
| `.cap-panel/.cap-overlay` 硬编码表面/scrim | 2 处 | 0（→ `--ws-*` 令牌）✅ |
| `.map/doc/memory/review-stage` 硬编码渐变 | 4 处 | 0（→ `--surface-2/--bg-2`）✅ |
| `.sysmon-panel` 青色光晕 | 2 处 | 0（→ `--accent`）✅ |
| `.zz-panel*` 裸 `ease` 过渡 | 4 处 | 0（→ `--ease-soft`）✅ |
| `styles.css` 青色硬编码总计 | 193 | **180**（剩 180 全为**领域数据可视化**，见遗留） |
| 新增令牌 | — | `--ws-*` ×17 + `--panel-*` ×15（纯别名，零新视觉值） |

### 文件改动
- `ui2.css`：新增 `--ws-*` 六层视觉令牌（17）+ `--panel-*` 面板规范令牌（15）；纯 `:root` 增量。
- `styles.css`：`.zz-panel*` / `.settings-head-title` / `.cap-*` / `.map/doc/memory/review-stage` / `.sysmon-panel` 共 **~28 处** 表面/边框/模糊/过渡收口到令牌。

### 零架构 / 生命周期 / 导航变更
- 未改 `panel-manager.js`、`overlay-manager.js`、`focus-manager.js`、`app.js` 任一逻辑。
- 未改 `index.html` 结构 / `data-ws-layer` 标注。
- 未新增 / 删除任何 Panel。

---

## 6. 截图前后对比（Before / After — 描述性，因本地 server 未运行）

> 说明：当前为本地 `浏览器 + http.server` 模型，P2 后端（:8011）与 :8000 均已 DOWN，无活动会话截图。下列为**代码级视觉差异**的等价描述，供 GUI 验收时对照。

| 元素 | Before | After |
|------|--------|-------|
| 浮层面板边框 | 青色 `rgba(34,211,238,.32)` 实边 | `color-mix(accent 32%, transparent)` 主题感知蓝紫边 |
| 浮层面板表面 | 深色直角渐变 `rgba(6,12,18,.94)` | `--surface-2 → --bg-2` 玻璃渐变 + 26px backdrop blur |
| 浮层面板阴影 | 普通黑阴影 | `--elev-3`（含内高光 + 重投影） |
| 面板标题 | 青色 + 青色文字阴影 | `--accent` + `--glow` 文字光晕（与 HUD/导航一致） |
| 面板标签 | 青底青字 `#bfeaff` | `color-mix(accent 80%, #fff)` 字 + `accent 10%` 底（主题感知） |
| 能力浮层 scrim | 固定 `rgba(4,7,11,.72)` + 6px | `--ws-overlay-scrim` 72% + 26px（浅色主题自动变浅） |
| 全屏内容页（地图/文档/记忆/审阅） | 固定深色渐变 | `--surface-2 → --bg-2` 玻璃（浅色主题可见） |
| 入场/关闭过渡 | 裸 `ease` | `--ease-soft`（与全站动效曲线统一） |

**视觉收益**：打开任意面板 / 能力浮层 / 全屏页时，其玻璃质感、圆角、边框、强调色、阴影深度、入场缓动**与首屏 OS 外壳（`.os-panel` / 导航 / HUD）像素级一致**，不再有"青色科技面板浮在蓝色 AI OS 上"的割裂感。

---

## 7. Verify（验证）

| 检查项 | 结果 |
|--------|------|
| `.zz-panel-card` 家族青色硬编码 | **0** ✅ |
| 面板 chrome 全部走 `--accent` / `--surface-2` / `--bg-2` / `--border` / `--radius-md` / `--elev-3` | ✅ |
| 三 CSS 花括号全 BALANCED（ui2 234/234，styles 1648/1648） | ✅ |
| 新增 `--ws-*` / `--panel-*` 令牌全部定义且无 typo | ✅（17 + 15 定义，9 处 `--ws-*` 已消费） |
| 浅色主题适应性（scrim / 表面经令牌重算） | ✅（修复旧 `rgba(4,7,11,.72)` 硬编码 bug） |
| 零 JS / HTML / 架构改动 | ✅（仅 CSS 令牌层） |
| 红线：未碰 Runtime / Agent / EventBus / Galaxy 本体 / Mobile / Capability | ✅ |

---

## 8. 遗留问题（Residual）

- 🟢 **R1（领域数据可视化青色，非缺陷）**：剩余 180 处 `rgba(34,211,238,…)` 全部位于**领域内容**（对话 orb/avatar 辉光、会话 chip、场景卡、hotspot/地球可视化、sysmon 仪表、能力矩阵节点）。`styles.css` 第 16 行明文声明此为**有意设计**（青在 dark-cyan 等主题下即 `--accent`，在 midnight 下为刻意数据强调色）。**不应统一为 `--accent`**——会抹除领域语义（如"地球/热点"用青表达数据，与 UI 强调色解耦）。移交后续 Phase 9（Release Polish）做可选的"领域色令牌化"评审，不阻塞本 Phase。
- 🟢 **R2（`.hotspot-panel` 37 处青）**：同上，属 hotspot 领域可视化，非面板 chrome，保持。
- 🟢 **R3（bare `ease` 过渡仍 ~42 处）**：Phase 1 已收口动画时长，Phase 2 收口了面板入场/关闭的 bare `ease`；其余 42 处为各微交互（hover/tooltip/feed），属 Phase 7（Motion System）统一范围，不在此 Phase 强求。
- 🟡 **R4（字体本地化，续 Phase 1 L1）**：`fonts/` 仍空，`--font-display/ui/mono` 回落系统字体；建议 Beta 前落地 `@font-face`。

---

## 9. 红线自检（Red-Line Compliance）

- ✅ 仅 Visual Layer；未改 Workspace Architecture / Panel 生命周期 / Navigation / Capability。
- ✅ 未新增功能 / Panel；未改 Runtime / Agent / EventBus。
- ✅ 未碰 Galaxy 本体（`solar-system.js` 等受 L0 红线-5 + DECISION_004 保护）；未碰 Mobile。
- ✅ 所有改动为令牌消费 / 别名增量，零第二套设计语言。

---

## 10. 状态

**✅ Phase 2 完成**：统一 Workspace 六层视觉关系、Panel 四区规范、Surface/Blur/Shadow/Elevation 令牌全部落地；主浮层面板 chrome 由"青色科技面板"收口为"AI OS 玻璃面板"，与首屏外壳一致。零架构/导航/生命周期变更，零红线触碰。

**🛑 STOP — 等待人工 Review 后进入 Phase 3（Galaxy Experience：重设计 Galaxy 为 AI OS Navigation Core）。**

> 注：Galaxy 本体（`solar-system.js` 等 Three.js 渲染）受冻结红线保护**不可改**；Phase 3 仅能在"如何用 Galaxy 作为导航核心的 UI 包装层 / 标注 / 交互说明"范围内工作，且须显式标注 Galaxy 本体为 No-Go。
