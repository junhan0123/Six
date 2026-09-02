# Xiao6 UI Element Inventory v1.0

> Formal UI System Consolidation v1.0 · Section 2 交付物
> 生成时间：2026-08-09
> 状态：**INVENTORY COMPLETE / 🛑 STOP**（不进入 Section 3，不提交 Git，不修改代码）

---

## 0. 本文档的性质与取证纪律

本文档是**盘点（Inventory）**，不是设计方案，也不是修复报告。它只回答一个问题：

> 小6当前到底有哪些 UI 元素，它们的样式从哪来、令牌从哪来、交互从哪来、有没有重复、在哪些维度上已经分叉。

### 0.1 取证纪律（强制）

- **全部数据来自真实读盘与真实浏览器渲染**，不使用任何历史摘要、不凭记忆。
- 与历史记录冲突时，**以本次磁盘实测为准**。本轮已修正两处历史错误数据（见 §0.3）。
- 本文档撰写期间**零代码改动**。所有 `_*.py` / `_*.mjs` / `_*.json` 均为只读探针与其产物。

### 0.2 证据文件清单（均位于 `docs/ui-system/`）

| 证据文件 | 类型 | 用途 | 产出 |
|---|---|---|---|
| `_css_audit.py` → `_css_audit.json` | 静态解析 | 6 个 CSS 的行数/选择器/keyframes/硬编码/跨文件重复/同文件多定义/跨文件令牌冲突 | §1 §7 §8 |
| `_theme_conflict.py` | 静态解析 | ui2.css `[data-theme]` vs styles.css `body[data-theme]` 变量逐项比对 | §2.2 |
| `_token_probe.mjs` → `_token_probe.json` | **真实浏览器渲染**（CDP） | 9 主题逐个切换，实测 `--glow` 在真实 `box-shadow` 上的最终计算值 | §2.3 D-01 |
| `_dom_audit.py` → `_dom_audit.json` | 静态解析 | index.html 顶层骨架 / id / class / 内联 style；66 个 JS 的 UI 生产强度评分 | §5 §6 |
| `_shell_probe.mjs` → `_shell_probe.json` | **真实浏览器渲染**（CDP） | 双外壳 `#osShell` / `#app` 是否并存、各部件可见性与层级 | §5.2 |
| `_hidden_probe.mjs` → `_hidden_probe.json` | **真实浏览器渲染**（CDP） | 9 类隐藏机制的真实计算样式 + 焦点陷阱枚举 | §5.3 D-14 |
| `_inventory_map.py` → `_inventory_map.json` | 静态解析 | 2126 个选择器按 52 个 UI 分类归属，标记多文件来源 | §3 |
| `_f01_minimal.mjs` | **真实浏览器渲染**（CDP） | F-01 四场景对照实验（已于 Section 1 收口） | §9 F-01 |

渲染类证据的运行环境：Chrome Headless `--remote-debugging-port=9222`（Chrome/151.0.7922.76），后端 `http://127.0.0.1:8000` `/api/health` 存活，四档宽度 1920 / 1440 / 1280 / 1024。

### 0.3 对历史记录的两处更正

| 项 | 历史记录 | **磁盘实测** | 影响 |
|---|---|---|---|
| CSS 选择器总数 | 2247 | **2126** | 所有"总量"分母以 2126 为准 |
| `_inventory_map` 未归类选择器 | 665 | **503** | 归类覆盖率实为 76.3%，非 70.4% |

---

## 1. 样式来源全景

### 1.1 六个 CSS 文件（`index.html` 与 `companion.html` 实际加载）

`index.html` 的 `<link>` 顺序（实测，带版本号）：

```
styles.css?v=20260807p9
premium.css?v=20260805p4
runtime-viz.css?v=20260805r1
execution-channel.css?v=20260805e1
ui2.css?v=20260807p9
```

`companion.html` 独立加载：`companion.css?v=20260805b11`（**不加载上面任何一个**）。

| 文件 | 行数 | 字节 | 规则块 | 选择器 | keyframes | 硬编码 | `:root` 令牌 | 角色定位 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `styles.css` | 3613 | 194,616 | 1413 | **1476** | 40 | **1306** | 0 | 历史主样式（领域 UI 集中地） |
| `premium.css` | 235 | 11,630 | 73 | 80 | 5 | 51 | 0 | Phase 4 精装增强层（纯增量） |
| `runtime-viz.css` | 162 | 4,632 | 32 | 32 | 0 | 68 | 0 | 运行时可视化 |
| `execution-channel.css` | 144 | 4,007 | 23 | 22 | 1 | 48 | 0 | 执行通道 |
| `ui2.css` | 1690 | 94,981 | 370 | 400 | 8 | 156 | **158** | **令牌与组件最终权威** |
| `companion.css` | 624 | 27,762 | 117 | 116 | 19 | 47 | 38 | 伴生窗（独立文档） |
| **合计** | **6468** | **337,628** | **2028** | **2126** | **73** | **1676** | **196** | — |

去重后唯一选择器 **1890**，即存在 **236 次重复定义**（跨文件 29 组 + 同文件 22 组 + 其余为同名不同上下文）。

`styles.css` 一个文件占了 **69.4% 的选择器**和 **77.9% 的硬编码**，是整个分叉问题的重心。

### 1.2 三个游离 HTML（内联样式，完全在令牌体系之外）

| 文件 | 总行 | `<style>` 块 | 内联选择器 | 外链样式 | 是否被引用 |
|---|---:|---:|---:|---|---|
| `mobile-app.html` | 94 | 1 | **28** | 无 | `mobile-app.js` |
| `selfcheck.html` | 283 | 1 | **62** | **Google Fonts（联网 CDN）** | `hotspot.js:780` 真实按钮 |
| `weather-modal-preview.html` | 76 | 1 | **22** | 无 | **零引用（孤儿）** |
| 合计 | — | 3 | **112** | — | — |

这 112 个选择器**不在 §1.1 的 2126 统计内**，且完全不消费任何 CSS 变量 → 属于事实上的"第三套样式"。

---

## 2. Token（令牌）权威与分叉

### 2.1 名义权威

`DESIGN.md §7` 与 `ui2.css` 加载顺序确立：**ui2.css 是令牌与组件的最终权威**。ui2.css 定义 158 个 `:root` 变量 + 9 套主题块（`dark / quantum / midnight / dark-cyan / dark-green / dark-purple / dark-amber / dark-rose / light`，默认 `dark-cyan`）。

### 2.2 实际分叉：主题令牌双源（D-02）

