# 05 · 实现路线图（Implementation Roadmap）
### Xiao6 UI-3B · Galaxy × Workspace Experience Design v1.0

> **阶段**：UI-3B · Design Only（0 代码改动）
> **下游**：UI-4（实现唯一依据）
> **上游**：`04_INTERACTION_FLOW.md` · `03_FIRST_SCREEN_DESIGN.md` · `02_GALAXY_WORKSPACE_RELATION.md` · `01_EXPERIENCE_MODEL.md` · `00_CURRENT_STATE_AUDIT.md`
> **生成日期**：2026-08-09

---

## 0. 目的

本文件是 UI-3B Blueprint 的**实现交付物**，将前 5 份设计文档拆解为 UI-4 可执行的 Phase A / B / C 路线图。每一个 Phase 标注：目标、涉及模块、改动类型、禁止项、验收。

**本文件本身 0 代码改动**——仅规划。

---

## 1. 总体策略

| 维度 | 策略 |
|---|---|
| 设计纪律 | Design Only 已完成；UI-4 才实现 |
| 核心修正 | 消除 surface 硬切换（S1/S2）、Dock 永驻（S7）、单输入语法（S3） |
| 实现次序 | A（消除割裂）→ B（探索态连续 + 信息层级）→ C（可选 Order 8 着色） |
| 红线 | 不碰 solar-system.js 本体语义 / AppState 写入口 / 事件合约 / 后端 |
| 令牌基础 | 复用 UI-3A（Token Activation / R2 / R3）+ UI-A P7 Motion Token |

---

## 2. Phase A — 消除硬切换 + Dock 永驻（核心，必做）

**目标**：让银河在所有态暗化常驻、Dock 永驻、输入统一、空间连续（修正 S1/S2/S3/S7）。

### A1 · 银河在所有态常驻（修正 S1）
- **模块**：index.html 布局合成、CSS（ui2.css / styles.css 加载序）、solar-system.js 渲染保持。
- **改动**：调整 surface 合成，使 `.app`（z-index:2）不再彻底遮盖 `#solarCanvas`（z-index:0）；Workspace 下银河降为暗化背景而非消失。
- **禁止**：改 solar-system.js 渲染逻辑；改银河数据链。

### A2 · 弃用 #universeView 独占视图（修正 S2）
- **模块**：index.html `#universeView`、路由 `openUniverse()`（L1461）/ `galaxy 导航→closeChat(); openUniverse()`（L1508-1509）。
- **改动**：不再切 `universe-mode` 独占；探索态改为连续亮度调节（见 B1）。`#universeView` 可删除或重定向为受控层容器，不再作独立页面。
- **禁止**：新增 surface；保留 `galaxy-experience.js` 受控层职责。

### A3 · Command Dock 永驻（修正 S7）
- **模块**：command-dock.js（build `#osDockBar` L26-36）、CSS 定位（--z-content 18）。
- **改动**：Dock 渲染于所有 surface 底部，探索态半透明退后但不消失。
- **禁止**：新增第二套 Dock 组件。

### A4 · 统一输入语法（修正 S3）
- **模块**：command-dock.js `sendText()`（L17-24）→ legacy `#input`/`#btnSend`；galaxy-experience.js 受控交互。
- **改动**：确保银河受控交互与 Dock 文本共用命令语言与后端入口。
- **禁止**：引入第二命令解析器。

### A5 · 单一连续空间导航脊柱
- **模块**：index.html `syncNav()`（L1484-1493）、`openChat()`（L1454）。
- **改动**：body class 仅表达态（theme/focus），不再互斥 surface。
- **禁止**：新增 surface 切换动词。

**Phase A 验收**
- [ ] Workspace 下银河暗化可见（不消失）
- [ ] 无 `universe-mode` 独占切换
- [ ] 任一 surface Dock 永驻可达
- [ ] 银河交互与 Dock 同命令语言
- [ ] syncNav 不再做 surface 互斥

---

## 3. Phase B — 探索态连续调节 + 信息层级收口

**目标**：实现注意力模型两态（02），收口信息密度（03 §2.5），确认 AI Presence 同源（04 §3.2）。

### B1 · 探索态连续亮度/透明度缓动（注意力模型）
- **模块**：CSS 变量（亮度/透明度）、UI-A P7 Motion Token（缓动，无新体系）。
- **改动**：操作态↔探索态经 CSS 变量插值（银河提亮~80%、操作层退后），非 body class 硬切。
- **触发控件**：由 UI-4 从 §7 候选（A/B/C）中选定（推荐 B 或 A+B）。

### B2 · 信息层级收口（修正低密度）
- **模块**：index.html 右栏（Matrix+Insight，`osContextToggle` L89）、gx-card（galaxy-experience.js:77-123）。
- **改动**：右栏默认收起为抽屉；银河节点信息仅在聚焦时经 gx-card 出现；无标签噪声。

### B3 · AI Presence 两层同源确认
- **模块**：avatar-state.js（派生）、index.html HUD（L85）、Companion（--z-companion 9999）。
- **改动**：确认 HUD 状态点 + Companion 同源（已成立，仅验收确认）。

**Phase B 验收**
- [ ] 探索态为连续缓动，非硬切
- [ ] 默认低密度（右栏抽屉收起）
- [ ] 聚焦才现 gx-card，银河无噪声
- [ ] AI Presence 两层同源显示

