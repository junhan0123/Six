# Input Primitive Design Alignment — Phase 2 Task B 报告

> **阶段**：Component System Sprint v1.0 · Phase 2（Input System Primitive 收敛）
> **执行身份**：DesignMdArchitect（Diana）
> **前置**：`INPUT_IMPLEMENTATION_AUDIT.md`（Task A 已完成）
> **日期**：2026-08-05
> **纪律红线**：零视觉/行为变化；可回滚；不新增功能/架构。

---

## 1. 对齐目标

依据 `DESIGN.md`（单值来源）统一输入框 / 文本域 / 搜索框的 **height·padding·radius·border·background·font·placeholder·focus·disabled·error** 维度。策略沿用 Phase 1「单值来源 + 别名兼容层」：
- 遗留变量（`--cyan`/`--line`/`--void`/`--txt`/`--dim2`）已在 `ui2.css:56-70` 别名到 NEW 令牌，替换**逐字节等价**。
- 裸 `rgba` 背景与裸 radius 数字路由到新增 `--input-*` 令牌（值=既有实值）。
- **不新建第二套组件类**（`.zz-input` 仅 DESIGN.md 预留命名）。

---

## 2. DESIGN.md §4.3 补全

原 §4.3 仅为 stub（`.os-dock input` + `.settings-input` 占位）。本 Task 补全为完整规范：
- **§4.3.1 Input 令牌集**：12 个 `--input-*` 令牌（填充 / 描边 / 圆角 / 内距 / 字号 / 聚焦 / 占位 / disabled / error）。
- **§4.3.2 变体矩阵**：A 有底边框型（`.settings-input` canonical）/ B 无边框透明型（聊天·指令）/ C 文本域 / D 搜索。
- **§4.3.3 状态规范**：Placeholder / Focus / Focus-visible / Disabled / Error 的令牌化定义。
- **§4.3.4 非文本控件**：Toggle / Checkbox / Range / File 沿用既有。

---

## 3. 令牌落地（ui2.css `:root` 新增，additive）

位置：`ui2.css:85-96`（在 `--r-*` 之后、`:root` 闭合前）。

```css
--input-bg: rgba(5,7,10,.6);            /* = 原 .settings-input 背景，零变化 */
--input-bg-soft: rgba(255,255,255,.05); /* = 原 .settings-textarea / .memq-search 背景 */
--input-bg-deep: rgba(0,0,0,.35);       /* = 原 .mem-search 背景 */
--input-border: var(--border);
--input-radius: var(--r-sm);            /* 10px */
--input-pad-y: 9px; --input-pad-x: 12px;
--input-font: 13px;
--input-focus-border: var(--accent);
--input-focus-glow: var(--glow);
--input-placeholder: var(--muted);
--input-disabled-op: .5;                /* 预留：文本输入 disabled 暂未应用 */
--input-error-border: var(--danger);    /* 预留：error 态全站缺失 */
```

> 令牌引用 `--border`/`--accent`/`--glow`/`--muted`/`--r-sm` 均为主题感知，故 Input 令牌随主题自动解析（背景 rgba 固定值 = 既有行为，无回归）。

---

## 4. 路由应用（仅 A 组低风险，零视觉）

| 类 | 文件:行 | 改动 | 计算值变化 |
|----|---------|------|-----------|
| `.settings-input` / `.settings-select` | `styles.css:2779-2781` | bg `rgba(5,7,10,.6)`→`var(--input-bg)`；border `var(--line)`→`var(--input-border)`；color `var(--txt)`→`var(--text)`；focus `var(--cyan)`→`var(--input-focus-border)`；padding/radius→令牌 | **无** |
| `.settings-textarea` | `styles.css:3062-3065` | bg `rgba(255,255,255,.05)`→`var(--input-bg-soft)`；border `var(--line)`→`var(--input-border)`；color `var(--txt)`→`var(--text)` | **无** |
| `.sc-input` | `styles.css:454-456` | border `var(--line)`→`var(--input-border)`；color `var(--txt)`→`var(--text)`；focus `var(--cyan)`→`var(--input-focus-border)`（bg `.55` 留） | **无** |
| `.wx-city-input` ×2 | `styles.css:1754` + `:1894` | bg `var(--void)`→`var(--bg)`；border `var(--line)`→`var(--input-border)`；color `var(--txt)`→`var(--text)`；focus `var(--cyan)`→`var(--input-focus-border)`（replace_all 双份一致） | **无** |
| `.mem-search` | `styles.css:2385-2389` | bg `rgba(0,0,0,.35)`→`var(--input-bg-deep)`；border `var(--line)`→`var(--input-border)`；color `var(--txt)`→`var(--text)` | **无** |
| `.memq-search` | `styles.css:3610-3611` | bg `rgba(255,255,255,.05)`→`var(--input-bg-soft)`；border `var(--line)`→`var(--input-border)` | **无** |
| `.memq-input` | `styles.css:3615-3617` | color `var(--txt)`→`var(--text)`；placeholder `var(--dim2)`→`var(--input-placeholder)` | **无** |
| `.settings-check input` | `styles.css:3070` | `accent-color:var(--cyan)`→`var(--accent)` | **无** |
| `.onb-input` | `premium.css:238-244` | border `var(--line-strong)`→`var(--input-border)`；focus `var(--cyan)`→`var(--input-focus-border)` | **无** |

