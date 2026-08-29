# 10 — Reality Audit（Phase 10-A · 真实代码审计）

- **阶段**：Xiao6 AI OS · Phase 10 · AI Provider Integration Foundation v1.0 / Phase A
- **日期**：2026-08-08
- **纪律**：禁止凭记忆。以下每一条结论均附**真实文件 + 行号**证据。
- **本阶段产出**：仅审计，**零代码改动**。

---

## 0. 强制前置读取（§一）执行记录

| 权威文档 | 路径 | 状态 |
|---|---|---|
| L0 Golden State | `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | ✅ 已读（55 行全文） |
| 治理权威层级 | `docs/audits/GOVERNANCE_AUTHORITY_HIERARCHY.md` | ✅ 已读（39 行全文） |
| Local First 原则 | `docs/ai-os/09_LOCAL_FIRST.md` | ✅ 已读（§1–§6） |
| Capability Inventory | `docs/capability-platform/01_CAPABILITY_INVENTORY.md` | ✅ 已读（CONV-01 / DEV-03 等条目） |
| Product Constitution | `docs/product-constitution/`（13 份） | ✅ 目录核实存在，v1.0 |
| UI Alpha P9 | `docs/ui-alpha/09_RELEASE_POLISH.md` | ✅ 已存在（上一 Phase 交付） |
| 事件合约 | `zz-events.js` / `eventbus.py` | ✅ 已读并**实测计数** |

### 0.1 关键上游约束（原文引用）

- **Golden State L21**：`Event Contract | FROZEN | DOMAIN = 71 / SYSTEM = 8，前后端逐字一致`
- **Golden State L40**：`禁止第二 Runtime / Memory / EventBus / Permission System`
- **09_LOCAL_FIRST §4 L51**：`模型可云，但**必须提供本地降级路径**（本地小模型或规则回退）。`
- **09_LOCAL_FIRST L4**：`红线：用户数据/记忆/知识默认本地；云端仅计算，不得成为状态所有者。`
- **09_LOCAL_FIRST §3 L31**：`凭据：本地密钥库（OS keychain / 加密文件），不落明文、不上云。`

> **推论**：Phase 10 不是"新增功能"，而是**补齐 Local First 已明文要求但尚未实现的地基**。

### 0.2 事件合约实测（禁止扩张的硬基线）

```
zz-events.js   DOMAIN= 71   SYSTEM= 8
eventbus.py    DOMAIN= 71
zz-events.js 中 LLM / PROVIDER / MODEL 关键字命中 = 0
```

→ **结论**：现有事件合约**完全没有** Provider 概念，且合约已 FROZEN。**Phase 10 禁止新增领域事件**（详见 §3 决策 D-03）。

---

## 1. 真实 AI 请求链（逐层实测）

```
[前端] index.html / app.js
    │  POST /api/chat  (fetch + ReadableStream 解析 SSE)
    ▼
[后端] server.py:973  do_POST → ppath == "/api/chat" → _handle_chat()
    │  server.py:1839  _handle_chat 入口
    │  server.py:1856  messages[0] = build_context_prompt(user_text)   ← Context 注入
    │  server.py:1914  FEATURE_GOAL_DECISION → intent_gateway（可选分叉）
    │  server.py:1886  Content-Type: text/event-stream                 ← SSE 开启
    │  server.py:1990  run_fc_loop(messages, emit, tools=select_tools(...))
    ▼
[工具/FC] tools.py:3330  run_fc_loop  (MAX_ROUNDS = 5)
    │  tools.py:3341    agnes_completion(messages, tools=..., stream=False, timeout=90)
    │  tools.py:3365    execute_tool_calls → Execution.run → PermissionGuard
    ▼
[LLM 层] llm.py:83   agnes_completion(...)
    │  llm.py:89       _base, _key, _model, _ = _provider_creds(provider)   ★唯一凭据解析点
    │  llm.py:124      urllib.Request(_base + "/chat/completions")
    │  llm.py:133      _urlopen_with_proxy(req, timeout)                    ★唯一出网点
    ▼
[Provider] config.AGNES_BASE / AGNES_KEY / AGNES_MODEL   （或 LLM2_*）
    ▼
[回程] server.py:2124  emit({"choices":[{"delta":{"content": content}}]})  ← 一次性整段
    │  server.py:2149  emit({"error": f"HTTP {e.code}: ..."})
    ▼
[前端] app.js:1034  payload === '[DONE]' → 结束
       app.js:1037  json.xiao6_event → handleToolEvent
