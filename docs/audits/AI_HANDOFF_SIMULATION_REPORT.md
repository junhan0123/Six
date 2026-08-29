# Xiao6 Understanding Report（AI Handoff Simulation）

> 模拟场景：一个新的高级 AI Agent 首次进入项目，仅被允许读取以下 6 个文件：
> `README.md` · `PROJECT_STATUS.md` · `CURRENT_STATE.md` · `ARCHITECTURE_MAP.md` · `DEVELOPMENT_PROGRESS.md` · `AI_BOOTSTRAP.md`
> 目标：验证是否达到「30 分钟接管标准」。本文件即模拟 AI 输出的「理解报告」。

---

## 一、项目是什么（能说清定位）

Xiao6（小6）是一个**本地优先的 Personal AI Operating System**（本地个人 AI 操作系统），运行在 Windows 桌面（Electron 包装）。后端 `server.py` + 前端 `xiao6-ui/`（原生 JS/Three.js）。它像「贾维斯」一样：理解电脑状态、组织上下文、执行被授权的能力。大脑走 Agnes API，语音用 FunASR + edge-tts，世界态势接 GDELT/USGS/OpenSky/Open-Meteo（免费无 key）。当前版本 **v1.0**，已完成 Phase 6/7/8，处于**架构稳定期（Architecture Stabilization）**。

## 二、当前状态（能说清进度与阻塞）

- **已完成并冻结**：Phase 6（Unified Runtime：EventBus / AppState / Galaxy / Overlay / Intent）、Phase 7（Computer Operating Layer：World Model / Capability / Permission / Executor / Verification）、Phase 8（Computer Perception MVP：Capture / UIA / OCR / Vision / Fusion）。
- **测试**：Phase 6/7/8 共 **28** 测试文件，全量 **0 FAIL / 0 Regression**。
- **当前进行**：v1.1 文档治理 + AI 交接协议（已完成并落地）。
- **阻塞**：Phase 9 实现等待用户批准 Step 1（设计 `Cognitive Context Architecture v1.0`）。
- **已知风险**：历史记忆引用的「九级参考体系」规范文件（constitution/IA 等）磁盘上不存在，仅为意图，需未来补建。

## 三、核心架构（能说清数据与决策流）

- **通信**：唯一事件总线 `eventbus.py`（DOMAIN 71 / SYSTEM 8），前端 `zz-events.js` 逐字对齐；未登记事件名抛 `ValueError`。
- **状态**：唯一写入口 `AppState.applyEvent → reducers`；GalaxyState / OverlayRuntime / ComputerState / PerceptionState 只是**只读投影**，不回写。
- **决策**：唯一决策运行时 `AgentRuntime`（IDLE→PLANNING→EXECUTING→REFLECTING）；CaptureRuntime / PerceptionRuntime 是**观察生产者**，只发事件、绝不构造 Action。
- **执行链**：`Goal → Agent Runtime → Capability Registry → Permission Guard → Computer Action → Executor → Verification → World Model`，全程经 EventBus。
- **记忆**：唯一来源 `memory.py`（短期/工作/长期/项目/知识分层）。
- **权限**：唯一闸门 `PermissionGuard` + `PolicyEngine`，Executor 不得绕过。

## 四、禁止事项（红线，能逐条复述）

- ❌ 第二 Runtime / 第二 Memory / 第二 EventBus / 第二 Permission System
- ❌ 绕过 AppState 写状态、绕过 EventBus 发事件
- ❌ 直接调用 Executor（必经 Permission Guard）
- ❌ 修改 Galaxy 语义或银河本体视觉资产
- ❌ 复制已有模块；引入 LangChain / AnythingLLM 运行时
- ❌ Vision / Perception 越权控制电脑（Observation ONLY）

## 五、开发纪律（能复述八步流程）

`Audit → Analysis → Design → Approval → Implementation → Test → Report → Freeze`
先读真实代码（不凭记忆）→ 产出设计 → 等 Approval → 仅实现批准范围 → 跑全量测试（Phase 6/7/8 须 0 FAIL）→ 写报告 → 完成即 Freeze，等下一条指令。重大修改还须走 Freeze Rule（Decision→Design→Approval→...）。

## 六、下一步流程（知道接手后怎么动）

1. 若被授权进入 Phase 9：先完成 Step 1 设计 `Cognitive Context Architecture v1.0`，等批准后再按 Order 实现（Workspace Manager → Context Engine → Capability Catalog → Knowledge Workspace Interface → Reflection Loop）。
2. 任何修改前重读真实冻结代码，更新 CHANGELOG_AI + 决策/库存，跑 `docs/reference/PROJECT_DOCUMENT_AUDIT.py` 与全量测试。
3. 遇架构漂移风险主动告警，不静默绕过。

## 七、30 分钟接管标准评估

| 能力项 | 是否达标 | 依据 |
|--------|----------|------|
| 说清项目定位 | ✅ | README + PROJECT_STATUS + AI_BOOTSTRAP |
| 说清当前状态/阻塞 | ✅ | CURRENT_STATE + DEVELOPMENT_PROGRESS |
| 说清核心架构与数据流 | ✅ | ARCHITECTURE_MAP（逐模块职责/禁止/方向） |
| 复述全部红线 | ✅ | CURRENT_STATE + AI_BOOTSTRAP + ARCHITECTURE_MAP |
| 复述开发纪律 | ✅ | AI_BOOTSTRAP 八步 + PROJECT_STATUS |
| 知道下一步流程 | ✅ | PROJECT_STATUS 下一阶段 + CURRENT_STATE Next |
| 知道去哪查决策/审计 | ✅ | 三文件均指向 docs/decisions、docs/audits、DOCUMENT_INVENTORY |
| 知道不做什么（禁止项） | ✅ | 红线贯穿全部 6 文件 |

**结论：达到 30 分钟接管标准 ✅。** 新 AI 仅凭这 6 个文件即可安全接手维护，不会误触架构红线。补充深读（docs/decisions、ARCHITECTURE_DRIFT_CHECK、AI_ONBOARDING_TEST）可进一步缩短至「5 分钟」级置信。

---

> 本模拟严格只读 6 个允许文件；未读取任何业务代码或 docs/ 下其他文件。输出即「理解报告」，用于验证交接协议有效性。
