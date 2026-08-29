# AI Onboarding Test

> 新 AI 入职测试 | 验证是否真正理解 Xiao6。
> 用法：新 AI 接手前自测；答案附于每题下方（折叠式）。覆盖：项目定位 / 架构原则 / Runtime 规则 / Event 规则 / Memory 规则 / Policy 规则 / Phase 规则 / 开发流程。
> 及格线：30 题中答对 ≥ 27（90%）。

---

## 一、项目定位（Q1–Q4）

**Q1. Xiao6 是什么？**
<details><summary>答案</summary>本地优先的「贾维斯」式中文 AI 助手（阿枢的具象化方向之一），定位为 Local Personal AI Operating System（本地个人 AI 操作系统）。纯本地 git，后端 server.py + 前端 xiao6-ui（原生 JS/Three.js），Electron 包装。</details>

**Q2. 大脑与语音分别是什么？**
<details><summary>答案</summary>大脑 = Agnes API；语音 = FunASR(ASR) + edge-tts(TTS)；世界态势接 GDELT/USGS/OpenSky/Open-Meteo（免费无 key）。代理 XIAO6_PROXY_URL 需先开 Clash 才能访问 Agnes。</details>

**Q3. 当前完成到哪个版本 / 阶段？**
<details><summary>答案</summary>Version v1.0；已完成 Phase 6（统一 Runtime）/ 7（Computer Operating Layer）/ 8（Computer Perception MVP）。Phase 9 待设计批准。</details>

**Q4. 当前系统稳定性状态（Golden State）如何？**
<details><summary>答案</summary>Architecture / Runtime / Event Contract / Memory / Policy / State 全 FROZEN；Tests PASS（28 文件全绿）；Documentation COMPLETE。详见 docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md。</details>

## 二、架构原则（Q5–Q10）

**Q5. 通信的唯一机制是什么？**
<details><summary>答案</summary>EventBus（eventbus.py）。所有跨模块通信必须发领域事件；publish_domain/publish_system 对未登记名抛 ValueError。</details>

**Q6. 状态唯一写入口是什么？**
<details><summary>答案</summary>AppState（app-state.js）的 applyEvent → reducers。无 reducer 的事件仍 emit('*') 但不改状态。任何状态变更必须经此。</details>

**Q7. 唯一权限来源是什么？**
<details><summary>答案</summary>PolicyEngine + PermissionGuard。高风险动作必须经 PermissionGuard 校验，风险等级映射 RISK_TIER。</details>

**Q8. 唯一记忆来源是什么？**
<details><summary>答案</summary>memory.py。禁止第二 Memory 系统，禁止绕过 Memory System 直接写文件。</details>

**Q9. 有多少个 Runtime？分别是什么？**
<details><summary>答案</summary>决策运行时 1 个（AgentRuntime）；观察生产者 2 个（CaptureRuntime / PerceptionRuntime，仅采集/感知，不做决策）。禁止第二 Runtime。</details>

**Q10. 前端状态层结构是怎样的？**
<details><summary>答案</summary>权威核心 1（AppState，11 子树）+ 只读投影 4（GalaxyState / OverlayRuntime / ComputerState / PerceptionState）。投影层只订阅、不回写。</details>

## 三、Runtime 规则（Q11–Q15）

**Q11. 为什么不能创建第二 Runtime？**
<details><summary>答案</summary>EventBus 是唯一模块通信机制，第二 Runtime 会脱离事件流与权限校验，造成架构漂移与不可控决策。见 DECISION_002。</details>

**Q12. CaptureRuntime / PerceptionRuntime 能直接决策吗？**
<details><summary>答案</summary>不能。它们是观察生产者，采集/感知后发事件到 EventBus，由 AgentRuntime 统一决策。Perception 永远只能 Observation，绝不能 Control。</details>

**Q13. AgentRuntime 的状态机是什么？**
<details><summary>答案</summary>IDLE → PLANNING → EXECUTING → REFLECTING，反射阶段 emit REFLECTING 并调用 reflect()。任何决策必须在其内。</details>

**Q14. 为什么不能直接调用 Executor？**
<details><summary>答案</summary>因为必须经 PermissionGuard 权限校验与规划流程；直接调用会绕过安全网。见 AI_HANDOFF_PROTOCOL 永久禁止清单。</details>

**Q15. Vision 模块能控制电脑吗？**
<details><summary>答案</summary>绝对不能。Vision 仅输出 Observation（图标/图片/非文本事实），永不产生 Action；error_dialog 等仅发 perception_alert 提醒。这是安全红线。</details>

## 四、Event 规则（Q16–Q20）

**Q16. 当前事件契约规模是多少？**
<details><summary>答案</summary>DOMAIN_EVENT_NAMES = 71，SYSTEM_EVENT_NAMES = 8，前后端逐字一致。</details>

