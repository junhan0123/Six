#!/usr/bin/env python3
"""Knowledge Intelligence — 知识智能聚合层。

职责：
- 读取已有 knowledge 数据
- 分析质量
- 生成建议
- 返回分析结果

约束：
- 禁止写入数据库
- 禁止修改 knowledge.py
- 只读操作
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from knowledge import list_docs, stats as knowledge_stats
from knowledge_analysis import analyze_knowledge, get_quality_metrics
from knowledge_pipeline import get_pipeline


def get_status() -> dict:
    """获取知识智能状态摘要。

    返回：
    {
        total_documents: int,
        quality_score: float,
        topics: list,
        stale_documents: list,
        generated_at: str
    }
    """
    try:
        # 获取知识根目录
        from knowledge import runtime
        knowledge_root = getattr(runtime, "root", Path(__file__).resolve().parent.parent / "knowledge")

        # 运行分析
        analysis = analyze_knowledge(knowledge_root)

        # 获取文档详情
        docs = list_docs() or []
        quality = get_quality_metrics(docs)

        return {
            "total_documents": analysis["total_documents"],
            "quality_score": analysis["quality_score"],
            "topics": analysis["topics"],
            "stale_documents": analysis["stale_documents"],
            "domain_distribution": analysis["domains"],
            "quality_distribution": quality.get("distribution", {}),
            "generated_at": analysis["generated_at"],
        }

    except Exception as e:
        return {
            "error": str(e),
            "total_documents": 0,
            "quality_score": 0.0,
            "topics": [],
            "stale_documents": [],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def analyze(dry_run: bool = True) -> dict:
    """执行知识分析（dry-run 模式，禁止修改数据库）。

    返回：
    {
        mode: "dry_run",
        documents_analyzed: int,
        summary_candidates: list,
        association_candidates: list
    }
    """
    try:
        from knowledge import list_docs
        docs = list_docs() or []

        pipeline = get_pipeline()
        summary_candidates = []
        association_candidates = []

        for doc in docs[:50]:  # 最多分析50条
            content = doc.get("content") or ""
            title = doc.get("title") or doc.get("path", "").stem

            # 生成摘要建议
            if len(content) > 200:
                summary = pipeline.generate_summary(content)
                if summary["compression_ratio"] < 0.3:
                    summary_candidates.append({
                        "doc_id": doc.get("id") or doc.get("path"),
                        "title": title,
                        "compression_ratio": summary["compression_ratio"],
                        "summary_preview": summary["summary"][:100],
                        "action": "generate_summary",
                    })

            # 提取实体建议
            entities = pipeline.extract_entities(content)
            if entities["count"] > 0:
                association_candidates.append({
                    "doc_id": doc.get("id") or doc.get("path"),
                    "title": title,
                    "entity_count": entities["count"],
                    "top_entities": [e["value"] for e in entities["entities"][:5]],
                    "action": "extract_entities",
                })

        return {
            "mode": "dry_run" if dry_run else "live",
            "documents_analyzed": len(docs),
            "summary_candidates": summary_candidates[:10],
            "association_candidates": association_candidates[:10],
            "total_suggestions": len(summary_candidates) + len(association_candidates),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "error": str(e),
            "mode": "dry_run",
            "documents_analyzed": 0,
            "summary_candidates": [],
            "association_candidates": [],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