`styles.css` 虽先加载，但它用 **`body[data-theme="..."]`（特异性 0,1,1）**，而 ui2.css 用 **`[data-theme="..."]`（特异性 0,1,0）**。

> **特异性 > 加载顺序** → 凡两边同名的主题变量，**最终生效的是 styles.css，不是名义权威 ui2.css**。

`_theme_conflict.py` 实测：

- ui2.css 覆盖 9 套主题；styles.css 覆盖 6 套（`light / dark-cyan / dark-green / dark-purple / dark-amber / dark-rose`）。
- 同名冲突变量 **26 个**，其中**真实值不同 10 个**：

| 主题 | 冲突变量 | ui2.css 值 | styles.css 值（实际生效） |
|---|---|---|---|
| dark-amber | `--glow` | `rgba(251,191,36,0.40)` | `0 0 24px rgba(251,191,36,.35)` |
| dark-cyan | `--glow` | `rgba(34,211,238,0.40)` | `0 0 24px color-mix(in srgb, var(--accent)…)` |
| dark-green | `--glow` | `rgba(52,211,153,0.40)` | `0 0 24px rgba(52,211,153,.35)` |
| dark-purple | `--glow` | `rgba(192,132,252,0.40)` | `0 0 24px rgba(192,132,252,.35)` |
| dark-rose | `--glow` | `rgba(251,113,133,0.40)` | `0 0 24px rgba(251,113,133,.35)` |
| light | `--line` | `rgba(15,116,144,0.18)` | `color-mix(in srgb, var(--accent) 35%…)` |
| light | `--line-strong` | `rgba(15,116,144,0.18)` | `rgba(34,211,238,.55)` |
| light | `--panel` | `rgba(255,255,255,0.72)` | `rgba(255,255,255,.72)`（写法不同） |
| light | `--panel-solid` | `#e2e8f0` | `#f8fafc` |
| light | `--void` | `#eef2f7` | `#f0f4f8` |

其余 16 个（`--cyan` / `--teal` / `--dim` / `--txt` 等）同值重复 —— 无视觉差，但仍是**重复定义**，属于必须收敛的冗余。

### 2.3 `--glow` 是类型冲突，且造成真实功能缺陷（D-01）

`--glow` 在两处的**语义类型完全不同**：

- ui2.css：`--glow: rgba(34,211,238,0.40)` → **一个颜色**
- styles.css：`--glow: 0 0 24px …` → **一整条 box-shadow 简写**

而 ui2.css 内部有 **14 处**这样使用它：

```css
box-shadow: 0 6px 18px -6px var(--glow);
```

当 styles.css 的值胜出时，展开结果变成 `0 6px 18px -6px 0 0 24px …` —— **非法声明，整条 box-shadow 被浏览器丢弃**。

`_token_probe.mjs` 在真实渲染中逐主题实测 `.os-nav-brand.active`：

| 主题 | `--glow` 实际值类型 | ui2 用法（当颜色） | styles 用法（当阴影） | `.os-nav-brand.active` 最终 box-shadow |
|---|---|---|---|---|
| dark | 颜色 | ✅ 正常 | ❌ 失效 | `2px accent 描边 + 辉光` ✅ |
| quantum | 颜色 | ✅ 正常 | ❌ 失效 | ✅ |
| midnight | 颜色 | ✅ 正常 | ❌ 失效 | ✅ |
| **dark-cyan（默认主题）** | 阴影简写 | ❌ **失效** | ✅ | **`none`** ❌ |
| **dark-green** | 阴影简写 | ❌ **失效** | ✅ | **`none`** ❌ |
| **dark-purple** | 阴影简写 | ❌ **失效** | ✅ | **`none`** ❌ |
| **dark-amber** | 阴影简写 | ❌ **失效** | ✅ | **`none`** ❌ |
| **dark-rose** | 阴影简写 | ❌ **失效** | ✅ | **`none`** ❌ |
| light | 颜色 | ✅ 正常 | ❌ 失效 | ✅ |

**结论：9 个主题中有 5 个（含默认的 dark-cyan）下，导航品牌激活态连 accent 描边一起丢失。** 这不是"视觉差异"，是**功能性缺陷**，且发生在默认主题上。

### 2.4 跨文件令牌值冲突（ui2.css ↔ companion.css）

`_css_audit.json.token_conflicts`：跨文件同名令牌 24 个，**真实值不同 2 个**：

| 令牌 | ui2.css | companion.css | 性质 |
|---|---|---|---|
| `--dur-focus` | `700ms` | `.42s` | **同一产品两窗口的动效节奏漂移**（D-04） |
| `--presence-color` | `var(--presence-idle)` | `#5fb3c8` | companion 未接入 Presence 令牌链，写死颜色（D-05） |

`--presence-color` 是 Phase 8「AI Presence 三唯一」的颜色权威。companion.css 把它写死，意味着**伴生窗不参与 Presence 状态投影**。

---

## 3. UI 分类盘点主表（52 类 / 2126 选择器）

`_inventory_map.py` 把全部 2126 个选择器按语义桶归属：**已归类 1623，未归类 503**（覆盖率 76.3%）。未归类主要是通用元素选择器、`*`、伪类、媒体查询内的裸标签等。

表头说明：

- **样式来源**：该分类的选择器分布在哪些 CSS 文件（数字为选择器数）
- **重复**：`MULTI` = 跨多个 CSS 文件定义，存在分叉风险；`single` = 单一来源
- **交互来源**：真实驱动该分类的 JS 文件
- **需统一**：是否应在 Formal UI System v1.0 中收敛
- **领域语义**：是否应保留其领域特有视觉语言（不强行同化）

### 3.1 系统层（Shell / 导航 / 存在感）

| 分类 | 选择器 | 样式来源 | 重复 | 交互来源 | 需统一 | 领域语义 |
|---|---:|---|---|---|---|---|
| App Shell / 布局 | 121 | styles 63 + premium 5 + ui2 37 + companion 16 | **MULTI** | — | ✅ 必须 | 否 |
| HUD / 顶栏 | 54 | styles 27 + ui2 27 | **MULTI** | `app.js` | ✅ 必须 | 否 |
| Navigation / 导航 | 25 | styles 9 + ui2 16 | **MULTI** | `app.js` / `panel-manager.js` | ✅ 必须 | 否 |
| Galaxy / 星系 | 24 | ui2 24 | single | `galaxy-experience.js` / `galaxy-runtime.js` | ⛔ 禁改语义 | **✅ 保留** |
| Avatar / 化身 | 76 | styles 24 + ui2 11 + companion 41 | **MULTI** | `avatar-renderer.js` / `avatar-state.js` | ⚠️ 谨慎 | **✅ 保留** |
| Presence / 存在感 | 10 | ui2 10 | single | （由 `refreshHud()` 单点写入） | ⛔ 禁动 | **✅ 保留** |
| Companion / 伴生窗 | 13 | companion 13 | single | `companion.js` | ⚠️ 令牌需对齐 | 部分保留 |

