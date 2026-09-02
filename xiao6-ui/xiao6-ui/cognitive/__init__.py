#!/usr/bin/env python3
"""Xiao6 · 认知层包（cognitive）

提供用户模型 + 情节记忆的读写/召回逻辑，以及后台自动抽取入口。
本包仅依赖 db / llm / embed / config / memory，不依赖 context（保持单向依赖）。
Source 适配器（产出 ContextItem）放在 context/cognitive_sources.py，由 context 单向 import 本包。
"""

from cognitive.episodic import add_episode, list_episodes, recall_episodes, render_episodes_block
from cognitive.extractor import maybe_extract
from cognitive.user_model import (
    is_empty,
    load_user_model,
    render_user_model_block,
    upsert_user_model,
)

__all__ = [
    "load_user_model",
    "upsert_user_model",
    "render_user_model_block",
    "is_empty",
    "add_episode",
    "recall_episodes",
    "render_episodes_block",
    "list_episodes",
    "maybe_extract",
]
