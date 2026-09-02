# UI-5B · Legacy Workspace Visual Assimilation v1.0 — 实现报告

> **阶段**：UI-5B（承 UI-5A · Unified Galaxy Workspace）
> **身份**：Senior Frontend Engineer + AI OS UX Engineer
> **目标**：将现有 Legacy Chat Workspace 同化进 Unified AI OS Space，**消除用户点击聊天后"进入另一个软件"的感觉**；**非**新增聊天功能 / **非**重构业务逻辑 / **非**迁移 Runtime。
> **纪律**：Audit → Design → Minimal CSS/DOM Implementation → Verify → Document → **STOP**
> **完成判定**：▣ STOP，不进 UI-5C，等 Review。

---

## 0. 元信息 & 红线边界

| 项 | 内容 |
|---|---|
| 本次代码足迹 | `xiao6-ui/styles.css`(M) + `xiao6-ui/ui2.css`(M) |
| 严格禁止（全未触碰） | Backend / Agent / AppState / EventBus / DOMAIN·SYSTEM EVENTS / solar-system.js / galaxy-experience.js / app.js 业务逻辑 / 新增事件 / 新增状态体系 |
| AI Presence 三唯一 | 状态权威 `avatar-state.js` · 写入点 `index.html::refreshHud()` · 颜色权威 `ui2.css body[data-presence]` —— **全程零触碰** |
| 实现手段 | 纯 CSS 令牌化，**零新增 token**；零 JS/DOM 删除或新增 |

---

## A1 · Legacy App Visual Audit（审计证据）

**结论 1 — 选择器归属（级联安全）**
- `styles.css` 是全部聊天选择器（`.chat-history` / `.dock` / `.bubble` / `.msg.*` / `.conv-item` / `.chip` / `.speak-btn` / `.tool-overlay` / `.proactive-tag` 等）的**唯一定义方**。
- `ui2.css`（最后加载、视觉权威）**不触碰**任何聊天选择器 → 在 `styles.css` 做 A3 编辑级联安全、不会被后续覆盖。

**结论 2 — "另一个软件"感的根因**
大部分 legacy chat 已用令牌，真正的割裂感来自**硬编码 `rgba()` 字面色**（绕过 `--surface`/`--line` 等令牌、不随主题变化）：

| 类型 | 硬编码值 |
|---|---|
| 暗色渐变底色 | `rgba(8,12,17,.55)` / `rgba(5,7,10,.55)` / `rgba(8,14,20,.92)` |
| 白底残留 | `rgba(255,255,255,.03)` |
| 青色强调 | `rgba(34,211,238,.05 ~ .25)` |
| 琥珀强调 | `rgba(245,181,68,.08 ~ .14)` |

**结论 3 — 结构限制（已知局限）**
`.app` 固定 1920×1080 画布（JS-scale 结构）→ 禁触，列为已知局限（同 UI-5A R4）。

---

## A2 · Conversation Panel Assimilation Design

- Legacy Chat **重定义为 Operation Layer Conversation Panel（操作层会话面板）**，**禁止独立页面**。
- 沿用 UI-5A（见 `docs/ui-system/ui5-unified-galaxy-workspace/UI5A_IMPLEMENTATION.md`）的 **Capability Focus 连续空间**：聊天 / 宇宙视图均为"连续空间中的聚焦层"，OS 操作层用 dim/blur + opacity 连续过渡而非 `display:none`；`chat-mode #app` 提 `z-index:50`（高于 OS z5/z35，低于模态 z≥60）。
- Galaxy **重定位为 World Layer**（不删除、不提亮，除非 `universe-mode`）。

---

## A3 · Visual Unification Implementation（CSS 优先，零新增 token）

**改动文件**：`xiao6-ui/styles.css`（git `M`）
**配方**：全部改用 OS 令牌 `--glass` / `--panel` / `--panel-solid` / `--line` / `--line-strong` / `--shadow-glow`，强调色用 `color-mix(in srgb, var(--cyan)/var(--amber) …)`。

### Before → After 清单（含行号）

