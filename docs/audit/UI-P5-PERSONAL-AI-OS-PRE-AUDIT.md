# UI-P5 Personal AI OS Context & Capability Pre-Audit 报告

**Date**: 2026-09-06  
**Base**: d9ede79 (UI-P4)  
**VERSION**: 1.0.0  
**Constraint**: 只读审计，不修改代码  

---

## 一、当前架构概览

```
                    ┌─────────────────────────────┐
                    │     首页 (Home View)         │
                    │  ┌───────────┬────────────┐ │
                    │  │  Left     │   Right    │ │
                    │  │  Today    │  Agent     │ │
                    │  │  Card     │  Activity  │ │
                    │  │           │   Center   │ │
                    │  │ ───────── │ ────────── │ │
                    │  │ Weather   │ acLive     │ │
                    │  │ Tasks     │ (常驻)     │ │
                    │  │ Schedule  ├────────────┤ │
                    │  │ Quick     │ acInsight  │ │
                    │  │ Actions   │ (可折叠)   │ │
                    │  │           ├────────────┤ │
                    │  └───────────┴ acHealth   │ │
                    │                           │acForesight│
                    │                           │(可折叠)  │
                    └───────────────────────────┘
                         ↑              ↑
                    /api/tasks      /api/interaction/activity
                    /api/weather    /api/intelligence/feed
                    /api/hotspots   /api/intelligence/foresight
```

---

## 二、Task 1 — Context Awareness 审计

### 后端 API 检查

| Endpoint | 状态 | 说明 |
|----------|------|------|
| `/api/intelligence/context` | ✅ 存在 | Context Engine 返回上下文数据 |
| `/api/intelligence/center/status` | ✅ 存在 | 所有 Intelligence 模块 active |
| `/api/memory` | ✅ 存在 | 用户画像 + 记忆摘要 |
| `/api/active_context` | ❌ 不存在 | 无"当前上下文"独立端点 |

### 当前 UI 展示

**✅ 已展示：**
- 系统健康状态（acHealth）
- 主动洞察（acInsight）
- 未来关注（acForesight）
- Agent 运行状态（aaTitle, aaSteps）

**❌ 未展示：**
- **当前上下文感知**：无 "Agent 正在处理什么主题/任务" 的可视化
- **当前目标**：50 个 Goals 存在于后端，但首页无任何展示
- **Memory 摘要**：35 条笔记、23 条日志存在于后端，但首页无入口
- **能力概览**：capabilities 仅在 Settings 页展示，首页无入口

### 数据缺口

```python
# Context Engine 已有但首页未消费
context_engine.get_contexts(limit=20)
# 返回: topics, entities, relations, importance

# Memory 已有但首页未消费
/api/memory
# 返回: profile (5条), note_count=35, log_count=23, summary

# Goals 已有但首页未消费
/api/goals
# 返回: 50 items (active=2, completed=8, archived=...)
```

---

## 三、Task 2 — Memory Awareness 审计

### API 数据验证

```json
GET /api/memory
{
  "profile": [
    {"key": "习惯", "value": "桌面路径为 F:\\桌面"},
    {"key": "偏好", "value": "不希望表情被读出来"},
    {"key": "称呼", "value": "小6"},
    {"key": "项目", "value": "连续任务稳定性测试"},
    {"key": "领域", "value": "EventBus、Memory、Runtime..."}
  ],
  "note_count": 35,
  "log_count": 23,
  "summary": "1. 身份：Agnes...\n2. 工具链与验证..."
}
```

### 当前 UI 消费位置

| 数据 | 消费位置 | 首页可见性 |
|------|----------|------------|
| `/api/memory` | Settings > Memory 页 | ❌ 不可见 |
| `/api/knowledge` | Settings > Knowledge 页 | ❌ 不可见 |
| `/api/notes` | Memory 页 (Obsidian 风格) | ❌ 不可见 |
| profile summary | 无 | ❌ 不可见 |

### UI 缺口分析

```
缺口 1: 首页无 Memory 摘要入口
  - 用户无法快速了解"小6记住了什么"
  - profile (5条) 是 AI 理解用户的关键信号

缺口 2: 今日 Card 未融合记忆上下文
  - taskCard() 只显示任务列表
  - 未关联到 goal 或 memory context

缺口 3: Agent 工作模式无记忆来源展示
  - aaSteps 只显示"正在调用 X 工具"
  - 不显示"基于 Y 记忆/Z 知识"
```

---

## 四、Task 3 — Goal Center 审计

### API 数据验证

