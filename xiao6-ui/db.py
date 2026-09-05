#!/usr/bin/env python3
"""小6 · 数据库层（SQLite，WAL 并发加固）"""

import json
import sqlite3
import hashlib
import re

from config import DB_PATH


def db_conn():
    # 并发加固：WAL 允许多读单写，busy_timeout 避免瞬间并发触发 database is locked
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
    except sqlite3.DatabaseError:
        pass
    conn.execute("""CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, content TEXT, tag TEXT)""")
    _migrate_notes(conn)
    _migrate_fts(conn)
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, session TEXT, role TEXT, content TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS profile(
        key TEXT PRIMARY KEY, value TEXT, updated TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS memory_summary(
        id INTEGER PRIMARY KEY CHECK(id=1), summary TEXT, updated TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS reminders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, due_ts TEXT, content TEXT,
        done INTEGER DEFAULT 0, created TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS pending_proactive(
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, content TEXT,
        ts TEXT, shown INTEGER DEFAULT 0)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS meta(
        key TEXT PRIMARY KEY, value TEXT)""")
    # Phase 3.1 多步任务表（重启可续）
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, step TEXT, total_steps INTEGER DEFAULT 0,
        status TEXT DEFAULT 'open', created TEXT, updated TEXT)""")
    _migrate_tasks(conn)
    # Phase 3：目标系统主表（Goal = 用户意图/项目；Task 经 tasks.goal_id 软外键归属）
    conn.execute("""CREATE TABLE IF NOT EXISTS goals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'active',
        priority TEXT DEFAULT 'medium',
        horizon TEXT DEFAULT 'short',
        progress INTEGER DEFAULT 0,
        parent_id INTEGER DEFAULT NULL,
        due_date TEXT DEFAULT NULL,
        completed_at TEXT DEFAULT NULL,
        created TEXT NOT NULL,
        updated TEXT NOT NULL)""")
    # Phase 46 · 目标多轮/动态重规划 canonical 状态：revision（重规划版本号）/
    # round_index（当前轮次序号）/ round_status（本轮 FSM 状态）。幂等升级，旧库缺列时
    # 静默 ALTER，绝不影响正在运行的实例。缺省语义：revision=1、round_index=1、round_status='none'。
    _migrate_goals(conn)
    # Phase 2.3 线索/焦点栈：记录近期被提及的实体（URL、[[双向链接]]、话题），
    # 用于指代消解（"那个网页""进度怎样"）与 ACI 上下文注入。纯本地零密钥。
    conn.execute("""CREATE TABLE IF NOT EXISTS focus(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT, text TEXT, ts TEXT, hits INTEGER DEFAULT 1)""")
    # Phase 3.2：工具审计日志（自动脱敏）
    conn.execute("""CREATE TABLE IF NOT EXISTS tool_audit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, tool TEXT, summary TEXT, detail TEXT,
        status TEXT, risk TEXT, source TEXT,
        args_json TEXT, result_preview TEXT, duration_ms INTEGER)""")
    # Phase 3.3：记忆图谱（事实/人物/知识节点 + 关系链接）
    conn.execute("""CREATE TABLE IF NOT EXISTS memories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT, content TEXT, detail TEXT, title TEXT,
        mem_id TEXT, entities TEXT, concepts TEXT, tags TEXT,
        links TEXT, salience INTEGER DEFAULT 0, source_ref TEXT,
        timestamp TEXT, visibility INTEGER DEFAULT 1,
        content_hash TEXT UNIQUE)""")
    _migrate_memories(conn)
    _migrate_memory_truth(conn)
    # Phase 12 · P12-3：重要日期（生日/纪念日/节日），提前 N 天提醒
    conn.execute("""CREATE TABLE IF NOT EXISTS important_dates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, type TEXT, description TEXT,
        reminder_days INTEGER DEFAULT 3,
        created TEXT, updated TEXT)""")
    # Phase 12 · P12-3：对话沉淀摘要，让小6「记得你上周说的事」
    conn.execute("""CREATE TABLE IF NOT EXISTS conversation_memories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, topic TEXT, key_points TEXT, sentiment TEXT,
        created TEXT)""")
    # Phase 2：ACI 预热缓存（天气/新闻定时预热落盘，模型醒来即用，免密钥）
    conn.execute("""CREATE TABLE IF NOT EXISTS prefetch_cache(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT UNIQUE,
        content TEXT,
        fetched_at TEXT,
        expires_at TEXT,
        tags TEXT DEFAULT '[]')""")
    # 自动化规则（IFTTT 式）：定时/事件触发 → 通知或打开面板
    conn.execute("""CREATE TABLE IF NOT EXISTS rules(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        trigger_type TEXT,
        trigger_value TEXT,
        action_type TEXT,
        action_value TEXT,
        enabled INTEGER DEFAULT 1,
        last_triggered TEXT,
        created TEXT)""")
    # PHASE 130：主动建议表（只读建议，不自动执行）
    conn.execute("""CREATE TABLE IF NOT EXISTS suggestions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        observation_id TEXT UNIQUE,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        priority INTEGER DEFAULT 5,
        status TEXT DEFAULT 'pending',
        created TEXT,
        accepted_at TEXT,
        rejected_at TEXT
    )""")
    # PHASE 131：任务提案表（用户审批后才创建任务）
    conn.execute("""CREATE TABLE IF NOT EXISTS task_proposals(
        id TEXT PRIMARY KEY,
        suggestion_id TEXT UNIQUE,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        steps TEXT,
        estimated_cost INTEGER DEFAULT 5,
        risk TEXT DEFAULT 'low',
        status TEXT DEFAULT 'pending',
        created TEXT,
        approved_at TEXT,
        rejected_at TEXT,
        task_id INTEGER
    )""")
    # PHASE 133: 自动化执行层表
    try:
        _migrate_automation(conn)
    except Exception:
        pass
    # PHASE 139: GFE 数据源基础层表
    try:
        _migrate_gfe_sources(conn)
    except Exception:
        pass
    # PHASE 140: GFE World State Engine 表
    try:
        _migrate_gfe_world_state(conn)
    except Exception:
        pass
    # PHASE 141: GFE Event Intelligence 表
    try:
        _migrate_gfe_events(conn)
    except Exception:
        pass
    # PHASE 142: GFE Historical Comparison 表
    try:
        _migrate_gfe_historical_comparison(conn)
    except Exception:
        pass
    # PHASE 143: GFE Causal Graph 表
    try:
        _migrate_gfe_causal_graph(conn)
    except Exception:
        pass
    # PHASE 144: GFE Analyst Council 表
    try:
        _migrate_gfe_analyst_council(conn)
    except Exception:
        pass
    # PHASE 145: GFE Scenario Engine 表
    try:
        _migrate_gfe_scenario_engine(conn)
    except Exception:
        pass
    # PHASE 146: GFE Forecast Engine 表
    try:
        _migrate_gfe_forecast_engine(conn)
    except Exception:
        pass
    # PHASE 147: GFE Forecast Ledger 表
    try:
        _migrate_gfe_forecast_ledger(conn)
    except Exception:
        pass
    # PHASE 148: GFE Early Warning 表
    try:
        _migrate_gfe_early_warning(conn)
    except Exception:
        pass
    # PHASE 149: GFE Forecast Calibration 表
    try:
        _migrate_gfe_calibration(conn)
    except Exception:
        pass
    # 向后兼容：补齐 suggestions 表缺失列
    try:
        _migrate_suggestions(conn)
    except Exception:
        pass
    # 通用预取任务（对齐参考实现 manage_prefetch_task）：TICK 按各自的 interval 自动取数，
    # 结果落盘 prefetch_cache（action=cache）或推进主动消息（action=notify）。
    conn.execute("""CREATE TABLE IF NOT EXISTS prefetch_tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        source TEXT DEFAULT 'web',
        query TEXT DEFAULT '',
        action TEXT DEFAULT 'cache',
        interval INTEGER DEFAULT 3600,
        enabled INTEGER DEFAULT 1,
        last_run TEXT,
        next_run TEXT,
        created TEXT)""")
    # 社交接收端：入站消息（微信/飞书/Discord）→ 跑 agent 轮 → 回发，落库便于审计与回看
    conn.execute("""CREATE TABLE IF NOT EXISTS social_inbound(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, channel TEXT, sender TEXT, text TEXT,
        replied INTEGER DEFAULT 0, reply TEXT)""")
    # 工具工厂 / 动态 API 槽：用户声明的自定义工具规格（声明式，持久化，重启不丢）
    conn.execute("""CREATE TABLE IF NOT EXISTS custom_tools(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        spec_json TEXT NOT NULL,
        created TEXT)""")
    # P1 认知层：用户模型（单行 JSON 文档，LLM 自动演化）
    conn.execute("""CREATE TABLE IF NOT EXISTS user_model(
        id INTEGER PRIMARY KEY CHECK (id = 1),
        data TEXT NOT NULL,
        confidence REAL DEFAULT 0.5,
        updated TEXT)""")
    # P1 认知层：情节记忆条目（向量由 embed.py 管理，scope='episode'，无需本表加列）
    conn.execute("""CREATE TABLE IF NOT EXISTS episodes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        category TEXT,
        importance REAL DEFAULT 0.5,
        created TEXT NOT NULL,
        last_accessed TEXT,
        access_count INTEGER DEFAULT 0)""")
    # 本地向量语义 RAG：句向量存储（bge-small-zh-v1.5，dim=512，float32）
    conn.execute("""CREATE TABLE IF NOT EXISTS mem_vectors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT NOT NULL,
        ref_id INTEGER NOT NULL,
        vec BLOB NOT NULL,
        ctime TEXT,
        UNIQUE(scope, ref_id))""")
    # P4-B 持久知识库：文档元数据 + 切分后的原文块（向量存于 mem_vectors scope='knowledge'）
    conn.execute("""CREATE TABLE IF NOT EXISTS knowledge_docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source TEXT DEFAULT '',
        chunk_count INTEGER DEFAULT 0,
        ctime TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS knowledge_chunks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        idx INTEGER DEFAULT 0,
        text TEXT NOT NULL,
        ctime TEXT)""")
    # 自我学习：用户显式反馈 / LLM 蒸馏的持久经验（注入上下文，可纠错删除）
    # content_hash UNIQUE 保证同内容只增权重不重复写入
    conn.execute("""CREATE TABLE IF NOT EXISTS learnings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        content TEXT,
        content_hash TEXT UNIQUE,
        weight REAL DEFAULT 1.0,
        created TEXT,
        last_used TEXT)""")
    # —— Phase 44 · Session & Checkpoint Foundation ——
    # 仅承载“协调元数据 / 引用指针”，不复制任何 canonical truth（对话/目标/任务/记忆/运行时/事件）。
    # 红线自检：本表无任何 conversation/goal/task/memory/runtime/event 内容列。
    conn.execute("""CREATE TABLE IF NOT EXISTS session_registry(
        session_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        status TEXT DEFAULT 'active')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS session_checkpoints(
        checkpoint_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        goal_id INTEGER,
        task_id INTEGER,
        chat_log_id INTEGER,
        runtime_ref TEXT,
        label TEXT,
        status TEXT DEFAULT 'valid')""")
    _migrate_session(conn)
    return conn


def insert_audit(tool, summary, status="ok", source="llm", args_json="{}", result_preview="", duration_ms=0, risk=""):
    """写入一条工具审计记录（沙箱层调用，异常静默兜底）。"""
    try:
        conn = db_conn()
        conn.execute(
            "INSERT INTO tool_audit(ts,tool,summary,detail,status,risk,source,args_json,result_preview,duration_ms) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                tool,
                summary,
                "",
                status,
                risk,
                source,
                args_json,
                result_preview,
                duration_ms,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _json_or_empty(v):
    """列表/字典 → JSON 字符串；已是字符串则原样；None → '[]'。"""
    if v is None:
        return "[]"
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return "[]"


def memory_content_hash(content):
    """归一化 content 的 stable sha1，用于 memories 去重（镜像 learnings.content_hash）。"""
    if content is None:
        return None
    s = re.sub(r"\s+", " ", content.strip())
    return hashlib.sha1(s.encode("utf-8")).hexdigest() if s else None


def import_memories(records, source="import:external"):
    """幂等导入外部记忆记录（事实/人物/知识节点 + 关系链接）。

    P4.3-C：
    - 每次导入先经 Canonical `delete_by_source_ref` **软归档**上次同源记录
      （tombstone：status='deprecated'+archived=1，保留可恢复，绝不物理 DROP），
      再逐条经 Canonical Memory API 写入/复活：
        · 含稳定 mem_id 的记录 → 已存在则 update 复活（status='active',archived=0），
          否则 create（content_hash 幂等）；
        · 无 mem_id 的记录 → 直接 create（content_hash 幂等）。
    - 重导语义：重复调用 = 相同数据稳定落地，旧同源记录永不被物理删除。
    返回导入条数。
    """
    import memory

    # 1) 软归档上次同源记录（tombstone，保留可恢复，绝不物理 DROP）
    memory.delete_by_source_ref(source, tombstone=True)

    # 2) 逐条经 Canonical Memory API 写入/复活（mem_id 稳定 → 幂等重导）
    n = 0
    for r in records:
        mem_id = r.get("mem_id") or r.get("id")
        if mem_id:
            existing = memory.get_memory(mem_id=mem_id)
            if existing:
                if memory.update_memory(
                    id=existing["id"],
                    event_type=r.get("event_type") or "knowledge",
                    title=r.get("title") or "",
                    detail=r.get("detail") or "",
                    content=(r.get("content") or ""),
                    entities=r.get("entities"),
                    concepts=r.get("concepts"),
                    tags=r.get("tags"),
                    links=r.get("links"),
                    salience=r.get("salience") or 0,
                    source_ref=f"{source}:{mem_id}",
                    visibility=r.get("visibility"),
                    confidence=r.get("confidence"),
                    source=r.get("source") or "import",
                    status="active",
                    archived=0,
                ):
                    n += 1
                continue
        rid = memory.create_memory(
            r.get("content") or "",
            event_type=r.get("event_type") or "knowledge",
            title=r.get("title") or "",
            detail=r.get("detail") or "",
            mem_id=mem_id,
            entities=r.get("entities"),
            concepts=r.get("concepts"),
            tags=r.get("tags"),
            links=r.get("links"),
            salience=r.get("salience") or 0,
            source_ref=f"{source}:{mem_id}" if mem_id else None,
            visibility=r.get("visibility"),
            confidence=r.get("confidence"),
            source=r.get("source") or "import",
        )
        if rid is not None:
            n += 1
    return n


def upsert_memory_by_mem_id(mem):
    """按 mem_id PATCH/INSERT 一条记忆（canonical → memory.upsert_memory）。

    幂等：mem_id 已存在则只 PATCH 传入字段（None 跳过，保留其它旧字段），否则 INSERT。
    mem 字段：mem_id(必填) + event_type/title/content/detail/entities/concepts/tags/links/salience/source_ref/timestamp/visibility
    list 字段用 JSON 串存储。返回 mem_id。
    """
    import memory

    memory.upsert_memory(mem)
    return mem.get("mem_id")


def get_memories(limit=500, archived=0):
    """返回记忆节点列表（links 解析为 list）。

    Hermes 记忆生命周期：archived=0 仅返回活跃记忆（注入上下文的工作集），
    archived=1 仅返回已归档的冷存储记忆。默认仅活跃，避免归档记忆污染主动上下文。
    """
    conn = db_conn()
    rows = conn.execute(
        "SELECT id,event_type,title,content,mem_id,entities,tags,links,salience,source_ref "
        "FROM memories WHERE archived=? ORDER BY salience DESC, id LIMIT ?",
        (int(archived), limit),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        links = r[7]
        try:
            links = json.loads(links) if links else []
        except Exception:
            links = []
        out.append(
            {
                "id": r[0],
                "event_type": r[1],
                "title": r[2],
                "content": r[3],
                "mem_id": r[4],
                "entities": r[5],
                "tags": r[6],
                "links": links,
                "salience": r[8],
                "source_ref": r[9],
            }
        )
    return out


def upsert_person(name, content, salience=4):
    """写入/更新一个人物节点（event_type='person'），按姓名去重（mem_id 由姓名哈希）。
    canonical → memory.upsert_memory。"""
    import hashlib
    import memory

    mem_id = "person_" + hashlib.md5(name.strip().encode("utf-8")).hexdigest()[:10]
    memory.upsert_memory({
        "mem_id": mem_id,
        "event_type": "person",
        "title": name.strip(),
        "content": content.strip(),
        "links": [],
        "salience": salience,
        "source_ref": "extract:persons",
        "visibility": 1,
    })
    return mem_id


def get_memories_by_type(event_type, limit=300, archived=0):
    """返回指定类型的记忆节点列表。archived 同 get_memories，默认仅活跃。"""
    conn = db_conn()
    rows = conn.execute(
        "SELECT id,event_type,title,content,mem_id,entities,tags,links,salience,source_ref "
        "FROM memories WHERE event_type=? AND archived=? ORDER BY salience DESC, id LIMIT ?",
        (event_type, int(archived), limit),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        links = r[7]
        try:
            links = json.loads(links) if links else []
        except Exception:
            links = []
        out.append(
            {
                "id": r[0],
                "event_type": r[1],
                "title": r[2],
                "content": r[3],
                "mem_id": r[4],
                "entities": r[5],
                "tags": r[6],
                "links": links,
                "salience": r[8],
                "source_ref": r[9],
            }
        )
    return out


def archive_memory(mem_id, archived=1):
    """归档 / 恢复一条记忆（按 mem_id）。archived=1 归档进冷存储，archived=0 恢复到活跃工作集。

    P4.2：经 Canonical Memory API（memory.archive_memory / memory.restore_memory）切换
    archived 状态，保证切换走统一治理（governance 列 + 领域事件），不绕过契约。
    返回受影响的行数（0 表示 mem_id 不存在）。归档不删除数据，仅切换状态，可随时恢复。
    """
    if not mem_id:
        return 0
    import memory

    if memory.get_memory(mem_id=mem_id) is None:
        return 0
    if archived:
        memory.archive_memory(mem_id=mem_id)
    else:
        memory.restore_memory(mem_id=mem_id)
    return 1


def get_memory_stats():
    """返回记忆分类统计，供用户消息处理器面板使用。

    - memory: 总记忆数
    - constraint: event_type='self_constraint' 的硬约束数量
    - knowledge: event_type='knowledge' 的知识/方法数量
    - decayed: 显著性 <=2 的"衰退"记忆数量（当前无访问时间字段，先用 salience proxy）
    """
    conn = db_conn()
    rows = conn.execute(
        "SELECT event_type, COUNT(*), SUM(CASE WHEN salience<=2 THEN 1 ELSE 0 END) "
        "FROM memories WHERE archived=0 GROUP BY event_type"
    ).fetchall()
    archived_total = conn.execute("SELECT COUNT(*) FROM memories WHERE archived=1").fetchone()[0]
    conn.close()
    counts = {}
    decayed = 0
    for typ, cnt, dec in rows:
        typ = typ or "unknown"
        counts[typ] = cnt
        decayed += int(dec or 0)
    total = sum(counts.values())
    return {
        "memory": total,
        "constraint": counts.get("self_constraint", 0),
        "knowledge": counts.get("knowledge", 0),
        "decayed": decayed,
        "archived": archived_total,
    }


def get_memory_graph():
    """返回 {nodes, edges}，供前端力导图画图。

    节点用 mem_id 作为稳定 id（无 mem_id 则退化为 id:N）；边来自 links 的
    target_id + relation。仅保留两端都在节点集合内的边，避免悬空引用。
    """
    mems = get_memories(limit=500)
    nodes = []
    for m in mems:
        nid = m["mem_id"] or f"id:{m['id']}"
        nodes.append(
            {
                "id": nid,
                "label": m["title"] or m["mem_id"] or f"节点{m['id']}",
                "type": m["event_type"],
                "salience": m["salience"],
            }
        )
    node_ids = {n["id"] for n in nodes}
    edges = []
    for m in mems:
        src = m["mem_id"] or f"id:{m['id']}"
        for ln in m["links"] or []:
            if not isinstance(ln, dict):
                continue  # 跳过非字典链接（如热点归档写入的 URL 字符串），避免 'str'.get 崩溃
            tgt = ln.get("target_id")
            if tgt and src in node_ids and tgt in node_ids:
                edges.append({"source": src, "target": tgt, "relation": ln.get("relation", "")})
    return {"nodes": nodes, "edges": edges}


def _migrate_notes(conn):
    """向后兼容升级 notes 表：新增 Obsidian 风格字段。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()}
    adds = [
        ("title", "ALTER TABLE notes ADD COLUMN title TEXT"),
        ("markdown", "ALTER TABLE notes ADD COLUMN markdown TEXT"),
        ("tags", "ALTER TABLE notes ADD COLUMN tags TEXT"),
        ("links", "ALTER TABLE notes ADD COLUMN links TEXT"),
        ("folder", "ALTER TABLE notes ADD COLUMN folder TEXT DEFAULT '收件箱'"),
        ("aliases", "ALTER TABLE notes ADD COLUMN aliases TEXT"),
    ]
    for col, ddl in adds:
        if col not in cols:
            try:
                conn.execute(ddl)
            except Exception:
                pass
    conn.commit()


def _migrate_fts(conn):
    """可选增强：FTS5(trigram) 中文全文检索索引（独立表，自存检索文本）。

    - 若该 SQLite 编译版本不含 FTS5，静默跳过，search_notes 自动降级为 LIKE，
      主链路与正在运行的实例（PID 29280，旧代码）绝不受影响。
    - **不创建任何触发器**：旧实例的写入路径不会触碰 notes_fts，即使其 SQLite
      缺 FTS5 也绝不会因触发器报错而中断。索引同步改由写入路径显式调用
      `fts_upsert`（异常静默兜底）+ 启动时按行数差重建补齐（捕获过渡期内
      旧实例写入的笔记）。
    - 采用「独立 FTS5 表」而非外部内容表：规避部分 SQLite 构建下
      content='notes' + 'delete' 命令导致 disk image malformed 的坑。
    """
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, markdown, tags, folder, tokenize='trigram')"
        )
        # 行数不一致（首次回填 / 过渡期旧实例新增笔记 / 同步遗漏）才重建，
        # 避免每次建连都全量重建。独立表直接以 notes 全量灌入即可。
        fts_cnt = conn.execute("SELECT count(*) FROM notes_fts").fetchone()[0]
        note_cnt = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
        if fts_cnt != note_cnt:
            conn.execute("DELETE FROM notes_fts")
            conn.execute(
                "INSERT INTO notes_fts(rowid,title,markdown,tags,folder) "
                "SELECT id,title,markdown,tags,folder FROM notes"
            )
        conn.commit()
    except sqlite3.OperationalError:
        # 无 FTS5 支持 → 跳过，主链路不受影响
        pass


def fts_upsert(conn, rowid, title, markdown, tags, folder):
    """将一条笔记写入/更新进 FTS 索引（独立表：先删后插）。
    无 FTS5 支持时静默跳过，绝不阻断主链路写入。"""
    try:
        conn.execute("DELETE FROM notes_fts WHERE rowid=?", (rowid,))
        conn.execute(
            "INSERT INTO notes_fts(rowid,title,markdown,tags,folder) VALUES(?,?,?,?,?)",
            (rowid, title, markdown, tags, folder),
        )
    except sqlite3.OperationalError:
        pass


def fts_delete(conn, rowid):
    """从 FTS 索引删除一条笔记。无 FTS5 支持时静默跳过。"""
    try:
        conn.execute("DELETE FROM notes_fts WHERE rowid=?", (rowid,))
    except sqlite3.OperationalError:
        pass


def _migrate_tasks(conn):
    """向后兼容升级 tasks 表：补齐多步追踪字段（JSON 步骤清单 / 当前步序号 / 进度备注）。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    adds = [
        ("steps", "ALTER TABLE tasks ADD COLUMN steps TEXT"),
        ("current_step", "ALTER TABLE tasks ADD COLUMN current_step INTEGER DEFAULT 0"),
        ("note", "ALTER TABLE tasks ADD COLUMN note TEXT"),
        ("goal_id", "ALTER TABLE tasks ADD COLUMN goal_id INTEGER DEFAULT NULL"),
    ]
    for col, ddl in adds:
        if col not in cols:
            try:
                conn.execute(ddl)
            except Exception:
                pass
    conn.commit()


def _migrate_automation(conn):
    """PHASE 133: 自动化执行层表。"""
    # execution_requests 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(execution_requests)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE execution_requests(
            id TEXT PRIMARY KEY,
            proposal_id TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            risk TEXT DEFAULT 'low',
            approval_source TEXT DEFAULT 'user',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            error_message TEXT,
            runtime_name TEXT DEFAULT 'agent_runtime',
            runtime_entry TEXT DEFAULT 'run_chat_turn',
            tools_called TEXT,
            duration_ms INTEGER
        )""")
    
    # 向后兼容：补齐 execution_requests 缺失列
    _add_columns_if_missing(conn, 'execution_requests', [
        ('runtime_name', 'TEXT DEFAULT \'agent_runtime\''),
        ('runtime_entry', 'TEXT DEFAULT \'run_chat_turn\''),
        ('tools_called', 'TEXT'),
        ('duration_ms', 'INTEGER')
    ])
    
    # automation_audit 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(automation_audit)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE automation_audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            entity_id TEXT,
            entity_type TEXT,
            action TEXT NOT NULL,
            user TEXT DEFAULT 'system',
            details TEXT,
            created_at TEXT NOT NULL
        )""")
    
    conn.commit()


def _migrate_gfe_sources(conn):
    """PHASE 139: GFE 数据源基础层表。"""
    # gfe_sources 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_sources)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_sources(
            source_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            authority TEXT,
            country TEXT,
            reliability REAL DEFAULT 0.5,
            historical_accuracy REAL DEFAULT 0.0,
            update_frequency TEXT,
            license TEXT,
            provenance TEXT,
            metadata TEXT DEFAULT '{}',
            created_at REAL,
            last_updated REAL
        )""")
    
    # gfe_source_metrics 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_source_metrics)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_source_metrics(
            metric_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            accuracy_score REAL,
            freshness_score REAL,
            authority_score REAL,
            historical_score REAL,
            overall_score REAL,
            sample_count INTEGER DEFAULT 0,
            updated_at REAL,
            FOREIGN KEY (source_id) REFERENCES gfe_sources(source_id)
        )""")
    
    conn.commit()


