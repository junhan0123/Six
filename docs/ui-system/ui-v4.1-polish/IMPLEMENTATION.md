# UI-v4.1 Product Polish Sprint · Implementation

> 所有改动均为**表现层**（CSS + 文案 + 轻量 JS 动画类）。
> 零架构改动 / 零新功能 / 零新事件 / 零后端 / 零 Runtime 改动。
> 改动文件：`index.html`、`ui-v4.css`、`js/overlay.js`、`js/intent-line.js`、`js/world-understanding.js`、`js/boot.js`（仅删死代码）。

## 一、Topbar 去 chrome（维度 5 · P0）

**`index.html`**：移除双描边状态徽章（`runtimeStatus`/`connectionStatus`）与 `AI OS · Presence Space` 工程自述。新结构仅留：
- `.topbar__pulse` 活体存在点（与整屏同色呼吸，离线自动变灰）
- `.topbar__mark` = 仅「小6」两字
- `.topbar__whisper` = 耳语隐私提示（无边框、mono 极淡）
- `#topbarTime` 时钟（保留，进一步淡化）

**`ui-v4.css`**：重写顶部样式块（50px 高、去边框徽章、`topbar__pulse` 用 `--core-color` + 3.4s 呼吸 + 柔光晕）。在线/离线信号由存在点颜色承载，**不再依赖独立徽章**。

**`js/boot.js`**：删除 `setConnection()` 死代码（其 DOM 元素已移除，原仅 no-op）。`--core-color` 由 `V4Core.applyState` 注入，离线态即 OFFLINE 灰，顶部点自然变灰。

*红线证明：未删连接能力，仅移除了"显示用"的冗余徽章；`applyState` 完全复用既有 `avatar-state.js` 八态颜色。*

## 二、AI Core 生命感（维度 1 · P0）

**`ui-v4.css`**：
- `.orb__core` 加 `overflow:hidden` 以容纳内部光泽。
- 新增 `.orb__core::after`：conic 渐变高光 + radial mask 成圆盘，`core-shimmer` 11s 缓转，安静态 `opacity:.16`，制造"内部有东西在流转"的智能感。
- 新增 `.orb__sat`：4px 环绕粒子，`sat-orbit` 16s 沿半径 54px 慢轨环绕；仅活跃态显形（thinking/planning/executing opacity .9，executing 轨道加快至 7s，waiting .45，idle/offline 隐藏）。
- 八态强度分档：在既有 `animation-duration` 节律之外，补 `core-shimmer` / `orb__sat` 的可见度与速度差异（executing 最亮最快、thinking 流转、planning 慢扫、idle 极淡、offline 归零）。
- 新增 keyframes：`core-shimmer`、`sat-orbit`。

**`index.html`**：`.orb` 内新增 `<span class="orb__sat"></span>`。

*红线证明：八态颜色仍 100% 来自 `avatar-state.js`（JS 未改）；所有节律由既有 `data-state` 选择器驱动；**未新增任何事件**。*

## 三、Overlay 能力展开（维度 4 · P1）

**`js/overlay.js`**：
- 新增 `LEAD` 引导语映射（memory/knowledge/projects/world/settings 各一句小6第一人称）。
- `open()` 先插入 `.sheet__lead` 引导语，再让各 render 函数 **append**（改为 `insertAdjacentHTML('beforeend', …)`），保证引导语不被行列表覆盖。
- 各 render（`renderMemory`/`renderKnowledge`/`renderProjects`/`renderSettings`）由 `b.innerHTML =` 改为 append，空态亦 append。

**`ui-v4.css`**：
- 新增 `.sheet__lead` 样式（faint、行距 1.75、底部发丝线）。
- 抽屉展开微动效：`.overlay.is-open .sheet__lead/.row/.group/.empty` 轻微上浮淡入，行按序递增延迟（40–190ms），像"展开"而非"弹出菜单"。

*红线证明：列表仍是行式（非卡片）；无统计数字；纯文案 + 入场动画。*

## 四、Intent Line 聚焦与反馈（维度 3 · P1）

**`ui-v4.css`**：
- `.intent` 过渡补 `transform`；`:focus-within` 叠加柔和 core 色投影 + 整体 1px 上浮，弱化"输入框"感、强化"我在听"。
- `.intent__send.is-ready` 加 `send-pop` 缩放入场（320ms），"可以发了"有正反馈。
- 新增 `.intent.is-sending` + `@keyframes intent-send`：提交后输入框短暂淡出再归位。

**`js/intent-line.js`**：`submit()` 在清空输入后给 `#intentLine` 加 `is-sending` 类，440ms 后移除（轻量视觉类，**非新事件**）。

## 五、Context Layer 微排版（维度 2 · P2）

**`ui-v4.css`**：`.context` 行距 `gap` 由 `sp-2`(10px) 放宽到 `sp-3`(16px)，三句呼吸更从容。
逻辑零改动（真实数据、三句措辞、无数字/无英文 slug 均保持不变）。

## 六、World Understanding 可读性（维度 6 · P2）

**`ui-v4.css`**：`.world-graph .w-label` 字号 8.5→9.5px、颜色 `text-faint`→`text-dim`。
**`js/world-understanding.js`**：`render()` 三处 `container.innerHTML =` 改为 `insertAdjacentHTML('beforeend', …)`，确保与 Overlay 引导语共存、且重新打开时不残留旧节点。默认仍不展示，仅 ⌘4/世界点入口（红线保持）。

## 七、红线遵守总表

| 红线 | 遵守证据 |
|---|---|
| 不重构架构 | 仅改 CSS/文案/动画类；DOM 结构未增删语义块 |
| 不新增功能 | 无新交互能力；Overlay 仅加引导语文本 |
| 不改 Runtime | 未触碰 `agent_runtime` / AppState / EventBus |
| 不改后端 | 仅消费既有 `/api/goals·memories·knowledge·agent/state·memories/graph` |
| 不新增事件 | 无新事件契约；`is-sending` 为纯 CSS 动画类 |
| 不恢复旧导航/Galaxy | grep 确认无 `app.js`/`main-orb.js`/`galaxy`/`three` 引用 |
| 不引入 Dashboard/卡片墙 | Context 三句、Overlay 行式，均未引入数字卡片 |
| 不做多页面 | 仍为单空间 + Overlay |

## 八、改动规模

| 文件 | 行数 |
|---|---|
| index.html | 109 |
| ui-v4.css | 627 |
| js/overlay.js | 206 |
| js/intent-line.js | 109 |
| js/world-understanding.js | 90 |
| js/boot.js | 52 |
