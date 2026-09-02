# UI-R3C - UI-API Mapping Matrix

**Date**: 2026-08-30

---

## 导航映射

| UI Element | API Endpoint | Runtime | E2E Status |
|------------|--------------|---------|------------|
| 对话 | /api/chat/sse | REAL | ✅ PASS |
| 项目 | /api/goals | REAL | ✅ PASS |
| 任务 | /api/tasks | REAL | ✅ PASS |
| 知识 | /api/knowledge | PARTIAL | ⚠️ READ |
| 记忆 | /api/memories | REAL | ✅ PASS |
| 工具 | /api/tools | REAL | ✅ PASS |
| 设置 | /api/config | REAL | ✅ PASS |

---

## 首页功能

| UI Element | API/Function | Runtime | E2E Status |
|------------|--------------|---------|------------|
| Composer输入 | /api/chat POST | REAL | ✅ PASS |
| Enter发送 | timeline.sendChat() | REAL | ✅ PASS |
| Shift+Enter换行 | textarea behavior | REAL | ✅ PASS |
| Smart模式 | payload.mode=smart | REAL | ✅ PASS |
| Expert模式 | payload.mode=expert | REAL | ✅ PARTIAL |
| 语音按钮 | /api/voice/transcribe | PARTIAL | ⚠️ DEPENDENCY |
| 附件按钮 | file input | REAL | ✅ PASS |

---

## Timeline功能

| UI Element | API/Event | Runtime | E2E Status |
|------------|-----------|---------|------------|
| tool_start | EventBus | REAL | ✅ PASS |
| tool_end | EventBus | REAL | ✅ PASS |
| execution状态 | agent/state | REAL | ✅ PASS |
| Inspector Drawer | 本地渲染 | REAL | ✅ PASS |

---

## 项目管理

| UI Element | API | Runtime | E2E Status |
|------------|-----|---------|------------|
| 项目列表 | /api/goals | REAL | ✅ PASS |
| 切换项目 | currentGoalId | REAL | ✅ PASS |
| 项目上下文注入 | payload.goal_id | REAL | ✅ PASS |

---

## 会话管理

| UI Element | API | Runtime | E2E Status |
|------------|-----|---------|------------|
| 历史列表 | /api/chat/history | REAL | ✅ PASS |
| Session Resume | /api/session/resume | REAL | ⚠️ NEEDS DATA |
| 新对话 | localStorage.clear() | REAL | ✅ PASS |

---

## 设置页面

| UI Element | API | Runtime | E2E Status |
|------------|-----|---------|------------|
| 常规设置 | /api/config GET | REAL | ✅ PASS |
| 模型选择 | config.LLM_PROVIDER | REAL | ✅ READ |
| 主题切换 | localStorage | REAL | ✅ PASS |
| 数据导出 | /api/data/export | REAL | ✅ PASS |

---

## 命令面板

| UI Element | Function | Runtime | E2E Status |
|------------|----------|---------|------------|
| Ctrl+K打开 | palette.openPalette() | REAL | ✅ PASS |
| 命令列表 | command_palette.py | REAL | ✅ PASS |
| 执行命令 | 对应API | REAL | ✅ PASS |

---

## 状态总结

| 类别 | REAL | PARTIAL | UNAVAILABLE |
|------|------|---------|-------------|
| 核心对话 | 5 | 1 | 0 |
| 项目管理 | 3 | 0 | 0 |
| 会话管理 | 2 | 1 | 0 |
| 设置 | 4 | 0 | 0 |
| 工具 | 2 | 0 | 0 |

**总计**: 16 REAL, 3 PARTIAL, 0 UNAVAILABLE
