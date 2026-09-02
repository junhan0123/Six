# Xiao6 AI OS — UI Component Library

> 先建立组件库，再应用于主界面。本文件是 `final-v2` 全部可复用组件的**权威规范**。
> 动效理念借鉴 Uiverse 的开源精神（Loader / Orbit / Particle 的纯粹化表达），但所有组件均为本项目自研，不复制任何网页组件。

## 0. 设计令牌（唯一真源：`final-v2/css/tokens.css`）

| Token | 值 | 用途 |
|---|---|---|
| `--bg-0` | `#07080b` | 虚空背景 |
| `--bg-1` / `--panel` | `#0d1016` | 面板底 |
| `--panel-solid` | `#0a0c11` | 弹层实底 |
| `--border` / `--border-strong` | `rgba(255,255,255,.07)` / `.14` | 发丝边 |
| `--text-1` / `--text-2` / `--text-3` | `#e9edf2` / `#aab2bd` / `#79828f` | 文字层级 |
| `--accent` | `#34d9d2` | OS 交互主色（冷青，非紫非蓝紫渐变） |
| `--core-color` / `--core-color-2` | 由 `AvatarState.META` 注入 | **8 态唯一颜色权威**（仅外环使用） |
| `--font` | `Sora` | 显示/UI |
| `--font-mono` | `JetBrains Mono` | 遥测/状态码 |
| `--ease` | `cubic-bezier(.22,1,.36,1)` | 统一缓动 |
| `--ui-scale` | 由 `viewport-scale.js` 注入 | 1920×1080 等比缩放 |

**铁律**：状态色只出现在能量环与状态读数上；界面主题保持中性深空，杜绝紫/蓝紫渐变背景。

## 1. 组件清单与 API

### 1.1 `ZZEnergyRing` — Hybrid Energy Ring（AI Core 外环）
*文件：`js/energy-ring.js`* · 4 层，对应 Uiverse 的 **Loader + Orbit + Particle**：

| 层 | 实现 | 8 态行为 |
|---|---|---|
| L1 Outer Aura | CSS `radial-gradient` + blur | 随 `--core-color` 呼吸 |
| L2 Energy Ring | SVG 3 圆环（status/voice/progress） | 颜色、转速、旋转方向随态变化 |
| L3 Particle | Canvas | IDLE 漂浮 / THINKING 向心聚集 / EXECUTING 向外释放 / LISTENING 声波 |
| L4 Audio Reactive | Canvas | 麦克风 RMS 驱动半径与亮度 |

```js
ZZEnergyRing.setState(state8)            // IDLE|WAITING|THINKING|PLANNING|EXECUTING|COMPLETED|ERROR|OFFLINE
ZZEnergyRing.setProgress(0..1)
ZZEnergyRing.setAudioActive(bool)        // 开启麦克风分析
ZZEnergyRing.setAudioLevel(0..1)        // 实时 RMS
ZZEnergyRing.setVoice('idle|listening|thinking|speaking')  // 语音态反射
```

### 1.2 `ZZVoiceCore` — Voice Core（聆听 / 思考 / 播报）
*文件：`components/voice-core.js`* · 5 态 `idle/listening/thinking/speaking/error`
- 优先后端 `/api/asr`（MediaRecorder 上传），降级浏览器 `SpeechRecognition(zh-CN)`
- `wakeword_detected` SSE → 自动聆听
- 聆听期间实时 RMS 喂给 Energy Ring L4

```js
ZZVoiceCore.init()  ZZVoiceCore.start()  ZZVoiceCore.stop()
```

### 1.3 `ZZCapabilityMatrix` — Capability Matrix（5 个 OS 层）
*文件：`components/capability-matrix.js`* · **Goal / Memory / Knowledge / Tools / Runtime**
- 每层实时状态来自真实 `ZZState` 快照，绝不造假
- 点击展开该层真实条目详情（目标标题 / 记忆文本 / 知识标题 / 工具名 / 运行时态）

```js
ZZCapabilityMatrix.build()   // 首次构建
ZZCapabilityMatrix.render(snapshot)  // 快照更新时刷新实时状态
```

### 1.4 `ZZExecutionTimeline` — Execution Timeline（Agent Runtime 可视化）
*文件：`components/execution-timeline.js`* · 七段管道：
`Input → Intent → Goal → Planner → Executor → Reflection → Complete`
- 当前阶段由真实 `agent_state` 映射高亮，进度线填充
- 非任务列表，而是「小6正在怎么做」的过程透明

```js
ZZExecutionTimeline.setStage(index0to6, currentLabel)
```

### 1.5 `ZZCommandSurface` — Intent Surface（AI Command Surface）
*文件：`components/intent-surface.js`* · 底部唯一入口，**非聊天框**
- 文字提交 / 语音（接入 Voice Core）/ 文件拖入
- 统一经 `ZZIntentGateway.dispatch(text)` → `POST /api/agent/intent`

```js
ZZIntentSurface.submit(text)
```

### 1.6 `ZZContextLayer` — Context Layer（小6现在知道）
*文件：`components/context-layer.js`* · 自然语言呈现 Memory/Knowledge/WorldModel，**无数字统计**

```js
ZZContextLayer.render()
```

### 1.7 `ZZAICore` — 编排器
*文件：`components/ai-core.js`* · 把真实 `agent_state` 映射为 `AvatarState` 8 态，驱动 Energy Ring + 读数 + Timeline + Voice 反射。

## 2. 主界面布局（5 区域，1920×1080 固定 + scale）

```
┌──────────────────────── TOP BAR（品牌 · 在线 · 时钟）────────────────────────┐
│ LEFT: Context Layer   │      CENTER: AI Core (Energy Ring)      │ RIGHT: Execution │
│ 小6现在知道           │       Avatar + 8态光环 + 状态读数        │ Timeline +       │
│ (自然语言)            │                                          │ Capability Matrix│
├───────────────────────┴─────────── INTENT SURFACE (Command) ──────────────────┤
│ 文字 / 语音 / 文件拖入 → Intent Gateway                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```
- 禁止：左侧后台菜单、多栏 Dashboard、普通聊天窗、数据卡片堆叠。
- 任意窗口尺寸下 `transform: scale(var(--ui-scale))` 保持 1:1 布局不变。

## 3. 数据来源（真实后端，无假数据）

| 组件 | 接口 |
|---|---|
| AI Core / Timeline | `/api/agent/state` + SSE(`agent_state`) |
| Capability: Goal | `/api/goals` |
| Capability: Memory | `/api/memories` |
| Capability: Knowledge | `/api/knowledge` |
| Capability: Tools | `/api/capabilities` |
| Capability: Runtime | `/api/health` + `agent_state` |
| Context | `/api/memories` `/api/knowledge` `/api/devices` |
| 主动/领域事件 | SSE（domain 嵌套 payload / system 扁平） |

## 4. 纪律
- 不新增 Runtime / Event；不绕过 EventBus；SSE 信封按 `eventbus.py` 契约解析。
- 共享库 `../avatar-state.js` 等只读引用，8 态颜色权威唯一来自 `AvatarState.META`。
- 所有动画 `prefers-reduced-motion` 友好；单次高光动效优先，避免零散微交互堆叠。
