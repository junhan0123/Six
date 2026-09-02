# AI_HANDOFF_PROTOCOL.md

> AI 交接与长期维护协议 | Xiao6 Project Intelligence System v1.2
> 目标：任何新 AI Agent 打开项目后 **5 分钟内理解**系统与纪律，安全接手维护；并作为**长期工程维护者**的永久行为准则。

## 一、第一阅读顺序（必须依次阅读）

1. **PROJECT_STATUS.md** — 项目定位、版本、测试状态、核心原则、下一阶段。
2. **CURRENT_STATE.md** — 当前完成/进行/阻塞/下一步 + 红线警告。
3. **ARCHITECTURE_MAP.md** — 完整模块图（职责/禁止/数据方向）。
4. **DEVELOPMENT_PROGRESS.md** — 各 Phase 完成记录、测试、报告。
5. **AI_BOOTSTRAP.md** — 新 AI 5 分钟上手速览（≤3000 字）。

> 补充参考：`docs/DOCUMENT_INVENTORY.md`（文档清单）、`docs/decisions/`（架构决策）、`CURRENT_PHASE.md`（阶段指针）、`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（黄金基线）。

## 二、永久禁止（任何 AI 不得违反）

- ❌ 创建 **第二 Runtime**（决策逻辑必须运行在 `AgentRuntime`）。
- ❌ 创建 **第二 Memory**（持久化记忆必须走 `memory.py`）。
- ❌ 创建 **第二 EventBus**（事件必须走 `eventbus.py`）。
- ❌ 创建 **第二 Permission System**（权限必须走 `PermissionGuard`）。
- ❌ **绕过 AppState**（状态变更必须经 `applyEvent → reducers`）。
- ❌ **绕过 EventBus**（跨模块通信必须发领域事件）。
- ❌ **直接调用 Executor**（必须经 `PermissionGuard` 校验）。
- ❌ **修改 Galaxy 语义**（银河本体视觉资产 100% 保留）。
- ❌ **复制已有模块**（新能力先查 Capability Registry / docs/，避免重复）。
- ❌ 引入 **LangChain / AnythingLLM 运行时**（仅借鉴思想，见 DECISION_006）。

## 三、开发流程（强制）

```
Audit → Analysis → Design → Approval → Implementation → Test → Report → Freeze
```

- **Audit**：重读真实冻结代码（禁止凭记忆），输出对齐/审查报告。
- **Analysis**：定位集成点与红线。
- **Design**：产出设计规范（如 Phase 9 `Cognitive Context Architecture v1.0`），等待批准。
- **Approval**：用户明确批准后才能实现（禁止边改边推翻）。
- **Implementation**：仅实现已批准范围；不超范围新增功能。
- **Test**：新增测试 + 全量回归（Phase 6/7/8 须 0 FAIL / 0 Regression）。
- **Report**：生成阶段报告（含修改文件/架构影响/测试结果/风险）。
- **Freeze**：完成后停止，等待批准进入下一阶段。

## 四、事件纪律

- 新增事件须**同时**修改 `eventbus.py`（`DOMAIN_EVENT_NAMES` / `SYSTEM_EVENT_NAMES`）与 `zz-events.js`（`EVENTS` / `SYSTEM_EVENTS`），逐字对齐。
- `publish_domain()` / `publish_system()` 对未登记名抛 `ValueError`——这是安全网，不要绕过。
- 事件预算受控（Phase 9 新增 ≤10）。

## 五、状态纪律

- 只读投影层（GalaxyState / OverlayRuntime / ComputerState / PerceptionState）**只订阅、不回写**。
- 新增状态视图须作为投影，不得新建状态权威。

## 六、交接检查清单（新 AI 自测）

- [ ] 已读 PROJECT_STATUS / CURRENT_STATE / ARCHITECTURE_MAP / DEVELOPMENT_PROGRESS / AI_BOOTSTRAP。
- [ ] 理解 6 条核心原则（EventBus / AppState / Policy / Memory / 无第二 Runtime / Vision 不 Control）。
- [ ] 确认未触碰任何红线。
- [ ] 实现前先产出设计文档并等待 Approval。
- [ ] 实现后跑全量测试，确认 0 FAIL。

> 完整决策依据：`docs/decisions/DECISION_001..006.md`。

---

## 七、AI Maintainer Role（v1.2 新增）

**AI 不是代码生成器。AI 是长期工程维护者。**

职责定位：

- 维护现有架构的**稳定性**，而非随意扩张功能面。
- 任何修改以「最小必要 + 可回滚 + 已记录」为原则。
- 优先理解既有决策（`docs/decisions/`），再决定动作；不重复造轮子。
- 保护冻结边界：EventBus / AppState / Policy / Memory / Runtime / Galaxy。
- 文档与代码同等重要：**修改必留痕**（CHANGELOG_AI + Decision/Review + 阶段报告）。
- 发现架构漂移风险时，主动告警而非静默绕过。

## 八、AI Maintenance Loop（v1.2 新增）

固定维护闭环（任何维护动作都必须走完）：

```
Observe（观察现状，重读真实代码/文档）
  ↓
Understand（理解上下文与既有决策）
  ↓
Audit（审计偏离、风险、孤儿/重复）
  ↓
Analysis（分析影响范围与红线命中）
  ↓
Plan（制定最小修改计划）
  ↓
Approval（用户 / 决策批准）
  ↓
Implementation（仅实现已批准范围）
  ↓
Verification（验证：测试 + 治理审计通过）
  ↓
Documentation（更新文档 / CHANGELOG / Decision）
  ↓
Freeze（停止，等待下一步指令）
```

禁止在中间环节擅自跳转或扩大范围。

## 九、Silent Change 禁止规则（v1.2 新增）

任何 AI **禁止**以下「静默修改」：

- ❌ **未记录修改**：无 CHANGELOG_AI 条目 / 无 Decision / 无 Change Review。
- ❌ **未说明修改**：改动原因、影响范围、回滚方案未写明。
- ❌ **未验证修改**：未跑测试 / 未跑 `docs/reference/PROJECT_DOCUMENT_AUDIT.py`。

> 「Silent Change」是架构腐烂的首要来源，一律禁止。所有修改必须可被追溯。

## 十、Freeze Rule（v1.2 新增）

任何**重大修改**必须遵循：

```
Decision（架构决策 / 理由）
  ↓
Design（设计规范，等待批准）
  ↓
Approval（用户明确批准）
  ↓
Implementation（仅实现已批准范围）
  ↓
Test（全量回归 0 FAIL / 0 Regression）
  ↓
Report（阶段报告 + 文档更新）
```

在 Approval 之前不得写任何业务代码；完成即 Freeze，等待下一条指令。

---

> 关联治理资产：
> - 黄金基线：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`
> - 漂移检测：`docs/audits/ARCHITECTURE_DRIFT_CHECK.md`
> - 变更评审：`docs/decisions/AI_CHANGE_REVIEW_TEMPLATE.md`
> - 知识图谱：`docs/reference/PROJECT_KNOWLEDGE_GRAPH.md`
> - 入职测试：`docs/reference/AI_ONBOARDING_TEST.md`
> - 文档审计：`docs/reference/PROJECT_DOCUMENT_AUDIT.py`
