# 00 · 小6当前系统全面审计

> Xiao6 UI v2.0 · Phase 0
> 审计日期：2026-08-10
> 审计范围：`G:\Xiao6`（前端 66 JS / 13 CSS，后端 90 Python / 66 API）
> 性质：**只读审计，未修改任何代码**

---

## 摘要（先说结论）

小6的**技术地基是优秀的，产品结构是失败的**。

- 后端 24,052 行 Python，66 个 API，62 个 LLM 工具，五大子系统均有真实实现与事件契约 —— 这是一个**真正的 AI Runtime**，不是套壳。
- 前端 Design Token 体系成熟（270 个变量、z-index 阶梯化、圆角 5 级、动效统一），状态层（AppState）与事件契约（zz-events）设计严谨。
- **但是**：`index.html` 一个文件里同时挂着三套互不兼容的产品心智，五代 CSS 补丁争夺同一批选择器，后端最强的能力（目标系统）在前端**零暴露**。

一句话诊断：

> **问题不在皮肤，在骨架。而过去五代 UI 修复全部被限定为"只准动皮肤"。**

这是本次审计最重要的发现，下文 §5 给出证据。

---

## 1. 系统真实能力地图

### 1.1 规模基线

| 层 | 指标 | 数值 |
|---|---|---|
| 前端 | JS 文件 | 66 个（56 被 index.html 引用，**10 个孤儿**） |
| 前端 | CSS 文件 | 13 个 / 8,218 行 |
| 前端 | index.html | 1,561 行（含 67 个内联 SVG symbol） |
| 前端 | 顶层浮层容器 | **11 个** |
| 前端 | 静态资源 | textures 4.7MB + three.module.js 1.27MB = **~6MB** |
| 后端 | Python 文件 | 90 个 / 24,052 行 |
| 后端 | HTTP API 端点 | 66 个 |
| 后端 | LLM 工具 | 62 个 |
| 数据 | SQLite 总行数 | **690 行**（xiao6.db，503KB，32 对象） |

### 1.2 五大子系统成熟度

| 子系统 | 核心实现 | 持久化 | 前端消费 | 后端成熟度 | **前端暴露度** |
|---|---|---|---|---|---|
| **Goal System** | `goals.py` 17 函数 + `goal_decision_engine.py` | goals / tasks 表 | ❌ 无 | ★★★★☆ | **★☆☆☆☆** |
| **Memory System** | `memory.py`+`distiller`+`audit`+`query` 34 函数 | memories 34 行 | ✅ memory.js / memory-panel.js | ★★★★☆ | ★★★★☆ |
| **Knowledge System** | `knowledge.py` 12 函数（facade→runtime） | **46 个 md 文件** | ❌ `/api/knowledge` 无人调用 | ★★★☆☆ | **★☆☆☆☆** |
| **Tool System** | 62 工具 + 四级授权分级 | tool_audit 1 行 | ⚠️ 部分（经对话） | ★★★★☆ | ★★☆☆☆ |
| **Proactive + Agent Runtime** | `proactive.py` 37KB / `agent_runtime.py` 33KB / `scheduler.py` | 514 行推送 | ❌ status/dnd 无 UI | ★★★★☆ | ★★☆☆☆ |

**关键失衡**：后端平均成熟度 ★★★★，前端平均暴露度 ★★。**小6有一个远比它的界面聪明的大脑。**

### 1.3 功能门控真实状态

`config.py` 模块顶部的 `FEATURE_*: bool = False` 是**类型声明诱饵**，真值在 `reload()`（config.py:217–328）：

| 开关 | 实际状态 | 说明 |
|---|---|---|
| FEATURE_AGENT_RUNTIME | **ON** | 目标驱动编排状态机已启用 |
| FEATURE_EVENTBUS | **ON** | 事件总线为通信脊柱 |
| FEATURE_MEMORY_DISTILL | **ON** | 靠 .env 翻转 |
| FEATURE_ALWAYS_ON | OFF | 常驻感知未启用 |
| TOOL_FACTORY_ENABLED | OFF | 自建工具关闭，custom_tools 0 行 |

默认 ON 共 21 项（GOAL_SYSTEM / GOAL_DECISION / KNOWLEDGE_PLATFORM / PROACTIVE_V2 / SELF_LEARNING / PERSONA…），默认 OFF 共 13 项（AVATAR_SCENE / CROSS_DEVICE / MOBILE_COMPANION / CALENDAR / APP_FOCUS / CLIPBOARD_SENSE…）。

### 1.4 能力的真实边界（必须诚实面对）

