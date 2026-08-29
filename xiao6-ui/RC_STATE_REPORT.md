# Xiao6 v1.0.0-rc1 系统状态档案

**版本**: v1.0.0-rc1  
**基线**: commit 93e2a6b, tag v1.0.0-rc1  
**生成时间**: 2026-08-28 22:05  
**维护者**: Hermes Agent (Agnes)

---

## 1. 项目结构

### 1.1 核心路径
```
G:\xiao6\xiao6-ui\          # 主项目目录
G:\xiao6\xiao6-ui\release\  # 发布包（冻结副本）
G:\xiao6\xiao6-ui\zz-space\ # 前端界面
G:\xiao6\xiao6-ui\tests\    # 测试套件
```

### 1.2 代码规模
| 指标 | 数值 |
|------|------|
| Python 文件数 | 2242 |
| Python 代码总行数 | 35,197 |
| 核心模块数 | 47 |
| 测试文件数 | 9 |

### 1.3 目录树（核心模块）

```
xiao6-ui/
├── server.py              # HTTP 入口（57KB, 1127 行）
├── config.py              # 全局配置（48KB, 756 行）
├── tools.py               # 工具注册表（190KB, 含 62 个工具）
├── agent_runtime.py       # Agent 编排状态机（69KB, 1357 行）
├── policy_engine.py       # 授权内核（14KB, 323 行）
├── goals.py               # 目标系统（23KB, 619 行）
├── intent_gateway.py      # 意图网关（5KB, 131 行）
├── memory.py              # 记忆压缩与上下文注入（33KB, 885 行）
├── db.py                  # 数据库层（31KB, 806 行）
├── capabilities.py        # 能力注册表（6KB）
├── capability_runtime.py  # 能力执行适配器（10KB）
├── eventbus.py            # 事件总线（13KB）
├── llm.py                 # LLM 调用封装（10KB）
├── session.py             # 会话管理（16KB）
├── context/               # 上下文构建（3 模块）
├── ai_core/               # AI 核心（lifecycle, execution）
├── capability_os/         # 能力 OS（7 模块）
├── cognitive/             # 认知层（4 模块）
├── computer_action/       # 电脑操作层（5 模块）
├── knowledge_runtime/     # 知识运行时（3 模块）
├── memory_evolution/      # 记忆演化（1 模块）
├── identity/              # 身份层（2 模块）
├── mcp_host/              # MCP 主机（2 模块）
├── launcher/              # 启动器（2 模块）
├── data/                  # 数据持久化
├── logs/                  # 运行日志
├── models/                # 模型缓存
├── tests/                 # 测试套件
│   └── r8_agent_benchmark/ # R8 基准测试（9 文件）
└── zz-space/             # 前端界面
    ├── index.html
    ├── css/zz-workspace.css
    └── js/zz-workspace.js
```

---

## 2. Runtime 入口

### 2.1 启动链
```
python server.py
    │
    ├─→ config.reload()           # 加载环境变量
    ├─→ db_conn()                 # 初始化 SQLite
    ├─→ capabilities.scan()       # 扫描 62 个工具
    ├─→ AgentRuntime.start()      # 启动编排线程
    ├─→ policy_engine._load_store()  # 加载策略存储
    ├─→ embed.warmup()           # 预热向量模型
    ├─→ proactive.tick_loop.start()  # 主动智能心跳
    └─→ http.server.serve_forever()  # 监听 :8000
```

### 2.2 配置来源
| 来源 | 优先级 | 示例 |
|------|--------|------|
| `.env` 文件 | 高 | `AGNES_API_KEY=sk-xxx` |
| 环境变量 | 高 | `XIAO6_PORT=8000` |
| config.py 默认值 | 低 | `PORT = 8000` |

### 2.3 端口统一
- **官方端口**: 8000
- **环境变量**: `XIAO6_PORT` 优先，`ZhuangZhou_PORT` 向后兼容
- **绑定地址**: 127.0.0.1（仅本机）

---

## 3. Agent 执行链

### 3.1 状态机
```
[IDLE] → [PLANNING] → [EXECUTING] → [REFLECTING] → [IDLE]
   ↑                                         │
   └──────────── 失败重试 ────────────────────┘
```

### 3.2 执行流程
```
用户输入 → IntentGateway → GoalDecisionEngine
    │
    ├─ 短文本 → skip（直接调用工具）
    └─ 长任务 → create goal
            │
            ▼
    AgentRuntime.submit_goal()
            │
            ▼
    [PLANNING] goals.plan_goal() → Task 拆解
            │
            ▼
    [EXECUTING] for each task:
        ├─ policy_engine.evaluate(tool) → auto/confirm/never
        ├─ tools.execute_tool(name, args)
        └─ 结果回写 trace
            │
            ▼
    [REFLECTING] reflector.reflect() → 经验沉淀
            │
            ▼
    Goal 完成 → GOAL_COMPLETED 事件
```

