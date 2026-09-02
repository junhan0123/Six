# PHASE 8 — Order 1「Screen Capture Foundation」实现报告

> **模式**：Implementation Only（严格遵循小6开发宪法）
> **纪律**：不重新设计 / 不扩展 Scope / 不进入 Order 2 / 完成即停止
> **冻结基线**：Phase 6 PASS · Phase 7 PASS · Phase 8 Architecture Specification v1.0（Design Only）PASS
> **日期**：2026-08-03（GMT+8）

---

## 1. 修改文件

### 新增（Production 模块）
| 文件 | 职责 | Scope 边界 |
|------|------|-----------|
| `xiao6-ui/frame.py` | 类型化 Frame DTO：`Frame` / `FrameMetadata` / `CaptureRequest` / `DisplayInfo`（`__slots__` 强制封闭，禁裸 dict） | 仅描述"采集到什么像素"，不含任何理解 |
| `xiao6-ui/capture_provider.py` | `CaptureProvider`（抽象）+ `RealCaptureProvider`（mss 惰性导入）+ `MockCaptureProvider`（零真实桌面依赖） | 只负责 Capture → Frame → Metadata |
| `xiao6-ui/capture_runtime.py` | `CaptureRuntime`：Provider → Frame → Event → EventBus | 仅发布 `SCREEN_CAPTURED` / `SCREEN_CAPTURE_FAILED` |

### 新增（测试）
| 文件 | 验证项 |
|------|--------|
| `tests/phase8-order1.backend.test.py` | Frame DTO / Mock Provider / CaptureRuntime 发布 / 失败路径 / Scope 静态检查 / 事件合约 / publish_domain 纪律（8 项） |
| `tests/phase8-order1.frontend.test.js` | 合约含新事件（66）/ applyEvent 不写 AppState / 非合约事件被拒 / 前后端对称（5 项） |

### 修改（事件合约扩展 64 → 66）
- `xiao6-ui/eventbus.py`：`DOMAIN_EVENT_NAMES` 新增 `SCREEN_CAPTURED`、`SCREEN_CAPTURE_FAILED`
- `xiao6-ui/zz-events.js`：`EVENTS` 新增同 2 个事件（前后端逐字对称）

### 修改（回归测试计数维护 64 → 66）
为保持 Phase 6/7 回归全绿，将现存硬编码事件总数断言同步维护为 66（仅数值/白名单，不改架构）：
`phase6-order1.backend.test.py`（expected 白名单）、`phase6-order1/03/04/05/08.frontend.test.js`、
`phase7-order1/02/03.frontend.test.js`、`phase7-order2/03/04.backend.test.py`、`phase7-order3.backend.test.py`。

> **未修改**（受 Scope 红线约束）：`verification.py` / `agent_runtime.py` / `policy_engine.py` / `permission_guard.py` / `computer_executor.py` / `computer-state.js`（ComputerState）/ `galaxy-state.js` / `overlay-runtime.js` / `app-state.js` / 任何 UI·CSS·Three.js。

---

## 2. 架构影响

- **不破冻结链**：`CaptureRuntime` 仅是 **EventBus 的生产者**（与既有 `COMPUTER_WORLD_SYNC` 生产者同构），接入既有统一 Runtime（EventBus → AppState → 投影），**不新建第二套 Runtime**。
- **AppState 零改动**：`SCREEN_CAPTURED` 是已登记的领域事件，但 `app-state.js` **无对应 reducer**；`applyEvent` 对其 `emit` 但不修改任何状态（已用前端测试 B 验证 `computer` 子树不变）。PerceptionState 按 Phase 8 规范推迟到 Order 6。
- **像素不进 SSE**：`SCREEN_CAPTURED` 信封仅携带帧元数据（`frame_id` / `display_id` / `size` / `pixel_format` / `byte_len` / `capture_ms` / `provider`），**原始像素字节仅驻留内存、由调用方持有**，未来供 Perception Runtime / Verification 消费，绝不落入总线或磁盘。
- **调用关系（确认）**：`CaptureRuntime.capture → provider.capture → Frame → eventbus.publish_domain(SCREEN_CAPTURED)`。无任何 Agent / Guard / Executor / Verification 交叉调用。

---

## 3. Capture Runtime

```
CaptureRequest(display_id, source, region?, size_hint?)
        │
        ▼
  CaptureRuntime.capture(request)
        │  provider = MockCaptureProvider (默认) | RealCaptureProvider
        ▼
  provider.capture(request)  ──►  Frame(metadata + 像素字节，仅内存)
        │
        ├─ 成功 ─► publish_domain("SCREEN_CAPTURED",  {元数据, byte_len})   ★ 无像素字节
        │
        └─ 失败 ─► publish_domain("SCREEN_CAPTURE_FAILED", {reason: unavailable|exception})
```

- `CaptureRuntime(provider=None)` 默认注入 `MockCaptureProvider`，保证无真实桌面也能运转。
- 失败被捕获并降级为 `SCREEN_CAPTURE_FAILED`（不向上抛），`failed_count` 自增。
- `last_frame` 仅作内存句柄；不写文件、不缓存到磁盘。

---

## 4. Event Contract

| 通道 | 事件 | 说明 |
|------|------|------|
| DOMAIN（领域） | `SCREEN_CAPTURED` | 一次采集成功，携带帧元数据 |
| DOMAIN（领域） | `SCREEN_CAPTURE_FAILED` | 采集失败（真实不可用 / 异常） |

