# Phase 8 — Computer Perception MVP · 最终报告（PHASE8_FINAL_REPORT）

> 状态：**Implementation Only · 完成待 Freeze / Gate 审核**
> 身份：Senior Developer（高级开发工程师）吴八哥
> 冻结前置：Phase 6 已冻结 PASS / Phase 7 已冻结 PASS / Phase 8 Order 1 已冻结
> 事件契约基线：DOMAIN 66 → **71**；SYSTEM 6 → **8**

---

## 0. 执行纪律回执（完成纪律）

- 一次性完成 9 大块（UIA / OCR / Vision / SemanticFusion / PerceptionRuntime /
  PerceptionState / Verification Upgrade / 事件契约 / Mock）。
- 全程未进入 Phase 9、未新增任何超出 MVP 范围的功能。
- 测试完成后自动修复全部测试计数断言、新增 Phase 8 MVP 测试、重跑 Phase 6/7/8 全量测试，
  **结果：29 个测试文件全部 PASS，0 FAIL / 0 Regression**。
- 本报告为交付物；完成即停止，等待最终 Gate 审核与 Freeze 批准。

---

## 1. 概述与交付总结

Phase 8 MVP 在**已冻结的 Phase 6/7 架构**之上，新增一层「计算机感知（Computer Perception）」——
把屏幕像素经 **Screen Capture → UIA → OCR → Vision → Semantic Fusion** 融合为统一的
`PerceptionModel`，通过既有 EventBus 脊柱发布 `PERCEPTION_*` 观察事件，并复用 Phase 7 的
`COMPUTER_WORLD_SYNC` 契约富化 World Model。

**核心铁律贯穿始终**：Vision 永远只能产出 Observation，**绝不控制**电脑；不新增 Mouse/Keyboard
自动化、不 UI Click、不 Auto Input、不 Browser Control；不新增 Executor / Permission / Policy
架构，也不新增第二 Runtime / 第二 World Model / AppState 写入口。

---

## 2. 修改文件列表

### 新增文件（7 个模块 + 2 个测试）
| 文件 | 职责 |
|------|------|
| `perception_model.py` | 统一感知模型 DTO（承载融合后观测事实，禁推理/规划） |
| `uia_provider.py` | UIA 抽象 + `MockUiProvider`（仅观察，产出结构化 UI 树） |
| `ocr_provider.py` | OCR 抽象 + `MockOcrProvider`（整屏/区域识别，低置信标记） |
| `vision_provider.py` | Vision 抽象 + `MockVisionProvider`（只读 Observation，绝不控制） |
| `semantic_fusion.py` | `SemanticFusion.merge`：UIA+OCR+Vision → `PerceptionModel`（禁推理/规划） |
| `perception_runtime.py` | Perception Runtime（EventBus 生产者，不新建第二 Runtime） |
| `perception-state.js` | 前端纯投影层（订阅 `AppState('*')`，不写 AppState） |
| `tests/phase8-mvp.backend.test.py` | 后端 9 大块验证（11 项检查） |
| `tests/phase8-mvp.frontend.test.js` | 前端投影层 + 事件契约验证（5 项检查） |

### 修改文件（3 个，最小侵入）
| 文件 | 修改内容 |
|------|----------|
| `eventbus.py` | `DOMAIN_EVENT_NAMES` +5（66→71）；`SYSTEM_EVENT_NAMES` +2（6→8） |
| `zz-events.js` | `EVENTS` +5（66→71）；`SYSTEM_EVENTS` +2；新增 `BATCH_8`（5 个 PERCEPTION 事件） |
| `verification.py` | `verify(action, result, observation=None)` 优先用观察快照；新增 `PerceptionWorldModelObserver`（复用 Perception 只读快照）；**不新增第二 Verification** |

### 测试计数维护（13 个既有测试文件）
phase6-order1.backend / phase6-hotfix / phase6-order1…order8.frontend / phase7-order1…order4.frontend /
phase7-order2…order4.backend / phase8-order1.frontend+backend —— 全部将硬编码 `66→71`、`6→8` 计数断言
对齐新事件契约；`phase6-order1.backend` 的 `expected` 集合补 5 个 PERCEPTION 事件；
`phase6-hotfix` 的 `EXPECTED_SYSTEM` 补 2 个系统事件。

### 修复的既有 Bug（1 处，属本次新增代码）
`uia_provider.py`：`MockUiProvider` 构造 `UiElement("DESKTOP","desktop", role="desktop")` 同时以位置参数
与关键字传入 `role`，触发 `TypeError`。已改为 `UiElement("DESKTOP", "desktop")`。此 Bug 会使所有依赖
UIA 树的测试级联失败，修复后全绿。

