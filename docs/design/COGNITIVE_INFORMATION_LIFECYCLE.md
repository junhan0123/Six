# Cognitive Information Lifecycle — Xiao6 v1.4

> 认知信息生命周期 | Project Intelligence System v1.4 · Phase 8
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；不实现、不引入数据库、不修改冻结基线。

---

## 1. 目的与定位

Phase 1 §3.5 指出：**信息生命周期缺统一模型**——各系统自管（Memory 分层、Knowledge 6 步、Goal 状态机），但缺跨七系统的统一纪律。本 Phase 建立**统一信息生命周期**：

```
Capture → Classify → Store → Validate → Retrieve → Update → Expire → Archive
```

每条信息从产生到退场，都走这 8 步；**每步明确归属系统与动作**，杜绝「随手塞、永不清理」。

---

## 2. 八阶段规范

### [1] Capture（捕获）
- **动作**：信息产生（用户说/感知到/任务生成/外部拉取）。
- **归属**：产生源——User（用户输入）/ Perception（World Model）/ Goal System（Task State）/ Agent（Temporary Context）。
- **纪律**：捕获时**不立即持久化**；先进入 Classify。

### [2] Classify（分类）
- **动作**：按 Phase 2 九类模型归类 → 确定唯一归属系统。
- **归属**：分类决策（AI 实操走 Phase 2 §4 决策树）。
- **纪律**：**每条信息唯一归属**；无法归类 → 先归 Temporary Context，待明确迁移；禁止「随手塞 Knowledge/World Model」。

### [3] Store（存储）
- **动作**：写入归属系统的存储。
- **归属**：
  - Knowledge → KU（12 Metadata + Payload），走 v1.3 Phase 10 六步治理。
  - Memory / User Model → memory.py（DECISION_003）。
  - World Model → PerceptionState / worldaware_cache.json（观察缓存）。
  - Goal System → goals.py。
  - Temporary → 运行态（不持久）。
- **纪律**：Single Source；禁止跨系统复制内容（走引用）。

### [4] Validate（校验）
- **动作**：校验信息合法性/权威/来源。
- **归属**：
  - Knowledge → v1.3 Phase 3 §7 元数据校验 + Phase 10 准入红线（source 登记、authority 匹配、relations 合法）。
  - Memory / World Model / Goal → 各自实现层校验（如 World Model 观察须来自 Perception 生产）。
- **纪律**：未通过校验 → 拒入核心上下文（Knowledge ARCHIVE/DEPRECATED 不得入；低权威 L30 降权）。

### [5] Retrieve（检索）
- **动作**：上下文组装时按需取用。
- **归属**：
  - Knowledge → v1.3 Phase 6 7 阶段管道（检索→过滤→排序→去冲突）。
  - Memory / World Model / Goal → Context Engine 三源并行收集（Phase 6 §2）。
- **纪律**：经 Context Engine 汇编；不可覆盖关系按 Phase 7 矩阵。

### [6] Update（更新）
- **动作**：信息变更。
- **归属**：
  - Knowledge → version 演进（MINOR=措辞/MAJOR=事实变走 Change Review）+ 关系更新；冻结后修改走 Freeze Rule。
  - Memory / User Model → memory.py 更新（用户态，单一来源）。
  - World Model → 观察刷新（易失，覆盖式）。
  - Goal → goals.py 状态机。
- **纪律**：**禁止时间优先**——新信息不因新而获高权威（v1.3 Phase 4 §3.2）；Knowledge MAJOR 变更须 Change Review。

### [7] Expire（过期）
- **动作**：信息失效/降权处理。
- **归属**：
  - World Model 观察 → 超时自动过期（缓存 TTL）。
  - Temporary Context → 会话/任务结束即弃。
  - Knowledge L30 前瞻 → 若被高权威覆盖，标记 superseded（不删，保留可追溯）。
  - Memory 经验 → 长期未用可降权（未来 usage 统计，v1.3 Phase 8 U 维）。
- **纪律**：过期≠删除；标记状态，保留溯源。

### [8] Archive（归档）
- **动作**：信息退出活跃上下文。
- **归属**：
  - Knowledge → status→ARCHIVE/DEPRECATED（不得入核心上下文，v1.3 Phase 3 §4）。
  - Memory → 归档经验（仍可读，不主动注入）。
  - Goal → 完成后沉淀经验→Memory learnings / 经治理 Knowledge。
  - World Model → 观察自然消失（不归档，仅弃）。
- **纪律**：归档信息**不得**回流核心上下文；需复活须走 Store/Validate 重入。

---

## 3. 跨系统生命周期对照

| 阶段 | Knowledge | Memory/User | World Model | Goal System | Temporary |
|------|-----------|-------------|-------------|-------------|-----------|
| Capture | 治理产出 | 用户输入 | Perception | Task 生成 | Agent |
| Classify | Phase 2 | Phase 2 | Phase 2 | Phase 2 | Phase 2 |
| Store | KU 六步 | memory.py | 观察缓存 | goals.py | 运行态 |
| Validate | 元数据+红线 | 单一来源 | Perception 生产 | 状态机 | — |
| Retrieve | Phase 6 管道 | Context 源 | Context 源 | Context 源 | — |
| Update | version/Change Review | memory.py | 覆盖刷新 | 状态机 | — |
| Expire | superseded 标记 | 降权 | TTL | 完成沉淀 | 会话结束 |
| Archive | ARCHIVE/DEPRECATED | 归档经验 | 自然弃 | 完成 | 弃 |

---

## 4. 关键纪律（防反模式）

1. **捕获不急着存**：Capture 后必过 Classify，禁止「边捕获边写 Knowledge」。
2. **唯一归属**：Store 只写归属系统，跨系统引用不复制（Single Source）。
3. **校验门禁**：未过 Validate 不得入核心上下文（Knowledge/World Model/Memory 各有门）。
4. **禁止时间优先**：Update 不因新获权；Knowledge MAJOR 走 Change Review。
5. **过期不删**：Expire/Archive 标记状态保留溯源，不物理删（除非显式 DEPRECATED 清理）。
6. **归档不回流**：ARCHIVE/DEPRECATED KU 不得重新注入核心上下文。

---

## 5. 与 v1.3 / GOLDEN_STATE 的兼容性

- ✅ Knowledge 生命周期复用 v1.3 Phase 10（6 步）+ Phase 3 §4（status 6 值），本文扩展为跨系统 8 步。
- ✅ Memory 单一来源（DECISION_003）、World Model 观察态（ARCHITECTURE_MAP）一致。
- ✅ 禁止时间优先、Change Review、Freeze Rule 继承 v1.3 / AI_HANDOFF。
- ✅ 不引入数据库、不修改冻结基线。

---

## 6. 设计纪律确认

✅ 仅定义统一信息生命周期，未实现、未引数据库。
✅ 八阶段跨七系统对齐，每步明确归属与纪律。
✅ 与 v1.3 Knowledge 生命周期、DECISION_003、GOLDEN_STATE 零冲突。
✅ 防反模式六条纪律固化。

> Phase 8 完成。下一步：Phase 9 定义 AI Cognitive Maintenance Protocol（任务 #214）。
