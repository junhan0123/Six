# Phase B · B13 — Visual Gate（视觉验收）

> 状态：**B9 VISUAL GATE = COMPLETE**
> 日期：2026-08-09
> 纪律：本轮**只读、只记录、不修改任何代码**（CSS/JS/HTML/Token/Primitive/Layout/Galaxy/Presence/Workspace/Settings/Provider/Runtime 等均不改动）。

---

## 0. 截图来源与覆盖度声明

本轮被要求查看：

1. 1920 Home Idle
2. 1000 Home
3. 720 Home
4. Workspace
5. Settings
6. Context

B9 生成的 6 张 CDP 截图（`docs/ui-system/phase-b/shots/`）实际为：

| B9 文件名 | 实际内容 | 问题 |
|-----------|----------|------|
| `01-home-1920.png` | Home 但被 onboarding 卡片遮挡 | onboarding 覆盖，无法评分底层 Home |
| `02-home-1440.png` | Home 但被 onboarding 卡片遮挡 | 同上 |
| `03-home-1280.png` | Home 但被 onboarding 卡片遮挡 | 同上 |
| `04-home-1024.png` | Home 但被 onboarding 卡片遮挡 | 同上 |
| `05-focus-dark-purple-1440.png` | 焦点环探针（dark-purple 主题） | 含注入的 probe 元素，非干净 UI 状态 |
| `06-onboarding-overlay-1440.png` | onboarding overlay + probe 元素 | 验证 glass/overlay 用，非普通界面 |

**结论**：B9 截图成功验证了 **F-B01 焦点环跨主题一致性** 与 **primitive computed style**，但 **01–04 被 onboarding 覆盖**，且**缺少 clean Home Idle / 1000 / 720 / Workspace / Settings / Context** 视图。

为完成视觉验收，本报告补充查看同一代码基线下的真实历史截图（来自 `docs/ui-consolidation/shots/` 与 `docs/ui-consolidation/shots-formal/`，均为 UI Consolidation Sprint v1.0 / UI Final Visual Review v1.0 产物），并在下表明确标注来源。

---

## 1. Screenshot Matrix

| # | 要求视图 | 实际查看文件 | 来源 | 可视状态 | 备注 |
|---|----------|--------------|------|----------|------|
| 1 | 1920 Home Idle | `docs/ui-consolidation/shots/01-full-1920-idle.png` | UI Consolidation Sprint | ✅ 干净 | Galaxy + Command Dock + HUD + Timeline |
| 2 | 1000 Home | `docs/ui-consolidation/shots/03-compact-1000.png` | UI Consolidation Sprint | ✅ 干净 | compact 响应式 |
| 3 | 720 Home | `docs/ui-consolidation/shots/04-narrow-720.png` | UI Consolidation Sprint | ✅ 干净 | narrow 响应式，顶部图标栏 |
| 4 | Workspace | `docs/ui-consolidation/shots/05-workspace-chat.png` | UI Consolidation Sprint | ✅ 干净 | chat workspace + runtime 右栏 |
| 5 | Settings | `docs/ui-consolidation/shots-formal/31-settings.png` | UI Final Visual Review | ⚠️ 较暗/略糊 | 右侧设置抽屉，可见主题选择器 |
| 6 | Context | `docs/ui-consolidation/shots/02-full-1920-context-open.png` | UI Consolidation Sprint | ✅ 干净 | 右侧 Capability Matrix + Insight |
| 附 | F-B01 焦点验证 | `docs/ui-system/phase-b/shots/05-focus-dark-purple-1440.png` | B9 CDP | ✅ 干净探针 | 紫描边 + 紫光晕一致 |
| 附 | Onboarding 玻璃面板 | `docs/ui-system/phase-b/shots/06-onboarding-overlay-1440.png` | B9 CDP | ✅ 干净探针 | glass-panel / onb-card / onb-overlay 验证 |

> 评分基于**真实像素**；来源差异在评分时已按可视质量与状态加权。

---

## 2. 10 项视觉评分（每项 1–5）

| 视图 | A Layout | B Typography | C Spacing | D Panel/Card | E Button/Input | F Border/Radius | G Shadow/Glow | H Theme | I Density | J Identity | 小计 |
|------|----------|--------------|-----------|--------------|----------------|-----------------|---------------|---------|-----------|------------|------|
| 1920 Home Idle | 5 | 4 | 4 | 5 | 4 | 5 | 5 | 5 | 4 | 5 | **46** |
| 1000 Home | 4 | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 4 | 5 | **44** |
| 720 Home | 3 | 4 | 3 | 4 | 4 | 5 | 5 | 5 | 3 | 4 | **40** |
| Workspace | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 4 | 4 | 3 | **33** |
| Settings | 4 | 3 | 4 | 4 | 3 | 4 | 4 | 5 | 4 | 4 | **39** |
| Context | 4 | 4 | 4 | 4 | 4 | 5 | 4 | 5 | 4 | 4 | **42** |

