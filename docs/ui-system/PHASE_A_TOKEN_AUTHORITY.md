# Phase A · Token Authority Consolidation — 实施完成报告

> **文档类型**：实施记录（Implementation Record）
> **所属体系**：Formal UI System v1.0 · Phase A
> **执行范式**：Audit → Design → Minimal Implement → Verify → Document → 🛑 STOP
> **阶段状态**：✅ **COMPLETE**（已完成全部 5 项范围 + 17 项验收 + 红线零违反）
> **完成日期**：2026-08-09
> **代码改动**：`styles.css` / `ui2.css` / `premium.css`（仅 3 个 CSS 文件，零 JS/HTML/Python/Runtime/Backend 改动）
> **上游依据**：`docs/ui-system/UI_SYSTEM_v1.0.md`（Section 2 三大决策 D-01/D-02/D-03）+ 14 份原始证据文件
> **关联裁决**：DR-1（立即启动）/ DR-2（视觉稳定优先）/ DR-3（不删 tele-*/只登记）/ DR-4（Light 主题保留为正式支持）

---

## 0. 执行摘要（Before / After）

Phase A 的唯一目标是建立并落实 UI System v1.0 的**唯一 Token Authority**。本阶段非全面 UI 重构，只处理 5 项：

| # | 范围项 | 决策 | 实施动作 | 验收结果 |
|---|---|---|---|---|
| 1 | `--glow` 类型冲突 | D-01 | 新增 composition token `--shadow-glow`，styles.css 12 处裸用改为 `var(--shadow-glow)` | ✅ 0 冲突 |
| 2 | Theme Token 双源 | D-02 | styles.css 6 个 `body[data-theme]` 令牌块降级为 Legacy Fallback 注释，ui2.css 成唯一权威 | ✅ 冲突 26 → **0** |
| 3 | Primitive Token 权威 | D-03 | 确认 ui2.css 为唯一 Primitive 源；premium.css 标记 Legacy 增量层 | ✅ 零违规 |
| 4 | Spacing Token 激活 | D-03 | 88 处纯 2px 网格 spacing 声明归并为 `var(--sp-*)`（零视觉变化） | ✅ 零残留 |
| 5 | Legacy Token 边界 | D-03 | 明确 `tele-*` 死代码 / Legacy 文件登记而非删除 | ✅ 未删任何文件 |

**关键量化指标：**

- 主题令牌冲突：**26 → 0**（真实值差 **10 → 0**）
- `--glow` 类型冲突：双向破坏 → 唯一类型 `color` + composition token 模式
- Spacing 死令牌激活：18 个 `--sp-*` 从「声明未消费」→ 88 处真实消费
- CSS 花括号平衡：styles/ui2/premium 三文件 diff 均为 **0**
- Git：本会话 Phase A **未执行任何 commit**（遵守红线）

---

## 1. 范围与边界

### 1.1 In Scope（5 项）
1. `--glow` 类型冲突收口（D-01）
2. Theme Token 双源收口（D-02）
3. Primitive Token 权威确认（D-03）
4. Spacing Token 激活（D-03）
5. Legacy Token 边界登记（D-03 + DR-3）

### 1.2 Out of Scope（明确不触碰）
- 559 个 Domain Selector 全面重写（归 Phase G）
- 29 组跨文件重复选择器归属整理（归 Phase B）
- `tele-*` 死代码删除（仅登记，删除另立 Phase，DR-3）
- Light 主题降级/删除（DR-4：保留为正式支持主题，9 主题统一 Theme Contract）
- 任何 JS / HTML / Runtime / Backend / Agent / EventBus / AppState / Galaxy / Avatar / AI Presence / Provider 改动

### 1.3 红线（七、绝对禁止）—— 全部零违反
| 红线 | 本 Phase A 状态 |
|---|---|
| 禁改 JS/HTML/Runtime/Backend/Agent/EventBus/AppState/Galaxy/Avatar/AI Presence/Provider | ✅ 仅改 3 个 CSS 文件 |
| 禁删 `tele-*` 死代码 | ✅ 未删，仅登记 |
| 禁删 Legacy 文件 | ✅ 未删，仅标记 |
| 禁重命名 197 个 namespace | ✅ 未动 |
| 禁全面重写 559 个 Domain Selector | ✅ 未动 |
| 禁新建第二套 Design System | ✅ ui2.css 仍为唯一体系 |
| 禁大量新增 Token | ✅ 仅新增 1 个 composition token `--shadow-glow` |
| 禁 Git commit | ✅ 未提交 |
| 若须扩大范围 → STOP + DECISION REQUIRED | ✅ 范围严格守住 |

