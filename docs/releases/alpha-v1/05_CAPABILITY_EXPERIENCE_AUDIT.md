# 05 · 能力体验审计（Capability Experience Audit）— Phase 4

> 阶段：AI OS Alpha Stabilization Program v1.0 · Phase 4
> 身份：Senior QA Architect + Senior Product Architect + Senior UX Engineer + AI OS Release Manager
> 模式：**Audit → Observe → Simulate → Verify → Document → STOP**（仅审计 + 文档，零代码改动）
> 审计时间：2026-08-06
> 上游：P0 预飞 / P1 用户旅程 / P2 每日工作流 / P3 Workspace 稳定性（均已落盘 00/02/03/04）
> 下游：P5 UX Bug Bash（建清单禁修） / P6 允许修复 / P7 回归 / P8 性能 / P9 就绪 / P10 文档

---

## 一、审计目的与纪律边界

**目的**：验证「能力真相（Capability Platform SSOT，14 份文档 / 19 分类 / ~135 能力）」中声明的**生命周期档位（Production / Beta / Experimental / Hidden / Dead / Missing）** 与**用户在 UI 中实际看到、能够触发的暴露面**是否一致。即：隐藏/死亡/缺失能力是否被误曝光？生产/实验能力是否可达且诚实标注？重复能力是否造成用户困扰？

**纪律（严守）**：
- ✅ 仅审计、观察、文档。不修改任何源码 / 配置 / UI / CSS / JS / Python。
- ✅ 不新增能力 / 不进禁区（Electron/Mobile/Voice/Perception/Planner/Workflow 等）。
- ✅ 所有发现留待 P5（清单）→ P6（修复）。本 Phase 产出**结论 + 发现清单 + 修复建议**，不落地修复。
- 已确认后端 `:8011`（P2 启动）仍运行，本次**未**依赖其运行——纯静态代码 + 真相文档交叉审计。

---

## 二、审计对象与方法

| 维度 | 数据来源 | 方法 |
|---|---|---|
| 能力真相（SSOT） | `docs/capability-platform/00~12,99` | 读取分类 / 生命周期 / 入口地图 / 重复 / 用户指南 |
| 暴露框架 | `xiao6-ui/capability-exposure.js` | 通读 T0–T4 + maturity + HIDDEN_MATURITY |
| 唯一命令入口 | `xiao6-ui/command-palette.js` | 通读 `buildCommands` / `closeAllPanels` / `MODES` |
| 面板分发器 | `xiao6-ui/panel-manager.js`（REG） | 比对 REG `overlayId` 与真实 `OverlayManager.track` id |
| 能力视图 | `xiao6-ui/capabilities-view.js` + `capability-registry.js` | 验证 `implemented:false` 是否诚实标注 |
| 浮层快捷键 | `xiao6-ui/command-dock.js` / `app.js` | 校验快捷键提示是否有对应实现 |
| 设置开关 | `xiao6-ui/settings.js` | 枚举暴露的 `FEATURE_*` 开关 |

**交叉比对原则**：以 SSOT 的「生命周期档位」为期望，以「前端实际暴露代码」为实测，二者不一致即记为体验发现。

---

## 三、能力暴露框架评估（强项，PASS）

`capability-exposure.js`（UI Experience Sprint 3）是**统一暴露真相**基础设施，质量高于一般 Alpha：

- **五档暴露级别 T0–T4**（`:16-22`）：默认展示 / 按需 / 自动 / 后台 / 专家模式——单一来源，覆盖全部 19 分类（`:35-55` `CATEGORY_DEFAULTS`）。
- **成熟度诚实标注**（`:25-32` `MATURITY`）：`prod/beta/exp/hidden/dead/missing` 各有 `badge` 与 `honest` 标签。
- **缺失/死亡严禁暴露**（`:58` `HIDDEN_MATURITY = { missing, dead }`）：`classify()` 对 `missing`/`dead` 返回 `exposed:false`，且 `tag()` 供指令中心/能力视图/设置统一读取（`:92-107`）。
- **电脑能力诚实降级**（`:111-141` `computerMap`）：`implemented === false` → 成熟度标 `missing`（即「规划中」，不暴露为可用）。
- **指令中心落地诚实标签**（command-palette.js:187）：命令经 `CapabilityExposure.tag()` 附加 `maturity` 徽标；`FEATURE_MULTI_DEVICE`（多端同步）在 `FEATURE_META` 标 `exp`（`:26`），命令渲染带 `exp` 标签。
- **能力视图诚实标注**（capabilities-view.js:74）：`implemented === false` 渲染为 `（规划中）`，而非「已接入」。