```

### 1.1 LLM 调用点全量清单（实测 grep）

`agnes_completion` 在全仓共 **12 个业务调用点**（不含定义与 import）：

| 文件:行 | 用途 | stream |
|---|---|---|
| `tools.py:3341` | **主对话 FC 闭环** | False |
| `tools.py:3374` | FC 超轮次收尾 | False |
| `tools.py:3322` | `_fc_fallback` 兜底重问 | False |
| `server.py:2024` | 工具结果汇总改写 | False |
| `agent_runtime.py:362` | Agent 工具派发 | False |
| `goals.py:412` | Goal 拆解 | False |
| `goal_decision_engine.py:128` | Goal 决策门 | False |
| `memory.py:74/92/144` | 记忆压缩 / 抽取 | False |
| `memory_distiller.py:114` | 记忆蒸馏 | False |
| `notes.py:242/488/543` | 笔记摘要 | False |
| `cognitive/extractor.py:128` | 认知抽取 | False |
| `review_clone.py:48/55` | 成果审视 | False |
| `social_inbound.py:138` | 社交入站回复 | False |

→ **结论 A**：`llm.agnes_completion` 是**事实上的唯一 LLM 出口**，`_provider_creds` 是**事实上的唯一 Provider 解析点**。Phase 10 的 Adapter 只需在此收口，**无需重构任何调用方**。

→ **结论 B（重要）**：**全链路 `stream=False`**。前端看到的"流式"是 SSE 传输层，但 LLM 侧是一次性响应，`server.py:2124` 把完整文本一次性包成一个 `delta` 发出。**当前系统并不存在真正的 token 级流式**。

---

## 2. §二 十八问 · 逐条真实回答

| # | 问题 | 真实答案 | 证据 |
|---|---|---|---|
| 1 | 当前默认 Provider 是什么？ | `agnes`。`ACTIVE_LLM` 缺省 `"agnes"`，`.env` 中**未设置**该键，故走默认。 | `config.py:23,198`；`.env` 无 `ACTIVE_LLM` |
| 2 | Model 在哪里决定？ | `llm.py:89` 从 `_provider_creds()` 取 `_model`，写入请求体 `body["model"]`（`llm.py:92`）。上游为 `config.AGNES_MODEL`。 | `llm.py:80,89,92` |
| 3 | Base URL 在哪里配置？ | `config.AGNES_BASE`，由 `os.environ["AGNES_BASE_URL"]` 填充，默认 `https://apihub.agnes-ai.com/v1`。**实机 `.env` 实为 `https://api.agnes-ai.cn/v1`**。 | `config.py:188`；`.env` |
| 4 | API Key 从哪读？ | `config.AGNES_KEY` ← `os.environ["AGNES_API_KEY"]` ← `.env`。**仅后端持有**，请求头 `Authorization: Bearer` 在 `llm.py:128` 拼装。 | `config.py:189`；`llm.py:128` |
| 5 | 是否用环境变量？ | 是，且是唯一来源。`config._load_env()` 用 `os.environ.setdefault` 加载 `.env`（不覆盖已有环境变量）。 | `config.py:160-164` |
| 6 | 有没有 config.py？ | 有。`config.py`（31661 B）。运行时值由 `reload()` 从 `os.environ` 刷新；`update_env_file()` 持久化回 `.env` 并自动 `reload()`。 | `config.py:167,482-520` |
| 7 | 有没有 settings？ | 有两层：① 后端 `/api/config` GET/POST（`server.py:1472` `_handle_config_get`）；② 前端 `settings.js` + `index.html` 「LLM 模型」Tab。 | `server.py:1472`；`index.html:524,676-717` |
| 8 | 前端能否配置 Provider？ | **能，但只是单槽覆盖**。`settingsLlmProvider` 是 3 选 1 下拉（agnes/openai/custom），保存时写的却是 `AGNES_PROVIDER/AGNES_BASE_URL/AGNES_MODEL/AGNES_API_KEY` —— 即**改的是同一组 AGNES_\* 变量**，不是切换到独立 Provider 实例。 | `index.html:689-693`；`settings.js:328-334` |
| 9 | 本地模型现状？ | **完全不存在**。全仓 grep `ollama / 11434 / lm studio / 1234/v1 / llama.cpp / mlx / vllm / gpt4all` → 业务代码命中 **0**（唯一命中是 `python/Lib/site-packages/pygments/unistring.py` 的 Unicode 表，属噪声）。 | 全仓 grep |
| 10 | oMLX / Ollama / LMStudio 接入了吗？ | **均未接入**。无检测、无适配、无配置项、无 UI。 | 同上 |
| 11 | 能否切换 Provider？ | **部分能，但残缺**。`llm._provider_creds` 支持 `agnes` 与 `llm2` 两路（`llm.py:72-80`），`ACTIVE_LLM` 可切。但：`LLM2_*` **无任何 UI**（`index.html` 零命中）、`.env` 与 `.env.example` **均未列出**、`/api/config` 只读回显 `llm2` 三字段却无写入表单。→ **实为"有后端骨架、无产品入口"的半成品。** | `llm.py:72-80`；`server.py:1490-1494`；`index.html` grep=0 |
| 12 | 有没有 fallback？ | **没有 Provider 级 fallback**。`tools.py:3305 _fc_fallback` 是**同 Provider 重问**（剥离工具上下文后再调一次 `agnes_completion`），**不切换供应商**。另 `llm.py:36-52` 有**代理→直连**降级，属网络层，非 Provider 层。 | `tools.py:3305-3327`；`llm.py:36-52` |
| 13 | 错误怎么返回？ | 三层：① `llm.py:137-169` 重试（401/429/500/502/503/504 退避 2s/4s，最多 3 次）+ 429 交 `quota.on_429()`；② `tools.py:3346/3350` 转为 `emit({"error": "核心调用失败（HTTP xxx）"})`；③ `server.py:2149/2151` 顶层兜底 `emit({"error": ...})`。**错误文案不含 Provider 身份**。 | `llm.py:137-170`；`tools.py:3346`；`server.py:2149` |
| 14 | SSE 是否表达 Provider 状态？ | **完全没有**。SSE 载荷只有 `choices/delta`、`xiao6_event`（tool_start/tool_end/modal/panel/scene/…）、`error`、`[DONE]`。无 provider / model / 本地云端字段。 | `server.py:1922,2124,2149`；`app.js:478-496,1034-1037` |
| 15 | Agent 是否假定固定模型？ | **是（隐式）**。`agent_runtime.py:362` 直接 `llm.agnes_completion(...)`，不传 `provider`，即无条件继承 `config.ACTIVE_LLM`。Agent 层**不感知**模型身份与能力。 | `agent_runtime.py:360-366` |
| 16 | Tool 是否假定固定 Provider？ | **是（隐式）**。`tools.py:3341` 同样不传 `provider`。且 FC 闭环**硬依赖 OpenAI `tools` / `tool_calls` 协议**（`tools.py:3355-3362`），一旦 Provider 不支持 tool calling，闭环会静默退化为纯文本（`tool_calls` 为空 → 直接 return）。 | `tools.py:3341,3355-3364` |
| 17 | Context 是否强绑定？ | **不绑定 Provider，但不感知 context_limit**。`server.py:1856` 由 `build_context_prompt()` 统一装配；系统内**无任何 `context_limit` / `max_tokens` 预算变量**（`llm.py` 请求体只有 model/messages/stream/temperature/[tools]/[reasoning_effort]）。 | `server.py:1856`；`llm.py:90-113` |
| 18 | UI 是否已有 Provider 入口？ | **有一个 LLM 表单，但没有 Provider 概念**。设置 → 「LLM 模型」Tab 提供：状态行、提供商下拉、端点、模型（+获取模型列表）、API Key（+测试连接）、Temperature、思考模式。状态行仅显示 `模型 · 已配置/未配置`（`settings.js:751-753`）——**不表达本地/云端、不表达可用性、不表达请求去向**。 | `index.html:676-726`；`settings.js:288-401,748-760` |

