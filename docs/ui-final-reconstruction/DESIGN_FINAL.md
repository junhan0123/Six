# Xiao6 AI OS · Final UI Design

> 身份：Senior Product Designer + Senior Frontend Architect + AI OS Experience Engineer  
> 目标：从零重建最终版「个人 AI 副驾」界面，不再修补旧 UI。  
> 版本：v1.0 — 设计阶段（Phase 1）

---

## 0. 核心回应：当前 `final/` 错在哪里？

你发的参考图 1 是一个**统一的 AI Presence 空间**：小6在中心，状态在呼吸，能力藏在语境里。  
当前 `final/` 做了外形近似，但本质上仍是：

- **左侧传统导航栏**（记忆/知识/任务/世界/设置）= 功能菜单思维。
- **能力总览做成了静态说明书**（16 个图标卡片墙）= 这是「给新人看的功能目录」，不是用户能触达的能力层。
- **底部快捷按钮** = 功能堆砌。
- **CSS 直接堆到 1500+ 行** = 没有设计系统，后续无法扩展。

本设计彻底放弃这些修补，按「One Space Architecture」重新来。

---

## 1. 产品定位

**Xiao6 AI OS = Personal AI Operating System**

不是：
- 聊天窗口
- 功能菜单
- Dashboard 卡片墙
- 工具集合页

首页回答三个问题：
1. **1 秒**：这是小6（AI Core 在中央，一眼识别）。
2. **5 秒**：小6现在状态如何（光球颜色 / 模态标签 / 左侧三句上下文）。
3. **30 秒**：我可以直接告诉它我要什么（Intent Line 在底部中央）。

---

## 2. One Space Architecture

整个应用只有一个空间，没有页面切换。

```
┌─────────────────────────────────────────────────────────────┐
│  小6 AI OS · 在线                        21:50  8月10日 周日 │
│  你的个人 AI 副驾，理解你，记住你，陪伴你                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   正在处理          ┌─────────────────┐    小6正在思考...   │
│   等待你的新指令    │                 │    ✓ 理解你的意图    │
│                     │   AI CORE       │    ✓ 分析相关信息    │
│   我记得            │   庄  周         │    ○ 规划执行步骤    │
│   你正在开发小6    │                 │      执行任务        │
│   AI OS             │   [Avatar]      │      生成结果        │
│                     │                 │                      │
│   我理解            │   · 我在思考    │                      │
│   你的目标是打造    │                 │                      │
│   个人 AI OS        └─────────────────┘                      │
│                                                             │
│              🎤  告诉小6你想完成什么...      ⏎ 发送         │
│                                                             │
│   ⌘1 记忆    ⌘2 知识    ⌘3 目标    ⌘4 世界    ⌘5 设置       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 禁止清单
- ❌ 多页面
- ❌ 左侧传统导航
- ❌ Dashboard 卡片墙
- ❌ 多个工作台
- ❌ Galaxy 太阳系首页
- ❌ Chat 页面
- ❌ 功能商城式能力墙
- ❌ 玻璃卡片堆叠
- ❌ 发光过度
- ❌ 游戏 HUD 感
- ❌ 廉价蓝色科技风
- ❌ 大量边框

---

## 3. 视觉规范

### 3.1 参考风格
Apple Vision Pro · Linear · Raycast · Claude

### 3.2 颜色
- **背景**：纯黑 `#000000` → 深蓝黑 `#030712` 径向渐变
- **AI 状态色**：唯一来源 `avatar-state.js` META
  - IDLE `#5fb3c8`
  - WAITING `#f0b35e`
  - THINKING `#8b9bff`
  - PLANNING `#c08bff`
  - EXECUTING `#56d364`
  - COMPLETED `#56d3a0`
  - ERROR `#ff6b6b`
  - OFFLINE `#8a93a6`
- **文字**：主白 `rgba(255,255,255,0.92)`，次白 `rgba(255,255,255,0.60)`，弱白 `rgba(255,255,255,0.35)`
- **辅助色**：只用状态色自身的 glow，不引入额外装饰色

### 3.3 字体
- 中文：`PingFang SC`, `Microsoft YaHei`, `system-ui`
- 数字/时间：`SF Mono`, `JetBrains Mono`

### 3.4 间距
基于 4px 网格：8 / 12 / 16 / 24 / 32 / 48 / 64

