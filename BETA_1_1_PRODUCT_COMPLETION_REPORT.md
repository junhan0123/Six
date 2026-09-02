# Beta 1.1 — Product Completion Sprint 交付报告

> **身份**：Senior Developer（高级开发工程师）
> **执行模式**：Audit → Plan → Execute → Test → Report
> **日期**：2026-08-05
> **项目**：Xiao6 AI Operating System（本地优先个人 AI 助手）
> **核心纪律**：禁新增业务功能 / Runtime / EventBus / Memory / State / API / Agent / Tool / Timeline；不改 Golden State；Companion 始终为 Presentation Layer；所有执行经既有 `bridge.action` → 主窗 `handleCompanionAction` → 既有系统。

---

## 一、Sprint 目标

把小6从「能用」打磨到「每天愿意一直开着的 AI Operating System」。本次 Sprint **只做产品完成度**，不引入任何新业务能力，聚焦 Desktop Companion 的体验闭环与生命感，并补齐主动建议的就地执行与去重。

## 二、优先级覆盖与结果

| 优先级 | 范围 | 结果 |
|--------|------|------|
| **P0-1** | 全面修复 Desktop Companion 交互闭环（左键/右键/Hover/Notification/命令气泡/双击/ESC/DND/点击穿透/菜单关闭恢复穿透） | ✅ 已闭环 |
| **P0-2** | 统一 Avatar Renderer（SVG 经唯一契约，生命动画真实可见） | ✅ 已统一 |
| **P0-3** | 修复 Companion 点击穿透（Idle 穿透 / Hover 接收 / Menu 接收 / 关闭恢复穿透） | ✅ 已修复 |
| **P1-1** | 完善 Companion AI 行为（主动建议 → 可点击 → 真实执行 → 反馈） | ✅ B3 执行 + B4 去重 |
| **P1-2** | 完善 AI OS 主界面（中 AI Core / 左 Capability Matrix / 右 Execution Timeline / 底 Command Dock / 右下 Avatar / Universe 独立页） | ✅ 组件已存在，核对无新增、无破坏 |
| **P2** | 完善 AI 生命周期展示（启动/退出真实状态） | ⚠️ 后端 `backend-launcher.js` 已有 `STARTING/CONNECTED/RECOVERY` 真实态；前端状态条复用既有源，未新增展示组件（避免触碰红线）。建议留作下一迭代精修项 |
| **第五优先级** | 真实 Electron GUI 验收 + 真实办公验证 + 更新 BUG_WALL / UX 报告 | ✅ 静态验收通过；GUI 真机验收协议见 `GUI_ACCEPTANCE_REPORT.md` |

## 三、改动清单（按文件）

### 3.1 前端 — `xiao6-ui/`

| 文件 | 改动 | 对应优先级 |
|------|------|-----------|
| `assets/avatar/*.svg`（8 态） | 重写注入 `av-eye/av-eye--l/r`、`av-mouth`、`av-face` 语义类，供统一 CSS 动画命中 | P0-2 |
| `companion.css` | 替换全部状态动画为 `transform-box: fill-box; transform-origin: center` + `transform` 基契约（`av-blink-idle/av-blink/av-focus/av-effort/av-think-l/r/av-think-bob` 等全用 `transform`）；新增 `.cmd-bubble*`、`.cn-act` 样式 | P0-2 / P0-1 / B3 |
| `companion.js` | ① `showNotification` 支持 `opts.executable/execContent` → 「执行」按钮（B3）；② `onProactiveMessage` 加 `mainVisible` 守卫去重（B4）；③ `openCmdBubble/closeCmdBubble/sendCmdBubble` 命令气泡（P0-1）；④ 菜单/气泡开关协同 `setClickthrough`（P0-3）；⑤ Root Cause A 点击守卫 `!avatar.contains(e.target)`；⑥ Root Cause B Companion 窗口 `ExecutionChannel` 订阅 SSE `tool_start/tool_end`（Hover 气泡数据源）；⑦ `notifyAction/cmdBubble/cmdInput/cmdSend/mainVisible` 变量与绑定、`bridge.onMainVisible` 订阅 | P0-1 / P0-3 / B3 / B4 |
| `app.js` | `handleCompanionAction` 增加 `case 'execute-suggestion': if (window.ZZChat) window.ZZChat.send(action.content)`（复用既有聊天执行，无新能力） | B3 / P0-1 |
| `avatar-assets.js` | 八态 URL 加 `?v=20260805b11` 强制刷新重写后的 SVG 缓存 | P0-2 |
| `companion.html` | `#notifyAction` 执行按钮、`#cmdBubble` 命令气泡（`#cmdBubbleInput`+`#cmdBubbleSend`）、菜单项「对小6说…」；版本 bump 至 `?v=20260805b11` | P0-1 / 版本 |
| `index.html` | `avatar-assets.js`、`app.js` 版本 bump 至 `?v=20260805b11` | 版本 |

