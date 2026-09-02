# Boot Manager v2 设计（Phase A1 — Design Only）

> 任务：Xiao6 Reliability & Knowledge Preservation Upgrade — Part 1 / Phase A1
> 模式：**仅设计，不编码**。本文件描述目标架构与契约，实现见 Phase A2。
> 依据：Phase A0 冻结确认 + `BOOT_CHAIN_AUDIT_REPORT.md` 根因 RC-1~RC-4
> 日期：2026-08-04

---

## A1.1 设计目标与原则

修复 RC-1~RC-4 四项根因，核心原则：

1. **进程存活（liveness）与功能就绪（readiness）必须分离** —— 端口先活，功能后熟。
2. **首次启动失败不得退出应用** —— 进入 `RECOVERY`，给用户"重试 / 诊断"出口。
3. **首启长窗口、运行短探针** —— 启动时允许预热耗时，运行期崩溃快速失败。
4. **可观测** —— 启动每一步都有 IPC 状态事件 + 结构化日志 + 错误上下文。
5. **小步、禁重构** —— 仅改必要点，不动既有架构与冰冻治理文档。

约束（来自任务禁令）：不引入新 Runtime / Memory / EventBus / 依赖；不改 Golden State；进入实现仍需遵守 Phase A2 的"修改前说明、修改后验证"。

---

## A1.2 启动状态机（Boot State Machine）

状态集合：`INIT → CHECK_ENV → STARTING → ALIVE → READY`（正常路径）
                    `→ DEGRADED`（就绪但部分功能受限）
                    `→ RECOVERY`（首启失败，可重试/诊断）
                    `→ FAILED`（重试耗尽，终态，但仍给诊断非静默退出）

```
        ┌─────────────────────────────────────────────────────────┐
        │                                                         │
        ▼                                                         │
   [INIT] ──▶ [CHECK_ENV] ──(python 可用 / 端口决策)──▶ [STARTING] │
                                                       │           │
                                            bootOnce 超时 / 起服失败 │
                                                       │           │
                                                       ▼           │
                                                 [RECOVERY] ◀──────┘
                                                  │   │   ▲
                                   retry 成功      │   │   │ retry 再次失败
                                                  ▼   │   │
                                              [STARTING] │
                                                  │       │
                                   serve_forever 起 │       │ 超过 MAX_BOOT_RETRIES
                                                  ▼       │
                                               [ALIVE] ──┘
                                                  │
                                   /api/ready 返回 ok=true │
                                                  ▼
                                               [READY]
                                                  │
                                   parts of self_check fail │
                                                  ▼
                                            [DEGRADED]（仍可用，UI 提示受限功能）
                                                  │
                                   MAX_BOOT_RETRIES 耗尽且仍失败
                                                  ▼
                                              [FAILED]（终态：展示诊断 + 退出按钮，非 app.quit 静默）
```

### 状态语义表

| 状态 | 含义 | 对外（IPC `backend:status`） |
|---|---|---|
| `INIT` | 启动器初始化 | `starting` |
| `CHECK_ENV` | 探测 Python / 端口 / 依赖 | `starting`（detail: checking env） |
| `STARTING` | 已 spawn 后端，等待端口活 | `starting`（detail: booting, attempt N/M） |
| `ALIVE` | 端口已监听（liveness OK） | `alive`（detail: port open） |
| `READY` | `/api/ready` 返回 ok | `ready` |
| `DEGRADED` | 活但未全就绪（如代理未开） | `ready`（detail: degraded） |
| `RECOVERY` | 首启失败，等待用户决策 | `recovery`（detail: 错误上下文 + retry/diagnostic 选项） |
| `FAILED` | 重试耗尽 | `failed`（detail: 诊断摘要） |

> 注：`ALIVE` 与 `READY` 分离是修复 RC-4 的关键——`ALIVE` 由端口监听决定，`READY` 由 `/api/ready` 的 `ok` 决定。

---

## A1.3 健康模型（Health Model）

### A1.3.1 `/api/health`（liveness only）
- **职责**：仅表示"进程是否存活、端口是否在监听"。
- **行为**：立即返回，不跑 `run_self_check`，不依赖外部网络。
- **响应契约**：
  ```json
  { "status": "alive", "port": 8000, "pid": 12345 }
  ```
  HTTP 200 = 进程活；连接拒绝/超时 = 进程未活。
- **launcher 用法**：`waitForHealth` 只判此端点 200，作为"端口已活"信号（对应状态 `ALIVE`）。

### A1.3.2 `/api/ready`（readiness，新增）
- **职责**：表示"服务是否完成初始化、功能是否就绪"。
- **行为**：返回 `ok` 字段 + 自检摘要（复用现有 `run_self_check`，带 30s 缓存）。
- **响应契约**：
  ```json
  {
    "ok": true,
    "key_present": true,
    "degraded": false,
    "self_check": { "ok": true, "elapsed_ms": 123, "checks": [ ... ] }
  }
  ```
  `ok=true` → `READY`；`ok=false` 但进程活 → `DEGRADED`（UI 提示受限功能，仍可进）。
- **launcher 用法**：进入 `ALIVE` 后轮询 `/api/ready`，`ok` 决定 `READY`/`DEGRADED`。

