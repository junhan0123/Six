# Release Final Checklist — Xiao6 RC → Beta → GA

> **身份**：Senior Release Engineer + QA Lead + Software Release Auditor
> **Sprint**：Release Audit Sprint v1.0（Release Governance Sprint，非开发 Sprint）
> **执行模式**：Audit → Verify → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议；禁止进入 GA；除非 Blocker 否则不得改代码。本清单**只列出待办与门禁，不执行、不修复**。

---

## 0. 摘要（TL;DR）

| 阶段 | 目标 | 关键缺口（来自 A/B/C/D/E） |
|---|---|---|
| **Beta Release（可分发）** | 产出可安装/可移植产物，他人可装可跑 | A5 未打包 / A9 启动脚本硬编码 / A10 未捆绑运行时 / C4 无首启向导 / B1·B2 依赖未声明 |
| **GA Release** | 合规、可复现、可维护的正式发布 | A1 LICENSE / A2·C5 版本单一源 / A3 Release Notes / A4 第三方许可 / §1.2 崩溃恢复压测 / §1.4 自动更新文档 / §1.7 性能实测 |
| **未来更新** | 打磨与流程固化 | P3 系列（R-A3/R-A6/R-A7/R-A8/R-B3/R-B4/R-C3/R-C6/R-C7/R-C8/R-R1/R-R3、BUG_WALL B5–B7） |

**整体判定**：当前 RC 在**目标机（老板本机）已实质处于 Beta 使用态**（应用持续运行，无 P0）。若「Beta」指「可分发给他人的安装包」，则须先走 **Beta 阶段清单** 补齐打包产物 + 首启向导 + 可移植性，再放行。GA 需全部 ⛔ 项清零。

> 最终放行建议见 `RELEASE_AUDIT_SUMMARY.md`（Task G）。本清单为门禁与工作项索引，不替代人工 Review。

---

## 1. 阶段一：Beta Release 清单

> 目标：让 Xiao6 成为「可分发、可安装、可运行」的 Beta 版本。此阶段**不要求**全部 GA ⛔ 项清零，但要求 Beta 用户在干净机器上能装能跑。

### 1.1 Beta 放行门禁（须全部满足）

| # | 门禁 | 来源 | 状态 | 说明 |
|---|---|---|---|---|
| B-G1 | 实际产出安装包（portable + nsis）并冒烟 | A5 / R-R3 | ⛡ 未做 | `npm run dist` 从未执行；须产出 installer/portable 并验证完整性/首次启动 |
| B-G2 | 安装后能在**干净机器**启动（无非目标机依赖） | A9 / A10 | ⛡ 未做 | `start-xiao6.bat` 硬编码 WorkBuddy venv（A9）；未捆绑 Python/torch（A10）→ 他机失效 |
| B-G3 | 干净环境首启可完成核心配置（Key 引导） | C4 / R-C4 | ⛡ 未做 | `AGNES_API_KEY` 默认空 → 新机核心对话静默失效，无向导提示 |
| B-G4 | 依赖在声明态可复现安装 | B1 / B2 | ⛡ 未做 | `numpy`/`sounddevice` 被 import 但未声明 → 干净 venv 崩溃 |
| B-G5 | 无启动级 Blocker | D / P0 | ✅ 已满足 | 当前目标机持续运行，无 P0 |

### 1.2 Beta 可接受（可延后至 GA）的 P2 项

| # | 项 | 来源 | 为何 Beta 可接受 |
|---|---|---|---|
| B-A1 | LICENSE 缺失 | A1 | MIT 文本未附属合规缺口，但不阻断安装运行；GA 前必须补 |
| B-A2 | 版本三源不一致 | A2 / C5 | 不阻断运行；损害崩溃版本标注，GA 前须统一 |
| B-A3 | 第三方许可缺失 | A4 | 不阻断运行；分发合规缺口，GA 前须补 |
| B-A4 | torch cu124 硬 pin 冲突 | B5 | 当前目标机已解析成功；GA 前须放宽 pin 保证可复现 |
| B-A5 | `.env` 含真实密钥 | C1 | 仓库卫生项，未分发；分发前须移除/轮换 |
| B-A6 | 机器特异性绝对路径/位置 | C2 | 目标机可用；分发前须参数化 |
| B-A7 | 崩溃恢复压测未做 | §1.2 / E#3 | Beta 可接受（非 ⛔）；GA 前须补 |
| B-A8 | 文档错位（README 非手册） | A6 | 目标机可用；GA 前须补产品手册 |
| B-A9 | 打包带入内部报告 | A8 | 包体臃肿；GA 前须排除 |

### 1.3 Beta 阶段收敛工作项（建议，不执行）

1. **B-G1/B-G2**：执行 `electron-builder --win`，产出 `dist/`，并在**非开发机**验证 portable + nsis 安装后启动；若绑定 Python 不可行，至少在 README/安装器内显式声明「需预装 Python 3.11 + `pip install -r requirements.txt`」。
2. **B-G3**：实现首启后端 Key 引导（onboarding 覆盖 `AGNES_API_KEY` 或提供设置入口），避免新机静默失效。
3. **B-G4**：在 `requirements.txt` 补齐 `numpy` / `sounddevice`，并验证 `pip install -r requirements.txt` 在干净 venv 成功。

> 以上为「建议收敛项」，属发布治理，非功能开发。是否执行由人工 Review 决定。

---

## 2. 阶段二：GA Release 清单（全部 ⛔ 须清零）

> 目标：正式发布。所有 RELEASE_CHECKLIST §3.2 已列 ⛔ 项，叠加本 Sprint A/B/C 审计的 GA 阻断项，必须全部清零。

### 2.1 合规与物料（来自 Task A）

