# Task E — Clean Environment Verification Report | 小6 GA

> **身份**：Senior Release Engineer + Software Delivery Engineer + QA Lead
> **Sprint**：Xiao6 GA Release Preparation Sprint v1.0
> **执行模式**：Audit → Plan → Execute → Verify → Report
> **日期**：2026-08-05
> **纪律红线**：仅验证 / 文档；无业务 / 架构 / Runtime / EventBus / Memory 改动。

---

## 1. 目标（模拟全新 Windows）

验证在一台**无 Python / 无开发环境 / 无配置 / 无缓存 / 无 venv / 无模型缓存**的全新 Windows 上：

1. 首次启动能成功初始化
2. 二次启动幂等、配置可恢复
3. 配置可保存（`.env` 持久）
4. 日志目录正常
5. Key 初始化（首启向导触发逻辑）正确
6. 卸载后重装行为安全

## 2. 方法（Execute）

- 取自打包产物 `dist/win-unpacked/resources/backend/`，用**内嵌 Python 运行时** `python/python.exe` 在隔离临时目录 `/c/tmp/zz_clean_test/` 模拟全新机（无系统 Python 参与）。
- 仅放置 `first_launch.py` / `.env.example` / `requirements.txt` 三个文件，模拟「无配置、无目录」状态。
- 运行 `first_launch.py` 并解析其 stdout 单行 JSON。

## 3. 结果（Verify）

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 内嵌 Python 可独立运行 | ✅ | `python.exe -V` → `Python 3.11.9`（无系统 Python） |
| 2 | 首次启动初始化 | ✅ | `FIRSTLAUNCH_EXIT=0`；`env_created=true`；`dirs_created=["sandbox","data","logs","docs"]` |
| 3 | `.env` 自动生成 | ✅ | 从 `.env.example` 生成 47 行 `.env` |
| 4 | Key 未配置 → 触发向导 | ✅ | `key_present=false`（主进程据此弹首启向导） |
| 5 | Key 已配置 → 不触发 | ✅ | 写入 `AGNES_API_KEY` 后重跑 `key_present=true` |
| 6 | 二次启动幂等 | ✅ | `SECOND_EXIT=0`；`env_created=false`；`dirs_created=[]`（不覆盖已有配置） |
| 7 | 核心 server 已捆绑 | ✅ | `resources/backend/server.py` 存在（130 KB） |
| 8 | 可选依赖非必需 | ✅ | `first_launch.py` 纯标准库，缺失可选依赖不阻断（exit 0） |

## 4. 六项映射

| 维度 | 判定 | 说明 |
|---|---|---|
| 首启 | ✅ | first_launch 自动建环境 + 引导 Key |
| 二次启动 | ✅ | 幂等，配置保留 |
| 配置保存 | ✅ | `.env` 落盘；用户数据（设置/记忆/桌宠）位于 userData，升级/重装保留 |
| 日志 | ✅ | `logs/` 目录创建；主进程日志写 `app.getPath('logs')/xiao6-backend.log` |
| Key 初始化 | ✅ | `key_present` 检测驱动首启向导；已验证 true/false 两态 |
| 卸载后重装 | 🟡（设计验证） | NSIS 默认**不删** userData；重装后 first_launch 幂等、不破坏既有配置。完整安装器端到端未在 headless 重跑（同 Beta 已知限制 #1），逻辑验证通过 |

## 5. 已知限制（诚实披露）

- **GUI 端到端未在 headless 重跑**：Electron 窗口渲染 / SSE / 向导交互需在带显示环境验证；机制由 Phase 8.6 真实 Electron 验证背书，本 Sprint 新增接线 + first_launch 逻辑已静态 + 隔离运行验证。
- **ASR 默认不装**：本地语音识别需显式安装 ~2GB 增强依赖（设计取舍，非阻断）。
- 卸载-重装仅做**逻辑/设计验证**（NSIS 不删 userData + first_launch 幂等），未在真实安装器流程实跑（待 Task B 安装器产物就绪后，可由人工在真机完成最终的卸载-重装冒烟）。

## 6. 纪律红线遵守声明

- ✅ 仅运行验证脚本 + 产出报告，未改动任何代码 / 配置 / 业务行为。
- ✅ 业务 Bug 仅记录，未修复。

---

**Task E 状态：✅ 完成（逻辑 + 隔离运行验证通过；GUI 端到端冒烟建议真机最终确认）。**
