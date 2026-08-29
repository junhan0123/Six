# 04 · 能力治理模型（Capability Governance Model）— v1.1

> 阶段：Capability Platform Phase v1.1（Governance Integration）
> 模式：Audit → Design → Document → Verify → STOP
> 性质：**纯治理 / 设计，零代码改动**
> 日期：2026-08-06
> 总治理入口：`docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md`（L0–L6 单一入口）

---

## 一、目的与范围

把 Phase v1.0 建立的**能力真相 SSOT** 从"一次性审计产物"升级为**持续运转的能力治理层（Capability Governance Layer）**，使其能：

1. 在**每次能力变更**时被引用、被维护、被校验（而非腐烂）；
2. 约束**任何 AI / 开发者**在动手前先认知能力现实、先过核查闸门；
3. 作为 AI OS 总治理体系（L0–L6）在**能力域**的派生子层，不创造第二权威。

本文件是该治理层的**总纲与地图**，下辖三份规范：

| 编号 | 文档 | 角色 |
|---|---|---|
| `01` | `01_CAPABILITY_REGISTRY_SPEC.md` | 能力注册表数据结构（Schema 契约） |
| `02` | `02_CAPABILITY_CHANGE_PROTOCOL.md` | 能力变更协议（评审闸门） |
| `03` | `03_AGENT_CAPABILITY_CHECK_PROTOCOL.md` | AI 开发前能力核查（强制预检） |

---

## 二、在 AI OS 治理层级中的定位

依据 `GOVERNANCE_AUTHORITY_HIERARCHY.md`：