**缓存炸弹**：`index.html` 三处 `?v=` 已 bump — `styles.css?s2→s3`、`premium.css?p2→p3`、`ui2.css?c2→c3`。

---

## 5. 故意未改动项（严守红线 / 留待 Review）

| 项 | 原因 |
|----|------|
| B 组高风险输入：`#input` / `.hs-chat-input textarea` / `.cp-input` / `.wc-cd-input` / `.os-dock input` / `.cmd-bubble-input` | 聊天核心 / Command Palette / 指令通道 / Companion 隔离层，改值=UX 变化，撞红线 |
| Focus 辉光硬编码 `rgba(34,211,238,..)`（`.sc-input`/`.settings-textarea`/`.hs-chat`/`.onb-input`） | 路由到 `var(--glow)` 会改变非 midnight 主题辉光色=视觉变化（F2 记录） |
| `.wx-city-input` / `.wc-cd-input` / `.cp-input` 重复定义 | F3 记录，合并改源结构留 Review |
| 文本输入 disabled / error 态 | F4/F5 缺口，实现=新增视觉/功能，记录不实现 |
| 圆角 9/8px 与 bg 微差（`.sc-input` `.55`、`.onb-input` `.04`） | 刻意变体，统一=视觉变化，记录不强制（F7） |
| 浅色主题输入底 `rgba(5,7,10,.6)` | F8 记录，令牌化后未来可主题化 |

---

## 6. 一致性核验

- `styles.css` 中仍有 `var(--cyan)` 引用（行 182/427/486/2460/2484/2496/2529/2567/2586/2786/2900/3028）均为**非输入元素**（tts-toggle / sc-choice / mic-btn / mem-btn / modal-close / hs-tts / theme-opt / zz-task-close / settings-save-btn），不在 Input 收敛范围，正确保留。
- 全部路由后的 input 规则经 Grep 复核：已无 `border-color:var(--cyan)` 残留于输入框 focus（仅按钮类保留）。
- 令牌在 `ui2.css` 定义完整（行 85-96），`:root` 单点声明，对全主题生效。

---

## 7. 验收对照（Phase 2 红线）

| 红线 | 本 Task 符合性 |
|------|---------------|
| 零视觉变化 | ✅ 所有改动计算值逐字节等价 |
| 不新增功能 | ✅ 仅令牌路由 + 文档；disabled/error 仅预留令牌未实现 |
| 不新增第二套组件 | ✅ 复用既有类，未建 `.zz-input` 实体 |
| 可回滚 | ✅ 改动为可逆文本替换 + 缓存 bomb；git 可 diff |
| 不修改 Runtime/EventBus/通信 | ✅ 纯 CSS / 文档 |
| 静态验证（无 GUI） | ✅ 代码级值核对完成；GUI 像素回归留 Review 门控 |

---

## 8. 结论

- `DESIGN.md §4.3` 由 stub 升级为完整 Input 规范（令牌集 + 4 变体 + 状态规范）。
- `ui2.css` 新增 12 个 Input 令牌（additive），`styles.css` / `premium.css` 8 类低风险输入完成令牌路由。
- 高风险 / 缺口项全部按纪律**记录不修改**，零视觉、零行为、可回滚。

> **状态**：Task B 完成（含实际代码改动：ui2.css +9 行令牌、styles.css 8 类路由、premium.css 1 类路由、index.html 3 处缓存 bump）。下一步 → Task C（Focus Integration）。