- **操作电脑是 Mock**：`permission_guard.py:40` 使用 `executor or MockComputerExecutor()`，`:165` 无参实例化 → 生产链路走 Mock。真实实现 `RealComputerExecutor`（`computer_executor.py:89–315`，ctypes EnumWindows / mss 截图 / tasklist）**代码是真的，但从未被实例化**，且 `server.py` 对其零引用。
- **13 个已声明能力仅 7 个实现**：`capability_registry.py` 中 modify_file / execute_command / kill_process（HIGH）与 delete / system / network（CRITICAL）标记 `implemented: False`。
- **主动引擎已停摆**：`pending_proactive` 514 行全部 `shown=1`，时间戳停在 08-03→08-04，此后 6 天无新增。

> v2 设计纪律：**Mock 能力不得获得一级入口。** 给假能力发居住权，是信任崩塌的起点。

---

## 2. 六个必答问题

### Q1 · 小6现在真正拥有多少核心能力？

**真实可用的核心能力：7 类，62 个工具。**

| # | 能力簇 | 工具数 | 状态 |
|---|---|---|---|
| 1 | 对话 + 多模态（图/音视频/屏幕） | — | ✅ 真实 |
| 2 | 记忆（记录/检索/蒸馏/审计/画像） | 8 | ✅ 真实 |
| 3 | 目标与任务（CRUD/拆解/进度聚合/决策引擎） | 9 | ✅ 真实，**前端不可见** |
| 4 | 知识（46 篇 md / 35 条关系） | 2 | ✅ 真实，**前端不可见** |
| 5 | 文件与进程（读写/列目录/进程/shell） | 13 | ✅ 真实 |
| 6 | 世界感知（天气/热点/地图/网页/搜索） | 8 | ✅ 真实，前端最完整 |
| 7 | 自我扩展（技能/自建工具/委派 Agent） | 6 | ⚠️ 门控关闭 |

**结论：能力是够的，甚至过剩。缺的不是功能，是这些能力如何被看见、被信任、被日常调用。**

### Q2 · 哪些功能用户每天会使用？

从数据库真实数据反推使用频率（这是唯一不撒谎的证据）：

| 表 | 行数 | 判读 |
|---|---|---|
| pending_proactive | **514** | hotspot 354 / alert 121 / weather 35 —— 主动推送是最高频，但已停摆 |
| memories | 34 | 记忆在被真实使用 |
| chat_log | 24 | 对话是主入口，但总量很低（08-06→08-09） |
| learnings | 23 | 自学习在跑 |
| tasks | 14 | **全部 open**，无一完成 → 任务没有闭环 UI |
| goals | 8 | 标题全为"总结当前项目状态"→ **测试残留，无真实使用** |
| notes | 5 | 低频 |
| custom_tools / episodes / knowledge_chunks / mem_vectors / user_model / rules / reminders | **0** | 完全未使用 |

**每日真实使用：① 对话 ② 主动推送/态势 ③ 记忆。仅此三项。**
**每日零使用：目标、任务闭环、知识库、自定义工具、情节记忆、规则、提醒。**

残酷但必须承认：**目标系统这个最强后端能力，用户一次都没真用过 —— 因为界面上根本没有它。**

### Q3 · 哪些 UI 只是历史遗留？

| 遗留物 | 证据 | 处置建议 |
|---|---|---|
| `.app` 三栏聊天软件（rail + main + tele） | index.html:259–467，被 `body.chat-mode` 切换 | **解构**，能力并入统一空间 |
| `.app` 固定 1920×1080 整体 `scale()` | index.html:1546–1557 | **删除**，这是伪响应式，小屏必然糊 |
| 右侧遥测面板 `.tele` | index.html:391–462，14 个指标格 | **降级**为按需诊断层 |
| 左栏"快捷能力"6 个硬编码 chip | index.html:283–293，写死 `data-q` 提示词 | **删除**，由意图行取代 |
| 地球定位球 `#earth` + 定位读数 | index.html:273–281 | **删除**，与 AI 无关 |
| `#universeView` 太阳系视图 | index.html:163–183 | **重生**（见 05 文档） |
| 9 个主题选择器常驻 HUD | index.html:105–115 | **收进设置**，首屏不该有 9 个色卡 |
| 10 个孤儿 JS | avatar / china_regions / companion / computer-action / computer-state / hud-ring / mobile-app / permission-guard / sw / voice-orb-simple | **归档或删除** |
| 临时文件 | `companion.css.tmp`、`saturn_ring.jpg.broken`、`_hs.mjs`、`_tmp_log.py` 等 | **清理** |

### Q4 · 哪些视觉元素没有实际价值？

按"占用资源 ÷ 传达的 AI 信息量"排序，最差的五个：

