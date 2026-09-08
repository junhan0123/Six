# Xiao6 v1.0.0 — PHASE 132 Proposal Validation & Task Bridge Report

**日期**: 2026-09-04  
**版本**: v1.0.0  
**状态**: 核心完成，外部服务待配置

---

## 1. 实施内容

### 1.1 新增文件

| 文件 | 行数 | 说明 |
|------|------|------|
| `xiao6-ui/proposal_validator.py` | 200 | 提案验证器 |
| `xiao6-ui/proposal_task_adapter.py` | 217 | 提案→任务适配器 |
| `xiao6-ui/email_sender.py` | 50 | 邮件通知工具 |
| `xiao6-ui/test_qq_email.py` | 70 | QQ邮箱测试脚本 |

### 1.2 修改文件

| 文件 | 变更 |
|------|------|
| `xiao6-ui/server.py` | +20 行，新增 `/api/proposals/{id}/create-task` 端点 |

---

## 2. 架构实现

### 2.1 Proposal Validator

```
输入: TaskProposal
检查:
  1. 字段完整性 (title, description, steps, risk)
  2. 类型验证 (steps: list, risk: low/medium/high)
  3. Policy Engine 只读检查
  4. Risk Gate:
     - low → 允许创建
     - medium → 需要用户确认
     - high → 需要二次确认

输出: ValidationResult
```

### 2.2 Proposal Task Adapter

```
流程:
  Proposal (approved)
      ↓
  Validate
      ↓
  Create TaskSpec
      ↓
  Insert tasks (status=pending)
      ↓
  Return Task ID

约束:
  - 只创建任务，不执行
  - 不触发 Runtime
  - 不修改 ai_core.execution.run
```

---

## 3. 测试结果

### 3.1 Validator Tests (4/4 PASS)

```
Test 1: Valid proposal
  PASS: valid=True, risk=medium, approval=True

Test 2: Missing required fields
  PASS: valid=False, errors=4

Test 3: High risk proposal
  PASS: valid=True, risk=high, needs_second_confirmation=True

Test 4: Invalid steps format
  PASS: valid=False, errors=["'steps' must be a list"]
```

### 3.2 Adapter Tests (3/3 PASS)

```
Test 1: Create task from valid proposal
  PASS: task_id=252, status=pending

Test 2: Reject invalid proposal
  PASS: rejected invalid proposal

Test 3: Verify task creation
  PASS: task created id=252, status=pending
```

---

## 4. API 端点

### 4.1 创建任务
```http
POST /api/proposals/{id}/create-task

要求:
  - 提案存在
  - 状态为 approved
  - 验证通过

响应:
  {"ok": true, "task_id": "123"}
```

### 4.2 现有端点 (Phase 131)
```http
GET  /api/proposals
POST /api/proposals/{id}/approve
POST /api/proposals/{id}/reject
```

---

## 5. 数据库 Schema

### 5.1 tasks 表
```sql
id INTEGER PRIMARY KEY
title TEXT
step TEXT
total_steps INTEGER DEFAULT 0
status TEXT DEFAULT 'open'
created TEXT
updated TEXT
steps TEXT
current_step INTEGER DEFAULT 0
note TEXT
goal_id INTEGER
session_id TEXT
```

### 5.2 task_proposals 表
```sql
id TEXT PRIMARY KEY
suggestion_id TEXT
type TEXT NOT NULL
title TEXT NOT NULL
description TEXT
steps TEXT
estimated_cost INTEGER DEFAULT 5
risk TEXT DEFAULT 'low'
status TEXT DEFAULT 'pending'
created TEXT
approved_at TEXT
rejected_at TEXT
task_id INTEGER
```

---

## 6. 外部服务配置

### 6.1 QQ 邮箱
**状态**: ❌ 连接失败（网络阻断）

配置:
- SMTP: smtp.qq.com
- 端口: 465 (SSL) / 587 (TLS)
- 邮箱: 1903999022@qq.com
- 授权码: vqmlyrdnrycibiab

错误: Connection unexpectedly closed

### 6.2 QQ Bot 网关
**状态**: 需手动配置
- app_id: 1903999022
- token: 从 .env 加载

---

## 7. 约束满足

| 约束 | 状态 |
|------|------|
| 不修改 ai_core.execution.run | ✓ |
| 不修改 planner | ✓ |
| 不修改 policy_engine | ✓ |
| 不自动执行任务 | ✓ |
| Human in the Loop | ✓ |
| 版本 v1.0.0 | ✓ |

---

## 8. 服务状态

| 服务 | 状态 |
|------|------|
| 后端服务器 | 待启动（端口 8000） |
| QQ Bot 网关 | 待配置 |
| 邮件服务 | 网络问题 |

---

## 9. Git Diff Summary

```
proposal_validator.py   | 200 lines (new)
proposal_task_adapter.py | 217 lines (new)
email_sender.py         | 50 lines (new)
test_qq_email.py        | 70 lines (new)
server.py               | +20 lines
```

---

**报告路径**: G:/xiao6/XIAO6-v1.0.0-PHASE-132-PROPOSAL-TASK-BRIDGE-REPORT.md  
**桌面副本**: F:/桌面/XIAO6-v1.0.0-PHASE-132-PROPOSAL-TASK-BRIDGE-REPORT.md

---

**完成时间**: 2026-09-04  
**状态**: 核心功能完成，外部服务待网络配置