### 3.3 Policy 四级授权
| 等级 | 含义 | 示例工具 |
|------|------|----------|
| `auto` | 自动执行 | get_time, calculator |
| `confirm` | 需用户确认 | run_shell, file_write |
| `session` | 会话级缓存 | - |
| `never` | 永久禁止 | kill_process, file_delete |

---

## 4. API 列表

### 4.1 Chat 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/speak` | POST | TTS 语音合成 |
| `/api/asr` | POST | 语音转文字 |
| `/api/transcribe` | POST | 转录接口 |
| `/api/kws` | POST | 唤醒词检测 |
| `/api/chat/history` | GET | 对话历史 |

### 4.2 Agent 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/agent/intent` | POST | 意图提交 |
| `/api/agent/goal` | POST | Goal 创建 |
| `/api/agent/approval` | POST | 审批 resolve |
| `/api/agent/state` | GET | 运行时状态 |

### 4.3 Goal 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/goals` | GET | 列出所有 Goal |
| `/api/goals/<id>` | GET | 查询单个 Goal |
| `/api/goals/<id>` | PUT | 更新 Goal |
| `/api/goals/<id>` | DELETE | 删除 Goal |

### 4.4 系统接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/config` | GET | 配置读取 |
| `/api/models` | GET | 模型列表 |
| `/api/test-llm` | POST | LLM 测试 |
| `/api/providers/probe` | POST | Provider 探测 |
| `/api/devices` | GET | 设备列表 |
| `/api/trace` | GET | 执行轨迹 |
| `/api/activity` | GET | 活动日志 |
| `/api/briefing` | GET | 每日简报 |
| `/api/alert-config` | GET/POST | 告警配置 |

### 4.5 Memory 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/memory/query` | POST | 记忆搜索 |
| `/api/memory/confirm` | POST | 记忆确认 |
| `/api/memory/backfill` | POST | 记忆回填 |
| `/api/memory/important-dates` | GET/POST | 重要日期 |
| `/api/memories` | GET/POST | 记忆 CRUD |
| `/api/learnings` | GET | 学习记录 |

### 4.6 Proactive 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/proactive/dnd` | GET/POST | 免打扰控制 |
| `/api/always-on/control` | GET/POST | 常驻伴随控制 |
| `/api/cross-device/relay` | POST | 跨端接力 |
| `/api/mobile/reminder` | POST | 移动提醒 |
| `/api/mobile/chat` | POST | 移动对话 |

### 4.7 Computer Action 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/vision/capture` | POST | 截图捕获 |
| `/api/action/plan` | POST | 动作规划 |
| `/api/action/execute` | POST | 动作执行 |
| `/api/focus/window` | GET | 当前窗口 |
| `/api/clipboard/clear` | POST | 清空剪贴板 |

### 4.8 Capability OS 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/capability_os/match` | POST | 能力匹配 |
| `/api/capability_os/plan` | POST | 能力规划 |

### 4.9 Self Awareness 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/self_awareness/run` | POST | 自检运行 |
| `/api/self_awareness/decide` | POST | 自检决策 |

