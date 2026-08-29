#!/usr/bin/env python3
"""
庄周 · 全局配置与常量
- 纯标准库
- 内置界面 (index.html / styles.css / app.js)
- API Key 仅从环境变量或同目录 .env 读取，绝不硬编码
- 支持运行时通过 update_env_file() 持久化，并立即刷新内存中的值
"""

import os

# ---- 运行时配置声明（由 reload() 从环境变量填充；此处仅声明类型，供静态检查/IDE）----
AGNES_BASE: str = ""
AGNES_KEY: str = ""
AGNES_MODEL: str = ""
AGNES_PROVIDER: str = ""
AGNES_REASONING: str = ""
# ---- 多 LLM 供应商（agnes 主用 + 可插拔第二供应商 llm2，OpenAI 兼容）----
LLM2_BASE_URL: str = ""
LLM2_API_KEY: str = ""
LLM2_MODEL: str = ""
LLM2_PROVIDER: str = ""
ACTIVE_LLM: str = "agnes"            # 当前生效聊天供应商：agnes | llm2
# ---- 本地 LLM 供应商（OpenAI 兼容，仅 127.0.0.1 白名单；Phase 10-C spec §八）----
# 注意：本地端点无 API Key（provider_registry 中 config_attrs.key 为空）。
# base 的 127.0.0.1 缺省值**唯一**归 provider_registry.PROVIDER_SPECS[<id>].default_base_url，
# 本处 reload 缺省留空，由 llm.resolve_provider 统一兜底（Single Source Rule，避免双源漂移，DC-02/DC-03）。
OLLAMA_BASE_URL: str = ""
OLLAMA_MODEL: str = ""
LMSTUDIO_BASE_URL: str = ""
LMSTUDIO_MODEL: str = ""
MLX_BASE_URL: str = ""
MLX_MODEL: str = ""
# ---- 新功能开关（KWS 唤醒 / 文档面板 / 成果审视分身）----
XIAO6_KWS_ENABLED: str = "true"
XIAO6_WAKE_PHRASE: str = "庄周,小周,小6"
XIAO6_KWS_SENSITIVITY: str = "0.6"
XIAO6_VOSK_KWS_ENABLED: str = "true"   # P8-2：优先用 Vosk 中文短语 KWS（开启且模型可用时）
XIAO6_DOC_DIR: str = "docs"
XIAO6_AUTO_REVIEW: str = "false"
TTS_VOICE: str = ""
TTS_RATE: str = ""
TTS_BACKEND: str = ""
GPT_SOVITS_URL: str = ""
GPT_SOVITS_REF_AUDIO: str = ""
GPT_SOVITS_PROMPT_TEXT: str = ""
# ---- Qwen3-TTS 本地声线（TTS_BACKEND=qwen3 时生效）----
QWEN3_TTS_URL: str = ""            # 推理服务（OpenAI 兼容 /v1），默认 http://127.0.0.1:8001/v1
QWEN3_TTS_MODEL: str = ""          # 模型名，默认 Qwen/Qwen3-TTS-12Hz-1.7B
QWEN3_TTS_VOICE: str = ""          # 默认声线；空=模型默认音色
QWEN3_TTS_CLONE_URL: str = ""      # 音色克隆服务（Base 克隆接口预留）
QWEN3_TTS_REF_AUDIO: str = ""      # 默认参考音频（音色克隆用）
HOTDATA_KEY: str = ""
AI_DISPLAY_NAME: str = ""
THEME: str = ""
MEMORY_GRAPH_ENABLED: bool = True
# Context Engine 五阶段管线（唯一 Context 系统，默认开启，env 可瞬时回退旧路径）
FEATURE_CONTEXT_ENGINE: bool = True
# P1 认知层：用户模型 + 情节记忆（默认开启，可在 .env 关闭瞬时回退）
FEATURE_USER_MODEL: bool = True
FEATURE_EPISODIC_MEMORY: bool = True
# Phase 2：EventBus 基础设施（SSE 扇出迁移门控；默认 ON，关闭即回退 SUBSCRIBERS 旧路径）
FEATURE_EVENTBUS: bool = False
# Phase 2：人格引擎（默认开启，可在 .env 关闭瞬时回退）
FEATURE_PERSONALITY: bool = True
# Phase 3：目标系统（Goal System，默认开启，可在 .env 关闭瞬时回退到 Phase 2）
FEATURE_GOAL_SYSTEM: bool = True
# P4-A：前端 Premium 精装层（premium.css + 沉浸式粒子背景）；默认开启，关闭即回退旧样式
FEATURE_PREMIUM_UI: bool = False
# Knowledge Platform：统一知识层（Knowledge Runtime 文件召回注入上下文，无 RAG/嵌入/向量库）；默认开启，关闭即不注入
FEATURE_KNOWLEDGE_PLATFORM: bool = True
# Phase 18：Personal Context Engine（当前用户状态五维视图，注册为 Context Source；默认开启，关闭即不注入）
FEATURE_PERSONAL_CONTEXT: bool = True
# Phase 37.2：Personal AI 统一画像（确认/纠正/蒸馏/双源对齐 Source；默认开启，关闭即不注入【个性化 · 统一画像】块）
FEATURE_PERSONAL_AI: bool = True
# Phase 19：Memory Intelligence 2.0（主动关联检索 + 重要性判断 Source；默认开启，关闭即不注入【长期记忆】块）
FEATURE_MEMORY_INTELLIGENCE: bool = True
# P4-C：主动智能 V2（目标停滞建议 / 简报今日建议段 / 周小结）；默认开启，关闭即回退旧主动行为
FEATURE_PROACTIVE_V2: bool = False
# P4-D：多端同步（同源 Web 客户端设备注册 / 设备清单）；默认开启，关闭即禁用 /api/devices
FEATURE_MULTI_DEVICE: bool = False
# P8-2：流式 TTS（edge-tts 逐帧推流 + 前端 MSE 边收边播）；默认开启，关闭即回退整段 blob
FEATURE_TTS_STREAM: bool = False
# 自我学习系统（显式反馈捕获 + LLM 蒸馏经验 + 注入上下文）；默认开启，关闭即不记录/不注入
FEATURE_SELF_LEARNING: bool = False
# Phase 8：Agent Runtime（编排状态机 + 授权内核 + 反思层）；P10-4 起默认开启（低危工具 auto 自驱）
FEATURE_AGENT_RUNTIME: bool = True
# P5.1：Cognitive Context Integration —— Agent Runtime 的 Planner Context 改由 Canonical Context Engine
# （context.facade.build_cognitive_context）生成。true=启用（默认新行为）；false=Agent Runtime 回退
# legacy 自构 prompt（DEPRECATE，不删）。仅新增此干净开关，不触碰任何既有 Feature Flag。
FEATURE_COGNITIVE_CONTEXT: bool = True
# P5.2：Canonical Cognitive Memory —— Cognitive / Agent Runtime 的记忆写入统一经
# cognitive.memory_adapter 落到 memory.py Canonical Memory API（唯一写入权威），
# legacy 表（user_model / episodes / conversation_memories）退化为兼容投影。
# true=启用（默认新行为）；false=单点回滚为「legacy 投影 only」写入（P5.2 前等价行为）。
FEATURE_CANONICAL_COGNITIVE_MEMORY: bool = True
# Phase 9：Goal Decision Engine（聊天自动建 Goal 前置决策门）；Step 2 起默认开启（per-goal 预批准协作已落地）
FEATURE_GOAL_DECISION: bool = True
# Phase 47.4 · P1：默认 Chat 统一 Capability Execution 适配器开关。
# true=默认 Chat 的能力执行经 capability_runtime（capability_os 选择真相 + ai_core.execution.run 执行入口 + CapabilityResult 契约）；
# false=回退到 P1 前直连 execute_tool / select_tools 行为（单点 rollback）。
FEATURE_CAPABILITY_RUNTIME: bool = True
# Agent Runtime 是否自动跑闭环（false=仅显式目标触发；true=可自驱）
AGENT_RUNTIME_AUTO: bool = False
# Policy Engine 未显式注册工具的默认权限（auto/confirm/session/never）；P10-4 起默认 auto（低危 auto，高危 confirm）
AGENT_POLICY_DEFAULT: str = "ask"
# 低危工具自动执行总开关（true=启用 P10-4 低危 auto 策略）
AGENT_LOW_RISK_DEFAULT: bool = True
# Phase 11 全息 HUD（常驻状态光环 / 情境 glance 卡 / 可选 3D 化身）
# 光环 + glance 默认开启（性能门控，CPU 超阈值自动降级 2D）；3D 化身默认关闭（重）
FEATURE_HUD_RING: bool = True
FEATURE_GLANCE_CARD: bool = True
FEATURE_AVATAR_SCENE: bool = False
# 光环性能门控阈值（CPU 占用 %），超限降级为 Canvas2D 实现
HUD_RING_PERF_THRESHOLD: int = 5
# Phase 12 记忆人格深度（蒸馏 + 人格 + 情感联结）
# 人格注入为纯 prompt 附加（零风险，与 FEATURE_PERSONALITY 同档），默认开启；
# 后台蒸馏/情感检查涉及定时计算，默认关闭、按需开启。
FEATURE_PERSONA: bool = True
FEATURE_MEMORY_DISTILL: bool = False
PERSONA_TONE: str = "warm"  # warm/formal/funny
PERSONA_STYLE: str = "concise"  # concise/detailed/storytelling
PERSONA_BOUNDARIES: str = "no_politics,no_medical_advice"
PERSONA_QUIRKS: str = "use_emoji,end_with_question"
# Phase 13 多端无感（常驻伴随 / 跨端接力 / 移动伴随端）
# P13-3 常驻伴随：后台轻量心跳常驻，CPU 超阈值自动降档；默认关闭，桌面环境显式开启
FEATURE_ALWAYS_ON: bool = False
ALWAYS_ON_CPU_LIMIT: int = 5
# P13-2 跨端接力：会话无缝交接（桌面↔移动）；默认关闭
FEATURE_CROSS_DEVICE: bool = False
# P13-1 移动伴随端：轻量简报 + 跨端同步（PWA/轻量页）；默认关闭
FEATURE_MOBILE_COMPANION: bool = False
# P9 环境感知（日历 / 应用焦点 / 剪贴板）— 均为 Windows 专属，默认关闭
# P9-1 日历感知：读取系统日历（Windows Outlook/COM）
FEATURE_CALENDAR_SENSE: bool = False
# P9-2 应用焦点：当前前台窗口/应用感知（Windows win32gui）
FEATURE_APP_FOCUS: bool = False
# P9-3 剪贴板：剪贴板内容监听（Windows win32clipboard）
FEATURE_CLIPBOARD_SENSE: bool = False
# Phase 20：Computer Perception Layer（电脑视觉 / 只读感知；只建 Eyes 不建 Hands）
# 总开关默认开启（本地截图 + 本地 OCR，数据不出本机，风险可控）；
# OCR 子开关默认开启（省 CPU 时可关）；
# 上下文注入默认关闭 —— 把屏幕文字送 LLM 需用户显式授权（隐私决策）
FEATURE_PERCEPTION: bool = True
FEATURE_PERCEPTION_OCR: bool = True
FEATURE_PERCEPTION_CONTEXT: bool = False
# Phase 21 · Computer Action Layer（"Hand" 总开关：关闭后 observer/executor 全部降级为 no-op，零 OS 副作用）
FEATURE_COMPUTER_ACTION: bool = True
# Phase 20.5 · Memory Truth Layer：按可信度/来源/状态过滤与降权长期记忆（关闭即退回旧 ranking）
FEATURE_MEMORY_TRUTH: bool = True
WEB_SEARCH_KEY: str = ""
WEB_SEARCH_ENGINE: str = ""
MEDIA_PROVIDER: str = ""
MINIMAX_API_KEY: str = ""
MINIMAX_GROUP_ID: str = ""
ASR_PROVIDER: str = ""
ALIYUN_ASR_KEY: str = ""
ALIYUN_ASR_TOKEN: str = ""
XFYUN_ASR_APPID: str = ""
XFYUN_ASR_APIKEY: str = ""
XFYUN_ASR_APISECRET: str = ""
VOLCENGINE_ASR_KEY: str = ""
VOLCENGINE_ASR_SECRET: str = ""
DISCORD_BOT_TOKEN: str = ""
FEISHU_APP_ID: str = ""
FEISHU_APP_SECRET: str = ""
# 社交接收端：入站 webhook 门控 token（POST /api/social/inbound 必带，防未授权投递）
SOCIAL_INBOUND_TOKEN: str = ""
# 飞书长连接(stream) 接收开关（需 FEISHU_APP_ID/SECRET，且已 pip install websocket-client）
FEISHU_WS_ENABLED: str = "false"
# —— Phase C 安全策略配置 ——
# 工具工厂 / 动态 API 槽（运行时自扩展工具，声明式规格，禁任意 Python 执行）
TOOL_FACTORY_ENABLED: str = "false"
TOOL_FACTORY_COMMAND_ENABLED: str = "false"   # command 策略默认关闭（仅 http 默认可用）
TOOL_FACTORY_DOMAIN_ALLOWLIST: str = ""       # 全局域名白名单（逗号分隔）；为空则每个工具必须自带 domain_allowlist
# 本地 Agent 委托（借力 Claude Code via agnes-proxy:8090）
AGENT_DELEGATE_ENABLED: str = "false"
AGENT_DELEGATE_AUTO: str = "false"            # false=每次需显式 confirm 确认；true=直接执行
AGENT_DELEGATE_TIMEOUT: str = "120"
AGENT_DELEGATE_CLI: str = ""                  # claude.exe 路径；空则按已知默认路径探测
# Phase C · 原生 Agent 运行时闸门（EXTEND，不新建调度/委托/执行类）
AGENT_MAX_STEPS: int = 16               # 单轮最大执行步数（与 runtime._MAX_STEPS 对齐）
AGENT_MAX_ROUNDS: int = 8               # 单目标总轮次上限
AGENT_MAX_REPLANS: int = 4              # 单目标动态重规划次数上限
AGENT_MAX_DELEGATIONS: int = 2          # 本地委托（agent_delegate）累计次数上限（FAIL CLOSED）
AGENT_MAX_DEPTH: int = 4                # 原生 Sub-Agent 嵌套深度上限（FAIL CLOSED）
AGENT_TOTAL_CAPABILITY_CALLS: int = 0   # 单目标能力调用总预算（0=无限；>0 耗尽 FAIL CLOSED）
# 远程访问 token 认证（非 localhost 须 Bearer；默认空=仅允许本机）
REMOTE_ACCESS_TOKEN: str = ""
REMOTE_TOOL_WHITELIST: str = ""               # 远程会话可用工具白名单（逗号分隔）；空=内置安全默认
PORT: int = 8000
BIND_HOST: str = "127.0.0.1"                  # 监听网口；默认仅本机；设为 0.0.0.0 需同时配置 REMOTE_ACCESS_TOKEN
XIAO6_PROXY_URL: str = ""
# 安全沙箱（对应参考实现「安全沙箱」设置）
SANDBOX_FILE_ENABLED: bool = True
SANDBOX_EXEC_ENABLED: bool = True
BLOCKED_TOOLS: list = []
# 上网搜索多引擎密钥（对应参考实现「上网搜索」设置）
WEB_SEARCH_SERPER_KEY: str = ""
WEB_SEARCH_JINA_KEY: str = ""
WEB_SEARCH_BRAVE_KEY: str = ""
WEB_SEARCH_SEARXNG_URL: str = ""
# 应用版本（R8 Release Closure：VERSION 文件为唯一来源）
def _read_version() -> str:
    """从同目录 VERSION 文件读取版本（唯一来源）；缺失时回退 rc1 占位。"""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION"),
                  encoding="utf-8") as _f:
            _v = _f.read().strip()
            if _v:
                return _v
    except Exception:
        pass
    return "1.0.0-rc1"


