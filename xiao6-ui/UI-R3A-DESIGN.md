# Xiao6 UI-R3A - UI 架构重建与设计冻结

**日期**: 2026-08-30
**状态**: 设计冻结
**范围**: 仅UI层，不修改后端

---

## 一、最高优先级硬约束

| 约束 | 状态 |
|------|------|
| 产品唯一身份: Xiao6 / 小6 / Six | ✅ 已统一 |
| 废弃身份清理: ZZ/zz/庄周等 | ✅ 已清理 |
| 唯一端口: 8000 | ✅ 验证通过 |
| 唯一UI入口: xiao6-space/index.html | ✅ 已确立 |
| v1.0.0 tag 不移动 | ✅ HEAD c01709d |

---

## 二、真实能力基线 (REAL / PARTIAL / UNAVAILABLE)

### 2.1 REAL - 完整实现

| 能力域 | API端点 | 说明 |
|--------|---------|------|
| **对话** | POST /api/chat | Smart/Expert模式, SSE流式 |
| **对话历史** | GET /api/chat/history | 分页加载 |
| **Session** | POST/GET /api/session, /api/session/resume | 会话恢复 |
| **目标** | /api/goals, /api/agent/goal | CRUD完整 |
| **任务** | /api/tasks | 50条任务 |
| **记忆** | /api/memories, /api/memory/query | 长期记忆搜索 |
| **知识** | /api/knowledge | 文件库检索 |
| **Agent状态** | GET /api/agent/state | IDLE/THINKING/RUNNING |
| **工具执行** | TOOLS in server.py | 62个工具已注册 |
| **语音ASR** | POST /api/asr, /api/transcribe | FunASR本地转写 |
| **语音TTS** | POST /api/speak | edge-tts/GPT-SoVITS |
| **唤醒词** | POST /api/kws | Vosk本地检测 |
| **天气** | GET /api/weather, /api/geo | Open-Meteo |
| **热点** | GET /api/hotspots | 抖音/微博热榜 |
| **简报** | GET /api/briefing | 聚合天气+热点+待办 |
| **审计** | GET /api/audit | 工具调用日志 |
| **能力目录** | GET /api/capabilities, /api/capability_os/catalog | 9大能力组 |
| **用户模型** | GET /api/user_model | 个性化画像 |
| **个人上下文** | GET /api/personal_context | 五维视图 |
| **自我学习** | GET /api/learnings | 经验沉淀 |

### 2.2 PARTIAL - 部分实现或条件启用

| 能力域 | 状态 | 说明 |
|--------|------|------|
| **EventBus/SSE** | PARTIAL | FEATURE_EVENTBUS=false，走旧路径 |
| **多端同步** | PARTIAL | FEATURE_MULTI_DEVICE=true但需注册 |
| **常驻伴随** | PARTIAL | FEATURE_ALWAYS_ON=false |
| **主动智能V2** | PARTIAL | FEATURE_PROACTIVE_V2=false |
| **日历感知** | PARTIAL | 仅Windows，默认关闭 |
| **应用聚焦** | PARTIAL | 未完全实现 |
| **剪贴板感知** | PARTIAL | 未完全实现 |
| **移动伴侣** | PARTIAL | 框架存在但功能有限 |
| **跨设备接力** | PARTIAL | API存在但使用率低 |

### 2.3 UNAVAILABLE - 不存在或禁用

| 能力域 | 原因 |
|--------|------|
| **插件市场** | 不存在后端API |
| **定时任务调度** | 无scheduler后端 |
| **模型CRUD管理** | 仅有probe/test，无持久化 |
| **Artifact系统** | 无独立实体 |
| **Plugin Market** | 硬编码禁止 |
| **Timer视图** | 已标记REMOVED |

---

## 三、工具清单 (62个)

### 3.1 基础工具 (AUTO)
- get_time, calculator, remember, note_save, note_list
- memory_search, profile_set, profile_get
- reminder_set, reminder_list

### 3.2 任务管理 (AUTO)
- set_task, update_task_step, complete_task, task_list

### 3.3 文件操作 (AUTO)
- file_read, file_list, file_write, file_make_dir
- file_delete, file_rename

