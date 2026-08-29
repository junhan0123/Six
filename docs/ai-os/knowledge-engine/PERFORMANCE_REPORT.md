# Knowledge Platform — Performance Benchmark Report (Stage H)

**Sprint**: Knowledge Platform Sprint v1.0 (Final) · Stage H
**Date**: 2026-08-06
**Status**: ✅ COMPLETE (Acceptance: load + search on 1000+ nodes, all within interactive budget)

---

## 1. Objective

Verify that the Knowledge Runtime (single source of truth = `.md` files, **no RAG / embedding / vector DB**) meets interactive latency budgets at scale:

- Load / index **≥ 1000** markdown documents within an acceptable cold-start time.
- Keyword search (`knowledge.search`) stays in the sub-millisecond-to-low-ms range.
- No regression in validation correctness (zero-error contract preserved at scale).

All measurements use the **real runtime package** (`knowledge_runtime.engine.KnowledgeRuntime`) — the same code path the OS uses in production.

---

## 2. Methodology

- A **synthetic vault** of **1200** documents was generated across the 7 knowledge domains, plus a root `index.md` (exempt from id/type), for **1201 nodes total**.
- Distribution: projects 100 · people 200 · concepts 200 · decisions 150 · rules 150 · experiences 200 · failures 200.
- Each document carries valid frontmatter (`id/type/title/status/created/updated/source: bootstrap`) and a body seeded with queryable keywords + `#tags`.
- **No inter-document links** were generated in the synthetic set → 0 relations (this isolates per-node parse + index cost; relation resolution is O(relations) and was separately validated at 35 relations in the canonical vault).
- The synthetic vault was created **outside** the canonical `knowledge/` directory (under `.bench_tmp/vault`) so the production knowledge base was never touched.
- Metrics captured:
  - **Cold load**: `KnowledgeRuntime.load(watch=False)` — full markdown parse + graph build + validate + manifest write.
  - **Warm reload**: second `load()` with manifest already present on disk.
  - **Search**: 8 representative queries, `limit=10` each; recorded avg and p95 latency.
- Environment: Python 3.11.9 (system), PyYAML 6.0.3, Windows (Git Bash), single-threaded.

---

## 3. Results

| Metric | Value | Budget | Verdict |
|---|---|---|---|
| Total nodes | 1201 | ≥ 1000 | ✅ |
| Relations | 0 (synthetic, isolated) | — | — |
| Validation | PASS (validation_ok=True) | 0 error | ✅ |
| **Cold load** | **0.801 s** | < 2 s | ✅ |
| — per-node | 0.667 ms/node | — | ✅ |
| **Warm reload** | **0.137 s** | < 0.5 s | ✅ |
| — per-node | 0.114 ms/node | — | ✅ |
| **Search avg** | **0.392 ms/query** | < 5 ms | ✅ |
| **Search p95** | **0.744 ms/query** | < 10 ms | ✅ |

### Per-query latency (ms)
| Query | Latency |
|---|---|
| xiao6 | 0.891 |
| local-first | 0.275 |
| runtime | 0.289 |
| overlay | 0.175 |
| benchmark | 0.744 |
| proactive | 0.179 |
| event bus | 0.330 |
| knowledge | 0.251 |

---

## 4. Scaling Interpretation

- **Cold load** scales linearly with node count at ~0.67 ms/node. A 5000-node vault would cold-load in ~3.3 s; even at 10,000 nodes the cold start stays under ~7 s — well within an acceptable Electron app boot budget, and the cost is paid once at startup (or lazily on first knowledge access).
- **Warm reload** is ~5× faster than cold (0.11 ms/node) because the manifest short-circuits re-validation work; this is the path used by the Watcher on file-change events, keeping the live index cheap to maintain.
- **Search** is a linear scan over in-memory indexed documents; at 1200 nodes it is effectively free (sub-ms). Even at 10,000 nodes, keyword recall would remain in the low-single-digit ms — far below any interactive threshold. No vector index is needed; the file-as-truth model is sufficient.
- **Relation resolution** (separately validated in the canonical vault at 35 relations) is O(relations) and resolves by id/title/alias in memory; at the observed relation density it is negligible.

---

## 5. Red-Line Confirmation

- ✅ **No RAG / Embedding / Vector DB** — search is pure keyword/structured recall over parsed frontmatter + body; no model inference, no FAISS/Chroma/Milvus/Neo4j.
- ✅ **Local First** — all I/O is local filesystem; no network, no cloud sync.
- ✅ **Single Runtime / Single Write Entry** — the benchmark exercises only `KnowledgeRuntime`; no second state store was introduced.
- ✅ **No change** to Planner / Workflow / Agent / Memory / LLM — measurement only.

---

## 6. Conclusion

The Knowledge Runtime satisfies interactive performance at 1000+ nodes with large headroom. Cold start (0.80 s for 1201 nodes) and search (sub-ms typical) are well within budget, and correctness (validation PASS) is preserved at scale. The platform is production-ready from a performance standpoint.

*Benchmark artifacts (synthetic vault + scripts) were generated under `.bench_tmp/` and removed after measurement; no production knowledge was modified.*
