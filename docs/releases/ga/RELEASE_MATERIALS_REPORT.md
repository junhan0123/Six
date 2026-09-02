# Task A — Release Materials Report | 小6 GA

> **身份**：Senior Release Engineer + Software Delivery Engineer + QA Lead
> **Sprint**：Xiao6 GA Release Preparation Sprint v1.0
> **执行模式**：Audit → Plan → Execute → Verify → Report
> **日期**：2026-08-05
> **纪律红线**：仅发布工程 / 文档 / 版本信息维护；无业务功能 / 架构 / Runtime / EventBus / Memory / Planner / Tool API / 数据库 / 协议 / AI 能力 / 交互逻辑 / 代码优化改动。

---

## 1. 审计基线（Audit）

| 发布物料 | 审计前状态 | 处置 |
|---|---|---|
| `LICENSE` | ❌ 缺失 | 新增（MIT） |
| `CHANGELOG.md` | ❌ 缺失（仅有 `CHANGELOG_AI.md`，为 AI 流程变更日志，非发布版本日志） | 新增（发布版） |
| `README.md`（发布版） | ⚠️ 存在但为「贾维斯构建方案」**设计愿景文档**，非产品手册（Beta Readiness 审计 A6 已标记） | 替换为发布版（用户向安装/配置/FAQ） |
| `THIRD_PARTY_LICENSES.md` | ❌ 缺失 | 新增（第三方许可聚合） |
| `VERSION` | ❌ 缺失 | 新增（`1.4.0`） |
| `RELEASE_NOTES.md` | ❌ 缺失 | 新增（用户向发布说明） |

版本真相来源：`electron/package.json` `version=1.4.0`、`xiao6-ui/config.py` `APP_VERSION="1.4.0"`、git tag `v1.4.0-当前版本`。三源已一致（Beta Packaging Sprint 已统一）。

## 2. 执行（Execute）

全部 6 个文件已创建于仓库根目录（`G:/xiao6/`）：

| 文件 | 内容要点 |
|---|---|
| `LICENSE` | MIT 许可证全文，版权 `Copyright (c) 2026 小6` |
| `VERSION` | 单行 `1.4.0` |
| `CHANGELOG.md` | `[1.4.0] — 2026-08-05 (GA)` 条目：能力 / 打包分发 / 文档合规 / 已知限制；并声明更早内部预览版本未对外发布 |
| `THIRD_PARTY_LICENSES.md` | 聚合 Electron / Chromium / Node / Python / electron-builder + 5 个可选 Python 依赖（含 torch/funasr 等 Apache/BSD）+ Three.js + 外部服务；标注可选依赖默认不安装 |
| `RELEASE_NOTES.md` | 用户向：两种安装方式、首次启动、主要能力、系统要求、已知限制、文档索引 |
| `README.md` | 用户向产品手册：是什么 / 系统要求 / 安装（Portable+Installer）/ 首次启动 / 配置表 / FAQ / 文档索引 |

所有内容均基于已审计的真实配置（`.env.example` 字段、`package.json` 构建目标、首启向导行为），未引入任何业务假设。

## 3. 验证（Verify）

- ✅ 6 个目标文件全部存在，路径与规格一致。
- ✅ `VERSION` 与 `package.json` / `config.py` 三源一致（`1.4.0`）。
- ✅ `LICENSE` 许可证类型与 `package.json` `"license": "MIT"` 一致。
- ✅ `THIRD_PARTY_LICENSES.md` 覆盖 `requirements.txt` 与 `package.json` devDependencies 中全部声明依赖，并标注可选依赖安装条件。
- ✅ `README.md` 不再引用缺失的 `PLAN.md`（旧愿景文档的遗留问题已消除）。
- ✅ 未修改任何 Python / JS / 业务代码；仅新增发布文档。
- ✅ 未发现需修复的业务 Bug（本任务不处理 Bug，仅产出文档）。

## 4. 已知限制 / 诚实披露

- `README.md` 原为开发者愿景文档，本次**替换为发布版**。旧愿景内容仍保留于 git 历史；如需保留「构建方案」文档，建议后续移入 `docs/` 并改名（非 GA 阻断，已记录为建议）。
- `THIRD_PARTY_LICENSES.md` 中可选依赖（torch/torchaudio/funasr/modelscope）的精确版本以 `requirements.txt` 为准；许可全文以各自官方 SPDX 文本为准。

## 5. 纪律红线遵守声明

- ✅ 仅新增发布文档（LICENSE / CHANGELOG / README / THIRD_PARTY / VERSION / RELEASE_NOTES），属「发布文档」与「版本信息维护」允许范围。
- ✅ 未新增业务功能、未改架构 / Runtime / EventBus / Memory / Planner / Tool API / 数据库 / 协议 / AI 能力 / 交互逻辑，未借机优化代码。
- ✅ 业务 Bug 仅记录，未修复。

---

**Task A 状态：✅ 完成。**
