# AI_DESIGN_CONTEXT — 设计哲学上下文入口

> **定位声明**：本文件**不是规则文件**，也不是权威层。它是给 AI Maintainer / 未来 Agent 的**上下文入口**——帮助快速建立「小6设计哲学」的心智模型，并指向权威与设计解释层文档。
> 若本文件与任何权威文件（Golden State / Decision / Governance）冲突，**一律以权威为准**。
> 创建：2026-08-04 · 配套 `AI_BOOTSTRAP.md` 使用。

## 一句话心智模型
小6是一个**本地优先的个人 AI 操作系统**：以「银河（太阳系）」作状态可视化品牌资产，以「左栏常驻能力 + 命令面板瞬时能力 + 银河状态可视化」三支柱共生，聊天只是平级入口之一；后端以 EventBus 为唯一脊柱、AppState 为唯一状态写入口、AgentRuntime 为唯一决策运行时。

## 阅读路径（配合 AI_BOOTSTRAP.md）
1. **必读权威**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` → `docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md` → `docs/decisions/DECISION_001..006`。
2. **设计解释层**（本报告册 `docs/design/frozen/` 8 份）：想理解「产品定位 / 设计原则 / IA / 银河交互 / 交互系统 / 设计系统 / 体验原型 / 领域模型」时，从这里进入——每份都标注 Source Authority / Related Documents / Frozen Status / Scope / Non-goals，且只解释、不覆盖权威。
3. **实现参考**：`ARCHITECTURE_MAP.md` + `docs/frozen/Xiao6-v2-*.md` + 前端 `xiao6-ui/`。

## 设计哲学要点（上下文，非规则）
- **品牌即状态**：银河本体视觉资产 100% 保留（自转/公转/星空/点击聚焦），是小6的标志性识别，OS 重构与品牌养护可并行不冲突。
- **三支柱共生**：常驻能力（左栏）/ 瞬时能力（命令面板）/ 状态可视化（银河）并存，聊天不独占中央。
- **本地优先 + 隐私优先 + 零密钥优先**：感知/常驻能力默认关、强开关、可审计；云能力单列、配密钥再启。
- **增量演进、不推翻**：保留现有 API/DB/工具/功能，新增模块/来源/表，不推翻运行时。
- **状态唯一、事件唯一**：所有状态经 AppState，所有跨模块通信经 EventBus。

## 给 AI 的提醒
- 设计解释层（8 份 Canon）是**索引与解释**，不是新规范；不要引用它们去「覆盖」Golden State / Decision / Governance。
- 若发现历史设计冲突，查 `docs/design/DESIGN_CONFLICT_REGISTER.md`；未登记且需裁决的，登记并等待主理人确认，不要自行裁决。
- 真正要改代码/架构前，回到 `AI_BOOTSTRAP.md` 的权威阅读顺序与 `GOVERNANCE_CHANGE_CONTROL.md`。
