# 02 — Provider Registry（Phase 10-B · 单一真相）

- **阶段**：Phase 10-B · 架构设计
- **关联**：`01_ARCHITECTURE.md` §2.1；spec §十九
- **纪律**：设计态，零代码。本文件定义 Registry 的形态、职责边界与内容。

---

## 1. 定义

**Provider Registry = 已识别 Provider 的元数据单一真相（Single Source of Truth）。**

它**只管 Metadata，不管执行**（spec §十九）。
- ✅ 存放：Provider 身份、类型、端点模板、认证需求、隐私类、能力引用、探测主机。
- ❌ 不存放：API Key / 运行时连接 / 执行逻辑 / 用户选择状态。

> 密钥仍在 `.env`（经 `config.ENV_KEYS` 白名单，`config.py:482`）。Registry 不含任何秘密。

---

## 2. 存储形态决策

| 候选 | 评估 | 决策 |
|---|---|---|
| YAML 文件 `providers.yaml` | 需引入解析器；与现有「env 唯一配置源」范式不一致 | ✗ |
| Python 模块 `provider_registry.py::PROVIDER_SPECS` | 可审查、可类型化、随仓版本化、零新依赖 | ✅ **采用** |
| 数据库表 | 过度工程；本地优先无需 | ✗ |

→ Registry 以**代码内常量字典**存在，随 Git 版本化、可 Review、无密钥。

---

## 3. 数据模型（ProviderSpec）

```python
# provider_registry.py（设计态伪代码，Phase C 落地）
PROVIDER_SPECS: dict[str, dict] = {
    "agnes": {
        "id": "agnes",
        "kind": "cloud",
        "display_name": "Agnes AI（云端）",
        "env_prefix": "AGNES",          # → AGNES_BASE_URL / AGNES_API_KEY / AGNES_MODEL
        "auth_required": True,
        "openai_compatible": True,
        "hosts": [],                     # 云端无固定 localhost
        "default_model": "agnes-2.5-flash",
        "privacy_class": "cloud",       # 数据出本机
        "capability_ref": "agnes",      # → 07_CAPABILITY_MATRIX.md
        "user_selectable": True,
    },
    "llm2": {
        "id": "llm2",
        "kind": "cloud",
        "display_name": "第二云端 Provider（OpenAI 兼容）",
        "env_prefix": "LLM2",
        "auth_required": True,
        "openai_compatible": True,
        "hosts": [],
        "default_model": "",
        "privacy_class": "cloud",
        "capability_ref": "openai_compatible",
        "user_selectable": True,
    },
    "ollama": {
        "id": "ollama",
        "kind": "local",
        "display_name": "Ollama（本地）",
        "env_prefix": "OLLAMA",
        "auth_required": False,
        "openai_compatible": True,
        "hosts": ["127.0.0.1:11434"],    # 仅已知 localhost（D-06）
        "default_model": "",
        "privacy_class": "local",        # 数据不出本机
        "capability_ref": "local_ollama",
        "user_selectable": True,
    },
    "lmstudio": {
        "id": "lmstudio",
        "kind": "local",
        "display_name": "LM Studio（本地）",
        "env_prefix": "LMSTUDIO",
        "auth_required": False,
        "openai_compatible": True,
        "hosts": ["127.0.0.1:1234"],
        "default_model": "",
        "privacy_class": "local",
        "capability_ref": "local_lmstudio",
        "user_selectable": True,
    },
    "mlx": {
        "id": "mlx",
        "kind": "local",
        "display_name": "MLX（本地 · Apple Silicon）",
        "env_prefix": "MLX",
        "auth_required": False,
        "openai_compatible": True,
        "hosts": ["127.0.0.1:8080"],
        "default_model": "",
        "privacy_class": "local",
        "capability_ref": "local_mlx",
        "user_selectable": True,
    },
}
```

### 3.1 字段语义
| 字段 | 含义 | 约束 |
|---|---|---|
| `kind` | `cloud` \| `local` | 驱动隐私类与探测逻辑 |
| `env_prefix` | 配置键前缀 | 解析 `config.<PREFIX>_BASE_URL/_API_KEY/_MODEL` |
| `auth_required` | 是否带 Bearer | Local = False（§2.3） |
| `hosts` | 探测主机列表 | **仅 `127.0.0.1`/`localhost`**（D-06） |
| `privacy_class` | `cloud` \| `local` | 直接回答 G-04 |
| `capability_ref` | 能力矩阵键 | 见 `07_CAPABILITY_MATRIX.md` |
| `user_selectable` | 是否出现在设置下拉 | 预留；当前全 True |

---

## 4. 运行时状态（不进 Registry）

`status`（available / unavailable / error）是**运行时探测结果**，不得固化进 Registry 常量：
- 存于轻量内存缓存（`provider_status_cache`，进程内 dict），随探测刷新；
- 经 `/api/config` 暴露（D-03：REST 而非事件）；
- 进程重启后重新探测，不持久化（避免 stale 状态）。

---

## 5. 与选择层、解析层的关系

```
Registry(PROVIDER_SPECS)  ──读──►  Resolver.resolve(id)
                                       │  + config.<PREFIX>_*（密钥/模型）
                                       ▼
                                  ProviderBinding
                                       │
                                       ▼
                                  Adapter（agnes_completion）
```

- Registry 是**静态元数据**，Resolver 是**动态绑定**，二者分离。
- 新增 Provider = 在 `PROVIDER_SPECS` 加一条 + 在 `ENV_KEYS` 登记前缀 + 在能力矩阵加一条。**无需改动任何调用方**（D-02）。

---

## 6. 治理与扩展纪律
- Registry 内容变更须随 Git Review（代码即配置，可审计）。
- 禁止在 Registry 内硬编码密钥、禁止写死运行时状态。
- 禁止为「未登记主机」动态生成 Spec（防扫描/防任意外联，D-06）。

> 🛑 本文件为设计。Phase C 才落地 `provider_registry.py`。
