# Cognitive System Current State Audit — Xiao6 v1.4

> 认知系统现状审计 | Project Intelligence System v1.4 · Phase 1
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 执行模式：Audit → Analysis → Design → Verification → Report → Stop
> 纪律：仅审计 / 分析 / 设计 / 记录 / 冻结规则；不修改业务代码、Runtime、Memory 实现、World Model 实现、Context Engine 实现、Event Contract、Policy、测试逻辑；不进入项目实现 Phase 9；不引入 RAG / Vector DB / Embedding；不新增功能。

---

## 0. 审计目的与范围

本审计是 v1.4「认知边界治理」的事实起点。v1.3 已建立 **Knowledge** 单一认知子系统的完整规范（KU / Metadata / Authority / Relation / Retrieval / Ranking / Governance），并在 `COGNITIVE_CONTEXT_BLUEPRINT.md` 中以五要素蓝图勾勒了 Knowledge / Memory / World Model / Context Engine / Reflection 的关系。

但 v1.3 仍遗留一个**未系统解答的问题**：在完整的「认知层」中，**Knowledge / Memory / World Model / Context Engine / User Model / Goal System / Event System** 七个系统各自的**职责边界**是什么？一条具体信息（如「用户爱吃辣」「Phase 8 已冻结」「屏幕当前亮度 60%」「今天的目标是整理项目」）应当**存哪里、不该存哪里、何时读、何时更新、谁有最终权威**？

> 本审计只**刻画现状**，不定义新规范。正式边界规范由 Phase 3–7 产出；本文件是它们的审计基线。本文件零触碰 GOLDEN_STATE 红线。

---

## 1. 七认知系统盘点（基于冻结基线 + v1.3 体系）

| # | 系统 | 权威载体（现状） | 当前状态 | v1.4 边界疑问 |
|---|------|------------------|----------|----------------|
| 1 | **Knowledge** | v1.3 KU 体系（Markdown + 12 Metadata + Payload） | ✅ 已规范（设计层） | 已清晰：仅项目知识。但须与 Memory/World Model 边界**显式固化** |
| 2 | **Memory** | `memory.py`（DECISION_003 单一来源） | ✅ 已冻结（实现层） | 承载「用户/系统长期记忆」，但**未区分 User Model 子域** |
| 3 | **World Model** | Computer World Model + PerceptionState 投影 + `data/worldaware_cache.json` | ✅ 已实现（观察态） | 承载「当前世界态势」，但**与 Knowledge 的「稳定事实」界限需显式** |
| 4 | **Context Engine** | Phase 9（项目）待设计审批 | ⛔ 未实现 | 须明确它是**消费者/汇编者**，不拥有任何信息 |
| 5 | **User Model** | `memory.py` 的 `profile` 字段（未独立规范） | ⚠️ 隐含于 Memory | 须从 Memory 中**析出**为概念子系统，明确与 Knowledge 不重叠 |
| 6 | **Goal System** | `goals.py`（ARCHITECTURE_MAP：Goal 生命周期） | ✅ 已实现 | 须明确 Goal = 任务态，**非长期知识、非用户记忆** |
| 7 | **Event System** | `eventbus.py`（DECISION_001：DOMAIN 71 / SYSTEM 8） | ✅ 已冻结 | 须明确它是**通信脊柱**，**不承载持久认知信息** |

---

## 2. 各系统「负责 / 不负责」现状刻画

### 2.1 Knowledge System（项目知识层，v1.3 已规范）
- **负责**：关于**项目本身**的持久、稳定、可检索知识——架构、红线、决策、阶段、事件契约、治理规则。
- **不负责**（现状已由 v1.3 声明，但未在「七系统边界」层统一固化）：
  - ❌ 不承载用户隐私/偏好/事实（那是 Memory / User Model）。
  - ❌ 不承载实时世界态势（那是 World Model）。
  - ❌ 不承载当前 Goal / 任务进度（那是 Goal System）。
  - ❌ 不承载对话历史（那是 Memory）。
- **权威**：L100–L30 六级，由 `source` 推导；GOLDEN_STATE = L100。
- **现状缺口**：边界声明散落在 v1.3 Phase 9 / 11，未形成「七系统边界」统一视图 → **Phase 5 补边界规范**。

### 2.2 Memory System（`memory.py` 单一来源，DECISION_003）
- **负责**：用户/系统的**长期记忆**——`profile`（用户画像）、`memory_summary`（对话摘要）、`learnings`（经验）、`reminders`（提醒）等。
- **不负责**：
  - ❌ 不承载项目架构知识（那是 Knowledge；Knowledge 层仅定义接口，复用同一 memory.py 底座，但**不新建第二 Memory**）。
  - ❌ 不承载实时世界态势（那是 World Model）。
  - ❌ 不承载尚未发生的 Goal（那是 Goal System）。