### 3.5 动画
- 所有过渡 ≤ 400ms
- 光球呼吸：4-7s
- 粒子漂移：自然随机
- 尊重 `prefers-reduced-motion`

### 3.6 设计语言关键词
**高级、克制、科技感、留白、中心聚焦、单一状态色、自然动效。**

---

## 4. AI Core（中央核心）

位置：绝对居中，占据屏幕 40-45% 视觉权重。

### 4.1 组成
1. **外层光晕**：随状态色呼吸的弥散 glow，半径约 300px，opacity 0.2-0.5。
2. **中环粒子流**：缓慢环绕的微小光点，状态活跃时密度增加。
3. **内球**：玻璃质感球体，表面有极淡的网格/经纬线，折射状态色。
4. **Avatar**：小6形象悬浮于球心偏下，被球体轻微遮挡，营造「生命体在核心中」的感觉。
5. **Brand 字标**：球体上方极淡地浮现「小6 / XIAO6」，不抢焦点。
6. **状态胶囊**：球体下方 80px 处，显示当前模态：「我在这里」「思考中」「执行中…65%」。

### 4.2 状态表现
| 状态 | 颜色 | 视觉行为 | 模态文案 |
|------|------|----------|----------|
| IDLE | 蓝青 | 缓慢呼吸，粒子稀疏 | 我在这里 |
| WAITING | 琥珀 | 光晕等待脉冲 | 等待你的指令 |
| THINKING | 紫蓝 | 内部光线流动，球体微亮 | 思考中 |
| PLANNING | 紫 | 环绕环旋转加速 | 规划中 |
| EXECUTING | 绿 | 能量流从球心向外 | 执行中…{progress}% |
| COMPLETED | 青绿 | 柔和 settling 动画 | 已完成 |
| ERROR | 红 | 不规则抖动+红光 | 遇到了问题 |
| OFFLINE | 灰 | 极暗呼吸，几乎静止 | 离线中 |

### 4.3 交互
- 点击光球：聚焦 Intent Line（不打开新页面）。
- 长按空格：语音输入（Voice Core）。

---

## 5. Voice Core（语音核心）

位置：Intent Line 左侧，与 AI Core 形成「对话三角」。

### 5.1 状态
- **idle**：麦克风图标静息。
- **listening**：声波从麦克风向外扩散，AI Core 同步进入 listening 光晕。
- **thinking**：麦克风图标变成频率波纹，AI Core 进入 thinking。
- **speaking**：能量从 AI Core 流向麦克风/底部，AI Core 进入 speaking 态。
- **error**：红色脉冲。

### 5.2 真实连接
- 优先 `/api/asr/status` 探测后端 ASR。
- 后端就绪 → 用 `/api/asr` + `MediaRecorder`。
- 后端不可用 → 降级 `SpeechRecognition` (webkit)。
- 唤醒词命中：SSE `wakeword_detected` → 自动进入 listening。

---

## 6. Intent Line（唯一主入口）

位置：底部中央，宽度 720px，悬浮于底边 40px 处。

### 6.1 设计
- 细长胶囊输入条，背景 `rgba(255,255,255,0.04)`，聚焦时边框微亮状态色。
- Placeholder：「告诉小6你想完成什么…」
- 左侧 Voice Core 按钮，右侧发送按钮（仅回车触发）。
- 支持文件拖拽到输入条：拖入时展开为「分析文件」意图。

### 6.2 调用链路
```
用户输入 → ZZIntentGateway.dispatch → POST /api/agent/intent
         → Backend Intent Gateway → Goal Decision Engine
         → 创建 Goal / 直接聊天 / 拒绝
         → 领域事件经 SSE → AppState → AI Core 状态变化
```

### 6.3 快捷能力入口（隐藏式）
输入条下方仅显示 ⌘1-5 提示，平时不抢焦点：
- ⌘1 Memory Overlay
- ⌘2 Knowledge Overlay
- ⌘3 Goals Overlay
- ⌘4 World Overlay
- ⌘5 Settings Overlay

---

## 7. 上下文感知卡（左侧三句）

位置：AI Core 左侧，宽度 260px，三行垂直排列。

不是 Dashboard 卡片，而是三句「小6此时知道什么」的自然语言：

