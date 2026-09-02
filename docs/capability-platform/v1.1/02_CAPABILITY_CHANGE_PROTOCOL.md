# 02 · 能力变更协议（Capability Change Protocol）— v1.1

> 阶段：Capability Platform Phase v1.1（Governance Integration）
> 模式：Audit → Design → Document → Verify → STOP
> 性质：**纯治理 / 设计，零代码改动**
> 上游：v1.0 SSOT（`docs/capability-platform/`）+ `01_CAPABILITY_REGISTRY_SPEC.md`
> 关联治理：`docs/audits/GOVERNANCE_CHANGE_CONTROL.md`（总变更控制）

---

## 一、目的

为"任何对小6能力的增 / 改 / 删 / 生命周期迁移 / Flag 变更"建立**强制评审闸门（Review Gate）**，确保：

- 能力真相（SSOT）始终与代码一致；
- 不引入重复能力、不复活死代码、不触碰单一来源红线；
- 所有变更**先文档、后实现**，且经 Capability Steward 评审。

本协议是 `GOVERNANCE_CHANGE_CONTROL.md` 在**能力域**的具体化，不替代总流程。

---

## 二、适用范围（什么算"能力变更"）

以下任一动作**必须**走本变更协议：

| 类别 | 示例 |
|---|---|
| 新增能力 | 新 Tool、新 API 路由、新 UI 面板能力、新 Agent/Goal 节点、新感知源 |
| 修改能力 | 改入口、改权限门、改依赖、改实现模块、改调用链 |
| 生命周期迁移 | `experimental→beta→production`、`production→deprecated→dead`、标 `missing`/`hidden` |
| Flag 变更 | 新增/修改/删除 `FEATURE_*`、改默认开关值 |
| 废弃 / 删除 | 标 `deprecated`、删 `dead` 代码、移除去重 |
| 重复处置 | 收敛 Toast/Overlay/天气/KWS 等 D1–D11 重复组 |
| 分类调整 | 改某能力主类、新增第 20 类 |

> **例外（不走本协议）**：纯 bug 修复不改变能力契约、纯文案/样式微调、依赖库升级——但这些若**改变入口/权限/依赖**，仍须走本协议。

---

## 三、角色（RACI）

| 角色 | 职责 | 谁担任 |
|---|---|---|
| **Proposer（提议者）** | 发起 CCR、填模板、先做 `03` 开发前检查 | 任何 AI / 开发者 |
| **Capability Steward（能力管家）** | 评审 CCR、维护 SSOT、裁决重复/死代码/分类争议 | 治理维护者（见 `04`） |
| **Reviewer（评审人）** | 对CCR 投票/批注，重点查红线与单一来源 | Steward + 相关模块负责人 |
| **Golden State Authority（最高权威）** | 裁决 L0 红线冲突、批准 L1 级不可逆决策 | Golden State 流程（`GOVERNANCE_CHANGE_CONTROL.md`） |
| **AI Maintainer** | 落地后同步 SSOT 文档、跑校验 | 同 Steward |

---

## 四、变更请求模板（CCR — Capability Change Request）

任何变更须提交 CCR（Markdown/Issue/PR 描述均可），含：

```markdown
## CCR-<序号> · <能力名>
- 类型: add | modify | lifecycle | flag | deprecate | remove | dedupe | reclassify
- 提出者: <AI/人>
- 日期: YYYY-MM-DD
- 关联能力 ID: <如 TOOL-63 / EXT-03>
- 动机: <为什么改，业务价值>
- 影响面: <入口/权限/依赖/下游>
- 红线自检:
  - [ ] 不新增第二 Execution/EventBus/Permission/Runtime/State
  - [ ] 不扩张 F1 事件契约（DOMAIN=71）
  - [ ] Local First 不被破坏
- 重复自检: 已查 05，非 D1–D11 新实例
- 死代码自检: 未依赖 06 死/孤儿模块
- 文档计划: 将更新 01/08 + (如有) 02/03/04/05/06
- Steward 评审结论: pending | approved | rejected | escalate
```

---

## 五、变更流程（Stages）

