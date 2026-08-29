# Release Package Audit — Xiao6 RC → Beta

> **身份**：Senior Release Engineer + QA Lead + Software Release Auditor
> **Sprint**：Release Audit Sprint v1.0（Release Governance Sprint，非开发 Sprint）
> **执行模式**：Audit → Verify → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议；禁止进入 GA；除非 Blocker 否则不得改代码。本报告**只指出问题，不修复**。

---

## 0. 摘要（TL;DR）

| 维度 | 结论 |
|---|---|
| 打包配置（electron-builder） | ✅ 配置完整、结构合理 |
| 发布必要文件完整性 | ⛔/🟡 **缺失 LICENSE / VERSION / CHANGELOG.md / 第三方许可聚合** |
| 打包产物（installer/portable） | 🟡 **仓库内从未实际打包**，产物不可验证 |
| README | 🟡 实为「设计可行性文档」，非产品安装/运行手册，且引用了不存在的 `PLAN.md` |
| 密钥/数据隔离 | ✅ `.gitignore` 与 `extraResources` 均正确排除 `.env`/`*.db`/`*.log`/`data/` |

**核心结论**：打包「配置」具备 Beta 级可构建性，但「发布物料」不齐（LICENSE/版本单一来源/Release Notes/第三方许可），且尚未产出任何可安装产物。这些属于发布治理缺口，**不阻断 Beta 的架构判定**，但其中 LICENSE 与第三方许可属合规项，GA 前必须补齐；VERSION 单一来源与 Release Notes 在 RELEASE_CHECKLIST §1.11 已列为 ⛔ GA 阻断。

---

## 1. 审计范围与方法

**范围**（仅静态审计，未执行 `electron-builder`）：
- `G:/xiao6/` 根目录与 `electron/`、`xiao6-ui/` 子目录结构
- `electron/package.json` 的 `build` 段（electron-builder 配置）
- 发布必要文件：`LICENSE` / `README*` / `CHANGELOG*` / `VERSION` / 第三方许可
- 打包产物目录：`dist/` / `out/` / `build/`
- `.gitignore` 与 `extraResources` 的密钥/数据排除规则
- 启动脚本对运行环境的依赖（可移植性）

**方法**：`ls` / `find` 目录枚举 + 文件内容读取 + 跨文件版本号比对 + 与前序 `RELEASE_CHECKLIST.md`（2026-08-05）发布规范对齐。

---

## 2. 发布目录结构（实际）

```
G:/xiao6/
├── README.md                         ← 实为设计可行性文档（非产品手册）
├── CHANGELOG_AI.md                   ← AI 向变更，非统一 CHANGELOG
├── (无 LICENSE)
├── (无 VERSION)
├── (无 CHANGELOG.md)
├── (无 THIRD_PARTY_LICENSES / licenses/)
├── electron/
│   ├── package.json                  ← build 配置（electron-builder）
│   ├── main.js / preload.js
│   ├── assets/ icon.ico / icon.png / tray.png   ← 打包图标齐备 ✅
│   ├── src/ backend-launcher.js      ← 存在 ✅
│   ├── scripts/ make-icon.py / make-shortcut.py
│   ├── node_modules/                 ← 仅 dev 依赖（electron/electron-builder）
│   └── (无 dist/ out/ build/)
├── xiao6-ui/
│   ├── requirements.txt / pyproject.toml
│   ├── .env                          ← 已 gitignore + 打包排除 ✅
│   ├── start-xiao6.bat          ← 硬编码 WorkBuddy venv 路径 ⚠️
│   └── (源码 / 报告 *.md …)
└── docs/ (architecture/audits/design/frozen/releases …)
```

---

## 3. 打包配置审查（electron-builder）

`electron/package.json` `build` 段审查结果：

| 项 | 取值 | 评价 |
|---|---|---|
| `appId` | `com.xiao6.desktop` | ✅ 规范 |
| `productName` | `小6` | ✅ |
| `copyright` | `Copyright © 2026 小6` | ✅ |
| `files` | `**/*` + 排除 node_modules 内 md/test/docs | ✅ 合理 |
| `extraResources` | `../xiao6-ui` → `backend`，过滤 `!__pycache__ !*.db !*.log !node_modules !.env` | ✅ 密钥/数据已排除 |
| `win.target` | `portable` + `nsis` | ✅ 双形态 |
| `win.icon` | `assets/icon.ico` | ✅ 文件存在（131KB） |
| `nsis.oneClick=false` + 可改安装目录 + 桌面快捷方式 | — | ✅ 友好 |
| `author` | `Senior Developer` | 🟡 占位，非真实作者/组织 |
| `private` | `true` | 🟡 不发布 npm，但产品仍以防 exe 分发，可接受 |

**结论**：打包配置本身**具备 Beta 可构建性**，无明显结构性缺陷。

---

## 4. 发布必要文件完整性矩阵

