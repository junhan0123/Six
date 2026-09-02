# 小6 Formal UI System v1.0

> **文档类型**：设计语言权威文档（Design Language Authority）
> **阶段**：Formal UI System v1.0 · Section 3 · Design Language Establishment
> **产出方式**：Audit → Decide → Design → Document → Verify → 🛑 STOP
> **代码改动**：**0**（本文件为纯设计文档，未修改任何 CSS / HTML / JS / 后端）
> **生成日期**：2026-08-09
> **上游依据**：`docs/ui-system/UI_ELEMENT_INVENTORY.md`（Section 2 全量盘点，645 行）+ 14 份原始证据文件

---

> 🟢 **Phase A 实施状态（2026-08-09）**：本节三大决策 **D-01 / D-02 / D-03 已全部实施完成** —— 主题令牌冲突自 **26 → 0**、`--glow` 类型冲突收口（新增 `--shadow-glow` composition token）、Spacing 死令牌激活 **88 处零残留**、红线零违反。本设计文档仍保持「纯设计文档」性质，下列裁决正文不再变更；实施细节与验收见 **`docs/ui-system/PHASE_A_TOKEN_AUTHORITY.md`**。

## 0. 文档定位与权威层级

### 0.1 本文档在权威体系中的位置

小6项目遵循 **Single Source Rule**（唯一真相源规则）。本文档的定位如下：

| 层级 | 文档 | 管辖范围 | 与本文档关系 |
|---|---|---|---|
| **L0 最高** | `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | 架构冻结红线（事件契约 / Runtime / Memory / Permission） | 本文档**不得违反**，只能在其约束内定义视觉 |
| 治理入口 | `docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md` | 治理流程 | 本文档受其流程约束 |
| 产品真相 | `docs/product-constitution/`（13 份 v1.0） | 产品定义 | 本文档为其视觉实现层 |
| **设计真相** | `xiao6-ui/DESIGN.md` | 既有设计约束（§7 Don'ts） | **本文档为其上位细化**，不推翻，只补全 |
| **本文档** | `docs/ui-system/UI_SYSTEM_v1.0.md` | **设计语言唯一权威**（Token / Layer / Primitive / Theme / Visual Language） | 自本文档发布起，任何 UI 视觉决策以本文档为准 |
| 证据层 | `docs/ui-system/UI_ELEMENT_INVENTORY.md` + 14 份探针 | 现状事实 | 本文档的**唯一事实输入**，不可被本文档改写 |

### 0.2 本文档不做什么（边界声明）

本文档 **是设计语言的定义**，不是实施记录。明确不包含：

- ❌ 不修改任何 `.css` / `.html` / `.js` 文件
- ❌ 不改动 Runtime / Agent / EventBus / AppState / Galaxy / AI Presence / Provider / Backend / API
- ❌ 不删除任何现有 UI 元素
- ❌ 不进入 Section 4（实施执行）
- ❌ 不提交 Git

所有涉及代码变更的内容，一律以「**Phase X 待执行**」形式登记在 §14 Migration Roadmap，**不在本阶段执行**。

### 0.3 术语约定

| 术语 | 定义 |
|---|---|
| **Primitive Token** | 无语义的原始值（如 `--cyan: #4fd1e8`），只描述"是什么颜色/多大" |
| **Semantic Token** | 有语义的角色值（如 `--accent`），只描述"用在哪个角色" |
| **Component Token** | 组件私有值（如 `--panel-header-bg`），只描述"哪个组件的哪个部位" |
| **Primitive（组件原语）** | 跨领域可复用的无业务语义组件（Button / Panel / Chip …） |
| **Domain Selector（领域选择器）** | 只服务单一业务面板的选择器（`.hs-*` / `.wx-*` …） |
| **名义权威** | 设计上应当生效的规则来源 |
| **实际生效权威** | 因 CSS 特异性/加载顺序而真正胜出的规则来源 |

---

## 1. Audit 数据基线（本文档的唯一事实输入）

> 本节数据全部来自 Section 2 与 Section 3 Audit 阶段的**真实读盘与探针实测**，不含任何推断。
> 数据凡有双口径差异，一律**双列标注**，不做单方面取舍。

### 1.1 CSS 资产总量

| 文件 | 行数 | 选择器 | 硬编码值 | 令牌定义 | 加载序 |
|---|---:|---:|---:|---:|---:|
| `styles.css` | 3613 | 1476 | 1306 | 0 | 1 |
| `premium.css` | 235 | 80 | 51 | 0 | 2 |
| `runtime-viz.css` | 162 | 32 | 68 | 0 | 3 |
| `execution-channel.css` | 144 | 22 | 48 | 0 | 4 |
| `ui2.css` | 1690 | 400 | 156 | **158–160** | **5（最后 = 最终权威）** |
| `companion.css` | 624 | 116 | 47 | 38 | 独立 |
| **合计** | **6468** | **2126**（唯一 1890） | **1676** | **196–198** | — |

**跨文件重复选择器**：29 组（含 `.btn-new` / `.chip` / `.glass-panel` / `.ic` / `.onb-card` / `.settings-switch*`(5 组) / `.premium-bg` / `.premium-focus` / `:root` / `html` / `body` / `*`）。

### 1.2 令牌体系现状（★ Section 3 最关键发现）

`ui2.css` **已存在一套结构完整但未接线的令牌体系**：

| 项目 | 实测值 |
|---|---|
| `:root` 块数量 | **4 个**（L4 主块 133 个 / L376 presence·tier 15 个 / L929 font 3 个 / L963 btn 9 个） |
| 令牌总定义数（全项目） | **228** |
| 实际被引用数 | **148** |
| **悬空引用**（用了但没定义） | **0** ✅ |
| **死令牌**（定义了但从未使用） | **80** ⚠️ |
| 主题块 | **9 个** × 每个 **29** 个令牌 |

**核心结论**：小6**不需要新建第二套 Token 体系**。骨架已经存在，问题是**"已声明未接线"**。
本文档的 Token 架构（§4）因此定位为 **"激活 + 归类 + 补齐"**，而非 **"重建"**。这是本次设计的根本范式，也是对 Golden State「禁止第二套 Token 体系」红线的直接遵守。

### 1.3 已有尺度令牌清单（ui2.css 实测）

| 族 | 数量 | 说明 |
|---|---:|---|
| `--fs-*` | 18 | 9px – 64px 字号阶梯 |
| `--sp-*` | 18 | 间距阶梯 |
| `--op-*` | 10 | 不透明度阶梯 |
| `--z-*` | 29 | ground/base/stage/orb/rail/hud/popover/scanlines/float/overlay(60)/panel(81)/dialog(83)/task/drawer(95)/menu(200)/modal-mask(9000)/companion(9999)/onboarding(9999) |
| `--radius-*` | 6 | xs 4 / sm 9 / md 14 / lg 22 / xl 28 / pill 999 |
| `--elev-*` | 3 | 高度阴影 |
| `--space-*` | 4 | 旧版间距（与 `--sp-*` 重叠） |
| `--sw-*` | 9 | 主题选择器渐变 |
| `--ws-*` | n | Workspace Surface |
| `--panel-*` | n | header / content / footer / toolbar / scrollbar |
| `--glass-1/2/3`、`--blur-glass` | 4 | 玻璃层级 |

### 1.4 令牌化率实测（Design 的直接依据）

| 维度 | 令牌化 | 硬编码 | 结论 |
|---|---:|---:|---|
| **圆角** | ~279 处 `var(--radius-*)` | 极少（51 处 `50%` 属合法圆形） | 🟢 已收敛 |
| **层叠** | ~45 处 `var(--z-*)` | ~10 处 | 🟢 基本收敛 |
| **动效** | 258 处 `var(--dur/--ease/--motion)` | — | 🟢 已收敛（`runtime-viz.css` = **0**，唯一缺口） |
| **字号** | **5 处** `var()` | **504 处**硬编码 / 18 个不同 px 值 | 🔴 几乎未令牌化 |
| **间距** | **0 处** `var(--sp-*)` | 100% 硬编码 | 🔴 **18 个间距令牌全部是死令牌** |

字号硬编码 Top：`13px×116` / `12px×83` / `11px×69` / `14px×65`。
gap 硬编码 Top：`8px×71` / `10px×53` / `6px×29` / `14px×21` / `12px×21`。

### 1.5 主题冲突实测

| 项目 | 实测值 |
|---|---|
| `ui2.css` 主题覆盖 | **9 个**全覆盖 |
| `styles.css` 主题覆盖 | **6 个**（dark-cyan / green / purple / amber / rose / light） |
| 同名令牌冲突 | **26 个** |
| **真实值不同**的冲突 | **10 个** |
| 特异性对比 | `styles.css body[data-theme]` = **(0,1,1)** ＞ `ui2.css [data-theme]` = **(0,1,0)** |

**关键矛盾**：`ui2.css` 加载最后（序 5），但 `styles.css` 的选择器特异性更高 → **加载顺序输给特异性**，形成「名义权威 = ui2，实际生效权威 = styles」的分叉。

真实值不同的 10 个：`--glow`（6 个彩色主题全不同）+ light 主题下的 `--line` / `--line-strong` / `--panel` / `--panel-solid` / `--void`。
其余 16 个（`--cyan` / `--teal` / `--dim` / `--txt` 等）为**同值冗余**，属可无损删除项。

### 1.6 `--glow` 类型冲突实测（P0 缺陷证据链）

| 使用点 | 数量 | 语义 |
|---|---:|---|
| `styles.css` 当**完整 box-shadow 简写** | **12** | `box-shadow: var(--glow)` |
| `styles.css` 当**颜色** | 2 | — |
| `ui2.css` 当**颜色** | 14 | `box-shadow: 0 6px 18px -6px var(--glow)` |
| `ui2.css` 别名 | 1 | `--input-focus-glow: var(--glow)` |
| **合计** | **28** | — |

**浏览器实测结果**（`_token_probe.json`）：

| 主题 | `--glow` 实际值类型 | 胜出方 |
|---|---|---|
| dark / quantum / midnight / light | **颜色** | ui2.css ✅ |
| **dark-cyan（默认）** / dark-green / dark-purple / dark-amber / dark-rose | **box-shadow 简写** | styles.css ⚠️ |

**造成的真实功能缺陷**：在 5 个彩色主题（含**默认主题 dark-cyan**）下，`ui2.css` 中所有 `box-shadow: <offsets> var(--glow)` 写法因值非法而被浏览器**整条丢弃**，实测后果：

1. `.os-nav-brand.active` 的 `navBrandShadow` = **`none`** —— 连 accent 描边一起丢失。
2. 全局 `:focus-visible`（ui2.css L1005-1018）的 `box-shadow: 0 0 0 4px var(--glow)` **同样失效** —— **WCAG 键盘焦点环在默认主题下破碎**。

→ 这是一条**可访问性 P0 缺陷**，非纯美学问题。

### 1.7 组件状态覆盖实测

| 状态 | 出现次数 | 评估 |
|---|---:|---|
| `:hover` | **152** | 🟢 充分 |
| `disabled` | 24 | 🟡 偏弱 |
| `:active` | 14 | 🔴 稀缺 |
| `:focus-visible` | **12** | 🔴 严重不足（对比 hover 152，比例 1:12.7） |
| `[aria-*]` | **2** | 🔴 几乎为零 |
| `prefers-reduced-motion` | 有覆盖 | 🟡 不完整 |

**结论**：小6现有 UI 是**"鼠标优先、键盘失明"**的。组件契约（§5）必须把 Focus / Disabled / Loading / Error 四态从"近乎空白"补成"强制项"。

### 1.8 组件原语存量实测（≥20 组件契约的现实基础）

| 组件 | 类名数 | 组件 | 类名数 | 组件 | 类名数 |
|---|---:|---|---:|---|---:|
| card | 40 | badge | 16 | tab | 7 |
| panel | 37 | item | 15 | toggle | 6 |
| btn | 31 | input | 14 | progress | 5 |
| toast | 19 | chip | 14 | menu | 3 |
| overlay | 19 | modal | 13 | **skeleton** | **0** |
| avatar | 19 | `ic-` | 13 | **scroll(组件)** | **0** |
| empty | 17 | icon | 10 | **loader** | **0** |
| list | 16 | dialog | 8 | — | — |