> **红线提示**：Galaxy 语义与 Presence 三唯一链路（`avatar-state.js` → `refreshHud()` → `ui2.css body[data-presence]`）在 Golden State 中受保护，盘点只记录、不动。

### 3.2 交互入口层

| 分类 | 选择器 | 样式来源 | 重复 | 交互来源 | 需统一 | 领域语义 |
|---|---:|---|---|---|---|---|
| Command Dock | 20 | styles 1 + ui2 19 | **MULTI** | `command-dock.js` | ✅ 清掉 styles 残留 | 否 |
| Command Palette | 38 | ui2 38 | single | `command-palette.js` | ✅ 已收口，保持 | 否 |
| Settings / 设置 | 82 | styles 58 + premium 17 + ui2 7 | **MULTI（三文件）** | `settings.js` | ✅ **高优先** | 否 |
| Context Drawer / 抽屉 | 43 | styles 38 + ui2 5 | **MULTI** | `panel-manager.js` | ✅ 必须 | 否 |
| Modal / 模态 | 15 | styles 13 + premium 2 | **MULTI** | `overlay-manager.js` | ✅ 必须 | 否 |
| Onboarding / 引导 | 46 | premium 34 + ui2 12 | **MULTI** | `onboarding.js` | ✅ 必须 | 否 |
| Dropdown / 下拉 | 9 | styles 9 | single | — | ✅ 迁入 ui2 | 否 |
| Theme Selector | 30 | styles 17 + premium 4 + ui2 9 | **MULTI（三文件）** | — | ✅ **高优先** | 否 |

Settings 与 Theme Selector 是**唯二横跨三个 CSS 文件**的分类，也是分叉最严重的两处。

### 3.3 信息展示层

| 分类 | 选择器 | 样式来源 | 重复 | 交互来源 | 需统一 | 领域语义 |
|---|---:|---|---|---|---|---|
| Memory / 记忆 | **171** | styles 171 | single | `memory.js` / `memory-panel.js` / `memory-query.js` | ✅ 必须（体量最大） | 否 |
| Status / 状态指示 | 109 | styles 103 + companion 6 | **MULTI** | `sysmon.js` | ✅ 必须 | 否 |
| Chat / 对话 | 65 | styles 59 + companion 6 | **MULTI** | `app.js` | ✅ 必须 | 否 |
| Capability Matrix | 49 | styles 39 + ui2 10 | **MULTI** | `capability-matrix.js` / `capabilities-view.js` | ✅ 必须 | 否 |
| Insight / 洞察 | 44 | styles 26 + ui2 18 | **MULTI** | `insight-panel.js` | ✅ 必须 | 否 |
| Tasks / 任务 | 38 | styles 38 | single | `tasks.js` | ✅ 迁入 ui2 | 否 |
| Notifications / 通知 | 35 | styles 35 | single | — | ✅ 迁入 ui2 | 否 |
| Runtime Viz | 33 | runtime-viz 32 + ui2 1 | **MULTI** | `runtime-visualization.js` | ⚠️ 谨慎 | 部分保留 |
| Agent / 代理 | 26 | styles 26 | single | — | ✅ 迁入 ui2 | 否 |
| Execution / 执行 | 22 | execution-channel 22 | single | `execution-channel.js` / `execution-timeline.js` | ⚠️ 谨慎 | 部分保留 |
| Empty / 空态 | 21 | styles 17 + runtime-viz 1 + exec 1 + ui2 2 | **MULTI（四文件）** | — | ✅ **必须** | 否 |
| Scrollbars / 滚动条 | 17 | styles 13 + exec 2 + ui2 2 | **MULTI** | — | ✅ 必须 | 否 |
| Toast | 2 | styles 2 | single | `app.js` | ✅ 迁入 ui2 | 否 |
| Workspace | 1 | styles 1 | single | — | ✅ 合并 | 否 |
| Profile / 档案 | 1 | styles 1 | single | — | ✅ 合并 | 否 |

`Empty / 空态` 横跨**四个**文件却只有 21 个选择器 —— 单位分叉密度最高，是"同一个空状态被四处各写一遍"的典型。

### 3.4 控件原语层（Formal UI System 的地基）

| 分类 | 选择器 | 样式来源 | 重复 | 需统一 |
|---|---:|---|---|---|
| Icons / 图标 | 15 | styles 2 + ui2 13 | **MULTI** | ✅（`.zz-icon` / `.ic` 已建别名，待清 styles 残留） |
| Buttons / 按钮 | 13 | styles 3 + premium 2 + ui2 8 | **MULTI（三文件）** | ✅ **最高优先** |
| Inputs / 输入 | 12 | styles 5 + ui2 7 | **MULTI** | ✅ 高优先 |
| Chips / 芯片 | 5 | styles 3 + premium 2 | **MULTI** | ✅ 高优先 |
| Cards / 卡片 | 4 | premium 3 + ui2 1 | **MULTI** | ✅ 高优先 |
| Select / 选择器 | 2 | ui2 2 | single | ✅ 已收口 |
| Badges / 徽标 | 1 | styles 1 | single | ✅ 迁入 ui2 |

**关键观察**：真正的原语（按钮/输入/卡片/芯片/徽标）加起来只有 **37 个选择器**，而领域面板有 **559 个**。这说明小6目前**不是"组件驱动"而是"面板驱动"** —— 每个面板各自重写按钮和卡片，原语层从未被真正建立。这正是 Formal UI System v1.0 要解决的根因。

### 3.5 领域层（应保留领域语义）

| 分类 | 选择器 | 样式来源 | 交互来源 | 领域语义 |
|---|---:|---|---|---|
| Hotspot / 热点 | **210** | styles 210 | `hotspot.js` | **✅ 保留**（态势感知视觉语言） |
| Weather / 天气 | **139** | styles 139 | `weather.js` | **✅ 保留** |
| Scene / 场景 | 73 | styles 73 | `scene.js` | **✅ 保留** |
| Map / 地图 | 36 | styles 36 | `map.js` | **✅ 保留** |
| Mic / 语音 | 36 | styles 36 | `kws.js` | **✅ 保留** |
| Review / 复核 | 31 | styles 31 | — | ⚠️ 待定 |
| Doc / 文档 | 26 | styles 26 | `doc.js` | **✅ 保留** |
| Tools / 工具 | 8 | styles 8 | — | ⚠️ 待定 |
| **领域小计** | **559** | 全部 styles.css | — | — |

