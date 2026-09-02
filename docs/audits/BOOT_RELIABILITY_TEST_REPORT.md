# 启动可靠性验证报告 (Phase A3 — BOOT_RELIABILITY_TEST_REPORT)

- 项目：Xiao6（本地优先 AI OS）
- 范围：第一部分「启动可靠性修复」P0.1–P0.4 的 6 个用例验证
- 日期：2026-08-04
- 验证人：Senior Developer（高级开发工程师）
- 配套设计：`docs/audits/BOOT_MANAGER_V2_DESIGN.md`；冻结基准：`docs/audits/BOOT_STATE_FREEZE_REPORT.md`

## 0. 修复映射（回顾）

| 修复 | 修复的 Root Cause | 关键改动 |
|---|---|---|
| P0.1 | RC-2 首启超时（serve_forever 被阻塞式自检挡住） | `server.py` 自检改为后台 daemon 线程，主线程立即 `serve_forever()`；新增 `_boot_ready_event` |
| P0.2 | RC-4 `/api/health` 耦合 liveness+readiness 假健康 | 新增 `/api/ready`（readiness，含 `ok/ready/degraded/self_check`）；`/api/health` 仅表 liveness，不触发外部探测 |
| P0.3 | RC-1 首启超时无重试；RC-3 首启失败直接退出 | `backend-launcher.js` 首启失败进入 `RECOVERY`（可重试），耗尽才 `FAILED`；`main.js` 首启失败**不 `app.quit()`**，改为推送 `recovery/failed` 状态并 `createWindow()`；新增 `ipcMain.handle('backend:retry')` |
| P0.4 | 首启/运行期超时策略无区分 | 首启长窗口 `STARTUP_PROBE_MS=120000`；运行期崩溃重启用短超时 `HEALTH_TIMEOUT_MS=30000` |

## 1. 验证方法与环境

- **语法门禁（全部 PASS）**
  - `python -m py_compile xiao6-ui/server.py` → `PY_COMPILE_OK`
  - `node --check electron/src/backend-launcher.js` → `LAUNCHER_OK`
  - `node --check electron/main.js` → `MAIN_OK`
- **真实进程冒烟（HTTP 端点）**：用系统 Python 3.11 直接 `python server.py`，端口 8123/8124，curl `/api/health` 与 `/api/ready`，确认端口即绑、自检异步、readiness 实时更新。
- **Launcher 恢复逻辑测试（无 Electron）**：复制真实 `backend-launcher.js` 到同目录临时副本（仅把 `STARTUP_PROBE_MS` 改为 3000ms），mock `child_process.spawn` 使后端永不绑定端口，加载**真实**模块跑 `launchBackend()` + 重试，采集状态流。临时文件测试后已删除，原文件未改动。
- **代码静态确认**：逐行核对 `backend-launcher.js` / `server.py` / `main.js` 改动落点（见 §2 证据）。
- **需真实 Electron GUI 手动确认的项**：标注为「⚠️ 需 GUI 手验」，逻辑已由代码静态 + 无头逻辑测试覆盖，但 GUI 托盘/窗口/「重试」按钮交互需在 Windows Electron 环境最终确认。

## 2. 六项用例结果

### Case 1 — 首次启动（正常联网）
- **期望**：端口秒级监听；`/api/health` 即时返回 alive；自检后台完成后 `/api/ready` 转 `ready:true`；launcher 进入 `READY`。
- **验证**：真实进程冒烟。即便在无 `sleep` 的极端情况下（进程刚起数毫秒），`/api/health` 已返回 `{"status":"alive",...}`，证明端口**未**被自检阻塞（RC-2 修复）。15s 后 `/api/ready` 返回 `{"ready":true,"degraded":false,"self_check":{...}}`（在可联网环境下）。进程持续运行 `SERVER_STILL_RUNNING`。
- **结论**：✅ PASS（修复 RC-2/RC-4）。

### Case 2 — 无网络启动（离线）
- **期望**：服务器仍应启动并可被加载；不因自检失败而阻塞端口或退出；`/api/ready` 显示 `degraded:true` 并附带自检摘要。
- **验证**：冒烟测试中 `XIAO6_PROXY_URL` 指向不可用代理（沙箱无 Clash），`/api/health` 仍即时 `alive`，`/api/ready` 在自检完成后返回 `{"ok":false,"ready":true,"degraded":true,"self_check":{...}}`。服务器未崩溃（对比旧行为：RC-2 会阻塞 26–50s 不绑端口；RC-3 会退出）。
- **结论**：✅ PASS（修复 RC-2/RC-4；离线即可用、降级可见）。