已成型的原语命名族：`.zz-*`（28 个：dialog / focus / icon / overlay / toast）、`.cp-*`（32 个：badge / box / caret / cat / empty / hint / input / item / kbd / label / list / mode / overlay / state / status）、`.glass-panel`、`.ic`、`.onb-*`、`.premium-focus`、`.settings-switch*`。

### 1.9 结构与可访问性实测

| 项目 | 实测值 |
|---|---|
| 双外壳 | `#osShell` 可见(z5) / `#app` `visibility:hidden`(z2) → **无双导航、无双主区** ✅ |
| 可聚焦元素总数 | 182 |
| **焦点陷阱** | **29 个**（其中 **17 个在 `#settingsPanel`**） |
| 陷阱成因 | 面板仅用 `transform` 移出视口，但保留 `pointer-events:auto` 且未设 `inert` / `visibility:hidden` → Tab 键仍可进入不可见面板 |

### 1.10 命名空间与领域选择器口径

| 口径 | 数值 | 状态 |
|---|---:|---|
| 唯一类名 | 1186 | ✅ |
| 唯一前缀（Inventory §8 记载） | **197** | 🟡 双口径 |
| 唯一前缀（Section 3 原始扫描） | **191** | 🟡 双口径（差 6，解析口径不同） |
| 选择器总量 | 2126 | ✅ |
| 已归类（去重口径 = 2126−503） | **1623** | ✅ |
| 已归类（含多归属重复求和） | **1851** | ✅ 差 228 = 多桶重复计数，非数据错误 |
| 未归类 | 503 | ✅ |
| **纯领域选择器（重点治理对象）** | **559** | ✅ **已验算吻合** |

**559 的构成验算**（全部位于 `styles.css`）：
Hotspot 210 + Weather 139 + Scene 73 + Map 36 + Mic 36 + Review 31 + Doc 26 + Tools 8 = **559** ✅

前缀 Top 20：`hs` 274 / `os` 262 / `zz` 149 / `wx` 145 / `mem` 139 / `settings` 91 / `hotspot` 86 / `avatar` 82 / `sm` 53 / `sc` 50 / `tele` 48 / `ts` 48 / `onb` 47 / `orb` 42 / `cp` 42 / `cap` 41 / `rv` 41 / `memq` 36 / `map` 32 / `doc` 28。
长尾：一次性前缀 **57 个**、出现 ≤3 次的前缀 **94 个**。

### 1.11 Audit 结论三条

1. **小6是"面板驱动"而非"组件驱动"架构** —— 原语层仅约 37 个通用选择器，领域面板独占 559 个。设计语言必须**先承认这个现实**，再逐步反转，而不是假装它是组件化系统。
2. **令牌骨架已存在但未接线** —— 0 悬空 / 80 死令牌。工作重点是**激活**，不是**重建**。
3. **权威分叉是所有视觉不一致的总根因** —— `--glow` 类型冲突、主题 10 处真值分叉、29 组重复选择器，全部源自「ui2.css 名义权威 vs styles.css 实际权威」这一条矛盾。

---

## 2. 三大核心决策裁决（D-01 / D-02 / D-03）

> 本节是整个 UI System v1.0 的**地基**。三条裁决一旦确立，后续 §3–§14 全部由其推导。
> 每条裁决包含：问题 → 证据 → 备选方案 → **裁决** → 影响面 → 实施归属。

---

### D-01 · `--glow` 到底属于什么类型？

#### 问题
同一个令牌 `--glow` 在两个文件中被赋予**两种互不兼容的类型**：一处是「颜色值」，一处是「完整 box-shadow 简写」。CSS 变量无类型系统，两种用法在不同主题下交替胜出，导致声明被静默丢弃。

#### 证据
- 定义端：`ui2.css :root` L4 定义 `--glow: rgba(80,120,255,0.40)`（**颜色**）；`styles.css body[data-theme=...]` 在 6 个彩色主题重定义为**阴影简写**。
- 使用端：28 处使用中，**12 处**（styles.css）当简写、**16 处**（ui2.css 14 + 别名 1 + styles 2 中的颜色用法）当颜色。
- 实测后果：5 个彩色主题（含默认 `dark-cyan`）下 ui2.css 侧全部 `box-shadow` 复合声明失效，`.os-nav-brand.active` 阴影 = `none`，**全局 `:focus-visible` 焦点环失效**。

#### 备选方案
| 方案 | 内容 | 评估 |
|---|---|---|
| A | 统一为 **box-shadow 简写** | ❌ 丧失可组合性；无法做 `0 0 0 4px var(--glow)` 这类焦点环；与 `--input-focus-glow` 别名语义冲突 |
| B | 统一为 **颜色值** | ✅ 可组合、可叠加、可用于 border/text/gradient；符合三级令牌体系中"Primitive = 原始值"的定义 |
| C | 拆成两个令牌 `--glow-color` + `--glow-shadow` | 🟡 可行但增加认知负担，且 `--glow-shadow` 本质是 Component Token，不应停留在主题层 |

#### 🔨 裁决

> **`--glow` 的唯一合法类型 = 颜色值（color）。**
>
> 1. `--glow` 归入 **Semantic Token · 辉光色角色**，其值**必须**是合法 `<color>`（推荐 `rgba()` 带透明度）。
> 2. **禁止**任何文件将 `--glow` 定义为 box-shadow 简写、多值列表或含长度单位的复合值。
> 3. 需要"整条辉光阴影"的场景，一律在**组件层**自行组合：`box-shadow: 0 0 24px var(--glow)`，或定义 Component Token（如 `--btn-primary-shadow`），**不得下沉到主题层**。
> 4. `--input-focus-glow: var(--glow)` 的别名写法**合法保留**，因为它继承的是颜色语义。

#### 影响面
- `styles.css` 12 处 `box-shadow: var(--glow)` 需改写为 `box-shadow: 0 0 24px var(--glow)` 形态（**具体数值在 Phase A 逐点确认，不做统一粗暴替换**）。
- `styles.css` 6 个彩色主题中 `--glow` 的重定义值需从"阴影简写"降解为"颜色"。
- 修复后自动连带解决：`.os-nav-brand.active` 描边丢失、`:focus-visible` 焦点环破碎两项 P0 缺陷。

#### 实施归属
**Phase A · Token Authority Consolidation** ✅ **已于 Phase A（2026-08-09）实施完成**，详见 `PHASE_A_TOKEN_AUTHORITY.md`。

---

### D-02 · Theme Token Authority 到底是谁？

#### 问题
主题令牌存在两个来源：`ui2.css [data-theme]`（9 主题全覆盖，加载序最后）与 `styles.css body[data-theme]`（6 主题，特异性更高）。26 个同名令牌冲突，10 个真实值不同。**加载顺序与特异性给出了相反的答案**，导致"名义权威 ≠ 实际生效权威"。

#### 证据
- 特异性：`body[data-theme="x"]` = **(0,1,1)** ＞ `[data-theme="x"]` = **(0,1,0)**。特异性优先于加载顺序 → **styles.css 实际胜出**。
- 但项目既定的 CSS 加载顺序权威（DESIGN.md）明确规定 `ui2.css` 最后加载 = **令牌/组件最终权威**。
- 结果：**设计意图（ui2）与运行时事实（styles）分叉**，`--glow` 类型冲突只是这条分叉最严重的一个表现。

#### 备选方案
| 方案 | 内容 | 评估 |
|---|---|---|
| A | 承认 `styles.css` 为权威 | ❌ 与 DESIGN.md 既定加载顺序权威冲突；且 styles.css 只覆盖 6/9 主题，无法承担权威；会把"历史债"合法化 |
| B | **`ui2.css` 为唯一权威**，styles.css 主题块降级并逐步清空 | ✅ 符合既定加载顺序权威、9 主题全覆盖、与 Token 体系归属一致 |
| C | 提升 ui2.css 特异性至 `body[data-theme]` 强行压制 | 🟡 可立即止血，但把"特异性军备竞赛"制度化，长期恶化 |

#### 🔨 裁决

> **唯一 Theme Token Authority = `ui2.css` 的 `[data-theme="…"]` 块。**
>
> 1. **9 个主题的全部 29 个主题令牌，唯一定义于 `ui2.css`。**
> 2. `styles.css` 的 6 个 `body[data-theme]` 块**降级为 Legacy Fallback**，标记为 `@deprecated`，在 Phase A 逐块清空，**不得新增任何主题令牌**。
> 3. 处理 26 个冲突的规则：
>    - **16 个同值冗余** → 直接从 styles.css 删除，零风险、零视觉变化。
>    - **10 个真值不同** → 取 **ui2.css 语义版本**为准；其中 `--glow` 按 D-01 一并降解为颜色；light 主题的 `--line` / `--line-strong` / `--panel` / `--panel-solid` / `--void` 五项需**逐项人眼复核**后再合并（light 主题对比度敏感）。
> 4. **禁止**通过提高特异性来"抢权威"。任何 `body[data-theme]`、`html[data-theme]`、`#id[data-theme]` 写法一律视为违规。
> 5. 主题令牌**只允许出现在主题块内**；组件文件中不得重定义主题令牌，只能消费。

#### 影响面
- `styles.css` 6 个主题块最终清空（约 26 条声明）。
- 修复后 9 个主题在所有文件中获得**一致的令牌语义**，`--glow` 分叉自动消失。
- 需回归验证：9 主题 × HUD / Settings / Command Palette / Bootstrap 四方一致性（Phase 9 已建立该回归口径，可直接复用）。

#### 实施归属
**Phase A · Token Authority Consolidation** ✅ **已于 Phase A（2026-08-09）实施完成**，详见 `PHASE_A_TOKEN_AUTHORITY.md`。

---

### D-03 · Primitive System 到底如何处理 premium.css vs ui2.css 双源？

#### 问题
组件原语疑似存在双源：`premium.css`（80 选择器）与 `ui2.css`（400 选择器）有 29 组跨文件重复选择器（`.glass-panel` / `.ic` / `.btn-new` / `.chip` / `.premium-focus` / `.settings-switch*` 等）。是否构成"第二套设计系统"？

#### 证据
- `ui2.css` 已有成型原语族：`.zz-*`（28）+ `.cp-*`（32）+ `.glass-panel` / `.ic` / `.onb-*` / `.settings-switch*`。
- `premium.css` 仅 235 行 / 80 选择器 / 0 令牌定义，自我定位为**纯增量增强层**（加载序 2，在 ui2.css 之前）。
- 关键事实：**premium.css 不定义任何令牌**（token_count = 0）→ 它不构成"第二套 Token 体系"，只是"额外样式补充"。
- 但重复选择器的存在意味着：同一个类在两处被定义，**维护者无法确定改哪里生效**。

#### 备选方案
| 方案 | 内容 | 评估 |
|---|---|---|
| A | 合并 premium.css 进 ui2.css | 🟡 一次性大改动，违反本阶段"最小侵入"，且 premium 的分层（在 ui2 之前加载）本身是有意设计 |
| B | **ui2.css 为唯一 Primitive 权威，premium.css 定位为纯增量增强层保留** | ✅ 尊重既有分层意图，零立即改动，只加约束 |
| C | 废弃 premium.css | ❌ 会造成视觉回退，且无收益 |

#### 🔨 裁决

> **Primitive System 唯一权威源 = `ui2.css`。**
>
> 1. **`ui2.css` 是组件原语的唯一定义地**。所有新增原语、所有原语的"基础态 + 状态矩阵"必须写在 `ui2.css`。
> 2. **`premium.css` 正式定位为「纯增量增强层」（Enhancement-Only Layer）**，允许保留，但受三条硬约束：
>    - **不得定义任何 CSS 变量**（保持 token_count = 0）；
>    - **不得定义新的原语类**，只能对 ui2.css 已有原语做视觉增强；
>    - **不得覆盖 ui2.css 原语的结构性属性**（display / position / 盒模型），只能改装饰属性。
> 3. **29 组跨文件重复选择器**：逐组判定归属，规则为「结构 + 状态 → ui2.css，装饰增强 → premium.css」，Phase B 执行。
> 4. **`styles.css` 中的领域面板**：**保留其造型语言**（不重写、不组件化），但**只允许消费令牌**，不得再引入新硬编码值。这是本裁决对 559 领域选择器的处理总纲。
>
> #### 🔑 D-03 附带的**范式校正**（本次设计最重要的一条）
>
> **小6不建立第二套 Token / Primitive 体系。**
> `ui2.css` 已有 **160 个令牌 + 60 个原语类**的完整骨架，其中 **80 个令牌处于"已声明未接线"状态**。
> 因此 UI System v1.0 的本质工作是：
>
> **① 激活（把 80 个死令牌接进真实样式）→ ② 归类（把 228 个令牌纳入 Primitive/Semantic/Component 三级）→ ③ 补齐（Focus/Disabled/Loading/Error 四态 + 缺失的 skeleton/loader）→ ④ 收敛（559 领域选择器改为只消费令牌）。**
>
> 明确**不是** "从零设计一套新的 Design System"。这既是效率选择，也是对 Golden State「无第二 Design System / 无第二 Token 体系」红线的直接遵守。