领域层占 styles.css 的 37.9%，**全部单一来源、无跨文件分叉**。它们的问题不是"重复"，而是"不消费令牌"——这是收敛的方式差异：领域层应**保留造型语言、只替换令牌**，不做结构同化。

### 3.6 零实现分类（有语义桶但无任何样式）

`Goals / 目标`、`Loading / 加载`、`Error / 错误`、`Provider Settings`、`Tabs / 标签页`、`Tooltips / 提示`、`Mobile / 移动` —— 共 **7 类，0 选择器**。

其中值得注意：

- `Error / 错误`：`error-boundary.js` 存在（84 行，7 处直接写 style），但**没有任何 CSS 类** → 错误态完全靠 JS 内联样式，无设计语言。
- `Loading / 加载`：全项目**没有统一加载态**。
- `Tooltips / 提示`：**零实现**，但 UI 中大量图标按钮无文字标签 → 可访问性缺口。
- `Provider Settings`：Phase 10 的 Provider 下拉复用了通用 settings 样式，无独立视觉。
- `Mobile / 移动`：`mobile-app.js` 存在，样式全在 `mobile-app.html` 内联（见 §1.2）。

---

## 4. 重复定义清单（收敛的直接靶子）

### 4.1 跨文件重复选择器（29 组）

| 选择器 | 出现文件 | 性质判定 |
|---|---|---|
| `:root` | ui2.css / companion.css | 两个文档各自的根，**合理** |
| `*` / `html` / `body` | styles.css / ui2.css | 基础重置重复，**需收敛** |
| `.glass-panel` | premium.css / ui2.css | **Panel 原语双源 → 必须收敛** |
| `.onb-card` / `.onb-overlay` | premium.css / ui2.css | 引导卡片双源 → 收敛 |
| `.btn-new` / `.btn-new:hover` | premium.css / ui2.css | **Button 原语双源 → 必须收敛** |
| `.chip` / `.chip:hover` | premium.css / ui2.css | **Chip 原语双源 → 必须收敛** |
| `.ic` / `.ic.f` | styles.css / ui2.css | Icon 原语双源 → 收敛 |
| `.settings-panel` / `.settings-head` / `.settings-head-title` / `.settings-body` / `.settings-nav-item` | styles.css / premium.css | **设置面板整体双源（5 组）** |
| `.settings-switch` 及其 4 个子选择器 | styles.css / premium.css | **开关控件整体双源（5 组）** |
| `.premium-bg` / `.premium-focus:focus-visible` | premium.css / ui2.css | 精装层双源 |
| `body.reduced-motion *` / `body.reduced-motion .premium-bg` | premium.css / ui2.css | 降级动效双源 |
| `#runtime-viz .rv-empty` | runtime-viz.css / ui2.css | 空态双源 |

**判定说明**：`premium.css` 自我定位为「Phase 4 精装层，纯增量、不改动 styles.css」。因此 `.settings-*` 系列的 10 组重复属于**有意的分层增强**，不是无意分叉。但它造成的后果是真实的：**同一个设置面板的最终视觉由两个文件叠加决定，任何一处改动都需要同时读两个文件**。Formal UI System v1.0 需要决策是"合并"还是"明确分层契约"，本盘点不做决策。

### 4.2 同文件多次定义（22 组）

| 文件 | 选择器 | 组数 |
|---|---|---:|
| styles.css | `.hotspot-panel` + `body.hotspot-mode .hotspot-panel.hs-booting` 的 5 个子选择器 | 6 |
| styles.css | `.wx-body` / `.wx-now` / `.wx-foot` / `.wx-hourly` / `.wx-hb` | 5 |
| styles.css | `.zz-panel` | 1 |
| ui2.css | `:root` | 1 |
| ui2.css | `.os-shell` / `.os-core` / `.os-core .os-core-state` | 3 |
| ui2.css | `.os-hero` / `.os-hero-title` / `.os-hero-sub` / `.os-hero-desc` | 4 |
| ui2.css | `.os-side` / `.os-bottom` | 2 |

ui2.css 的 10 组同文件重复**几乎全部来自 Phase 9 / UI Final Visual Review 的后续覆写**（例如 Hero 改水印徽章是在文件后部再写一遍覆盖前面的定义）。这属于**技术债形式的"补丁式覆写"**：可读性差，但当前视觉正确。

### 4.3 keyframes 重名（D-17）

全项目 **73 个 `@keyframes`，唯一名 70 个**。`styles.css` 内部有 3 个动画被**定义了两次**：

| 动画名 | 第一次 | 第二次 | 后果 |
|---|---:|---:|---|
| `wxGlitch` | L1715 | L1855 | 后者胜出，前者是死代码 |
| `wxPulse` | L1818 | L1958 | 同上 |
| `tsBlink` | L2077 | L2110 | 同上 |

---

## 5. DOM 结构盘点

### 5.1 `index.html` 骨架（实测 35 个顶层容器 / 314 个 id / 283 个唯一 class / 18 行内联 style）

```
L64   div.galaxy-veil                    ← 星系遮罩（fixed, z:1）
L67   section#osShell.os-shell           ← 【当前生效外壳】z:5
        L70   nav.os-nav                 ← 左侧导航 76px
        L83   header.os-hud              ← 顶栏 56px
        L108  div#osCore.os-core         ← 中央核心区
        L125  aside.os-side              ← Context 抽屉（离屏）
        L137  div.os-bottom              ← Command Dock 区
L150  div#universeView                   ← 星系全屏视图（display:none）
        L153 .gx-status / L157 .gx-card / L168 .gx-hint / L169 .uv-tip
L246  div#app.app                        ← 【旧外壳】visibility:hidden, z:2
        L248  aside.rail
        L307  main#mainArea.main
        L378  aside#tele.tele
L456  div#toast.toast
L459  div#memPanel.mem-panel             ← display:none
L518  div#settingsOverlay + L519 aside#settingsPanel
L1213 div#sysPromptOverlay + L1214 aside#sysPromptPanel
L1226 div#capOverlay      + L1227 aside#capPanel
L1240 div#zzPanel.zz-panel
L1249 div#onbOverlay + L1250 div.onb-card.glass-panel.neon-edge
```

