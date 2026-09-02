# 01 — Provider Architecture（Phase 10-B · 架构设计）

- **阶段**：Xiao6 AI OS · Phase 10 · AI Provider Integration Foundation v1.0 / Phase B
- **日期**：2026-08-08
- **纪律**：本文件为**设计态**，**零代码改动**。所有结论均回溯 `10_REALITY_AUDIT.md` 的真实证据。
- **上游红线**：Golden State L21（事件合约 FROZEN 71/8）、L40（禁第二 Runtime/Memory/EventBus/Permission）；09_LOCAL_FIRST §3/§4/§6。

---

## 0. 设计输入（来自 10_REALITY_AUDIT.md）

| 审计事实 | 编号 | 对架构的约束 |
|---|---|---|
| `llm.agnes_completion` 是唯一 LLM 出口；`_provider_creds` 是唯一解析点 | 结论 A | Adapter 仅在此收口，**不新建第二 HTTP 路径** |
| 全链路 `stream=False` | 结论 B | 本 Phase **不引入真流式**；标记 NOT SUPPORTED |
| 已有未完成的双 Provider 骨架 `ACTIVE_LLM` + `LLM2_*` | 发现 1 | **完成半成品**，非另起炉灶 |
| 本地模型路径 = 0 | 发现 2 / G-01 | 首要合规缺口：补 Local 接入 |
| 事件合约 71/8 且无 Provider 关键字 | 实测 | **禁新增领域事件**（D-03） |
| 决策 D-01…D-08 | §5 | 本设计逐条遵守 |

---

## 1. 设计目标与边界

### 1.1 目标
建立「云端 API + 本地大模型」**可选择、可治理、可扩展**的 AI Provider 接入基础。Provider 是能力接入层；UI 仅为其表现层，不得反向侵入系统核心。

### 1.2 In Scope（本 Phase 10 内）
- 最小 Provider 抽象（Spec / Resolver / Adapter）；
- Provider Registry（元数据单一真相）；
- Provider 选择（用户显式切换，持久化）；
- 本地 Provider 接入（Ollama / LM Studio / MLX，OpenAI 兼容）；
- 隐私边界表达（本地/云端可见）；
- 能力矩阵（tool_calling / vision / streaming / context_limit）；
- 连通性测试端点复用与收敛。

### 1.3 Out of Scope（本 Phase 10 明确不做）
- ❌ 真 token 级流式（现状 `stream=False`，见结论 B）—— 属独立 Phase；
- ❌ 新增领域事件 / 触碰 EventBus / AppState（D-03）；
- ❌ 触碰 AI Presence 三唯一链路（D-04）；
- ❌ 系统级端口扫描（D-06）；
- ❌ Silent Cloud Fallback（D-05）；
- ❌ 引入 Electron / 重构 12 个调用方（D-01/D-02）；
- ❌ OS keychain 改造（G-08 记录为已知债，不在本 Phase 解）。

---

## 2. 最小 Provider 抽象（三层，不虚构层）

