# Xiao6 v1.0.0 R8-P3 API Surface Repair — FINAL REPORT

> 阶段目标：恢复 UI/API → Agent Runtime 的完整控制链（只修 API 表面，不修改 Runtime 内核）。
>
> 状态：**全部完成，API 套件 ALL PASS ✅ + 全量基准回归 ALL PASS ✅**。
> 未修改 ai_core.execution.run() / Policy / PermissionGuard / Runtime 编排；未执行 UI 重做。
> 按任务要求停止；未执行 UI 恢复 / 版本修改 / Git 清理。

---

## 一、调查结论（任务 1：悬空 API 根因）

| 端点 | 路由注册 | Handler 定义 | 结论 |
|---|---|---|---|
| POST `/api/agent/goal` | `server.py do_POST` L854-855 已注册 | **全仓库历史从未定义** | 悬空引用 → 请求时 AttributeError → 500 |
| POST `/api/agent/intent` | `server.py do_POST` L856-857 已注册 | **全仓库历史从未定义** | 同上 |
| POST `/api/agent/approval` | `server.py do_POST` L858-859 已注册 | **全仓库历史从未定义** | 同上 |

`git log -S 'def _handle_agent_approval'` 全历史无结果——自拆分前（S76 单体 server.py）起
这三个端点就是悬空引用：路由存在、Handler 从未实现。R8-P3 将其恢复，路由层零改动。

真实 Runtime 调用关系（本阶段接入的系统）：
- **GoalSystem**：`agent_runtime.runtime.submit_goal(title, description, intent_id)` → `goals.create_goal`（唯一写出口，内部同步发 GOAL_CREATED）→ 编排队列 → PLANNING/EXECUTING。
- **IntentGateway**：`intent_gateway.run_intent_gateway(text, source)` → `GoalDecisionEngine.ingest`（确定性规则 + mid 带 LLM 辅助）→ `engine.submit` → `runtime.submit_goal`；Intent 生命周期事件经 `publish_domain` 单一来源。
- **Approval 流程**：`policy_engine.request_approval` 生成 ticket + 弹 modal + `ev.wait` 挂起 → `policy_engine.resolve(ticket, decision)` 唤醒（该函数注释即写明「POST /api/agent/approval 调用」）。
- UI 契约（冻结快照 `_audit/…/zz-workspace.js`）：`POST /api/agent/approval?ticket=<t>&decision=<approve|reject>`。

---

## 二、修复方式（任务 2：恢复 Handler，全部经既有系统，禁止直连工具）

修改文件：`xiao6-ui/server_handlers_system.py`（SystemMixin，紧邻既有 `_handle_agent_state`），+87 行，无删改：

```python
def _handle_agent_goal(self):
    """POST /api/agent/goal — 提交目标到 Agent Runtime（GoalSystem 单一路径）。"""
    # FEATURE_AGENT_RUNTIME 门控 → 404 disabled
    # payload = self._read_json() → "_error" → 400；缺 title → 400
    # runtime 未运行则幂等 start() → runtime.submit_goal(title, description, intent_id)
    # → 200 {"ok": True, "goalId": int, "title": str}；异常 → 500
    ...
def _handle_agent_intent(self):
    """POST /api/agent/intent — 用户意图经 IntentGateway（GDE 识别/决策 → 建目标）。"""
    # 门控/校验同上；runtime 幂等 start()
    # from intent_gateway import run_intent_gateway
    # → 200 {"ok": True, "intentId", "action", "classification", "confidence", "title", "goalId", "reason"}
    ...
def _handle_agent_approval(self):
    """POST /api/agent/approval — Approval 流程：policy_engine.resolve 唤醒挂起审批单。"""
    # 解析 query：ticket / decision(approve|reject)；非法 → 400
    # policy_engine.resolve(ticket, decision)：未知/过期 → 404；成功 → 200 {"ok": True, ...}
    ...
```

设计要点：
- **API → Agent Runtime 必须经过 GoalSystem / IntentGateway / Approval 流程**——handler 内只出现
  `runtime.submit_goal` / `run_intent_gateway` / `policy_engine.resolve`，**零工具直连**、
  零 `execute_tool`、零 `ai_core.execution.run` 调用（工具执行仍唯一经 Runtime → Execution Core 链）。
- 幂等 `runtime.start()`：保证 API 提交的目标必定被编排执行（无 UI 触发时亦然）。
- 路由层（server.py do_POST）与 UI 审批契约（query 参数）零改动——修复完全落在 Handler 表面。

