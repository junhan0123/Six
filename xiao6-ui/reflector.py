#!/usr/bin/env python3
"""小6 · 反思层（Reflector）—— 闭环后的经验沉淀（差异化竞争力）。

目标 / 任务结束后自动反思：完成度？遗漏？更好方案？是否更新知识库？
产出 Execution Report（成功 / 失败 / 经验），经验沉淀回 允许的存储
（记忆 / 规则 / 知识）。第一阶段仅写入被允许的、零密钥的本地存储。

纯标准库。
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

REPORT_DIR = os.path.join("data", "agent_reports")


def reflect(goal_id: int, executions: list, extra: Optional[dict] = None) -> dict:
    """对一次目标闭环做反思，返回 Execution Report（dict）。"""
    total = len(executions)
    ok = sum(1 for e in executions if e.get("ok"))
    blocked = sum(1 for e in executions if e.get("blocked"))
    rejected = sum(1 for e in executions if e.get("rejected"))
    failed = total - ok - blocked - rejected
    lessons = _distill(executions)
    report = {
        "goal_id": goal_id,
        "ts": time.time(),
        "summary": f"完成 {ok}/{total} 步；拦截 {blocked}，拒绝 {rejected}，失败 {failed}",
        "executions": executions,
        "lessons": lessons,
    }
    _persist(goal_id, report)
    _feed_memory(goal_id, report, lessons)
    return report


def _distill(executions: list) -> list:
    """从执行结果中提炼经验（规则 / 反例）。第一阶段用轻量启发式，不强制 LLM。"""
    lessons = []
    for e in executions:
        if e.get("blocked"):
            lessons.append(f"工具 {e.get('tool')} 被永久 / 危险拦截：{e.get('reason')}")
        elif e.get("rejected"):
            lessons.append(f"用户拒绝了 {e.get('tool')} 的执行（confirm 未通过）")
        elif not e.get("ok") and e.get("error"):
            lessons.append(f"任务执行出错：{e.get('error')}")
        elif e.get("ok"):
            lessons.append(f"成功执行：{e.get('tool')}")
    return lessons


def _persist(goal_id: int, report: dict) -> None:
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        with open(os.path.join(REPORT_DIR, f"goal_{goal_id}.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[reflector] 报告持久化失败: {e}")


def _feed_memory(goal_id: int, report: dict, lessons: list) -> None:
    """经验回灌到允许的存储。第一阶段：追加到本地知识库（add_knowledge，零密钥）。

    Order 4：透传 memory_id=f"mem{goal_id}"，使反思产出的 MEMORY_CREATED 与
    真实落库的 MEMORY_STORED/LINKED 共享同一 memoryId（连贯 Memory 生命周期）。
    """
    if not lessons:
        return
    try:
        from ai_core.execution import run as _execution_run
        from eventbus import publish_domain
        memory_id = f"mem{goal_id}"
        title = f"Agent 经验 #{goal_id}"
        # Order 4：反思蒸馏出 Memory 的瞬间，先发射 MEMORY_CREATED（早于真实落库的
        # MEMORY_STORED / MEMORY_LINKED，保证生命周期顺序 REFLECTING→CREATED→STORED→LINKED）。
        # 经 publish_domain 单一来源发射，与 knowledge.py 落库事件共享同一 memoryId。
        publish_domain("MEMORY_CREATED", {
            "memoryId": memory_id,
            "goalId": goal_id,
            "title": title,
            "lessonCount": len(lessons),
        }, source="reflector")
        text = "Agent 闭环经验（目标 #%d）：\n" % goal_id + "\n".join(f"- {l}" for l in lessons)
        # Phase 3：统一经 Execution.run（单一执行入口；行为等价于 execute_tool）
        # R8-P0：参数契约 run(task, context={"args": args})，add_knowledge 参数不得丢失
        _execution_run("add_knowledge", {"args": {
            "text": text,
            "title": title,
            "memory_id": memory_id,
        }})
    except Exception as e:
        print(f"[reflector] 经验回灌失败（非致命）: {e}")
