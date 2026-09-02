# Design Token Audit — Xiao6 RC Poland Sprint v1.0

> **身份**：Senior Frontend Engineer + Design System Guardian
> **任务**：P3 统一 Design Token
> **日期**：2026-08-05
> **纪律**：仅 Design Token 收敛 / 重复令牌清理 / 文档记录；无功能 / 逻辑 / 架构变更。本报告为**审计报告**，代码收敛限「定义层 + 别名」，组件字面量路由列为后续建议。

---

## 1. 扫描基线（Audit）

全项目扫描 `xiao6-ui/*.css` 的 Radius / Shadow / Border / Hover / Focus / Opacity / Z-index / Spacing / Typography 使用频率（来自 `zz_audit.py`）。

### 1.1 Radius（圆角）

| 文件 | 主要字面量（频率） | Token 使用 |
|---|---|---|
| `styles.css` | `10px`×33、`50%`×32、`12px`×31、`14px`×25、`9px`×24、`6px`×18、`8px`×16、`16px`×12 | 几乎全字面量 |
| `ui2.css` | `8px`×4、`50%`×3、`999px`×2、`10px`×2、`9px`×1、`2px`×1 | `--radius-md`(14) / `--radius-lg`(=var(--r-lg)=22) |
| `premium.css` | `50%`×2、`999px`×1、`5px`×1、`inherit`×1 | `--r-lg` / `--r-md` / `--r-xl` / `--r-sm` |

**冲突发现**：存在两套 Radius 令牌族——
- `--r-*`（定义于 `ui2.css`）：`r-sm=10 / r-md=16 / r-lg=22 / r-xl=28`
- `--radius-*`（定义于 `ui2.css`）：`radius-sm=9 / radius-md=14 / radius-lg=22`

→ `radius-md`(14) ≠ `r-md`(16)，`radius-sm`(9) ≠ `r-sm`(10)，**语义重叠但值不同**。
→ 本 Sprint 已收敛：`--radius-lg` 别名到 `--r-lg`（同值 22px，零改动）。`md/sm` 差异标注为已知项（见 §4）。

### 1.2 Shadow（阴影）

| 文件 | Token | 字面量 |
|---|---|---|
| `styles.css` | `var(--glow)`×8、`0 0 8px var(--cyan)`×4 | `0 30px 90px rgba(0,0,0,.55)...`×3、`.6`×2、`.55`×2 等多套 |
| `ui2.css` | `0 0 12px var(--glow)`、`--elev-1/2/3` | `0 12px 30px rgba(0,0,0,.35)` 等 |
| `premium.css` | `--elev-1/2/3`×6 | `0 0 0 4px rgba(34,211,238,.18)` 等 |

**结论**：阴影令牌 **已存在**（`--glow` 强调辉光 + `--elev-1/2/3` 高度阴影），但 `styles.css` 仍大量使用字面量 + 直接 `var(--cyan)`。需后续路由（见 §4）。

### 1.3 Border（边框）

| 文件 | 主要用法 |
|---|---|
| `styles.css` | `1px solid var(--line)`×124、`1px solid var(--line-strong)`×23（**已 token 化，良好**） |
| `ui2.css` | `1px solid var(--border)`×14 + 字面量 rgba |
| `premium.css` | `var(--border)` + 字面量 rgba |

**✅ 本 Sprint 已收敛**：`ui2.css :root` 定义 `--line: var(--border); --line-strong: var(--border)`，旧 UI 的 `--line/--line-strong` 与新 UI 的 `--border` 单源化，消除双源。

### 1.4 Hover / Focus

| 指标 | styles.css | ui2.css | companion.css |
|---|---|---|---|
| `:hover` | 138 | 8 | 7 |
| `:focus-visible` | **1** | **0** | **0** |
| `outline: none` | 10 | 0 | 1 |

**⚠️ 可访问性缺口**：`:focus-visible` 全项目仅 1 处，`outline:none` 多处移除默认焦点环却未提供替代环。属 WCAG 关注项（详见 §4 建议）。

### 1.5 Opacity / Z-index / Spacing / Typography

| 类别 | 定义层令牌（本 Sprint 新增） | 使用现状 |
|---|---|---|
| Opacity | `--op-0..--op-100`（10 档） | `styles.css` 仍用字面量（`opacity:0`×73、`1`×52、`.5/.9/.35/.2/.55/.45`） |
| Z-index | `--z-base/z-rail/z-popover/z-modal/z-toast/z-companion`（1/5/30/60/82/9999） | `styles.css` 仍用裸数字（60×11、30、5、82、1、2、-1） |
| Spacing | `--space-1..4`（8/14/22/34） | 仅 `ui2.css` 少量使用，`styles.css` 全字面量 padding/margin |
| Typography | `--fs-10..--fs-18`（10/11/11.5/12/12.5/13/14/15/16/18） | `styles.css` 全字面量（`13px`×79、`12px`×60、`11px`×51…） |

