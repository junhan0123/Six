# 00 · 小6能力平台 — 执行摘要（Executive Summary）

> 阶段：Capability Platform Phase v1.0
> 模式：Audit → Inventory → Analyze → Consolidate → Verify → Document → STOP
> 性质：**纯审计 / 建档 / 验证，零代码改动**（严守纪律红线）
> 审计时间：2026-08-06
> 审计范围：整个 `G:/xiao6` 项目（后端 Python + 前端原生 JS + 配置 + 文档）

---

## 一、本阶段做了什么

本阶段**不是开发**，而是把小6目前**真正拥有的一切能力**全部摸清，建立**唯一能力真相（Single Source of Truth）**。
最终产出 14 份文档，覆盖：能力清单、分类、入口地图、生命周期、重复审计、未用审计、能力关系图、能力书、用户手册、开发者手册、统计、终审。

- 全仓扫描：后端 `server.py`(73 路由) / `tools.py`(62 工具) / `ai_core/` / `context/` / `memory*` / `knowledge*` / `agent_runtime` / `goals` / `tasks` / `scheduler` / `proactive*` / `computer*` / `permission*` / `social*` / `perception*` / `capture*` 等。
- 前端：`index.html` / `app.js` / `command-palette.js` / `companion.js` / `overlay-manager.js` / `settings.js` / 各面板 JS / `mobile-app.*` 等。
- 配置：`config.py` 全部 `FEATURE_*` 开关 + `settings.js` 全部设置键。

## 二、关键结论（高信号）

1. **小6已是一个功能相当完整的本地优先 AI OS**，核心闭环（对话 → 意图 → 目标 → 执行 → 工具 → 记忆/知识/上下文 → 响应 → UI）完整可运行。
2. **重大架构事实纠正**：用户假设存在 Electron 外壳，但**全仓无 `electron/` 目录、无 `require('electron')`、无 `BrowserWindow`/`ipcMain`**。所谓"桌面应用"实为**浏览器渲染脚本 + Python `http.server` 静态托管**。"Electron"能力**不存在**，相关审计项（托盘/菜单栏/IPC）均为 0。
3. **重复 UI 子系统严重**：Toast 至少 5 套、Overlay/Modal/Dialog 管理器至少 12 套并行，统一化（OverlayManager）已建但未收口。
4. **大量"概念能力"未落地**：`Planner`、`Workflow` 在文档/注释中被描述为独立阶段/入口，但**代码中无对应模块或路由**（仅蓝图）。`scheduler.py` 完整实现却**零生产接线**（隐藏孤儿）。
5. **感知识别层全 Mock**：UIA/OCR/Vision 仅 `Mock*` 实现，真实识别未接；`perception_runtime` 未接入 `server.py`。
6. **Feature Flag 声明默认 ≠ 运行时默认**：`config.py` 顶部常量多为 `False`，但 `reload()` 以 `os.environ.get("FEATURE_X","true")` 覆盖，导致绝大多数 flag **实际默认开启**，维护者易被声明误导。
7. **死代码/孤儿模块明确可清理**：`_smts_append.py` / `_wcpc_append.py` / `_exec_regression_tmp.py` / `_tmp_log.py` / `e.txt` / `err.txt` / 各类 `.tmp` / `.bak.zzstep1` / `personalization.py` / `perception_*`（未接线）均确认无调用者。

## 三、能力数量概览（详见 11_CAPABILITY_STATISTICS）

| 维度 | 数量 |
|---|---|
| API 路由 | ~73 |
| 工具（TOOL_FUNCS） | 62 |
| DOMAIN 事件 | 71 |
| SYSTEM 事件 | 22 |
| Feature Flag（`FEATURE_*`） | ~27（含 1 幻影 1 悬空） |
| 上下文源 | 8（3 为未注册桩） |
| Overlay/Modal/Dialog 管理器 | 12+（1 权威 + 11 遗留） |
| Toast 系统 | 5+ |
| 指令中心命令 | ~30 |
| 键盘快捷键 | ~8 |
| 页面/视图 | 5 |
| 死代码文件 | ~12 |
| 重复能力组 | ~10 |

## 四、红线复核（本阶段未违反任何一条）

- ✅ 未新增功能 / 未修改业务逻辑 / 未修改 Runtime / Planner / Goal / Workflow / Memory / Knowledge / Plugin / Permission / EventBus / Prompt / Agent / API / Tool 行为 / DB / UI / CSS / JS / Python / Electron / 配置 / AI 行为。
- ✅ 未进行任何功能优化、代码重构、Rename、删除代码、顺手修 Bug、进入实现。
- ✅ 全阶段仅 Audit / Inventory / Analysis / Documentation / Verification。

## 五、交付物（14 份，详见 99_MASTER_INDEX）

`00_EXECUTIVE_SUMMARY` · `01_CAPABILITY_INVENTORY` · `02_CAPABILITY_CLASSIFICATION` · `03_ENTRY_MAP` · `04_CAPABILITY_LIFECYCLE` · `05_DUPLICATE_REPORT` · `06_UNUSED_REPORT` · `07_CAPABILITY_GRAPH` · `08_CAPABILITY_BOOK` · `09_USER_CAPABILITY_GUIDE` · `10_DEVELOPER_CAPABILITY_GUIDE` · `11_CAPABILITY_STATISTICS` · `12_FINAL_REVIEW` · `99_MASTER_INDEX`

## 六、状态

🛑 **本 Phase 为纯审计，已完成、验证通过、14 份文档齐备 —— 统一 STOP，等待人工 Review。**