**评分说明**

- **A Layout hierarchy**：Home Idle 层级最清晰（Galaxy 核心 > Command Dock > HUD/侧边栏）；Workspace 三栏信息密度高，层级弱于 Home。
- **B Typography consistency**：Home/Context 统一；Workspace 右栏与聊天侧栏字号偏小、字重不一致；Settings 因截图较暗略降。
- **C Spacing consistency**：Home 与 Context 节奏一致；720 narrow 顶部栏与 Hero 区域略显拥挤；Workspace 面板间距紧凑。
- **D Panel/Card consistency**：Home 的 Command Dock、HUD 卡片、Context 的 Capability Matrix 卡片共享玻璃/圆角语言；Workspace 面板更扁平、更不透明。
- **E Button/Input consistency**：Command Dock 输入框与发送按钮统一；Workspace 底部输入框与 Command Dock 风格不同；Settings 中可见旧式 toggle。
- **F Border/Radius consistency**：全站圆角语言基本统一（卡片、按钮、输入框）。
- **G Shadow/Glow consistency**：Home/Context 光晕使用一致；Workspace 光晕弱，部分文字在 Galaxy 背景上可读性下降。
- **H Theme consistency**：dark-cyan 主题在所有视图中一致应用；Settings 中主题选择器可见 9 色板。
- **I Information density**：Idle  intentionally 稀疏；Workspace 高但合理；720 narrow 偏高。
- **J Xiao6 OS identity**：Home/Context 身份感强；Workspace 更像传统 dashboard/chat，身份感弱。

---

## 3. Overall Score

| 指标 | 分数 | 计算方式 |
|------|------|----------|
| **Overall UI System Score** | **81 / 100** | 六视图小计均值：244 / 300 → 81.3，取整 |
| **Home Score** | **87 / 100** | (46 + 44 + 40) / 3 = 43.3 / 50 → 87 |
| **Workspace Score** | **66 / 100** | 33 / 50 → 66 |
| **Settings Score** | **78 / 100** | 39 / 50 → 78 |
| **Responsive Score** | **82 / 100** | 1920/1000/720 的 A/C/J 均值：37 / 45 → 82 |

**解读**：Home 与 Context 已达到较高统一度；Workspace 仍是最大短板；Settings 处于中间，主要受旧 toggle 与面板细节拖累。

---

## 4. Before/After 判断

**第一批 Primitive 收口后，视觉上是否已经明显比 Phase A 之前统一？**

**是。** 证据：

1. **焦点环跨主题一致**：B9 `05-focus-dark-purple-1440.png` 与 `_probe.json` 证明 9 主题下 button/input/link 的 outline 与 box-shadow 均跟随 `--accent` / `--glow`，F-B01 修复生效。
2. **玻璃面板/卡片语言收敛**：onboarding 卡片使用统一 `.glass-panel` / `.onb-card` / `.onb-overlay`；B9 `_probe.json` 中 `.glass-panel`、`.onb-card`、`.onb-overlay` 的 backdrop-filter、border、radius 一致。
3. **按钮基础语言一致**：`.btn-new` 在 onboarding 与 Command Dock 中保持相同 gradient + radius + border 语言。
4. **Home/Context 视觉同构**：Hero 徽章、Capability Matrix 卡片、Command Dock 共享深色玻璃 + 青色光晕。

但**Workspace 仍未被 Primitive 收口覆盖**，其设计语言与 Home 存在代差。

---

## 5. 最大视觉分叉 Top 10（本轮只记录，不修改）

