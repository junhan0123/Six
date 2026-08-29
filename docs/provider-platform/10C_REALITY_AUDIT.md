# 10-C — Implementation Reality Audit（实现前真实读盘）

- **阶段**：Xiao6 AI OS · Phase 10-C · Provider Architecture Minimal Implementation
- **日期**：2026-08-08
- **纪律**：本文件产出时**零代码改动**。所有结论均为真实读盘所得，逐条带文件:行号。
- **依据**：Phase 10-C spec §一（先读真实项目再写代码）、§十八（Audit → Implement → Verify → Regression → Document → STOP）
- **上游权威**：Golden State L21（事件合约 FROZEN 71/8）、L40（禁第二 Runtime/Memory/EventBus/Permission）；`docs/product-constitution/09_LOCAL_FIRST.md` §4/§6；Phase 10-B 设计（`docs/ai-provider/`）

---

## 0. 本次实际读取 / 扫描清单

| 类别 | 对象 | 方式 |
|---|---|---|
| 设计真相 | `docs/ai-provider/10_REALITY_AUDIT.md`、`01_ARCHITECTURE.md`、`02_REGISTRY.md`（全文） | 真实读取 |
| 后端核心 | `xiao6-ui/llm.py`（全文 170 行） | 真实读取 |
| 配置权威 | `xiao6-ui/config.py`（全文 549 行） | 真实读取 |
| HTTP 层 | `xiao6-ui/server.py:1465-1834`（config GET/POST、models、test-llm） | 真实读取 |
| 前端设置 | `xiao6-ui/settings.js:289-402, 744-760`；`index.html:524, 675-745` | 真实读取 |
| 调用点 | 全仓 `agnes_completion` grep | 真实扫描 |
| 选择器 | 全仓 `_provider_creds` / `ACTIVE_LLM` / `AGNES_PROVIDER` grep | 真实扫描 |
| 本地 Provider | 全仓 `ollama` / `11434` / `lmstudio` / `LM Studio` / `mlx` grep（排除 `python/Lib`、`node_modules`） | 真实扫描 |
| 环境 | `xiao6-ui/.env` / `.env.example` 键名（不读值） | 真实扫描 |
| 工程状态 | `git status --short` / `git log -1` | 真实执行 |

---

## 1. 真实代码事实（带行号，实现的唯一依据）

### 1.1 LLM 出口链（`llm.py`）

| 事实 | 位置 | 说明 |
|---|---|---|
| 唯一出网点 | `llm.py:18` `_urlopen_with_proxy(req, timeout)` | 显式 `ProxyHandler({})` 强制绕过环境变量代理（`llm.py:41,54`）——**这对 127.0.0.1 本地探测至关重要**，本地请求不会被 `XIAO6_PROXY_URL` 劫持 |
| 唯一凭据解析点 | `llm.py:65-80` `_provider_creds(provider=None)` | 返回 4 元组 `(base, key, model, supports_reasoning)` |
| 选择表达式 | `llm.py:72` | `p = (provider or config.ACTIVE_LLM or config.AGNES_PROVIDER or "agnes").strip().lower()` |
| 第二 Provider 分支 | `llm.py:73-79` | `p in ("llm2","secondary","openai","custom")` → `LLM2_*`，回落 `AGNES_*` |
| 唯一 LLM HTTP 出口 | `llm.py:83` `agnes_completion(...)` | 形参已含 `provider=None` |
| 解析调用 | `llm.py:89` | `_base,_key,_model,_supports = _provider_creds(provider)` |
| URL 拼接 | `llm.py:124` | `_base + "/chat/completions"`（OpenAI 兼容） |
| **无条件 Bearer** | `llm.py:128` | `"Authorization": "Bearer " + _key` —— 本地 Provider 必须能跳过此头 |
| 出网 | `llm.py:133` | `_urlopen_with_proxy(req, timeout=timeout)` |
| 日志安全 | `llm.py:141, 166` | 仅打印 `provider=` 与错误码，**不打印 key**（已合规 §七） |
| 配额门 | `llm.py:116-117` | `quota.estimate_input_tokens` + `wait_if_needed`（云端语义；本地是否计费另议，见 §4 IA-5） |

**`_provider_creds` 的调用方只有 1 处**（`llm.py:89`）——全仓 grep 证实。→ **可安全内部升级，零外部影响。**

### 1.2 配置权威（`config.py`）

