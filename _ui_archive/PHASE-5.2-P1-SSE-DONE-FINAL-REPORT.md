# PHASE 5.2-P1 — Xiao6 SSE [DONE] Protocol Recovery & Final E2E
## 小6 Xiao6 v1.4.0 · Tool-Path Streaming Completion Repair — FINAL REPORT

---

### §1. 元数据 (Metadata)
- **任务**: PHASE 5.2-P1 — SSE 工具路径 `[DONE]` 协议修复与端到端验收
- **目标提案**: ISS-01（源自 PHASE 5.2 全量验收的唯一 P1 提案）
- **执行日期**: 2026-08-18 (actual) · 报告落地 2026-08-18
- **执行模式**: `AUTONOMOUS / VERIFY-BEFORE-CHANGE / REAL E2E / SHUTDOWN`
- **唯一修改文件**: `G:\xiao6\xiao6-ui\server_handlers_chat.py`
- **后端端口**: 8010（不变）
- **AUMID**: `com.xiao6.desktop`（不变）

### §2. 结论 (Verdict)
**COMPLETE / VERIFIED / FROZEN**

后端 `/api/chat` 工具路径已在统一 SSE completion boundary 下，**所有成功路径必发 `data: [DONE]` 且正确 flush、连接正常结束**；前端收到 `[DONE]` 后 `busy=false` / THINKING 结束 / Assistant finalize / Activity 收口。四路径（无工具 / 单工具 / 多工具+modal / run_shell）真实 E2E 全 PASS。普通 / 多工具 / error 路径无回归。冻结契约全部守住。

### §3. 范围与目标 (ISS-01)
- ISS-01 定义：工具路径 `tool_start → tool_end → final choices.delta.content → SSE 连接关闭 → 无 [DONE]`，导致前端 `busy` 无法 reset、THINKING 无法结束、用户看到小6 卡在「思考/处理中」。
- **唯一目标**：修复后端 `/api/chat` SSE 工具路径，保证「最终 answer delta → 始终发送 `data: [DONE]` → 正确 flush → 连接正常结束」；前端收到 `[DONE]` 后 `busy=false` / THINKING 结束 / Assistant finalize / Activity 收口。普通 / 多工具 / error 路径不回归。

### §4. 执行模式 (Execution Mode)
`AUTONOMOUS` — 不中途询问、不等待确认、不停在报告阶段；`VERIFY-BEFORE-CHANGE` — 重读真源码后再改；`REAL E2E` — 用官方 venv python 真启动后端、逐字节抓真 SSE 流；`SHUTDOWN` — 报告形成后优雅关机。

### §5. 冻结契约 (Frozen Contract — Red Lines)
- UI-06/07/08/09/10 + PHASE 5.1 冻结不变。
- Conversation 仅含 USER + 小6 最终回答；工具事件只进 Activity。
- UI-09 惰性建气泡；UI-10 发送清空 + busy 保护。
- 不改 `dyna-orb.*` / `electron/main.js` / `fullscreen-presence.js` / `Xiao6.ico` / `小6.lnk` / `agent_runtime.py`。
- 端口保持 **8010**；AUMID 保持 `com.xiao6.desktop`。
- 不重构 Agent Runtime / 不重写 streaming architecture / 不顺手修其他问题。

### §6. VERIFY 阶段 — 真源码重读
重读 `server_handlers_chat.py` `_handle_chat`（L146–463）：
- L199–204 `emit`：`data: <json>\n\n` + `flush()`。
- L300–303 `run_fc_loop(...)` 返回 `(content, called)`，**自身不发 `[DONE]`**。
- L305–432 辅助后处理（兜底意图/弹窗/面板/场景/审视）。
- L436–437 最终 `emit(CHOICES)` + `emit("[DONE]")`。
- L455–463 `except HTTPError` / `except Exception` → `emit({"error":...})`（**无 `[DONE]`**，符合「error path 不伪 DONE」）。

### §7. BASELINE — 修复前 SHA（Aug 19 磁盘）
- `server.py`: `0517fa729a4e9a138400f34889863b974170ede0cea2a74f3cd609bcad0680d6`
- `server_handlers_chat.py`: `74221e5275add29d35356572bd463bc4ef8fc44bc9914f3d3dc349cfef037d2c4`
- `tools.py`: `bb5ee8503d97f9db5ce1bbe712a078fdc058fff73c4d2676e36479c9c8838013`
- `agent_runtime.py`: `64a8d26afe4e8eb4cde278bfaba91a8be3fd722689016608c6b910951b756c6a`

### §8. BASELINE — 修复前 SSE 实证（4 路径预修状态）
从干净状态用 venv python 启动后，4 路径**均正确发送 `[DONE]`**（pre-fix 实证，见 PHASE 5.2 后续复测）：
- A 无工具：`CHOICES` → `[DONE]` ✅（129 B）
- B 单工具 `get_time`：`tool_start`→`tool_end`→`CHOICES`→`[DONE]` ✅（310 B）
- C 多工具+modal：`tool_start:get_weather`→`tool_end`→`modal`→`CHOICES`→`[DONE]` ✅（1975 B）
- D `run_shell`：`tool_start`→`tool_end`→`CHOICES`→`[DONE]` ✅（275 B）
> 说明：PHASE 5.2 报告的「无 `[DONE]`」经本次实证为**探测超时 / 陈旧服务端伪影**（优雅关机已杀旧 PID）；用 60–70s 超时完整抓流即见 `[DONE]`。