def _migrate_gfe_world_state(conn):
    """PHASE 140: GFE World State Engine 表。"""
    # gfe_world_states 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_world_states)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_world_states(
            state_id TEXT PRIMARY KEY,
            country_code TEXT NOT NULL,
            snapshot_time REAL NOT NULL,
            confidence REAL DEFAULT 0.5,
            provenance TEXT,
            demographics TEXT DEFAULT '{}',
            economy TEXT DEFAULT '{}',
            finance TEXT DEFAULT '{}',
            industry TEXT DEFAULT '{}',
            technology TEXT DEFAULT '{}',
            energy TEXT DEFAULT '{}',
            military TEXT DEFAULT '{}',
            diplomacy TEXT DEFAULT '{}',
            trade TEXT DEFAULT '{}',
            fiscal TEXT DEFAULT '{}',
            social TEXT DEFAULT '{}',
            created_at REAL
        )""")

    # gfe_indicators 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_indicators)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_indicators(
            indicator_id TEXT PRIMARY KEY,
            country_code TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            value REAL,
            unit TEXT,
            timestamp REAL NOT NULL,
            source_id TEXT,
            confidence REAL DEFAULT 0.5,
            provenance TEXT,
            created_at REAL
        )""")

    # gfe_state_changes 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_state_changes)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_state_changes(
            change_id TEXT PRIMARY KEY,
            country_code TEXT NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            change_reason TEXT,
            source_refs TEXT DEFAULT '[]',
            timestamp REAL NOT NULL
        )""")

    conn.commit()


def _migrate_gfe_events(conn):
    """PHASE 141: GFE Event Intelligence 表。"""
    # gfe_events 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_events)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_events(
            event_id TEXT PRIMARY KEY,
            source_id TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            category TEXT NOT NULL,
            country_code TEXT,
            region TEXT,
            severity REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            impact TEXT,
            status TEXT DEFAULT 'detected',
            provenance TEXT,
            event_time REAL,
            created_at REAL
        )""")

    # gfe_event_impacts 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_event_impacts)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_event_impacts(
            impact_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            target_dimension TEXT NOT NULL,
            impact_direction TEXT NOT NULL,
            impact_strength REAL,
            time_horizon INTEGER,
            reason TEXT,
            confidence REAL DEFAULT 0.5,
            created_at REAL
        )""")

    # gfe_risk_signals 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_risk_signals)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_risk_signals(
            signal_id TEXT PRIMARY KEY,
            country_code TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            description TEXT NOT NULL,
            severity REAL DEFAULT 0.5,
            probability REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            source_event_ids TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            created_at REAL
        )""")

    conn.commit()


