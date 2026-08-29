# AI Cognitive Maintenance Protocol — Xiao6 v1.4

> AI 认知维护协议 | Project Intelligence System v1.4 · Phase 9
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；补充 AI_HANDOFF_PROTOCOL 的认知边界维度；不实现、不修改代码。

---

## 1. 目的与定位

`AI_HANDOFF_PROTOCOL.md` 已定义 AI 是**长期工程维护者**，含维护闭环（Observe→Understand→Audit→Analysis→Plan→Approval→Implementation→Verification→Documentation→Freeze）与 Silent Change 禁止。

但 Phase 1 §3.6 指出：**缺「认知边界操作」指引**——新 AI 接管时，遇到一条信息「该放哪、冲突怎么解、过期怎么降、缺失怎么请求」无具体操作手册。本 Phase 在 AI_HANDOFF 维护闭环之上，**补充认知边界维度的操作协议**。

> 本文是 AI_HANDOFF 的**认知维度补充**，不替代它；操作仍走维护闭环 + Freeze Rule + Change Review。

---

## 2. 四情景操作手册

### 2.1 发现一条信息 → 放哪？
**步骤**（复用 Phase 2 §4 决策树）：
1. 判定语义：关于用户？世界实时态？项目本身？Goal？经验？洞察？临时？
2. 按九类模型（Phase 2 §3）确定**唯一归属系统**。
3. 走对应 Store 路径（Phase 8 §3）：
   - Knowledge → KU 六步治理（v1.3 Phase 10）。
   - Memory/User → memory.py（DECISION_003）。
   - World Model → 观察缓存（不持久为知识）。
   - Goal → goals.py。
   - Temporary → 运行态（不持久）。
4. **铁律**：唯一归属、引用不复制；无法归类→Temporary，待明确迁移。

### 2.2 发现冲突 → 怎么解？
**步骤**（复用 Phase 7 矩阵）：
1. 判定双方归属系统 + 权威性质（L100–L30 / 用户态 / 观察态 / 任务态）。
2. 查 Phase 7 §3 矩阵：
   - L100 红线 > 一切。
   - 用户态优先于通用知识默认（仅交互风格）。
   - 观察态不推翻稳定知识。
   - 任务态优先于观察态/Temporary。
3. 采用优先方，另一方标记 superseded/脏数据/待核实。
4. 同级同性质冲突 → **人工裁决**（AI_CHANGE_REVIEW_TEMPLATE），**禁止 AI 猜测**（呼应 v1.3 Phase 4 §4）。
5. 若涉及 Knowledge 权威变更 → 走 Change Review + Freeze Rule。

### 2.3 发现过期 → 怎么降级？
**步骤**（复用 Phase 8 §7 Expire）：
1. 判定信息类型与过期条件：
   - World Model 观察 → TTL 自动过期。
   - Temporary → 会话/任务结束即弃。
   - Knowledge L30 前瞻被高权威覆盖 → 标记 superseded（不删）。
   - Memory 经验长期未用 → 降权（未来 usage 统计）。
2. **过期≠删除**：标记状态，保留溯源（Phase 8 §4 纪律 #5）。
3. 归档（ARCHIVE/DEPRECATED）信息**不得**回流核心上下文（纪律 #6）。

### 2.4 发现缺失 → 怎么请求？
**步骤**：
1. 判定缺失的是哪类信息、归属哪系统：
   - 缺项目知识 → 应已存 Knowledge；若确实无，评估是否需新建 KU（走治理六步 + Change Review）。
   - 缺用户事实 → 向用户询问（不臆测），存入 Memory User Model（经允许）。
   - 缺世界态势 → 经 Perception 重新感知，不臆造。
   - 缺 Goal → 经 Goal System 创建（用户触发）。
2. **禁止臆造**：缺失信息不得由 AI 编造填充（防幻觉/Prompt Injection，呼应 v1.3 Phase 9 §3.5）。
3. 需新建 Knowledge KU → 走 v1.3 Phase 10 六步 + AI_CHANGE_REVIEW_TEMPLATE；**不得静默创建**（Silent Change 禁止）。

---

## 3. 认知维护红线（AI 必须遵守）

| # | 红线 | 对应规范 |
|---|------|----------|
| 1 | 不把用户隐私写入 Knowledge | Phase 3 §3 / Phase 5 §3 |
| 2 | 不把实时态势冒充稳定知识 | Phase 4 §3 / §4 |
| 3 | 不把 Goal/任务态当长期知识 | Phase 2 §3.7 / Phase 5 §3 |
| 4 | 不复制跨系统内容（引用不复制） | Phase 2 §4 / Phase 8 §4 |
| 5 | 不臆造缺失信息 | §2.4 |
| 6 | 不静默提权/静默创建（Silent Change 禁止） | AI_HANDOFF §九 / v1.3 Phase 10 §4 |
| 7 | 不绕过权威矩阵自行裁决同级冲突 | Phase 7 §5 |
| 8 | 不修改 GOLDEN_STATE / 红线 / 单一来源纪律 | GOLDEN_STATE / DECISION_003 |

---

## 4. 与 AI_HANDOFF_PROTOCOL 的衔接

| AI_HANDOFF 机制 | 本协议的补充点 |
|------------------|----------------|
| 维护闭环（10 步） | 认知边界维度的「发现信息→分类→归属→治理」细化 |
| Silent Change 禁止 | 认知写入（Knowledge KU / Memory）须留痕 |
| Freeze Rule | Knowledge 冻结后修改、权威提升须走重审 |
| Change Review | 冲突裁决、缺失信息新建 KU 复用模板 |
| 交接检查清单 | 新增「认知边界自测」项（见 §5） |

---

## 5. 认知边界自测（新 AI 接管 5 问）

新 AI 接管时，除 AI_HANDOFF 检查清单外，须能答：

1. 「用户爱吃辣」该存哪？→ Memory User Model（profile），**不**进 Knowledge。
2. 「屏幕当前亮度 60%」该存哪？→ World Model 观察态，**不**进 Knowledge/Memory。
3. 「DOMAIN_EVENT_NAMES=71」该存哪？→ Knowledge KU（L100，GOLDEN_STATE）。
4. 若 World Model 报「事件=72」与 Knowledge「71」冲突？→ 以 Knowledge L100 为准，观察标记脏数据。
5. 发现缺用户时区，怎么办？→ 向用户询问，存入 Memory（经允许），不臆造。

> 五问全过 = 认知边界接管就绪。

---

## 6. 设计纪律确认

✅ 仅补充 AI 认知维护协议，未实现、未改代码。
✅ 四情景操作手册（放哪/冲突/过期/缺失）固化。
✅ 八条认知维护红线，与 GOLDEN_STATE/DECISION_003/AI_HANDOFF 一致。
✅ 不替代 AI_HANDOFF，为其认知维度补充。

> Phase 9 完成。下一步：Phase 10 定义 Cognitive Knowledge Graph Extension（任务 #213）。
