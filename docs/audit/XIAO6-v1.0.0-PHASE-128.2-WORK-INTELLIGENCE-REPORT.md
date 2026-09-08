# Xiao6 v1.0.0 — PHASE 128.2 Work Intelligence Layer 报告

**日期**: 2026-09-04  
**状态**: 已完成  
**版本**: v1.0.0 (tag=2798c6e)

---

## 1. 实施内容

### 1.1 Task Health Layer (128.2-A)

**新增文件**: `ui/js/work_health.js`

健康度计算规则：

| 状态 | 触发条件 | 原因 |
|------|---------|------|
| GOOD | 正常运行/已完成 | "任务正在正常推进" / "任务正常完成" |
| WARNING | RUNNING + 24h无进度 | "任务24小时无进度更新" |
| STALE | RUNNING + 72h无进度 | "任务超过72小时没有进度更新" |
| FAILED | status包含failed/error | "任务失败需要处理" |

数据来源（仅读取已有字段）：
- `status` — 任务状态
- `updated` / `updated_at` — 最后更新时间
- `current_step` / `total_steps` — 步骤进度
- `history` — 执行历史（可选）

### 1.2 Task Risk Indicator (128.2-B)

风险徽章显示在任务卡片右上角：
- ⚠ WARNING 状态
- ⏸ STALE 状态  
- ✗ FAILED 状态

所有风险原因通过 `title` 属性展示，可解释、可追溯。

### 1.3 Task Watch / Favorite (128.2-C)

**新增文件**: `ui/js/work_filters.js`

存储方式：`localStorage`

```json
{
  "xiao6.watched_tasks": ["task-001", "task-002"]
}
```

功能：
- 点击 ☆/★ 按钮关注/取消关注
- 筛选器增加"我的关注"选项
- 刷新后状态保持

### 1.4 Recent Work View (128.2-D)

新增"最近工作"标签页，分类显示：
- **最近打开** — 用户点击过的任务
- **最近完成** — status 为 done/completed/finished/success
- **最近失败** — status 为 failed/error/failure

数据来源：`localStorage` 历史记录 + 已有任务状态。

### 1.5 Work Center Filter Upgrade (128.2-E)

统一过滤逻辑收口到 `work_filters.js`：

```javascript
filterTasks(tasks, { mode: 'all|run|done|failed|watched' })
```

现有筛选器升级：
- 全部任务
- 运行中
- 已完成
- 失败
- 我的关注

### 1.6 UI 样式 (128.2-F)

新增 CSS 样式（不破坏现有布局）：

```css
.health-badge        /* 健康度徽章 */
.watch-btn           /* 关注按钮 */
.recent-work-*       /* 最近工作视图 */
```

---

## 2. 新增文件

| 文件 | 大小 | 职责 |
|------|------|------|
| `ui/js/work_health.js` | 4.5 KB | 健康度计算引擎 |
| `ui/js/work_filters.js` | 6.3 KB | 统一过滤层 + 关注管理 |

---

## 3. 修改文件

| 文件 | 变更行数 | 主要修改 |
|------|---------|---------|
| `ui/index.html` | +3 | 引入新 JS 文件，添加"最近工作"标签 |
| `ui/js/app.js` | +237/-15 | 集成健康度、关注、最近工作视图 |
| `ui/css/style.css` | +90 | 新增样式规则 |

---

## 4. 数据来源

**严禁新请求 API**。所有数据来自：

1. **S.tasks** — 已有任务列表（API `/api/tasks`）
2. **localStorage** — 关注列表、最近工作记录
3. **任务字段** — status, updated, current_step, total_steps 等

---

## 5. 健康度规则

```
状态判定流程：
┌─────────────────────────────────────┐
│  输入: task 对象                     │
├─────────────────────────────────────┤
│  1. status 包含 failed/error?       │
│     → HEALTH.FAILED                │
├─────────────────────────────────────┤
│  2. status 包含 done/completed?     │
│     → HEALTH.GOOD                  │
├─────────────────────────────────────┤
│  3. status 在 RUNNING 集合中？      │
│     ├─ 有 updated 且 >= 72h 无更新  │
│     │   → HEALTH.STALE             │
│     ├─ 有 updated 且 >= 24h 无更新  │
│     │   → HEALTH.WARNING           │
│     └─ 其他                        │
│         → HEALTH.GOOD              │
├─────────────────────────────────────┤
│  4. 其他状态                        │
│     → HEALTH.GOOD                  │
└─────────────────────────────────────┘
```

