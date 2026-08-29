# UI-4B-2A Explore Transition Foundation v1.0 · Implementation Report

**身份**：Senior Frontend Engineer / AI OS Interaction Engineer  
**日期**：2026-08-09  
**状态**：✅ 完成；STOP 等待 Review（不进 UI-4B-2B Panel Migration、不提交 Git）

---

## 1. Before / After

### 1.1 审计结论：当前硬切换链路

触发（未改动）：

- `index.html:1461-1476` — Ctrl/Cmd+U → `openUniverse()`：
  - `document.body.classList.add('universe-mode')`
  - `#universeView.classList.add('open')`
- Esc / `openChat()` / `galaxy-experience.js:_enterCapability()` 负责退出。
- `body.zz-explore` 为 UI-4A 预留钩子，**仍未接线**（触发器延后到 UI-4）。

硬切表现（`ui2.css:927-948`）：

| 元素 | 默认 Operation Focus | universe-mode（硬切） |
|------|---------------------|----------------------|
| `#osShell`, `#app` | `visibility: visible` | `visibility: hidden; pointer-events: none`（二进制，无过渡） |
| `#universeView` | `display: none` | `display: block; z-index: 30; background: var(--bg)`（不透明实底页） |
| `#solarCanvas` | z-index 默认 | `z-index: 29; opacity: 1` |
| `.galaxy-veil` | `opacity: 1` | `opacity: 0` |

**根因**：Operation Layer 用 `visibility:hidden` 瞬灭，而 `#universeView` 是一块不透明实底页 + `display` 突变。二者共同制造了「Workspace / Galaxy 像两个页面」的导航跳转感。

### 1.2 After：连续空间注意力迁移

目标达成：**Explore State = Attention Redistribution State**。

| 维度 | Before | After |
|------|--------|-------|
| Operation Layer（Workspace / Dock / HUD / Panel） | `visibility:hidden` 瞬灭 | `opacity: 0.35` + `blur(7px)` + `scale(0.984)` + `pointer-events:none`，450ms 连续退后 |
| `#universeView` | 不透明实底页 | 40% 半透明空间纱；Galaxy / OS 在背后连续可见 |
| World Layer | 暗化 `brightness(0.72)` + 叙事纱 | 提亮 `brightness(1)` + 叙事纱淡出 |
| 交互语义 | 切到新页面 | 同一连续空间内，注意力重新分配到世界层 |

---

## 2. Transition Model

### 2.1 空间模型（沿用 UI-3B v1.1 冻结）

- **World Layer**：`#solarCanvas` + `.galaxy-veil`（z 0–4）
- **Operation Layer**：`#osShell` / `#app` + Command Dock + Panels + HUD（z 18+）
- **Global AI Intent Entry**：Command Dock（底部永驻）

### 2.2 Explore = Attention Redistribution

默认态（Operation Focus）：

- Operation Layer 全显、可交互。
- World Layer 暗化至 `brightness(0.72)`，作为连续背景在场。

Explore / Universe 态（World Focus）：

- World Layer 提亮至 `brightness(1)`，叙事纱淡出。
- Operation Layer 不消失，而是**空间后退**：
  - `opacity: 0.35`（注意力权重降低）
  - `filter: blur(7px)`（景深退后）
  - `transform: scale(0.984)`（轻微远离）
  - `pointer-events: none`（点击穿透到 Galaxy）
- `#universeView` 退为 40% 半透明纱，保留 GEL 卡片可读性，但不再是一块不透明新页。

### 2.3 缓动参数

全部复用既有 Motion Token，**零新令牌**：

- `--attention-dur: var(--dur-slow)`（450ms）
- `--attention-ease: var(--ease-premium)`（cubic-bezier(0.16, 1, 0.3, 1)）

> 注：原 `spatial-runtime.css` 中 `--attention-dur: var(--dur-med)` 指向一个 ui2.css 中不存在的令牌，导致整条 `transition` 声明被丢弃（`transition-duration: 0s`）。本次将其修正为 `--dur-slow`，同时修复了 UI-4A 以来 `.solar-canvas` 亮度过渡无效的问题。

---

## 3. Files Changed

### 3.1 新增文件

#### `xiao6-ui/ui4b-explore-transition.css`（ADDITIVE，末位加载）

- **A1 Explore State Hook**：复用 `body.zz-explore`（UI-4A 预留）与 `body.universe-mode`（既有 Ctrl/Cmd+U 路径），不新增业务状态 / 不接线触发器。
- **A2 Transition Language**：覆盖 `ui2.css:933-934` 的 `visibility:hidden` 硬切，改为 `opacity`/`filter`/`transform` 连续缓动。
- **A3 Remove Hard Page Feeling**：`#universeView` 不透明实底页 → 40% 半透明空间纱；保留 `display:none/.open` 机制（不删除、不重写）。

#### `docs/ui-system/ui4b-explore-transition/_probe_explore.mjs`

CDP 验证探针：

- 默认 / Explore(`zz-explore`) / Universe(`universe-mode + #universeView.open`) 三态结构断言。
- 核心断言：Operation Layer 不再 `visibility:hidden`，而是 `opacity≈0.35 + blur + transition>0`。
- 回归断言：JS 错误 0、无横向溢出。

### 3.2 修改文件

#### `xiao6-ui/index.html`

在 `ui4b-first-screen.css` 之后新增 `ui4b-explore-transition.css` 链接，确保覆盖权威位于末位。

```html
<link rel="stylesheet" href="ui4b-explore-transition.css?v=20260809a2" />
```

#### `xiao6-ui/spatial-runtime.css`（令牌别名修正）

```css
:root {
  --attention-ease: var(--ease-premium);
  --attention-dur: var(--dur-slow);   /* 原 var(--dur-med) 在 ui2.css 中不存在 */
}
```