**观察 1**：`#settingsPanel` / `#sysPromptPanel` / `#capPanel` 三个抽屉**共用 `.settings-head` 类**（L520 / L1215 / L1228）—— 这是项目中**唯一一处已经自发形成的"面板头部原语"**，Formal UI System 可以直接采纳为 Panel Header 的事实标准。

**观察 2**：`.onb-card.glass-panel.neon-edge` 是唯一同时挂三个视觉类的元素，说明 `glass-panel` 已具备原语雏形。

### 5.2 双外壳并存问题（真实渲染实测）

| 外壳 | 存在 | 可见 | display | opacity | z-index | pointer-events | 尺寸 | 子节点 |
|---|---|---|---|---|---:|---|---|---:|
| `#osShell` | ✅ | **✅ 可见** | grid | 1 | 5 | auto | 1920×1080 | 5 |
| `#app` | ✅ | ❌ 隐藏 | grid | 1 | 2 | **none** | 1920×1080 | 4 |
| `#universeView` | ✅ | ❌ | **none** | 1 | 30 | auto | 0×0 | 5 |
| `.galaxy-veil` | ✅ | ✅ | block | 1 | 1 | none | 1920×1080 | 0 |

**结论：双导航 / 双主区 / 双侧栏并存 = 否 ✅**

`#app` 通过 `visibility: hidden` 隐藏，`pointer-events: none`，且其子节点（`.rail` / `.main` / `#tele`）也全部继承 `visibility:hidden` —— **正确排除出 Tab 序列，无焦点污染，无视觉重叠**。

但 `#app` 及其 4 个子树仍然完整存在于 DOM 中（`.rail` 248×1052、`.main` 1316×1052、`#tele` 300×1052 都有真实布局尺寸），意味着：

- 浏览器仍在为这套旧外壳做完整的布局计算（无渲染，但有 layout 成本）
- `styles.css` 中服务于旧外壳的选择器（`.rail` / `.main` / `.tele` 系列）**全部是活代码但不产生任何可见效果**
- 这是一笔明确的**结构债**，但**当前无害**（D-15，低优先）

### 5.3 隐藏机制盘点（9 种，实测计算样式）

| 元素 | 隐藏手段 | pointer-events | 是否污染 Tab 序列 |
|---|---|---|---|
| `#app` / `.rail` / `.main` / `#tele` | `visibility:hidden` | none | ✅ 否（正确） |
| `#memPanel` | `display:none` + `[hidden]` + 零尺寸 | auto | ✅ 否（display:none 已足够） |
| `#zzPanel` | `opacity:0` | none | ⚠️ 是（opacity 不移出 Tab 序列） |
| `#toast` | `opacity:0` | none | ⚠️ 是 |
| `.os-side` | `opacity:0` + `transform` 离屏 | none | ⚠️ 是 |
| `#settingsPanel` | **仅 `transform` 离屏**（translateX 560） | **auto** | ❌ **是（严重）** |

项目中**混用了 4 种互不等价的隐藏机制**，且只有 `visibility:hidden` 与 `display:none` 能正确移出可访问性树。

### 5.4 焦点陷阱（D-14）

实测页面可聚焦元素 **182 个**，其中 **29 个不可见却仍可 Tab 到达**：

| 归属 | 隐藏原因 | 数量 |
|---|---|---:|
| `#settingsPanel` | `transform` 离屏（`pointer-events:auto`） | **17** |
| `body` | `opacity:0` | 7 |
| `#capPanel` | `opacity:0` | 2 |
| `#settingsPanel` | `opacity:0` | 2 |
| `#sysPromptPanel` | `opacity:0` | 1 |
| **合计** | | **29** |

样例（真实坐标已在视口外）：

```
button#settingsClose   @ x=2426, y=18    ← 视口宽仅 1920
button                 @ x=1933, y=85
button                 @ x=1933, y=129
```

**这是真实的可访问性缺陷**：用户在首页连按 Tab，焦点会"消失"到屏幕外的设置面板里，且这 17 个按钮**可被回车真实触发**（`pointer-events:auto`）。

---

## 6. 交互来源盘点（JS 侧）

`_dom_audit.py` 扫描 66 个 JS 文件，按 `innerHTML` / `createElement` / `classList` / 直接写 `style` / `insertAdjacentHTML` 加权得出 UI 生产强度（uiScore），共 **23 个真实 UI 生产者**：

| # | 文件 | 行数 | innerHTML | createElement | classList | 写 style | uiScore | 对应 UI 分类 |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `app.js` | 2506 | 27 | 20 | 54 | 6 | **107** | HUD / Navigation / Chat / Toast |
| 2 | `hotspot.js` | 1882 | 13 | 7 | 10 | **17** | 48 | Hotspot（领域） |
| 3 | `memory.js` | 635 | 21 | 0 | 19 | 4 | 44 | Memory |
| 4 | `overlay-manager.js` | 526 | 5 | 19 | 6 | 5 | 35 | Modal / Overlay 治理 |
| 5 | `settings.js` | 1111 | 8 | 4 | 15 | 1 | 28 | Settings |
| 6 | `companion.js` | 646 | 0 | 0 | 11 | 10 | 21 | Companion |
| 7 | `sysmon.js` | 239 | 5 | 3 | 3 | 5 | 17 | Status |
| 8 | `weather.js` | 498 | 7 | 1 | 7 | 0 | 15 | Weather（领域） |
| 9 | `command-palette.js` | 358 | 3 | 3 | 6 | 0 | 13 | Command Palette |
| 10 | `memory-panel.js` | 205 | 8 | 0 | 2 | 0 | 13 | Memory |
| 11 | `avatar-renderer.js` | 80 | **10** | 0 | 0 | 2 | 12 | Avatar |
| 12 | `doc.js` | 153 | 9 | 0 | 2 | 0 | 12 | Doc（领域） |
| 13 | `mobile-app.js` | 222 | 4 | 4 | 4 | 0 | 12 | Mobile |
| 14 | `tasks.js` | 147 | 2 | 2 | 8 | 0 | 12 | Tasks |
| 15 | `capabilities-view.js` | 209 | 3 | 0 | 8 | 0 | 11 | Capability Matrix |
| 16 | `insight-panel.js` | 142 | 1 | 9 | 1 | 0 | 11 | Insight |
| 17 | `memory-query.js` | 137 | 7 | 0 | 2 | 0 | 10 | Memory |
| 18 | `terminal-stream.js` | 99 | 2 | 1 | 6 | 0 | 10 | Execution |
| 19 | `main-cognitive.js` | 254 | 4 | 4 | 1 | 0 | 9 | 认知主区 |
| 20 | `error-boundary.js` | 84 | 0 | 1 | 0 | **7** | 8 | Error（**无 CSS 类**） |
| 21 | `kws.js` | 200 | 1 | 1 | 6 | 0 | 8 | Mic（领域） |
| 22 | `map.js` | 135 | 5 | 0 | 2 | 0 | 8 | Map（领域） |
| 23 | `onboarding.js` | 173 | 0 | 0 | 8 | 0 | 8 | Onboarding |

