# 小6 v2 Phase 7 开发计划 — 体验升华与产品化

> 制定时间：2026-08-01
> 制定人：Senior Developer（高级开发工程师）
> 代码基线：`7674a31`（Phase 6 完成：能力对比重做 + Skills 内容填充）
> 前置：Phase 1–6 已落地（Context Engine / 世界模型 / 人格源 / 目标系统 / 沉浸视觉 / 知识 RAG / 主动智能 V2 / 多端同步 / 健壮性收尾 / 白龙马能力与 Skills）

---

## 一、当前状态

- **已落地**：Phase 1–6 全量入库。零密钥能力已对标并反超白龙马（详见 `小6vs白龙马_能力对比_2026-08-01.md`）。
- **工作树**：干净。仅余运行数据缓存（`geo-weather.json` / `habits.json` / `devices.json` / `../Xiao6-v2-后续开发计划.md` 未跟踪计划文档），非源码。
- **已知基础骨架**：`command-palette.js`（Ctrl/Cmd+K）已接入 `index.html`，但只是「只开面板」的基础版——11 条命令、无分类/键盘导航/模糊排序、无主题与功能开关入口、样式朴素、且 `styles.css` 中 `.cp-*` 存在重复定义块。

## 二、Phase 7 目标

把小6从「功能齐全」推向「体验升华、可产品化」：全局指令中心、数据自主、首启引导、可分发包。

---

## 三、任务清单

### P7-1 · 全局指令中心升级 ⭐ 首项开整
**现状**：`command-palette.js` 仅开面板，无键盘导航/分类/主题/功能开关。
**方案**：
- 分类（面板 / 主题 / 功能 / 创建 / 系统）+ 模糊搜索排序 + 分类标题。
- 键盘导航：↑↓ 移动、Enter 执行、Esc 关闭、激活高亮 + 滚动跟随。
- 真实桥接：
  - 面板（9）：`ZZHotspot` / `ZZDoc` / `ZZMemory` / `ZZMap` / `ZZSysmon` / `ZZTerminal` / `ZZWorldClock` / `ZZSettings` + `#wxOpenBtn` / `#btnBriefing`。
  - 主题（6）：`ZZSettings.set({theme})` + `POST /api/config {XIAO6_THEME}`。
  - 功能（4）：`POST /api/config {FEATURE_*}`，开面板时 `GET /api/config` 拉真实状态显示「开/关」。
  - 创建（3）：预填 `userInput`（设定目标/添加待办/提醒我），交给 LLM 走工具循环，零后端改动。
- 样式升级：玻璃拟态 + 入场动效 + 激活辉光；清理 `styles.css` 重复块。
- 验收：`node --check`；Ctrl K 开合、方向键选中、主题/功能实时生效、关闭后不残留。

### P7-2 · 数据管理面板（导出 / 导入 / 重置）
- 前端：导出记忆/设置/目标为 JSON、导入恢复、重置本地缓存（`localStorage`）。
- 后端（gated）：`/api/data/export` | `/api/data/import` 服务端数据备份（复用 `db.py`）。
- 设置面板新增「数据管理」分组。

### P7-3 · 首次启动引导（Onboarding）
- 首启欢迎 + 快速设置（AI 名字、主题、语音/主动智能开关）。
- `localStorage` 标记已引导；设置里可「重新引导」。纯前端、零密钥。

### P7-4 · 部署打包（Electron build + 启动健壮性）
- Electron 打包脚本（electron-builder 配置）。
- 后端启动健壮性：端口占用处理、异常自动重启、结构化日志。
- 离线能力确认；可选自更新通道。

---

## 四、执行纪律（沿用）

- 纯本地 git，小步提交、确认后入库；不推翻 Phase 1–3 架构。
- 新增能力默认开、FEATURE flag 门控、可瞬切。
- 前端改动后 **bump `index.html` 的 `?.js?v=` / `?.css?v=`**；重启 Electron + Ctrl+F5 强刷生效。
- 真机验证：改完请你重启后端走查，我据反馈定点修。

## 五、建议执行顺序

1. **P7-1**（本迭代）：命令面板升级，一次性提交。
2. **P7-2 → P7-3**：数据自主 + 首启引导。
3. **P7-4**：部署打包（收尾，产出可分发包）。
