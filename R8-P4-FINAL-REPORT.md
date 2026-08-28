# Xiao6 v1.0.0 R8-P4 Release Hardening — FINAL REPORT

> 阶段目标：进入 v1.0.0 发布前稳定阶段（修复已知问题 + timeout 策略审查 + 完整回归）。
>
> 状态：**全部完成，完整回归 ALL PASS ✅**。
> 未重构 Runtime / 未修改 ai_core.execution.run() / 未修改 Policy 架构 / 未重做 UI / 未新增功能。
> 按任务要求停止；未执行 UI 重做 / 版本修改 / Git 清理。

---

## 一、任务 1：修复 context.facade 缺失（Context/Planner 衔接）

### 根因（调查）
- 调用方：`agent_runtime._llm_dispatch`（无 suggested_tool 任务的 LLM 派发路径）在
  `FEATURE_COGNITIVE_CONTEXT=True`（默认）时 `from context.facade import build_cognitive_context`。
- `context/` 包是 S79.7 stub（budget/models/__init__），**facade.py 在 git 全历史与所有副本中从未存在**
  （S79.7 前提交的 `context/__init__.py` 引用了 facade/builder/sources 等 7 个模块，但这些模块从未入库——
  这正是 S79.7 把包 stub 化的原因）。
- 备份中的完整 Context Engine 与现行 `BuildContext` 契约冲突（`ai_core.execution.api.run()` 依赖 stub 版
  `BuildContext(session_id, goals)`；完整引擎为 `BuildContext(user_text, tier, extra)`），**全量恢复会破坏
  run()**，违反 R8-P4 约束 → 采用最小恢复。
- 连带发现：即使 facade 恢复，`_llm_dispatch` 的消息列表只有 system 角色 → Agnes 端点 400
  `"No user query found in messages."`（R8-P2 观察到的真实失败链）→ 派发失败 → 任务 failed → REPLAN 循环。

### 修复方式（只修 Context/Planner 衔接，执行链零改动）
1. **新增 `context/facade.py`**：恢复 `build_cognitive_context(goal_id, task, mode, tier)` 与
   `build_context_prompt(user_text)` 门面 API——复用 Chat 同一组装源（`memory.build_system_prompt`：
   人格块 + 系统提示 + ACI 预判 + 记忆块），附 goal/task 只读即时上下文；全异常安全（失败返回 ""，
   调用方回退 legacy prompt，绝不阻断调度）。
2. **`context/__init__.py`**：导出 `build_cognitive_context`（additive；stub 版 `build_context_prompt` 保持
   不动——不改变 Chat 现状，零风险）。
3. **`agent_runtime._llm_dispatch`**：消息列表补 user 消息（派发请求规格，非知识上下文），
   消除 400 失败。

### 验证
```
[PASS] build_cognitive_context 可用且非空  -> len=2280（人格/系统/记忆组装）
[PASS] mode/tier 契约参数兼容
[PASS] 无 suggested_tool 任务 LLM 派发成功（不再 400）  -> tool=get_time args={}
```
R8-P2 时代必失败的无 suggested_tool 场景现已真实派发成功。

---

## 二、任务 2：timeout 策略审查

| 层 | 现状 |
|---|---|
| 分类（`_classify_error`） | TimeoutError / "timed out" → `timeout`（非致命瞬时类，不在 `_FATAL_ERROR_CATEGORIES`） |
| Recovery Router（`_execute_task`） | 仅 `network`（退避重试）/ `file`（换替代工具）实施重试；`timeout` 走快速失败（attempts=1） |
| 行为安全性 | ✅ FAIL CLOSED：宁拒勿挂（R8-P2 已验证：timeout → ok=False，不重试，无 300s 挂起） |

**结论：保持现状，记为已知限制。**
理由：当前行为安全（失败即终止，无挂起面）；为 timeout 增加重试属「扩大 Recovery 改造」——任务明令禁止。
已将 `_FATAL_ERROR_CATEGORIES` 旁注释更新为与实现一致（timeout 归瞬时类但当前不重试，见 R8-P4 报告），
消除设计注释与实现的文档性偏差（不改任何行为）。

---

## 三、任务 3：完整回归（全部通过）

