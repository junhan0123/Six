# Task B — 发布就绪复核报告 | 小6 GA Gate Review

> **身份**：Chief Software Architect + Chief Release Engineer + QA Director + Project Governance Auditor
> **Sprint**：Xiao6 GA Gate Review Sprint v1.0
> **执行模式**：Audit → Verify → Decision → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计 / 验证 / 风险评估 / 文档（仅审计结论）/ 门禁裁定；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议 / 改 UI / 优化代码 / 借机修 Bug。

---

## 0. 摘要（TL;DR）

| 发布就绪项 | 状态 | 证据 |
|---|---|---|
| Portable 单文件 | ✅ 已构建 | `electron/dist/小6-1.4.0-x64.exe`（108MB） |
| 内嵌 Python 运行时 | ✅ | `resources/backend/python/`（3.11.9）+ 轻量依赖随 extraResources 分发 |
| 首启向导 | ✅ | `first_launch.py`（纯标准库，退出码恒 0）+ `firstlaunch.html` 隔离 IPC |
| 版本一致性 | ✅ | `package.json` / `config.py` / `VERSION` / git tag 全 = 1.4.0 |
| 代码签名 | 🟡（已披露） | 无证书，未签名；SmartScreen 提示（已知限制，非阻断） |
| NSIS 安装器 | 🔄 **验证构建进行中（P-2）** | 本 Sprint 已启动 `electron-builder --win nsis`；产物 `小6-Setup-1.4.0-x64.exe` 待确认 |
| 自动更新通道 | 🟡（GA 范围外） | `CHANGELOG.md` 已声明无内置自动更新；NSIS 就地覆盖保留 userData |
| 配置恢复 | ✅ | `companion.json` / 设置（localStorage）/ DB 均落 userData，升级保留 |
| 日志 | ✅ | `first_launch.py` 创建 `logs/`；主进程日志落 `app.getPath('logs')` |

**结论：发布就绪度基本达成；唯一开放项为 NSIS 安装器产物确认（P-2，本 Sprint 验证构建中）。**

---

## 1. 复核范围

- **输入**：前序 `RELEASE_ASSETS_REPORT.md` / `CLEAN_ENVIRONMENT_REPORT.md` / `SIGNING_PREPARATION_REPORT.md`、`RELEASE_FINAL_CHECKLIST.md` §1（Beta 门禁 B-G1~B-G5）、本 Sprint Task A/C/D 发现。
- **方法**：逐项核验发布产物与发布流程在当前仓库的真实状态。
- **两极判定**：沿用前序「目标机（老板本机）vs 可分发（安装包给他人）」区分；本复核聚焦**可分发**维度（GA 要求）。

---

## 2. 发布就绪逐项核验

### 2.1 Portable 单文件（✅）
- 产物：`electron/dist/小6-1.4.0-x64.exe`（108,198,200 字节）。
- 内含：`win-unpacked/resources/backend/`（server.py + first_launch.py + 内嵌 Python 3.11.9）。
- 判定：可分发 Portable 已具备。

### 2.2 内嵌 Python 运行时（✅）
- `resources/backend/python/` 含 `python.exe` + `Lib/` + `DLLs/` + `libs/` + `LICENSE.txt` + `COPYING`。
- `CLEAN_ENVIRONMENT_REPORT` 验证：`python.exe -V → Python 3.11.9`，无系统 Python 依赖。
- 判定：干净机可独立运行，无「目标机预装 Python」前提。

### 2.3 首启向导（✅）
- `first_launch.py`：纯标准库（json/os/subprocess/sys），生成 `.env`、创建 `sandbox/data/logs/docs`、`key_present` 检测、可选 ASR 安装（默认关），退出码恒 0。
- `firstlaunch.html` + `firstlaunch-preload.js`：Key 向导隔离 IPC。
- 判定：新机首启可完成核心配置引导，无「静默失效」。

### 2.4 版本一致性（✅）
- `electron/package.json` version = 1.4.0
- `xiao6-ui/config.py` APP_VERSION = "1.4.0"
- `VERSION` = 1.4.0
- git tag `v1.4.0-当前版本`
- 判定：用户可见版本四源一致。