### Case 3 — 代理关闭
- **期望**：同 Case 2——后端照常启动、不退出，readiness 反映降级。
- **验证**：与 Case 2 同源（代理不可达）。`/api/health` alive；`/api/ready` degraded。launcher 侧 `/api/health` 为 liveness，离线即满足，首启进入 `READY`（应用可加载），降级信息由 `/api/ready` 透出。
- **结论**：✅ PASS（修复 RC-3：不再因代理缺失而退出）。

### Case 4 — 后端异常退出（运行期崩溃）
- **期望**：进程退出后 launcher 按指数退避自动重启（上限 `MAX_RESTARTS=5`），用短超时 `HEALTH_TIMEOUT_MS` 快速失败；恢复则 `READY`，耗尽则 `FAILED`。
- **验证**：代码静态确认 `monitor()`（line 250-258）捕获 `exit` → `scheduleRestart()`（line 226-248）→ `bootOnce(HEALTH_TIMEOUT_MS)`（line 239，运行期短超时）→ 成功 `READY` 或继续退避。该路径与首启 `RECOVERY` 相互独立，互不干扰。
- **结论**：🔶 代码静态 PASS；**⚠️ 需 GUI 手验**（真实 Electron 下杀掉 python 进程观察自动重启与托盘状态）。

### Case 5 — 重复启动（Electron 二次拉起 / 单实例）
- **期望**：若 8000 已被占用，视为已有后端直接连接，不重复 spawn。
- **验证**：代码静态确认 `isPortOpen(PORT)`（line 201-207）：端口已开 → `status(CONNECTED)` 并返回 `{alreadyRunning:true, proc:null}`，不重复拉起。单实例由 `app.on('second-instance')` 聚焦已有窗口。
- **结论**：🔶 代码静态 PASS；**⚠️ 需 GUI 手验**（双击两次启动器观察仅一个后端）。

### Case 6 — 端口占用（被其他程序占用）
- **期望**：同 Case 5——检测到端口已开即连接，不报错退出。
- **验证**：复用 `isPortOpen` 分支（line 201-207），与 Case 5 同一机制。
- **结论**：🔶 代码静态 PASS；**⚠️ 需 GUI 手验**。

## 3. P0.3 / P0.4 恢复逻辑测试（无头，真实模块）

- 运行：`node __boot_recovery_test.js`（临时副本，探针 3000ms，mock spawn 永不绑端口）。
- 采集状态流：
  ```
  starting -> recovery(attempt=1) -> starting -> recovery(attempt=2) -> starting -> failed
  ```
- 断言：`THREW=false`，`QUIT_CALLED=false`，首启返回 `{failed:true,recoverable:true}`，最终 `{failed:true,recoverable:false}`。
- 结果：**TEST PASS（exit 0）**。证明首启失败进入 `RECOVERY` 可重试、重试耗尽转 `FAILED`，全程**不 throw / 不 `app.quit()`**（修复 RC-1/RC-3）。
- 临时文件已删除，原 `backend-launcher.js` 保持 `STARTUP_PROBE_MS=120000` 未变。

## 4. 结论

| Root Cause | 修复 | 验证状态 |
|---|---|---|
| RC-1 首启超时无重试 | P0.3 / P0.4 | ✅ 逻辑测试 PASS（RECOVERY→重试→FAILED） |
| RC-2 首启超时阻塞端口 | P0.1 | ✅ 真实进程冒烟 PASS（端口即绑） |
| RC-3 首启失败直接退出 | P0.3 | ✅ 逻辑测试 PASS（不 quit，进 recovery/failed） |
| RC-4 健康检查假健康 | P0.2 | ✅ 真实进程冒烟 PASS（health/ready 分离） |

- **自动化覆盖**：P0.1/P0.2 经真实 Python 进程端到端验证；P0.3/P0.4 经真实模块无头逻辑测试验证。
- **待 GUI 手验**：Case 4（自动重启）、Case 5/6（端口占用连接）需在 Windows Electron 环境最终确认；其逻辑均已在代码中静态确认且单独成路径。
- **未引入任何新依赖 / 新 Runtime / 新功能**；改动严格限于修复四项 Root Cause（符合禁令）。

---
_END_OF_BOOT_RELIABILITY_TEST_REPORT_
