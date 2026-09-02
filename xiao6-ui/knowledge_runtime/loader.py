"""Markdown knowledge document loader.

Responsibilities:
- Parse YAML frontmatter (PyYAML when available, otherwise a small built-in
  fallback sufficient for the flat frontmatter schema used by Xiao6).
- Extract wikilinks ([[target|alias]]) and #tags from the body.
- Produce a :class:`KnowledgeDoc` dataclass that the rest of the runtime consumes.

No RAG / Embedding / database. The .md file is the single source of truth.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except Exception:  # pragma: no cover - depends on environment
    _HAVE_YAML = False


# ---------------------------------------------------------------------------
# Schema constants (must stay in sync with KNOWLEDGE_SCHEMA.md)
# ---------------------------------------------------------------------------
STATUSES = {"captured", "reviewed", "linked", "consolidated", "archived", "deprecated"}
TYPES = {"project", "person", "concept", "decision", "rule", "experience", "failure"}
DOMAIN_BY_TYPE = {
    "project": "projects",
    "person": "people",
    "concept": "concepts",
    "decision": "decisions",
    "rule": "rules",
    "experience": "experiences",
    "failure": "failures",
}
TYPE_BY_DOMAIN = {v: k for k, v in DOMAIN_BY_TYPE.items()}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_\u4e00-\u9fff][\w/\u4e00-\u9fff\-]*)")
HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass
class KnowledgeDoc:
    """A single knowledge document (one .md file)."""

    path: str
    id: Optional[str] = None
    type: Optional[str] = None
    title: str = ""
    status: str = "reviewed"
    created: Optional[str] = None
    updated: Optional[str] = None
    source: str = "human"
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    related_knowledge: List[str] = field(default_factory=list)
    related_docs: List[str] = field(default_factory=list)
    confidence: Optional[str] = None
    provenance: Optional[str] = None
    owner: Optional[str] = None
    review_due: Optional[str] = None
    body: str = ""
    frontmatter_raw: str = ""
    mtime: float = 0.0
    domain: Optional[str] = None
    parse_error: Optional[str] = None
    wikilinks: List[Tuple[str, Optional[str]]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------
def _fallback_yaml(text: str) -> dict:
    """Minimal YAML parser for the flat frontmatter schema (no nesting)."""
    out: dict = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            continue
        key, _, val = s.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            out[key] = None
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if inner == "":
                out[key] = []
            else:
                out[key] = [
                    _unquote(x.strip()) for x in inner.split(",") if x.strip() != ""
                ]
        else:
            out[key] = _unquote(val)
    return out


def _unquote(v: str) -> object:
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", "~", ""):
        return None
    return v


def parse_frontmatter(text: str) -> Tuple[dict, str, Optional[str]]:
    """Return (frontmatter_dict, body, parse_error).

    parse_error is None on success; otherwise a human-readable message and the
    frontmatter dict is empty.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        # No frontmatter block -> treat whole text as body, empty metadata.
        return {}, text, None
    raw = m.group(1)
    body = text[m.end():]
    try:
        if _HAVE_YAML:
            fm = yaml.safe_load(raw)
        else:
            fm = _fallback_yaml(raw)
        if fm is None:
            fm = {}
        if not isinstance(fm, dict):
            return {}, body, "frontmatter 不是映射（应为键值对）"
        return fm, body, None
    except Exception as e:  # pragma: no cover - yaml edge cases
        return {}, body, "frontmatter 解析失败: %s" % e


