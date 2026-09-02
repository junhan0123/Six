# 04 · 世界理解设计（WORLD UNDERSTANDING DESIGN）

> **阶段**：UI-v3 Clean Reconstruction · Phase 1（Design Only）
> **依赖**：`00`（能力来源：galaxy-state 关系投影）/ `01`（Overlay Layer · ⌘4）
> **目标**：把 Galaxy（3D 太阳系）降级为**理解网络**——小6"如何看待你的世界"的 2D 关系信息图。

---

## 1. 为什么 Galaxy 必须走下首屏

来自 v2 审计（`00_CURRENT_SYSTEM_AUDIT.md` 与 `05_GALAXY_ROLE_REDESIGN.md`）的硬事实：

- `solar-system.js` 是**真实 NASA 行星模拟器**（真实轴向倾角/公转周期，海王星 164.8 年），与 AI 语义**零关联**。
- AI 语义节点（goal/agent/task/memory/knowledge）被渲染为 `0x88aaff` 灰蓝小球，推到 `radius 115+` 外围；真实行星占 `13–98` 中心舞台。
- 资源开销：textures 4.7MB + three.module.js 1.27MB ≈ **6MB**，只为背景装饰。
- 用户每天**几乎不用**它——它抢了首屏中央，却对"小6在做什么"毫无贡献。

**结论（v2 已定，v3 沿用）**：天文渲染层**移除**；其**关系投影数据层**（`galaxy-state.js` 的 `relations`）是真资产，**保留并重渲**为理解网络。

---

## 2. 理解网络 = 小6的世界模型（2D）

不是 3D 星系，是**一张 2D 关系信息图**：让小6"看见、并让你看见"它如何理解你的世界——目标、代理、记忆、知识如何相连。

### 2.1 节点类型（取自 galaxy-state 关系投影，语义重映射）
| 节点 | 含义 | 数据来源 |
|---|---|---|
| Goal | 你的目标 | `/api/goals` |
| Agent | 执行代理 | Agent Runtime（既有） |
| Memory | 记住的事 | `/api/memories` |
| Knowledge | 知识文档 | `/api/knowledge` |
| Task | 任务步骤 | Goal 展开（既有） |

### 2.2 边（关系）
- 取自 `galaxy-state.js` 的关系投影（`relations`：goal↔agent、goal↔task、memory↔knowledge 等）。
- **不新增关系计算**；仅把既有投影数据用 2D 力导向/层级图重渲。

### 2.3 视觉
- 极简 2D：节点为小圆点/圆角标签，边为细线（hairline），颜色用 v3 语义色（见 `05`），**不用天文贴图、不用 3D、不用 6MB 资源**。
- 布局：力导向或径向分层，节点可点击展开详情（复用既有 Overlay 机制）。
- 交互：hover 高亮邻域，点击聚焦子图；滚轮缩放、拖拽平移（轻量，非 Three.js）。

---

## 3. 触发方式（不在首屏）

理解网络**不是首页元素**，是 ⌘4 唤起的 **Overlay Layer**（`01` §3 Layer 4）：

- `⌘4` 或 AI Core 周围 Ambient 微点"查看小6如何理解你的世界" → 覆盖层展开。
- 覆盖层浮于 Presence Surface 之上，关闭即回小6面前（同其他 Overlay）。
- **不恢复 Galaxy 首页**：它永远是一个按需深入的视图，不是首屏目的地。

---

## 4. 与旧代码关系

| 旧元素 | v3 处理 |
|---|---|
| `#solarCanvas` + `.galaxy-veil` | 首屏隐藏（不再作背景）；不加载 3D 星系 |
| `solar-system.js` | **不用于首页**；理解网络不依赖 Three.js |
| `galaxy-state.js` 关系投影 | **保留**，取其 `relations` 数据层 |
| `galaxy-runtime.js` / `galaxy-experience.js` | 不带入 v3 首页；理解网络用轻量 2D 渲染替代 |
| `galaxy-experience.js` 叙事纱 | 首屏隐藏 |

> **性能收益**：移除 6MB 天文资源后，首页首屏不再加载 Three.js / 贴图，启动与内存显著改善——这是 v3 的隐性红利。

---

## 5. 理解网络设计原则

- **信息 > 炫技**：图的价值是"看清关系"，不是"好看的天体"。
- **2D 优先**：平面关系图比 3D 星系更易读、更轻、更易交互。
- **按需出现**：默认不在首屏，避免分散"小6是谁/在做什么"的注意力。
- **真实数据**：节点/边全部来自既有 API 与 galaxy-state 投影，零新增数据源。

---

## 6. 验收（理解网络维度）

- [ ] 首屏**没有** 3D 星系 / `#solarCanvas` 背景。
- [ ] `⌘4` 唤起 2D 理解网络覆盖层，关闭即回存在界面。
- [ ] 节点/边来自 `/api/goals`、`/api/memories`、`/api/knowledge`、galaxy-state 关系投影（真实数据）。
- [ ] 无 Three.js / 无天文贴图 / 无 6MB 资源加载。
- [ ] 不产生 Galaxy 首页心智。

→ 下一文档 `05` 详述 v3 视觉设计语言。