#### 影响面
- 零立即代码改动，只增加约束。
- 后续所有 Phase 的落点全部锁定 `ui2.css`，避免改动扩散。

#### 实施归属
约束即刻生效；重复选择器归属整理归 **Phase B · Primitive Consolidation**。

---

### 2.4 三大裁决的连锁效应

```
D-02（ui2.css = Theme 唯一权威）
      │
      ├──► 解决 26 个主题令牌冲突
      │
      └──► 使 D-01 可执行
                │
   D-01（--glow = 颜色）
                │
                ├──► 修复 .os-nav-brand.active 描边丢失（P0）
                └──► 修复 :focus-visible 焦点环破碎（P0 · 可访问性）
                              │
D-03（ui2.css = Primitive 唯一权威 + 激活而非重建）
                              │
                              └──► 焦点环修复后，§5 组件契约的 Focus 态才具备落地基础
```

三条裁决**必须按 D-02 → D-01 → D-03 的顺序实施**：先定权威，再修类型，最后收组件。逆序会导致修复被覆盖。

---

## 3. UI Layer Architecture（L0 – L7）

### 3.1 分层总图

```
┌──────────────────────────────────────────────────────────────┐
│ L7  Presence & Identity Layer      AI 存在感 · 不可组件化      │
│     Galaxy / Avatar / Presence / Orb                          │
├──────────────────────────────────────────────────────────────┤
│ L6  Domain Layer                   业务面板 · 559 领域选择器   │
│     Hotspot / Weather / Scene / Map / Mic / Review / Doc      │
├──────────────────────────────────────────────────────────────┤
│ L5  Feature Composition Layer      功能组合 · 面板内部结构     │
│     Settings / Memory / Capability / Tasks / Insight          │
├──────────────────────────────────────────────────────────────┤
│ L4  Shell & Navigation Layer       外壳 · 全局骨架             │
│     os-shell / rail / HUD / Command Dock / Context Drawer     │
├──────────────────────────────────────────────────────────────┤
│ L3  Surface Layer                  承载面 · Panel/Overlay/Card │
│     glass-panel / zz-overlay / zz-dialog / cp-box             │
├──────────────────────────────────────────────────────────────┤
│ L2  Component Primitive Layer      组件原语 · 无业务语义        │
│     Button / Input / Chip / Badge / Toggle / Toast / List     │
├──────────────────────────────────────────────────────────────┤
│ L1  Element & Reset Layer          元素基线 · 标签级样式        │
│     * / html / body / 滚动条 / 焦点环 / 字体基线                │
├──────────────────────────────────────────────────────────────┤
│ L0  Design Token Layer             设计令牌 · 唯一真相          │
│     Primitive → Semantic → Component（228 令牌）               │
└──────────────────────────────────────────────────────────────┘
              ▲ 依赖方向：上层只能向下依赖，禁止反向
```

### 3.2 各层定义与硬约束

| 层 | 名称 | 唯一归属文件 | 可以做 | **禁止做** | 现状 |
|---|---|---|---|---|---|
| **L0** | Design Token | `ui2.css`（`:root` + `[data-theme]`） | 定义 Primitive / Semantic / Component 三级令牌 | 定义任何选择器样式；引用组件类；在其他文件重定义主题令牌 | 🟡 骨架完整，80 死令牌 |
| **L1** | Element & Reset | `ui2.css`（元素级块） | `*` / `html` / `body` / 滚动条 / `:focus-visible` / 字体基线 | 定义带 class 的规则；写业务样式 | 🟡 焦点环因 D-01 破碎 |
| **L2** | Component Primitive | `ui2.css`（`.zz-*` / `.cp-*` / 通用类） | 定义无业务语义组件 + 完整状态矩阵 | 引用任何领域前缀（`.hs-*` / `.wx-*` …）；写硬编码值 | 🟡 60 类已有，状态矩阵残缺 |
| **L3** | Surface | `ui2.css`（`.glass-panel` / `--panel-*` / `--ws-*`） | 定义承载面层级、玻璃/实体、内边距、滚动区 | 直接放业务内容样式 | 🟡 令牌已备，未接线 |
| **L4** | Shell & Navigation | `ui2.css` + `styles.css`(legacy) | 全局骨架、导航、HUD、Command Dock、Drawer | 定义组件原语；定义主题令牌 | 🟢 已收敛（UI Consolidation v1.0） |
| **L5** | Feature Composition | `styles.css` / `execution-channel.css` | 面板内部结构组合 | 定义新原语；引入新硬编码 | 🟡 大量硬编码 |
| **L6** | Domain | `styles.css`（559 选择器） | **保留既有造型语言**，只消费令牌 | 新增硬编码值；新增一次性前缀；跨领域复用 | 🔴 100% 硬编码为主 |
| **L7** | Presence & Identity | `ui2.css` + `avatar-state.js` + `runtime-viz.css` + `companion.css` | Galaxy / Avatar / Presence / Orb 的专属视觉 | **任何组件化改造**；改动 P8 三唯一链路 | 🟢 已冻结保护 |

### 3.3 依赖方向规则（Layering Rule）

1. **单向依赖**：Lx 只能引用 L0…L(x−1) 的产物，**禁止**引用 L(x+1) 及以上。
2. **L0 无依赖**：令牌层不引用任何选择器。
3. **L2 领域洁净**：组件原语层出现任何领域前缀即为违规。
4. **L6 只消费不定义**：领域层不得定义可复用原语；若某领域样式被第 2 个领域复用，必须**上提到 L2**。
5. **L7 豁免**：Presence & Identity 层豁免"组件化"要求（见 §11 Domain Visual Exceptions），但**不豁免令牌消费要求**。

### 3.4 与 AI Presence（P8 三唯一）的边界

L7 中的 AI Presence 链路是 **Golden State 冻结资产**，本设计语言对其**只做保护性约束，不做改造**：

```
avatar-state.js  AvatarState.deriveFromGlobals()   ← 唯一状态权威（8 态纯函数）
        ↓
index.html       refreshHud() 单处 setAttribute('data-presence')  ← 唯一写入点
        ↓
ui2.css          body[data-presence] → --presence-color           ← 唯一颜色权威
```

**本文档新增的约束**：`--presence-*` 系列令牌归入 L0 的 **Semantic Token · 状态色**，其**定义权归 ui2.css**；`companion.css` 中的 `--presence-color: #5fb3c8` 属于已知冲突（Section 2 记录的 2 个真值不同令牌之一），处置方式为 **Phase A 改为引用 ui2 的语义令牌**，不得独立定义。

---

## 4. Token Architecture（三级体系 · 18 类）

### 4.1 三级模型

```
Primitive Token          Semantic Token           Component Token
（原始值，无语义）    →   （角色值，有语义）    →   （组件私有值）
--cyan: #4fd1e8          --accent: var(--cyan)     --btn-primary-bg: var(--accent)
--fs-13: 13px            --fs-body: var(--fs-13)   --panel-header-fs: var(--fs-body)
```

**三条铁律**：

| 规则 | 内容 |
|---|---|
| **R1 单向引用** | Component → Semantic → Primitive。**禁止**反向，**禁止**跨级（组件不得直接引用 Primitive，主题层除外） |
| **R2 主题只改 Semantic** | 9 个 `[data-theme]` 块**只能重定义 Semantic Token**。禁止在主题块中定义 Component Token 或 Primitive Token |
| **R3 组件只消费 Semantic/Component** | 选择器规则里出现的 `var()` 必须是 Semantic 或 Component 级；出现 Primitive 级（如 `var(--cyan)`）视为违规 |

> **现状差距**：当前 9 个主题块中的 29 个令牌**混杂了三级**（`--cyan` / `--teal` / `--amber` / `--red` 是 Primitive；`--accent` / `--bg` / `--text` 是 Semantic；`--panel` / `--panel-solid` 介于 Semantic 与 Component 之间）。
> **处置**：Phase A 拆分 —— 主题块只保留 Semantic，Primitive 上移至 `:root`，Component 下沉至组件块。

### 4.2 18 类令牌定义

| # | 类别 | 前缀 | 级别 | 现状 | 规格 |
|---:|---|---|---|---|---|
| 1 | **色彩 · 基础** | `--cyan` `--teal` `--amber` `--red` | Primitive | ✅ 已有 | 上移至 `:root`，主题块不再重定义 |
| 2 | **色彩 · 背景** | `--bg` `--bg-2` `--void` `--void2` | Semantic | ✅ 已有（`--void2` 死令牌） | 4 档：页面底 / 次级底 / 虚空 / 深虚空 |
| 3 | **色彩 · 表面** | `--surface` `--surface-2` `--panel` `--panel-solid` `--glass` | Semantic | ✅ 已有 | 与 §6 Surface 层级一一对应 |
| 4 | **色彩 · 文本** | `--text` `--text-dim` `--muted` `--txt` `--dim` `--dim2` | Semantic | ⚠️ **6 个存在语义重叠** | 收敛为 4 档：primary / secondary / tertiary / disabled |
| 5 | **色彩 · 描边** | `--border` `--line` `--line-strong` `--grid-line` | Semantic | ⚠️ `--grid-line` 死令牌 | 3 档 + 1 网格专用 |
| 6 | **色彩 · 强调** | `--accent` `--accent-2` | Semantic | ✅ 已有 | 主/次强调色，主题驱动 |
| 7 | **色彩 · 状态** | `--ok` `--warn` `--danger` | Semantic | ✅ 已有 | 补 `--info`（缺失） |
| 8 | **色彩 · 辉光** | `--glow` | Semantic | 🔴 **类型冲突（D-01）** | **唯一类型 = color**，禁作简写 |
| 9 | **色彩 · Presence** | `--presence-*` | Semantic | 🟢 P8 冻结 | 8 态映射，定义权归 ui2.css |
| 10 | **色彩 · Tier** | `--tier-*` | Semantic | ✅ 已有（P5 引入） | Command Center 分级 |
| 11 | **字号** | `--fs-*` | Primitive→Semantic | 🔴 **18 档定义 / 5 处使用 / 16 个死令牌** | 收敛为 **8 档语义**（§7） |
| 12 | **字体族 / 字重 / 行高 / 字距** | `--font-*` `--fw-*` `--lh-*` `--ls-*` | Semantic | ⚠️ 仅 `--font-display` / `--font-ui` 存在 | **需补齐 fw / lh / ls 三族** |
| 13 | **间距** | `--sp-*` `--space-*` | Primitive | 🔴 **18+4 档定义 / 使用 0 处 / 全部死令牌** | 收敛为 **8 档**，废弃 `--space-*`（§8） |
| 14 | **圆角** | `--radius-*` | Primitive | 🟢 **6 档 / ~279 处使用**（最健康） | 维持 6 档不变 |
| 15 | **高度 / 阴影** | `--elev-*` | Semantic | 🟡 3 档，使用偏低 | 扩为 **5 档**（§8） |
| 16 | **层叠** | `--z-*` | Semantic | 🟢 29 档 / ~45 处使用 | 收敛为 **9 语义档**，残余 10 处硬编码归并 |
| 17 | **动效** | `--dur-*` `--ease-*` `--motion-*` | Semantic | 🟢 258 处使用 | `runtime-viz.css` 0 处为唯一缺口；修复 `--dur-focus` 冲突 |
| 18 | **不透明度 / 模糊** | `--op-*` `--blur-glass` `--glass-1/2/3` | Primitive | 🟡 10+4 档，多为死令牌 | 保留 `--glass-*`，`--op-*` 收敛为 5 档 |

