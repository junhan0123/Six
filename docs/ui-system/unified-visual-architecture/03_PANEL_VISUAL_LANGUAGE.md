# 03 · 面板视觉语言（Panel Visual Language）

> **文档类型**：统一视觉架构设计 · 面板语言层
> **阶段**：Unified Visual Architecture Design Phase v1.0 · 只设计，不实现 · **0 代码改动**
> **上游依据**：`00_DESIGN_PRINCIPLES.md` · `DESIGN.md` §4.2/§6 · `UI_SYSTEM_v1.0.md` §1.7/§4 · `final-convergence/00_AUDIT.md`（F1/F3/F7）
> **生成日期**：2026-08-09

---

## 0. 问题陈述

当前面板系统「缺少统一空间语言」（用户 7 大问题之六）。根因（Final Convergence Audit）：
- **F1**：缺 `.zz-input` 正式原语，输入各写各的。
- **F3**：`.zz-panel`（官方面板）实际定义在 `styles.css`，与「ui2.css = 令牌权威」位置矛盾；`.os-panel` / `.settings-panel` 三类并存。
- **F7**：领域面板（`.hs-*` 等）用本地 CSS，圆角/间距/字号与系统面板不同调。

本章规定**统一的面板视觉语言（规则，非 CSS）**，使 17+ 面板读起来是「同一套 AI OS 的容器」，同时保留领域个性。

---

## 1. 面板语言五原则

1. **统一容器语法，保留领域个性** —— 容器（边框 / 圆角 / 玻璃 / 内距 / 标题）走统一规则；内容区允许领域个性化外观（如天气面板用图表、热点面板用列表）。
2. **层级靠透明度与 blur，不靠重投影** —— 玻璃拟态本质（DESIGN.md §1）。
3. **深度 ladder 单一令牌源** —— 所有浮层引用 `--z-*`，禁止裸数字（DESIGN.md §6.3）。
4. **状态四态强制** —— hover / focus-visible / disabled / loading / error 是组件契约强制项（UI_SYSTEM v1.0 §1.7）。
5. **信息密度靠网格，不靠压缩留白** —— 面板内 22px 留白 + 内部网格承载密度（DESIGN.md §5）。

---

## 2. 层级（Depth Ladder）

| 层 | z 令牌 | 用途 |
|---|---|---|
| ground | `--z-ground`(0) | 银河世界层 |
| base | `--z-base`(1) | App 基底 |
| stage / orb | `--z-stage`(2-4) | 银河舞台 / 星球 |
| rail | `--z-rail`(5) | 左栏常驻能力 |
| content | `--z-content`(18) | Workspace 主内容 |
| hud | `--z-hud`(20) | 顶栏 |
| panel | `--z-panel`(81) | 侧栏 / 抽屉面板 |
| overlay / dialog | `--z-overlay`(60) / `--z-dialog`(83) | 遮罩 / 模态 |
| command | `--z-command`(90) | 命令面板 |
| companion | `--z-companion`(9999) | AI Presence 化身 |

**规则**：面板本身是 `--z-content`(18) 内的玻璃元件；侧栏/抽屉升 `--z-panel`(81)；模态升 `--z-dialog`(83)。任何面板不得自造 z 值。

---

## 3. 深度与阴影（Elevation）

沿用 DESIGN.md §6.1 三档阴影（均含顶部 1px 内高光，玻璃质感来源）：

| 档 | 阴影 | 用途 |
|---|---|---|
| `--elev-1` | `0 1px 0 rgba(255,255,255,.04) inset, 0 8px 24px rgba(0,0,0,.28)` | 普通面板 |
| `--elev-2` | `…0 18px 48px rgba(0,0,0,.40)` | 抬升面板 / 抽屉 |
| `--elev-3` | `…0 30px 80px rgba(0,0,0,.55)` | 模态 / 高亮面板 |

**规则**：禁止自定义 `box-shadow`（丢失玻璃内高光）；通知卡片用 `0 12px 30px rgba(0,0,0,.35)`。

---

## 4. 玻璃材质（Glass Material）

| 属性 | 规则 | 令牌 |
|---|---|---|
| 背景 | 半透明 surface 渐变（`--surface-2` → `--bg-2`） | `--surface` / `--surface-2` / `--bg-2` |
| 描边 | 1px 细描边 | `--border` |
| 模糊 | 26px（`.os-panel`）/ 28px（`.glass-panel` 字面，2px 偏差如实保留） | `--blur-glass`(26px) |
| 内高光 | 顶部 1px inset highlight | 阴影内置 |
| 圆角 | 22px（大面板）/ 16px（按钮）/ 10px（输入） | `--r-lg`(22) / `--r-md`(16) / `--r-sm`(10) |

