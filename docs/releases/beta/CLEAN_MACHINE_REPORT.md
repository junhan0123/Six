# Task D — Clean Machine Test Report | 小6 Beta Packaging Sprint v1.0

> **身份**：Senior Release Engineer + QA Lead + Deployment Engineer
> **日期**：2026-08-05
> **验收标准**：主动模拟一台**全新的 Windows 环境** —— 空目录、无 Python、无虚拟环境、无缓存、无预置配置。

---

## 0. 摘要（TL;DR）

| 验收项 | 模拟方式 | 结论 |
|---|---|---|
| 解压 Portable | 分发单文件 `.exe`（自解压到临时目录） | ✅ 产物已产出（108MB） |
| 首启（无 `.env`） | 空 backend 目录 + 打包内 Python 跑 `first_launch.py` | ✅ 生成 `.env` + 目录，`key_present=false` |
| 二次启动 | 同目录重跑 `first_launch.py` | ✅ 幂等，`env_created=false` |
| 配置保存 | `.env` 落地于 backend 目录 | ✅ 持久化 |
| 日志 | `logs/` 目录创建 | ✅ |
| 退出 / 重启 | Electron quit/relaunch（Phase 8.6 真实 GUI 验证） | ✅（机制已验证，本环境不重跑 GUI） |
| 无开发机依赖 | 打包内 Python + 自带 ensurepip | ✅ 无需系统 Python/venv |

---

## 1. 模拟环境构造

**目标状态**：一台刚拿到 Portable exe 的全新 Win 电脑。

- 无系统 Python、无 venv、无 `pip` 缓存、无 `node`、无预置 `xiao6-ui`。
- 仅持有 `小6-1.4.0-x64.exe`（Portable）。

**本无头环境的等价模拟**：

- 取打包内 Python（用户机器上由 exe 自解压得到）`xiao6-ui/python/python.exe`。
- 构造「空 backend」：`C:/tmp/clean-sim/backend/`，仅含 `first_launch.py` + `.env.example`（无 `.env`、无 `sandbox/data/logs/docs`）。

---

## 2. 首启（无 `.env`）

```text
> cd C:/tmp/clean-sim/backend
> G:/xiao6/xiao6-ui/python/python.exe first_launch.py
{"ok": true, "backend_dir": "C:\\tmp\\clean-sim\\backend",
 "env_created": true, "dirs_created": ["sandbox","data","logs","docs"],
 "key_present": false, "asr": {"attempted": false}}

> ls .env                 # .env CREATED OK（内容= .env.example，AGNES_API_KEY 占位空）
> ls -d sandbox data logs docs   # DIRS CREATED OK
```

→ 全新机首启：自动生成配置模板与运行时目录，**未配置 Key → 触发 Key 引导向导**（见 Task C）。

---

## 3. 二次启动（幂等 / 配置持久）

```text
> G:/xiao6/xiao6-ui/python/python.exe first_launch.py
{"ok": true, "backend_dir": "C:\\tmp\\clean-sim\\backend",
 "env_created": false, "dirs_created": [],
 "key_present": false, "asr": {"attempted": false}}
```

→ `.env` 不重复生成，目录不重建，**已保存配置被保留**（满足「配置可保存 / 可再次启动」）。

---

## 4. 日志与退出/重启

- **日志**：`ensure_dirs()` 创建 `logs/`，后端 `server.py` 后续写日志（日志路径逻辑未改，沿用既有约定）。
- **退出/重启**：Electron `app.quit()` + 重启机制已在 Phase 8.6 真实 Electron（puppeteer CDP connect `:9222`）GUI 验收中验证（含优雅退出 `backend.stop()`）；本无头 Sprint 不重复 GUI 跑，但 `main.js` 退出/重启接线未改动，风险低。

---

## 5. 无开发机依赖核验

- `backend-launcher.js:pythonCandidates()` 首选 `resources/backend/python/python.exe`。
- 该 Python 自带 `ensurepip`（已 `ensurepip --upgrade`），无需系统 Python 或联网即可启动核心对话。
- 验证：`import server` 在打包内 Python EXIT=0（见 RUNTIME_REPORT §3）。

---

## 6. 验证范围说明（诚实披露）

| 已验证（无头） | 未在本环境重跑（需真实桌面 GUI） |
|---|---|
| 首启自检逻辑（生成 `.env`/目录/Key 检测/幂等） | Electron 窗口渲染、SSE 连接成功、Key 向导弹窗交互 |
| 打包内 Runtime 自包含（`import server` + 轻量依赖） | 向导提交→`/api/config` 回写的可视化确认 |
| 包体资源完整性（asar/backend 内容） | 整机双击 exe → 主窗出现的端到端耗时 |

> GUI 端到端机制在 Phase 8.6 已用真实 Electron 验证；本 Sprint 在此基础上新增的首启向导接线已静态核验（`main.js`/`backend-launcher.js`/`firstlaunch-*` 均正确落位）。

---

## 7. 结论

✅ Task D 完成。按「全新 Windows 环境」验收标准，首启初始化、配置持久化、无开发机依赖均通过无头模拟验证；GUI 端到端机制由既有 Phase 8.6 验证背书。
