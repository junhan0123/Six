# Xiao6 OS Experience Sprint v1.0 — 实施报告

> 状态：**STOP · 等待 Review**
> 执行模式：Audit → Plan → Execute → Verify → Report → STOP
> 身份：Senior Product Designer + Senior UX Architect + Senior Frontend Architect
> 交付日期：2026-08-06

---

## 0. 摘要（Executive Summary）

本 Sprint **不新增任何业务功能**，目标是在既有能力之上重组产品体验，使小6作为「本地个人 AI 副驾」的第一印象达到商业产品水准。落地三处 presentation 层改造：

| 编号 | 改造项 | 核心改动文件 |
|------|--------|--------------|
| 【B】 | 统一 AI OS 导航脊柱 | `index.html` / `ui2.css` |
| 【A+E】 | 首屏身份英雄区（3 秒价值表达） | `index.html` / `ui2.css` |
| 【D】 | Command Center 统一入口分段 | `command-palette.js` / `ui2.css` |

**红线合规结论：零运行时/代理/记忆/规划/工具/数据库/事件总线改动。** 详见第 6 节。

---

## 1. 目标与红线纪律

### 1.1 目标
- 重新组织已有能力，让首屏在 **3 秒内** 传达：「我是小6 / 我是本地 AI / 我现在可以做什么」。
- 建立全产品**单一导航逻辑**（Galaxy / Workspace / Command / Settings / Assistant）。
- 提升首屏价值表达、导航体验、Command Center 体验，达到「AI Operating System」质感。

### 1.2 允许范围 ✅
UI / UX / 页面布局 / 信息架构 / 动效 / 组件组合 / 首屏体验 / 导航体验 / 引导体验。

### 1.3 禁止范围 ❌
新增业务功能 / 修改 Runtime / 修改 Agent / 修改 Memory / 修改 Planner / 修改 Tool / 修改数据库 / 修改 EventBus。

---

## 2. 【B】统一 AI OS 导航脊柱

### 2.1 问题
原 HUD 内含独立的聊天/宇宙切换按钮，与 Command Palette、Settings 等入口各自为政，导航**碎片化**，用户无法形成「单一 OS 导航」心智。

### 2.2 方案
新增贯穿 OS Home 的**左侧导航脊柱** `nav.os-nav`，覆盖 6 个统一目的地：

| data-nav | 含义 | 触发行为 |
|----------|------|----------|
| `home` | 小6首页 | 关闭 chat/universe、关闭 Settings、关闭 Command Palette |
| `workspace` | 工作台（对话） | `closeUniverse()` + `openChat()` |
| `assistant` | 语音助理 | `openChat()` + 派发 `zz:voice-toggle` 事件 |
| `command` | 指令中心 | `ZZCommandPalette.open()` |
| `galaxy` | 星图（宇宙视图） | `closeChat()` + `openUniverse()` |
| `settings` | 设置 | `ZZSettings.open()` |

**同步机制（单一真相）**：导航高亮**不新建状态机**，由 `body` 的 `class` 与 `settingsPanel` 的 `open` 类推导：
```js
function syncNav() {
  var b = document.body.classList, cur = 'home';
  if (b.contains('universe-mode')) cur = 'galaxy';
  else if (b.contains('cp-mode')) cur = 'command';
  else if (b.contains('chat-mode')) cur = navVoice ? 'assistant' : 'workspace';
  else if (settingsOpen()) cur = 'settings';
  navBtns.forEach(function (btn) {
    btn.classList.toggle('active', btn.getAttribute('data-nav') === cur);
  });
}
// 监听 body 类 + 设置面板 open 类变更 → 自动同步高亮
var navObs = new MutationObserver(syncNav);
navObs.observe(document.body, { attributes: true, attributeFilter: ['class'] });
```

### 2.3 布局与样式
- `ui2.css` `.os-shell` grid 增加左侧 76px 导航列：
  ```css
  grid-template-columns: 76px 1fr 380px;
  grid-template-areas: "nav hud hud" / "nav core side" / "nav bottom bottom";
  ```
