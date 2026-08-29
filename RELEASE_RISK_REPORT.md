# Release Risk Audit — Xiao6 RC → Beta

> **身份**：Senior Release Engineer + QA Lead + Software Release Auditor
> **Sprint**：Release Audit Sprint v1.0（Release Governance Sprint，非开发 Sprint）
> **执行模式**：Audit → Verify → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议；禁止进入 GA；除非 Blocker 否则不得改代码。本报告**只分类，不修复**。

---

## 0. 摘要（TL;DR）

| 项 | 结论 |
|---|---|
| **P0 Blocker（禁止发布）** | **无**（目标机可运行；无启动级阻断） |
| P1 Critical | 0 条活跃（BUG_WALL B1/B2 为历史 P1，Beta 1.1 已标记解决，LIVE 待老板确认） |
| P2 Major | 12 条（物料/依赖/配置/安全卫生类，多为 GA 阻断） |
| P3 Minor | 多条（打磨/文档/流程类） |
| 整体判定 | RC 在**目标机可运行**，无 P0；但存在若干 GA 阻断项（版本/许可/密钥/依赖声明/首启），须 GA 前消除 |

> 本审计未发现「必须禁止 Beta」的 P0 Blocker。是否放行 Beta 的最终建议见 `RELEASE_AUDIT_SUMMARY.md`（Task G）。

---

## 1. 方法与输入

- 输入：Task A（`RELEASE_PACKAGE_REPORT.md`）、Task B（`DEPENDENCY_AUDIT_REPORT.md`）、Task C（`CONFIGURATION_AUDIT_REPORT.md`）全部发现项；`BUG_WALL.md`（B1–B7）；`RELEASE_CHECKLIST.md` §3 门禁。
- 方法：按 P0/P1/P2/P3 四级对全部问题进行归类；判定是否存在阻断级（P0）；标注每条的 Beta/GA 影响与「是否需 Owner」。
- 严重度定义：
  - **P0 Blocker**：导致目标机无法启动 / 数据不可逆丢失 / 安全裸奔 → 禁止发布。
  - **P1 Critical**：核心功能在某路径必崩 / 重大安全暴露 → Beta 前须修或降级。
  - **P2 Major**：发布治理/合规/可复现/首启缺口 → 不阻断目标机 Beta，GA 前须消。
  - **P3 Minor**：打磨/文档/流程 → 可延后。

---

## 2. P0 Blocker 判定

**结论：无 P0。**

- 启动链路：server.py 纯标准库 monolith + 本地模块；前端/Electron `node --check` 已在前序 Sprint 通过（RELEASE_CHECKLIST §1.4）；应用在当前目标机持续运行（日志/DB 存在）。
- 数据：db.py WAL + 增量迁移；companion.json 有恢复；无「卸载即删数据」的显式配置（R1 待验，但默认 NSIS 不删 userData）。
- 安全：无匿名远程执行默认开启（REMOTE_ACCESS_TOKEN 默认空 → 远程工具关）；companion.json/设置均本地。
- 故：**不存在禁止 Beta 的 P0**。

---

## 3. 风险登记总表（合并 A/B/C + BUG_WALL + 新增 R）

### 3.1 P2 Major（GA 前须消；不阻断目标机 Beta）

| # | 来源 | 风险 | 区域 | 须 Owner |
|---|---|---|---|---|
| R-A1 | A1 | 缺 LICENSE（声明 MIT 未附文本） | 合规 | 是 |
| R-A2 | A2/C5 | 版本三源不一致（1.4.0/1.0.0/0.1.0） | 发布一致性 | 是 |
| R-A4 | A4 | 缺第三方许可聚合 | 合规 | 是 |
| R-A9 | A9 | `start-xiao6.bat` 硬编码 WorkBuddy venv 路径 | 可移植 | 是 |
| R-A10 | A10 | 未捆绑 Python/torch 运行时，依赖目标机预置 | 启动前提 | 是 |
| R-B1 | B1 | `numpy` 被 import 但未声明（干净 venv 崩溃） | 可复现 | 是 |
| R-B2 | B2 | `sounddevice` 被 import 但未声明 | 可复现 | 是 |
| R-B5 | B5 | torch cu124 硬 pin + funasr/modelscope 无 pin（解析冲突 + CUDA 专属） | 安装 | 是 |
| R-C1 | C1 | `.env` 含真实密钥（虽未分发，仓库卫生） | 安全 | 是 |
| R-C2 | C2 | 机器特异性绝对路径/位置硬编码 | 可移植 | 是 |
| R-C4 | C4 | 无首启 Key 引导（默认空 → 新机核心失效） | 首体验 | 是 |
| R-R2 | 新增 | 弱默认令牌（SOCIAL_INBOUND_TOKEN=test123；REMOTE_ACCESS_TOKEN 默认空） | 安全 | 是 |

