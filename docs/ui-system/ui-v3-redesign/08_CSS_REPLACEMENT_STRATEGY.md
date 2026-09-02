# 08 · CSS 替换策略（CSS REPLACEMENT STRATEGY）

> **阶段**：UI-v3 Clean Reconstruction · Phase A-0（Bridge Design Only，不改 CSS 文件）
> **依赖**：`00`（废弃五代叠加 + 9 色选择器 + 玻璃卡片）、`05`（视觉语言）、`06`（Phase A/G）、`07`（DOM 容器）
> **目的**：定义从"五代叠加"到"单一 `ui-v3.css`"的替换路径、token 继承边界、z-index 规划、动画规范。全程不修改任何 `.css` 文件。

---

## 1. ui2.css 五代叠加清理方案

### 1.1 当前首屏 CSS 加载链（index.html `<head>`，实测顺序）

```
styles.css                  (8)   原始聊天皮肤（属 .app，不在 v3 首页）
premium.css                 (9)   同上
runtime-viz.css             (10)  通道可视化（属 chat）
execution-channel.css       (11)  同上
ui2.css                     (13)  ★ Phase 10.1 OS 首页基础（含 token + 旧布局）
spatial-runtime.css         (14)  空间运行时
ui4b-first-screen.css       (16)  ✗ 五代叠加 ①
ui4b-explore-transition.css (18)  ✗ 五代叠加 ②
ui4c-visible-upgrade.css    (20)  ✗ 五代叠加 ③
ui4c-unified-home.css       (22)  ✗ 五代叠加 ④
ui4d-home-experience.css    (24)  ✗ 五代叠加 ⑤
ui5d-first-screen-polish.css(26)  ✗ 五代叠加 ⑥
ui-v2-readout.css           (28)  ✗ P0-B 补丁（叠加）
ui-v2-workspace.css         (29)  ✗ P1 补丁（叠加）
ui-v3.css                   (新增) ★ v3 单一样式表（置于最后）
```

> 这正是 v2 审计判定"五代叠加治不了结构病灶"的物理证据：6 个 ADDITIVE 化妆层 + 2 个补丁，全部在 ui2 之后叠加。

### 1.2 清理策略（分阶段，可逆）

| 阶段 | 动作 | 说明 |
|---|---|---|
| **Phase A（脚手架）** | `ui-v3.css` 链接置于**最后**（最高层叠） | 不删任何旧链接；回滚安全 |
| **Phase A–F** | v3 用 `body.v3-home` 作用域 + 链接顺序压过旧样式 | 旧 `.os-*` 节点 `display:none`，旧 CSS 选择器无可见目标 |
| **Phase G（清理）** | 从 `<head>` 移除 `ui4b*/ui4c*/ui4d*/ui5d*/ui-v2-*` 链接 | 仅清理**首屏**叠加；`styles.css/premium.css/runtime-viz/execution-channel` 属 `.app` 视图，**保留其自身加载**（不动 chat） |
| **Phase G+** | `ui2.css` 在首屏不再被引用（其 token 已复制进 `ui-v3.css`） | 若 `.app` 视图不依赖 ui2，可一并移除；否则保留 |

**关键**：清理是"移除 `<link>`"，不是"删除文件"——文件保留，出问题时把链接加回即可（配合 `body.v3-home` 开关双保险回滚）。

### 1.3 旧布局规则如何"自然失效"

v3 首页**不出现** `.os-shell / .os-nav / .os-hud / .os-side / .os-panel / .os-bottom` 这些类名（它们只在被 `display:none` 的旧 `.os-shell` 内）。`ui-v3.css` 只定义 `.v3-*` 作用域规则 + 对 `#osCoreCanvas`/`#osDock` 的 `body.v3-home` 重定位。**旧 CSS 的布局规则因无匹配元素而沉默**，无需逐一覆写。

---

## 2. ui-v3.css 替代边界

### 2.1 负责（IN）

