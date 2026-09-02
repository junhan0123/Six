# 03 · 入口地图（Entry Map）— Stage C

> 扫描**所有入口**，覆盖：首页 / Command / Chat / 菜单 / Dock / 快捷键 / Electron(无) / 右键 / 设置 / API / URL / CLI / 自动触发 / Proactive。
> 核心发现：**不存在 Electron 入口**（无托盘/菜单栏/IPC）。所有"桌面入口"实为浏览器事件。

---

## 一、入口总览

| 入口类型 | 数量 | 落地 |
|---|---|---|
| 首页/页面 | 5 | index/companion/mobile-app/selfcheck/weather-modal-preview |
| 指令中心命令 | ~30 | command-palette.js |
| Chat 输入 | 1 | #userInput + 发送 |
| 菜单(右键/伴侣) | 1 主 | companion.html #quickMenu |
| Dock | 1 | command-dock.js #osDockBar |
| 快捷键 | ~8 | 见下表 |
| 设置 | 1 | settings.js / #settingsOpenBtn |
| API(HTTP) | ~73 | server.py |
| URL 路由 | =API | server.py 路由 |
| CLI | 0 | 无命令行入口(仅启动 bat) |
| Electron | 0 | **不存在** |
| 自动触发 | 多 | proactive tick / SSE 事件 / watcher / scheduler(未接线) |
| Proactive | 多 | PRO-01..05 |

---

## 二、页面/视图入口

| 入口 | 文件 | 触发方式 | 对应能力 |
|---|---|---|---|
| 主桌面应用 | index.html | 浏览器打开 :8000 | UI-01, CONV-01, 各面板 |
| 桌面伴侣 | companion.html | 常驻浮窗 | UI-02, 伴侣菜单 |
| 移动伴随端 | mobile-app.html | PWA(默认 off) | UI-03 |
| 自检测页 | selfcheck.html | 设置内引用 | SYS-06 |
| 天气预览页 | weather-modal-preview.html | 开发预览 | EXT-02(预览) |

---

## 三、指令中心（Command Palette）入口 — `command-palette.js`（唯一，无重复）

> 触发：Ctrl/Cmd+K。命令由 `buildCommands()` 本地数组 `c.push(...)` 构建（非插件式注册）。分 4 段。

| 段 | 命令示例 | 能力入口 |
|---|---|---|
| 面板(10) | 实时热点/天气观测/系统监控/终端日志/每日简报/文档库/记忆网络/查询长期记忆/地图/设置 | 对应 UI 面板 + EXT |
| 主题(6) | 深空青/极光绿/霓虹紫/熔岩橙/霓虹粉/白昼 | SET-02 |
| 功能(4) | 沉浸视觉/知识平台/主动智能V2/多端同步 | SET-03(切 FEATURE_*) |
| 创建(3) | 新建目标/待办/提醒 | GOAL-01 / TOOL-08 / TOOL-07 |
| 系统(2) | 聚焦对话输入/关闭所有面板 | UI |
| 意图 | 自由文本 → Intent Gateway | GOAL-05 |

---

## 四、Chat 入口

| 入口 | 文件 | 能力 |
|---|---|---|
| 输入框 #userInput | index.html/app.js | CONV-01 |
| 发送按钮 #btnSend | index.html | CONV-01 |
| 语音输入 #btnMic(mic-overlay) | app.js | PERC-06/07 |
| 自动朗读 #btnTts | index.html | SET-02(autoTts) |

---

## 五、菜单 / Dock 入口

| 入口 | 文件 | 触发 | 能力 |
|---|---|---|---|
| 伴侣右键菜单 #quickMenu | companion.html | 右键头像 | 打开主窗/对小6说/当前任务/系统状态/记忆/项目/快速指令/设置/暂停动画/勿扰/隐藏 |
| 指令坞 #osDockBar | command-dock.js | 点击 | 语音/文本/拖文件/截图/快捷命令/发送 |
| 主窗按钮 | index.html | 点击 | 简报#btnBriefing/记忆#btnMem/天气#wxOpenBtn/热点#hsOpenBtn/设置#settingsOpenBtn |

---

## 六、快捷键入口

| 快捷键 | 动作 | 文件 | 状态 |
|---|---|---|---|
| Ctrl/Cmd+K | 开关指令中心 | command-palette.js | 活跃 |
| Esc | 关闭栈顶 overlay / 各遗留面板 / 伴侣菜单 | overlay-manager.js + 各 panel | 活跃(18+ 去中心化监听) |
| `,`(逗号) | 打开设置 | app.js | 活跃 |
| `/` | 聚焦输入框 | app.js | 活跃 |
| Enter | 发送/指令提交 | app.js / companion.js | 活跃 |
| ↑/↓ | 指令中心导航 | command-palette.js | 活跃 |
| 伴侣单击/双击 | 菜单/开主窗 | companion.js | 活跃 |
| Ctrl/Cmd+U | "打开宇宙视图"(仅提示文字) | command-dock.js | **疑似未实现/死快捷键** |

---

## 七、设置入口

| 入口 | 文件 | 能力 |
|---|---|---|
| 设置面板 #settingsOpenBtn / `,` | settings.js | SET-02/03 |
| 配置 API | /api/config | SET-01 |

---

## 八、API 入口（HTTP，全部 localhost-only 门控）

> 详见 01 速查。约 73 路由，本机放行、非本机需 `REMOTE_ACCESS_TOKEN`。SSE 两处：`/api/chat`、`/api/stream`。
> 代表性入口：`/api/chat`(对话) / `/api/agent/goal`(目标) / `/api/agent/intent`(意图) / `/api/social/inbound`(社交入站) / `/api/capabilities`(开发者) / `/api/config`(设置)。

---

## 九、自动触发 / Proactive 入口

| 触发 | 机制 | 能力 |
|---|---|---|
| 主动心跳 | proactive.tick_loop(TICK→scanners) | PRO-01..04 |
| SSE 事件扇出 | eventbus → /api/stream → 前端订阅 | CONV-03 下游(场景卡/执行监视/Glance/HUD) |
| 文件监听 | knowledge Watcher(Win) | KNOW-06 |
| 任务恢复 | 启动 recover_tasks() | GOAL-12 |
| 自检测 | 启动 self_check | SYS-06 |
| 常驻伴随 | always_on(默认 off) | SYS-08 |

---

## 十、CLI / Electron 入口

| 类型 | 是否存在 | 说明 |
|---|---|---|
| CLI 命令 | 否 | 仅有 `start-xiao6.bat` 启动脚本，无功能 CLI |
| Electron 托盘/菜单栏/IPC | **否** | 全仓无 `electron/` 目录、无 `require('electron')`、无 `BrowserWindow`/`ipcMain`/`new Tray`/`app.dock`。所谓"桌面应用"是浏览器渲染 + Python http.server 托管。 |

> ⚠️ 影响：任何依赖"Electron 原生能力"（系统托盘、全局快捷键、原生菜单、主进程 IPC、开机自启）的设计**目前均无落地基础**。如需，应作为新能力立项（不在本审计范围）。

---

## 十一、入口重复/缺口

- **入口重复**：多个 UI 面板可由"按钮 + 指令中心 + 伴侣菜单"三处触发（同一能力多入口，属正常）；但 Toast/Overlay 的**渲染入口重复**（5+/12+）属需收敛。
- **入口缺口**：Scheduler 无入口；Planner/Workflow 无入口；`personalization.py` 无入口（死代码）；`Ctrl/Cmd+U` 提示但无处理。
- **入口风险**：18+ 去中心化 ESC 监听（各 panel 各自绑定），焦点管理分散。