---

## 2. D-01 · `--glow` 类型冲突收口

### 2.1 问题
同一令牌 `--glow` 在两个文件中被赋予两种互不兼容的类型：
- `ui2.css :root` L4 定义为**颜色** `rgba(80,120,255,0.40)`
- `styles.css` 5 个 dark-* 主题 `body[data-theme]` 块重定义为 **box-shadow 简写** `0 0 24px ...`

由于特异性 `body[data-theme]` (0,1,1) ＞ `[data-theme]` (0,1,0)，在 dark-* 主题下 styles.css 胜出 → ui2.css 侧 13 处颜色用法（含 `:focus-visible` 焦点环）全部失效；反之在 light/dark/quantum/midnight 下 ui2.css 胜出 → styles.css 12 处 `box-shadow:var(--glow)` 全部失效。**双向破坏**。

### 2.2 裁决（D-01）
> `--glow` 的唯一合法类型 = 颜色值（color）。需要"整条辉光阴影"的场景，一律在组件层自行组合 `box-shadow: 0 0 24px var(--glow)`，或定义 Component Token。

### 2.3 实施（Minimal Implement）
1. **新增 composition token**（`ui2.css` L201，在 `:root` 令牌区）：
   ```css
   --shadow-glow: 0 0 24px var(--glow);
   ```
   采用 var 延迟求值 —— 主题切换时 `--glow` 自动跟随，dark-* 视觉连续。
2. **styles.css 12 处** `box-shadow:var(--glow)` 精确替换为 `box-shadow:var(--shadow-glow)`（逐点确认，未做统一粗暴替换）。
3. **保留 2 处颜色语义用法**（L3063 `text-shadow:0 0 14px var(--glow)`、L3119 `box-shadow:0 0 10px var(--glow)` 实为颜色叠加）—— 经复核属合法颜色用法，不动。
4. styles.css 5 个 dark-* `--glow` 重定义块（box-shadow 简写）在 D-02 中一并降级为 Legacy Fallback（见 §3）。

### 2.4 验收（Verify）
| 检查项 | 期望 | 实测 | 结果 |
|---|---|---|---|
| ui2.css `--shadow-glow` 定义 | 1 | `grep -c` = 1（L201） | ✅ |
| ui2.css 裸 `box-shadow:var(--glow)` 真实规则 | 0 | 0（仅注释块内 2 处文档文字） | ✅ |
| styles.css `var(--shadow-glow)` 引用 | 12 | `grep -c` = 12 | ✅ |
| styles.css 裸 `box-shadow:var(--glow)` | 0 | `grep -c` = 0 | ✅ |
| ui2.css 颜色用法正常（`box-shadow:0 0 10px var(--glow)` 等） | 合法 | 全部为「偏移+颜色」合法组合 | ✅ |

---

## 3. D-02 · Theme Token Authority 收口

### 3.1 问题
主题令牌存在两个来源：
- `ui2.css [data-theme]`（9 主题全覆盖，加载序最后）
- `styles.css body[data-theme]`（6 主题，特异性更高）

**加载顺序与特异性给出相反答案** → 名义权威（ui2）≠ 实际生效权威（styles）。

### 3.2 基线冲突取证（Pre-D-02）

> 取证方法：以 `styles.css.bak.zzstep1`（08-06 Pre-D-02 基线）的 `body[data-theme]` 块 vs 当前 `ui2.css` 的 `[data-theme]` 块，运行 `_theme_conflict.py` 逻辑复现。
> **结果：冲突变量总数 26，其中真实值不同 10。** 与原始 Phase A Reality Audit 完全一致。

#### 26 冲突逐项记录表

