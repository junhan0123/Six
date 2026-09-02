# 03 — Provider Selection（Phase 10-B · 选择机制）

- **阶段**：Phase 10-B · 架构设计
- **关联**：`01_ARCHITECTURE.md` §3/§6；`02_REGISTRY.md`；spec §七/§十八
- **纪律**：设计态，零代码。

---

## 1. 原则

**Provider 选择必须由用户显式做出，且用户始终知道数据发往何处。**

- 默认 Provider = `agnes`（云端），与现状 `config.ACTIVE_LLM="agnes"` 一致；
- 切换是**有意识动作**，UI 须展示目标 Provider 的隐私类（本地/云端）；
- **Fallback 默认 OFF**；任何跨 Provider 回退须用户明确 opt-in，且**不得是 Silent Cloud Fallback**（D-05）。

---

## 2. 选择流（User → Resolver → Binding）

```
[用户] Settings「LLM 模型」Tab 下拉选 provider_id
   │  save → update_env_file({ACTIVE_PROVIDER: id})   (config.py:482)
   ▼
[后端] config.reload() 刷新 ACTIVE_PROVIDER
   │
   ▼
[下一次请求] Resolver.resolve(ACTIVE_PROVIDER)
   │  → 查 Registry(PROVIDER_SPECS)
   │  → 读 config.<PREFIX>_BASE_URL / _API_KEY / _MODEL
   ▼
ProviderBinding → Adapter（agnes_completion, auth_required）
```

- 复用现有 Settings Tab（`index.html:676-726`），**不新建页面**（D-08）；
- 复用 `update_env_file` 持久化，**新键经 `ENV_KEYS` 白名单**（D-07 安全护栏）；
- 12 个调用方无需改动，自动继承 `ACTIVE_PROVIDER`（D-02）。

---

## 3. 选择可见性（修复 G-03 / G-04）

Provider 身份**不进 SSE / EventBus**（D-03），改由 REST 暴露：

| 通道 | 内容 | 现状 | Phase 10 |
|---|---|---|---|
| `/api/config` 响应 | 新增 `active_provider`、`privacy_class`、`provider_status` | `server.py:1488` 仅 `key_present` | 扩展三字段，**Key 仍仅 `bool`**（D-07） |
| Settings 状态行 | `settings.js:751` 仅「模型·已配置」 | 不表达去向 | 改为「Agnes · 云端 · 已配置」/「Ollama · 本地 · 可用」 |
| 切换确认 | 无 | — | 切到 **cloud** Provider 时弹一次隐私提示（复用现有 Toast/Modal 通道，非新事件） |

---

## 4. Fallback 策略（D-05 严格版）

### 4.1 现有 `_fc_fallback` 定性
`tools.py:3305` 是**同 Provider 重试**（剥离工具上下文再问一次），**不是跨 Provider fallback**。Phase 10 明确标注其语义，避免被误读为 Provider 级容灾。

### 4.2 跨 Provider Fallback（默认 OFF）
| 维度 | 规定 |
|---|---|
| 默认状态 | **OFF** |
| 开启方式 | 用户在 Settings 显式勾选「允许云端兜底」之类开关（opt-in） |
| 允许方向 | 仅**同隐私类**或**降级到本地**：cloud→cloud 显式 secondary；**禁止** local→cloud 静默外发 |
| 静默 | **禁止 Silent Cloud Fallback**：任何实际服务的 Provider 必须在 UI 可见（状态行/Toast） |
| 实现 | 若开启，Resolver 在 primary 探测 `error` 时回退 secondary，并记录 `served_by` 到 `/api/config` 的 `provider_status` |

### 4.3 禁项
- ❌ 系统自动把本地失败静默转云端（数据泄露风险，违反 09_LOCAL_FIRST §6）；
- ❌ 无用户授权下跨隐私类回退；
- ❌ fallback 链路中携带/缓存任何密钥。

---

## 5. 选择状态的生命周期
- `ACTIVE_PROVIDER` 持久化于 `.env`（用户意图，长期有效）；
- `provider_status`（available/unavailable/error）为运行时探测，进程内缓存，重启重建（见 `02_REGISTRY.md` §4）；
- 二者分离：用户选择 ≠ 运行时可用性。UI 同时展示「你选了 X」与「X 当前 Y」。

---

## 6. 与 Agent / Tool 层的耦合说明
- `agent_runtime.py:362`、`tools.py:3341` 当前不传 provider → 继承 `ACTIVE_PROVIDER`（与现状一致）。
- FC 闭环硬依赖 OpenAI `tools/tool_calls`（`tools.py:3355`）：若所选 Provider 不支持 tool_calling，闭环退化为纯文本（已有行为）。Selection 层**不为此特殊分支**，能力差异由 `07_CAPABILITY_MATRIX.md` 声明并由用户在切换时知情。

> 🛑 设计态。Phase C 才落地 Resolver 与 Settings 扩展。