> **附加类（组件私有，不计入 18 类）**：`--panel-header/content/footer/toolbar/scrollbar-*`、`--ws-*`、`--sw-*`、`--btn-*`、`--input-*`。这些是合法的 **Component Token**，归属其组件块。

### 4.3 80 个死令牌的处置裁决

Audit 实测 **80 个"已声明未接线"令牌**。逐族裁决如下：

| 族 | 死令牌数 | 裁决 | 理由 |
|---|---:|---|---|
| `--fs-*`（10/11/14/15/16/18/20/22/24/26/28/34/44/56/64/9） | 16 | **保留 8 档 + 删除 8 档** | 字号收敛为 8 档语义后，多余档位删除（§7） |
| `--sp-*` | 18 | **保留 8 档 + 删除 10 档**，并在 Phase C **接线** | 间距是最大空洞，必须接线而非删除 |
| `--space-*` | 4 | **全部删除** | 与 `--sp-*` 完全重叠，属历史遗留双源 |
| `--op-*` | ~10 | **保留 5 档 + 删除 5 档** | 使用率为 0，过度设计 |
| `--panel-*` | ~8 | **保留并接线** | Surface 层级（§6）直接依赖，属"未接线"而非"多余" |
| `--ws-*` | ~5 | **保留并接线** | Workspace Surface 依赖 |
| `--void2` / `--grid-line` | 2 | **保留** | 主题块 29 令牌之一，删除会破坏主题契约完整性 |
| `--input-error-border` / `--input-focus-glow` | 2 | **保留并接线** | 组件契约（§5）的 Error / Focus 态直接依赖 |
| `--presence-remind` | 1 | **保留** | P8 冻结资产，不动 |
| `--z-companion` / `--z-modal` | 2 | **保留并接线** | 层叠语义完整性 |
| 其余 | ~10 | **逐个复核** | Phase A 人工判定 |

**处置总原则**：
- **能接线的优先接线**（`--sp-*` / `--panel-*` / `--ws-*` / `--input-*`）—— 这些是"骨架未接"，删了等于自废武功；
- **纯冗余才删除**（`--space-*` / 超编 `--fs-*` / 超编 `--op-*`）；
- **冻结资产一律保留**（`--presence-*` / 主题 29 令牌全集）。

### 4.4 令牌命名规范（新增令牌必须遵守）

```
--<类别>-<角色>[-<变体>][-<状态>]

✅ --text-secondary          ✅ --btn-primary-bg-hover
✅ --surface-raised          ✅ --fs-body
❌ --blue2                   （无语义，且带序号）
❌ --settings-title-color    （领域私有，应下沉为组件块内变量或直接用语义令牌）
❌ --glow-shadow             （违反 D-01：阴影属组件层，不入令牌）
```

四条硬约束：
1. **禁止序号式命名**（`--blue2` / `--gray3`），除非是 Primitive 阶梯（`--fs-13` 合法）。
2. **禁止领域前缀进入 L0**（`--hs-*` / `--wx-*` 一律违规）。
3. **禁止在 L0 之外定义主题令牌**（D-02）。
4. **新增 Semantic Token 必须同时在 9 个主题块中定义**，否则主题会出现"某主题下令牌缺失"。

---

## 5. Component Primitive Contract（22 组件）

### 5.1 契约模型

每个原语必须声明 **10 个状态**。这不是建议，是**准入条件**：任一状态缺失，该组件不得标记为"已纳入 UI System"。

| 状态 | 符号 | 定义 | 现状覆盖 |
|---|---|---|---:|
| Base | `B` | 默认静止态 | 152+ |
| Hover | `H` | 指针悬停 | **152** 🟢 |
| Active | `A` | 按下 / 选中 | **14** 🔴 |
| Focus | `F` | `:focus-visible` 键盘焦点 | **12** 🔴 |
| Disabled | `D` | 不可用 | **24** 🟡 |
| Loading | `L` | 异步进行中 | **≈0** 🔴 |
| Error | `E` | 校验/执行失败 | **≈0** 🔴 |
| Dark | `Dk` | 8 个暗色主题 | 🟢 |
| Light | `Lt` | light 主题 | 🟡 |
| Reduced Motion | `RM` | `prefers-reduced-motion` | 🟡 |

**图例**：✅ 已实现 · 🟡 部分实现 · ❌ 缺失 · 🔒 冻结豁免

### 5.2 22 个组件原语契约表

| # | 组件 | 归属类 | B | H | A | F | D | L | E | Dk | Lt | RM | 层 |
|---:|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | **Button** | `.btn-new` `.zz-btn` | ✅ | ✅ | 🟡 | ❌ | 🟡 | ❌ | ❌ | ✅ | 🟡 | 🟡 | L2 |
| 2 | **Icon Button** | `.ic` `.ic-*` | ✅ | ✅ | 🟡 | ❌ | 🟡 | ❌ | — | ✅ | 🟡 | 🟡 | L2 |
| 3 | **Chip / Tag** | `.chip` `.cp-badge` | ✅ | ✅ | 🟡 | ❌ | ❌ | — | — | ✅ | 🟡 | ✅ | L2 |
| 4 | **Badge** | `.cp-badge` `.badge-*` | ✅ | — | — | — | — | — | — | ✅ | 🟡 | ✅ | L2 |
| 5 | **Text Input** | `.cp-input` `.zz-input` | ✅ | 🟡 | — | 🟡 | 🟡 | ❌ | ❌ | ✅ | 🟡 | ✅ | L2 |
| 6 | **Textarea** | `.settings-textarea` | ✅ | 🟡 | — | 🟡 | 🟡 | ❌ | ❌ | ✅ | 🟡 | ✅ | L2 |
| 7 | **Select / Dropdown** | `.zz-select` `.dropdown-*` | ✅ | ✅ | 🟡 | ❌ | ❌ | ❌ | ❌ | ✅ | 🟡 | 🟡 | L2 |
| 8 | **Toggle / Switch** | `.settings-switch` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | — | ✅ | 🟡 | 🟡 | L2 |
| 9 | **Slider** | `input[type=range]` | ✅ | 🟡 | 🟡 | ❌ | ❌ | — | — | ✅ | 🟡 | ✅ | L2 |
| 10 | **List / List Item** | `.cp-list` `.cp-item` | ✅ | ✅ | ✅ | ❌ | 🟡 | ❌ | — | ✅ | 🟡 | ✅ | L2 |
| 11 | **Card** | `.card-*`（40 类） | ✅ | ✅ | 🟡 | ❌ | — | ❌ | — | ✅ | 🟡 | ✅ | L3 |
| 12 | **Panel** | `.glass-panel`（37 类） | ✅ | 🟡 | — | — | — | ❌ | — | ✅ | 🟡 | ✅ | L3 |
| 13 | **Dialog** | `.zz-dialog` | ✅ | — | — | 🟡 | — | ❌ | — | ✅ | 🟡 | 🟡 | L3 |
| 14 | **Modal / Mask** | `.modal-*` `--z-modal-mask` | ✅ | — | — | 🟡 | — | ❌ | — | ✅ | 🟡 | 🟡 | L3 |
| 15 | **Overlay** | `.zz-overlay` `.cp-overlay` | ✅ | — | — | 🔴**陷阱** | — | — | — | ✅ | 🟡 | 🟡 | L3 |
| 16 | **Drawer** | Context Drawer `--z-drawer` | ✅ | — | ✅ | 🔴**陷阱** | — | ❌ | — | ✅ | 🟡 | 🟡 | L3 |
| 17 | **Toast** | `.zz-toast`（19 类） | ✅ | 🟡 | — | ❌ | — | — | 🟡 | ✅ | 🟡 | 🟡 | L3 |
| 18 | **Tooltip** | — | ❌ | ❌ | — | ❌ | — | — | — | ❌ | ❌ | ❌ | L2 |
| 19 | **Tabs** | `.tab-*`（7 类） | 🟡 | 🟡 | 🟡 | ❌ | ❌ | — | — | 🟡 | 🟡 | 🟡 | L2 |
| 20 | **Progress** | `.progress-*`（5 类） | ✅ | — | — | — | — | ✅ | 🟡 | ✅ | 🟡 | 🟡 | L2 |
| 21 | **Skeleton / Loader** | — | ❌ | — | — | — | — | ❌ | — | ❌ | ❌ | ❌ | L2 |
| 22 | **Empty State** | `.cp-empty`（17 类） | ✅ | — | — | — | — | — | 🟡 | ✅ | 🟡 | ✅ | L3 |

### 5.3 契约缺口汇总（Design Debt Ledger）

| 缺口 | 严重度 | 影响组件数 | 归属 Phase |
|---|---|---:|---|
| **Focus 态几乎全缺**（`:focus-visible` 仅 12 处） | 🔴 P0 · 可访问性 | 20/22 | Phase D |
| **`--glow` 破坏全局焦点环**（D-01） | 🔴 P0 · 可访问性 | 全部 | Phase A |
| **29 个焦点陷阱**（17 在 `#settingsPanel`） | 🔴 P0 · 可访问性 | Overlay / Drawer / Dialog | Phase D |
| **Loading 态近乎为零** | 🟠 P1 | 12/22 | Phase D |
| **Error 态近乎为零** | 🟠 P1 | 8/22 | Phase D |
| **Tooltip / Skeleton / Loader 零实现** | 🟠 P1 | 3 个组件不存在 | Phase E |
| **`[aria-*]` 仅 2 处** | 🟠 P1 · 可访问性 | 全部 | Phase D |
| **Active 态稀缺**（14 处） | 🟡 P2 | 10/22 | Phase D |
| **Light 主题普遍未复核** | 🟡 P2 | 全部 | Phase F |

### 5.4 强制状态规范（各态的统一视觉定义）

> 以下为**语义定义**，不是最终 CSS。实施时一律通过令牌表达。

| 状态 | 统一规范 |
|---|---|
| **Hover** | 表面提亮一档（`--surface` → `--surface-2`）或描边转 `--accent`；**不得**改变尺寸/位移超过 1px；时长 `--dur-fast` |
| **Active** | 表面压暗或内缩 1px；**必须**与 Hover 视觉可区分 |
| **Focus** | **统一**：`outline: 2px solid var(--accent)` + `box-shadow: 0 0 0 4px var(--glow)`。**只用 `:focus-visible`，禁止用 `:focus`**（避免鼠标点击出现焦点环）。此规则已存在于 `ui2.css` L1005-1018，但因 D-01 在 5 个主题下失效，Phase A 修复后自动全局生效 |
| **Disabled** | `opacity: var(--op-disabled)` + `cursor: not-allowed` + `pointer-events: none`；**必须**同时设 `aria-disabled` |
| **Loading** | 内容区替换为 Skeleton 或 Progress；**禁止**只改文案；**必须**保持容器尺寸不跳动（防布局抖动） |
| **Error** | 描边 `--danger` + 辅助文本 `--danger`；**禁止**只用颜色表达（色盲可达性），必须配图标或文字 |
| **Reduced Motion** | 所有 `transition` / `animation` 降级为 `--dur-instant`（≤1ms）或直接移除；**Presence 脉动（`vitPulse`）除外**（属 L7 冻结资产，但仍应在 RM 下降低幅度而非频率） |

### 5.5 组件层禁止事项（Component Don'ts）

1. ❌ 组件规则中出现**硬编码颜色 / 字号 / 间距**（必须用令牌）。
2. ❌ 组件规则中出现**领域前缀**（`.hs-*` / `.wx-*` / `.mem-*`）。
3. ❌ 用 `:focus` 代替 `:focus-visible`。
4. ❌ 用 `transform` 移出视口来"隐藏"可交互面板（这是 29 个焦点陷阱的成因）——**必须**同时设置 `visibility:hidden` 或 `inert`。
5. ❌ 在组件层重定义主题令牌。
6. ❌ 通过提高特异性（`body .x` / `#id .x` / `!important`）来覆盖原语。
7. ❌ 新增第二套同类组件（如已有 `.btn-new` 就不得再造 `.button-v2`）。

---

## 6. Surface / Panel Hierarchy（承载面层级）

### 6.1 设计目标：Personal AI Operating System，不是 Dashboard

**Dashboard 的特征**（小6必须避免）：所有卡片等权、平铺陈列、玻璃遍地、每块都在争夺注意力。
**AI OS 的特征**（小6必须呈现）：**存在感居中、操作入口唯一、信息按需浮现、承载面有明确纵深**。

