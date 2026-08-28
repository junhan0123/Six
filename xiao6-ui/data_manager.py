"""服务端数据备份 / 恢复（导出 / 导入为 JSON）。

- 导出：把用户数据表 + 关键本地 JSON 文件打包成一个 JSON，供下载。
- 导入：仅恢复白名单内的表与文件，DELETE + INSERT 整体替换；导入后重建笔记 FTS。
- 所有 BLOB 字段（如 mem_vectors.vec）自动 base64 转码，确保 JSON 可序列化。
"""
import base64
import json
import os
import time

import config
from db import db_conn

# 纳入备份的用户数据表（排除 volatile 缓存 / 审计日志）
EXPORT_TABLES = [
    "notes", "profile", "memory_summary", "reminders", "goals", "tasks",
    "memories", "mem_vectors", "knowledge_docs", "knowledge_chunks",
    "rules", "custom_tools", "user_model", "episodes", "focus", "meta",
    "chat_log", "social_inbound",
]

# 纳入备份的本地 JSON 文件
EXPORT_FILES = ["devices.json", "habits.json"]

BACKUP_SENTINEL = "__zhuangzhou_data_backup__"


def _base_dir():
    try:
        return os.path.dirname(os.path.abspath(config.DB_PATH))
    except Exception:
        return "."


def _enc(v):
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"$b64": base64.b64encode(bytes(v)).decode("ascii")}
    return v


def _dec(v):
    if isinstance(v, dict) and "$b64" in v and isinstance(v["$b64"], str):
        try:
            return base64.b64decode(v["$b64"])
        except Exception:
            return None
    return v


def export_data():
    conn = db_conn()
    try:
        tables = {}
        for name in EXPORT_TABLES:
            try:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({name})").fetchall()]
                rows = conn.execute(f"SELECT * FROM {name}").fetchall()
                tables[name] = {
                    "columns": cols,
                    "rows": [[_enc(c) for c in row] for row in rows],
                }
            except Exception:
                continue
    finally:
        conn.close()

    files = {}
    base = _base_dir()
    for fn in EXPORT_FILES:
        p = os.path.join(base, fn)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    files[fn] = json.load(f)
            except Exception:
                pass

    return {
        BACKUP_SENTINEL: True,
        "schema_version": 1,
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tables": tables,
        "files": files,
    }


def import_data(payload):
    if not isinstance(payload, dict) or not payload.get(BACKUP_SENTINEL):
        raise ValueError("无效的备份文件（缺少校验标记）")
    tables = payload.get("tables", {})
    if not isinstance(tables, dict):
        raise ValueError("tables 字段格式错误")

    allowed = set(EXPORT_TABLES)
    conn = db_conn()
    counts = {}
    try:
        for name, data in tables.items():
            if name not in allowed:
                continue
            cols = data.get("columns")
            rows = data.get("rows")
            if not cols or not isinstance(rows, list):
                continue
            placeholders = ",".join("?" * len(cols))
            col_list = ",".join(f'"{c}"' for c in cols)
            conn.execute(f"DELETE FROM {name}")
            for r in rows:
                if not isinstance(r, list) or len(r) != len(cols):
                    continue
                conn.execute(
                    f"INSERT INTO {name}({col_list}) VALUES({placeholders})",
                    [(_dec(c) if isinstance(c, dict) and "$b64" in c else c) for c in r],
                )
            counts[name] = len(rows)
        # 重建笔记 FTS（本项目不使用触发器，导入后手动补齐）
        try:
            conn.execute("DELETE FROM notes_fts")
            conn.execute(
                "INSERT INTO notes_fts(rowid,title,markdown,tags,folder) "
                "SELECT rowid,title,markdown,tags,folder FROM notes"
            )
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()

    file_counts = {}
    base = _base_dir()
    for fn, content in (payload.get("files") or {}).items():
        if fn not in set(EXPORT_FILES):
            continue
        p = os.path.join(base, fn)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            file_counts[fn] = True
        except Exception:
            pass

    return {"ok": True, "tables": counts, "files": file_counts}
