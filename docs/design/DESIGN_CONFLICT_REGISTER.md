# DESIGN_CONFLICT_REGISTER — 设计冲突登记册

> 性质：冲突登记册（非裁决文件）。
> 纪律：发现历史设计冲突时**不自行裁决**，在此登记并等待主理人确认（用户约束 4）。
> 创建：2026-08-04

## 登记规则
- 每条冲突含：编号、冲突双方、性质、影响、建议处理（仅建议，非裁决）、状态。
- 状态：PENDING（待主理人确认）/ RESOLVED（已确认并修订）。
- 本册不创造新规范、不覆盖任何权威文件。

---

## CONFLICT-001：治理层级文档「设计层零命中」声明 vs 新建 Design Canon

- **冲突双方**
  - A：`docs/audits/GOVERNANCE_AUTHORITY_HIERARCHY.md` 第 32 行 ——「设计层文档（Product Constitution / Redesign Strategy / IA Freeze / Galaxy·Interaction·Design System Spec / Experiential Prototype Spec / Domain Model / UI Audit v2）**经全量扫描零命中，无落盘冻结文件**」。
  - B：本任务（B2）在 `docs/design/frozen/` 新建 8 份 Design Canon（PRODUCT_CONSTITUTION / AI_OS_DESIGN_PRINCIPLES / INFORMATION_ARCHITECTURE / GALAXY_INTERACTION_SPEC / INTERACTION_SYSTEM_SPEC / DESIGN_SYSTEM_SPEC / EXPERIENTIAL_PROTOTYPE_SPEC / DOMAIN_MODEL）。
- **性质**：事实声明与新落地文件之间的矛盾。A 写于 Design Canon 创建之前；B 落地后 A 的「零命中」描述变为不实。
- **影响**：新 AI 维护者若先读 GOVERNANCE_AUTHORITY_HIERARCHY，会得到「设计层文档不存在」的错误印象；且 A 第 32 行同时称「若未来此类文档被正式创建并冻结，须明确插入本层级（介于 L0 与 L1 之间或作为 L0 替代）」——但本任务已明确 Design Canon **不属于 L0/L1**，是独立的「设计解释层」，与 A 的预设插入位置冲突。
- **建议处理（非裁决）**：
  1. 修订 `GOVERNANCE_AUTHORITY_HIERARCHY.md` 第 32 行：将「零命中」更新为「设计解释层（docs/design/frozen/ 8 份）已于 2026-08-04 落盘，定位为设计解释层，非 L0/L1 权威层，不覆盖 Golden State / Decision / Governance」。
  2. 在 `AI_OPERATING_SYSTEM_GOVERNANCE.md` 阅读顺序中增加 Design Canon 作为「设计解释层（索引/参考，非规范）」条目。
- **状态**：RESOLVED — 经主理人明确授权（v1.4.1 Finalization 任务指令），2026-08-04 由 AI 维护者按 `GOVERNANCE_CHANGE_CONTROL.md` 提交 CR-20260804-001 并修订治理文档（GOVERNANCE_AUTHORITY_HIERARCHY.md:32 / AI_OPERATING_SYSTEM_GOVERNANCE.md:57），设计与架构层级未变。

---

## CONFLICT-002：（观察，暂挂起）v2 架构升级草案「server.py 模块化」意图 vs Golden State 冻结现状

- **冲突双方**
  - A：`docs/frozen/Xiao6-v2-架构升级设计文档.md` §3.2/§5 规划的 `api/` 微服务式拆分（server.py 瘦身为启动器）。
  - B：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` 冻结现状：server.py 仍为 monolith（Phase A0 冻结确认 + P0.1 仅把自检异步化，未做模块拆分），Electron 启动 `python server.py`。
- **性质**：设计意图（草案，未冻结）与冻结现状之间的差异——属「历史设计意图尚未落地」，非真正的规范冲突（草案本就标注「待评审」）。
- **影响**：无规范冲突；仅说明 Design Canon 须以 Golden State 冻结现状为准，v2 草案仅作背景参考。
- **建议处理（非裁决）**：本解释层已据此锚定（DOMAIN_MODEL / INFORMATION_ARCHITECTURE 以 Golden State 为准，v2 草案标注为「未冻结，仅参考」）。无需修订权威，仅作为注释留存。
- **状态**：PENDING（挂起，无需裁决，供主理人知悉）。

---

> 本册随 B2 落地维护；新增冲突请按上方格式追加，状态保持 PENDING 直至主理人确认。
