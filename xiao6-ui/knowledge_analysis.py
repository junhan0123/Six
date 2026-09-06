#!/usr/bin/env python3
"""Knowledge Analysis — 只读分析层。

职责：
- 分析现有 knowledge 数据
- 统计文档数量
- 文档更新时间
- 主题分布
- 知识质量指标

约束：
- 不修改 knowledge.py
- 不创建新数据库
- 不修改已有知识数据
- 只读操作
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any


def analyze_knowledge(knowledge_root: Path) -> dict:
    """分析知识目录。

    返回：
    {
        "total_documents": int,
        "domains": dict,
        "topics": list,
        "quality_score": float,
        "stale_documents": list,
        "recent_updates": list,
        "generated_at": str
    }
    """
    if not knowledge_root.is_dir():
        return {
            "total_documents": 0,
            "domains": {},
            "topics": [],
            "quality_score": 0.0,
            "stale_documents": [],
            "recent_updates": [],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": "knowledge root not found",
        }

    # 扫描所有 .md 文件
    docs = []
    skip_dirs = {".obsidian", ".git", ".trash", "node_modules", "__pycache__"}

    for p in sorted(knowledge_root.rglob("*.md")):
        rel = p.relative_to(knowledge_root)
        if any(part in skip_dirs or part.startswith(".") for part in rel.parts):
            continue
        docs.append(p)

    # 分析每个文档
    domain_stats = {}
    all_topics = set()
    stale_docs = []
    recent_docs = []
    total_quality = 0.0

    now = datetime.now()
    stale_threshold = now - __import__("datetime").timedelta(days=30)

    for doc_path in docs:
        try:
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # 域名
        rel = doc_path.relative_to(knowledge_root)
        domain = rel.parts[0] if len(rel.parts) > 1 else ""
        domain_stats[domain] = domain_stats.get(domain, 0) + 1

        # 标题提取
        title = doc_path.stem
        lines = content.split("\n")
        for line in lines[:5]:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # 主题提取（简单启发：从 YAML frontmatter 或标签提取）
        topics = _extract_topics(content, title)
        all_topics.update(topics)

        # 质量评分
        quality = _calculate_quality(content, title, doc_path)
        total_quality += quality

        # 更新检测
        mtime = datetime.fromtimestamp(doc_path.stat().st_mtime)
        if mtime < stale_threshold:
            stale_docs.append({
                "path": str(rel),
                "title": title,
                "last_modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                "days_since_update": (now - mtime).days,
            })
        else:
            recent_docs.append({
                "path": str(rel),
                "title": title,
                "last_modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            })

    total_docs = len(docs)
    avg_quality = total_quality / total_docs if total_docs > 0 else 0.0

    return {
        "total_documents": total_docs,
        "domains": domain_stats,
        "topics": sorted(list(all_topics))[:50],  # 最多50个主题
        "quality_score": round(avg_quality, 2),
        "stale_documents": stale_docs[:20],  # 最多20条
        "recent_updates": recent_docs[-10:],  # 最近10条
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _extract_topics(content: str, title: str) -> list:
    """提取主题。"""
    topics = set()

    # 从 YAML frontmatter 提取 tags
    if content.startswith("---"):
        try:
            end = content.index("---", 3)
            yaml = content[3:end]
            for line in yaml.split("\n"):
                if line.strip().startswith("tags:"):
                    tags_str = line.split(":", 1)[1].strip()
                    # 支持列表格式
                    for tag in re.findall(r'"([^"]+)"|\'([^\']+)\'|([^\s,]+)', tags_str):
                        t = tag[0] or tag[1] or tag[2]
                        if t:
                            topics.add(t)
                    break
        except Exception:
            pass

    # 从内容提取 ## 标题
    for line in content.split("\n"):
        if line.startswith("## "):
            topics.add(line[3:].strip().split()[0] if line[3:].strip() else "")

    # 从标题提取关键词
    for word in title.split():
        if len(word) >= 2:
            topics.add(word)

    return sorted(list(topics))


def _calculate_quality(content: str, title: str, path: Path) -> float:
    """计算文档质量分（0-10）。"""
    score = 5.0  # 基础分

    # 长度加分（最多+2）
    words = len(content.split())
    if words > 500:
        score += 2.0
    elif words > 200:
        score += 1.0

    # 结构加分（最多+1）
    if content.count("\n") > 10:
        score += 0.5
    if re.search(r"^## ", content, re.MULTILINE):
        score += 0.5

    # 链接检查（-1 如果有 broken wikilinks）
    links = re.findall(r"\[\[([^\]]+)\]\]", content)
    if links:
        # 简单检查：如果链接目标不存在于文件名中，扣分
        missing = 0
        for link in links:
            if not any(link.lower() in p.name.lower() for p in path.parent.glob("*.md")):
                missing += 1
        if missing > len(links) * 0.5:
            score -= 1.0

    return max(0.0, min(10.0, score))


def get_quality_metrics(docs: list[dict]) -> dict:
    """从已知文档列表计算质量指标。"""
    if not docs:
        return {"average": 0.0, "distribution": {}}

    scores = []
    for d in docs:
        content = d.get("content") or ""
        title = d.get("title") or ""
        path_str = d.get("path") or ""
        path = Path(path_str) if path_str else None
        score = _calculate_quality(content, title, path or Path("."))
        scores.append(score)

    avg = sum(scores) / len(scores) if scores else 0
    dist = {"excellent": 0, "good": 0, "average": 0, "poor": 0}
    for s in scores:
        if s >= 8:
            dist["excellent"] += 1
        elif s >= 6:
            dist["good"] += 1
        elif s >= 4:
            dist["average"] += 1
        else:
            dist["poor"] += 1

    return {
        "average": round(avg, 2),
        "distribution": dist,
        "total": len(scores),
    }
