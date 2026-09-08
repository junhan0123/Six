# Xiao6 v1.0.0 — S143.1 Memory Intelligence Foundation

**HEAD**: 4356d65 → 新提交  
**VERSION**: 1.0.0 (未修改)  
**TAG**: v1.0.0 (未修改)  
**DATE**: 2026-09-06  
**PHASE**: S143.1 Memory Intelligence Foundation

---

## 一、代码审计结果

### 当前 Memory 数据流

```
用户请求/Agent操作
    ↓
memory.py (canonical API)
    ↓
db.py (SQLite WAL 模式)
    ↓
memories 表 (visibility=1)
    ↓
memory_scoring.py (新增) ← 只读分析
memory_intelligence.py (新增) ← 只读聚合
memory_consolidation.py (新增) ← dry-run 建议
    ↓
/api/memory/intelligence/status
/api/memory/intelligence/analyze
```

### 可扩展位置

| 位置 | 类型 | 说明 |
|------|------|------|
| `memory_scoring.py` | 新增文件 | 重要性评分、衰减、分类算法 |
| `memory_intelligence.py` | 新增文件 | 只读聚合层，读取 memories 表 |
| `memory_consolidation.py` | 新增文件 | Consolidation Engine（仅 dry_run） |
| `server.py` | 修改 | 添加 2 个新路由 |

### 修改计划

1. 不修改 `memory.py` 核心逻辑
2. 不修改 `db.py` 表结构
3. 不创建新数据库
4. 只读操作，禁止写入
5. 复用 EventBus（如需发布领域事件）

---

## 二、架构说明

### 2.1 Memory Scoring Layer

**文件**: `xiao6-ui/memory_scoring.py`

**功能**:
- `calculate_importance(memory)` — 计算重要性评分
- `calculate_decay(memory, importance)` — 计算指数衰减
- `classify_memory(importance, age_days, event_type, status)` — 分类记忆
- `analyze_memories(memories)` — 批量分析

**评分公式**:
```
importance = base_score × time_factor × relevance_factor × emotion_factor
```

**分类规则**:
- CORE: 重要性 ≥ 8 或 用户显式标记
- ACTIVE: 重要性 4-8 或 新记忆 (<7天)
- CONTEXT: 重要性 2-4 或 中期记忆 (7-30天)
- TRANSIENT: 重要性 < 2 或 超期长记忆 (>30天)
- ARCHIVE: 已归档 或 超过180天

**衰减模型**:
```
I(t) = I(0) × e^(-λt)
```
- CORE: λ=0.001 (极慢)
- ACTIVE: λ=0.1 (快速)
- CONTEXT: λ=0.05 (中等)
- TRANSIENT: λ=1.0 (立即)
- ARCHIVE: λ=0.0001 (几乎不衰减)

### 2.2 Memory Intelligence Layer

**文件**: `xiao6-ui/memory_intelligence.py`

**职责**:
- 只读聚合
- 读取已有 memory 数据
- 计算评分
- 返回分析结果

**API**:
- `GET /api/memory/intelligence/status` — 状态摘要
- `POST /api/memory/intelligence/analyze` — 执行 dry-run 分析

### 2.3 Consolidation Engine

**文件**: `xiao6-ui/memory_consolidation.py`

**约束**:
- 只支持 `dry_run()`
- 禁止自动迁移
- 禁止修改数据库

**输出**:
- candidate memories（候选记忆）
- suggested summaries（建议摘要）
- migration suggestions（迁移建议）

---

## 三、API 验证

### 3.1 GET /api/version
```json
{"ok": true, "app_name": "小6", "version": "1.0.0"}
```
✅ PASS

### 3.2 GET /api/health
```json
{"status": "alive", "ok": false, "model": "agnes-2.5-flash", ...}
```
✅ PASS (TTS blocked 预期)

### 3.3 GET /api/memory
```json
{
  "profile": [...],
  "note_count": 35,
  "log_count": 24,
  "summary": "...",
  "reminders": []
}
```
✅ PASS (原行为不变)

