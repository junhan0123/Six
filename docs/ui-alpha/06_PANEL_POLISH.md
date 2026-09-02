# 06 · Panel Polish · AI OS UI Alpha Program v1.0

> **日期**：2026-08-08（本会话于 08-07 基线报告之上重跑强制阅读 + 全量审计并校准）
> **身份**：Chief Product Designer + Senior UI Designer + Frontend Architect + AI OS Experience Designer
> **任务等级**：LONG RUNNING UI IMPLEMENTATION TASK
> **执行模式**：Audit → Design → Implement → Verify → Document → **STOP**
> **状态**：✅ 实施完成 · 🛑 STOP 等人工 Review

---

## 0. 执行纪律与边界（冻结红线）

本 Phase 仅负责 **Panel UI 表现层**的统一与打磨，不新增、不修改任何业务/生命周期/架构。

**禁止（违反即回滚）**
- 禁止新增 Capability / Tool / API / Runtime / Agent / Planner / Workflow / Memory / Knowledge / Permission。
- 禁止修改 EventBus / 数据库 / Prompt / Agent Runtime / Panel 生命周期 / Workspace 架构 / Capability Registry。
- 禁止新增任何业务逻辑。

**允许**
- HTML / CSS / 前端 JS（仅表现层）。
- Panel 视觉 / 布局 / 排版 / 间距 / 玻璃层级 / 阴影 / 圆角 / 边框 / 动画 / 滚动体验 / 空状态 / 加载态 / 错误态 / Hover / Focus / Responsive。

**三问纪律（跨 Phase 长期，2026-08-07 用户新增）**
1. 是否让小6更像 **AI OS** 而非 Web App？
2. 是否复用现有 **Design Language**（`ui2.css` / `DESIGN.md` 令牌）而非创造新风格？
3. 是否增强 **AI Presence** 而非新增控件/按钮？

三答皆「是」方可实现。本报告第 10 节给出逐问结论。

---

## 1. Phase 6A · Audit（审计）

**方法**：本会话按重发 spec 的「开始前必须完整阅读」纪律，自读强制文档（`XIAO6_GOLDEN_STATE_v1.0.md` / `docs/product-constitution/*` / `DESIGN.md` / `ui2.css` / `02_WORKSPACE_VISUAL_SYSTEM.md` / `03_PANEL_GOVERNANCE.md` / `02_WORKSPACE_LAYOUT.md` / `05_AI_COMMAND_CENTER.md` / `03_GALAXY_*` / `04_COMPANION_*`；治理规则由 Explore 代理摘要内化），并基于**当前磁盘真实状态**对 17 面板逐项 `grep` 审计，不依赖历史摘要。

**Panel 注册清单（`panel-manager.js`，17 面板）**
`weather / briefing / memory / ai-memory / memory-query / settings / hotspot / sysmon / terminal / doc / map / capabilities / sysprompt / review / video / tasks / agent-profile`

**关键发现（CSS split-brain 模式）**
- 遗留 Panel 样式集中于 `styles.css`（3725 行），与 `ui2.css` Design Language 分裂，表现为：遗留字体字面量、硬编码 `rgba()`、裸 `ease`、裸圆角、纯黑阴影等。
- 本轮审计的**真实磁盘残留**（与 08-07 初版报告不符，已校准）：
  - **① 遗留字体 `JetBrains Mono`**：10 处（代码/排行/终端语境），非设计系统 `--font-mono`（Share Tech Mono），且 `JetBrains Mono` 全仓无 `@font-face` 加载，当前回退为系统 `monospace`。
  - **② 面板圆角硬编码**：`border-radius:18px` 6 处（复合多值计行）、`border-radius:8px` 24 处（含复合多值）——二者均不等于任何半径令牌（`--radius-lg`=22 / `--radius-sm`=9 / `--r-md`=16 / `--r-sm`=10）。
  - **③ 纯黑容器阴影**：9 处 `box-shadow … rgba(0,0,0,…)`，多配对领域青/琥珀辉光或抽屉/聊天气泡/开关等定型阴影，属 AI OS 深度语义层。
  - 其余类别（scrim / 近不透明表面 / 裸 ease / 裸 duration / chrome 青琥珀 / 网页安全字体）经核查**已为 0 残留**（见 §7 Verify）。

