# Phase 8 — Perception Intelligence Specification v1.0（冻结规范）

> **阶段性质**：Design Only / Analysis Only（设计冻结，未实现）
> **依据（重新读取的真实冻结体系，非记忆）**：
> - Phase 6 冻结：`eventbus.py`（事件合约 64 DOMAIN + 6 SYSTEM）、`app-state.js`（唯一写入口 `applyEvent`）、`galaxy-state.js`（纯投影）、`overlay-runtime.js`（纯投影）、`policy_engine.py`（四级授权唯一来源）、`intent_gateway.py`（意图生命周期）。
> - Phase 7 冻结：`computer-state.js`（World Model 纯投影）、`capability_registry.py`、`permission_guard.py`、`computer_executor.py`、`verification.py`、`agent_runtime.py`。
> **纪律红线（本规范继承，不可破坏）**：
> - 不写代码、不修改冻结代码、不修改冻结文档、不创建模块、不创建事件、不进 Implementation、不进 Order 1。
> - 本文件为**新规范**（Phase 8 v1.0），非对 Phase 6/7 冻结文档的修改。

---

## 1. Phase 定位

**Phase 8 = Computer Perception（电脑感知），不是 Computer Operating。**

当前小6（Phase 6 + Phase 7 已冻结）具备：

- 理解任务（Intent Gateway → Goal Decision Engine）
- 做决策（Agent Runtime 编排）
- 操作电脑（Permission Guard → Executor，经 Policy Engine 裁决）
- 验证执行（Verification Layer）

但 World Model（Phase 7 Order 1）**只来自结构化数据**：Windows API / Process / Window / File / Browser / Terminal / Device。它知道"有哪些窗口、哪些进程"，但**不理解屏幕**——不知道"屏幕上现在显示的是什么、按钮在哪里、是不是登录界面、有没有弹错误框"。

Phase 8 目标：让小6真正"看懂电脑"。新增 **Perception Layer**，作为 **World Model 之前的一层**：

```
Screen ──▶ Perception ──▶ World Model ──▶ Agent ──▶ Computer Action
```

> 关键边界：**Perception 永不直接控制鼠标/键盘/执行器**。它只观察、理解、产出"用户当前看到的世界"模型。任何动作（点击 Vision 发现的按钮）仍走 Phase 7 冻结链：Task → PermissionGuard → Executor（带坐标 target + confirm 闸门）。

---

## 2. 整体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│  Screen (像素 / 窗口句柄 / 区域 / 多显示器)                            │
└───────────────┬──────────────────────────────────────────────────────┘
                │  raw frames（不理解的原始帧）
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ ① Screen Capture Layer  窗口/区域/全屏/多屏截图 · 缓存/TTL · 内存不落盘 │
└───────────────┬──────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ ② UI Understanding Layer（UIA 优先，非 OCR）                           │
│    Element / Role / Tree / Accessibility / Focus / Window Mapping      │
└───────────────┬──────────────────────────────────────────────────────┘
        ┌───────┴────────┐
        ▼                ▼