| 事实 | 位置 |
|---|---|
| `AGNES_*` / `LLM2_*` / `ACTIVE_LLM` 声明 | `config.py:13-23` |
| `ACTIVE_LLM` 恒非空 | `config.py:198` `= (os.environ.get("ACTIVE_LLM","agnes") or "agnes").strip().lower()` |
| `AGNES_PROVIDER` 取值域 | `config.py:191` 注释 `agnes \| openai \| custom` |
| `ENV_KEYS` 白名单 | `config.py:343-450`，其中 `LLM2_*`/`ACTIVE_LLM` 在 `config.py:387-391` |
| 持久化护栏 | `config.py:489-492` `allowed = set(ENV_KEYS.keys())`；未登记键**静默丢弃** |
| 热重载 | `config.py:524` `reload()` 在写盘后立即刷新内存 |

### 1.3 HTTP 层（`server.py`）

| 端点 | 位置 | 现状 |
|---|---|---|
| `GET /api/config` | `server.py:259-260` → `1472-1581` | `llm` 段 `1483-1495`；脱敏范式 `key_present: bool`（`1488`、`1493`） |
| `POST /api/config` | `server.py:977-978` → `1583-1702` | 白名单 `1590-1683`（含 `ACTIVE_LLM` @`1636`）；Key 空值跳过 `1689-1691` |
| `POST /api/models` | `server.py:983-984` → `1743-1771` | **无条件带 Bearer**（`1755`）；复用 `_urlopen_with_proxy`（`1758`） |
| `POST /api/test-llm` | `server.py:985-986` → `1773-1822` | **无条件带 Bearer**（`1797`）；返回 `latency_ms` |
| health 也暴露 provider | `server.py:208` | `"provider": config.AGNES_PROVIDER` |
| 启动日志 | `server.py:2620` | 打印 `提供商: config.AGNES_PROVIDER` |

### 1.4 调用方现状（Backward Compatibility 基线）

`agnes_completion` 真实调用点 **17 处 / 11 个模块 + server.py**：

```
agent_runtime.py:362      cognitive/extractor.py:128   goals.py:412
goal_decision_engine.py:128   memory.py:74, 92, 144    memory_distiller.py:114
notes.py:242, 488, 543    review_clone.py:48, 55       server.py:2024
social_inbound.py:138     tools.py:3322, 3341, 3374
```

**关键：0 处显式传 `provider=`**（grep 证实，唯一匹配是 `llm.py:83` 的形参定义本身）。
→ 全部调用方**隐式继承 `config.ACTIVE_LLM`**。这正是「换 Provider 无需改调用方」的既有基础（D-02 成立）。

### 1.5 前端设置现状

| 事实 | 位置 |
|---|---|
| 导航项「LLM 模型」 | `index.html:524` `data-tab="model"` |
| Tab 主体 | `index.html:677-745` |
| 「提供商」下拉（3 项：agnes / openai / custom） | `index.html:688-693` |
| 端点 / 模型 / Key / 获取模型 / 测试连接 | `index.html:696-712` |
| DOM 引用 | `settings.js:289-299` |
| 保存动作写入的键 | `settings.js:328-334` → `AGNES_PROVIDER` / `AGNES_BASE_URL` / `AGNES_MODEL` /（非空才写）`AGNES_API_KEY` |
| 回填来源 | `settings.js:751-760` 读 `/api/config` 的 `d.llm.*` |
| 已有「获取模型」 | `settings.js:344-372` → `POST /api/models` |
| 已有「测试连接」 | `settings.js:374-399` → `POST /api/test-llm` |

### 1.6 本地 Provider 现状

全仓干净扫描（排除 `python/Lib`、`node_modules`）：
```
ollama / 11434 / lmstudio / "LM Studio" / mlx  →  命中 0
```
→ **G-01 确认成立**：本地模型接入路径 = 0，违反 `09_LOCAL_FIRST §4`。这是 Phase 10-C 的首要合规缺口。

### 1.7 环境与工程状态

- `.env` 现有键 23 个，**不含 `ACTIVE_LLM`、不含任何 `LLM2_*`** → 运行时取默认 `"agnes"`，与生产行为一致。
- `git status`：工作区**已存在大量既有未提交改动**（文档迁移 R + `README.md` M），非本 Phase 产生。
- 当前分支 `master`，`HEAD = 90bf66c`。
- **纪律**：本 Phase 全程不 `git add` / 不 `git commit`（spec §十七、§二十）。