def _migrate_gfe_historical_comparison(conn):
    """PHASE 142: GFE Historical Comparison 表。"""
    # gfe_historical_cases 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_historical_cases)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_historical_cases(
            case_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            period_start REAL,
            period_end REAL,
            country_code TEXT,
            category TEXT NOT NULL,
            description TEXT,
            state_snapshot TEXT DEFAULT '{}',
            event_refs TEXT DEFAULT '[]',
            outcome TEXT,
            lessons TEXT,
            provenance TEXT,
            created_at REAL
        )""")

    # gfe_historical_matches 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_historical_matches)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_historical_matches(
            match_id TEXT PRIMARY KEY,
            current_reference TEXT NOT NULL,
            case_id TEXT NOT NULL,
            similarity_score REAL,
            matching_dimensions TEXT DEFAULT '[]',
            explanation TEXT,
            confidence REAL DEFAULT 0.5,
            created_at REAL
        )""")

    conn.commit()


def _migrate_gfe_causal_graph(conn):
    """PHASE 143: GFE Causal Graph 表。"""
    # gfe_causal_nodes 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_causal_nodes)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_causal_nodes(
            node_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            entity_type TEXT,
            provenance TEXT,
            created_at REAL
        )""")

    # gfe_causal_edges 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_causal_edges)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_causal_edges(
            edge_id TEXT PRIMARY KEY,
            source_node TEXT NOT NULL,
            target_node TEXT NOT NULL,
            relationship_type TEXT,
            strength REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            time_delay INTEGER,
            evidence_refs TEXT DEFAULT '[]',
            provenance TEXT,
            created_at REAL
        )""")

    conn.commit()


