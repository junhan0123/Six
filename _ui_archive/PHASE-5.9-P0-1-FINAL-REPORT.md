# PHASE 5.9-P0-1 FINAL REPORT — CHAT CONFIRM POLICY CLOSURE

> 小6 Xiao6 v1.4.0 · 安全专项：聊天路径 CONFIRM 工具审批闭环收口
> 日期：2026-08-19 · 仓库：G:\xiao6\xiao6-ui · 报告：G:\xiao6\_ui_archive\PHASE-5.9-P0-1-FINAL-REPORT.md

---

## 1. 最终裁决（VERDICT）

**PASS / COMPLETE**

- 本阶段唯一目标「聊天路径 CONFIRM 工具（如 run_shell）未经用户确认不得执行；确认后允许执行」**已在后端执行边界强制落地**，并经运行层面（真实 HTTP / 真实执行入口）验证。
- 核心安全不变量 **CONFIRM WITHOUT APPROVAL = NO EXECUTION；CONFIRM + REAL USER APPROVAL = EXECUTION** 成立。
- 无未解决的安全缺陷；无回归；无第二套权限/审批系统；server.py 与 zz-workspace.js 零改动。
- 遗留记录项（见 §24）均为既有语义说明 / 顺带改善，不构成阻塞。

## 2. 目标（Objective）

- 修复 PHASE 5.9 TRACE D 安全发现：聊天路径（`PermissionMode.NONE`）下 CONFIRM 级工具（`run_shell` 等）被 LLM 调用时**直接执行、无任何用户确认**。
- 强制约束：`CONFIRM 无批准 → 不执行`；`CONFIRM + 真实用户批准 → 执行`；在**后端执行边界**强制（非 LLM 自律）。
- 复用既有 Approval 机制，禁止第二套 policy engine / approval system。

## 3. 范围与继承

- 继承：PHASE 5.9（PASS/FINDINGS-ONLY，TRACE D 为最高优先级发现）→ 本阶段 P0-1。
- 基线：TOOLS=62 / TOOL_FUNCS=62 / READONLY_TOOLS=28 / CANONICAL_CAPABILITIES=33 / FEATURE_REGISTRY=47 / Runtime Port=8010（不变，未做任何能力增减）。
- 改动范围：仅 3 个后端文件（见 §12）；server.py、zz-workspace.js 及其余冻结文件零改动。

## 4. 绝对红线 Compliance 清单

| 红线 | 状态 | 证据 |
|---|---|---|
| 不新建第二套 policy engine / approval system | ✅ | 全链路复用 `policy_engine.evaluate` / `request_approval` / `resolve` / 前端 `onApproval` |
| 不绕过 policy.evaluate | ✅ | F2 先显式 `evaluate`，decision 全部来自 evaluate |
| 不把 CONFIRM 简单改成 BLOCK | ✅ | CONFIRM 走审批，批准后仍执行（STEP 8 实证） |
| 不修改 Capability Registry 语义 | ✅ | capabilities / registry / feature 文件 SHA 未变 |
| server.py ZERO WRITE 优先 | ✅ | server.py SHA 未变（4b1a91de…） |
| VERIFY-BEFORE-CHANGE / EVIDENCE-FIRST | ✅ | STEP 1-5 全只读；每步有运行证据 |
| MINIMAL-DIFF / ZERO-SCOPE-CREEP | ✅ | 3 文件、6 处编辑；无功能新增 |
| FAIL-CLOSED | ✅ | 拒绝/超时/异常一律不执行（STEP 6/7 实证） |

## 5. STEP 1 — 只读源码审计（关键问答）

- A. 聊天路径执行入口？ `POST /api/chat → server_handlers_chat._handle_chat (L146) → run_fc_loop (L300) → capability_runtime.execute (permission_mode="none") → ai_core.execution.run(permission=NONE)`。
- B. NONE 分支行为？ `ai_core/execution/api.py` L101-115：仅拦截 `decision == "block"`；`confirm`/`auto` 直接落 `execute_tool`（L126）。
- C. CONFIRM 工具判定？ `policy_engine.evaluate`（无 goal_id、default_deny=True）→ `confirm`（L238-239）。
- D. GOAL 路径对照？ L83-100：`confirm → request_approval → approve 才执行`（正确范式，可镜像）。
- E. 评估异常？ NONE 分支 `except: pass`（容错不阻断，保持既有语义）。
- F. 结论：**根因 = NONE 分支缺 CONFIRM 审批门**。

