# Regression Verification — Phase 2 Task E 报告

> **阶段**：Component System Sprint v1.0 · Phase 2（Input System）
> **执行身份**：DesignMdArchitect（Diana）
> **前置**：Task A–D 完成
> **日期**：2026-08-05
> **方法**：静态回归核验（无 GUI）。Phase 2 仅改动 Input CSS + Input 令牌 + 缓存炸弹；Button/Panel/Theme/Focus/Responsive 维度应零回归。

---

## 1. 改动面收敛确认

Phase 2 实际改动文件：
- `ui2.css`：`:root` 新增 12 个 `--input-*` 令牌（additive，行 85-96）。
- `styles.css`：8 类低风险输入令牌路由（§4.3 对齐）。
- `premium.css`：`.onb-input` 令牌路由。
- `index.html`：3 处 CSS `?v=` 缓存 bump。

**未触碰**：Button 系统（`.btn` Phase 1）、Panel 系统（`.glass-panel`/`.os-panel` Phase 1）、Theme 切换逻辑、Focus System 定义、Responsive 断点、任何 JS / HTML 结构。

---

## 2. 六界面回归矩阵

| 界面 | Input | Button | Panel | Theme | Focus | Responsive |
|------|-------|--------|-------|-------|-------|-----------|
| **首页 (OS Shell)** | `.mem-search` 路由(等价)；`.os-dock input` 未动 | 未动 | 未动 | 令牌主题感知，无回归 | 容器 focus-within  intact | 未动 |
| **Galaxy (宇宙视图)** | 无输入控件 | 未动 | 未动 | 未动 | 未动 | 未动 |
| **聊天 (Chat)** | `#input` 未动；`.send-btn`(按钮)未动 | 未动 | 未动 | 未动 | `#input` 靠 `.dock.focus-within`(styles.css:354) 可见 | 未动 |
| **Workspace** | `.settings-input`/`.settings-textarea` 路由(等价)；`.settings-switch`/`.settings-check`/`.settings-range` 未动 | 未动 | `.os-panel`/`.glass-panel` 未动 | 未动 | Toggle/Check focus-visible  intact | 未动 |
| **设置 (Settings)** | 同 Workspace（主设置输入族） | 未动 | `.settings-panel` 未动 | 未动 | 未动 | 未动 |
| **Command Palette** | `.cp-input` 未动（高风险） | 未动 | `.modal-card` 未动 | 未动 | `.cp-input` 取 `input:focus-visible` 环 | 未动 |

---

## 3. 维度细化核验

### 3.1 Input
- 低风险 8 类：路由后计算值逐字节等价（Task D §2 已证）。
- 高风险 6 类（`#input` / `.hs-chat-input textarea` / `.cp-input` / `.wc-cd-input` / `.os-dock input` / `.cmd-bubble-input`）：grep 确认保留原始值（Task D §3 证据）。
- 无新增 / 删除输入类。

### 3.2 Button（Phase 1 资产）
- `ui2.css` `.btn` 体系（Phase 1 行 591+）在本 Sprint **无任何编辑**。`.send-btn` / `.sc-submit` / `.settings-save-btn` / `.hs-chat-send` 等按钮类维持原值。

### 3.3 Panel（Phase 1 资产）
- `.glass-panel` / `.onb-card` / `.os-panel` / `.settings-panel`（Phase 1 行 120-135）**无编辑**。玻璃层级 / blur / border 维持。

### 3.4 Theme
- 新增 `--input-*` 令牌中：`--input-border`/`--input-focus-border`/`--input-focus-glow`/`--input-placeholder` 引用主题感知变量（`--border`/`--accent`/`--glow`/`--muted`），随主题解析。
- `--input-bg`/`--input-bg-soft`/`--input-bg-deep` 为固定 rgba，与迁移前硬编码值一致（含 light 主题既有行为），无回归。
- 主题块（dark/quantum/midnight/light/…）未改动，Legacy 别名层完好。

### 3.5 Focus
- Task C 已确认：所有输入键盘焦点可见（直接或经容器 focus-within）；Focus System 定义（`ui2.css:547` + `premium.css:48`）未改。

### 3.6 Responsive
- Phase 2 未触及任何 `@media` / grid / flex 布局属性。聊天降级、侧栏限高、断点（`>980px` / `≤980px`）全部维持原行为。

---

## 4. 结构完整性

- `ui2.css` `:root` 闭合正常（令牌块行 85-96，行 97 `}`）。
- `index.html` 三 CSS 链接 `?v=` 已 bump（s3 / p3 / c3），确保新文件被拉取。
- 无 CSS 语法错误、无未闭合块、无孤立令牌引用。

---

## 5. 结论

- ✅ 六界面 × 六维度全部零回归（Input 等价路由、Button/Panel/Theme/Focus/Responsive 未触碰）。
- ✅ 高风险输入与所有非 Input 维度完好。
- ✅ 结构完整、缓存到位、可回滚。

> **状态**：Task E 完成（零新增代码改动，纯静态回归核验）。下一步 → Final（Phase 2 Summary + STOP）。