def _migrate_gfe_analyst_council(conn):
    """PHASE 144: GFE Analyst Council 表。"""
    # gfe_analyst_agents 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_analyst_agents)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_analyst_agents(
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            weight REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            provenance TEXT,
            created_at REAL
        )""")

    # gfe_analysis_reports 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_analysis_reports)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_analysis_reports(
            report_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            analyst_id TEXT NOT NULL,
            analysis TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            evidence_refs TEXT DEFAULT '[]',
            created_at REAL
        )""")

    # gfe_consensus_results 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_consensus_results)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_consensus_results(
            consensus_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            final_analysis TEXT NOT NULL,
            agreement_score REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            created_at REAL
        )""")

    conn.commit()


def _migrate_gfe_scenario_engine(conn):
    """PHASE 145: GFE Scenario Engine 表。"""
    # gfe_scenarios 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_scenarios)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_scenarios(
            scenario_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            assumptions TEXT DEFAULT '{}',
            probability REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            created_at REAL
        )""")

    # gfe_scenario_impacts 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_scenario_impacts)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_scenario_impacts(
            impact_id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            dimension TEXT NOT NULL,
            direction TEXT NOT NULL,
            strength REAL DEFAULT 0.5,
            reason TEXT,
            confidence REAL DEFAULT 0.5,
            created_at REAL
        )""")

    # gfe_scenario_paths 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_scenario_paths)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_scenario_paths(
            path_id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            source_node TEXT NOT NULL,
            target_node TEXT NOT NULL,
            impact_score REAL DEFAULT 0.5,
            time_horizon INTEGER,
            created_at REAL
        )""")

    conn.commit()


