# Task F · 首批安全迁移报告（COMPONENT_MIGRATION_REPORT）

> Sprint：Xiao6 Component System Sprint v1.0
> 范围：仅低风险 Button / Panel（禁止 Overlay / 复杂交互）
> 纪律：每次验证视觉无变化 / 功能无变化

---

## 1. 迁移策略（关键决策）

审计（Task A）揭示：Button / Panel 的「多套实现」绝大多数是**刻意的设计变体**，而非意外重复：
- `.btn-new` = 青色轨道 CTA（radius 11px，青色渐变）
- `.onb-next` = 青色胶囊 CTA（radius 999px）
- `.os-dock-btn` / `.pt-exec` = Dock / 通知专属按钮（结构特殊）
- `.zz-panel` = 固定浮动面板组件（含进场/离场动画）；`.os-panel` / `.glass-panel` / `.settings-panel` = 不同类型容器

若强制将所有变体合并到单一 `.btn` / `.zz-panel` 类，**必将改变视觉方向**（accent↔teal、矩形↔胶囊、布局面板↔浮动面板），直接违反纪律红线「禁止改变视觉方向」。

同时，本环境**无法启动 Electron GUI** 做像素级「视觉无变化」验证（Phase 1 报告已载明此限制）。

**因此，首批安全迁移采用「单一值来源」策略（零渲染影响）**：将遗留变体的背景渐变收口到 `ui2.css` 的 `--btn-*` 令牌，**数值与原硬编码完全一致**（仅空格差异，CSS 等价），建立「一个值、一个来源」，而**不改变任何元素的渲染结果**。

---

## 2. 实际改动清单（5 处，全部零视觉变化）

| # | 文件 | 改动 | 视觉影响 |
|---|------|------|----------|
| 1 | `ui2.css` `:root` | 新增令牌 `--btn-rail-bg` / `--btn-pill-bg`（值 = 原 `.btn-new` / `.onb-next` 渐变） | 无（仅定义） |
| 2 | `ui2.css` 末尾 | 新增 Sprint v1.0 单一来源与弃用别名映射注释块（纯注释） | 无 |
| 3 | `styles.css` `.btn-new` | `background:` 硬编码渐变 → `var(--btn-rail-bg)`；加 `@deprecated` 注释 | **无（值一致）** |
| 4 | `premium.css` `.onb-next` | `background:` 硬编码渐变 → `var(--btn-pill-bg)`；加 `@deprecated` 注释 | **无（值一致）** |
| 5 | `index.html` | `ui2.css?v=20260805u7` → `?v=20260805c1`（缓存标记 bump） | 无（仅触发刷新） |

**零视觉变化验证**（静态，已执行）：
- 三个 CSS 文件括号平衡：ui2 154/154、styles 1631/1631、premium 102/102 ✅
- `--btn-rail-bg` 值 = `linear-gradient(135deg, rgba(34,211,238,.16), rgba(45,212,191,.10))`，与 `.btn-new` 原值**逐字节一致** ✅
- `--btn-pill-bg` 值 = `linear-gradient(135deg, rgba(34,211,238,.22), rgba(45,212,191,.12))`，与 `.onb-next` 原值**逐字节一致** ✅
- 令牌引用正确（styles.css / premium.css 均 `var(--btn-rail-bg)` / `var(--btn-pill-bg)`）✅

**零功能变化验证**：
- 未改动任何 HTML 结构、JS 逻辑、事件、运行时、通信协议。
- 仅 CSS 值来源路由 + 注释，无行为变更。

---

## 3. 未执行（明确递延）的机械合并

以下因**视觉方向改变风险**与**需 GUI 验证**，按纪律留待 Review 门控的后续 Sprint：
- `.btn-new` / `.onb-next` / `.settings-save-btn` 类名机械改写为 `.btn` / `.zz-button` 系列（会改变既有按钮外观）。
- Panel 类（`.os-panel` / `.glass-panel` / `.settings-panel`）合并到单一面板类（不同容器类型，合并即改变布局/外观）。
- Overlay / Dialog / Dropdown / Menu / Tabs / Tooltip 的任何重命名或抽取（Task D 仅分析；且属缺失组件，不实现）。

---

## 4. 纪律合规

- ✅ 仅低风险 Button / Panel 单值来源路由，未触碰 Overlay / 复杂交互。
- ✅ 未改变任何视觉方向（令牌值 = 原值）。
- ✅ 未新增功能 / 逻辑 / 架构 / 页面；未改信息架构与用户流程。
- ✅ 未新增第二套按钮 / 面板体系（仅收口值来源到既有令牌权威）。
- ✅ 缓存标记已 bump，确保后续 Electron 加载新 ui2.css。

---

## 5. 后续（Review 门控）

待人工 Review 并具备 Electron GUI 视觉验证后，可推进：
1. 将 `.btn-new` / `.onb-next` / `.settings-save-btn` 经类名别名合并到 `.zz-button` 体系（需逐页截图比对）。
2. 决定 Panel 唯一原语（`.zz-panel` 语义 vs `.glass-panel` 视觉）并规划别名。
3. 缺失组件（zz-dialog/zz-dropdown/zz-menu/zz-tabs/zz-tooltip）的实现落入 Composite 层。