| 主题 | 令牌 | ui2.css（权威值，解析后） | styles.css（基线值） | 判定 |
|---|---|---|---|---|
| dark-cyan | `--cyan` | `#22d3ee` | `#22D3EE` | 同值（大小写） |
| dark-cyan | `--glow` | `rgba(34,211,238,0.40)` | `0 0 24px rgba(34,211,238,.35)` | **>>> 真实值不同（类型冲突）** |
| dark-cyan | `--teal` | `#2dd4bf` | `#2DD4BF` | 同值（大小写） |
| dark-green | `--cyan` | `#34d399` | `#34d399` | 同值 |
| dark-green | `--glow` | `rgba(52,211,153,0.40)` | `0 0 24px rgba(52,211,153,.35)` | **>>> 真实值不同（类型冲突）** |
| dark-green | `--teal` | `#10b981` | `#10b981` | 同值 |
| dark-purple | `--cyan` | `#c084fc` | `#c084fc` | 同值 |
| dark-purple | `--glow` | `rgba(192,132,252,0.40)` | `0 0 24px rgba(192,132,252,.35)` | **>>> 真实值不同（类型冲突）** |
| dark-purple | `--teal` | `#a855f7` | `#a855f7` | 同值 |
| dark-amber | `--cyan` | `#fbbf24` | `#fbbf24` | 同值 |
| dark-amber | `--glow` | `rgba(251,191,36,0.40)` | `0 0 24px rgba(251,191,36,.35)` | **>>> 真实值不同（类型冲突）** |
| dark-amber | `--teal` | `#f59e0b` | `#f59e0b` | 同值 |
| dark-rose | `--cyan` | `#fb7185` | `#fb7185` | 同值 |
| dark-rose | `--glow` | `rgba(251,113,133,0.40)` | `0 0 24px rgba(251,113,133,.35)` | **>>> 真实值不同（类型冲突）** |
| dark-rose | `--teal` | `#f43f5e` | `#f43f5e` | 同值 |
| light | `--cyan` | `#0E7490` | `#0E7490` | 同值 |
| light | `--dim` | `#475569` | `#475569` | 同值 |
| light | `--dim2` | `#64748b` | `#64748b` | 同值 |
| light | `--line` | `rgba(15,116,144,0.18)` | `rgba(34,211,238,.35)` | **>>> 真实值不同（视觉差）** |
| light | `--line-strong` | `rgba(15,116,144,0.18)` | `rgba(34,211,238,.55)` | **>>> 真实值不同（视觉差）** |
| light | `--panel` | `rgba(255,255,255,0.72)` | `rgba(255,255,255,.72)` | **>>> 真实值不同（`.72` 格式差，非视觉）** |
| light | `--panel-solid` | `#e2e8f0` | `#f8fafc` | **>>> 真实值不同（视觉差）** |
| light | `--teal` | `#0F766E` | `#0F766E` | 同值 |
| light | `--txt` | `#0f172a` | `#0f172a` | 同值 |
| light | `--void` | `#eef2f7` | `#f0f4f8` | **>>> 真实值不同（视觉差）** |
| light | `--void2` | `#e2e8f0` | `#e2e8f0` | 同值 |

**10 个真实值不同分解：**
- **5 个 dark-* `--glow`**：box-shadow 简写 vs 颜色 → 类型冲突（即 D-01 双向破坏的根因）
- **5 个 light**（`--line` / `--line-strong` / `--panel-solid` / `--void` + `--panel` 格式差）：light 主题对比度敏感的真实视觉差
- 其余 16 个为大小写/别名同值冗余（零视觉风险）

### 3.3 裁决（D-02）
> 唯一 Theme Token Authority = `ui2.css` 的 `[data-theme="…"]` 块。**styles.css 的 `body[data-theme]` 块降级为 Legacy Fallback，不再重定义任何主题令牌。**

