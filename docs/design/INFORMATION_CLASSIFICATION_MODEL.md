# Information Classification Model — Xiao6 v1.4

> 信息分类模型 | Project Intelligence System v1.4 · Phase 2
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；不实现、不引入数据库、不修改冻结基线。

---

## 1. 目的

Phase 1 §3.1 指出：**当前缺失「一条信息该存哪」的统一决策模型**。本 Phase 建立 **9 类信息分类模型**，使任何一条信息都能被**唯一归类**到某个认知子系统，从而：

1. 明确**每类信息的唯一归属系统**（Single Owner）——杜绝跨系统重复存储。
2. 明确**每类信息的存储形态、权威来源、生命周期**。
3. 为 Phase 3–7 的边界规范、权威矩阵、生命周期提供分类基础。

> 核心原则：**每条信息有且仅有 1 个归属系统**。若一条信息看似跨两类，则按「最稳定的语义归属」归类；跨类引用走 Phase 7 权威矩阵与 Phase 10 关系图，不复制内容。

---

## 2. 九类信息总览

| # | 类别 | 一句话定义 | 唯一归属系统 | 是否持久 | 典型载体 |
|---|------|-----------|--------------|----------|----------|
| 1 | **User Fact** | 关于用户本人的客观事实 | User Model（memory.py `profile`） | ✅ 持久 | memory.py profile 字段 |
| 2 | **User Preference** | 用户的主观偏好/习惯/禁忌 | User Model（memory.py `profile`） | ✅ 持久 | memory.py profile 字段 |
| 3 | **Temporary Context** | 单次会话/任务的易失上下文 | 运行态（不持久 / 工作记忆） | ❌ 易失 | Agent Runtime 工作记忆 |
| 4 | **World State** | 当前世界/环境/设备/外部态势 | World Model | 🟡 观察缓存（可短存） | PerceptionState / worldaware_cache.json |
| 5 | **Project Knowledge** | 关于项目本身的稳定知识 | Knowledge（KU 体系） | ✅ 持久（冻结级） | Markdown + KU Metadata |
| 6 | **Decision Record** | 架构/工程决策及其理由 | Knowledge（KU `type=decision`）+ DECISION_* | ✅ 持久（L80） | DECISION_001–006 + KU |
| 7 | **Task State** | Goal / 任务进度与状态 | Goal System（goals.py） | 🟡 任务期（完成后沉淀） | goals.py / AppState goal 子树 |
| 8 | **Historical Experience** | 已完成任务后的经验/教训 | Memory（`learnings`） | ✅ 持久 | memory.py learnings |
| 9 | **Generated Insight** | 经治理沉淀的通用洞察/规则 | Knowledge（KU `type=spec/glossary`）或 Memory | ✅ 持久（须治理） | KU / memory.py |

> 注：「持久」指跨会话保留；「易失」指会话/任务结束即弃；「任务期」指 Goal 生命周期内有效，完成后按 Phase 8 生命周期沉淀或归档。

---

## 3. 逐类规范

### 3.1 User Fact（用户事实）
- **定义**：关于用户本人的、可验证的客观事实（姓名、职业、所在地、设备、健康状况等）。
- **归属**：User Model → `memory.py` 的 `profile` 字段（DECISION_003 单一来源）。
- **权威**：用户态数据，不由 Knowledge L100–L30 赋权；其「单一来源」由 DECISION_003 保护。
- **禁入**：❌ **绝不**写入 Knowledge 层（否则污染项目知识权威）。❌ 不写入 World Model。
- **示例**：「用户住在上海」「用户使用 Windows 桌面」。

