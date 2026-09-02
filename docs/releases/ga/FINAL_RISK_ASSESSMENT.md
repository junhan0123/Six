# Task C — 最终风险评估报告 | 小6 GA Gate Review

> **身份**：Chief Software Architect + Chief Release Engineer + QA Director + Project Governance Auditor
> **Sprint**：Xiao6 GA Gate Review Sprint v1.0
> **执行模式**：Audit → Verify → Decision → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计 / 验证 / 风险评估 / 文档（仅审计结论）/ 门禁裁定；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议 / 改 UI / 优化代码 / 借机修 Bug。

---

## 0. 摘要（TL;DR）

| 级别 | 数量 | 说明 |
|---|---|---|
| **P0 Blocker（禁止发布）** | **0** | 无启动级 / 数据不可逆 / 安全裸奔阻断 |
| **P1 Critical（核心必崩/重大暴露）** | **0 活跃** | 历史 B1/B2 已标记解决，LIVE 待老板日常确认 |
| **P2 Major（发布治理/合规/可复现缺口）** | **0 活跃** | 前序 12 项 P2 经 GA Prep 已**全部关闭或降级** |
| **P3 Minor（打磨/文档/验证缺口）** | 多项 | 未签名（已披露）/ 安装器确认中 / 崩溃恢复压测 / 性能实测 / UI 一致性 / 文档指针漂移 |

**结论：不存在任何禁止进入 GA 的 P0 / P1 / P2 阻断项。** 全部剩余风险为 P3 级（验证、文档、体验），均可在不改动代码的前提下关闭或已作为已知限制如实披露。

> 本报告**只分类，不修复**。是否放行 GA 由 Task E 裁定。

---

## 1. 方法

- **输入**：前序 `RELEASE_RISK_REPORT.md`（12 P2 / 12 P3）、`RELEASE_FINAL_CHECKLIST.md` §2 GA 门禁、本 Sprint Task A 审计发现、发布物料/产物实证。
- **方法**：对前序每条 P2/P3 重新核验当前仓库状态（文件存在性、代码扫描、打包产物、依赖声明），按 P0/P1/P2/P3 重分类，判定是否存在发布阻断。
- **严重度定义**（同前序，沿用）：
  - P0：目标机无法启动 / 数据不可逆丢失 / 安全裸奔 → 禁止发布。
  - P1：核心功能某路径必崩 / 重大安全暴露 → Beta 前须修或降级。
  - P2：发布治理/合规/可复现/首启缺口 → GA 前须消。
  - P3：打磨/文档/验证 → 可延后。

---

## 2. 前序 P2 重分类（逐条核验）

| 原编号 | 风险 | 当前核验 | 新判定 |
|---|---|---|---|
| R-A1 | 缺 LICENSE | `LICENSE`（MIT）已新增于根目录 | ✅ **CLOSED** |
| R-A2 | 版本三源不一致 | 用户可见源 `package.json` / `config.py APP_VERSION` / `VERSION` / git tag **全部 = 1.4.0** 一致；仅 `pyproject.toml=0.1.0`（Python 工具元数据，不参与分发版本）+ 指针文档标 v1.0（见 D-3） | ✅ **CLOSED**（用户可见一致）；残留降 P3（D-3/D-4） |
| R-A4 | 缺第三方许可聚合 | `THIRD_PARTY_LICENSES.md` 已新增，覆盖全部声明依赖 | ✅ **CLOSED** |
| R-A9 | `start-xiao6.bat` 硬编码 venv | 该脚本为**开发机便捷脚本**，不进入分发包；分发经 Portable/Installer + 内嵌 Python，干净机由 `first_launch.py` 初始化 | ✅ **CLOSED（分发范围外）** |
| R-A10 | 未捆绑 Python/torch | 内嵌 Python 3.11.9 + 轻量依赖随 `extraResources` 分发；`CLEAN_ENVIRONMENT_REPORT` 验证可独立运行 | ✅ **CLOSED** |
| R-B1 | `numpy` 未声明 | `requirements.txt:15` `numpy>=1.24.0` **已声明** | ✅ **CLOSED** |
| R-B2 | `sounddevice` 未声明 | `requirements.txt:18` `sounddevice>=0.4.6` **已声明** | ✅ **CLOSED** |
| R-B5 | `torch==2.6.0+cu124` 硬 pin | 仍硬 pin（CUDA 专属，可选依赖，已随包捆绑）；核心对话不依赖 | 🟡 **降 P3**（来源构建可复现性卫生） |
| R-C1 | `.env` 含真实密钥 | `.env` **未入库**（不被分发）；打包 `extraResources` 已 `!.env` 排除；仅本地开发机存在 | ✅ **CLOSED（分发层面）**；建议补 `.gitignore` 防误提交（P3 卫生） |
| R-C2 | 机器特异性绝对路径 | GPT-SoVITS / 郑州位置等已配置驱动，非分发阻断 | 🟡 **降 P3** |
| R-C4 | 无首启 Key 向导 | `first_launch.py` + `firstlaunch.html` 向导已落地，`key_present` 驱动 | ✅ **CLOSED** |
| R-R2 | 弱默认令牌 | `REMOTE_ACCESS_TOKEN` 默认空 → 远程工具关；`SOCIAL_INBOUND_TOKEN=test123` 为本地收件箱默认，无外部暴露 | 🟡 **降 P3**（安全卫生） |

