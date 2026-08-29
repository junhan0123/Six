# 03 · Agent 开发前能力核查协议（Agent Capability Check Protocol）— v1.1

> 阶段：Capability Platform Phase v1.1（Governance Integration）
> 模式：Audit → Design → Document → Verify → STOP
> 性质：**纯治理 / 设计，零代码改动**
> 上游：v1.0 `10_DEVELOPER_CAPABILITY_GUIDE.md` + `01_CAPABILITY_REGISTRY_SPEC.md` + `02_CAPABILITY_CHANGE_PROTOCOL.md`
> 强制读者：任何 AI（WorkBuddy / Claude Code / Cursor / ChatGPT / Gemini）在本仓库动手前

---

## 一、目的

把 v1.0 `10_DEVELOPER_CAPABILITY_GUIDE.md` 的"开发前必读"升级为**强制性预检闸门（Pre-Flight Gate）**。任何 AI 在小6仓库**写任何涉及能力的代码之前**，必须先过本核查；任一门（Gate）不通过 → **禁止动手**，回到设计或提交 CCR（`02`）。

> 本协议是 `02` 变更协议第 [1] 步的**具体操作化**。它保证：AI 不会"重复造轮子"、不会"误建第二执行/权限/事件系统"、不会"踩已知重复/死代码坑"。

---

## 二、适用场景（何时必须跑）

满足任一即触发：

- 任务涉及**新增** Tool / API 路由 / UI 面板能力 / Agent/Goal 节点 / 感知源 / 外部适配；
- 任务涉及**修改**某能力的入口 / 权限门 / 依赖 / 调用链 / 生命周期 / Flag；
- 任务涉及**删除 / 废弃**能力或代码；
- 任务被归类为"功能开发 / 架构演进 / 重构涉及能力"。

> **不适用**：纯 bug 修复（不改能力契约）、纯文案/样式微调、依赖升级——但若这些**改变入口/权限/依赖**，仍须跑。

---

## 三、预检阅读门（Read Gate，强制）

动手前 AI **必须**已读（或已在其上下文载入）：

| 顺序 | 文档 | 为何 |
|---|---|---|
| 1 | `AI_BOOTSTRAP.md` | 进入状态 + 能力现实认知规范（本 v1.1 写入） |
| 2 | `10_DEVELOPER_CAPABILITY_GUIDE.md` | 红线 + 已知坑 |
| 3 | `01_CAPABILITY_INVENTORY.md` | 查该能力是否已存在（搜 ID/名称） |
| 4 | `08_CAPABILITY_BOOK.md` | 人读说明 + 调用链 |
| 5 | `02_CAPABILITY_CLASSIFICATION.md` | 新能力归类 |
| 6 | `05_DUPLICATE_REPORT.md` | 重复坑 |
| 7 | `06_UNUSED_REPORT.md` | 死代码/孤儿坑 |
| 8 | `docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md` | 单一治理入口 + 红线 |

> 若 AI 未确认已读上述，视为**跳过预检**，属架构违规。

---

## 四、八道核查闸门（Gates）

每道闸门输出 **PASS / BLOCK / ESCALATE**。任一 **BLOCK** → 禁止实现，回到设计或提交 `02` 的 CCR。**ESCALATE** → 升级 L0/L1/L3（见 `02` §七）。

### G1 · 能力存在性（Capability Existence）
- 问：要建的能力**已在 `01` 注册表**中存在吗？
- 若存在 → **扩展**现有能力，禁止重建同名/同功能第二份。
- BLOCK 若：发现"新写一份与 `01` 已记录能力功能重复"的代码。

### G2 · 单一来源红线（Single-Source Red Line）
- 问：本任务是否触碰以下任一？
  - 执行入口 → 必须走 `Execution.run`（EXEC-01），禁止第二 Runtime/Execution。
  - 真正实现 → 在 `tools.execute_tool`（EXEC-02），`Execution.run` 只路由。
  - 权限 → 必须 `PolicyEngine`+`PermissionGuard`（PERM），电脑能力经 `PermissionGuard`，Agent 严禁直连 executor。
  - 事件 → 单 `eventbus`；telemetry 走 SYSTEM 通道；领域事件须先改前端 `zz-events.js` 并 Review（禁扩 F1/DOMAIN=71）。
  - 状态 → 单 `ExecutionState` 归一。
- BLOCK 若：出现第二执行/权限/事件/状态/Runtime 的任何苗头。
- ESCALATE 若：确需变更红线本身 → 升 L0。

