# Knowledge Authority System — Xiao6 v1.3

> 知识权威系统 | Project Intelligence System v1.3 · Phase 4
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：仅设计/规范；不实现、不修改冻结基线、不引入新权限系统。

---

## 1. 目的

Phase 1 §2.2 指出：**当前权威仅 1 处显式优先条款（GOLDEN_STATE），其余靠约定推断，无机器可读等级，无覆盖规则**。本 Phase 形式化 6 级权威（L100–L30），使 KU 的 `authority` 字段可赋值、可比较、可自动裁决冲突。

> 本 Authority System 是**知识层**的权威排序，与系统运行时的 `PolicyEngine`/`PermissionGuard` **完全无关**——后者管「能否执行」，前者管「知识谁更可信」。二者不冲突、不重叠。

---

## 2. 六级权威定义

| 等级 | 名称 | 对应来源 | 可覆盖 | 示例 KU |
|------|------|----------|--------|---------|
| **L100** | 黄金基线 | `XIAO6_GOLDEN_STATE_v1.0.md` | 不可被任何覆盖 | 6 条红线、Event=71/8 |
| **L90** | 冻结规范 | `docs/frozen/` 中 FROZEN 类（Phase8 spec 等） | 仅 L100 可覆盖 | Phase8 感知规范条款 |
| **L80** | 架构决策 | `DECISION_001`–`006` + 未来决策 | L90/L100 可覆盖 | EventBus 单一来源 |
| **L70** | 交接/红线协议 | `AI_HANDOFF_PROTOCOL.md` 永久禁止清单 | L80+ 可覆盖 | Silent Change 禁止 |
| **L50** | 审计/治理机制 | Drift Check / Change Review / 一致性报告 | L70+ 可覆盖 | 漂移检测清单 |
| **L30** | 前瞻/设计提案 | `docs/design/` + v2 冻结文档（前瞻部分） | 任何更高等级可覆盖 | v2 能力目录升级提案 |

> v2 两份 `Xiao6-v2-*` 虽在 frozen 目录，但内容为**前瞻方向**（Phase 1 §3.4），故其 KU 归 **L30**，不享受 L90 冻结权威——除非某条被显式提升（须走 Decision + Change Review）。

---

## 3. 核心规则

### 3.1 高覆盖低（Override by Level）
- 当两条 KU 在**同一事实**上冲突时，**高等级权威胜出**，低等级自动降级为「被覆盖 / 仅供参考」。
- 覆盖关系：L100 > L90 > L80 > L70 > L50 > L30。

### 3.2 禁止时间优先（No Time-Priority）❗
- **新文档 / 新 KU 不自动获得更高权威**。L30 的前瞻提案即使比 L100 基线「新」，也**不得**覆盖 L100。
- 提升权威**唯一路径**：走 `AI_CHANGE_REVIEW_TEMPLATE` + 关联 DECISION +（必要时）更新 GOLDEN_STATE。时间不是理由。
- 此规则直接继承 v1.2 已记录的「禁止时间优先」原则，并固化为可机读字段约束。

### 3.3 来源决定初始等级
- KU 创建时，`authority` **由 `source` 推导**（见 §2 映射），不得手动乱填。
- 若 source 为 ARCHIVE/DEPRECATED（status，见 Phase 3 §4），该 KU **不得赋予 ≥L50** 的权威，且不可入核心上下文。

### 3.4 显式冲突标注
- 低等级 KU 若知自己与高等级冲突，须在 `relations` 中加 `contradicts` 关联（Phase 5）并 `note` 说明，便于检索期提示而非静默错误。

---

## 4. 冲突裁决流程（知识层）

```
两 KU 关于同一事实冲突
   ↓
比较 authority 等级
   ↓
高等级胜出 → 低等级标记 superseded（不删除，保留可追溯）
   ↓
若等级相同 → 比较 source 稳定性（FROZEN > ACTIVE > DESIGN）
   ↓
仍相同 → 人工裁决（走 AI_CHANGE_REVIEW_TEMPLATE），禁止 AI 自行猜测
```

> 此流程是**规范**，不要求代码实现。Phase 9 Context Integration 可据此组装「去冲突后」的上下文。

---

## 5. 与 GOLDEN_STATE 的衔接

- GOLDEN_STATE 的显式条款「任何冲突以本基线优先」= 本系统的 **L100 最高级**，二者完全一致，无矛盾。
- 本 Authority System **不修改** GOLDEN_STATE，仅将其「优先条款」泛化为 6 级可赋值模型，使非基线文档也能获明确等级。

---

## 6. 权威与检索/排序的衔接

| 后续 Phase | 使用 authority 的方式 |
|-----------|----------------------|
| Phase 6 Retrieval | 检索后按 authority 过滤（L30 默认降权/不直接入核心） |
| Phase 8 Ranking | Authority 为排序主权重（见 Ranking Model） |
| Phase 10 Governance | 创建 KU 时校验 authority 与 source 匹配（§3.3） |

---

## 7. 设计纪律确认

✅ 仅定义权威等级与覆盖规则，未新增运行时权限。
✅ 明确禁止时间优先，继承 v1.2 原则并机读化。
✅ v2 前瞻文档归 L30，化解 Phase 1 §3.4 混淆风险。
✅ 与 GOLDEN_STATE 优先条款完全一致，无 Drift。

> Phase 4 完成。下一步：Phase 5 定义类型化 Relation Graph（任务 #189）。
