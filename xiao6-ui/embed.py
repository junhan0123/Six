#!/usr/bin/env python3
"""小6 · 本地向量语义嵌入（对齐参考实现 bge ONNX 本地向量 RAG）

模型：BAAI/bge-small-zh-v1.5 的 ONNX 量化版（Xenova 移植，dim=512，~24MB，纯 CPU 推理）。
- 依赖：onnxruntime + tokenizers（均已安装），无需 transformers。
- 检索语义：query 侧加 bge 检索指令前缀；文档侧不加；CLS 池化 + L2 归一化。
- 向量持久化在 db.mem_vectors，检索走 numpy 余弦（个人助手量级足够，毫秒级）。
"""

import os
import threading

import numpy as np

_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "embed")
_TOKENIZER_PATH = os.path.join(_MODEL_DIR, "tokenizer.json")
_QUANT_ONNX = os.path.join(_MODEL_DIR, "onnx", "model_quantized.onnx")
_FULL_ONNX = os.path.join(_MODEL_DIR, "onnx", "model.onnx")
_MAX_LEN = 512
_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："  # bge 中文检索指令前缀

_lock = threading.Lock()
_tok = None
_sess = None
_dim = 512


def _ensure_model():
    """懒加载 tokenizer + onnx session（首次调用时），缓存单例。"""
    global _tok, _sess
    if _tok is not None and _sess is not None:
        return _tok, _sess
    with _lock:
        if _tok is not None and _sess is not None:
            return _tok, _sess
        from tokenizers import Tokenizer

        _tok = Tokenizer.from_file(_TOKENIZER_PATH)
        _tok.enable_truncation(_MAX_LEN)
        onnx = _QUANT_ONNX if os.path.exists(_QUANT_ONNX) else _FULL_ONNX
        import onnxruntime as ort

        _sess = ort.InferenceSession(onnx, providers=["CPUExecutionProvider"])
    return _tok, _sess


def _encode_batch(texts):
    """文本列表 → (input_ids, attention_mask, token_type_ids) 的 int64 numpy 数组（统一 pad 到最长）。"""
    tok, _ = _ensure_model()
    encs = tok.encode_batch(list(texts))
    maxlen = max((len(e.ids) for e in encs), default=0)
    ids, masks, tts = [], [], []
    for e in encs:
        n = len(e.ids)
        pad = maxlen - n
        ids.append(e.ids + [0] * pad)
        masks.append([1] * n + [0] * pad)
        tts.append([0] * maxlen)
    return (
        np.array(ids, dtype=np.int64),
        np.array(masks, dtype=np.int64),
        np.array(tts, dtype=np.int64),
    )