> **结论**：暴露框架**本身诚实、健全**，是 Alpha 可被日常使用的正面支撑——用户不会被「不存在的能力」误导。这是 Phase 4 最重要的正向结论。

---

## 四、入口暴露一致性审计

### 4.1 指令中心（唯一命令入口，command-palette.js）

`buildCommands()`（`:71-96`）暴露：面板 ×10 / 主题 ×6 / 功能 ×4 / 创建 ×3 / 系统 ×2 + 意图自由文本。

| 检查项 | 结果 |
|---|---|
| 是否存在 Planner/Workflow/Scheduler 幽灵命令？ | ✅ 无。`MODES`（`:32-35`）的「工作流/Agent」仅是**过滤 tab**（workflow→create 分类，agent→intent 网关），非能力命令；无对应「蓝图能力」误曝光。 |
| 生产面板是否可达？ | ✅ 全部经 `PanelManager.openCapability()` 唯一分发（`:74-83`），回落 `window.ZZ*` 桥，路径健壮。 |
| 实验能力是否诚实标注？ | ✅ `多端同步` 带 `exp` 徽标（`:87`）。 |
| 创建类是否真实？ | ✅ 目标/待办/提醒预填对话输入框，交 LLM 工具循环（`:89-91`）。 |

### 4.2 主窗按钮 / 伴侣菜单 / 设置（03 入口地图复核）

- 主窗按钮（briefing/memory/weather/hotspot/settings）与指令中心面板命令**一一对应**，多入口属正常（03 已判定「正常」）。
- 设置面板暴露 14 个 `FEATURE_*` 开关（settings.js:266-277），均为 opt-in 显式配置，无隐藏能力误曝光。
- 伴侣右键菜单（companion #quickMenu）条目均指向真实能力（开主窗/对小6说/任务/状态/记忆/项目/指令/设置/勿扰/隐藏），无幽灵项。

---

## 五、体验发现明细（EXP-1 ~ EXP-7）

### 🔴 EXP-1 · 缺陷（高，面板关闭孤儿化）— 每日简报无法被「关闭所有面板」关闭

**现象**：用户在指令中心执行「关闭 所有面板」后，**每日简报（briefing）浮层仍保持打开**。

**根因（连接 P3-F6）**：
- `command-palette.js:98-102` `closeAllPanels()` 三步走：
  1. 移除硬编码 `*-mode` 体类列表 `['hotspot','weather','sysmon','term','doc','memory','map','memq']`（**无 `briefing`**）；
  2. `ZZSettings.close()`；
  3. `PanelManager.closeAll()`。
- `briefing` 真实经 `app.js` `OverlayManager.track('briefing', …)` 注册（P3 已确认 app.js:1655），但 `panel-manager.js:93` REG 中 `briefing` 声明 `overlayId:'zz-panel', host:true` → `PanelManager.isOpen('briefing')` 查的是 `OverlayManager.isOpen('zz-panel')`（恒 false）→ `PanelManager.closeAll()` **跳过 briefing**。
- 硬编码体类列表亦不含 `briefing-mode` → 第一步也漏掉。
- 结果：briefing 成为「关闭所有面板」的**永久孤儿**。

**影响**：用户期望一键收拢全部浮层，实际简报残留，造成「关不掉」的困惑；与 P3-F6 同源，属既有 latent 缺陷（非本次回归）。

**修复建议（P6，单行配置级，零行为新增）**：将 `panel-manager.js:93` REG `briefing` 改为 `{ btnId:'btnBriefing', overlayId:'briefing' }`（与 P3-F6 修复同源）。修复后 `PanelManager.closeAll()` 经 `OverlayManager.isOpen('briefing')` 正确命中并关闭。亦可顺带在 `closeAllPanels` 体类列表补 `'briefing'`（防御性，非必须）。

---

### 🟠 EXP-2 · 缺陷（中，误导快捷键）— `Ctrl/Cmd+U 打开宇宙视图` 无实现

**现象**：`command-dock.js:36` 渲染提示文案 `Ctrl/Cmd+U 打开宇宙视图 · ⌘/Ctrl+K 快捷命令 · 支持拖拽文件`，但全仓**无 `Ctrl/Cmd+U` 处理器**（03 入口地图已标注「疑似未实现/死快捷键」）。