---

## 2. 设计（Phase 10-B）↔ 代码 一致性核对

| 设计断言 | 真实代码 | 判定 |
|---|---|---|
| `agnes_completion` 是唯一 LLM 出口 | `llm.py:83`，17 调用点全部经此 | ✅ 一致 |
| `_provider_creds` 是唯一解析点 | `llm.py:65`，仅 1 处调用 | ✅ 一致（且升级零风险） |
| 全链路 `stream=False` | 17 调用点均未传 `stream=True`（`tools.py:3322/3374`、`memory.py:74` 等显式 `stream=False`） | ✅ 一致 → streaming **NOT SUPPORTED** 属实 |
| 已有双 Provider 半成品 | `config.py:19-23` + `llm.py:73-79` | ✅ 一致 |
| 本地路径 = 0 | 扫描命中 0 | ✅ 一致 |
| `/api/config` 脱敏范式 | `server.py:1488/1493` `key_present` | ✅ 一致，可原样扩展 |
| Settings「LLM 模型」Tab 可复用 | `index.html:677-745` | ✅ 一致（D-08 可执行） |
| 12 调用方不传 provider | 实测 **17 调用点 / 0 传参** | ✅ 一致（数量修正见 §3 DC-05） |

---

## 3. DESIGN CONFLICT 清单（spec §十八：冲突先记录，不擅自改设计）

> 处理原则：**上位权威优先**。spec §二（架构铁律）> Phase 10-B 设计文档 > 实现便利。
> 以下冲突均**不修改 Phase 10-B 设计文档**，只在实现层按上位权威取舍并留痕。

### DC-01 ｜`ACTIVE_PROVIDER` vs `ACTIVE_LLM`（**阻断级**）
- **设计**：`01_ARCHITECTURE.md §6.1` 要求新增 env 键 `ACTIVE_PROVIDER`（「取代/别名 `ACTIVE_LLM`」）。
- **代码**：`ACTIVE_LLM` 已存在且已是**事实上的唯一选择器**——`config.py:198` 定义、`config.py:391` 已入 `ENV_KEYS`、`server.py:1636` 已在 POST 白名单、`llm.py:72` 已读取。
- **冲突**：新增 `ACTIVE_PROVIDER` 将产生**第二个 Selection / Configuration authority**，直接违反 spec §二「禁新增第二 Selection authority / 第二 Configuration authority」。
- **裁决**：**不新增 `ACTIVE_PROVIDER`**，复用 `ACTIVE_LLM` 作为唯一 active provider 选择键。设计文档的意图（「唯一选择器」）被完整满足，只是键名沿用既有。
- **影响**：`.env` 无需新增选择键；POST 白名单无需扩；默认值 `"agnes"` 保证向后兼容 100%。

### DC-02 ｜本地 Provider 配置键命名内部不一致
- **设计 A**：`01_ARCHITECTURE.md §6.1` 写 `OLLAMA_HOST` / `LMSTUDIO_HOST` / `MLX_HOST`。
- **设计 B**：`02_REGISTRY.md §3.1` 规定 Resolver 解析 `config.<PREFIX>_BASE_URL / _API_KEY / _MODEL`。
- **冲突**：同一份设计内两种键名规则；且既有代码范式是 `AGNES_BASE_URL`（`config.py:188`）、`LLM2_BASE_URL`（`config.py:194`）。
- **裁决**：统一采用 **`<PREFIX>_BASE_URL`**（`OLLAMA_BASE_URL` / `LMSTUDIO_BASE_URL` / `MLX_BASE_URL`），与既有两个 Provider 命名范式一致，Resolver 得以用**同一条规则**解析全部 5 个 Provider（无特例分支）。

### DC-03 ｜Registry `default_model` 造成双默认值真相
- **设计**：`02_REGISTRY.md:46` 给 agnes 写死 `default_model: "agnes-2.5-flash"`。
- **代码**：`config.py:190` 真实默认 `"agnes-2.0-flash"`。
- **冲突**：Registry 与 config 各持一个默认模型 → 双真相（违反 Single Source Rule）。
- **裁决**：**agnes / llm2 的 `default_model` 留空**，模型一律由 `config.<PREFIX>_MODEL` 提供；`default_model` 仅对本地 Provider 作为**空值兜底提示**使用（本地模型名因人而异，同样留空）。Registry 只管元数据，不复制配置值。

