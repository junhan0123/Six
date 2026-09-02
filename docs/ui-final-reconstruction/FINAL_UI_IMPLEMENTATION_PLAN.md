# Xiao6 AI OS · Ultimate Interface Reconstruction
## FINAL_UI_IMPLEMENTATION_PLAN

> 身份：Senior Product Designer + Frontend Architect + UI System Engineer  
> 目标：将 xiao6-ui/final/ 升级为参考图所示的终极 AI OS 界面。  
> 纪律：不修改后端 / 不新增 Runtime / 不新建 EventBus / 只读消费已有能力。

---

## 0. 能力审计（Phase 0）

### 0.1 已有 API（全部可调用）
| 能力 | 端点 | 用途 |
|------|------|------|
| Agent State | `GET /api/agent/state` | 驱动 AI Core 8 态 |
| Goals | `GET /api/goals` | 展示当前目标与进度 |
| Memory | `GET /api/memories` | "我记得" 上下文 |
| Memory Graph | `GET /api/memories/graph` | 记忆关联 |
| Knowledge | `GET /api/knowledge` | "我了解" 知识库 |
| Capabilities | `GET /api/capabilities` | 工具/能力清单 |
| Tasks | `GET /api/tasks` | 任务状态 |
| Devices | `GET /api/devices` | 设备状态 |
| Briefing | `GET /api/briefing` | 综合简报 |
| Intent | `POST /api/agent/intent` | 自然语言入口（复用 intent-gateway.js） |
| Voice | `GET /api/asr/status`, `/api/wakeword` | 语音状态 |
| SSE | `GET /api/stream` | agent_state / wakeword_detected 实时推送 |

### 0.2 共享库（只读引用）
- `../avatar-state.js` — 8 态权威 + META 颜色。
- `../zz-events.js` — 事件总线。
- `../sse-manager.js` — SSE 连接。
- `../intent-gateway.js` — Intent 网关。

### 0.3 当前 final/ 状态
已存在独立目录 `xiao6-ui/final/`，包含：
- `index.html` + `css/ui-final.css` + `js/viewport-scale.js` + `js/data-adapter.js` + `js/boot.js`
- 组件：`ai-core.js`, `context-aura.js`, `voice-core.js`, `intent-channel.js`, `overlay.js`, `thought-stream.js`, `capability-matrix.js`, `avatar-panel.js`, `quick-actions.js`, `world-map.js`, `galaxy-view.js`

差距：当前布局缺少参考图中的"资源统计顶栏"、"当前状态"、"执行进度"、"小6理解的你"三卡片，左侧导航也没有数字徽章。

---

## 1. 设计目标

产品定位：小6不是聊天机器人/后台/Dashboard，而是用户的本地 AI 副驾。打开界面第一眼应感受到"小6正在这里"。

核心原则：
- One Space，无页面切换。
- 中央 AI Core 绝对优先。
- 真实能力驱动，禁止假数据。
- 深色科技 HUD，色彩由 avatar-state.js META 驱动。
- 任意窗口比例下等比缩放、布局不变形。

---

## 2. 最终空间结构（对应参考图）

