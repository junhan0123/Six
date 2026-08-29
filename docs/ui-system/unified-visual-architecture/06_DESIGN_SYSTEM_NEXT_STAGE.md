# 06 · 设计系统下一阶段（Design System · Next Stage）

> **文档类型**：统一视觉架构设计 · 设计系统补完层
> **阶段**：Unified Visual Architecture Design Phase v1.0 · 只设计，不实现 · **0 代码改动**
> **上游依据**：`UI_SYSTEM_v1.0.md`（设计语言唯一权威）· `DESIGN.md` §2/§3/§6 · `final-convergence/00_AUDIT.md` · `07_MOTION_SYSTEM.md`（Phase 7）
> **生成日期**：2026-08-09

---

## 0. 定位：补完，非重建

`UI_SYSTEM_v1.0.md` 已是**设计语言唯一权威**（令牌 / 原语 / 主题 / 视觉语言）。其 §1.2 核心结论：**小6不需要第二套 Token 体系**，骨架已存在，问题是「已声明未接线」。

本章遵循 Golden State「禁止第二套 Token 体系」红线，只做 **6 个方向的补完**：
- **Color**：激活死令牌 + 完善强调/在场色。
- **Typography**：冻结字阶 + 令牌化硬编码字号。
- **Motion**：形式化 Motion System（承接 Phase 7）。
- **Depth**：把深度 ladder 升华为「空间语法」。
- **Spatial（新）**：定义 Galaxy↔Workspace 的空间关系（本蓝图核心新增）。
- **Component**：补齐缺失原语（含 `.zz-input`）。

> 本章**不重定义令牌值**，只规定「激活哪些死令牌、补齐哪些原语、Spatial 层如何组织」。

---

## 1. Color（色彩下一阶段）

### 1.1 现状
- 9 主题全覆盖（midnight / dark / quantum / light + 5 个 accent 变体）。
- Phase A 已收口 `--glow` 类型冲突（颜色语义），主题令牌冲突 **26 → 0**（UI_SYSTEM v1.0 §1.5/§1.6）。
- 角色令牌已定义：`--accent`/`--accent-2`/`--surface`/`--surface-2`/`--border`/`--text`/`--text-dim`/`--muted`/`--ok`/`--warn`/`--danger`/`--glow`/`--grid-line`。

### 1.2 下一阶段补完
| 项 | 要求 | 依据 |
|---|---|---|
| **激活强调双色** | 确认 `--accent`/`--accent-2` 在所有 9 主题的对比度与渐变可用性 | DESIGN.md §2.1 |
| **在场色令牌** | 正式化 `--presence-*` / `--tier-*`（ui2.css L376 已存在 15 个 presence·tier 令牌），作为 AI Presence 唯一颜色权威 | Phase 8 三唯一 |
| **WCAG AA 守门** | 9 主题下正文/次要/禁用灰阶守住 AA；浅色主题 `#0E7490`/`#0F766E`，深主题最低 `#5e6c96` | DESIGN.md §2.1/§7 |
| **语义色统一** | `--ok`/`--warn`/`--danger` 全主题一致；禁用更深灰阶跌破 AA | DESIGN.md §2.2 |

---

## 2. Typography（排版下一阶段）

### 2.1 现状
- 字阶已定义（DESIGN.md §3.2）：Display Hero 18 → Nano 10。
- 字体栈：`--font-display`(Orbitron/Rajdhani) / `--font-ui`(Rajdhani) / `--font-mono`(Share Tech Mono)。
- **缺口（UI_SYSTEM v1.0 §1.4）**：字号硬编码 **504 处 / 18 个不同 px 值**，仅 5 处用 `var()`；`--fs-*` 18 个令牌多为**死令牌**。

### 2.2 下一阶段补完
| 项 | 要求 |
|---|---|
| **冻结字阶** | 以 DESIGN.md §3.2 为唯一字阶；新增文本一律 `--fs-*`，禁裸 px |
| **激活死 `--fs-*`** | 把 504 处硬编码字号逐步路由到 `--fs-10..64` 阶梯（UI_SYSTEM v1.0 §1.3 实测 18 个 `--fs-*`） |
| **字体离线化** | 自托管 `@font-face` 指向 `fonts/*.woff2`，禁 CDN；无网络回落系统字体（DESIGN.md §3.1） |
| **数字对齐** | 数值/状态码一律 `tabular-nums` + `--font-mono` |

---

## 3. Motion（动效下一阶段）

### 3.1 现状
- 动效令牌已收敛：258 处 `var(--dur/--ease/--motion)`（UI_SYSTEM v1.0 §1.4）。
- Phase 7 已产出 `07_MOTION_SYSTEM.md`（Motion Token 单源）。
- 时长/曲线：`--motion-fast`(.18s)/`--motion-base`(.28s)/`--motion-slow`(.45s) + `--ease-premium`。

### 3.2 下一阶段补完
| 项 | 要求 |
|---|---|
| **承接 Phase 7** | 以 `07_MOTION_SYSTEM.md` 为 Motion 唯一真相，不另起炉灶 |
| **在场动效令牌** | 形式化 thinking / planning / executing 脉动令牌（`vitPulse` 仅此三态，ERROR 不脉动，见 Phase 8） |
| **降级全覆盖** | `prefers-reduced-motion` + `body.reduced-motion` 全量归零 |
| **注意力态缓动** | 为 `02` 的「探索态/操作态」定义缓动令牌（如 `--attention-ease`、`--attention-dur`） |

