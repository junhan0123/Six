# Overlay Inventory Report — Xiao6 Frontend

> **Sprint**: Overlay System Preflight Audit v1.0
> **Mode**: Audit → Report → STOP（纯只读，禁改代码/CSS/JS/HTML）
> **Date**: 2026-08-05
> **Scope**: 10 类 Overlay 的现有实现数量盘点（CSS 类 / JS 管理器 / HTML 结构 / 事件绑定）
> **依据**: `xiao6-ui/DESIGN.md` §4.7 / §6.3；源码静态扫描

---

## 0. 审计纪律声明

本文件为**只读盘点**。所有结论均来自对 `xiao6-ui/` 下 CSS/JS/HTML 的静态检索，未发现任何代码被修改。下列行号指向扫描时刻的源码位置，供后续 Implementation Sprint 精确定位。

---

## 1. 10 类 Overlay 实现数量总表

| # | 类别 | 状态 | CSS 类（styles.css 为主） | JS 管理器 | HTML 容器 |
|---|------|------|---------------------------|-----------|-----------|
| 1 | **Dialog / Modal** | ✅ 有（2 套并存） | `.modal-mask`(L2500,z9000) `.modal-card`(L2508) `.modal-close`(L2524)；`premium.css` `.wx-modal-head`/`wx-modal` | `app.js` `showModal/closeModal/modalRoot`(L744-816) | 动态挂载 `.modal-mask` 到 `<body>`（不在 index.html） |
| 2 | **Popup** | ✅ 有（轻量） | `.more-dropdown`(L2313,z200) `.tg-*` tooltip 类(L414-422) | `app.js` 下拉/工具提示切换(L2140-2206) | `#moreMenuWrap`/`#moreDropdown`(index.html:275-277) |
| 3 | **Toast** | ✅ 有（**3 套重复**） | `.toast`(L537) | `app.js` `toast()`(L306) · `error-boundary.js` `toast()`(L6) · `mobile-app.js` `toast()`(L15) | `#toast`(index.html:399) |
| 4 | **Notification** | ⚠️ 无独立组件 | 无 `.notification` 类 | 折叠进 toast + companion `onProactiveMessage` 气泡 | companion 窗口气泡（`status-bubble`） |
| 5 | **Tooltip** | ⚠️ 无组件 | 无 `.tooltip` 类（仅原生 `title` 属性，如 `zz-panel-close` title="关闭"） | 无 | — |
| 6 | **Dropdown** | ✅ 有（1 套） | `.more-dropdown`(L2313) | `app.js`(L2140-2206) | `#moreDropdown` |
| 7 | **Menu** | ✅ 有（companion） | `.quick-menu`(companion.css:200,z10) `.quick-menu-sep` | `companion.js`(L340-560) | companion 窗口内 |
| 8 | **Context Menu** | ✅ 有（companion，原生右键） | 复用 `.quick-menu` | `companion.js` `contextmenu` 监听(L522) | companion 窗口内 |
| 9 | **Overlay Layer（遮罩层）** | ✅ 有（多套并存） | `.settings-overlay`(L2741,z80) `.sysprompt-overlay`(L2803,z82) `.cap-overlay`(L2820,z82) `.cp-overlay`(L2146,z90) `.onb-overlay` `.mem-graph-wrap`(L2473) | 各面板 JS | `#settingsOverlay`/`#sysPromptOverlay`/`#capOverlay`/`#onbOverlay` |
| 10 | **Drawer / Panel（抽屉/面板）** | ✅ 有（**~15 套并存**） | `.settings-panel`(z81) `.sysprompt-panel`(z83) `.cap-panel`(z83) `.hotspot-panel`(L618) `.mem-panel`(z60) `.memq-panel`(z61) `.term-panel`(z60) `.wc-panel`(z60) `.zz-panel`(L3122,z95) `.doc*` `.map*` `.review*` `.tasks*` `.video*` `.os-chat-drawer`(z25) | settings.js / sysprompt.js / capabilities-view.js / memory.js / memory-panel.js / memory-query.js / hotspot.js / doc.js / map.js / review.js / tasks.js / video.js / weather.js / onboarding.js / app.js(chatArea,zzPanel) | `#settingsPanel`/`#sysPromptPanel`/`#capPanel`/`#zzPanel`/`#memPanel`/`#onbOverlay` |

> 注：companion 窗口（`companion.html/css/js`）为独立 Electron 窗口，其 `z-index`（10/11/12/13）仅在 companion 窗口局部生效，不与主窗口 z 轴竞争。

---

## 2. CSS 类清点（按文件）