这一目标已在 UI Final Visual Review v1.0 中被验证有效（Hero 降为左上角水印徽章、Galaxy 成为唯一视觉中心、Command Dock 成为唯一主入口）。本节把该结论**固化为承载面规范**。

### 6.2 六级承载面（Surface Levels）

| 级 | 名称 | 语义 | 视觉规格 | 令牌 | 典型用例 |
|---:|---|---|---|---|---|
| **S0** | **Void（虚空）** | 宇宙底，非承载面 | 无边框、无阴影、可含 Galaxy | `--void` `--void2` | Galaxy 背景、`.galaxy-veil` |
| **S1** | **Ground（地面）** | 页面底层 | 纯色/极淡渐变，无玻璃 | `--bg` `--bg-2` | `os-shell` 主区 |
| **S2** | **Raised（浮起）** | 常驻结构面 | 轻描边 + 无/极弱阴影，**不加玻璃** | `--surface` `--border` `--elev-1` | Rail、HUD、Command Dock |
| **S3** | **Panel（面板）** | 功能承载面 | 描边 + 玻璃 1 档 + `--elev-2` | `--panel` `--glass-1` `--panel-*` | Settings、Memory、Capability |
| **S4** | **Floating（浮层）** | 临时浮层 | 描边强 + 玻璃 2 档 + `--elev-3` | `--panel-solid` `--glass-2` | Command Palette、Dropdown、Tooltip |
| **S5** | **Modal（模态）** | 打断式 | 遮罩 + 实体面 + `--elev-4/5` | `--glass-3` `--z-modal-mask` | Dialog、Onboarding、确认框 |

### 6.3 玻璃使用配额（Glass Budget）★ 核心约束

> **"到处玻璃"是小6当前最大的视觉失控风险**。本节设定硬配额。

| 规则 | 内容 |
|---|---|
| **G1** | 玻璃**只允许出现在 S3 / S4 / S5**。S0 / S1 / S2 **禁止**使用 `backdrop-filter` |
| **G2** | 同一屏幕内，**最多 2 层玻璃叠加**。第 3 层必须降级为实体面（`--panel-solid`） |
| **G3** | 玻璃**必须**配描边（`--line` 或 `--line-strong`），无描边玻璃在暗色主题下会"融化" |
| **G4** | `light` 主题下玻璃模糊半径**减半**（浅色背景玻璃对比度不足） |
| **G5** | `prefers-reduced-transparency` 或低性能设备下，玻璃**整体降级**为 `--panel-solid` |

### 6.4 注意力预算（Attention Budget）★ 反 Dashboard 的核心机制

任一时刻，屏幕上的"高注意力元素"总量受限：

| 等级 | 定义 | 同屏配额 | 允许的表达手段 |
|---|---|---:|---|
| **A0 · 存在感中心** | AI 本体 | **恰好 1 个** | Galaxy / Avatar / Presence 辉光 |
| **A1 · 主操作入口** | 用户的唯一起点 | **恰好 1 个** | Command Dock |
| **A2 · 当前任务** | 正在发生的事 | ≤ 1 个 | Timeline / Execution（空闲时折叠） |
| **A3 · 状态指示** | 系统在想什么 | ≤ 3 个 | HUD 徽标、Presence 色、轻量指示 |
| **A4 · 上下文** | 按需信息 | ≤ 1 面板 | Context Drawer（抽屉，非常驻） |
| **A5 · 辅助信息** | 背景信息 | 不限，但**必须低对比** | 水印、次级文本 `--text-dim` |

**违反判定**：若同屏出现 ≥2 个 A0/A1 级元素，或 ≥2 个常驻面板同时使用 `--accent` 强调，即视为**注意力争夺**，属设计缺陷。

### 6.5 Panel 内部结构标准

所有 S3 级面板必须遵循统一骨架（对应 ui2.css 已有但未接线的 `--panel-*` 令牌族）：

```
┌─ Panel ──────────────────────────────────┐
│  Header    --panel-header-*   固定，含标题 + 关闭  │
├──────────────────────────────────────────┤
│  Toolbar   --panel-toolbar-*  可选，筛选/操作      │
├──────────────────────────────────────────┤
│  Content   --panel-content-*  滚动区              │
│            --panel-scrollbar-*                   │
├──────────────────────────────────────────┤
│  Footer    --panel-footer-*   可选，主操作         │
└──────────────────────────────────────────┘
```

**硬约束**：
1. Header **必须**含可键盘触达的关闭控件（ESC 已由 Experience v1.0 中央治理，但需有可见控件）。
2. Content 区**必须**使用 `--panel-scrollbar-*` 统一滚动条，禁止各面板自定义。
3. 面板隐藏时**必须** `visibility:hidden` 或 `inert`，**禁止**只用 `transform`（29 焦点陷阱的直接成因）。

---

## 7. Typography Scale（8 档语义字号）

### 7.1 现状

- **18 个** `--fs-*` 令牌定义，**仅 5 处**使用 `var()`，**504 处**硬编码。
- 实际使用的 px 值分布高度集中：`13px×116` / `12px×83` / `11px×69` / `14px×65` —— **四个值占据主体**。
- 这说明：**真实的字号需求远少于 18 档**，18 档是过度设计。

### 7.2 8 档语义阶梯（正式定义）

| # | 语义名 | 映射 Primitive | px | 用途 | 现有硬编码归并来源 |
|---:|---|---|---:|---|---|
| 1 | `--fs-micro` | `--fs-10` | 10 | 角标、极小标注 | 9px / 10px |
| 2 | `--fs-caption` | `--fs-11` | 11 | 辅助说明、时间戳 | 11px（**69 处**） |
| 3 | `--fs-label` | `--fs-12` | 12 | 标签、按钮文字、Chip | 12px（**83 处**） |
| 4 | `--fs-body` | `--fs-13` | 13 | **正文基准** | 13px（**116 处**，最高频） |
| 5 | `--fs-body-lg` | `--fs-14` | 14 | 强调正文、列表主文本 | 14px（**65 处**） |
| 6 | `--fs-title` | `--fs-16` | 16 | 面板标题、区块标题 | 15px / 16px |
| 7 | `--fs-heading` | `--fs-20` | 20 | 主标题 | 18px / 20px / 22px |
| 8 | `--fs-display` | `--fs-28` | 28 | 展示级（Hero / 大数字） | 24px / 26px / 28px+ |

**超出 8 档的现有令牌**（`--fs-9` / `--fs-15` / `--fs-18` / `--fs-22` / `--fs-24` / `--fs-26` / `--fs-34` / `--fs-44` / `--fs-56` / `--fs-64`）：
- `--fs-34` 及以上（34/44/56/64）→ **保留为 L7 专用**（Galaxy / Avatar 大数字展示），不进入通用阶梯；
- 其余（9/15/18/22/24/26）→ **删除**，用例归并到最近档位。

### 7.3 字重 / 行高 / 字距（需补齐的三族）

当前**完全缺失令牌**，全部硬编码（字重 112 处、字距 90 处）。正式定义：

| 族 | 令牌 | 值 | 用途 |
|---|---|---|---|
| **字重** | `--fw-normal` / `--fw-medium` / `--fw-semibold` / `--fw-bold` | 400 / 500 / 600 / 700 | 4 档封顶，**禁止** 300/800/900 |
| **行高** | `--lh-tight` / `--lh-normal` / `--lh-relaxed` | 1.25 / 1.5 / 1.75 | 3 档 |
| **字距** | `--ls-tight` / `--ls-normal` / `--ls-wide` / `--ls-caps` | −0.01em / 0 / 0.02em / 0.08em | `--ls-caps` 专用于全大写标签 |

### 7.4 字体族

| 令牌 | 用途 | 约束 |
|---|---|---|
| `--font-display` | 展示级标题、Galaxy 数字、品牌 | 已存在，跨 ui2/companion 同值 ✅ |
| `--font-ui` | 全部界面文字 | 已存在 ✅ |
| `--font-mono` | 代码、ID、时间戳、数值对齐 | **缺失，需补** |

**约束**：全项目**只允许 3 个字体族令牌**。17 处 `font-family` 硬编码在 Phase C 归并。

---

## 8. Spacing / Radius / Elevation / Z-Index（有限尺度）

### 8.1 Spacing（8 档）★ 最大的令牌化空洞

**现状**：18 个 `--sp-*` + 4 个 `--space-*` 定义，**使用 0 处**，间距 **100% 硬编码**。

实测 gap 分布：`8px×71` / `10px×53` / `6px×29` / `14px×21` / `12px×21`。

| # | 令牌 | px | 用途 |
|---:|---|---:|---|
| 1 | `--sp-1` | 2 | 极窄（图标与文字贴合） |
| 2 | `--sp-2` | 4 | 紧凑内间距 |
| 3 | `--sp-3` | 6 | 小 gap（**29 处**归并） |
| 4 | `--sp-4` | 8 | **基准间距**（**71 处**归并，最高频） |
| 5 | `--sp-5` | 12 | 常规 gap（**21 处**归并） |
| 6 | `--sp-6` | 16 | 面板内边距 |
| 7 | `--sp-7` | 24 | 区块分隔 |
| 8 | `--sp-8` | 32 | 大区块 / 页面级留白 |

**处置**：`10px` / `14px` 两个高频值（53 + 21 处）**归并到 `--sp-4`(8) 与 `--sp-5`(12)**，属 1–2px 级视觉差异，Phase C 逐点复核。
`--space-*`（4 个）**整族删除**，属与 `--sp-*` 重叠的历史双源。

### 8.2 Radius（6 档 · 唯一健康的尺度，保持不变）

| 令牌 | px | 用途 |
|---|---:|---|
| `--radius-xs` | 4 | 徽标、极小控件 |
| `--radius-sm` | 9 | 输入框、按钮 |
| `--radius-md` | 14 | 卡片、Chip 容器 |
| `--radius-lg` | 22 | 面板 |
| `--radius-xl` | 28 | 大浮层、Dialog |
| `--radius-pill` | 999 | 胶囊 / 圆形 |

**现状 ~279 处令牌化，硬编码残余极少**（51 处 `50%` 属合法圆形写法，**允许保留**）。
**约束**：不新增档位；`50%` 仅允许用于真圆形元素（Avatar / Orb / 圆形图标按钮）。

### 8.3 Elevation（3 档 → 5 档）

| 令牌 | 语义 | 对应 Surface |
|---|---|---|
| `--elev-0` | 无阴影 | S0 / S1 |
| `--elev-1` | 轻浮起 | S2 |
| `--elev-2` | 面板 | S3 |
| `--elev-3` | 浮层 | S4 |
| `--elev-4` | 模态 | S5 |

**约束**：
1. Elevation **只用 `box-shadow`**，不用 `filter: drop-shadow`（性能）。
2. **禁止裸 `rgba()` 阴影**（DESIGN.md §7 已有此 Don't）。已知历史债：P6 保留的 **9 处黑阴影**，登记在 Phase F 处理，**本阶段不动**。
3. 辉光（glow）**不属于 Elevation**，是 Accent 表达，按 D-01 用 `--glow` 颜色自行组合。

### 8.4 Z-Index（29 档 → 9 语义档）

现有 29 个 `--z-*` 覆盖 ground → onboarding(9999)。收敛为 9 个语义档：

| 语义档 | 数值区间 | 归并的现有令牌 |
|---|---:|---|
| `--z-ground` | 0 | ground |
| `--z-base` | 1–5 | base, stage, orb |
| `--z-shell` | 10–20 | rail, hud |
| `--z-float` | 50–60 | float, overlay(60), popover, scanlines |
| `--z-panel` | 80–85 | panel(81), dialog(83) |
| `--z-drawer` | 90–95 | task, drawer(95) |
| `--z-menu` | 200 | menu |
| `--z-modal` | 9000 | modal-mask(9000) |
| `--z-topmost` | 9999 | companion, onboarding |

**约束**：
1. **禁止**在选择器中写裸 `z-index` 数值（残余约 10 处，Phase C 归并）。
2. **禁止**新增介于既有档位之间的"插队值"（如 `z-index: 82`）。
3. `companion` 与 `onboarding` 同为 9999，属**已知并列**，需在 Phase F 明确先后（当前无实际冲突，因两者不同屏共存）。