- **权威**：Memory 内容为**用户态数据**，不由 Knowledge Authority 体系赋权；但其「单一来源」地位由 DECISION_003（≈L80 决策级）保护。
- **现状缺口**：Memory 内部未区分「User Model（用户画像）」与「对话/经验记忆」的概念子域 → **Phase 2/3 在信息分类与 Memory 边界中析出 User Model**。

### 2.3 World Model（Computer World Model，观察态）
- **负责**：当前**世界/环境/设备/外部**态势——屏幕内容、热点、设备状态、外部数据源（GDELT/USGS/OpenSky/Open-Meteo）、环境感知。
- **不负责**：
  - ❌ 不承载稳定项目知识（那是 Knowledge；World Model 是动态态势，知识不消费实时感知）。
  - ❌ 不承载用户长期偏好（那是 Memory / User Model）。
  - ❌ 不承载 Goal（那是 Goal System）。
- **权威**：观察态，由 Perception 层生产，经 EventBus 写 AppState，投影为 PerceptionState / World Model。**不持久化为「知识」**——除非经治理升级为 Knowledge KU（带 source/authority）。
- **现状缺口**：World Model 的「观察态缓存」与 Knowledge 的「稳定事实」界限在七系统层未显式 → **Phase 4 补边界规范**。

### 2.4 Context Engine（Phase 9 项目实现，待审批）
- **负责**：汇编最终 LLM 上下文——并行收集 Memory / World Model / Knowledge 三源，合并、截断、产出 ContextPackage。
- **不负责**：
  - ❌ 不拥有任何信息（它是**消费者/汇编者**，不是存储）。
  - ❌ 不新增决策 Runtime（DECISION_002）。
  - ❌ 不替代任一源系统。
- **权威**：无信息权威；它**服从**各源系统的权威（如 Knowledge 的 L100 红线优先级、Memory 的用户态优先）。
- **现状缺口**：项目实现 Phase 9 仍未审批、未实现；v1.3 仅给出设计层集成关系 → v1.4 **不进入实现**，仅在 Phase 6 治理「上下文组装顺序与不可覆盖关系」。

### 2.5 User Model（用户模型，隐含于 Memory）
- **负责**：关于**用户本人**的结构化事实与偏好——身份、习惯、偏好、禁忌、语言风格。
- **不负责**：
  - ❌ 不承载项目知识（那是 Knowledge；User Model 与 Knowledge 内容域完全不重叠）。
  - ❌ 不承载实时世界态势（那是 World Model）。
  - ❌ 不承载 Goal（那是 Goal System）。
- **权威**：属 Memory 子系统（memory.py `profile`），由 DECISION_003 保护单一来源。
- **现状缺口**：User Model 在现有文档中**无独立规范**，仅作为 memory.py 的一个字段隐含存在 → v1.4 在 Phase 2（信息分类）、Phase 3（Memory 边界）中**正式析出**为认知子系统，但**不新建存储**（仍走 memory.py）。

### 2.6 Goal System（`goals.py`，已实现）
- **负责**：Goal 生命周期——创建、规划（plan_goal 拆 3–8 步）、更新、完成；驱动 Agent Runtime 目标驱动循环。
- **不负责**：
  - ❌ 不承载已完成经验/知识（完成后的经验沉淀归 Memory / 经治理归 Knowledge）。
  - ❌ 不承载用户长期偏好（那是 User Model / Memory）。
  - ❌ 不承载项目稳定架构（那是 Knowledge）。
- **权威**：Goal 为**任务态**，生命周期由 goals.py 管理；Goal 内容不进入 Knowledge 权威体系（除非完成后经治理升级）。
- **现状缺口**：Goal 与「临时上下文 / 任务态」的边界在七系统层未显式 → **Phase 2/8 在信息分类与生命周期中明确**。

### 2.7 Event System（`eventbus.py`，DECISION_001）
- **负责**：跨模块**通信脊柱**——DOMAIN（71，领域事件）/ SYSTEM（8，系统遥测）两互斥命名空间；`publish_domain`/`publish_system` 对未登记名抛 ValueError。
- **不负责**：
  - ❌ 不持久化认知信息（事件是瞬时通知，不是存储）。
  - ❌ 不承载知识/记忆/世界态势的「内容」（内容在源系统，事件只传变更通知）。
  - ❌ 不决策（决策在 Agent Runtime）。
- **权威**：由 DECISION_001（≈L80）保护单一来源；事件契约冻结（DOMAIN 71 / SYSTEM 8）。
- **现状缺口**：事件作为「信息流动通道」与七认知系统的关系（哪些系统经事件通信、哪些只读）需在 Phase 6（上下文组装）/ Phase 7（权威矩阵）中固化。

---

## 3. 当前边界问题（七系统视角）

> 在 v1.3 知识架构缺口基础上，从**七认知系统边界**视角扩展。每条标注：现象 / 风险 / 影响面 / 对应 v1.4 Phase。