### 4.10 Data 接口
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/data/export` | GET | 数据导出 |
| `/api/data/import` | POST | 数据导入 |
| `/api/sessions` | GET | 会话列表 |
| `/api/session` | POST | 会话管理 |
| `/api/knowledge` | POST | 知识管理 |
| `/api/social/inbound` | POST | 社交接收 |
| `/api/boot/avatar-ready` | POST | Avatar 就绪 |

---

## 5. Tool 列表（62 个）

### 5.1 系统工具（12）
| 名称 | 权限 | 描述 |
|------|------|------|
| `get_time` | auto | 获取当前时间 |
| `calculator` | auto | 数学计算 |
| `remember` | auto | 记忆保存 |
| `memory_search` | auto | 记忆搜索 |
| `tick_now` | auto | 主动智能触发 |
| `web_search` | auto | 网页搜索 |
| `web_fetch` | auto | 网页抓取 |
| `browser_read` | auto | 浏览器读取 |
| `get_weather` | auto | 天气查询 |
| `get_hotspots` | auto | 热点数据 |
| `scan_resources` | auto | 资源扫描 |
| `list_skills` | auto | 技能列表 |

### 5.2 文件工具（7）
| 名称 | 权限 | 描述 |
|------|------|------|
| `file_read` | confirm | 读取文件 |
| `file_list` | confirm | 列出文件 |
| `file_write` | confirm | 写入文件 |
| `file_make_dir` | confirm | 创建目录 |
| `file_delete` | never | 删除文件 |
| `file_rename` | confirm | 重命名文件 |

### 5.3 任务工具（4）
| 名称 | 权限 | 描述 |
|------|------|------|
| `set_task` | auto | 创建任务 |
| `update_task_step` | auto | 更新进度 |
| `complete_task` | auto | 完成任务 |
| `task_list` | auto | 任务列表 |

### 5.4 提醒工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `reminder_set` | auto | 设置提醒 |
| `reminder_list` | auto | 提醒列表 |

### 5.5 笔记工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `note_save` | auto | 保存笔记 |
| `note_list` | auto | 笔记列表 |

### 5.6 用户画像工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `profile_set` | auto | 设置画像 |
| `profile_get` | auto | 读取画像 |

### 5.7 Shell 工具（3）
| 名称 | 权限 | 描述 |
|------|------|------|
| `run_shell` | confirm | 执行命令 |
| `session_state` | confirm | 查看会话状态 |
| `reset_session` | confirm | 重置会话 |

### 5.8 进程工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `list_processes` | auto | 列出进程 |
| `kill_process` | never | 终止进程 |

### 5.9 安装工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `install_software` | confirm | 安装软件 |

### 5.10 桌面工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `scan_desktop` | auto | 扫描桌面 |
| `scan_installed_software` | auto | 扫描已装软件 |

### 5.11  prefetch 工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `manage_prefetch_task` | auto | 管理预取任务 |

### 5.12 | 媒体工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `media_generate` | auto | 生成媒体 |

### 5.13 | 社交工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `social_send` | confirm | 发送消息 |

### 5.14 | ASR 工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `asr_transcribe` | auto | 语音转文字 |

### 5.15 | 热点工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `open_hotspot_panel` | auto | 打开热点面板 |
| `typhoon_panel` | auto | 台风信息 |

### 5.16 | 卡片工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `person_card` | auto | 人物卡片 |
| `render_card` | auto | 渲染卡片 |

### 5.17 | 地图工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `map_query` | auto | 地图查询 |

### 5.18 | 面板工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `open_doc_panel` | auto | 打开文档面板 |
| `open_memory_audit` | auto | 打开记忆审计 |

### 5.19 | 审查工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `review_output` | auto | 审查输出 |

### 5.20 | 视频工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `play_video` | auto | 播放视频 |

### 5.21 | 规则工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `manage_rule` | confirm | 管理规则 |

### 5.22 | 技能工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `use_skill` | auto | 使用技能 |
| `list_skills` | auto | 列出技能 |

### 5.23 | 自定义工具（3）
| 名称 | 权限 | 描述 |
|------|------|------|
| `create_custom_tool` | confirm | 创建自定义工具 |
| `list_custom_tools` | auto | 列出自定义工具 |
| `delete_custom_tool` | never | 删除自定义工具 |

### 5.24 | 委托工具（1）
| 名称 | 权限 | 描述 |
|------|------|------|
| `delegate_agent` | confirm | 委托子 Agent |

### 5.25 | Goal 工具（5）
| 名称 | 权限 | 描述 |
|------|------|------|
| `set_goal` | auto | 设置 Goal |
| `update_goal` | auto | 更新 Goal |
| `list_goals` | auto | 列出 Goal |
| `delete_goal` | never | 删除 Goal |
| `plan_goal` | auto | 规划 Goal |

### 5.26 | 知识工具（2）
| 名称 | 权限 | 描述 |
|------|------|------|
| `add_knowledge` | auto | 添加知识 |
| `archive_knowledge` | auto | 归档知识 |

---

## 6. 数据库架构

### 6.1 数据库文件
| 文件 | 大小 | 用途 |
|------|------|------|
| `zhuangzhou.db` | 225KB | 主数据库（记忆、对话、Goal） |
| `xiao6.db` | 1.3MB | 向量数据库 |
| `xiao6_sessions.db` | 36KB | 会话管理 |

### 6.2 核心表
```sql
-- 对话记录
chat_log (id, role, content, timestamp)

-- 记忆摘要
memory_summary (id, summary, updated_at)

-- Goal 表
goals (id, title, description, status, priority, progress, ...)

-- Task 表
tasks (id, goal_id, title, status, order_index, ...)

-- 记忆图谱
memories (id, content, type, importance, created_at)

-- Meta 表
meta (key, value)