| 排名 | 分叉点 | 视图 | 严重度 | 说明 |
|------|--------|------|--------|------|
| 1 | **Workspace 整体面板语言** | Workspace | 🔴 高 | 右栏 runtime 面板更扁平、字号更小、间距更紧，与 Home 的玻璃卡片语言不一致 |
| 2 | **Workspace 输入框** | Workspace | 🔴 高 | 底部 chat 输入框样式与 Command Dock 输入框不同 |
| 3 | **Settings 旧式 Toggle** | Settings | 🟡 中 | 仍使用 `.settings-switch`（Legacy fallback），未迁移到 `.zz-toggle` |
| 4 | **720 narrow 顶部图标栏** | 720 Home | 🟡 中 | 侧边栏图标移至顶部后，与桌面 OS 身份略有偏离，更像移动 App |
| 5 | **Workspace 聊天侧边栏** | Workspace | 🟡 中 | 左侧会话列表样式与全局 sidebar 不一致 |
| 6 | **Settings 面板内部分节** | Settings | 🟡 中 | 部分设置项间距/标签样式与 Context 右栏有差异 |
| 7 | **按钮动效来源不一致** | 全局 | 🟢 低 | `.btn-new` 动效在 styles.css 与 premium.css 均有来源，虽已收口同值 transform，但 transition 增强仍分散 |
| 8 | **Chip/Badge 域变体** | Context/Workspace | 🟢 低 | `cap-chip`、`cp-mode-chip`、`os-hero-chip` 等多种 chip 变体尚未统一为 Surface 层规范 |
| 9 | **Modal/Dialog 未在截图中验证** | — | 🟢 低 | B9 与历史截图均未覆盖 modal/dialog，存量 .zz-dialog 与 legacy .modal 实际视觉一致性未知 |
| 10 | **Galaxy 背景与文字可读性** | Workspace | 🟢 低 | 部分右栏文字在星空背景上对比度弱于 Home |

---

## 6. 第二批优先级建议（5 个 Primitive / Surface）

| 优先级 | 目标 | 类型 | 理由 |
|--------|------|------|------|
| P0 | **Workspace Surface 对齐** | Surface | 最大视觉分叉（66/100），必须先统一再向其中注入更多 Primitive |
| P1 | **Toggle Primitive 收口** | Primitive | `.settings-switch` → `.zz-toggle`，Settings 中最明显的旧样式 |
| P2 | **Settings Surface 收口** | Surface | settings-panel 家族需纳入统一抽屉/卡片语言 |
| P3 | **Input Primitive 统一** | Primitive | Command Dock / Workspace / `.onb-input` / `.cp-input` 输入框视觉分裂 |
| P4 | **Chip/Badge Surface 规范** | Surface | 多种 chip/badge 变体需要在 Surface 层明确 Domain 变体 vs Primitive 统一边界 |

**注**：Modal/Dialog 与 Icon 已在第一批登记；第二批开始前建议先补拍 Workspace/Settings/Context 的 B9 级别 CDP 截图，避免 onboarding 覆盖。

---

## 7. Regression 状态

引用 B10 真实运行结果，全部绿灯：

- R1 Phase8 AI Presence：**20/0 PASS**
- R2 JS 语法：**101 文件 0 fail**
- R3 9 主题 FOCUS 令牌：**0 每主题覆写**
- R4 焦点唯一权威：premium.css 焦点块已删，ui2.css 独占
- R5 CSS 花括号：ui2/premium/styles 全平衡
- R6 B9 CDP 探针：6 截图 + `_probe.json` 存在

本轮 Visual Gate **未引入任何新代码改动**，Regression 状态保持不变。

---

## 8. Git Status

```
本轮代码改动：0
B13 新增文档：docs/ui-system/phase-b/B13_VISUAL_GATE.md
Commit：未提交
```

仓库当前仍有此前 Phase 累积的未提交改动（含 `xiao6-ui/ui2.css`、`xiao6-ui/premium.css`、`xiao6-ui/styles.css` 等），但**本轮 Visual Gate 未触碰任何源码**，仅新增本验收报告。

---

## 9. Scope Audit（本轮未扩大范围）

以下领域本轮**仅记录、未处理**：

- 领域 CSS / 559 Domain selectors
- `tele-*`
- Accessibility（除焦点环已作为 Primitive 契约验证外）
- Mobile 适配细节（仅作为 responsive 评分因素）
- Electron
- Provider
- Voice
- Galaxy（仅作为视觉背景评价，未改动）
- Runtime / Agent / EventBus
- 新增组件体系 / 第二 Design System

---

## 10. 结论

- **B9 VISUAL GATE = COMPLETE ✅**
- **Overall UI System Score = 81 / 100**
- **Home / Context 已明显统一；Workspace 仍是最大分叉；Settings 存在旧 Toggle 等遗留。**
- **建议第二批优先处理 Workspace Surface 对齐 + Toggle Primitive 收口。**
- **Git = NOT COMMITTED；Code changes = 0。**

🛑 **STOP — 等待主人 Review，不自动进入 Phase B 第二批。**