### 8.5 Motion（已收敛，只补缺口）

| 项目 | 现状 | 处置 |
|---|---|---|
| `var(--dur/--ease/--motion)` 使用 | **258 处** 🟢 | 维持 |
| `runtime-viz.css` 令牌使用 | **0 处** 🔴 | Phase C 接入（唯一缺口） |
| `--dur-focus` 冲突 | ui2 `700ms` vs companion `.42s` | Phase A 统一取 **ui2 值** |
| `prefers-reduced-motion` | 部分覆盖 | Phase D 补全至所有动效组件 |

---

## 9. Theme Contract（9 主题）

### 9.1 主题全集（唯一权威清单）

| # | 主题 ID | 明暗 | 定位 | ui2.css | styles.css |
|---:|---|---|---|:-:|:-:|
| 1 | `dark` | 暗 | 中性暗色 | ✅ | ❌ |
| 2 | `quantum` | 暗 | 量子（冷蓝紫） | ✅ | ❌ |
| 3 | `midnight` | 暗 | 午夜（深蓝） | ✅ | ❌ |
| 4 | **`dark-cyan`** | 暗 | **默认主题** | ✅ | ⚠️ 冲突 |
| 5 | `dark-green` | 暗 | 青绿 | ✅ | ⚠️ 冲突 |
| 6 | `dark-purple` | 暗 | 紫 | ✅ | ⚠️ 冲突 |
| 7 | `dark-amber` | 暗 | 琥珀 | ✅ | ⚠️ 冲突 |
| 8 | `dark-rose` | 暗 | 玫瑰 | ✅ | ⚠️ 冲突 |
| 9 | `light` | 亮 | 唯一亮色主题 | ✅ | ⚠️ 冲突 |

**归一化规则**（已由 Phase 9 Release Polish 确立，本文档确认并锁定）：
- `normalizeTheme` **只折叠 `system` → `dark-cyan`**；
- **`dark` 是有效主题**，不得被折叠；
- 四方（HUD / Settings / Command Palette / Bootstrap）必须提供**完全相同的 9 项主题列表**与**相同默认值 `dark-cyan`**。

### 9.2 主题契约的 29 个令牌（Theme Token Set）

每个 `[data-theme]` 块**必须完整定义以下 29 个令牌，一个不缺**：

```
bg  bg-2  surface  surface-2  border
text  text-dim  muted
accent  accent-2  glow
ok  warn  danger
grid-line  void  void2
panel  panel-solid  glass
line  line-strong
cyan  teal  amber  red
txt  dim  dim2
```

**契约条款**：

| 条款 | 内容 |
|---|---|
| **T1 完整性** | 9 个主题块 × 29 个令牌 = **261 条定义，缺一即违约**。缺失会导致该主题下继承 `:root` 默认值，产生"半个主题" |
| **T2 唯一定义地** | 全部定义于 `ui2.css`（D-02 裁决）。`styles.css` / `companion.css` **不得**定义主题令牌 |
| **T3 类型一致** | 同一令牌在 9 个主题中**必须是同一类型**。`--glow` 必须 9 个主题全为 `<color>`（D-01 裁决） |
| **T4 语义不崩坏** | 切换主题后，组件的**语义角色不得改变**：`--danger` 在任何主题下都必须是"危险色"，不得在某主题变成装饰色 |
| **T5 对比度下限** | `--text` 对 `--bg` 的对比度 ≥ **4.5:1**；`--text-dim` 对 `--bg` ≥ **3:1**；`--accent` 对 `--surface` ≥ **3:1** |
| **T6 三级纯净** | 主题块**只允许**重定义 Semantic Token。当前混入的 Primitive（`--cyan` / `--teal` / `--amber` / `--red`）在 Phase A 上移至 `:root` |
| **T7 light 特殊处理** | `light` 主题的玻璃模糊减半（G4）、阴影减弱、`--line` 系需单独调优。**light 是最易崩坏的主题，任何 Phase 都必须单独验收** |

### 9.3 已知主题冲突处置表

| 冲突令牌 | 主题范围 | 类型 | 处置 |
|---|---|---|---|
| `--glow` | 6 个彩色主题 | 🔴 **类型冲突** | D-01：统一为 color，删除 styles.css 定义 |
| `--line` / `--line-strong` | light | 🟡 真值不同 | 取 ui2 值，**人眼复核**后合并 |
| `--panel` / `--panel-solid` | light | 🟡 真值不同 | 取 ui2 值，**人眼复核**后合并 |
| `--void` | light | 🟡 真值不同 | 取 ui2 值 |
| 其余 16 个 | 6 主题 | 🟢 同值冗余 | 直接删除 styles.css 侧，零风险 |
| `--dur-focus` | 全局 | 🟡 ui2 `700ms` vs companion `.42s` | 取 ui2 值 |
| `--presence-color` | 全局 | 🟡 ui2 `var(--presence-idle)` vs companion `#5fb3c8` | companion 改为引用 ui2 语义令牌 |

### 9.4 主题验收口径（复用 Phase 9 回归）

任何涉及主题的改动，必须通过 **9 主题 × 4 方一致性回归**：

1. HUD 主题切换器 —— 9 项完整、默认 `dark-cyan`
2. Settings 主题面板 —— 9 项完整、与 HUD 同序
3. Command Palette 主题命令 —— 9 项完整
4. Bootstrap + `normalizeTheme` —— 只折叠 `system`，`dark` 保持有效
5. HUD MutationObserver 同步正常

---

## 10. AI OS Visual Language（AI 操作系统视觉语言）

### 10.1 反面定义：什么**不是** AI OS 视觉语言

> ❌ **"到处玻璃 + 青色 + 发光 = AI OS"** —— 这是最常见也最致命的误解，本节明确禁止。

| 反模式 | 为什么错 | 正确做法 |
|---|---|---|
| **玻璃遍地** | 玻璃是"浮层"的信号。遍地玻璃 = 没有任何东西真正浮起 = 纵深丧失 | 玻璃配额 G1–G5（§6.3），只在 S3–S5 |
| **青色刷满** | `--accent` 是"这里需要你注意"的信号。刷满 = 无处需要注意 | Accent 配额（§10.3） |
| **处处发光** | 辉光是"AI 活着"的信号，属 Presence 专属语汇 | 辉光只服务 A0/A1（§10.4） |
| **等权卡片墙** | 这是 Dashboard 语法，不是 OS 语法 | 注意力预算 A0–A5（§6.4） |
| **科幻装饰线/扫描线堆砌** | 装饰不产生信息，只消耗注意力 | 装饰元素必须承载状态语义，否则删除 |

### 10.2 正面定义：AI OS 的四条视觉原则

| # | 原则 | 内容 | 可验证判据 |
|---:|---|---|---|
| **P1** | **存在感优先（Presence First）** | 屏幕上永远有且只有**一个** AI 存在感中心，它比任何面板更重要 | 遮住 Galaxy/Avatar 后，界面应立刻"失去主体" |
| **P2** | **唯一入口（Single Entry）** | 用户的操作起点**唯一且恒定**（Command Dock），不因页面变化而漂移 | 任意界面状态下，"我该从哪开始"只有一个答案 |
| **P3** | **按需浮现（On-Demand Surfacing）** | 信息默认收起，被召唤时才浮现；空闲时界面应"安静" | 空闲态截图中，非 A0/A1 元素应低对比、可忽略 |
| **P4** | **状态可读（Legible State）** | 系统在想什么/在做什么，必须通过**视觉**而非文字说明可读 | 静音看屏，能判断 AI 是 idle / thinking / executing / error |

### 10.3 Accent 使用配额

| 规则 | 内容 |
|---|---|
| **A1** | 同屏 `--accent` 作为**填充色**（背景/大面积）的元素 ≤ **1 个** |
| **A2** | 同屏 `--accent` 作为**描边/文字**的元素 ≤ **5 个** |
| **A3** | `--accent-2` 仅用于**渐变第二色**与**次级强调**，不得独立作主强调 |
| **A4** | 状态色（`--ok` / `--warn` / `--danger`）**优先级高于** `--accent`：当元素处于状态态时，状态色覆盖 accent |

### 10.4 辉光（Glow）语汇专属化

**辉光在小6中不是装饰，是"AI 生命体征"的语汇。** 因此：

| 规则 | 内容 |
|---|---|
| **GL1** | 辉光**只允许**用于：① AI Presence（Avatar/Orb/Galaxy）② 焦点环（`:focus-visible`）③ 唯一主入口（Command Dock 激活态） |
| **GL2** | **禁止**普通卡片、列表项、普通按钮使用辉光 |
| **GL3** | 辉光**动态**（脉动）仅限 Presence 的 THINKING / PLANNING / EXECUTING 三态（P8 冻结规则：**ERROR 不脉动**） |
| **GL4** | 辉光通过 `--glow` 颜色令牌 + 组件层组合实现（D-01），**禁止**把整条阴影塞进令牌 |

### 10.5 运动语汇（Motion Language）

| 语汇 | 含义 | 时长 | 用例 |
|---|---|---|---|
| **Emerge（浮现）** | 信息按需出现 | `--dur-normal` | 面板打开、Drawer 展开 |
| **Settle（落定）** | 操作已被接收 | `--dur-fast` | 按钮 active、Chip 选中 |
| **Pulse（脉动）** | AI 正在思考/执行 | 循环 | **仅 Presence 三态** |
| **Fade（隐没）** | 信息退场 | `--dur-fast` | Toast 消失、面板关闭 |

**禁止**：弹跳（bounce）、旋转装饰、视差滚动、无语义的持续动画 —— 这些是 Web App 语汇，不是 OS 语汇。

---

## 11. Domain Visual Exceptions（领域视觉例外）

### 11.1 例外的正当性

**并非所有 UI 都应该被组件化。** 强行把 Galaxy 拆成"通用组件"只会产出一个没人复用的畸形抽象。本节明确定义**豁免组件化**的范围。

### 11.2 三类例外

| 类别 | 成员 | 豁免内容 | **不豁免**内容 |
|---|---|---|---|
| **E1 · Identity（身份视觉）** | Galaxy、Avatar、Orb、`.galaxy-veil` | 豁免组件化、豁免原语契约（§5）、豁免 Surface 层级（§6） | ❌ 不豁免**令牌消费**（颜色必须来自主题令牌）<br>❌ 不豁免**主题契约**（9 主题下必须正常）<br>❌ 不豁免 **Reduced Motion** |
| **E2 · Presence（存在感）** | `body[data-presence]`、`--presence-*`、`vitPulse` | 豁免组件化；**且属 Golden State 冻结，禁止任何改动** | ❌ 不豁免令牌归属（`--presence-*` 定义权归 ui2.css） |
| **E3 · Visualization（可视化）** | `runtime-viz.css`、`execution-channel.css`、Weather/Map 图形层 | 豁免组件化、豁免 8 档字号（数据可视化可用专用字号） | ❌ 不豁免**动效令牌**（`runtime-viz.css` 当前 0 处使用，属违规，Phase C 修复）<br>❌ 不豁免颜色令牌 |

### 11.3 例外申请规则（防止例外泛滥）

新增视觉例外必须同时满足**全部 4 条**，否则一律走标准组件化路径：

1. 该视觉**只服务单一身份/可视化目的**，不存在第二个复用场景；
2. 强行组件化会产生**只有一个使用者的抽象**；
3. 它**不承载常规交互**（不是按钮/输入/列表）；
4. 它**仍然消费令牌**，只是不遵守组件契约。

> **当前例外总数 = 3 类。任何新增必须记录在本节，并说明四条满足情况。**

---

## 12. 559 个 Domain Selectors 的分类与迁移规则

### 12.1 总原则

> **保留造型语言，收敛技术实现。**
>
> 559 个领域选择器承载了小6各业务面板的**独特造型**，这些造型是产品资产，**不删、不重写、不强行组件化**。
> 需要收敛的只有一件事：**把硬编码值换成令牌消费**。

### 12.2 A–G 七类分类

