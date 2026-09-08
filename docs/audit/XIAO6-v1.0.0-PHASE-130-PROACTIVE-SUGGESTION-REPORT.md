# Xiao6 v1.0.0 — PHASE 130 Proactive Suggestion Layer Report

**日期**: 2026-09-04
**版本**: v1.0.0
**状态**: 已完成

---

## 1. 架构设计

### 1.1 数据流

```
Observation (来自 ObservationService)
    ↓
SuggestionGenerator (规则匹配)
    ↓
SuggestionStore (SQLite 持久化)
    ↓
/api/suggestions (前端轮询)
    ↓
用户查看建议
```

### 1.2 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| Suggestion | suggestion_service.py | 数据模型 |
| SuggestionGenerator | suggestion_service.py | 规则引擎 |
| SuggestionStore | suggestion_service.py | 持久化层 |
| SuggestionService | suggestion_service.py | 协调层 |
| /api/suggestions | server.py | REST API |

---

## 2. Suggestion Model

### 2.1 数据结构

```python
@dataclass
class Suggestion:
    id: str                    # 唯一标识
    observation_id: str        # 关联 Observation
    type: str                  # TASK_STALE / TASK_FAILED / GOAL_STUCK
    title: str                 # 建议标题
    description: str           # 详细描述
    priority: int              # 优先级 (1=高, 5=中, 10=低)
    status: str                # pending / accepted / rejected / expired
    created_at: float          # 创建时间
```

### 2.2 状态机

```
pending → accepted
      ↓
   rejected
      ↓
   expired (超时自动)
```

---

## 3. 规则引擎

### 3.1 规则映射表

| health_status | risk_level | type | title | priority |
|---------------|------------|------|-------|----------|
| STALE | - | TASK_STALE | 任务可能停滞 | MEDIUM (5) |
| WARNING | - | TASK_STALE | 任务进度可能缓慢 | LOW (10) |
| FAILED | - | TASK_FAILED | 任务执行失败 | HIGH (1) |
| - | high | TASK_FAILED | 高风险任务 | HIGH (1) |
| - | medium | TASK_STALE | 任务需要关注 | MEDIUM (5) |

### 3.2 匹配逻辑

1. 遍历规则列表（按顺序）
2. 检查 health 和 risk 条件
3. 返回第一个匹配的规则
4. 生成 Suggestion 对象

---

## 4. 数据库表

### 4.1 suggestions 表

```sql
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id TEXT UNIQUE,    -- 关联 Observation ID
    type TEXT NOT NULL,            -- 建议类型
    title TEXT NOT NULL,           -- 标题
    description TEXT,              -- 描述
    priority INTEGER DEFAULT 5,    -- 优先级
    status TEXT DEFAULT 'pending', -- 状态
    created TEXT,                  -- 创建时间
    accepted_at TEXT,              -- 接受时间
    rejected_at TEXT               -- 拒绝时间
);
```

### 4.2 向后兼容

`_migrate_suggestions()` 函数补齐缺失列，确保存量数据库正常升级。

---

## 5. API 端点

### 5.1 GET /api/suggestions

**请求**:
```http
GET /api/suggestions?limit=20
```

**响应**:
```json
{
  "suggestions": [
    {
      "id": 1,
      "observation_id": "obs_001",
      "type": "TASK_STALE",
      "title": "任务可能停滞",
      "description": "任务超过72小时无进度更新",
      "priority": 5,
      "status": "pending",
      "created_at": 1725424500.0
    }
  ],
  "count": 1
}
```

**排序**: 按 priority ASC（数字越小优先级越高），created DESC（最新优先）

---

## 6. 去重控制

### 6.1 策略

- 同 observation_id 只允许一个 active（pending）suggestion
- INSERT OR IGNORE 防止重复写入
- 服务启动时清理过期 suggestion

### 6.2 实现

```python
# SuggestionStore.save()
conn.execute("""
    INSERT OR IGNORE INTO suggestions
    (observation_id, ...)
    VALUES (?, ...)
""")

# SuggestionService.process_observation()
existing = self._db.get_pending()
for es in existing:
    if es["observation_id"] == obs_id:
        return None  # 已存在，跳过
```

---

## 7. 测试证据

### 7.1 测试用例

| Test | 场景 | 预期 | 结果 |
|------|------|------|------|
| 1 | STALE task | TASK_STALE suggestion | PASS |
| 2 | FAILED task | TASK_FAILED suggestion | PASS |
| 3 | GOOD task | no suggestion | PASS |
| 4 | 重复观察 | 只生成一条 | PASS |
| 5 | 服务集成 | 获取建议正常 | PASS |

### 7.2 测试命令

```bash
cd G:/xiao6/xiao6-ui && python suggestion_service.py
```

### 7.3 测试结果

```
=== PHASE 130 Suggestion Layer Tests ===

Test 1: STALE task generates suggestion
  PASS: type=TASK_STALE, priority=5

Test 2: FAILED task generates suggestion
  PASS: type=TASK_FAILED, priority=1

Test 3: GOOD task no suggestion
  PASS: no suggestion generated

Test 4: Duplicate detection
  PASS: duplicate correctly detected (count=1)

Test 5: Service integration
  PASS: service works, pending count=1

=== All Tests Complete ===
```

---

## 8. 约束满足

| 约束 | 状态 |
|------|------|
| 不修改 ai_core.execution.run | ✓ 未触碰 |
| 不修改 planner | ✓ 未触碰 |
| 不修改 policy_engine | ✓ 未触碰 |
| 不修改 tool executor | ✓ 未触碰 |
| 只读建议，不自动执行 | ✓ 仅生成建议 |
| SQLite 持久化 | ✓ suggestions 表 |
| Human in the Loop | ✓ 用户接受/拒绝 |

---

## 9. 修改文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `xiao6-ui/suggestion_service.py` | 新增 | 建议层核心实现（465行） |
| `xiao6-ui/db.py` | 修改 | 添加 suggestions 表 |
| `xiao6-ui/server.py` | 修改 | 添加 /api/suggestions 端点 |

**Git Diff Summary**:
```
xiao6-ui/db.py         |  +18 lines
xiao6-ui/server.py     |  +13 lines
xiao6-ui/suggestion_service.py |  +465 lines (new)
```

---

## 10. 后续扩展

### 10.1 可扩展点

1. **更多规则**: 在 RULES 列表中添加新规则
2. **优先级调整**: 修改 PRIORITY_* 常量
3. **前端集成**: Work Center 展示建议列表
4. **用户反馈**: 接受/拒绝建议后触发后续流程

### 10.2 与 PHASE 131 接口

```python
# PHASE 131 可调用
from suggestion_service import get_suggestion_service
svc = get_suggestion_service()
suggestions = svc.get_pending_suggestions()
```

---

## 11. 总结

PHASE 130 完成了：

1. ✓ Suggestion 数据模型定义
2. ✓ SuggestionGenerator 规则引擎实现
3. ✓ SQLite 持久化存储
4. ✓ 去重控制机制
5. ✓ REST API 端点
6. ✓ 完整测试覆盖

**所有测试通过（5/5），约束满足，等待 PHASE 131 指令。**

---

*报告生成时间: 2026-09-04T06:30:00+08:00*