- **styles.css（199KB）**：overlay 相关类约 **60+** 个选择器，分布于 L28–L3701。核心家族：`toast` / `modal-*` / `settings-*` / `sysprompt-*` / `cap-*` / `hotspot-panel` / `mem-panel` / `memq-panel` / `more-dropdown` / `zz-panel*` / `cp-overlay` / `term-panel` / `wc-panel` / `onb-*` / `os-chat-drawer` / `os-chat-fab` / `bubble`（会话气泡，非 overlay）。
- **premium.css**：`.modal-card::after`、`.wx-modal-head`、`.wx-modal`（微信弹窗变体，重复 Dialog 实现）。
- **companion.css**：`.quick-menu` / `.status-bubble` / `.quick-menu-sep`（companion 窗口菜单/气泡）。
- **ui2.css**：仅令牌（`--z-*` / `--elev-*` / `--blur-glass`），**未定义任何 overlay 组件类**。
- **runtime-viz.css / execution-channel.css**：含 overlay-ish 可视化层（RuntimeViz），属只读投影，不计入交互 overlay。

---

## 3. JS 管理器清点（~20 个独立模块）

| 模块 | 管理的 Overlay | 开关方式 |
|------|---------------|----------|
| `app.js` | `toast`、`modal-mask`、`.more-dropdown`、`chatArea` 抽屉、`zz-panel` | `.show` / `.open` / `aria-hidden` |
| `overlay-runtime.js` | **纯数据模型**（Overlay Model），非渲染器，无生产者 | —（仅 `getModel()`/`subscribe()`） |
| `command-palette.js` | `cp-overlay` | body `.cp-mode` |
| `error-boundary.js` | 自带 `toast` | `.show` |
| `mobile-app.js` | 自带 `toast` | `.hidden` |
| `companion.js` | `quick-menu`、`status-bubble` | `[hidden]` / 右键 contextmenu |
| `settings.js` | `settings-overlay`+`settings-panel` | `.show`+`.open` |
| `sysprompt.js` | `sysprompt-overlay`+`sysprompt-panel` | `.show`+`.open` |
| `capabilities-view.js` | `cap-overlay`+`cap-panel` | `.show`+`.open` |
| `memory.js` | `mem-panel` | `hidden` 属性 |
| `memory-panel.js` | 记忆网络面板 | `.open`/ESC |
| `memory-query.js` | `memq-panel` | body `.memq-mode` |
| `hotspot.js` | `hotspot-panel` + `hs-region-popup` | body `.hotspot-mode` / `hidden` |
| `doc.js` | 文档面板 | `.open`/ESC |
| `map.js` | 地图面板 | `.open`/ESC |
| `review.js` | 简报/审阅面板 | `.open`/ESC |
| `tasks.js` | 任务 overlay | `.show` |
| `video.js` | 视频面板 | `.open`/ESC |
| `weather.js` | 天气 modal | `.open`/ESC |
| `onboarding.js` | `onb-overlay`+`onb-card` | `.show` |

---

## 4. 事件绑定清点

| 事件类型 | 绑定位置数 | 说明 |
|----------|-----------|------|
| `keydown` → `Escape` | **16+** 个全局 `document.addEventListener` | 每模块各自注册（app.js:755/1146/2223、capabilities-view:182、command-palette:195、companion:553、doc:38、hotspot:747/775、map:37、memory-panel:38、memory-query:46、memory.js:605、review:36、settings:128、sysprompt:43、tasks:50、video:46）。**无中央 ESC 分发器。** |
| 点击外部关闭 | 每模块各自实现 | modal(`e.target===_modalMask`)、cp(`e.target.id==='cpOverlay'`)、其余经 overlay 背景点击 |
| 焦点管理 | **仅 2 处** | command-palette(`cpInput.focus()` L180)、companion(`cmdInput.focus()` L365) |
| 焦点陷阱 / `inert` | **0 处** | 全项目无 focus-trap、无 `inert`、无 `trapFocus` |

---

## 5. 关键数量结论

1. **Overlay 管理器 ~20 个**，"Modal/Panel/Dialog" 同一范式被**重复实现 ~15 次**（settings/sysprompt/cap/mem/memq/hotspot/doc/map/review/tasks/video/weather/onb/zz/term/wc/chat），各自带独立 overlay div + 面板 + JS 开合 + ESC + 点击外部。
2. **Toast 实现 3 套**（app.js 全局 / error-boundary / mobile-app），违背单一职责。
3. **Tooltip 与 Notification 无独立组件**——前者缺位（仅原生 title），后者被折叠进 toast/companion 气泡。
4. **overlay-runtime.js 是纯数据层，生产代码无消费者**（仅测试引用），与 DESIGN.md §4.7「管理器单一：overlay-runtime.js」表述不一致。
5. **焦点陷阱 / `inert` 全项目为零**，可访问性（WCAG AA）存在系统性缺口。

→ 进入 [OVERLAY_ARCHITECTURE_AUDIT.md](./OVERLAY_ARCHITECTURE_AUDIT.md) 做架构维度分析。