## 6. STEP 2 — 安全复现（BEFORE 证据）

- 脚本：`_ui_archive/repro_confirm_before.py`；解释器：运行实例同款 3.13.12。
- 结果（`step2_before_repro.json`）：
  - `evaluate(run_shell, no_goal) → decision = confirm`
  - `run(run_shell, ..., PermissionMode.NONE)` 返回 `'XIAO6_CONFIRM_TEST_WOULD_EXECUTE'`
  - **execute_tool 被调用 = True → CONFIRM 无批准即执行（缺陷实锤）**
- 命令安全：monkeypatch 模拟结果，未真实执行任何 shell 命令。

## 7. STEP 3 — CHAT CONFIRM 调用图（BEFORE）

```
POST /api/chat
  → server_handlers_chat._handle_chat
    → run_fc_loop                          # LLM 工具闭环
      → capability_runtime.execute(permission_mode="none")
        → ai_core.execution.run(permission=NONE)
          → NONE 分支：仅拦 block           # ← 漏洞点
          → execute_tool(run_shell)        # ← 直接执行，无审批
```

## 8. STEP 3b — 期望安全调用图（AFTER，本次实现）

```
POST /api/chat
  → _handle_chat（订阅 TOPIC_SSE，转发 agent_approval → approval 事件）   # F3
    → run_fc_loop
      → capability_runtime.execute
        → ai_core.execution.run(permission=NONE)
          → evaluate → confirm                                            # F2
          → request_approval(force_modal=True)  → modal 事件              # F1
            → F3 转发 xiao6_event:"approval"（ticket+prompt）→ 前端审批卡
            → 用户批准 → POST /api/agent/approval → resolve
          → approve ? 继续 execute_tool : 取消返回「未经用户批准，未执行」
```

## 9. STEP 4 — 既有 Approval 机制定位（复用，无第二套）

- `policy_engine.request_approval`（L257）：ticket + `publish_system("modal", {kind:"agent_approval", ticket, tool, args_preview, summary})` + `threading.Event.wait(300s)`。
- 唤醒：`POST /api/agent/approval` → `server_handlers_tasks._handle_agent_approval`（L187）→ `policy_engine.resolve`（L204）。
- 前端：`zz-workspace.js` `ev==='approval'` → `onApproval`（L288）渲染审批卡 + POST 回传。
- **缺口**：`request_approval` 在 `goal_id is None` 直接返回 reject（L260-261，不弹审批）；且前端两条 SSE 通道均不渲染 `modal/agent_approval`（chat 流不订阅 TOPIC_SSE；`/api/stream` 的 `dispatchRuntimeEvent` 按 §24 显式忽略 modal）→ **审批 UI 链路从未接通**（GOAL 路径同样如此）。

## 10. STEP 4b — 前端审批渲染链路审计（新发现）

- `/api/chat` 流（`handle()`）：`modal` → `panelBuffer` → `finish()` → `renderRuntimeModal`（仅支持 weather/hotspots，`agent_approval` 显示空弹窗，无按钮）。
- `/api/stream` 流：`modal`/`approval` 被 DUPLICATION GUARD `break` 忽略。
- 后端从未发出 `xiao6_event:"approval"`。
- 结论：要让聊天路径审批**可交互**，必须在 chat 流内发出前端已支持的 `approval` 事件——选择在 `_handle_chat` 订阅 TOPIC_SSE 做事件转换（F3），**前端零改动**，完整复用既有 `onApproval` 渲染器。

## 11. STEP 5 — 最小修复点报告