**关键风险点**：

- **`innerHTML` 写入合计 145 处** → UI 结构大量由字符串模板生成，CSS 类名散落在 JS 字符串里，**静态分析无法完全覆盖**。这意味着 §3 的 2126 选择器统计**是样式侧的完整集合，但 DOM 侧还有由 JS 动态生成、CSS 中未定义的类名**（未归类的 503 中有一部分属于此）。
- **JS 直接写 `style` 合计 57 处** → 绕过令牌体系的运行时样式注入。其中 `hotspot.js` 17 处、`companion.js` 10 处、`error-boundary.js` 7 处最集中。
- **`error-boundary.js` 是唯一"纯 JS 内联样式、零 CSS 类"的 UI 生产者** → 错误态没有设计语言（D-16）。
- `overlay-manager.js`（19 处 createElement）与 `panel-manager.js` 是 Overlay/Focus/ESC 的中央治理者，Formal UI System 的 Panel 层必须与它们对齐，**不得另起炉灶**。

---

## 7. 视觉分叉量化（硬编码）

### 7.1 总量

硬编码声明合计 **1676 处**（未使用任何 CSS 变量的字面值）。

| 文件 | 硬编码 | 占该文件选择器比 | 备注 |
|---|---:|---:|---|
| `styles.css` | **1306** | 88.5% | 分叉重心 |
| `ui2.css` | 156 | 39.0% | 令牌权威自身也有残留 |
| `runtime-viz.css` | 68 | 212.5% | 平均每个选择器 2 个硬编码 |
| `premium.css` | 51 | 63.8% | — |
| `execution-channel.css` | 48 | 218.2% | 密度最高 |
| `companion.css` | 47 | 40.5% | — |

`runtime-viz.css` 与 `execution-channel.css` 的硬编码密度（>2/选择器）远高于其他文件 —— 这两个文件**几乎完全不消费令牌**，是独立配色的"飞地"。

### 7.2 按维度分解

下表基于各文件 TOP 明细（`styles.css` 的明细被截断至 80 条 / 920 次），故为**下界**：

| 维度 | 计数（下界） | 典型值 | 判定 |
|---|---:|---|---|
| **字号** | **496** | 13px(95) / 14px(65) / 12px(83) / 11px(68) / 10px(35) | ❌ 无字号阶梯，5 档以上随意混用 |
| **颜色** | **471** | `#22d3ee` 系 cyan 大量重复、`rgba(255,255,255,.0X)` 分层 | ❌ 主题色写死，切主题不跟随 |
| **字重** | 112 | 600(61) / 700(41) / 800(2) / 900(3) / 500(2) | ❌ 无字重语义 |
| **字距** | 90 | 1px / 2px / .04em / .05em / .25em 混用 | ❌ px 与 em 混用 |
| **圆角** | 56 | `50%`(51) / `inherit`(5) | ⚠️ 大部分是圆形头像/圆点，合理 |
| **z-index** | 26 | 0,1,2,3,5,10,11,12,13,22,24,25,29,30,31,32,35,60 | ❌ 无层级令牌，18 个不同值 |
| **阴影** | 22 | 全部为完整 box-shadow 字面量 | ❌ 无 elevation 阶梯 |
| **字体族** | 17 | `Orbitron` / `Rajdhani` / `Share Tech Mono` / `inherit` | ⚠️ 见下 |
| 其他 | 剩余 | — | — |

### 7.3 字体：分叉最轻的一项 ✅

`font-family` 硬编码仅 **17 处**，其中 4 处是 `inherit`（无害）。全项目 `font-family` 声明共 **204 处**，绝大多数已走令牌（`--font-display` / `--font-body` / `--font-mono`）。

> **这是唯一一个已基本完成令牌化的维度**，可作为其他维度收敛的范式参考。

⚠️ 但存在一个例外：**`selfcheck.html` 通过 Google Fonts CDN 联网加载 Orbitron / Rajdhani / Share Tech Mono**（D-11），而主应用使用本地字体。这既违反 Local First，也意味着离线时该页字体降级。

### 7.4 z-index 层级失控明细

实测出现过的 z-index 值（18 个不同值，无任何令牌）：

```
ui2.css        : 0, 1, 2, 5, 22, 24, 25, 29, 30, 31, 32, 35
companion.css  : 1, 2, 3, 10, 11, 12, 13
runtime-viz.css: 60
execution-channel.css: 60
```

`runtime-viz.css` 与 `execution-channel.css` **同时使用 z:60**，而 ui2.css 的最高层是 35 —— 这两个飞地文件的层级**凌驾于整个 OS 外壳之上**，且两者互相冲突（同值，靠 DOM 顺序决胜负）。

---

## 8. 命名空间碎片化

以 class 名的第一段作为前缀统计，全项目共 **197 个不同前缀**：

| 前缀 | 出现次数 | 归属 | 是否受控 |
|---|---:|---|---|
| `os` | 288 | OS 外壳（ui2.css） | ✅ 受控 |
| `hs` | 276 | Hotspot 领域 | ✅ 领域自洽 |
| `zz` | 175 | 小6通用 | ⚠️ 语义模糊 |
| `wx` | 145 | Weather 领域 | ✅ 领域自洽 |
| `mem` | 140 | Memory | ✅ 领域自洽 |
| `settings` | 99 | 设置 | ⚠️ 跨两文件 |
| `hotspot` | 86 | Hotspot（**与 `hs` 重复的第二套前缀**） | ❌ 同一领域双前缀 |
| `avatar` | 84 | 化身 | ✅ |
| `sm` | 53 | 场景/系统监控 | ⚠️ 缩写歧义 |
| `onb` | 53 | Onboarding | ✅ |
| `sc` | 50 | Scene | ⚠️ 与 `sm` 界限不清 |
| `tele` | 49 | 旧外壳遥测栏（**已隐藏**） | ❌ 死前缀 |
| `css` | 48 | — | ❌ 无语义 |
| `ts` | 48 | Terminal Stream | ⚠️ |
| `orb` | 42 | 语音球 | ✅ |
| `cap` | 42 | Capability | ✅ |
| （其余 181 个前缀） | — | 长尾 | ❌ |