1. **正在处理**
   - 空闲："等待你的新指令"
   - 有任务："正在分析项目架构，进度 65%"
2. **我记得**
   - "你正在开发小6 AI OS"
   - "你偏好简洁、高级的界面"
3. **我理解**
   - "你的目标是打造个人 AI OS"
   - "当前上下文是 UI 重建设计阶段"

数据来源：
- `/api/memory` summary/profile
- `/api/tasks` 当前任务
- `/api/goals` 进行中目标
- SSE Agent 状态

### 7.1 设计原则
- 不显示数字。
- 不显示列表。
- 只显示一句最相关的自然语言。
- 文案由前端轻量组装，数据必须真实。

---

## 8. 思维流（右侧）

位置：AI Core 右侧，宽度 280px。

不是聊天历史，而是当前 Intent → Goal → Task 的生命周期可视化。

### 8.1 阶段
1. 理解你的意图
2. 分析相关信息
3. 规划执行步骤
4. 执行任务
5. 生成结果

### 8.2 状态
- 已完成：✓
- 进行中：● 脉冲
- 等待中：○

### 8.3 数据来源
- SSE 领域事件：`INTENT_*` / `GOAL_*` / `AGENT_*` / `TASK_*`
- 不显示具体聊天内容，只显示执行阶段。

---

## 9. 能力层设计（关键修正）

### 9.1 之前的问题
旧 `capability-view` 把 16 个能力做成静态图标卡片墙，本质是说明书，不可触发，违反「能力感知」原则。

### 9.2 正确做法
能力不以按钮墙展示，而是通过三层触达：

#### 第一层：自然语言（默认）
用户直接对 Intent Line 说：
- "帮我整理知识体系" → 触发 knowledge 相关工具
- "分析当前项目" → 触发 project 相关工具
- "提醒我下午三点开会" → 触发 reminder 工具

AI Core 与上下文卡给出反馈，不需要用户知道能力叫什么名字。

#### 第二层：⌘1-5 Overlay（按需浮现）
用户按快捷键或点击底部提示，从右侧滑入 Overlay，展示该领域实时状态：

- **⌘1 Memory Overlay**
  - 顶部："我记得你…" 摘要
  - 中部：记忆网络 2D 力导向图（`/api/memories/graph`）
  - 底部：最近 3 条关键记忆

- **⌘2 Knowledge Overlay**
  - 顶部：知识库统计（文档数、最近更新）
  - 中部：知识主题网络（`/api/notes/graph`）
  - 底部：搜索入口

- **⌘3 Goals Overlay**
  - 顶部：进行中目标数
  - 中部：目标时间线（`/api/goals` + `/api/tasks`）
  - 底部：新建目标入口（ Intent Line 预填）

- **⌘4 World Overlay**
  - 2D AI Understanding Graph
  - 节点：项目 / 人物 / 知识点 / 设备 / 事件
  - 边：关系类型
  - 数据来源：`/api/memories/graph` + computer world events

- **⌘5 Settings Overlay**
  - 系统状态 / 特性开关 / ASR/KWS 状态 / 主题

#### 第三层：AI Core 微文案反馈
当某类能力被触发时，AI Core 下方状态胶囊变化：
- "正在读取你的项目结构…"
- "正在搜索相关知识…"
- "正在创建任务…"

### 9.3 能力总览作为「初次见面」引导
仅在首次启动或用户主动问「你能做什么」时，AI Core 进入特殊展示模式：
- 光球周围浮现 4-6 个能力光环（项目管理 / 知识管理 / 任务执行 / 记忆 / 自动化 / 语音）。
- 每个光环 hover 显示一句话说明。
- 点击任一光环 → Intent Line 预填相关示例指令。
- 按 Esc 退出展示模式。

这不再是静态说明书，而是可交互的「能力入口」。

---

## 10. World Model 2D 图

废弃太阳系视觉。采用 2D 力导向图，展示「小6如何理解你的世界」。

### 10.1 节点类型
- 项目（Project）
- 人物（Person）
- 知识点（Knowledge）
- 记忆（Memory）
- 设备（Device）
- 事件（Event）

### 10.2 边类型
- `related_to`
- `part_of`
- `created_by`
- `depends_on`

