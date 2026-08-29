# PHASE 5.9-P0-1 · STEP 5 — 最小修复点报告

> 小6 Xiao6 v1.4.0 · CHAT CONFIRM POLICY CLOSURE · 安全加固
> 时间：2026-08-19 · 状态：READ-ONLY 审计完成，BEFORE 复现完成，以下为修复点决策

## 1. 根因（已证实，非推测）

- **执行层**：`ai_core/execution/api.py` 的 `PermissionMode.NONE` 分支（L101–115）只拦截
  `decision == "block"`；`confirm`（含 run_shell 等 CONFIRM 级工具）直接穿透到
  L117 `execute_tool()` —— **未经用户确认即执行**。
- **复现证据**（STEP 2，运行实例解释器 3.13.12 实测）：
  - `policy_engine.evaluate("run_shell", {"command":"echo XIAO6_CONFIRM_TEST"}, default_deny=True) → decision = confirm`
  - `run("run_shell", ..., permission=PermissionMode.NONE)` 返回
    `'XIAO6_CONFIRM_TEST_WOULD_EXECUTE'`，`execute_tool` 被调用 = True
  - 结论：**CONFIRM WITHOUT APPROVAL = EXECUTION（安全缺陷实锤）**，证据见 `step2_before_repro.json`。

## 2. CHAT CONFIRM 调用图（BEFORE）

```
POST /api/chat
  → server_handlers_chat._handle_chat (L146)
    → run_fc_loop (L300)                      # LLM 函数调用闭环
      → capability_runtime.execute (L147, permission_mode="none")
        → ai_core.execution.run (permission=NONE)
          → [NONE 分支 L101-115] 仅拦 block    # ← 漏洞点：confirm 穿透
          → execute_tool (L126)               # ← 直接执行，无审批
```

## 3. 既有 Approval 机制（已定位，必须复用，禁止第二套）

```
policy_engine.request_approval (L257-289)
  → 生成 ticket + publish_system("modal", {kind:"agent_approval", ticket, tool, args_preview, summary})
    → eventbus → TOPIC_SSE
  → threading.Event.wait(timeout=300)          # 挂起等待
  → 用户批准路径：POST /api/agent/approval?ticket=&decision=
    → server_handlers_tasks._handle_agent_approval (L187) → policy_engine.resolve (L204)
  → 返回 approve | reject | timeout
```

**关键缺口（本次审计新发现）**：
1. `request_approval` 在 `goal_id is None`（聊天路径无 Goal）时直接返回 `"reject"`，**不弹审批**（L260-261）。
2. 前端有两条 SSE 通道，但都不渲染 `modal/agent_approval` 审批卡：
   - `/api/chat`（`_handle_chat`）**不订阅 TOPIC_SSE**，`modal` 事件到不了聊天流；
   - `/api/stream`（`_handle_stream`）虽订阅 TOPIC_SSE，但前端 `dispatchRuntimeEvent`
     把 `modal`/`approval` 按 §24 DUPLICATION GUARD 显式忽略（zz-workspace.js L865）。
   - 前端 `onApproval`（可交互审批卡）只由 `xiao6_event:"approval"` 触发，而后端**从未发过该事件**。

→ 结论：现有审批 UI 链路实际从未接通（GOAL 路径同样如此）；要让聊天路径 CONFIRM 闭环可用，
   必须在 chat 流内发出前端已支持的 `approval` 事件（复用 onApproval，非新建）。

## 4. 最小修复点（共 3 文件；server.py 与 zz-workspace.js 零改动）

### F1. `policy_engine.py` — `request_approval`（L257）
- 加参数 `force_modal: bool = False`；
- 早退条件改为 `if default_deny and not goal_id and not force_modal:`（默认保持 FAIL-CLOSED 不弹）；
- approve 时守卫 `if decision == "approve" and goal_id is not None: approve_in_goal(...)`。
- 作用：聊天路径（无 goal_id）也可弹出审批卡；其余调用方（GOAL/MCP/computer/permission_guard）
  行为零变化（force_modal 默认 False）。

### F2. `ai_core/execution/api.py` — NONE 分支（L101-115）
- evaluate 后新增 `decision == "confirm"` 分支：
  `_pe_approve = policy_engine.request_approval(name, args, goal_id=context.goal_id,
   default_deny=True, force_modal=True)`；
  - `approve` → 继续执行（落到 L117 execute_tool）；
  - `reject` / `timeout` / 任何异常 → cancel + return「未经用户批准，未执行」。
- 作用：CONFIRM 工具在聊天路径 **NO APPROVAL → NO EXECUTION；APPROVED → EXECUTION**。
- 保持既有语义：AUTO 直接执行、BLOCK 仍拦截、NEVER 仍拦截（is_never_by_args）、评估异常容错不阻断。

### F3. `server_handlers_chat.py` — `_handle_chat`（emit 定义后）
- 订阅 `TOPIC_SSE`，把 `modal(kind=agent_approval)` **转换为** `xiao6_event:"approval"`
  （含 `ticket` + `prompt` = summary + 命令预览）emit 到聊天流；
- 流结束（成功路径 + 两个 except）取消订阅。
- 作用：前端 `handle()` 的既有 `ev === 'approval'` 分支（zz-workspace.js L253 → onApproval L288）
  直接渲染可交互审批卡（批准/拒绝按钮 → POST /api/agent/approval），**前端零改动**。
- 顺带修复：GOAL 路径的 `request_approval` 事件若用户处于聊天视图，也会渲染审批卡（复用同一机制，
  非新功能）。

## 5. 安全不变量（修复后）

| 不变量 | 满足方式 |
|---|---|
| INVARIANT-01 CONFIRM 无批准 = 不执行 | F2：非 approve 一律 return |
| INVARIANT CONFIRM + 批准 = 执行 | F2+F3：approve → 继续 execute_tool |
| BLOCK 仍 BLOCK | F2 保留 block 拦截（evaluate 先行） |
| AUTO 保持原有 | F2 不触碰 auto 分支 |
| NEVER/CRITICAL 保持 | evaluate 内 is_never_by_args → block → 拦截 |
| 无第二套审批系统 | 全链路复用 request_approval + resolve + onApproval |
| FAIL-CLOSED | 审批异常/超时/拒绝 → 不执行；事件发布失败 → reject |

## 6. 验收对齐（STEP 十一 TEST 矩阵）

- TEST A/B/C（chat 路径 auto/confirm/block 决策）→ F2 判定
- TEST D（run_shell 无批准不执行）→ F2
- TEST E（批准后执行）→ F2+F3（需 SSE 流内 POST /api/agent/approval）
- TEST F（拒绝不执行）→ F2
- TEST G（超时不执行）→ F2（300s timeout → reject 语义）
- TEST H（is_never_by_args / sandbox 危险命令）→ evaluate → block，F2 不改变
- TEST I（policy.evaluate 未被绕过）→ F2 显式调用 evaluate 先行
- TEST J/K（GUI 审批卡 / TTS 不自动批准）→ F3 触发 onApproval；无 TTS 改动
- TEST L（回归：AUTO/BLOCK/NEVER 不退化）→ F1 默认参数不变 + F2 只加 confirm 分支
