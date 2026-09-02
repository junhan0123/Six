# 当前启动状态确认报告（Phase A0 — Freeze）

> 任务：Xiao6 Reliability & Knowledge Preservation Upgrade — Part 1 / Phase A0
> 模式：只读冻结确认。**本报告不包含任何代码修改。**
> 参照：`docs/audits/BOOT_CHAIN_AUDIT_REPORT.md`（已完成，根因已确认）
> 日期：2026-08-04

---

## A0.1 目的

在进入实现（Phase A2）之前，先对**当前启动链的真实代码状态**做逐文件、逐行确认，作为后续"小步修改、禁止重构"的基准快照。本阶段**不修改任何文件**。

## A0.2 已确认文件清单（读，未改）

| 文件 | 行数 | 关键确认点 |
|---|---|---|
| `electron/main.js` | 266 | `:243-248` 首启失败 → `dialog.showErrorBox` + `app.quit()` |
| `electron/src/backend-launcher.js` | 289 | `:23` 端口 env；`:25` 30s 超时；`:117-135` 健康轮询；`:214-221` bootOnce；`:223-255` 崩溃重启；`:257-278` 首启 catch throw |
| `xiao6-ui/server.py` | 2617 | `:186-219` `/api/health`；`:2508-2617` `main()`；`:2525` 阻塞自检；`:2591` `serve_forever`；`:2596-2612` `_warmup_embed` |
| `xiao6-ui/self_check.py` | 267 | `:25` 缓存 30s；`:131-168` 外网探测；`:225-260` `run_self_check` |
| `docs/audits/BOOT_CHAIN_AUDIT_REPORT.md` | — | 根因报告（上游产物） |

## A0.3 四确认根因（现状快照）

### RC-1 首启 health 超时无重试（致命）
- `backend-launcher.js:257-278`：首启走 `try { const p = await bootOnce(); ... } catch (e) { throw e; }`。`bootOnce()`（`:214-221`）内含 `await waitForHealth(PORT)`，超时即 reject → catch 抛错。
- `main.js:243-248`：捕获后 `dialog.showErrorBox('小6启动失败', ...)` + `app.quit()` → **整窗退出、无重试 UI**。
- `scheduleRestart`/`monitor`（`:223-255`）仅通过 `p.on('exit')` 监听**运行中崩溃**，对**首次启动超时完全无效**。
- **现状结论**：首次启动失败 = 用户无二次机会，直接退出。

### RC-2 后端端口绑定被阻塞式预热延迟（结构性）
- `server.py main():2525` 在 `serve_forever():2591` **之前**执行 `checks = run_self_check(force=True)`。
- `self_check.py:131-168`：外部网络探测离线累计 `≈10s(Agnes) + 8s(Open-Meteo) + (2~5)×8s(热点) ≈ 26–50s`。
- 期间 `ThreadingHTTPServer` 尚未创建（`:2589`），端口**不监听**。launcher 的 `HEALTH_TIMEOUT_MS=30000`（`:25`）从 spawn 即倒计时 → 端口来不及就绪 → 超时 → 退出。
- **现状结论**：离线/代理未开时，后端预热（26–50s）必然超过 30s 上限，形成计时竞争、后端必输。

### RC-3 首次启动失败直接退出、无恢复能力
- 同 RC-1：`main.js:243-248` 的 `app.quit()` 是终态处置，无 `RECOVERY` / `retry` / `diagnostic` 概念。
- **现状结论**：失败即结束，违反"自愈"目标。

### RC-4 health 语义错误（liveness 与 readiness 混同 → 假健康）
- `server.py:186-219` `/api/health`：每次请求（缓存未命中）重跑 `run_self_check`，且**无论 `ok` 真假都返回 200**（`:190-191` 固定 200）。
- `backend-launcher.js:117-135` `waitForHealth`：仅判定 `res.statusCode === 200`（`:123`），**不读响应体 `ok`**。
- **现状结论**：launcher 无法区分"服务没起"与"服务起了但自检慢"；即便服务就绪，外部探测失败也返回 200（假健康）。

## A0.4 附加现状观察（非根因，记录待后续）

| 项 | 位置 | 说明 |
|---|---|---|
| 端口 env 大小写 | launcher `:23` `XIAO6_PORT` vs `config.py:316` `Xiao6_PORT` | Windows env 大小写不敏感，不致命；代码卫生 |
| ui 版 .bat 超时 | `xiao6-ui/start-xiao6.bat` 10s | 与 launcher 30s 不一致 |
| 前端 health 轮询 | `app.js:2047` 20000ms | 粗粒度，仅显示离线无恢复指引 |
| 依赖无自动校验 | grep `electron/` 无 `pip install` | 零侵入设计如此，缺 Environment Check 层 |

## A0.5 冻结声明

- 本阶段**未修改任何代码 / 配置 / Electron / Python / 依赖**。
- 上述 RC-1~RC-4 与 `BOOT_CHAIN_AUDIT_REPORT.md` 完全一致，确认无误，作为 Phase A2 实现的修改基准。
- 下一步：Phase A1（Boot Manager v2 设计，仅设计不编码）。

---

*Phase A0 完成。只读冻结，等待 Phase A1。*
