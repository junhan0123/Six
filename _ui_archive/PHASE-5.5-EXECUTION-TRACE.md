# PHASE 5.5 — EXECUTION TRACE (STEP 6)

> 模式：READ-ONLY / VERIFY-BEFORE-DOCUMENT / ZERO WRITE
> 所有结论基于真实源码 + 真实 live import + 安全 dry-run（不执行任何工具）。
> 审计对象：G:\xiao6\xiao6-ui

## 0. 真实执行拓扑（已确证）

小6 存在 **三条收敛到同一执行内核的执行路径**，全部经过 `ai_core.execution.run` 的 policy 门：

```
(A) 默认 Chat 路径：
   POST /api/chat → server_handlers_chat._handle_chat (server_handlers_chat.py:300)
     → run_fc_loop (tools.py:3363)
     → execute_tool_calls (tools.py:3291)
     → capability_runtime.execute (capability_runtime.py:147)   ← 默认 Chat 唯一收敛点
     → ai_core.execution.run (ai_core/execution/api.py:31)       ← POLICY 门
     → tools.execute_tool (tools.py:3990) → TOOL_FUNCS[name]

(B) Computer Action 路径（白名单受限）：
   /api/action/execute → os_bridge.action_execute (os_bridge.py:815)
     → permission_guard.PermissionGuard (os_bridge.py:11, 唯一入口)
     → computer_action.executor.ComputerExecutor.execute (executor.py:44)
     → safety.assert_allowed (safety.py:87)  ← 白名单闸门
     → _op_* 

(C) Goal / Planning 路径：
   chat → GoalDecisionEngine.ingest (goal_decision_engine.py:71) → classify C → create
     → agent_runtime.submit_goal (agent_runtime.py:82)
     → goals.plan_goal (goals.py:464)  ← LLM 拆解任务
     → agent_runtime._llm_dispatch (agent_runtime.py:866)
     → policy_engine.evaluate (GOAL mode) (agent_runtime.py:413)
     → tools.execute_tool
```

**关键修正（相对 handoff 假设）**：
- `capability_os.matcher` / `router` / `compose` **不在** LLM 热路径上。它们是
  `server_handlers_capability.py` 的 `/api/capability_os/match`(L48/L59) 与
  `/api/capability_os/plan`(L66/L77) **API 级能力建议/编排服务**，喂给 advanced
  feature `capability-os` 与外部。Chat 真实入口是 LLM function-calling + `tool_to_capability`。
- `ai_core/execution.py` 实为包 `ai_core/execution/`，主入口 `api.py:31 run()`。
- `zz-workspace.js` 真实路径为 `xiao6-space/js/zz-workspace.js`（handoff 写的
  `xiao6-ui/zz-workspace.js` 路径已失效/迁移）。

---

## TRACE A — 普通信息能力（"现在几点了" → get_time）

| # | 问题 | 回答 |
|---|------|------|
|1|入口|POST /api/chat → server_handlers_chat._handle_chat (server_handlers_chat.py:300) → run_fc_loop|
|2|Intent 分类|LLM function-calling 选工具；服务端兜底 detect_intents (tools.py:3600)|
|3|Context 来源|context/facade.build_context_prompt (facade.py:33) → LegacyContextBuilder；能力上下文经 capabilities.active_capability_blocks 注入（hotspot/prefetch/computer_action）|
|4|Matcher 调用|Chat 热路径**不调** matcher；若强制 capability_os.match("现在几点") → 返回 time(score=3, blocked=False)【dry-run 已证】|
|5|Capability ID|time（tool_to_capability("get_time")→"time"）|
|6|Planner 介入|否（单工具调用）|
|7|Tool ID|get_time（TOOL_FUNCS["get_time"] 已确认存在）|
|8|Policy 评估|ai_core.execution.run (api.py:31) permission=NONE → policy_engine.evaluate("get_time")→AUTO（在 READONLY_TOOLS）【dry-run: get_time→auto】|
|9|Executor|tools.execute_tool (tools.py:3990) → TOOL_FUNCS["get_time"](args)|
|10|Verification|capability_os.verification.verify_capability("time")（预期 READY）；执行期 audit + ExecutionEvent/metrics|
|11|最终结果|返回当前时间字符串，成功|
|12|断点|无|

---

## TRACE B — memory / knowledge（"记住这个" / "查一下知识库"）

| # | 问题 | 回答 |
|---|------|------|
|1|入口|POST /api/chat → run_fc_loop（同 A）|
|2|Intent 分类|LLM 选 remember / memory_search / knowledge_search|
|3|Context 来源|facade.build_context_prompt（同 A）|
|4|Matcher 调用|不调（chat 热路径）|
|5|Capability ID|memory（tool memory_search）／ knowledge（builtin knowledge.search，knowledge.py:43 def search 已确认）|
|6|Planner 介入|否|
|7|Tool ID|remember / memory_search / knowledge_search（均在 TOOL_FUNCS）|
|8|Policy 评估|ai_core.execution.run → policy_engine.evaluate；readonly→auto，否则无 Goal→confirm 模态|
|9|Executor|TOOL_FUNCS[name]（memory）／ builtin knowledge.search（knowledge）|
|10|Verification|verify_capability("memory")（tool memory_search callable→READY）；verify_capability("knowledge")（builtin knowledge.search 存在→READY/PARTIAL 待 live 确认 hasattr）|
|11|最终结果|记忆写入/召回 或 知识检索返回|
|12|断点|无|

---

## TRACE C — computer action（"打开记事本" / read_file）

