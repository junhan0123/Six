# 小6 AI OS · 最终界面组件说明

> 所有组件位于 `xiao6-ui/final/components/`，全局挂载在 `window` 上供 `boot.js` 调度。

---

## 1. FinalData（js/data-bridge.js）

**类型**：数据聚合层  
**职责**：只读消费既有 API，输出单一 `snapshot`。

```js
FinalData.fetchSnapshot() -> Promise<{
  agent: { enabled, state, running, queue, current_goal, failures, raw },
  goals: Array,
  activeGoal: Object|null,
  execSteps: Array<{id,label,status,current,total,detail}>,
  memories: Array,
  knowledge: { docs: Array, stats },
  capabilities: Array,
  tasks: Array,
  devices: Array,
  stats: { memory, knowledge, goals, tools, tasks }
}>
```

**关键规则**：
- `activeGoal` 优先选「进行中 + 已有进度」的目标。
- `execSteps` 必须由 `/api/tasks` 通过 `note` 中「来自目标 #N」关联真实目标，**禁止写死步骤**。

---

## 2. FinalState（js/state.js）

**类型**：单一状态源  
**职责**：持有当前快照、分发订阅、SSE 触发刷新。

| API | 说明 |
|---|---|
| `FinalState.subscribe(cb)` | 订阅快照；首次立即回调当前快照 |
| `FinalState.get()` | 取当前快照 |
| `FinalState.refresh()` | 手动触发 API 聚合 |
| `FinalState.initSSE()` | 监听 `agent_state` / `wakeword_detected` 事件 |

轮询周期：30 秒。SSE 到达时立即刷新。

---

## 3. FinalAICore（components/ai-core.js）

**DOM**：`#aiCore`（680×680 居中容器）  
**职责**：把 Agent/语音状态转化为视觉生命感。

| API | 说明 |
|---|---|
| `setState(state)` | 根据 `AvatarState.META` 设置 `--core-color`、文字、引语 |
| `setVoice(mode)` | 设置 `data-voice` 属性，影响脉冲 |
| `setVoiceLevel(0..1)` | 真实 RMS 电平，驱动波形振幅 |

**视觉层**：
- SVG 三环（外环能量、中环呼吸、内环轨道）
- Canvas 粒子（随状态色旋转）
- Canvas 波形（仅在活动/语音时绘制，叠加电平）

---

## 4. FinalStatePanel（components/state-panel.js）

**DOM**：`#stateList`（8 行状态行）  
**职责**：高亮当前 Agent/语音状态对应行。

| API | 说明 |
|---|---|
| `update(state)` | Agent 状态变化时调用 |
| `setVoice(mode)` | 语音态变化时调用 |

语音态优先级高于 Agent 态：listening/thinking 时总是高亮「聆听中」。

---

## 5. FinalExecutionPanel（components/execution-panel.js）

**DOM**：`#execPanel`  
**职责**：渲染当前目标 + 真实进度 + 真实任务步骤。

| API | 说明 |
|---|---|
| `render(snapshot)` | 用 `snapshot.activeGoal` 与 `snapshot.execSteps` 刷新 |

空态显示：「该目标尚未拆解出任务」。

---

## 6. FinalUnderstanding（components/understanding.js）

**DOM**：`#underMemory` / `#underKnowledge` / `#underGoals`  
**职责**：三张「小6理解的你」卡片，分别展示记忆/知识/目标。

- 我记得：按 `salience` 降序取前 3 条记忆标题/内容。
- 我了解：按 `mtime` 降序取前 3 篇知识标题。
- 我关注：优先进行中目标，按进度降序取前 3 个。

---

## 7. FinalIntentBar（components/intent-bar.js）

**DOM**：`#intentForm` / `#intentInput`  
**职责**：唯一意图入口。

| API | 说明 |
|---|---|
| `submit(text)` | 投递意图到 `ZZIntentGateway.dispatch` 或 `POST /api/agent/intent` |
| `focus()` | 聚焦输入框 |

投递成功后 0.4s / 1.8s 各刷新一次快照，使状态与进度实时跟上。

---

## 8. FinalVoice（components/voice-core.js）

**DOM**：`#intentMic` / `#voiceHint` / `#intentInput`  
**职责**：真实语音链路。

| API | 说明 |
|---|---|
| `init()` | 探测 ASR、订阅唤醒词、绑定快捷键 |
| `start()` | 开始听 |
| `stop()` | 结束听 |
| `toggle()` | 切换听/停 |
| `speak(text)` | TTS 朗读 |
| `setTTS(bool)` | 开关语音播报 |

**通道选择**：
1. `GET /api/asr/status` → `enabled=true`：后端 ASR（`MediaRecorder → POST /api/asr`）
2. 否则：浏览器 `SpeechRecognition(zh-CN)` 兜底
3. 若均不可用：显示错误态并提示文字输入

**唤醒**：SSE `wakeword_detected` 自动触发 `start()`。

**麦克风电平**：通过 `AnalyserNode` 计算 RMS，调用 `FinalAICore.setVoiceLevel()`。

---

## 9. FinalSideNav（components/side-nav.js）

**DOM**：`#sideNav`  
**职责**：左侧能力导航，打开覆盖层。

| API | 说明 |
|---|---|
| `update(snapshot)` | 刷新 memory/knowledge/goals 徽章 |
| `setActive(name)` | 设置当前选中项 |

快捷键：`1-6` 分别打开 memory/knowledge/goals/world/tools/settings。

---

## 10. FinalTopBar（components/top-bar.js）

**DOM**：`#topbar`  
**职责**：资源计数 + 在线指示 + 时钟。

- 资源来自 `snapshot.stats`。
- 在线状态由 SSE 连接状态与 Agent 运行状态共同决定：
  - SSE 断开 →「连接中断」
  - Agent 停用/未运行 →「已停用 / 未运行」
  - 正常 →「在线」

---

## 11. FinalOverlay（components/overlay-system.js）

**DOM**：`#overlay`  
**职责**：在同一空间上浮出能力详情，不是新页面。

支持类型：`memory` `knowledge` `goals` `world` `tools` `settings`

| API | 说明 |
|---|---|
| `open(type)` | 打开并渲染对应能力 |
| `close()` | 关闭 |
| `refresh(snapshot)` | 覆盖层打开时自动同步最新数据 |

---

## 12. ViewportScale（js/viewport-scale.js）

**职责**：计算 `--ui-scale` 并写入 `:root`。

```js
scale = Math.min(window.innerWidth / 1920, window.innerHeight / 1080)
```

配合 CSS 的 `transform: translate(-50%, -50%) scale(var(--ui-scale))` 实现任意窗口下 16:9 锁定。
