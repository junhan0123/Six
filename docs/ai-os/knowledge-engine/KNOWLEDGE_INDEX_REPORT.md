# Knowledge Platform — Index & Reindex Report (Stage I · C)

**Sprint**: Knowledge Platform Sprint v1.0 (Final)
**Date**: 2026-08-06
**Status**: ✅ COMPLETE

---

## 1. What "Index" Means Here

There is **no external index engine** (no SQLite, no FAISS, no Neo4j). The "index" is the in-memory model the runtime rebuilds from the markdown vault on every load. Freshness is maintained two ways:

1. **Cold / warm load** — `knowledge.load()` parses all `.md` files, builds the document + link + tag graph, validates, and writes a manifest.
2. **Live reindex** — the event-driven Watcher detects file changes and triggers a reload, so the in-memory index tracks Obsidian edits within ~0.4 s.

---

## 2. Components of the Index

| Component | Source | Built from |
|---|---|---|
| Document index | `knowledge/*.md` | Frontmatter (id/type/title/status/...) + body |
| Link graph | `links` / `related_knowledge` + `[[wikilinks]]` | Out/back adjacency, tag index |
| Resolver index | frontmatter `id` / `title` / `alias` | `by_id` / `by_title` / `by_alias` maps |
| Search index | parsed text | Keyword tokens over title + body + tags (no embedding) |
| Manifest | `knowledge_manifest.json` (sidecar) | `nodes / relations / validation_ok / generated_at` |

### Root MOC
`knowledge/index.md` is the **Map of Content** — the Obsidian entry point. It is exempt from the id/type requirement (validator `_is_root_index()`) and uses `[[wikilinks]]` to surface the major domains and hub node.

---

## 3. Reindex Triggers

| Trigger | Path | Latency |
|---|---|---|
| App start / first access | `knowledge.load(watch=False)` | ~0.8 s for 1200 nodes (Stage H) |
| File created/edited/deleted in vault | Watcher → `reload()` | debounce 0.4 s; 0.14 s reload @1200 |
| Manual | `knowledge.reload()` via API | same as warm reload |
| Ingest / archive / delete | facade write → manifest refresh | synchronous, validated |

The Watcher uses Windows `ReadDirectoryChangesW` (ctypes, daemon thread, **no polling**). On non-Windows it is a no-op and `reload()` is used manually. The manifest lives **outside** the vault (`knowledge_manifest.json`) so the runtime's own manifest write never triggers a self-reload storm.

---

## 4. Search Semantics

- `search(query, limit=N)` is **keyword/structured** recall: it matches the query against titles, tags, and body text of parsed documents.
- It returns ranked snippets with `id / title / path / snippet / score`.
- There is **no semantic/vector ranking** — `semantic_query` was removed. This keeps the index transparent, debuggable, and zero-cost to rebuild.

---

## 5. Consistency Guarantees

- **Validation gate**: every load runs `validate()`; the zero-error contract must hold (errors = missing/duplicate id, invalid type/status, unparseable frontmatter). Warnings (broken link, orphan, cycle) are surfaced but non-fatal.
- **Single writer**: only the facade may mutate the vault, so the index can never diverge from disk except within the 0.4 s debounce window (intentional, self-healing).
- **Git auditability**: because the index is derived entirely from markdown, any divergence is resolved by re-reading files — there is no separate store to corrupt.

---

## 6. Live Verification (2026-08-06)

- Nodes: **46**, Relations: **35**, validation_ok: **True**.
- Manifest sidecar present and current.
- Watcher available on Windows; live reindex exercised successfully in the Obsidian Bridge smoke test (create +1 / delete −1 detected).

---

## 7. Conclusion

The index is a pure function of the markdown vault, rebuilt on load and kept live by the Watcher. It is correct, fast, and fully Local-First — no external index technology required.
