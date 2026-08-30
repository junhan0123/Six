# UI-R3D UI ↔ Runtime Matrix

**Date**: 2026-08-30

---

## 核心链路验证

| UI Component | API Endpoint | Runtime | E2E Status |
|--------------|--------------|---------|------------|
| Chat Input | POST /api/chat | REAL | ✅ PASS |
| Chat Response | SSE Stream | REAL | ✅ PASS |
| Goals List | GET /api/goals | REAL | ✅ PASS (50) |
| Tasks List | GET /api/tasks | REAL | ✅ PASS (50) |
| Memories | GET /api/memories | REAL | ✅ PASS (124) |
| Knowledge | GET /api/knowledge | REAL | ✅ PASS (329 docs) |
| Agent State | GET /api/agent/state | REAL | ✅ PASS |
| Health Check | GET /api/health | REAL | ✅ PASS |

---

## 导航映射

| UI Button | View | API/Data Source |
|-----------|------|-----------------|
| 对话 | home | chatList (state.timeline) |
| 项目 | projects | /api/goals |
| 任务 | tasks | /api/tasks |
| 知识 | knowledge | /api/knowledge |
| 记忆 | memory | /api/memories |
| 工具 | tools | /api/capabilities |
| 设置 | settings | /api/config |

---

## 交互验证

| Action | Handler | API/Effect | Result |
|--------|---------|------------|--------|
| Enter key | keydown → submitCmd → sendChat | POST /api/chat | ✅ |
| Send button | click → submitCmd → sendChat | POST /api/chat | ✅ |
| Mode toggle | click → state.toolModes.expert | payload.mode | ✅ |
| New chat | click → resetTimeline | localStorage clear | ✅ |
| Nav click | click → switchView | DOM display toggle | ✅ |
| Settings | click → switchView('settings') | renderSettingsPage | ✅ |
| Theme toggle | click → data-theme | CSS variables | ✅ |
| Command palette | Ctrl+K → openPalette | filter commands | ✅ |

---

## SSE Events

| Event | Source | UI Effect |
|-------|--------|-----------|
| tool_started | /api/stream | timeline node (tool) |
| tool_finished | /api/stream | timeline node update |
| agent_state | /api/stream | nowBar update |
| goal_events | /api/stream | goals refresh |
| task_events | /api/stream | tasks refresh |

---

## Error Handling

| Scenario | UI Behavior | Verified |
|----------|-------------|----------|
| API failure | Error toast + status 'failed' | ✅ |
| Empty data | "暂无..." placeholder | ✅ |
| Network error | "请求失败" message | ✅ |
| Timeout | Loading state (realistic) | ✅ |

---

## No Mock Data

| Component | Source | Status |
|-----------|--------|--------|
| Goals | Real API (50 items) | ✅ |
| Tasks | Real API (50 items) | ✅ |
| Memories | Real API (124 items) | ✅ |
| Knowledge | Real API (329 docs) | ✅ |
| Chat response | Real model (Agnes) | ✅ |

---

## Legacy Clean

| Search Term | Runtime References | Status |
|-------------|-------------------|--------|
| zz-space | 0 | ✅ |
| zhuangzhou | 0 | ✅ |
| ZhuangZhou | 0 (only in comments) | ✅ |
| 庄周 | 0 (only in comments) | ✅
| ZZ | 0 | ✅ |

---

## Performance

| Metric | Value | Status |
|--------|-------|--------|
| Initial load | <1s | ✅ |
| API responses | <500ms | ✅ |
| Chat response | <3s | ✅ |
| Console errors | 0 | ✅ |
| Failed requests | 0 | ✅ |

---

**Matrix Version**: 1.0
**Last Updated**: 2026-08-30