---

## 4. Phase C — 可选 · Order 8 状态色专项（Galaxy 节点着色）

**目标**：将 Galaxy 状态节点从占位色 `0x88aaff`（solar-system.js:562）映射为真实状态色（Order 8）。**本 Phase 可选**，若视觉校准风险高可单列。

### C1 · 状态→颜色映射（严格 DECISION_004 边界）
- **模块**：galaxy-runtime.js `mapState()` / `RUNTIME_STATES`（纯数据收敛）、galaxy-state.js（只读投影）、solar-system.js `syncState()`（L545-593 着色）。
- **改动**：`syncState()` 用 `RUNTIME_STATES` 真实色替代占位 `0x88aaff`；`mapState()` 收敛完成。
- **边界（硬）**：仅渲染层颜色映射；**绝不持有可写状态、绝不改 SolarSystem 状态语义、绝不写 AppState**；交互全经受控层。
- **禁止**：扩展 DOMAIN/SYSTEM 事件；新增状态语义。

**Phase C 验收**
- [ ] 状态节点按真实态着色（非占位色）
- [ ] 银河数据链与着色零耦合写入口
- [ ] 回归 Phase 8 AI Presence 20/0 通过

---

## 5. 禁止修改项清单（Hard Forbidden List）

UI-4 实现时**绝对禁止**以下改动（与 00/01/02 红线一致）：

1. **solar-system.js 本体渲染/状态语义**（DECISION_004；Phase C 仅着色层，不碰语义）
2. **AppState 写入口**（必经 `applyEvent`→reducers；Galaxy 只读投影）
3. **事件合约**（DOMAIN=71 / SYSTEM=8 未扩张）
4. **后端 server.py**（UI-3B 纯前端表现层）
5. **Galaxy 直接写状态**（仅经 galaxy-experience.js 受控层）
6. **新建第二 Runtime / Memory / Permission / Design System / Token 体系**
7. **DESIGN.md §7 Don'ts**：禁 styles.css 新增 class / 第二套 class / 内联 style= / 裸 rgba / 改视觉方向

---

## 6. 依赖与前置（Prerequisites）

- [x] UI-3A 已完成：Token Activation / R2 Input Primitive / R3 Spatial Foundation（令牌基础）
- [x] UI-A P7 Motion System（Motion Token 单源，供 B1 缓动）
- [x] DESIGN.md §7 Don'ts（CSS 约束）
- [x] 9 主题全集（ui2.css，默认 dark-cyan，P9 已统一）
- [x] Phase 8 AI Presence 三唯一（HUD/Companion 同源成立）

---

## 7. 风险与开放问题

| 项 | 描述 | 处置建议 |
|---|---|---|
| #universeView 处置 | 现有代码（`index.html:150`）删除 vs 重定向 | UI-4 实现时评估，优先删除独占语义 |
| Order 8 配色 | 状态→颜色视觉校准需真机验证 | Phase C 单列，真机 GUI 验收 |
| `.app` z-index 合成 | 跨浏览器一致性 | A1 实现时 Chrome/Edge 双验 |
| 探索态触发控件 | A/B/C 候选未定 | UI-4 按 UX 决策（推荐 B 或 A+B） |
| Dock 永驻布局 | 小屏（≤980px）Dock 不挤压操作层 | 沿用 03 §4 响应式重排 |

---

## 8. UI-4 验收总表（汇总 00-05）

| 维度 | 关键验收点 |
|---|---|
| 银河常驻 | 所有态暗化可见，不被 `.app` 遮盖（S1） |
| 无硬切换 | 无 `universe-mode` 独占（S2） |
| 单输入 | 银河交互与 Dock 同语言（S3） |
| 布局统一 | 三套布局语法收敛为单连续空间（S4） |
| 状态色 | 可选 Order 8 真实色（S5） |
| 中央视觉 | 银河为唯一世界中心，hero 水印（S6） |
| Dock 永驻 | 所有 surface 底部常驻（S7） |
| 第一屏 | 1s 见世界+工作台，无进入步骤（03） |
| 交互流 | 五大流无页面跳转（04） |
| 注意力 | 操作态↔探索态连续缓动（02/04 §7） |

---

## 9. 角色与交接（Handoff to UI-4）

- 本 Blueprint（00-05 六份文档）为 **UI-4 实现唯一依据**。
- 设计纪律重申：实现须保持「Galaxy = World Layer / Workspace = Operation Layer / 单一连续空间」的心智模型。
- 任何偏离须回到本 Blueprint 复核，不得擅自引入第二体系或改动冻结红线。

**交付物清单（UI-3B）**
```
docs/ui-system/galaxy-workspace-experience/
  00_CURRENT_STATE_AUDIT.md
  01_EXPERIENCE_MODEL.md
  02_GALAXY_WORKSPACE_RELATION.md
  03_FIRST_SCREEN_DESIGN.md
  04_INTERACTION_FLOW.md
  05_IMPLEMENTATION_ROADMAP.md
```

> **🛑 STOP 声明**：UI-3B 全部 6 份设计文档已完成，0 代码改动，0 commit。等待 Review，不进入 Galaxy/Workspace Implementation、Three.js/CSS 修改。最终形成 **Xiao6 Galaxy Workspace Experience Blueprint v1.0** 作为 UI-4 实现唯一依据。