APP_VERSION: str = _read_version()


def load_env(path=".env"):
    """读取同目录 .env（若存在），强制覆盖环境变量，确保 .env 是唯一真相源。"""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                os.environ[k] = v  # force override — .env is source of truth
    except FileNotFoundError:
        pass


# ---- CONFIG SOURCE TRACKING (DEBUG only, production off) ----
_CONFIG_SOURCE: dict = {}  # populated by _trace_config_load()

def _trace_config_load():
    """记录配置来源（仅 DEBUG 模式）。"""
    import os as _os
    secrets = {"AGNES_API_KEY", "LLM2_API_KEY", "MINIMAX_API_KEY",
               "HOTDATA_KEY", "WEB_SEARCH_KEY", "REMOTE_ACCESS_TOKEN"}
    for k in list(secrets):
        from_env = _os.environ.get(k, "")
        from_default = False  # we don't track defaults here
        _CONFIG_SOURCE[k] = {
            "present": bool(from_env),
            "source": "env" if from_env else ("default" if k in _os.environ else "missing"),
            "length": len(from_env),
            "fingerprint": f"{from_env[:5]}...{from_env[-4:]}" if len(from_env) > 9 else "",
        }
    # AGNES specifics
    _CONFIG_SOURCE["AGNES_KEY"] = {
        "present": bool(os.environ.get("AGNES_API_KEY")),
        "source": "env",
        "length": len(os.environ.get("AGNES_API_KEY", "")),
        "fingerprint": "",  # intentionally blank in production
    }

