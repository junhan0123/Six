# Configuration Audit — Xiao6 RC → Beta

> **身份**：Senior Release Engineer + QA Lead + Software Release Auditor
> **Sprint**：Release Audit Sprint v1.0（Release Governance Sprint，非开发 Sprint）
> **执行模式**：Audit → Verify → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议；禁止进入 GA；除非 Blocker 否则不得改代码。本报告**只指出问题，不修复**。

---

## 0. 摘要（TL;DR）

| 维度 | 结论 |
|---|---|
| 配置加载健壮性 | ✅ `config.py` 全量 `os.environ.get(..., default)` + `load_env()` setdefault，强默认、可覆盖 |
| 配置恢复 | ✅ `companion.json` 有校验+多显示器钳制+安全默认；`db.py` 有增量迁移 |
| 密钥安全 | ⛔/🟡 **`.env` 含真实 API Key**（AGNES/HOTDATA），虽 gitignore+打包排除但未进分发，仓库卫生待治理 |
| 首启引导 | 🟡 **无首启向导**：`AGNES_API_KEY` 默认空，分发后无 `.env` → 新机核心对话不可用 |
| 版本号 | ⛔ **三套版本源不一致**（config `1.4.0` / electron `1.0.0` / pyproject `0.1.0`） |
| 机器特异性 | 🟡 `.env` 硬编码 `D:/GPT-SoVITS/...` 绝对路径、郑州位置 |

**核心结论**：配置「机制」健康（强默认、恢复稳健），但配置「物料与首启体验」有发布级缺口——尤其密钥卫生、三源版本不一致、缺少首启必填项引导。其中三源版本不一致在 RELEASE_CHECKLIST §1.11 已列为 ⛔ GA 阻断的延伸。

---

## 1. 审计范围与方法

- `G:/xiao6/xiao6-ui/.env`（运行时环境变量，已读取）
- `G:/xiao6/xiao6-ui/config.py`（config 模块：load_env / reload / 默认值）
- `G:/xiao6/xiao6-ui/server.py`（TTS 代理逻辑、默认端口）
- `G:/xiao6/xiao6-ui/db.py`（SQLite schema + 迁移）
- `G:/xiao6/xiao6-ui/settings.js`（前端设置持久化）
- `G:/xiao6/electron/main.js`（companion.json 用户配置读写与恢复）
- **方法**：静态读取配置加载/持久化/恢复路径，比对默认值、首启行为、跨版本迁移、机器特异性。

---

## 2. 配置面概览（三套存储，无统一真源）

| 存储 | 位置 | 内容 | 持久化 |
|---|---|---|---|
| A. 后端环境变量 | `.env` → `config.py` | ~80 项（LLM/ASR/TTS/功能开关/代理/限速） | 文件（gitignore + 打包排除） |
| B. 前端设置 | `settings.js` → `localStorage` | 设置中心用户偏好（主题/遥测/键位…） | 渲染进程 localStorage（Electron userData） |
| C. 桌宠状态 | `companion.json`（userData） | `{pos, ui:{hidden,paused,dnd}}` | 主进程写 userData |

> 无统一配置参考文档；~80 个 env 变量仅在 `config.py` 代码中可见（C7）。

---

## 3. 默认值与首启行为

- **`config.py`**：`load_env()` 仅 `os.environ.setdefault`（不覆盖已设环境）；`reload()` 从 `os.environ` 全量刷新，每项均有硬编码默认值。工程良好。
- **`AGNES_API_KEY` 默认 `""`**（config.py:189）→ 无 LLM Key 时核心对话不可用。
- **首启**：`.env` 被打包排除；分发产物不含 `.env` → 新机 `AGNES_KEY` 为空 → **首启即核心功能失效**，且无向导收集 Key（C4）。
- **`XIAO6_LOCATION=河南省 · 郑州市`** / `XIAO6_DEFAULT_CITY=郑州市` 硬编码开发者地理位置（C2-位置）。

---

## 4. 迁移与恢复

- **DB 迁移**：`db.py` 在 `init_db()` 内对 `notes/tasks/memories/fts` 调用 `_migrate_*()`，采用 `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`（**增量、加列式**）。无 `user_version` 戳记，靠列存在性隐式判定（C6）。
- **companion.json 恢复**：`loadCompanionState()` 校验 `pos` 数组长度、`ui` 对象；越界/缺失 → `computeDefaultCompanionPos()`（右下角，避开任务栏）；`clampCompanionState()` 多显示器钳制（main.js:112-223）。稳健 ✅。
- **前端设置**：`settings.js` `loadSettings()` 合并默认 + localStorage；无显式 schema 迁移，旧键安全保留（C8）。

---

## 5. 发现项

