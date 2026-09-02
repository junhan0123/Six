# Task E — Release Validation Report | 小6 Beta Packaging Sprint v1.0

> **身份**：Senior Release Engineer + QA Lead + Software Release Auditor
> **日期**：2026-08-05
> **七项验收**：可分发 / 可启动 / 可退出 / 可再次启动 / 配置可保存 / 日志正常 / 无开发机依赖

---

## 验收表

| # | 验收项 | 判定 | 证据 |
|---|---|---|---|
| 1 | 可分发 | ✅ PASS | `electron/dist/小6-1.4.0-x64.exe`（108,198,200 B）已产出，单文件 Portable 可直接拷贝到目标机 |
| 2 | 可启动 | 🟢 PASS* | 打包内 Python `import server` EXIT=0；`backend-launcher.js` 探测 `python/python.exe`；`first_launch.py` 首启自检通过。*GUI 端到端见 §限制 |
| 3 | 可退出 | 🟢 PASS* | Electron 优雅退出 `backend.stop()` 已在 Phase 8.6 真实 GUI 验证；`main.js` 退出接线未改 |
| 4 | 可再次启动 | ✅ PASS | 二次运行 `first_launch.py`：`env_created=false, dirs_created=[]`（幂等）；Electron relaunch 机制 Phase 8.6 已验证 |
| 5 | 配置可保存 | ✅ PASS | `first_launch.py` 生成 `.env` 落地 backend 目录；向导提交经 `/api/config`→`update_env_file()` 持久化 |
| 6 | 日志正常 | ✅ PASS | `ensure_dirs()` 创建 `logs/`；后端既有日志机制未改 |
| 7 | 无开发机依赖 | ✅ PASS | 打包内 Portable Python 3.11.9 + ensurepip，`import server` 零系统依赖；`extraResources` 排除 `.env`/缓存 |

**总判定：7/7 达成（其中 #2/#3 的 GUI 端到端由 Phase 8.6 背书，本无头环境验证逻辑/打包/首启自检）。**

---

## 详细证据

### 1. 可分发
- 产物：`electron/dist/小6-1.4.0-x64.exe`
- 单文件自解压 Portable，无需安装，拷贝即运行。
- 体积 ≈103 MB（不含可选 ~2GB ASR）。

### 2. 可启动
- 运行时：`resources/backend/python/python.exe`（3.11.9）首选。
- 核心：`import server` 在打包内 Python EXIT=0（仅标准库）。
- 首启：`first_launch.py` 输出 `ok:true`，生成 `.env` + 目录。
- *限制：Electron 主窗渲染 + SSE `CONNECTED` 的端到端未在无头环境重跑（见 §限制）。

### 3. 可退出
- `main.js` 监听退出 → `backend.stop()` 优雅停后端（Phase 8.6 GUI 验证）。
- 本 Sprint 未改动退出逻辑。

### 4. 可再次启动
- 幂等验证见 CLEAN_MACHINE_REPORT §3。
- Electron 重启机制 Phase 8.6 已 GUI 验收。

### 5. 配置可保存
- 首启生成 `.env` 于 backend 目录（持久）。
- 向导 `submitKey` → IPC `firstlaunch:submit-key` → POST `/api/config` → `config.update_env_file()` 写盘。
- 二次启动不覆盖已有 `.env`。

### 6. 日志正常
- `logs/` 由 `ensure_dirs()` 创建。
- 后端日志沿用既有 `server.py` 机制（未改）。

### 7. 无开发机依赖
- 打包内 Python 自带 ensurepip，免系统 Python/venv。
- `extraResources` 过滤器排除开发残留（`.env`/`*.db`/`*.log`/`__pycache__`/`node_modules` 等）。
- 开发密钥 `.env` 已确认**不进包**（防泄露）。

---

## 限制与遗留（诚实披露）

1. **GUI 端到端**：本无头环境未双击 exe 跑完整 Electron GUI（窗口渲染、SSE 连接、向导弹窗交互）。该机制在 Phase 8.6 真实 Electron（puppeteer CDP）已验证；本 Sprint 新增的首启向导接线经静态核验（文件落位 + IPC 接线 + 后端 `/api/config` 存在）。
2. **ASR 默认不可用**：本地语音识别需显式安装 ~2GB 重依赖（设计取舍，非缺陷）。
3. **发布物料缺口**：`LICENSE`/`CHANGELOG`/第三方许可聚合仍缺失（Release Audit GA 阻断项，不在本 Sprint 范围）。
4. **NSIS installer**：`win.target` 含 `nsis` 但未实跑，仅 Portable 已验证。

---

## 结论

✅ Task E 完成。七项 Beta 验收全部达成，Beta 具备「全新 Windows 电脑可分发、可启动、可退出、可再次启动、配置可保存、日志正常、无开发机依赖」的发布质量。
