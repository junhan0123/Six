# Cognitive Authority Matrix — Xiao6 v1.4

> 认知权威矩阵 | Project Intelligence System v1.4 · Phase 7
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；不实现、不新增权限系统、不触碰 GOLDEN_STATE。

---

## 1. 目的与定位

v1.3 Phase 4 已定义 **Knowledge 内部**的 L100–L30 权威（高覆盖低、禁止时间优先）。但 v1.4 七系统框架下，**跨系统冲突**（如 World Model 观察 vs Knowledge 事实、用户偏好 vs 通用知识）尚无统一裁决矩阵。

本 Phase 建立**认知权威矩阵**——跨七系统的冲突优先级，使任何冲突都有**可机读裁决依据**。

> 本文是**认知层**权威矩阵，与系统运行时的 `PolicyEngine`/`PermissionGuard`（管「能否执行」）**完全无关**（呼应 v1.3 Phase 4 §1）。

---

## 2. 权威来源分级（跨系统统一视图）

| 层级 | 来源 | 性质 | 保护依据 |
|------|------|------|----------|
| **L100** | GOLDEN_STATE 红线/事实 | 系统正确态 | GOLDEN_STATE（最高优先条款） |
| **L90** | `docs/frozen/` 规范（Phase8 感知规范等） | 冻结规范 | frozen 目录 |
| **L80** | DECISION_001–006 + 未来决策 | 架构决策 | DECISION_* |
| **L70** | AI_HANDOFF 永久禁止清单 | 交接红线 | AI_HANDOFF |
| **L50** | 审计/治理机制（Drift/Change Review） | 治理 | audits |
| **L30** | 前瞻/设计提案（含 v2 冻结文档前瞻部分） | 提案 | design/frozen(前瞻) |
| — | **Memory / User Model**（用户态） | 用户数据 | DECISION_003（单一来源） |
| — | **World Model**（观察态） | 实时态势 | Perception/EventBus |
| — | **Goal System**（任务态） | 任务数据 | goals.py |

> 注意：Memory / World Model / Goal 三者**不进入 L100–L30 知识权威体系**——它们是不同性质的数据（用户态/观察态/任务态），与 Knowledge 的「项目权威」正交。冲突时按 §3 矩阵裁决，而非简单比 L 级。

---

## 3. 冲突裁决矩阵（核心）

下表定义「当 A 与 B 冲突时，谁优先」。✅=前者优先；🔄=按具体语义；❌=前者不得覆盖后者。

| 冲突方 A \ B | Knowledge(L100) | Knowledge(L80↓) | Memory(User) | World Model | Goal | Temporary |
|--------------|-----------------|-----------------|--------------|-------------|------|-----------|
| **Knowledge(L100)** | — | L100 | ✅ L100 | ✅ L100 | ✅ L100 | ✅ L100 |
| **Knowledge(L80↓)** | ❌ | 比 L 级 | 🔄 用户态优先* | ✅ L80↓ | ✅ L80↓ | ✅ L80↓ |
| **Memory(User)** | ❌ L100 | 🔄 用户态优先* | — | 🔄 用户态优先** | 🔄 用户态优先** | 🔄 用户态优先 |
| **World Model** | ❌ L100 | ❌ L80↓ | 🔄 用户态优先** | — | 🔄 任务态优先 | 🔄 任务态优先 |
| **Goal** | ❌ L100 | ❌ L80↓ | 🔄 用户态优先** | 🔄 任务态优先 | — | 🔄 任务态优先 |
| **Temporary** | ❌ L100 | ❌ L80↓ | 🔄 用户态优先 | 🔄 任务态优先 | 🔄 任务态优先 | — |

标注说明：
- **\* 用户态优先**：用户明确偏好/事实（Memory）覆盖通用知识默认（L80↓），但**仅限用户交互风格**，不覆盖 L100 红线。例：「用户要求不带 emoji」覆盖「通用知识建议带 emoji」。
- **\*\* 用户态优先**：用户长期事实优先于 World Model 瞬时观察、Goal 临时约束。例：用户常住地（Memory）优先于 World Model 此刻定位漂移；用户偏好优先于 Goal 默认设定。
- **任务态优先**：Goal 约束优先于 World Model 观察态与 Temporary 上下文（任务范围界定权）；但不优先于 Knowledge L100/L80↓ 与 Memory 用户态。

---

## 4. 三类关键边界裁决（规格重点）

### 4.1 Memory vs Knowledge
- **Knowledge L100（红线/事实）> Memory**：用户记忆不得推翻项目红线（如用户「记得某事件=72」不得覆盖 Knowledge「事件=71 L100」）。
- **Memory(User) > Knowledge(L80↓) 于交互风格**：用户偏好覆盖通用知识默认（§3 *）。
- **内容域不重叠**：两者本不冲突（项目知识 vs 用户记忆）；冲突多因误用，按 Phase 3/5 边界纠正。

### 4.2 World Model vs Knowledge
- **Knowledge(任意 L) > World Model 观察态**：实时态势**不得**推翻稳定知识（Phase 4 §3 #1、Phase 6 §4.1）。
- 观察态若与 Knowledge 冲突，标记「脏数据/待核实」，不进入权威上下文。
- World Model 观察**升级**为 Knowledge 须走治理（Phase 4 §4），升级后获 L 级。

### 4.3 Temporary vs Stored
- **Stored（Knowledge/Memory）> Temporary**：持久存储的权威事实优先于单次会话易失上下文。
- Temporary 上下文仅在「本次任务范围」内有效，不得作为跨会话权威。
- Temporary 若需留存，先转化为 Historical Experience（Memory）或经治理 Generated Insight（Knowledge），不得直接固化。

---

## 5. 裁决流程（通用）

```
两信息冲突
  ↓
判定各自归属系统 + 权威性质（L100–L30 / 用户态 / 观察态 / 任务态）
  ↓
查 §3 矩阵
  ↓
  ├─ 明确优先方 → 采用优先方，另一方标记 superseded/脏数据/待核实
  └─ 🔄 语义优先 → 按 §3 标注的语义（用户态/任务态优先）裁决
  ↓
仍无法裁决（同级同性质）→ 人工裁决（AI_CHANGE_REVIEW_TEMPLATE），禁止 AI 猜测
```

> 与 v1.3 Phase 4 §4 知识层裁决流程一致，扩展为跨系统版；禁止时间优先贯穿始终。

---

## 6. 与 GOLDEN_STATE / v1.3 的兼容性

- ✅ L100 = GOLDEN_STATE 优先条款，完全一致。
- ✅ 高覆盖低、禁止时间优先继承 v1.3 Phase 4。
- ✅ Memory/World Model/Goal 不进入知识权威体系，与各自 DECISION/ARCHITECTURE_MAP 一致。
- ✅ 不新增运行时权限系统，与 PolicyEngine/PermissionGuard 解耦。

---

## 7. 设计纪律确认

✅ 仅定义跨系统权威矩阵，未实现、未新增权限系统。
✅ 三类关键边界（Memory↔Knowledge / World Model↔Knowledge / Temporary↔Stored）明确裁决。
✅ 与 GOLDEN_STATE L100、v1.3 Authority、DECISION_003 零冲突。
✅ 禁止时间优先贯穿；同级冲突走人工裁决。

> Phase 7 完成。下一步：Phase 8 定义 Cognitive Information Lifecycle（任务 #215）。
