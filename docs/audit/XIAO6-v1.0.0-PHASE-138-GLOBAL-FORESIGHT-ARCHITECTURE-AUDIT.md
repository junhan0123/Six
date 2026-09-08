# Xiao6 v1.0.0 — PHASE 138 Global Foresight Engine Architecture Audit

**日期**: 2026-09-04  
**版本**: v1.0.0  
**状态**: 完成 (READ-ONLY 审计，无代码修改)

---

## 1. Executive Summary

Global Foresight Engine (GFE) 是一个高级智能研判系统，其目标不是做新闻摘要，而是建立：

> 全球情报 → 世界状态 → 历史类比 → 因果关系 → 多 Agent 研判 → 情景推演 → 概率预测 → 风险预警 → 预测验证 → 持续校准

### 关键发现

1. **架构完整度**: Xiao6 已有 Execution System (PHASE 131-137)，支持 Proposal → Approval → Runtime → Timeline → Audit 完整闭环
2. **复用性高**: Scheduler、EventBus、Observation/Suggestion/Proposal 层、Execution Request 体系可直接复用
3. **需要新增**: World State Engine、Causal Graph、Forecast Ledger、Analyst Council、数据源管理层
4. **Memory 挑战**: 现有 Memory 架构(Compact/Canonical)适合运营数据，但需扩展支持结构化实体(国家/指标/事件)和预测记录

---

## 2. Current Architecture

### 2.1 核心模块清单