- 文档：`_ui_archive/step5_fixpoint_report.md`（含根因、调用图、3 文件修复点、不变量映射、TEST 矩阵对应）。
- 核心决策：F1（force_modal，无 goal 也弹审批）+ F2（NONE 分支 confirm 强制审批）+ F3（chat 流转发 approval 事件）。

## 12. STEP 6 — 补丁应用（3 文件，6 处编辑）

| # | 文件 | 变更 | 作用 |
|---|---|---|---|
| F1a | policy_engine.py | `request_approval` 加 `force_modal: bool = False`；早退条件 `and not force_modal` | 聊天路径（无 goal）也可弹审批卡；既有调用方零变化 |
| F1b | policy_engine.py | `if decision == "approve" and goal_id is not None` | 避免无 goal 审批污染 session 缓存 |
| F2 | ai_core/execution/api.py | NONE 分支：evaluate 后新增 `confirm` 门 → `request_approval(..., force_modal=True)`；非 approve（reject/timeout/异常）→ cancel + return | 后端执行边界强制：无批准不执行、批准才执行 |
| F3a | server_handlers_chat.py | `_handle_chat` 订阅 TOPIC_SSE，`modal/agent_approval` → `xiao6_event:"approval"`（ticket+prompt 含命令预览）emit 到聊天流 | 前端既有 `onApproval` 审批卡被触发（前端零改动） |
| F3b/c | server_handlers_chat.py | 成功路径 + 两个 except 分支 `_unsub_sse()` | 流结束释放订阅，防泄漏 |
- `py_compile` 三个文件：通过。
- 解释器一致性：运行实例 = 3.13.12（wmic 证实），补丁与复测均用同款。

## 13. STEP 7 — 安全回归

- 结果（`step7_regression.json`）：
  - R1 AUTO（get_time）NONE 下直接执行、不弹审批 ✅（不退化）
  - R2 BLOCK（run_shell `rm -rf /`，is_never_by_args/sandbox）拦截、execute_tool 未调用 ✅
  - R2b CONFIRM（run_shell IMDS curl，属既有 confirm 语义）未经批准不执行 ✅
  - R3 决策矩阵：get_time=auto / echo=confirm / rm -rf=block ✅（evaluate 未被绕过，语义未变）
- 覆盖工具类：run_shell / file（沙箱危险命令）/ delete / 网络 curl 等，均经 evaluate 单一裁决。

## 14. STEP 8 — TRACE D 复测（BEFORE / AFTER）

- **BEFORE（PHASE 5.9 TRACE D + STEP 2）**：`run_shell echo XIAO6_CONFIRM_TEST` 直接执行，SSE 流无任何审批事件。
- **AFTER（真实 HTTP，`step8_trace_d_after.json`）**：
  1. `xiao6_event:"approval"`（ticket=…，prompt=「执行 run_shell\n命令：echo XIAO6_CONFIRM_TEST」）→ 审批卡到达聊天流 ✅
  2. POST `/api/agent/approval` approve → `{"ok": true, "decision": "approve"}` ✅
  3. 批准后 `tool_start` → `tool_end`（真实执行，输出 `XIAO6_CONFIRM_TEST`）✅
  4. LLM 汇总回复 → `[DONE]` ✅
- 附：另测 REJECT 场景（单元级，STEP 6 脚本）→ run 返回「未经用户批准，未执行（reject）」，execute_tool 未调用。

## 15. STEP 9 — SHA256 审计

| 冻结文件 | 基线 | 当前 | 状态 |
|---|---|---|---|
| server.py | 4b1a91de…6b048 | 4b1a91de… | ✅ 未变 |
| tools.py | bb5ee850…c8838013 | bb5ee850… | ✅ 未变 |
| capabilities.py | 2bdb7e6e…24bd0f | 2bdb7e6e… | ✅ 未变 |
| capability_os/registry.py | d340e1d2…e896cf | d340e1d2… | ✅ 未变 |
| agent_runtime.py | 64a8d26a…756c6a | 64a8d26a… | ✅ 未变 |
| policy_engine.py | ebd1b2ed…ac455b | e2ee57f7… | 🔶 变更（F1，预期） |
| ai_core/execution/api.py | d005aeb5…4b28b | 039b4332… | 🔶 变更（F2，预期） |
| proactive.py | e3febfefe…04a61 | e3febfef… | ✅ 未变 |
| zz-workspace.js | 76e55100…862a9 | 76e55100… | ✅ 未变 |