def _pool_cls(last_hidden):
    """取 [CLS]（第 0 位）作为句向量，并 L2 归一化。"""
    vec = last_hidden[:, 0, :].astype(np.float32)
    norm = np.linalg.norm(vec, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return vec / norm


def embed_texts(texts, is_query=False):
    """批量嵌入，返回 list[np.ndarray(512,)] 归一化向量。"""
    if isinstance(texts, str):
        texts = [texts]
    if not texts:
        return []
    if is_query:
        texts = [_QUERY_INSTRUCTION + t for t in texts]
    tok, sess = _ensure_model()
    ids, masks, tts = _encode_batch(texts)
    out = sess.run(
        ["last_hidden_state"],
        {"input_ids": ids, "attention_mask": masks, "token_type_ids": tts},
    )[0]
    vecs = _pool_cls(out)
    return [vecs[i] for i in range(vecs.shape[0])]


def embed_query(text):
    """单条查询嵌入（带检索指令前缀）。"""
    return embed_texts([text], is_query=True)[0]


def embed_doc(text):
    """单条文档嵌入（不带前缀）。"""
    return embed_texts([text], is_query=False)[0]


def cosine(a, b):
    """余弦相似度（a,b 已归一化时即点积）。"""
    return float(np.dot(a, b))


# ─────────────────────────── 向量持久化（db.mem_vectors） ───────────────────────────
def _vec_to_blob(vec):
    return np.asarray(vec, dtype=np.float32).tobytes()


def _blob_to_vec(blob):
    return np.frombuffer(blob, dtype=np.float32)


def add_vector(scope, ref_id, vec):
    """写入/更新一条向量（同一 scope+ref_id 覆盖）。"""
    from db import db_conn

    blob = _vec_to_blob(vec)
    ts = _now()
    conn = db_conn()
    try:
        conn.execute(
            "INSERT INTO mem_vectors(scope,ref_id,vec,ctime) VALUES(?,?,?,?) "
            "ON CONFLICT(scope,ref_id) DO UPDATE SET vec=excluded.vec, ctime=excluded.ctime",
            (scope, ref_id, blob, ts),
        )
        conn.commit()
    finally:
        conn.close()


def delete_vectors(scope, ref_id=None):
    """删除某 scope（及可选 ref_id）的向量。"""
    from db import db_conn

    conn = db_conn()
    try:
        if ref_id is None:
            conn.execute("DELETE FROM mem_vectors WHERE scope=?", (scope,))
        else:
            conn.execute("DELETE FROM mem_vectors WHERE scope=? AND ref_id=?", (scope, ref_id))
        conn.commit()
    finally:
        conn.close()


def semantic_search(scope, query_vec, top_k=5, min_score=0.0):
    """在 scope 内做余弦检索，返回 [(ref_id, score), ...] 降序，top_k 个。"""
    from db import db_conn

    conn = db_conn()
    try:
        rows = conn.execute("SELECT ref_id,vec FROM mem_vectors WHERE scope=?", (scope,)).fetchall()
    finally:
        conn.close()
    if not rows:
        return []
    scored = []
    for ref_id, blob in rows:
        v = _blob_to_vec(blob)
        if v.shape[0] != _dim:
            continue
        s = float(np.dot(query_vec, v))
        if s >= min_score:
            scored.append((ref_id, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def _now():
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def model_ready():
    return os.path.exists(_QUANT_ONNX) or os.path.exists(_FULL_ONNX)


# ─────────────────────────── 业务层：索引 + 语义召回 ───────────────────────────
def index_note(nid, text):
    """把一条笔记索引进向量库（写入失败静默，不影响主链路）。"""
    text = (text or "").strip()
    if not text:
        return
    try:
        add_vector("note", nid, embed_doc(text))
    except Exception as e:
        print("[embed] index_note 失败 nid=%s: %s" % (nid, e))


def index_memory(mid, text):
    """把一条记忆索引进向量库。"""
    text = (text or "").strip()
    if not text:
        return
    try:
        add_vector("memory", mid, embed_doc(text))
    except Exception as e:
        print("[embed] index_memory 失败 mid=%s: %s" % (mid, e))


def _fetch_text(scope, ref_id):
    """取回 scope+ref_id 的原文（用于召回结果展示）。"""
    from db import db_conn

    conn = db_conn()
    try:
        if scope == "note":
            r = conn.execute("SELECT title,markdown,content FROM notes WHERE id=?", (ref_id,)).fetchone()
            if not r:
                return None
            title, md, content = r
            text = (md or content or "").strip()
            return ("【%s】%s" % (title, text)) if title else text
        elif scope == "memory":
            r = conn.execute("SELECT title,content FROM memories WHERE id=?", (ref_id,)).fetchone()
            if not r:
                return None
            title, content = r
            text = ((title or "") + " " + (content or "")).strip()
            return text
    except Exception:
        return None
    finally:
        conn.close()
    return None


def memory_search(query, top_k=5, min_score=0.2, scopes=("note", "memory")):
    """语义召回：在指定 scope 内做向量检索，返回 [{'scope','ref_id','score','text'}, ...]。"""
    query = (query or "").strip()
    if not query:
        return []
    qv = embed_query(query)
    res = []
    for scope in scopes:
        for ref_id, score in semantic_search(scope, qv, top_k=top_k, min_score=min_score):
            res.append((scope, ref_id, score))
    res.sort(key=lambda x: x[2], reverse=True)
    out = []
    for scope, ref_id, score in res[:top_k]:
        text = _fetch_text(scope, ref_id)
        if text:
            out.append({"scope": scope, "ref_id": ref_id, "score": round(float(score), 3), "text": text})
    return out


def backfill_all():
    """一次性回填：把 notes / memories 全量嵌入向量库（仅当向量库为空时调用，避免重复）。"""
    from db import db_conn

    conn = db_conn()
    try:
        n = conn.execute("SELECT COUNT(*) FROM mem_vectors").fetchone()[0]
        if n > 0:
            return 0
        done = 0
        rows = conn.execute("SELECT id,markdown,content FROM notes").fetchall()
        for nid, md, content in rows:
            text = (md or content or "").strip()
            if text:
                try:
                    add_vector("note", nid, embed_doc(text))
                    done += 1
                except Exception:
                    pass
        rows = conn.execute("SELECT id,title,content FROM memories").fetchall()
        for mid, title, content in rows:
            text = ((title or "") + " " + (content or "")).strip()
            if text:
                try:
                    add_vector("memory", mid, embed_doc(text))
                    done += 1
                except Exception:
                    pass
        return done
    finally:
        conn.close()
