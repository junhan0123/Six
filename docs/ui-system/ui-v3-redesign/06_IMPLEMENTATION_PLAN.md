# 06 · 实施计划（IMPLEMENTATION PLAN）

> **阶段**：UI-v3 Clean Reconstruction · Phase 1（Design Only，本文件仅规划，不执行）
> **依赖**：`00`–`05` 六份设计文档
> **重要**：本文是**实施蓝图**，当前阶段**不写代码**。待 Review 通过后，按此计划进入实现阶段。

---

## 1. 实施总原则

1. **替换而非叠加**：v3 首页用单一 `ui-v3.css` + 全新首页 DOM 片段，**不**在五代叠加上再盖层。
2. **隐藏而非删除**：被红线禁止的元素（nav/hud/side/bottom/readout/galaxy）在首屏 `display:none`/移出语境，**不删 DOM、不改 JS、不删功能**。其他视图（chat/universe/settings）不受影响。
3. **能力复用**：三个数据 API、8 态色板、`sendText`、galaxy-state 关系、agent_state 事件——全部直接复用，零新增后端/运行时/事件。
4. **可逆**：每步带回滚开关（见 §3），出问题一键回退旧首页。

---

## 2. 分阶段实施

### Phase A · 脚手架与样式表（地基）
- 新建 `ui-v3.css`（单一样式表，含 §5 色彩/空间/字体/动效 token）。
- 在 `index.html` `<head>` 末尾引入 `ui-v3.css`；**暂不移除**旧链接（回滚用）。
- 定义 v3 首页容器 `.v3-presence`（替代 `.os-shell` 在首屏的角色），初始 `display:none`，由开关控制显隐。

### Phase B · 首页存在界面 DOM（Presence Surface）
- 在 `index.html` 新增 v3 首页片段：`.v3-presence` 内含 AI Core 容器（复用 `#osCoreCanvas`）、Context Layer 容器、Intent Line 容器（复用 `#osDock`）。
- **隐藏**旧首屏元素：`.os-nav` / `.os-hud` / `.os-side` / `.os-bottom` / `.os-readout` / `#solarCanvas` / `.galaxy-veil`（首屏 `display:none`）。
- 不删任何旧 DOM/JS。

### Phase C · AI Core（Presence Layer）
- 用 `ui-v3.css` 把 `#osCoreCanvas` 重定位到视口中心，光核随 `--core-color`（avatar-state）变色，呼吸动效（≤400ms）。
- Core 文案：身份 + 状态（agent_state）+ 正在处理（取 `/api/goals?status=active` 首条）+ 下一步建议。
- 点击 Core 原地展开浮层（复用既有 Overlay 机制），关闭回存在界面。

### Phase D · Intent Line（Intent Layer）
- `#osDock` 重定位为底部居中悬浮输入线；移除 `.os-dock-console-head` 外壳（仅视觉）。
- 占位符随 `agent_state` 四态切换文案与 `--core-color` 输入线（见 `03` §3）。
- **不改 `command-dock.js` 发送逻辑**。

### Phase E · Context Layer
- Context 容器渲染：正在处理（active goals 流）、记住了（最近记忆）、知道（知识语义摘要）。
- 复用 `ui-data-adapter.js` 的 fetch+render 隔离模式（可借鉴，展示层全新），数据取自既有 API。

### Phase F · Overlay Layer（理解网络 + 设置 + 抽屉）
- `⌘4` 唤起理解网络：2D 关系图，数据取自 galaxy-state 关系投影 + 三个 API（见 `04`）。不加载 Three.js。
- 设置（含主题选择器）迁入 `⌘,` Overlay；上下文抽屉（能力矩阵+洞察）迁入 `⌘` Overlay。
- 旧 HUD 元素功能保留，入口迁移，首屏不再显示。

### Phase G · 旧层清理（可逆）
- 确认 v3 稳定后，从 `index.html` 移除五代叠加 CSS 链接（ui4b/c/d、ui5d）与 P0-B/P1 补丁（ui-v2-*）在**首屏**的加载（chat 视图若依赖可保留其自身加载）。
- `ui2.css` 仅作 token 提供方，旧布局规则在 v3 首页不再被引用。

---

## 3. 风险与回滚

