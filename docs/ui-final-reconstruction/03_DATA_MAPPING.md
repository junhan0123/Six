# 小6 AI OS · 最终界面数据映射说明

> 只读消费既有 API，不新增表、不新增接口、不修改后端。

---

## 1. 后端接口清单

| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/agent/state` | GET | Agent 运行/状态/当前目标 |
| `/api/goals` | GET | 目标列表 |
| `/api/memories` | GET | 记忆列表 |
| `/api/knowledge` | GET | 知识文档与统计 |
| `/api/capabilities` | GET | 系统能力清单 |
| `/api/tasks` | GET | 任务列表（含执行步骤） |
| `/api/devices` | GET | 设备/世界视图 |
| `/api/asr/status` | GET | ASR 是否可用 |
| `/api/asr` | POST | 后端语音识别（二进制音频） |
| `/api/agent/intent` | POST | 投递用户意图 |
| `/api/stream` | SSE | 实时事件：agent_state、wakeword_detected 等 |

---

## 2. 字段映射表

### 2.1 Agent 状态

| UI | 字段 | 来源 |
|---|---|---|
| 当前状态色/标签 | `agent.state` | `/api/agent/state` → `AvatarState.META[state].color/label` |
| 在线/停用指示 | `agent.enabled`, `agent.running`, SSE state | `/api/agent/state` + ZZSSE |
| 当前目标 | `agent.current_goal` 或 `activeGoal.title` | `/api/agent/state` / `/api/goals` |

**状态归一化**：后端状态字符串统一转大写；不在 8 态表中的回落为 `IDLE`；`disabled` 映射为 `OFFLINE`。

### 2.2 资源统计（顶部 + 侧边徽章）

| UI 字段 | 映射 | 备注 |
|---|---|---|
| 记忆 | `memories.length` | `/api/memories` 数组 |
| 知识 | `knowledge.docs.length` | `/api/knowledge.docs` |
| 目标 | `goals.length` | `/api/goals` 数组 |
| 工具 | `capabilities.length` | `/api/capabilities.items` |

### 2.3 执行进度（右侧面板）

| UI | 映射 | 备注 |
|---|---|---|
| 目标标题 | `activeGoal.title` | 优先进行中 + 有进度 |
| 目标描述 | `activeGoal.description` + `priority` + `status` | 组合显示 |
| 进度条 | `activeGoal.progress` | 0-100 |
| 步骤列表 | `tasks` 中 `note` 包含「来自目标 #N」 | 按 `id` 排序 |
| 步骤状态 | `task.status`, `task.current_step` | `done/closed` → completed；`current_step>0` → running；其余 pending |
| 步骤详情 | `task.steps[]` 合并为 tooltip | 鼠标悬停显示 |

**关键规则**：执行步骤绝不写死；若目标无关联任务，显示空态。

### 2.4 小6理解的你（底部三卡片）

| 卡片 | 映射 | 排序 |
|---|---|---|
| 我记得 | `memories[].title/content` | `salience` 降序 |
| 我了解 | `knowledge.docs[].title` | `mtime` 降序 |
| 我关注 | `goals[].title + progress` | 优先进行中，再按进度降序 |

### 2.5 能力覆盖层

| 类型 | 数据源 | 渲染 |
|---|---|---|
| memory | `snapshot.memories` | 卡片：标题 + 内容 + 标签 |
| knowledge | `snapshot.knowledge.docs` | 按 `domain` 分组卡片 |
| goals | `snapshot.goals` + `snapshot.tasks` | 卡片：标题 + 进度条 + 关联任务数 |
| world | `snapshot.devices` | 设备卡片：在线状态 + UA + 最后活跃 |
| tools | `snapshot.capabilities` | 能力卡片：描述 + 触发词 |
| settings | `snapshot.agent` + SSE + ASR | 只读状态 + TTS/动效开关（前端偏好） |

---

## 3. 目标 ↔ 任务关联

后端未提供显式外键，但通过 `task.note` 中的固定文本关联：

```text
来自目标 #N 拆解 | suggested_tool=... args=...
```

映射函数（`data-bridge.js`）：

```js
var GOAL_REF = /来自目标\s*#(\d+)/;
function goalIdOfTask(task) {
  var m = GOAL_REF.exec(String(task && task.note || ''));
  return m ? Number(m[1]) : null;
}
```

**示例验证数据**：
- 目标 #5（active，progress=83）关联任务 6-11，共 6 个任务。
- UI 渲染：标题「总结当前项目状态」，进度 83%，步骤 6 条，第一条「获取当前目标列表」。

---

## 4. SSE 事件映射

| SSE 事件 | 用途 | UI 行为 |
|---|---|---|
| `agent_state` | Agent 状态变化 | 刷新快照，更新核心/面板 |
| `wakeword_detected` | 唤醒词触发 | `FinalVoice.start()`，高亮聆听中 |
| `proactive` | 主动推送/结果摘要 | `FinalVoice.speak(text)` 朗读 |

SSE 事件名来源：`../zz-events.js` 中 `SYSTEM_EVENTS`。

---

## 5. 语音链路映射

| 用户动作 | 前端处理 | 后端/浏览器接口 |
|---|---|---|
| 点击麦克风 | `FinalVoice.toggle()` | `/api/asr/status` 决定后端或浏览器 ASR |
| 按住空格 | `start()` | 同上 |
| 听到唤醒词 | SSE `wakeword_detected` → `start()` | 后端唤醒事件 |
| 识别中 | 中间文本填入 `#intentInput` | `SpeechRecognition.onresult` |
| 识别完成 | `FinalIntentBar.submit(text)` | `POST /api/agent/intent` |
| 服务端结果 | `proactive` SSE | `speechSynthesisUtterance` TTS |

---

## 6. 不落地为数据的内容

以下仅作为视觉/交互元素，**不写、不读、不改后端**：

- 设置面板里的 TTS 开关、降低动效开关 → 仅 `localStorage` + 前端 CSS class。
- 快捷操作按钮 → 直接调用 `FinalIntentBar.submit()` 或 `FinalOverlay.open()`。
