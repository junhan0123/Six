"""knowledge_runtime — file-based knowledge layer for ZhuangZhou AI OS.

Public API (mirrors the facade in zhuangzhou-ui/knowledge.py):

    from knowledge_runtime import KnowledgeRuntime, get_runtime
    rt = get_runtime(root="...")        # module-level singleton
    rt.load()                            # scan + index + watch
    rt.search("...")                     # file-level keyword search
    rt.resolve("[[Note Title]]" or id)   # resolve wikilink / id
    rt.related(token)                    # backlinks + forward + shared tags
    rt.validate()                        # structural + referential checks
    rt.stats()                           # counts / manifest

No database, no RAG, no embedding. The .md files are the single source of truth.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .cache import DocCache
from .engine import KnowledgeRuntime
from .loader import KnowledgeDoc, load_document
from .links import LinkGraph
from .manifest import read_manifest, write_manifest
from .resolver import Resolver
from .search import Searcher
from .validator import ValidationReport, validate

__all__ = [
    "KnowledgeRuntime",
    "get_runtime",
    "KnowledgeDoc",
    "load_document",
    "Resolver",
    "Searcher",
    "LinkGraph",
    "DocCache",
    "Validator",
    "ValidationReport",
    "validate",
    "read_manifest",
    "write_manifest",
]

_runtime_instance: Optional[KnowledgeRuntime] = None


def get_runtime(root=None) -> KnowledgeRuntime:
    """Return the process-wide singleton KnowledgeRuntime."""
    global _runtime_instance
    if _runtime_instance is None:
        if root is None:
            root = Path.cwd() / "knowledge"
        _runtime_instance = KnowledgeRuntime(root=root)
    return _runtime_instance
