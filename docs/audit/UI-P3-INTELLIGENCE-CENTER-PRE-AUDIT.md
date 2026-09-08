# UI-P3 Intelligence Center Pre-Audit 报告

**Date**: 2026-09-06  
**Scope**: Intelligence Feed + Foresight Panel  
**Constraint**: 只读审计，不修改任何代码  

---

## 一、API Schema 分析

### 1.1 GET /api/intelligence/feed

**返回结构**：
```json
{
  "ok": true,
  "feed": [
    {
      "id": "world-risk-1788702588",
      "type": "world",
      "priority": 5,
      "title": "世界风险: medium",
      "content": "严重度: 0.50, 事件数: 2",
      "source": "World Model",
      "timestamp": 1788702588.1480544,
      "relative_time": "刚刚",
      "score": 9.5,
      "rank_reason": "中优先级 + 近期变化 + 高影响",
      "summary": "检测到 2 个相关事件",
      "impact": "可能影响未来趋势判断",
      "recommendation": "继续观察相关事件发展",
      "status": "new",
      "feedback": null
    }
  ],
  "stats": {
    "total_items": 4,
    "by_type": { "world": 2, "proactive": 1, "knowledge": 1 },
    "by_priority": { "high": 0, "medium": 3, "low": 1 },
    "by_score_range": { "critical": 0, "high": 3, "medium": 1, "low": 0 },
    "high_priority": 0,
    "medium_priority": 3,
    "low_priority": 1
  },
  "generated_at": "2026-09-06 21:49:48"
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一标识，格式 `{type}-{timestamp}` |
| type | string | 来源类型：memory/knowledge/world/proactive |
| priority | int 1-10 | 优先级评分 |
| title | string | 标题 |
| content | string | 详细描述 |
| source | string | 数据来源名称 |
| timestamp | float | Unix 时间戳 |
| relative_time | string | 相对时间（如"刚刚"、"5分钟前"） |
| score | float | Ranking 综合评分 |
| rank_reason | string | 评分原因说明 |
| summary | string | 一句话摘要 |
| impact | string | 影响说明 |
| recommendation | string | 建议操作 |
| status | string | new/acknowledged/actioned |
| feedback | string|null | 用户反馈内容 |

**数据来源**：
- `intelligence_feed.py` → 聚合 World Model、Knowledge、Proactive、Memory 数据
- Ranking 算法：`score = priority + freshness(0-1) + impact(0-1) + relevance(0-1)`
- 所有数据来自已有模块，无新依赖

---

### 1.2 GET /api/intelligence/foresight

**返回结构**：
```json
{
  "ok": true,
  "signals": [
    {
      "signal_id": "knowledge-trend-stable",
      "type": "stable",
      "title": "知识库稳定",
      "confidence": 0.8,
      "reason": "知识库包含 330 文档",
      "source": "knowledge",
      "timestamp": 1788702588.9608479
    }
  ],
  "warnings": [
    {
      "warning_id": "world-medium-risk",
      "level": "medium",
      "message": "世界风险维持 medium，持续观察",
      "source": "world",
      "timestamp": 1788702588.9608479
    }
  ],
  "total": 3
}
```

**字段说明**：
| 字段 | 类型 | 说明 |
|------|------|------|
| signal_id | string | 信号唯一标识 |
| type | string | 趋势类型：rising/falling/stable/emerging |
| title | string | 信号标题 |
| confidence | float 0-1 | 置信度 |
| reason | string | 产生原因 |
| source | string | 数据源 |
| timestamp | float | Unix 时间戳 |
| warning_id | string | 预警唯一标识 |
| level | string | 级别：low/medium/high |
| message | string | 预警信息 |

**数据来源**：
- `foresight_engine.py` → 读取 Memory、Knowledge、World、Proactive 历史数据
- 趋势检测：基于统计计数，无 ML 模型
- 预警生成：基于 World Model 风险级别 + Proactive 观察

---

## 二、前端实现分析

### 2.1 DOM 节点

**Intelligence Feed** (`ui/index.html` L155-163)：
```html
<div class="intelligence-feed" id="intelligenceFeed">
  <div class="feed-header">
    <div class="feed-title"><span class="feed-icon-large">🔮</span> AI Insight Center</div>
    <button class="feed-refresh" id="feedRefresh" title="刷新">↻</button>
  </div>
  <div class="feed-list" id="feedList">
    <div class="feed-loading">加载中...</div>
  </div>
