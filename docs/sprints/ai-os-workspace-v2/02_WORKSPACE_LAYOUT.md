# 02 — Workspace Layout（六层信息架构）

> Sprint #618 · 定义 Primary / Secondary / Assistant / Context / Background / Overlay 六层。
> 纪律：**不新增页面**，仅对既有容器做信息架构分类与 `data-ws-layer` 标注。

## 1. 六层定义

| 层 | 职责 | 既有承载 | 持久性 |
|----|------|----------|--------|
| **Primary** | 主任务流（对话 / 执行） | `.app` 对话抽屉 / `#osCoreCanvas` / `#osTimeline` / `#osDock` | 始终存在 |
| **Secondary** | 侧弹面板（能力详情） | `#zzPanel` 共享宿主 + 14 个独立面板 | 按需唤出 |
| **Assistant** | 常驻 AI 伴侣 | Companion（`companion-bubble` 等，**独立治理**） | 常驻浮层 |
| **Context** | 情境侧栏（洞察 / 状态） | `#osInsight`（InsightPanel）/ HUD / Glance | 常驻或按需 |
| **Background** | 氛围 / 宇宙背景 | `#solarCanvas`（太阳系）/ 星空 | 始终存在 |
| **Overlay** | 模态 / 指令 / 菜单 | 20 个 `OverlayManager.track` 浮层 | 栈式，中央 ESC |

## 2. 层映射原则（对齐 Product Constitution §07 信息架构 L1–L6）

- **L1 首页（Home）** → Primary + Background。
- **L2 工作台（Workspace）** → Primary（对话）+ Secondary（面板）。
- **L3 指令中心（Command）** → Overlay（COMMAND 类型，`command-palette`）。
- **L4 星图（Galaxy）** → Background 扩展（宇宙视图，**不在本 Sprint 范围**）。
- **L5 Assistant（语音/Companion）** → Assistant 层。
- **L6 设置（Settings）** → Secondary（settings 面板）。

## 3. `data-ws-layer` 标注（具体落地，additive markup）

为让布局可工具化、可校验，向稳定容器注入 `data-ws-layer` 属性（纯标记，零行为）：

| 容器（index.html / 模块） | `data-ws-layer` |
|---------------------------|-----------------|
| `#solarCanvas` | `background` |
| `.app`（对话抽屉根） | `primary` |
| `#osCoreCanvas` / `#osTimeline` / `#osDock` | `primary` |
| `#osInsight` | `context` |
| Companion 根（Electron 渲染进程，前端仅事件桥） | `assistant` |
| `.zz-panel` / 各独立面板根 | `secondary` |
| `.zz-overlay` / `OverlayManager` 浮层 | `overlay` |

> 实施说明：Background / Primary / Context 容器集中在 `index.html` 与各模块根节点；Companion 属独立渲染进程，仅在前端事件桥标注语义，不扩张其职责。标注动作属纯 HTML 属性增量，不触发任何行为变更。

## 4. 布局纪律（红线）

- **禁止**为"统一工作空间"新增独立页面 / 路由 / 第二导航树。
- 六层为**分类视图**；物理 DOM 结构不变，仅加语义标注。
- Overlay 层继续由 `OverlayManager` 唯一掌管（栈 / ESC / 焦点 / z-index），不回退到散落监听。

> 下一步：#619 Panel Governance（统一生命周期管理器）。