- 导航样式复用既有 Design Token（`--surface` / `--blur-glass` / `--accent`），`.os-nav-btn.active` 用左侧高亮条 `::before`，`z-index: 35`。
- **HUD 去重**：删除 `osChatToggle` / `osUniverseBtn` 冗余按钮，保留主题选择器，消除导航碎片。
- **响应式**（`@media max-width:980px`）：导航转为横向底栏，`flex-direction: row`，active 高亮条移至底部横条。

---

## 3. 【A+E】首屏身份英雄区

### 3.1 问题
原 `.os-core` 仅显示弱标签 `AI Consciousness Core`，首屏**无法在 3 秒内传达身份与价值**。

### 3.2 方案
将弱标签替换为首屏身份英雄区 `.os-hero`，复用既有 `osCoreCanvas` 背景：

```html
<div class="os-hero">
  <div class="os-hero-eyebrow"><span class="dot"></span> 本地运行 · 隐私优先</div>
  <h1 class="os-hero-title">小6</h1>
  <p class="os-hero-sub">你的本地个人 AI 操作系统</p>
  <p class="os-hero-desc">完全运行在你的设备上：对话、调度任务、统观全局——一个真正属于你的 AI 副驾。</p>
  <div class="os-hero-actions">
    <button class="os-hero-chip" data-nav="workspace">对话</button>
    <button class="os-hero-chip" data-nav="command">指令</button>
    <button class="os-hero-chip" data-nav="galaxy">星图</button>
  </div>
</div>
```

### 3.3 价值表达层级（3 秒认知路径）
1. **隐私徽章**（eyebrow）：本地运行 · 隐私优先 → 建立信任。
2. **身份标题**（64px 渐变文字）：小6 → 我是谁。
3. **副标题**：你的本地个人 AI 操作系统 → 我是什么。
4. **能力说明**：对话 / 调度 / 统观 → 我能做什么。
5. **快捷 chip**（对话 / 指令 / 星图）：**复用 `[data-nav]`**，与统一导航脊柱联动，点击即跳转对应视图。

### 3.4 样式要点
- `.os-hero-title` 64px 渐变文字；窄屏（`max-width:980px`）降为 44px。
- chip hover / active 态复用 `--accent`（`#04101a` 文字 + accent 背景），与导航 active 视觉一致。

---

## 4. 【D】Command Center 统一入口分段

### 4.1 问题
原 Command Palette 单一输入框混合搜索/命令/Agent/工作流，用户**缺乏分类心智**，且自然语言意图无明确入口。

### 4.2 方案（纯展示层过滤，无新后端线缆）
显式分段 `MODES`，复用既有 `ZZIntentGateway` 单一意图入口纪律：

```js
const MODES = [
  { id: 'search',   label: '搜索' },
  { id: 'command',  label: '命令' },
  { id: 'agent',    label: 'Agent' },
  { id: 'workflow', label: '工作流' },
];
const MODE_CATS = {
  search:   null,                               // 搜索 = 浏览全部
  command:  ['panel', 'feature', 'system', 'theme'],  // 命令 = 显式动作
  agent:    ['intent'],                         // Agent = 自然语言意图网关
  workflow: ['create'],                         // 工作流 = 目标/待办/提醒
};
```

- `render()` 按 `_mode` 过滤分类；仅 `search` / `agent` 段提供「作为意图发送」Intent Gateway 逃逸舱（维持 `ZZIntentGateway` 单一入口）。
- `syncModes()` 同步 chip active 态；`openCp()` 重置 `_mode='search'`。
- `init()` 动态生成 `.cp-mode-chip` 并绑定点击（`_mode` 切换 + `render()`）。
- `CP_HTML` 新增 `<div class="cp-modes" id="cpModes">`，placeholder 改为「搜索、执行命令、调度 Agent 或运行工作流…」。

### 4.3 样式
- `.cp-modes` / `.cp-mode-chip` 分段 chips 样式，active 用 `--accent`。

---

## 5. 验证结果（Verify）