| 行 | 选择器 | Before（硬编码） | After（令牌化） |
|---|---|---|---|
| L335 | `.chat-history` | `linear-gradient(180deg,rgba(8,12,17,.55),rgba(5,7,10,.55))` | `background:var(--glass)` |
| L346 | `.chat-area.open .chat-history` | `box-shadow:0 0 42px rgba(34,211,238,.10)` | `box-shadow:var(--shadow-glow)` |
| L366 | `.dock` | `linear-gradient(...)` | `background:var(--glass)` |
| L380 | `.msg.user .avatar` | `rgba(245,181,68,.14)/.4` | `color-mix(in srgb,var(--amber) 16%/40%,transparent)` |
| L381 | `.msg.xiao6 .avatar` | `rgba(34,211,238,.14)` | `color-mix(in srgb,var(--cyan) 16%,transparent)` |
| L383 | `.bubble` | `rgba(255,255,255,.03)` | `background:var(--panel)` |
| L384 | `.msg.user .bubble` | `rgba(245,181,68,.08/.3)` | `color-mix(in srgb,var(--amber) 10%/30%,transparent)` |
| L385 | `.msg.xiao6 .bubble` | `rgba(34,211,238,.05)` | `color-mix(in srgb,var(--cyan) 8%,transparent)` |
| L392 | `.msg.proactive .bubble` | `rgba(34,211,238,.10)` | `color-mix(in srgb,var(--cyan) 12%,transparent)` + `box-shadow:var(--shadow-glow)` |
| L393 | `.proactive-tag` | `rgba(34,211,238,.12)` | `color-mix(in srgb,var(--cyan) 12%,transparent)` |
| L395 | `.speak-btn` | `rgba(34,211,238,.07)` | `color-mix(in srgb,var(--cyan) 10%,transparent)` |
| L402 | `.tool-overlay` | `rgba(8,14,20,.92)` | `background:var(--panel-solid)` |
| L117 | `.conv-list` 滚动条 | `rgba(34,211,238,.25)` | `color-mix(in srgb,var(--cyan) 25%,transparent)` |
| L120 | `.conv-item` | `rgba(255,255,255,.03)` | `background:var(--panel)` |
| L122 | `.conv-item.active` | `rgba(34,211,238,.08)` | `color-mix(in srgb,var(--cyan) 8%,transparent)` |
| L130 | `.chip` | `rgba(255,255,255,.04)` | `background:var(--panel)` |
| L132 | `.chip:hover` | `rgba(34,211,238,.07)` | `color-mix(in srgb,var(--cyan) 7%,transparent)` |
| L2842 | light `.msg.xiao6 .bubble` | `rgba(34,211,238,.10)` | `color-mix(in srgb,var(--cyan) 10%,transparent)` |
| L2843 | light `.msg.user .bubble` | `rgba(245,181,68,.10)` | `color-mix(in srgb,var(--amber) 10%,transparent)` |

**唯一保留的硬编码（已判定为合理例外）**
- L2841 `body[data-theme="light"] .bubble{background:rgba(255,255,255,.55)}` —— 属显式 **legacy light-fallback 块**（L2839 注释："仅保留旧 UI 的 light 组件外观规则"）。这是浅色主题下的浅表面选择，**非**"另一个软件"暗色泄漏；同块青/琥珀气泡（L2842–2843）已令牌化。故仅白色 `.55` 保留并标注。

**超范围不处理（明确标注）**
- L251 `rgba(8,14,20,.92)` 属非 chat-panel 选择器。
- 其余散落 `rgba()`（rail / settings / scene-cards / meters / logs 等）按 A3 范围判定为"非 Legacy Chat Conversation Panel"，保持原样（同 UI-5A R4 已知局限）。

---

## A4 · Galaxy Attention Balance

**发现**：`ui4c-unified-home.css`（UI-4C-2）已在**默认/主页态**把 Galaxy 降权：
```css
body:not(.chat-mode):not(.universe-mode) #solarCanvas{filter:brightness(.46) saturate(.6) contrast(.95)}
.galaxy-veil{opacity:.5}
```
**缺口**：因该规则作用域为 `:not(.chat-mode)`，进入对话时 Galaxy 回退全亮 —— **恰与"注意力层级 Galaxy 应最低"相反**（此时 `#osShell` 被虚化，亮 Galaxy 反而更显眼）。

**方案**：在 `ui2.css`（git `??`→`M`）L945-948 新增 `body.chat-mode` 降权规则，**镜像 UI-4C-2 数值**；`universe-mode` 保持唯一例外（L944 提亮）。