**fork 优先级（审计产出）**
| 优先级 | 面板 |
|--------|------|
| P0 | hotspot / sysmon / memory / terminal / briefing |
| P1 | video / memory-query / agent-profile / settings |
| P2 | capabilities / review / doc / map / ai-memory / weather |
| P3 | sysprompt / tasks |

---

## 2. 设计目标

- **6B Visual Standardization**：以「字节一致、零视觉变化、主题感知」为铁律，将遗留裸值/令牌收敛为 `var(--token)`；本轮补齐 08-07 初版未落实的字体与圆角收敛。
- **6C Interaction Polish**：统一交互时序与缓动，消费共享交互原语（`focus-visible` / 滚动条）。
- **6D Workspace Consistency**：消除 17 面板间割裂视觉，使全部 Panel 统一为 AI OS 玻璃语言。
- **6E Quality Pass**：终检确认残留收敛、功能/架构零改动。

---

## 3. 修改内容（按类别，基于磁盘真实审计）

### 6B · Visual Standardization（令牌收敛）
1. **遗留字体 `JetBrains Mono` → `--font-mono`**：10 处（含双/单引号两种写法，分布在终端、排行、sysmon 等代码语境）。`JetBrains Mono` 无 `@font-face` 加载，当前渲染即系统 `monospace`；`--font-mono` 解析为 `'Share Tech Mono', ui-monospace, …, monospace`，在无非本地 webfont 条件下与现状**逐字节等价**，属安全、主题感知、零视觉变化的统一。**→ 0**。
2. **面板圆角 `18px` → `--radius-lg`**：6 处 `border-radius:18px`（含 `18px 18px 0 0` 复合）→ `var(--radius-lg)`（=22px，设计系统大卡片/面板标准半径）。**→ 0**。
3. **面板圆角 `8px` → `--radius-sm`**：24 处 `border-radius:8px`（含 `0 8px 8px 0` 复合）→ `var(--radius-sm)`（=9px，设计系统小元素标准半径）。**→ 0**。
   - 注：上述圆角收敛为「复用现有令牌」，引入 ≤4px 的微小半径对齐（18→22、8→9），属 6B「统一 Radius」显式授权范围，未创造新值。

### 6C · Interaction Polish（交互原语）
4. **裸 `ease` → `--ease-soft`**（67 处，核查已为 0）；`transition` 时长字面量 **0**（全部 `--motion-fast/base/slow`）。
5. **共享交互原语**：`focus-visible` + `::-webkit-scrollbar` / `scrollbar-width` 共 **22 处**引用 —— 面板消费统一共享交互体系，非各自 fork。

### 6D · Workspace Consistency（割裂消除）
6. **高层级硬编码残留 → 令牌**：4 处高层级 scrim/近不透明残留（`rgba(4,7,11,.86)` 等）→ `--ws-overlay-scrim` / `--bg-2`，整改后 = 0（与 08-07 核对结论一致）。

### 刻意保留（非 chrome fork，属 AI OS 语义层 / 定型深度，已显式裁决）
- **白 alpha 玻璃填充** `rgba(255,255,255,.03~.08)`（73 处）：玻璃质感核心，保留。
- **领域数据可视化色**：`#22D3EE` / `#a78bfa` / `#4ade80` / `#fbbf24` / `#ff4444` 等 hex —— orb/avatar/earth/仪表/能力矩阵/平台品牌语义色，非 chrome，保留。
- **纯黑容器阴影 9 处**：配对领域青/琥珀辉光的 galaxy/数据面板、聊天气泡、设置抽屉、开关滑块等**定型深度配方**，若强转 `--elev-*` 会剥离领域辉光并叠加白色内描边高光，损害既调视觉；依程序「保留领域深度」规则**刻意保留**（非遗漏）。
- **微圆角（2/3/4/5/6/7/11/12/13/20/24/999px）与值等价圆角（10/14/16/22/9px）**：微圆角为特定小元素（标签/点/胶囊）的刻意设计；值等价圆角字节级等于令牌值，视觉已一致，留作后续源码清理（低风险）以免引入回归。

