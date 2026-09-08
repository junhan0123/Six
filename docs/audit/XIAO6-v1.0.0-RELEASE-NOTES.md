# Xiao6 v1.0.0 Release Notes

**版本**: 1.0.0  
**发布日期**: 2026-09-05  
**Commit**: f5080e5  
**Tag**: v1.0.0

---

## Release Summary

Xiao6 v1.0.0 是第一个正式 Release，核心 Agent Runtime 已验证通过。

---

## Architecture

### Core Runtime
- **AgentRuntime**: 唯一执行入口
- **ai_core.execution.run()**: 唯一 Tool Execution Core
- **Policy Engine**: 强制执行闸门
- **EventBus**: 模块通信总线

### Execution Chain (Verified)
```
Intent → Planner → AgentRuntime._run_fc_loop()
    → ai_core.execution.run() → Policy Engine → Tool → Observation → Response
```

### Prohibited (By Design)
- No second Runtime
- No second Execution Entry
- No ExecutionBridge
- No Planner direct Tool call
- No Policy bypass

---

## Testing

```
219 tests
219 passed
0 failed
0 errors
1 skipped (pre-existing mcp_host import error)
```

---

## Agent E2E

| Task | Result |
|------|--------|
| 12 × 34 | 408 ✅ |
| Tool: calculator | via ai_core.execution.run → Policy → calculator ✅ |
| Decision: auto | Policy engine approved ✅ |

---

## Runtime

| Endpoint | Status |
|----------|--------|
| /api/version | 1.0.0 ✅ |
| /api/ready | ready=true |
| /api/health | alive, 63 tools ✅ |
| /api/chat | Working ✅ |

---

## Known Scope Boundaries

| Component | Status | Reason |
|-----------|--------|--------|
| TTS (GPT-SoVITS) | CONDITIONAL | External service not deployed |
| Browser E2E | BLOCKED | Environment limitation |
| Live External Ingestion | BLOCKED | v1.0.0 scope boundary |

---

## Features

### Agent Core
- Intent Gateway
- Planner (intent → plan)
- AgentRuntime with FC loop
- Tool Registry (63 tools)
- Policy Engine (allow/deny/auto)
- Observation Service

### UI
- Chat Interface
- Work Center (trace/recent)
- Knowledge/Notes Management
- Global Foresight Dashboard (GFE)

### GFE (Global Foresight Engine)
- Data Sources (5 sources)
- World State Engine
- Event Intelligence
- Causal Graph
- Analyst Council (8 analysts)
- Scenario Engine
- Forecast Engine
- Early Warning
- Calibration

---

## Repository Integrity

- Zero historical project references in active code
- Single version: 1.0.0
- Clean architecture: no second execution entry
- All reports preserved as evidence

---

## Release Notes Location

- G:/xiao6/XIAO6-v1.0.0-RELEASE-NOTES.md
- F:/桌面/XIAO6-v1.0.0-RELEASE-NOTES.md