┌───────────────┐  ┌───────────────────────────────────────────────────┐
│ ③ OCR Layer   │  │ ④ Vision Understanding（真正视觉语义，不控制）       │
│  文字识别      │  │  "屏幕有什么 / 按钮在哪 / 是否登录界面 / 是否报错"    │
└───────┬───────┘  └───────────────────────┬───────────────────────────┘
        └───────────────┬───────────────────┘
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ ⑤ Semantic Fusion Layer  合并 UIA + OCR + Vision → 统一 Perception Model│
└───────────────┬──────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ ⑥ PerceptionState（新状态：用户当前"看到"的世界，World Model 之前）      │
│    ── 后端：Perception Runtime 持有的实时上游模型（生产者态）           │
│    ── 前端：perception-state.js 纯投影（与 ComputerState 平级，只读）    │
└───────────────┬──────────────────────────────────────────────────────┘
                │  PERCEPTION_* DOMAIN 事件（经 EventBus → AppState）
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  World Model（Phase 7 冻结：AppState.computer + ComputerState 投影）    │
│   —— 被 Perception 富化（新增 perception 子树的观测事实）               │
└───────────────┬──────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Agent Runtime ─▶ Task ─▶ PermissionGuard ─▶ Executor ─▶ Verification  │
│                          ▲                                              │
│                          │ Verification 复用 Perception（非重复 World）  │
└──────────────────────────────────────────────────────────────────────┘
```

**对接冻结体系的三条硬约束**：
1. Perception Runtime 是 **生产者（producer）**，走与现有 World Model 生产者**同一条 EventBus 脊柱**（非第二 Runtime）。
2. 所有 Perception 事实经 `publish_domain` / `publish_system` 单一来源门控（非第二事件系统）。
3. 前端 `perception-state.js` 是 **纯下游投影**（与 `ComputerState` 同级），只读、不 emit，数据单向派生自 `AppState`。

---

## 3. 模块职责

> 以下为**设计定义**（Design Only，未实现）。模块名仅为规范命名，落地时须遵守本规范的接入纪律。

### 一、Screen Capture Layer（屏幕采集层）
- **职责**：负责屏幕采集。支持窗口截图 / 区域截图 / 全屏截图 / 多显示器。
- **提供**：显示器枚举、窗口句柄→位图、区域裁剪、缓存（TTL）、刷新率控制。
- **禁止**：理解图像、做任何语义分析。产出只是"帧"（bitmap / 内存缓冲）。
- **与现有纪律一致**：沿用 Phase 7 `computer_executor._op_capture_screen` 的"截到内存、绝不落盘"原则；原始帧**禁止写磁盘、禁止进日志**。

### 二、UI Understanding Layer（UI 理解层，UIA 优先）
- **职责**：理解 Windows UI。**优先 UI Automation（UIA / Accessibility）**，不是 OCR。
- **建模对象**：
  - `Element`：控件实例（id / name / automation_id）
  - `Role`：控件类型（button / edit / combobox / menu / dialog / pane …）
  - `Tree`：从桌面根到叶的层级结构
  - `Accessibility`：acc name / value / state（enabled/checked/readonly）
  - `Focus`：当前 accessibility focus 元素
  - `Window Mapping`：UIA 元素 ↔ Phase 7 `state.computer.windows` 的 windowId 映射
- **产出**：结构化 UI 树（比 OCR 更准、可交互），作为 Semantic Fusion 的主干。

### 三、OCR Layer（文字识别层）
- **职责**：文字识别。**不是语义理解**——只把图像区域转成文字 span。
- **定义**：
  - 输入：截图区域（bitmap / 裁剪框）
  - 输出：`OcrSpan[]`（text / bbox / confidence / language）
  - 缓存：同一区域（按 screenId + bbox hash）TTL 内复用
  - 失败策略：低置信度/空结果 → 标记 `low_confidence`，不伪造；降级为 UIA 文本（若 UIA 可用）

### 四、Vision Understanding（视觉理解层）
- **职责**：真正视觉语义理解。例："屏幕上有登录表单""主按钮在右下""当前是错误弹窗""页面空白加载中"。
- **禁止**：直接控制鼠标 / 键盘 / 任何执行器。只产出 `VisionFact`（带 bbox + confidence + 类别）。
- **与 UIA 关系**：UIA 给"可交互结构"，Vision 补"像素级语义"（图标含义、弹窗类型、布局判断）。二者在 Semantic Layer 融合。

### 五、Semantic Fusion Layer（语义融合层）
- **职责**：把 UIA + OCR + Vision 三路融合为**统一 Perception Model**。
- **融合规则**：以 UIA 树为主干；OCR 文本补到对应 element 的 `text`；Vision Fact 挂到最匹配的 element / region（IOU 匹配）。冲突时：UIA > Vision > OCR（可交互性优先），并保留各自 `confidence` 供上层裁决。
- **产出**：`PerceptionModel { screenId, monitors[], focusedElement, uiTree, ocrSpans[], visionFacts[], mergedText[], lastUpdated, ttl }`。

### 六、Perception World Model — PerceptionState（感知世界模型）
- **职责**：统一描述"用户当前看到的世界"，位于 World Model **之前**（语义上游）。
- **两层含义（必须区分，避免与冻结体系冲突）**：
  - **后端 PerceptionState**：Perception Runtime 持有的实时上游模型（生产者态），是 PERCEPTION_* 事件的**来源**。
  - **前端 perception-state.js**：纯下游投影（与 `ComputerState` 平级），订阅 `AppState.*` 重建感知视图，**只读、不 emit**。
- **不是 AppState、不是 ComputerState**：它是 World Model 的"更上游输入"；经事件流入 AppState 后，成为 `state.perception` 子树（World Model 富化的一部分）。

### 七、Perception Event（感知事件）
- 见 §6 事件设计（DOMAIN / SYSTEM 分类与命名）。

### 八、Runtime（运行时）
- 见 §7 Runtime 设计（必须接入已有 Runtime，禁第二套）。

### 九、Agent 集成
- 见 §8 Agent 集成（消费 Perception，Vision 禁直调 Executor）。

### 十、Verification 设计
- 见 §9 Verification 设计（复用 Perception，非重复 World Model）。

---

## 4. 生命周期

**Perception Runtime 后台生产者循环（持续运行，非按需编排）**：

```
[启动] Perception Runtime 随后端启动（与 World Model 生产者同级，门控 FEATURE_PERCEPTION）
   │
   ▼