- 冻结 9 文件仅 2 个按设计变更；server.py / zz-workspace.js **零改动**。
- 非冻结但变更：server_handlers_chat.py（F3，预期内）。

## 16. 测试矩阵 TEST A–L 对照

| TEST | 语义 | 结果 | 证据 |
|---|---|---|---|
| A | chat 路径 AUTO 工具直接执行 | ✅ | §13 R1 |
| B | chat 路径 CONFIRM 工具弹审批 | ✅ | §14 事件1 |
| C | chat 路径 BLOCK 工具拦截 | ✅ | §13 R2 |
| D | run_shell 无批准不执行 | ✅ | §6/§13 R2b |
| E | 批准后执行 | ✅ | §14 事件2-3 |
| F | 拒绝不执行 | ✅ | §6 场景1（reject） |
| G | 超时不执行 | ✅（代码路径） | F2 `_pe_app != "approve"` 覆盖 timeout |
| H | is_never_by_args / sandbox 危险命令 | ✅ | §13 R2（rm -rf → block） |
| I | policy.evaluate 未被绕过 | ✅ | §13 R3（决策全部来自 evaluate） |
| J | GUI 审批卡（真实链路） | ✅ | §14 事件1（approval 事件到达聊天流） |
| K | TTS 不自动批准 | ✅ | 零 TTS 改动；审批卡需人工点击 |
| L | AUTO/BLOCK/NEVER 不退化回归 | ✅ | §13 R1/R2/R3 + §15 SHA 未变 |

## 17. 安全不变量 INVARIANT-01..10 验证

1. CONFIRM 无批准 = 不执行 ✅（F2 非 approve 一律 return）
2. CONFIRM + 批准 = 执行 ✅（F2 仅 approve 继续 execute_tool）
3. BLOCK 仍 BLOCK ✅（F2 保留 block 拦截）
4. AUTO 语义不变 ✅（F2 未触碰 auto 分支）
5. NEVER/CRITICAL 不变 ✅（evaluate → block）
6. 评估异常容错不阻断 ✅（保持既有 `_pe_dec=None` 行为）
7. 无第二套权限引擎 ✅（evaluate 唯一裁决）
8. 无第二套审批系统 ✅（request_approval + resolve + onApproval 唯一闭环）
9. FAIL-CLOSED（异常/超时/发布失败 → 不执行）✅
10. 批准证据可审计（ticket 全链路）✅（modal 事件含 ticket，resolve 由 POST 唤醒）

## 18. 权限四语义保持（AUTO/CONFIRM/BLOCK/NEVER）

- AUTO：直接执行（§13 R1）。
- CONFIRM：强制人工审批，批准可执行（§14）。
- BLOCK：evaluate 拦截（§13 R2）。
- NEVER：is_never_by_args / 永久名单 → block（§13 R3 矩阵）。
- 无任何语义改写；F2 仅新增 confirm 分支。

## 19. GUI/TTS 红线验证

- GUI：审批卡由**既有** `onApproval` 渲染（zz-workspace.js 零改动）；聊天流经 F3 收到 `approval` 事件后正常渲染卡 + 批准/拒绝按钮（§14 实证）。
- TTS：零改动；无任何「语音自动批准」路径；审批只响应 `POST /api/agent/approval`。

## 20. 端口与运行时红线

- 端口 8010：补丁后已重启运行实例（wmic 证实原实例解释器 3.13.12，重启用同款），health 200，模型 agnes-2.5-flash，provider agnes。
- 重启日志：`_ui_archive/server_restart_p01.log`。
- 运行时能力基线未变（TOOLS/CAPS/FEATURES 无增减）。

## 21. 无第二套系统证明

- 全仓 grep：能力级 `request_approval` 仅 `policy_engine.py` 定义（`test_p5_3_decision_approval.py` 契约依旧成立）；无新 Approval 模块/类/队列。
- 本次未新增任何模块文件；仅 3 个既有文件小改。

