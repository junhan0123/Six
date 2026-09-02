# Button System Implementation — Xiao6 Component System Sprint v1.0 · Phase 1 (Task B)

> **Sprint**: Component System Implementation Sprint v1.0 — Phase 1
> **Task**: B — Button System Implementation
> **日期**: 2026-08-05
> **执行模式**: Audit → Plan → Execute → Verify → Report → STOP
> **纪律红线**: 仅 Primitive 收敛；仅令牌/别名层 + 基准类完善；零视觉/行为变化；禁改 HTML/JS 逻辑；禁机械合并类名（留 Review）；可回滚。

---

## 1. 目标（来自指令）

> 统一 `.btn` / `.btn-primary` / `.btn-ghost` / `.btn-danger` 的 **padding / height / radius / typography / color / hover / active / disabled / focus**；优先 CSS Token + 别名兼容层，禁改交互逻辑。

---

## 2. 实施动作清单

| # | 动作 | 文件 | 行 | 类型 | 视觉影响 |
|---|------|------|----|------|----------|
| 1 | 核验 `.btn` 四变体与 DESIGN.md §4.1 逐字节一致 | `ui2.css` | 591-601 | 核验（无改） | 无 |
| 2 | 补 `.btn:disabled` 规则 | `ui2.css` | 601 后 | **新增（additive）** | 无（仅作用于 disabled 态，当前无 `.btn` 处于 disabled） |
| 3 | 别名/令牌层核实（`--btn-rail-bg` / `--btn-pill-bg` 单值来源） | `ui2.css` / `styles.css` / `premium.css` | — | 核实（无改） | 无 |
| 4 | 前端缓存标记 bump（`ui2.css?v=20260805c1` → `c2`） | `index.html` | 13 | 机械 | 无 |

**代码改动总计**：`ui2.css` +4 行（`.btn:disabled`）；`index.html` 1 行（缓存版本）。**零 HTML/JS 逻辑改动。**

---

## 3. `.btn` 四变体统一核验（指令属性全覆盖）

对照 `DESIGN.md §4.1:94-112` 与 `ui2.css:591-601`：

| 属性 | `.btn`（base） | `.btn.primary` | `.btn.ghost` | `.btn.danger` | 结论 |
|------|----------------|----------------|--------------|---------------|------|
| padding | 8/18（`--btn-pad-y/x`） | 继承 | 继承 | 继承 | ✅ 统一 |
| height | 内容驱动（inline-flex，未强制） | 继承 | 继承 | 继承 | ✅（DESIGN.md 未规定固定 height） |
| radius | `--btn-radius`=`--r-md`(16) | 继承 | 继承 | 继承 | ✅ 统一 |
| typography | 13/600 | 继承 | 继承 | 继承 | ✅ 统一 |
| color（bg/border/text） | `accent 16%` / `accent 45%` / `var(--text)` | `accent` 实心 / `#04101a` | transparent / `var(--border)` | `danger 12%` / `danger 55%` / `danger` | ✅ 统一 |
| hover | bg `accent 26%` + 位移 | 继承 | 继承 | 继承 | ✅ 统一 |
| active | `translateY(0)` | 继承 | 继承 | 继承 | ✅ 统一 |
| **disabled** | **`opacity:.5; cursor:not-allowed; transform:none`**（本次新增） | 继承 | 继承 | 继承 | ✅ **补齐** |
| focus | 全局 `:focus-visible`（ui2.css:547-551，accent 环 + glow） | 继承 | 继承 | 继承 | ✅ 统一（无需重复定义） |

> **height 说明**：`.btn` 采用内容驱动高度（inline-flex，无 `min-height`）。DESIGN.md §4.1 未规定固定 height，且强制 `min-height` 会改变 `mobile-app.html` 中已有 `.btn` 表单按钮的渲染高度（视觉变化），故**有意不添加**，保持与规范一致、零视觉位移。

---

## 4. 别名兼容层现状（G2 遗留 CTA）

前置 Sprint 已完成值单源收口，本次核实无误：

| 遗留类 | 背景值来源 | 状态 |
|--------|-----------|------|
| `.btn-new` | `var(--btn-rail-bg)`（`ui2.css:588` → `styles.css:87`） | ✅ 单值来源，零视觉变化 |
| `.onb-next` | `var(--btn-pill-bg)`（`ui2.css:589` → `premium.css:224`） | ✅ 单值来源，零视觉变化 |

>G2 类名机械合并（`.btn-new`→`.zz-button`、`.onb-next`→`.zz-button--pill`）**不在 Phase 1**，因合并会改变 CTA 刻意视觉方向（radius 11 vs 16、font 15 vs 13、胶囊 vs 圆角），标注为 **Review 门控**。

---

## 5. 明确未执行（撞红线，一律递延）

| 项 | 原因 | 处置 |
|----|------|------|
| `.btn-new` / `.onb-next` 类名合并到 `.zz-button` | 改视觉方向 | Review 门控（需 GUI 验证） |
| `.settings-save-btn` → `.btn` | 广泛使用（≈18 处 HTML）+ radius 10≠16 视觉位移 | Review 门控 |
| 5 个 `-open-btn` rail 按钮合并为 `.rail-open-btn` | HTML 类名改动 | Review 门控 |
| `.wx-mode-btn` / `.wx-exit-btn` / `.ts-exit-btn` CSS 双定义去重 | 属「扩大范围」专项清理 | 仅记录（见 A-§6），不处理 |
| 任何 HTML/JS 改动、任何新功能、任何动画/主题/布局重构 | 红线禁止 | 禁止 |

---

## 6. 风险与回滚

- **风险等级**：🟢 低。改动为 additive CSS 规则 + 缓存 bump，不影响任何当前渲染中的按钮。
- **可回滚**：是。回滚 = 删除 `ui2.css` 第 602-604 行（`.btn:disabled`）+ `index.html` 第 13 行版本回 `c1`。
- **验证方式**：本环境无法启动 Electron GUI，采用静态验证（Task C）。

---

## 7. 结论

Button System 在 Phase 1 内达成：
1. 规范基准 `.btn` 四变体**已与 DESIGN.md 完全一致**，且补齐唯一缺失的 `disabled` 态。
2. 别名/令牌单值来源层（G2）**已核实完整**，值零视觉变化。
3. **零机械合并**、零逻辑改动、零视觉变化、全部可回滚。
4. 高/中风险合并项全部递延 Review 门控。

下一步：Task C（Button Migration Verify — 静态验证改动正确性与无副作用）。