**问题定性**：

1. **同一领域双前缀**：Hotspot 同时用 `hs-`（276）和 `hotspot-`（86）。
2. **死前缀仍在**：`tele-`（49 次）服务于 `visibility:hidden` 的旧外壳。
3. **长尾失控**：197 个前缀中，前 16 个占绝大多数，剩余 **181 个前缀属于一次性命名** —— 这是"面板驱动"开发方式的直接证据。

---

## 9. 缺陷清单（本次盘点查实，共 22 项）

优先级定义：**P0** = 功能性缺陷或可访问性缺陷，影响用户实际使用；**P1** = 系统性分叉，阻碍 Formal UI System 建立；**P2** = 冗余/技术债，不影响当前表现。

| 编号 | 缺陷 | 优先级 | 证据来源 | 性质 |
|---|---|---|---|---|
| **D-01** | `--glow` 类型冲突（颜色 vs 阴影简写），致 `.os-nav-brand.active` 在 **dark-cyan（默认）/ green / purple / amber / rose 5 个主题下 `box-shadow: none`**，连 accent 描边一并丢失 | **P0** | `_token_probe.json` 真实渲染 | 功能性 |
| **D-14** | **29 个焦点陷阱**：不可见元素仍可 Tab 到达并可回车触发，其中 `#settingsPanel` 占 17 个（`transform` 离屏但 `pointer-events:auto`） | **P0** | `_hidden_probe.json` | 可访问性 |
| **D-02** | 主题令牌双源：`styles.css body[data-theme]`(0,1,1) 覆盖名义权威 `ui2.css [data-theme]`(0,1,0)，26 个同名变量、**10 个真实值不同** | **P0** | `_theme_conflict.py` | 架构 |
| **D-08** | 控件原语双源：`.btn-new` / `.chip` / `.glass-panel` / `.onb-card` / `.ic` 同时定义在 premium.css 与 ui2.css | **P0** | `_css_audit.json` 跨文件重复 | 架构 |
| **D-06** | Settings 面板横跨 **三个文件**（styles 58 + premium 17 + ui2 7 = 82 选择器），`.settings-panel` / `.settings-head` / `.settings-switch` 系列共 10 组双源 | P1 | `_inventory_map.json` | 分叉 |
| **D-07** | Theme Selector 横跨 **三个文件**（styles 17 + premium 4 + ui2 9） | P1 | `_inventory_map.json` | 分叉 |
| **D-09** | Empty 空态横跨 **四个文件**，仅 21 个选择器 —— 单位分叉密度最高 | P1 | `_inventory_map.json` | 分叉 |
| **D-10** | `runtime-viz.css` / `execution-channel.css` 为配色飞地（硬编码密度 >2/选择器，几乎不消费令牌），且两者**同用 z-index:60 凌驾于 OS 外壳最高层 35 之上** | P1 | `_css_audit.json` | 分叉 + 层级 |
| **D-11** | `selfcheck.html` 通过 **Google Fonts CDN 联网**加载 Orbitron/Rajdhani/Share Tech Mono，由 `hotspot.js:780` 的真实按钮打开 → 违反 Local First，离线字体降级 | P1 | HTML 外链实测 | 合规 |
| **D-12** | `mobile-app.html`(28) / `selfcheck.html`(62) / `weather-modal-preview.html`(22) 共 **112 个内联选择器完全游离于令牌体系外**（第三套样式） | P1 | HTML 内联统计 | 分叉 |
| **D-16** | `error-boundary.js` 零 CSS 类、7 处 JS 内联 style → **错误态没有设计语言** | P1 | `_dom_audit.json` | 缺失 |
| **D-18** | z-index 共 **18 个裸值无令牌**（0…60），跨文件冲突 | P1 | `_css_audit.json` | 分叉 |
| **D-19** | **4 种不等价的隐藏机制混用**（`visibility` / `display` / `opacity` / `transform` 离屏），仅前两者能正确移出可访问性树 | P1 | `_hidden_probe.json` | 一致性 |
| **D-21** | 7 个零实现分类，其中 **Loading / Tooltips / Error 三项属基础态缺失** | P1 | `_inventory_map.json` | 缺失 |
| **D-05** | `--presence-color` 在 companion.css 被写死为 `#5fb3c8`，伴生窗**不参与 Phase 8 Presence 状态投影** | P1 | `_css_audit.json` 跨文件令牌 | 一致性 |
| **D-03** | 16 个同名同值令牌在两处重复定义（`--cyan` / `--teal` / `--dim` / `--txt` 等） | P2 | `_theme_conflict.py` | 冗余 |
| **D-04** | `--dur-focus`：ui2.css `700ms` vs companion.css `.42s` —— 同一产品两窗口动效节奏漂移 | P2 | `_css_audit.json` | 冗余 |
| **D-13** | `weather-modal-preview.html` **零引用孤儿文件**（精确 grep 无任何命中） | P2 | grep 实证 | 死代码 |
| **D-15** | 旧外壳 `#app` 及 `.rail` / `.main` / `#tele` 子树仍完整存在于 DOM（`visibility:hidden`，有 layout 成本、无渲染），相关 CSS 全为活代码零效果 | P2 | `_shell_probe.json` | 结构债 |
| **D-17** | `styles.css` 内 `wxGlitch`(L1715/L1855) / `wxPulse`(L1818/L1958) / `tsBlink`(L2077/L2110) 各重复定义 2 次，前者为死代码 | P2 | keyframes 扫描 | 死代码 |
| **D-20** | 命名空间 **197 个前缀**；Hotspot 双前缀（`hs-` 276 + `hotspot-` 86）；`tele-`(49) 为死前缀；181 个长尾一次性前缀 | P2 | 前缀统计 | 一致性 |
| **D-22** | JS 侧 **145 处 `innerHTML`** 字符串模板生成 DOM，类名散落 JS 中 → 静态分析存在盲区（503 个未归类选择器中含此类） | P2 | `_dom_audit.json` | 可分析性 |

### 9.1 已在 Section 1 收口的项：F-01

**F-01 全局横向滚动** 已于 Section 1 修复并验证，此处仅存档结论：

- **真实根因**：离屏 Context 抽屉 `.os-side` 的**包含块是 `.os-shell`**（`position:absolute` 的最近已定位祖先），**不是初始包含块**。
- **对照实验**（`_f01_minimal.mjs`，CDP 真实渲染，四档宽度 1920/1440/1280/1024 的 `canScrollX`）：

