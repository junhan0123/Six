# Task C · 面板原语统一报告（PANEL_SYSTEM_REPORT）

> Sprint：Xiao6 UI Foundation Unification Sprint v1.0
> 目标：Panel / Card / Container / Surface / Glass 唯一来源，禁第二套。

## 1. P0 来源

UI/UX Polish Sprint v1.0 审计报告 — **「面板 Chrome 6 套」**。
历史上存在 6 套面板外观（`os-panel` / `glass-card` / `glass-panel` / `settings-panel` / `modal-card` / `zz-panel`），部分使用硬编码深色渐变，浅色主题下失效。

## 2. 审计发现

- 6 类面板选择器分散于 `ui2.css` / `premium.css` / `styles.css`。
- `.glass-panel`（premium.css:26）与 `.onb-card`（premium.css:192）使用**固定深色渐变** `linear-gradient(... rgba(12,20,28,.82) ...)`，浅色主题（data-theme="light"）下背景仍为深色 → 视觉断裂。
- 其余面板（`.os-panel` / `.glass-card` / `.settings-panel` / `.modal-card` / `.zz-panel`）已通过 `ui2.css` 令牌（`--surface` / `--border` / `--radius-*` / `--blur-glass`）驱动。

## 3. 执行（单一来源 = ui2.css 令牌；增量别名，零 HTML/JS 改动）

- ui2.css 已通过 `:root` + `[data-theme="..."]` 双命名空间（NEW `--surface` + LEGACY `--panel`/`--glass`）桥接，全文档面板类获得合法令牌值，**无第二套令牌**。
- 新增覆盖：将硬编码深色渐变令牌化（ui2.css 收敛层）：
  ```css
  .glass-panel { background: linear-gradient(160deg, var(--surface-2), var(--bg-2)); }
  .onb-card    { background: linear-gradient(165deg, var(--surface-2), var(--bg-2)); }
  ```
  → 浅色主题下自动跟随，消除断裂。

## 4. 纪律合规

- ✅ 未新增第二套面板体系 / 类。
- ✅ 仅 CSS 增量别名；未改 HTML 结构 / JS。
- ✅ 未改布局盒尺寸（仅背景令牌来源）。

## 5. 验证

代码级：`.glass-panel` / `.onb-card` 现引用 `var(--surface-2)` / `var(--bg-2)`，无硬编码深色 rgba。

## 6. 状态

✅ **P0 收敛** — 面板原语唯一来源 = ui2.css 令牌；硬编码深色渐变已令牌化，浅色主题可用。
> 后续（Review 门控，非本 Sprint P0）：可选将 `.zz-panel` 等旧类逐步别名到 `.glass-panel`，进一步减少选择器数量（机械替换，需视觉评审）。