---

## 3. 架构影响分析（Architecture Review）

**结论：未破坏任何冻结链，无旁路、无第二 Runtime / Permission / Policy。**

- **宪法合规**：所有状态变更仍经 EventBus 单一脊柱；UI 只经 `AppState.applyEvent` 写入；
  Perception 是「生产者 + 纯投影」，与 Capture Runtime / World Model 生产者同构，不另立通道。
- **无第二 Runtime**：`PerceptionRuntime` 仅持有 `CaptureRuntime` + 三个 Provider + `SemanticFusion`，
  是 EventBus 的生产者，接入既有统一 Runtime（EventBus → AppState → 投影），**不新建第二套运行时**。
- **无第二 Permission / Policy**：`perception_runtime.py` 不 import `permission_guard` / `policy_engine` /
  `computer_executor` / `agent_runtime`（已由测试 9b Scope 静态检查断言）。
- **无第二 World Model 架构**：World Model 经既有 `COMPUTER_WORLD_SYNC` 契约富化（Perception 为其生产者之一，
  翻译 UIA 顶层 window 为 `windows[]`），**未新增 World Model 模块**。
- **AppState 写入口未变**：`perception-state.js` 为纯投影（订阅 `AppState('*')` 重建本地投影），
  不新增 `state.perception` 子树、不新增 reducer、不写 AppState（已测试 D 断言 `AppState` 无 `perception` 子树、
  `computer` 子树不变）。
- **Galaxy / Overlay 未触碰**：前端仅新增 `perception-state.js` 数据投影层，未改 Three.js / WebGL / Overlay。

---

## 4. 新增模块说明（9 大块）

1. **UIA Foundation（仅观察）**：`UiElement`/`UITree`/`UiProvider` 抽象 + `MockUiProvider`（确定性合成
   记事本/资源管理器 UI 树）。无任何 click/type/invoke 控制方法。
2. **OCR Foundation（整屏/区域）**：`OcrSpan`/`OcrResult`/`OcrProvider` 抽象 + `MockOcrProvider`。
   支持 `region` 裁剪；低置信不伪造，标记 `lowConfidence = confidence < 0.5`。
3. **Vision Foundation（只读 Observation）**：`VisionFact`/`VisionObservation`/`VisionProvider` 抽象 +
   `MockVisionProvider`。产出类别/bbox/confidence/label；`has_actionable` 仅供上层判断是否提醒，
   **不触发控制**；Fact 无 `action` 字段。
4. **Semantic Fusion**：`SemanticFusion.merge(ui_tree, ocr_result, vision_obs, frame, ttl)` → `PerceptionModel`。
   以 UIA 树为主干，mergedText = UIA name/value + OCR 文本去重，focused_element 来自 UIA 焦点引用，
   monitors 来自帧元数据。**禁推理/规划**（已断言无 `plan`/`next_action` 字段）。
5. **Perception Runtime**：`Perceive()` 跑完整采集→理解→融合→发布周期；`_world_from_model` 翻译 World Model
   快照；`_publish` 发出 `PERCEPTION_*` + `COMPUTER_WORLD_SYNC` +（可选）`perception_alert`/`perception_health`。
   `observe()` 返回只读快照供 Verification 复用。
6. **Perception State（纯投影）**：`perception-state.js` 订阅 `AppState('*')`，按 5 个 `PERCEPTION_*` 事件
   重建本地投影；仅在确有变化时 `notify()`（防噪声）；API：`getPerception/getFocusedElement/
   getVisionFacts/getOcrSpans/getMergedText/onPerceptionChange`。
7. **Verification Upgrade**：`verify(..., observation=None)` 优先采用显式观察快照，否则回退 `self.observer()`；
   新增 `PerceptionWorldModelObserver`（复用 Perception `observe()` 只读快照，转 Verification 兼容字典）。
   **未新增第二 Verification 类**。
8. **事件契约**：DOMAIN +5 / SYSTEM +2，前后端逐字一致；`BATCH_8` 聚合 5 个 PERCEPTION 事件。
9. **Mock**：`PerceptionRuntime()` 默认全 Mock（`uia/ocr/vision/capture` 均为 `mock`），零真实桌面/OCR/Vision/UIA
   依赖；Provider 类型校验生效（传入非 Provider 实例抛 `TypeError`）。

---

## 5. Event Contract 变化（Event Contract Review）