---

## 3. 现有可复用资产（Phase 10 的地基）

| 资产 | 位置 | Phase 10 用途 |
|---|---|---|
| 唯一凭据解析点 `_provider_creds` | `llm.py:65-80` | **升级为 Resolver 的调用方**，不新增第二解析点 |
| 唯一出网点 `_urlopen_with_proxy` | `llm.py:18-54` | 本地 Provider 探测复用（含"强制绕过环境代理"能力，对 `127.0.0.1` 至关重要） |
| 配置持久化 `update_env_file` | `config.py:482-520` | Provider 配置落盘；**已有 `ENV_KEYS` 白名单机制**，新键须显式登记 |
| 配置只读回显 `/api/config` | `server.py:1472-1495` | 已有 `llm.key_present` 布尔脱敏范式，**Key 从不下发前端** |
| 模型列表 `/api/models` | `server.py:1743-1771` | 已实现 OpenAI 兼容 `GET /models`，**Local Provider 可直接复用** |
| 连通性测试 `/api/test-llm` | `server.py:1773-1810` | 已是"纯连通性"语义（`max_tokens:5`，不启 Agent/Tool/Memory），**符合 §十二 要求** |
| Settings「LLM 模型」Tab | `index.html:676-726` | **复用现有入口扩展**，不新建孤立页面 |
| Capability 登记 DEV-03 | `01_CAPABILITY_INVENTORY.md:296` | `/api/models /test-llm` 已在能力清单内，扩展需同步登记 |