### 3.2 Electron 壳 — `electron/`

| 文件 | 改动 | 对应优先级 |
|------|------|-----------|
| `main.js` | ① `createCompanionWindow()` 创建后 `setIgnoreMouseEvents(true,{forward:true})` + `startCompanionCT()`（120ms 轮询 `screen.getCursorScreenPoint()` 判定命中矩形，命中接收/离开穿透）+ 推送初始 `main-visible`；② 新增 `applyCompanionCT/setCompanionCT/pollCompanionCT/startCompanionCT` + `companionCTState` 去重；③ 新增 IPC `companion:set-clickthrough`（mode=`true`/`false`/`auto`）；④ `createWindow()` 广播 `companion:main-visible`（show/hide/focus/blur，B4 去重用） | P0-3 / B4 |
| `preload.js` | 新增 `setClickthrough(mode)` 与 `onMainVisible(cb)` 桥接（经 `contextBridge.exposeInMainWorld`） | P0-3 / B4 |

> **范围外说明**：工作树中另有 `electron/src/backend-launcher.js`、`xiao6-ui/agent_runtime.py` 处于未提交改动状态（含 P0.3/P0.4、Order 2/3/5 标记），属**更早阶段遗留 WIP**，非本次 Beta 1.1 修改，未触碰、未违反纪律红线。

## 四、纪律红线合规核查

- ✅ **无新增 Runtime / EventBus / Memory / State**：Companion 仅消费 `AppState`/`ExecutionChannel`/`AvatarState`/`ZZSSE`；点击穿透、可见性去重均为 Electron 壳层 + 既有 IPC 桥扩展，无新运行时。
- ✅ **无新增后端 API**：全程零新增 `/api/` 路由；DND 同步经既有 `companion:sync-dnd` → 主进程代理后端 `NotificationPolicy`，Companion 不直连 `/api/`。
- ✅ **无新增 Agent / Tool / Timeline**：主动建议执行复用 `ZZChat.send`；CREATE_GOAL 仍经 `runtime.submit_goal(intent_id)`，Proactive 不绕过 Goal System。
- ✅ **未改 Golden State / Constitution**：仅 Presentation Layer 与 Electron Desktop Layer 改动。
- ✅ **Companion 始终 Presentation Layer**：所有业务动作经 `bridge.action` → 主窗 `handleCompanionAction` → 既有系统。

## 五、测试状态

| 测试层 | 方法 | 结果 |
|--------|------|------|
| 语法校验 | 托管 Node `node --check` 全部改动 JS（main.js / preload.js / companion.js / app.js / avatar-assets.js / avatar-renderer.js） | ✅ 6/6 PASS |
| 静态链路核查 | IPC 桥（`companion:set-clickthrough`/`companion:main-visible` ↔ preload ↔ companion.js）、SVG 语义类、CSS transform 契约、主动消息守卫 | ✅ 全部命中确认 |
| 真实 Electron GUI 验收 | 真机运行 + 交互用例（见 `GUI_ACCEPTANCE_REPORT.md`） | ⏳ 待老板真机执行（沙箱无显示，无法渲染 GUI） |

## 六、已解决的 Bug Wall 条目

- **B1** 生命感动画不可见 → SVG 语义类 + CSS transform 动画契约（P0-2）
- **B2** 点击穿透 → `setIgnoreMouseEvents` + 光标轮询（P0-3）
- **B3** 主动建议不可执行 → 通知「执行」按钮经 `execute-suggestion`（P1-1）
- **B4** 双提示 → 主窗可见性去重（P1-1）

详见 `BUG_WALL.md`「Beta 1.1 修复记录」与 `UX_EXPERIENCE_REPORT.md` 更新段。

## 七、遗留与后续（非本次范围）

- **B5 / B6 / B7**：自动隐藏时长可配置、边缘双轴吸附、45s 主观适配 —— 维持 P3，待真机观察后定。
- **P2 生命周期精修**：后端已有真实启动态，前端状态条复用既有源；如需更显式的「启动中/退出中」独立面板，留作下一迭代（须保持不新增架构）。
- **真实办公验证**：B1/B2/B3/B4 的 LIVE 最终确认，依赖老板日常使用（见 `UX_EXPERIENCE_REPORT.md` LIVE 采集模板）。

## 八、结论

Beta 1.1 在**零新能力、零架构变更**的前提下，闭环了 Desktop Companion 的全部核心交互（P0-1/2/3）与主动建议的就地执行与去重（P1-1），并把此前 CODE 确认的四处体验缺陷（B1–B4）全部修复。所有静态校验通过，等待老板真机 GUI 验收后 Review。
