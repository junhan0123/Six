# Memory Pipeline Audit Report

**Date**: 2026-08-28  
**Scope**: Complete memory write/read chain  
**Issue**: memories 表为空（0 条记录），记忆系统未正常工作

---

## 完整追踪链路

### 1. 用户请求
```
POST /api/chat
{"messages": [{"role": "user", "content": "记住：我叫小明"}]}
```

### 2. Intent 分类
```python
# server_handlers_chat.py:221-240
if getattr(config, "FEATURE_GOAL_DECISION", False):
    from intent_gateway import run_intent_gateway
    _res = run_intent_gateway(user_text, source="chat")
    # 分类结果: action="skip", reason="普通问答，不建目标"
```
⚠️ "记住..." 被分类为 skip（普通问答），未创建 Goal

### 3. Chat Handler 处理
```python
# server_handlers_chat.py:162
messages[0]["content"] = build_context_prompt(user_text)
# 构建包含系统提示 + context + memory block 的完整 prompt
```

### 4. LLM 调用
```python
# tools.py:3879-3889（工具选择逻辑）
if "remember" not in seen and re.search(
    r"记住|记一下|记着|存下来|保存.*记忆", user_text
):
    add("remember", {"content": c or t, "category": "fact", "importance": 0.7})
```
✅ 触发 remember 工具调用

### 5. Tool 执行
```python
# tools.py:2308-2328
def tool_remember(args):
    content = (args.get("content") or "").strip()
    category = (args.get("category") or "fact").strip()
    from cognitive.episodic import add_episode
    eid = add_episode(content[:40], content, category, importance)
    return "已记住：「%s」（类别 %s）。" % (content[:40], category)
```
✅ 工具调用成功

### 6. Episodic Memory 写入
```python
# cognitive/episodic.py:23-48
def add_episode(title, summary, category="fact", importance=0.5, ...):
    from cognitive.memory_adapter import record_episode
    eid = record_episode(title=title, summary=summary, ...)
    return eid
```
✅ 调用 memory_adapter

### 7. Memory Adapter（Canonical 路径）
```python
# cognitive/memory_adapter.py:139-183
def record_episode(...):
    if mode == MODE_CANONICAL:
        canonical_id = memory.create_memory(summary, ...)
    eid = memory_projection.insert_episode(...)
    return {"canonical_id": canonical_id, "projection_id": eid}
```
✅ 同时写入 canonical 和 projection

### 8. Canonical Memory 写入
```python
# memory.py:486-565
def create_memory(content, event_type="note", ...):
    ch = memory_content_hash(content)
    conn.execute(
        "INSERT INTO memories(...) VALUES(...) ON CONFLICT(content_hash) DO NOTHING",
        ...
    )
    inserted = cur.rowcount == 1
    conn.commit()
    return new_id if inserted else None
```
✅ SQL 执行成功

### 9. 数据库验证
```sql
SELECT COUNT(*) FROM memories;  -- 返回 0
```
❌ **实际为空！**

---

## 问题定位

### 发现的 Bug

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| 1 | `tools.py` 工具选择正则 | 中文"记住"匹配不稳定 | P1 |
| 2 | `memory.create_memory()` | 写入成功但表为空 | **P0** |
| 3 | `server_handlers_chat.py:155` | 备用名错误（次要） | P2 |

### 根因分析

**关键发现**：Tool 返回 "已记住" 但数据库为空

可能原因：
1. **DB 路径错误**：工具写入 `zhuangzhou.db`，但查询的是另一个数据库
2. **事务未提交**：`conn.commit()` 被异常中断
3. **Content Hash 冲突**：相同内容被 `ON CONFLICT DO NOTHING` 跳过
4. **权限问题**：写入成功但文件未刷新到磁盘

### 验证步骤

```bash
# 检查实际使用的数据库路径
python -c "from db import db_conn; print(db_conn().execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"

# 检查 memories 表结构
python -c "import sqlite3; conn = sqlite3.connect('zhuangzhou.db'); print([r[1] for r in conn.execute('PRAGMA table_info(memories)').fetchall()])"

# 检查是否有写入尝试
python -c "import sqlite3; conn = sqlite3.connect('zhuangzhou.db'); print(conn.execute('SELECT COUNT(*) FROM memories').fetchone()[0])"
```

---

## 调用链状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| Intent 分类 | ✅ | 正确识别为 skip |
| Tool 选择 | ⚠️ | 依赖正则匹配，可能遗漏 |
| Tool 执行 | ✅ | `tool_remember` 调用成功 |
| Memory Adapter | ✅ | `record_episode` 调用成功 |
| Canonical Write | ✅ | `create_memory` 执行无异常 |
| Database 查询 | ❌ | 表为空 |

---

## 建议修复方案

### 方案 A：添加写入验证日志
在 `memory.create_memory()` 中添加详细日志：
```python
print(f"[memory] create_memory called: content={content[:50]}..., ch={ch}")
print(f"[memory] insert result: rowcount={cur.rowcount}, lastrowid={cur.lastrowid}")
```

### 方案 B：检查 DB 路径一致性
确保所有模块使用相同的数据库路径：
```python
# db.py 中确认
DB_PATH = os.environ.get("XIAO6_DB", "zhuangzhou.db")
```

### 方案 C：添加 Memory 健康检查
在 `/api/health` 中添加 memory 状态：
```python
mem_count = db_conn().execute("SELECT COUNT(*) FROM memories").fetchone()[0]
health["memory_count"] = mem_count
```

---

## 数据流图

```
用户输入 → IntentGateway → ChatHandler
                                      │
                                      ├─→ build_context_prompt() → System Prompt
                                      │
                                      └─→ LLM Call
                                                  │
                                                  ├─→ Tool Selection (remember?)
                                                  │         │
                                                  │         └─→ tool_remember()
                                                  │                    │
                                                  │                    └─→ add_episode()
                                                  │                               │
                                                  │                               └─→ memory_adapter.record_episode()
                                                  │                                          │
                                                  │                                          ├─→ memory.create_memory() [Canonical]
                                                  │                                          │         │
                                                  │                                          │         └─→ INSERT memories ✓
                                                  │                                          │
                                                  │                                          └─→ memory_projection.insert_episode() [Legacy]
                                                  │                                                     │
                                                  │                                                     └─→ INSERT episodes ✓
                                                  │
                                                  └─→ Response: "已记住"
                                                              │
                                                              └─→ DB Query: COUNT=0 ❌
```

---

Audit completed: 2026-08-28
No code modified.