### DC-04 ｜Resolver 返回类型 vs 调用方兼容
- **设计**：`01_ARCHITECTURE.md §2.2` 要求 `resolve(provider_id) → ProviderBinding`（新结构）。
- **代码**：`llm.py:89` 解包 4 元组；虽仅 1 处，但 `agnes_completion` 的形参契约被 17 个调用点依赖。
- **裁决**：**双出口 · 单真相**——
  - 新增 `llm.resolve_provider(provider_id) -> dict`（ProviderBinding，含 `auth_required/kind/privacy_class/capabilities`），作为唯一解析实现；
  - 保留 `_provider_creds(provider)` 4 元组签名不变，内部**委托** `resolve_provider`（薄适配）。
  - 结果：0 个调用方需要修改，且不产生第二套解析逻辑。

### DC-05 ｜调用点数量口径
- **设计/前序审计**：称「12 个调用方」。
- **实测**：**17 个调用点**，分布在 **11 个模块 + `server.py`**（= 12 个文件）。
- **裁决**：非架构冲突，仅口径差异。回归清单以**17 个调用点 / 12 个文件**为准（§十五）。

### DC-06 ｜config **属性名** ≠ **环境变量键名**（agnes 特例，实现期新发现）
- **设计**：`02_REGISTRY.md §3.1` 规定 Resolver 统一读 `config.<PREFIX>_BASE_URL / <PREFIX>_API_KEY / <PREFIX>_MODEL`。
- **代码实测**（`config.py:188-196`）：

  | Provider | env 键 | config 属性名 | 是否同名 |
  |---|---|---|---|
  | agnes | `AGNES_BASE_URL` | `config.AGNES_BASE` | ❌ |
  | agnes | `AGNES_API_KEY` | `config.AGNES_KEY` | ❌ |
  | agnes | `AGNES_MODEL` | `config.AGNES_MODEL` | ✅ |
  | llm2 | `LLM2_BASE_URL` | `config.LLM2_BASE_URL` | ✅ |
  | llm2 | `LLM2_API_KEY` | `config.LLM2_API_KEY` | ✅ |
  | llm2 | `LLM2_MODEL` | `config.LLM2_MODEL` | ✅ |

- **冲突**：若 Resolver 按设计的单一规则 `getattr(config, PREFIX + "_BASE_URL")` 解析，**agnes 会解析失败**（`config.AGNES_BASE_URL` 不存在），导致主链路 100% 中断——这是**阻断级实现风险**。
- **可选方案**：
  - (a) 重命名 `config.AGNES_BASE → AGNES_BASE_URL`：需改 `llm.py`、`server.py`、`settings` 回填等全部引用 → **违反 spec §十七「禁借机重构」**，且触碰主链路。
  - (b) Registry 显式声明属性名映射（`config_attrs`），Resolver 只按 Registry 声明取值 → 零重构、无特例分支、映射本身即元数据。
- **裁决**：采用 **(b)**。`PROVIDER_SPECS[*]` 增加 `config_attrs = {base/key/model: <config 属性名>}` 与 `env_keys = {base/key/model: <env 键名>}` 两张显式映射表。Resolver 保持**单一通用规则**（读 Registry 声明），既满足设计「统一解析」意图，又零改动既有属性名。
- **副产物**：`env_keys` 同时供 §十二 Settings 保存路径与 `ENV_KEYS` 登记核对使用，避免 UI 写错键名（G-11 同类问题的结构性预防）。

---

## 4. 实现调整项（Implementation Adjustments）

| 编号 | 调整 | 理由 |
|---|---|---|
| IA-1 | `agnes_completion` 新增 `auth_required=None` 形参；`None` = 由 binding 自动推导，显式传值可覆盖 | 调用方**无需感知**，仍是零改动；设计 §2.3 的「加 `auth_required` 形参」得以满足 |
| IA-2 | 本地探测复用 `llm._urlopen_with_proxy` | `llm.py:41/54` 已强制绕过环境代理，127.0.0.1 不会被代理劫持；且不新建 HTTP 路径 |
| IA-3 | 探测只对 `PROVIDER_SPECS[*].hosts` 中已登记的 `127.0.0.1:*` 发 `GET /models`，**超时 ≤ 2s、不重试、不扫描** | spec §八；D-06 |
| IA-4 | `provider_status` 存进程内 dict，不持久化、不进事件 | `02_REGISTRY §4`；D-03 |
| IA-5 | 本地 Provider 仍走 `quota.wait_if_needed`（不改配额逻辑） | spec §十七「禁借机重构」；配额语义调整属独立议题，记为已知债 |
| IA-6 | Settings「提供商」下拉改为写 `ACTIVE_LLM`（真选择器），`AGNES_PROVIDER` 保持原样不动 | 修复 G-11（见 §5），且不删除既有键 |
| IA-7 | 不修改 `server.py:208` health 与 `server.py:2620` 启动日志 | 非本 Phase scope，避免扩散 |
| IA-8 | Registry 携带 `config_attrs` / `env_keys` 双映射，Resolver 只按声明取值，不硬编码任何 Provider 分支 | DC-06 裁决；保留 `config.AGNES_BASE` 等既有属性名不重命名 |

