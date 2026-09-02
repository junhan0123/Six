---
id: experience-knowledge-as-files
type: experience
title: 知识即文件而非向量库
status: reviewed
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- experience
- knowledge
related_knowledge:
- concept-knowledge-as-files
---

曾评估 RAG / 嵌入 / 向量库方案，但违背 Local First 与可审计原则。最终采用 [[知识即文件]]：.md 为唯一事实源，Knowledge Runtime 做关键词检索与链接图，零向量、零数据库。检索质量靠良好的 frontmatter（id/type/tags/links）与 wikilink 网络保障。
