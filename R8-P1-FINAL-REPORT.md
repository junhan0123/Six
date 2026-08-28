# Xiao6 v1.0.0 R8-P1 Agent Reliability Validation — FINAL REPORT

> 阶段目标：验证 Runtime 在真实复杂任务下的稳定性（R8-P0 执行链已恢复）。
> 本阶段只增加观测（Execution Trace）+ 建立基准测试，未修改 UI / 未新增功能 / 未重构 Execution Core /
> 未绕过 ExecutionPolicy / 未直连 execute_tool。
>
> 状态：**全部完成**。按任务要求停止；未执行 UI 恢复 / 版本升级 / Git 清理。

---

## 一、结论

| 验证项 | 结果 |
|---|---|
| A. 单工具（calculator / get_time） | ✅ 各 10/10 成功，延迟 0.28–0.56 ms |
| B. 多步骤 Goal（submit→plan→Policy→run→Tool→Verify→completed） | ✅ Goal #7 → completed（46.5s，2/2 tasks done） |
| C. Failure Recovery（exception / timeout / policy deny） | ✅ 10/10 项通过（含 2 项已知问题观测） |
| Execution Trace | ✅ 38 条记录，字段完整（goal_id/task_id/step_id/tool/args摘要/duration/status/error/recovery_action） |
| 观测不改变执行逻辑 | ✅ 验证通过（修复了一处开发期 trace 调用错误后，执行结果与无埋点完全一致） |

**当前 Runtime 评级：B+（可靠，但存在 1 个需修复的故障掩蔽缺陷，见 §六）**

---

## 二、任务 1：统一 Execution Trace（纯观测）

### 2.1 交付物
- `xiao6-ui/ai_core/execution/trace.py` —— 单一 trace 记录器（JSONL 落盘 `logs/execution_trace/trace_YYYYMMDD.jsonl`）
  - `record()`：写一条记录（任何异常静默吞掉，**绝不影响执行主链路**）
  - `begin()/end()`：起止配对（自动算 duration）
  - `recent()/clear()`：报告/测试读取与清理
  - args 摘要脱敏（token/secret/password/api_key 等键 → `***`）+ 200 字符截断
- 埋点（仅观测，未动任何控制流）：
  - `ai_core.execution.api.run()`：入口计时 + 4 个终态点（block / rejected / ok|failed / exception）各写 1 条
  - `agent_runtime._execute_task()`：policy block / 审批拒绝 / 网络重试 / 换工具 / 快速失败 / 重试耗尽 各写 1 条（含 recovery_action），并把 `task_id`/`step_id` 透传入 run() 上下文使整链可串联
- 记录字段：`goal_id / task_id / step_id / tool_name / args_summary / start_time / end_time / duration_ms / status / error / recovery_action / execution_id / attempt / decision`

### 2.2 Execution Trace 示例（真实记录）

**① 多步骤 Goal #7 完整链路（B 套件，2 条 ok 记录）**
```json
{"execution_id": "f3b5730f", "goal_id": 7, "task_id": 16, "step_id": "16",
 "tool_name": "calculator", "args_summary": "{\"expression\": \"21*2\"}",
 "start_time": "2026-08-28T19:56:59.305", "end_time": "2026-08-28T19:56:59.306",
 "duration_ms": 0.05, "status": "ok", "error": null,
 "recovery_action": "none", "attempt": 0, "decision": "auto"}
{"execution_id": "0b870202", "goal_id": 7, "task_id": 15, "step_id": "15",
 "tool_name": "get_time", "args_summary": "{}",
 "duration_ms": 0.05, "status": "ok", "recovery_action": "none", "decision": "auto"}
```
（calculator 收到真实 args `{"expression": "21*2"}`——参数契约在 Goal 链路同样成立）

**② Policy 硬阻断（run_shell 危险参数）**
```json
{"tool_name": "run_shell", "args_summary": "{\"command\": \"rm -rf /\"}",
 "status": "blocked", "error": "Policy blocked: 危险命令被拦截（sandbox.is_dangerous_command）",
 "recovery_action": "policy_blocked", "duration_ms": 0.03}
```