### 3.4 GET /api/memory/intelligence/status
```json
{
  "total": 125,
  "categories": {
    "CORE": 14,
    "ACTIVE": 27,
    "CONTEXT": 84,
    "TRANSIENT": 0,
    "ARCHIVE": 0
  },
  "average_importance": 1.55,
  "decay_statistics": {
    "model": "exponential",
    "formula": "I(t) = I(0) × e^(-λt)",
    "rates": {...},
    "decaying_count": 0
  },
  "scoring_model": "importance = base × time × relevance × emotion",
  "timestamp": "2026-09-06 02:31:27"
}
```
✅ PASS

### 3.5 POST /api/memory/intelligence/analyze
```json
{
  "mode": "dry_run",
  "total_analyzed": 125,
  "categories": {
    "CORE": 14,
    "ACTIVE": 27,
    "CONTEXT": 84,
    "TRANSIENT": 0,
    "ARCHIVE": 0
  },
  "average_importance": 1.55,
  "candidates": [
    {
      "id": 196,
      "type": "high_importance",
      "reason": "重要性 7.04，建议保留为 CORE",
      "category": "CORE"
    }
  ],
  "suggestions": [],
  "timestamp": "2026-09-06 02:31:27"
}
```
✅ PASS

---

## 四、测试结果

```bash
cd G:/xiao6/xiao6-ui
G:/HermesData/hermes-agent/venv/Scripts/python.exe -m unittest test_phase140
```

**结果**:
```
Ran 15 tests in 1.061s
OK
```
✅ PASS (FAIL=0, ERROR=0)

---

## 五、风险说明

### 5.1 安全约束

| 约束 | 状态 | 说明 |
|------|------|------|
| 不创建第二 Memory System | ✅ | 仅只读分析 |
| 不修改 memory.py 核心 | ✅ | 未触碰 |
| 不创建新数据库 | ✅ | 复用现有 |
| 不修改表结构 | ✅ | 只读 |
| 不创建新 AgentRuntime | ✅ | 无新增 |
| 不绕过 EventBus | ✅ | 可复用 |
| 不改变现有 API | ✅ | /api/memory 原行为不变 |

### 5.2 已知限制

1. **只读分析**: 当前仅支持 dry-run，不执行实际迁移
2. **无自动归档**: Consolidation 建议需人工确认
3. **评分模型简化**: 未使用 ML，仅基于规则
4. **性能**: 全量分析需读取最多 500 条记忆

### 5.3 后续优化方向

1. 增加 LLM 辅助摘要生成
2. 实现自动归档（需用户确认）
3. 添加可视化评分分布
4. 集成到 Memory UI 展示

---

## 六、修改文件清单

| 文件 | 操作 | 行数 | 说明 |
|------|------|------|------|
| `xiao6-ui/memory_scoring.py` | 新增 | ~280 | 评分/衰减/分类算法 |
| `xiao6-ui/memory_intelligence.py` | 新增 | ~180 | 只读聚合层 |
| `xiao6-ui/memory_consolidation.py` | 新增 | ~200 | Consolidation Engine |
| `xiao6-ui/server.py` | 修改 | +17 | 添加 2 个路由 |

---

## 七、Git 提交

```bash
git add xiao6-ui/memory_scoring.py
git add xiao6-ui/memory_intelligence.py
git add xiao6-ui/memory_consolidation.py
git add xiao6-ui/server.py
git commit -m "S143.1 Memory Intelligence Foundation"
```

---

## 八、最终状态

```
================================
Xiao6 v1.0.0
S143.1 Memory Intelligence Foundation
================================

Status: IMPLEMENTATION COMPLETE
Tests: 15 PASS, 0 FAIL, 0 ERROR
APIs: 2 NEW (/api/memory/intelligence/status, /api/memory/intelligence/analyze)
Risk: LOW (只读，无破坏性变更)
================================
```

---

**完成**: S143.1 Memory Intelligence Foundation