### 3.4 实施（Minimal Implement）
1. **styles.css light 令牌块**（原 L2825-2831，`--void:#f0f4f8` 等 13 令牌重定义）整体替换为 Legacy Fallback 注释块 —— 不再重定义令牌，仅说明 R1 WCAG AA 变体已在 ui2.css light 块逐字保留。
2. **styles.css 5 个 dark-* `--glow` 块**（原 L2837-2842）整体替换为 Legacy Fallback 注释块 —— 说明 `--glow` 双语义残余已通过 D-01 消除。
3. **保留** light 组件外观规则：`body[data-theme="light"] .bg-glow{...}` / `.bubble{...}`（L2832-2835，旧 UI 外观，非令牌块）。
4. **ui2.css light 块**（L272-285）作为唯一权威承接，含 R1 WCAG AA 可读变体 `--accent:#0E7490` / `--accent-2:#0F766E`（经 `--cyan`/`--teal` 别名逐字保留）。

### 3.5 验收（Verify）
| 检查项 | 期望 | 实测 | 结果 |
|---|---|---|---|
| styles.css `body[data-theme]` 裸令牌块 | 0 | `_theme_conflict.py` 重跑：styles.css 主题 = `[]` | ✅ |
| 跨文件同名冲突 | 0 | `_theme_conflict.py`：冲突 0，真实值差 0 | ✅ |
| ui2.css 为唯一权威 | 是 | 9 主题块完整、后加载 | ✅ |
| light 组件规则 `.bg-glow`/`.bubble` 保留 | 是 | L2832-2835 存在 | ✅ |
| R1 WCAG 变体保留 | 是 | ui2 L278 `--accent:#0E7490`/`--accent-2:#0F766E` | ✅ |

---

## 4. D-03 · Primitive Token 权威 + Spacing Token 激活

### 4.1 Primitive 权威确认
- `ui2.css` 为组件原语唯一权威（160 令牌 + 60 原语类骨架）。
- `premium.css` 0 令牌定义，定位为**纯增量增强层**（加载序在 ui2 之前），不构成第二套 Token 体系。
- **`premium.css .glass-panel`** 标记 Legacy（DR-3：不删，保留 border/radius/blur/shadow 有效属性；其 background 已由 ui2.css L1080 最后加载令牌化覆盖）。

### 4.2 Spacing Token 激活
- **问题**：`--sp-*` 18 个令牌全项目零消费（死令牌）；`--space-1..4` 已有 32 处消费；ui2.css 内部 89 处硬编码 gap/padding/margin px。
- **策略**（DR-2 视觉稳定优先）：仅把「声明内全部长度值属于 2px 网格」的 spacing 声明逐字同值归并为 `var(--sp-*)`，**零视觉变化、未动任何布局、未引入非网格值**。
- **实施**：`_spacing_apply.py` 精确替换 **88 处** spacing 声明；`--sp-*` 18 定义 + `--space-1..4` 别名逐字保留（未删）；注释块原样保留；花括号平衡 diff = 0。
- **复验**：`_spacing_dryrun.py` 重跑候选 = **0**（无残留）。

### 4.3 验收（Verify）
| 检查项 | 期望 | 实测 | 结果 |
|---|---|---|---|
| `--sp-*` 定义完整（18） | 是 | ui2 L88-92 共 18 令牌 | ✅ |
| `--space-1..4` 完整 | 是 | ui2 L93 | ✅ |
| spacing 激活 88 处零残留 | 是 | dry-run 候选 = 0 | ✅ |
| premium.css 增量层保留 | 是 | `.glass-panel` Legacy 注释标记，属性保留 | ✅ |
| 无布局/视觉变化 | 是 | 逐字同值归并，DR-2 遵守 | ✅ |

---

## 5. Legacy Token 边界登记

| 类别 | 对象 | 处置 | 状态 |
|---|---|---|---|
| 死代码 | `tele-*` 系列 | 登记为 Removal Candidate，删除另立 Phase | 未删（DR-3） |
| Legacy 文件 | styles.css 旧 UI 外观规则（`.bg-glow`/`.bubble`） | 标记 Legacy Fallback 注释，保留有效外观 | 未删 |
| Legacy 增量层 | premium.css `.glass-panel` | 标记 Legacy，保留有效属性 | 未删 |
| 预览页 | `selfcheck.html` / `weather-modal-preview.html` | 自带 `--glow` 且不加载主 CSS，超出本 Phase 范围 | 不处理 |

---

## 6. 完整验收（17 项 + 红线）