```json
GET /api/goals → list (50 items)
[
  {"id": 77, "title": "R1B契约验证...", "status": "completed", "progress": 100},
  {"id": 6, "title": "GUI链路验证-可忽略", "status": "active", ...},
  {"id": 5, "title": "p44_080c460456 goal-B", "status": "active", ...}
]

GET /api/tasks → list (50+ items)
[{"id": 252, "title": "恢复停滞任务", "status": "pending", ...}]
```

### 数据关系

```
Goal (50个)
├── active: 2个
├── completed: 8个
├── archived: 多个
└── TODO: 其他状态

Task (50+个)
├── pending: 多个
├── running: 少数
└── completed: 多个
```

### 当前 UI 消费位置

| 数据 | 消费位置 | 首页可见性 |
|------|----------|------------|
| `/api/goals` | Settings > Goals 页 | ❌ 不可见 |
| `/api/tasks` | Today Card taskCard() | ⚠️ 仅显示 running 状态 |
| task 与 goal 关联 | 无 | ❌ 未建立 |

### Today Card 改造建议

**现状：**
```
Today Card
├── Weather
├── Tasks (running only)
└── Schedule
```

**升级方案：**
```
Today Card → Today Center
├── Weather
├── Active Goals (最多 3 个)
│   └── 进度条 + 关联任务数
├── Tasks (running + today's)
└── Memory Summary (最近 2 条)
```

### Goal Center 改造建议

**新增首页区块：`acGoals`**
```html
<section class="ac-section collapsible" id="acGoals">
  <div class="ac-sec-head">
    <span class="ac-ico">🎯</span>
    <span>当前目标</span>
    <span class="ac-badge active">2</span>
    <span class="ac-caret">▾</span>
  </div>
  <div class="ac-sec-body" id="acGoalsBody">
    <!-- 从 /api/goals 读取 active goals -->
  </div>
</section>
```

---

## 五、Task 4 — Capability OS 审计

### API 数据验证

```json
GET /api/capability_os/catalog
{
  "total": 33,
  "available": 27,
  "groups": {
    "Voice": [...],
    "Memory": [...],
    "Knowledge": [...],
    "Tools": [...],
    "Agent": [...]
  }
}

GET /api/capabilities
{
  "ok": true,
  "count": 3,
  "items": [
    {"id": "hotspot", "label": "热点上下文", ...},
    {"id": "prefetch", "label": "预取背景", ...}
  ]
}
```

### 当前 UI 消费位置

| 数据 | 消费位置 | 首页可见性 |
|------|----------|------------|
| `/api/capability_os/catalog` | Settings > Capabilities 页 | ❌ 不可见 |
| `/api/capabilities` | 无消费 | ❌ 未实现 |
| `/api/tools/list` | systemCard() 显示数量 | ⚠️ 仅数字，无详情 |

### 用户价值展示缺口

**现状：**
```
systemCard() 输出：
"⚙️ 系统状态"
"63 个工具已挂载" ← 纯数字，无价值描述
```

**升级方案：**
```
新增首页区块：acCapabilities

┌──────────────────────────────────┐
│ 🛠️ 核心能力                      │
├──────────────────────────────────┤
│ 🎙️ 语音识别  ✅ TTS 配置中       │
│ 🧠 长期记忆  ✅ 35 条笔记        │
│ 📚 知识库    ✅ 330 文档         │
│ 🔍 意图理解  ✅ S144 就绪        │
│ ⚡ 主动智能  ✅ 4 观察源         │
└──────────────────────────────────┘
```

---

## 六、Task 5 — UI 架构审计

### 当前首页布局

```
┌─────────────────────────────────────────────┐
│  [Sidebar]      [Home Content]             │
│             ┌─────────────┬─────────────┐  │
│             │    Left     │   Right     │  │
│             │  Today Card │ Agent Center│  │
│             ├─────────────┼─────────────┤  │
│             │ Weather     │ acLive      │  │
│             │ Tasks       │ (常驻)      │  │
│             │ Schedule    ├─────────────┤  │
│             │ Quick       │ acInsight   │  │
│             │ Actions     │ (🔮)        │  │
│             └─────────────┴ acHealth    │  │
│                               (⚙️)      │  │
│                               ├─────────┤  │
│                               │acForesight│
│                               │ (📊)     │  │
│                               └─────────┘  │
└─────────────────────────────────────────────┘
```

### 推荐新增区域位置

