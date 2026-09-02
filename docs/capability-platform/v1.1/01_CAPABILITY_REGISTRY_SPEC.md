# 01 · 能力注册表规范（Capability Registry Spec）— v1.1

> 阶段：Capability Platform Phase v1.1（Governance Integration）
> 模式：Audit → Design → Document → Verify → STOP
> 性质：**纯治理 / 设计，零代码改动**（严守纪律红线）
> 日期：2026-08-06
> 上游：Capability Platform Phase v1.0（`docs/capability-platform/00..12+99`，唯一能力真相 SSOT）
> 治理层级：L6（Implementation Reference，详情见 `04_CAPABILITY_GOVERNANCE_MODEL.md`）

---

## 一、目的与定位

Phase v1.0 用 `01_CAPABILITY_INVENTORY.md` 建立了**人读的能力真相（SSOT）字段表**。本规范把该字段表**形式化为可校验的注册表数据结构（Capability Registry Schema）**，使：

1. 每条能力记录有**唯一、确定、机器可校验**的字段契约；
2. 未来若落地机器可读注册表（如 `capability_registry.yaml`/`json`），**必须**符合本 Schema，不得自创字段；
3. AI / 开发者 / 治理流程在"增删改能力"时有**统一的数据结构锚点**（配合 `02` 变更协议与 `03` 开发前检查）。

> ⚠️ 本文件是 **Schema 契约（设计）**，不是运行时代码。v1.1 不生成运行时注册表文件、不修改任何 `.py`/`.js`/`.css`/`.html`/配置。当前唯一 SSOT 仍是 v1.0 的 `01` 字段表（人读）。

---

## 二、权威关系（Single Source Rule）

- **最高权威**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（L0）。本 Schema 不重定义任何 Golden State 红线（单一执行/事件/权限等）。
- **Schema 来源**：本 Schema 是 v1.0 `01_CAPABILITY_INVENTORY.md` 列字段的**规范化抽取**，不新增业务事实。
- **不创造第二权威**：能力注册表是"真相的索引/结构"，不替代架构规范（L3）与边界规范（L5）。
- **冲突裁决**：若本 Schema 与 `01` 字段表字面不一致，以 `01`（SSOT 人读表）为准，并触发 `02` 变更协议修订本 Schema。

---

## 三、能力记录 Schema（Capability Record）

每条能力在注册表中是一个 `CapabilityRecord` 对象。字段定义如下（类型：`string`/`enum`/`bool`/`list`/`date`/`object`）。