### 3.2 User Preference（用户偏好）
- **定义**：用户的主观偏好、习惯、禁忌、语言风格（如「回复不带 emoji」「爱吃辣」「默认用中文」）。
- **归属**：User Model → `memory.py` 的 `profile`（与 User Fact 同载体，概念区分）。
- **权威**：同 User Fact。
- **禁入**：❌ 不写入 Knowledge（除非经 Phase 9/10 治理升级为通用交互规则 KU，但那已脱离「用户特定偏好」语义）。
- **示例**：「聊天回复不带 emoji」（← 与 working_memory 中 cleanReply 规则呼应，但那是代码实现，非认知存储）。

### 3.3 Temporary Context（临时上下文）
- **定义**：单次会话/任务内的易失上下文（当前正在处理的请求、中间推理、未定结论）。
- **归属**：运行态——Agent Runtime 工作记忆 / 当前 ContextPackage；**不持久化**。
- **权威**：无持久权威；任务结束即弃。
- **禁入**：❌ 不写入 Memory / Knowledge / World Model / Goal System 的持久存储；若需留存，先转化为 Historical Experience（§3.8）或 Generated Insight（§3.9）经治理沉淀。
- **示例**：「用户本次问的是太阳系可视化」「当前正在拆解的 Task #3」。

### 3.4 World State（世界态势）
- **定义**：当前世界/环境/设备/外部数据源的实时态势（屏幕内容、热点、设备状态、地震/天气/航班等外部数据）。
- **归属**：World Model → PerceptionState 投影 + `data/worldaware_cache.json` 观察缓存。
- **权威**：观察态，由 Perception 层生产，经 EventBus 写 AppState；**不持久化为知识**。
- **禁入**：❌ 不写入 Knowledge（除非经治理升级为稳定 KU，见 §3.9 + Phase 4）；❌ 不写入 User Model / Goal System。
- **示例**：「屏幕当前亮度 60%」「今日台北有地震预警」「GDELT 当前热点：某国选举」。

### 3.5 Project Knowledge（项目知识）
- **定义**：关于项目本身的稳定、可复用知识——架构、红线、事件契约、阶段定义、治理规则。
- **归属**：Knowledge → KU 体系（v1.3：12 Metadata + Payload）。
- **权威**：L100–L30，由 `source` 推导；GOLDEN_STATE = L100（v1.3 Phase 4）。
- **禁入**：❌ 不承载用户事实/偏好（§3.1/3.2）；❌ 不承载实时态势（§3.4）；❌ 不承载 Goal（§3.7）。
- **示例**：「DOMAIN_EVENT_NAMES = 71」「禁止第二 Runtime」「Galaxy 本体视觉资产 100% 保留」。

### 3.6 Decision Record（决策记录）
- **定义**：架构/工程决策的「是什么 + 为什么」，含理由、影响、未来限制。
- **归属**：Knowledge（`type=decision` KU）+ `docs/decisions/DECISION_001–006`（L80 决策级）。
- **权威**：DECISION_* = L80（v1.3 Phase 4）；是 Knowledge 关系主轴的根节点（PROJECT_KNOWLEDGE_GRAPH）。
- **禁入**：❌ 不写入 Memory / World Model / Goal System。
- **示例**：「DECISION_003：Memory 单一来源」「DECISION_001：EventBus 单一来源」。

### 3.7 Task State（任务态）
- **定义**：Goal / 任务的创建、规划、进度、完成状态。
- **归属**：Goal System → `goals.py`（Goal 生命周期：create→plan→execute→reflect→complete）。
- **权威**：任务态，由 goals.py 管理；不进入 Knowledge 权威体系。
- **禁入**：❌ 不写入 Knowledge（Goal 是任务态，非稳定知识）；❌ 不写入 User Model / World Model。
- **完成沉淀**：Goal 完成后，经验经 reflector 沉淀为 Historical Experience（§3.8）或经治理升级为 Generated Insight（§3.9）。
- **示例**：「当前 Goal：整理项目并生成总结」「Task #2 进行中」。