### 3.2 P3 Minor（可延后 / Beta 打磨）

| # | 来源 | 风险 | 区域 |
|---|---|---|---|
| R-A3 | A3 | 缺统一 CHANGELOG.md / Release Notes | 文档 |
| R-A6 | A6 | README 为设计文档、引用缺失 PLAN.md | 文档 |
| R-A7 | A7 | package.json `author` 占位 | 元数据 |
| R-A8 | A8 | 打包带入内部阶段报告 | 包体 |
| R-B3 | B3 | torchaudio 已声明未直接 import | 依赖 |
| R-B4 | B4 | modelscope 冗余显式声明 | 依赖 |
| R-C3 | C3 | 代理假设 127.0.0.1:7890（门控） | 连通性 |
| R-C6 | C6 | DB 迁移隐式无 version 戳 | 迁移 |
| R-C7 | C7 | 三存储无统一配置参考 | 文档 |
| R-C8 | C8 | 前端设置 localStorage 跨升级保留（待实测） | 持久化 |
| R-R1 | 新增 | 卸载数据保留策略未显式配置（默认 NSIS 不删，待验） | 数据 |
| R-R3 | A5 | 从未实际打包，无 installer/portable 产物可校验 | 流程 |

### 3.3 BUG_WALL 集成（历史，非本审计新发现）

| # | 来源 | 优先级 | 状态 |
|---|---|---|---|
| B1 | BUG_WALL | P1 | Beta 1.1 已解决（LIVE 待老板确认） |
| B2 | BUG_WALL | P1（若确认阻断升 P0） | Beta 1.1 已解决（LIVE 待确认） |
| B3 | BUG_WALL | P2 | Beta 1.1 已解决 |
| B4 | BUG_WALL | P2 | Beta 1.1 已解决 |
| B5 | BUG_WALL | P3 | 待处理 |
| B6 | BUG_WALL | P3 | 待处理 |
| B7 | BUG_WALL | P3 | 待处理 |

> B1/B2 为历史 P1，已标记解决但 **LIVE（真机）最终确认待老板日常使用**——属发布后观察项，非当前 Blocker。

---

## 4. 严重度分布

| 级别 | 数量 | 说明 |
|---|---|---|
| P0 Blocker | 0 | 无禁止发布项 |
| P1 Critical | 0 活跃 | 历史 B1/B2 已解决待 LIVE |
| P2 Major | 12 | 全部 GA 阻断或 GA 前须消 |
| P3 Minor | 12 | 打磨/文档/流程 |

---

## 5. 风险聚合观察

1. **无启动级阻断**：应用在当前目标机可运行，无 P0。
2. **GA 阻断集中在「发布治理」**：版本一致性、LICENSE/第三方许可、密钥卫生、依赖声明、首启引导——均属 RELEASE_CHECKLIST §3.2 已列的 ⛔ 项延伸，与本审计互相印证。
3. **可移植性是最大共性短板**：A9/A10/B5/C2/C4 共同指向「当前仅在开发机可跑，跨机分发需补齐运行时与首启」。若 Beta 解释为「分发给他人的可安装包」，则这些 P2 实质升格为发布阻断，应先走 Option B（继续 RC 补齐）再放 Beta。
4. **安全面可控**：无默认开启的远程执行；主要风险为密钥仓库卫生（C1）与弱默认令牌（R-R2），属治理项。

---

## 6. STOP 声明

本报告为 **纯审计/分类交付**，未修改任何代码/配置/文档。所有风险（R-A*/R-B*/R-C*/R-R*）仅分类与记录，**不修复**。是否放行 Beta、是否需先消 P2，由 `RELEASE_AUDIT_SUMMARY.md`（Task G）给出最终建议，并交人工 Review。

下一步：Task E（Beta Readiness Review）→ `BETA_READINESS_REPORT.md`。