1. **NASA 行星贴图（4.7MB）** —— 传达 AI 信息量 = 0。水星、金星、木星的真实表面纹理，与用户的目标、记忆、任务毫无语义关系。
2. **真实天文物理模拟** —— `solar-system.js:38–47` 实现了真实轴向倾角、真实自转周期、真实公转周期（海王星 164.8 年）。**这是一个天文教育软件的内核，被放在了 AI OS 的首屏背景。**
3. **月球绕地公转** —— `MOON = { revRate: 0.7 * 2.5 }`，3.6 秒一圈。纯装饰。
4. **扫描线 / HUD 装饰** —— `--z-scanlines: 40`，科幻片道具感，不承载状态。
5. **三重"小6"品牌重复** —— HUD 品牌 + 英雄标题 + rail 品牌区，同屏出现三次。ui5d 已试图用 CSS 压制（`ui5d:D1-a` 注释明说"消除三重小6的视觉竞争"），但**没有删掉任何一个，只是调小了字号**。

**最扎心的对比**（`solar-system.js:576–580`）：

```js
collect(model.planets,    'goal');       // 目标
collect(model.satellites, 'agent');      // 智能体
collect(model.orbits,     'task');       // 任务
collect(model.archives,   'memory');     // 记忆
collect(model.links,      'knowledge');  // 知识
```

这五行把 AI 的全部语义映射进了 3D 场景。它们被渲染成什么？

```js
const mat = new THREE.MeshBasicMaterial({ color: 0x88aaff });  // 占位中性色
const radius = 115 + i * 7;  // 品牌行星在 13~98，语义节点被推到 115+ 外围
```

> **半径 13–98 的舞台中心，留给了与 AI 无关的八大行星（4.7MB 高清贴图）；
> 用户真正的目标、记忆、任务，是半径 115 开外一圈没有材质的灰蓝小球。**

这一行代码，就是整个 UI 问题的隐喻：**视觉预算 100% 给了天文，0% 给了智能。**

### Q5 · 当前 Galaxy 是否有必要？

**当前形态：完全没有必要。数据层：极有价值。**

拆开看：

| 组成 | 判断 | 理由 |
|---|---|---|
| `solar-system.js` 天文渲染（29KB + 6MB 资源） | ❌ **移除** | 与产品语义零关联，是最大的认知噪音源 |
| `galaxy-state.js` 关系投影（AppState → 节点图） | ✅ **保留并升级** | 把 goal/agent/task/memory/knowledge 投影为带关系的图，这是真资产 |
| `galaxy-runtime.js` / `galaxy-experience.js` | ⚠️ 重写 | 交互包装层，随渲染层一起重做 |

详细论证与最终推荐见 `05_GALAXY_ROLE_REDESIGN.md`。

### Q6 · 当前 Chat 模式是否应该存在？

**对话必须存在。"Chat 模式"必须消失。**

现状问题：对话被实现为一个用 `body.chat-mode` 整体切入切出的**独立软件**（自带 rail、自带品牌、自带 HUD、自带遥测栏），进入它就等于离开 AI OS。

```js
function openChat()  { document.body.classList.add('chat-mode');
                       document.body.classList.remove('universe-mode'); }
function closeChat() { document.body.classList.remove('chat-mode'); }
```

三个模式类互斥（`chat-mode` / `universe-mode` / `cp-mode` / 默认 home），构成**四选一的页面级跳转**——这正是"三个软件拼在一起"的技术根源。

v2 定位：**对话不是一个空间，是贯穿所有空间的常驻输入层（Intent Line）。** 用户在任何焦点下都能直接说话，AI 的回应在当前焦点内就地展开，不发生空间切换。

---

## 3. 三套产品心智的物理证据

`index.html` 同时挂载三个平级顶层容器：

| 行号 | 容器 | 心智 | 触发 |
|---|---|---|---|
| 80–160 | `<section class="os-shell">` | **AI 操作系统** | 默认态 |
| 259–467 | `<div class="app">` | **三栏聊天软件** | `body.chat-mode` |
| 163–183 | `<div id="universeView">` | **太阳系浏览器** | `body.universe-mode` / `Ctrl+U` |

三者同时存在于 DOM，靠 body class 互斥显示。每一个都自带完整的品牌区、状态显示和导航逻辑。

**一级导航则有 6 项**（index.html:87–93）：

```
home | workspace | command | galaxy | assistant | settings
```

这既超过了"最多 5 个"的红线，更严重的是它**正是被明令禁止的传统软件菜单形态**：以"页面/模块"命名，而不是以"AI 的注意力"命名。且 `workspace`（对话）与 `assistant`（语音）指向同一个 `.app`，仅差一个 `navVoice` 布尔值 —— **两个导航项，一个目的地。**

---

## 4. CSS 五代叠加实录

加载顺序（index.html:8–26），后者覆盖前者：

```
styles.css (3620行)  →  premium.css  →  runtime-viz.css  →  execution-channel.css
  →  ui2.css (1794行, Token 权威)  →  spatial-runtime.css
  →  ui4b-first-screen.css  →  ui4b-explore-transition.css
  →  ui4c-visible-upgrade.css  →  ui4c-unified-home.css
  →  ui4d-home-experience.css  →  ui5d-first-screen-polish.css
```