**影响**：Command Dock 向用户**承诺一个不存在的能力**，点击/按键无反应 → 误导、降低信任。

**修复建议（P6，纯文案/体验修复）**：删除该误导提示文案（或若决定立项宇宙视图，则不在 Alpha 范围）。仅删文案，零行为新增，属体验修复。

---

### 🟠 EXP-3 · 架构风险（中，面板关闭约定分裂）

**现象**：`closeAllPanels()`（command-palette.js:98-102）同时依赖：
- (a) 手写 `*-mode` 体类白名单（必须与各面板 `setXxxMode` 保持手动同步）；
- (b) `PanelManager.closeAll()`（依赖 REG `overlayId` 与 `OverlayManager.track` id 一致）。

两条路径**不一致即产生孤儿**（EXP-1 即后果）。任何新增面板若只接 REG 而不加体类、或反之，都会被「关闭所有面板」漏掉。

**影响**：面板关闭语义碎片化，是 Overlay 统一化（D9，05 重复报告）未收口的**直接体验后果**。

**修复建议（P6）**：以 `PanelManager.closeAll()` 为**唯一**关闭收敛点（修复 F6 后其覆盖所有 REG 面板），`closeAllPanels` 退化为仅调 `PanelManager.closeAll()` + `ZZSettings.close()`，删除手写体类白名单。属体验架构收敛，不新增能力。

---

### 🟡 EXP-4 · 观察（低，多入口冗余但一致）

`weather`/`hotspot`/`briefing`/`memory` 各自有 3 个入口（主窗按钮 + 指令中心 + 伴侣菜单）。**一致、不冲突、不困惑**，属正常多入口设计。仅 note：weather 三处（wxOpenBtn / 指令中心「打开天气观测」/ 伴侣菜单）略冗余，可接受，不强制收敛。

---

### 🟡 EXP-5 · 观察（低–中，Feature Flag 默认值声明 vs 运行时不一致）

**现象**：`config.py` 顶部常量多为 `False`，但 `reload()` 以 `os.environ.get("FEATURE_X","true")` 覆盖，导致多数 flag **实际运行时默认开启**（02 统计已标「一致性风险」）。设置面板暴露 14 开关（settings.js:266-277）。

**影响**：用户在设置里切换某 flag，若其运行时默认被 env 强制，可能出现「关不掉/开不稳」的体验不确定感。属配置一致性问题，对日常使用影响有限但存在。

**修复建议（P6 评估）**：统一 `config.py` 声明默认与 `reload()` 运行时默认（低风险，不触架构/权限红线）。建议 P6 仅做一致性对齐，不改功能行为。

---

### 🟡 EXP-6 · 观察（低，能力视图范围局限）

`capabilities-view.js` 数据源为 `window.ZZCapabilities.allCapabilities()`（即 `capability-registry.js` 的**电脑控制**注册表，13 项），故「能力清单视图」仅展示电脑能力，非全量 ~135。该视图本意是权限/风险透明面板，范围合理；但若用户预期「查看小6全部能力」，会有轻微期望落差。

**建议**：视图标题/引导文案明确「电脑控制能力」范围即可（P6 文案级，可选）。非缺陷。

---

### ✅ EXP-7 · 正向确认（强项）

- **无 dead/missing 能力误曝光**：`capability-exposure.js` `HIDDEN_MATURITY` 屏蔽 `dead`/`missing`；指令中心/按钮/伴侣菜单均未出现 Planner/Workflow/Scheduler 幽灵项。
- **实验能力诚实标注**：`多端同步` 带 `exp` 徽标；computer `implemented:false` 在能力视图标「规划中」。
- **隐藏能力均 opt-in**：CrossDevice/感知/常驻/移动端等经设置显式开关，无强制曝光。

---

## 六、与 SSOT 生命周期交叉比对

| SSOT 生命周期 | 数量 | UI 实际暴露 | 一致性 |
|---|---|---|---|
| Production | ~95 | 指令中心/按钮/伴侣/设置均可达 | ✅ 一致 |
| Beta | ~12 | Social（需配置）/ 部分 feature；诚实 | ✅ 一致 |
| Experimental | ~8 | `多端同步` 标 `exp`；感知 Mock 文档已说明 | ✅ 一致（标注诚实） |
| Hidden | ~14 | opt-in 设置开关；未在主命令流强制 | ✅ 一致 |
| Dead | ~12 | `HIDDEN_MATURITY` 屏蔽；无入口 | ✅ 一致（未误曝光） |
| Missing（蓝图） | 2 | Planner/Workflow/Scheduler 均无命令/按钮 | ✅ 一致（未误曝光） |