```
┌─────────────────────────────────────────────────────────────┐
│ ProviderSpec          （元数据 · Registry 记录 · 纯数据）      │
│  id / kind(cloud|local) / display / env_prefix / auth_required│
│  / hosts[] / openai_compatible / default_model / privacy_class│
│  / capability_ref                                       │
└───────────────┬─────────────────────────────────────────────┘
                │ 读取
┌───────────────▼─────────────────────────────────────────────┐
│ ProviderResolver       （升级现有 _provider_creds）            │
│  resolve(provider_id) → ProviderBinding                       │
│  查 Registry → 读 config.<ENV_PREFIX>_* → 填 capability       │
└───────────────┬─────────────────────────────────────────────┘
                │ 产出
┌───────────────▼─────────────────────────────────────────────┐
│ ProviderBinding       （运行时绑定 · 一次性值）                │
│  {base_url, api_key, model, auth_required, kind,             │
│   capabilities, privacy_class, status}                      │
└───────────────┬─────────────────────────────────────────────┘
                │ 传入
┌───────────────▼─────────────────────────────────────────────┐
│ ProviderAdapter        （复用 agnes_completion，单 HTTP 路径） │
│  agnes_completion(binding, messages, tools, auth_required)   │
│  Cloud: auth_required=True  → 带 Bearer                       │
│  Local: auth_required=False → 不带 Bearer，仅换 base_url      │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 ProviderSpec（元数据）
纯数据，不含任何执行逻辑、不含密钥。存放于 `provider_registry.py::PROVIDER_SPECS`（见 `02_REGISTRY.md`）。

### 2.2 ProviderResolver（升级 `_provider_creds`）
- 现有 `llm._provider_creds(provider)`（`llm.py:65-80`）返回 4 元组 `(base, key, model, supports_reasoning)`。
- 升级为 `resolve(provider_id) -> ProviderBinding`：增加 `auth_required`、`kind`、`privacy_class`、`capabilities`、`status` 字段；内部结构不变，调用方签名保持兼容（D-02）。
- **仍是唯一解析点**（D-01）。

### 2.3 ProviderAdapter（复用 `agnes_completion`）
- Ollama / LM Studio / MLX 均暴露 OpenAI 兼容 `/v1/chat/completions`，与 Agnes 同源。
- **唯一最小代码改动**：`agnes_completion` 增加 `auth_required: bool = True` 形参（`llm.py:83`）；当 `False`（本地）时跳过 `Authorization: Bearer` 头（`llm.py:128`）。
- 本地 Provider 因此**零新建 HTTP 路径**，复用同一出网点 `_urlopen_with_proxy`（`llm.py:18`）。

---

## 3. 请求解析路径（运行时）

```
用户请求
  → server.py:1839 _handle_chat
  → tools.py:3341 run_fc_loop → agnes_completion(messages, tools, stream=False)
  → [Phase 10 注入] 解析 ACTIVE_PROVIDER
        → ProviderResolver.resolve(ACTIVE_PROVIDER)
        → ProviderBinding
  → agnes_completion(binding, ..., auth_required=binding.auth_required)
  → _urlopen_with_proxy（唯一出网，llm.py:18）
  → Provider（Agnes / LLM2 / Ollama / LMStudio / MLX）