**同一选择器被反复覆写的 TOP 5：**

| 选择器 | 被几个 CSS 文件定义 |
|---|---|
| `.os-core`（首屏 AI 核心） | **6** |
| `.os-shell`（首屏外壳） | **4** |
| `.onb-card` | 4 |
| `.os-hero` / `.os-hero-desc` / `.os-dock` / `.os-bottom` | 各 3 |
| `#universeView` | 3 |

> 首屏最核心的那一个元素 `.os-core`，正在被六代设计意志同时争夺。
> 没有人能靠读代码回答"它现在到底长什么样"——只能打开浏览器看。

**值得表扬的部分（v2 必须继承）**：`!important` 全库仅 31 处，z-index 已完全 token 化（`--z-ground` → `--z-top` 14 级阶梯），圆角收敛为 5 级，动效缓动统一。**基础设施纪律是优秀的。**

---

## 5. 根因分析：为什么五代都没修好

这是本次审计的核心发现。请阅读 `ui4d-home-experience.css` 与 `ui5d-first-screen-polish.css` 的文件头注释：

```
/* UI-4D-1 · AI OS Home Experience v1.0
 * 性质：纯表现层 ADDITIVE 最高覆盖
 * 纪律：
 *  - 不修改 Backend / Agent / AppState / EventBus / Galaxy 逻辑 / 新增功能
 *  - 不触碰 fixed 定位、不修改三面板外层、零逻辑改动、不新增/重定义令牌体系
 */
```

```
/* UI-5D · First Screen Product Polish v1.0
 * 目标映射（把「架构融合完成」提升到「产品视觉完成」）：
 *  - D1 · 顶部 HUD 收敛：消除三重「小6」的视觉竞争
 *  - D2 · 左导航补可见能力名标签（不改 JS / syncNav）
 *  - D4 · Galaxy 默认环境化：从「暗壁纸」调为「活的氛围环境」
 */
```

**诊断清楚地写在注释里了：**

- 4D 知道问题是"AI 在哪、AI 什么状态、我能让 AI 做什么、有没有任务"没答案。
- 5D 知道问题是"三重小6在竞争"、"Galaxy 只是暗壁纸"。

**每一代都诊断对了，每一代都被禁止治疗。**

约束条件是"不修改结构、不触碰 fixed 定位、不改 JS、纯表现层 ADDITIVE 覆盖"。于是：

- 三重品牌 → 不删，改成 `font-size: 11px`
- Galaxy 无意义 → 不删，改成"活的氛围环境"
- 导航是软件菜单 → 不改，加上文字标签

> **这是五代 CSS 叠加的真正成因：结构性病灶，被反复施以化妆品治疗。
> 每一层新 CSS 都是上一层诊断失败的墓碑。**

**v2 的第一条纪律因此确定：这一次，动骨架。**

---

## 6. 交付给下一阶段的结论

### 保留（地基，勿动）

- `app-state.js` 统一状态树 + `zz-events.js` 事件契约 —— 设计严谨，v2 直接复用
- `ui2.css` 的 270 个 Design Token —— 作为 v2 视觉语言的起点重新裁剪
- 全部 66 个后端 API 与 62 个工具 —— 一行不改
- `galaxy-state.js` 关系投影数据层
- z-index 阶梯 / 圆角 5 级 / 动效缓动规范

### 重建（骨架，必动）

- `index.html` 三容器结构 → 单一 Stage
- 6 项软件菜单导航 → 5 焦点脊柱（见 02 文档）
- `body.chat-mode` 页面级切换 → 常驻意图层（见 03 文档）
- `.app` 的 1920×1080 `scale()` → 真实响应式
- 11 个浮层 → 分层浮层体系

### 删除（噪音，清零）

- `solar-system.js` 天文模拟 + 4.7MB 行星贴图 + Three.js 1.27MB
- 10 个孤儿 JS + 全部 `.tmp` / `.broken` / `_` 临时文件
- 5 代 UI 补丁 CSS（ui4b / ui4c / ui4d / ui5d 共 6 个文件，1,524 行）
- 地球定位球、扫描线、月球公转、9 色主题常驻选择器

### 新建（最大机会点）

按价值排序，这是 v2 最应该抢占的屏幕空间：

1. **目标 / 任务执行空间** —— 后端完整（17 函数 + 决策引擎），前端为零。需补 `/api/goals` REST 层。
2. **知识空间** —— 46 篇文档 + 35 条关系，用户完全看不见。
3. **主动洞察收件箱** —— 514 条推送历史，无消费界面，引擎已停摆 6 天。

---

**Phase 0 结束。** 下一步：`01_PRODUCT_VISION_V2.md`。
