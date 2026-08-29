"""庄周 · 身份与自我模型层（Identity & Self Model Layer）—— Phase 26

包门面：对外暴露 IdentityProvider / get_provider。

身份是「庄周是谁」的唯一权威来源（Single Source of Truth），仅被 Context Engine
（IdentitySource）与 persona_engine 单向读取，不反向依赖其它模块。
每条事实带 source / confidence / updated / status，可验证、可追溯来源、可评可信度；
只有可信度 >= MIN_INJECT_CREDIBILITY 的事实才允许进入系统提示，低可信信息被拦截。
"""

from .provider import (
    CRED_SOURCE_LEVELS,
    IdentityError,
    IdentityProvider,
    MIN_INJECT_CREDIBILITY,
    get_provider,
    load_identity,
    validate_identity,
)

__all__ = [
    "IdentityProvider",
    "IdentityError",
    "get_provider",
    "validate_identity",
    "load_identity",
    "MIN_INJECT_CREDIBILITY",
    "CRED_SOURCE_LEVELS",
]
