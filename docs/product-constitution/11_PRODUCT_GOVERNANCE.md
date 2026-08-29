# 11 · 产品治理（Product Governance）

> 依赖：00（执行摘要 · 权威关系）、`GOVERNANCE_AUTHORITY_HIERARCHY.md`、能力治理 v1.1/04
> 红线：仅定义本产品宪法的治理方式；不改动任何既有治理/冻结文档、不引入新功能。

---

## 1. 本宪法的性质与定位

- **性质**：小6 AI OS **产品/体验层单一真相源（Single Source of Product Truth）**。
- **非性质**：不是第二 Golden State、不是第二 Architecture、不是第二 Capability/Execution/Knowledge 真相。它是**产品层**的权威，引用而非重定义技术层真相。
- **权威关系**：见 00 §二。本宪法服从 Golden State（L0）与既有技术真相；冲突以 L0 与各自真相源为准。

---

## 2. 与总治理体系的关系

| 总治理（既有，冻结） | 本产品宪法（新） |
|---|---|
| `AI_OPERATING_SYSTEM_GOVERNANCE.md`（L0–L6 入口） | 产品层入口，引用总治理 |
| `GOVERNANCE_AUTHORITY_HIERARCHY.md`（L0–L6） | 本宪法拟登记为"产品治理层"（待 Review 后走变更控制） |
| 能力治理 v1.1（L6 子层） | 本宪法引用能力 SSOT，不重定义 |
| Design Canon `PRODUCT_CONSTITUTION.md`（解释层） | 旧设计 Canon 应视为本宪法的解释子文档（待变更控制标注） |

> ⚠️ **注册缺口**：本宪法尚未登记进总治理层级（既有治理文档冻结，修改须经 `GOVERNANCE_CHANGE_CONTROL.md`）。本阶段未改动它们。建议 Review 批准后由维护者登记。

---

## 3. 引用纪律（Single Source Rule · 产品层）

- **任何产品/体验意图**（UI/Overlay/Galaxy/Companion/Dock/Command Palette/Prompt/Capability/Memory/Knowledge 相关）**必须引用本宪法**，不得各自重述或另立产品意图。
- 本宪法**不重复**架构/能力/执行/知识的技术细节；需要技术事实时引用对应真相源（见 99 关系图）。
- 禁止产生"第二份产品真相"：任何新文档若定义产品愿景/哲学/交互/心智模型，须是本宪法的子文档或索引，不得独立成第二权威。

---

## 4. 变更控制（Change Control）

本产品宪法冻结后，任何修改须走治理变更流程：

1. **提案**：在 Review 中或经 `GOVERNANCE_CHANGE_CONTROL.md` 提出变更。
2. **影响评估**：核对是否触及 Golden State 红线（L0）、是否与其他真相冲突。
3. **评审闸门**：产品治理变更须由维护者 + 相关真相 Steward（能力/执行/知识）联审。
4. **文档先行**：先更本宪法，后改任何实现（与能力治理 Document-First 一致）。
5. **重审计**：重大变更后跑 Verify（见 99 / 00 红线复核方法）。

> 路线图（10）变更同样适用本节；阶段启动前须 Review 批准 + CCR + 预检（见 10 §5）。

---

## 5. 与能力治理的衔接

- 产品想法 → 能力影响 → 先过 `v1.1/03` 预检（G1–G8）+ `v1.1/02` CCR。
- 能力 SSOT（`01_CAPABILITY_INVENTORY.md`）是"能力事实"权威；本宪法是"能力如何呈现"权威。二者互补，不重叠。
- 任何 AI 进入仓库：应同时读能力现实认知规范（AI_BOOTSTRAP）与本产品宪法（建议 Review 后补入 AI_BOOTSTRAP）。

---

## 6. 维护者角色

| 角色 | 职责 | 常设 |
|---|---|---|
| **Product Steward** | 维护本宪法、评审产品层变更、裁决产品意图争议 | 治理维护者 |
| **真相 Steward（能力/执行/知识/架构）** | 联审跨层冲突 | 各真相维护者 |
| **Golden State Authority** | 裁决 L0 红线冲突 | 总治理流程 |
| **Any AI Agent** | 动手前读本宪法 + 跑相应预检 | 所有 AI |

> 当前 Steward 可由同一治理维护者兼任；后续可指定专人。

---

## 7. 重审计节奏（Re-Audit Cadence）

| 触发 | 动作 |
|---|---|
| 每个开发 Phase 结束 | 核对本宪法未被实现漂移；跑 00 红线复核 |
| 重大产品变更（路线图阶段启动） | 即时复核相关章节 + 更新关系图（99） |
| 红线疑似被破 | 立即 `GOVERNANCE_INTEGRITY_AUDIT` + 升级 L0 |
| 季度 / 跨大版本 | 全量复核本宪法与各真相源一致性 |

---

## 8. 治理纪律（不可破）

1. **Single Source Rule（产品层）**：产品意图唯一源 = 本宪法；禁止第二产品真相。
2. **Reference Only**：引用技术真相，不重定义。
3. **No Second Authority**：本宪法不声称高于 Golden State；冲突以 L0 与各真相源为准。
4. **Red-Line Immutable**：L0 红线（单 Runtime/事件/权限/状态/Vision 仅观察）不可由产品层修改。
5. **Honesty**：产品表达须诚实标注成熟度（prod/beta/exp/missing/dead）。
6. **Document-First**：变更先更本宪法，后改实现。

---

## 9. 状态

🛑 **Product Constitution Phase v1.0 治理框架已建立（11 份正文 + 00 + 99）。纯治理、零代码改动。待 Verify + STOP 等 Review。**