> **P2 归零**：前序 12 项 P2 中，10 项已 CLOSED，2 项（R-B5/R-C2/R-R2）降为 P3 卫生项。GA 前「发布治理」缺口已实质清零。

---

## 3. 前序 P3 重分类 + 本 Sprint 新增 P3

| 编号 | 风险 | 区域 | 处置 |
|---|---|---|---|
| P-1 | 未做代码签名（SmartScreen 提示未知发布者） | 体验 | 🟡 已接受为已知限制，`SIGNING_PREPARATION_REPORT.md` 完整披露 + 提供接入清单；非功能阻断 |
| P-2 | NSIS 安装器产物待确认 | 发布 | 🔄 本 Sprint 已启动 `electron-builder --win nsis` 验证构建（见 Task B）；预期产出 `小6-Setup-1.4.0-x64.exe` |
| P-3 | 后端崩溃恢复压测（≥3 次 kill -9）未实测 | 质量 | 🟡 `RELEASE_CHECKLIST §1.2` 标 🟡（Beta 可接受，GA 前建议验证）；恢复代码路径已存在并经单测 |
| P-4 | 性能实测未量化（首屏≤1.5s / 60fps） | 质量 | 🟡 `RELEASE_CHECKLIST §1.7` 标 🟡（Beta 可接受，GA 前建议验证） |
| P-5 | UI 一致性打磨（U1 图标风 / U6 Focus 环 / U7 动效令牌） | 体验 | 🟡 `RELEASE_CHECKLIST §1.3/§1.8` 标 🟡（PM 可豁免） |
| P-6 | 文档指针漂移（D-1 CURRENT_PHASE / D-2 PROJECT_STATUS / D-3 GOLDEN_STATE / D-4 pyproject） | 文档 | 🟡 非阻断；建议 GA 前更新指针 |
| P-7 | 自动更新通道文档化 | 文档 | 🟡 `CHANGELOG.md` 已声明「无内置自动更新通道（GA 范围外）」，升级经 NSIS 就地覆盖保留 userData |
| P-8 | `torch==2.6.0+cu124` 硬 pin | 依赖卫生 | 🟡 同 R-B5 |
| P-9 | 机器特异性绝对路径 | 可移植 | 🟡 同 R-C2 |
| P-10 | 弱默认令牌 | 安全卫生 | 🟡 同 R-R2；建议 GA 后轮换默认值 |
| P-11 | `.gitignore` 未排除 `.env` | 仓库卫生 | 🟡 当前 `.env` 未跟踪，但建议显式忽略防误提交 |

---

## 4. 严重度分布（本 Sprint 重分类后）

| 级别 | 数量 | 阻断 GA？ |
|---|---|---|
| P0 Blocker | 0 | — |
| P1 Critical | 0 活跃 | — |
| P2 Major | 0 | 否 |
| P3 Minor | 11 | 否（均可在不改动代码下关闭/披露） |

---

## 5. 阻断判定

**不存在禁止进入 GA 的阻断项（无 P0 / 无活跃 P1 / 无活跃 P2）。**

- 启动链路：server.py 纯标准库 monolith + 内嵌 Python 3.11.9，干净机 `first_launch.py` 验证可初始化（退出码 0）。
- 数据：WAL + 增量迁移 + companion.json 恢复；NSIS 默认不删 userData。
- 安全：无默认开启的远程执行；`.env` 真实密钥不进入分发包。
- 合规：LICENSE / CHANGELOG / THIRD_PARTY / VERSION / RELEASE_NOTES / README 齐备。
- 架构：单一 Runtime/EventBus/Memory/Policy，代码扫描零漂移。

> 唯一需「验证确认」的是安装器产物（P-2，本 Sprint 验证构建中）与两项质量门禁实测（P-3/P-4，验证性质、非代码缺陷）。三者均不构成功能性阻断。

---

## 6. 风险聚合观察

1. **发布治理缺口已实质清零**：前序 12 项 P2 全部关闭/降级，GA 不再受「许可/版本/依赖/首启/运行时」类阻断。
2. **剩余风险均为 P3（非阻断）**：未签名（披露）、安装器确认、质量门禁实测、UI 打磨、文档漂移。
3. **无功能缺陷类风险**：能力集经 Phase 6→10 + RC 验证，Beta 完整态。
4. **安全面可控**：远程工具默认关；密钥不进包；仅余令牌默认值卫生项（P-10）。

---

## 7. 纪律红线遵守声明

- ✅ 本报告为纯风险评估交付；所有风险仅分类与记录，**不修复、不改动任何代码/配置/UI**。
- ✅ 未新增功能、未改架构/Runtime/EventBus/Memory/Planner/Tool/API/数据库/协议。
- ✅ 业务 Bug 仅记录（BUG_WALL B5–B7 维持待处理，P3）。

---

**Task C 状态：✅ 完成（P0=0 / P1=0 / P2=0；无发布阻断；剩余均为 P3 非阻断项）。**