</div>
```

**Foresight Panel** (`ui/index.html` L177-189)：
```html
<div class="foresight-panel" id="foresightPanel">
  <div class="feed-header">
    <div class="feed-title"><span class="feed-icon-large">📊</span> 未来关注</div>
    <button class="feed-refresh" id="foresightRefresh" title="刷新">↻</button>
  </div>
  <div class="foresight-tabs">
    <button class="foresight-tab active" data-tab="signals">趋势信号</button>
    <button class="foresight-tab" data-tab="warnings">早期预警</button>
  </div>
  <div class="foresight-content" id="foresightContent">
    <div class="foresight-loading">加载中...</div>
  </div>
</div>
```

### 2.2 JS 消费位置

**注意**：Feed/Foresight 的 JS 代码嵌入在 `ui/index.html` 的 `<script>` 标签中（L400-607），而非 `app.js`。

| 函数 | 位置 | 功能 |
|------|------|------|
| `loadFeed()` | index.html L410 | 拉取 feed，渲染列表，支持反馈操作 |
| `escapeHtml()` | index.html L461 | XSS 防护（内联定义） |
| `loadForesight(tab)` | index.html L553 | 拉取 foresight，按 tab 渲染信号/预警 |
| 刷新按钮绑定 | index.html L468-470 | feedRefresh 点击触发 loadFeed |
| 定时刷新 | index.html L478 | setInterval 60秒刷新 feed |
| 初始加载 | index.html L474-475 | 页面加载时调用 loadFeed + loadForesight |

### 2.3 CSS 组件状态

**当前存在的 CSS**（`ui/css/style.css`）：
```css
/* L1410-1417 */
.agent-center .intelligence-feed,
.agent-center .foresight-panel {
  background: transparent; border: 0; box-shadow: none;
  padding: 0; margin: 0; border-radius: 0;
}
.agent-center .feed-tabs-mini { display: none; }
```

**缺失的 CSS 类**（在 JS/HTML 中引用但样式表中未定义）：
| 类名 | 用途 | 状态 |
|------|------|------|
| `.feed-header` | Feed 头部 | ❌ 缺失 |
| `.feed-title` | Feed 标题 | ❌ 缺失 |
| `.feed-icon-large` | 大图标 | ❌ 缺失 |
| `.feed-refresh` | 刷新按钮 | ❌ 缺失 |
| `.feed-list` | 列表容器 | ❌ 缺失 |
| `.feed-loading` | 加载状态 | ❌ 缺失 |
| `.feed-empty` | 空状态 | ❌ 缺失 |
| `.feed-item` | 单条条目 | ❌ 缺失 |
| `.feed-icon` | 条目图标 | ❌ 缺失 |
| `.feed-content` | 条目内容区 | ❌ 缺失 |
| `.feed-title-text` | 条目标题 | ❌ 缺失 |
| `.feed-meta` | 元信息行 | ❌ 缺失 |
| `.feed-source` | 来源标签 | ❌ 缺失 |
| `.feed-time` | 时间标签 | ❌ 缺失 |
| `.feed-status` | 状态标签 | ❌ 缺失 |
| `.feed-summary` | 摘要 | ❌ 缺失 |
| `.feed-impact` | 影响说明 | ❌ 缺失 |
| `.feed-recommendation` | 建议 | ❌ 缺失 |
| `.feed-score` | 评分 | ❌ 缺失 |
| `.feed-actions` | 操作按钮区 | ❌ 缺失 |
| `.feed-btn` | 反馈按钮 | ❌ 缺失 |
| `.priority-high` | 高优先级样式 | ❌ 缺失 |
| `.priority-medium` | 中优先级样式 | ❌ 缺失 |
| `.priority-low` | 低优先级样式 | ❌ 缺失 |
| `.status-new` | 新状态 | ❌ 缺失 |
| `.status-seen` | 已读状态 | ❌ 缺失 |
| `.status-done` | 已处理状态 | ❌ 缺失 |
| `.foresight-panel` | 面板容器 | ⚠️ 仅透明重置 |
| `.foresight-tabs` | 标签栏 | ❌ 缺失 |
| `.foresight-tab` | 标签按钮 | ❌ 缺失 |
| `.foresight-content` | 内容区 | ❌ 缺失 |
| `.foresight-loading` | 加载状态 | ❌ 缺失 |
| `.foresight-empty` | 空状态 | ❌ 缺失 |
| `.foresight-signal` | 信号条目 | ❌ 缺失 |
| `.foresight-signal-header` | 信号头 | ❌ 缺失 |
| `.foresight-trend` | 趋势标签 | ❌ 缺失 |
| `.foresight-confidence` | 置信度 | ❌ 缺失 |
| `.foresight-title` | 信号标题 | ❌ 缺失 |
| `.foresight-reason` | 原因说明 | ❌ 缺失 |
| `.foresight-meta` | 元信息 | ❌ 缺失 |
| `.foresight-warning` | 预警条目 | ❌ 缺失 |
| `.foresight-warning-icon` | 预警图标 | ❌ 缺失 |
| `.foresight-warning-message` | 预警消息 | ❌ 缺失 |
| `.warning-high` | 高级预警 | ❌ 缺失 |
| `.warning-medium` | 中预警 | ❌ 缺失 |
| `.warning-low` | 低预警 | ❌ 缺失 |

---

## 三、当前展示能力评估

### 3.1 功能完整性

| 功能 | 后端 | 前端 | 状态 |
|------|------|------|------|
| Feed 数据获取 | ✅ 正常 | ✅ 调用正确 | ✅ 完整 |
| Feed 渲染 | ✅ 4条数据 | ⚠️ JS渲染但无样式 | ⚠️ 可见无格式 |
| Foresight 数据获取 | ✅ 正常 | ✅ 调用正确 | ✅ 完整 |
| Foresight Tab 切换 | ✅ 支持 | ⚠️ JS逻辑正确 | ⚠️ 可见无格式 |
| 反馈按钮 | ✅ API可用 | ⚠️ 按钮渲染但无样式 | ⚠️ 可用但不可见 |
| 定时刷新 | ✅ | ⚠️ 60秒间隔已设置 | ⚠️ 功能存在 |
| 刷新按钮 | ✅ | ⚠️ 按钮存在 | ⚠️ 可见但无样式 |

### 3.2 已知缺陷

#### 缺陷 1：CSS 大量缺失（严重）
- 40+ 个 CSS 类未在 `style.css` 中定义
- Feed 和 Foresight 内容可以渲染（JS 正确），但视觉呈现几乎为零
- 所有元素使用浏览器默认样式，排版混乱

#### 缺陷 2：颜色硬编码（中等）
- `loadForesight()` 中使用硬编码颜色：
  ```js
  const trendColor = s.type === 'rising' ? '#4caf50' : ...
  ```
- 未使用 Design Token（`--ok`、`--warn`、`--brand` 等）
- 与项目整体设计风格不一致

#### 缺陷 3：优先级样式缺失（中等）
- JS 计算了 `priorityClass`（priority-high/medium/low）并添加到 DOM
- 但对应的 CSS 类不存在，优先级视觉差异无法体现

#### 缺陷 4：状态徽章缺失（低等）
- JS 生成了 `statusClass`（status-new/se en/done）
- CSS 未定义，状态徽章无视觉区分

#### 缺陷 5：Insight 面板折叠行为（低等）
- `acInsight` 使用 `data-toggle` 实现折叠
- 但折叠后内容区域无过渡动画

#### 缺陷 6：Escaped HTML 函数重复定义（低等）
- `escapeHtml` 在 index.html 的内联 script 中定义
- app.js 中可能有全局版本（需确认）

---

## 四、UI-P3 升级方案

### 目标
将 Intelligence Feed 和 Foresight Panel 从"功能可用但视觉缺失"升级为"符合 Xiao6 v1.0.0 设计规范的完整 UI 组件"。

### 方案 A：补全 CSS 样式（推荐）

**修改文件**：仅 `ui/css/style.css`

**新增样式**：
```css
/* Feed 组件 */
.intelligence-feed { padding: 12px; }
.feed-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.feed-title { font-size: 14px; font-weight: 600; color: var(--ink-1); display: flex; align-items: center; gap: 6px; }
.feed-icon-large { font-size: 16px; }
.feed-refresh { background: none; border: none; cursor: pointer; font-size: 16px; color: var(--ink-3); padding: 4px; }
.feed-refresh:hover { color: var(--brand); }
.feed-list { display: flex; flex-direction: column; gap: 8px; }
.feed-loading, .feed-empty { text-align: center; color: var(--ink-3); font-size: 13px; padding: 20px 0; }

