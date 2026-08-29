#!/usr/bin/env python3
"""庄周 · 认知层 · 自动抽取（Extractor）

一次 LLM pass 同时产出「用户模型增量 + 新 episodes」，落库到各自表。
历史对话压缩（memory_summary 写入 + chat_log 旧轮次删除）仍由 memory.compress_memory 负责，
本模块**只**负责认知抽取，避免双写 memory_summary 与竞争删除 chat_log。
阈值触发 + 后台线程 + 全链路 try/except，失败仅日志，绝不阻断聊天主链路。
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from db import db_conn

# 总轮次超过此值才考虑抽取（与 memory.MEM_KEEP 量级一致）。
THRESHOLD = 40
# 距上次抽取至少新增这么多轮才再次抽取（控制成本）。
EXTRACT_STEP = 20
# 单次抽取最多送入的对话字符数（防 token 爆炸）。
_CONVO_CAP = 6000

_SYS = (
    "你是庄周（个人 AI 副驾）的认知抽取器。阅读下方历史对话片段，"
    "抽取对长期服务该用户有价值的认知，只输出一个 JSON 对象，不要任何解释或 Markdown 代码块。\n"
    "JSON 结构：\n"
    "{\n"
    '  "user_model_delta": {  // 用户模型增量，字段可部分。数组会去重合并，字典会浅更新\n'
    '    "identity": {"name":"","role":"","org":""},\n'
    '    "expertise": ["..."],\n'
    '    "communication_style": {"verbosity":"concise|verbose","formality":"casual|formal","humor":"welcome|avoid"},\n'
    '    "preferences": {"languages":["..."],"frameworks":["..."]},\n'
    '    "recurring_projects": ["..."],\n'
    '    "values": ["..."],\n'
    '    "feedback": ["被纠正过的点/偏好反馈"]\n'
    "  },\n"
    '  "episodes": [  // 重要事件/决定/承诺/偏好，每条独立\n'
    '    {"title":"简短标题","summary":"发生了什么/决定了什么/承诺了什么","category":"decision|commitment|project_state|preference|fact|event","importance":0.0~1.0}\n'
    "  ]\n"
    "}\n"
    "若某字段无新信息，省略该字段或给空值。"
)

_META_KEY = "cognitive_extract_at"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _meta_get(k: str):
    conn = db_conn()
    try:
        r = conn.execute("SELECT value FROM meta WHERE key=?", (k,)).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def _meta_set(k: str, v: str):
    conn = db_conn()
    try:
        conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (k, v),
        )
        conn.commit()
    finally:
        conn.close()


def _extract_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


def maybe_extract():
    """后台线程入口：阈值触发的一次性认知抽取。任何异常都吞掉，不阻断对话。"""
    try:
        from cognitive.episodic import add_episode
        from cognitive.user_model import load_user_model, upsert_user_model
        from llm import agnes_completion
        from memory import MEM_KEEP

        conn = db_conn()
        total = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
        conn.close()
        if total < THRESHOLD:
            return

        last = _meta_get(_META_KEY)
        last = int(last) if last and str(last).isdigit() else 0
        if last and total - last < EXTRACT_STEP:
            return

        # 取最旧待压缩轮次
        conn = db_conn()
        prune = max(0, total - MEM_KEEP)
        old = conn.execute(
            "SELECT role,content FROM chat_log ORDER BY id ASC LIMIT ?", (prune,)
        ).fetchall()
        eps = conn.execute("SELECT summary FROM episodes ORDER BY id DESC LIMIT 15").fetchall()
        conn.close()

        convo = "\n".join(((("用户" if r == "user" else "庄周") + "：" + c) for r, c in old))
        if len(convo) > _CONVO_CAP:
            convo = convo[-_CONVO_CAP:]
        um = load_user_model()
        existing_eps = "\n".join((r[0] or "") for r in eps if r and r[0]) or "（无）"

        prompt = (
            "【已有用户模型】\n" + json.dumps(um, ensure_ascii=False) + "\n\n"
            "【已有情节记忆摘要】\n" + existing_eps + "\n\n"
            "【待抽取的历史对话片段】\n" + convo
        )

        with agnes_completion(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": prompt}],
            tools=[],
            stream=False,
            timeout=90,
        ) as resp:
            import json as _json

            raw = resp.read().decode("utf-8")
            d = _json.loads(raw)
        content = (d.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        out = _extract_json(content)
        if not out:
            _meta_set(_META_KEY, str(total))
            return

        import config  # 惰性导入，避免启动期耦合

        # 1) 用户模型增量（受 FEATURE_USER_MODEL 门控；仅开关开启才落库）
        if getattr(config, "FEATURE_USER_MODEL", False):
            delta = out.get("user_model_delta") or {}
            if isinstance(delta, dict) and delta:
                upsert_user_model(delta)

        # 2) 新情节记忆（受 FEATURE_EPISODIC_MEMORY 门控；历史对话压缩仍由
        #    memory.compress_memory 负责，避免双写 memory_summary / 竞争删除 chat_log）
        if getattr(config, "FEATURE_EPISODIC_MEMORY", False):
            for ep in out.get("episodes") or []:
                if isinstance(ep, dict) and (ep.get("summary") or "").strip():
                    add_episode(
                        ep.get("title", ""),
                        ep.get("summary", ""),
                        ep.get("category", "fact"),
                        float(ep.get("importance", 0.5) or 0.5),
                    )

        _meta_set(_META_KEY, str(total))
    except Exception as e:
        print(f"[cognitive] maybe_extract 失败（已隔离，不影响对话）: {e}")