> 生命周期档位 ↔ UI 暴露**总体一致**；不一致处均为「关闭路径孤儿（EXP-1）」与「误导文案（EXP-2）」，不涉及 dead/missing 误曝光。

---

## 七、重复能力对体验的影响（D1–D11 精选）

| 组 | 用户侧体验影响 | 严重度 |
|---|---|---|
| D8 Toast 5+ 套 | 不同来源 toast 样式/位置/时序不一致，用户感知「通知抖动」 | 中（体验层） |
| D9 Overlay 12+ 套 | ESC/焦点分散 → 部分浮层 ESC 关不掉、焦点陷阱 0 处（P3 已确认）→ EXP-1/EXP-3 同源 | 高（体验层） |
| D10 能力视图三源 | `capability-registry` / `capabilities-view` / `capability-matrix` 同源三渲，无用户可见分歧 | 低 |
| D1 天气双源 / D4 跨端 / D5 蒸馏双写 | 后端逻辑分歧，用户侧通常无感（除非结果不一致） | 低–中 |

> 重复 UI 子系统（D8/D9）是 Phase 4 体验缺陷（EXP-1/EXP-3）的**架构根因**，统一化（OverlayManager）已建未收口。

---

## 八、能力体验裁决

| 维度 | 结论 |
|---|---|
| 暴露框架诚实性 | ✅ PASS（T0–T4 + maturity + HIDDEN_MATURITY 健全） |
| 生命周期 ↔ UI 一致性 | ✅ PASS（dead/missing 未误曝光；exp/beta 诚实标注） |
| 生产/实验能力可达性 | ✅ PASS |
| 面板关闭完整性 | 🔴 FAIL（EXP-1 briefing 孤儿；根因 F6） |
| 快捷键提示真实性 | 🔴 FAIL（EXP-2 宇宙视图死提示） |
| 关闭路径架构一致性 | 🟠 PARTIAL（EXP-3 双路径分裂） |

**总裁决**：能力**暴露面诚实、可达、不误导**（强项），但存在 **2 个具体用户可见缺陷（EXP-1/EXP-2）+ 1 个架构碎片化（EXP-3）**，均非能力新增、均可在 P6 以配置/文案级修复收口，且 EXP-1 与 P3-F6 同源。

**Release Gate 4（Capability 未违反）状态**：
- ✅ 能力真相 SSOT 未被破坏（无新增/删除能力、无生命周期篡改）。
- ✅ 无 dead/missing 能力误曝光。
- 🔴 存在 2 个体验缺陷（EXP-1/EXP-2），建议 P6 修复后 Gate 4 → FULL PASS。
- **Gate 4 = PARTIAL → 修复 EXP-1/EXP-2 后 FULL**。

---

## 九、下一步（移交 P5 / P6）

**P5 UX Bug Bash（仅建清单，禁修）**：将 EXP-1、EXP-2、EXP-3 纳入 UX Bug 清单（不重复修复，等 P6 统一窗口）。

**P6 允许修复（建议项，均零行为新增 / 配置·文案级）**：
1. **EXP-1 + P3-F6（同源）**：`panel-manager.js:93` REG `briefing` 改 `{ btnId:'btnBriefing', overlayId:'briefing' }`；可选补 `closeAllPanels` 体类列表 `'briefing'`。
2. **EXP-2**：删除 `command-dock.js:36` 中 `Ctrl/Cmd+U 打开宇宙视图` 误导文案。
3. **EXP-3（架构收敛）**：`closeAllPanels` 退化为仅 `PanelManager.closeAll()` + `ZZSettings.close()`，删手写体类白名单（依赖 #1 修复后覆盖完整）。
4. **EXP-5（评估）**：统一 `config.py` 声明/运行时默认（低风险）。
5. **EXP-6（可选）**：能力视图文案明确「电脑控制能力」范围。

**不动作（严守禁区）**：不实现宇宙视图、不新增能力、不接入 Planner/Workflow/Scheduler、不改权限/EventBus/架构。

---

## 十、状态

🛑 **本 Phase 4 为纯审计，已完成、结论明确、发现清单齐备 —— STOP，移交 P5（建清单）/ P6（修复）。** 全程零代码改动，能力真相 SSOT 完好，暴露框架诚实性为 Alpha 日常可用的正面支撑。