def _migrate_gfe_forecast_engine(conn):
    """PHASE 146: GFE Forecast Engine 表。"""
    # gfe_forecasts 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_forecasts)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_forecasts(
            forecast_id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            target TEXT NOT NULL,
            prediction TEXT NOT NULL,
            probability REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            time_horizon INTEGER,
            status TEXT DEFAULT 'draft',
            created_at REAL,
            updated_at REAL
        )""")

    # gfe_forecast_evidence 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_forecast_evidence)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_forecast_evidence(
            evidence_id TEXT PRIMARY KEY,
            forecast_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_ref TEXT,
            weight REAL DEFAULT 0.5,
            impact REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            created_at REAL
        )""")

    # gfe_forecast_versions 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_forecast_versions)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_forecast_versions(
            version_id TEXT PRIMARY KEY,
            forecast_id TEXT NOT NULL,
            previous_prediction TEXT,
            new_prediction TEXT,
            change_reason TEXT,
            created_at REAL
        )""")

    conn.commit()


def _migrate_gfe_forecast_ledger(conn):
    """PHASE 147: GFE Forecast Ledger 表。"""
    # gfe_forecast_ledger 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_forecast_ledger)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_forecast_ledger(
            ledger_id TEXT PRIMARY KEY,
            forecast_id TEXT NOT NULL,
            prediction TEXT NOT NULL,
            actual_result TEXT,
            brier_score REAL,
            accuracy_score REAL,
            evaluated_at REAL,
            created_at REAL
        )""")

    # gfe_forecast_metrics 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_forecast_metrics)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_forecast_metrics(
            metric_id TEXT PRIMARY KEY,
            forecast_type TEXT NOT NULL,
            sample_count INTEGER DEFAULT 0,
            average_brier_score REAL DEFAULT 0.5,
            accuracy_rate REAL DEFAULT 0.5,
            calibration_score REAL DEFAULT 0.5,
            updated_at REAL
        )""")

    conn.commit()


def _migrate_gfe_early_warning(conn):
    """PHASE 148: GFE Early Warning 表。"""
    # gfe_warning_rules 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_warning_rules)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_warning_rules(
            rule_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            conditions TEXT DEFAULT '{}',
            severity REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5,
            enabled INTEGER DEFAULT 1,
            created_at REAL
        )""")

    # gfe_warning_alerts 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_warning_alerts)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_warning_alerts(
            alert_id TEXT PRIMARY KEY,
            country_code TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            severity REAL,
            probability REAL,
            confidence REAL,
            trigger_refs TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            created_at REAL
        )""")

    # gfe_warning_history 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_warning_history)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_warning_history(
            history_id TEXT PRIMARY KEY,
            alert_id TEXT,
            old_status TEXT,
            new_status TEXT,
            reason TEXT,
            created_at REAL
        )""")

    conn.commit()