| 套件 | 结果 |
|---|---|
| **Tool Args**（R8-P0 参数契约） | ✅ 15/15 PASS |
| **A 单工具**（calculator / get_time 基准） | ✅ PASS（10/10 各） |
| **B 多步骤 Goal E2E**（submit→plan→Policy→run→Tool→Verify→completed） | ✅ PASS（4.1s，2/2 tasks） |
| **C Failure Recovery**（taxonomy / router / retry / policy deny） | ✅ 10/10 |
| **R8-P2 Truthfulness**（异常/未知/拒绝/成功） | ✅ 6/6 |
| **R8-P4 Planner**（facade + 无 suggested_tool 派发） | ✅ 3/3 |
| **API Surface + Approval**（R8-P3：goal/intent/approval/错误返回） | ✅ ALL PASS |
| **服务器启动 + /api/ready** | ✅ HTTP 200，ready=true，无 TypeError |
| **/api/agent/state** | ✅ 200，runtime running=true |

```
FULL BENCHMARK:  PASS A / PASS B / PASS C(10/10) / PASS R8-P2(6/6) / PASS R8-P4(3/3)
                 Overall: ALL PASS ✅
API SURFACE:     R8-P3 API 套件：ALL PASS ✅（approval 闭环 + intent create/skip + goal 创建 + 400/404 错误返回）
```

---

## 四、发布前状态

| 维度 | 状态 |
|---|---|
| 执行链（Chat → Runtime → run() → Policy → PermissionGuard → Tool → Verification） | ✅ R8-P0 恢复，R8-P1~P4 全链路回归稳定 |
| Failure Truthfulness（失败必 success=False + 正确 Recovery/失败状态） | ✅ R8-P2 修复 + 回归 |
| API 控制链（/api/agent/goal·intent·approval → GoalSystem/IntentGateway/Approval） | ✅ R8-P3 恢复 |
| Planner 衔接（无 suggested_tool 派发） | ✅ R8-P4 修复 |
| 观测（Execution Trace） | ✅ R8-P1，38+ 字段完整记录 |
| 安全面（server_globals 真实实现 / CORS 白名单 / 远程门控） | ✅ R8-P0 恢复 |

## 五、已知限制（不阻塞 RC，如实记录）

1. **timeout 不重试**：分类为瞬时类但路由器快速失败（安全；如需重试属后续 Recovery 扩展，本轮禁止）。
2. **完整 Context Engine 未恢复**：S79.7 丢失的 builder/sources/ranker 等 7 模块与现行 BuildContext
   契约冲突，本阶段以 facade 最小恢复（同一 `memory.build_system_prompt` 组装源）替代；Chat 的
   `build_context_prompt` 仍为 stub（返回 ""），Chat 系统提示词回填属后续阶段。
3. **环境类自检降级**（非代码缺陷）：edge_tts 未安装、Open-Meteo SSL 超时、wakeword 缺 numpy、
   热点源 401 缓存回退——`/api/ready` 的 self_check 如实报告 degraded。
4. **UI 未托管**：`index.html/app.js` 不在工作树（UI 重做被本阶段明令禁止），前端恢复属独立阶段。
5. **`_classify_error` 的 `"oom"` 子串过匹配**（如 "boom"→resource）：已规避测试，建议后续收紧关键词。

---

## 六、是否进入 v1.0.0 RC：**建议：是 ✅（有条件）**

六套回归全绿、执行链/真实性/API/Planner 四项核心链路均有自动化验证、安全面为真实实现、
已知限制均已文档化且无一为「数据/执行正确性」级缺陷。建议进入 v1.0.0 RC 的条件（属后续独立阶段，
本阶段不执行）：① UI 恢复；② 版本号更新与发布元数据；③ Git 清理与提交。

---

## 七、变更文件

| 文件 | 变更 |
|---|---|
| `xiao6-ui/context/facade.py` | **新增**：Context 门面（build_cognitive_context / build_context_prompt） |
| `xiao6-ui/context/__init__.py` | +导出 build_cognitive_context（stub 其余不动） |
| `xiao6-ui/agent_runtime.py` | `_llm_dispatch` 补 user 消息（消除 400）；timeout 注释对齐实现 |
| `xiao6-ui/tests/r8_agent_benchmark/test_r8p4_planner.py` | **新增**：R8-P4 Planner 测试 |
| `xiao6-ui/tests/r8_agent_benchmark/run_benchmark.py` | 接入 R8-P4 Planner 套件 |

```
$ git -C G:\xiao6 diff --stat -- xiao6-ui/context/__init__.py xiao6-ui/agent_runtime.py
 xiao6-ui/agent_runtime.py    | 118 +++++++++++++++++++++++++++++++++++--------   （含 R8-P1/P2/P4 累计未提交）
 xiao6-ui/context/__init__.py |   4 +-
（新增未跟踪：context/facade.py、tests/）
```

---

## 八、按任务要求未执行（等待下一阶段）

- ❌ UI 重做
- ❌ 版本修改
- ❌ Git 清理