### 10.3 数据来源
- `/api/memories/graph`
- `/api/notes/graph`
- Computer World events（WINDOW_OPENED / PROJECT_DETECTED / APP_LAUNCHED 等）

### 10.4 视觉
- 深色画布，节点为微光点，边为极细线。
- 当前聚焦节点轻微放大并发光。
- 缩放/拖拽探索，点击节点显示详情浮层。

---

## 11. 组件架构

```
final-v2/
├── index.html              # 唯一入口
├── css/
│   ├── tokens.css          # 设计令牌
│   ├── base.css            # 全局/动画
│   ├── core.css            # AI Core
│   ├── intent.css          # Intent Line + Voice Core
│   ├── context.css         # 上下文卡 + 思维流
│   └── overlay.css         # Overlay + World Graph
├── js/
│   ├── viewport-scale.js   # 1600×900 等比缩放
│   ├── state.js            # 轻量只读 AppState（订阅 SSE）
│   ├── data-bridge.js      # 聚合 /api/* 数据
│   └── boot.js             # 装配
└── components/
    ├── ai-core.js          # AI Core 渲染 + 8 态
    ├── voice-core.js       # 语音输入
    ├── intent-line.js      # 输入条 + 提交
    ├── context-cards.js    # 左侧三句
    ├── thought-stream.js   # 右侧思维流
    ├── overlay.js          # Overlay 框架
    ├── world-graph.js      # 2D 世界图
    ├── memory-overlay.js   # ⌘1
    ├── knowledge-overlay.js# ⌘2
    ├── goals-overlay.js    # ⌘3
    ├── world-overlay.js    # ⌘4
    └── settings-overlay.js # ⌘5
```

### 11.1 数据流
```
后端 EventBus → SSE /api/stream
                   ↓
            frontend state.js
                   ↓
        ┌─────────┼─────────┐
        ↓         ↓         ↓
     ai-core  context-cards thought-stream
     voice-core intent-line  overlays
```

### 11.2 共享库只读引用
```html
<script src="../avatar-state.js"></script>
<script src="../zz-events.js"></script>
<script src="../sse-manager.js"></script>
<script src="../intent-gateway.js"></script>
```

---

## 12. 实现阶段

### Phase 2：建立新 UI 框架
- 创建 `xiao6-ui/final-v2/`
- 搭建 `index.html` 骨架
- 建立 CSS 设计令牌系统
- 实现 viewport-scale 等比缩放

### Phase 3：接入核心能力
- AI Core 8 态渲染
- Voice Core 语音输入
- Intent Line → `/api/agent/intent`
- SSE → state.js
- 上下文卡真实数据

### Phase 4：接入 Overlay
- ⌘1 Memory
- ⌘2 Knowledge
- ⌘3 Goals
- ⌘4 World（2D 图）
- ⌘5 Settings

### Phase 5：视觉打磨
- 光球质感
- 动效自然度
- 响应式/缩放无重叠
- reduced-motion 支持

### Phase 6：真实浏览器验证
- 各 API 200
- SSE 状态流转
- 缩放/全屏无重叠
- 语音输入可用

---

## 13. 验收标准映射

| 验收项 | 设计满足方式 |
|--------|-------------|
| ✅ 一个界面 | One Space，无页面切换 |
| ✅ 一个 AI Core | 中央光球，唯一状态权威 |
| ✅ 一个入口 | Intent Line 唯一主入口 |
| ✅ 所有能力可调用 | 自然语言 + ⌘1-5 Overlay |
| ✅ 无聊天页面感 | 思维流替代聊天历史 |
| ✅ 无后台管理感 | 无 Dashboard 卡片墙 |
| ✅ 无功能堆砌 | 能力隐藏，按需浮现 |
| ✅ AI 存在感强 | AI Core 占 40%+ 视觉权重 |
| ✅ 科技感强 | 黑底+状态色+留白+自然动效 |
| ✅ 长期可扩展 | 设计令牌 + 组件化 |

---

## 14. 下一步

设计已完成。进入 Phase 2 实现前，请确认：
1. 是否同意本设计方向？
2. 是否确认在 `xiao6-ui/final-v2/` 独立重建，保留旧 `final/`？
3. AI Core 中 Avatar 位置：当前新图是胸像，是否按「球心偏下、被球体轻微遮挡」处理，还是完全居中显示？

确认后立即进入实现阶段。