### G3 · 重复防治（Duplicate Prevention）
- 问：本任务是否落入 `05` 的 D1–D11 重复模式？
  - D8 Toast / D9 Overlay-Modal-Dialog → **禁止**新建第 N+1 套，必须用 `OverlayManager`（权威）。
  - D1 天气 / D3 KWS / D7 JSON 抽取 / D5 蒸馏 / D6 人格 / D4 跨端 / D2 截图 → 先确认归哪套，勿复制。
- BLOCK 若：新建与 D1–D11 同模式的能力且未先走 `02` 去重方案。

### G4 · 死代码/孤儿隔离（Dead-Code Isolation）
- 问：本任务是否**依赖/复活** `06` 列出的死/孤儿？
  - 死文件：`personalization.py`、`perception_*.py`、`scheduler.py`(孤儿)、`*.tmp`、`*.bak.zzstep1`、`_smts_append.py` 等。
  - 悬空/幻影 Flag：`FEATURE_PERCEPTION`、`FEATURE_PROACTIVE_ENGINE`。
  - 幽灵工具名：`profile_read`/`profile_write`/`reminder_add`/`session_run`。
  - 死快捷键：`Ctrl/Cmd+U`。
- BLOCK 若：依赖上述且未先经 `02` 评审清理/复活。
- 注意：`scheduler`/`perception_*` 若启用，须先作为 CCR 立项，不得"顺手接上"。

### G5 · 分类合法性（Classification Validity）
- 问：新能力能归入 19 分类之一吗？
- BLOCK 若：无法归类（说明边界不清或需新类）→ 先按 `02` §七 升级讨论加类。
- 规则：单一主类；Execution 是横切不吞并；蓝图≠能力（Planner/Workflow 仍 missing）。

### G6 · 入口合规（Entry-Point Compliance）
- 问：入口是否复用既有机制？
  - UI → 走指令中心(`command-palette.js`)/既有面板，禁止新建独立 Overlay。
  - API → 走 `server.py` 路由 + localhost 门控 + `REMOTE_ACCESS_TOKEN`。
  - 无 Electron 入口（不存在），不得假设托盘/IPC/原生菜单。
- BLOCK 若：新建独立 Overlay/Modal 或假设 Electron 原生能力。

### G7 · 生命周期/Flag 诚实（Lifecycle & Flag Honesty）
- 问：
  - 是否把 `missing`/`experimental`(Mock)/`hidden`(未接线) **伪装成 `production`**？
  - Flag 默认值是否声明≠运行时（见 `11`：config 顶部 False 但 reload 翻 true）？
  - 是否引用悬空/幻影 Flag？
- BLOCK 若：生命周期不诚实、或引用未定义 Flag。
- 规则：Beta 须明确"密钥/模型缺失时的用户提示"，避免静默降级。

### G8 · 文档义务（Documentation Obligation）
- 问：本次提交是否**包含** SSOT 更新（至少 `01` + `08`，必要时 `02/03/04/05/06`）？
- BLOCK 若：代码改动落地但 SSOT 未同步（违反 `02` Document-First）。
- 规则：每能力 `change_log` + `last_audited` 须更新。

---

## 五、预检产物（Capability Check Report）

AI 跑完八道闸门后，**必须**在工作记录/PR 描述中附一份简短报告：

```markdown
## Capability Check Report (v1.1/03)
- 任务: <简述>
- 预检阅读门: ✅ 已读 1..8
- G1 存在性: PASS/BLOCK
- G2 单一来源: PASS/BLOCK/ESCALATE
- G3 重复防治: PASS/BLOCK
- G4 死代码隔离: PASS/BLOCK
- G5 分类合法: PASS/BLOCK
- G6 入口合规: PASS/BLOCK
- G7 生命周期/Flag诚实: PASS/BLOCK
- G8 文档义务: PASS(pending-impl)/BLOCK
- 结论: GO / NO-GO(原因) / ESCALATE(目标层)
- 关联 CCR: <若有>
```

> **NO-GO** 时，AI 不得擅自实现；须先解决 BLOCK 项（扩展现有 / 去重 / 清理 / 升类 / 立 CCR）。

---

## 六、与 AI_BOOTSTRAP 的衔接

`AI_BOOTSTRAP.md` 的"能力现实认知规范"段（本 v1.1 写入）**必须**指向本协议为"动手前强制预检"。任何 AI 打开仓库即受本协议约束。

---

## 七、违规处置

- 跳过预检或 NO-GO 下强行实现 → 视为**架构违规**；产出代码须回滚/重写，并补跑 `02` CCR。
- 重复/红线违规计入 `GOVERNANCE_INTEGRITY_AUDIT` 问题清单。

---

## 八、状态

🛑 **本核查协议为 v1.1 治理层强制预检规范，纯设计、零代码改动。已就绪，待 Verify + STOP 等 Review。**