### 3.4 系统操作 (CONFIRM)
- list_processes, kill_process, run_shell
- install_software

### 3.5 网络工具 (AUTO)
- web_fetch, browser_read, web_search
- get_weather, get_hotspots

### 3.6 感知工具 (AUTO)
- scan_desktop, scan_installed_software
- manage_prefetch_task, tick_now

### 3.7 Agent工具 (CONFIRM)
- session_state, reset_session
- delegate_agent

### 3.8 知识工具 (AUTO)
- add_knowledge, archive_knowledge
- list_skills, use_skill
- create_custom_tool, list_custom_tools, delete_custom_tool

---

## 四、UI 信息架构设计

### 4.1 一级菜单 (6+1)

```
┌─────────────────────────────────────────────────────────┐
│ 小6    对话  项目  任务  知识  记忆  工具    🔍 👤      │
└─────────────────────────────────────────────────────────┘
```

### 4.2 二级菜单设计

#### 对话
- 新对话 (Ctrl+N)
- 最近对话 (自动加载 /api/chat/history)
- 全部对话 (分页浏览)
- 搜索 (文本过滤)

**功能支持**:
- Smart/Expert模式切换 ✅
- Session Resume ✅
- Project Context (goal_id) ✅
- Voice输入 ✅
- 联网搜索 ✅
- 深度思考 ✅
- Command Palette (Ctrl+K) ✅
- 审批流 (approval) ✅

#### 项目
- 我的项目 (/api/goals)
- 最近项目 (按updated排序)
- 项目详情

**项目详情子页**:
- 概览: 目标进度、关联任务
- 对话: 该项目下的所有对话
- 任务: 该项目下的任务列表
- 活动: 工具调用时间线

**关键**: 项目切换必须传递 goal_id 到 /api/chat

#### 任务
- 进行中 (status!=done)
- 历史 (已完成)
- 任务详情

**详情展示**:
- 人话: Plan → Execute → Verify → Result
- 技术: Tool Call / Execution ID / Runtime (Drawer内)

#### 知识
- 知识库 (/api/knowledge)
- 搜索 (模糊匹配)
- 知识详情 (原文展示)