| 范围 | 说明 |
|---|---|
| 首屏存在界面布局 | `.v3-presence` 中心辐射；`.v3-core`/`.v3-context`/`.v3-intent`/`.v3-ambient` 定位 |
| 组件视觉 | AI Core 光核/呼吸、Context 文字层、Intent Line 输入线、Ambient 微点、World Overlay |
| Token 体系 | 颜色/空间/圆角/缓动/z-index（复制自 ui2，自命名） |
| 动效 | ≤400ms 状态过渡/呼吸/淡入/浮层（见 §5） |
| 深色主题 | 默认深色；Light 变体（若交付）仅反转明度 |

### 2.2 不负责（OUT）

| 范围 | 归属 |
|---|---|
| `.app` 聊天视图样式 | `styles.css` / `premium.css` / `runtime-viz.css` / `execution-channel.css` |
| `#universeView` 开发者视图 | 既有 galaxy/solar CSS |
| 旧 OS 首页布局规则 | `.os-shell` 等（已被隐藏，不继承） |
| 9 色主题切换 | 废弃；仅保留单强调色 `--core-color` |

### 2.3 替换而非叠加（根治病灶）

v3 首页稳定后，**首屏只加载 `ui-v3.css` 一个样式表**（Phase G 移除其余叠加链接）。不再有"化妆层盖化妆层"的累积债务。

---

## 3. token 继承策略

### 3.1 原则

- **不 `@import ui2.css`**：`@import` 会把 ui2 的**旧布局规则**一并引入，旧病灶复活。
- **复制 token 值，自命名**：把 ui2 的 token 定义（颜色/空间/圆角/缓动/z-index 阶梯）**值**复制进 `ui-v3.css` 的 `:root`，v3 用自己命名，零运行时依赖 ui2。
- **v3 新增 token**：`--bg / --bg-raise / --core-color / --text-bright / --text-base / --text-dim / --line / --line-strong`（来自 `05` §2）。

### 3.2 继承映射表（ui2 → v3）

| ui2 token（沿用命名） | v3 取值/动作 | 说明 |
|---|---|---|
| `--space-2/3/4/6/8` | 复制值 (8/12/16/24/32) | 空间阶梯直接复用 |
| `--r-2/3/4` | 复制值 (8/12/16) | 圆角克制 |
| `--ease-soft` 等缓动 | 复制值 | 统一缓动，不新造 |
| `--z-ground … --z-top`（14 级） | 复制为 v3 同名 ladder | z-index 阶梯复用（见 §4） |
| `--font-display / --font-ui / --font-mono` | 复制（系统字体栈） | 字体策略复用 |
| `--accent`（旧） | **废弃**，改用 `--core-color` | 单强调色 = AI 状态色 |
| 颜色 `--bg-*`/`--text-*` | 用 v3 新值（05 §2.1）覆盖 | 深色优先新基调 |

### 3.3 防冲突

- v3 所有 token 在 `ui-v3.css` 的 `:root` 中**自包含定义**；不读取 ui2 变量。
- 若 Phase G 前 ui2 仍加载，因 v3 链接在后且 `body.v3-home` 作用域，v3 的 `:root` 变量与 ui2 同名变量**仅在 v3 作用域内生效**（CSS 变量按层叠，后定义者胜），旧 `.os-*` 节点已隐藏，无冲突。
- 明确**禁止** v3 复用 `.os-*` 类名以避免旧规则命中。

---

## 4. z-index 规划

复用 ui2 的 14 级阶梯概念（`--z-ground` → `--z-top`），在 `ui-v3.css` 中映射为 v3 层级。v3 是独立表面，使用自包含整数映射：