| 类 | 名称 | 判定标准 | 选择器数 | 处置动作 | Phase |
|---|---|---|---:|---|---|
| **A** | **Tokenize（令牌化）** | 纯样式差异，值可映射到现有令牌 | ~300 | 硬编码 → `var()`，**造型不变** | C |
| **B** | **Promote（上提原语）** | 已被 ≥2 个领域复用的样式 | ~40 | 上提到 L2 `ui2.css`，领域侧改为引用 | E |
| **C** | **Keep as Domain（保留领域）** | 单领域独有造型，无复用可能 | ~120 | **原样保留**，仅令牌化 | C |
| **D** | **Merge（同族合并）** | 同领域内近似规则（如 `.hs-*` 内部重复） | ~50 | 合并为带修饰符的单一规则 | E |
| **E** | **Exception（视觉例外）** | 属 §11 三类例外 | ~30 | 豁免组件化，仅令牌化 | C |
| **F** | **Deprecate（废弃）** | 死前缀 / 无 DOM 对应 | ~10 | 标记 `@deprecated`，**Phase G 才删除** | G |
| **G** | **Freeze（冻结）** | Golden State 冻结资产 | ~9 | **禁止任何改动** | — |

> 数量为**分类估算区间**，精确归属在 Phase C 启动时逐条落表。**本文档不承诺精确到个位的分类结果**，这是诚实标注，不是遗漏。

### 12.3 按领域的分类落点

| 领域 | 前缀 | 选择器数 | 主类别 | 备注 |
|---|---|---:|---|---|
| Hotspot | `hs` / `hotspot` | **210** | A + C + D | **最大领域**；`hs`(274) 与 `hotspot`(86) **双前缀并存**，属 D 类合并重点 |
| Weather | `wx` | **139** | A + E | 图形层归 E3 例外 |
| Scene | `sc` | **73** | A + C | — |
| Map | `map` | **36** | A + E | 地图图形层归 E3 |
| Mic | `mic` | **36** | A + B | 录音状态指示可上提为 B |
| Review | `review` | **31** | A + C | — |
| Doc | `doc` | **26** | A + C | — |
| Tools | — | **8** | A + B | 工具条可上提 |
| **合计** | | **559** ✅ | | 验算：210+139+73+36+36+31+26+8 = 559 |

### 12.4 迁移硬规则

| # | 规则 |
|---:|---|
| **M1** | **禁止在迁移中改变视觉表现**。A 类令牌化必须是**像素级等价**；若令牌值与硬编码值不等（如 `10px` → `--sp-4`(8px)），必须**单独标注并人眼复核** |
| **M2** | **禁止在迁移中删除任何 DOM 或功能** |
| **M3** | **一次只迁移一个领域**，迁完立即回归该领域 + 9 主题 |
| **M4** | 迁移后该领域**新硬编码值 = 0**（可用扫描脚本验证） |
| **M5** | B 类上提必须先在 `ui2.css` 建立原语并通过 §5 契约（10 态），才能替换领域侧 |
| **M6** | F 类**只标记不删除**。删除统一在 Phase G，且需 DOM 探针证明零引用 |

---

## 13. Namespace 策略（191 / 197 前缀）

### 13.1 口径声明（诚实标注）

| 来源 | 数值 |
|---|---:|
| `UI_ELEMENT_INVENTORY.md` §8 记载 | **197** |
| Section 3 原始扫描实测 | **191** |
| 差值 | **6** |

**差异原因**：两次扫描的前缀切分规则不同（是否把 `companion.css` 内部前缀、是否把状态类如 `active` / `show` 计为前缀）。
**处置**：**两个口径并存记录，不做单方面覆盖**。精确对账列入 Phase B 的一次性任务。此差异**不影响**任何设计决策，因为策略是按"前缀频次分层"制定的，与总数无关。

### 13.2 四级前缀策略

| 级别 | 判定 | 前缀数 | 策略 | 示例 |
|---|---|---:|---|---|
| **N1 · 官方保留（Reserved）** | 系统级 / 原语级前缀 | 5 | **保留并强制使用**，新代码只能用这几个 | `zz-`(149) 原语 · `cp-`(42) Command Palette · `os-`(262) Shell · `ic-`(24) 图标 · `sw-` 主题选择器 |
| **N2 · 领域正式（Domain）** | 高频领域前缀（≥20 次） | ~20 | **保留**，每领域**只允许一个前缀** | `hs`(274) · `wx`(145) · `mem`(139) · `settings`(91) · `avatar`(82) · `sc`(50) · `ts`(48) · `onb`(47) · `orb`(42) · `cap`(41) · `rv`(41) · `memq`(36) · `map`(32) · `doc`(28) · `hud`(27) · `briefing`(26) · `conv`(25) · `mic`(23) · `gx`(23) · `proactive`(22) |
| **N3 · 待合并（Merge）** | 同领域双前缀 / 语义重叠 | ~10 | **合并到 N2 正式前缀** | `hotspot`(86) → `hs` · `memory`(15) → `mem` · `em`(22) → `execution` 待定 |
| **N4 · 冻结/废弃（Frozen / Deprecated）** | 死前缀、一次性前缀、状态误判 | ~150 | 死前缀标 `@deprecated`；长尾**冻结**（不新增、不强制改） | `tele`(48) **死前缀**（`#tele` 已 hidden）· 一次性前缀 **57 个** · ≤3 次前缀 **94 个** |

### 13.3 命名硬规则（新代码强制）

| # | 规则 |
|---:|---|
| **NS1** | **禁止新增前缀**。新样式必须落入 N1（原语）或已有 N2（领域）前缀 |
| **NS2** | **一个领域一个前缀**。发现双前缀立即归入 N3 合并清单 |
| **NS3** | **状态用属性不用类前缀**。优先 `[data-state="active"]` / `[aria-expanded]`，避免 `active`(24) / `show`(16) 这类无前缀全局状态类 |
| **NS4** | **原语层禁用领域前缀**（与 §3.3 L2 洁净规则一致） |
| **NS5** | N4 长尾**冻结而非清理**。历史长尾一次性清理风险高于收益，**只禁止增量**，存量随领域迁移自然消化 |

### 13.4 死前缀专项：`tele`

- 实测 **48 个 `tele-*` 选择器**；`#tele` 元素已 `visibility:hidden`（`_hidden_probe.json`）。
- **裁决**：标记 `@deprecated`，**Phase G 删除前必须**：① DOM 探针证明零渲染引用；② JS 全文搜索证明零动态引用。
- **本阶段不删除**（红线：不删除现有 UI）。

---

## 14. Migration Roadmap（Phase A – G）

> **本文档不执行任何 Phase。** 以下为经排序的实施路线，每个 Phase 需独立立项、独立走 Audit→Implement→Verify→Document→STOP。

### 14.1 路线总览

| Phase | 名称 | 目标 | 依赖 | 风险 | 代码改动量 |
|---|---|---|---|---|---|
| **A** | **Token Authority Consolidation** | 落实 D-01 + D-02 | 无 | 🔴 高（触碰主题） | 中 |
| **B** | **Primitive Consolidation** | 落实 D-03，整理 29 组重复选择器 | A | 🟡 中 | 小 |
| **C** | **Tokenization Sweep** | 504 字号 + 全量间距 + 残余 z-index 令牌化 | A, B | 🟡 中 | **大** |
| **D** | **Interaction State Completion** | 补齐 Focus/Disabled/Loading/Error + 修 29 焦点陷阱 | A | 🟢 低 | 中 |
| **E** | **Primitive Promotion** | B 类上提 + D 类合并 + 补 Tooltip/Skeleton/Loader | B, D | 🟡 中 | 中 |
| **F** | **Light Theme & Polish** | light 主题专项 + 9 处黑阴影 + z-index 并列 | A–E | 🟡 中 | 小 |
| **G** | **Deprecation Cleanup** | 删除 F 类死代码 + `tele-*` + 死令牌 | A–F | 🔴 高（删除） | 中 |

### 14.2 各 Phase 详细定义

#### Phase A · Token Authority Consolidation 🔴
**目标**：消除权威分叉，这是所有后续工作的前提。
1. `--glow` 在 `styles.css` 6 个主题块中由"阴影简写"降解为 color（D-01）
2. `styles.css` 12 处 `box-shadow: var(--glow)` 改写为 `0 0 24px var(--glow)` 形态（**逐点确认，禁止统一替换**）
3. 删除 `styles.css` 16 个同值冗余主题令牌
4. 10 个真值不同令牌取 ui2 值（light 五项需人眼复核）
5. 主题块三级纯净化：Primitive（`--cyan`/`--teal`/`--amber`/`--red`）上移 `:root`
6. 统一 `--dur-focus`（取 ui2 `700ms`）；`companion.css` 的 `--presence-color` 改为引用
7. **验收**：9 主题 × 4 方一致性回归 + `.os-nav-brand.active` 阴影非 none + `:focus-visible` 焦点环 9 主题可见

#### Phase B · Primitive Consolidation 🟡
1. 29 组重复选择器逐组判定归属（结构+状态→ui2，装饰→premium）
2. `premium.css` 三条约束落地（0 令牌 / 不定义新原语 / 不覆盖结构属性）
3. 191 vs 197 前缀口径精确对账
4. **验收**：跨文件重复选择器 ≤ 5 组；premium.css token_count = 0

#### Phase C · Tokenization Sweep 🟡（工作量最大）
1. 字号：504 处硬编码 → 8 档语义令牌；删除超编 `--fs-*`
2. 间距：全量 gap/padding/margin → 8 档 `--sp-*`；删除 `--space-*` 族
3. 字重/行高/字距：补齐三族令牌，归并 112 字重 + 90 字距硬编码
4. 字体族：补 `--font-mono`，归并 17 处硬编码
5. z-index：29 档 → 9 语义档，归并残余 ~10 处裸值
6. `runtime-viz.css` 接入动效令牌（唯一 0 使用文件）
7. 559 领域选择器 A 类令牌化（**按领域逐个进行，一次一个**）
8. **验收**：每领域迁移后硬编码 = 0；像素级视觉等价（截图 diff）

#### Phase D · Interaction State Completion 🟢
1. 修复 **29 个焦点陷阱**（17 个在 `#settingsPanel`）：隐藏面板加 `visibility:hidden` 或 `inert`
2. 22 组件补齐 `:focus-visible`（当前仅 12 处）
3. 补 Disabled（+`aria-disabled`）、Loading、Error 三态
4. 补 `[aria-*]`（当前仅 2 处）
5. `prefers-reduced-motion` 全覆盖
6. **验收**：Tab 键遍历 182 个可聚焦元素，陷阱 = 0；焦点环 9 主题可见；axe 无 critical

#### Phase E · Primitive Promotion 🟡
1. B 类 ~40 选择器上提为 L2 原语（先建原语过契约，再替换）
2. D 类 ~50 同族合并；`hotspot` → `hs` 前缀合并
3. 补齐零实现组件：**Tooltip / Skeleton / Loader**
4. **验收**：新原语 10 态齐备；领域选择器净减少

#### Phase F · Light Theme & Polish 🟡
1. `light` 主题专项验收（玻璃减半、阴影减弱、`--line` 调优）
2. T5 对比度全量检查（4.5:1 / 3:1）
3. P6 遗留 9 处黑阴影令牌化
4. `--z-companion` / `--z-onboarding` 并列 9999 明确先后
5. **验收**：9 主题 × 22 组件 × 10 态视觉巡检

#### Phase G · Deprecation Cleanup 🔴
1. 删除 F 类死代码 ~10 选择器
2. 删除 `tele-*` 48 选择器（需双重零引用证明）
3. 删除确认无用的死令牌（`--space-*` / 超编 `--fs-*` / 超编 `--op-*`）
4. **验收**：全量回归 + DOM 探针 + 视觉 diff 零差异

### 14.3 排序理由

```
A 必须最先 ── 权威不定，任何修复都会被覆盖
    ↓
B 紧随 ────── 原语归属不定，C 无法确定"改哪个文件"
    ↓
C 与 D 可并行 ─ C 改值不改结构，D 改状态不改值，冲突面小
    ↓
E 依赖 B+D ── 上提原语必须先有契约（D 提供状态矩阵）
    ↓
F 依赖 A–E ── 打磨必须在体系稳定后
    ↓
G 最后 ────── 删除风险最高，必须全部稳定后执行
```

### 14.4 每个 Phase 的通用准入/准出条件

