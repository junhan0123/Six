# Overlay Architecture Audit — Xiao6 Frontend

> **Sprint**: Overlay System Preflight Audit v1.0 · **Mode**: Audit → Report → STOP
> **Date**: 2026-08-05 · **依据**: DESIGN.md §6.3 Z-index Scale / §6.4 Backdrop；源码静态扫描

---

## 0. 审计纪律声明

纯只读。下列分析基于对 `styles.css` / `ui2.css` / `premium.css` / `companion.css` 及 20 个 JS 管理器的静态检索，未修改任何代码。

---

## 1. Z-index 体系（核心问题）

### 1.1 DESIGN.md §6.3 定义的设计令牌

```css
--z-base: 1;  --z-rail: 5;  --z-popover: 30;  --z-modal: 60;  --z-toast: 82;  --z-companion: 9999;
```

补充：`.os-shell` z5；`#solarCanvas` z0；`#universeView` z30；`.os-chat-drawer` z25；`.os-chat-fab` z24。

### 1.2 实际使用的字面 z-index（styles.css，近乎全部硬编码，未引用令牌）

| 实际值 | 对应 Overlay | 与设计令牌对比 |
|--------|-------------|----------------|
| 0 | `#solarCanvas` 背景 | = `--z-base` ✅ |
| 1–7 | 内容/HUD/轨道 | ≈ base/rail ✅ |
| 18 / 20 / 30 | HUD 浮动件 | ≈ popover(30) ✅ |
| 40 | L35 辉光层 | 未定义 |
| 55 / 56 | memq 相关 | 未定义 |
| **60** | `mem-panel` `term-panel` `wc-panel` L1440/1679/1819/1958/3394/3441（约 10 处全屏模态类） | = `--z-modal` ✅（巧合一致，但非引用令牌） |
| 61 | `memq-panel` | 未定义 |
| 80 | `settings-overlay` | 介于 modal(60) 与 toast(82) |
| 81 | `settings-panel` | 未定义 |
| **82** | `sysprompt-overlay` `cap-overlay` L3323 | = `--z-toast` ⚠️ 遮罩复用 toast 层级 |
| 83 | `sysprompt-panel` `cap-panel` | 未定义 |
| 85 / 86 | companion 相关(L2971/2982) | 未定义 |
| **90** | `cp-overlay`（命令面板） | 高于 settings(80) ⚠️ 瞬时面板压过设置抽屉 |
| **95** | `zz-panel` | 高于 toast(82)/modal(60) ⚠️ 压过设置与模态 |
| 100 | L564 / L1383 | 未定义 |
| **200** | `more-dropdown` | 远高于 `--z-popover:30` ⚠️ 下拉压过几乎所有面板 |
| **9000** | `modal-mask` | ≠ `--z-modal:60`、**≠** `--z-toast:82` ❌ 完全脱离尺度 |
| 9999 | companion（令牌 `--z-companion`） | = 令牌 ✅（仅此与令牌对齐） |

### 1.3 架构结论

1. **设计令牌 `--z-*` 几乎未被 overlay 引用**——所有 overlay 用硬编码字面量，令牌形同虚设。
2. **`modal-mask` 用 9000 脱离整套尺度**，是历史遗留的「暴力置顶」，会压过除 companion(9999) 外的一切。
3. **层级倒挂**：`more-dropdown`(200) > `zz-panel`(95) > `cp-overlay`(90) > `settings`(80-83) > `modal`(60)。在面板（z80-83）中弹出的下拉（z200）会盖住模态（z9000 除外），但 `zz-panel`(95) 却能盖住设置/系统提示面板—— escalation 无序。
4. **无 `--z-popover` 消费者**：下拉/菜单/气泡未落到 30，而是 200（companion 局部 10-13）。

---

## 2. 显示 / 隐藏方式（5 种并存范式）

| 范式 | 使用者 | 备注 |
|------|--------|------|
| **`.show` 类** | toast · modal-mask · more-dropdown · mic-overlay · tg 提示 · onboarding · tasks-root · capabilities-overlay | 最常用，但触发时机/过渡各异 |
| **`.open` 类** | settings-panel · sysprompt-panel · cap-panel · chatArea | 配合 overlay `.show` 双类联动 |
| **`hidden` 属性** | mobile-app 元素 · mem-panel · onb-overlay | 布尔属性，无过渡 |
| **body 类切换** | `cp-mode`(command-palette) · `memq-mode`(memory-query) · `hotspot-mode` · `hs-*` | overlay 自身 `display:none`，靠 body 类显隐 |
| **`aria-hidden` + 状态类** | `zz-panel`（`--entering`/`--leaving`） | 唯一带显式进入/离开生命周期态 |

> **结论**：同一「开合」语义有 5 种实现，无统一原语。新增 overlay 时开发者需从 5 种范式里挑，且过渡动画/可达性各写各的。

---

## 3. 生命周期管理