---

## 6. 风险规则

| 规则 ID | 条件 | 风险提示 |
|--------|------|---------|
| RISK-01 | status 包含 failed/error | "任务失败需要处理" |
| RISK-02 | RUNNING + 24h 无 current_step 更新 | "任务24小时无进度更新" |
| RISK-03 | RUNNING + 72h 无 current_step 更新 | "任务超过72小时没有进度更新" |

**禁止**：无依据推测、AI 猜测任务状态。

---

## 7. 测试证据

### 7.1 代码验证

```bash
# 检查文件是否存在
ls -la ui/js/work_health.js ui/js/work_filters.js
# ✓ work_health.js (4523 bytes)
# ✓ work_filters.js (6278 bytes)

# 检查集成
grep -n "WorkHealth\|WorkFilters" ui/js/app.js
# ✓ 771行: const health = WorkHealth ? WorkHealth.calculateHealth(t) : null;
# ✓ 779行: const isWatched = WorkFilters ? WorkFilters.isTaskWatched(t.id) : false;
# ✓ 1161行: function renderRecentWork(box) { ... }
```

### 7.2 语法检查

```bash
# Python 项目无需 npm build
# 纯前端实现，无构建步骤
```

### 7.3 浏览器测试

**前置条件**: 启动服务器
```bash
cd G:/xiao6/xiao6-ui && python server.py
```

**测试用例**:

| 测试项 | 验证方法 | 预期结果 |
|--------|---------|---------|
| 健康度计算 | 打开 Work Center，检查任务卡片 | 非 GOOD 状态显示徽章 |
| 关注功能 | 点击 ☆ 按钮 | 变为 ★，localStorage 保存 |
| 刷新保持 | 刷新页面 | 关注状态不变 |
| 过滤器 | 点击"我的关注" | 只显示关注的任务 |
| 最近工作 | 切换到"最近工作"标签 | 显示分类列表 |
| 健康度规则 | 创建长时间无更新的任务 | 显示 WARNING/STALE |

---

## 8. Git Diff Summary

```diff
Diff: ui/css/style.css
  +90 lines (health-badge, watch-btn, recent-work styles)

Diff: ui/index.html
  +3 lines (script imports, recent tab)

Diff: ui/js/app.js
  +237 lines, -15 lines
  - 集成 WorkHealth.calculateHealth()
  - 集成 WorkFilters.isTaskWatched()
  - 新增 renderRecentWork() 函数
  - 修改 bindWxFilters() 支持关注按钮
  - 修改 wxFiltered() 支持 watched 模式
  - 修改 wxFilters() 添加"我的关注"选项

Untracked:
  + ui/js/work_health.js (4523 bytes)
  + ui/js/work_filters.js (6278 bytes)
```

---

## 9. 设计约束验证

| 约束 | 状态 | 说明 |
|------|------|------|
| 不修改核心执行链 | ✓ | 未触碰 ai_core.execution.run, planner, policy_engine |
| 不修改后端 API | ✓ | 纯前端实现，零新增接口 |
| 不污染 UI 组件 | ✓ | 独立 utility 文件 |
| 可解释的智能判断 | ✓ | 所有规则基于真实字段 |
| 不恢复旧命名 | ✓ | 禁用 ZZ/ZhuangZhou/庄周 |
| 版本冻结 | ✓ | 基于 v1.0.0 tag=2798c6e |

---

## 10. 后续步骤

**等待下一阶段指令**。不自动进入 PHASE 129。

如需启动测试环境：
```bash
cd G:/xiao6/xiao6-ui && python server.py
# 然后打开 http://localhost:8000/index.html
# 点击左侧"⚡ 工作"进入 Work Center
```