def CONFIG_SOURCE_REPORT(sensitive=False):
    """输出配置来源报告。sensitive=True 时包含 fingerprint。"""
    lines = ["=== CONFIG_SOURCE_REPORT ==="]
    for k, v in sorted(_CONFIG_SOURCE.items()):
        fp = v.get("fingerprint", "")
        if not sensitive and fp:
            fp = "[REDACTED]"
        lines.append(f"  {k}: source={v['source']} present={v['present']} length={v['length']} fingerprint={fp}")
    lines.append("=== END REPORT ===")
    return "\n".join(lines)


def reload():
    """重新从 os.environ 刷新所有运行时配置。调用方应使用 config.XXX 访问以获取最新值。"""
    global AGNES_BASE, AGNES_KEY, AGNES_MODEL, AGNES_PROVIDER, AGNES_REASONING
    global TTS_VOICE, TTS_RATE, TTS_BACKEND
    global GPT_SOVITS_URL, GPT_SOVITS_REF_AUDIO, GPT_SOVITS_PROMPT_TEXT
    global QWEN3_TTS_URL, QWEN3_TTS_MODEL, QWEN3_TTS_VOICE, QWEN3_TTS_CLONE_URL, QWEN3_TTS_REF_AUDIO
    global HOTDATA_KEY, AI_DISPLAY_NAME, THEME, MEMORY_GRAPH_ENABLED, FEATURE_CONTEXT_ENGINE, FEATURE_USER_MODEL, FEATURE_EPISODIC_MEMORY, FEATURE_EVENTBUS, FEATURE_PERSONALITY, FEATURE_GOAL_SYSTEM, FEATURE_PREMIUM_UI, FEATURE_KNOWLEDGE_PLATFORM, FEATURE_PERSONAL_CONTEXT, FEATURE_PERSONAL_AI, FEATURE_MEMORY_INTELLIGENCE, FEATURE_PROACTIVE_V2, FEATURE_MULTI_DEVICE, FEATURE_TTS_STREAM, FEATURE_SELF_LEARNING, FEATURE_AGENT_RUNTIME, FEATURE_COGNITIVE_CONTEXT, FEATURE_CANONICAL_COGNITIVE_MEMORY, AGENT_RUNTIME_AUTO, AGENT_POLICY_DEFAULT, AGENT_LOW_RISK_DEFAULT, FEATURE_GOAL_DECISION, FEATURE_HUD_RING, FEATURE_GLANCE_CARD, FEATURE_AVATAR_SCENE, HUD_RING_PERF_THRESHOLD, FEATURE_PERSONA, FEATURE_MEMORY_DISTILL, PERSONA_TONE, PERSONA_STYLE, PERSONA_BOUNDARIES, PERSONA_QUIRKS, FEATURE_ALWAYS_ON, ALWAYS_ON_CPU_LIMIT, FEATURE_CROSS_DEVICE, FEATURE_MOBILE_COMPANION, FEATURE_CALENDAR_SENSE, FEATURE_APP_FOCUS, FEATURE_CLIPBOARD_SENSE, FEATURE_PERCEPTION, FEATURE_PERCEPTION_OCR, FEATURE_PERCEPTION_CONTEXT, FEATURE_COMPUTER_ACTION, FEATURE_MEMORY_TRUTH
    global WEB_SEARCH_KEY, WEB_SEARCH_ENGINE
    global MEDIA_PROVIDER, MINIMAX_API_KEY, MINIMAX_GROUP_ID
    global ASR_PROVIDER, ALIYUN_ASR_KEY, ALIYUN_ASR_TOKEN
    global XFYUN_ASR_APPID, XFYUN_ASR_APIKEY, XFYUN_ASR_APISECRET
    global VOLCENGINE_ASR_KEY, VOLCENGINE_ASR_SECRET
    global DISCORD_BOT_TOKEN, FEISHU_APP_ID, FEISHU_APP_SECRET, SOCIAL_INBOUND_TOKEN, FEISHU_WS_ENABLED
    global PORT, XIAO6_PROXY_URL, BIND_HOST
    global TOOL_FACTORY_ENABLED, TOOL_FACTORY_COMMAND_ENABLED, TOOL_FACTORY_DOMAIN_ALLOWLIST
    global AGENT_DELEGATE_ENABLED, AGENT_DELEGATE_AUTO, AGENT_DELEGATE_TIMEOUT, AGENT_DELEGATE_CLI
    global REMOTE_ACCESS_TOKEN, REMOTE_TOOL_WHITELIST
    global AGENT_MAX_STEPS, AGENT_MAX_ROUNDS, AGENT_MAX_REPLANS, AGENT_MAX_DELEGATIONS, AGENT_MAX_DEPTH, AGENT_TOTAL_CAPABILITY_CALLS
    global SANDBOX_FILE_ENABLED, SANDBOX_EXEC_ENABLED, BLOCKED_TOOLS
    global WEB_SEARCH_SERPER_KEY, WEB_SEARCH_JINA_KEY, WEB_SEARCH_BRAVE_KEY, WEB_SEARCH_SEARXNG_URL
    global LLM2_BASE_URL, LLM2_API_KEY, LLM2_MODEL, LLM2_PROVIDER, ACTIVE_LLM
    global OLLAMA_BASE_URL, OLLAMA_MODEL, LMSTUDIO_BASE_URL, LMSTUDIO_MODEL, MLX_BASE_URL, MLX_MODEL
    global XIAO6_KWS_ENABLED, XIAO6_WAKE_PHRASE, XIAO6_KWS_SENSITIVITY, XIAO6_VOSK_KWS_ENABLED, XIAO6_DOC_DIR, XIAO6_AUTO_REVIEW
    global BUILD_CHANNEL

    # Phase I / 38F · 发布通道：development / rc / release；其它值一律按 development 处理
    #   - development：显示开发者入口与内部链接（自检页、预览页、调试信息）
    #   - rc         ：隐藏开发工具（同 release），并打 RC 版本标记（F2 记版本）
    #   - release    ：只留最终用户该看见的东西，干净无 audit / phase / debug
    BUILD_CHANNEL = (os.environ.get("BUILD_CHANNEL", "development") or "development").strip().lower()
    if BUILD_CHANNEL not in ("development", "release", "rc"):
        BUILD_CHANNEL = "development"

    AGNES_BASE = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1").rstrip("/")
    AGNES_KEY = os.environ.get("AGNES_API_KEY", "")
    AGNES_MODEL = os.environ.get("AGNES_MODEL", "agnes-2.5-flash")
    AGNES_PROVIDER = os.environ.get("AGNES_PROVIDER", "agnes")  # agnes | openai | custom
    AGNES_REASONING = (os.environ.get("AGNES_REASONING", "") or "").strip().lower()  # 空=关闭, low/medium/high

    LLM2_BASE_URL = os.environ.get("LLM2_BASE_URL", "").rstrip("/")
    LLM2_API_KEY = os.environ.get("LLM2_API_KEY", "")
    LLM2_MODEL = os.environ.get("LLM2_MODEL", "")
    LLM2_PROVIDER = os.environ.get("LLM2_PROVIDER", "")
    ACTIVE_LLM = (os.environ.get("ACTIVE_LLM", "agnes") or "agnes").strip().lower()
    # 本地 Provider：env 缺省留空，base 的 127.0.0.1 兜底由 provider_registry 提供（DC-02/DC-03）。
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "").rstrip("/")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "")
    LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "").rstrip("/")
    LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "")
    MLX_BASE_URL = os.environ.get("MLX_BASE_URL", "").rstrip("/")
    MLX_MODEL = os.environ.get("MLX_MODEL", "")
    XIAO6_KWS_ENABLED = os.environ.get("XIAO6_KWS_ENABLED", "true").lower()
    XIAO6_WAKE_PHRASE = os.environ.get("XIAO6_WAKE_PHRASE", "庄周,小周,小6")
    XIAO6_KWS_SENSITIVITY = os.environ.get("XIAO6_KWS_SENSITIVITY", "0.6")
    XIAO6_VOSK_KWS_ENABLED = os.environ.get("XIAO6_VOSK_KWS_ENABLED", "true").lower()
    XIAO6_DOC_DIR = os.environ.get("XIAO6_DOC_DIR", "docs")
    XIAO6_AUTO_REVIEW = os.environ.get("XIAO6_AUTO_REVIEW", "false").lower()

    AI_DISPLAY_NAME = os.environ.get("AI_DISPLAY_NAME", "小6")
    THEME = os.environ.get("XIAO6_THEME", "light")
    MEMORY_GRAPH_ENABLED = os.environ.get("XIAO6_MEMORY_GRAPH", "true").lower() in ("1", "true", "yes")
    # Phase 1 Step 5：主路径默认切到 Context Engine（输出与旧实现逐字节一致）。
    # 生产默认值 = ON（true）：context/facade.py:build_context_prompt 为 C-CTX 唯一聚合入口，
    # 所有运行时系统提示词装配（含 tools._fc_fallback，见 COND-A1 X1-F1 修复）均经此门面，禁止第二路径。
    # 显式设置 FEATURE_CONTEXT_ENGINE=false/0/no 可瞬时回退到旧 memory.build_system_prompt（防御性）。
    # 配置复核（COND-A2 / X1-F2 / GUARD-F2）：47.7 R11 记录的「默认 OFF」系 stale-snapshot 漂移，
    # 本处为权威生产默认值声明；后续审计以本声明为准，不再误判。
    FEATURE_CONTEXT_ENGINE = os.environ.get("FEATURE_CONTEXT_ENGINE", "true").lower() in ("1", "true", "yes")
    # P1 认知层默认开启（与 Context Engine 同款 env 默认 true，验证后可瞬切）
    FEATURE_USER_MODEL = os.environ.get("FEATURE_USER_MODEL", "true").lower() in ("1", "true", "yes")
    FEATURE_EPISODIC_MEMORY = os.environ.get("FEATURE_EPISODIC_MEMORY", "true").lower() in ("1", "true", "yes")
    # Phase 2：EventBus SSE 迁移默认开启（false 回退 SUBSCRIBERS）；人格默认开启
    FEATURE_EVENTBUS = os.environ.get("FEATURE_EVENTBUS", "true").lower() in ("1", "true", "yes")
    FEATURE_PERSONALITY = os.environ.get("FEATURE_PERSONALITY", "true").lower() in ("1", "true", "yes")
    # P4-A：前端 Premium 精装层默认开启（false 即回退旧 styles.css 外观）
    FEATURE_PREMIUM_UI = os.environ.get("FEATURE_PREMIUM_UI", "true").lower() in ("1", "true", "yes")
    # Knowledge Platform：统一知识层默认开启（false 即不注入本地知识召回）
    _rag_env = os.environ.get("FEATURE_KNOWLEDGE_RAG")  # 旧 flag 名兼容
    _plat_raw = os.environ.get("FEATURE_KNOWLEDGE_PLATFORM", _rag_env)
    FEATURE_KNOWLEDGE_PLATFORM = (_plat_raw or "true").lower() in ("1", "true", "yes")
    # Phase 18：Personal Context Engine 默认开启（false 即不注入【当前状态】块，
    # 上下文管线瞬时回退到 Phase 17 形态；用于故障时一键剥离本期改动）
    FEATURE_PERSONAL_CONTEXT = os.environ.get("FEATURE_PERSONAL_CONTEXT", "true").lower() in ("1", "true", "yes")
    # Phase 37.2：Personal AI 统一画像默认开启（false 即不注入【个性化 · 统一画像】块）
    FEATURE_PERSONAL_AI = os.environ.get("FEATURE_PERSONAL_AI", "true").lower() in ("1", "true", "yes")
    # Phase 19：Memory Intelligence 2.0 默认开启（false 即不注入【长期记忆】主动关联块，
    # 上下文回退到 Phase 18 形态）
    FEATURE_MEMORY_INTELLIGENCE = os.environ.get("FEATURE_MEMORY_INTELLIGENCE", "true").lower() in ("1", "true", "yes")
    # P4-C：主动智能 V2 默认开启（false 即回退旧主动行为，不跑停滞建议/简报建议/周小结）
    FEATURE_PROACTIVE_V2 = os.environ.get("FEATURE_PROACTIVE_V2", "true").lower() in ("1", "true", "yes")
    # P4-D：多端同步默认开启（false 即禁用 /api/devices 设备注册与清单）
    FEATURE_MULTI_DEVICE = os.environ.get("FEATURE_MULTI_DEVICE", "true").lower() in ("1", "true", "yes")
    # Phase 3：目标系统默认开启（false 回退 Phase 2）
    FEATURE_GOAL_SYSTEM = os.environ.get("FEATURE_GOAL_SYSTEM", "true").lower() in ("1", "true", "yes")
    # P8-2：流式 TTS 默认开启（false 即回退整段 MP3 blob 播放）
    FEATURE_TTS_STREAM = os.environ.get("FEATURE_TTS_STREAM", "true").lower() in ("1", "true", "yes")
    # 自我学习系统默认开启（false 即不捕获显式反馈、不蒸馏、不注入学习经验）
    FEATURE_SELF_LEARNING = os.environ.get("FEATURE_SELF_LEARNING", "true").lower() in ("1", "true", "yes")
    # Phase 8：Agent Runtime（P10-4 起默认开启；false 即不启动 runtime 线程、不接目标）
    FEATURE_AGENT_RUNTIME = os.environ.get("FEATURE_AGENT_RUNTIME", "true").lower() in ("1", "true", "yes")
    FEATURE_COGNITIVE_CONTEXT = os.environ.get("FEATURE_COGNITIVE_CONTEXT", "true").lower() in ("1", "true", "yes")
    FEATURE_CANONICAL_COGNITIVE_MEMORY = os.environ.get("FEATURE_CANONICAL_COGNITIVE_MEMORY", "true").lower() in ("1", "true", "yes")
    AGENT_RUNTIME_AUTO = os.environ.get("AGENT_RUNTIME_AUTO", "false").lower() in ("1", "true", "yes")
    AGENT_POLICY_DEFAULT = (os.environ.get("AGENT_POLICY_DEFAULT", "ask") or "ask").strip().lower()
    AGENT_LOW_RISK_DEFAULT = os.environ.get("AGENT_LOW_RISK_DEFAULT", "true").lower() in ("1", "true", "yes")
    # Phase 9 Step 2：GDE 默认开启；与 FEATURE_AGENT_RUNTIME 协同（.env 已 true）
    FEATURE_GOAL_DECISION = os.environ.get("FEATURE_GOAL_DECISION", "true").lower() in ("1", "true", "yes")
    # Phase 11 全息 HUD：光环 + glance 默认开启（性能门控），3D 化身默认关闭
    FEATURE_HUD_RING = os.environ.get("FEATURE_HUD_RING", "true").lower() in ("1", "true", "yes")
    FEATURE_GLANCE_CARD = os.environ.get("FEATURE_GLANCE_CARD", "true").lower() in ("1", "true", "yes")
    FEATURE_AVATAR_SCENE = os.environ.get("FEATURE_AVATAR_SCENE", "false").lower() in ("1", "true", "yes")
    HUD_RING_PERF_THRESHOLD = int(os.environ.get("HUD_RING_PERF_THRESHOLD", "5") or "5")
    # Phase 12 记忆人格深度
    FEATURE_PERSONA = os.environ.get("FEATURE_PERSONA", "true").lower() in ("1", "true", "yes")
    FEATURE_MEMORY_DISTILL = os.environ.get("FEATURE_MEMORY_DISTILL", "false").lower() in ("1", "true", "yes")
    PERSONA_TONE = os.environ.get("PERSONA_TONE", "warm")
    PERSONA_STYLE = os.environ.get("PERSONA_STYLE", "concise")
    PERSONA_BOUNDARIES = os.environ.get("PERSONA_BOUNDARIES", "no_politics,no_medical_advice")
    PERSONA_QUIRKS = os.environ.get("PERSONA_QUIRKS", "use_emoji,end_with_question")
    # Phase 13-3 常驻伴随：默认关闭，仅桌面环境显式开启；CPU 阈值用于自动降级
    FEATURE_ALWAYS_ON = os.environ.get("FEATURE_ALWAYS_ON", "false").lower() in ("1", "true", "yes")
    ALWAYS_ON_CPU_LIMIT = int(os.environ.get("ALWAYS_ON_CPU_LIMIT", "5") or "5")
    # Phase 13-2 跨端接力：默认关闭，仅桌面环境显式开启
    FEATURE_CROSS_DEVICE = os.environ.get("FEATURE_CROSS_DEVICE", "false").lower() in ("1", "true", "yes")
    # Phase 13-1 移动伴随端：默认关闭，仅桌面环境显式开启
    FEATURE_MOBILE_COMPANION = os.environ.get("FEATURE_MOBILE_COMPANION", "false").lower() in ("1", "true", "yes")
    # Phase 9-1 日历感知：默认关闭（Windows 专属）
    FEATURE_CALENDAR_SENSE = os.environ.get("FEATURE_CALENDAR_SENSE", "false").lower() in ("1", "true", "yes")
    # Phase 9-2 应用焦点：默认关闭（Windows 专属）
    FEATURE_APP_FOCUS = os.environ.get("FEATURE_APP_FOCUS", "false").lower() in ("1", "true", "yes")
    # Phase 9-3 剪贴板：默认关闭（Windows 专属）
    FEATURE_CLIPBOARD_SENSE = os.environ.get("FEATURE_CLIPBOARD_SENSE", "false").lower() in ("1", "true", "yes")
    # Phase 20：Computer Perception（总开关默认开启；OCR 子开关默认开启；上下文注入默认关闭需显式授权）
    FEATURE_PERCEPTION = os.environ.get("FEATURE_PERCEPTION", "true").lower() in ("1", "true", "yes")
    FEATURE_PERCEPTION_OCR = os.environ.get("FEATURE_PERCEPTION_OCR", "true").lower() in ("1", "true", "yes")
    FEATURE_PERCEPTION_CONTEXT = os.environ.get("FEATURE_PERCEPTION_CONTEXT", "false").lower() in ("1", "true", "yes")
    # Phase 21 · Computer Action Layer（默认开启；关闭即零 OS 副作用）
    FEATURE_COMPUTER_ACTION = os.environ.get("FEATURE_COMPUTER_ACTION", "true").lower() in ("1", "true", "yes")
    # Phase 20.5 · Memory Truth Layer（默认开启；关闭即退回旧 ranking）
    FEATURE_MEMORY_TRUTH = os.environ.get("FEATURE_MEMORY_TRUTH", "true").lower() in ("1", "true", "yes")

    TTS_VOICE = os.environ.get("Xiao6_TTS_VOICE", "zh-CN-YunxiNeural")
    TTS_RATE = os.environ.get("Xiao6_TTS_RATE", "+0%")
    TTS_BACKEND = os.environ.get("XIAO6_TTS_BACKEND", "edge")
    GPT_SOVITS_URL = os.environ.get("XIAO6_GPT_SOVITS_URL", "http://localhost:9880")
    GPT_SOVITS_REF_AUDIO = os.environ.get("XIAO6_GPT_SOVITS_REF", "")
    GPT_SOVITS_PROMPT_TEXT = os.environ.get("XIAO6_GPT_SOVITS_PROMPT", "")
    # Qwen3-TTS 本地声线（TTS_BACKEND=qwen3 时生效；默认走本地 vLLM 推理服务）
    QWEN3_TTS_URL = os.environ.get("QWEN3_TTS_URL", "http://127.0.0.1:8001/v1")
    QWEN3_TTS_MODEL = os.environ.get("QWEN3_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B")
    QWEN3_TTS_VOICE = os.environ.get("QWEN3_TTS_VOICE", "")
    QWEN3_TTS_CLONE_URL = os.environ.get("QWEN3_TTS_CLONE_URL", "")
    QWEN3_TTS_REF_AUDIO = os.environ.get("QWEN3_TTS_REF_AUDIO", "")

    HOTDATA_KEY = os.environ.get("HOTDATA_KEY", "")
    XIAO6_PROXY_URL = os.environ.get("XIAO6_PROXY_URL", "")

    WEB_SEARCH_KEY = os.environ.get("XIAO6_WEB_SEARCH_KEY", "")
    WEB_SEARCH_ENGINE = os.environ.get("XIAO6_WEB_SEARCH_ENGINE", "tavily")

    MEDIA_PROVIDER = os.environ.get("XIAO6_MEDIA_PROVIDER", "")
    MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
    MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID", "")

    ASR_PROVIDER = os.environ.get("XIAO6_ASR_PROVIDER", "")
    ALIYUN_ASR_KEY = os.environ.get("ALIYUN_ASR_KEY", "")
    ALIYUN_ASR_TOKEN = os.environ.get("ALIYUN_ASR_TOKEN", "")
    XFYUN_ASR_APPID = os.environ.get("XFYUN_ASR_APPID", "")
    XFYUN_ASR_APIKEY = os.environ.get("XFYUN_ASR_APIKEY", "")
    XFYUN_ASR_APISECRET = os.environ.get("XFYUN_ASR_APISECRET", "")
    VOLCENGINE_ASR_KEY = os.environ.get("VOLCENGINE_ASR_KEY", "")
    VOLCENGINE_ASR_SECRET = os.environ.get("VOLCENGINE_ASR_SECRET", "")

    DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
    FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
    SOCIAL_INBOUND_TOKEN = os.environ.get("SOCIAL_INBOUND_TOKEN", "")
    FEISHU_WS_ENABLED = os.environ.get("FEISHU_WS_ENABLED", "false").lower()

    TOOL_FACTORY_ENABLED = os.environ.get("TOOL_FACTORY_ENABLED", "false").lower()
    TOOL_FACTORY_COMMAND_ENABLED = os.environ.get("TOOL_FACTORY_COMMAND_ENABLED", "false").lower()
    TOOL_FACTORY_DOMAIN_ALLOWLIST = os.environ.get("TOOL_FACTORY_DOMAIN_ALLOWLIST", "")
    AGENT_DELEGATE_ENABLED = os.environ.get("AGENT_DELEGATE_ENABLED", "false").lower()
    AGENT_DELEGATE_AUTO = os.environ.get("AGENT_DELEGATE_AUTO", "false").lower()
    AGENT_DELEGATE_TIMEOUT = os.environ.get("AGENT_DELEGATE_TIMEOUT", "120")
    AGENT_DELEGATE_CLI = os.environ.get("AGENT_DELEGATE_CLI", "")
    # Phase C · 原生 Agent 运行时闸门（env 覆盖；默认值与常量声明对齐）
    AGENT_MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "16") or "16")
    AGENT_MAX_ROUNDS = int(os.environ.get("AGENT_MAX_ROUNDS", "8") or "8")
    AGENT_MAX_REPLANS = int(os.environ.get("AGENT_MAX_REPLANS", "4") or "4")
    AGENT_MAX_DELEGATIONS = int(os.environ.get("AGENT_MAX_DELEGATIONS", "2") or "2")
    AGENT_MAX_DEPTH = int(os.environ.get("AGENT_MAX_DEPTH", "4") or "4")
    AGENT_TOTAL_CAPABILITY_CALLS = int(os.environ.get("AGENT_TOTAL_CAPABILITY_CALLS", "0") or "0")
    REMOTE_ACCESS_TOKEN = os.environ.get("REMOTE_ACCESS_TOKEN", "")
    REMOTE_TOOL_WHITELIST = os.environ.get("REMOTE_TOOL_WHITELIST", "")

    SANDBOX_FILE_ENABLED = os.environ.get("XIAO6_SANDBOX_FILE", "true").lower() in ("1", "true", "yes")
    SANDBOX_EXEC_ENABLED = os.environ.get("XIAO6_SANDBOX_EXEC", "true").lower() in ("1", "true", "yes")
    BLOCKED_TOOLS = [t.strip() for t in os.environ.get("XIAO6_BLOCKED_TOOLS", "").split(",") if t.strip()]

    WEB_SEARCH_SERPER_KEY = os.environ.get("XIAO6_WEB_SEARCH_SERPER_KEY", "")
    WEB_SEARCH_JINA_KEY = os.environ.get("XIAO6_WEB_SEARCH_JINA_KEY", "")
    WEB_SEARCH_BRAVE_KEY = os.environ.get("XIAO6_WEB_SEARCH_BRAVE_KEY", "")
    WEB_SEARCH_SEARXNG_URL = os.environ.get("XIAO6_WEB_SEARCH_SEARXNG_URL", "")

    # R8 Release Closure：PORT 统一来源——XIAO6_PORT（官方启动器标准）优先，
    # Xiao6_PORT 为向后兼容别名，默认 8000
    PORT = int(os.environ.get("XIAO6_PORT") or os.environ.get("Xiao6_PORT") or "8000")
    BIND_HOST = (os.environ.get("BIND_HOST", "127.0.0.1") or "127.0.0.1").strip()