### A1.3.3 分离带来的修复
- RC-4（假健康）：`/api/health` 不再耦合外部网络，永远"真"反映存活；就绪与否交给 `/api/ready` 的 `ok`。
- RC-2（预热阻塞端口）：`serve_forever` 提前 → `/api/health` 立即 200 → `ALIVE` 快速达成；`run_self_check` 移到 `serve_forever` **之后**异步执行，`/api/ready` 在预热完成后才返回 `ok`。

---

## A1.4 启动策略（Startup Strategy）

| 阶段 | 窗口 | 说明 |
|---|---|---|
| `CHECK_ENV` | 即时 | 探测 python / 端口占用 / 依赖冒烟 |
| `STARTING` → `ALIVE` | **STARTUP_PROBE_MS = 120000**（首启长窗口） | 给离线/大库预热余量；期间每 400ms 轮询 `/api/health` |
| `ALIVE` → `READY` | 复用同上窗口 | 轮询 `/api/ready`，容忍自检慢 |
| 运行期崩溃重启 | 短间隔 + 指数退避（沿用 `BACKOFF_BASE_MS=1500`, `BACKOFF_MAX_MS=20000`, `MAX_RESTARTS=5`） | 快速失败检测；达上限转 `FAILED` |

- 首启长窗口（120s）直接消除 RC-2 的"30s < 26–50s 预热"计时竞争。
- 运行期仍用短探针 + 退避（原 `scheduleRestart` 逻辑保留），不退化自愈能力。

---

## A1.5 失败策略（Failure Strategy）—— 修复 RC-1 / RC-3

**禁止**：首次启动失败直接 `app.quit()`。

**改为**：`bootOnce` 超时/起服失败 → 进入 `RECOVERY` 状态（不再 `throw` 到 `main.js` 触发 quit）。

`RECOVERY` 向渲染进程推送：
```json
{
  "status": "recovery",
  "detail": {
    "stage": "STARTING",
    "reason": "健康检查超时（120s）",
    "diagnostic": {
      "python": "C:/.../Python311/python.exe",
      "port": 8000,
      "portInUse": false,
      "selfCheckReachable": false,
      "proxySet": false,
      "suggestions": [
        "确认已开启 Clash 代理（XIAO6_PROXY_URL=http://127.0.0.1:7890）",
        "确认 AGNES_API_KEY 已配置",
        "检查 8000 端口是否被占用"
      ]
    },
    "canRetry": true
  }
}
```

- 前端据此渲染"重试 / 查看诊断"面板（不退出）。
- 用户点"重试" → 重新 `bootOnce`（计入 `bootRetries`，上限 `MAX_BOOT_RETRIES=2`）。
- `MAX_BOOT_RETRIES` 耗尽 → `FAILED`：展示诊断摘要 + 退出按钮（用户主动退出，**非** `app.quit` 静默）。

> 这把 RC-1（无重试）与 RC-3（失败即退出）同时修复：首启失败转为可恢复状态。

---

## A1.6 启动可观测性（Observability）

### A1.6.1 IPC 状态事件
复用现有 `backend:status` 通道（`main.js:178-184` → 渲染进程 `app.js` 监听 `backend:status`）。
扩展 `status` 取值：`starting | alive | ready | degraded | recovery | failed`（对应状态机）。
`detail` 携带阶段 / 尝试次数 / 诊断摘要。

### A1.6.2 启动日志
现有 `backend-launcher.js` 结构化日志（`logLine`，带时间戳+级别+logFile）保留并增强：
- 每个状态转换写一行：`[ts] [BOOT] state=CHECK_ENV`
- 失败原因写 `ERROR` 级 + 诊断 JSON。

### A1.6.3 错误上下文
`RECOVERY`/`FAILED` 的 `detail.diagnostic` 包含可操作的排查建议（见 A1.5），供前端"诊断报告"页渲染。

---

## A1.7 映射：设计 → 当前代码（实现指引，非实现）

| 设计项 | 当前代码 | 实现目标（Phase A2） |
|---|---|---|
| liveness 端点 | `server.py:186-219` `/api/health` 跑 self_check | 改为只回存活，新增 `/api/ready` 跑 self_check |
| 预热后移 | `server.py:2525` 在 `serve_forever():2591` 前 | 移到 `serve_forever` 之后异步 |
| 首启长窗口 | `backend-launcher.js:25` `HEALTH_TIMEOUT_MS=30000` | 首启用 `STARTUP_PROBE_MS=120000` |
| 首败不退出 | `backend-launcher.js:257-278` throw → `main.js:243-248` quit | 首败转 `RECOVERY`，不再 throw |
| 状态机 | 现有 `STATUS` 枚举（starting/connected/ready/down/restarting/failed） | 扩展为 8 态（含 alive/recovery/degraded） |

---

## A1.8 验证计划（对应 Phase A3）
1. 首次启动：端口快速 `ALIVE`，`/api/ready` 预热后 `ok`。
2. 无网络启动：不阻塞端口，`/api/health` 立即活，`/api/ready` 返回 degraded。
3. 代理关闭：同无网络，给出"开 Clash"建议。
4. 后端异常退出：运行期 `scheduleRestart` 退避重启。
5. 重复启动：单实例锁 + `isPortOpen` 直连。
6. 端口占用：连接已有后端或提示冲突。

---

*Phase A1 设计完成。下一步：Phase A2 实现 P0 修复（小步、禁重构）。*