---

## 2. 规范决策（Plan / Canonical）

| 类别 | Canonical 令牌 | 决策 |
|---|---|---|
| Radius | `--r-*`（r-sm/r-md/r-lg/r-xl） | 主族；`--radius-lg` 已别名；`md/sm` 待后续对齐 |
| Border | `--border`（旧 `--line/--line-strong` 别名） | ✅ 已单源化 |
| Shadow | `--elev-1/2/3` + `--glow` | 既有；字面量后续路由 |
| Z-index | `--z-*` | 本 Sprint 定义；裸数字后续路由 |
| Opacity | `--op-*` | 本 Sprint 定义；裸数字后续路由 |
| Spacing | `--space-*` | 本 Sprint 定义；字面量后续路由 |
| Typography | `--fs-*` | 本 Sprint 定义；字面量后续路由 |
| Focus | `--focus-ring`（**待建**） | 可访问性建议，GA 前必须补 |

---

## 3. 本 Sprint 已执行的收敛（零回归）

1. `ui2.css :root` 新增 **Design Token v2 定义层**：`--icon-size`、`--z-*`、`--op-0..--op-100`、`--fs-10..--fs-18`、`--space-1..4`、`--blur-glass`。（仅提供规范，零组件改动 → 零回归）
2. `--radius-lg: var(--r-lg)`（同值 22px，零改动）。
3. `--dur-*` 降为 `--motion-*` 别名（见 `MOTION_SYSTEM_REPORT.md`）。
4. `--line / --line-strong` 别名到 `--border`（Border 单源化）。
5. `.ic` 基样式 `width/height` → `var(--icon-size)`（见 `ICON_SYSTEM_REPORT.md`，零视觉变更）。

---

## 4. 残留差异与后续建议（非 RC 范围）

| 项 | 现状 | 建议 | 风险 |
|---|---|---|---|
| Radius `md/sm` 双值 | `--radius-md`=14 vs `--r-md`=16；`--radius-sm`=9 vs `--r-sm`=10 | 二选一为 canonical，另一别名 | 低（仅边角 1–2px 差异） |
| Shadow 字面量 | `styles.css` 多套 rgba 阴影 | 路由到 `--elev-*` / `--glow` | 中（需逐一核对视觉） |
| Z-index 裸数字 | `styles.css` 60/30/82/5/1/2/-1 | 路由到 `--z-*` | 低 |
| Opacity 裸数字 | `styles.css` `.5/.9/.35...` | 路由到 `--op-*` | 低 |
| Spacing 字面量 | `styles.css` padding/margin | 路由到 `--space-*` | 中（间距敏感） |
| Typography 字面量 | `styles.css` 全字号字面量 | 路由到 `--fs-*` | 中（排版敏感） |
| **`:focus-visible` 缺口** | 全项目仅 1 处 | **GA 前必须补 `--focus-ring` + `:focus-visible` 工具类** | **高（WCAG AA）** |

> 上述「路由」类建议涉及组件级字面量替换，需配合真实 Electron GUI 回归测试，故**不在 RC 冻结窗口内执行**（纪律：RC 仅收敛 / 清理 / 文档，避免未测视觉漂移）。列为 GA 前 Backlog。

---

## 5. 验证（Verify）

- ✅ 新增令牌（`--icon-size / --z-* / --op-* / --fs-* / --space-*`）均在 `ui2.css :root` 单一定义，`var()` 解析无未定义（除预存 `--sw`）。
- ✅ 别名收敛（`--radius-lg`、`--dur-*`、`--line/--line-strong`）未改任何组件视觉输出（同值替换）。
- ✅ CSS 括号平衡 6 文件断言通过；`node --check` 全 JS OK。
- ✅ 前端测试 16 PASS / 0 新增失败；纪律 grep 清洁。

---

## 6. 结论

Design Token 体系已形成**单一定义来源**（`ui2.css` 末加载、cascade 胜出）：Radius 主族 `--r-*`、Border `--border`、Shadow `--elev-*`+`--glow`、并补齐 Z-index / Opacity / Spacing / Typography 刻度。Border 双源已消除，Radius `lg` 已对齐。残留为 `md/sm` 双值差异与组件级字面量未路由，及 `:focus-visible` 可访问性缺口——均列为 GA 前 Backlog（RC 窗口内仅做定义层收敛，确保 0 回归）。