```
[0] 触发
  │
  ▼
[1] 开发前检查（强制）── 先跑 03_AGENT_CAPABILITY_CHECK_PROTOCOL
  │   不通过 → 阻塞，回到设计（禁止动手）
  ▼
[2] 提交 CCR（填第四节模板）
  │
  ▼
[3] 资格闸门（Steward 自动判）
  ├─ 红线冲突？ → escalate 至 Golden State Authority
  ├─ 属 D1–D11 重复？ → 要求"去重方案"而非新建
  ├─ 依赖死/孤儿模块？ → 驳回（除非先清理/复活经评审）
  └─ 引用悬空/幻影 Flag？ → 驳回（先修 Flag 定义）
  ▼
[4] 分类与生命周期评审
  ├─ 新能力必须可归入 19 分类；否则 escalate 讨论是否加类
  └─ 生命周期必须诚实（蓝图≠production；见 01 §六.7）
  ▼
[5] 文档先行（Document-First）
  └─ 先更新 SSOT：01（字段表）+ 08（能力书）；必要时 02/03/04/05/06
  ▼
[6] Review Gate（Steward + Reviewer）
  ├─ approved → 进入实现（按 CCR 落地代码，仍受 03 约束）
  ├─ rejected → 关闭，记录原因
  └─ escalate → 升 L0/L1/L3（见第七节）
  ▼
[7] 落地后校验
  ├─ 跑 01 §六 校验规则（唯一性/完整性/入口/闭合/诚实）
  └─ 更新该能力 change_log + last_audited
  ▼
[8] 闭合：SSOT 与代码 diff 复核 → CCR 标记 done
```

> **Document-First 铁律**：第 5 步 SSOT 更新 **先于** 任何代码改动；禁止"先改代码后补文档"。

---

## 六、生命周期迁移规则

| 迁移 | 条件 | 审批 |
|---|---|---|
| `experimental → beta` | 真实实现（非 Mock）、有入口或明确外部依赖 | Steward |
| `beta → production` | 默认开启、接线主链路、无静默降级 | Steward |
| `hidden → production` | flag 改默认开 + 入口就绪 | Steward + Reviewer |
| `production → deprecated` | 有新实现取代，保留兼容期 | Steward |
| `deprecated → dead` | 兼容期过、无调用者 | Steward |
| `missing/blueprint → production` | **必须有真实实现 + 验证报告**，不得仅因文档宣称 | Reviewer + 验证证据 |
| `dead → removed` | 高置信死代码（见 `06`），零行为影响 | Steward（可批量） |
| 新类加入（第 20 类） | 现有 19 类无法容纳且经论证 | escalate L3 |

---

## 七、升级矩阵（Escalation）

以下变更**不得**由 Steward 单方面批准，须升级：

| 变更类型 | 升级至 | 依据 |
|---|---|---|
| 触碰单一执行入口 `Execution.run` / 第二 Runtime | L0 Golden State | 红线不可破 |
| 新增/修改 DOMAIN 事件名（F1 契约扩张） | L0 + 前端 `zz-events.js` 评审 | 前端红线 |
| 新增第二 EventBus / Permission / Memory 写源 | L0 Golden State | 红线 |
| 不可逆架构决策（如删除整个子系统） | L1 Decision Record | `GOVERNANCE_CHANGE_CONTROL` |
| 新架构分类 / 重大组件规范变更 | L3 Architecture Spec | 权威层级 |
| 跨系统边界归属争议 | L5 Boundary Spec | 权威层级 |
| Planner/Workflow 等蓝图"宣称落地" | L3 + 验证报告 | 终审 Top3 风险 |

---

## 八、与现有治理的衔接

- **总入口**：`docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md`（L0–L6 单一治理入口）。
- **总变更控制**：`docs/audits/GOVERNANCE_CHANGE_CONTROL.md`。本 CCR 是其"能力域实例"。
- **AI 维护者职责**：`docs/audits/GOVERNANCE_MAINTENANCE_PROTOCOL.md`（含 SSOT 同步义务）。
- **冲突**：本协议与总流程冲突 → 以总流程（及更高 L0–L5）为准；本协议仅细化能力域。

---

## 九、状态

🛑 **本变更协议为 v1.1 治理层流程规范，纯设计、零代码改动。已就绪，待 Verify + STOP 等 Review。**