[采集] Screen Capture Layer 按 TTL/焦点变更触发 → 原始帧
   │
   ▼
[理解] UIA 树 →（并行）OCR spans + Vision facts
   │
   ▼
[融合] Semantic Fusion → 更新后端 PerceptionState（实时上游模型）
   │
   ▼
[发布] publish_domain(PERCEPTION_SYNC / PERCEPTION_UI_UPDATED / …)  → AppState
   │        └─ 若发现值得主动告知用户的事实 → publish_system(perception_alert)（类 scene）
   │
   ▼
[投影] AppState.state.perception → perception-state.js（前端只读投影）
   │
   ▼
[消费] World Model 富化 → Agent 规划读取；Verification 复用作观察源
   │
   └─（回到采集，受 TTL / 焦点事件 / 节流控制，禁止自激循环）
```

**与领域生命周期的关系**：Perception 事件**不创建 Goal / Task / Agent**。它是 World Model 的观测来源，与 `COMPUTER_WORLD_SYNC` / `WINDOW_OPENED` 同性质——只写"世界状态"，不写"编排状态"。

---

## 5. 数据流

**正向（观察流）**：

```
Screen
  → ScreenCapture.capture(windowId|region|monitor) → Frame
  → UIALayer.tree(frame) → UITree
  → OCRLayer.recognize(frame, regions) → OcrSpans   （并行）
  → VisionLayer.understand(frame) → VisionFacts       （并行）
  → SemanticFusion.merge(uiTree, ocrSpans, visionFacts) → PerceptionModel
  → PerceptionState(backend).update(PerceptionModel)
  → publish_domain(PERCEPTION_SYNC, {perception: <model>})
  → AppState.applyEvent → state.perception 子树（reducer）
  → perception-state.js 投影 → UI / Agent 读取
```

**反向（验证流，复用而非重复）**：

```
Executor 执行动作（如 open_application）
  → VerificationLayer.verify(action, result)
  → RealObserver 升级：调用 PerceptionRuntime.observe()（只读快照）
  → 返回 PerceptionModel（UIA+OCR+Vision）
  → 按能力 _verify_* 比对 UI Fact（如 "error dialog 未出现" / "目标窗口已聚焦"）
  → publish_domain(COMPUTER_ACTION_VERIFIED | UNVERIFIED)   （沿用 Phase 7 事件）