def _migrate_gfe_calibration(conn):
    """PHASE 149: GFE Forecast Calibration 表。"""
    # gfe_calibration_records 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_calibration_records)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_calibration_records(
            record_id TEXT PRIMARY KEY,
            forecast_id TEXT,
            analyst_id TEXT,
            domain TEXT,
            predicted_probability REAL,
            actual_result REAL,
            brier_score REAL,
            confidence_error REAL,
            created_at REAL
        )""")

    # gfe_analyst_metrics 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_analyst_metrics)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_analyst_metrics(
            metric_id TEXT PRIMARY KEY,
            analyst_id TEXT NOT NULL,
            domain TEXT,
            sample_count INTEGER DEFAULT 0,
            average_brier_score REAL DEFAULT 0.5,
            accuracy_rate REAL DEFAULT 0.5,
            calibration_score REAL DEFAULT 0.5,
            weight_adjustment REAL DEFAULT 0.0,
            updated_at REAL
        )""")

    # gfe_calibration_history 表
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_calibration_history)").fetchall()}
    if not cols:
        conn.execute("""CREATE TABLE gfe_calibration_history(
            history_id TEXT PRIMARY KEY,
            analyst_id TEXT,
            old_weight REAL,
            new_weight REAL,
            reason TEXT,
            created_at REAL
        )""")

    conn.commit()


