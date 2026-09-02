# 小6 AI OS · 产品界面架构 v1

> 身份：Senior Product Designer + AI Operating System Architect + Frontend Lead Engineer
> 阶段：架构与设计（本阶段不写代码，代码在架构确认后）
> 状态：v1 — 基于真实能力起草，待补全能力清单后定稿

---

## 0. 工作契约（本版红线）

- **不是**优化旧 UI、**不是**修改旧页面、**不是**继续 v4 / v5。
- 从「系统当前真实能力」出发，设计真正属于 AI OS 的产品界面。
- 所有界面元素必须能映射到真实后端能力；不造假数据、不新增 Runtime / Event、不绕过 EventBus。
- 共享库（`avatar-state.js` / `zz-events.js` / `sse-manager.js` / `intent-gateway.js`）只读引用，不重写。

---

## 1. 核心产品定位

**小6 = 长期陪伴用户的个人 AI 操作系统（Personal AI Copilot OS）。**

用户打开小6的第一感觉：

> 不是「我打开了一个软件」，
> 而是「小6正在这里，我可以直接让它行动」。

**反定位（明确排除）：**
- ❌ 聊天机器人 / ChatGPT clone（无对话气泡、无历史线程）
- ❌ Dashboard（无指标墙、无卡片堆叠）
- ❌ 控制台（无侧边设置树、无管理后台感）
- ❌ 多页面应用（无路由切换、无导航）

小6是一个**持续在场的存在**，用户与之交互的方式是「下达意图 → 看它行动 → 感知状态」，而非「操作一个工具」。

---

## 2. 三大支柱（Architecture Pillars）

### 支柱一 · AI Life Core（系统中心，不是头像、不是装饰）

小6的「生命状态」是整套界面的几何与语义中心，一切围绕它组织。

- **状态维度**：idle / thinking / planning / executing / reflecting / completed / error（权威定义来自 `avatar-state.js` 的 META，颜色与标签唯一来源）。
- **呈现方式**：持续存在的「在场（presence）」——随状态流转的光、呼吸、粒子与微文案；不是一张静态图片，不是吉祥物。
- **结构地位**：AI Core 占据视觉与交互的绝对中心；Command Surface、能力感知层、世界图都「环绕」它。
- **数据驱动**：`/api/agent/state` + SSE（`agent_state` 等系统事件）实时驱动 8 态流转。

### 支柱二 · Command Surface（唯一入口，不是聊天框）

用户唯一的主动交互面，是「行动面」而非「对话面」。

- **形态**：单条自然语言意图入口（不是多轮聊天窗）。用户输入一句意图，小6理解并执行。
- **链路**：用户输入 → Intent Gateway（`/api/agent/intent`）→ Goal → Agent Runtime。
- **示例意图**：「分析我的项目」 / 「整理今天任务」 / 「检查电脑状态」 / 「搜索资料」。
- **反馈回归**：执行结果不堆成对话，而是回到 Life Core 状态与能力感知层（目标、记忆、世界图等）。
- **不用聊天框的原因**：聊天框暗示「来回对话」，而小6是「下指令—看行动」的 OS 范式。

### 支柱三 · 能力即状态 / 感知（不是菜单、不是按钮墙）

所有真实系统以「活的状态」环绕 Core 呈现，而不是被收纳进导航或功能列表。

- **常态感知**：当前目标、近期记忆、世界态势、主动提醒等，以低密度、常驻的「状态碎片」浮在 Core 周边。
- **深度查看**：`⌘1–5` Overlay（Memory / Knowledge / Goals / World / Settings）用于展开细节，数据全部真实。
- **原则**：用户先「感知到小6在做什么 / 能做什么」，再决定是否深入；而不是面对一排需要学习的按钮。

---

## 3. 真实能力 → UI 映射

> 基础事实来自 `00_CAPABILITY_AUDIT.md`（已审计后端真实能力）。下表为 UI 落点，非端点清单。

| 能力 | 真实后端（审计结论） | UI 落点 |
|---|---|---|
| **AI Core** | agent_runtime 状态机 + `/api/agent/state` + SSE | 支柱一 Life Core（系统中心） |
| **Intent** | Intent Gateway + `/api/agent/intent` | 支柱二 Command Surface（唯一入口） |
| **Goal** | `goals.py` + `/api/goals`、`/api/tasks` | 当前目标 / 正在做什么（状态层） |
| **Memory** | `memory.py` + `/api/memories`、`/api/memories/graph` | ⌘1 + 上下文感知碎片 |
| **Knowledge** | `knowledge.py` + `/api/knowledge` | ⌘2 |
| **Tools** | `tools.py`（TOOLS 列表） | 执行态微显示（「正在调用 X」） |
| **Voice** | `asr.py` + `wakeword.py` + `/api/asr` | Voice Core 5 态（idle/listening/thinking/speaking/error） |
| **World** | devices / context + `/api/devices` 等 | 2D World Understanding Graph |
| **Comm** | （审计待补） | 状态层轻提示（待你定义） |
| **Proactive** | 主动推送事件 | 状态层轻提示，非弹窗轰炸 |
| **System** | `/api/health`、`/api/ready` | 顶栏在线 / 就绪指示 |

---

## 4. 明确不做（Anti-Patterns）

- 不做聊天框、对话气泡、历史线程。
- 不做左侧导航、Dashboard、控制台、多页面 / 路由切换。
- 不造假数据；不新增 Runtime / Event；不绕过 EventBus。
- 不「优化」`final/` / v4 / v5 —— 而是按真实能力从零定义界面语言。

---

## 5. 下一步

1. **补全能力清单**：你被截断的部分（Goal 示例 + Memory / Knowledge / Tools / Voice / World / Comm / Proactive / System 的具体 UI 要求）贴出后，我将据此定稿。
2. **定稿架构**：产出最终「AI OS 界面系统规范」（含布局、状态机、Command Surface 交互、感知层、Overlay、World Graph、动效与配色令牌）。
3. **实现**：架构确认后再进入代码（独立重建，不污染旧目录）。

> 注：此前 `DESIGN_FINAL.md` 的 One Space / Life Core / Command Surface / ⌘1–5 思路与本版方向一致，但本版以「产品 / OS」层级重新定义，旧文档仅作参考，不作为实现约束。
