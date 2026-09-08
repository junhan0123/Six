# Xiao6 v1.0.0 — PHASE 143 Causal Graph Foundation Report

**日期**: 2026-09-04  
**版本**: v1.0.0  
**状态**: 已完成

---

## 1. 执行摘要

PHASE 143 完成 Global Foresight Engine Causal Graph Foundation。

本阶段建立因果关系图谱，支持节点管理、边管理、路径查找和影响路径计算，为后续预测引擎提供因果推理基础。

---

## 2. 数据库结构

### 2.1 gfe_causal_nodes

| 列名 | 类型 | 说明 |
|------|------|------|
| node_id | TEXT PRIMARY KEY | 节点唯一标识 |
| name | TEXT NOT NULL | 节点名称 |
| category | TEXT | 类别（economy/finance/energy等） |
| description | TEXT | 描述 |
| entity_type | TEXT | 实体类型（indicator/policy/event等） |
| provenance | TEXT | 来源追溯 |
| created_at | REAL | 创建时间戳 |

### 2.2 gfe_causal_edges

| 列名 | 类型 | 说明 |
|------|------|------|
| edge_id | TEXT PRIMARY KEY | 边唯一标识 |
| source_node | TEXT NOT NULL | 源节点ID |
| target_node | TEXT NOT NULL | 目标节点ID |
| relationship_type | TEXT | 关系类型（cause/lead_to/correlate等） |
| strength | REAL DEFAULT 0.5 | 强度 (0-1) |
| confidence | REAL DEFAULT 0.5 | 置信度 (0-1) |
| time_delay | INTEGER | 时间延迟（天） |
| evidence_refs | TEXT DEFAULT '[]' | 证据引用 |
| provenance | TEXT | 来源追溯 |
| created_at | REAL | 创建时间戳 |

---

## 3. 核心模块

### 3.1 CausalGraphEngine

**文件**: `xiao6-ui/gfe_causal.py` (610 lines)

**核心方法**:
- `add_node()` — 添加因果节点
- `add_edge()` — 添加因果边
- `get_nodes()` — 查询节点（支持类别过滤）
- `get_edges()` — 查询边（支持源/目标过滤）
- `find_path()` — BFS路径查找
- `calculate_impact_path()` — 计算影响路径
- `get_node()` — 按ID获取节点
- `get_node_by_name()` — 按名称获取节点

### 3.2 图遍历算法

**BFS (广度优先搜索)**:
```python
queue = deque([(start, [start], [])])
visited = {start}

while queue:
    current, path, edge_path = queue.popleft()
    
    if current == end:
        return CausalPath(...)
    
    for neighbor in adjacency[current]:
        if neighbor not in visited:
            visited.add(neighbor)
            queue.append((neighbor, path + [neighbor], ...))
```

**影响路径计算**:
```python
queue = deque([(node_id, 0, [node_id])])
while queue:
    current, depth, path = queue.popleft()
    # 记录所有可达节点
```

---

## 4. 种子数据

### 4.1 能源因果链 (5 nodes, 4 edges)

```
oil_price → energy_cost → inflation → interest_rate → growth
```

### 4.2 科技因果链 (4 nodes, 3 edges)

```
chip_supply → technology_output → industrial_capacity → economic_growth
```

### 4.3 金融因果链 (4 nodes, 3 edges)

```
interest_rate → liquidity → asset_price → investment
```

**总计**: 12 nodes, 10 edges

---

## 5. API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/gfe/causal/nodes` | 查询节点列表 |
| POST | `/api/gfe/causal/node` | 创建节点 |
| POST | `/api/gfe/causal/edge` | 创建边 |
| GET | `/api/gfe/causal/path/{node}` | 计算影响路径 |

### 响应格式示例

**查询节点**:
```json
{
  "nodes": [
    {
      "node_id": "node_1725441234_abc",
      "name": "oil_price",
      "category": "energy",
      "description": "国际原油价格",
      "provenance": "IEA, OPEC reports"
    }
  ],
  "count": 12
}
```

**影响路径**:
```json
{
  "node_id": "oil_price",
  "impacts": [
    {
      "target_node": "energy_cost",
      "depth": 1,
      "path": ["oil_price", "energy_cost"],
      "edge_count": 1
    },
    {
      "target_node": "inflation",
      "depth": 2,
      "path": ["oil_price", "energy_cost", "inflation"],
      "edge_count": 2
    }
  ]
}
```

---

## 6. EventBus 集成

### 6.1 新增主题

