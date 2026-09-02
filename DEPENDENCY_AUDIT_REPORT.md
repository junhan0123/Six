# Dependency Audit — Xiao6 RC → Beta

> **身份**：Senior Release Engineer + QA Lead + Software Release Auditor
> **Sprint**：Release Audit Sprint v1.0（Release Governance Sprint，非开发 Sprint）
> **执行模式**：Audit → Verify → Report → STOP
> **日期**：2026-08-05
> **纪律红线**：仅审计；禁止新增功能 / 改业务逻辑 / 改架构 / 改 Runtime / 改 EventBus / 改 Memory / 改 Planner / 改 Tool / 改 API / 改数据库 / 改通信协议；禁止进入 GA；除非 Blocker 否则不得改代码。本报告**只指出问题，不修复**。

---

## 0. 摘要（TL;DR）

| 维度 | 结论 |
|---|---|
| 声明来源 | Python：`requirements.txt`（7 项）+ `pyproject.toml`（无 `[project.dependencies]`）；Node：`electron/package.json` devDependencies |
| 未声明但被使用 | ⛔/🟡 **`numpy`、`sounddevice` 被代码 import 但未写入 `requirements.txt`** |
| 已声明但未直接使用 | 🟡 `torchaudio`、`modelscope` 无直接 import（transitive of funasr） |
| 版本冲突 | 🟡 `torch==2.6.0+cu124` 硬 pin + `funasr`/`modelscope` 无 pin → 解析冲突风险 + CUDA 专属安装约束 |
| 开发依赖入生产 | ✅ 无（Node 仅 devDeps；Python 全为 lazy 可选增强） |
| 重复依赖 | ✅ 无重复声明 |

**核心结论**：依赖表基本健康，但存在**两组未声明运行时依赖（numpy/sounddevice）**——在干净 venv 执行 `pip install -r requirements.txt` 后运行 embed.py / wakeword.py 会触发 `ImportError`。这是发布可复现性的实质缺口（Beta 即应修复，但不由本审计执行）。Node 侧干净。

---

## 1. 审计范围与方法

- `G:/xiao6/xiao6-ui/requirements.txt`（声明）
- `G:/xiao6/xiao6-ui/pyproject.toml`（build/tool 配置，无依赖段）
- `G:/xiao6/electron/package.json`（`devDependencies` + `build`）
- `G:/xiao6/electron/node_modules/`（293 个包，build 工具链）
- 全量 `*.py` 的 `import`/`from ... import` 静态扫描，比对声明
- **方法**：声明清单 ∩ 实际 import 集合，求差集（未声明已用 / 已声明未用 / 版本约束）

---

## 2. 已声明依赖清单

### 2.1 Python（`requirements.txt`）
```
edge-tts>=1.0.0
psutil>=5.9.0
zhconv>=1.4.3
torch==2.6.0+cu124        # CUDA 12.4 专属 wheel
torchaudio==2.6.0+cu124
funasr>=1.0.0
modelscope>=1.0.0
```
注释声明：缺省时 server.py 自动降级（跳过语音 / 返回友好提示），不影响核心对话。

### 2.2 Node（`electron/package.json` → devDependencies）
```
electron ^33.4.11
electron-builder ^25.1.8
```
（无 `dependencies` 段——运行时由 electron-builder 捆绑 electron 二进制；app 自身无 npm 运行时依赖）

---

## 3. 使用 vs 声明矩阵（实际 import 扫描）

| 包 | 声明 | 直接 import 位置 | 判定 |
|---|---|---|---|
| `edge_tts` | ✅ | `server.py:2337,2424`（lazy） | ✅ 用且声明 |
| `psutil` | ✅ | `always_on.py`（lazy `import psutil`） | ✅ 用且声明 |
| `zhconv` | ✅ | `geo_weather.py`（lazy） | ✅ 用且声明 |
| `torch` | ✅ | `asr.py`（`import torch`） | ✅ 用且声明 |
| `funasr` | ✅ | `asr.py`（`from funasr import AutoModel`） | ✅ 用且声明 |
| `torchaudio` | ✅ | **无直接 import** | 🟡 已声明未用（funasr 可能间接需要，须核实） |
| `modelscope` | ✅ | **无直接 import** | 🟡 已声明未用（funasr 传递依赖，可移除显式声明） |
| `numpy` | ❌ **未声明** | `embed.py:13`、`wakeword.py:86,109` | ⛔ 用但未声明 |
| `sounddevice` | ❌ **未声明** | `wakeword.py:52,69,110` | ⛔ 用但未声明 |
| `vosk` | ❌ 未声明 | `wakeword_vosk.py` 未见模块级 import | ✅ 未用（文件疑似遗留/未激活） |

> 其余 import 全部为标准库（asyncio / http.server / sqlite3 / json / os / threading / datetime / re / uuid / hashlib / base64 / subprocess / glob / shutil / tempfile / enum / dataclasses / typing / collections / functools / itertools / math / random / time / logging / pathlib / io / queue / sys / signal …）。server.py 为纯标准库 `http.server` monolith，未用 flask/fastapi/aiohttp/requests 等。

