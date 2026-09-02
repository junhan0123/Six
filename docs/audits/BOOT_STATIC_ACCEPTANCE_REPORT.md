# 小6启动可靠性 — A1 静态验收报告

> **Boot Reliability — A1 Static Acceptance Report**
> 任务：Xiao6 AI OS v1.4.1 Release Readiness · 任务 A Boot Reliability Acceptance · A1 静态验证
> 验收对象：Boot Manager v2 P0 修复（P0.1 / P0.2 / P0.3 / P0.4）
> 执行模式：Audit → Analyze → Plan → Execute → Verify → Report（本步为 Static Verify）
> 纪律：只读验收，不修改任何代码；失败仅报告，不扩大修复范围。
> 日期：2026-08-04
> 执行：Senior Developer（高级开发工程师）

---

## 0. 验收范围与方法

### 0.1 验收目标
确认 `electron/main.js`、`electron/src/backend-launcher.js`、`xiao6-ui/server.py` 三处实体代码已按 `BOOT_MANAGER_V2_DESIGN.md` 落点，且逐项满足以下 **5 个静态验收点**（对应 4 项 Root Cause）：

| # | 静态验收点 | 修复的 Root Cause |
|---|---|---|
| S1 | `serve_forever()` 不再被 `run_self_check` 阻塞（预热改后台线程，端口即绑） | RC-2 |
| S2 | `/api/health` 仅负责 liveness，不触发外部探测 | RC-4 |
| S3 | 新增 `/api/ready` 负责 readiness（含 `ok/degraded/self_check`） | RC-4 |
| S4 | `RECOVERY` 流程存在于 launcher 与 main | RC-1 / RC-3 |
| S5 | 首次启动失败不再直接 `app.quit()`，改推 recovery/failed 状态 + 建窗 | RC-1 / RC-3 |

### 0.2 验收方法
- **代码静态走读**（逐行确认落点 + 行号索引）。
- **语法编译门禁**：`node --check` ×2 + `python -m py_compile` ×1，确认三文件无语法错误（不代表运行验收，运行验收见 A2）。
- 不启动真实进程、不触发 Electron GUI（运行期行为归 A2）。

### 0.3 参考基准
- `docs/audits/BOOT_CHAIN_AUDIT_REPORT.md`（4 项 Root Cause 来源）
- `docs/audits/BOOT_MANAGER_V2_DESIGN.md`（A1 设计基准）
- `docs/audits/BOOT_RELIABILITY_UPGRADE_REPORT.md`（A2 执行落点记录）

---

## 1. 逐项静态验收结果

### S1 — `serve_forever()` 不再被 `run_self_check` 阻塞  ✅ PASS

**落点：`xiao6-ui/server.py` `main()`，行 2561–2637**

| 关键事实 | 行号 | 说明 |
|---|---|---|
| 自检移入后台 daemon 线程 | `:2561–2581` | `def _async_self_check(): ... threading.Thread(target=_async_self_check, daemon=True).start()` |
| 自检完成后置位就绪事件 | `:2576–2580` | `global _BOOT_SELF_CHECK_DONE/_BOOT_SELF_CHECK_RESULT; _boot_ready_event.set()` |
| 主线程立即 `serve_forever()` | `:2635–2637` | `httpd = ThreadingHTTPServer(...); httpd.serve_forever()` |

**结论**：`run_self_check(force=True)` 在 `:2566` 于 daemon 线程内执行，主线程在 `:2637` 立即绑定端口并开始监听，**自检不再位于 `serve_forever` 之前**。端口即绑，RC-2 结构性计时竞争消除。

> 注：旧审计报告的 `:2525` 阻塞点已不存在——该行区间现为主线程顺序启动其余 daemon 线程（tick_loop / get_geo / _warmup_embed / 飞书 / KWS / Agent Runtime），均不阻塞端口绑定。

---

### S2 — `/api/health` 仅 liveness，不触发外部探测  ✅ PASS

