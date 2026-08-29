# 07 · 能力关系图（Capability Graph）— Stage G

> 建立能力间依赖/数据流关系。横切关注：Execution 是唯一执行入口，EventBus 是唯一事件总线，PolicyEngine 是唯一权限。

---

## 一、主链路（核心闭环）

```
User(输入)
  │  (UI: index.html / companion / command-palette / 快捷键)
  ▼
Conversation(CONV-01 对话闭环 / CONV-02 意图)
  │  run_fc_loop → select_tools(依赖 CONV-02 意图裁剪)
  ▼
Context(CTX-01 引擎)  ←── 组装自下列"源"
  ├─ CTX-03 MemorySource  ← Memory(MEM-01..10)
  ├─ CTX-04 UserModelSource ← cognitive/user_model
  ├─ CTX-05 EpisodicSource ← cognitive/episodic(embed.py)
  ├─ CTX-06 PersonalitySource ← Personalization(PERS-01/02)
  ├─ CTX-07 KnowledgeSource ← Knowledge(KNOW-01..08)
  └─ CTX-08 GoalSource ← Goals(GOAL-01..03)
  │
  ▼  (LLM function-calling)
Intent → Goal(GOAL-05 意图网关 → GOAL-04 GDE → GOAL-01 建目标)
  │
  ▼
Execution(EXEC-01 run)  ←══ 全 OS 唯一执行入口 ══
  ├─ EXEC-08 ExecutionPolicy → Permission(PERM-01 PolicyEngine / PERM-02 PermissionGuard)
  ├─ EXEC-02 execute_tool → Tools(TOOL-01..62)
  │     ├─ Tools → Knowledge / Memory / External / Social / Computer …
  │     ├─ Computer(COMP-01..06) → PermissionGuard → ComputerExecutor
  │     └─ Goals(GOAL-07 任务执行) → Tools
  ├─ EXEC-05 Queue / EXEC-04 Session / EXEC-06 State / EXEC-09 Metrics
  ├─ EXEC-07 Event → EventBus(SYSTEM 通道)
  └─ EXEC-11 Reflection → 本地 jsonl(非 Memory/Knowledge)
  │
  ▼
Knowledge(KNOW) / Memory(MEM) / Context(CTX)  ←── 写回(经验沉淀 GOAL-09 reflector)
  │
  ▼
Response(LLM 输出) → UI(CONV-03 提示词) → UI(app.js / companion.js / 场景卡)
  │
  ▼
EventBus(DOMAIN 71 + SYSTEM 22) → SSE(/api/stream) → 前端订阅
  ├─ 场景卡(scene.js) / 执行监视(execution-channel.js)
  ├─ Glance(glance-card.js) / HUD(capability-matrix.js)
  └─ 主动洞察(insight-panel.js) / 伴侣通知(companion.js)
```

---

## 二、Proactive 旁路（自动触发）

```
Proactive(PRO-01 tick_loop)
  ├─ scanners(舆情/天气/关键词/目标截止/周小结/IFTTT/看门狗)
  ▼
PRO-02 ProactiveEngine.decide(IGNORE/SUGGEST/NOTIFY/CREATE_GOAL)
  ├─ NOTIFY → PRO-03 NotificationPolicy → UI(insight-panel/companion)
  └─ CREATE_GOAL → Goals(GOAL-01/05) → Execution(EXEC-01)  ══ 仍经唯一执行入口 ══
```

---

## 三、感知旁路（仅观察，绝不控制）

```
Perception(PERC-01 屏幕采集 / PERC-06 ASR / PERC-07 KWS)
  └─ PERC-02..05 (UIA/OCR/Vision/Fusion, 当前 Mock)
        ▼
     PERCEPTION_* 事件 → EventBus → (未来可供 Context/Proactive 消费)
  ⚠ 红线：感知不调用 Execution / Computer，不写回控制
```

---

## 四、社交旁路

```
Social(SOC-02 入站 /api/social/inbound)
  └─ 跑一轮 Agent(→ Conversation → Execution) → SOC-01 回发
SOC-03 飞书 WS → SOC-02.handle_inbound
```

---

## 五、跨端旁路

```
CrossDevice(XDEV-01 设备登记) / XDEV-02 跨端接力
  └─ (默认 off) 与 Conversation/Execution 解耦，仅做会话交接占位
```

---

## 六、能力依赖矩阵（关键边）

| 能力 | 依赖 | 被依赖 |
|---|---|---|
| Execution(EXEC-01) | Tools, Permission, EventBus | 全部执行方(Goal/Computer/Chat/Social/Proactive) |
| Context(CTX-01) | Memory, Knowledge, UserModel, Episodic, Personality, Goal | Conversation(LLM) |
| Permission(PERM-01/02) | PolicyEngine | Execution, Computer |
| EventBus | — | 全部 DOMAIN/SYSTEM 事件生产者/消费者 |
| Tools(TOOL) | Knowledge/Memory/External/Social/Computer | Execution |
| Knowledge(KNOW) | — | Context, Tools(add/archive) |
| Memory(MEM) | — | Context, Tools(remember/memory_search), reflector 写回 |
| Proactive(PRO) | Goals, NotificationPolicy, EventBus | UI(notify) |
| Perception(PERC) | EventBus(产出) | (当前无消费者, Mock) |
| UI | EventBus(SSE), Conversation, Settings | User |

---

## 七、关键架构约束（关系图中的红线）

1. **单一执行入口**：Goal / Computer / Chat / Social / Proactive 全部 → `Execution.run`（EXEC-01）。禁止第二执行入口。
2. **单一事件总线**：所有 DOMAIN/SYSTEM 事件 → `eventbus`。禁止第二 EventBus。
3. **单一权限**：所有执行/电脑 → `PolicyEngine` + `PermissionGuard`。禁止第二权限系统。
4. **单一状态写源**：四套状态源(tasks/goals/agent_runtime/scheduler)经 `ExecutionState` 归一。
5. **感知不控制**：Perception 只产出 PERCEPTION_* 事件，绝不调用 Execution/Computer。
6. **Local First**：无云同步/联网（外部数据均为只读 API 拉取，非上传）。

---

## 八、关系图中的风险点

- **Planer/Workflow 缺失**：关系图中 Goal 的"怎么做"由 `plan_goal`+`_llm_dispatch` 内联，无独立 Planner 节点 → 关系图缺口（蓝图未落地）。
- **Scheduler 孤立**：`scheduler.py` 在关系图中无任何生产者/消费者连线（孤儿）。
- **Perception 悬空**：PERCEPTION_* 事件产出后无消费者（Mock + 未接线）。
- **personalization.py 悬空**：与 Conversation/Memory 无连线（死代码）。
- **D 重复组**：天气/截图/KWS/跨端/蒸馏/人格/JSON 抽取在图中出现"双节点"，应合并。