---

## 4. 发现项

### B1 ⛔ 未声明运行时依赖 `numpy`（P2 Major）
- `embed.py` 与 `wakeword.py` 直接 `import numpy as np`。
- `requirements.txt` 未列入。当前环境可用仅因 `torch` 传递安装了 numpy；一旦在**干净 venv** 执行 `pip install -r requirements.txt`（不装 torch 的降级场景，或未来拆分），这两处会 `ImportError`。
- 影响：embed（语义向量）/ wakeword（唤醒词）功能在干净环境崩溃。

### B2 ⛔ 未声明运行时依赖 `sounddevice`（P2 Major）
- `wakeword.py` 音频采集依赖 `sounddevice`。
- 未声明。干净 venv 下 wakeword 启动即 `ImportError`。

### B3 🟡 已声明未直接使用的 `torchaudio`（P3 Minor）
- 全代码库无 `import torchaudio`。funasr 可能间接依赖，但显式声明带来数百 MB 冗余（与 torch 同 cu124 wheel）。
- 建议（不执行）：确认 funasr 是否真需；若否，移除以减重。

### B4 🟡 冗余显式声明 `modelscope`（P3 Minor）
- 无直接 import，系 funasr 的传递依赖。显式声明可降为「由 funasr 自动拉取」，避免双来源版本漂移。

### B5 🟡 `torch` 硬 pin 与 funasr/modelscope 无 pin 的解析冲突 + CUDA 专属约束（P2 Major）
- `torch==2.6.0+cu124` 为 CUDA 12.4 专属预编译 wheel；`funasr>=1.0.0` / `modelscope>=1.0.0` 不约束 torch 版本。
- 风险 1：pip 在解析 funasr 的依赖图时可能试图安装与 cu124 不兼容的 torch（CPU 版或不同 CUDA 版），导致依赖树冲突或运行时 CUDA 错配。
- 风险 2：`requirements.txt` 注释要求 `--extra-index-url https://download.pytorch.org/whl/cu124`；**无 CUDA 环境（纯 CPU / 非 12.4）无法安装**，与「隐私优先本地运行、可跨机分发」目标冲突。
- 关联：Task A 的 A9/A10（未捆绑 Python/torch 运行时、启动前提供环境）。

### B6 ✅ 无「开发依赖入生产」
- Node 侧：electron / electron-builder 均为 `devDependencies`，打包后仅 electron 二进制入产物，electron-builder 不进分发包。
- Python 侧：无 prod/dev 拆分，但全部为 lazy 可选增强（缺失即降级），无 dev-only 包泄漏到核心路径。

### B7 ✅ 无重复依赖声明
- 无同一包在 requirements.txt 与 pyproject.toml 双声明；pyproject.toml 无 `[project.dependencies]` 段，单一真源为 requirements.txt（良好实践）。

### B8 信息项：vendored 资产
- `xiao6-ui/vendor/three/three.module.js`（Three.js）、`vendor/earth/*`（贴图）为本地内置资产，不走 npm/pip，无供应链依赖风险。

---

## 5. 发现项汇总（仅列，不修）

| # | 发现 | 严重度 | Beta 影响 | GA 影响 |
|---|---|---|---|---|
| B1 | `numpy` 被 import 但未声明 | P2 Major | ⛔ 干净环境崩溃 | ⛔ 阻断 |
| B2 | `sounddevice` 被 import 但未声明 | P2 Major | ⛔ 干净环境崩溃 | ⛔ 阻断 |
| B3 | `torchaudio` 已声明未直接 import | P3 Minor | 🟡 包体冗余 | 🟡 |
| B4 | `modelscope` 冗余显式声明 | P3 Minor | 🟡 | 🟡 |
| B5 | torch cu124 硬 pin + funasr/modelscope 无 pin：解析冲突 + CUDA 专属约束 | P2 Major | ⛔ 跨机安装受限 | ⛔ 阻断 |
| B6 | 无 dev 依赖入生产 | — | ✅ | ✅ |
| B7 | 无重复声明 | — | ✅ | ✅ |
| B8 | vendored 资产无供应链风险 | — | ✅ | ✅ |

> 严重度与 Blocker 最终裁定见 `RELEASE_RISK_REPORT.md`（Task D）。

---

## 6. STOP 声明

本报告为 **纯审计交付**，未修改 `requirements.txt`、`pyproject.toml`、任何 `.py` 或 `package.json`。所有发现（B1–B5）仅记录，**不修复**。是否补齐 `numpy`/`sounddevice` 声明、是否调整 torch 版本策略，由人工 Review 决定（属开发 Sprint 范畴，不在本 Governance Sprint 内）。

下一步：Task C（Configuration Audit）→ `CONFIGURATION_AUDIT_REPORT.md`。