| v3 层级 | z-index | token（建议） | 内容 |
|---|---|---|---|
| 世界背景（solarCanvas 隐藏态） | `-1` | `--z-ground` | 不在首屏显示 |
| 存在界面基底 | `0` | `--z-surface` | `.v3-presence` 常态流 |
| Context Layer | `20` | `--z-context` | 环绕信息（低于 Core，不抢中心） |
| AI Core | `30` | `--z-core` | 视觉重心，高于 Context |
| Intent Line | `40` | `--z-intent` | 底部输入，用户必见 |
| Ambient 微点 | `42` | `--z-ambient` | 与 Intent 同级，角落 |
| Overlay（世界/设置/抽屉） | `900` | `--z-overlay` | 覆盖于存在界面之上 |
| 关键模态/Toast | `1000` | `--z-top` | 最高，错误确认等 |

**规则**：
- Overlay 永远高于存在界面四层；关闭即落回 `0`。
- AI Core(30) > Context(20)，确保"中心权重最高"。
- Intent(40) > Core(30)，确保输入永远可达（不被 Core 遮挡）。
- 全部落在 ui2 阶梯语义内，不跳号、不冲突。

---

## 5. 动画规范

### 5.1 统一约束

- 所有动效 **≤400ms**，统一缓动 `var(--ease-soft)`。
- 目的导向：每次动效表达"状态变化"或"空间关系"，禁止装饰性炫技（旋转/翻转/粒子/扫描线/弹跳/3D 透视）。
- 尊重 `prefers-reduced-motion`：开启时呼吸/淡入降级为静态。

### 5.2 动效清单（来自 `05` §5，落到具体声明）

| 动效 | 时长 | 缓动 | 目的 | 关键帧/属性（规格） |
|---|---|---|---|---|
| 状态色过渡 | 320ms | `ease-soft` | 小6状态变化 | `transition: --core-color 320ms var(--ease-soft)`（或 `background-color`） |
| AI Core 呼吸 | 4000ms 循环 | linear/soft | 表达"活着" | `@keyframes v3-breathe { 0%,100%{opacity:.5;scale:1} 50%{opacity:.8;scale:1.02} }` |
| 浮层进出 | 240ms | `ease-soft` | Overlay 空间关系 | `@keyframes v3-overlay-in { from{opacity:0;translate:0 8px} to{opacity:1;translate:0} }` |
| Context 淡入 | 280ms | `ease-soft` | 信息出现不突兀 | `@keyframes v3-fade-in { from{opacity:0} to{opacity:1} }` |
| 焦点微放 | 200ms | `ease-soft` | hover/点击 Core 可交互暗示 | `transition: transform 200ms var(--ease-soft)` |
| Intent Line 输入线 | 200ms | `ease-soft` | 输入时状态色细线浮现 | `transition: border-color 200ms var(--ease-soft)` |

### 5.3 禁用清单（旧 Galaxy 病灶，v3 一律禁止）

星系旋转 · 粒子爆炸 · 3D 翻转 · 霓虹扫描线 · 弹跳 · 透视位移 · 多色闪烁。

### 5.4 reduced-motion 降级（规格）

```css
@media (prefers-reduced-motion: reduce) {
  .v3-core__ring, .v3-ctx-block, .v3-overlay { animation: none !important; transition: none !important; }
}
```

### 5.5 颜色驱动（不新造）

所有动效的"色"来自 `var(--core-color)`，其值由 `avatar-state.color(state)` 注入（见 `02` §3）。v3 不定义任何状态颜色常量。

---

## 6. 与实施计划的对接

| 本文节 | 对应 `06` 阶段 | 动作 |
|---|---|---|
| §1 清理方案 | Phase A / G | 加 `ui-v3.css` 链接 / 移除叠加链接 |
| §2 替代边界 | Phase A–G | 单一样式表承载首屏 |
| §3 token 继承 | Phase A | 复制 ui2 token 进 `ui-v3.css` |
| §4 z-index | Phase C–F | 按层级映射落地 |
| §5 动画 | Phase C/D | 按规范落地 AI Core / Intent / Overlay 动效 |

→ 下一文档 `09_COMPONENT_BOUNDARY.md` 定义五组件职责边界。
