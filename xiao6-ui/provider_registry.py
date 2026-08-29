#!/usr/bin/env python3
"""小6 · Provider Registry（Phase 10-C · 单一元数据真相）

职责边界（严格最小）：
- 本模块**只声明元数据**：Provider 身份、配置键映射、鉴权要求、隐私类、能力矩阵。
- 本模块**不做**：不读 config、不发 HTTP、不持有运行时状态、不做选择决策、不缓存探测结果。
  → 解析归 llm.resolve_provider()；选择归 config.ACTIVE_LLM；探测状态归 server 进程内 dict。

架构约束（Phase 10-C spec §二 / §三）：
- 不新增第二 Runtime / Agent / LLM client / EventBus / Selection authority / Configuration authority。
- 不新增领域事件（事件合约 FROZEN 71/8）。
- 所有出网仍走 llm._urlopen_with_proxy 的唯一 HTTP 路径。

设计冲突裁决留痕（docs/provider-platform/10C_REALITY_AUDIT.md §3）：
- DC-01：不新增 ACTIVE_PROVIDER，active provider 唯一键 = config.ACTIVE_LLM。
- DC-02：本地 Provider 配置键统一 <PREFIX>_BASE_URL（非 <PREFIX>_HOST）。
- DC-03：default_model 一律留空，模型真相唯一归 config.<PREFIX>_MODEL。
- DC-06：config 属性名 ≠ env 键名（agnes 特例），故显式声明 config_attrs / env_keys 双映射，
         Resolver 按声明取值，保持单一通用规则且零重构既有属性名。
"""

# ---------------------------------------------------------------------------
# 常量：隐私类（spec §七）
# ---------------------------------------------------------------------------
PRIVACY_LOCAL = "local"      # 数据不出本机
PRIVACY_CLOUD = "cloud"      # 数据发往第三方云端

# ---------------------------------------------------------------------------
# 常量：Provider 种类
# ---------------------------------------------------------------------------
KIND_CLOUD = "cloud"
KIND_LOCAL = "local"

# ---------------------------------------------------------------------------
# 能力矩阵（spec §九：必须诚实，不得声称未实现的能力）
# 真相依据：llm.agnes_completion 全链路 stream=False，无 SSE 解析、无增量回调。
#   → streaming 对所有 Provider 均为 False（NOT SUPPORTED），不因 Provider 而异。
# tool_calling / reasoning 取决于具体模型，标 True 表示「链路支持透传」，非保证模型支持。
# ---------------------------------------------------------------------------
_CAP_OPENAI_COMPATIBLE = {
    "chat": True,               # IMPLEMENTED
    "tool_calling": True,       # MODEL DEPENDENT（链路已透传 tools/tool_choice）
    "reasoning_effort": True,   # MODEL DEPENDENT（不支持时 llm.py 自动降级重试）
    "streaming": False,         # NOT SUPPORTED（全链路 stream=False，Phase 10-C 不实现）
    "embeddings": False,        # NOT SUPPORTED（本 Phase OUT OF SCOPE）
    "vision": False,            # NOT SUPPORTED（本 Phase OUT OF SCOPE）
}


def _caps(**overrides):
    c = dict(_CAP_OPENAI_COMPATIBLE)
    c.update(overrides)
    return c