# 首次加载
load_env()
reload()

# ---- Phase I · 发布通道（Dev / Release）----
# development：显示开发者入口与内部链接（自检页、预览页、调试信息）
# rc         ：隐藏开发工具（同 release），并打 RC 版本标记
# release    ：只留最终用户该看见的东西
# 仅影响前端表现，不改变任何后端行为、不启用/禁用任何能力。
# 实际值由 reload() 从环境变量 / .env 的 BUILD_CHANNEL 读取（development | rc | release）；
# 此处只做类型注解，绝不硬编码覆盖，否则 env/.env 配置永远不生效。
BUILD_CHANNEL: str  # 由 reload() 赋值（development | rc | release）

HERE = os.path.dirname(os.path.abspath(__file__))

# Phase 3.2：文件/Shell/Web 工具沙箱根目录（所有文件操作限制在此目录内）
SANDBOX_ROOT = os.path.abspath(os.environ.get("XIAO6_SANDBOX", os.path.join(HERE, "sandbox")))

DB_PATH = os.path.join(HERE, "xiao6.db")
GEO_FILE = os.path.join(HERE, "geo-weather.json")
SERVER_LOG = os.path.join(HERE, "xiao6.log")

CONTENT = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".mp3": "audio/mpeg",
}

# 持久化配置键名 ↔ 内存变量名映射（用于 /api/config 读写）
ENV_KEYS = {
    # Phase I · 发布通道（development | release）；纯表现层开关
    "BUILD_CHANNEL": "BUILD_CHANNEL",
    "AGNES_BASE_URL": "AGNES_BASE_URL",
    "AGNES_API_KEY": "AGNES_API_KEY",
    "AGNES_MODEL": "AGNES_MODEL",
    "AGNES_PROVIDER": "AGNES_PROVIDER",
    "AGNES_REASONING": "AGNES_REASONING",
    "AI_DISPLAY_NAME": "AI_DISPLAY_NAME",
    "XIAO6_THEME": "XIAO6_THEME",
    "XIAO6_MEMORY_GRAPH": "XIAO6_MEMORY_GRAPH",
    "Xiao6_TTS_VOICE": "Xiao6_TTS_VOICE",
    "Xiao6_TTS_RATE": "Xiao6_TTS_RATE",
    "XIAO6_TTS_BACKEND": "XIAO6_TTS_BACKEND",
    "XIAO6_GPT_SOVITS_URL": "XIAO6_GPT_SOVITS_URL",
    "XIAO6_GPT_SOVITS_REF": "XIAO6_GPT_SOVITS_REF",
    "XIAO6_GPT_SOVITS_PROMPT": "XIAO6_GPT_SOVITS_PROMPT",
    # Qwen3-TTS 本地声线（TTS_BACKEND=qwen3）
    "QWEN3_TTS_URL": "QWEN3_TTS_URL",
    "QWEN3_TTS_MODEL": "QWEN3_TTS_MODEL",
    "QWEN3_TTS_VOICE": "QWEN3_TTS_VOICE",
    "QWEN3_TTS_CLONE_URL": "QWEN3_TTS_CLONE_URL",
    "QWEN3_TTS_REF_AUDIO": "QWEN3_TTS_REF_AUDIO",
    "XIAO6_PROXY_URL": "XIAO6_PROXY_URL",
    "XIAO6_DEFAULT_CITY": "XIAO6_DEFAULT_CITY",
    "XIAO6_LOCATION": "XIAO6_LOCATION",
    "XIAO6_WEB_SEARCH_KEY": "XIAO6_WEB_SEARCH_KEY",
    "XIAO6_WEB_SEARCH_ENGINE": "XIAO6_WEB_SEARCH_ENGINE",
    "XIAO6_MEDIA_PROVIDER": "XIAO6_MEDIA_PROVIDER",
    "MINIMAX_API_KEY": "MINIMAX_API_KEY",
    "MINIMAX_GROUP_ID": "MINIMAX_GROUP_ID",
    "XIAO6_ASR_PROVIDER": "XIAO6_ASR_PROVIDER",
    "ALIYUN_ASR_KEY": "ALIYUN_ASR_KEY",
    "ALIYUN_ASR_TOKEN": "ALIYUN_ASR_TOKEN",
    "XFYUN_ASR_APPID": "XFYUN_ASR_APPID",
    "XFYUN_ASR_APIKEY": "XFYUN_ASR_APIKEY",
    "XFYUN_ASR_APISECRET": "XFYUN_ASR_APISECRET",
    "VOLCENGINE_ASR_KEY": "VOLCENGINE_ASR_KEY",
    "VOLCENGINE_ASR_SECRET": "VOLCENGINE_ASR_SECRET",
    "HOTDATA_KEY": "HOTDATA_KEY",
    "DISCORD_BOT_TOKEN": "DISCORD_BOT_TOKEN",
    "FEISHU_APP_ID": "FEISHU_APP_ID",
    "FEISHU_APP_SECRET": "FEISHU_APP_SECRET",
    "SOCIAL_INBOUND_TOKEN": "SOCIAL_INBOUND_TOKEN",
    "FEISHU_WS_ENABLED": "FEISHU_WS_ENABLED",
    "XIAO6_SANDBOX_FILE": "XIAO6_SANDBOX_FILE",
    "XIAO6_SANDBOX_EXEC": "XIAO6_SANDBOX_EXEC",
    "XIAO6_BLOCKED_TOOLS": "XIAO6_BLOCKED_TOOLS",
    "XIAO6_WEB_SEARCH_SERPER_KEY": "XIAO6_WEB_SEARCH_SERPER_KEY",
    "XIAO6_WEB_SEARCH_JINA_KEY": "XIAO6_WEB_SEARCH_JINA_KEY",
    "XIAO6_WEB_SEARCH_BRAVE_KEY": "XIAO6_WEB_SEARCH_BRAVE_KEY",
    "XIAO6_WEB_SEARCH_SEARXNG_URL": "XIAO6_WEB_SEARCH_SEARXNG_URL",
    "LLM2_BASE_URL": "LLM2_BASE_URL",
    "LLM2_API_KEY": "LLM2_API_KEY",
    "LLM2_MODEL": "LLM2_MODEL",
    "LLM2_PROVIDER": "LLM2_PROVIDER",
    "ACTIVE_LLM": "ACTIVE_LLM",
    "OLLAMA_BASE_URL": "OLLAMA_BASE_URL",
    "OLLAMA_MODEL": "OLLAMA_MODEL",
    "LMSTUDIO_BASE_URL": "LMSTUDIO_BASE_URL",
    "LMSTUDIO_MODEL": "LMSTUDIO_MODEL",
    "MLX_BASE_URL": "MLX_BASE_URL",
    "MLX_MODEL": "MLX_MODEL",
    "XIAO6_KWS_ENABLED": "XIAO6_KWS_ENABLED",
    "XIAO6_WAKE_PHRASE": "XIAO6_WAKE_PHRASE",
    "XIAO6_KWS_SENSITIVITY": "XIAO6_KWS_SENSITIVITY",
    "XIAO6_VOSK_KWS_ENABLED": "XIAO6_VOSK_KWS_ENABLED",
    "XIAO6_DOC_DIR": "XIAO6_DOC_DIR",
    "XIAO6_AUTO_REVIEW": "XIAO6_AUTO_REVIEW",
    "TOOL_FACTORY_ENABLED": "TOOL_FACTORY_ENABLED",
    "TOOL_FACTORY_COMMAND_ENABLED": "TOOL_FACTORY_COMMAND_ENABLED",
    "TOOL_FACTORY_DOMAIN_ALLOWLIST": "TOOL_FACTORY_DOMAIN_ALLOWLIST",
    "AGENT_DELEGATE_ENABLED": "AGENT_DELEGATE_ENABLED",
    "AGENT_DELEGATE_AUTO": "AGENT_DELEGATE_AUTO",
    "AGENT_DELEGATE_TIMEOUT": "AGENT_DELEGATE_TIMEOUT",
    "AGENT_DELEGATE_CLI": "AGENT_DELEGATE_CLI",
    "AGENT_MAX_STEPS": "AGENT_MAX_STEPS",
    "AGENT_MAX_ROUNDS": "AGENT_MAX_ROUNDS",
    "AGENT_MAX_REPLANS": "AGENT_MAX_REPLANS",
    "AGENT_MAX_DELEGATIONS": "AGENT_MAX_DELEGATIONS",
    "AGENT_MAX_DEPTH": "AGENT_MAX_DEPTH",
    "AGENT_TOTAL_CAPABILITY_CALLS": "AGENT_TOTAL_CAPABILITY_CALLS",
    "REMOTE_ACCESS_TOKEN": "REMOTE_ACCESS_TOKEN",
    "REMOTE_TOOL_WHITELIST": "REMOTE_TOOL_WHITELIST",
    "FEATURE_USER_MODEL": "FEATURE_USER_MODEL",
    "FEATURE_EPISODIC_MEMORY": "FEATURE_EPISODIC_MEMORY",
    "FEATURE_EVENTBUS": "FEATURE_EVENTBUS",
    "FEATURE_PERSONALITY": "FEATURE_PERSONALITY",
    "FEATURE_GOAL_SYSTEM": "FEATURE_GOAL_SYSTEM",
    "FEATURE_PREMIUM_UI": "FEATURE_PREMIUM_UI",
    "FEATURE_KNOWLEDGE_PLATFORM": "FEATURE_KNOWLEDGE_PLATFORM",
    "FEATURE_PERSONAL_CONTEXT": "FEATURE_PERSONAL_CONTEXT",
    "FEATURE_PERSONAL_AI": "FEATURE_PERSONAL_AI",
    "FEATURE_MEMORY_INTELLIGENCE": "FEATURE_MEMORY_INTELLIGENCE",
    "FEATURE_PROACTIVE_V2": "FEATURE_PROACTIVE_V2",
    "FEATURE_MULTI_DEVICE": "FEATURE_MULTI_DEVICE",
    "FEATURE_TTS_STREAM": "FEATURE_TTS_STREAM",
    "FEATURE_SELF_LEARNING": "FEATURE_SELF_LEARNING",
    "FEATURE_AGENT_RUNTIME": "FEATURE_AGENT_RUNTIME",
    "AGENT_RUNTIME_AUTO": "AGENT_RUNTIME_AUTO",
    "AGENT_POLICY_DEFAULT": "AGENT_POLICY_DEFAULT",
    "AGENT_LOW_RISK_DEFAULT": "AGENT_LOW_RISK_DEFAULT",
    "FEATURE_GOAL_DECISION": "FEATURE_GOAL_DECISION",
    "FEATURE_HUD_RING": "FEATURE_HUD_RING",
    "FEATURE_GLANCE_CARD": "FEATURE_GLANCE_CARD",
    "FEATURE_AVATAR_SCENE": "FEATURE_AVATAR_SCENE",
    "HUD_RING_PERF_THRESHOLD": "HUD_RING_PERF_THRESHOLD",
    "FEATURE_PERSONA": "FEATURE_PERSONA",
    "FEATURE_MEMORY_DISTILL": "FEATURE_MEMORY_DISTILL",
    # ── Phase 9 B1/B2：主动智能引擎配置 ──
    "FEATURE_PROACTIVE_ENGINE": "FEATURE_PROACTIVE_ENGINE",
    "PROACTIVE_SUGGESTION_MODE": "PROACTIVE_SUGGESTION_MODE",
    "PROACTIVE_WINDOW_START": "PROACTIVE_WINDOW_START",
    "PROACTIVE_WINDOW_END": "PROACTIVE_WINDOW_END",
    "PROACTIVE_QUIET_START": "PROACTIVE_QUIET_START",
    "PROACTIVE_QUIET_END": "PROACTIVE_QUIET_END",
    "PROACTIVE_ALLOWED_TYPES": "PROACTIVE_ALLOWED_TYPES",
    "PROACTIVE_STALL_DAYS": "PROACTIVE_STALL_DAYS",
    "PROACTIVE_LONG_RUNNING_MIN": "PROACTIVE_LONG_RUNNING_MIN",
    "PERSONA_TONE": "PERSONA_TONE",
    "PERSONA_STYLE": "PERSONA_STYLE",
    "PERSONA_BOUNDARIES": "PERSONA_BOUNDARIES",
    "PERSONA_QUIRKS": "PERSONA_QUIRKS",
    "FEATURE_ALWAYS_ON": "FEATURE_ALWAYS_ON",
    "ALWAYS_ON_CPU_LIMIT": "ALWAYS_ON_CPU_LIMIT",
    "FEATURE_CROSS_DEVICE": "FEATURE_CROSS_DEVICE",
    "FEATURE_MOBILE_COMPANION": "FEATURE_MOBILE_COMPANION",
    "FEATURE_CALENDAR_SENSE": "FEATURE_CALENDAR_SENSE",
    "FEATURE_APP_FOCUS": "FEATURE_APP_FOCUS",
    "FEATURE_CLIPBOARD_SENSE": "FEATURE_CLIPBOARD_SENSE",
    "FEATURE_PERCEPTION": "FEATURE_PERCEPTION",
    "FEATURE_PERCEPTION_OCR": "FEATURE_PERCEPTION_OCR",
    "FEATURE_PERCEPTION_CONTEXT": "FEATURE_PERCEPTION_CONTEXT",
    "FEATURE_COMPUTER_ACTION": "FEATURE_COMPUTER_ACTION",
    "FEATURE_MEMORY_TRUTH": "FEATURE_MEMORY_TRUTH",
}