**落点：`xiao6-ui/server.py` `do_GET`，行 186–220**

| 关键事实 | 行号 | 说明 |
|---|---|---|
| 显式 liveness 注释 | `:187` | `liveness：仅表进程存活；ok 取最近一次自检缓存，不触发外部探测（P0.2 修复 RC-4）` |
| `ok` 取自缓存而非实时探测 | `:188, :195` | `cached = _BOOT_SELF_CHECK_RESULT; "ok": bool(key_ok and cached and cached.get("ok"))` |
| 无 `run_self_check()` 调用 | 全段 | 整段 `:186–220` 不含任何 `run_self_check` / 外部 HTTP 探测 |

**结论**：`/api/health` 每次请求仅读全局缓存 `_BOOT_SELF_CHECK_RESULT`，**绝不触发外部网络自检**。launcher 的 `waitForHealth`（仅判 `statusCode===200`）因此只在乎"端口已监听"，与自检快慢解耦。RC-4 的"假健康 + 语义错位"消除。

---

### S3 — 新增 `/api/ready` 负责 readiness  ✅ PASS

**落点：`xiao6-ui/server.py` `do_GET`，行 221–247**

| 关键事实 | 行号 | 说明 |
|---|---|---|
| readiness 注释 | `:222` | `readiness：服务是否完成初始化、功能是否就绪（P0.2 新增）` |
| 读取就绪事件 | `:225` | `ready = _boot_ready_event.is_set()` |
| 缓存为空 → 未就绪 | `:226–233` | 返回 `{"ok": False, "ready": ready, "key_present": key_ok, "degraded": False, "self_check": None}` |
| 缓存就绪 → 完整语义 | `:234–247` | 返回 `{"ok", "ready", "key_present", "degraded": not ok, "self_check"}` |

**结论**：`/api/ready` 提供 liveness / readiness 两层分离的 readiness 层，含 `ok/degraded/ready/self_check` 完整字段，前端可用于诊断与"降级可见"。RC-4 修复闭环成立。

---

### S4 — `RECOVERY` 流程存在（launcher + main）  ✅ PASS

**落点 A：`electron/src/backend-launcher.js`**
| 关键事实 | 行号 | 说明 |
|---|---|---|
| `RECOVERY` 状态枚举 | `:41` | `RECOVERY: 'recovery', // P0.3：首启失败恢复态（不退出，可重试/诊断）` |
| 首启重试计数 | `:261–262` | `let bootRetries = 0; const MAX_BOOT_RETRIES = 2;` |
| 首败转 RECOVERY（可重试） | `:301–322` | `catch` 内 `if (bootRetries < MAX_BOOT_RETRIES)` → `status(STATUS.RECOVERY, {canRetry:true})`，返回 `{failed:true, recoverable:true, retry: ...}` |
| 重试耗尽转 FAILED | `:323–332` | 否则 `status(STATUS.FAILED, {canRetry:false})`，返回 `{failed:true, recoverable:false}` |
| `retry()` 重入首启 | `:299, :320` | `retry: async () => attemptFirstBoot()` |

**落点 B：`electron/main.js`**
| 关键事实 | 行号 | 说明 |
|---|---|---|
| 首败状态推送 | `:263–268` | `if (backend && backend.failed)` → `pushBackendStatus(backend.recoverable ? 'recovery' : 'failed', {...})` |
| `backend:retry` IPC | `:227–243` | `ipcMain.handle('backend:retry', ...)` 调用 `backend.retry()`，回流 recovery/failed/ready |

**结论**：首启失败链路完整——`attemptFirstBoot` 失败 → `RECOVERY`（≤2 次可重试）→ `FAILED`（不可重试）。状态经 IPC 回流前端，前端可触发 `backend:retry` 重新拉起。RC-1/RC-3 的"无重试通道"消除。

---

### S5 — 首次启动失败不再直接 `app.quit()`  ✅ PASS

**落点：`electron/main.js` `app.whenReady().then`，行 250–276**

