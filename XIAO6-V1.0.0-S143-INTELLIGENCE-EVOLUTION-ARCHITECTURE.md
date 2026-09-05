# Xiao6 v1.0.0 — S143 Intelligence Evolution Architecture

**HEAD**: 4356d65  
**VERSION**: 1.0.0  
**TAG**: v1.0.0  
**DATE**: 2026-09-06  
**PHASE**: S143 Intelligence Evolution Planning

---

## 一、Current Baseline

### 1.1 版本信息

| 项目 | 值 |
|------|-----|
| Version | 1.0.0 |
| HEAD | 4356d65 |
| TAG | v1.0.0 |
| Worktree | G:/xiao6 |

### 1.2 当前能力基线

```
Runtime:       READY
Tools:         63 total, 63 implemented
Capabilities:  33 total
  READY:       20
  PARTIAL:     2
  BLOCKED:     5
  NOT_IMPL:    6

Memory:        READY (125 entries, 35 notes, 24 logs)
Knowledge:     READY (330 docs, 112 relations)
Goals:         READY (50 goals)
Tasks:         READY (50 tasks)
Perception:    READY (Screen 2560x1440, 9 Windows)
GFE:           READY (sources, dashboard, risk_index)

TTS:           BLOCKED (GPT-SoVITS not deployed)
```

### 1.3 已验证状态

- S141 Release Hardening ✅ COMPLETE
- S142 Product Experience Closure ✅ COMPLETE
- Runtime Consistency ✅ VERIFIED
- Capability Truth ✅ VERIFIED
- API Health ✅ VERIFIED