---

## 4. 缺口清单（Gap Analysis）

| # | 缺口 | 严重度 | 违反的上游约束 |
|---|---|---|---|
| G-01 | **无本地模型路径** | 🔴 高 | `09_LOCAL_FIRST §4 L51`「必须提供本地降级路径」——**当前明确违反** |
| G-02 | 无 Provider Registry（元数据无单一真相） | 🔴 高 | Single Source Rule |
| G-03 | 无 Provider 可用性状态（Available/Unavailable/Error） | 🟠 中 | §八 |
| G-04 | 无隐私边界表达（用户不知数据发往何处） | 🔴 高 | `09_LOCAL_FIRST §6 隐私即架构` |
| G-05 | 无 Capability Matrix（tool_calling/vision/streaming/context_limit 未知） | 🟠 中 | §十四/§十五 |
| G-06 | `LLM2_*` 有后端无 UI（半成品） | 🟠 中 | 产品完整性 |
| G-07 | 错误文案不含 Provider 身份，用户无法定位 | 🟡 低 | §十七 |
| G-08 | API Key 明文存 `.env`（未用 OS keychain） | 🟠 中 | `09_LOCAL_FIRST §3 L31` |
| G-09 | 无 `context_limit` 概念 | 🟡 低 | §十五 |
| G-10 | 无真正 token 级流式（`stream=False`） | 🟡 低 | §十三（属既有事实，非本 Phase 引入） |

---

## 5. 关键架构决策（据审计事实推导）

| ID | 决策 | 依据 |
|---|---|---|
| **D-01** | **不新建 LLM 执行路径**。Provider 层只提供「元数据 + 解析」，实际 HTTP 仍唯一走 `llm.agnes_completion`。 | Golden State L40 禁第二 Runtime；`llm.py` 已是唯一出口 |
| **D-02** | **不重构 12 个调用方**。在 `_provider_creds` 内部收口即可全局生效。 | 结论 A；§二十「最小化改动」 |
| **D-03** | **禁止新增领域事件**。Provider 状态经 REST（`/api/config`、新 `/api/providers`）暴露，**不进 EventBus / AppState / SSE**。 | Golden State L21 事件合约 FROZEN（实测 71/8）；spec §一 禁扩张 |
| **D-04** | **Provider State ≠ AI Presence**。不触碰 `avatar-state.js` / `data-presence` 三唯一链路。 | spec §八；Phase 8 三唯一须保护 |
| **D-05** | **Fallback 默认 OFF，且禁止 Silent Cloud Fallback**。现有 `_fc_fallback` 需明确标注为「同 Provider 重试」，不得被误认为跨 Provider。 | spec §七/§十八；Local First 隐私红线 |
| **D-06** | **本地端点仅探测已知 localhost**（`127.0.0.1`/`localhost` + 标准端口），且**禁止系统扫描**。 | spec §二十二 |
| **D-07** | **API Key 绝不下发前端**。沿用现有 `key_present: bool` 脱敏范式；不进日志、不进 SSE、不进 Git。 | spec §十六；`server.py:1488` 现有范式 |
| **D-08** | **UI 复用 Settings「LLM 模型」Tab**，不新建页面、不新增 CSS 类到 `styles.css`。 | DESIGN.md §7 Don'ts；spec §九 |

---

## 6. Phase A 结论

- **审计完成度**：18/18 问已用真实代码回答，**零凭记忆**。
- **代码改动**：0（本阶段纯只读）。
- **最重要发现**：
  1. 系统**已有一个未完成的双 Provider 骨架**（`ACTIVE_LLM` + `LLM2_*`），但无 UI、无文档、无状态、无隐私表达 → Phase 10 应**完成它**而非另起炉灶。
  2. **本地模型路径为 0**，而 `09_LOCAL_FIRST` 已明文要求 → 这是 Phase 10 的**首要合规缺口**。
  3. `llm.py::_provider_creds` 是天然的 Adapter 收口点，**改动面可以极小**。
- **进入 Phase B 的前提**：✅ 满足。

> 🛑 本文件仅记录审计事实。任何实现见 `01_ARCHITECTURE.md` 及后续交付。