**推荐 A：Home Context Bar（顶部）**
```
┌─────────────────────────────────────────────┐
│ [Context Bar: 当前目标 + 活跃记忆 + 能力概览] │  ← 新增
├─────────────────────────────────────────────┤
│  [Sidebar]      [Home Content]             │
└─────────────────────────────────────────────┘
```

**推荐 B：Agent Center 扩展（右侧）**
```
右侧 Agent Center 新增区块：
├── acLive (现有)
├── acGoals (新增)     ← 🎯 当前目标
├── acMemory (新增)    ← 🧠 记忆摘要
├── acInsight (现有)
├── acHealth (现有)
└── acForesight (现有)
```

**推荐 C：Today Card 扩展（左侧）**
```
Today Card 升级为 Today Center：
├── Weather
├── Active Goals       ← 新增
├── Tasks
├── Schedule
└── Quick Actions
```

---

## 七、P5 实施方案

### 优先级排序

| 优先级 | 任务 | 预估工作量 | 风险 |
|--------|------|-----------|------|
| P0 | acGoals 区块 | 2h | 低 |
| P0 | Today Card 扩展 Goals | 1.5h | 低 |
| P1 | acMemory 摘要 | 1h | 低 |
| P1 | Context Bar 顶部 | 2h | 中 |
| P2 | Capability 可视卡片 | 1.5h | 低 |

### 修改文件预测

| 文件 | 预计改动 |
|------|---------|
| `ui/index.html` | +40 行（新增 2-3 个 section） |
| `ui/js/app.js` | +80 行（新增 loadGoals/renderGoals/loadMemorySummary） |
| `ui/css/style.css` | +50 行（新组件样式） |
| `UI-P5-COMPLETION-REPORT.md` | +100 行 |

### API 影响评估

**无需新增 API：**
- `/api/goals` — 已存在
- `/api/memory` — 已存在（可直接用于摘要）
- `/api/capability_os/catalog` — 已存在
- `/api/intelligence/context` — 已存在

**仅需前端消费：**
- 读取已有数据并渲染到首页

### 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| Goals 数据量过大（50条） | 低 | 首页只显示 active（最多 5 条） |
| Memory 摘要过长 | 低 | 限制 200 字符截断 |
| Capability 分类过多 | 低 | 只显示 READY/PARTIAL/BLOCKED 三类计数 |
| 与现有 UI 风格冲突 | 低 | 复用现有 Design Token |

---

## 八、红线检查

| 约束 | 状态 |
|------|------|
| 不修改 server.py | ✅ 仅消费已有 API |
| 不修改 API contract | ✅ 无新增端点 |
| 不修改 DB | ✅ 只读 |
| 不修改 Agent Runtime | ✅ 不影响 |
| 不修改 interaction_activity.py | ✅ 仅消费数据 |
| VERSION 保持 1.0.0 | ✅ |
| 无 ZZ/ZhuangZhou/庄周资产 | ✅ 已确认过滤 |

---

## 九、API 数据来源汇总

| 数据源 | API | 首页消费位置 | 当前状态 |
|--------|-----|-------------|---------|
| Goals | `/api/goals` | 待新增 `acGoals` | ❌ 未消费 |
| Memory Profile | `/api/memory` | 待新增 `acMemory` | ❌ 未消费 |
| Memory Summary | `/api/memory` | 待新增 Today Card 扩展 | ❌ 未消费 |
| Capabilities | `/api/capability_os/catalog` | 待新增 `acCapabilities` | ❌ 未消费 |
| Context | `/api/intelligence/context` | 待新增 Context Bar | ❌ 未消费 |
| Tools Count | `/api/tools/list` | `systemCard()` | ⚠️ 仅数字 |

---

## 十、结论

**当前状态：**
- 后端数据层完整（Goals/Memory/Capabilities/Context）
- 前端 UI 层仅在 Settings 页展示详细数据
- 首页缺失"AI OS 感知"层（用户无法快速了解小6的状态）

**P5 升级价值：**
1. 用户价值：让 AI 的"记忆、目标、能力"对用户可见
2. 体验升级：从"功能型输入框"升级为"上下文感知型 AI OS"
3. 架构一致：复用已有 API，零后端改动

**推荐实施顺序：**
1. Today Card 扩展（Goals + Memory Summary）— 1.5h
2. Agent Center 扩展（acGoals + acMemory）— 2h
3. Capability 可视卡片 — 1.5h
4. Context Bar 顶部 — 2h

**预计总工作量：** 7-8 小时  
**预计改动量：** ~170 行 HTML，~80 行 JS，~50 行 CSS

---

**审计完成。等待下一步指令。**