| 层级 | 文档 | 与能力治理关系 |
|---|---|---|
| **L0** Golden State | `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | 最高权威；能力治理不得破其红线（单执行/事件/权限等） |
| **L1** Decision Records | `docs/decisions/DECISION_001..006` | 不可逆能力决策（如删子系统）走此 |
| **L2** Governance Rules | `KNOWLEDGE_GOVERNANCE_RULES` | 知识域；能力治理引用不冲突 |
| **L3** Architecture Spec | `ARCHITECTURE_MAP.md` 等 | 新架构分类/组件规范在此裁决 |
| **L4** Knowledge Spec | `docs/design/KNOWLEDGE_*.md` | — |
| **L5** Boundary Spec | `*_BOUNDARY_SPECIFICATION.md` | 跨系统归属争议在此裁决 |
| **L6** Implementation Reference | `docs/audits/*`、`docs/reference/*` | **能力治理层落此层**：v1.0 `00..12+99` 与 v1.1 `01..04` 均为 L6 |

> ✅ **能力治理层 = L6 实现参考治理子层**，由本文件统领。它**不提升为 L0–L5**，不替代任何高层规范。
> 任何冲突：高层覆盖低层；能力治理与总流程冲突以总流程（`GOVERNANCE_CHANGE_CONTROL`）为准。

---

## 三、治理角色（Governance Roles）

| 角色 | 职责 | 常设 |
|---|---|---|
| **Capability Steward（能力管家）** | 维护 SSOT（v1.0 `01/08` + v1.1 `01`）、评审 CCR（`02`）、裁决重复/死代码/分类争议、跑校验（`01` §六） | 治理维护者 |
| **AI Maintainer** | 落地变更后同步 SSOT、闭合 CCR、参与 `GOVERNANCE_MAINTENANCE_PROTOCOL` | 同 Steward/维护者 |
| **Reviewer** | 对 CCR 评审，重点查红线与单一来源 | Steward + 模块负责人 |
| **Golden State Authority** | 裁决 L0 红线冲突、批准 L1 | 总治理流程 |
| **Any AI Agent** | 动手前强制跑 `03` 预检，遵守 `02` | 所有 AI |

> 当前（v1.1）Steward/Reviewer/Maintainer 可由同一治理维护者兼任；后续可指定专人。

---

## 四、治理工件与权威（Artifacts）

| 工件 | 权威层 | 状态 | 说明 |
|---|---|---|---|
| v1.0 `00_EXECUTIVE_SUMMARY` | L6 | Frozen(待 Review) | 审计摘要 |
| v1.0 `01_CAPABILITY_INVENTORY` | L6 | **SSOT 人读真值** | 能力字段表；新增能力先更新此 |
| v1.0 `02..12,99` | L6 | Frozen(待 Review) | 分类/入口/生命周期/重复/死代码/关系图/书/指南/统计/终审/索引 |
| v1.1 `01_CAPABILITY_REGISTRY_SPEC` | L6 | 本阶段新增 | 注册表 Schema 契约 |
| v1.1 `02_CAPABILITY_CHANGE_PROTOCOL` | L6 | 本阶段新增 | 变更评审闸门 |
| v1.1 `03_AGENT_CAPABILITY_CHECK_PROTOCOL` | L6 | 本阶段新增 | 开发前强制预检 |
| v1.1 `04_CAPABILITY_GOVERNANCE_MODEL` | L6 | 本阶段新增 | 本总纲 |
| （未来）`capability_registry.yaml/json` | L6 | 未落地 | 若实现机器可读注册表，必须符 `01` Schema |

---

## 五、治理闭环（Governance Loop）

```
        ┌─────────────────────────────────────────────┐
        │                                             │
        ▼                                             │
  ① 任何能力变更意图                                    │
        │                                             │
        ▼                                             │
  ② AI 跑 03 预检（Read Gate + G1–G8）                 │
        │  NO-GO ──┐                                   │
        │          ▼                                   │
        │     回到设计 / 立 CCR                         │
        ▼ PASS                                         │
  ③ 提交 CCR（02 模板）                                 │
        │                                             │
        ▼                                             │
  ④ Steward 资格闸门 + Review Gate                     │
        │  escalate ──► L0/L1/L3                       │
        ▼ approved                                     │
  ⑤ Document-First：先更新 SSOT（01/08...）            │
        │                                             │
        ▼                                             │
  ⑥ 实现（仍受 03 约束）                                │
        │                                             │
        ▼                                             │
  ⑦ 校验（01 §六 规则）+ 更新 change_log/last_audited   │
        │                                             │
        ▼                                             │
  ⑧ 闭合 CCR；SSOT 与代码 diff 复核 ──────────────────┘
```

> 闭环保证：**文档先行、预检强制、评审有闸、落地可验、真相不腐**。

---

## 六、重审计节奏（Re-Audit Cadence）

| 触发 | 动作 |
|---|---|
| 每个开发 Phase 结束 | Steward 跑 `01` §六 校验 + 核对 SSOT 与代码 diff |
| 重大能力变更（CCR 落地） | 即时更新对应能力记录 + 统计（`11`） |
| 季度 / 跨大版本 | 全量重审计（可复用 v1.0 Stage A–L 方法） |
| 红线疑似被破 | 立即 `GOVERNANCE_INTEGRITY_AUDIT` + 升级 L0 |

---

## 七、关键治理纪律（不可破）

1. **Single Source Rule**：能力真相唯一源 = v1.0 `01`；v1.1 仅索引/契约/流程，不重定义业务事实。
2. **Document-First**：任何能力变更先更 SSOT，后改代码。
3. **Pre-Flight Mandatory**：任何 AI 动手前必跑 `03`；NO-GO 下禁止实现。
4. **No Second Authority**：能力治理不声称高于 Golden State；冲突以 L0–L5 为准。
5. **Red-Line Immutable**：单执行/事件/权限/状态/Runtime 红线（来自 L0）不可由能力治理修改。
6. **Honesty**：蓝图(`missing`)/Mock(`experimental`)/未接线(`hidden`) 不得伪装 `production`。

---

## 八、与 AI_BOOTSTRAP 的衔接

`AI_BOOTSTRAP.md`（本 v1.1 更新）新增"能力现实认知规范"段，要求任何 AI：
- 进入即读 v1.0 `00..99` + v1.1 `01..04`；
- 动手前强制跑 `03`；
- 变更能力走 `02` CCR。

---

## 九、进入未来阶段的握手（Roadmap Handshake）

- **本阶段（v1.1）仅治理/设计**，不实现注册表文件、不改代码。
- 后续若落地机器可读注册表（`capability_registry.yaml`）→ 必须符 `01` Schema，并作为 L6 数据工件。
- v1.0 `12_FINAL_REVIEW` 的 P3（治理）项由本阶段兑现；P0/P1/P2（UI 收口/去重/能力补强）仍按原建议推进，且每个均需走 `02`/`03`。
- 任何未来 Phase 启动前，先复核本治理层是否覆盖其能力变更类型；未覆盖则先扩 `02` 协议。

---

## 十、状态

🛑 **Capability Governance Layer 已建立（v1.1/01..04 四份治理文档 + AI_BOOTSTRAP 认知规范更新）。纯治理、零代码改动。待 Verify + STOP 等 Review。**