-- 学习记录
learnings (id, content, source, created_at)
```

---

## 7. 测试套件

### 7.1 R8 Agent Benchmark（9 测试文件）
| 文件 | 测试项 | 状态 |
|------|--------|------|
| `test_api_surface.py` | 17 | ✅ PASS |
| `test_a_single_tool.py` | 8 | ✅ PASS |
| `test_b_multi_step_goal.py` | 6 | ✅ PASS |
| `test_c_failure_recovery.py` | 10 | ✅ PASS |
| `test_release_security.py` | 15 | ✅ PASS |
| `test_ui_runtime.py` | 9 | ✅ PASS |
| `test_r8p4_planner.py` | 3 | ✅ PASS |
| `failure_truthfulness_test.py` | 6 | ✅ PASS |
| `test_r8_tool_args_contract.py` | 15 | ✅ PASS |
| **总计** | **89** | **✅ ALL PASS** |

### 7.2 其他测试
| 文件 | 描述 | 状态 |
|------|------|------|
| `test_s68_capabilities.py` | 能力注册表 | ✅ |
| `test_s69_session_integrity.py` | 会话完整性 | ✅ |
| `test_s70_shared_context.py` | 共享上下文 | ✅ |
| `test_s71_prompt_architecture.py` | Prompt 架构 | ✅ |
| `test_s81_chat_e2e.py` | Chat E2E | ⚠️ PARTIAL |

---

## 8. 已知问题（P2）

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| 1 | `vosk` 模块未安装 | KWS 语音唤醒不可用 | 已知限制 |
| 2 | `knowledge_runtime.cache.DocCache` 导入失败 | 知识索引不完整 | 核心功能不受影响 |
| 3 | `FEISHU_WS_URL` 未配置 | 飞书长连接跳过 | 预期行为 |
| 4 | `self_diagnosis.startup_check` 不存在 | 自检跳过 | 非致命 |
| 5 | `proactive_agent` 模块缺失 | 主动智能 V2 降级 | 配置开关可控制 |
| 6 | `beta_boot.mark_backend_ready` 不存在 | Beta Boot 跳过 | 非致命 |
| 7 | HOTDATA_KEY 未配置 | 热点数据源 401 | 非阻塞 |
| 8 | `/api/tools` 端点 404 | 工具列表不可查 | 设计决策 |
| 9 | `/api/memory/search` 端点 404 | 记忆搜索 API 缺失 | 可能需要补充 |

---

## 9. 冻结模块清单

### 9.1 Runtime 核心（禁止修改）
- `agent_runtime.py` - 编排状态机
- `policy_engine.py` - 授权内核
- `ai_core/execution/*.py` - 执行核心
- `capability_os/*.py` - 能力 OS

### 9.2 数据层（禁止修改 Schema）
- `db.py` - 数据库连接
- `goals.py` - 目标系统
- `memory.py` - 记忆系统

### 9.3 API 层（禁止破坏向后兼容）
- `server.py` - HTTP 路由
- `server_handlers_*.py` - Handler 实现
- `tools.py` - 工具注册表

---

## 10. Git 历史

```
203fc04 Docs: add R8 Release Closure final report (v1.0.0-rc1)
93e2a6b Xiao6 v1.0.0-rc1: Release Closure (R8-P0~P4 + UI Recovery + hardening)
c52a3c9 S87: Release baseline & repository integrity audit
ec6d554 S86: Runtime stability closure
a79d992 S85: Credential configuration lock
f7aa544 S84: Execution core recovery with policy gate
ec599e7 S83: Agent Loop E2E validation complete
8b60e2f S82: Session & Trace persistence closure
af0be77 S81 FINAL: Real Chat E2E complete
```

**Tag**: `v1.0.0-rc1`

---

## 11. 维护约束

### 禁止事项
1. ❌ 不允许破坏 Runtime 架构
2. ❌ 不允许重新设计 Execution Core
3. ❌ 不允许大规模重构
4. ❌ 不允许修改冻结模块
5. ❌ 不允许破坏 API 向后兼容
6. ❌ 不允许修改数据库 Schema

### 必须遵守
1. ✅ 所有修改必须先审计再执行
2. ✅ 遵循 VERIFY-BEFORE-CHANGE 原则
3. ✅ 保持最小变更
4. ✅ 中文报告格式固定
5. ✅ 真实 E2E 测试，禁止伪造 PASS

---

## 12. 下一步

- [ ] Phase RC-2: 建立监控系统
- [ ] Phase RC-3: 收集用户反馈
- [ ] Phase RC-4: 规划 v1.0.0 正式版本

---

Report generated: 2026-08-28 22:05
Maintained by: Hermes Agent (Agnes)
