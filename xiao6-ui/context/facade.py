# -*- coding: utf-8 -*-
"""context.facade — Context 门面（R8-P4 恢复，衔接 Agent Planner）

恢复 P5.1 契约：Agent Runtime 的 Planner Context 唯一入口。
R8-P4 采用最小恢复：复用 Chat 同一套 Context 组装（memory.build_system_prompt，
含人格 / 系统提示 / ACI 预判 / 记忆块），不引入完整 Context Engine（其全量
models 与 ai_core.execution 的 BuildContext 契约冲突，超出本阶段范围）。

设计纪律（延续原 facade 注释）：
- 只读组装层：本模块不执行任何工具、不改任何系统状态。
- 单源组装：与 Chat 共享同一 memory.build_system_prompt，禁止第二套 Prompt Builder。
- 失败安全：任何异常返回 ""（调用方 agent_runtime._llm_dispatch 自行回退 legacy prompt），
  绝不阻断调度主链路。
"""

from __future__ import annotations

from typing import Optional


def build_context_prompt(user_text: str = "") -> str:
    """Chat 系统提示词入口（与 legacy 实现同源：memory.build_system_prompt）。"""
    try:
        import memory

        return memory.build_system_prompt(user_text or "")
    except Exception:
        return ""


def build_cognitive_context(
    goal_id: Optional[int] = None,
    task: Optional[dict] = None,
    mode: str = "plan",
    tier=None,
) -> str:
    """P5.1：Agent Runtime 的 Planner Context 唯一入口。

    复用 Chat 同一 Context 组装（memory.build_system_prompt），并附当前
    goal / task 即时上下文（只读拉取）。mode/tier 为契约占位参数（与原始
    签名兼容），本实现统一注册同一组上下文，不按 mode 分叉。

    Returns:
        Planner 上下文文本；任何异常返回 ""（调用方回退 legacy prompt）。
    """
    try:
        parts: list = []
        try:
            import memory

            base = memory.build_system_prompt("")
            if base:
                parts.append(base)
        except Exception:
            pass
        # goal 即时上下文（只读）
        if goal_id is not None:
            try:
                from goals import get_goal

                g = get_goal(goal_id)
                if g is not None:
                    parts.append(
                        f"[当前目标] #{g.id} {g.title}（状态 {g.status}，进度 {g.progress}%）"
                    )
            except Exception:
                pass
        # task 即时上下文（只读）
        if isinstance(task, dict):
            t = (task.get("title") or "").strip()
            if t:
                parts.append(f"[当前任务] {t}")
            steps = task.get("steps") or []
            if steps:
                parts.append("[子步骤] " + "；".join(str(s) for s in steps[:8]))
        return "\n".join(p for p in parts if p)
    except Exception as e:
        print(f"[facade] build_cognitive_context 构建失败（交由调用方回退）: {e}")
        return ""