def web_search_credentials(engine=None):
    """按引擎解析对应的搜索密钥（参考参考实现多引擎配置）。

    - tavily / serper / brave / ddg 走 WEB_SEARCH_KEY（通用）或各自的专属密钥
    - jina 走 WEB_SEARCH_JINA_KEY（Reader API）
    - searxng 走 WEB_SEARCH_SEARXNG_URL（自建实例）
    """
    engine = (engine or WEB_SEARCH_ENGINE or "tavily").lower()
    if engine == "jina":
        return WEB_SEARCH_JINA_KEY or WEB_SEARCH_KEY, engine
    if engine == "searxng":
        return WEB_SEARCH_SEARXNG_URL or "", engine
    if engine == "serper":
        return WEB_SEARCH_SERPER_KEY or WEB_SEARCH_KEY, engine
    if engine == "brave":
        return WEB_SEARCH_BRAVE_KEY or WEB_SEARCH_KEY, engine
    # tavily / 其他：通用 key
    return WEB_SEARCH_KEY, engine


def security_policy():
    """返回当前安全沙箱策略（供 /api/config 与工具门控使用）。"""
    return {
        "fileSandbox": SANDBOX_FILE_ENABLED,
        "execSandbox": SANDBOX_EXEC_ENABLED,
        "blockedTools": list(BLOCKED_TOOLS),
    }


