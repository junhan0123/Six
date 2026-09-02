# 07 — Proactive AI（主动智能系统）

> 依赖：01（分层 L1）、04（Goal 入口）、P13（薄主动层）
> 红线：Proactive 只能"建议/通知/建目标"，不能"自己干"；所有主动行为经 Goal/Execution 通道。

---

## 1. 设计目标

让 AI OS 从"被叫醒才动"进化为"在恰当时刻、以恰当方式、主动帮忙"。但主动性必须**克制、可追溯、可撤销、低打扰**——这是 2.0 与"又一个自动执行 Agent"的根本分野。

---

## 2. 薄决策层（P13）

Proactive 是**薄决策层**：它评估上下文、产出决策，但**不执行任何副作用**。所有落地动作都汇入 Goal/Workflow/Execution 通道。

### 2.1 决策分类

| 决策 | 含义 | 后续通道 |
|------|------|---------|
| `IGNORE` | 无需动作 | 无 |
| `SUGGEST` | 给建议（不建目标） | Surface 提示卡 |
| `NOTIFY` | 重要信息通报 | Surface 通知 |
| `CREATE_GOAL` | 提出目标 | `goal:proposed`（须用户确认） |

- `CREATE_GOAL` 默认 `priority ≤ P2` 且需用户确认才转 `approved`（见 04 §3）。
- Proactive **绝不**自动将 Goal 转 `approved`、绝不自行执行步骤。

---

## 3. 触发器（Triggers）

| 触发器 | 示例 |
|--------|------|
| 时间触发 | 每日晨间简报、周报前提醒 |
| 事件触发 | 文件变更、日历临近、邮件到达（经 Plugin） |
| 上下文触发 | 当前任务与历史目标冲突、知识缺口显现 |
| 异常触发 | 数据异常、计划偏离、健康指标越界 |
| 闲置触发 | 用户空闲时主动整理/蒸馏（低打扰窗口） |

- 触发器只读 Memory/Knowledge/State（经 Brain 上下文管道），不修改状态。
- 触发器产生"评估请求"，由 Proactive 决策模块统一裁决。

---

## 4. 上下文评估（只读）

```
[触发器] → Proactive 决策模块
   → 拉取上下文（Brain 管道：Memory L5/L7 + Knowledge + Goal/State）
   → 评分：相关性 / 紧迫性 / 打扰成本
   → 产出决策（IGNORE/SUGGEST/NOTIFY/CREATE_GOAL）
   → 仅当 CREATE_GOAL：publish(goal:proposed)
```

- 评估过程**不产生副作用**（不写 Memory、不改 Knowledge、不发消息）。
- 评估结果可缓存，避免重复触发同一条建议。

---

## 5. 打扰预算（Disturbance Budget）

- 每个 Proactive 行为计入"打扰预算"，防止通知轰炸。
- 高打扰动作（NOTIFY/CREATE_GOAL）受频控；低打扰（SUGGEST）可批量入 Surface 提示区。
- 用户可配置"免打扰时段"与"主动级别"（关 / 仅提醒 / 可建目标）。

---

## 6. 可撤销与审计

- 每条 Proactive 行为带 `proactive_id` + 触发来源 + 决策依据，可回溯。
- `CREATE_GOAL` 在被用户批准前不产生任何副作用；用户拒绝即 `IGNORE`。
- 用户可"不再建议此类"，Proactive 将样本写入 Memory L7 调整未来策略。

---

## 7. 与 Surface 的边界

- Proactive 产出决策，Surface 负责呈现（通知/提示卡/Companion 气泡）。
- Proactive 不直接渲染 UI；只发事件 `proactive:decision`。
- Surface 按"打扰预算"与用户设置决定呈现时机与形式。

---

## 8. 接口（事件）

```text
publish(proactive:trigger   {source, ctx_ref})     ← 触发器
publish(proactive:decision  {type, payload})       ← IGNORE/SUGGEST/NOTIFY/CREATE_GOAL
publish(goal:proposed        {source: proactive})   ← 仅 CREATE_GOAL
subscribe(proactive:feedback {decision_id, accept})← 用户响应（调策略）
```

---

## 9. 红线

- 禁止 Proactive 自动执行动作（无副作用，薄层原则 P13）。
- 禁止 Proactive 绕过 Goal 直接将动作送 Execution Channel。
- 禁止 Proactive 自动 `approved` 任何 Goal。
- 禁止无打扰预算控制的通知轰炸。

> 目标态设计；实现由 Proactive Sprint 承接（v1.0 Phase 9 已具薄层雏形，2.0 升格形式化），本 Sprint 不写代码。