| 关键事实 | 行号 | 说明 |
|---|---|---|
| 旧 `app.quit()` 路径消失 | 全文检索 | `main.js` 中 `app.quit()` 仅出现在：单实例锁失败 `:29`、菜单"退出" `:99, :127`、**`before-quit` 钩子** `:279`。**首启失败路径无 `app.quit()`** |
| 首败仍建窗 | `:263–272` | `if (backend.failed)` 分支：`pushBackendStatus(...)` → `createWindow()` → `buildTray()` → `return;`（不再 throw/quit） |
| 正常路径不变 | `:274–275` | 否则 `createWindow(); buildTray();` |

**对比旧根因（RC-1）**：原 `main.js:243–248` 为 `dialog.showErrorBox('小6启动失败') + app.quit()`。现该终态退出逻辑已被 `:263–272` 的"建窗 + 推 recovery/failed 状态"取代。用户首次启动即使后端彻底失败，也能看到窗口与恢复 UI，而非整窗消失。

**结论**：S5 PASS。首启失败不再静默退出，符合 RC-1/RC-3 修复目标。

---

## 2. 语法编译门禁（静态）

| 文件 | 命令 | 结果 |
|---|---|---|
| `electron/main.js` | `node --check` | ✅ OK |
| `electron/src/backend-launcher.js` | `node --check` | ✅ OK |
| `xiao6-ui/server.py` | `python -m py_compile` | ✅ OK |

三文件均无语法错误，可进入下一步运行验收（A2）。

---

## 3. A1 静态验收结论

| 验收点 | 结论 | 修复 Root Cause |
|---|---|---|
| S1 serve_forever 不被自检阻塞 | ✅ PASS | RC-2 |
| S2 /api/health 仅 liveness | ✅ PASS | RC-4 |
| S3 /api/ready 负责 readiness | ✅ PASS | RC-4 |
| S4 RECOVERY 流程存在 | ✅ PASS | RC-1 / RC-3 |
| S5 首启失败不 app.quit | ✅ PASS | RC-1 / RC-3 |

**A1 静态验收：5/5 全部 PASS。**

> 说明：静态验收确认代码落点与语法正确，但不验证真实运行行为（离线/代理关/端口占用等场景）。运行期行为与恢复能力由 **A2 运行验收**（真实进程冒烟 + 无头逻辑测试）覆盖，结论归并于 `BOOT_RUNTIME_ACCEPTANCE_REPORT.md`。

---

## 4. 行号索引（验收证据）

| 文件 | 关键行 | 作用 |
|---|---|---|
| `xiao6-ui/server.py` | 186–220 | `/api/health` liveness only |
| `xiao6-ui/server.py` | 221–247 | `/api/ready` readiness |
| `xiao6-ui/server.py` | 2536–2539 | `_boot_ready_event` / 缓存全局变量 |
| `xiao6-ui/server.py` | 2561–2581 | `_async_self_check` daemon 线程 |
| `xiao6-ui/server.py` | 2635–2637 | `serve_forever()` 立即监听 |
| `electron/src/backend-launcher.js` | 32 | `STARTUP_PROBE_MS=120000`（P0.4 首启长窗口） |
| `electron/src/backend-launcher.js` | 41 | `STATUS.RECOVERY` 枚举 |
| `electron/src/backend-launcher.js` | 217–224 | `bootOnce`（默认 `STARTUP_PROBE_MS`） |
| `electron/src/backend-launcher.js` | 239 | 运行期重启用短超时 `HEALTH_TIMEOUT_MS` |
| `electron/src/backend-launcher.js` | 261–334 | `attemptFirstBoot` RECOVERY/FAILED 流转 |
| `electron/main.js` | 227–243 | `backend:retry` IPC |
| `electron/main.js` | 250–276 | `app.whenReady` 首败建窗（无 app.quit） |

---

_END_OF_BOOT_STATIC_ACCEPTANCE_REPORT_
