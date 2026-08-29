"""knowledge_runtime.engine — KnowledgeRuntime（文件知识层的运行时引擎）。

基于 :mod:`knowledge_runtime.loader` 解析的 .md 文档提供：扫描索引、关键词搜索、
wikilink 解析、关联查找、结构校验、统计、以及写入/归档/删除。

红线（与 knowledge.py facade 一致）：
- NO database / NO RAG / NO embedding / NO vector store。
- ``knowledge/*.md`` 是唯一事实源；本模块只做内存索引与缓存。
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .cache import DocCache
from .loader import DOMAIN_BY_TYPE, TYPE_BY_DOMAIN, KnowledgeDoc, load_document, slugify

# 扫描时忽略的目录（Obsidian 配置 / 版本控制 / 缓存）
_SKIP_DIRS = {".obsidian", ".git", ".trash", "node_modules", "__pycache__"}


class KnowledgeRuntime:
    """File-based knowledge runtime（进程内单例，见 knowledge_runtime.get_runtime）。"""

    def __init__(self, root=None) -> None:
        self.root = Path(root) if root is not None else Path.cwd() / "knowledge"
        self._cache = DocCache()
        self._docs = []          # list[KnowledgeDoc]，按 path 排序
        self._by_path = {}       # path -> KnowledgeDoc
        self._titles = {}        # 归一化标题 -> KnowledgeDoc
        self._stats = {}
        self._validation = {"ok": True, "errors": [], "warnings": []}
        self._loaded = False

    # ------------------------------------------------------------------
    # 扫描 / 索引
    # ------------------------------------------------------------------
    def _iter_md_files(self):
        if not self.root.is_dir():
            return []
        out = []
        for p in sorted(self.root.rglob("*.md")):
            rel = p.relative_to(self.root)
            if any(part in _SKIP_DIRS or part.startswith(".") for part in rel.parts):
                continue
            out.append(p)
        return out

    def _load_doc(self, path: Path):
        key = str(path)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            doc = load_document(key)
        except Exception as e:  # 单个坏文件不应毁掉整轮索引
            doc = KnowledgeDoc(path=key, title=path.stem, parse_error=str(e))
        self._cache.put(key, doc)
        return doc

    @staticmethod
    def _domain_of(path: Path, root: Path) -> str:
        try:
            rel = path.relative_to(root)
        except ValueError:
            return ""
        return rel.parts[0] if len(rel.parts) > 1 else ""

    @staticmethod
    def _norm(s: str) -> str:
        return re.sub(r"\s+", "", (s or "").strip().lower())

    def _build_index(self):
        docs = []
        for p in self._iter_md_files():
            doc = self._load_doc(p)
            doc.domain = self._domain_of(p, self.root) or (DOMAIN_BY_TYPE.get(doc.type or "", "") or "")
            if not doc.type:
                doc.type = TYPE_BY_DOMAIN.get(doc.domain)
            docs.append(doc)

        self._docs = docs
        self._by_path = {d.path: d for d in docs}

        # 标题索引（含别名）
        self._titles = {}
        for d in docs:
            for name in [d.title, d.id, *(d.aliases or [])]:
                k = self._norm(name)
                if k:
                    self._titles.setdefault(k, d)

        # 关系（wikilink 解析）+ 校验
        relations = 0
        bad_links = []
        errors = []
        warnings = []
        for d in docs:
            if d.parse_error:
                errors.append("%s: %s" % (_rel(d.path, self.root), d.parse_error))
            for target, _alias in d.wikilinks or []:
                hit = self._titles.get(self._norm(target))
                if hit is not None and hit.path != d.path:
                    relations += 1
                else:
                    bad_links.append({"from": _rel(d.path, self.root), "to": target})
                    warnings.append("%s: 断链 [[%s]]" % (_rel(d.path, self.root), target))
            if d.type and d.type not in DOMAIN_BY_TYPE:
                warnings.append("%s: 未知 type=%s" % (_rel(d.path, self.root), d.type))

        by_domain = {}
        by_type = {}
        for d in docs:
            by_domain[d.domain or "(none)"] = by_domain.get(d.domain or "(none)", 0) + 1
            by_type[d.type or "(none)"] = by_type.get(d.type or "(none)", 0) + 1

        self._validation = {"ok": not errors, "errors": errors, "warnings": warnings}
        self._stats = {
            "manifest_version": 1,
            "root": str(self.root),
            "nodes": len(docs),
            "relations": relations,
            "by_domain": dict(sorted(by_domain.items())),
            "by_type": dict(sorted(by_type.items())),
            "bad_links": len(bad_links),
            "broken_links": bad_links,
            "validation_ok": not errors,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "indexed_at": date.today().isoformat(),
            "docs": len(docs),
        }
        self._loaded = True
        return self._stats

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def load(self) -> dict:
        """扫描 + 建索引 + 校验（不启动 watcher）。返回 stats。"""
        return self._build_index()

    def reload(self) -> dict:
        """清缓存后重建索引。返回 stats。"""
        self._cache.clear()
        return self._build_index()

    def _ensure_loaded(self):
        if not self._loaded:
            self._build_index()

    # ------------------------------------------------------------------
    # 读 API
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        self._ensure_loaded()
        return dict(self._stats)

    def list_docs(self, limit: int = 0) -> list:
        """返回文档摘要列表（供 /api/knowledge 与 UI 使用）。"""
        self._ensure_loaded()
        items = [self._doc_view(d, i) for i, d in enumerate(self._docs)]
        return items[:limit] if limit and limit > 0 else items

    def _doc_view(self, doc: KnowledgeDoc, idx: int) -> dict:
        return {
            "id": idx,
            "doc_id": doc.id,
            "path": _rel(doc.path, self.root),
            "title": doc.title,
            "type": doc.type,
            "status": doc.status,
            "tags": list(doc.tags or []),
            "links": [t for t, _ in (doc.wikilinks or [])],
            "domain": doc.domain,
            "source": doc.source,
            "updated": doc.updated,
            "created": doc.created,
            "parse_error": doc.parse_error,
        }

    def search(self, query: str, limit: int = 20) -> list:
        """关键词搜索：标题 > 标签 > 正文。返回命中的文档摘要（含 score）。"""
        self._ensure_loaded()
        q = (query or "").strip()
        if not q:
            return []
        ql = q.lower()
        hits = []
        for i, d in enumerate(self._docs):
            title = (d.title or "").lower()
            tags = " ".join(d.tags or []).lower()
            body = (d.body or "").lower()
            score = 0
            if ql in title:
                score += 10
            if ql in tags:
                score += 5
            if ql in body:
                score += 1
            if score:
                view = self._doc_view(d, i)
                view["score"] = score
                hits.append(view)
        hits.sort(key=lambda x: (-x["score"], x["path"]))
        return hits[:limit] if limit and limit > 0 else hits

    def resolve(self, ref: str):
        """解析 [[标题]] / doc id / 路径 为文档摘要。找不到返回 None。"""
        self._ensure_loaded()
        ref = (ref or "").strip().strip("[]")
        if not ref:
            return None
        doc = self._titles.get(self._norm(ref))
        if doc is None:
            doc = self._by_path.get(ref) or self._by_path.get(str(self.root / ref))
        if doc is None:
            return None
        return self._doc_view(doc, self._docs.index(doc))

    def related(self, token: str, limit: int = 10) -> list:
        """按共享标签 / wikilink 关系找相关文档。"""
        self._ensure_loaded()
        base = self.resolve(token)
        if base is None:
            return []
        doc = self._docs[base["id"]]
        base_tags = set(t.lower() for t in doc.tags or [])
        base_links = set(self._norm(t) for t, _ in (doc.wikilinks or []))
        if not base_tags and not base_links:
            return []
        out = []
        for i, d in enumerate(self._docs):
            if d.path == doc.path:
                continue
            tags = set(t.lower() for t in d.tags or [])
            score = len(base_tags & tags) * 2
            if self._norm(d.title) in base_links or self._norm(d.id or "") in base_links:
                score += 5
            if score:
                view = self._doc_view(d, i)
                view["score"] = score
                out.append(view)
        out.sort(key=lambda x: (-x["score"], x["path"]))
        return out[:limit] if limit and limit > 0 else out

    def validate(self) -> dict:
        self._ensure_loaded()
        return dict(self._validation)

    # ------------------------------------------------------------------
    # 写 API
    # ------------------------------------------------------------------
    def ingest_document(self, title: str, text: str, source: str = "upload"):
        """写入一篇新文档到 inbox/。返回稳定 doc id（slug），失败返回 None。"""
        self._ensure_loaded()
        title = (title or "未命名文档").strip()[:120]
        text = text or ""
        slug = slugify(title)
        target_dir = self.root / "inbox"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / ("%s.md" % slug)
        n = 1
        while path.exists():
            path = target_dir / ("%s-%d.md" % (slug, n))
            n += 1
        body = "---\nid: %s\ntype: %s\ntitle: %s\nstatus: captured\nsource: %s\ncreated: %s\nupdated: %s\n---\n\n%s\n" % (
            slug,
            "concept",
            title.replace('"', '\\"'),
            source or "upload",
            date.today().isoformat(),
            date.today().isoformat(),
            text,
        )
        try:
            path.write_text(body, encoding="utf-8")
        except OSError:
            return None
        self._cache.invalidate(str(path))
        self.reload()
        return slug

    def archive_conversation(self, session: str, title: str = ""):
        """把一段会话归档为 daily/ 下的一篇 md。返回 doc id；无内容返回 None。"""
        self._ensure_loaded()
        session = (session or "").strip()
        if not session:
            return None
        turns = self._read_session_turns(session)
        if not turns:
            return None
        today_s = date.today().isoformat()
        doc_id = "know-%s-%s" % (today_s, slugify(session)[:24])
        lines = []
        for role, content, ts in turns:
            who = "用户" if role == "user" else "小6"
            lines.append("### %s（%s）\n\n%s\n" % (who, ts or "", content or ""))
        body = "---\ndate: %s\ntags:\n  - 每日归档\n  - 对话记录\nid: %s\nsource: conversation\nsession: %s\ncreated: %s\nupdated: %s\n---\n\n# %s\n\n%s\n" % (
            today_s,
            doc_id,
            session,
            today_s,
            today_s,
            (title or "%s 会话归档" % today_s),
            "\n".join(lines),
        )
        target_dir = self.root / "daily"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / ("%s-归档.md" % doc_id)
        try:
            path.write_text(body, encoding="utf-8")
        except OSError:
            return None
        self._cache.invalidate(str(path))
        self.reload()
        return doc_id

    def _read_session_turns(self, session: str):
        """从 chat_log 读取会话轮次（时间正序）。读取失败返回空列表。"""
        try:
            from db import db_conn
        except Exception:
            return []
        try:
            conn = db_conn()
            rows = conn.execute(
                "SELECT role, content, ts FROM chat_log WHERE session=? ORDER BY id ASC",
                (session,),
            ).fetchall()
            conn.close()
            return [(r[0], r[1], r[2]) for r in rows]
        except Exception:
            return []

    def delete_doc(self, doc_id) -> bool:
        """按 list_docs 返回的整数 id 删除文档。"""
        self._ensure_loaded()
        try:
            idx = int(doc_id)
        except (TypeError, ValueError):
            # 也接受 slug / doc_id
            for i, d in enumerate(self._docs):
                if d.id == doc_id or slugify(d.title) == doc_id:
                    idx = i
                    break
            else:
                return False
        if idx < 0 or idx >= len(self._docs):
            return False
        path = Path(self._docs[idx].path)
        try:
            path.unlink()
        except OSError:
            return False
        self._cache.invalidate(str(path))
        self.reload()
        return True

    def delete_by_source(self, source: str) -> int:
        """按 source 批量删除（用于清理外部导入的知识）。返回删除数量。"""
        self._ensure_loaded()
        source = (source or "").strip()
        if not source:
            return 0
        n = 0
        for d in list(self._docs):
            if (d.source or "") == source:
                try:
                    Path(d.path).unlink()
                    n += 1
                except OSError:
                    continue
        if n:
            self.reload()
        return n


def _rel(path: str, root: Path) -> str:
    try:
        return str(Path(path).relative_to(root)).replace("\\", "/")
    except ValueError:
        return path