**③ 网络故障 → 退避重试（路由器观测）**
```json
{"goal_id": 999174, "task_id": 101, "tool_name": "__r8_net_flaky__",
 "status": "failed", "error": "simulated network failure",
 "recovery_action": "retry_with_backoff", "attempt": 1, "duration_ms": 200.52}
```

**④ confirm 无 Goal 快速拒绝**
```json
{"tool_name": "__r8_confirm__", "status": "rejected",
 "error": "Approval rejected: reject", "recovery_action": "fail_closed_no_retry"}
```

**全量统计（本运行 38 条）**：status → ok×25 / failed×9 / blocked×3 / rejected×1；
recovery_action → none×26 / retry_with_backoff×5 / policy_blocked×3 / fail_closed_no_retry×3 / retry_alternative_tool×1。

---

## 三、任务 2：tests/r8_agent_benchmark/ 基准套件

```
tests/r8_agent_benchmark/
├── __init__.py                 # 套件说明
├── _fixture.py                 # Probe（记 args/调用次数）+ ToolRegistry（合成工具注册/还原）+ check/warn
├── test_a_single_tool.py       # A. 单工具
├── test_b_multi_step_goal.py   # B. 多步骤 Goal
├── test_c_failure_recovery.py  # C. Failure Recovery
└── run_benchmark.py            # 全量入口（python tests/r8_agent_benchmark/run_benchmark.py）
```

### A. 单工具测试
| 工具 | 结果 | 延迟 min/avg/max（10 次） |
|---|---|---|
| calculator（`21*2`） | ✅ 10/10 成功，参数真实到达 | 0.31 / 0.35 / 0.40 ms |
| get_time | ✅ 10/10 成功，返回真实时间 | 0.33 / 0.37 / 0.42 ms |

另验证：trace 已为二者落盘（status=ok、字段完整）。

### B. 多步骤 Goal 测试（Goal #7）
链路 `submit_goal → plan_goal（LLM 拆解 2 tasks）→ ExecutionPolicy（Plan Gate + evaluate）→ run() → Tool → 观察/评估（Verify）→ completed`：
- ✅ goal 收敛 `completed`（round_status=COMPLETE），wall-time **46.5s**（含 LLM 拆解/反思）
- ✅ 2/2 tasks done（calculator + get_time）
- ✅ 观察缓冲两条成功执行；trace 2 条 ok 记录且带 task_id 串联
- 无头环境使用设计内 GDE 预批准通道 `policy_engine.pre_approve_tools`（per-goal 隔离），非绕过 Policy

### C. Failure Recovery 测试（10/10）
| 模拟 | 验证结果 |
|---|---|
| ERROR_TAXONOMY | ✅ 17 类分类全部正确（network/timeout/file/permission/tool_missing/skill/mcp/computer/parse/serialization/validation/resource + 4 合成标记 budget/depth/injection/policy + unknown） |
| tool exception（network 类，run() 级异常） | ✅ Recovery Router 短退避重试，3 次内恢复成功（calls=3）；trace 记录 retry_with_backoff×2 |
| 重试耗尽 | ✅ 4 次（_MAX_RETRIES+1）后 FAIL CLOSED：category=network, attempts=4 |
| timeout | ✅ 分类 timeout、快速失败不重试（attempts=1）—— 见已知问题 #2 |
| file 异常 | ✅ 换替代工具重试成功（file → get_time），trace 记录 retry_alternative_tool |
| policy deny（NEVER 工具，路由器级） | ✅ 执行前拦截：blocked=True，run 调用 0 次 |
| policy deny（confirm 无 Goal） | ✅ 快速拒绝（decision=confirm_rejected），工具函数 0 次调用；trace status=rejected |
| policy deny（run_shell 危险参数） | ✅ 硬阻断（`rm -rf /` → block），命令未执行 |
| policy deny（kill_process NEVER 名单） | ✅ run() → block |
| 真实工具异常（观测项） | ⚠️ 观测：execute_tool 吞异常为失败串，_execute_task 仍报 ok=True —— 见已知问题 #1 |

---

## 四、观测纯度验证