.feed-item { padding: 10px 12px; border-radius: var(--r-sm); border-left: 3px solid var(--line); background: var(--bg-soft); }
.feed-item.priority-high { border-left-color: var(--danger); background: var(--danger-tint); }
.feed-item.priority-medium { border-left-color: var(--warn); }
.feed-item.priority-low { border-left-color: var(--ink-4); }

.feed-icon { font-size: 16px; flex-shrink: 0; }
.feed-content { flex: 1; min-width: 0; }
.feed-title-text { font-size: 13px; font-weight: 500; color: var(--ink-1); margin-bottom: 4px; }
.feed-meta { display: flex; gap: 8px; font-size: 11px; color: var(--ink-3); margin-bottom: 4px; }
.feed-source { background: var(--bg); padding: 1px 6px; border-radius: 4px; }
.feed-time { }
.feed-status { padding: 1px 6px; border-radius: 4px; font-weight: 500; }
.status-new { background: #e3f2fd; color: #1976d2; }
.status-seen { background: #f3e5f5; color: #7b1fa2; }
.status-done { background: #e8f5e9; color: #388e3c; }

.feed-summary { font-size: 12px; color: var(--ink-2); margin: 4px 0; }
.feed-impact { font-size: 11px; color: var(--ink-3); }
.feed-recommendation { font-size: 11px; color: var(--brand); font-weight: 500; }
.feed-score { font-size: 11px; color: var(--ink-3); margin-top: 4px; }
.feed-actions { display: flex; gap: 4px; margin-top: 6px; }
.feed-btn { background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer; }
.feed-btn:hover { border-color: var(--brand); color: var(--brand); }

/* Foresight 组件 */
.foresight-tabs { display: flex; gap: 4px; margin-bottom: 12px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }
.foresight-tab { background: none; border: none; padding: 6px 12px; font-size: 13px; color: var(--ink-3); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -9px; }
.foresight-tab.active { color: var(--brand); border-bottom-color: var(--brand); }
.foresight-content { display: flex; flex-direction: column; gap: 8px; }
.foresight-loading, .foresight-empty { text-align: center; color: var(--ink-3); font-size: 13px; padding: 20px 0; }

.foresight-signal { padding: 10px 12px; background: var(--bg-soft); border-radius: var(--r-sm); }
.foresight-signal-header { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; }
.foresight-trend { font-weight: 600; text-transform: uppercase; }
.foresight-confidence { color: var(--ink-3); }
.foresight-title { font-size: 13px; font-weight: 500; color: var(--ink-1); margin-bottom: 2px; }
.foresight-reason { font-size: 12px; color: var(--ink-2); }
.foresight-meta { font-size: 11px; color: var(--ink-3); margin-top: 4px; }

.foresight-warning { padding: 10px 12px; border-radius: var(--r-sm); display: flex; gap: 8px; align-items: flex-start; }
.warning-high { background: var(--danger-tint); border-left: 3px solid var(--danger); }
.warning-medium { background: #fff8e1; border-left: 3px solid var(--warn); }
.warning-low { background: var(--bg-soft); border-left: 3px solid var(--ink-4); }
.foresight-warning-icon { font-size: 14px; flex-shrink: 0; }
.foresight-warning-message { font-size: 13px; color: var(--ink-1); flex: 1; }
```

**同步修改 JS**：
- 将 `loadForesight()` 中的硬编码颜色替换为 CSS 变量或 Design Token
- 统一 `escapeHtml` 函数引用

### 方案 B：整合到 app.js（可选）

将内联 script 中的 `loadFeed` / `loadForesight` 迁移到 `app.js`，统一管理。

**优点**：代码组织更清晰  
**缺点**：需要重构现有结构，风险较高  
**建议**：UI-P3 阶段不执行此方案，作为后续优化项

### 方案 C：增加数据可视化（可选）

- Feed 列表添加评分进度条
- Foresight 信号添加趋势箭头图标
- 预警等级使用颜色编码

---

## 五、验收标准

| 检查项 | 标准 |
|--------|------|
| Feed 列表渲染 | 每条记录有清晰视觉层次，优先级颜色区分 |
| Foresight 标签页 | 切换流畅，信号/预警样式分明 |
| 响应式 | 在 220px 窄边栏内正常显示，无溢出 |
| 空状态 | 无数据时显示友好提示 |
| 错误状态 | API 失败时显示错误信息 |
| 设计一致性 | 使用 Design Token，与现有组件风格统一 |
| 无 JS 报错 | Console 无错误 |

---

## 六、风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| CSS 修改影响现有布局 | 低 |  scoped 选择器 `.agent-center .xxx` |
| JS 逻辑变更 | 无（本次不改 JS） | 仅补全 CSS |
| 硬编码颜色修改 | 低 | 替换为 Design Token |

---

**审计结论**：Intelligence Feed 和 Foresight Panel 后端 API 完整、前端 JS 逻辑正确，但 CSS 样式大量缺失导致视觉呈现不完整。建议执行**方案 A**（补全 CSS），预期改动量小、风险低、收益明确。

---

*本报告仅用于审计，未修改任何代码。*