这是一次必要的上游修正：原 `--attention-dur` 解析为无效值，导致 `.solar-canvas` 的亮度变化以及所有依赖它的过渡都退化为 `0s`。

### 3.3 生成文件（验证产物）

- `docs/ui-system/ui4b-explore-transition/_probe_explore.json`
- `docs/ui-system/ui4b-explore-transition/shots/explore_default.png`
- `docs/ui-system/ui4b-explore-transition/shots/explore_zz.png`
- `docs/ui-system/ui4b-explore-transition/shots/explore_universe.png`

### 3.4 红线检查

- ✅ 未修改 `solar-system.js` / Three.js renderer / Galaxy 数据 / AppState / EventBus / Backend / Agent。
- ✅ 未重写导航（Ctrl/Cmd+U 触发逻辑零改动）。
- ✅ 未修改功能入口。
- ✅ 未新增 Event Contract（DOMAIN=71 / SYSTEM=8 未扩张）。
- ✅ 未做 Panel Lifecycle Migration（`.panel-lifecycle-*` 三态未迁移）。
- ✅ 未触碰 `--presence-color` 三唯一权威（P8 保护）。
- ✅ 全部颜色经 `color-mix()` 从既有令牌派生，无裸色值。

---

## 4. Existing State Compatibility

### 4.1 `body.universe-mode`（Ctrl/Cmd+U 真实路径）

- 触发器、函数入口、`#universeView.open` 机制完全保留。
- 仅视觉表现从「硬页」改为「空间纱 + 操作层连续退后」。
- 退出路径（Esc / `openChat()` / `_enterCapability()`）行为不变。

### 4.2 `body.zz-explore`（UI-4A 预留钩子）

- 本阶段**仍不接线触发器**（按 UI-4A 设计延后到 UI-4）。
- 过渡语言已就位；UI-4 触发控件接入后即可立即生效，无需再改 CSS。

### 4.3 `chat-mode` / 默认首屏

- 全部规则限定于 `body.zz-explore` / `body.universe-mode`。
- 默认 Operation Focus 与聊天模式零副作用（探针 A1-A5 验证）。

### 4.4 加载顺序与层叠

```
styles.css → premium.css → runtime-viz.css → execution-channel.css
  → ui2.css → spatial-runtime.css → ui4b-first-screen.css → ui4b-explore-transition.css
```

`ui4b-explore-transition.css` 仅覆盖本文件显式声明的选择器（`#osShell`/`#app` opacity+filter+transform、`#universeView` background、`.galaxy-veil` opacity），不侵入既有规则。

---

## 5. Regression Test

### 5.1 UI-4B-2A 验证探针：20/20 ALL_PASS

```text
[explore] 20/20 checks passed. ALL_PASS
```

关键事实：

| 检查项 | 结果 | 证据 |
|--------|------|------|
| 默认 `#osShell` 无硬切 | PASS | `visibility=visible, opacity=1, blur=none` |
| Explore `#osShell` 不再 `visibility:hidden` | PASS | `visibility=visible` |
| Explore `#osShell` opacity 退后 | PASS | `0.35` |
| Explore `#osShell` 景深 blur | PASS | `blur(7px)` |
| Explore `#osShell` 连续缓动 | PASS | `transition-duration=450ms` |
| Explore `#osShell` 点击穿透 | PASS | `pointer-events:none` |
| Explore `#universeView` 半透明纱 | PASS | `alpha=0.40` |
| Explore `.galaxy-veil` 淡出 | PASS | `opacity=0` |
| Explore `.solar-canvas` 世界层上浮 | PASS | `brightness(1)` |
| Universe 路径同上 | PASS | 所有关键指标一致 |
| 无 JS 运行时错误 | PASS | `errCount=0` |
| 无横向溢出 | PASS | `scrollWidth=1920 ≤ innerWidth=1920` |

### 5.2 Phase 8 AI Presence 回归：20/0 PASS

```text
AI PRESENCE (Phase 8): PASS  (passed=20, failed=0)
```

本阶段为纯 CSS 改动，未触及 `avatar-state.js` / `index.html` HUD 写入 / `--presence-color` 权威。

### 5.3 事件合约与架构红线

- 未新增任何 JS 文件或事件派发代码。
- `DOMAIN=71` / `SYSTEM=8` 未扩张。
- AppState / EventBus / Backend / Agent 接口零改动。

---

## 6. UI-4B-2B Preparation

### 6.1 本阶段已交付

- `body.zz-explore` 与 `body.universe-mode` 共用的连续过渡语言。
- `#universeView` 从硬页切换为空间注意力纱。
- Operation Layer 硬隐藏改为连续退后。
- 共享 `--attention-dur` 令牌修正为有效值。

### 6.2 明确留给 UI-4B-2B / UI-4 的工作

- **Panel Lifecycle Migration**：`.panel-lifecycle-{dormant,attention,active}` 三态到 `PanelManager` 的打标与行为迁移仍在红线禁止范围内，未在本阶段实施。
- **`body.zz-explore` 触发控件接线**：候选触发入口（Command Dock 动作 / HUD 按钮 / 键盘快捷键）由 UI-4 产品决策后接入；本阶段仅确保 CSS 规则就位。
- **动画触发时序微调**：本阶段验证了终态事实；实际触发时（UI-4）可基于用户反馈微调 `--operation-opacity-explore`（0.35）或 veil alpha（0.40），二者均通过既有 CSS 变量可控，无需架构改动。

### 6.3 STOP 声明

**当前停在 UI-4B-2A Foundation 边界**：已完成 Audit → Design → Implement → Verify → Document。  
**不进入 UI-4B-2B Panel Migration。不提交 Git。等待 Review。**
