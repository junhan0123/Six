# Beta Readiness Review — Xiao6 RC → Beta

> **身份**：Senior Release Engineer + QA Lead + Software Release Auditor
> **Sprint**：Release Audit Sprint v1.0（Release Governance Sprint，非开发 Sprint）
> **执行模式**：Audit → Verify → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议；禁止进入 GA；除非 Blocker 否则不得改代码。本报告**只评估，不修复**。

---

## 0. 摘要（TL;DR）

| 维度 | 目标机（老板本机） | 可分发 Beta（给他人） |
|---|---|---|
| 10 项就绪度 | 8 ✅ / 2 🟡 | 4 ✅ / 4 🟡 / 2 ⛡缺口 |
| 关键缺口 | 打包产物未产（A5）、首启 Key（C4）、版本致崩溃难定位（C5） | 安装包未构建、Python/torch 未捆绑、首启向导缺失、README 非产品手册 |

**核心结论**：在**目标机**上，Xiao6 已持续运行，10 项中 8 项实质就绪、2 项（可安装产物、崩溃版本标签）待补；作为**可分发 Beta**，尚缺「安装包构建 + 运行时捆绑 + 首启引导」三块，须先走 Option B（继续 RC）补齐再做分发。

---

## 1. 评审范围

- 10 项：可安装 / 启动 / 恢复 / 升级 / 卸载 / 配置保留 / 日志 / 崩溃定位 / 文档 / 用户首次体验完整。
- 输入：Task A/B/C/D 发现项 + `RELEASE_CHECKLIST.md` §1.2/§1.4/§1.7/§1.11 + `BUG_WALL.md`。
- 区分两级判定：**目标机**（当前开发/老板机器，已运行）vs **可分发**（安装包给他人）。

---

## 2. 十项就绪度

| # | 维度 | 目标机 | 可分发 | 证据 / 缺口 |
|---|---|---|---|---|
| 1 | 可安装 | 🟡 | ⛡ | 从未 `npm run dist`，无 installer/portable（A5）；build 配置完整但产物未验证 |
| 2 | 启动 | ✅ | 🟡 | 目标机持续运行；但无 Python/torch 捆绑（A10）、`start` bat 硬编码 venv 路径（A9） |
| 3 | 恢复 | 🟡 | 🟡 | 代码恢复路径存在（companion.json C9、DB 迁移 C6）；但后端 kill -9 压测未做（RELEASE_CHECKLIST §1.2 🟡） |
| 4 | 升级 | 🟡 | 🟡 | NSIS 就地升级保留 userData；无自动更新（GA ⛔，Beta 可接受） |
| 5 | 卸载 | ✅ | 🟡 | NSIS 卸载器默认不删 userData（标准行为，待打包实测 R1） |
| 6 | 配置保留 | ✅ | 🟡 | localStorage + companion.json + db 均在 userData，升级保留（C8）；无显式迁移但安全 |
| 7 | 日志 | ✅ | ✅ | server_run.log / xiao6.log 等存在；日志已 gitignore+打包排除 |
| 8 | 崩溃定位 | 🟡 | 🟡 | 有 error-boundary.js + 后端 print 回溯；但**版本三源不一致（C5）致崩溃报告无法可靠版本标注** |
| 9 | 文档 | 🟡 | 🟡 | README 为设计文档非产品手册（A6）；无安装/构建/运行文档、无 Release Notes（A3）、无配置参考（C7） |
| 10 | 用户首次体验完整 | 🟡 | ⛡ | 无首启 Key 向导：`AGNES_API_KEY` 默认空（C4）→ 新机核心对话不可用且无提示；onboarding.js 存在但疑似不收后端 Key |

---

## 3. 逐项说明

### 3.1 可安装（#1）
- 配置：`electron/package.json` `build` 段完整（win portable + nsis，icon 齐备）。
- 缺口：仓库内无 `dist/`，从未实际打包 → **无法验证安装包完整性/签名/自动更新**。须先 `npm run dist` 产出并冒烟测试（R-R3）。

### 3.2 启动（#2）
- 目标机：server.py + Electron 已运行（日志/DB 实证）。
- 分发缺口：未捆绑 Python 3.11 + venv + torch(CUDA wheel)（A10）；`start-xiao6.bat` 硬编码 `%USERPROFILE%\.workbuddy\binaries\python\envs\default`（A9）→ 他机失效。

### 3.3 恢复（#3）
- companion.json：校验+多显示器钳制+安全默认（C9）✅。
- DB：增量迁移（C6）✅。
- 未做：后端 ≥3 次 `kill -9` 自动恢复压测（RELEASE_CHECKLIST §1.2 标 🟡，非 ⛔）→ Beta 可接受，GA 前须补。

### 3.4 升级（#4）
- NSIS `oneClick:false` + 可改目录；就地升级保留 userData → 配置/DB/设置保留。
- 自动更新通道未文档化（§1.4 ⛔ GA），Beta 不要求。

### 3.5 卸载（#5）
- electron-builder NSIS 默认**不删** `appData`/userData（标准行为）→ 用户数据在卸载后保留（R1，待打包实测确认）。

### 3.6 配置保留（#6）
- 设置（localStorage）、桌宠态（companion.json）、业务数据（xiao6.db）均落 userData → 升级保留（C8）。
- 无显式设置迁移，旧键安全合并。

### 3.7 日志（#7）
- 后端多日志文件（server_run / xiao6 / backend_restart）；前端无独立日志但 error-boundary 兜底。
- 日志已正确排除出版本控制与打包（不泄露用户数据量可控）。

### 3.8 崩溃定位（#8）
- 前端 `error-boundary.js`；后端异常 `print` 回溯（如 TTS 降级）。
- **削弱项**：版本三源不一致（config 1.4.0 / electron 1.0.0 / pyproject 0.1.0，C5）→ 用户/崩溃报告无法对齐版本，直接损害 triage 效率。

### 3.9 文档（#9）
- `README.md` 实为「贾维斯构建方案」设计文档，非安装/运行/构建手册，且引用缺失的 `PLAN.md`（A6）。
- 缺 Release Notes（A3）、配置参考（C7）。目标机使用可接受；分发须补。

### 3.10 用户首次体验（#10）
- 无首启后端 Key 引导：`AGNES_API_KEY` 默认空（C4）→ 干净环境核心对话静默失效。
- `onboarding.js` 存在，但后端 LLM Key 属 `.env`/环境变量，前端 onboarding 疑似不覆盖 → 新机首启即遇「不可用且无提示」。
- 关联 Task D R-C4（P2）。

---

## 4. 就绪度结论

- **目标机 Beta**：10 项中 8 ✅/🟡 实质就绪，无 P0；剩余 🟡（#1 打包产物、#8 版本标签）为收尾项。
- **可分发 Beta**：存在 2 项实质缺口（#1 安装包未构建、#10 首启向导）+ 多项 🟡（#2 运行时捆绑、#9 文档）。建议先走 **Option B（继续 RC）** 补齐后再分发。

---

## 5. STOP 声明

本报告为 **纯评估交付**，未修改任何代码/配置/文档。10 项就绪度仅记录与判定，**不修复**。是否放行 Beta 见 `RELEASE_AUDIT_SUMMARY.md`（Task G）。

下一步：Task F（Release Checklist）→ `RELEASE_FINAL_CHECKLIST.md`。