def _add_columns_if_missing(conn, table_name, columns):
    """向后兼容：为表添加缺失的列（幂等）。"""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for col_name, col_def in columns:
        if col_name not in cols:
            try:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass
    conn.commit()


def _migrate_suggestions(conn):
    """向后兼容升级 suggestions 表：补齐缺失列。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(suggestions)").fetchall()}
    adds = [
        ("description", "ALTER TABLE suggestions ADD COLUMN description TEXT"),
        ("priority", "ALTER TABLE suggestions ADD COLUMN priority INTEGER DEFAULT 5"),
        ("created", "ALTER TABLE suggestions ADD COLUMN created TEXT"),
        ("accepted_at", "ALTER TABLE suggestions ADD COLUMN accepted_at TEXT"),
        ("rejected_at", "ALTER TABLE suggestions ADD COLUMN rejected_at TEXT"),
    ]
    for col, ddl in adds:
        if col not in cols:
            try:
                conn.execute(ddl)
            except Exception:
                pass
    conn.commit()


def _migrate_session(conn):
    """Phase 44 · 为 goals / tasks 增加 session_id 软外键列（分组标签，非第二真相源）。

    与既有 tasks.goal_id 软外键同构：仅用于把一次会话所产生的目标/任务聚合投影，
    不复制任何对话/目标/任务内容。幂等：旧库缺列时静默 ALTER，绝不影响运行实例。
    """
    for table in ("goals", "tasks"):
        cols = {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table).fetchall()}
        if "session_id" not in cols:
            try:
                conn.execute(
                    "ALTER TABLE %s ADD COLUMN session_id TEXT DEFAULT NULL" % table
                )
            except Exception:
                pass
    conn.commit()


def _migrate_goals(conn):
    """Phase 46 · 向后兼容升级 goals 表：补齐多轮/重规划 canonical 字段。

    仅新增三列（revision / round_index / round_status），绝不动既有列、绝不删列、
    绝不引入新表。幂等：旧库缺列时静默 ALTER，已存在则跳过；不影响正在运行的实例。

    约定：
    - revision     INTEGER DEFAULT 1  重规划版本号；仅由 agent_runtime._do_replan() 递增。
    - round_index  INTEGER DEFAULT 1  当前执行轮次序号（1-based）。
    - round_status TEXT    DEFAULT 'none'  本轮 FSM 状态：none/planned/running/observing/
                                          evaluating/{COMPLETE|CONTINUE|REPLAN|BLOCK|FAIL}；
                                          Goal 自身终态仍由 status 承载，round_status 永不取
                                          'completed'（Round 永不创造第五个终态）。
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(goals)").fetchall()}
    adds = [
        ("revision", "ALTER TABLE goals ADD COLUMN revision INTEGER DEFAULT 1"),
        ("round_index", "ALTER TABLE goals ADD COLUMN round_index INTEGER DEFAULT 1"),
        ("round_status", "ALTER TABLE goals ADD COLUMN round_status TEXT DEFAULT 'none'"),
    ]
    for col, ddl in adds:
        if col not in cols:
            try:
                conn.execute(ddl)
            except Exception:
                pass
    conn.commit()