```

- 12 个调用方（`tools.py/agent_runtime.py/goals.py/...`）**不传 provider 即继承 `ACTIVE_PROVIDER`**，与现状 `config.ACTIVE_LLM` 行为一致（D-02）。
- `agent_runtime.py:362` 不感知 Provider 的现状**保持不变**（不扩大隐式耦合，但 Selection 层记录此事实）。

---

## 4. 与现有系统的接口契约（零破坏基线）

| 契约 | 现状 | Phase 10 处理 |
|---|---|---|
| 12 个 `agnes_completion` 调用方 | 不传 provider | **不变**（D-02） |
| SSE 载荷 `choices/delta/error/[DONE]` | `server.py:2124` | **不变**（D-03）；Provider 身份走 REST，不进 SSE |
| EventBus / AppState / Golden State 71/8 | FROZEN | **不触碰**（D-03） |
| AI Presence 三唯一（`avatar-state.js`→`refreshHud`→`data-presence`） | Phase 8 锁定 | **不触碰**（D-04） |
| `/api/config` 脱敏范式（`key_present: bool`） | `server.py:1488` | 扩展 `active_provider` + `privacy_class`，**Key 仍不下发**（D-07） |
| `/api/models` OpenAI 兼容 | `server.py:1743` | Local Provider 直接复用 |
| `/api/test-llm` 纯连通性 | `server.py:1773` | 复用为「连接测试」语义（见 `06_CONNECTION_TEST.md`） |
| Settings「LLM 模型」Tab | `index.html:676-726` | 复用扩展（见 `05_UI.md`），不新建页面（D-08） |

---

## 5. 本地 Provider 接入（修复 G-01 · Local First 合规）

| Provider | kind | 已知端点（仅 localhost，D-06） | auth | OpenAI 兼容 |
|---|---|---|---|---|
| Ollama | local | `127.0.0.1:11434` | 否 | 是（`/v1/chat/completions`） |
| LM Studio | local | `127.0.0.1:1234` | 否 | 是（`/v1/chat/completions`） |
| MLX（mlx-lm server） | local | `127.0.0.1:8080` | 否 | 是（`/v1/chat/completions`） |

- **探测方式**：仅对 Registry 中登记的已知 `hosts` 发 `GET /models`（或 `/api/tags` 兼容层）做可用性探测；**禁止任何端口范围扫描 / 系统服务发现**（D-06）。
- **探测触发**：用户主动「测试连接」或 Settings 打开时按需探测；结果缓存为 `status ∈ {available, unavailable, error}`，经 `/api/config` 暴露（非事件）。
- **隐私类**：本地 Provider `privacy_class = "local"` → UI 显式标注「数据不出本机」（G-04）。

---

## 6. 配置模型（最小扩展）

### 6.1 新增 env 键（经 `config.ENV_KEYS` 白名单登记，`config.py:482`）
| 键 | 用途 | 是否密钥 |
|---|---|---|
| `ACTIVE_PROVIDER` | 当前生效 Provider id（取代/别名 `ACTIVE_LLM`） | 否 |
| `OLLAMA_HOST` | Ollama 基址（默认 `http://127.0.0.1:11434`） | 否 |
| `OLLAMA_MODEL` | 默认模型名 | 否 |
| `LMSTUDIO_HOST` | LM Studio 基址（默认 `http://127.0.0.1:1234`） | 否 |
| `LMSTUDIO_MODEL` | 默认模型名 | 否 |
| `MLX_HOST` | MLX 基址（默认 `http://127.0.0.1:8080`） | 否 |
| `MLX_MODEL` | 默认模型名 | 否 |

> 现有 `AGNES_*` / `LLM2_*` 键**全部保留**，与 `agnes` / `llm2` 两个 Spec 的 `env_prefix` 对齐；`.env.example` 同步补齐。

### 6.2 持久化
沿用 `config.update_env_file(updates)`（`config.py:482-520`）—— 新键须先加入 `ENV_KEYS` 白名单，否则被拒（安全护栏）。

---

## 7. 设计态判定的 NOT SUPPORTED / FORBIDDEN 项

| 项 | 判定 | 依据 |
|---|---|---|
| 真 token 级流式 | **NOT SUPPORTED**（当前 `stream=False`） | 结论 B；Out of Scope |
| 系统端口/服务扫描 | **FORBIDDEN** | D-06；§二十二 |
| Silent Cloud Fallback（数据静默外发） | **FORBIDDEN** | D-05；09_LOCAL_FIRST §6 |
| 本地小模型视觉输入 | **通常 NOT SUPPORTED**（取决于模型，运行时声明） | `07_CAPABILITY_MATRIX.md` |
| 新增领域事件表达 Provider | **FORBIDDEN** | D-03；Golden State L21 |
| OS keychain 存储 Key | **NOT SUPPORTED（本 Phase）** | G-08 已知债，记录不修 |
| 跨 Provider 自动切换（无用户授权） | **FORBIDDEN** | D-05 |

---

## 8. 进入 Phase C（实现）的前提
- [x] 审计完成（10_REALITY_AUDIT.md）
- [x] 架构设计完成（本文件 + 02/03/04/07）
- [ ] 用户/老板 Review 架构（Phase 工作流：Design → 待确认 → Implement）
- [ ] 决策冻结：Registry 用 Python 模块（非 YAML）；本地探测仅已知 localhost

> 🛑 设计未获 Review 前，不进入 Phase C 写代码。本文件仅描述「应然」，不含实现。