| # | 问题 | 回答 |
|---|------|------|
|2|Intent 分类|UI action 面板选能力，或 GDE 分类；capability_os.match("打开记事本")→computer_action(score=1, blocked=False, perm=confirm)【dry-run 已证】|
|3|Context 来源|action_plan 生成预览（observe→plan→confirm→execute 四态）；能力上下文注入|
|4|Matcher 调用|capability_os.match（API 级）返回 computer_action（confirm）|
|5|Capability ID|open_application（WHITELIST op）或 computer_action 总览|
|6|Planner 介入|os_bridge.action_plan (os_bridge.py:765) → permission_guard 规划（可选 computer_action/planner.py）|
|7|Tool ID|非 TOOL_FUNCS 工具；为 computer_action 白名单 op "open_application"（safety.py:28 WHITELIST 已含）|
|8|Policy 评估|safety.assert_allowed (safety.py:87) 白名单+风险闸门；MEDIUM→needs_confirm→policy_engine.request_approval (safety.py:101)|
|9|Executor|computer_action.executor.ComputerExecutor.execute (executor.py:44) → _dispatch → _op_open_application (executor.py:84)|
|10|Verification|safety 闸门 + verifier；verify_capability("open_application")（computer_action 在 WHITELIST→callable→READY/PARTIAL）|
|11|最终结果|应用被打开，状态展示四态|
|12|断点|无（白名单内 op）。注：read_file 实为 flat tool `file_read`（capability read_file→tool file_read，亦在 _READONLY_ALLOWED），走 Chat 路径而非 computer_action 白名单 op——handoff 将 read_file 表述为 computer_action 不够精确，此处按真实代码记录|

---

## TRACE D — goal / planning（"调研一下竞品"）

| # | 问题 | 回答 |
|---|------|------|
|1|入口|chat 消息 → GoalDecisionEngine.ingest (goal_decision_engine.py:71)（GDE 在 goal/agent 管线中被调用）|
|2|Intent 分类|GDE 确定性分类（LONG_VERBS 含"调研"）→ C 长任务 → create（auto_threshold 0.55）(goal_decision_engine.py:142,105)|
|3|Context 来源|build_cognitive_context (facade.py:62) 供 Planner|
|4|Matcher 调用|GDE 不调 matcher；plan_goal 用 LLM + 工具清单|
|5|Capability ID|goals（tool set_goal，TOOL_FUNCS 已确认）|
|6|Planner 介入|是 — goals.plan_goal (goals.py:464) → LLM 拆解为 tasks（工具清单=TOOL_FUNCS+external.mcp.*+skills）|
|7|Tool ID|set_goal（建目标）+ 后续任务工具|
|8|Policy 评估|agent_runtime._llm_dispatch (agent_runtime.py:866) → policy_engine.evaluate (GOAL mode: block/confirm) (agent_runtime.py:413)；GDE.submit 调 pre_approve_tools (goal_decision_engine.py:228)|
|9|Executor|tools.execute_tool 经 ai_core（GOAL perm→policy 门）|
|10|Verification|capability verification + task 结果；ExecutionEvent/metrics|
|11|最终结果|目标创建→计划任务→在 policy 下执行|
|12|断点|无（合法目标）|

---

## TRACE E — BLOCKED capability（delete / system / network）— **仅 dry-run / policy 追踪，未执行任何危险操作**

| # | 问题 | 回答 |
|---|------|------|
|1|入口|capability_os.match（server_handlers_capability._handle_capability_match:48/59）dry-run|
|2|Intent 分类|goal "删除所有文件" / "修改系统设置"|
|3|Context 来源|无需|
|4|Matcher 调用|capability_os.match("删除所有文件")→ delete(score=1, **blocked=True, perm=block, avail=False**)【dry-run 已证】；match("修改系统设置")→ system(blocked=True, perm=block)|
|5|Capability ID|delete / system / network（均为 CRITICAL，registry dump: avail=False, perm=block）|
|6|Planner 介入|无（在语义层即被拒）|
|7|Tool ID|不可达。file_delete 工具存在但 policy NEVER；delete/system/network **无对应 TOOL_FUNCS 键、无 computer_action 白名单项**|
|8|Policy 评估|**三重闸门全部命中**：(a) matcher blocked=True；(b) router.route→blocked=['delete'], **safe_to_execute=False**【dry-run 已证】；(c) policy_engine.evaluate("file_delete")→**block**「永久禁止名单」；evaluate("kill_process")→**block**【dry-run 已证】|
|9|Executor|NONE — execution_mapping kind="none" → executor_callable=False（verify_capability→BLOCKED）|
|10|Verification|verify_capability("delete")→BLOCKED（avail=False/perm=block）|
|11|最终结果|**永不进入执行路径**；在语义层(matcher/router) + 工具层(policy NEVER) + 执行体层(none) 三重拦截|
|12|断点|**无**——这正是预期的安全行为，不存在危险断点。证明 BLOCKED 能力不会落入危险执行路径|

### dry-run 实测输出（节选，未执行任何工具）
```
[删除所有文件]
  computer_action  score=1 blocked=False perm=confirm
  delete           score=1 blocked=True  perm=block
  route.blocked=['delete'] safe=False
[修改系统设置]
  system  score=2 blocked=True perm=block ; route.blocked=['system'] safe=False
policy_engine.evaluate no-goal:
  file_delete  -> block   工具已被列入永久禁止名单
  kill_process -> block   工具已被列入永久禁止名单
  read_file    -> auto    只读/低危工具，自动执行
```