| 类型 | 条件 |
|---|---|
| **准入** | ① 前置 Phase 已 STOP 并通过 Review ② 独立立项 ③ 明确回归口径 |
| **准出** | ① 视觉零回退（截图 diff）② 9 主题回归通过 ③ P8 Presence 20/0 通过 ④ JS 语法全绿 ⑤ 文档落盘 ⑥ 🛑 STOP 不自动进下一 Phase |

---

## 15. Verify — 12 项验收

> 验收对象是**本文档自身**（设计语言是否成立），不是代码。

| # | 验收项 | 要求 | 结果 | 证据位置 |
|---:|---|---|:-:|---|
| 1 | **三大决策已裁决** | D-01 / D-02 / D-03 各有明确裁决 + 影响面 + 实施归属 | ✅ | §2 |
| 2 | **裁决基于真实证据** | 每条裁决引用实测数据，无凭记忆推断 | ✅ | §1 + §2 证据段 |
| 3 | **L0–L7 层级完整** | 8 层各有定义、归属文件、可做/禁止清单 | ✅ | §3.2（8/8） |
| 4 | **依赖方向有规则** | 单向依赖 + 领域洁净 + 例外豁免边界 | ✅ | §3.3 |
| 5 | **Token ≥16 类且三级区分** | 实际 **18 类**，Primitive/Semantic/Component 三级明确 | ✅ | §4.2（18 ≥ 16） |
| 6 | **死令牌有处置裁决** | 80 个死令牌逐族给出保留/删除/接线 | ✅ | §4.3 |
| 7 | **组件契约 ≥20 且 10 态** | 实际 **22 组件** × 10 态矩阵 | ✅ | §5.2（22 ≥ 20） |
| 8 | **Surface / Panel 层级成立** | 6 级承载面 + 玻璃配额 + 注意力预算 | ✅ | §6（S0–S5） |
| 9 | **Typography ≥8 档** | 实际 **8 档语义** + 字重/行高/字距/字体族 | ✅ | §7（8 = 8） |
| 10 | **9 主题契约完整** | 9 主题 × 29 令牌 = 261 条 + T1–T7 七条契约 | ✅ | §9 |
| 11 | **AI OS 视觉语言明确反 Dashboard** | 显式禁止"玻璃+青色+发光=AI OS" + 四原则 + 配额 | ✅ | §10 |
| 12 | **559 / Namespace / Migration 全覆盖** | 559 分 A–G 七类 + 前缀四级策略 + Phase A–G 路线 | ✅ | §12 / §13 / §14 |

### 15.1 附加合规检查（红线）

| 检查 | 结果 |
|---|:-:|
| 未修改任何 `.css` 文件 | ✅ 0 处 |
| 未修改任何 `.html` / `.js` 文件 | ✅ 0 处 |
| 未触碰 Runtime / Agent / EventBus / AppState | ✅ |
| 未触碰 Galaxy / AI Presence（P8 三唯一） | ✅ 仅做保护性约束 |
| 未触碰 Provider / Backend / API | ✅ |
| 未删除任何现有 UI | ✅ |
| 未建立第二套 Token / Design System | ✅ 明确采用"激活而非重建"范式（§2 D-03） |
| 未新增事件契约 | ✅ |
| 未提交 Git | ✅ |
| 未进入 Section 4 | ✅ |
| 本次仅新增 1 个文件 | ✅ `docs/ui-system/UI_SYSTEM_v1.0.md` |

### 15.2 机器复核记录（Machine Verification Log）

> **纪律**：§15 表格中的 ✅ 不采信文档自述，全部经**独立机器实测**复核。以下为复核命令与实测输出，任何人可原样重跑验证。
> 复核时间：2026-08-09 11:0x　复核对象：`docs/ui-system/UI_SYSTEM_v1.0.md`（1270 行 / 79,795 字节）

| # | 复核方式 | 实测结果 | 判定 |
|---:|---|---|:-:|
| 1 | `grep -nE "^### .*D-0[123]"` | 命中 3 处：L227 `D-01`、L263 `D-02`、L302 `D-03` | ✅ |
| 2 | 人工核对 §2 每条裁决的「证据」段 | 三条裁决均引用 §1 实测数据（28 处 `--glow` 使用、26 主题冲突、160 令牌/80 死令牌），无凭记忆推断 | ✅ |
| 3 | `grep -E "^\| \*\*L[0-7]"` 于 §3.2 | 命中 **8 行**（L0…L7），每行含「归属文件 / 可做 / 禁止 / 健康度」四列 | ✅ 8/8 |
| 4 | 读取 §3.3 | 5 条依赖规则（单向依赖 / L0 无依赖 / L2 领域洁净 / L6 只消费不定义 / L7 豁免） | ✅ |
| 5 | §4 编号表行计数 | **18 行** ≥ 16，且 §4.2 明确 Primitive / Semantic / Component 三级 | ✅ 18≥16 |
| 6 | 读取 §4.3 | **11 族**死令牌逐族裁决（保留 / 删除 / 接线），覆盖 80 个 | ✅ |
| 7 | §5 编号表行计数 | **22 行** ≥ 20，配 10 态矩阵 | ✅ 22≥20 |
| 8 | `grep -E "^\| \*\*S[0-5]"` 于 §6 | 命中 **6 行**（S0 Void → S5 Modal），各带玻璃配额与令牌归属 | ✅ |
| 9 | 读取 §7.2 | **8 行**语义档（`--fs-micro` → `--fs-display`），另含字重 4 / 行高 3 / 字距 4 / 字体族 3 | ✅ 8=8 |
| 10 | 读取 §9.1 + §9.2 | 主题表 **9 行**（`dark` … `light`，默认 `dark-cyan`）× 29 令牌 = 261 条，T1–T7 契约齐备 | ✅ |
| 11 | `grep "Dashboard"` | 命中 L624 / L626 / L654 / L900 / L907，含显式禁令「到处玻璃 + 青色 + 发光 = AI OS」 | ✅ |
| 12 | §12 / §13 / §14 分别 grep | §12 命中 **A–G 七类**（含各类数量与迁移目标 Phase）；§13 前缀四级策略；§14 命中 **Phase A–G 七行**（含依赖 / 风险 / 改动量） | ✅ |

**红线复核（文件系统实测，非声明）**：

| 检查 | 命令 | 实测输出 | 判定 |
|---|---|---|:-:|
| 6 个 CSS 未被改动 | `ls --time-style=full-iso` | styles `02:35:15`、ui2 `03:11:43`、premium `02:34:58`、runtime-viz `02:30:21`、execution-channel `02:27:30`、companion `02:27:30` —— **全部远早于本轮工作时段（10:50+）** | ✅ |
| 无任何代码文件变更 | `find xiao6-ui -name '*.css|*.js|*.html|*.py' -newermt "2026-08-09 10:00"` | **空集** | ✅ |
| 本轮唯一新增文件 | `find docs/ui-system -newermt "2026-08-09 10:00" -type f` | 仅 `UI_SYSTEM_v1.0.md` 一项 | ✅ |
| 01–09 分册未创建 | 逐文件 `-f` 判定 | 九份**全部 ABSENT**（符合指令「不写分册」） | ✅ |
| 文档无残留占位符 | 全文扫描构建期临时分节标记 | **0 处残留**（分节写入所用的临时标记已全部被正文替换） | ✅ |

> **复核结论**：12 项验收 + 5 项红线**全部实测通过**，文档自述与磁盘真实状态**完全一致**，无夸大、无未落盘内容。

---

## 16. READINESS 判定

### 16.1 分项 READINESS

| 维度 | 判定 | 说明 |
|---|:-:|---|
| 设计语言完整性 | 🟢 | 12/12 验收项通过，覆盖令牌→层级→组件→主题→视觉语言→迁移全链路 |
| 证据可靠性 | 🟢 | 全部基于真实读盘/浏览器探针，0 推断；三处口径差异**已如实双列标注** |
| 三大决策可执行性 | 🟢 | 三条裁决均有明确影响面与 Phase 归属，且给出强制实施顺序（D-02→D-01→D-03） |
| 与 Golden State 兼容性 | 🟢 | 无第二 Token/Design System、无事件扩张、Presence 冻结资产仅保护不改造 |
| 组件契约落地基础 | 🟡 | 22 组件契约成立，但 **Focus/Loading/Error 三态现状近乎空白**，Phase D 工作量真实存在 |
| 559 领域分类精度 | 🟡 | 七类框架成立，但**各类数量为估算区间**，精确归属需 Phase C 逐条落表（已在 §12.2 诚实标注） |
| Namespace 口径 | 🟡 | **191 vs 197 差 6** 未对账，已双列标注，不阻断决策，列入 Phase B |
| 代码现状健康度 | 🔴 | 字号 504 处硬编码、间距 100% 硬编码、29 焦点陷阱、`--glow` 破坏默认主题焦点环 —— **这是现状评级，不是本文档缺陷** |

### 16.2 综合判定

> # 🟢 READY — 设计语言 v1.0 成立，可作为后续所有 UI 工作的唯一权威

**判定理由**：
1. 12 项验收全部通过，无 🔴 阻断项；
2. 三个 🟡 均为**已知且已标注**的精度问题（559 分类粒度、191/197 对账、Phase D 工作量），**不影响设计语言本身的自洽性**；
3. 唯一 🔴 是**代码现状**评级，正是本文档要治理的对象，其存在恰恰证明本文档的必要性。

### 16.3 DECISION REQUIRED（需老板拍板事项）

以下 4 项超出设计范畴，涉及**取舍偏好**，需明确决策后方可进入 Phase A：

| # | 事项 | 选项 | 建议 |
|---:|---|---|---|
| **DR-1** | **Phase A 是否立即启动？** | ① 立即启动（先修 P0 可访问性缺陷）<br>② 暂缓，先做 Phase D 焦点陷阱（不触碰主题，风险更低） | 建议 **①**：`--glow` 导致**默认主题下焦点环失效**属 P0，且 Phase D 的焦点环补齐依赖 Phase A 先修好 `--glow` |
| **DR-2** | **`10px` / `14px` 间距归并是否接受 1–2px 视觉变化？** | ① 接受归并（74 处→`--sp-4`/`--sp-5`）<br>② 保留这两档，间距扩为 10 档 | 建议 **①**：8 档是可维护上限；1–2px 差异在人眼阈值内，但**必须逐点截图复核** |
| **DR-3** | **`tele-*`（48 选择器）与 `--space-*` 等死代码是否授权 Phase G 删除？** | ① 授权删除（需双重零引用证明）<br>② 永久冻结，只标记不删 | 建议 **①**，但严格前置证明；若老板倾向零风险则选 ② |
| **DR-4** | **Light 主题的战略定位？** | ① 一等公民（每 Phase 同等验收）<br>② 二等（Phase F 集中处理）<br>③ 降级为实验性 | 建议 **②**：现状 light 主题多项令牌与 ui2 分叉，集中处理成本最低 |

> 🟡 上述 4 项**未决不阻断本文档成立**，但**阻断 Phase A 启动**。

---

## 17. 🛑 STOP

### 17.1 本轮完成

- ✅ Section 3 · Audit（上一轮完成，本轮未重跑）
- ✅ Section 3 · Decide（D-01 / D-02 / D-03 裁决完成）
- ✅ Section 3 · Design（L0–L7 / 18 类 Token / 22 组件 / S0–S5 / 8 档字号 / 尺度 / 9 主题 / 视觉语言 / 例外 / 559 / Namespace / Phase A–G）
- ✅ Section 3 · Document（**本文档落盘**）
- ✅ Section 3 · Verify（12 项 + READINESS 🟢 + 4 项 DECISION REQUIRED）

### 17.2 本轮明确未做

- ❌ 未写 `01_DESIGN_PRINCIPLES.md` ~ `09_MIGRATION_ROADMAP.md` 九份分册（**按指令跳过**，其内容已完整并入本主文档）
- ❌ 未执行任何 Phase A–G
- ❌ 未修改任何代码
- ❌ 未进入 Section 4
- ❌ 未提交 Git

### 17.3 下一步（等待指令，不自动执行）

1. **回答 §16.3 的 4 项 DECISION REQUIRED**；
2. 或指示补写 01–09 分册；
3. 或授权立项 **Phase A · Token Authority Consolidation**。

> 🛑 **STOP。等待 Review。**

---

*本文档为 Formal UI System v1.0 唯一权威。任何与之冲突的历史文档，以本文档为准；任何与 Golden State v1.0 冲突之处，以 Golden State 为准。*

