#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage F — Obsidian Bridge smoke test.

Proves the file-system Watcher keeps the Knowledge Runtime index fresh when
files change OUTSIDE the runtime (i.e. when the user edits in Obsidian).
No DB/RAG; single source of truth = knowledge/ .md files.

Key facts validated:
  - external CREATE of a .md -> runtime auto-reindexes (+1 node)
  - external DELETE of a .md -> runtime auto-reindexes (-1 node)
  - runtime ingest -> doc present (write path works)
All temp artifacts are removed from disk so knowledge/ stays at 46 nodes.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path("G:/xiao6")
sys.path.insert(0, str(ROOT / "xiao6-ui"))

from knowledge_runtime import KnowledgeRuntime

KNOWLEDGE_ROOT = ROOT / "knowledge"
STAMP = time.strftime("%H%M%S")


def main():
    rt = KnowledgeRuntime(str(KNOWLEDGE_ROOT))
    rt.load(watch=True)          # starts Windows ReadDirectoryChangesW watcher
    time.sleep(0.8)              # let the watcher enter its blocking read
    base = rt.stats()["nodes"]
    print("[base] nodes = %d | watcher_active = %s" % (base, rt.stats()["watcher_active"]))

    ok = True

    # 1) Simulate Obsidian creating a note externally.
    ext_file = KNOWLEDGE_ROOT / "concepts" / ("concept-ext-%s.md" % STAMP)
    ext_file.write_text(
        "---\nid: concept-ext-%s\ntype: concept\ntitle: Ext %s\nstatus: reviewed\n"
        "created: '2026-08-06'\nupdated: '2026-08-06'\nsource: bootstrap\ntags: [test]\n"
        "---\n\ntemporary external-create probe\n" % (STAMP, STAMP),
        encoding="utf-8",
    )
    time.sleep(1.2)              # debounce 0.4s + margin
    after_create = rt.stats()["nodes"]
    det_c = (after_create == base + 1)
    ok &= det_c
    print("[external create] nodes = %d (expected %d) -> %s"
          % (after_create, base + 1, "OK" if det_c else "FAIL"))

    # 2) Simulate Obsidian deleting the note externally.
    os.remove(ext_file)
    time.sleep(0.9)
    after_delete = rt.stats()["nodes"]
    det_d = (after_delete == base)
    ok &= det_d
    print("[external delete] nodes = %d (expected %d) -> %s"
          % (after_delete, base, "OK" if det_d else "FAIL"))

    # 3) Runtime write path still works (ingest) -> then clean from disk.
    new_id = rt.ingest_document("Bridge Ingest %s" % STAMP, "probe body",
                                source="bootstrap", domain="concepts", type="concept")
    ingested = (rt.read_by_id(new_id) is not None)
    ok &= ingested
    print("[runtime ingest] id=%s present=%s" % (new_id, ingested))
    probe_doc = rt.read_by_id(new_id)
    if probe_doc and Path(probe_doc.path).exists():
        os.remove(probe_doc.path)
    rt.reload()

    # final sanity: back to base, no temp files left
    final = rt.stats()["nodes"]
    clean = (final == base)
    ok &= clean
    print("[final] nodes = %d (expected %d) -> %s" % (final, base, "OK" if clean else "FAIL"))

    # belt-and-suspenders: sweep any probe residue from disk
    import glob as _glob
    for pat in ("concepts/concept-ext-*.md", "concepts/bridge-ingest-*.md",
                "concepts/concept-bridge-test.md"):
        for f in _glob.glob(str(KNOWLEDGE_ROOT / pat)):
            try:
                os.remove(f)
            except OSError:
                pass
    rt.reload()

    if rt.watcher:
        rt.watcher.stop()

    print("\nBRIDGE SMOKE TEST: %s" % ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