---

## 三、测试结果（任务 3）

新增 `xiao6-ui/tests/r8_agent_benchmark/test_api_surface.py`（自启服务器子进程 :8033 + 进程内 Handler 直测）。

### A. Approval 流程（进程内，真实 Handler + policy_engine）
```
  [PASS] 审批单已生成（request_approval 挂起）  -> ticket=217f95cb
  [PASS] Handler 返回 200 ok:True
  [PASS] 挂起线程被唤醒且返回 approve          -> verdict=approve
  [PASS] per-goal 批准生效（approve_in_goal）
  [PASS] 未知/过期 ticket → 404
  [PASS] 非法 decision → 400
  [PASS] 缺 ticket → 400
```
闭环验证：`request_approval`（ev.wait 挂起）→ POST approval?ticket=&decision=approve → resolve 唤醒 →
挂起线程返回 "approve" → 该 Goal 的 tool 进入 session 批准集（approve_in_goal）——完整 Approval 流程。

### B. HTTP（真实路由 → Handler → 系统）
```
  [PASS] 服务器启动 /api/health 200
  [PASS] intent 提交（长任务）→ 200            -> action=create
  [PASS] intent create → goalId 非空           -> goalId=11 intentId=int_a1dc6106
  [PASS] intent 响应含意图字段（intentId/classification/confidence/title/reason）
  [PASS] intent 一次性文本 → skip（不建目标）  -> action=skip reason=一次性工具调用，直派不建目标
  [PASS] goal 创建 → 200 ok:True + goalId      -> goalId=12
  [PASS] GET /api/goals/<id> 可查（GoalSystem 落库）
  [PASS] goal 缺 title → 400
  [PASS] goal 非法 JSON → 400
  [PASS] intent 缺 text → 400
  [PASS] approval 未知 ticket（HTTP）→ 404
  [PASS] approval 缺 ticket（HTTP）→ 400
```
- intent 提交：长任务文本（"帮我整理一份本周工作周报并总结项目进展"）确定性命中 GDE create →
  经 `engine.submit → runtime.submit_goal → goals.create_goal` 产出 goalId=11；
  一次性文本（"查一下天气"）命中 skip 不建目标。
- goal 创建：`runtime.submit_goal` → GoalSystem 落库，GET /api/goals/12 可查回读。
- 错误返回：400/404 各路径齐全。

### 全量基准回归（未改动 Runtime，仅确认无回归）
```
  PASS  A 单工具                0.0s
  PASS  B 多步骤 Goal           8.0s
  PASS  C Failure Recovery      0.9s
  PASS  R8-P2 Truthfulness      0.3s
  Overall: ALL PASS ✅
```
测试自启服务器随套件退出正常释放端口 8033，无进程残留。

---

## 四、对 Runtime 状态的影响

| 项 | 状态 |
|---|---|
| UI/API → Agent Runtime 控制链 | ✅ 恢复：goal / intent / approval 三个悬空端点已可用 |
| Runtime 内核 | 零改动（编排状态机 / Execution Core / Policy / PermissionGuard 均未触碰） |
| 工具执行路径 | 不变：仍唯一经 Runtime → ai_core.execution.run() → Policy → Tool |
| 审批闭环 | ✅ resolve 唤醒挂起审批（原有 policy_engine 能力首次有 API 出口） |
| 错误契约 | 明确：400 参数错误 / 404 门控关闭或未知 ticket / 500 内部异常 |

---

## 五、变更文件

| 文件 | 变更 |
|---|---|
| `xiao6-ui/server_handlers_system.py` | +87 行：新增 `_handle_agent_goal` / `_handle_agent_intent` / `_handle_agent_approval`（SystemMixin） |
| `xiao6-ui/tests/r8_agent_benchmark/test_api_surface.py` | 新增：R8-P3 API 测试（进程内 Approval 闭环 + 自启服务器 HTTP 全套） |

```
$ git -C G:\xiao6 diff --stat -- xiao6-ui/server_handlers_system.py
 xiao6-ui/server_handlers_system.py | 87 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 87 insertions(+)
```

---

## 六、按任务要求未执行（等待下一阶段）

- ❌ UI 恢复 / UI 重做（当前 UI 文件未随服务托管，按约束未处理）
- ❌ 版本修改
- ❌ Git 清理