### 3.8 Historical Experience（历史经验）
- **定义**：已完成任务后的经验/教训/更好的做法（「这次这样做成/失败」）。
- **归属**：Memory → `memory.py` 的 `learnings` 字段（DECISION_003 单一来源）。
- **权威**：用户态/系统态数据，单一来源由 DECISION_003 保护。
- **禁入**：❌ 不写入 Knowledge（除非经治理升级为通用规则 KU）；❌ 不写入 World Model / Goal System。
- **示例**：「上次批量重命名因未备份导致丢失，今后先备份」。

### 3.9 Generated Insight（生成洞察）
- **定义**：从经验/观察中提炼的、可通用的洞察或规则（有时效性或通用性）。
- **归属（二元，须治理判定）**：
  - 若为**项目级通用规则/规范** → 经 Phase 9/10 治理升级为 Knowledge KU（`type=spec`/`glossary`，带 source/authority）。
  - 若为**用户/系统特定经验** → 留在 Memory `learnings`（§3.8）。
- **权威**：升级为 KU 后按 source 推导 L 级；留在 Memory 则由 DECISION_003 保护。
- **禁入**：❌ 未经理治理，不得直接写入 Knowledge（防低权威冒充，呼应 v1.3 Phase 10 准入红线 #5）。
- **示例（升级为 KU）**：「世界态势标记须用 THREE.RingGeometry 正圆环」→ 若源自 GOLDEN_STATE/Phase8 规范则 KU L90；若为某次临时观察则先留 Memory。

---

## 4. 分类决策树（AI 实操）

```
收到一条新信息
  │
  ├─ 关于「用户本人」？ ──────────────► User Fact / User Preference（§3.1/3.2）→ User Model
  │
  ├─ 关于「当前世界/设备/外部实时态」？ ─► World State（§3.4）→ World Model
  │
  ├─ 关于「项目本身架构/红线/决策/阶段」？► Project Knowledge / Decision Record（§3.5/3.6）→ Knowledge
  │
  ├─ 关于「当前 Goal/任务进度」？ ──────► Task State（§3.7）→ Goal System
  │
  ├─ 关于「已完成任务的经验/教训」？ ───► Historical Experience（§3.8）→ Memory learnings
  │
  ├─ 关于「可通用的洞察/规则」？ ───────► 经治理升级 → Knowledge KU 或留 Memory（§3.9）
  │
  └─ 仅「本次会话/任务的中间上下文」？ ─► Temporary Context（§3.3）→ 运行态（不持久）
```

> 决策铁律：**每条信息归属唯一系统**；跨类关系走引用（Phase 10 关系图），不复制内容。无法归类 → 先归 Temporary Context，待明确后迁移，禁止「随手塞进 Knowledge/World Model」。

---

## 5. 与现有体系的衔接

| 现有机制 | 本模型的衔接点 |
|----------|----------------|
| v1.3 KU / Metadata / Authority | §3.5/3.6/3.9 的 Knowledge 归属复用 KU 12 Metadata + L100–L30 |
| DECISION_003（Memory 单一来源） | §3.1/3.2/3.8 的 Memory 归属受该决策保护 |
| ARCHITECTURE_MAP（World Model） | §3.4 的 World State 归属对齐观察态 |
| goals.py（Goal 生命周期） | §3.7 的 Task State 归属对齐 |
| v1.3 Phase 10 准入红线 | §3.9 的「经治理升级」呼应红线 #5（禁止低权威冒充） |

---

## 6. 设计纪律确认

✅ 仅定义信息分类模型，未建存储、未改代码。
✅ 每条信息唯一归属，贯彻 Single Source Principle。
✅ User Model 从 Memory 中**析出为概念子系统**，但不新建存储（仍走 memory.py）。
✅ 与 v1.3 Knowledge 体系、DECISION_003、ARCHITECTURE_MAP 完全一致，无 Drift。
✅ 不触碰 GOLDEN_STATE 红线、不进入 Phase 9 实现。

> Phase 2 完成。下一步：Phase 3 定义 Memory Boundary Specification（任务 #207）。