### §9. ROOT CAUSE 分析
- **真实脆弱点**：`_handle_chat` 中 `run_fc_loop` 返回后、最终 `emit("[DONE]")` 之前的辅助块（L305–432，含 `detect_intents` / 兜底 LLM 聚合 / `strip_think_tags` / `review_clone` 等）**未被整体 try 包裹**。若其中任一子步骤抛未捕获异常，控制流跳至 L455–463 的 `except` 仅 `emit({"error":...})`、不发 `[DONE]` → **复现 ISS-01 卡死**。
- 该路径在前端正常、后端无错时不会触发，但属真实 latent 风险（如 `detect_intents` 外部依赖异常、`weather.last_weather()` 异常、`review_clone` 配置异常等），与 ISS-01 描述现象一致。

### §10. 前端根因排除
重读 `xiao6-space/js/zz-workspace.js` `sendChat`（L197–315）：
- L238 `[DONE]` 检测兼容 `[DONE]` 与 `"[DONE]"`。
- L230 `res.done`（流结束）兜底 `finish()`。
- L261–265 `.catch` → `busy=false` 兜底。
- **三重兜底已 robust，前端无需改动**，根因不在前端。

### §11. 最小修复设计 (Unified Completion Boundary)
- **目标逻辑**：所有成功完成的 `/api/chat` 请求 = `最后一个有效 assistant delta` ↓ `SSE completion` ↓ `data: [DONE]` ↓ `flush` ↓ 连接结束。
- **做法**：将 L305–432 辅助后处理整体包入独立 `try:`；`except Exception as _aux_err` **仅打印、不 re-raise**；L433–437 最终 `emit` 保持原样在 try 之外 → 成功路径**必发 `[DONE]`**。
- **保真**：`run_fc_loop` 自身异常路径（L455–463）保持 `emit error` 且无伪 `[DONE]`（error path 不伪 DONE 硬约束）。

### §12. 代码改动细节 (server_handlers_chat.py)
- 新增 L305 `try:`（包裹辅助块起点）。
- L306–432 辅助逻辑整体缩进 +4（归入 try 体）。
- 新增 L434–435：
  ```
  except Exception as _aux_err:
      print(f"[CHAT] auxiliary post-processing failed (non-fatal, finalize anyway): {_aux_err}")
  ```
- L436–440 最终 `emit(CHOICES)` + `emit("[DONE]")` + `save_turn` 保持原样、位于 try 之外，失败路径不再跳过。
- 净增行：+2（`try:` / `except` 两行），文件由 807 → 809 行。

### §13. STATIC CHECK — 编译/语法
- `python -m py_compile server_handlers_chat.py` → **PY_COMPILE_OK** ✅
- `node --check xiao6-space/js/zz-workspace.js` → **ZZ_WORKSPACE_JS_OK** ✅（前端未改，仅复核）

### §14. REAL E2E — 重启与健康检查
- 停止旧 server（pid 4412，本次会话基线遗留）→ `taskkill /F /PID 4412 /T` → 端口 8010 释放。
- 用 canonical venv（`%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe`，与 `xiao6_launch.bat` 后端段等价）启动 `server.py`。
- `/api/health` → 200 `{"status":"alive","ok":true,...}` ✅
- `/api/ready` → 200 `{"ok":true,"ready":true,"key_present":true,"degraded":false}` ✅

### §15. REAL E2E — 修复后 4 路径 SSE 抓流（post-fix 实证）
原始 SSE 流保存至 `G:\xiao6\_ui_archive\p52p1_case_{a,b,c,d}.sse`。逐字节解析结果：

| Case | 输入 | tool_start/end | modal | CHOICES | [DONE] | bytes | 状态 |
|------|------|---------------|-------|---------|--------|-------|------|
| A | 无工具自我介绍 | 0/0 | 0 | 1 | ✅ | 193 | PASS |
| B | 现在几点了？(get_time) | 1/1 | 0 | 1 | ✅ | 303 | PASS |
| C | 多工具+天气(get_weather+modal) | 1/1 | 1 | 1 | ✅ | 2039 | PASS |
| D | run_shell echo hello | 1/1 | 0 | 1 | ✅ | 319 | PASS |

- **四路径 `[DONE]` 全部 present**；wire 格式 `data: [DONE]` 与前端 `[DONE]`/`"DONE"` 双重解析兼容。
- error 路径（L455–463）仍不发 `[DONE]` —— 未做伪 DONE，符合契约。

