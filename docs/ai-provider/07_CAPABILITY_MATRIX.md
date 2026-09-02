# 07 — Capability Matrix（Phase 10-B · 能力矩阵）

- **阶段**：Phase 10-B · 架构设计
- **关联**：`02_REGISTRY.md` §3.1 `capability_ref`；`03_SELECTION.md` §6；spec §十四/§十五
- **纪律**：设计态。**诚实标记每一格**：✅ 协议保证 / ⚠️ 运行时依赖 / ❌ NOT SUPPORTED / 🔴 架构阻塞。

---

## 1. 能力维度定义
| 维度 | 含义 |
|---|---|
| `chat` | 基础对话（含 SSE 传输层包装，非真流式） |
| `tool_calling` | OpenAI `tools/tool_calls` 协议；FC 闭环依赖（`tools.py:3355`） |
| `vision` | 多模态图像输入 |
| `streaming` | 真 token 级流式（`stream=True`） |
| `reasoning_effort` | `agnes_completion` 的 `reasoning_effort` 降级（`llm.py` 重试逻辑） |
| `context_limit` | 上下文窗口上限（用于预算提示） |
| `privacy_class` | 本地/云端（见 `04_PRIVACY_AND_FALLBACK.md`） |

---

## 2. 能力矩阵（设计态诚实表）

图例：✅ 协议保证　⚠️ 运行时/模型依赖　❌ NOT SUPPORTED　🔴 架构阻塞（本 Phase 不解除）

| Provider (capability_ref) | chat | tool_calling | vision | streaming | reasoning_effort | context_limit | privacy_class |
|---|---|---|---|---|---|---|---|
| **agnes** (agnes-2.5-flash) | ✅ | ✅ | ✅ | ❌ NOT SUPPORTED | ✅ | ⚠️ 由模型声明 | cloud |
| **llm2** (OpenAI 兼容云端) | ✅ | ⚠️ 取决于具体端点 | ⚠️ 取决于端点 | ❌ NOT SUPPORTED | ❌（除非端点支持） | ⚠️ 由端点声明 | cloud |
| **ollama** (local) | ✅ | ⚠️ 取决于模型（如 llama3 支持） | ⚠️ 取决于模型 | ❌ NOT SUPPORTED | ❌ NOT SUPPORTED | ⚠️ 用户配置声明 | local |
| **lmstudio** (local) | ✅ | ⚠️ 取决于模型 | ⚠️ 取决于模型 | ❌ NOT SUPPORTED | ❌ NOT SUPPORTED | ⚠️ 用户配置声明 | local |
| **mlx** (local) | ✅ | ⚠️ 取决于模型 | ⚠️ 取决于模型 | ❌ NOT SUPPORTED | ❌ NOT SUPPORTED | ⚠️ 用户配置声明 | local |

### 2.1 关键诚实标注
- **streaming = ❌ NOT SUPPORTED（全部）**：现状全链路 `stream=False`（`10_REALITY_AUDIT.md` 结论 B）。前端「流式」是 SSE 传输包装，LLM 侧一次性响应。真流式属独立 Phase，本 Phase 不引入（Out of Scope）。
- **vision**：Agnes `agnes-2.5-flash` ✅（多模态）；本地小模型通常 ❌，但取决于用户装载的模型，故标 ⚠️ 而非绝对否定。
- **tool_calling**：本地 Provider 的能力**取决于具体模型**（如 Ollama 的 `llama3`/`qwen` 支持，`tiny` 模型不支持）。不支持时 FC 闭环**已能优雅退化**为纯文本（`tools.py:3355` 空 `tool_calls` → return），不报错。
- **context_limit**：本地模型无统一 API 声明，由**用户在 Settings 配置**声明（G-09 的部分缓解），系统不做自动推断。

---

## 3. 不支持组合的处理（spec §二十三/§二十四）
| 组合 | 行为 | 不静默 |
|---|---|---|
| 本地 Provider + 需要 vision | 用户所选模型不支持 → 请求失败/降级；UI 在选择时声明 ⚠️ | ✅ 显式 |
| 任意 Provider + 真流式 | 系统不支持，永不发起 `stream=True` | ✅ 架构阻塞 |
| 本地 Provider + tool_calling 不支持的模型 | FC 退化为纯文本（已有） | ✅ 不报错但行为可知 |
| local → cloud 自动 fallback | **禁止**（D-05） | ✅ 架构禁止 |

---

## 4. 能力探测（可选、Phase C 细化）
- 对 `tool_calling` / `vision` 等，可在「测试连接」时发一次最小 probe（如带空 `tools` 的请求看是否返回 `tool_calls` 字段）来**运行时确认** ⚠️ 项；
- 探测结果缓存进 `provider_status_cache`，经 `/api/config` 暴露；
- **绝不**为探测而扫描系统或外联未登记主机（D-06）。

---

## 5. 与选择层的关系
- `03_SELECTION.md` 切换 Provider 时，UI 展示该 Provider 的 `privacy_class` + 关键能力（tool_calling/vision 是否 ⚠️）；
- 用户切换到一个 ⚠️ 项较多的本地模型时，应被提示「此模型可能不支持工具调用/视觉」；
- 不允许系统因能力缺失而**静默**改变行为路径（除 FC 退化为纯文本这一**已有且显式**的行为）。

> 🛑 设计态。能力矩阵在 Phase C 由 `provider_registry.py` 的 `capability_ref` 引用，运行时探测补充 ⚠️ 项。