---

## 5. 新增缺口发现（本次审计新增）

### G-11 ｜Settings「提供商」下拉是**运行时无效的假选择器**（诚实披露）

- `settings.js:329` 把下拉值写入 `AGNES_PROVIDER`；
- 但 `llm.py:72` 的选择表达式为
  `p = (provider or config.ACTIVE_LLM or config.AGNES_PROVIDER or "agnes")`；
- 而 `config.py:198` 保证 `ACTIVE_LLM` **恒为非空字符串**（默认 `"agnes"`）；
- → **`config.AGNES_PROVIDER` 永远短路，从不参与 Provider 选择**。

**后果**：用户在设置里把「提供商」选成 `OpenAI` / `自定义端点（本地/其他）` 并保存，界面显示成功，但后端**仍然走 Agnes**。这也解释了为何 `LLM2_*` 骨架自始至终从未被真正激活。

**判定**：`DESIGNED ONLY`（UI 存在，运行时未接通）。
**Phase 10-C 必须修复**：让下拉成为真实的 Provider 选择器（写 `ACTIVE_LLM`），并在 UI 上诚实反映 provider 身份、隐私类与可用状态（spec §十一/§十二）。

### G-12 ｜`/api/models` 与 `/api/test-llm` 对本地 Provider 会发无意义 Bearer
- `server.py:1755` / `server.py:1797` 无条件拼 `Authorization: Bearer `（key 为空时是 `"Bearer "`）。
- 多数本地端点会忽略该头，但属不诚实实现。
- **Phase 10-C 处理**：按 binding 的 `auth_required` 决定是否附加该头（最小改动，不改端点语义）。

---

## 6. 实现边界自检（写码前的红线确认）

| 红线 | 本 Phase 计划 | 状态 |
|---|---|---|
| 不新建第二 Runtime / Agent / LLM client | 仅升级 `llm.py` 内部 + 新增纯元数据模块 | ✅ |
| 不新建第二 EventBus / 不增领域事件（71/8 FROZEN） | Provider 状态**只走 REST `/api/config`** | ✅ |
| 不新建第二 Selection / Configuration authority | 复用 `ACTIVE_LLM` + `ENV_KEYS`（DC-01） | ✅ |
| 不触碰 AI Presence 三唯一 | 不改 `avatar-state.js` / `refreshHud` / `data-presence` | ✅ |
| API Key 不下发前端 | 沿用 `key_present: bool` 范式 | ✅ |
| 禁端口扫描 / 自动发现 | 仅白名单 `127.0.0.1` 已登记端口 | ✅ |
| Fallback 默认 OFF、禁 Silent Cloud | 本 Phase **不实现任何自动 fallback**，`fallback_enabled` 常量 `False` | ✅ |
| 禁借机重构 / 清理死代码 | 不动 `AGNES_PROVIDER`、不动 quota、不动 12 文件调用方 | ✅ |
| 不提交 Git | 全程只改工作区 | ✅ |

---

## 7. 审计结论

- **设计与代码整体一致**，Phase 10-B 的三层抽象（Spec → Resolver → Adapter）在真实代码上**可以无损落地**。
- **6 项 DESIGN CONFLICT 已识别并按上位权威裁决**（DC-01 / DC-06 为阻断级：分别避免了第二配置权威、避免了 agnes 主链路解析失败）。
- **2 项新缺口**（G-11 假选择器、G-12 本地无意义 Bearer）为本次审计新增，均纳入实现范围。
- **本文件产出过程零代码改动**，工作区无新增/修改的 `.py` / `.js` / `.html` 文件。

> ✅ Audit 完成，允许进入 Implement 阶段。
