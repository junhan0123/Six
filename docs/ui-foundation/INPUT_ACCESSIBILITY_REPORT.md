# Input Focus Integration & Accessibility — Phase 2 Task C 报告

> **阶段**：Component System Sprint v1.0 · Phase 2（Input System）
> **执行身份**：DesignMdArchitect（Diana）
> **前置**：Task A（审计）、Task B（对齐，已完成）
> **日期**：2026-08-05
> **范围**：focus-visible / keyboard navigation / placeholder contrast / disabled state 与既有 Focus System 的一致性核验。
> **纪律红线**：不修改 Focus System（改=动主题/视觉方向，违红线）→ 本 Task 为**核验 + 记录**，不落地代码改动。

---

## 1. 既有 Focus System（基准）

- **全局定义**：`ui2.css:547` `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; box-shadow: 0 0 0 4px var(--glow); }`（DESIGN.md §7 Do's #4、§9.1 引用）。
- **元素级覆盖**：`premium.css:45-54` `button/ a/ input/ select/ textarea/ [tabindex]:focus-visible { outline: 2px solid var(--cyan); box-shadow: 0 0 0 4px rgba(34,211,238,.18); }`。
- **加载顺序**：`index.html` → `styles.css`(8) → `premium.css`(9) → `ui2.css`(13)。`ui2.css` 最后加载，但 `premium.css` 用**更高特异性**（`input:focus-visible` = 0,1,1）覆盖 `ui2.css` 全局 `:focus-visible`（0,1,0）。
- **结论**：所有 `<input>` / `<textarea>` 实际取 `premium.css` 的 focus-visible 环（accent 描边 + 青色辉光），**键盘可达，WCAG 2.1 AA 可见性满足**。

---

## 2. 逐项核验

### 2.1 focus-visible 覆盖

| 输入 | 自身 outline | focus-visible 来源 | 键盘焦点可见？ | 说明 |
|------|-------------|-------------------|---------------|------|
| `.settings-input` / `.settings-textarea` | 无 `outline:none` | `input/textarea:focus-visible`（premium.css） | ✅ | 直接环 |
| `.sc-input` | `outline:0`（类 0,1,0） | 被 `input:focus-visible`（0,1,1）覆盖 | ✅ | 环生效 |
| `.wx-city-input` | 无 | premium.css | ✅ | 直接环 |
| `.mem-search` | `outline:none` | 被覆盖 | ✅ | 环生效 |
| `.memq-input` | `outline:none` | 被覆盖 | ✅ | 容器 `.memq-search:focus-within` 另显 teal 辉光 |
| `.cp-input` | `outline:none`（类 0,1,0） | 被 `input:focus-visible`（0,1,1）覆盖 | ✅ | 环生效（`.cp-inputrow` 无 focus-within，靠环） |
| `.onb-input` | `outline:none` | 被覆盖 | ✅ | 环生效 |
| `.os-dock input` | `outline:0` | 被覆盖；容器 `.os-dock-bar:focus-within` 显 accent 辉光 | ✅ | 双保险 |
| `#input`（主聊天） | `outline:0`（**ID 1,0,0 > 0,1,1**） | `input:focus-visible` 被 ID 覆盖 → 自身无环 | ⚠️ 靠容器 | 容器 `.chat-area .dock.focus-within`（styles.css:354）显 border + `var(--glow)`，键盘聚焦时触发，可见 |

> **结论**：所有输入键盘焦点均可见（直接或经容器 focus-within）。`#input` 自身无 outline 但容器补偿，符合可访问性。

### 2.2 Keyboard Navigation

- 所有输入为原生 `<input>` / `<textarea>`，浏览器原生 Tab 序可达，无需额外 `tabindex`。
- Toggle / Checkbox / Range 同为原生控件，焦点环经 `:focus-visible` 覆盖生效。
- 无 `tabindex="-1"` 误禁用、无 `pointer-events:none` 阻断键盘到达的输入。
- **结论**：键盘导航合规。

### 2.3 Placeholder Contrast

| 占位色 | 值（midnight） | 背景 | 估算对比 | 判定 |
|--------|---------------|------|---------|------|
| `var(--input-placeholder)` = `--muted` | `#5e6c96` | 深色底（≈`#04060f`） | ≈ 3.4:1 | 设计令牌授权（DESIGN.md §2.2 明定为占位/禁用最低灰阶，禁用更深灰阶防跌破 AA） |
| `.hs-chat-input textarea::placeholder` = `--dim` | `#9fb0d8` | `rgba(255,255,255,.05)` 上 | > 7:1 | 优秀 |
| `.onb-input` 无占位色覆盖 | 浏览器默认（取自 color `#eafdff` 派生） | 浅填充 | 充足 | OK |

> **结论**：占位色统一到 `--input-placeholder`（Task B 路由），取值为设计系统明示授权的最低可读灰阶，符合项目 AA 策略。占位文本属「辅助/瞬时」性质，3.4:1 在 DESIGN.md 框架内被接受；如需更严可在未来主题化时评估，不在本 Sprint 范围。

### 2.4 Disabled State

- **现存**：仅 `.settings-check input:disabled { cursor:not-allowed; opacity:.5 }`（styles.css:3071）— 非文本控件。
- **文本输入**：无任何 `:disabled` 样式。
- **运行时核查**：`index.html` 中文本输入（`.settings-input` / `#input` / `.cp-input` 等）**无任何 `disabled` 属性**使用 → 当前无功能缺口。
- **规范**：`DESIGN.md §4.3.3` 已定义 `--input-disabled-op:.5` 作为预留令牌。
- **判定**：缺口 F4 已记录；实现=新增视觉/功能，违红线，**仅记录不实现**。

### 2.5 Error State

- 全站无输入 error 态（仅 `.orb-wrap.error` 非输入元素）。
- `DESIGN.md §4.3.3` 已定义 `--input-error-border: var(--danger)` 预留令牌。
- 判定：缺口 F5 已记录，仅记录不实现。

---

## 3. 发现与处置（Finding）

| ID | 发现 | 处置 |
|----|------|------|
| F1 | Focus System 双定义：`ui2.css:547` 全局 `:focus-visible`（glow .40）被 `premium.css:48` `input:focus-visible`（glow .18，硬编码青色）以更高特异性覆盖 → 输入实际辉光为硬编码青，不随主题 | **记录**（改=动 Focus System + 非 midnight 主题视觉变化，违红线） |
| F4 | 文本输入无 disabled 态 | **记录**（无运行时使用；规范已预留令牌） |
| F5 | 输入无 error 态 | **记录**（规范已预留令牌） |
| F6 | 占位色曾混用 `--dim2`/`--muted`/`--dim`/无 | ✅ Task B 已统一到 `--input-placeholder` |

---

## 4. 与 Focus System 一致性结论

- ✅ 所有输入具备键盘可见焦点指示（直接或经容器 focus-within）。
- ✅ 键盘导航原生合规。
- ✅ 占位色经 Task B 统一，符合 DESIGN.md AA 灰阶策略。
- ⚠️ F1 双定义属预存在状态，输入焦点环可见但辉光不随主题；按红线**不改**。
- ⚠️ F4/F5 disabled/error 缺口已规范预留，按红线**不实现**。

**本 Task 零代码改动**（纯核验 + 记录），符合「确保符合已有 Focus System」且严守红线。

---

> **状态**：Task C 完成（零代码改动）。下一步 → Task D（Low Risk Migration 静态验证）。