```

**关键纪律**：Perception 数据流是**单向**的（Screen → PerceptionState → 事件 → AppState → 投影）。不存在 Perception → Executor 的反向控制边。

---

## 6. 事件设计

> 设计定义，未实现。落地时须同步追加到 `eventbus.DOMAIN_EVENT_NAMES` 与 `zz-events.js EVENTS`（单一来源纪律，readiness §5），并保持 `publish_domain` 校验。

### DOMAIN EVENT（进入 AppState，成为 World Model 富化事实）—— 新增 5 个

| 事件名 | 触发 | payload 关键字段 | 类比 |
|--------|------|------------------|------|
| `PERCEPTION_SYNC` | 周期性/变更时批量推送感知世界模型 | `perception: {screenId, monitors, focusedElement, uiTree, ocrSpans, visionFacts, mergedText, lastUpdated, ttl}` | `COMPUTER_WORLD_SYNC` |
| `PERCEPTION_UI_UPDATED` | UIA 树增量（元素增删/role/state 变） | `elementId, windowId, role, state, parentId, bbox` | `WINDOW_OPENED/CLOSED` |
| `PERCEPTION_OCR_UPDATED` | OCR 文本增量 | `spanId, text, bbox, confidence, language` | （新类别） |
| `PERCEPTION_VISION_FACT` | 离散视觉事实出现/消失 | `factId, category(login_screen/error_dialog/captcha/empty_state/…), bbox, confidence` | （新类别） |
| `PERCEPTION_FOCUS_CHANGED` | UIA accessibility focus 变化 | `elementId, windowId, role, name` | `WINDOW_FOCUSED` |

- 数量影响：DOMAIN_EVENT_NAMES 64 → **69**；`zz-events.js EVENTS` 同步 64 → 69。
- 单一来源：两端逐字一致，未知名由 `publish_domain` 拒绝（与现有纪律完全一致）。

### SYSTEM EVENT（主动推送/telemetry，独立 SSE 监听器消费，不进 AppState）—— 新增 2 个

| 事件名 | 触发 | 消费方 | 类比 |
|--------|------|--------|------|
| `perception_alert` | 感知到值得主动告知用户的状态（错误弹窗/登录界面达成/验证码） | `glance-card.js` / `app.js`（同 `scene`/`proactive`） | `scene` |
| `perception_health` | 引擎健康/采集帧率/缓存命中/模型延迟 telemetry | HUD/状态（`agent_state`） | `agent_state` |

- 数量影响：SYSTEM_EVENT_NAMES 6 → **8**；`zz-events.js SYSTEM_EVENTS` 同步 6 → 8。
- 信封：扁平 `{xiao6_event, ...fields}`，经 `publish_system` 校验（与现有 SYSTEM 纪律一致）。

**纪律重申**：Perception **不发布任何 COMPUTER_ACTION_*** 或 GOAL/AGENT/TASK 事件——它只观察。任何"用户看到错误弹窗→小6去点掉"的动作，都由 `perception_alert`（SYSTEM）→ 用户/Intent Gateway → Goal → 冻结链完成，Perception 自身不跨过动作边界。

---

## 7. Runtime 设计

**铁律：禁止新增第二套 Runtime。Perception Runtime 必须接入已有 Runtime（EventBus 脊柱）。**

- **定位**：Perception Runtime 是**后台生产者**（与 Phase 7 World Model 生产者同级），不是编排 Runtime。它**不创建 Goal/Task/Agent**，不调用 `PermissionGuard`/`computer_executor`（除复用为观察源的 `observe()` 只读调用）。
- **接入方式**：
  - 后端新增 `perception_runtime.py`（设计命名），持有 `PerceptionState` 实时上游模型，运行采集→理解→融合→发布的后台循环（可取消、可节流、可经 config 关闭）。
  - 它**只经 `publish_domain` / `publish_system` 向外通信**，与现有所有模块共用 `eventbus.bus`。无独立 topic 体系，无第二 SSE 通道。
  - 前端新增 `perception-state.js`（与 `computer-state.js` 平级）：`AppState.subscribe('*', …)` → 重建 `state.perception` 投影；只暴露 `getPerception() / getFocusedElement() / getVisionFacts()` / `onPerceptionChange()`；**无写入口、无 emit**。
- **AppState 扩展（冻结纪律内）**：`state` 新增 `perception` 子树（类比 `state.computer`），由 `PERCEPTION_*` reducer 写入；`state.computer` 可选增加一个 `perceptionRef` 指针关联窗口与其感知。World Model 投影（`ComputerState`）可新增 `getPerceptionFor(windowId)` 便捷读取——仍只读。
- **节流与自激防护**：采集频率受 TTL + 焦点事件驱动；**排除小6自身窗口**（避免观察自己的 UI）；`perception_alert` 有去重/冷却，杜绝观察→推送→再观察的振荡循环。
- **与 Galaxy / Overlay 的关系**：本 Phase **不改 Galaxy 语义、不改 Overlay 映射**。Perception 的事实经 World Model 暴露；若未来要在银河/Overlay 展现"当前屏幕"节点，属后续独立提案，不在 Phase 8 MVP 范围。

---

## 8. Agent 集成

**纪律：Agent 只经 World Model / PerceptionState 投影消费 Perception；Vision 绝不直调 Executor。**

- **读取路径**（保持冻结链不变）：
  ```
  AgentRuntime._execute_task → _resolve_dispatch（沿用 Phase 7）
    → 规划时读取 World Model（已被 Perception 富化）：
        ComputerState.getPerceptionFor(windowId) / perception-state.js.getPerception()
    → 形成 Task + target（如按钮坐标来自 Vision bbox）
    → 若 target 是已注册 Capability → guard.plan → guard.run → PolicyEngine → Executor
  ```
  Agent **不调用** `PerceptionRuntime.observe()` 触发采集；它只读已发布的感知投影（与读 `ComputerState` 同方式）。
- **Vision 发现按钮 → 点击按钮 的正确路径**：
  - Vision 产出 `VisionFact{category:button, bbox, confidence}`（仅事实）。
  - Agent 将其转为 Task：`capability=click_at`（若注册）/ 或 `focus_window`+坐标；target = bbox 中心坐标。
  - 该 Task 经 `_resolve_dispatch → is_known → _execute_computer_task → guard.run`；MEDIUM/需确认能力仍走 `request_approval` 模态（Phase 7 闸门不变）。
  - **Vision 本身没有任何执行权限**，不能直接发 `COMPUTER_ACTION_*` 或调 `executor`。
- **主动感知（proactive）**：当 Perception 经 `perception_alert`（SYSTEM）告知"检测到登录界面/错误弹窗"，由既有 proactive 流程 / Intent Gateway 决定是否成立 Goal——与"小6自己看屏幕后决定行动"的语义完全一致，且动作仍走冻结链。

---

## 9. Verification 设计

**目标：Verification 复用 Perception 作为观察源，而非重复 World Model 的观测逻辑。**

- **现状（Phase 7 冻结）**：`verification.RealObserver` 用 `RealComputerExecutor._op_list_process` + ctypes 前台窗口做观测；仅能验证"进程在跑/窗口聚焦"。无法验证"错误弹窗是否消失""登录是否完成"这类**屏幕语义**。
- **升级方案（不新增 Verification 事件合约）**：
  - `RealObserver.__call__()` 改为委托 `PerceptionRuntime.observe()`（**只读快照**，返回 `PerceptionModel`）。
  - 各能力 `_verify_*` 规则扩展为比对 UI Fact：
    - `open_application`：验证 `visionFacts` 中目标应用窗口可见 / UIA 树含其主窗口。
    - `focus_window`：验证 `PERCEPTION_FOCUS_CHANGED` 后的 `focusedElement.windowId == target`。
    - 新增可选 `_verify_click_at`：验证点击后 `visionFacts` 中目标状态变化（如 toggle 切换 / 弹窗关闭）。
  - 仍返回 `(verified, detail)`，仍经 `publish_domain(COMPUTER_ACTION_VERIFIED | UNVERIFIED)`——**完全复用 Phase 7 事件合约**，不漂移。
- **纪律**：Verification 复用 Perception 意味着"执行后复核"与"持续感知"共享同一观察能力，避免 Phase 7 `RealObserver` 与 Phase 8 Perception 各写一套屏幕读取（重复 = 漂移风险）。Perception 是观察源，Verification 是裁决方，职责不混。

---

## 10. 风险分析（≥10 项）

| # | 风险 | 表现 | 缓解（设计层） |
|---|------|------|----------------|
| 1 | **OCR 误判** | 文字识别错 → World Model 文本错 → Agent 基于错文本决策 | 置信度阈值；UIA 文本优先于 OCR；低置信标 `low_confidence` 不伪造；关键字段强制二次确认 |
| 2 | **Vision 误判** | 视觉幻觉 → 误报"错误弹窗"/按钮位置错 | Vision 输出带 `confidence`；低置信→视为 unknown，**绝不自动动作**；仅作建议，动作仍走 confirm 闸门 |
| 3 | **缓存陈旧** | TTL 过长 → 基于过期屏幕行动 | 每屏区域带 `ttl` + `screenId` 版本；焦点/窗口变更即失效；Agent 行动前校验 `lastUpdated` 新鲜度 |
| 4 | **延迟** | 采集→理解→发布滞后于真实屏幕 | 异步流水线；`lastUpdated` 时间戳随投影暴露；Agent 读取时检查新鲜度，过旧则等待/请求刷新 |
| 5 | **多显示器** | 坐标映射错（主屏/扩展屏） | 显示器感知采集；坐标按 monitor 归一化；UIA `Window Mapping` 关联 windowId 而非裸坐标 |
| 6 | **权限缺失** | 屏幕采集/UIA 被 OS 拒绝 → 静默空白 | 优雅降级：仅有结构化 World Model（Phase 7）仍可工作；发 `perception_health` 暴露权限状态；不阻塞主链路 |
| 7 | **安全/隐私** | 屏幕含密钥/PII；Vision 输入 LLM 泄露 | 沿用"内存不落盘"；原始帧禁日志；送 Vision LLM 前做 PII 脱敏（输入框内容/密码框屏蔽）；审计不含像素 |
| 8 | **性能** | OCR+Vision 重 → 抢占 CPU/GPU、拖慢系统 | 频率限制 + 低优先级线程；可配置关闭；懒加载（仅当 Agent 需要/焦点变更时）；多屏按需不全量 |
| 9 | **循环观察** | 感知观察自身动作 → 无限再感知/振荡 | 排除小6自身窗口；`perception_alert` 去重冷却；**Perception 永不自动动作**（无自激回路） |
| 10 | **误操作** | 误感知元素 → Agent 点错目标 | Perception 永不自动点击；坐标在**执行时**由 Executor 重新校验；目标经 confirm 闸门；Vision 仅提供建议 |
| 11 | **模型版本漂移** | Vision 模型升级改变语义/类别 | 固定模型版本号；回归测试覆盖 `visionFacts` 类别；类别变更须走事件合约评审 |
| 12 | **隐私合规** | 持续屏幕监控的法律/伦理风险 | 显式 opt-in；常驻状态指示；用户可暂停；`perception_health` 暴露开关状态 |

---

## 11. Implementation Roadmap（仅规划，不实现）

> 顺序遵循"自底向上、每层可独立验证"，且每层都须先通过事件合约评审 + 不破坏冻结链。

- **Order 1 — Screen Capture Foundation**
  原始采集：窗口/区域/全屏/多显示器；缓存/TTL；内存不落盘（沿用 `capture_screen` 纪律）。**不理解的帧**。
- **Order 2 — UI Automation Foundation**
  UIA：Element / Role / Tree / Accessibility / Focus / Window Mapping（windowId 关联）。结构化 UI 树产出。
- **Order 3 — OCR Runtime**
  文字识别：输入/输出/cache/TTL/失败策略；低置信降级 UIA。
- **Order 4 — Vision Runtime**
  视觉语义理解：只读、`VisionFact` 产出、带 confidence、绝不控制。
- **Order 5 — Semantic Fusion**
  UIA + OCR + Vision → 统一 `PerceptionModel`（冲突裁决 UIA>Vision>OCR）。
- **Order 6 — Perception Runtime**
  生产者循环 + `PerceptionState`（后端实时模型）+ `PERCEPTION_*` 事件发射（接入 EventBus）；前端 `perception-state.js` 投影 + `state.perception` reducer。
- **Order 7 — Agent Integration**
  Agent 经富化 World Model 消费 Perception；Vision 发现→Task→冻结链动作；`perception_alert`→Intent Gateway 主动建 Goal。
- **Order 8 — Verification Upgrade**
  `RealObserver` 复用 Perception（`observe()` 只读快照）；按能力 `_verify_*` 比对 UI Fact；沿用 `COMPUTER_ACTION_VERIFIED/UNVERIFIED` 事件。

**每 Order 前置闸门**：事件合约评审（DOMAIN/SYSTEM 单一来源对齐）→ 不破坏 Phase 6/7 冻结链 → 重跑 Phase 6+7 全量测试绿 → 方可进入下一 Order。

---

## 12. 冻结建议

**建议：将本规范冻结为 Phase 8 v1.0（设计基线），Implementation 须待批准后才可进入 Order 1。**

冻结期内必须遵守的接入契约（落地 Order 1 之前须先就绪）：

1. **事件单一来源**：新增 5 个 DOMAIN（`PERCEPTION_SYNC / PERCEPTION_UI_UPDATED / PERCEPTION_OCR_UPDATED / PERCEPTION_VISION_FACT / PERCEPTION_FOCUS_CHANGED`）+ 2 个 SYSTEM（`perception_alert / perception_health`），须**同时**写入 `eventbus.DOMAIN_EVENT_NAMES`（64→69）与 `zz-events.js EVENTS`（64→69）/ `SYSTEM_EVENTS`（6→8），并保持 `publish_domain`/`publish_system` 校验。禁止第二事件系统。
2. **唯一写入口**：前端 `AppState` 新增 `state.perception` 子树 + `PERCEPTION_*` reducer；`applyEvent` 仍为唯一写入口，不新增旁路。
3. **纯投影**：新增 `perception-state.js` 与 `computer-state.js` 平级，只读、不 emit、数据单向派生自 `AppState`。
4. **单 Runtime**：Perception Runtime 仅为 EventBus 的生产者，不创建 Goal/Task/Agent，不成为第二编排 Runtime。
5. **动作纪律不变**：Vision 绝不调用 Executor；任何动作经 `Task → PermissionGuard → Executor`（Phase 7 冻结链 + Policy Engine 闸门）。
6. **Verification 复用**：`RealObserver` 升级为复用 Perception 观察源，不重复 World Model 观测逻辑；不新增 Verification 事件合约。
7. **Galaxy / Overlay 语义零改动**：本 Phase 不引入新的银河节点类型或 Overlay 映射；感知展现留待后续独立提案。
8. **安全基线**：原始帧内存不落盘、禁日志；送 Vision LLM 前 PII 脱敏；感知可显式关闭。

**未批准前**：不得进入 Phase 8 Order 1，不得创建任何模块/事件/代码，不得修改 Phase 6/7 冻结文档与代码。

---

*生成方式：基于重新读取的真实冻结代码（eventbus / app-state / galaxy-state / overlay-runtime / policy_engine / intent_gateway / computer-state / capability_registry / permission_guard / computer_executor / verification / agent_runtime），非记忆推断。本文件为 Design Only 交付物。*