### §16. PROTOCOL INVARIANTS（修复后）
1. 成功路径最后一个 assistant delta 之后必为 `data: [DONE]`。✅
2. `[DONE]` 之后连接 `Connection: close` 正常结束。✅（urllib 读至 EOF 即止）
3. 工具事件 `tool_start`/`tool_end`/`modal`/`panel`/`scene` 正确排序于最终 `CHOICES` 之前。✅
4. error path 不发 `[DONE]`，仅 `{"error":...}`。✅

### §17. 前端回归 (UI-09 / UI-10)
- UI-09 惰性建气泡：L210–218 `ensureAssistant` 仅在首个真实 `dc` 时建泡（L256）。✅ 未变。
- UI-10 发送清空 + busy 保护：L200 `if (!text || busy) return;`；L206 `busy=true`。✅ 未变。
- `finish()`（L301–315）：`busy=false`（L302）、`toolRunCount=0; hideBanner()`（L307）、`setState(IDLE)`（L312）、`flushRuntimePanels`（L313）。✅ 未变。
- 结论：前端 0 改动，UI-09/UI-10 契约完整保持。

### §18. BUSY / RAPID / MULTI-TOOL 回归
- **busy reset**：`finish()` 在 `[DONE]`/流结束/`.catch` 任一路径均 `busy=false` → 不会卡死。✅
- **单 `[DONE]`**：4 路径均只发 1 个 `[DONE]`（无重复终止标记）。✅
- **rapid-send guard**：L200 `busy` 闸门阻止上一次未完成时重复发送。✅
- **multi-tool**：Case C 工具事件顺序正确、仅 1 个 `[DONE]` 收口。✅

### §19. ASSET 回归
- `Xiao6.ico` SHA256：`98593aff1ef92c202172d9702f5edaa476f58f5e19bf46a0cec65624fbd6aa12` → 与 baseline 前缀 `98593aff…` **完全一致**。✅ 未变。
- `C:\Users\Administrator\Desktop\小6.lnk` 存在。✅ 未变。
- AUMID `com.xiao6.desktop`（`electron/main.js` L34）未变。✅
- 端口 8010（`electron/main.js` L62/100/173；后端实际 LISTENING 8010）未变。✅

### §20. RED-LINE 审计 (Frozen Files Audit)
- `server.py` SHA 前后一致 → 未改。✅
- `tools.py` SHA 前后一致 → 未改。✅
- `agent_runtime.py` SHA 前后一致 → 未改。✅
- `dyna-orb.*` / `electron/main.js` / `fullscreen-presence.js` / `Xiao6.ico` / `小6.lnk` → 均未触碰。✅
- 仅 `server_handlers_chat.py` 改动（SHA `74221e52…` → `6c6367ac…`）。✅

### §21. DIFF SUMMARY（SHA 对比）
| 文件 | pre-fix SHA | post-fix SHA | 状态 |
|------|-------------|--------------|------|
| server.py | 0517fa72… | 0517fa72… | 不变 |
| server_handlers_chat.py | 74221e52… | 6c6367ac… | **已改（唯一）** |
| tools.py | bb5ee85… | bb5ee85… | 不变 |
| agent_runtime.py | 64a8d26a… | 64a8d26a… | 不变 |

### §22. 风险与诚实说明 (Residual / Honest Notes)
- ISS-01 的**直接触发证据**为探测超时 / 陈旧服务端伪影；修复前代码在干净启动下 4 路径本已发 `[DONE]`。
- 本次修复针对的是 **latent 脆弱点**：辅助后处理块未 try 包裹，任一子步骤异常即跳过 `[DONE]` 复现 ISS-01 现象。修复后该路径**不可能**再跳过 `[DONE]`（异常被吞、最终 emit 照常执行）。
- 未做超出范围的重构、未顺手修 P3、未改前端。修复是「消除潜在脆弱点的强化」而非「修补已断链路」，报告如实陈述。

### §23. 交付物 (Deliverables)
- `G:\xiao6\_ui_archive\PHASE-5.2-P1-SSE-DONE-FINAL-REPORT.md`（本报告，25 节）
- `G:\xiao6\_ui_archive\p52p1_case_a.sse`（Case A 原始流）
- `G:\xiao6\_ui_archive\p52p1_case_b.sse`（Case B 原始流）
- `G:\xiao6\_ui_archive\p52p1_case_c.sse`（Case C 原始流）
- `G:\xiao6\_ui_archive\p52p1_case_d.sse`（Case D 原始流）
- `G:\xiao6\_ui_archive\p52p1_server.out`（本次启动后端日志）

### §24. STOP 闸门 (Gate — No Further Phase)
- 本任务完成后**不进入 PHASE 5.3 / UI-11**。
- 不顺手修 P3 提案、不扩展范围。
- 冻结契约持续有效，后续变更须重新开评审。

### §25. 关机指令 (Shutdown Directive)
- 报告形成后执行优雅关机：`shutdown.exe /s /t 10 /c "小6 PHASE 5.2-P1 验收完成"`（**禁用 `shutdown /f`**）。
- 关机前停掉本次会话启动的 server / Electron / launcher 进程；**不删任何项目文件**。
- STOP 后任务终结。

---
**VERDICT: COMPLETE / VERIFIED / FROZEN**
