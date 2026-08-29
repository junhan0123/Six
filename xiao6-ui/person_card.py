"""小6 · 人物卡（本地结构化人物档案，纯标准库）。

用于保存 / 检索用户关心的人的结构化档案（身份、关键事实、标签、关系）。
零外部依赖、零密钥；无数据时优雅提示如何创建。后续若需要可平滑替换为
联网百科数据源（如百度百科 / Wikipedia），接口保持不变。
"""

import json
import os
from datetime import datetime

from config import HERE

STORE = os.path.join(HERE, "data", "person_cards.json")


def _load():
    try:
        if os.path.exists(STORE):
            with open(STORE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save(cards):
    try:
        os.makedirs(os.path.dirname(STORE), exist_ok=True)
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_card(name):
    """按名称精确或包含匹配返回单张人物卡；无则返回 None。"""
    cards = _load()
    name = (name or "").strip()
    if not name:
        return None
    for c in cards:
        cn = c.get("name", "")
        if cn == name or name in cn:
            return c
    return None


def list_cards():
    """返回全部人物卡（按更新时间倒序）。"""
    cards = _load()
    cards.sort(key=lambda c: c.get("updated", ""), reverse=True)
    return cards


def save_card(name, identity="", facts=None, tags=None, relation=""):
    """新建或更新一张人物卡，返回最终卡片对象。"""
    cards = _load()
    name = (name or "").strip()
    if not name:
        return None
    facts = facts or []
    tags = tags or []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for c in cards:
        if c.get("name") == name:
            c["identity"] = identity or c.get("identity", "")
            c["facts"] = facts or c.get("facts", [])
            c["tags"] = tags or c.get("tags", [])
            c["relation"] = relation or c.get("relation", "")
            c["updated"] = now
            _save(cards)
            return c
    card = {
        "name": name,
        "identity": identity,
        "facts": facts,
        "tags": tags,
        "relation": relation,
        "created": now,
        "updated": now,
    }
    cards.append(card)
    _save(cards)
    return card


def format_card(c):
    """把单张人物卡格式化为给 LLM 的文字摘要。"""
    if not c:
        return ""
    lines = [f"# 人物卡：{c.get('name', '?')}"]
    if c.get("identity"):
        lines.append(f"身份：{c['identity']}")
    if c.get("relation"):
        lines.append(f"与你的关系：{c['relation']}")
    facts = c.get("facts") or []
    if facts:
        lines.append("关键事实：")
        lines += [f"  • {f}" for f in facts]
    tags = c.get("tags") or []
    if tags:
        lines.append("标签：" + "、".join(tags))
    lines.append(f"（更新于 {c.get('updated', '')}）")
    return "\n".join(lines)
