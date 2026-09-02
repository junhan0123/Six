# Knowledge Platform — Runtime Report (Stage I · A)

**Sprint**: Knowledge Platform Sprint v1.0 (Final)
**Date**: 2026-08-06
**Status**: ✅ COMPLETE

---

## 1. Purpose

The Knowledge Runtime is the **single source of truth and single entry point** for all knowledge in Xiao6 AI OS. It replaces the legacy RAG/embedding backend with a **file-based** model: every knowledge item is a markdown document under `knowledge/`, and all reads/writes flow through one facade.

Core invariants (also the Sprint red lines):
- **The `.md` file is the only source of truth** — no DB, no vector store, no RAG, no embedding.
- **One runtime, one write entry.** No second state store, EventBus, or Memory.
- **Local First** — all I/O is local; git-tracked; no cloud sync, no network.
- **Obsidian is the only editor.** The vault is a standard Obsidian vault.

---

## 2. Package Layout

```
xiao6-ui/
├── knowledge.py                 # Public facade (single entry point)
├── knowledge_runtime/
│   ├── __init__.py              # Re-exports KnowledgeRuntime, get_runtime
│   ├── engine.py                # KnowledgeRuntime: load/parse/validate/manifest/write
│   ├── loader.py                # Frontmatter + wikilink + tag parsing; schema constants
│   ├── validator.py             # Zero-error contract (error/warning/info)
│   ├── resolver.py              # Resolve by id / title / alias
│   ├── links.py                 # Out/back links, tag index, cycle detection, related()
│   ├── search.py                # Keyword search (file-level, no embedding)
│   ├── manifest.py              # Manifest write/read (sidecar file)
│   ├── watcher.py               # Event-driven fs watcher (ReadDirectoryChangesW)
│   └── cache.py                 # Lightweight in-memory caches
└── context/
    └── knowledge_source.py      # Context-provider adapter (uses knowledge.search)
```

Vault: `G:/xiao6/knowledge/` (Obsidian vault root).
Manifest sidecar: `G:/xiao6/knowledge_manifest.json` (vault-external, prevents reload storms).

---

## 3. Public API Surface (`knowledge.*`)

**Reads**
- `load()` / `reload()` — parse vault, build graph, validate, write manifest.
- `search(query, limit=N)` — keyword/structured recall over parsed docs (no embedding).
- `resolve(target)` — resolve a wikilink/title/id/alias to a doc.
- `related(id, limit=N)` — scored neighbours (out +3 / back +2 / shared-tag +1).
- `validate()` — run the zero-error contract; returns errors/warnings/info.
- `stats()` — `by_domain / by_type / by_status / nodes / relations / validation_ok / watcher_active`.
- `list_docs()`, `read(path)`, `read_by_id(id)`.

**Writes**
- `ingest_document(...)` — create a new knowledge doc with validated frontmatter.
- `archive_conversation(...)` — convert a conversation transcript into a knowledge doc.
- `delete_doc(id)` — soft-delete (mark `deprecated`, keep file for git audit).
- `delete_by_source(source)` — bulk soft-delete by provenance.

Advanced callers may use `knowledge.runtime` (the live `KnowledgeRuntime` instance).

---

## 4. Design Principles

1. **File = truth.** Frontmatter is the structured contract; the body is human-readable markdown. Obsidian edits the body; nothing else owns the data.
2. **Schema-driven validation.** Required `id/type/title/status/created/updated/source`; optional `tags/alias/links/confidence/related_goals/...`. Root `index.md` is exempt from id/type.
3. **No RAG.** `search()` is keyword + frontmatter recall over in-memory parsed docs. No model inference, no vector maths.
4. **Event-driven freshness.** A Windows `ReadDirectoryChangesW` watcher rebuilds the index on file changes (debounce 0.4 s, daemon thread, no polling). On non-Windows it degrades to a no-op (manual reload still works).
5. **Manifest sidecar.** Index metadata lives *outside* the vault so the runtime never triggers its own reload storm.
6. **Single write entry.** All mutations go through the facade → `KnowledgeRuntime` → validated frontmatter → file. No module writes knowledge markdown directly.

---

## 5. Live State (verified 2026-08-06)

| Property | Value |
|---|---|
| Nodes | 46 |
| Relations | 35 |
| Validation | PASS (validation_ok = True, 0 error, 0 warning) |
| Watcher | available (Windows) |
| Manifest | sidecar `knowledge_manifest.json` |

---

## 6. Red-Line Compliance

| Red line | Status |
|---|---|
| No RAG / Embedding / Vector DB | ✅ keyword-only; `semantic_query` alias removed |
| No second Runtime / Memory / EventBus | ✅ single facade + single runtime |
| Local First (no cloud/network) | ✅ local fs + git only |
| No change to Planner/Workflow/Agent/Memory/LLM | ✅ measurement + adapter only |
| Obsidian = only editor | ✅ vault config supplied |

---

## 7. Conclusion

The Knowledge Runtime is a complete, validated, Local-First file-based knowledge layer. It is the sole knowledge entry point for the entire OS and is frozen for long-term use after this Sprint.