# ---------------------------------------------------------------------------
# PROVIDER_SPECS · 唯一元数据真相
#
# 字段说明：
#   id                 Provider 标识（= config.ACTIVE_LLM 的取值）
#   label              UI 展示名（中文）
#   kind               cloud | local
#   privacy_class      local | cloud（spec §七）
#   auth_required      是否需要 Authorization: Bearer（本地端点为 False）
#   openai_compatible  是否 OpenAI /chat/completions 兼容（当前全部为 True）
#   config_attrs       config 模块的**属性名**映射（DC-06）
#   env_keys           .env / ENV_KEYS 的**环境变量键名**映射（DC-06）
#   default_base_url   config 缺省时的兜底 base（仅本地 Provider 使用；云端留空→由 config 提供）
#   default_model      一律留空（DC-03：模型真相唯一归 config.<PREFIX>_MODEL）
#   hosts              允许本地探测的白名单主机（spec §八：仅 127.0.0.1，禁扫描/禁自动发现）
#   probe_path         本地可用性探测路径（GET，超时 ≤2s，不重试）
#   user_selectable    是否在 Settings 下拉中可选
#   aliases            历史别名（向后兼容 llm.py:73 既有取值）
#   capabilities       能力矩阵（诚实）
# ---------------------------------------------------------------------------
PROVIDER_SPECS = {
    "agnes": {
        "id": "agnes",
        "label": "Agnes（云端 · 主用）",
        "kind": KIND_CLOUD,
        "privacy_class": PRIVACY_CLOUD,
        "auth_required": True,
        "openai_compatible": True,
        "config_attrs": {"base": "AGNES_BASE", "key": "AGNES_KEY", "model": "AGNES_MODEL"},
        "env_keys": {"base": "AGNES_BASE_URL", "key": "AGNES_API_KEY", "model": "AGNES_MODEL"},
        "default_base_url": "",
        "default_model": "",
        "hosts": [],
        "probe_path": "",
        "user_selectable": True,
        "aliases": ("primary",),
        "capabilities": _caps(),
    },
    "llm2": {
        "id": "llm2",
        "label": "第二供应商（OpenAI 兼容 · 自定义）",
        "kind": KIND_CLOUD,
        "privacy_class": PRIVACY_CLOUD,
        "auth_required": True,
        "openai_compatible": True,
        "config_attrs": {"base": "LLM2_BASE_URL", "key": "LLM2_API_KEY", "model": "LLM2_MODEL"},
        "env_keys": {"base": "LLM2_BASE_URL", "key": "LLM2_API_KEY", "model": "LLM2_MODEL"},
        "default_base_url": "",
        "default_model": "",
        "hosts": [],
        "probe_path": "",
        "user_selectable": True,
        # 历史别名：llm.py 既有分支接受 secondary/openai/custom，全部归一到 llm2
        "aliases": ("secondary", "openai", "custom"),
        "capabilities": _caps(),
    },
    "ollama": {
        "id": "ollama",
        "label": "Ollama（本地）",
        "kind": KIND_LOCAL,
        "privacy_class": PRIVACY_LOCAL,
        "auth_required": False,
        "openai_compatible": True,
        "config_attrs": {"base": "OLLAMA_BASE_URL", "key": "", "model": "OLLAMA_MODEL"},
        "env_keys": {"base": "OLLAMA_BASE_URL", "key": "", "model": "OLLAMA_MODEL"},
        "default_base_url": "http://127.0.0.1:11434/v1",
        "default_model": "",
        "hosts": ["127.0.0.1:11434"],
        "probe_path": "/models",
        "user_selectable": True,
        "aliases": (),
        "capabilities": _caps(),
    },
    "lmstudio": {
        "id": "lmstudio",
        "label": "LM Studio（本地）",
        "kind": KIND_LOCAL,
        "privacy_class": PRIVACY_LOCAL,
        "auth_required": False,
        "openai_compatible": True,
        "config_attrs": {"base": "LMSTUDIO_BASE_URL", "key": "", "model": "LMSTUDIO_MODEL"},
        "env_keys": {"base": "LMSTUDIO_BASE_URL", "key": "", "model": "LMSTUDIO_MODEL"},
        "default_base_url": "http://127.0.0.1:1234/v1",
        "default_model": "",
        "hosts": ["127.0.0.1:1234"],
        "probe_path": "/models",
        "user_selectable": True,
        "aliases": (),
        "capabilities": _caps(),
    },
    "mlx": {
        "id": "mlx",
        "label": "MLX / llama.cpp（本地）",
        "kind": KIND_LOCAL,
        "privacy_class": PRIVACY_LOCAL,
        "auth_required": False,
        "openai_compatible": True,
        "config_attrs": {"base": "MLX_BASE_URL", "key": "", "model": "MLX_MODEL"},
        "env_keys": {"base": "MLX_BASE_URL", "key": "", "model": "MLX_MODEL"},
        "default_base_url": "http://127.0.0.1:8080/v1",
        "default_model": "",
        "hosts": ["127.0.0.1:8080"],
        "probe_path": "/models",
        "user_selectable": True,
        "aliases": (),
        "capabilities": _caps(),
    },
}

# 默认 Provider（与 config.py:198 的 ACTIVE_LLM 默认值保持一致）
DEFAULT_PROVIDER_ID = "agnes"

# 别名 → 正式 id（由 PROVIDER_SPECS 自动派生，避免第二份手写表）
_ALIAS_MAP = {}
for _pid, _spec in PROVIDER_SPECS.items():
    _ALIAS_MAP[_pid] = _pid
    for _a in _spec.get("aliases", ()):
        _ALIAS_MAP[_a] = _pid


def normalize_provider_id(provider_id):
    """把任意输入（含历史别名 / 大小写 / 空值）归一为正式 Provider id。

    未知取值一律回退 DEFAULT_PROVIDER_ID，保证主链路永不因配置错字中断
    （与 llm._provider_creds 原有「未知回退主用」语义完全一致）。
    """
    p = (provider_id or "").strip().lower()
    return _ALIAS_MAP.get(p, DEFAULT_PROVIDER_ID)


def get_spec(provider_id):
    """按 id / 别名取 Spec（只读元数据）。未知回退默认 Provider。"""
    return PROVIDER_SPECS[normalize_provider_id(provider_id)]


def list_specs():
    """返回全部 Spec（保持声明顺序）。供 /api/config 与 Settings 消费。

    注意：**不含** API Key、不含运行时状态（spec §七 / §十）。
    """
    return [PROVIDER_SPECS[pid] for pid in PROVIDER_SPECS]


def is_local(provider_id):
    return get_spec(provider_id)["kind"] == KIND_LOCAL


def local_probe_targets():
    """返回允许探测的 (provider_id, host) 列表 —— 白名单，禁扫描（spec §八）。"""
    out = []
    for pid, spec in PROVIDER_SPECS.items():
        for host in spec.get("hosts", ()):
            out.append((pid, host))
    return out


def public_view(provider_id):
    """Provider 的**安全公开视图**（可下发前端；绝不含 API Key）。"""
    s = get_spec(provider_id)
    return {
        "id": s["id"],
        "label": s["label"],
        "kind": s["kind"],
        "privacy_class": s["privacy_class"],
        "auth_required": s["auth_required"],
        "openai_compatible": s["openai_compatible"],
        "user_selectable": s["user_selectable"],
        "capabilities": dict(s["capabilities"]),
    }
