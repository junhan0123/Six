# ARCHITECTURE_MAP.md

> 系统架构地图 | Xiao6 v1.0
> 绘制完整系统的模块职责、禁止事项与数据方向。配合 `AI_HANDOFF_PROTOCOL.md` 与 `docs/decisions/` 使用。

## 1. 系统总览（数据流）

```
User
  │ (输入/语音/文本/意图)
  ↓
Intent Gateway ──────────────┐
  │                          │
  ↓                          │
Goal System                  │
  │ (Goal 生成/更新)         │
  ↓                          │
Agent Runtime ◀──────────────┘ (目标驱动)
  │ (唯一决策运行时)
  ↓
Capability Registry ──→ Permission Guard ──→ Computer Action ──→ Executor ──→ Verification
  │                                  ↑                                  │
  │                                  │ (权限否决)                         ↓
  │                          Computer World Model ←──────────────────────┘ (执行结果回填)
  │
  ↓ (消费观察)
Perception Layer (Capture / UIA / OCR / Vision / Fusion)
  │  PERCEPTION_* 事件
  ↓
Computer World Model ◀────── (富化 World Model)

Memory System ──→ (供给 Agent / Context Engine)
Context Engine ──→ (汇编 ContextPackage 供 Agent Runtime)
Reflection ─────→ (每轮后 Context Update 事件)

EventBus ◀──────────── (所有状态变化经此)
  │
  ↓
AppState (唯一写入口) ──→ Galaxy State / Overlay Runtime / Computer State / Perception State (只读投影)
  │
  ↓
Renderer (Galaxy Three.js / UI)
```

## 2. 模块清单（职责 / 禁止 / 数据方向）

### 用户与意图
| 模块 | 职责 | 禁止事项 | 数据方向 |
|------|------|----------|----------|
| Intent Gateway | 接收用户输入（语音/文本/命令），归一化为意图 | 不得直接执行动作 | User → Goal |
| Goal System | 管理 Goal 生命周期（创建/更新/完成） | 不得绕过 Agent 直接执行 | Intent → Agent |

### 决策与执行
| 模块 | 职责 | 禁止事项 | 数据方向 |
|------|------|----------|----------|
| **Agent Runtime** | **唯一决策运行时**：Goal → Capability → Executor 编排；REFLECTING 阶段发 `REFLECTING` + `reflect()` | 不得成为第二 Runtime；不得被状态层调用 | Goal → Capability → Executor |
| Capability Registry | 单一能力目录（computer/knowledge/memory/automation/analysis），含 risk 分级 | 不得含 OS 调用；不得自判权限 | Agent → Permission |
| Permission Guard | **唯一权限闸门**，校验 Computer Action | 不得被绕过；不得下放决策 | Capability → Action |
| Computer Action | 动作数据结构（鼠标/键盘/应用等） | 不得自行执行 | Permission → Executor |
| Executor | 执行已授权动作 | 不得绕过 PermissionGuard；不得写 AppState | Action → World Model |
| Verification | 动作后验证闭环（复用 Perception 只读快照） | 不得新增第二 Verification | Executor → World Model |

### 观察层（Perception）
| 模块 | 职责 | 禁止事项 | 数据方向 |
|------|------|----------|----------|
| Capture Runtime | 截屏采集（仅采集，不含理解） | 不得识别/理解 | Screen → Perception |
| UIA Provider | UI 自动化树（仅观察） | 不得操作控件 | Desktop → Fusion |
| OCR Provider | 整屏/区域文字识别 | 不得控制 | Frame → Fusion |
| Vision Provider | 图像理解（只读 Observation） | **绝不控制电脑** | Frame → Fusion |
| Semantic Fusion | 融合 UIA+OCR+Vision 为 PerceptionModel（禁推理/规划） | 不得产出 Action | → Perception Runtime |
| Perception Runtime | EventBus 生产者（发 PERCEPTION_* + COMPUTER_WORLD_SYNC） | **非第二 Runtime**；不得构造 Action | → World Model / EventBus |

### 状态与事件
| 模块 | 职责 | 禁止事项 | 数据方向 |
|------|------|----------|----------|
| **EventBus** | **唯一事件通信**（DOMAIN 71 / SYSTEM 8，前后端逐字对齐） | 不得引入第二事件总线；未知名抛 ValueError | 全局 |
| **AppState** | **唯一状态写入口**（applyEvent → reducers，11 子树） | 不得被投影层回写 | EventBus → State |
| Galaxy State | 银河可视化只读投影 | 不得写 AppState | AppState → Render |
| Overlay Runtime | 叠加层只读投影 | 不得写 AppState | AppState → Render |
| Computer State | 电脑状态只读投影 | 不得写 AppState | AppState → Render |
| Perception State | 感知状态只读投影 | 不得写 AppState | AppState → Render |

### 记忆与上下文
| 模块 | 职责 | 禁止事项 | 数据方向 |
|------|------|----------|----------|
| Memory System (`memory.py`) | **唯一记忆来源**（短期/工作/长期/项目/知识分层） | 不得建第二 Memory | → Agent / Context |
| Context Engine (Phase 9) | 汇编 ContextPackage 供 Agent | 不得新增决策 Runtime | Memory/Workspace/State → Agent |
| Reflection | 每轮后发 Context Update 事件 | 不得越权执行 | Agent → Context |

### 视觉
| 模块 | 职责 | 禁止事项 | 数据方向 |
|------|------|----------|----------|
| Galaxy (Three.js) | 太阳系可视化（表现层） | 不得持有业务状态；不得改银河本体 | Render-only |

## 3. 红线速查

- 决策唯一在 **Agent Runtime**；观察不决策（Perception/Vision）。
- 状态唯一在 **AppState**；投影层只读。
- 事件唯一在 **EventBus**；权限唯一在 **Permission Guard**。
- 记忆唯一在 **memory.py**。
- Vision 永远 **Observation，不 Control**。

> 决策依据见 `docs/decisions/DECISION_001_EVENTBUS.md` … `DECISION_006_LANGCHAIN_POSITION.md`。