---

## 4. Depth（深度下一阶段：从 ladder 到 Spatial Grammar）

### 4.1 现状
- `--z-*` 29 档（UI_SYSTEM v1.0 §1.3），已与 ui2.css 对齐（DESIGN.md §6.3）。
- `--elev-1/2/3` 三档阴影（含顶部内高光）。

### 4.2 下一阶段补完
- **升华为「空间语法」**：depth 不仅是 z 值，更是「银河世界层 → 操作层 → 浮层 → 模态 → 化身」的**连续空间关系**（见 §5 Spatial）。
- 禁止裸 z 数字（DESIGN.md §6.3 纪律）。
- 阴影只经 `--elev-*`，禁自定义 box-shadow（丢失玻璃内高光，DESIGN.md §6.1）。

---

## 5. Spatial（空间层 · 本蓝图核心新增）⭐

> 这是 `UI_SYSTEM_v1.0.md` 尚未覆盖的层面——**宏观空间关系**。它把令牌/原语（微观）组织成「一个 AI OS 空间」（宏观）。

### 5.1 空间定义
- **世界层（World Layer）= Galaxy**：`--z-ground`(0) → `--z-stage`(4)，常驻、暗化、可被注意力提亮。
- **操作层（Operation Layer）= Workspace + Dock + Panels + AI Presence**：`--z-content`(18) 起，玻璃元件。
- **两层共享语法**：depth / glass / grid / glow / motion 完全一致 → 读起来是「一个空间」。

### 5.2 网格与边距（控制甲板隐喻）
| 项 | 规则 | 令牌 |
|---|---|---|
| 间距基数 | 8px 节奏（非标准 4 倍数，沿用项目） | `--sp-*`(18 档，待激活) / `--space-1..4` |
| 面板内距 | 22px 呼吸感 | `--space-3`(22) |
| 面板间距 | 22px | `--space-3` |
| 网格秩序 | 背景 `--grid-line` 细网格 + 面板内网格承载密度 | `--grid-line` |

### 5.3 注意力态令牌（新增提议，归 `02`）
| 令牌（提议） | 用途 |
|---|---|
| `--attention-world-dim` | 操作态下世界层亮度（~30%） |
| `--attention-world-focus` | 探索态下世界层亮度（~80%） |
| `--attention-ease` / `--attention-dur` | 两态连续缓动 |

> 以上为**设计层提议**，具体取值在 Visual Redesign 阶段以令牌落地，不在此阶段写值。

---

## 6. Component（组件下一阶段：补齐缺失原语）

### 6.1 现状（DESIGN.md §4/§9 + Final Convergence）
- 已成形：`zz-icon` / `zz-dialog` / `zz-toast` / `zz-toggle` / `zz-panel` / `zz-overlay`（部分）。
- **缺失（仅命名，未实现）**：`zz-dropdown` / `zz-menu` / `zz-tabs` / `zz-tooltip` / `zz-modal-card`（DESIGN.md §9.1）。
- **F1**：缺 `.zz-input` 正式原语，输入 4 套各写各的（Command Dock / Legacy `#input` / `.settings-input` / `.hs-chat-input`）。
- **Toast 双体系（F4）**：`.zz-toast` 与 Legacy `.toast` 并存。

### 6.2 下一阶段补完（仅设计契约，不实现）
| 原语 | 要求 |
|---|---|
| **`.zz-input`** | 落地Typography/Radius/Border/Focus/Accent/Background/Glow/Spacing/Motion 令牌化状态契约（Default/Hover/Focus-visible/Active/Disabled/Loading/Error）；让 4 套输入引用同一组令牌（消除 F1） |
| **`zz-dropdown` / `zz-menu`** | 统一下拉/菜单原语，承接 Overlay 单一管理器（DESIGN.md §4.7） |
| **`zz-tabs`** | 统一选项卡（Settings/领域面板复用，消除 `.settings-tab` 第二套） |
| **`zz-tooltip`** | 统一提示（键盘可达） |
| **`zz-modal-card`** | 内容层统一（`.modal-card` 升级） |
| **Toast/Modal 收口** | `.toast`→`.zz-toast`、`.modal`→`.zz-dialog` 迁移规划（F4/F6） |

> 缺失原语**只定义命名与契约**，实现留 Visual Redesign 阶段（遵守 DESIGN.md「缺失组件仅命名不实现」）。

---

## 7. 下一阶段边界纪律

- ❌ 不重建令牌体系（Golden State 红线）。
- ❌ 不新建令牌值（只激活死令牌 `--fs-*`/`--sp-*`、补齐原语命名）。
- ❌ 不改 Runtime / EventBus / AppState / Galaxy / Provider 后端。
- ✅ 所有补完引用既有 `--*` 与 `zz-` 体系。
- ✅ Spatial 层为**本蓝图新增**，不与 UI_SYSTEM v1.0 冲突（它管微观，本蓝图管宏观空间）。

> **🛑 STOP 声明**：本章为纯设计系统补完规划，0 代码改动，待 Review。