**数据源**: G:/Xiao6/knowledge/*.md

#### 记忆
- 长期记忆 (/api/memories)
- 用户档案 (/api/user_model)
- 工作记录 (/api/learnings)
- 搜索 (memory_query)

**数据源**: SQLite xiao6.db

#### 工具
- 工具库 (动态从 /api/capability_os/catalog 生成)
- 应用控制 (process/kill/shell)
- MCP/外部工具 (仅真实存在的)
- 运行记录 (/api/audit)

#### 设置 (独立入口，不占导航位)
- 常规: 主题、语言
- 模型: Agnes API配置、LLM2配置
- 权限: 工具权限策略
- 语音: ASR/TTS配置
- 数据: 导出/导入
- 高级: Runtime/Debug/Policy/Tool Trace

---

## 五、首页设计 (非Dashboard)

```
┌─────────────────────────────────────────────────────────┐
│ 小6          对话  项目  任务  知识  记忆  工具     🔍 👤 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    小6                                   │
│                 今天想做什么？                           │
│                                                         │
│              ┌─────────────────────┐                   │
│              │ 告诉小6你想完成什么… │                   │
│              ├─────────────────────┤                   │
│              │ 📎 🔍 🎤 ↑          │                   │
│              └─────────────────────┘                   │
│                                                         │
│              当前项目: xxx                              │
│              最近工作: 3项                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 六、执行体验设计

### 6.1 默认展示
- "小6正在检查项目…"
- "正在修改代码…"
- "已完成。"

### 6.2 详情Drawer (点击展开)
- Plan: 意图识别结果
- Execute: 工具调用序列
- Verify: 结果验证
- Result: 最终输出

**包含真实数据**:
- Tool Call名称/参数/结果
- Execution ID
- 耗时
- Approval决策
- 错误与Recovery

---

## 七、顶部栏设计

```
┌─────────────────────────────────────────────────────────┐
│ 小6 ▼   当前项目: xxx         🔍 铃铛  👤 用户        │
└─────────────────────────────────────────────────────────┘
```

- 左侧: 品牌Logo + 项目名称
- 中间: 当前上下文
- 右侧: 搜索、通知、用户

---

## 八、视觉规范

### 8.1 配色

| 用途 | 色值 |
|------|------|
| 背景 | #F8F9FB |
| 表面 | #FFFFFF |
| 主文字 | #18181B |
| 次要文字 | #71717A |
| 品牌强调 | #6366F1 |
| 危险/错误 | #C83A3A |
| 成功 | #22C55E |
| 警告 | #F59E0B |

### 8.2 设计原则

```
"Low Default Complexity, High Capability Density"
"低默认复杂度，高能力密度。"
```

1. 用户不需要理解内部架构
2. 用户只需告诉小6想完成什么
3. 能力按需出现
4. 结果优先
5. 过程可展开
6. 技术细节进Drawer/高级
7. 所有UI连接真实能力
8. 不做假功能
9. 不做重复入口
10. 不做第二套UI

### 8.3 禁止项

❌ 巨大爱心
❌ 大面积渐变
❌ 大量彩色卡片
❌ AI科技装饰
❌ 过度圆角
❌ 过多图标
❌ 信息墙
❌ 伪数据
❌ 假进度
❌ 假能力

---

## 九、废弃UI清理

### 9.1 已确认清理

| 废弃项 | 状态 |
|--------|------|
| zz-space | ✅ 已删除 |
| _archive | ✅ 标记DEPRECATED |
| xiao6-ui (历史) | ✅ 标记DEPRECATED |
| zz/ZhuangZhou/庄周 | ✅ 已清理 |

### 9.2 待验证清理

```bash
# 扫描运行时引用
grep -r "zz-space\|zhuangzhou\|ZhuangZhou\|庄周" /g/xiao6/xiao6-ui --include="*.py" --include="*.js" --include="*.html" --include="*.css"
```

---

## 十、端口清理

### 10.1 当前状态

| 端口 | 用途 | 状态 |
|------|------|------|
| 8000 | Xiao6 UI | ✅ 唯一使用 |
| 8010 | 旧端口 | ❌ 无进程 |
| 8022 | 旧端口 | ❌ 无进程 |

### 10.2 清理检查

```bash
# 检查配置中的端口引用
grep -r "8010\|8022" /g/xiao6/xiao6-ui --include="*.py" --include="*.js" --include="*.html"

# 检查结果应该为空
```

---

## 十一、UI → Runtime 映射表

| UI组件 | 后端API | 数据源 |
|--------|---------|--------|
| 对话列表 | GET /api/chat/history | SQLite turns |
| 发送消息 | POST /api/chat | Agnes LLM |
| 模式切换 | payload.mode | capability_runtime |
| 项目选择 | goal_id参数 | /api/goals |
| 任务列表 | GET /api/tasks | SQLite tasks |
| 记忆搜索 | POST /api/memory/query | SQLite memories |
| 知识检索 | GET /api/knowledge | 文件库 |
| 工具执行 | tools.execute_tool | tools.py |
| 语音输入 | POST /api/asr | FunASR |
| 语音输出 | POST /api/speak | edge-tts |
| Agent状态 | GET /api/agent/state | runtime.state |
| 能力目录 | GET /api/capability_os/catalog | registry.py |

---

## 十二、待实现的新UI文件结构

```
xiao6-space/
├── index.html          # 主入口 (重写)
├── css/
│   ├── tokens.css      # 不变
│   ├── layout.css      # 重写
│   ├── components.css  # 重写
│   └── workspace.css   # 重写
└── js/
    ├── main.js         # 重写
    ├── api.js          # 不变
    ├── state.js        # 不变
    ├── sidebar.js      # 重写
    ├── timeline.js     # 不变
    ├── palette.js      # 不变
    └── voice.js        # 不变
```

---

## 十三、下一步

**设计冻结后执行**:
1. 清理废弃UI引用
2. 验证端口清理
3. 重写 xiao6-space/index.html
4. 更新 CSS/JS 适配新架构
5. E2E测试所有交互

**禁止**:
- 修改核心Runtime
- 修改Planner/Execution/Policy
- 增加不存在的后端能力
- 创建第二套UI

---

*设计冻结完成，等待执行阶段启动。*