| 场景 | 配置 | 结果 |
|---|---|---|
| A | `html:clip` + `.os-shell:clip` | `0 / 0 / 0 / 0` ✅ |
| B | 仅 `.os-shell:clip` | `0 / 0 / 0 / 0` ✅ **单独充分** |
| C | 仅 `html:clip` | `382 / 382 / 370 / 722` ❌ |
| D | 两者都退回（缺陷基线） | `382 / 382 / 370 / 722` |

- **C ≡ D**，证明根元素上的 `overflow-x` 对本缺陷**零贡献**。
- **最终修复**：`ui2.css` 仅保留 `html { overflow-x: hidden; }`，真正的修复点是 `.os-shell { overflow-x: clip; }`；诊断注释已重写为与实测一致。
- 抽屉打开态复验通过（`left=1538 / right=1898 / visibleInViewport=true`，滑入动画未受影响）。

---

## 10. Section 2 指标汇总

大指令 Section 10 要求的 11 项指标中，**Section 2 只能交付前 3 项**（盘点性指标），其余 8 项依赖 Section 3–9 的实施与验收，此处如实标注为未开始。

| # | 指标 | Section 2 实测值 | 状态 |
|---:|---|---|---|
| 1 | **UI 元素总数** | CSS 选择器 **2126**（唯一 1890）+ HTML 内联 **112** = **2238**；DOM 侧 314 个 id / 283 个唯一 class / 35 个顶层容器；UI 语义分类 **52 类**（其中 7 类零实现） | ✅ 已测 |
| 2 | **重复元素数** | 跨文件重复 **29 组** + 同文件多定义 **22 组** + keyframes 重名 **3 组** = **54 组**；选择器层面重复定义 **236 次** | ✅ 已测 |
| 3 | **视觉分叉数** | 硬编码 **1676 处**（字号 496 / 颜色 471 / 字重 112 / 字距 90 / 圆角 56 / z-index 26 / 阴影 22，均为下界）+ 令牌冲突 **26 个（10 个值不同）** + 跨文件令牌冲突 **2 个** + 多文件来源分类 **22 类** + 命名空间前缀 **197 个** + 缺陷 **22 项（P0×4 / P1×11 / P2×7）** | ✅ 已测 |
| 4 | 收敛后统一数 | — | ⏸ Section 3–6 |
| 5 | 新增 Token 数 | — | ⏸ Section 3 |
| 6 | 删除遗留样式数 | — | ⏸ Section 4–6 |
| 7 | 保留领域特殊样式数 | 候选集已定：**559 个**（Hotspot 210 / Weather 139 / Scene 73 / Map 36 / Mic 36 / Review 31 / Doc 26 / Tools 8）+ Galaxy 24 + Avatar 76 + Presence 10 | 🟡 候选已定，未决策 |
| 8 | GUI 截图数量 | 0（Section 2 为静态盘点；已有渲染类探针 4 个但不产出验收截图） | ⏸ Section 7 |
| 9 | Responsive 结果 | 仅 F-01 的四档 `canScrollX` 全 0 | ⏸ Section 7 |
| 10 | Regression 结果 | 本 Section **零代码改动**，无回归面 | ⏸ Section 9 |
| 11 | 红线检查结果 | ✅ 通过：未新增 Runtime / EventBus / State 写入点，未新增 Presence 写入点，未引入第二 Design System，未改 Galaxy 语义，未触碰 Planner / Workflow / Agent / Memory / LLM | ✅ 已核 |

### 10.1 盘点的三条核心结论

1. **小6不是"组件驱动"，是"面板驱动"。** 真正的控件原语（按钮/输入/卡片/芯片/徽标）合计仅 **37 个选择器**，而领域面板有 **559 个**、Memory 单项就有 **171 个**。每个面板各自重写按钮和卡片 —— 这是 197 个命名前缀、1676 处硬编码的共同根因。Formal UI System v1.0 的第一要务不是"改样式"，而是**首次真正建立原语层**。

2. **名义权威与实际权威不一致。** `ui2.css` 在文档上是令牌最终权威，但 `styles.css` 用更高特异性的 `body[data-theme]` 实际接管了 6 套主题的关键变量，并因 `--glow` 的类型冲突在**默认主题**上造成了真实功能缺陷。**先解决权威归属，再谈收敛**，否则任何令牌改动都会被静默覆盖。

3. **分叉是分层的，收敛方式必须分层。** 系统层（Shell/HUD/导航/控件）应**结构级统一**；领域层（Hotspot/Weather/Scene/Map/Mic/Doc）应**保留造型语言、只替换令牌**；受保护层（Galaxy 语义 / Presence 三唯一 / Avatar 状态机）**只记录不动**。用同一把尺子推平全部 2126 个选择器，会破坏 Golden State 红线。

---

## 11. 🛑 STOP

本 Section 到此结束。

**已完成**：Section 2 UI 全量盘点，交付本文档。

**未进入**：Section 3（Formal UI System v1.0 设计语言）及之后的任何环节。

**本 Section 的边界（严格遵守）**：

- ❌ 未修改任何 CSS / JS / HTML 源文件（F-01 的 ui2.css 改动属 Section 1，已于本轮之前完成）
- ❌ 未提交 Git
- ❌ 未做任何收敛决策（`--glow` 归属、premium 分层契约、领域层处理方式均为**待决策**）
- ❌ 未进入 Provider / Electron / Mobile / Voice / Automation 任何方向

**等待 Review 后方可进入 Section 3。**

---

### 附录 A：文档与证据的对应关系

| 本文档章节 | 依赖证据 |
|---|---|
| §1 样式来源全景 | `_css_audit.json` + HTML `<link>` / `<style>` 实测 |
| §2 令牌权威与分叉 | `_theme_conflict.py` + `_token_probe.json`（真实渲染） |
| §3 52 分类主表 | `_inventory_map.json` |
| §4 重复定义清单 | `_css_audit.json`（cross_file_dupes / same_file_multi / keyframes） |
| §5 DOM 结构 | `_dom_audit.json` + `_shell_probe.json` + `_hidden_probe.json`（真实渲染） |
| §6 交互来源 | `_dom_audit.json` |
| §7 视觉分叉量化 | `_css_audit.json`（hardcode） |
| §8 命名空间 | CSS 前缀统计（读盘计算） |
| §9 缺陷清单 | 以上全部 |
| §9.1 F-01 | `_f01_minimal.mjs`（真实渲染四场景对照） |