| 字段 | 类型 | 必填 | 约束 / 取值 | 说明 |
|---|---|---|---|---|
| `id` | string | ✅ | 格式 `^[A-Z]{2,6}-\d{2,3}$`（如 `CONV-01`、`TOOL-62`） | 全局唯一能力 ID；命名空间 = 分类 Code（见 `02_CAPABILITY_CLASSIFICATION.md`） |
| `name` | object | ✅ | `{ "zh": string, "en"?: string }` | 能力名称，中文必填 |
| `category` | enum | ✅ | 19 分类 Code 之一：`Conversation`/`Knowledge`/`Memory`/`Context`/`Execution`/`Tools`/`Goals`/`Computer`/`Permission`/`Proactive`/`Social`/`Perception`/`External`/`CrossDevice`/`Personalization`/`Settings`/`System`/`UI`/`Developer` | 单一主类，禁止多归类 |
| `lifecycle` | enum | ✅ | `production`/`beta`/`experimental`/`hidden`/`internal`/`deprecated`/`legacy`/`dead`/`missing` | 见 `04_CAPABILITY_LIFECYCLE.md` 定义 |
| `summary` | string | ✅ | ≤ 200 字 | 一句话能力说明 |
| `entry_points` | list[object] | 条件 | 至少 1 项，**除非** `lifecycle ∈ {dead, missing}` | 入口数组，见下"EntryPoint 子结构" |
| `owner_module` | string | ✅ | 相对仓库路径（如 `tools.py`/`ai_core/execution/api.py`） | 真正实现所在模块；`missing` 可填 `none` |
| `dependencies` | list[string] | — | 元素为其他能力 `id` | 本能力依赖的能力（有向边，供关系图） |
| `dependents` | list[string] | — | 元素为其他能力 `id` | 反向依赖（可由依赖集自动推导，允许冗余镜像） |
| `permissions` | object | ✅ | 见"Permission 子结构" | 权限门配置 |
| `feature_flags` | list[string] | — | `FEATURE_*` 或运行时常量名 | 门控此能力的开关（可空 = 无 flag） |
| `risk` | enum | ✅ | `low`/`medium`/`high`/`critical` | 见 `01` 风险列 |
| `tags` | list[enum] | — | `duplicate`/`blueprint`/`orphan`/`ghost-alias`/`fallback`/`single-source` | 派生标记；`duplicate` 须配合 `duplicate_of` |
| `duplicate_of` | list[string] | 条件 | 当 `tags` 含 `duplicate` 时必填 | 指向同组权威能力 id（如 `weather.py` 的 `duplicate_of: [EXT-01]`） |
| `verified` | bool | ✅ | — | `true`=已验证落地；`false`=蓝图/未接线（`missing`/`experimental` 多为 false） |
| `source_doc` | string | ✅ | `01`/`08`/具体文档锚点 | 人读详细说明出处 |
| `last_audited` | date | ✅ | ISO `YYYY-MM-DD` | 最近一次审计日期 |
| `change_log` | list[object] | — | `{ date, type, by, note }` | 变更轨迹（配合 `02` 变更协议） |

### EntryPoint 子结构

| 字段 | 类型 | 必填 | 取值 |
|---|---|---|---|
| `type` | enum | ✅ | `api`/`ui`/`command`/`shortcut`/`proactive`/`auto`/`social`/`cli` |
| `path` | string | 条件 | `api`→路由（如 `/api/chat`）；`ui`→文件（`index.html`）；`command`→命令名；`shortcut`→按键；其余可空 |
| `method` | string | 条件 | `api` 时填 `GET`/`POST`/`SSE` |
| `auth` | enum | — | `none`/`localhost`/`token`/`key`/`policy`/`confirm` |
| `note` | string | — | 调用链说明（如 `run_fc_loop→Execution.run→execute_tool`） |

### Permission 子结构

| 字段 | 类型 | 必填 | 取值 |
|---|---|---|---|
| `risk_level` | enum | ✅ | `low`/`medium`/`high`/`critical` |
| `gate` | enum | ✅ | `none`/`policy_engine`/`permission_guard`/`remote_whitelist`/`auto`/`confirm`/`session`/`never`/`deny` |
| `remote_allowed` | bool | — | 是否允许远程调用（对应 `server.py` `_REMOTE_FORBIDDEN`） |
| `note` | string | — | 权限说明 |

---

## 四、注册表容器 Schema（Registry Container）

机器可读注册表（未来落地时）整体结构：

```yaml
registry:
  schema_version: "1.0"          # 本 Spec 版本
  generated_at: "2026-08-06"     # 最近一次从 SSOT 同步日期
  source_of_truth: "docs/capability-platform/01_CAPABILITY_INVENTORY.md"
  governance: "docs/capability-platform/v1.1/04_CAPABILITY_GOVERNANCE_MODEL.md"
  counts:                        # 与 11_CAPABILITY_STATISTICS 对齐
    total: 135
    by_lifecycle: { production: 95, beta: 12, experimental: 8, hidden: 14, dead: 12, missing: 2, ... }
  capabilities: [ CapabilityRecord, ... ]   # 全量记录
  indexes:
    by_category: { Conversation: [...ids], ... }
    by_lifecycle: { production: [...ids], ... }
    duplicate_groups: [ { group: "D1", members: [EXT-01, EXT-02], authority: EXT-01 }, ... ]
    dead_list: [...ids]
    orphan_list: [...ids]
```

