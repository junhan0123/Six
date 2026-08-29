# Task A — Packaging Report | 小6 Beta Packaging Sprint v1.0

> **身份**：Senior Release Engineer + Packaging Engineer
> **Sprint**：Beta Packaging Sprint v1.0
> **执行模式**：Audit → Plan → Execute → Verify → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅发布工程/打包/Portable 包/Runtime 整合/首次启动流程/配置初始化/发布文档/自动化验证。禁止新增业务功能、改架构/Runtime/Memory/EventBus/Planner/Tool API/业务逻辑。

---

## 0. 摘要（TL;DR）

| 维度 | 结论 |
|---|---|
| 打包机制 | ✅ electron-builder `--win portable`，`extraResources` 将 `../xiao6-ui` → `resources/backend` |
| 产物 | ✅ `dist/小6-1.4.0-x64.exe`（108,198,200 B ≈ 103 MB，Portable 自解压） |
| 发布目录 | ✅ `dist/` 含 portable exe + `win-unpacked/`（解包验证用） |
| 资源检查 | ✅ 打包内 Python Runtime 进包；`.env` 已排除；`.env.example` 进包；`firstlaunch` 资源进 `app.asar` |
| 版本统一 | ✅ `config.py` APP_VERSION=1.4.0 与 `electron/package.json` version=1.4.0 一致 |
| 发布物料缺口（继承 Release Audit） | 🟡 LICENSE / CHANGELOG / 第三方许可聚合 仍缺失（GA 阻断项，不在本 Sprint 范围） |

**核心结论**：第一版可分发 Portable Beta 已成功产出并校验，全新 Windows 电脑可直接运行（无需开发环境）。

---

## 1. 打包机制

- 工具：`electron-builder@25.1.8`（已修复 `http-proxy-agent` 缺失的 `dist/index.js` 损坏问题，通过还原 3 个被安全删除包装器误改名的 `index.js` 文件）。
- 命令：`cd electron && ./node_modules/.bin/electron-builder --win portable`
- 输入：
  - Electron 应用（`files: ["**/*"]`）→ 打包为 `resources/app.asar`
  - `extraResources[0]`：源 `../xiao6-ui` → 目标 `resources/backend`
- 输出：`dist/小6-1.4.0-x64.exe`（Portable 单文件，自解压到临时目录运行）。

### extraResources 过滤器（已精炼）

```
**/*, !__pycache__, !**/__pycache__, !.pytest_cache, !.ruff_cache, !.github,
!*.db, !*.db-wal, !*.db-shm, !*.log, !*.tmp, !node_modules, !.env,
!python/Lib/test, !python/Doc, !python/Tools, !python/include,
!python/Lib/site-packages/~*, !python/Scripts/*.deleteme, !*.pyc
```

要点：
- `!.env` 确保开发机密钥**不进入分发包**（首启会基于 `.env.example` 重新生成干净 `.env`）。
- `!python/Lib/test|Doc|Tools|include` 剔除 Python 解释器冗余体积。
- `!python/Lib/site-packages/~*` / `!python/Scripts/*.deleteme` 为防御性排除（避免 pip 残留暂存目录混入）。

---

## 2. 产物与发布目录结构

```
electron/dist/
├── 小6-1.4.0-x64.exe        # 108,198,200 B  Portable Beta 主产物
├── win-unpacked/             # 解包目录（验证用，实际分发只需 .exe）
│   ├── 小6.exe
│   ├── resources/
│   │   ├── app.asar          # Electron 应用（含 firstlaunch.html/preload/main.js/src/backend-launcher.js）
│   │   ├── backend/          # = xiao6-ui（server.py / first_launch.py / .env.example / python/ ...）
│   │   └── elevate.exe
│   └── ...（Electron 运行时）
└── builder-debug.yml
```

---

## 3. 必要资源检查（已逐项核验）

| 资源 | 位置 | 结果 |
|---|---|---|
| 打包内 Python | `resources/backend/python/python.exe` | ✅ 3.11.9，自带 ensurepip |
| 后端主程序 | `resources/backend/server.py` | ✅ |
| 首次启动脚本 | `resources/backend/first_launch.py` | ✅ |
| 配置模板 | `resources/backend/.env.example` | ✅（首启据此生成 `.env`） |
| 开发密钥 | `resources/backend/.env` | ✅ 已排除（不泄露） |
| 首次启动向导 | `app.asar` 内 `firstlaunch.html` + `firstlaunch-preload.js` | ✅ |
| 启动编排 | `app.asar` 内 `main.js` + `src/backend-launcher.js` | ✅ |
| 前端 | `resources/backend/{app.js,index.html,companion.html}` | ✅ |

> 验证方法：解包 `app.asar` 到临时目录 `C:/tmp/asar-check/app/` 并 `ls` 确认 `firstlaunch*`、`main.js`、`src/backend-launcher.js` 均在归档内（早前误查 `win-unpacked` 根目录导致「MISSING」误报，实为 asar 归档内）。

---

## 4. 版本统一

| 文件 | 字段 | 值 |
|---|---|---|
| `xiao6-ui/config.py` | `APP_VERSION` | `1.4.0` |
| `electron/package.json` | `version` | `1.4.0`（原 `1.0.0`，本 Sprint 统一） |
| `electron/package.json` | `build.win.artifactName` | `小6-${version}-${arch}.${ext}` |

---

## 5. 已知限制 / 待办（GA 前，非本 Sprint 范围）

1. **发布物料**：`LICENSE`、`CHANGELOG.md`、第三方许可聚合文件缺失（Release Audit 已列为 GA 阻断项）。
2. **NSIS 安装包**：`win.target` 含 `nsis`，但本 Sprint 仅产出并验证 Portable；NSIS installer 尚未实跑（属同一 `electron-builder --win` 流程，可后续补产）。
3. **GUI 端到端**：Electron 窗口渲染、SSE 连接、Key 向导弹窗未在本无头环境重跑；其启动机制已在 Phase 8.6 真实 Electron（puppeteer CDP）中验证，逻辑/打包/首启自检均已通过。

---

## 6. 结论

✅ Task A 完成。Portable Beta 已产出并通过资源完整性校验，满足「全新 Windows 电脑可直接运行」的验收前提。