```
┌─────────────────────────────────────────────────────────────┐
│  小6 AI OS · 在线   记忆 256  知识 1287  目标 8  工具 34    21:50 │
├────┬──────────────────────────────────────────────┬─────────┤
│ 核心│                                              │ 执行进度 │
│ 记忆│            AI Core（Avatar + 光环）           │ 当前目标 │
│ 知识│                                              │ 65%     │
│ 目标│            小6 / XIAO6                 │ 理解需求 ✓│
│ 世界│            正在思考中...                      │ 收集文件 ✓│
│ 工具│                                              │ 分析代码 ●│
│ 设置│                                              │ 生成架构图○│
├────┴──────────────────────────────────────────────┴─────────┤
│ 当前状态                                                      │
│ 🟣 思考中  🔵 分析中  🟣 规划中  ⚪ 待执行  🟢 监听中  🟢 在线  │
├─────────────────────────────────────────────────────────────┤
│ 小6理解的你                                                  │
│ ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│ │  我记得    │  │  我了解    │  │  我关注    │              │
│ │ ...        │  │ ...        │  │ ...        │              │
│ └────────────┘  └────────────┘  └────────────┘              │
├─────────────────────────────────────────────────────────────┤
│ 🎤 告诉小6你想完成什么...              ➤                   │
│ [分析项目] [创建任务] [搜索知识] [打开文件] [系统状态] ...    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 文件结构

```
xiao6-ui/final/
├── index.html
├── css/
│   ├── tokens.css      # 设计令牌
│   ├── base.css        # 缩放 + 布局骨架
│   ├── layout.css      # 顶栏/边栏/三栏/底部
│   ├── ai-core.css     # 中央 AI Core + 光环
│   ├── panels.css      # 当前状态 / 执行进度 / 理解你
│   ├── intent.css      # 输入条 + 快捷操作
│   └── overlay.css     # 覆盖层
├── js/
│   ├── viewport-scale.js   # 等比缩放
│   ├── data-bridge.js      # 真实数据聚合
│   ├── state.js            # SSE + 轮询状态机
│   └── boot.js             # 启动装配
└── components/
    ├── ai-core.js           # 中央核心 8 态 + SVG/Canvas 环
    ├── state-panel.js       # 左侧"当前状态"
    ├── execution-panel.js   # 右侧"执行进度"
    ├── understanding.js     # "小6理解的你"三卡片
    ├── intent-bar.js        # 底部输入条
    ├── quick-actions.js     # 快捷操作
    ├── side-nav.js          # 左侧边栏 + 数字徽章
    ├── top-bar.js           # 顶栏 + 资源统计
    ├── voice-core.js        # 语音核心
    └── overlay-system.js    # 能力覆盖层
```

---

## 4. 数据映射

| UI 元素 | 数据来源 | 说明 |
|---------|----------|------|
| 顶栏资源 | `/api/memories`, `/api/knowledge`, `/api/goals`, `/api/capabilities` | 取 count / length |
| 当前状态 | `AvatarState.derive()` | 8 态 + 子状态（分析中/规划中/待执行/监听中/在线） |
| AI Core | `/api/agent/state` + SSE agent_state | 驱动光环/颜色/速度 |
| 执行进度 | `/api/goals` + `/api/tasks` | active goal progress + steps |
| 我记得 | `/api/memories` | 最近 3 条自然语言 |
| 我了解 | `/api/knowledge` | 最近/最相关 3 个知识领域 |
| 我关注 | `/api/goals` active | 当前 active goals |
| 快捷操作 | `/api/capabilities` | 取前 8 个能力 |

---

## 5. Phase 计划

- **Phase 1**: UI Shell — 新建文件结构、HTML 骨架、CSS 令牌、缩放基线。
- **Phase 2**: Data Bridge — 接入所有真实 API，只读聚合。
- **Phase 3**: AI Core — 8 态驱动 Avatar + SVG/Canvas 外环 + 波形。
- **Phase 4**: Voice Core — 麦克风动画 + ASR/wakeword 状态。
- **Phase 5**: Panels + Overlay — 当前状态、执行进度、理解你、能力覆盖层。
- **Phase 6**: Verify — 无头校验、API 测试、多窗口截图验证、输出报告。

---

## 6. 验收标准

- [ ] 第一眼像 AI 生命体，不是 Dashboard/聊天/后台。
- [ ] 任意窗口比例等比缩放，无压扁。
- [ ] Goal / Memory / Knowledge 可查看真实数据。
- [ ] Agent 状态实时变化驱动 AI Core。
- [ ] Voice 可调用，Intent 可执行。
- [ ] 不修改后端，不新增 Runtime/EventBus。
- [ ] 可独立回滚（final/ 独立目录）。