| 文件 | 要求 | 状态 | 备注 |
|---|---|---|---|
| `LICENSE` | 必需（MIT 已在 package.json 声明） | ⛔ **缺失** | MIT 要求随分发附许可文本；合规缺口 |
| `VERSION` | 推荐（单一版本来源） | ⛔ **缺失** | 版本散落，见 §5 |
| `CHANGELOG.md` | 必需（Release Notes） | ⛔ **缺失** | 仅 `CHANGELOG_AI.md`；RELEASE_CHECKLIST §1.11 已列 ⛔ GA 阻断 |
| `README.md`（产品手册） | 必需 | 🟡 **存在但错位** | 实为「贾维斯构建方案」设计文档，非安装/运行/构建手册；且引用了不存在的 `xiao6-ui/PLAN.md` |
| 第三方许可聚合（`THIRD_PARTY_LICENSES` / `licenses/`） | 推荐（分发合规） | ⛔ **缺失** | Python 依赖含 torch/funasr/modelscope（Apache/GPL 混合）、Node 依赖 electron/electron-builder，须聚合声明 |

---

## 5. 版本号碎片化（须建立单一来源）

| 位置 | 声明版本 |
|---|---|
| `electron/package.json` | `1.0.0` |
| `xiao6-ui/pyproject.toml` | `0.1.0` |
| `manifest.json`（PWA 移动端） | 无版本字段 |
| `electron/package.json` `private` | `true` |

**风险**：无单一版本真源 → 打包产物版本（`${version}` 取自 electron/package.json=1.0.0）与 Python 包（0.1.0）不一致；用户/崩溃报告无法对齐版本。**建议**（仅建议，不执行）：建立根 `VERSION` 文件或统一 `package.json` 版本为单一来源。

---

## 6. 打包产物验证

- 仓库内 **不存在 `dist/` / `out/` / `build/`**（`electron/.gitignore` 已忽略 `dist/`/`out/`）。
- `package.json` `scripts.dist = "electron-builder --win"` 存在，但**从未在本仓库执行/产出**，无 installer（nsis）或 portable exe 可供校验。
- **审计限制**：当前无法验证安装包完整性、签名、自动更新通道、首次启动行为。这些须在实际 `npm run dist` 后于 Task E 补验证。

---

## 7. 可移植性隐患（跨 Task E/C 关联）

- `xiao6-ui/start-xiao6.bat` 硬编码：
  `set "VENV_PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"`
  → 该路径为**开发机专属（WorkBuddy 托管 venv）**，非目标用户机器所有。分发后此启动脚本在他人机器失效。
  **关联**：Task E「可安装/启动」、Task C「首启/缺省值」。建议发布包自带 Python 运行时或可探测系统 Python，但本报告**不修改**。
- `extraResources` 仅复制 `xiao6-ui` 源码，**未捆绑 Python 解释器 / venv / torch(CUDA wheel)**。打包后 app 依赖目标机预装 Python 3.11 + 已 `pip install -r requirements.txt`（含 CUDA 专属 torch）。这是 Beta 启动可行性的实质前提，须在 Task E 评估。

---

## 8. 发现项汇总（仅列，不修）

| # | 发现 | 严重度 | Beta 影响 | GA 影响 |
|---|---|---|---|---|
| A1 | 缺 `LICENSE`（虽声明 MIT） | P2 Major（合规） | 🟡 建议补 | ⛔ 阻断 |
| A2 | 缺 `VERSION` / 版本碎片化（1.0.0 vs 0.1.0） | P2 Major | 🟡 | ⛔ 阻断（RELEASE_CHECKLIST §1.11） |
| A3 | 缺统一 `CHANGELOG.md` / Release Notes | P3 Minor | 🟡 | ⛔ 阻断（§1.11） |
| A4 | 缺第三方许可聚合 | P2 Major（合规） | 🟡 建议补 | ⛔ 阻断 |
| A5 | 从未实际打包，无 installer/portable 产物可校验 | P3 Minor（流程） | 🟡 须先产出再验 | ⛔ 阻断 |
| A6 | README 为设计文档、非产品手册，且引用缺失 `PLAN.md` | P3 Minor | 🟡 | 🟡 |
| A7 | `package.json` `author` 占位 `Senior Developer` | P3 Minor | 🟡 | 🟡 |
| A8 | 打包将全部内部阶段报告（`PHASE*.md`/`BUG_WALL.md` 等）带入 `backend/` 分发 | P3 Minor | 🟡 包体臃肿 | 🟡 |
| A9 | `start-xiao6.bat` 硬编码开发机 venv 路径 | P2 Major（可移植） | ⛔ 他机无法启动 | ⛔ 阻断 |
| A10 | 未捆绑 Python/torch 运行时，依赖目标机预置 | P2 Major | ⛔ 启动前提未证 | ⛔ 阻断 |

> 严重度与 Blocker 最终裁定见 `RELEASE_RISK_REPORT.md`（Task D）。本表为 Task A 范围内的发布物料发现。

---

## 9. STOP 声明

本报告为 **纯审计交付**，未修改任何代码、配置或文档。所有发现项（A1–A10）仅记录，**不修复**。是否补 LICENSE/VERSION/Release Notes/第三方许可、是否实际执行 `electron-builder` 产出 installer，由人工 Review 决定。

下一步：Task B（Dependency Audit）→ `DEPENDENCY_AUDIT_REPORT.md`。