| 主题 | 说明 |
|------|------|
| `gfe_causal_node_added` | 因果节点新增 |
| `gfe_causal_edge_added` | 因果边新增 |
| `gfe_causal_path_generated` | 因果路径生成 |

### 6.2 事件格式

```json
{
  "event_name": "gfe_causal_node_added",
  "timestamp": 1725441234.5,
  "node_id": "node_xxx",
  "name": "节点名称"
}
```

---

## 7. 测试结果

```
Ran 16 tests in 1.156s
OK
```

### 测试覆盖

| 测试类 | 测试数 | 说明 |
|--------|--------|------|
| TestPhase143Database | 3 | 数据库表结构验证 |
| TestPhase143Engine | 12 | 核心引擎功能 |
| TestPhase143API | 1 | API端点定义 |
| TestPhase143SeedData | 1 | 种子数据加载 |

### 具体测试项

- ✓ 数据库表存在 (`test_tables_exist`)
- ✓ 节点表结构完整 (`test_nodes_schema`)
- ✓ 边表结构完整 (`test_edges_schema`)
- ✓ 添加节点 (`test_add_node`)
- ✓ 添加边 (`test_add_edge`)
- ✓ 查询节点 (`test_get_nodes`)
- ✓ 查询边 (`test_get_edges`)
- ✓ 路径查找 (`test_find_path`)
- ✓ 不存在路径 (`test_find_path_not_exist`)
- ✓ 影响路径计算 (`test_calculate_impact_path`)
- ✓ 按名称获取节点 (`test_get_node_by_name`)
- ✓ EventBus主题注册 (`test_eventbus_topics_registered`)
- ✓ 前端格式转换 (`test_to_frontend_format`)
- ✓ 路径强度计算 (`test_path_strength_calculation`)
- ✓ API端点定义 (`test_api_endpoints_defined`)
- ✓ 种子数据加载 (`test_seed_data`)

---

## 8. 架构约束验证

### ✅ 遵守的约束

1. **未修改执行系统核心**
   - ai_core.execution.run — 未触碰
   - planner — 未触碰
   - policy_engine — 未触碰
   - ExecutionBridge — 未触碰
   - AgentRuntime — 未触碰

2. **无第二 Runtime**
   - 所有操作通过现有 EventBus
   - 无独立执行入口

3. **数据层隔离**
   - 新表 gfe_* 命名空间
   - 不影响现有数据表

4. **EventBus 解耦**
   - 所有事件通过 publish_system() 发布
   - 无直接模块调用

### ✅ 架构一致性

- 遵循 PHASE 139-142 的 Singleton 模式
- 遵循幂等 migration 模式
- 遵循 to_frontend() 格式化模式
- 遵循 provenance 追溯要求
- 使用 BFS 而非 ML 模型

---

## 9. 修改文件清单

| 文件 | 操作 | 行数变化 |
|------|------|----------|
| `xiao6-ui/db.py` | 修改 | +38 行 |
| `xiao6-ui/eventbus.py` | 修改 | +4 行 |
| `xiao6-ui/server.py` | 修改 | +55 行 |
| `xiao6-ui/gfe_causal.py` | 新建 | 610 行 |
| `xiao6-ui/test_phase143.py` | 新建 | 280 行 |

---

## 10. Git Diff 摘要

```bash
$ git diff --stat
 xiao6-ui/db.py         |  38 +++++++++++
 xiao6-ui/eventbus.py   |   4 ++
 xiao6-ui/server.py     |  55 ++++++++++++++
 xiao6-ui/gfe_causal.py | 610 +++++++++++++++++++++++++++++++++++++++++++++++++
 xiao6-ui/test_phase143.py | 280 ++++++++++++++++++++++++++
 5 files changed, 987 insertions(+)
```

---

## 11. 下一阶段展望

PHASE 143 完成后，GFE 因果图谱基础已建立：
- PHASE 139: Data Source Foundation ✓
- PHASE 140: World State Engine ✓
- PHASE 141: Event Intelligence ✓
- PHASE 142: Historical Comparison ✓
- PHASE 144: Analyst Council Foundation
- PHASE 145: Forecast Engine Foundation

等待用户指示。

---

**报告输出**: `G:/xiao6/XIAO6-v1.0.0-PHASE-143-CAUSAL-GRAPH-FOUNDATION-REPORT.md`  
**桌面副本**: `F:\桌面\XIAO6-v1.0.0-PHASE-143-CAUSAL-GRAPH-FOUNDATION-REPORT.md`  
**Git 状态**: modified，未 commit ✓

---

## 12. PHASE 143 COMPLETE