### 3.1 信息归属缺失统一模型（最高优先级）
- **现象**：一条具体信息「该存哪」无统一决策模型。现有约定分散在 v1.3（Knowledge vs Memory）、DECISION_003（Memory 单一来源）、ARCHITECTURE_MAP（World Model 观察态）。
- **风险**：AI 可能把用户偏好误写入 Knowledge、把实时态势误当作稳定知识、把 Goal 误当长期记忆。
- **影响**：高——直接威胁 Single Source 与 GOLDEN_STATE 红线。
- **对应 Phase**：Phase 2（信息分类模型）+ Phase 3/4/5（各系统边界）。

### 3.2 User Model 未独立析出
- **现象**：User Model 仅作为 memory.py `profile` 字段隐含存在，无独立边界规范；易与 Knowledge（项目知识）混淆。
- **风险**：把「用户爱吃辣」这类用户事实错误提升为「项目知识 KU」（污染 Knowledge 权威层）。
- **影响**：中–高。
- **对应 Phase**：Phase 2 / Phase 3。

### 3.3 World Model 与 Knowledge 的稳定/动态界限未显式
- **现象**：World Model 是动态态势，Knowledge 是稳定事实，但二者在「外部事实」维度（如「当前地震」「今日天气」vs「系统事件=71」）易混淆。
- **风险**：把实时态势误冻为 Knowledge KU（L100 红线级），或反向把稳定事实降级为易失观察态。
- **影响**：中。
- **对应 Phase**：Phase 4 / Phase 5。

### 3.4 Context Engine 的「不可覆盖」关系未固化
- **现象**：Context Engine 未实现，但其「三源合并时谁优先」的权威关系只在 v1.3 Phase 9/11 概念提及，未形成可机读矩阵。
- **风险**：未来实现时三源冲突无裁决依据。
- **影响**：中（未来实现期）。
- **对应 Phase**：Phase 6 / Phase 7。

### 3.5 信息生命周期缺统一模型
- **现象**：Capture→Classify→Store→...→Archive 无跨七系统的统一生命周期；各系统自管（Memory 有分层、Knowledge 有 6 步生命周期、Goal 有状态机）。
- **风险**：信息过期/降权/归档无统一纪律，易残留陈旧知识。
- **影响**：中。
- **对应 Phase**：Phase 8。

### 3.6 AI 维护协议缺边界视角
- **现象**：`AI_HANDOFF_PROTOCOL.md` 维护闭环偏「代码/架构维护」，缺「发现一条信息该放哪、冲突怎么解、过期怎么降」的认知边界操作指引。
- **风险**：新 AI 接管时按直觉存放信息，造成 Source 漂移。
- **影响**：中。
- **对应 Phase**：Phase 9。

### 3.7 知识图未含 Memory/World/Context 边界关系
- **现象**：v1.3 `KNOWLEDGE_RELATION_GRAPH.md` 仅覆盖 Knowledge 内部与主轴（Decision→...→Memory）；未含 Memory Boundary / World State Boundary / Context Flow 关系。
- **风险**：知识图无法表达「此 KU 来自 World Model 观察」等跨系统关系。
- **影响**：低–中。
- **对应 Phase**：Phase 10。

---

## 4. 与现有基线的边界（防 Drift）

- **不触碰** GOLDEN_STATE 的 6 条红线、Event Contract（DOMAIN 71 / SYSTEM 8）、Runtime（AgentRuntime 唯一）、Memory（memory.py 单一来源）、Policy（PolicyEngine/PermissionGuard）、State（AppState 唯一写入口）、Galaxy 语义。
- **不替代** v1.3 知识层体系；v1.4 在其上**扩展**认知边界维度（Memory / World Model / User Model / Goal / Event 边界），不重写 KU/Metadata/Authority。
- **不替代** `AI_HANDOFF_PROTOCOL.md`；Phase 9 AI 维护协议为**认知边界维度补充**。
- **不进入** 项目实现 Phase 9；Context Engine 边界仅在设计层治理。
- **不引入** 任何数据库 / 向量检索 / Embedding；全部为 Markdown 规范 + 概念模型。

---

## 5. 审计结论

当前 Xiao6 七认知系统中，**Knowledge（v1.3）与 Memory / World Model / Event System（冻结基线）已有明确实现与部分边界声明**，但**缺乏统一的「信息归属模型」与 User Model / Goal System / Context Engine 的边界固化**。最关键的缺口是 **3.1（信息归属缺失统一模型）** 与 **3.2（User Model 未独立析出）**。

v1.4 的 Phase 2–10 正是针对这七项缺口做**设计层补全**，且严格不触碰冻结基线、不实现。本审计为后续 Phase 的事实基准。

> 审计完成。下一步：Phase 2 设计 Information Classification Model（任务 #206）。
