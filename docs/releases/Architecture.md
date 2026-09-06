# Xiao6 v1.0.0 Architecture

**Document Version**: 1.0.0  
**Last Updated**: 2026-09-06  

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      UI Layer                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Dashboard │  │   Chat   │  │Work Center│  │Insight   │   │
│  │          │  │          │  │          │  │Center    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────┤
│                   Intelligence Center                       │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│  │  Feed   │ │ Foresight│ │  Context │ │   Reasoning   │   │
│  │  +Rank  │ │  Engine  │ │  Engine  │ │    Engine     │   │
│  └─────────┘ └──────────┘ └──────────┘ └───────────────┘   │
│  ┌──────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────┐  │
│  │ Decision │ │  Prediction  │ │  Learning  │ │  Center │  │
│  │  Engine  │ │   Ledger     │ │   Engine   │ │ Engine  │  │
│  └──────────┘ └──────────────┘ └────────────┘ └─────────┘  │
├─────────────────────────────────────────────────────────────┤
│                   Agent Runtime                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Planner   │  │ ToolExecution│  │   Intelligence   │   │
│  │             │  │              │  │      Registry     │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Memory  │  │ Knowledge│  │  Goals   │  │  Tasks   │   │
│  │(USER.MD)│  │ (SQLite) │  │          │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────┤
│                   Tool System                               │
│  63 tools mounted via local MCP server                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### Agent Runtime

**职责**：核心执行引擎

- `Planner` — 任务规划与分解
- `ToolExecution` — 工具执行与结果处理
- `IntelligenceRegistry` — 能力注册中心

**约束**：v1.0.0 架构冻结，禁止修改

---

### Intelligence Center

**职责**：统一洞察、分析、推理、决策

**模块列表**：

| 模块 | 文件 | 职责 |
|------|------|------|
| Feed | `intelligence_feed.py` | 统一洞察入口，Ranking 排序 |
| Foresight | `foresight_engine.py` | 趋势检测，早期预警 |
| Context | `intelligence_context.py` | 关联分析，关系映射 |
| Reasoning | `intelligence_reasoning.py` | 推理引擎，证据链 |
| Decision | `intelligence_decision.py` | 决策辅助，选项分析 |
| Prediction | `intelligence_prediction.py` | 预测账本，验证记录 |
| Learning | `intelligence_learning.py` | 学习反馈，经验积累 |
| Center | `intelligence_center.py` | 聚合层，完整快照 |

**数据流**：

```
World Model → Feed → Foresight → Context
                                      ↓
                              Reasoning → Decision
                                      ↓
                            Prediction → Learning
                                      ↓
                               Center (Snapshot)
```

---

### Memory

**职责**：用户记忆与个人配置

**存储**：
- `MEMORY.md` — 持久化记忆
- `USER.md` — 用户档案

**API**：
- `GET /api/memory` — 记忆列表
- `POST /api/memory` — 添加记忆

---

### Knowledge

**职责**：结构化知识图谱

**存储**：SQLite 数据库

**规模**：
- 330 节点
- 112 关系

**API**：
- `GET /api/knowledge` — 知识图谱
- `POST /api/knowledge` — 添加知识

---

### Tool System

**职责**：本地工具注册与执行

**规模**：63 工具挂载

**工具类别**：
- 文件系统：file_read, file_write, file_list, file_delete
- 系统管理：run_shell, list_processes, kill_process
- 网络：web_fetch, web_search, browser_read
- 媒体：media_generate, asr_transcribe, play_video
- 日程：reminder_set, reminder_list, set_task, complete_task
- 工具管理：list_skills, use_skill, create_custom_tool
- AI：delegate_agent, render_card

---

### UI

**职责**：用户界面与交互

**架构**：
- 单页应用（SPA）
- 侧边栏导航
- 模块化面板

**主要模块**：
- Dashboard — 首页概览
- Chat — 对话界面
- Work Center — 任务管理
- Knowledge — 知识库
- Memory — 记忆管理
- AI Insight Center — 智能洞察中心（7 Tabs）

**AI Insight Center Tabs**：
1. [洞察] — Feed + Ranking
2. [趋势] — Foresight
3. [关联] — Context
4. [推理] — Reasoning
5. [决策] — Decision
6. [预测] — Prediction
7. [学习] — Learning

---

## Constraints

### Architecture Freeze (S143.5)

禁止修改：
- AgentRuntime
- Planner
- ToolExecution
- Memory Schema
- Knowledge Schema

禁止创建：
- 新数据库
- 新执行入口
- 新模型参数

允许：
- 新增 Intelligence 子模块（只读聚合）
- 扩展 UI 展示
- 优化 API 响应

---

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 1.0.0 | 2026-09-06 | Initial release, Intelligence Center complete |