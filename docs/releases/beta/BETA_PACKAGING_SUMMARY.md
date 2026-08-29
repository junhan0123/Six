# Beta Packaging Sprint v1.0 — Final Summary | 小6

> **身份**：Senior Release Engineer + Packaging Engineer + Deployment Engineer
> **执行模式**：Audit → Plan → Execute → Verify → Report → **STOP（等人工 Review）**
> **日期**：2026-08-05
> **结束条件**：完成全部验证后 STOP，等待人工 Review；**未经批准不得进入 GA**。

---

## 1. Sprint 目标

完成第一版可分发 Beta，让一台**全新 Windows 电脑**能成功运行（非新增功能，仅发布工程）。

---

## 2. 七大任务交付物

| Task | 交付物 | 状态 |
|---|---|---|
| A Packaging | `docs/releases/beta/PACKAGING_REPORT.md` + 产物 `electron/dist/小6-1.4.0-x64.exe` | ✅ |
| B Runtime | `docs/releases/beta/RUNTIME_REPORT.md` | ✅ |
| C First Launch | `docs/releases/beta/FIRST_LAUNCH_REPORT.md` | ✅ |
| D Clean Machine | `docs/releases/beta/CLEAN_MACHINE_REPORT.md` | ✅ |
| E Validation | `docs/releases/beta/BETA_VALIDATION_REPORT.md` | ✅ |
| Final | `docs/releases/beta/BETA_PACKAGING_SUMMARY.md`（本文件） | ✅ |

---

## 3. 核心交付（代码/产物变更）

### 新增文件（均在纪律红线内：首次启动流程 / 配置初始化 / 发布工程）
- `xiao6-ui/first_launch.py` — 首启初始化（纯标准库，退出码恒 0）
- `xiao6-ui/.env.example` — 配置模板（首启据此生成 `.env`）
- `electron/firstlaunch.html` — Key 引导窗（premium 风格）
- `electron/firstlaunch-preload.js` — 隔离 contextBridge 白名单

### 修改文件
- `electron/src/backend-launcher.js` — 新增 `runFirstLaunch()`，`firstLaunch` 贯穿全部 return
- `electron/main.js` — 首启状态变量 + `firstlaunch:submit-key`/`skip` IPC + 向导窗 + 启动流接线
- `xiao6-ui/requirements.txt` — 显式声明 `numpy>=1.24.0` 与 `sounddevice`（可复现）
- `xiao6-ui/.gitignore` — 忽略 `python/`（防打包内解释器入库）
- `electron/package.json` — `version` 1.0.0→1.4.0（与 `config.py` 统一）；`extraResources` 过滤器精炼 + 防御性排除

### 产物
- `electron/dist/小6-1.4.0-x64.exe`（108,198,200 B ≈ 103 MB，Portable）

---

## 4. 验收结论

**Beta Validation 七项：7/7 达成**（可分发 / 可启动 / 可退出 / 可再次启动 / 配置可保存 / 日志正常 / 无开发机依赖）。

**全新 Windows 验收模拟通过**：首启自动生成 `.env` + `sandbox/data/logs/docs`，`key_present=false` 触发向导；二次启动幂等配置持久；打包内 Python 3.11.9 免系统依赖。

---

## 5. 已知限制（诚实披露）

1. **GUI 端到端未在无头环境重跑**：Electron 窗口渲染 / SSE `CONNECTED` / Key 向导弹窗交互。机制由 Phase 8.6 真实 Electron 验证背书；本 Sprint 新增接线经静态核验。
2. **ASR 默认不装**：本地语音识别需显式安装 ~2GB 重依赖（设计取舍）。
3. **发布物料缺口（GA 阻断，非本 Sprint）**：`LICENSE` / `CHANGELOG.md` / 第三方许可聚合缺失。
4. **NSIS installer 未实跑**：仅 Portable 已验证（同 `electron-builder --win` 流程，可补产）。
5. **numpy 2.x 兼容性**：`embed.py` 若用被 2.x 移除 API 可能报错（懒加载，仅 RAG/向量路径）。建议 GA 前冒烟（仅记录）。

---

## 6. 纪律红线遵守声明

- ✅ 仅发布工程 / 打包 / Portable / Runtime 整合 / 首次启动 / 配置初始化 / 发布文档 / 自动化验证。
- ✅ 未新增业务功能、未改产品架构 / Runtime 设计 / Memory / Goal Runtime / EventBus / Planner / Tool API / 业务逻辑。
- ✅ 发现业务 Bug 仅记录（如 numpy 2.x 兼容性），未修复。

---

## 7. 后续步骤（需人工决策）

- **Review 本 Sprint 交付**（报告 + 产物 + 代码 diff）。
- 决定是否进入 GA；GA 前须补齐发布物料（LICENSE/CHANGELOG/第三方许可）与 NSIS installer 实跑。
- **未获批准，不得进入 GA。**

---

**Sprint 状态：✅ 执行完成，STOP 等待 Review。**
