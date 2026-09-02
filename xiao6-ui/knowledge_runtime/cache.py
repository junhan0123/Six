"""knowledge_runtime.cache — 文档缓存（DocCache）。

职责：缓存已解析的 :class:`~knowledge_runtime.loader.KnowledgeDoc`，按
``path + mtime`` 判定新鲜度，避免每次索引/搜索都重读并重新解析全部 .md 文件。

不做任何数据库 / RAG / 嵌入；.md 文件始终是单一事实源。
"""
from __future__ import annotations

import os
import threading


class DocCache:
    """按 mtime 失效的文档缓存。"""

    def __init__(self) -> None:
        self._docs: dict = {}
        self._mtimes: dict = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get(self, path: str):
        """返回缓存文档；若文件已变更或不存在则返回 None。"""
        with self._lock:
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                self.invalidate(path)
                return None
            if self._mtimes.get(path) == mtime and path in self._docs:
                return self._docs[path]
            return None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def put(self, path: str, doc) -> None:
        with self._lock:
            self._docs[path] = doc
            self._mtimes[path] = getattr(doc, "mtime", None) or _safe_mtime(path)

    def invalidate(self, path: str) -> None:
        with self._lock:
            self._docs.pop(path, None)
            self._mtimes.pop(path, None)

    def clear(self) -> None:
        with self._lock:
            self._docs.clear()
            self._mtimes.clear()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        with self._lock:
            return len(self._docs)

    def __contains__(self, path: str) -> bool:
        with self._lock:
            return path in self._docs

    def paths(self):
        with self._lock:
            return list(self._docs.keys())

    def values(self):
        with self._lock:
            return list(self._docs.values())

    def items(self):
        with self._lock:
            return list(self._docs.items())


def _safe_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0