- trace.record() 全程 try/except，IO/序列化失败静默——开发期发现一处调用点把 `decision` 当关键字传入导致 TypeError 冒泡改变了 run() 返回值（calculator 被误判失败），**已修复**；修复后回归验证 calculator/get_time 结果与未埋点时完全一致。
- `agent_runtime` 补模块级 `import time` 并移除 except 分支内的局部 `import time`（局部导入使 `time` 成为函数级局部变量，与埋点引用冲突，曾导致 UnboundLocalError）——修复后 Goal 执行恢复正常（该错误系埋点引入，非 Runtime 原有缺陷）。
- 所有合成工具经 `tools.TOOL_FUNCS` 注册/还原，执行仍走真实 `run() → Policy → execute_tool`，未绕过任何门。

---

## 五、Benchmark 汇总

```
  PASS  A 单工具                    0.0s
  PASS  B 多步骤 Goal               46.5s
  PASS  C Failure Recovery       0.9s
  Total: 47.4s | Execution Trace 记录: 38 条
  Overall: ALL PASS ✅
```

---

## 六、当前 Runtime 评级：B+（可靠）

| 维度 | 评级 | 依据 |
|---|---|---|
| 执行链完整性 | A | Chat→Runtime→run()→Policy→Tool→Verify 全链路真实走通（R8-P0 恢复 + 本阶段复验） |
| 单工具可靠性 | A+ | 20/20 成功，sub-ms 延迟，零漂移 |
| 多步骤 Goal 收敛 | B+ | completed（2/2 tasks），但 wall-time 46.5s 主要消耗在 LLM 拆解/反思，无并行 |
| Policy 门 | A | never / 危险参数 / confirm 无 Goal / 高危能力（PermissionGuard HIGH deny）全部执行前拦截，工具 0 调用 |
| Recovery Router | B- | network 退避重试与 file 换工具有效；但故障掩蔽使 Router 在真实工具失败时**不触发**（见 #1） |
| 可观测性 | A | 38 条 trace，10 字段完整，脱敏 + 失败不冒泡 |

---

## 七、已知问题（本阶段验证发现，未在本阶段修复）

1. **故障掩蔽（failure masking，严重度：高）**
   `tools.execute_tool` 把工具异常吞成 `"工具执行失败：{e}"` 字符串；`agent_runtime._execute_task` 对 `run()` 返回值**不检查 success 标志**，一律返回 `ok=True`。后果：工具真实失败的任务被标记为 done，Goal 可能以「失败步骤计为成功」收敛。同时导致 Recovery Router 的异常分支对真实工具异常**永远不可达**（仅 run() 级基础设施异常可触发）。建议下一阶段：`_execute_task` 检查 `result["success"]`，失败时按 result 分类走 ERROR_TAXONOMY/重试。
2. **timeout 分类与路由器实现不一致（严重度：低）**
   `_FATAL_ERROR_CATEGORIES` 注释称 timeout 属可重试瞬时类，但路由器仅重试 network / file，timeout 落入「快速失败」分支（attempts=1）。当前行为本身安全（FAIL CLOSED），仅文档/意图不一致。
3. **多步骤 Goal 拆解质量波动（严重度：观察）**
   同一目标在重复实验中曾拆出 10 个 task（LLM 拆解不稳定）；本阶段以 2-task 收敛成功。规划步数上限（_MAX_STEPS=16）未触发，属 LLM 提示词层问题。

---

## 八、变更文件

**修改（2）**：`xiao6-ui/agent_runtime.py`、`xiao6-ui/ai_core/execution/api.py`（均为纯观测埋点 + 埋点所需 `import time` 整理；无执行逻辑变更）
**新增（3）**：`xiao6-ui/ai_core/execution/trace.py`、`xiao6-ui/tests/r8_agent_benchmark/`（6 文件）
**生成物**：`xiao6-ui/logs/execution_trace/trace_20260828.jsonl`（38 条，随运行追加）

```
$ git -C G:\xiao6 diff --stat -- xiao6-ui/ai_core/execution/api.py xiao6-ui/agent_runtime.py
 xiao6-ui/agent_runtime.py         | 49 +++++++++++++++++++++++++++++++---
 xiao6-ui/ai_core/execution/api.py | 55 ++++++++++++++++++++++++++++++++++++---
 2 files changed, 96 insertions(+), 8 deletions(-)
```

---

## 九、按任务要求未执行（等待下一阶段）

- ❌ UI 恢复
- ❌ 版本升级
- ❌ Git 清理