| 验证项 | 命令 / 方法 | 结果 |
|--------|-------------|------|
| Command Palette 语法 | `node --check command-palette.js` | `SYNTAX_OK` |
| `bootOS()` 内联脚本 | `new Function()` 校验（6741 chars，含导航控制器） | `BOOTOS_SYNTAX_OK` |
| `fit()` 内联脚本 | `new Function()` 校验（462 chars） | `FIT_SYNTAX_OK` |
| `ui2.css` 花括号平衡 | open/close 计数 | `234 / 234 BALANCED` |
| 冗余按钮残留 | Grep `osChatToggle` / `osUniverseBtn` in `index.html` | **0 匹配**（已清除） |
| `[data-nav]` 就绪 | Grep `index.html` + `ui2.css` | 导航 6 项 + 英雄 3 chip 全部就绪 |
| 资源版本号 | `ui2.css?v=` 链接 | 已 bump `20260806c7` |

### 5.1 协同验证说明
- **响应式**：导航在 ≤980px 转横向底栏；英雄标题降至 44px；grid 转 `1fr` 单列。
- **主题**：导航 / 英雄 / chip 全部复用既有 Design Token（`--surface` / `--accent` / `--text-dim` 等），三主题（dark / quantum / midnight）自动适配。
- **键盘**：Command Center 键盘导航（`↑↓` / `Enter` / `Esc`）未改动；`Ctrl/⌘+K` / `Ctrl/⌘+U` 既有快捷键不受影响。
- **Overlay**：导航 click 复用既有 `ZZSettings.open/close` 与 `ZZCommandPalette.open/close`，不新建 Overlay 管理器；Overlay 治理由独立 Sprint 负责。

---

## 6. 红线合规声明

### 6.1 本 Sprint 实际编辑文件（仅 3 个 presentation 文件）
- `xiao6-ui/index.html` — 导航脊柱 DOM + 英雄区 DOM + 导航控制器 JS + 资源版本号 bump。
- `xiao6-ui/ui2.css` — `.os-shell` grid + `.os-nav*` + `.os-hero*` + `.cp-modes*` + 响应式。
- `xiao6-ui/command-palette.js` — `MODES` / `MODE_CATS` / `_mode` / `syncModes()` / `.cp-modes` 渲染。

### 6.2 禁止项触碰核查
| 禁止项 | 是否触碰 | 说明 |
|--------|----------|------|
| 新增业务功能 | 否 | 仅重组既有能力，零新功能 |
| Runtime | 否 | 未改任何 `.py` 运行时 |
| Agent | 否 | 未改代理逻辑 |
| Memory | 否 | 未改记忆层 |
| Planner | 否 | 未改规划器 |
| Tool | 否 | 未改工具定义 |
| 数据库 | 否 | 未改 DB / schema |
| EventBus | 否 | 仅派发既有 `zz:voice-toggle` 事件，未新建通道 |

> 注：工作树存在大量 **Phase 10 既有未提交改动**，本 Sprint 仅在上述 3 个 presentation 文件内做外科式编辑，未引入任何运行时/逻辑层变更。

---

## 7. 明确排除项（受红线约束，未实施）

- Dialog / Modal 全量迁移（由 Overlay Implementation Sprint 负责）。
- Focus Trap / `inert` 全量开启（Overlay 治理范畴）。
- 新增业务模块 / 新后端线缆。

---

## 8. 后续建议（待 Review 批准后）

1. **Overlay Implementation Sprint**：落实 `z-index` 令牌化、中央 ESC / 焦点分发器、Toast 3→1 收敛。
2. **Hero 视觉增强**：考虑加入微型状态指示（当前 AI 状态 / 今日任务计数）以呼应【C】内容层级整理（本 Sprint 未实施【C】）。
3. **导航 Voice 态持久化**：当前 `navVoice` 仅在会话内有效，刷新后重置——如需持久，建议走既有偏好存储而非新建状态。

---

**STOP — 报告完成，等待人工 Review。未经批准不进入 Overlay Implementation Sprint 或任何新功能阶段。**