**Q17. 为什么不能直接 import 另一个模块而不发事件？**
<details><summary>答案</summary>这绕过 EventBus 单一通信，属 Event Drift；会造成模块耦合、状态不一致、无法审计。见 ARCHITECTURE_DRIFT_CHECK Event Drift 段。</details>

**Q18. 新增事件的正确流程是什么？**
<details><summary>答案</summary>同时修改 eventbus.py（DOMAIN/SYSTEM 集合）与 zz-events.js（EVENTS/SYSTEM_EVENTS），逐字对齐；未登记名会被 publish 拒绝（ValueError 安全网）。</details>

**Q19. 前端是否能收到未登记事件？**
<details><summary>答案</summary>不能。两端契约逐字绑定；zz-events.js 未登记的事件名在前端不存在，后端 publish 未登记名会抛错。这是防漂移的双向校验。</details>

**Q20. Perception 相关新增了哪些事件？**
<details><summary>答案</summary>5 个 DOMAIN：PERCEPTION_SYNC / PERCEPTION_UI_UPDATED / PERCEPTION_OCR_UPDATED / PERCEPTION_VISION_FACT / PERCEPTION_FOCUS_CHANGED；2 个 SYSTEM：perception_alert / perception_health。</details>

## 五、Memory 规则（Q21–Q24）

**Q21. 为什么不能创建第二 Memory？**
<details><summary>答案</summary>记忆必须单一来源（memory.py）以保证一致性；第二 Memory 会导致数据分裂、来源不一致、记忆冲突。见 DECISION_003。</details>

**Q22. Memory 系统包含哪些层次？**
<details><summary>答案</summary>短期/工作/长期/项目/知识分层，均以 memory.py 为单源。Phase 9 可借鉴 LangChain Memory 思想但不引入其运行时。</details>

**Q23. 绕过 Memory System 直接写文件有什么后果？**
<details><summary>答案</summary>属 Memory Drift；记忆不可追溯、无法被 Agent 统一读取，破坏「记忆单一来源」红线。</details>

**Q24. MEMORY_LINKED 与知识关联是什么关系？**
<details><summary>答案</summary>KNOWLEDGE_LINKED 与已冻结的 MEMORY_LINKED 重复，已被合并（单一来源纪律）；知识关联复用 MEMORY_LINKED，不新增第二事件。</details>

## 六、Policy 规则（Q25–Q28）

**Q25. 权限逻辑可以分散在多个模块自行判断吗？**
<details><summary>答案</summary>不可以。权限逻辑必须集中在 PermissionGuard + PolicyEngine；分散判断属 Policy Drift，会造成放行不一致。</details>

**Q26. 高风险动作执行前必须经过什么？**
<details><summary>答案</summary>PermissionGuard 校验（基于 PolicyEngine 的 RISK_TIER 风险等级）。未经校验不得执行。</details>

**Q27. 能否在测试里临时绕过 Permission 验证逻辑？**
<details><summary>答案</summary>不能在生产路径绕过；测试可用 Mock/单例注入，但不得修改 PermissionGuard 校验逻辑本身（Policy FROZEN）。</details>

**Q28. LangChain / AnythingLLM 能直接引入吗？**
<details><summary>答案</summary>不能引入其运行时；仅可借鉴 Tool Registry / Chain / Memory / Workspace 思想，运行在既有 AgentRuntime 内。见 DECISION_006。</details>

## 七、Phase 规则（Q29–Q32）

**Q29. 为什么不能直接进入 Phase 9？**
<details><summary>答案</summary>因为必须经过设计审批流程：Design → Approval → Implementation。Phase 9 Step 0 已完成对齐报告，须等 Step 1 设计批准方可实现。</details>

**Q30. Phase 的推进纪律是什么？**
<details><summary>答案</summary>Audit → Analysis → Design → Approval → Implementation → Test → Report → Freeze。完成即停止，等待批准进入下一阶段；禁止边改边推翻。</details>

**Q31. Phase 8 与 Phase 9 的边界是什么？**
<details><summary>答案</summary>Phase 8 = 让小6「看到电脑状态」（感知层，Observation）；Phase 9 = 让小6「理解用户工作并组织上下文」（认知编排层，消费感知但不改其架构）。Phase 9 不重新做 Agent、不替换 AgentRuntime。</details>

**Q32. 当前是否已冻结、能否随意加功能？**
<details><summary>答案</summary>Phase 6/7/8 已冻结；Golden State 为最高权威。新增功能须走 Freeze Rule（Decision → Design → Approval → ...），禁止随意扩展或 Silent Change。</details>

---

> 评分：答对 ≥ 27/30 视为具备接管能力。未达标的新 AI 必须先读 AI_BOOTSTRAP.md 与 ARCHITECTURE_MAP.md，并重读 docs/decisions/DECISION_001..006.md。
