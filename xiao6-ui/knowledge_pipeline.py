#!/usr/bin/env python3
"""Knowledge Pipeline — 文档处理流水线（proposal only，禁止直接写入）。

职责：
- analyze_document() — 分析文档
- generate_summary() — 生成摘要
- extract_entities() — 提取实体
- extract_topics() — 提取主题

输出必须是 proposal（建议），禁止直接写入数据库。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class KnowledgePipeline:
    """知识处理流水线。"""

    def __init__(self):
        self.max_summary_length = 200  # 摘要最大长度
        self.min_entity_length = 2     # 实体最小长度

    def analyze_document(self, content: str, metadata: dict = None) -> dict:
        """分析文档，返回 proposal。

        返回：
        {
            "proposal_type": "analysis",
            "word_count": int,
            "paragraph_count": int,
            "has_structure": bool,
            "quality_score": float,
            "recommendations": list
        }
        """
        metadata = metadata or {}
        lines = content.split("\n")
        words = len(content.split())
        paragraphs = len([l for l in lines if l.strip()])

        # 结构检查
        has_h1 = bool(re.search(r"^# ", content, re.MULTILINE))
        has_h2 = bool(re.search(r"^## ", content, re.MULTILINE))
        has_h3 = bool(re.search(r"^### ", content, re.MULTILINE))
        has_structure = has_h1 or has_h2

        # 质量评分
        score = 5.0
        if words > 500:
            score += 2
        elif words > 200:
            score += 1
        if has_h2:
            score += 1
        if has_h3:
            score += 0.5

        # 建议
        recommendations = []
        if not has_h1:
            recommendations.append({"action": "add_title", "reason": "缺少一级标题"})
        if words < 100:
            recommendations.append({"action": "expand", "reason": "内容过短，建议补充"})
        if not has_h2:
            recommendations.append({"action": "add_sections", "reason": "建议添加二级标题分段"})

        return {
            "proposal_type": "analysis",
            "status": "proposal",
            "word_count": words,
            "paragraph_count": paragraphs,
            "has_structure": has_structure,
            "quality_score": round(min(score, 10.0), 2),
            "recommendations": recommendations,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def generate_summary(self, content: str, max_length: int = None) -> dict:
        """生成摘要 proposal。

        注意：此实现使用启发式方法，生产环境可接入 LLM。
        """
        max_length = max_length or self.max_summary_length
        lines = [l.strip() for l in content.split("\n") if l.strip()]

        # 提取前 N 个关键句
        summary_parts = []
        for line in lines:
            # 跳过代码块、链接等
            if line.startswith("```") or line.startswith("[") or line.startswith("<"):
                continue
            if len(line) > 10:
                summary_parts.append(line)
            if len("".join(summary_parts)) >= max_length:
                break

        summary = " ".join(summary_parts)[:max_length]
        if len(summary_parts) > 0 and summary.endswith("."):
            summary = summary[:-1]

        return {
            "proposal_type": "summary",
            "status": "proposal",
            "original_length": len(content),
            "summary_length": len(summary),
            "compression_ratio": round(len(summary) / max(len(content), 1), 3),
            "summary": summary,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def extract_entities(self, content: str) -> dict:
        """提取实体 proposal。"""
        entities = []

        # 人名（简单启发：2-4字中文）
        chinese_names = re.findall(r'[\u4e00-\u9fff]{2,4}(?=，|。|、|\s|$)', content)
        for name in set(chinese_names):
            if len(name) >= self.min_entity_length:
                entities.append({
                    "type": "person",
                    "value": name,
                    "confidence": 0.6,
                })

        # 项目名（## 标题或 [[wikilink]]）
        project_titles = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        for proj in project_titles:
            entities.append({
                "type": "project",
                "value": proj.strip(),
                "confidence": 0.8,
            })

        wikilinks = re.findall(r'\[\[([^\]|]+)\]\]', content)
        for link in wikilinks:
            entities.append({
                "type": "reference",
                "value": link.strip(),
                "confidence": 0.9,
            })

        # URL
        urls = re.findall(r'https?://[^\s\)>\]]+', content)
        for url in urls[:10]:  # 最多10个
            entities.append({
                "type": "url",
                "value": url,
                "confidence": 1.0,
            })

        return {
            "proposal_type": "entities",
            "status": "proposal",
            "entities": entities,
            "count": len(entities),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def extract_topics(self, content: str, title: str = "") -> dict:
        """提取主题 proposal。"""
        topics = set()

        # 从标题提取
        if title:
            for word in title.split():
                if len(word) >= 2:
                    topics.add(word)

        # 从 YAML frontmatter tags
        if content.startswith("---"):
            try:
                end = content.index("---", 3)
                yaml = content[3:end]
                for line in yaml.split("\n"):
                    if line.strip().startswith("tags:"):
                        tags_str = line.split(":", 1)[1].strip()
                        for tag in re.findall(r'"([^"]+)"|\'([^\']+)\'|([^\s,]+)', tags_str):
                            t = tag[0] or tag[1] or tag[2]
                            if t:
                                topics.add(t)
                        break
            except Exception:
                pass

        # 从 ## 标题提取
        for line in content.split("\n"):
            if line.startswith("## "):
                topic = line[3:].strip().split()[0] if line[3:].strip() else ""
                if topic:
                    topics.add(topic)

        return {
            "proposal_type": "topics",
            "status": "proposal",
            "topics": sorted(list(topics)),
            "count": len(topics),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# 单例
_pipeline = None


def get_pipeline() -> KnowledgePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = KnowledgePipeline()
    return _pipeline