| 模块 | 文件 | 状态 | 大小 |
|------|------|------|------|
| AgentRuntime | agent_runtime.py | ✅ 存在 | 78KB |
| ai_core.execution | ai_core/execution/ | ✅ 存在 | 4KB |
| EventBus | eventbus.py | ✅ 存在 | 13KB |
| Goals | goals.py | ✅ 存在 | 23KB |
| Tasks | tasks.py | ✅ 存在 | 10KB |
| Memory | memory.py | ✅ 存在 | 33KB |
| Episodic Memory | cognitive/episodic.py | ✅ 存在 | 7KB |
| Memory Adapter | cognitive/memory_adapter.py | ✅ 存在 | 10KB |
| Knowledge/RAG | knowledge/*.py | ✅ 存在 | 23文件 |
| Tools | tools.py | ✅ 存在 | 190KB |
| Scheduler | scheduler.py | ✅ 存在 | 14KB |
| Observation | observation_service.py | ✅ 存在 | 15KB |
| Suggestion | suggestion_service.py | ✅ 存在 | 15KB |
| Proposal | proposal_service.py | ✅ 存在 | 15KB |
| Validator | proposal_validator.py | ✅ 存在 | 7KB |
| Adapter | proposal_task_adapter.py | ✅ 存在 | 6KB |
| Automation Policy | automation_policy.py | ✅ 存在 | 5KB |
| Execution Request | execution_request.py | ✅ 存在 | 2KB |
| Execution Bridge | execution_bridge.py | ✅ 存在 | 14KB |
| Self-Improvement | self_improvement.py | ✅ 存在 | (通过 proactive.py 调用) |

### 2.2 EventBus Topics (可扩展性评估)

```
xiao6.task.lifecycle     - 任务生命周期(已有)
xiao6.goal.lifecycle     - 目标生命周期(已有)
xiao6.sse                - SSE 实时推送(已有)
xiao6.hud.state          - HUD 状态(已有)
xiao6.goal               - 目标更新(已有)
xiao6.mobile.sync        - 移动端同步(已有)
xiao6.clipboard          - 剪贴板(已有)
xiao6.agent.*            - Agent 事件(已有)
xiao6.tool.*             - 工具事件(已有)
```

**GFE 需要新增的 Topic**:

```
gfe.news.arrived         - 新情报到达
gfe.indicator.updated    - 指标更新
gfe.forecast.created     - 预测创建
gfe.forecast.resolved    - 预测验证
gfe.risk.signal          - 风险信号
```

### 2.3 执行链路 (已验证)

```
用户/Proposal
    ↓
Intent Gateway (server.py)
    ↓
AgentRuntime.run_chat_turn() / ExecutionBridge.execute_request()
    ↓
Policy Engine.evaluate()
    ↓
Task System → ExecutionRequest (pending)
    ↓
approval_gate (pending → approved)  ← 用户审批
    ↓
Runtime._execute_task()
    ↓
ai_core.execution.run() ← 唯一入口 ✓
    ↓
Tool Executor
    ↓
EventBus.publish() → ObservationService
    ↓
Result → Timeline → Audit
```

**结论**: 执行链路完整、单一入口、有审批门控。GFE 的任务必须通过此路径执行。

---

## 3. Capability Reuse Matrix

| 能力 | 当前实现 | 文件/模块 | 是否可复用 | 是否需要扩展 | 风险 |
|------|----------|-----------|------------|--------------|------|
| Agent | ✅ 完整 | agent_runtime.py | ✅ 高 | ❌ 否 | 低 |
| Task | ✅ 完整 | tasks.py | ✅ 高 | ❌ 否 | 低 |
| DAG | ✅ 已有 | goals.py (plan_goal) | ✅ 高 | ❌ 否 | 低 |
| Tool | ✅ 完整 | tools.py | ✅ 高 | ❌ 否 | 低 |
| Runtime | ✅ 完整 | ai_core/execution/ | ✅ 高 | ❌ 否 | 低 |
| Execution | ✅ 完整 | execution_bridge.py | ✅ 高 | ❌ 否 | 低 |
| Approval | ✅ 完整 | proposal_service.py | ✅ 高 | ❌ 否 | 低 |
| Timeline | ✅ 完整 | execution_bridge.py | ✅ 高 | ❌ 否 | 低 |
| Audit | ✅ 完整 | execution_bridge.py (AuditLog) | ✅ 高 | ❌ 否 | 低 |
| Memory | ⚠️ 部分 | memory.py, episodic.py | ⚠️ 中 | ✅ 是 | 中 |
| Event | ✅ 完整 | eventbus.py | ✅ 高 | ✅ 小扩展 | 低 |
| Scheduler | ✅ 完整 | scheduler.py | ✅ 高 | ✅ 需配置周期任务 | 低 |
| API | ✅ 完整 | server.py | ✅ 高 | ✅ 需新增 GFE 端点 | 低 |
| SSE/WebSocket | ✅ 完整 | server.py (SSE) | ✅ 高 | ❌ 否 | 低 |
| UI Router | ✅ 完整 | ui/js/app.js | ✅ 高 | ✅ 需新增 GFE Tab | 低 |
| Work Center | ✅ 完整 | PHASE 137 | ✅ 高 | ✅ 需扩展 Observation | 低 |
| Self Improvement | ✅ 完整 | self_improvement.py | ✅ 高 | ✅ 需集成 Forecast | 中 |

---

## 4. Memory Integration Analysis

### 4.1 现有 Memory 架构

```
memory.py (33KB)
├── Compact Memory: chat_log 压缩 → memory_summary
├── Canonical Memory: 统一写入权威 (memory_adapter.py)
├── Episodic Memory: 情节记忆 (cognitive/episodic.py)
├── Vector Search: embed.py ONNX 向量检索
└── Tables: memories, mem_vectors, episodes
```

### 4.2 GFE 数据类型需求

| 数据类型 | 存储需求 | 推荐方案 |
|----------|----------|----------|
| 新闻/事件 | 结构化实体 + 时间序列 | 新增 `gfe_events` 表 |
| 国家状态 | JSON 实体 + 置信度 | 新增 `gfe_world_state` 表 |
| 指标数据 | 时间序列 + 来源追溯 | 新增 `gfe_indicators` 表 |
| 历史案例 | 相似度 + 结构映射 | 复用 `episodic` + 向量索引 |
| 预测记录 | 量化概率 + 假设 | 新增 `gfe_forecasts` 表 |
| 因果图谱 | 节点 + 边 + 机制 | 新增 `gfe_causal_graph` 表 |
| 预测账本 | Brier Score + 校准 | 新增 `gfe_forecast_ledger` 表 |

### 4.3 建议: 新建 GFE Schema

```sql
-- 新闻/事件存储
CREATE TABLE IF NOT EXISTS gfe_events (
    event_id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES gfe_sources(source_id),
    title TEXT NOT NULL,
    summary TEXT,
    category TEXT,      -- policy/market/industry/diplomacy/military/social
    country_code TEXT,
    timestamp REAL,
    confidence REAL,    -- 来源可信度
    provenance TEXT,    -- 原始URL/文档引用
    created_at REAL
);

-- 世界状态
CREATE TABLE IF NOT EXISTS gfe_world_state (
    state_id TEXT PRIMARY KEY,
    country_code TEXT NOT NULL,
    snapshot_ts REAL,
    demographics JSON,
    economy JSON,
    finance JSON,
    industry JSON,
    technology JSON,
    energy JSON,
    military JSON,
    diplomacy JSON,
    trade JSON,
    fiscal JSON,
    social JSON,
    confidence REAL,
    source_refs TEXT,   -- JSON array of source_ids
    updated_at REAL
);

-- 指标时间序列
CREATE TABLE IF NOT EXISTS gfe_indicators (
    indicator_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country_code TEXT,
    unit TEXT,
    value REAL,
    previous_value REAL,
    timestamp REAL,
    source_id TEXT REFERENCES gfe_sources(source_id),
    provenance TEXT
);

-- 预测记录
CREATE TABLE IF NOT EXISTS gfe_forecasts (
    forecast_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    target TEXT,
    created_at REAL,
    horizon INTEGER,    -- 预测周期(天)
    probability REAL,   -- P(0-1)
    confidence REAL,    -- 置信度(0-1)
    base_rate REAL,     -- 基准率
    evidence TEXT,      -- JSON array of evidence items
    assumptions TEXT,   -- JSON array
    alternative_scenarios TEXT,  -- JSON array
    key_drivers TEXT,   -- JSON array
    contradicting_evidence TEXT, -- JSON array
    resolution_criteria TEXT,
    resolution_date REAL,
    actual_outcome TEXT,
    score REAL,         -- Brier Score
    created_by TEXT,    -- Agent role
    status TEXT         -- active/resolved/retracted
);

-- 因果图谱
CREATE TABLE IF NOT EXISTS gfe_causal_nodes (
    node_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,          -- variable/policy/outcome/indicator
    category TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS gfe_causal_edges (
    edge_id TEXT PRIMARY KEY,
    from_node TEXT REFERENCES gfe_causal_nodes(node_id),
    to_node TEXT REFERENCES gfe_causal_nodes(node_id),
    mechanism TEXT,     -- 因果机制描述
    sign TEXT,          -- positive/negative
    time_lag REAL,      -- 时间延迟(天)
    confidence REAL,
    evidence TEXT       -- JSON array of supporting evidence
);

-- 数据源管理
CREATE TABLE IF NOT EXISTS gfe_sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,          -- official/international/market/news/academic/historical/open_data
    country TEXT,
    authority TEXT,
    reliability REAL,   -- 0-1 可信度评分
    update_frequency TEXT,  -- hourly/daily/weekly/monthly
    license TEXT,
    provenance TEXT,
    created_at REAL,
    last_updated REAL
);

-- 预测账本 (Brier Score / 校准 / Agent 准确率)
CREATE TABLE IF NOT EXISTS gfe_forecast_ledger (
    ledger_id TEXT PRIMARY KEY,
    forecast_id TEXT REFERENCES gfe_forecasts(forecast_id),
    brier_score REAL,
    log_loss REAL,
    calibration REAL,
    bias REAL,
    overconfidence REAL,
    underconfidence REAL,
    agent_accuracy REAL,
    domain_accuracy REAL,
    country_accuracy REAL,
    horizon_accuracy REAL,
    resolved_at REAL
);
```

---

## 5. Event Integration Analysis

### 5.1 现有 EventBus 能力

- ✅ 支持 topic 维度 pub/sub
- ✅ 支持 sync/async 订阅者
- ✅ 支持优先级队列
- ✅ 支持死信队列 (Dead Letter)
- ✅ SSE 桥接已实现

### 5.2 GFE 需要的 Event Topics

```python
# 建议添加到 eventbus.py
TOPIC_GFE_NEWS_ARRIVED = "gfe.news.arrived"
TOPIC_GFE_INDICATOR_UPDATED = "gfe.indicator.updated"
TOPIC_GFE_FORECAST_CREATED = "gfe.forecast.created"
TOPIC_GFE_FORECAST_RESOLVED = "gfe.forecast.resolved"
TOPIC_GFE_RISK_SIGNAL = "gfe.risk.signal"
TOPIC_GFE_COUNTR_YSTATE_UPDATED = "gfe.country.state.updated"
```

### 5.3 Event Payload 设计

```python
@dataclass
class GFEEvent:
    event_id: str
    topic: str
    timestamp: float
    source: str           # "data_ingestion" | "analysis" | "forecast" | "warning"
    payload: dict
    priority: int = 5
    
    # News Arrived
    # { "event_id": str, "title": str, "country": str, "category": str, "reliability": float }
    
    # Indicator Updated
    # { "indicator": str, "country": str, "value": float, "previous": float, "source": str }
    
    # Forecast Created
    # { "forecast_id": str, "question": str, "probability": float, "confidence": float }
    
    # Risk Signal
    # { "signal_id": str, "type": str, "country": str, "severity": str, "probability": float }
```

---

## 6. Scheduler Integration Analysis

### 6.1 现有 Scheduler 能力

```python
# scheduler.py (14KB)
class Scheduler:
    - schedule_once(delay_seconds, callback, task_id)    # 单次延迟
    - schedule_interval(interval_seconds, callback, task_id)  # 周期任务
    - schedule_event(event_name, callback, task_id)      # 事件驱动
```

### 6.2 GFE 需要的调度任务

| 任务 | 频率 | 实现方式 |
|------|------|----------|
| 新闻/事件扫描 | 每小时 | `schedule_interval(3600, ...)` |
| 全球状态更新 | 每天 | `schedule_interval(86400, ...)` |
| 风险扫描 | 每天 | `schedule_interval(86400, ...)` |
| 国家状态重新评估 | 每周 | `schedule_interval(604800, ...)` |
| 预测校准 | 每月 | `schedule_interval(2592000, ...)` |
| 预测到期 Resolution | 事件驱动 | `schedule_event("FORECAST_EXPIRED", ...)` |

### 6.3 集成方案

```python
# 在 proactive.py 或新建 gfe_scheduler.py
def bootstrap_gfe_scheduler():
    scheduler = Scheduler()
    scheduler.start()
    
    # 每小时新闻扫描
    scheduler.schedule_interval(
        interval_seconds=3600,
        callback=scan_intelligence,
        task_id="gfe_news_hourly"
    )
    
    # 每天全球状态更新
    scheduler.schedule_interval(
        interval_seconds=86400,
        callback=update_world_state,
        task_id="gfe_state_daily"
    )
    
    # 每周国家重新评估
    scheduler.schedule_interval(
        interval_seconds=604800,
        callback=reassess_countries,
        task_id="gfe_country_weekly"
    )
    
    return scheduler
```

---

## 7. Execution Integration Analysis

### 7.1 GFE 任务类型与现有系统映射

| GFE 任务 | 现有系统 | 映射方式 |
|----------|----------|----------|
| 情报采集 | ExecutionRequest | 同 PHASE 137 流程 |
| 数据更新 | ExecutionRequest | 同 PHASE 137 流程 |
| 历史分析 | ExecutionRequest | 同 PHASE 137 流程 |
| Agent 推演 | ExecutionRequest | 同 PHASE 137 流程 |
| 预测验证 | ExecutionRequest | 同 PHASE 137 流程 |
| 风险扫描 | ExecutionRequest | 同 PHASE 137 流程 |

### 7.2 复用路径

```
GFE Intelligence Task
    ↓
Task System → ExecutionRequest (pending)
    ↓
GFE 内部审批 (规则/置信度阈值)
    ↓
Runtime._execute_task()
    ↓
ai_core.execution.run() ← 唯一入口 ✓
    ↓
Result → GFE ObservationService → EventBus → Timeline → Audit
```

### 7.3 关键约束

✅ **可以复用**:
- `GET /api/execution/requests` — 查看待处理任务
- `POST /api/execution/requests/{id}/approve` — 审批
- `POST /api/execution/requests/{id}/cancel` — 取消(kill switch)
- `GET /api/execution/timeline/{id}` — 查看执行历史
- `GET /api/automation/audit` — 审计日志

❌ **禁止**:
- GFE 直接调用 Runtime
- GFE 绕过 ExecutionRequest 执行
- GFE 自动 approve (必须经审批)

---

## 8. Data Architecture Design

### 8.1 数据源分类与元数据

```python
@dataclass
class DataSource:
    source_id: str           # 唯一标识
    name: str                # 显示名称
    type: str                # official/international/market/news/academic/historical/open_data
    country: str             # ISO 国家代码
    authority: str           # 发布机构
    reliability: float       # 0-1 可信度评分
    update_frequency: str    # hourly/daily/weekly/monthly
    license: str             # 使用许可
    provenance: str          # 原始引用/URL
    created_at: float        # 注册时间
    last_updated: float      # 最后更新
    metadata: dict           # 额外元数据
```

### 8.2 Source Reliability Score

```python
# 动态可信度计算
def calculate_source_reliability(source: DataSource, historical_accuracy: float) -> float:
    base_score = source.reliability
    history_factor = historical_accuracy * 0.3  # 历史准确率权重 30%
    authority_factor = _authority_weight(source.authority)  # 机构权重
    return min(1.0, base_score + history_factor + authority_factor)
```

### 8.3 数据源分级

| 级别 | 类型 | 示例 | 权重 |
|------|------|------|------|
| A | Official | 央行报告、统计局、政府公报 | 1.0 |
| B | International | IMF、World Bank、UN | 0.9 |
| C | Financial | Bloomberg、Reuters | 0.85 |
| D | News | 主流媒体报道 | 0.7 |
| E | Academic | 期刊论文、研究报告 | 0.75 |
| F | Open Data | 开源数据集 | 0.6 |

---

## 9. World State Engine Design

### 9.1 Entity Schema

```python
@dataclass
class CountryState:
    state_id: str
    country_code: str
    snapshot_ts: float
    demographics: dict     # 人口结构
    economy: dict          # GDP、通胀、就业
    finance: dict          # 利率、汇率、流动性
    industry: dict         # 产业分布
    technology: dict       # 技术阶段
    energy: dict           # 能源结构
    military: dict         # 军事能力
    diplomacy: dict        # 外交关系
    trade: dict            # 贸易数据
    fiscal: dict           # 财政政策
    social: dict           # 社会指标
    confidence: float      # 综合置信度
    provenance: list       # 数据来源列表
    updated_at: float
```

### 9.2 时间维度支持

- ✅ 快照式存储 (每次更新为新记录)
- ✅ 时间序列回溯 (可查询历史状态)
- ✅ 变更追踪 (diff 当前 vs 上次)

### 9.3 更新触发条件

1. **定时更新**: 每天/每周/每月
2. **事件触发**: 重大政策发布、经济数据公布
3. **预测驱动**: 需要更新预测输入参数时

---

## 10. Historical Comparison Engine Design

### 10.1 比较框架

```
当前国家状态 → Feature Extraction → Historical Case Retrieval → Similarity Score
                                                         ↓
                                    Structural Difference Analysis
                                                         ↓
                                    Path Comparison (当前 vs 历史路径)
                                                         ↓
                                    Overall Similarity Score
```

### 10.2 特征维度

| 维度 | 特征 | 数据来源 |
|------|------|----------|
| 人口 | 年龄结构、增长率、城市化率 | 统计局 |
| 产业 | GDP 构成、支柱产业 | 国民经济核算 |
| 房地产 | 房价收入比、库存周期 | 房产数据 |
| 财政 | 赤字率、债务/GDP | 财政报告 |
| 金融 | 杠杆率、流动性 | 央行数据 |
| 国际环境 | 贸易关系、地缘政治 | 外交部 |
| 制度 | 治理指数、政策稳定性 | 国际组织 |
| 科技 | R&D 投入、专利数量 | 科技部 |

### 10.3 避免简单类比

❌ **错误**: "中国 = 日本 1990s"
✅ **正确**: "中国当前状态 ≈ 历史案例 A(40%) + 历史案例 B(35%) + 历史案例 C(25%)"

---

## 11. Causal Graph Design

### 11.1 最小模型

```python
@dataclass
class CausalNode:
    node_id: str
    name: str
    type: str      # variable/policy/outcome/indicator
    category: str
    description: str
    confidence: float

@dataclass
class CausalEdge:
    edge_id: str
    from_node: str
    to_node: str
    mechanism: str      # 因果机制描述
    sign: str           # positive/negative
    time_lag: float     # 时间延迟(天)
    confidence: float
    evidence: list      # 支持证据
```

### 11.2 支持的因果模式

- ✅ 一阶影响 (直接)
- ✅ 二阶影响 (间接)
- ✅ 三阶影响 (深度)
- ✅ 正反馈循环
- ✅ 负反馈循环
- ✅ 时间滞后效应
- ✅ 阈值效应

### 11.3 示例因果链

```
利率上升 (policy)
    ↓ [+3个月]
融资成本增加 (variable)
    ↓ [+1个月]
房地产投资下降 (outcome)
    ↓ [+6个月]
地方财政收缩 (variable)
    ↓ [+12个月]
就业压力上升 (outcome)
    ↓
居民收入下降 (outcome)
    ↓
消费信心下降 (outcome)
```

---

## 12. Multi-Agent Architecture Design

### 12.1 Analyst Council (分析委员会)

```
                    Global Foresight Engine
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    Intelligence     World State         Forecast
       Engine            Engine           Engine
              │               │               │
              ↓               ↓               ↓
           新闻/政策       国家状态        概率预测
           经济数据       指标时间序列    情景推演
           市场数据       实体关系        风险预警
           官方数据       因果图谱        预测验证
              │               │               │
              └───────────────┼───────────────┘
                              ↓
                        Analyst Council
                              │
            ┌─────────┬───────┼───────┬─────────┐
            │         │       │       │         │
        Macro    Geopolitics  Finance  Demographics  Technology
        Agent      Agent       Agent       Agent         Agent
            │         │       │       │         │
            └─────────┴───────┼───────┴─────────┘
                              ↓
                        Red Team Agent
                              │
                   Forecast Aggregator
                              │
                       Probability Engine
                              │
                       Forecast Ledger
                              │
                       Early Warning
```

### 12.2 Agent 定义模板

```python
@dataclass
class AnalystAgent:
    role: str                    # 角色名称
    scope: list[str]             # 管辖领域
    allowed_tools: list[str]     # 可用工具
    data_sources: list[str]      # 数据源白名单
    output_schema: dict          # 输出格式
    confidence_threshold: float  # 最低置信度
    known_bias: str              # 已知偏差
    prompt_template: str         # 专属提示词
```

### 12.3 核心 Agent 角色

| Agent | 领域 | 数据源 | 输出 |
|-------|------|--------|------|
| Macro Analyst | 宏观经济 | 央行、统计局、IMF | 经济周期判断 |
| Geopolitical Analyst | 地缘政治 | 外交、军事、国际组织 | 冲突风险评估 |
| Financial Analyst | 金融市场 | 交易所、 Bloomberg | 市场走势预测 |
| Demographic Analyst | 人口结构 | 统计局、UN | 人口趋势分析 |
| Technology Analyst | 科技创新 | 专利、论文、产业报告 | 技术突破预判 |
| Historical Analyst | 历史类比 | 历史数据库、研究 | 相似案例匹配 |
| Country Specialist | 国别研究 | 多源综合 | 综合国别报告 |
| Risk Analyst | 风险识别 | 全量数据 | 风险信号输出 |
| Red Team Agent | 反方论证 | 反对证据 | 挑战主预测 |
| Forecast Aggregator | 汇总整合 | 各 Agent 输出 | 综合预测 |

---

## 13. Forecast Architecture

### 13.1 Forecast Schema (量化强制)

```python
@dataclass
class Forecast:
    forecast_id: str
    question: str                  # 明确的问题陈述
    target: str                    # 目标变量
    created_at: float
    horizon: int                   # 预测周期(天)
    probability: float             # P(0-1)
    confidence: float              # 置信度(0-1)
    base_rate: float               # 基准率
    evidence: list[str]            # 支持证据
    assumptions: list[str]         # 关键假设
    alternative_scenarios: list[dict]  # 替代情景
    key_drivers: list[str]         # 关键驱动因素
    contradicting_evidence: list[str]  # 反驳证据
    resolution_criteria: str       # 验证标准
    resolution_date: float         # 验证日期
    actual_outcome: str            # 实际结果(验证后)
    score: float                   # Brier Score(验证后)
    created_by: str                # Agent 角色
    status: str                    # active/resolved/retracted
```

### 13.2 禁止模糊输出

❌ **禁止**: "我认为大概率会发生"
✅ **要求**: "未来12个月发生某事件的概率为 27%"

---

## 14. Forecast Ledger Design

### 14.1 评估指标

```python
@dataclass
class ForecastLedger:
    ledger_id: str
    forecast_id: str
    brier_score: float             # (predicted - actual)²
    log_loss: float                # -log(P)
    calibration: float             # 校准度
    bias: float                    # 偏差
    overconfidence: float          # 过度自信程度
    underconfidence: float         # 自信不足程度
    agent_accuracy: float          # 该 Agent 准确率
    domain_accuracy: float         # 该领域准确率
    country_accuracy: float        # 该国别准确率
    horizon_accuracy: float        # 该周期准确率
    resolved_at: float
```

### 14.2 统计维度

- ✅ Agent 准确率 (哪个分析师最准)
- ✅ 领域准确率 (哪个领域最难预测)
- ✅ 国家准确率 (哪个国家最稳定)
- ✅ 周期准确率 (短期 vs 长期)
- ✅ 数据源可靠性 (哪个信源最准)

---

## 15. Early Warning System Design

### 15.1 Signal 定义

```python
@dataclass
class RiskSignal:
    signal_id: str
    type: str                    # weak/trend/anomaly/correlation/突变的
    country: str
    indicator: str
    threshold: float
    current_value: float
    trend: str                   # accelerating/stable/declining
    persistence: int             # 持续周期数
    acceleration: float          # 加速度
    correlation: float           # 相关系数
    impact: str                  # low/medium/high
    probability: float           # 触发概率
    severity: float              # 严重程度
    confidence: float
    created_at: float
    resolved_at: float           # 如已解决
```

### 15.2 风险等级

| 等级 | 颜色 | 含义 | 响应 |
|------|------|------|------|
| NORMAL | 绿 | 正常范围 | 监控 |
| WATCH | 黄 | 关注 | 加强观测 |
| ELEVATED | 橙 | 升级 | 主动分析 |
| HIGH | 红 | 高危 | 预警通知 |
| CRITICAL | 紫 | 紧急 | 立即响应 |

---

## 16. Source Reliability Architecture

### 16.1 Source Reliability Score

```python
def calculate_reliability(source: DataSource) -> float:
    """综合可信度评分"""
    base = source.reliability
    history = source.historical_accuracy * 0.3
    authority = _authority_weight(source.authority)
    timeliness = _timeliness_score(source.update_frequency)
    return min(1.0, base + history + authority + timeliness)
```

### 16.2 数据源类型权重

| 类型 | 基础权重 |
|------|----------|
| official | 0.95 |
| international | 0.90 |
| financial | 0.85 |
| news | 0.70 |
| academic | 0.75 |
| historical | 0.65 |
| open_data | 0.60 |

---

## 17. Fact vs Inference vs Hypothesis vs Forecast vs Scenario

### 17.1 区分标准

| 类型 | 定义 | 示例 | 置信度 |
|------|------|------|--------|
| FACT | 可验证的真实 | "美国央行公布加息25bp" | 0.99 |
| INFERENCE | 基于事实的推论 | "该政策可能增加金融压力" | 0.70 |
| HYPOTHESIS | 待验证的假设 | "如果压力持续，可能触发反应" | 0.50 |
| FORECAST | 量化预测 | "未来12个月概率27%" | 0.37 |
| SCENARIO | 假设情景 | "如果A+B+C，概率升至44%" | 0.20 |

### 17.2 禁止行为

❌ **禁止**: 把推测伪装成事实
✅ **要求**: 明确标注推断层级

---

## 18. PHASE 137 Integration Principles

### 18.1 正确集成路径

```
GFE Task
    ↓
Task System
    ↓
Execution Request
    ↓
Existing Execution Pipeline (审批 → Runtime → ai_core.execution.run)
    ↓
Execution Observatory (查看)
    ↓
Audit System (审计)
```

### 18.2 禁止行为

❌ **禁止**:
```
GFE Engine → 直接调用 Runtime
GFE Engine → 绕过 Execution Request
GFE Engine → 自动 approve
```

---

## 19. S36 Self-Improvement Integration

### 19.1 现有 S36 能力

- ✅ run_cycle() — 自我改进周期
- ✅ 预测准确率分析
- ✅ Agent 权重优化
- ✅ Prompt 权重优化
- ✅ 数据源权重优化
- ✅ 错误模式识别

### 19.2 安全边界

```
GFE 自我改进流程:
    Analyze → Propose → Simulate → Validate → Approve → Apply
              ↑_________________________________________↓
              (保持当前自我改进的安全边界)
```

❌ **禁止**: S36 自动修改核心预测逻辑
✅ **允许**: S36 分析、建议、校准 (需人工审批)

---

## 20. Security & Safety Boundaries

### 20.1 硬性约束

1. **禁止**: GFE 直接调用 Runtime
2. **禁止**: GFE 绕过 Execution Request 执行
3. **禁止**: GFE 自动 approve (必须经审批)
4. **禁止**: GFE 修改 ai_core.execution.run
5. **禁止**: GFE 修改 planner/policy_engine
6. **禁止**: 新增第二执行入口
7. **禁止**: 新增第二 Runtime

### 20.2 验证机制

- ✅ Execution Bridge → AgentRuntime.run_chat_turn() (已有)
- ✅ 审计日志记录所有执行 (已有)
- ✅ Kill Switch 可取消 pending/approved 请求 (已有)
- ✅ Timeline 可追溯完整执行路径 (已有)

---

## 21. Required New Modules

| 模块 | 文件名 | 职责 |
|------|--------|------|
| World State Engine | `gfe_world_state.py` | 管理国家状态快照 |
| Data Ingestion | `gfe_ingestion.py` | 接入数据源、更新状态 |
| Historical Comparison | `gfe_historical.py` | 历史案例匹配、相似度计算 |
| Causal Graph | `gfe_causal_graph.py` | 因果网络构建、推理 |
| Analyst Council | `gfe_analysts.py` | 多 Agent 分析、输出聚合 |
| Forecast Engine | `gfe_forecast.py` | 概率预测生成、验证 |
| Forecast Ledger | `gfe_ledger.py` | 准确率统计、校准 |
| Early Warning | `gfe_warning.py` | 风险信号检测、预警 |
| Source Manager | `gfe_sources.py` | 数据源注册、可信度评分 |
| Event Subscribers | `gfe_events.py` | EventBus 订阅、事件处理 |

---

## 22. Modules That Must NOT Be Added

❌ **禁止**:
- 第二套 Runtime
- 绕过 Execution Request 的执行路径
- 修改 ai_core.execution.run
- 修改 planner
- 修改 policy_engine
- 新增独立的任务队列
- 绕过审批的执行入口

---

## 23. Dependency Graph

```
                    ┌─────────────────┐
                    │  GFE Engine     │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ World State  │  │ Historical   │  │ Causal Graph │
   │ Engine       │  │ Comparison   │  │              │
   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Analyst Council │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Forecast Engine │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │Forecast Ledger  │
                   │ (Self-Improve)  │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Early Warning   │
                   └─────────────────┘
                            │
                            ▼
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │Scheduler    │ │EventBus     │ │Execution    │
    │(周期任务)    │ │(事件驱动)    │ │Request      │
    └─────────────┘ └─────────────┘ └─────────────┘
                            │
                            ▼
              ┌─────────────────────┐
              │ Existing Execution  │
              │ System (PHASE 137)  │
              └─────────────────────┘
```

---

## 24. Recommended Development Phases

### 24.1 当前项目真实状态

根据已完成 Phase:
- PHASE 128-137 已完成 (Work Center + Execution Observatory)
- 下一个可用 Phase: 138

### 24.2 推荐 Phase 编号

| Phase | 主题 | 内容 |
|-------|------|------|
| 138 | Architecture Audit | ✅ 本 Phase 完成 |
| 139 | Data/Source Foundation | 数据源管理、Source Reliability |
| 140 | World State Engine | 国家状态存储、更新机制 |
| 141 | Event Intelligence | EventBus 集成、事件订阅 |
| 142 | Historical Comparison | 历史案例库、相似度计算 |
| 143 | Causal Graph | 因果网络构建、推理引擎 |
| 144 | Analyst Council | 多 Agent 分析、输出聚合 |
| 145 | Scenario Engine | 情景推演、假设分析 |
| 146 | Forecast Engine | 概率预测生成、验证流程 |
| 147 | Forecast Ledger | 准确率统计、校准算法 |
| 148 | Early Warning | 风险检测、预警系统 |
| 149 | S36 Calibration | 自我改进集成、模型优化 |
| 150 | GFE UI | 全局态势面板、预测展示 |
| 151 | Integration/E2E | 端到端测试、性能验证 |
| 152 | Production Acceptance | 生产环境部署、验收 |

---

## 25. Risks

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 数据源不可用 | 中 | 多源冗余、降级策略 |
| 预测偏差累积 | 高 | 定期校准、Brier Score 追踪 |
| Agent 同质化 | 中 | 多样化 prompt、独立训练 |
| 因果网络错误 | 高 | 人工审核、证据验证 |
| 性能瓶颈 | 中 | 异步处理、缓存策略 |
| 过度自动化 | 高 | 保持审批门控、Kill Switch |
| Memory 膨胀 | 中 | 定期清理、分层存储 |
| 信号噪声 | 中 | 置信度过滤、多重验证 |

---

## 26. Migration Strategy

### 26.1 分阶段迁移

```
Phase 139-140: 数据基础
  → 建立数据源管理、World State 存储
  → 不影响现有功能

Phase 141-143: 分析引擎
  → 事件订阅、历史对比、因果图
  → 纯新功能，无侵入

Phase 144-146: 预测系统
  → Agent Council、预测生成
  → 复用现有 Execution System

Phase 147-149: 校准系统
  → Ledger、Early Warning、S36
  → 基于已有数据进行优化

Phase 150-152: UI 与集成
  → 全局态势面板
  → E2E 测试、验收
```

### 26.2 关键里程碑

| 里程碑 | Phase | 验收标准 |
|--------|-------|----------|
| 数据基础就绪 | 140 | 至少 3 个数据源、World State 更新正常 |
| 分析引擎可用 | 143 | 历史案例匹配、因果推理可运行 |
| 预测系统成型 | 146 | 至少生成 10 条预测，有验证记录 |
| 预警系统运行 | 148 | 检测到真实风险信号 |
| 系统集成完成 | 151 | E2E 测试全部通过 |

---

## 27. Acceptance Criteria

### 27.1 Phase 138 完成标准 (已满足)

✅ 能够回答: "Global Foresight Engine 应该插在哪里?"
- 答案: 通过 Task System → Execution Request → 现有 Execution Pipeline

✅ 哪些现有能力直接复用?
- AgentRuntime、Scheduler、EventBus、Execution System、Audit System、Memory System

✅ 哪些必须新增?
- World State Engine、Historical Comparison、Causal Graph、Analyst Council、Forecast Engine、Early Warning

✅ 哪些地方绝对不能动?
- ai_core.execution.run、planner、policy_engine、Execution Bridge、Prediction System

✅ 未来如何避免形成第二套 Runtime/Execution/Memory?
- 所有 GFE 任务必须通过 Execution Request → Approval → Runtime 路径
- 所有 GFE 数据必须通过现有 EventBus 分发
- 所有 GFE 预测必须通过现有 Forecast Ledger 记录

✅ 如何保证预测可追溯、可验证、可校准?
- 每条预测记录 base_rate、evidence、assumptions、resolution_criteria
- 预测完成后计算 Brier Score、calibration、bias
- 定期触发 S36 自我改进流程进行校准

---

## 28. Summary

### 架构完整性

Xiao6 v1.0.0 已具备构建 Global Foresight Engine 的完整基础架构:

1. ✅ **执行系统完整**: Proposal → Approval → Execution → Timeline → Audit 闭环
2. ✅ **事件系统健全**: EventBus 支持 topic 维度 pub/sub
3. ✅ **调度系统可用**: Scheduler 支持周期/单次/事件驱动
4. ✅ **记忆系统可扩展**: Canonical Memory + Episodic Memory + Vector Search
5. ✅ **API 体系完善**: REST API + SSE 实时推送
6. ✅ **安全边界清晰**: Kill Switch + Audit Trail + Approval Gate

### 关键设计原则

1. **复用而非重建**: 所有 GFE 任务通过现有 Execution System 执行
2. **单一入口**: 禁止绕过 ai_core.execution.run
3. **审批门控**: 禁止自动 approve
4. **可追溯**: 每条预测都有完整证据链
5. **可校准**: 定期验证、统计准确率、自我优化

### 下一步行动

Phase 139 开始实施 Data/Source Foundation，建议:
1. 创建 gfe_sources 表
2. 实现 DataSource 管理 API
3. 添加 3-5 个初始数据源
4. 编写 E2E 测试验证数据管道

---

**PHASE 138 COMPLETE / BLOCKED**

*本报告为 READ-ONLY 审计，未修改任何生产代码。*
*Git 状态: 保持 clean 或仅含 PHASE 137 的修改。*
