# DESIGN_HANDOFF_SIMULATION — 设计交接仿真

> 目的：模拟一名**新 AI Maintainer** 仅阅读 `AI_BOOTSTRAP.md` + `AI_OPERATING_SYSTEM_GOVERNANCE.md` + Design Canon（`docs/design/AI_DESIGN_CONTEXT.md` + `docs/design/frozen/` 8 份），能否正确回答典型设计问题。
> 方法：逐问给出「仿真回答 + 引用来源 + 是否可答 + 缺口」。
> 创建：2026-08-04 · 配套 B4。

## 仿真设定
- 读者：新 AI，未读 `xiao6-ui/` 源码、未读 v2 草案全文、未读 `GOVERNANCE_AUTHORITY_HIERARCHY` 之外治理细节。
- 可用材料：`AI_BOOTSTRAP.md` → `AI_OPERATING_SYSTEM_GOVERNANCE.md` → `DECISION_001..006` → `AI_DESIGN_CONTEXT.md` → `docs/design/frozen/` 8 份 → `DESIGN_CONFLICT_REGISTER.md`。

---

## Q1：小6的产品定位是什么？能否引入第二 Runtime？
**仿真回答**：小6是「本地优先的个人 AI 操作系统」（Golden State L0 §项目标识）。**不能**引入第二 Runtime——Golden State 红线明确禁止第二 Runtime / Memory / EventBus / Permission；DECISION_002 进一步确定 AgentRuntime 为唯一决策运行时。
**来源**：`PRODUCT_CONSTITUTION.md`（Source Authority→Golden State）+ `AI_OS_DESIGN_PRINCIPLES.md`（红线 A + 决策 B）。
**可答**：✅ 完全可答，且指向权威。

## Q2：聊天窗口在信息架构里是什么角色？是否独占中央？
**仿真回答**：聊天只是左栏/面板**平级入口之一**，不独占中央。三支柱共生：左栏常驻能力 + 命令面板（Ctrl/Cmd+K）瞬时能力 + 银河状态可视化。当前实现中聊天窗默认收起为底部细触发条，hover/钉住展开。
**来源**：`INFORMATION_ARCHITECTURE.md`（三支柱 + 聊天定位）+ `INTERACTION_SYSTEM_SPEC.md`（整窗收起 hover 展开）。
**可答**：✅ 可答。Galaxy 边界依据 `DECISION_004`。

## Q3：银河（Galaxy）能否承载业务状态？点击行星能直接改 AppState 吗？
**仿真回答**：**不能**。银河是表现层 + 受控交互层（DECISION_004）。状态权威永远在 AppState；Galaxy 经 GalaxyState 只读投影渲染。允许点击行星→能力面板、拖动轨道→调 Goal，但须经 `galaxy-overlay` 叠加层，**不得改银河本体、不得持有可写状态**。
**来源**：`GALAXY_INTERACTION_SPEC.md`（允许/禁止交互）+ `DOMAIN_MODEL.md`（银河隐喻映射）。
**可答**：✅ 可答，明确边界。

## Q4：前端视觉风格用什么令牌/材质？
**仿真回答**：观察到实现令牌——色彩 `--cyan`/`--teal`/`--txt`（暗色基底）、玻璃拟态材质（`.zz-panel-*`/`.chat-panel-*`）、面板缓动 `cubic-bezier(.16,1,.3,1)`。确切 hex 值与完整令牌表在 `xiao6-ui/styles.css`（实现文件）。
**来源**：`DESIGN_SYSTEM_SPEC.md`（索引实现令牌，明示不重定义）。
**可答**：⚠️ 部分可答——风格与索引可答，但**确切令牌值须读 styles.css**（Design Canon 不复制实现值，符合解释层纪律）。此为预期缺口，非失败。

## Q5：设计层文档（Design Canon）的权威层级是什么？能否覆盖 Golden State？
**仿真回答**：Design Canon 是**设计解释层，不属于 L0/L1 权威层**；它只解释/索引，明确「不覆盖、不替代」Golden State / Decision / Governance。任何冲突以 Golden State 优先。
**来源**：每份 Canon 头部纪律声明 + `AI_DESIGN_CONTEXT.md`（定位声明）+ `DESIGN_CONFLICT_REGISTER.md`（CONFLICT-001 记录与治理层级文档的待确认冲突）。
**可答**：✅ 可答，且自我约束清晰。

## Q6：若发现历史设计冲突，新 AI 应怎么做？
**仿真回答**：**不自行裁决**。查 `DESIGN_CONFLICT_REGISTER.md`；若未登记且需裁决，登记新条目（状态 PENDING）并等待主理人确认。例如 CONFLICT-001 已登记「治理层级文档零命中声明 vs 新建 Design Canon」，等待主理人确认后修订治理文档。
**来源**：`DESIGN_CONFLICT_REGISTER.md` + `AI_DESIGN_CONTEXT.md`（给 AI 的提醒）。
**可答**：✅ 可答，流程明确。

---

## 仿真结论
- 6/6 问题均可从 Bootstrap + Governance + Design Canon 获得**正确且权威可追溯**的回答。
- 唯一缺口（Q4）：确切视觉令牌值需读实现文件 styles.css——这是**解释层纪律的应有结果**（不重定义实现），非交接失败。
- Design Canon 作为「设计解释层」成功达成目标：新 AI 能在不读源码/不读全部 v2 草案的情况下，建立正确的小6设计心智模型，并知道冲突时回退到何处。

> 本仿真证明 B2/B3 交付物具备「可交接性」。CONFLICT-001 待主理人确认后将进一步提升治理一致性。