- **zz-panel** 是唯一具备显式状态机的 overlay（`aria-hidden` + `--entering`/`--leaving`，app.js:2190-2224），含进入/离开动画与 `aria-live="polite"`（index.html:1164）。
- 其余 overlay 仅有「开/关」二元态，无 entering/leaving 过渡钩子（部分靠 CSS transition 隐式完成，但 JS 无状态跟踪）。
- **overlay-runtime.js** 定义了 5 态生命周期枚举（`OPEN/UPDATING/ACTIVE/COMPLETED/CLOSED`）但**仅用于数据模型，前端无渲染消费**（见 Inventory §3）。

---

## 4. ESC 处理（16+ 全局监听器，去中心化）

- 每模块各自 `document.addEventListener('keydown', e => { if(e.key==='Escape') ... })`，**无中央 ESC 分发器**。
- **守卫不一致**：
  - 守卫开启态：`capabilities-view:182`(`panel.contains('open')`)、`command-palette:202`(`_open`)、`doc/map/memory-panel/memory-query/review/video/weather/sysprompt/tasks/hotspot`(各自 `*Open` 标志)、`app.js:2223`(`aria-hidden==='false'`)。
  - **未守卫**：`app.js:756`（`closeModal` 无条件触发，监听器在 `modalRoot` 首次调用时注册一次，永不移除）、`settings.js:128`（`if Escape close()` 无开启守卫）。
- **风险**：监听器随模块加载持续累积；未守卫者在 overlay 关闭态仍响应 Escape（虽 `close()` 幂等无害，但语义脏、且若将来 close 有副作用会误触发）；多 overlay 同开时 ESC 行为依赖各模块守卫正确性。

---

## 5. 点击外部关闭

- 实现方式各异，无统一 backdrop-click 原语：
  - modal：`e.target === _modalMask` → close（app.js:752）
  - command-palette：`e.target.id === 'cpOverlay'` → closeCp（command-palette:194）
  - settings/sysprompt/cap/zz：经各自 overlay 背景点击（per-module）
  - more-dropdown / companion quick-menu：经 document 级 click 关闭
- **风险**：部分 overlay（如 `zz-panel`、`mem-panel`）是否完整实现外部点击关闭需逐模块核对；范式不一导致边界行为（点到面板内子元素 vs 遮罩）容易写错。

---

## 6. 焦点管理（系统性缺口）

| 能力 | 覆盖情况 |
|------|----------|
| 打开时聚焦首个可聚焦元素 | **仅 command-palette(L180) / companion(L365)** |
| 焦点陷阱（focus trap） | **0 处** |
| 背景 `inert` / 禁用背景焦点 | **0 处** |
| 关闭时焦点归还（restore） | **0 处**（modal/zz-panel/panel 均未记录 opener 焦点） |

> **结论**：除命令面板与 companion 输入框外，**所有 modal/panel 均无焦点管理**。打开 overlay 后 Tab 仍能逃到背景元素，违背 WCAG 2.4.3 / 2.1.2；DESIGN.md §7 Do's #4 要求保留 `:focus-visible` 环，但「打开 overlay 即陷阱」的基线能力缺失。

---

## 7. 遮罩管理（Backdrop）

- **显式遮罩 div**：`settings-overlay`/`sysprompt-overlay`/`cap-overlay`（`background:rgba(4,7,11,.72); backdrop-filter:blur(6px)`，z80/82）。
- **modal-mask**：`position:fixed;inset:0;z-index:9000`，背景/模糊需核对（疑似未用令牌 blur）。
- **cp-overlay**：z90，是否有背景模糊需核对。
- **zz-panel**：index.html 中**无独立遮罩 div**，为居中浮卡（z95），打开时不dim背景 → 与 modal 视觉语义冲突。
- **一致性缺口**：DESIGN.md §6.4 定义 `--blur-glass:26px`，但实际遮罩用 `blur(6px)`/`blur(10px)` 字面量，偏差远超 2px 容差（Inventory 已记 premium.css `blur(28px)` 偏差）。

---

## 8. 架构总评

| 维度 | 评级 | 主要问题 |
|------|------|----------|
| Z-index 体系 | ❌ 失败 | 令牌未用，9000/200/95 倒挂，无统一尺度 |
| 显隐范式 | ⚠️ 差 | 5 种并存，无原语 |
| 生命周期 | ⚠️ 中 | 仅 zz-panel 有状态机；数据层 5 态未落地 |
| ESC 处理 | ❌ 失败 | 16+ 去中心化监听，部分未守卫 |
| 点击外部 | ⚠️ 中 | per-module，无统一原语 |
| 焦点管理 | ❌ 失败 | 无 trap/inert/restore（仅 2 处聚焦输入框） |
| 遮罩 | ⚠️ 中 | 模糊值未令牌化；zz-panel 无遮罩 |

→ 进入 [OVERLAY_DUPLICATION_REPORT.md](./OVERLAY_DUPLICATION_REPORT.md) 量化重复实现。
