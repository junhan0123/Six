# 02 · Galaxy × Workspace 关系模型（Dual-Layer Re-Evaluation）
### Xiao6 UI-3B · Galaxy × Workspace Experience Design v1.0

> **阶段**：UI-3B · Design Only（0 代码改动）
> **上游**：`00_CURRENT_STATE_AUDIT.md`（真实割裂点 S1–S7）· `02_GALAXY_WORKSPACE_INTEGRATION.md`（方案 C 推荐）· `GALAXY_INTERACTION_SPEC.md`（DECISION_004）
> **生成日期**：2026-08-09

---

## 0. 重评估结论（先给答案）

既有设计（`02_GALAXY_WORKSPACE_INTEGRATION.md`）推荐 **方案 C · 双层空间模型（Dual-Layer Spatial）** 仍然成立，且是**唯一不违反 DECISION_004 的路线**。但基于 `00` 的真实代码审计，本阶段对方案 C 做**关键修正**：

> **原方案 C 的「探索态」被实现成了硬切换的 `#universeView`（universe-mode），这违背了 C 的「连续注意力调节」初衷。** UI-3B 要求把"探索态"从"独立视图"降级/重构为"对世界层的亮度+操作层透明度的连续调节"，并让世界层在 Workspace 下**不再被遮盖**。

即：**保留 Dual-Layer 的世界观，修正其实现落点**——消除 S1（Workspace 遮盖银河）与 S2（银河=独立视图）。

---

## 1. Dual-Layer Spatial Model（终态定义）

```
        Xiao6 OS = 单一连续空间
   ┌───────────────────────────────────────────┐
   │  World Layer（世界层）= Galaxy             │  z 0 → 4
   │   · 太阳=核心 / 轨道=Goal / 星球=能力域    │  始终渲染·暗化常驻
   │   · 只读投影（GalaxyState），零可写状态     │  探索态提亮，操作态暗化
   │                                            │
   │  Operation Layer（操作层）= 前景玻璃元件   │  z 18+ / Panel 81 / HUD 20
   │   · Command Dock / Workspace 内容 / Panel  │  玻璃悬浮·共享语法
   │   · AI Presence（--z-companion 9999）      │
   └───────────────────────────────────────────┘
   两层共存于同一屏幕，注意力模型调节显隐（非硬切）
```

**两层共享同一空间语法**（来自 `01_GLOBAL_LAYOUT_ARCHITECTURE.md §2`）：depth / glass / grid / glow / motion。用户**不切换 App**，而是**调节对世界的注意力**。

---

## 2. World Layer ↔ Operation Layer 的四类流

### 2.1 信息流（Information Flow）
| 方向 | 机制 | 证据/合规 |
|---|---|---|
| World → Operation | GalaxyState 投影 → gx-status/gx-card 展示节点状态（`galaxy-experience.js:78-123`）；HUD 状态点来自 AvatarState 派生 | 只读，DECISION_004 ✅ |
| Operation → World | 用户下达指令 → AppState 领域事件 → GalaxyState 拉取 → solar-system `syncState` 渲染状态节点（`galaxy-state.js:38-59` → `solar-system.js:545-593`） | 单向派生，银河零可写 ✅ |

### 2.2 状态流（State Flow）
- **唯一写入口**：AppState（Single Source Rule）。银河与操作层都是其**只读投影**。
- 聚焦某星球 → `solar-system._publishFocus` 经 `ZZ_EVENTS.FOCUS_CHANGED` 写 AppState.focus（`solar-system.js:610-621`）→ `galaxy-experience` 读 AppState.focus 渲染 gx-card（`galaxy-experience.js:80-91`）。
- **世界层绝不反向持有可写状态**（L0 红线-5 + DECISION_004）。

### 2.3 视觉连接（Visual Connection）
- 共享 glass/accent/glow 令牌（`ui2.css` 9 主题），使前景玻璃与银河氛围同源。
- 探索态提亮世界层时，前景玻璃**降低不透明度 + 增加模糊**，形成「世界浮现、操作退后」的连续感（CSS 表现层，不碰 renderer）。
- 点击星球 → 经 `galaxy-experience._enterCapability` → `PanelManager.openCapability('capabilities')`（`galaxy-experience.js:50-61`）→ 面板在世界层之上滑出。这是 World→Operation 的**视觉桥**。

### 2.4 注意力切换（Attention Switch）
- **操作态（默认）**：世界层暗化（遮罩 ~30% 亮度），操作层全亮。
- **探索态**：世界层提亮（~80%），操作层半透明退后。
- 切换**连续缓动**（`--ease-premium`），由 `body.explore-mode` 类驱动 CSS 过渡；**取消 `#universeView` 独占**（现状 S2 的根因）。

---

## 3. 与现状的关键差异（修正点）

| 维度 | 现状（00 审计） | UI-3B 终态 |
|---|---|---|
| Galaxy 在 Workspace 下 | 被 `.app` 遮盖，不可见（S1） | **始终暗化在场**，不被遮盖 |
| 探索银河 | 切到独立 `#universeView`（S2） | 连续提亮世界层 + 操作层退后（非独立视图） |
| `#universeView` / `universe-mode` | 独立 Surface（index.html:150, 1461） | 降级为「探索态注意力调节」，或保留为可选专注模式但**不切断**与工作台的联系 |
| 两输入通道 | #osDock（Home）+ #input（Workspace）割裂（S3/S7） | Command Dock 永驻统一入口 |
| 银河状态节点 | 中性色 0x88aaff（S5） | 维持中性色（Order 8 属专项，UI-3B 不强制改 renderer） |

---

## 4. 为什么此模型不违反任何红线（合规自检）

- ✅ 银河**零可写状态**：仍是 GalaxyState 只读投影（`galaxy-state.js`, `galaxy-runtime.js`）。
- ✅ **不改 solar-system.js 本体**：世界层可见性/提亮经前景 CSS 遮罩与 `body` 类调节（表现层）；自转/公转/星空/点击聚焦资产 100% 保留（`solar-system.js:78-111`）。
- ✅ **交互全经受控层**：聚焦写 AppState.focus 事件契约（`solar-system.js:610-621`）；点星球开面板经 PanelManager（`galaxy-experience.js:50-61`）。
- ✅ **未新增 Runtime/Memory/EventBus**：注意力态是纯表现层状态，不入 AppState 子树。
- ✅ **未创造新隐喻**：太阳=核心/轨道=Goal/星球=能力域严格沿用 DECISION_004（`GALAXY_INTERACTION_SPEC.md §1`）。

---

## 5. 风险与开放问题（留待 UI-4 实现决策）

1. **`#universeView` 处置**：是彻底移除（合并为探索态）还是保留为「专注探索模式」？UI-3B 建议**合并且取消其独占性**——探索态可在工作台之上叠加，而非替换工作台。需 UI-4 实现时二选一。
2. **状态节点配色（Order 8）**：若要让银河真正「读得出状态」，需改 `solar-system.js` 动态节点着色（非本体天体）。UI-3B 标为**专项评估**，不在此阶段强制，且须单独纪律审查（不违反「不改本体视觉资产」前提下仅改占位节点）。
3. **`.app` 不再遮盖银河的实现**：需将 `.app`/`.os-shell` 前景改为「玻璃浮于银河之上」而非「不透明遮盖」——属 CSS 表现层调整（见 `05_ROADMAP` Phase A）。

> **🛑 STOP 声明**：本章为纯关系设计（重评估 Dual-Layer + 修正落点），0 代码改动，待 Review。