### C1 ⛔/🟡 `.env` 含真实密钥（P2 Major · 安全卫生）
- `AGNES_API_KEY=sk-T6vvLuU9...`（真实 Key）、`HOTDATA_KEY=zIisgRZJ...=`、`SOCIAL_INBOUND_TOKEN=test123`（弱默认）。
- 缓解：`.gitignore` 忽略 + `extraResources` 排除 `.env` → **不进 electron 分发产物**。
- 风险：若以「压缩源码目录」方式共享/备份，`.env` 随包泄露；Key 一旦暴露须轮换。属仓库卫生缺口，非分发阻断。

### C2 🟡 机器特异性绝对路径 / 位置（P2 Major · 可移植）
- `XIAO6_GPT_SOVITS_REF=D:/GPT-SoVITS/voices/d374j_ref.wav`（开发机 D: 盘绝对路径）。
- `XIAO6_TTS_BACKEND=sovits` 默认开；他机路径无效 → 代码回退 edge-tts（server.py:2415 有可达性判断），不崩溃但常走降级。
- `XIAO6_LOCATION/DEFAULT_CITY` 硬编码郑州。

### C3 🟡 硬编码代理假设 `127.0.0.1:7890`（P3 Minor · 连通性）
- `server.py:_edge_use_proxy()` 默认探测 127.0.0.1:7890（Clash）；可达且无环境代理时强制设 `HTTP_PROXY/HTTPS_PROXY=127.0.0.1:7890`（server.py:2430-2434）。
- 该分支由「7890 可达」门控，非无脑注入；纯净环境 7890 不可达 → 走 else 清空代理。属开发机网络拓扑假设，分发后通常无害，但逻辑耦合开发者环境（C3）。

### C4 🟡 无首启必填项引导（P2 Major · 首体验）
- 分发后无 `.env`，`AGNES_API_KEY` 默认空 → 新机首启核心对话不可用，且无配置向导/校验提示（仅后端静默空 Key）。
- 关联 Task E「用户首次体验完整性」。

### C5 ⛔ 版本号三源不一致（P2 Major · 发布一致性）
- `config.py:149 APP_VERSION = "1.4.0"`（设置页「更新」展示）
- `electron/package.json version = "1.0.0"`
- `xiao6-ui/pyproject.toml version = "0.1.0"`
- **三处互不相同**，用户/崩溃报告/自动更新无法对齐版本。延伸 Task A 的 A2/A5（版本碎片化）。RELEASE_CHECKLIST §1.11 已列版本/发布说明为 ⛔ GA 阻断。

### C6 🟡 DB 迁移隐式无戳记（P3 Minor）
- `db.py` 用列存在性隐式迁移，无 `PRAGMA user_version` 版本戳；仅支持加列，不支持列删/类型变更。当前够用，但跨大版本升级缺乏显式版本控制。

### C7 🟡 三套配置存储、无统一参考（P3 Minor）
- 后端 env / 前端 localStorage / companion.json 三者独立；~80 个 env 变量无运维参考文档。建议（不执行）补 `.env.example` + 配置参考。

### C8 🟡 前端设置 localStorage 持久化（P3 Minor · 跨升级保留）
- 设置存渲染进程 localStorage（Electron userData 内）。NSIS 就地升级保留 userData → 配置应保留；但无显式迁移，旧键安全保留。须在 Task E 实测「升级后配置保留」。

### C9 ✅ companion.json 恢复稳健
- 校验/钳制/默认完整，多显示器支持，无第二状态源。符合纪律。

---

## 6. 发现项汇总（仅列，不修）

| # | 发现 | 严重度 | Beta 影响 | GA 影响 |
|---|---|---|---|---|
| C1 | `.env` 真实密钥（未分发但仓库卫生） | P2 Major | 🟡 | ⛔ 须治理 |
| C2 | 机器特异性路径/位置硬编码 | P2 Major | 🟡 常走降级 | 🟡 |
| C3 | 代理假设 127.0.0.1:7890（门控） | P3 Minor | 🟡 | 🟡 |
| C4 | 无首启 Key 引导（默认空） | P2 Major | ⛔ 新机首启失效 | ⛔ 阻断 |
| C5 | 版本三源不一致（1.4.0/1.0.0/0.1.0） | P2 Major | 🟡 | ⛔ 阻断 |
| C6 | DB 迁移隐式无 version 戳 | P3 Minor | 🟡 | 🟡 |
| C7 | 三存储无统一参考 | P3 Minor | 🟡 | 🟡 |
| C8 | 前端设置 localStorage 跨升级 | P3 Minor | 🟡 待实测 | 🟡 |
| C9 | companion.json 恢复稳健 | — | ✅ | ✅ |

> 严重度与 Blocker 最终裁定见 `RELEASE_RISK_REPORT.md`（Task D）。

---

## 7. STOP 声明

本报告为 **纯审计交付**，未修改 `.env`、`config.py`、`server.py`、`db.py`、`settings.js`、`main.js` 或任何配置文件。所有发现（C1–C8）仅记录，**不修复**。是否轮换密钥、统一版本源、补首启向导，由人工 Review 决定（属开发 Sprint 范畴）。

下一步：Task D（Release Risk Audit）→ `RELEASE_RISK_REPORT.md`。