**规则**：所有面板走玻璃拟态；禁纯扁平、禁重投影；浅色主题面板用 `--surface-2`/`--bg-2` 渐变（DESIGN.md §4.2）。

---

## 5. 边框与光效（Border & Glow）

| 用途 | 规则 | 令牌 |
|---|---|---|
| 常态描边 | 1px 低对比描边 | `--border`（如 `rgba(110,140,220,.14)`） |
| 焦点环 | accent 描边 + glow（键盘可达 WCAG AA） | `--accent` + `--glow` / `--shadow-glow` |
| 激活态 | accent 描边 + accent 辉光 | `--accent` + `--glow` |
| 强调 glow | 仅用于 Presence / 激活 / 品牌，**禁滥用** | `--glow`（颜色语义） |

**规则**：
- `--glow` 在 Phase A 已收口为**颜色语义**（`--shadow-glow` 承接 box-shadow 简写），全 9 主题生效（UI_SYSTEM v1.0 §1.6）。
- glow 是「意识核心」信号，**克制使用**：状态点、激活输入、品牌辉光；不当装饰满屏撒。

---

## 6. 动效（Motion）

| 维度 | 规则 | 令牌 |
|---|---|---|
| 时长 | 微动效：fast(.18s) / base(.28s) / slow(.45s) | `--motion-fast` / `--motion-base` / `--motion-slow` |
| 曲线 | 高级感缓动 | `--ease-premium`（`cubic-bezier(.16,1,.3,1)`） |
| hover | 微位移 `translateY(-1~3px)` | 克制 |
| 降级 | `prefers-reduced-motion` / `body.reduced-motion` 归零 | 全量 |

**规则**：面板展开/收起用 `--ease-premium`；状态脉动（thinking/planning/executing）仅经 AI Presence 层呈现（Phase 8 三唯一），面板本身不自行脉动。

---

## 7. 信息密度与排版（Density & Typography）

| 角色 | 字体 | 字号 | 字距 | 用途 |
|---|---|---|---|---|
| H3 分区标题 | `--font-display`(Orbitron) | 12px | `.20em` uppercase | 面板分区（`.os-panel > h3`） |
| Body | `--font-ui`(Rajdhani) | 14px | `.01em` | 正文 / 输入 |
| Caption | `--font-ui` | 12px | `.02em` | 辅助 / 时间戳 |
| Meta / 数值 | `--font-mono`(Share Tech Mono) | 11px | tabular-nums | 状态码 / 数字 |

**规则**：
- 面板内 padding 22px（`--space-3`），面板间距 22px，营造悬浮呼吸感（DESIGN.md §5）。
- 高密度信息靠**面板内网格**（如能力矩阵 2 列）承载，不压缩留白。
- 分区标题用大写 + 宽字距营造「控制台」秩序（DESIGN.md §3.3）。

---

## 8. 状态契约（State Contract，强制）

依据 UI_SYSTEM v1.0 §1.7（当前 hover 152 vs focus-visible 12，键盘「失明」），面板内所有可交互元件**强制**实现：

| 状态 | 要求 | 令牌 |
|---|---|---|
| hover | 微提亮 / 微位移 | `--motion-fast` + accent 提亮 |
| focus-visible | accent 描边 + glow（键盘可达） | `--accent` + `--shadow-glow` |
| active | 按下反馈 | `translateY(0)` |
| disabled | 透明度 `.5` + 禁交互 | `--input-disabled-op`(.5) |
| loading | 进度 / spinner（当前缺失 → 补 `--zz-toast__progress` 思路） | 补齐 |
| error | danger 描边（当前全站缺失 → 补 `--input-error-border`） | `--danger` |

**规则**：未实现 focus-visible / disabled / loading / error 的元件，视为**面板语言违规**。

---

## 9. 领域面板个性化（保留个性，统一容器）

F7 根因是领域面板未消费系统令牌。规则：
- **容器**统一走 `.os-panel` / `.zz-panel` 玻璃语法（border / radius / blur / padding / 标题）。
- **内容区**允许领域个性（图表、列表、地图），但须消费 `--surface` / `--radius` / `--ease-*` / `--panel-*` 令牌（F7 修复方向，见 `06`）。
- **禁**领域面板自造第二套 class 或硬编码 rgba。

---

## 10. 对齐声明

- 全部令牌值继承自 ui2.css / DESIGN.md，**不新建令牌值**。
- 承接 Final Convergence F1 / F3 / F7，转化为 `06` 的「激活 `.zz-input` + 补齐缺失原语 + 领域令牌化」要求。
- 遵守 DESIGN.md §7 Don'ts（禁第二套 class / 禁硬编码 rgba / 禁内联 style）。

> **🛑 STOP 声明**：本章为纯面板语言规则，0 代码改动，待 Review。
