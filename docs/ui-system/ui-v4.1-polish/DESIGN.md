# UI-v4.1 Product Polish Sprint · Design

> 一句话目标：把"正确的 AI OS 原型"提升为"高级 AI 产品界面"——
> 用户打开小6第一眼觉得"**这是我的 AI**"，而不是"**这是一个软件界面**"。

## 一、设计律（沿用并收紧）

1. **先有他，再有事**——小6的存在感先于一切信息。
2. **他说人话**——所有文案第一人称，零机器措辞、零数字、零英文 slug。
3. **安静比响亮贵**——动效是为"生命感"服务，不是为"炫技"。新增的任何运动都必须"可被忽略"。

## 二、六维打磨设计

### 维度 5（最高优先）—— 顶部区域：去 chrome，留"在场"

**问题**：双描边徽章（本地模式 / 在线）+ 连接状态条 = 软件标题栏观感。

**设计**：
- 移除 `本地模式` / `在线` 两个 boxed 徽章，与 `AI OS · Presence Space` 工程自述。
- 品牌仅留 **「小6」** 两字（克制、像人名不是产品名）。
- 小6名前加一枚**活体存在点** `.topbar__pulse`：颜色取 `--core-color`（与整屏强调同色），3.4s 呼吸。它同时承担"在线/离线"语义——离线时 `applyState('offline')` 把 `--core-color` 注入为 OFFLINE 灰，点自然变灰。
- 右侧仅留一条**耳语隐私提示**（mono、极淡、无边框）：`本地运行 · 数据不出这台设备`——这是信任信号，不是状态条。
- 时钟保留但进一步淡化（mono、faint）。

**红线自检**：未删连接逻辑（`boot.js` 的 `setConnection` 对缺失元素安全 no-op）；存在点颜色完全复用既有 `--core-*` 注入；无任何新元素承载"功能"。

### 维度 1 —— AI Core：从光球到"在场的智能体"

**设计（全部 CSS，承接既有 `data-state`）**：
- **内禀光泽流转（shimmer）**：`.orb__core::after` 一层 conic 渐变高光，mask 成圆盘，缓慢旋转（11s）。安静态极淡（opacity .16），思考/执行态增强——制造"内部有东西在流转"的智能感。
- **环绕粒子（satellite）**：新增 `.orb__sat`（无需新事件，纯视觉），沿半径 54px 椭圆慢轨环绕（16s）。仅在活跃态显形：thinking/planning/executing 显形（opacity .9，执行态轨道加快至 7s），waiting 半显（.45），idle/offline 隐藏。这是"生命感"的关键笔触。
- **八态强度差异**（在既有 duration 之外补 intensity）：
  - `executing`：环扫快（2.4s）、环边提亮、粒子加速、shimmer 最亮（.5）。
  - `thinking`：shimmer 流转（.42）、粒子温和（11s）。
  - `planning`：环扫慢（6s）、shimmer（.30）。
  - `waiting`：整体略快呼吸。
  - `idle`：最慢最淡，仅 shimmer 极淡流转。
  - `offline`：dim（既有）+ shimmer/粒子归零。

**红线自检**：八态颜色仍 100% 来自 `avatar-state.js`（JS 不变）；所有节律由 CSS `data-state` 选择器驱动；**未新增任何事件**。

### 维度 4 —— Overlay：从"带标题的列表"到"能力展开"

**设计**：每个类型在标题/kicker 之下、行之上，加一句**小6引导语**（`.sheet__lead`），用第一人称说明"这是我的哪一面"：
- memory：`这些是我替你记着的，重要的排在前面。`
- knowledge：`我读过的资料，按它们讲的事分了类。`
- projects：`我正在帮你推进的几件事。`
- world：`我怎么把你的事连起来看。`
- settings：`关于我，还有你随时能用的几件事。`

配合：行入场微动效（开抽屉时 `.row` 轻微上浮淡入），强化"展开"而非"弹出菜单"。

**红线自检**：纯文案 + 入场动画；列表仍是行式（非卡片）；无统计/无数字。

### 维度 3 —— Intent Line：聚焦与反馈更"贵"

**设计**：
- 聚焦态：在既有描边外，叠加一层柔和 core 色投影 + 整体 1px 上浮，弱化"输入框"感、强化"我在听你说"。
- 发送就绪：键由 ghost→实心时加一次 `send-pop` 缩放入场（320ms），让"可以发了"有正反馈。
- 提交微交互：提交后输入框短暂淡出再归位（JS 轻量加类，非新事件），呼应"已送出"。

### 维度 2 —— Context Layer：微排版

**设计**：三句行距由 `sp-2`(10px) 放宽到 `sp-3`(16px)，呼吸更从容；lead 句保持强调但字距更克制。逻辑零改动。

### 维度 6 —— World Understanding：保持隐藏 + 可读性微调

**设计**：默认仍不展示（仅 ⌘4/世界点入口）；SVG 标签字号 8.5→9.5px、颜色提一档到 `text-dim`，提升可读性。

## 三、变更清单（仅表现层）

| 文件 | 改动 |
|---|---|
| `v4/index.html` | topbar 去 chrome（品牌+活体点 / 耳语+时钟）；orb 增 `.orb__sat` |
| `v4/ui-v4.css` | 顶部去 chrome 样式；AI Core shimmer + satellite + 八态强度；Intent 聚焦柔光 + send-pop；Overlay lead + 行入场；Context 行距；World 标签 |
| `v4/js/overlay.js` | 新增 `LEAD` 引导语；render 改为 append（保留 lead）；world 改为 append |
| `v4/js/context-layer.js` | 无逻辑改动（仅 CSS 行距） |
| 其余 js / data-adapter / boot | 不变（`boot.js` 连接逻辑对新缺失 id 安全 no-op） |

## 四、红线总自检

✅ 不重构架构 ✅ 不新增功能 ✅ 不改 Runtime ✅ 不改后端 ✅ 不新增事件
✅ 不恢复旧导航/Galaxy ✅ 不引入 Dashboard/卡片墙 ✅ 不做多页面