### 2.5 代码签名（🟡 已接受为已知限制）
- 无证书，Portable 与（待构建的）安装器均未签名。
- `SIGNING_PREPARATION_REPORT.md` 已完整披露并给出证书接入清单（OV/EV/Azure Trusted Signing）。
- 判定：SmartScreen 提示为**体验风险，非功能阻断**；如实披露即可 GA。

### 2.6 NSIS 安装器（🔄 验证构建进行中，P-2）
- 前序 GA Prep 配置了 `build.nsis.artifactName="小6-Setup-${version}-${arch}.${ext}"` 并设置 `win.target=["portable","nsis"]`，但安装器产物未产出、`INSTALLER_REPORT.md` 未写。
- **本 Sprint 行动**：启动 `electron-builder --win nsis` 验证构建（后台运行）。截至本报告撰写，构建仍在「packaging win-unpacked」阶段（嵌入式 Python 大体积复制，耗时较长），`小6-Setup-1.4.0-x64.exe` 尚未生成。
- **判定**：安装器为唯一开放发布就绪项（P-2）。构建完成后的产物确认将追加至本报告（见 §4 更新说明）。
- **风险**：若构建最终失败，则「可分发安装器」暂缺，须作为 GA 公告前必须关闭项（Portable 仍可分发，故非功能性阻断）。

### 2.7 自动更新通道（🟡 GA 范围外）
- `CHANGELOG.md` 已声明「无内置自动更新通道（GA 范围外）；升级通过 NSIS 就地覆盖并保留用户数据」。
- 判定：已文档化，非 GA 阻断。

### 2.8 配置恢复 / 日志（✅）
- 设置（localStorage）、桌宠态（companion.json）、业务数据（xiao6.db）均落 userData → 升级/重装保留。
- `first_launch.py` 创建 `logs/`；主进程日志写 `app.getPath('logs')/xiao6-backend.log`。
- 判定：配置保留与日志目录就绪。

---

## 3. 与前序 Beta 门禁（B-G1~B-G5）对齐

| Beta 门禁 | 前序状态 | 本 Sprint 复核 |
|---|---|---|
| B-G1 实际产出安装包 | ⛡ 未做 | 🟡 Portable ✅；NSIS 🔄 验证中（P-2） |
| B-G2 干净机启动 | ⛡ 未做 | ✅ 内嵌 Python + first_launch 验证 |
| B-G3 干净机首启 Key 引导 | ⛡ 未做 | ✅ first_launch + 向导 |
| B-G4 依赖声明可复现 | ⛡ 未做 | ✅ requirements.txt 已声明 numpy/sounddevice（R-B1/B2 CLOSED） |
| B-G5 无启动级 Blocker | ✅ | ✅ 维持（P0=0） |

> 前序 5 项 Beta 门禁中，B-G2/B-G3/B-G4/B-G5 已实质满足；B-G1 的 Portable 已满足，NSIS 待确认（P-2）。

---

## 4. 结论与更新说明

**发布就绪度：基本达成。** Portable / 内嵌运行时 / 首启 / 版本 / 配置恢复 / 日志 均已验证就绪；代码签名已披露（非阻断）；自动更新已文档化（GA 外）；**唯一开放项 = NSIS 安装器产物确认（P-2）**。

> **更新说明**：本报告撰写时 NSIS 验证构建仍在后台运行。构建完成（成功/失败）后，将在此追加一条确认记录，更新 §2.6 与 §3 的 B-G1 状态，并相应调整 Task E 裁定的第一优先级措辞。若构建失败，P-2 升为 GA 公告前必须关闭项（Portable 仍可分发，非架构/功能阻断）。

---

## 5. 纪律红线遵守声明

- ✅ 仅读取 / 核验 / 启动验证构建 / 撰写报告；未改动任何业务/Runtime/EventBus/Memory/UI 代码。
- ✅ 安装器构建为发布工程验证（允许范围），非功能开发；未伪造签名、未修改架构。

---

**Task B 状态：🟡 完成（核心就绪项全绿；NSIS 安装器产物确认待补充，见 §4 更新说明）。**