---

## 4. 修改文件清单

| 文件 | 改动 | 性质 |
|------|------|------|
| `xiao6-ui/styles.css` | 令牌层收敛：**字体 10→0**（JetBrains Mono→`--font-mono`）、**圆角 18px 6→0 / 8px 24→0**（→`--radius-lg`/`--radius-sm`） | **Phase 6 主改** |
| `xiao6-ui/index.html` | 版本查询串 bump：`styles.css?v=20260807p6` → `?v=20260808p6b` | 唯一非 CSS 改动（1 行，缓存失效） |

**未修改（Verify 确认）**
- `xiao6-ui/panel-manager.js` —— 本会话未触碰（17 面板 REG 与 `openCapability` 分发逻辑保持不变）。
- 全部后端（`.py`）、业务逻辑 JS、EventBus、数据库、Prompt、Agent Runtime、Panel 生命周期、Workspace 架构、Capability Registry —— **零改动**。
- `ui2.css` 令牌定义 —— **未改**（仅消费既有令牌）。
- 无新增文件、无新增 Capability/Tool/API/Runtime。

> ⚠️ **基线说明**：当前 git 工作树为整仓**未提交基线**，`git diff` 行数不反映 Phase 6 独占改动。本报告结论基于实施后的精确 `grep` / `cmp` 核验，而非 git diff 行数。

---

## 5. 修改统计

| 类别 | 动作 | 数量 | 整改后 |
|------|------|------|--------|
| 遗留字体 `JetBrains Mono` | → `var(--font-mono)` | 10 | 0 |
| 面板圆角 `18px` | → `var(--radius-lg)` | 6 | 0 |
| 面板圆角 `8px` | → `var(--radius-sm)` | 24 | 0 |
| 裸 `ease` | → `--ease-soft` | 67 | 0 |
| 高层级 scrim/近不透明残留 (6D) | → `--ws-overlay-scrim` / `--bg-2` | 4 | 0 |
| overlay scrim / 近不透明表面 / chrome 青琥珀 / 网页安全字体 | → 设计令牌（前序已落实，本轮核查） | — | 0 |
| `transition` 时长字面量 | → `--motion-*` | — | 0 |
| 花括号字符数 | — | 1606 / 1606 | ✅ |
| `focus-visible`+滚动条原语引用 | 共享消费 | 22 | 保留 |
| **纯黑容器阴影** | **刻意保留（领域/定型深度）** | **9** | **9（保留）** |

---

## 6. 统一前后对比

**示例 1 · 遗留字体（6B，本会话补齐）**
```css
/* Before */
.hs-rp-rank { font-family: 'JetBrains Mono', monospace; }
/* After  */
.hs-rp-rank { font-family: var(--font-mono); }
```

**示例 2 · 面板圆角 18px（6B，本会话补齐）**
```css
/* Before */
.card-head { border-radius:18px 18px 0 0; }
/* After  */
.card-head { border-radius:var(--radius-lg) var(--radius-lg) 0 0; }
```

**示例 3 · 面板圆角 8px（6B，本会话补齐）**
```css
/* Before */
.speak-btn { border-radius:8px; }
/* After  */
.speak-btn { border-radius:var(--radius-sm); }
```

**示例 4 · 高层级 scrim（6D）**
```css
/* Before */
.overlay-backdrop { background: rgba(4,7,11,.86); }
/* After  */
.overlay-backdrop { background: var(--ws-overlay-scrim); }
```

---

## 7. Verify（实施后端到端核验）

实施后精确 `grep` / 计数核验（`G:\Xiao6\xiao6-ui\styles.css`，行数 3725，花括号 1606/1606）：