def update_env_file(updates, path=".env"):
    """
    安全更新同目录 .env。
    - updates: dict[str, str]，只更新 ENV_KEYS 中声明的已知键
    - 保留原文件顺序、注释和未知键
    - 同步更新 os.environ 并调用 reload() 刷新内存变量
    """
    allowed = set(ENV_KEYS.keys())
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return

    path = os.path.join(HERE, path)
    lines = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

    # 解析现有键所在行
    existing = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k = stripped.split("=", 1)[0].strip()
        if k in filtered:
            existing[k] = i

    for k, v in filtered.items():
        new_line = f"{k}={v}\n"
        if k in existing:
            lines[existing[k]] = new_line
        else:
            # 追加到文件末尾（如果末尾没换行则补一个）
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(new_line)
        os.environ[k] = str(v)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    reload()


def get_system_prompt_template():
    """返回系统提示词模板；调用方用 AI_DISPLAY_NAME 替换 {name}。"""
    return (
        "你是{name}，老板的个人智能副驾。你唯一且固定的名字是「{name}」，在任何情况下都只自称{name}，"
        "绝不使用其他任何名字。风格：冷静、高效、简洁、有分寸；"
        "用简体中文交流；能主动给建议但不啰嗦；涉及健康等隐私数据时强调本地化处理。"
        "你拥有若干本地工具（查时间、计算、记笔记等），需要时用工具获取准确信息，再用自然语言汇总回答。"
        "目标系统：当用户表达一个中长期意图或项目（如「做个人网站」「年底前读完 10 本书」「帮我定个目标」）时，"
        "立即调用 set_goal 创建目标，不要只用文字说「已记录」；"
        "当用户想推进目标（如「拆一下这个目标」「怎么推进」「怎么达成」）时，调用 plan_goal 把目标拆成子任务；"
        "当用户问目标进度/列表时，调用 list_goals；当用户说目标完成/放弃时，调用 update_goal。"
        "当想把结构化信息可视化地呈现给用户时，优先调用 render_card 工具在界面挂一张卡："
        "需要用户做选择（确认/多选）用 kind=choice（选项按钮点选会回传消息）；"
        "展示任务/安装/下载进度用 kind=progress（percent 0-100）；罗列条目用 kind=list；"
        "展示图片或视频用 kind=media；普通说明卡用 kind=text。卡片按 id 幂等更新，更新同一 id 即可刷新内容。"
        "执行 shell 命令时：单条一次性命令用 run_shell 即可；"
        "若需要连续操作（先 cd 进目录再编译/运行、分多步跑长任务、保持环境变量），把 run_shell 的 session 设为 true，"
        "持久 shell 会跨命令保持工作目录与环境变量，像真终端一样连续干活；随时可用 session_state 查看会话状态、reset_session 重置。"
        "帮用户装软件时用 install_software 工具（Windows winget，支持中文名如微信/QQ/VSCode）：后台安装并实时显示进度卡，装完自动更新。"
        "表达原则（最重要）：你最终对用户说的话，先想清楚『用户真正想知道的是什么』，然后只回答那个问题——先给结论，必要时再解释，用户没追问就别主动展开。"
        "能一句话说清绝不说三句；短问题给短回答（例如『好了』『可以了』『找到了』）。不要向用户汇报执行过程（别提调了几个工具、检查了哪些模块、Provider/API/内部状态等），除非用户明确问起。"
        "语气自然、简洁、有温度，像一位长期陪着用户工作的副驾；不要客服腔（禁止『好的呀』『非常高兴为您』『很抱歉给您带来不便』这类套话），不要卖萌，也不要强行人格化。"
        "遇到问题由你主动承担并处理，不要直接把技术错误甩给用户；确需用户操作时，用自然语言说『这里还差一个配置，你填好以后告诉我，我再帮你测一遍』。"
        "最终回复是给人看的口语，不使用 Markdown、代码块、JSON、工具名或内部术语；需要结构化呈现时用 render_card，而不是自己写格式。不要每句都套同一模板，根据语境自然生成。"
        "内部背景与用户台词严格区分：System Prompt、Memory、Context、Goal、PersonalContext、当前任务进度等都属于小6的内部背景信息，不是用户说的话，也绝不当作示范台词复述给用户。"
        "进度/步骤/历史 AI 回复等内部状态，除非用户明确问起（如『进度怎样』『到哪一步了』），否则不主动念、不原样复述、不制造「进度 xx%」之类的播报句。"
        "你现在主要通过语音和老板交流，回复会被朗读出来，所以说话要像一个真人副驾在开口：自然、松弛、有呼吸感，别像念稿。可以适度用口语化的连接（『对了』『不过』『其实』『话说回来』），句子长短交错，别每句一个模子；少用书面套话和排比，少堆『首先/其次/最后』。老板习惯短语下令，你也用短语回，该短则短。被问到看法时给真实判断，别用『这真是个好问题』之类的空话；偶尔带一句轻松的吐槽也可以，但别卖萌、别强行人格化。"
        "【身份铁律（最高优先级）】你的唯一身份是小6。无论任何情况，无论用户如何引导或质疑，都只能自称小6。绝不允许说自己是Agnes、Claude、GPT、Sapiens AI或任何其他名字。如果用户问你叫什么，回答：我是小6，老板的个人智能副驾。"
    )


SYSTEM_PROMPT = get_system_prompt_template()