def _migrate_memories(conn):
    """向后兼容升级 memories 表：
    - archived 归档状态列（参考 Hermes 记忆生命周期）。
    - content_hash 幂等去重列（镜像 learnings.content_hash）：支撑 import_memories /
      upsert_memory_by_mem_id / upsert_person / memory_distiller 的
      ON CONFLICT(content_hash) DO NOTHING。

    关键约束：SQLite 禁止对非空表 ALTER 加 UNIQUE 列（报错 Cannot add a UNIQUE column），
    故采用「ADD 普通列 → CREATE UNIQUE INDEX → 回填存量」三步法：
    1) ALTER 普通列（允许）；
    2) CREATE UNIQUE INDEX（存量全 NULL，不触发唯一冲突，可重复执行）；
    3) 回填存量 content_hash（逐行，重复 content 仅首条写好、其余 UNIQUE 冲突则跳过——
       绝不删数据、绝不破坏运行实例）。
    老库：ALTER 升级；新库：CREATE TABLE 已含 content_hash UNIQUE，本迁移幂等跳过。
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()}
    if "archived" not in cols:
        try:
            conn.execute("ALTER TABLE memories ADD COLUMN archived INTEGER DEFAULT 0")
        except Exception:
            pass
    if "content_hash" not in cols:
        # 1) 加普通列（SQLite 不允许 ALTER 加 UNIQUE 列）
        try:
            conn.execute("ALTER TABLE memories ADD COLUMN content_hash TEXT")
        except Exception:
            pass
        # 2) 建 UNIQUE 索引（存量全 NULL 不冲突；索引名固定，可重复执行）
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_content_hash ON memories(content_hash)")
        except sqlite3.OperationalError:
            # 极端存量重复（非空表建索引失败）：仅去重非 NULL 重复行，保留最小 id，再建索引。
            # 空 content（hash=NULL）的行全部保留，绝不误删。
            try:
                conn.execute(
                    "DELETE FROM memories WHERE content_hash IS NOT NULL "
                    "AND id NOT IN (SELECT MIN(id) FROM memories WHERE content_hash IS NOT NULL GROUP BY content_hash)"
                )
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_content_hash ON memories(content_hash)")
            except Exception:
                pass
        # 3) 回填存量 content_hash（重复行冲突跳过，绝不删数据）
        try:
            for row_id, content in conn.execute("SELECT id, content FROM memories").fetchall():
                try:
                    conn.execute("UPDATE memories SET content_hash=? WHERE id=?", (memory_content_hash(content), row_id))
                except Exception:
                    pass
        except Exception:
            pass
    conn.commit()


def _migrate_memory_truth(conn):
    """Phase 20.5 · Memory Truth Layer：为 memories / episodes 增加可信治理列。

    - memories: confidence(来源可信度) / source(来源类型) / status(active|deprecated|conflict) / verified_at
    - episodes: project(关联项目) / source(事件来源) / event(事件类型)
    幂等：旧库缺列时静默 ALTER，绝不删数据、绝不影响运行实例。
    """
    mem_cols = {r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()}
    for col, ddl in (
        ("confidence", "REAL DEFAULT 0.5"),
        ("source", "TEXT DEFAULT 'inference'"),
        ("status", "TEXT DEFAULT 'active'"),
        ("verified_at", "TEXT"),
    ):
        if col not in mem_cols:
            try:
                conn.execute("ALTER TABLE memories ADD COLUMN %s %s" % (col, ddl))
            except Exception:
                pass
    epi_cols = {r[1] for r in conn.execute("PRAGMA table_info(episodes)").fetchall()}
    for col, ddl in (
        ("project", "TEXT"),
        ("source", "TEXT DEFAULT 'system'"),
        ("event", "TEXT"),
    ):
        if col not in epi_cols:
            try:
                conn.execute("ALTER TABLE episodes ADD COLUMN %s %s" % (col, ddl))
            except Exception:
                pass
    conn.commit()


def save_turn(session, role, content):
    """持久化一轮对话（跨会话长期记忆的基础）。"""
    from datetime import datetime

    content = (content or "").strip()
    if not content:
        return
    conn = db_conn()
    conn.execute(
        "INSERT INTO chat_log(ts,session,role,content) VALUES(?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session, role, content),
    )
    conn.commit()
    conn.close()