### 1.4 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                    Xiao6 v1.0.0                         │
├─────────────────────────────────────────────────────────┤
│  UI Layer    │  index.html, js/app.js, css/            │
├─────────────────────────────────────────────────────────┤
│  API Layer   │  server.py (port 8000)                   │
│              │  /api/* routes with path hints          │
├─────────────────────────────────────────────────────────┤
│  Agent       │  AgentRuntime, capability_os            │
│  Layer       │  EventBus, Policy Engine                 │
├─────────────────────────────────────────────────────────┤
│  Data Layer  │  xiao6.db (SQLite)                      │
│              │  knowledge/ (markdown)                  │
├─────────────────────────────────────────────────────────┤
│  Tools       │  63 tools mounted                       │
└─────────────────────────────────────────────────────────┘
```

---

## 二、Evolution Vision

### 2.1 当前范式

```
用户请求 → Agent 执行 → 返回结果
User Request → Agent Execute → Response
```

**局限**：被动响应，无预测，无主动智能

### 2.2 目标范式

```
Observe → Understand → Reason → Predict → Recommend → Act
 └─────────────────────────────────────────────────────┘
              闭环增强（Feedback Loop）
```

### 2.3 Xiao6 定位升级

| 维度 | v1.0.0 | v2.0.0 (目标) |
|------|--------|---------------|
| 响应模式 | 被动请求 | 主动推荐 |
| 记忆系统 | 静态存储 | 重要性评估+衰减 |
| 知识系统 | 文档库 | 图谱推理 |
| 感知能力 | 屏幕/窗口 | 环境理解 |
| 决策能力 | 规则执行 | 因果推理 |
| 预测能力 | 无 | 趋势预测 |
| 学习能力 | 无 | 持续优化 |

---

## 三、Memory Intelligence Architecture

### 3.1 设计目标

将 Memory 从"存储系统"升级为"智能记忆系统"，具备：
- 重要性评估（Importance Scoring）
- 自然衰减（Memory Decay）
- 知识巩固（Consolidation）

### 3.2 Memory Importance 模型

```python
# 重要性评分公式
importance = base_score × time_factor × relevance_factor × emotion_factor

base_score:
  - user_explicit: 10 (用户明确标记)
  - high_frequency: 8 (高频访问)
  - core_context: 6 (核心上下文)
  - daily_log: 3 (日常日志)
  - transient: 1 (临时信息)

time_factor:
  - < 1 day: 1.5
  - 1-7 days: 1.0
  - 7-30 days: 0.8
  - > 30 days: 0.5

relevance_factor:
  - directly_related: 1.2
  - indirectly_related: 1.0
  - unrelated: 0.7

emotion_factor:
  - positive: 1.1
  - negative: 1.3 (负面记忆更持久)
  - neutral: 1.0
```

### 3.3 Memory Categories

| 类型 | 说明 | 保留策略 |
|------|------|----------|
| **Core** | 用户核心信息（偏好、项目、身份） | 永久保留 |
| **Active** | 当前任务相关 | 保留30天 |
| **Context** | 历史上下文 | 保留7天 |
| **Transient** | 临时会话数据 | 保留1天 |
| **Archive** | 归档历史记录 | 永久保留 |

### 3.4 Memory Decay 机制

```
时间衰减曲线：

importance(t) = importance(0) × e^(-λt)

λ (decay rate):
  - Core memories: 0.001 (极慢衰减)
  - Active memories: 0.1 (快速衰减)
  - Transient memories: 1.0 (立即衰减)

threshold:
  - < 0.1: 标记为待清理
  - < 0.01: 自动归档
  - = 0: 删除（仅Transient类型）
```

**保护规则**：
- Core 类型记忆永不衰减
- 用户手动标记的记忆永不衰减
- 负面情绪相关的记忆衰减减半

### 3.5 Memory Consolidation 流程

```
周期：每周日凌晨 2:00

Step 1: Fragment Collection
  - 收集过去一周的碎片记忆
  - 按主题聚类

Step 2: Summary Generation
  - LLM 生成摘要
  - 提取关键洞见

Step 3: Knowledge Migration
  - 重要摘要迁移到 Knowledge
  - 原始碎片标记为已归档

Step 4: Relationship Building
  - 建立新记忆与现有知识的关联
  - 更新知识图谱

Step 5: Cleanup
  - 清理已 consolidted 的碎片
  - 归档到 archive/ 目录
```

---

## 四、Knowledge Intelligence Architecture

### 4.1 设计目标

将 Knowledge 从"文档库"升级为"智能知识系统"，具备：
- 自动摘要
- 自动关联
- 知识图谱增强
- 主动推荐

### 4.2 Knowledge Pipeline

```
┌─────────────┐
│   Input     │  markdown / api / import
└──────┬──────┘
       ↓
┌─────────────┐
│ Ingestion   │  parsing, cleaning, validation
└──────┬──────┘
       ↓
┌─────────────┐
│ Extraction  │  entities, topics, relationships
└──────┬──────┘
       ↓
┌─────────────┐
│  Embedding  │  text → vector (future)
└──────┬──────┘
       ↓
┌─────────────┐
│   Graph     │  node-edge storage
└──────┬──────┘
       ↓
┌─────────────┐
│  Reasoning  │  inference, correlation
└──────┬──────┘
       ↓
┌─────────────┐
│ Recommendation│  active suggestions
└─────────────┘
```

### 4.3 Auto-Summary

```python
# 触发条件
- 文档长度 > 1000 字
- 文档更新超过 7 天
- 用户手动请求

# 输出格式
{
  "summary": "200字摘要",
  "key_points": ["要点1", "要点2", ...],
  "entities": ["实体1", "实体2", ...],
  "topics": ["主题1", "主题2", ...],
  "confidence": 0.85
}
```

### 4.4 Auto-Association

```
关联类型：
1. Semantic (语义关联)
   - 基于内容相似性
   - threshold: cosine_similarity > 0.7

2. Temporal (时间关联)
   - 同一时间段创建的文档
   - 周期性事件

3. Causal (因果关联)
   - 文档A提到文档B的结果
   - 需人工确认或高置信度LLM判断

4. Hierarchical (层级关联)
   - 父子文档关系
   - 整体-部分关系
```

### 4.5 Active Recommendation

```
推荐场景：
1. 用户查询相关文档时，推荐关联知识
2. 新文档入库时，推荐可能需要的背景知识
3. 用户任务执行中，主动推送相关知识

禁止：
- 无关推荐
- 过度推送（threshold: importance < 0.5 不推荐）
- 干扰用户工作流
```

---

## 五、GFE 2.0 Architecture

### 5.1 当前状态

```
GFE (Global Foresight Engine):
- sources: 新闻源采集
- dashboard: 数据展示
- risk_index: 风险指数
```

### 5.2 World Model

```
World Model 实体类型：

1. Nation (国家)
   - 经济指标
   - 政策变化
   - 外交关系

2. Enterprise (企业)
   - 财务状况
   - 市场动态
   - 管理层变动

3. Technology (技术)
   - 技术趋势
   - 专利动态
   - 研发投入

4. Market (市场)
   - 行业报告
   - 竞争格局
   - 消费者行为

5. Policy (政策)
   - 法规变化
   - 监管动态
   - 标准更新

6. Event (事件)
   - 重大事件
   - 危机事件
   - 里程碑事件
```

### 5.3 Event Graph

```
节点：Event (事件)
边：
  - CAUSES (导致)
  - AFFECTS (影响)
  - CORRELATES (相关)
  - PRECEDES (precede)
  - CONSEQUENCE (后果)

示例：
[美联储加息] --CAUSES--> [美元走强]
[美元走强] --AFFECTS--> [新兴市场资本外流]
[新兴市场资本外流] --CONSEQUENCE--> [货币贬值]
```

### 5.4 Causal Reasoning

```python
# 因果推理流程
def causal_chain(start_event, depth=3):
  chain = []
  current = start_event
  
  for i in range(depth):
    effects = find_effects(current)  # 查找直接效应
    if not effects:
      break
    
    # 计算因果强度
    for effect in effects:
      strength = calculate_causal_strength(current, effect)
      chain.append({
        "from": current,
        "to": effect,
        "strength": strength,
        "time_lag": estimate_time_lag(current, effect)
      })
    
    # 选择最强效应继续
    current = max(effects, key=lambda e: e["strength"])
  
  return chain
```

**要求**：
- 不是新闻总结，而是因果分析
- 需要标注置信度
- 需要时间维度

### 5.5 Prediction Ledger

```
记录格式：
{
  "prediction_id": "pred_20260906_001",
  "timestamp": "2026-09-06T10:00:00Z",
  "event": "预测事件描述",
  "basis": ["依据1", "依据2"],
  "probability": 0.75,
  "time_horizon": "30天",
  "confidence": "high",
  "status": "pending",  # pending/confirmed/refuted
  "result": null,
  "error": null,
  "updated_at": null
}
```

**用途**：
- 持续优化预测能力
- 校准概率模型
- 学习历史错误

### 5.6 Early Warning System

```
预警触发条件：

1. Risk Pattern
   - 风险指标超过阈值
   - 多个风险信号同时出现

2. Trend Anomaly
   - 趋势突然变化
   - 与历史模式偏离

3. Correlation Break
   - 历史强相关变量突然脱钩
   - 预示潜在危机

4. Cascade Detection
   - 事件链传播速度异常
   - 影响范围扩大
```

---

## 六、Proactive Intelligence Architecture

### 6.1 Observation Loop

```
观察维度：
1. Time (时间)
   - 定时检查任务状态
   - 周期提醒

2. Task (任务)
   - 任务进度跟踪
   - 阻塞检测

3. Knowledge (知识)
   - 新文档入库
   - 关联知识更新

4. World (世界变化)
   - GFE 数据更新
   - 外部事件监测
```

### 6.2 Suggestion Engine

```python
# 建议生成逻辑
def generate_suggestion(observation):
  # 1. 计算重要性
  importance = calculate_importance(observation)
  
  # 2. 检查阈值
  if importance < IMPORTANCE_THRESHOLD:
    return None  # 不生成建议
  
  # 3. 生成建议
  suggestion = {
    "type": observation.type,
    "content": generate_content(observation),
    "priority": importance,
    "action": suggest_action(observation),
    "reasoning": explain_reasoning(observation)
  }
  
  # 4. 防骚扰检查
  if is_annoying(suggestion):
    return None
  
  return suggestion
```

**Importance Threshold**:
- 仅当 importance >= 0.7 时推送
- 低于此阈值的观察记录但不推送

**Anti-Harassment Rules**:
- 同一主题 24 小时内最多推送一次
- 用户忽略后 7 天内不再推送同类
- 每日最大推送数量限制

### 6.3 Proactive Scenarios

| 场景 | 触发条件 | 行动 |
|------|----------|------|
| Task Stalled | 任务超过预计时间未完成 | 提醒并询问是否需要帮助 |
| New Relevant Knowledge | 新知识与当前任务相关 | 主动推荐 |
| Risk Detected | GFE 检测到风险 | 预警通知 |
| Pattern Recognition | 发现用户行为模式 | 优化建议 |

---

## 七、Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                             │
│  User Request ──┐                                               │
│  External Events├──→ EventBus ──→ Agent Runtime ──→ Tool Calls │
│  Scheduled Jobs ─┘                    │                         │
└───────────────────────────────────────┼─────────────────────────┘
                                        │
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
                ▼                       ▼                       ▼
┌───────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│     MEMORY SYSTEM     │  │    KNOWLEDGE SYSTEM  │  │     GFE SYSTEM      │
│                       │  │                     │  │                     │
│ • Importance Score    │  │ • Auto Summary      │  │ • World Model       │
│ • Decay Mechanism     │  │ • Auto Association  │  │ • Event Graph       │
│ • Consolidation       │  │ • Active Rec        │  │ • Causal Reasoning  │
└───────────┬───────────┘  └──────────┬──────────┘  └──────────┬──────────┘
            │                          │                        │
            │                          │                        │
            └──────────────────────────┼────────────────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────┐
                          │   PROACTIVE ENGINE      │
                          │                         │
                          │ • Observation Loop      │
                          │ • Suggestion Engine     │
                          │ • Warning System        │
                          └───────────┬─────────────┘
                                      │
                                      ▼
                          ┌─────────────────────────┐
                          │     USER INTERFACE      │
                          │                         │
                          │ • Recommendations       │
                          │ • Warnings              │
                          │ • Suggestions           │
                          └─────────────────────────┘
```

---

## 八、Module Boundary

### 8.1 现有模块（复用）

| 模块 | 文件 | 职责 | 复用方式 |
|------|------|------|----------|
| AgentRuntime | agent_runtime.py | 主循环执行 | 保持现状 |
| CapabilityOS | capability_os/ | 能力管理 | 保持现状 |
| Memory | memory.py | 记忆存储 | 扩展intelligence层 |
| Knowledge | knowledge.py | 知识管理 | 扩展pipeline层 |
| GFE | gfe_*.py | 全球洞察 | 扩展2.0功能 |
| PolicyEngine | automation_policy.py | 策略执行 | 保持现状 |
| EventBus | event_bus.py | 事件总线 | 保持现状 |

### 8.2 新增模块

| 模块 | 文件 | 职责 | 依赖 |
|------|------|------|------|
| MemoryIntelligence | memory_intelligence.py | 重要性/衰减/巩固 | Memory, LLM |
| KnowledgePipeline | knowledge_pipeline.py | 摘要/关联/推荐 | Knowledge, LLM |
| GFE2.0 | gfe_2.0.py | World Model/因果推理 | GFE, LLM |
| ProactiveEngine | proactive_engine.py | 观察/建议引擎 | EventBus, 所有系统 |
| PredictionLedger | prediction_ledger.py | 预测记录/校准 | GFE 2.0 |

### 8.3 禁止事项

- ❌ 新建第二个 AgentRuntime
- ❌ 新建第二个 Memory System
- ❌ 新建第二个 Knowledge System
- ❌ 绕过 Policy Engine
- ❌ 创建新的执行入口

---

## 九、Implementation Roadmap

### Phase 1: Foundation (2-3 weeks)

**目标**：建立 Intelligence 基础架构

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 1.1 | Memory Importance 评分实现 | P0 |
| 1.2 | Memory Decay 机制实现 | P0 |
| 1.3 | Knowledge Auto-Summary API | P1 |
| 1.4 | GFE World Model 数据模型 | P1 |
| 1.5 | EventBus 扩展支持新事件类型 | P1 |

**验收标准**：
- Memory 系统具有重要性评分
- Knowledge 可自动生成摘要
- GFE 存储世界模型数据

### Phase 2: Intelligence (3-4 weeks)

**目标**：实现核心 Intelligence 功能

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 2.1 | Memory Consolidation 流程 | P0 |
| 2.2 | Knowledge Auto-Association | P0 |
| 2.3 | GFE Event Graph 实现 | P1 |
| 2.4 | GFE Causal Reasoning | P1 |
| 2.5 | Prediction Ledger 实现 | P2 |
| 2.6 | Proactive Engine 基础 | P2 |

**验收标准**：
- 每周自动 Consolidation 运行
- 知识关联自动建立
- 事件因果关系可查询
- 预测可记录

### Phase 3: Polish (2-3 weeks)

**目标**：优化体验，完善功能

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 3.1 | GFE Early Warning System | P0 |
| 3.2 | Proactive Suggestion UI | P1 |
| 3.3 | Prediction Calibration | P2 |
| 3.4 | Anti-Harassment 优化 | P2 |
| 3.5 | Performance Tuning | P2 |

**验收标准**：
- 预警准确率达到基准
- 建议质量用户反馈正面
- 系统响应时间无明显下降

---

## 十、Risk Analysis

### 10.1 技术风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| LLM 调用成本 | 高 | 中 | 本地模型优先，云端备用 |
| 记忆数据丢失 | 低 | 高 | 定期备份，Consolidation前快照 |
| 系统复杂度增加 | 中 | 中 | 严格模块边界，接口隔离 |
| 性能下降 | 中 | 中 | 异步处理，缓存优化 |

### 10.2 产品风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 主动建议打扰用户 | 高 | 高 | 严格的 importance threshold |
| 预测准确率不足 | 中 | 中 | 明确标注置信度，避免过度信任 |
| 知识关联错误 | 中 | 低 | 人工审核通道，可修正 |

### 10.3 架构风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 模块耦合增加 | 中 | 高 | 依赖注入，接口隔离 |
| 数据一致性 | 低 | 高 | 事务处理，备份恢复 |
| 向后兼容 | 低 | 中 | API 版本控制 |

---

## 十一、Success Criteria

### 11.1 量化指标

| 指标 | 当前 | 目标 (Phase 3后) |
|------|------|------------------|
| 记忆重要性评分覆盖率 | 0% | 100% |
| 知识自动摘要覆盖率 | 0% | 80% |
| 知识关联自动率 | 0% | 60% |
| 预测记录数 | 0 | >100 |
| 预测准确率 | N/A | >60% |
| 主动建议采纳率 | N/A | >30% |
| 用户骚扰投诉 | N/A | 0 |

### 11.2 定性指标

- [ ] Memory 系统智能化程度提升
- [ ] Knowledge 系统自动维护
- [ ] GFE 具备因果推理能力
- [ ] 用户收到有价值的主动建议
- [ ] 系统响应时间无明显下降
- [ ] 架构保持清晰，可维护性不降低

---

## 十二、Summary

### 设计完成状态

```
================================
Xiao6 v1.0.0
S143 Intelligence Evolution Architecture
================================

Design Status: COMPLETE

Architecture:
  - Memory Intelligence: ✅ Designed
  - Knowledge Intelligence: ✅ Designed
  - GFE 2.0: ✅ Designed
  - Proactive Intelligence: ✅ Designed

Constraints:
  - No second runtime: ✅ Enforced
  - No second memory: ✅ Enforced
  - No second knowledge: ✅ Enforced
  - Reuse existing modules: ✅ Enforced

Roadmap:
  - Phase 1: Foundation (2-3 weeks)
  - Phase 2: Intelligence (3-4 weeks)
  - Phase 3: Polish (2-3 weeks)

Next Step:
  - Implementation can begin after approval
================================
```

---

**报告生成完成**
