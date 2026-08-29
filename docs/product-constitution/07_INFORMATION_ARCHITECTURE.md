# 07 · 信息架构（Information Architecture）

> 依赖：05（暴露级别）、06（交互面职责）、能力真相（`03_ENTRY_MAP.md` 入口）
> 红线：仅定义信息层级；不引入新页面、不改动代码、不重定义能力真相。

---

## 1. 分层模型

信息架构按"用户访问频率 + 暴露级别（05）"组织为六层。越常用越浅，越专业越深。

| 层 | 名称 | 内容 | 对应交互面 |
|---|---|---|---|
| L1 | **最常访问（Surface）** | 对话、Galaxy 背景、Dock、Companion、晨间简报 | Chat / Galaxy / Dock / Companion |
| L2 | **第二层（On-Demand）** | 指令中心、业务面板（天气/监控/记忆/知识）、目标管理 | Command Palette / Panel |
| L3 | **第三层（Contextual）** | 场景卡、执行监视、Glance、HUD、详情 | Overlay / Panel |
| L4 | **后台（Ambient）** | 状态投影、Watcher、Proactive 扫描、自检 | 系统状态 / Notification 角标 |
| L5 | **系统/开发者（System/Dev）** | 设置、权限、能力清单 API、审计页、自检页 | Settings / Developer API |
| L6 | **权限/专家（Permission/Expert）** | 高危动作确认、专家模式、跨端/感知实验开关 | Overlay 确认 / T4 设置 |

---

## 2. 各层详述

### L1 最常访问（首屏即达）
- 对话输入框（Chat）、Galaxy 可视化、底部 Dock（输入/语音/截图/拖文件）、Companion 浮窗、简报入口。
- 原则：零学习成本；用户打开即拥有核心闭环（说/看/做）。

### L2 第二层（召唤即达）
- **Command Palette（Ctrl/Cmd+K）**：唯一指令中心，聚合 T0/T1 能力（面板 10 + 主题 6 + 功能 4 + 创建 3 + 系统 2 + 自由意图）。
- 业务面板：天气观测、系统监控、实时热点、文档库、记忆网络、长期记忆、地图、设置。
- 目标管理：新建目标/待办/提醒。

### L3 第三层（上下文）
- 场景卡（SSE 驱动）、执行监视、Glance、HUD。
- 模态层（Overlay）：权限确认、沉浸视觉、详情。

### L4 后台（无感）
- AppState 只读投影（Galaxy/Overlay/Computer/Perception State）。
- knowledge Watcher、Proactive tick、启动 self_check。
- 不以界面形式打扰，仅以角标/未读累积（Notification）。

### L5 系统/开发者
- 设置面板（`,` 或 `#settingsOpenBtn`）：主题、FEATURE 开关、TTS、自动朗读。
- 开发者：能力清单 `/api/capabilities`、工具审计、自检页 `selfcheck.html`。

### L6 权限/专家
- 高危动作确认（Overlay 模态，P-SAFE）。
- 专家模式：跨端接力、感知实验、Social 接入配置（T4）。

---

## 3. 导航原则

1. **唯一指令入口**：所有"找功能"经由 Command Palette；不设第二入口。
2. **深度有界**：任何信息 ≤ 3 次操作可达（L1→L2→L3）；L5/L6 属专家，可更深。
3. **上下文优先**：相关信息就近呈现（场景卡随对话、执行监视随任务），不强迫跳转。
4. **不迷失**：任何层都有"回到 L1"的显式路径（Esc 关闭栈顶 / Companion 回主窗）。

---

## 4. 与能力暴露的对应

- T0 能力 → L1/L2。
- T1 能力 → L2（指令中心）。
- T2/T3 能力 → L4（后台/角标）。
- T4 能力 → L5/L6（设置/专家）。

---

## 5. 现实约束（诚实）

- **页面仅 5 个**：index/companion/mobile-app/selfcheck/weather-modal-preview（`03_ENTRY_MAP.md` §二）。信息架构不得假设更多原生页面；新增页面须作为能力立项。
- **无 CLI / 无 Electron 入口**：架构仅浏览器+HTTP；命令行/原生菜单不在当前信息架构内。

---

## 6. 本文向下约束

- 08 用户心智模型的"小6由哪些部分组成"须与本分层一致。
- 09 AI 行为中"把信息放哪层"须符合本架构（建议→L2/L4，确认→L6）。
- 10 路线图中 Desktop Shell/Mobile 须扩展本分层而非另建。