| 维度 | 修改前 | 修改后 | 校验 |
|------|--------|--------|------|
| `DOMAIN_EVENT_NAMES` | 66 | **71**（+5 PERCEPTION_*） | 后端 test8 / 前端 testB 断言 == 71 |
| `SYSTEM_EVENT_NAMES` | 6 | **8**（+`perception_alert`/`perception_health`） | 后端 test8 / 前端 testB 断言 == 8 |
| `zz-events.js EVENTS` | 66 | **71** | 与后端逐字 diff 无差集 |
| `zz-events.js SYSTEM_EVENTS` | 6 | **8** | 与后端 `SYSTEM_EVENT_NAMES` 值集合一致 |
| `BATCH_8` | — | 新增（5 个 PERCEPTION 事件） | 前端 testA 断言长度 5 |

新增 5 个 DOMAIN 事件（均为观察类，无控制语义）：
`PERCEPTION_SYNC` / `PERCEPTION_UI_UPDATED` / `PERCEPTION_OCR_UPDATED` /
`PERCEPTION_VISION_FACT` / `PERCEPTION_FOCUS_CHANGED`。

> 命名纪律：`PERCEPTION_FOCUS_CHANGED` 与 Phase 6 既有 `FOCUS_CHANGED`（银河节点聚焦态）**独立共存、互不冲突**，
> 二者语义不同，均已保留。

契约纪律强化：`publish_domain` 对未知名抛 `ValueError`；`publish_system` 同样校验 `SYSTEM_EVENT_NAMES`。
所有新事件均经单一来源登记，**无同义漂移、无遗留旧计数**。

---

## 6. Runtime 数据流（Runtime Review — 无旁路）

```
Screen ──▶ CaptureRuntime.capture ──▶ Frame(metadata, 内存像素不进 SSE)
                                      │
                                      ├─▶ UIA.tree()          ─┐
                                      ├─▶ OCR.recognize()     ├─▶ SemanticFusion.merge ─▶ PerceptionModel
                                      ├─▶ Vision.understand()─┘            │
                                                                          ▼
                                          PERCEPTION_SYNC / _UI_UPDATED / _OCR_UPDATED
                                          / _VISION_FACT / _FOCUS_CHANGED   ──▶ EventBus(TOPIC_SSE)
                                          COMPUTER_WORLD_SYNC (富化 World Model)       │
                                          perception_health (SYSTEM)                  ▼
                                                                      AppState 投影 / 前端 perception-state.js
                                                                      World Model ──▶ Agent（经既有 Phase 7 链路）
```

- **旁路检查**：`PerceptionRuntime` 不调用任何 Executor / PermissionGuard / PolicyEngine；
  全周期只 `publish_domain` / `publish_system`。**不发布任何 `COMPUTER_ACTION_*` 事件**（测试 5/5b 断言）。
- **闭环纪律**：Screen Capture → Perception → World Model → Agent → Computer Action → Verification →
  World Model 完整；Vision 永远只 Observation，绝不能 Control。

---

## 7. Verification 数据流（Verification Upgrade Review）

```
VerificationLayer.verify(action, result, observation=None)
        │
        ├─ observation 显式传入？ ──是──▶ 直接用作观测
        └─ 否 ──▶ self.observer()（RealObserver / MockObserver / PerceptionWorldModelObserver）
                        │
                        ▼
        _verify_<capability>(action, data, obs) ──▶ (verified: bool, detail)
                        │
                        ▼
        COMPUTER_ACTION_VERIFIED / COMPUTER_ACTION_UNVERIFIED（沿用 Phase 7 合约）
```

- `PerceptionWorldModelObserver(rt)` 复用 `PerceptionRuntime.observe()` 只读快照，转
  `{processes, applications, focused_window, visionFacts, uiTree, ocrText}`，与 `RealObserver`
  **同接口、不重复 World Model 观测逻辑**。
- **未新增第二 Verification**：Verification 仅是裁决方，Perception 是观察源，职责不混（测试 7 断言）。

---

## 8. Performance Review

- **TTL 节流**：`PerceptionRuntime` 默认 `ttl=2000ms`，后台循环由宿主（server.py）以线程 + TTL 驱动，
  非自递归，避免事件风暴。
- **像素纪律**：原始像素字节仅驻留内存（`Frame.data`），**不进 SSE、不落盘**（沿用 Phase 7 截图纪律）；
  事件载荷仅含元数据（`screenId/monitors/mergedText` 等文本/结构），体积小。
- **快照复用**：`observe()` 返回缓存的 `state.to_dict()`，Verification 复用不重新采集，零额外 CPU。
- **投影降噪**：`perception-state.js` 仅在投影确有变化时 `notify()`，避免无变化时的订阅风暴。
- **焦点变更节流**：`PERCEPTION_FOCUS_CHANGED` 仅在焦点元素变化时发布，非每帧。
- **风险点**：生产环境真实 UIA/OCR/Vision Provider 的采集频率须由 `FEATURE_PERCEPTION` 门控与宿主 TTL
  约束（本 MVP 用 Mock，频率由测试驱动）；建议生产默认 TTL ≥ 1000ms、单显示器、避免与 Screen Capture
  同帧争用。