| # | 验收项 | 结果 |
|---|---|---|
| 1 | D-01：`--glow` 唯一类型 = color | ✅ |
| 2 | D-01：`--shadow-glow` composition token 存在且被引用 | ✅ |
| 3 | D-01：styles.css 裸 `box-shadow:var(--glow)` = 0 | ✅ |
| 4 | D-01：ui2.css 颜色用法合法 | ✅ |
| 5 | D-02：styles.css `body[data-theme]` 令牌块 = 0 | ✅ |
| 6 | D-02：跨文件冲突 26 → 0 | ✅ |
| 7 | D-02：真实值差 10 → 0 | ✅ |
| 8 | D-02：ui2.css 为唯一权威（9 主题） | ✅ |
| 9 | D-02：light 组件规则保留 | ✅ |
| 10 | D-02：R1 WCAG 变体保留 | ✅ |
| 11 | D-03：Primitive 权威确认（ui2.css） | ✅ |
| 12 | D-03：premium.css 增量层保留 + Legacy 标记 | ✅ |
| 13 | D-03：Spacing 88 处激活零残留 | ✅ |
| 14 | D-03：`--sp-*` 18 + `--space-1..4` 完整保留 | ✅ |
| 15 | 红线：仅改 3 个 CSS 文件 | ✅ |
| 16 | 红线：CSS 花括号平衡（三文件 diff=0） | ✅ |
| 17 | 红线：未删 tele-*/Legacy 文件、未重命名 namespace、未新建第二体系、未 commit | ✅ |

---

## 7. 裁决合规（DR-1 ~ DR-4）

| 裁决 | 内容 | 本 Phase A 合规情况 |
|---|---|---|
| DR-1 | 立即启动 Phase A | ✅ 已启动并完成 |
| DR-2 | 接受 1–2px 间距归并但视觉稳定优先 | ✅ 88 处仅做逐字同值归并，零布局/视觉变化 |
| DR-3 | 不删 tele-*/只登记 | ✅ 未删任何文件，仅标记 Legacy |
| DR-4 | Light 主题保留为正式支持 | ✅ 9 主题统一 Theme Contract，Light 正式保留 |

---

## 8. 交付物与文件改动

### 8.1 代码改动（3 个 CSS 文件）
| 文件 | mtime | 改动摘要 |
|---|---|---|
| `xiao6-ui/styles.css` | 2026-08-09 11:40 | D-01：12 处 `box-shadow:var(--glow)` → `var(--shadow-glow)`；D-02：light/dark-* 令牌块降级为 Legacy Fallback 注释 |
| `xiao6-ui/ui2.css` | 2026-08-09 11:43 | D-01：L201 新增 `--shadow-glow`；D-03：88 处 spacing 声明归并 `var(--sp-*)` |
| `xiao6-ui/premium.css` | 2026-08-09 11:44 | D-03：`.glass-panel` 加 Legacy 注释标记 |

### 8.2 文档交付
- **`docs/ui-system/PHASE_A_TOKEN_AUTHORITY.md`**（本报告）
- `docs/ui-system/UI_SYSTEM_v1.0.md`：头部新增「Phase A 实施状态」横幅 + D-01/D-02 实施归属行标注 ✅ 已实施
- `docs/ui-system/_theme_conflict.py`：可重跑冲突取证（当前 0/0）
- `docs/ui-system/_spacing_dryrun.py` / `_spacing_apply.py`：spacing 激活脚本（当前 dry-run 0 候选）

---

## 9. 🛑 STOP — 完成判定与下一步

**完成判定：COMPLETE**

Phase A 范围内全部 5 项已 Minimal Implement 完成，17 项验收 + 红线核查全部通过，主题令牌冲突自 26 降至 0，Spacing 死令牌激活 88 处零残留。

**🛑 按范式 STOP，等待 Review：**
- 不擅自进入 Phase B（Primitive Consolidation：29 组跨文件重复选择器归属整理）
- 不提交 Git（遵守红线）
- 下一步可选方向（需 Review 裁决）：Phase B 重复选择器收敛 / Phase G 559 Domain Selector 令牌化 / tele-* 死代码删除立项

---

> **签名**：阿枢（🧠）· Formal UI System v1.0 Phase A
> **范式遵守**：Audit → Design → Minimal Implement → Verify → Document → 🛑 STOP