> 当前（v1.1）`registry` 容器**以 v1.0 `01` 人读表为唯一事实源**；本 Schema 仅规定"若落地 YAML/JSON 必须长这样"。

---

## 五、ID 与命名约定

1. **ID 命名空间 = 分类 Code**：`CONV`/`KNOW`/`MEM`/`CTX`/`EXEC`/`TOOL`/`GOAL`/`COMP`/`PERM`/`PRO`/`SOC`/`PERC`/`EXT`/`XDEV`/`PERS`/`SET`/`SYS`/`UI`/`DEV`。
2. **序号从 01 起始连续**，同分类内唯一；新增按顺序追加（如 `UI-17`）。
3. **禁止复用已死 ID**：`dead` 能力移除后，其 ID **永久保留不回收**（避免历史引用错乱）；新能力用新 ID。
4. **工具（TOOL）特例**：62 项已在 `TOOLS`/`TOOL_FUNCS` 注册表，其 ID 与函数名一一对应；注册表 `owner_module` 统一定为 `tools.py`。

---

## 六、校验规则（Registry Validation）

注册表（无论人读 `01` 还是未来机器可读文件）**必须**满足：

1. **唯一性**：所有 `id` 全局唯一；无重复。
2. **完整性**：每条记录 `id`/`name`/`category`/`lifecycle`/`summary`/`owner_module`/`permissions`/`risk`/`verified`/`source_doc`/`last_audited` 齐全。
3. **入口完整性**：`lifecycle ∉ {dead, missing}` 的记录 **必须** 有 ≥1 个 `entry_points` 项（无入口即孤儿，须标 `orphan` 或降 `dead`/`hidden`）。
4. **分类合法**：`category` 必为 19 分类之一；单主类。
5. **依赖闭合**：`dependencies`/`dependents` 中所有 id 必须存在于注册表。
6. **重复标记一致**：`tags` 含 `duplicate` ⇒ 必须 `duplicate_of` 指向同组权威项；同组 `duplicate_of` 聚合 = `05` 报告的 D1–D11。
7. **生命周期诚实**：`verified=false` 且 `lifecycle=production` **禁止**（蓝图/未接线不得伪装生产）；`missing` 必须 `verified=false`。
8. **单一来源红线**：任何记录不得声称拥有"第二执行/事件/权限"——Execution 类能力的 `entry_points` 必须经 `Execution.run`；Permission 类只能 `policy_engine`/`permission_guard`。
9. **Flag 真实**：`feature_flags` 引用的开关必须在 `config.py` 实际消费（禁止引用 `FEATURE_PERCEPTION` 等悬空/幻影开关；见 `06`）。

> 校验可由未来脚本自动跑（不在 v1.1 范围）；当前由 `02`/`03` 人工 + Review 保证。

---

## 七、与 v1.0 文档的映射

| 本 Schema 字段 | v1.0 出处 |
|---|---|
| `id`/`name`/`category`/`lifecycle` | `01` 速查总表 + `02` 分类 |
| `entry_points` | `01` 入口列 + `03_ENTRY_MAP.md` |
| `owner_module` | `01` 负责人模块列 |
| `dependencies`/`dependents` | `07_CAPABILITY_GRAPH.md` |
| `permissions` | `01` 权限列 + `PERM` 类 |
| `feature_flags` | `01` Flag 列 + `11` Feature Flag 统计 |
| `risk` | `01` 风险列 |
| `tags`(`duplicate`) | `05_DUPLICATE_REPORT.md` D1–D11 |
| `tags`(`dead`/`orphan`) | `06_UNUSED_REPORT.md` |
| `verified`/`lifecycle=missing` | `04` + `12` 终审（Planner/Workflow 缺失） |

---

## 八、状态

🛑 **本规范为 v1.1 治理层 Schema 契约，纯设计、零代码改动。已就绪，待 Verify + STOP 等 Review。**
