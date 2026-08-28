#!/usr/bin/env python3
"""ZhuangZhou · Knowledge Platform — file-based knowledge runtime (facade).

This module is the single public entry point for the knowledge layer. It
replaces the legacy RAG/embedding backend (``knowledge.py`` RAG) with a
file-based runtime (``knowledge_runtime`` package).

Red lines honoured:
- NO database, NO RAG, NO embedding, NO vector store.
- All knowledge lives in ``knowledge/*.md`` (Local First, git-tracked).
- Reads/writes go ONLY through this runtime.

Backwards-compatible surface for existing callers (server.py / tools.py /
context/knowledge_source.py): ``load, reload, search, resolve, related,
validate, stats, list_docs, ingest_document, archive_conversation, delete_doc,
delete_by_source``.

There is no ``semantic_query`` — semantic/vector recall was removed together
with the legacy RAG backend; all recall is keyword/structured only.
"""
from __future__ import annotations

from pathlib import Path

from knowledge_runtime import KnowledgeRuntime, get_runtime

# Vault root: sibling of zhuangzhou-ui/ -> G:/ZhuangZhou/knowledge
_ROOT = Path(__file__).resolve().parent.parent / "knowledge"
_runtime = get_runtime(root=_ROOT)


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------
def load():
    return _runtime.load()


def reload():
    return _runtime.reload()


def search(*args, **kwargs):
    return _runtime.search(*args, **kwargs)


def resolve(*args, **kwargs):
    return _runtime.resolve(*args, **kwargs)


def related(*args, **kwargs):
    return _runtime.related(*args, **kwargs)


def validate(*args, **kwargs):
    return _runtime.validate(*args, **kwargs)


def stats(*args, **kwargs):
    return _runtime.stats(*args, **kwargs)


def list_docs(*args, **kwargs):
    return _runtime.list_docs(*args, **kwargs)


# ---------------------------------------------------------------------------
# Legacy / write API (server.py + tools.py)
# ---------------------------------------------------------------------------
def ingest_document(*args, **kwargs):
    return _runtime.ingest_document(*args, **kwargs)


def archive_conversation(*args, **kwargs):
    return _runtime.archive_conversation(*args, **kwargs)


def delete_doc(*args, **kwargs):
    return _runtime.delete_doc(*args, **kwargs)


def delete_by_source(*args, **kwargs):
    return _runtime.delete_by_source(*args, **kwargs)


# Expose the runtime for advanced callers / tests.
runtime = _runtime