def _dump_frontmatter(fm: dict) -> str:
    """Serialize a flat frontmatter dict back to YAML text."""
    if _HAVE_YAML:
        return yaml.safe_dump(
            fm, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    lines = []
    for k, v in fm.items():
        if v is None:
            lines.append("%s:" % k)
        elif isinstance(v, (list, tuple)):
            if not v:
                lines.append("%s: []" % k)
            else:
                lines.append("%s: [%s]" % (k, ", ".join(_quote_scalar(x) for x in v)))
        else:
            lines.append("%s: %s" % (k, _quote_scalar(v)))
    return "\n".join(lines) + "\n"


def _quote_scalar(v: object) -> str:
    s = "" if v is None else str(v)
    needs_quote = any(c in s for c in (":", "#", "/", ",", "*", "?", "[", "]", "{", "}"))
    if s == "" or needs_quote:
        return '"%s"' % s.replace('"', '\\"')
    return s


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------
def extract_wikilinks(body: str) -> List[Tuple[str, Optional[str]]]:
    out: List[Tuple[str, Optional[str]]] = []
    for m in WIKILINK_RE.finditer(body or ""):
        inner = m.group(1).strip()
        if "|" in inner:
            target, alias = inner.split("|", 1)
            out.append((target.strip(), alias.strip()))
        else:
            out.append((inner, None))
    return out


def extract_tags(body: str, fm_tags: Optional[List[str]]) -> List[str]:
    found: List[str] = []
    seen = set()
    for t in (fm_tags or []):
        if t and t not in seen:
            seen.add(t)
            found.append(t)
    for m in TAG_RE.finditer(body or ""):
        t = m.group(1).strip()
        if t and t not in seen:
            seen.add(t)
            found.append(t)
    return found


def slugify(text: str, max_len: int = 48) -> str:
    text = (text or "").strip().lower()
    words = re.findall(r"[a-z0-9]+", text)
    if words:
        slug = "-".join(words)[:max_len]
        if slug:
            return slug
    return "doc-" + hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def today() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------
def load_document(path: str) -> KnowledgeDoc:
    """Load and parse a single knowledge .md file into a KnowledgeDoc."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    mtime = p.stat().st_mtime
    fm, body, perr = parse_frontmatter(text)

    title = fm.get("title")
    if not title:
        h = HEADING_RE.search(body)
        title = (h.group(1).strip() if h else p.stem)

    wikilinks = extract_wikilinks(body)
    tags = extract_tags(body, fm.get("tags"))

    doc = KnowledgeDoc(
        path=str(p),
        id=fm.get("id"),
        type=fm.get("type"),
        title=title or p.stem,
        status=fm.get("status") or "reviewed",
        created=fm.get("created"),
        updated=fm.get("updated"),
        source=fm.get("source") or "human",
        tags=tags,
        aliases=list(fm.get("aliases") or []),
        links=list(fm.get("links") or []),
        related_knowledge=list(fm.get("related_knowledge") or []),
        related_docs=list(fm.get("related_docs") or []),
        confidence=fm.get("confidence"),
        provenance=fm.get("provenance"),
        owner=fm.get("owner"),
        review_due=fm.get("review_due"),
        body=body,
        frontmatter_raw=(text[: text.find("---", 3)] if perr is None else ""),
        mtime=mtime,
        parse_error=perr,
        wikilinks=wikilinks,
    )
    return doc


def to_markdown(doc: KnowledgeDoc, body: Optional[str] = None) -> str:
    """Serialize a KnowledgeDoc (with current frontmatter fields) back to markdown."""
    fm: dict = {
        "id": doc.id,
        "type": doc.type,
        "title": doc.title,
        "status": doc.status,
        "created": doc.created or today(),
        "updated": doc.updated or today(),
        "source": doc.source,
    }
    for opt in (
        "tags",
        "aliases",
        "links",
        "related_knowledge",
        "related_docs",
        "confidence",
        "provenance",
        "owner",
        "review_due",
    ):
        v = getattr(doc, opt, None)
        if v:
            fm[opt] = v
    # Drop empty optional fields for cleanliness.
    fm = {k: v for k, v in fm.items() if v not in (None, "", [], {})}
    return "---\n%s---\n\n%s" % (_dump_frontmatter(fm), body if body is not None else doc.body)