| 风险 | 影响 | 回滚方案 |
|---|---|---|
| v3 首页视觉不及预期 | 体验倒退 | 用开关（如 `body.v3-home` 类 / `?v3=0`）切回旧 `.os-shell` 首页；v3 片段 `display:none` |
| `#osDock` 重定位破坏发送 | 意图失效 | `command-dock.js` 未改，仅 CSS 定位；回退 CSS 即可恢复旧 dock |
| 隐藏旧元素误伤其他视图 | chat/universe 异常 | 隐藏仅作用于首屏语境（v3 容器激活时），其他视图 DOM 未删；关掉 v3 开关即恢复 |
| 理解网络 2D 渲染性能 | 卡顿 | 节点上限 + 虚拟化；回退为不加载（⌘4 暂不可用） |
| token 命名冲突（ui2 vs v3） | 样式错乱 | v3 用独立前缀（如 `--v3-*`）或明确覆盖，不与旧 token 混用 |
| Agent/EventBus 误触 | 超出纪律 | 实施期严格只读既有事件/API，不 import 不改；Code Review 卡点 |

**回滚机制（推荐）**：实现阶段用单一开关
```html
<!-- 伪代码，仅示意回滚点 -->
<body class="v3-home">   <!-- 去掉此类即回旧首页 -->
```
+ `ui-v3.css` / 旧五代 css 均保留链接，v3 类控制显隐。确认稳定后再清理旧链接（Phase G）。

---

## 4. 验收对照（v3 原则 → 检查项）

| v3 原则 | 验收检查 |
|---|---|
| 一个空间、一个 AI、一个入口 | 单一 `.v3-presence`；AI Core 唯一中心；Intent Line 唯一输入 |
| 不允许 Dashboard 心智 | 无侧栏双面板/底部双面板/独立状态条 |
| 不允许左侧导航 | 无 `.os-nav`；导航走 ⌘ + Ambient 微点 + Overlay |
| 不允许 HUD | 无 `.os-hud`；品牌/时钟/主题移出首屏 |
| 不允许 Galaxy 首页 | `#solarCanvas` 降级；理解网络仅 ⌘4 Overlay |
| AI Core 唯一视觉中心 | 光核居中、权重最高 |
| 简洁/高级/科技感 | 真实浏览器观感评审通过 |

---

## 5. 开放决策（待 Review 拍板）

1. **导航彻底无栏 vs 保留 Ambient 微点**：首页是否连微点都不要，纯靠 Intent + ⌘？还是保留 ≤3 个极轻量微点指示焦点？
2. **Light 变体本期是否必须**：深色优先已定，Light 是否本期交付？
3. **AI Core 化身形态**：光核（呼吸环）vs 更具体的符号形象？
4. **理解网络默认范围**：⌘4 是否足够，还是 Intent Line 也提供"查看世界"建议入口？
5. **Phase G 清理时机**：v3 稳定后是否立即移除五代叠加链接，还是长期保留开关共存？

---

## 6. 本阶段纪律确认（Phase 1）

- ✗ 不写代码 / 不改 CSS / 不改 HTML / 不改 JS
- ✗ 不新增功能 / 不新增事件 / 不改 Agent / EventBus / AppState
- ✓ 仅产出 7 份设计文档（00–06）
- → **STOP，等待 Review**。确认或修订后，按 §2 进入实现阶段。

---

## 附：文档清单

| 文档 | 内容 |
|---|---|
| `00_UI_V3_AUDIT_FINAL.md` | 可复用 / 必须隐藏 / 必须废弃 终审 |
| `01_UI_V3_INFORMATION_ARCHITECTURE.md` | 四层信息架构（Presence/Context/Intent/Overlay） |
| `02_AI_CORE_DESIGN.md` | AI Core 状态机 / 动效 / Presence 映射 |
| `03_INTENT_LINE_DESIGN.md` | Intent Line 输入体验 / Goal 转换流程 |
| `04_WORLD_UNDERSTANDING_DESIGN.md` | Galaxy → 理解网络 |
| `05_VISUAL_LANGUAGE.md` | 色彩/字体/空间/动效 |
| `06_IMPLEMENTATION_PLAN.md` | 分阶段/风险/回滚（本文件） |