---

## 9. Safety Review（Vision 绝不控制）

- **静态保证**：`vision_provider.py` 不 import 任何控制库（`pyautogui`/`autopy`/`pynput`/`SendInput`），
  `VisionFact` 无 `action` 字段（测试 3 断言）。
- **动态保证**：`PerceptionRuntime.perceive()` 全周期不发布任何 `COMPUTER_ACTION_*`（测试 5 断言）。
- **可提醒不可控**：当 Vision 发现 `error_dialog`/`login_screen`/`captcha` 时，仅发 `perception_alert`
  （SYSTEM telemetry，类 `scene`/`agent_state`），由上层决定是否主动告知用户；**不触发任何执行器**
  （测试 5b：error_dialog → `perception_alert` 触发，仍 0 个 `COMPUTER_ACTION_*`）。
- **闭环铁律**：Screen Capture → Perception → World Model → Agent → Computer Action → Verification →
  World Model；Vision 处于「观察」环节，永远不能跳过 Agent/Executor 直接控制电脑。

---

## 10. 测试结果（Test Results）

**全量重跑（Phase 6 / Phase 7 / Phase 8）：29 个测试文件，全部 PASS，0 FAIL / 0 Regression。**

- 后端 `.test.py`：phase6-hotfix / phase6-order1..order8（含 integration）/ phase7-order2..order4 /
  phase8-order1 / **phase8-mvp** —— 全部 PASS。
- 前端 `.frontend.test.js`：phase6-order1..order8 / phase7-order1..order4 / phase8-order1 /
  **phase8-mvp** —— 全部 PASS。
- 新增 Phase 8 MVP 覆盖：UIA / OCR / Vision / SemanticFusion / PerceptionRuntime / PerceptionState 投影 /
  Verification Upgrade / 事件契约 71==71 & 8==8 / Mock & Scope 纪律。
- 环境说明：integration 测试依赖 `embed`（`numpy`）。本机通过 managed venv（Python 3.13 + numpy）运行
  以达成 0 FAIL；**该 4 个 integration 失败纯为缺 numpy 的环境问题，与 Phase 8 改动无关**。

---

## 11. 风险分析（Risk Analysis）

| 风险 | 等级 | 说明 / 缓解 |
|------|------|-------------|
| 真实 Provider 性能 | 中 | 真实 UIA/OCR/Vision 采集耗时；由 `FEATURE_PERCEPTION` + TTL 门控，默认低频 |
| 事件风暴 | 低 | TTL + 焦点变更节流 + 投影降噪三重防护 |
| 像素隐私 | 低 | 像素字节不进 SSE/不落盘，仅元数据流通 |
| Vision 误提醒 | 低 | `has_actionable` 仅用于提醒，不触发控制；`perception_alert` 为 SYSTEM 通道 |
| 上下文误用 | 低 | Perception 为纯观察；任何「理解/规划/执行」必须由 Agent 经既有链路完成 |

---

## 12. Freeze 建议（Freeze Recommendation）

- **建议：Phase 8 MVP 进入 Freeze。** 5 维 Gate Review 全部通过，测试 0 FAIL / 0 Regression，
  未破坏 Phase 6/7 任何冻结链。
- **冻结范围**：`perception_model.py` / `uia_provider.py` / `ocr_provider.py` / `vision_provider.py` /
  `semantic_fusion.py` / `perception_runtime.py` / `perception-state.js` / `eventbus.py`（+5/+2）/
  `zz-events.js`（+5/+2/BATCH_8）/ `verification.py`（ observation 参数 + `PerceptionWorldModelObserver`）。
- **冻结后禁止**：在感知层新增任何控制能力、把 Vision 接入 Executor、在 `perception-state.js` 写 AppState、
  新增第二 Runtime / Permission / Policy / World Model。
- **下一步（待批准后）**：Phase 9 Goal Decision Engine 可消费本 MVP 的 `PERCEPTION_*` 观察与 World Model
  富化结果，但感知层本身不再扩展控制语义。

---

## 13. 完成纪律（Stop & Await Gate）

- 全部 9 大块已实现、测试全绿、Gate Review 完成、本报告交付。
- **立即停止**：未进入 Phase 9，未新增任何超出 MVP 的功能。
- 等待最终 **Gate 审核 / Freeze 批准** 后，方可开启 Phase 9。