| # | GA 阻断项 | 来源 | 关联 RELEASE_CHECKLIST |
|---|---|---|---|
| G-A1 | 附 `LICENSE` 文本（MIT 已声明未附） | A1 | §1.11 合规 |
| G-A2 | 建立版本单一来源（消 1.4.0/1.0.0/0.1.0 三源） | A2 / C5 | §1.11 版本一致性 ⛔ |
| G-A3 | 产出统一 `CHANGELOG.md` / Release Notes | A3 | §1.11 ⛔ |
| G-A4 | 聚合第三方许可（`THIRD_PARTY_LICENSES` 或 `licenses/`） | A4 | §1.11 合规 ⛔ |
| G-A5 | 安装包须产出 + 签名 + 自动更新通道文档化 | A5 | §1.4 ⛔ |
| G-A6 | 提供产品手册（安装/构建/运行），替换设计文档 | A6 | §1.11 文档 ⛔ |
| G-A7 | `package.json` author 填真实作者/组织 | A7 | §1.11 元数据 |
| G-A8 | 打包排除内部阶段报告（PHASE*/BUG_WALL 等） | A8 | §1.11 包体 |

### 2.2 可移植与启动（来自 Task A/C）

| # | GA 阻断项 | 来源 |
|---|---|---|
| G-A9 | `start-xiao6.bat` 去除开发机 venv 硬编码，或自带运行时探测 | A9 |
| G-A10 | 捆绑 Python/torch 运行时，或文档化「目标机预装」前提并经真机验证 | A10 |

### 2.3 依赖与可复现（来自 Task B）

| # | GA 阻断项 | 来源 |
|---|---|---|
| G-B1 | `requirements.txt` 补齐 `numpy` / `sounddevice` | B1 / B2 |
| G-B5 | 放宽 `torch==2.6.0+cu124` 硬 pin 或显式声明 CUDA 专属约束，避免 funasr/modelscope 解析冲突 | B5 |

### 2.4 配置与安全（来自 Task C）

| # | GA 阻断项 | 来源 |
|---|---|---|
| G-C1 | 分发前移除/轮换 `.env` 真实密钥（AGNES_API_KEY / HOTDATA_KEY / SOCIAL_INBOUND_TOKEN） | C1 / R-R2 |
| G-C2 | 参数化机器特异性绝对路径（GPT-SoVITS / 郑州位置） | C2 |
| G-C4 | 实现首启 Key 向导（核心对话可用性前提） | C4 / R-C4 |

### 2.5 质量门禁（来自 RELEASE_CHECKLIST §1）

| # | GA 阻断项 | 来源 |
|---|---|---|
| G-Q1 | 后端 ≥3 次 `kill -9` 自动恢复压测通过 | §1.2 ⛔ |
| G-Q2 | 自动更新通道文档化（含回滚） | §1.4 ⛔ |
| G-Q3 | 性能实测达标（启动/响应/资源） | §1.7 ⛔ |
| G-Q4 | 一致性打磨（UI/交互/文案跨模块统一） | §1.11 ⛔ |

---

## 3. 阶段三：未来更新清单（P3 打磨 / 流程固化）

> 不阻断 Beta/GA，建议后续迭代处理。

| # | 打磨项 | 来源 |
|---|---|---|
| F-1 | 统一 `CHANGELOG_AI.md` 与 `CHANGELOG.md` 双轨 | R-A3 |
| F-2 | README 重构为「产品手册 + 设计文档分离」 | R-A6 |
| F-3 | `package.json` author 规范化 | R-A7 |
| F-4 | 内部报告移出 `backend/` 分发 | R-A8 |
| F-5 | 清理 `torchaudio` 冗余声明 | R-B3 |
| F-6 | 清理 `modelscope` 冗余显式声明 | R-B4 |
| F-7 | 代理 127.0.0.1:7890 假设文档化或改为可配置 | R-C3 |
| F-8 | DB 迁移加 `user_version` 戳，便于未来升级检测 | R-C6 |
| F-9 | 建立三存储（.env / localStorage / companion.json）统一配置参考文档 | R-C7 |
| F-10 | 前端 localStorage 跨升级保留实测 | R-C8 |
| F-11 | 卸载数据保留策略显式配置（默认 NSIS 不删，待打包实测确认） | R-R1 |
| F-12 | 持续执行 `npm run dist` 并纳入 CI 冒烟 | R-R3 |
| F-13 | BUG_WALL B5 / B6 / B7 待处理项闭环 | BUG_WALL |

---

## 4. 与 RELEASE_CHECKLIST（前序）门禁对齐

| RELEASE_CHECKLIST § | 本 Sprint 结论 |
|---|---|
| §1.2 崩溃恢复压测 | 🟡 未做 → GA ⛔（G-Q1） |
| §1.4 安装/签名/自动更新文档 | ⛡ 未打包 → GA ⛔（G-A5 / G-Q2） |
| §1.7 性能实测 | 🟡 未做 → GA ⛔（G-Q3） |
| §1.11 版本/合规/文档一致性 | ⛔ 多项缺口 → GA ⛔（G-A1~G-A8 / G-A2 / G-C2） |
| §3.2 GA 阻断项 | 全部映射至 §2 本清单，须清零后方可 GA |

---

## 5. STOP 声明

本清单为 **纯审计/门禁索引交付**，未修改任何代码/配置/文档。所有工作项（B-G* / G-A* / G-B* / G-C* / G-Q* / F-*）仅列出，**不执行、不修复**。是否按阶段推进、是否先走 Option B 补齐 Beta 门禁，由 `RELEASE_AUDIT_SUMMARY.md`（Task G）给出最终建议并交人工 Review。

下一步：Task G（Final Recommendation）→ `RELEASE_AUDIT_SUMMARY.md`。