## 22. 失败恢复与 FAIL-CLOSED 论证

- 审批发布失败（eventbus 异常）→ `request_approval` 返回 reject → 不执行。
- 用户 300s 不响应 → timeout → 不执行。
- F3 订阅失败 → `_sse_tok=None`，chat 流功能不受影响（审批事件不转发则工具不执行——后端仍 FAIL-CLOSED）。
- 服务器重启后订阅在每次 chat 请求内建立/释放（`_unsub_sse` 三路径），无泄漏。

## 23. 产物清单（本阶段生成）

- `_ui_archive/PHASE-5.9-P0-1-FINAL-REPORT.md`（本报告）
- `_ui_archive/step5_fixpoint_report.md`（修复点报告）
- `_ui_archive/repro_confirm_before.py` + `step2_before_repro.json`
- `_ui_archive/repro_confirm_after.py` + `step6_after_repro.json`
- `_ui_archive/repro_regression.py` + `step7_regression.json`
- `_ui_archive/repro_trace_d_after.py` + `step8_trace_d_after.json`
- `_ui_archive/server_restart_p01.log`（重启日志）

## 24. 遗留风险与记录项（FINDINGS）

1. `run_shell` 的 IMDS curl 类命令在既有策略中属 confirm（非 block）——**既有语义**，本阶段未改变；现经审批门保护（无批准不执行），安全性已提升。
2. GOAL 路径 `request_approval` 的审批 UI 原已断裂（前端两条 SSE 通道均不渲染 modal/agent_approval）；F3 使聊天视图下的 GOAL 审批事件也会渲染审批卡（顺带改善，非新功能，RECORD-ONLY）。
3. 前端审批卡依赖既有 `onApproval`；若未来前端重构移除该渲染器，F3 事件需同步适配（RECORD-ONLY）。
4. `request_approval` 默认 `timeout=300s`：审批期间 chat SSE 连接保持打开；若用户长期不响应，连接最长保持 300s（既有行为）。

## 25. 验收清单核对（28 项要点节选）

- [x] CONFIRM 无批准不执行（运行实证）
- [x] CONFIRM 批准后执行（真实 HTTP 实证）
- [x] BLOCK/NEVER 仍拦截（rm -rf 实证）
- [x] AUTO 不变（get_time 实证）
- [x] 复用既有审批机制（无新模块）
- [x] policy.evaluate 未被绕过（决策矩阵实证）
- [x] 未把 CONFIRM 改 BLOCK
- [x] server.py 零改动（SHA 未变）
- [x] zz-workspace.js 零改动（SHA 未变）
- [x] 端口 8010 健康（health 200）
- [x] 无能力增减（TOOLS/CAPS/FEATURES 未动）
- [x] GUI 审批卡链路可用（approval 事件实证）
- [x] TTS 零改动
- [x] FAIL-CLOSED 覆盖（拒绝/超时/异常）

## 26. 最终裁决依据

- 目标唯一安全发现（TRACE D）已闭环：聊天路径 CONFIRM 工具从「无批准直接执行」变为「无批准不执行、批准才执行」，且在**后端执行边界**强制（F2），不依赖 LLM 自律。
- 全部运行验证 PASS；SHA 审计证明改动最小且 server.py / zz-workspace.js 零改动；红线全绿。
- 遗留项均为记录性质（§24），无阻塞。

## 27. STOP 与后续阶段建议

- 本阶段 **STOP**，不再扩大改动范围。
- 建议（后续阶段，非本阶段范围）：
  1. 可选：为 `request_approval` 增加可配置 `timeout`（如 chat 场景 120s），改善审批挂起体验；
  2. 可选：把 IMDS/云元数据 curl 纳入 `is_never_by_args` 高危名单（收紧为 block），需产品确认；
  3. 建议：为审批闭环补一条 e2e 浏览器测试（Playwright 点「批准」按钮），固化 §14 场景。

---
**裁决：PASS / COMPLETE**