```css
/* A4 · Galaxy 注意力平衡：对话(Task)聚焦态 Galaxy 降权为 World Layer（与 UI-4C-2 H2 默认态一致），
 * 注意力层级 AI Identity > Intent Console > Task > Galaxy；universe-mode 仍由上行提亮（唯一例外）。 */
body.chat-mode #solarCanvas { filter: brightness(0.46) saturate(0.6) contrast(0.95); transition: filter var(--dur-slow) var(--ease-soft); }
body.chat-mode .galaxy-veil { opacity: 0.5; }
```

**最终注意力层级**：AI Identity > Intent Console > Task(对话) > Galaxy(World Layer)。

---

## A5 · Verify（四项，全部文本证据；模型不可读图）

| # | 验证项 | 结果 |
|---|---|---|
| ① | 聊天同空间感 | `.app` 画布令牌化后随主题变化，与 OS 玻璃/面板同源，不再"另一个软件" |
| ② | Galaxy 环境化 | `chat-mode` 下 Galaxy 降权为 World Layer（与默认态一致），不再抢焦点 |
| ③ | Command Dock 唯一意图入口 | `command-dock.js` 零改动（L59 路由到 CommandPalette 保留），未新增任何控件 |
| ④ | AI Presence 三唯一 | 状态权威 `avatar-state.js`(零触碰) / 写入点 `index.html::refreshHud()`(×5 不变) / 颜色权威 `ui2.css body[data-presence]`(×2 不变) |

### 程序化终检结果

- **CSS 括号平衡**（剥离注释/字符串后）：`styles.css` depth=0 ✓；`ui2.css` depth=0 ✓。
- **会话面板选择器内硬编码 `rgba()` 终检**：除 L2841 显式保留的 light 白 `.55` 外，全部清除 ✓。
- **红线文件 grep UI-5B 专属标记**（`A3 ·` / `A4 ·` / `Conversation Panel` / `同化 OS`）：
  `index.html` / `app.js` / `galaxy-experience.js` / `solar-system.js` / `command-dock.js` / `avatar-state.js` / `server.py` **全部 0 命中** ✓。
- `index.html` `refreshHud` 计数 = 5 ✓；`data-presence` = 2；`avatar-state.js` 无 `A3`/`A4`/`galaxy`/`chat-mode` 标记 ✓。

---

## 红线零违反

未触碰：Backend / Agent / AppState / EventBus / DOMAIN·SYSTEM EVENTS / solar-system.js / galaxy-experience.js / app.js 业务逻辑 / avatar-state.js / server.py / command-dock.js / index.html。
**本次会话代码足迹仅** `styles.css`(M) + `ui2.css`(M)。

---

## 已知局限

1. **`.app` 固定画布割裂感**：`.app` 固定 1920×1080 画布（JS-scale 结构限制，禁触），"同空间感"靠视觉令牌同源达成，结构性画布限制留待后续。
2. **before/after 截图无法真机核验**：本模型不支持图像读取，且当前环境无浏览器自动化工具，无法真机采集/比对截图。该交付物为**名义项**；本报告以"DOM/CSS 证据级 before/after diff 表"（A3 章节）作为可核验替代。
3. **非会话面板散落 `rgba()`**（rail / settings 等）按范围判定不处理（同 UI-5A R4）。
4. **遗留临时文件**：`styles.css.bak.zzstep1` / `styles.css.tmp` 非本会话产物（时间戳早于本会话），建议用户自行清理（按纪律不擅自删项目文件）。

---

## 交付物清单

| 类型 | 路径 |
|---|---|
| 本报告 | `docs/ui-system/ui5b-legacy-workspace-assimilation/00_IMPLEMENTATION_REPORT.md` |
| A3 代码 | `xiao6-ui/styles.css`（Conversation Panel 令牌化） |
| A4 代码 | `xiao6-ui/ui2.css`（chat-mode Galaxy 降权） |
| before/after 截图 | 名义交付，受模型能力限制未真机生成（见已知局限 2） |

---

## STOP 判定

▣ **UI-5B 完成。** Audit / Design / Implement / Verify / Document 五段全部交付；红线零违反；AI Presence 三唯一保护到位；CSS 平衡与令牌化终检通过。

**不进入 UI-5C，等待 Review。** 未提交 Git（按纪律）。