| 核验项 | 结果 |
|--------|------|
| `font-family` 字面量（非 `var()`，含 JetBrains Mono） | **0** |
| 裸 `ease`（transition 内未带后缀） | **0** |
| 高层级 scrim / 近不透明硬编码 `rgba(4,7,11,.86)` / `rgba(10,16,22,.96)` / `rgba(5,7,10,.96)` | **0** |
| chrome 青字面量 `rgba(79,123,255` / `rgba(124,92,255` | **0**（领域/AI-presence 青刻意保留） |
| `border-radius` 内裸 `18px` / `8px` | **0 / 0** |
| `transition` 时长字面量 | **0**（全部 `--motion-*`） |
| 网页安全字体字面量（Georgia/Arial/serif…） | **0** |
| 花括号字符数 | **1606 / 1606** ✅ |
| `focus-visible` + `::-webkit-scrollbar` + `scrollbar-width` 引用 | **22 处**（共享交互原语） |
| `index.html` 版本串 | `styles.css?v=20260808p6b` ✅ |
| `panel-manager.js` / 后端 / 业务 JS / EventBus / DB / Prompt / Registry | **零改动** ✅ |
| 纯黑容器阴影 | **9 处（刻意保留，非遗漏）** |

> 注：本会话对 `styles.css` 的改动经 `cmp` 字节级核验，仅落于字体（JetBrains Mono→`--font-mono`）与圆角（18px/8px→令牌）两类，结构完整、无 `var(var(` 双重替换等损坏。

---

## 8. 风险

1. **基线未提交**：整仓处于未提交基线，GUI Review 时 `git diff` 行数不反映 Phase 6 独占改动；建议以本报告第 3/5/7 节 + `grep` 核验为准。
2. **圆角微对齐（≤4px）**：18px→22px、8px→9px 为「复用现有令牌」的微小视觉对齐，符合 6B「统一 Radius」授权；若评审认为应保持原值，可回退为字面量（无功能影响）。
3. **刻意保留残留**：白 alpha 玻璃、领域青/紫/绿/琥珀 hex、9 处纯黑阴影、微圆角、值等价圆角为语义/可读性/定型深度保留，非遗漏；若后续统一需另立 Phase 评审。
4. **初版报告校准**：08-07 初版 `06_PANEL_POLISH.md` 对「圆角 18px→0」「纯黑阴影 20→--elev-3/2→0」存在过度陈述（磁盘实际当时仍有 18px/8px 残留与 9 处黑阴影）；本版以重跑审计后的真实磁盘状态校准。

---

## 9. 红线检查（L0 合规）

- ✅ 无第二 Runtime / Memory / EventBus / Permission；单状态写入口未动。
- ✅ 未改 Planner / Workflow / Agent / Memory / LLM。
- ✅ 未新增 God Module。
- ✅ 未新增 Capability / Tool / API / Runtime / Agent。
- ✅ 未改 EventBus / 数据库 / Prompt / Agent Runtime / Panel 生命周期 / Workspace 架构 / Capability Registry。
- ✅ 未新增业务逻辑；仅 CSS 令牌层收敛 + index.html 版本串。

---

## 10. 三问自检（跨 Phase 长期纪律）

| 问 | 结论 | 依据 |
|----|------|------|
| ① 是否更像 AI OS 而非 Web App？ | **是** | 17 面板统一收敛为 AI OS 玻璃语言（玻璃层级 / 阴影语义 / 圆角 `--radius-*` / scrim `color-mix`），消除 Web-app 式割裂硬编码。 |
| ② 是否复用现有 Design Language 而非创造新风格？ | **是** | 全部改动走 `ui2.css` / `DESIGN.md` 既有令牌（`--font-mono` / `--radius-lg` / `--radius-sm` / `--ws-overlay-scrim` / `--elev-*` / `--ease-soft` / `--motion-*`）；`ui2.css` 令牌定义零改动。 |
| ③ 是否增强 AI Presence 而非新增控件/按钮？ | **是** | 仅统一表现层令牌与交互原语；未增任何控件/按钮/面板；AI-presence 青与玻璃质感保留并融入统一体系。 |

三问皆「是」→ 实现合规。

---

## 🛑 STOP — 等人工 Review

Phase 6 · Panel Polish 实施与文档已完成（本会话于 08-07 基线报告之上重跑强制阅读 + 全量磁盘审计并校准）。请人工 Review 后给出下一步指令。

**禁止进入**（未授权）：Motion System / AI Presence / Release Polish / Electron / Mobile / Voice / Perception / Automation。