- 仅此 2 个事件，符合"本 Order 仅允许 SCREEN_CAPTURED / SCREEN_CAPTURE_FAILED"。
- 后端 `DOMAIN_EVENT_NAMES` 64 → **66**；前端 `zz-events.js EVENTS` 64 → **66**；两端**严格对称**（脚本验证 `SYMMETRIC True`）。
- `SCREEN_CAPTURED` 经 `applyEvent` 流入前端时**不产生任何状态变更**（无 PerceptionState 投影，Order 6 才建）。
- 严禁 OCR / Vision / UIA / Semantic / Computer Action / 鼠标 / 键盘 / 自动化类事件——Scope 静态检查已覆盖。

---

## 5. DTO（Frame）

全部使用 `__slots__` 强制字段封闭，杜绝以裸 dict 在调用边界传递帧数据：

- **`Frame`**：`frame_id` / `timestamp` / `data(bytes, 仅内存)` / `metadata(FrameMetadata)`；`to_dict()`（可选 `include_data`）、`from_dict()`。
- **`FrameMetadata`**：`display_id` / `display_name` / `source('full'|'window'|'region')` / `width` / `height` / `pixel_format('RGB'|'RGBA'|'BGR')` / `region(x,y,w,h)` / `bytes_per_pixel` / `capture_ms` / `provider`。
- **`CaptureRequest`**：`display_id` / `source` / `region` / `size_hint`（采集请求描述）。
- **`DisplayInfo`**：`display_id` / `name` / `width` / `height` / `is_primary`（多显示器支持）。

`__slots__` 使任意 `frame.some_random_attr = 1` 抛 `AttributeError`——以测试断言"类型化契约不可被绕过"。

---

## 6. 测试结果

### 新增 Phase 8 Order 1
| 套件 | 结果 |
|------|------|
| `phase8-order1.backend.test.py` | **8 / 8 PASS，0 FAIL** |
| `phase8-order1.frontend.test.js` | **5 / 5 PASS，0 FAIL** |

### Phase 6 / 7 回归（全量现存测试）
| 层 | 文件 | 结果 |
|----|------|------|
| 后端 | phase6-hotfix / phase6-order1 / phase7-order2 / phase7-order3 / phase7-order4 / phase7-order4.integration | **全部 PASS，0 FAIL**（74/74） |
| 前端 | phase6-order1..8 + phase7-order1..4（12 文件） | **全部 exit 0，0 FAIL** |

> **结论**：Phase 6 + Phase 7 全量回归 **0 失败 / 0 回归**；事件合约从 64 平滑扩展至 66，对称无漂移。

---

## 7. 风险分析（Order 1 及前向）

1. **mss 依赖**：`RealCaptureProvider` 惰性导入 `mss`；生产环境需安装 `mss`，缺失时 `list_displays` 返回 fallback、`capture` 抛 `CaptureUnavailableError`（失败路径已被测试覆盖）。
2. **多显示器**：`mss.monitors[0]` 为全屏聚合，按 `DISPLAY-N` 解析；Order 1 仅基础支持，区域/窗口精准映射留 Order 2（UIA）。
3. **隐私/权限**：截图涉及屏幕隐私。当前仅采集、不存储、不落盘；未来 Perception 层须经 `PermissionGuard` + Policy Engine 管控（Order 2+ 接入）。
4. **性能**：全屏 RGB 约 1920×1080×3 ≈ 6MB/帧。Order 1 不进 SSE（仅元数据）；未来 Vision/OCR 消费须受帧率/TTL/缓存约束（Phase 8 风险清单已列）。
5. **磁盘安全**：严禁落盘——像素仅驻留内存，`CaptureRuntime` 不写文件（Scope 静态检查已确认无 `open`/`shell=True`/`os.system`）。
6. **失败处理**：真实不可用/异常均被 `CaptureRuntime` 捕获并发布 `SCREEN_CAPTURE_FAILED`（`reason: unavailable|exception`），不向上抛。
7. **合约膨胀**：64→66 已两端同步并维持对称；现存计数断言已维护为 66。
8. **Mock 保真度**：`MockCaptureProvider` 生成确定性合成像素（非真实屏幕），仅用于无桌面测试，不可用于生产验证。
9. **循环观察**：`CaptureRuntime` 本身不自动循环；未来若接入定时采集须受节流/熔断（Order 6+）。
10. **跨层边界**：`CaptureRuntime` 不依赖 Agent/Guard/Executor/Verification（静态检查通过）；Vision 绝不直调 Executor（架构红线，Order 2+ 遵守）。

---

## 8. 下一步建议

- **进入 Order 2「UI Automation Foundation」**（须单独批准）：实现 UIA 优先于 OCR 的 `UI Understanding Layer`——`Element` / `Role` / `Tree` / `Accessibility` / `Focus` / `Window Mapping`，作为 Perception 第二层；**不**在本 Order 实现 OCR / Vision / Semantic。
- 保持 Scope 纪律：Capture Runtime 不扩展理解能力；OCR/Vision/Semantic 分别在 Order 3/4/5 实现。
- 待批准后再启动 Order 2；本 Order 1 已冻结。

---

**状态**：Phase 8 Order 1 实现完成，测试全绿，报告生成。**按完成纪律立即停止，等待批准，不进入 Order 2。**
