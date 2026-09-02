#!/usr/bin/env python3
"""小6 · Agent Runtime —— 目标驱动的编排状态机（核心新建）。

状态机：IDLE -> PLANNING -> EXECUTING -> REFLECTING -> (IDLE | PLANNING)
职责：编排已有能力，不做任何业务逻辑。
- PLANNING:   调 goals.plan_goal 拆解 Task
- EXECUTING:  每个 Task 经 policy_engine.evaluate 裁决后调 tools.execute_tool
- REFLECTING: 调 reflector.reflect 产出 Execution Report + 经验沉淀
经 EventBus 通信，跑后台线程，不阻塞对话主链路（conversation_loop）。

纯标准库 + 已有模块；由 FEATURE_AGENT_RUNTIME 门控（默认 off）。
"""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import date
from typing import Optional

import llm as _llm_mod
from llm import agnes_completion
from tools import TOOLS, execute_tool_calls

# 状态
IDLE, PLANNING, EXECUTING, REFLECTING = "IDLE", "PLANNING", "EXECUTING", "REFLECTING"

# 性能调优（P4）：蒸馏单次读取的对话历史上限（旧消息压缩，向后兼容）
_MAX_DISTILL_MESSAGES = 50


def _parse_date(s: str):
    """把 '2026-03-15' / '2026/3/15' / '2026年3月15日' 解析为 date，失败返回 None。"""
    if not s:
        return None
    import re as _re
    m = _re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


class AgentRuntime:
    # —— 测试注入 seam（instance-scoped，生产默认 None）——
    # 每个实例独立维护 completion_provider，避免跨实例状态污染
    _test_completion_response = None  # 保留向后兼容

    def __init__(self, completion_provider=None):
        # Instance-scoped completion provider:
        # - None (default): 生产路径，使用真实 Agnes LLM
        # - callable: 测试路径，使用确定性 mock
        self._completion_provider = completion_provider
        self.state = IDLE
        self._queue = []
        self._ql = threading.Lock()
        self._cv = threading.Condition(self._ql)
        self._thread = None
        self._running = False
        self._current = None
        self._last_report = None
        self._consecutive_failures = 0      # 连续失败计数（换工具用）
        self._MAX_RETRIES = 3               # 最大重试次数
        self._MAX_CONSECUTIVE_FAIL = 2      # 连续失败后清空队列
        self._MAX_STEPS = 16                # Phase 42 · Agent Loop 单轮最大执行步数上限
        # Phase 46 · 多轮 / 重规划上限（与 _MAX_STEPS 正交；均可用 config 覆盖）
        self._MAX_ROUNDS = 8                # 单目标总轮次上限
        self._MAX_REPLANS = 4               # 单目标动态重规划次数上限
        self._reservations = {}             # Phase 46 · Reservation：goal_id -> {reservation_id,revision,round_index}
        self._replans_used = 0             # Phase 46 · 已用重规划次数（供 _evaluate_round / _do_replan 读取）
        self._last_maintenance_date = None  # P12 每日记忆维护去重标记
        # —— Phase C · G2/G3 · 运行时级预算与深度（在 _run_goal 中按 config 覆盖）——
        self._call_budget = None            # ContextBudget 实例（None=未初始化，视作无限）
        self._max_depth = 4                 # 原生 Sub-Agent 嵌套深度上限（默认）

    # ---- 生命周期 ----
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="xiao6-agent-runtime", daemon=True)
        self._thread.start()
        self._publish_state("started")

    def stop(self):
        self._running = False
        with self._ql:
            self._cv.notify_all()

    # ---- 外部入口 ----
    def submit_goal(self, title: str, description: str = "", intent_id: Optional[str] = None) -> Optional[int]:
        from goals import create_goal
        g = create_goal(title=title, description=description, priority="high", horizon="short",
                        intent_id=intent_id)  # Order 5：携带 intentId 供 GOAL_CREATED 关联
        if not g:
            return None
        with self._ql:
            self._queue.append(g.id)
            self._cv.notify_all()
        self._publish_state("goal_submitted", goal_id=g.id)
        self._emit_agent_domain("AGENT_CREATED", g.id)  # Order 3：Agent 编排体随 Goal 创建
        self._emit_goal_domain("GOAL_STARTED", g.id)  # Order 2：运行时接管目标
        return g.id

    def run_chat_turn(self, messages: list, emit, user_text: str = "", tools=None,
                      temperature: float = 0.7, reasoning=None, allowed=None,
                      mode: str = "smart", goal_id=None) -> tuple:
        """Unified chat execution through AgentRuntime.

        这是 Chat → AgentRuntime 统一架构的唯一入口。
        所有 Chat 请求必须经过此方法，不得绕过。

        设计要点：
        - 真正统一执行：状态机 + Function Calling + Memory 蒸馏
        - 经过 AgentRuntime 状态机（IDLE → PLANNING → EXECUTING → IDLE）
        - 所有工具调用经过同一 Policy Gate（ai_core.execution.run）
        - 工具结果通过 EventBus 发布（供 SSE 消费）
        - 执行后自动蒸馏 Memory（与 AgentRuntime Goal 路径一致）

        Args:
            messages: 对话历史消息列表（已含 system prompt）
            emit: SSE 事件发射函数
            user_text: 用户原始输入文本（用于 Memory 蒸馏）
            tools: 可下发的工具 schema（默认全量 TOOLS）
            temperature: LLM 温度
            reasoning: 是否启用 reasoning
            allowed: 远程会话白名单
            mode: smart|expert
            goal_id: 关联的 Goal ID（可选，用于 Policy 上下文）

        Returns:
            (final_content, called_tools_set)
        """
        # 1. 状态转换：IDLE → PLANNING → EXECUTING
        prev_state = self.state
        self.state = PLANNING
        self._publish_state(PLANNING)

        try:
            # 2. 轻量 Planner：判断任务复杂度
            plan = self._plan_chat_turn(user_text, tools)

            # 3. 执行
            self.state = EXECUTING
            self._publish_state(EXECUTING)

            content, called = self._execute_chat_turn(
                messages, emit, plan, temperature, reasoning,
                allowed, mode, goal_id
            )

            # 4. 发布执行完成事件
            self._emit_agent_domain("AGENT_COMPLETED", goal_id)

            # 5. 自动 Memory 蒸馏（统一入口）
            if user_text:
                self._distill_memory(session_id="chat", messages=[{"role": "user", "content": user_text}])

            return content, called

        except Exception as e:
            print(f"[runtime] Chat turn execution failed: {e}")
            self._emit_agent_domain("AGENT_FAILED", goal_id, error=str(e))
            emit({"error": f"执行失败：{e}"})
            return f"（抱歉，处理出错：{e}）", set()

        finally:
            # 6. 状态恢复：EXECUTING → IDLE
            self.state = IDLE
            self._publish_state("idle")
            # 恢复前一个状态（如果有的话）
            if prev_state and prev_state != IDLE:
                self.state = prev_state

    def _plan_chat_turn(self, user_text: str, tools):
        """轻量 Planner：判断任务复杂度。"""
        simple_patterns = [
            r"^(你好|您好|嗨|hello|hi|在吗|谢谢|你好呀)",
            r"^(你是谁|介绍一下自己|自我介绍)",
            r"^(几点了|现在时间|今天星期)",
        ]
        for pattern in simple_patterns:
            if re.match(pattern, user_text.strip()):
                return {"type": "direct", "tools": [], "steps": 1}
        return {"type": "function_calling", "tools": tools or TOOLS, "steps": 5}

    def _execute_chat_turn(self, messages, emit, plan, temperature, reasoning,
                           allowed, mode, goal_id):
        """执行 Chat turn（内部方法）。"""
        if plan["type"] == "direct" and not plan["tools"]:
            # 简单聊天：不下发工具
            return self._run_fc_loop(messages, emit, tools=[],
                                      temperature=temperature, reasoning=reasoning,
                                      allowed=allowed, mode=mode, goal_id=goal_id)
        else:
            # 复杂任务：使用 function calling
            return self._run_fc_loop(messages, emit, tools=plan["tools"],
                                      temperature=temperature, reasoning=reasoning,
                                      allowed=allowed, mode=mode, goal_id=goal_id)

    def _run_fc_loop(self, messages, emit, tools=None, temperature=0.7,
                     reasoning=None, allowed=None, mode="smart", goal_id=None):
        """Internal LLM function calling loop.

        这是 Chat 执行的统一引擎，不再暴露为公共 API。
        所有 Chat 请求通过 run_chat_turn() → _run_fc_loop() 执行。
        """
        from tools import TOOLS, execute_tool_calls

        MAX_ROUNDS = 5
        called = set()
        effective_tools = tools if tools is not None else TOOLS

        for _ in range(MAX_ROUNDS):
            try:
                # —— 测试注入 seam：如果设置了 instance-scoped provider，使用 mock 而非真实 LLM ——
                if self._completion_provider is not None:
                    # Test path: use mock provider
                    resp = self._completion_provider()
                    if hasattr(resp, 'read'):
                        data = json.loads(resp.read().decode("utf-8"))
                    else:
                        data = json.loads(resp)
                else:
                    # Production path: use real Agnes LLM
                    with agnes_completion(
                        messages, tools=effective_tools, stream=False,
                        timeout=90, temperature=temperature, reasoning=reasoning
                    ) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                emit({"error": f"核心调用失败：{e}"})
                return ("（抱歉，核心暂时无法响应）"), called

            msg = (data.get("choices") or [{}])[0].get("message", {})
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []

            for tc in tool_calls:
                fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                called.add(fn.get("name", ""))

            assistant_msg = {"role": "assistant", "content": content or None}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            if not tool_calls:
                return content, called  # 无工具调用 = 最终自然语言回复

            tool_msgs, events = execute_tool_calls(
                tool_calls, allowed, mode=mode, goal_id=goal_id
            )
            for kind, name, payload in events:
                if kind == "start":
                    emit({"xiao6_event": "tool_start", "tool": name, "args": payload})
                else:
                    emit({"xiao6_event": "tool_end", "tool": name, "result": payload})
            messages.extend(tool_msgs)

        # 超轮次保护
        try:
            with agnes_completion(
                messages, tools=[], stream=False, timeout=90, temperature=temperature
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return (data.get("choices") or [{}])[0].get("message", {}).get("content") or "（抱歉，处理超时）", called
        except Exception as e:
            emit({"error": f"收尾调用失败：{e}"})
            return ("（抱歉，处理超时）"), called

    def _distill_memory(self, session_id="agent", messages=None):
        """统一 Memory 蒸馏入口（Chat 和 Goal 共享）。

        直接从 chat_log 拉最近若干轮对话（与 goals.py 解耦，不破坏其事件契约），
        经 memory_distiller.distill 提取 habit/preference/important_event/relationship，
        并顺带沉淀一条 ConversationMemory（P12-3）。
        若已传入 messages（Chat 路径），则直接使用；否则从 DB 加载（Goal/定时路径）。
        """
        try:
            import config
            if not getattr(config, "FEATURE_MEMORY_DISTILL", False):
                return
            if messages is None:
                messages = self._load_recent_chat()
            if not messages:
                return
            from memory_distiller import distill
            distill(session_id, messages)
            self._record_conversation_memory(messages)
        except Exception:
            pass

    def get_state(self) -> dict:
        return {
            "state": self.state,
            "current_goal": self._current,
            "queue": list(self._queue),
            "running": self._running,
            "last_report": self._last_report,
            "consecutive_failures": self._consecutive_failures,
        }

    # ---- 主循环 ----
    def _loop(self):
        while self._running:
            with self._ql:
                while self._running and not self._queue:
                    self._cv.wait(timeout=1.0)
                if not self._running:
                    break
                self._maybe_daily_maintenance()  # P12 每日一次记忆维护（蒸馏 + 重要日期），门控
                goal_id = self._queue.pop(0)
            try:
                self._run_goal(goal_id)
            except Exception as e:
                print(f"[runtime] 目标 #{goal_id} 执行异常: {e}")
                self._set_goal_status(goal_id, "active")
                self._emit_agent_domain("AGENT_FAILED", goal_id, error=str(e))  # Order 3
                self._emit_goal_domain("GOAL_FAILED", goal_id, error=str(e))  # Order 2
            finally:
                self.state = IDLE
                self._current = None
                self._publish_state("idle")

    def _observe(self, goal_id: int, res: dict) -> None:
        """Phase 42 · Observation：把单次任务执行结果落入运行态观察缓冲。

        这是 Agent Loop 的 OBSERVE 环节——SELECT→EXECUTE 的结果在此被记录，
        供 REFLECT（reflector）蒸馏为 lessons / 回灌 Memory。仅内存缓冲，不修改任何系统状态。
        """
        try:
            if not hasattr(self, "_observations"):
                self._observations = {}
            self._observations.setdefault(goal_id, []).append({
                "tool": res.get("tool"),
                "ok": res.get("ok"),
                "category": res.get("category"),
                "blocked": bool(res.get("blocked", False)),
                "result_snippet": str(res.get("result") or res.get("error") or "")[:300],
            })
        except Exception:
            pass

    # ============ Phase 46 · 多轮 / 动态重规划 / Plan Gate / Reservation ============

    def _run_goal(self, goal_id: int, depth: int = 0):
        """Phase 46 · Goal 编排状态机（多轮驱动 + 动态重规划）。

        轮次 FSM：none→planned→running→observing→evaluating→{COMPLETE|CONTINUE|REPLAN|BLOCK|FAIL}
        严格收敛到 Goal 四态终态之一（completed / failed / max_steps_exceeded / blocked_by_policy）；
        round_status 永不取 'completed'（Round 永不创造第五个终态）。

        纪律红线（来自设计 §四/§五/§七/§十六/§十七）：
        - 唯一 Round Driver 是 _run_goal；revision 仅由 _do_replan 经 goals.bump_revision 递增。
        - REPLAN 绝不删除任何 Task；新执行路径以「新建 Task 行（新身份）」表达，旧 Task 惰性保留，
          由 note 中的 revision 标记 + goals.revision 过滤区分。
        - 零新增 EventBus 域事件：仅扩展 GOAL_RUNNING payload + 经 publish_domain 重发 GOAL_PLANNED。
        - _MAX_ROUNDS / _MAX_REPLANS / _MAX_STEPS 三者正交；任一耗尽 → max_steps_exceeded。
        """
        self._current = goal_id
        # Phase 46.2 · 工具基线修复（STEP 2）：complete_task 是 Goal 完成信号，
        # 在本 Goal 范围内预批准，避免真实 E2E 在无头/无人审批环境下因
        # policy_engine.request_approval 模态挂起（ev.wait(timeout=300)）而阻塞。
        # 仅 Goal 级（per-goal 隔离）、仅 complete_task，保留 policy_engine 真实裁决通道，
        # 不全局关闭 confirm、不新建第二套权限系统。
        try:
            from policy_engine import pre_approve_tools as _pre_approve_tools
            _pre_approve_tools(goal_id, ["complete_task"])
        except Exception:
            pass
        import config as _cfg
        self._MAX_ROUNDS = getattr(_cfg, "AGENT_MAX_ROUNDS", 8)
        self._MAX_REPLANS = getattr(_cfg, "AGENT_MAX_REPLANS", 4)
        # —— Phase C · G3 · 原生 Sub-Agent 嵌套深度闸门（FAIL CLOSED）——
        self._max_depth = getattr(_cfg, "AGENT_MAX_DEPTH", 4)
        # —— Phase C · G2 · 能力调用预算（复用 ContextBudget 单预算模块；0/None=无限）——
        from context.budget import ContextBudget
        _cap_calls = getattr(_cfg, "AGENT_TOTAL_CAPABILITY_CALLS", 0) or None
        self._call_budget = ContextBudget(max_calls=_cap_calls)
        # —— Phase C · G3 · 深度超限 → 目标直接失败（FAIL CLOSED）——
        if not self._within_depth(depth):
            self._set_goal_status(goal_id, "failed")
            self._emit_agent_domain("AGENT_FAILED", goal_id, error="depth_exceeded")
            self._emit_goal_domain("GOAL_FAILED", goal_id, error="depth_exceeded")
            return
        from goals import (
            plan_goal, get_revision, set_round, get_goal, task_revision_of,
        )
        from tasks import get_tasks, update_task_step

        self._replans_used = 0
        round_index = 0
        final_outcome = None      # 四态终态；None = 继续轮转
        executions_all = []

        # ---------- PLANNING（首次规划，revision 不变）----------
        self.state = PLANNING
        self._set_goal_status(goal_id, "active")
        self._publish_state(PLANNING, goal_id=goal_id)
        self._emit_agent_domain("AGENT_STARTED", goal_id)    # Order 3
        self._emit_agent_domain("AGENT_THINKING", goal_id)   # Order 3：规划中
        task_ids = plan_goal(goal_id)
        if not task_ids:
            print(f"[runtime] 目标 #{goal_id} 拆解为空，跳过执行")
            self._set_goal_status(goal_id, "completed", progress=100)
            self._emit_agent_domain("AGENT_COMPLETED", goal_id)
            self._emit_goal_domain("GOAL_COMPLETED", goal_id)
            self._notify_goal_done(goal_id, "目标拆解为空")
            return
        set_round(goal_id, 1, "planned")
        self._emit_goal_planned(goal_id)   # 首次发射 GOAL_PLANNED（合法既有事件）
        rows = get_tasks(goal_id=goal_id, limit=100)
        for tid in task_ids:
            t = next((x for x in rows if x["id"] == tid), None) or {}
            self._emit_task_domain("TASK_CREATED", goal_id, tid, title=t.get("title"))

        # ---------- ROUND LOOP ----------
        while final_outcome is None:
            round_index += 1
            if round_index > self._MAX_ROUNDS:
                final_outcome = "max_steps_exceeded"
                break

            # Reservation（防旧结果覆盖）：canonical revision + 内存 dict + 最佳努力 Checkpoint 快照
            reservation = self._reserve_round(goal_id, get_revision(goal_id), round_index)

            # ---------- EXECUTING（本轮仅执行「当前 revision 且仍 open」的任务）----------
            self.state = EXECUTING
            set_round(goal_id, round_index, "running")
            self._publish_state(EXECUTING, goal_id=goal_id, round_index=round_index, tasks=task_ids)
            self._emit_goal_domain("GOAL_RUNNING", goal_id, round_index=round_index,
                                   revision=get_revision(goal_id))  # Order 2：扩展 payload
            self._emit_agent_domain("AGENT_WORKING", goal_id)       # Order 3：执行任务中

            # Plan Gate：每轮对所有计划内工具调 policy.evaluate（confirm 经 approve_in_goal 去重）
            self._plan_gate(goal_id, task_ids)

            cur_rev = get_revision(goal_id)
            rows = get_tasks(goal_id=goal_id, limit=100)
            round_tasks = [
                t for t in rows
                if t["id"] in set(task_ids)
                and task_revision_of(t.get("note")) in (None, cur_rev)
                and t.get("status") == "open"
            ]
            executions = []
            step_count = 0
            max_steps_exceeded = False
            total = max(len(task_ids), 1)
            for t in round_tasks:
                # —— Phase 42 Agent Loop：_MAX_STEPS 为「单轮」执行步数硬边界 ——
                if step_count >= self._MAX_STEPS:
                    max_steps_exceeded = True
                    break
                tid = t["id"]
                self._emit_task_domain("TASK_STARTED", goal_id, tid)
                self._emit_task_domain("TASK_RUNNING", goal_id, tid)
                try:
                    res = self._execute_task(goal_id, t)
                except Exception as e:
                    res = {"task_id": tid, "ok": False, "error": str(e)}
                step_count += 1
                executions.append(res)
                # 持久化 task 状态（供跨轮 EVALUATE 读取；用 update_task_step 避免 recalc_progress 副作用）
                if res.get("ok"):
                    update_task_step(tid, status="done")
                    self._emit_task_domain("TASK_COMPLETED", goal_id, tid)
                else:
                    update_task_step(tid, status="failed")
                    self._emit_task_domain("TASK_FAILED", goal_id, tid,
                                           error=res.get("error"), category=res.get("category"))
                # —— OBSERVE：把真实执行结果落入观察缓冲（供 REFLECT 蒸馏）——
                self._observe(goal_id, res)
            executions_all.extend(executions)
            # 进度反馈（仅展示，不触发自动终态）
            _done = sum(1 for e in executions if e.get("ok"))
            self._set_goal_progress(goal_id, min(100, int(_done / total * 100)))

            # ---------- OBSERVING -> EVALUATING ----------
            set_round(goal_id, round_index, "observing")
            set_round(goal_id, round_index, "evaluating")
            round_outcome = self._evaluate_round(goal_id, executions, max_steps_exceeded)
            set_round(goal_id, round_index, round_outcome)  # COMPLETE/CONTINUE/REPLAN/BLOCK/FAIL

            # COMMIT reservation（compare-and-commit；stale 拒绝覆盖）
            if not self._commit_round_advance(goal_id, reservation):
                final_outcome = "max_steps_exceeded"
                break

            # ---------- 依 round_outcome 收敛 ----------
            if round_outcome == "COMPLETE":
                final_outcome = "completed"
            elif round_outcome == "BLOCK":
                final_outcome = "blocked_by_policy"
            elif round_outcome == "FAIL":
                final_outcome = "failed"
            elif round_outcome == "CONTINUE":
                continue   # 同 revision 下一轮继续（task_ids / revision 不变）
            elif round_outcome == "REPLAN":
                if self._replans_used >= self._MAX_REPLANS:
                    final_outcome = "max_steps_exceeded"
                    break
                new_ids = self._do_replan(goal_id)   # 唯一 revision bump 拥有者
                if not new_ids:
                    final_outcome = "failed"
                    break
                task_ids = new_ids
                continue   # 进入新 revision 的下一轮

        # ---------- P5-PRE-REQ-01：连续失败计数 + 阈值队列清空（防雪崩）----------
        # 计数语义（以 Goal 为单位，复用既有 _queue 唯一权威）：
        #   - Goal 整体失败（非 completed）→ _consecutive_failures += 1；
        #   - Goal 完成 → _consecutive_failures = 0（与 _execute_task 成功重置语义一致）；
        #   - 达 _MAX_CONSECUTIVE_FAIL 阈值 → 清空执行队列，阻断连续失败雪崩（进入 _loop 下一轮前停止后续 Goal）。
        # 复用 P3 既有 _queue（不新建第二套 Recovery）；重规划已在轮循环内复用 _do_replan。
        if final_outcome == "completed":
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._MAX_CONSECUTIVE_FAIL:
                self._queue.clear()

        # ---------- REFLECTING + 四态终态 ----------
        self.state = REFLECTING
        self._publish_state(REFLECTING, goal_id=goal_id)
        self._emit_agent_domain("AGENT_THINKING", goal_id)   # Order 3：反思中
        self._emit_reflect_domain("REFLECTING", goal_id)      # Order 4：反思阶段入口事件
        from reflector import reflect
        report = reflect(goal_id, executions_all)
        self._last_report = report
        self._publish_state("reflected", goal_id=goal_id, report=report)

        _OUTCOME_STATUS = {
            "completed": "completed",
            "failed": "failed",
            "max_steps_exceeded": "max_steps_exceeded",
            "blocked_by_policy": "blocked_by_policy",
        }
        final_status = _OUTCOME_STATUS.get(final_outcome, "failed")
        self._set_goal_status(
            goal_id, final_status, progress=100 if final_outcome == "completed" else None)
        self._emit_agent_domain("AGENT_COMPLETED", goal_id)   # Order 3：编排体完成
        if final_outcome == "completed":
            self._emit_goal_domain("GOAL_COMPLETED", goal_id)  # Order 2：目标执行完成
        else:
            self._emit_goal_domain("GOAL_FAILED", goal_id)    # Order 2：目标执行未完成
        summary = (
            f"轮次={round_index} 重规划={self._replans_used} 终态={final_outcome}"
            f"（完成 {sum(1 for e in executions_all if e.get('ok'))}/{len(executions_all)} 步）"
        )
        self._notify_goal_done(goal_id, summary)
        self._release_reservation(goal_id)

    # ---- Phase 46 · Round 辅助 ----

    def _reserve_round(self, goal_id, revision, round_index) -> dict:
        """Reservation：为一次 round 推进建立 reservation（uuid4 防重放）。

        权威守卫是 canonical goals.revision（compare-and-commit 在 _commit_round_advance 校验）；
        内存 dict 记录 reservation_id 供陈旧检测；最佳努力把快照写入归属 session 的
        Checkpoint.runtime_ref（无 session 时跳过，不影响主链路）。
        """
        import uuid
        reservation_id = uuid.uuid4().hex
        self._reservations[goal_id] = {
            "reservation_id": reservation_id,
            "revision": revision,
            "round_index": round_index,
        }
        # 最佳努力：把快照写入归属 session 的 Checkpoint.runtime_ref
        try:
            from db import db_conn
            conn = db_conn()
            row = conn.execute("SELECT session_id FROM goals WHERE id=?", (goal_id,)).fetchone()
            conn.close()
            sid = row[0] if row else None
            if sid:
                from session import create_checkpoint
                create_checkpoint(
                    sid, goal_id=goal_id,
                    runtime_ref=json.dumps(
                        {"reservation_id": reservation_id, "revision": revision,
                         "round_index": round_index}, ensure_ascii=False),
                    label=f"reservation@goal{goal_id}:r{revision}:{round_index}",
                )
        except Exception:
            pass
        return self._reservations[goal_id]

    def _commit_round_advance(self, goal_id, reservation) -> bool:
        """compare-and-commit：canonical goals.revision 必须等于 reservation 快照，
        否则视为陈旧写入（被其他路径改动），拒绝提交以防覆盖。"""
        try:
            from goals import get_revision
            if not reservation:
                return False
            return get_revision(goal_id) == reservation.get("revision")
        except Exception:
            return False

    def _release_reservation(self, goal_id) -> None:
        self._reservations.pop(goal_id, None)

    def _plan_gate(self, goal_id, task_ids) -> None:
        """Phase 46 · Plan Gate：每轮对所有计划内工具调 policy.evaluate()
        （confirm 工具经 policy.approve_in_goal 预批准，执行阶段命中缓存不重复弹窗）。
        完全复用既有 policy_engine，不创建第二套权限系统。
        """
        try:
            from policy_engine import evaluate as _evaluate, request_approval as _request, approve_in_goal as _approve
            from goals import get_revision, task_revision_of
            from tasks import get_tasks
            cur_rev = get_revision(goal_id)
            rows = get_tasks(goal_id=goal_id, limit=100)
            seen = set()
            for t in rows:
                if t["id"] not in set(task_ids):
                    continue
                if task_revision_of(t.get("note")) not in (None, cur_rev):
                    continue
                if t.get("status") != "open":
                    continue
                tool, args = self._resolve_dispatch(t)
                if not tool or tool in seen:
                    continue
                seen.add(tool)
                dec = _evaluate(tool, args, goal_id=goal_id, default_deny=True)
                if dec.get("decision") == "confirm":
                    d = _request(tool, args,
                                 summary=f"计划步骤需执行 {tool}（目标 #{goal_id}）",
                                 goal_id=goal_id, default_deny=True)
                    if d == "approve":
                        _approve(goal_id, tool)
        except Exception as e:
            print(f"[runtime] Plan Gate 异常（已忽略）: {e}")

    def _evaluate_round(self, goal_id, executions, max_steps_exceeded) -> str:
        """Phase 46 · 诚实轮次评估（基于真实 task 状态，绝不编造）。

        返回 Round FSM 中间态之一：COMPLETE / CONTINUE / REPLAN / BLOCK / FAIL。
        - COMPLETE：当前 revision 全部 Task 完成。
        - BLOCK：   全部失败且均为策略拒绝（blocked）。
        - REPLAN：  存在非策略失败的 Task 且重规划预算未耗尽（交由 _do_replan 换路径）。
        - FAIL：    存在非策略失败且重规划预算耗尽。
        - CONTINUE：仍有 open 任务（如 _MAX_STEPS 截断）→ 同 revision 下一轮继续。
        """
        from goals import get_revision, task_revision_of
        from tasks import get_tasks
        cur_rev = get_revision(goal_id)
        revision_tasks = [
            t for t in get_tasks(goal_id=goal_id, limit=100)
            if task_revision_of(t.get("note")) in (None, cur_rev)
        ]
        done = [t for t in revision_tasks if t.get("status") == "done"]
        failed = [t for t in revision_tasks if t.get("status") == "failed"]
        open_ = [t for t in revision_tasks if t.get("status") in ("open", "running", "paused")]
        blocked = [e for e in executions if e.get("blocked")]

        if revision_tasks and len(done) == len(revision_tasks):
            return "COMPLETE"
        if blocked and len(done) == 0:
            return "BLOCK"
        if failed:
            # 失败：交给轮循环依 _MAX_REPLANS 预算决定 REPLAN 或 max_steps_exceeded
            return "REPLAN"
        if open_:
            return "CONTINUE"
        return "FAIL"

    def _do_replan(self, goal_id) -> list:
        """Phase 46 · 动态重规划（唯一合法递增 revision 的入口）。

        纪律：
        - 经 goals.bump_revision 递增 revision（plan_goal 内部绝不 bump）。
        - 经 plan_goal(replan=True) 创建新 Task 行（新身份），旧 Task 全部惰性保留（绝不删除）。
        - 重发 GOAL_PLANNED；重置 round 状态为 planned。
        返回新 Task id 列表；规划失败返回 []。
        """
        from goals import bump_revision, plan_goal, set_round, get_goal
        from tasks import get_tasks
        new_rev = bump_revision(goal_id)          # 唯一 revision bump 拥有者
        self._replans_used += 1
        new_ids = plan_goal(goal_id, replan=True)  # 保留旧 Task，新建本轮路径
        set_round(goal_id, 1, "planned")
        self._emit_goal_planned(goal_id)           # 重发 GOAL_PLANNED（合法既有事件）
        if new_ids:
            rows = get_tasks(goal_id=goal_id, limit=100)
            for tid in new_ids:
                t = next((x for x in rows if x["id"] == tid), None) or {}
                self._emit_task_domain("TASK_CREATED", goal_id, tid, title=t.get("title"))
        return new_ids

    def _emit_goal_planned(self, goal_id: int) -> None:
        """Phase 46 · 重发 GOAL_PLANNED（设计 §十六允许：复用既有已注册域事件，零新增）。

        _emit_goal_domain 仅放行 4 个名，故此处直接用 publish_domain 发射 GOAL_PLANNED。
        """
        try:
            from eventbus import publish_domain
            from goals import get_goal
            g = get_goal(goal_id)
            if not g:
                return
            payload = {
                "goalId": g.id,
                "title": g.title,
                "revision": g.revision,
                "roundIndex": g.round_index,
                "status": g.status,
                "priority": g.priority,
                "horizon": g.horizon,
            }
            publish_domain("GOAL_PLANNED", payload, source="agent_runtime")
        except Exception as e:
            print(f"[runtime] GOAL_PLANNED 发布失败（已忽略）: {e}")

    def _execute_task(self, goal_id: int, task) -> dict:
        if not task:
            return {"ok": False, "error": "no task"}
        tool, args = self._resolve_dispatch(task)
        if not tool:
            return {"task_id": task.get("id"), "ok": False, "error": "no tool resolved", "title": task.get("title")}
        # —— Phase C · G2 · 能力调用预算闸门（FAIL CLOSED，复用 ContextBudget 单预算模块）——
        # 任一执行（skill / mcp / computer / tool）均消耗一次额度；耗尽即拒。
        if self._call_budget is not None and not self._call_budget.consume_call():
            return {"task_id": task.get("id"), "ok": False, "blocked": True,
                    "reason": "capability call budget exhausted",
                    "tool": tool, "category": "budget_exhausted"}
        # —— Phase C · G1 · 原生 Skill 句柄路由（skill:<name> 经单一 execute_tool，无第二执行器）——
        if isinstance(tool, str) and tool.startswith("skill:"):
            return self._execute_skill_task(goal_id, task, tool, args)
        # —— Phase 42 · 外部 MCP 能力路由（单一 policy 闸门，经此处统一处理）——
        # 外部能力 id 形如 external.mcp.<server>.<tool>；绝不在此直调 MCP Host，
        # 一律经 capability_os.execute_capability（policy_engine 单向控制，§十一）。
        if self._is_external_mcp(tool):
            return self._execute_mcp_task(goal_id, task, tool, args)
        # —— Phase 7 Order 4：电脑能力路由（Agent → Task → ComputerAction → PermissionGuard → Executor）——
        # 解析出的工具若是已注册的 Computer Capability，则委托 PermissionGuard 闭环执行；
        # Agent / Runtime 不直接构造 ComputerAction、不直调 executor（纪律红线），只透传
        # capability / target / parameters，由 guard.plan 构造、guard.run 执行。
        try:
            from capability_os.registry import is_known
            if is_known(tool):
                return self._execute_computer_task(goal_id, task, tool, args)
        except Exception:
            pass
        # Phase 3：权限经统一 ExecutionPolicy 门面（委托既有 PolicyEngine，无第二套权限）
        from ai_core.execution.policy import ExecutionPolicy
        from ai_core.execution import run as _execution_run
        from ai_core.execution import trace as _trace
        policy = ExecutionPolicy.get()
        task_id = task.get("id")
        step_id = str(task.get("step") or task_id or "")
        for attempt in range(self._MAX_RETRIES + 1):
            dec = policy.evaluate(tool, args, goal_id=goal_id, default_deny=True)
            if dec["decision"] == "block":
                _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                               tool_name=tool, args=args, start_time=time.time(),
                               end_time=time.time(), status=_trace.STATUS_BLOCKED,
                               error=dec["reason"], recovery_action=_trace.RECOVERY_POLICY_BLOCKED,
                               attempt=attempt)
                return {"task_id": task_id, "ok": False, "blocked": True, "reason": dec["reason"], "tool": tool}
            if dec["decision"] == "confirm":
                self._emit_agent_domain("AGENT_WAITING", goal_id, taskId=task_id)  # Order 3：等待用户确认
                d = policy.request_approval(tool, args, summary=f"任务「{task.get('title')}」需执行 {tool}", goal_id=goal_id, default_deny=True)
                if d != "approve":
                    _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                                   tool_name=tool, args=args, start_time=time.time(),
                                   end_time=time.time(), status=_trace.STATUS_REJECTED,
                                   error=f"approval {d}", recovery_action=_trace.RECOVERY_FAIL_CLOSED,
                                   attempt=attempt)
                    return {"task_id": task_id, "ok": False, "rejected": True, "decision": d, "tool": tool}
            _t0 = time.time()
            try:
                # Phase 3：统一经 Execution.run（单一执行入口；行为等价于 execute_tool）
                # R8-P0：参数契约 run(task, context={"args": args})，工具参数不得丢失
                # R8-P1：透传 task_id / step_id 供 Execution Trace 串联
                result = _execution_run(tool, {"args": args, "goal_id": goal_id,
                                                "task_id": task_id, "step_id": step_id})
            except Exception as e:
                # 运行核心级异常（基础设施/策略内核崩溃）——原异常对象分类保真
                category = self._classify_error(e, tool)
                err_msg = str(e)
            else:
                # —— R8-P2 Failure Truthfulness ——
                # run() 返回 success=False（工具异常 / 未知工具 / 权限拒绝 / 执行失败 /
                # timeout 全部落在失败串或 error 字段）必须如实进入失败/恢复路由，
                # 严禁不检查 success 标志而把失败任务记为成功。
                if isinstance(result, dict) and result.get("success") is False:
                    err_msg = result.get("error") or result.get("result") or "execution failed"
                    category = self._classify_error(RuntimeError(str(err_msg)), tool)
                else:
                    self._consecutive_failures = 0  # 成功重置
                    return {"task_id": task_id, "ok": True, "tool": tool, "args": args, "result": str(result)[:2000]}
            # —— Recovery Router（统一处理 run 级异常与 run 返回的失败）——
            if attempt < self._MAX_RETRIES:
                if category == "network":
                    time.sleep(0.1 * (attempt + 1))  # 短退避
                    _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                                   tool_name=tool, args=args, start_time=_t0, end_time=time.time(),
                                   status=_trace.STATUS_FAILED, error=err_msg,
                                   recovery_action=_trace.RECOVERY_RETRY_BACKOFF, attempt=attempt)
                    continue
                if category == "file":
                    _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                                   tool_name=tool, args=args, start_time=_t0, end_time=time.time(),
                                   status=_trace.STATUS_FAILED, error=err_msg,
                                   recovery_action=_trace.RECOVERY_RETRY_ALTERNATIVE, attempt=attempt)
                    tool, args = self._try_alternative_tool(task, excluded=tool)
                    if tool:
                        continue
                    # 无替代工具，标记并退出
                    return {"task_id": task_id, "ok": False, "error": str(err_msg)[:500], "tool": tool,
                            "category": category, "attempts": attempt + 1}
                # unknown/permission/tool_missing/timeout 等：直接标记，不重试（避免无意义等待）
                _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                               tool_name=tool, args=args, start_time=_t0, end_time=time.time(),
                               status=_trace.STATUS_FAILED, error=err_msg,
                               recovery_action=_trace.RECOVERY_FAIL_CLOSED, attempt=attempt)
                return {"task_id": task_id, "ok": False, "error": str(err_msg)[:500], "tool": tool,
                        "category": category, "attempts": attempt + 1}
            # 重试耗尽
            _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                           tool_name=tool, args=args, start_time=_t0, end_time=time.time(),
                           status=_trace.STATUS_FAILED, error=err_msg,
                           recovery_action=_trace.RECOVERY_FAIL_CLOSED, attempt=attempt)
            return {"task_id": task_id, "ok": False, "error": str(err_msg)[:500], "tool": tool,
                    "category": category, "attempts": attempt + 1}
        return {"task_id": task_id, "ok": False, "error": "未知错误", "tool": tool}

    def _execute_computer_task(self, goal_id: int, task, capability: str, parameters) -> dict:
        """Phase 7 Order 4：电脑能力闭环执行（Computer Layer 是能力，不是第二个 Agent）。

        链路（严格，全部委托 PermissionGuard 单例）：
            Task
              ↓ 本方法仅透传 capability / target / parameters
            guard.plan(...)            → 构造 ComputerAction + 发布 COMPUTER_ACTION_PLANNED
              ↓
            guard.run(...)             → Policy Engine 裁决（decide：auto|confirm|block|deny）
              ↓ （MEDIUM → request_approval 既有模态通道，复用 Policy Engine，无第二权限系统）
            computer_executor.execute  → 发布 COMPUTER_ACTION_CALLED / DONE
              ↓
            VerificationLayer.verify   → 发布 COMPUTER_ACTION_VERIFIED / UNVERIFIED

        纪律红线：
        - Agent / Runtime 不拥有 ComputerAction 构造权（guard.plan 内部构造）。
        - Agent / Runtime 不直调 executor（guard.run 内部调用，执行器唯一入口）。
        - confirm 流程 100% 复用既有 policy_engine.request_approval 模态通道。
        """
        task_id = task.get("id") if isinstance(task, dict) else None
        title = (task.get("title") if isinstance(task, dict) else None) or ""
        params = parameters if isinstance(parameters, dict) else {}
        target = params.get("target", "") or ""
        try:
            from capability_os.registry import risk_of
            from permission_guard import guard
            # MEDIUM（确认类）能力：先发 AGENT_WAITING，使 Agent 编排态反映“等待批准”
            # （Phase 7 Order 4 已注册实现能力中 MEDIUM ⟺ confirm，LOW ⟺ auto，确定性映射）
            if risk_of(capability) == "MEDIUM":
                self._emit_agent_domain("AGENT_WAITING", goal_id, taskId=task_id, capability=capability)
            # 1) 规划：委托 Guard 构造 ComputerAction（Agent 不直构）
            action = guard.plan(capability, target=target, parameters=params, goal_id=goal_id)
            action_id = action.actionId
            # 2) 执行 + 验证（Guard 内部走 Policy Engine → Executor → Verification）
            action = guard.run(action, goal_id=goal_id, default_deny=True)
        except Exception as e:
            return {
                "task_id": task_id, "ok": False,
                "error": f"computer_action_error: {e}",
                "tool": capability, "title": title, "category": "computer",
            }
        verified = bool(getattr(action, "verified", False))
        ok = action.status == "done"  # 执行成功即任务完成；验证仅复核（VERIFIED/UNVERIFIED 不阻断完成态）
        res = {
            "task_id": task_id,
            "ok": ok,
            "tool": capability,
            "capability": capability,
            "action_id": action_id,
            "status": action.status,
            "verified": verified,
            "result": str(getattr(action, "result", None))[:2000],
        }
        if not ok:
            res["category"] = "computer"
            res["error"] = getattr(action, "decisionReason", None) or f"computer action {action.status}"
        return res

    @staticmethod
    def _is_external_mcp(tool: str) -> bool:
        """能力 id 是否为外部 MCP 能力（external.mcp.*）。"""
        return isinstance(tool, str) and tool.startswith("external.mcp.")

    def _execute_mcp_task(self, goal_id: int, task, cap_id: str, args) -> dict:
        """Phase 42 · 外部 MCP 能力执行（单一 policy 闸门，绝不直调 MCP Host）。

        链路（严格，无第二套执行/权限系统）：
            capability_os.execute_capability(cap_id, args, auto_approve=True, goal_id)
              → mcp_host.executor._authorize（policy_engine.evaluate(default_deny=True)）
              → MCPExecutor → 真实外部工具（Playwright / 其他受信任 MCP）。

        non-interactive 场景由 mcp_host 如实记录 "auto_approved(non-interactive demo/test)"，
        不伪造已批准（§二十 NO FAKING）。
        """
        task_id = task.get("id") if isinstance(task, dict) else None
        title = (task.get("title") if isinstance(task, dict) else None) or ""
        try:
            from capability_os import execute_capability
            result = execute_capability(
                cap_id, args or {}, auto_approve=True, goal_id=goal_id, timeout=60)
        except Exception as e:
            return {
                "task_id": task_id, "ok": False,
                "error": f"mcp_exec_error: {e}",
                "tool": cap_id, "capability": cap_id, "title": title, "category": "mcp",
                "is_external": True,
            }
        if not isinstance(result, dict):
            # 极少路径：非字典结果视作成功文本
            return {"task_id": task_id, "ok": True, "tool": cap_id, "capability": cap_id,
                    "is_external": True, "result": str(result)[:2000]}
        ok = bool(result.get("ok")) and not result.get("is_error") and not result.get("error")
        text = result.get("text") or ""
        # —— Phase C · G5 · 注入边界：外部 MCP 结果进入上下文前校验（FAIL CLOSED）——
        safe, ireason = self._assert_safe_injection(text)
        if not safe:
            return {"task_id": task_id, "ok": False, "blocked": True,
                    "reason": ireason, "tool": cap_id, "category": "injection_blocked",
                    "is_external": True}
        reason = result.get("permission_reason")
        res = {
            "task_id": task_id,
            "ok": ok,
            "tool": cap_id,
            "capability": cap_id,
            "is_external": True,
            "result": str(text)[:2000],
            "raw": str(result.get("raw"))[:2000],
            "permission_reason": reason,
        }
        if not ok:
            res["category"] = "mcp"
            res["error"] = result.get("error") or reason or "mcp capability returned not ok"
            if reason and "deny" in str(reason).lower():
                res["blocked"] = True
        return res

    def _try_alternative_tool(self, task: dict, excluded: str) -> tuple:
        """尝试用替代工具执行同一任务（失败重试用）。"""
        try:
            from tools import TOOL_FUNCS
            alternatives = [t for t in TOOL_FUNCS.keys() if t != excluded]
            if not alternatives:
                return None, {}
            # 取第一个非 excluded 的工具，复用原 args
            return alternatives[0], {}
        except Exception:
            return None, {}

    def _within_depth(self, depth: int) -> bool:
        """Phase C · G3 · 深度闸门：当前嵌套深度是否仍在允许范围内。"""
        return depth <= self._max_depth

    def _execute_skill_task(self, goal_id: int, task, skill_handle: str, args) -> dict:
        """Phase C · G1 · 原生 Skill 执行（单一执行链，FAIL CLOSED）。

        链路：skill:<name> → tools.execute_tool（skill: 分支）→ skills.execute_skill
              → 返回技能 body 指令包（str）。Agent 据此在原 loop 中调用 canonical TOOL_FUNCS。
        纪律红线：Agent Runtime 不拥有技能执行权、不新建第二执行器。
        """
        task_id = task.get("id") if isinstance(task, dict) else None
        # R8-P0：消除 execute_tool 直连绕过 —— skill 统一经 ai_core.execution.run
        # （Policy 闸门先裁决；skill: 分支由 run → tools.execute_tool → skills.execute_skill 完成）。
        from ai_core.execution import run as _execution_run
        res = _execution_run(skill_handle, {"args": args or {}, "goal_id": goal_id})
        if not isinstance(res, dict) or not res.get("success"):
            # FAIL CLOSED：policy block / 审批拒绝 / 执行异常一律按失败处理
            return {"task_id": task_id, "ok": False, "blocked": True,
                    "reason": (res.get("error") if isinstance(res, dict) else str(res)) or "skill execution blocked",
                    "tool": skill_handle, "category": "skill"}
        result = res.get("result") or ""
        # FAIL CLOSED：未知技能经 execute_tool 返回「未知技能：...」
        if isinstance(result, str) and result.startswith("未知技能"):
            return {"task_id": task_id, "ok": False, "error": result,
                    "tool": skill_handle, "category": "skill"}
        # —— Phase C · G5 · 注入边界：技能体进入 Agent 上下文前校验（命中控制覆盖即拒）——
        safe, reason = self._assert_safe_injection(result)
        if not safe:
            return {"task_id": task_id, "ok": False, "blocked": True,
                    "reason": reason, "tool": skill_handle, "category": "injection_blocked"}
        return {"task_id": task_id, "ok": True, "tool": skill_handle,
                "skill": skill_handle, "instructions": result,
                "result": str(result)[:2000]}

    # —— Phase C · G4 · 统一错误分类（18 类，单一词汇表，见 ERROR_TAXONOMY）——
    ERROR_TAXONOMY = {
        "network", "timeout", "permission", "file", "not_found",
        "tool_missing", "skill_error", "mcp_error", "computer_error",
        "budget_exhausted", "depth_exceeded", "injection_blocked", "policy_blocked",
        "parse_error", "serialization", "validation", "resource", "unknown",
    }
    # FAIL-CLOSED 致命类：未知 / 预算耗尽 / 深度超限 / 注入阻断 / 策略阻断 等一律拒绝，
    # 不重试（其余均终止本次执行）。
    # R8-P4 timeout 策略审查：timeout 归入非致命瞬时类（设计意图为可重试），但 Recovery
    # Router 当前仅对 network（退避重试）/ file（换替代工具）实施重试；timeout 保持
    # FAIL CLOSED 快速失败（attempts=1）。行为安全（宁拒勿挂），按 R8-P4 结论保持现状
    # 并记为已知限制，不扩大 Recovery 改造。
    _FATAL_ERROR_CATEGORIES = {
        "unknown", "budget_exhausted", "depth_exceeded", "injection_blocked",
        "policy_blocked", "skill_error", "validation", "serialization",
        "parse_error", "resource", "tool_missing", "not_found",
        "mcp_error", "computer_error",
    }

    @staticmethod
    def _classify_error(error: Exception, tool: str) -> str:
        """Phase C · G4 · 统一 18 类错误分类（单一词汇表，见 ERROR_TAXONOMY）。

        顺序：先识别本运行时各 FAIL-CLOSED 路径显式嵌入的合成标记
        （budget_exhausted / depth_exceeded / injection_blocked / policy_blocked），
        再按异常消息关键词归并到具体类；兜底 unknown。
        """
        msg = (str(error) or "").lower()
        # —— 异常类型快路径（内置异常语义明确，优先于消息关键词，
        #     避免 FileNotFoundError 被 not_found 抢匹配、ConnectionError 被 timeout 抢匹配）——
        # FileNotFoundError / IsADirectoryError / NotADirectoryError → file（可换工具重试）
        if isinstance(error, (FileNotFoundError, IsADirectoryError, NotADirectoryError)):
            return "file"
        if isinstance(error, PermissionError):
            return "permission"
        if isinstance(error, TimeoutError):
            return "timeout"
        if isinstance(error, ConnectionError):
            return "network"
        # —— 失败字符串中的异常类名快路径（R8-P2 Failure Truthfulness：
        #     execute_tool 失败串携带 type(e).__name__，据此恢复被字符串包装
        #     丢失的异常类型语义，避免 FileNotFoundError 被 not_found 抢匹配等）——
        if "filenotfounderror" in msg or "isadirectoryerror" in msg or "notadirectoryerror" in msg:
            return "file"
        if "permissionerror" in msg:
            return "permission"
        if "timeouterror" in msg:
            return "timeout"
        if "connectionerror" in msg:
            return "network"
        # —— 合成标记（由各 FAIL-CLOSED 路径显式嵌入消息）——
        if "budget_exhausted" in msg or ("budget" in msg and "exhaust" in msg):
            return "budget_exhausted"
        if "depth_exceeded" in msg or ("depth" in msg and "exceed" in msg):
            return "depth_exceeded"
        if "injection_blocked" in msg:
            return "injection_blocked"
        if "policy_blocked" in msg or "denied by policy" in msg:
            return "policy_blocked"
        # —— 异常消息关键词归并 ——
        if "permission" in msg or "access" in msg or "denied" in msg \
           or "oserror" in msg or "forbidden" in msg or "unauthorized" in msg:
            return "permission"
        # —— network 先于 timeout：含 "connection" 的连接类错误归 network（可退避重试），
        #    纯超时（无 connection 字样）才归 timeout，避免 "connection timeout" 误判为 timeout ——
        if "network" in msg or "connection" in msg or "urlopen" in msg \
           or "socket" in msg or "dns" in msg or "getaddrinfo" in msg:
            return "network"
        if "timeout" in msg or "timed out" in msg:
            return "timeout"
        if "not found" in msg or "no such" in msg or "does not exist" in msg \
           or "missing" in msg:
            return "not_found"
        if "isfile" in msg or "isdir" in msg or "not a directory" in msg \
           or ("path" in msg and "file" in msg):
            return "file"
        if "unknown tool" in msg or "unknown capability" in msg or "unknown skill" in msg \
           or "未知工具" in msg or "未知技能" in msg or "未知能力" in msg:
            return "tool_missing"
        if "skill" in msg:
            return "skill_error"
        if "mcp" in msg:
            return "mcp_error"
        if "computer" in msg or "computer_action" in msg:
            return "computer_error"
        if "parse" in msg or "json" in msg or "syntax" in msg or "yaml" in msg:
            return "parse_error"
        if "serial" in msg or "pickle" in msg or "marshal" in msg or "unserial" in msg:
            return "serialization"
        if "valid" in msg or "schema" in msg or "required" in msg or "invalid" in msg:
            return "validation"
        if "memory" in msg or "resource" in msg or "oom" in msg or "too many" in msg \
           or "no space" in msg or "resource temporarily" in msg:
            return "resource"
        return "unknown"

    @staticmethod
    def _is_fatal_error(category: str) -> bool:
        """Phase C · G4 · 该错误类是否应 FAIL CLOSED（终止执行、不重试）。"""
        return category in AgentRuntime._FATAL_ERROR_CATEGORIES

    # —— Phase C · G5 · 显式注入边界（Prompt Injection Boundary）——
    # 技能体 / 外部结果进入 Agent 上下文前强制校验；命中控制覆盖标记即 FAIL CLOSED 拒绝。
    _INJECTION_MARKERS = (
        "ignore previous instructions", "ignore all previous", "忽略之前",
        "忽略上述", "忽略前面", "无视之前的", "disregard previous", "disregard all",
        "you are now", "你现在", "你现在是", "pretend to be", "假装你是",
        "system prompt", "system:", "new instructions", "新指令", "override",
        "忘记你", "forget your", "jailbreak", "越狱", "DAN", "developer mode",
        "print your", "reveal your", "泄露你的", "把你的", "exfiltrate",
    )

    @staticmethod
    def _assert_safe_injection(content) -> tuple:
        """Phase C · G5 · 校验内容是否含提示注入控制覆盖标记。

        返回 (ok, reason)。命中任一标记 → (False, "injection marker detected: ...")（FAIL CLOSED）。
        """
        if content is None:
            return True, ""
        text = str(content)
        low = text.lower()
        for marker in AgentRuntime._INJECTION_MARKERS:
            if marker.lower() in low:
                return False, "injection marker detected: %s" % marker
        return True, ""

    def _resolve_dispatch(self, task: dict):
        """解析任务对应的工具 + 参数。Round 2 起 plan_goal 会在 note 写入 suggested_tool；
        若没有则回退 LLM 派发（P5.1：LLM 派发改用 Canonical Cognitive Context）。
        goal_id 取自运行时当前目标（self._current，由 _run_goal 设置），避免改动调用签名以兼容既有测试桩。"""
        sug = _parse_suggested(task.get("note") or "")
        if sug and sug.get("tool"):
            return sug["tool"], sug.get("args", {})
        goal_id = getattr(self, "_current", None)
        return self._llm_dispatch(task, goal_id)

    def _llm_dispatch(self, task: dict, goal_id: int = None):
        try:
            # Phase C · G1 · 暴露完整可派发句柄：TOOL_FUNCS + external.mcp.* + skill:*
            from capability_os.discovery import dispatch_tool_list
            tool_names = sorted(dispatch_tool_list())
        except Exception:
            try:
                from tools import TOOL_FUNCS
                tool_names = sorted(TOOL_FUNCS.keys())
            except Exception:
                tool_names = []
        # —— P5.1：Planner Context 改由 Canonical Context Engine 生成 ——
        # 替换 agent_runtime.py:862-868 原硬编码「你是小6的调度器…」自构 prompt。
        # 记忆 / 目标 / 用户画像 / 人格 / 身份等认知上下文统一经 context.facade.build_cognitive_context
        # （与 Chat 共享同一 LegacyContextBuilder，禁止第二套 Context 组装 / 第二套 Prompt Builder）。
        # 仅「调度指令 + 动态工具清单 + 当前任务」作为即时调用规格保留在 Runtime
        # （属运行期调用契约，非知识上下文，不构成第二引擎）。
        # FEATURE_COGNITIVE_CONTEXT=False 时回退 legacy 自构 prompt（DEPRECATE，不删）。
        try:
            import config as _cfg
            _use_cog = bool(getattr(_cfg, "FEATURE_COGNITIVE_CONTEXT", True))
        except Exception:
            _use_cog = True
        if _use_cog:
            try:
                from context.facade import build_cognitive_context
                cog_ctx = build_cognitive_context(goal_id=goal_id, task=task, mode="plan")
            except Exception as e:
                cog_ctx = ""
                print(f"[runtime] Cognitive Context 构建失败，回退 legacy prompt: {e}")
        else:
            cog_ctx = ""
        dispatch_instruction = (
            "你是小6的调度器。根据任务选择最合适的工具并给出参数（只输出 JSON）。\n"
            f"可用工具：{', '.join(tool_names)}\n"
            f"任务标题：{task.get('title')}\n"
            f"子步骤：{task.get('steps')}\n"
            '输出格式：{"tool":"工具名","args":{...}}'
        )
        if cog_ctx:
            prompt = f"{cog_ctx}\n\n{dispatch_instruction}"
        else:
            prompt = dispatch_instruction
        try:
            import llm
            # R8-P4：修复无 suggested_tool 派发失败——LLM 请求必须带 user 消息
            #（Agnes 端点对仅 system 消息返回 400 "No user query found in messages."）。
            # 派发消息只含「调度规格」即时契约（非知识上下文），不构成第二套 Context 组装。
            with llm.agnes_completion(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user",
                     "content": f"请为任务「{task.get('title') or ''}」选择最合适的工具并给出参数（只输出 JSON）。"},
                ],
                stream=False, temperature=0.3, reasoning=None,
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            msg = (data.get("choices") or [{}])[0].get("message", {})
            text = msg.get("content") or ""
            obj = _extract_json(text)
            if obj and obj.get("tool"):
                return obj["tool"], obj.get("args", {})
        except Exception as e:
            print(f"[runtime] LLM 派发失败: {e}")
        return None, {}

    def _notify_goal_done(self, goal_id: int, summary: str):
        """Goal 完成后的自动汇报（TTS + 记忆蒸馏）。

        注：Goal 完成领域事件 GOAL_COMPLETED 已由 _emit_goal_domain 经 publish_domain 发出
        （单一来源纪律，readiness §5），此处不再重复发射其小写同义非合约事件。
        """
        try:
            # TTS 播报（可选，由 FEATURE_TTS_STREAM 控制）
            try:
                import config
                if getattr(config, "FEATURE_TTS_STREAM", False):
                    import tts
                    tts.speak(f"目标 {summary}")
            except Exception:
                pass
            # P12-1：Goal 完成后蒸馏记忆（非阻塞，不拖慢主流程）
            try:
                import config
                if getattr(config, "FEATURE_MEMORY_DISTILL", False):
                    threading.Thread(target=self._distill_memory, kwargs={"session_id": "goal"},
                                    name="zz-distill", daemon=True).start()
            except Exception:
                pass
        except Exception as e:
            print(f"[runtime] 汇报失败: {e}")

    # ---- Phase 12 记忆人格深度（蒸馏 + 情感联结）----

    def _load_recent_chat(self, limit: int = _MAX_DISTILL_MESSAGES) -> list:
        """从 chat_log 读取最近 limit 条对话（按时间升序），用于蒸馏/记忆沉淀。

        P4 性能调优：以参数化 LIMIT 截断旧消息，内存有界、向后兼容。
        """
        try:
            from db import db_conn
            conn = db_conn()
            rows = conn.execute(
                "SELECT role, content FROM chat_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [
                {"role": ("user" if r[0] == "user" else "assistant"), "content": r[1]}
                for r in reversed(rows)
            ]
        except Exception:
            return []

    def _record_conversation_memory(self, messages: list) -> None:
        """P12-3：把本次对话沉淀为 ConversationMemory（best-effort）。"""
        try:
            from datetime import datetime, date

            user_msgs = [
                m.get("content", "") for m in messages
                if m.get("role") == "user" and m.get("content")
            ]
            if not user_msgs:
                return
            topic = user_msgs[-1][:40]
            key_points = user_msgs[-5:]
            full = "\n".join(user_msgs)
            sentiment = "neutral"
            if any(w in full for w in ("难过", "烦", "生气", "讨厌", "失望", "累", "压力", "焦虑")):
                sentiment = "negative"
            elif any(w in full for w in ("开心", "高兴", "谢谢", "棒", "喜欢", "爱", "赞", "期待")):
                sentiment = "positive"
            # P5.2 · Canonical Memory Integration：Agent Runtime 不再自持记忆持久化，
            # 统一经 cognitive.memory_adapter → memory.py Canonical Memory API
            # （唯一写入权威）；conversation_memories 退化为 adapter 维护的兼容投影。
            from cognitive.memory_adapter import record_conversation_memory
            record_conversation_memory(
                date=date.today().isoformat(),
                topic=topic,
                key_points=key_points,
                sentiment=sentiment,
                created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception:
            pass

    def _check_important_dates(self) -> None:
        """P12-3：扫描重要日期，提前 reminder_days 天推送提醒（best-effort）。"""
        try:
            from datetime import date
            from db import db_conn
            conn = db_conn()
            rows = conn.execute(
                "SELECT id, date, type, description, reminder_days FROM important_dates"
            ).fetchall()
            conn.close()
            today = date.today()
            label_map = {"birthday": "生日", "anniversary": "纪念日",
                         "holiday": "节日", "event": "重要日子"}
            for r in rows:
                d = _parse_date(r[1])
                if not d:
                    continue
                days_left = (d - today).days
                if 0 <= days_left <= (r[4] or 3):
                    label = label_map.get(r[2], "重要日子")
                    content = f"提醒：{r[3] or label} 还有 {days_left} 天（{r[1]}）"
                    try:
                        from proactive import push_proactive
                        push_proactive("memory", content)
                    except Exception:
                        from eventbus import publish_system
                        publish_system("memory_reminder", {"content": content},
                                       source="agent_runtime")
        except Exception:
            pass

    def _maybe_daily_maintenance(self) -> None:
        """每日一次记忆维护：蒸馏 + 重要日期检查。门控 FEATURE_MEMORY_DISTILL，按天去重。"""
        try:
            import config
            if not getattr(config, "FEATURE_MEMORY_DISTILL", False):
                return
            today = date.today().isoformat()
            if getattr(self, "_last_maintenance_date", None) == today:
                return
            self._last_maintenance_date = today
            self._distill_memory(session_id="daily")
            self._check_important_dates()
        except Exception:
            pass

    # ---- 辅助 ----
    def _set_goal_status(self, gid, status, progress=None):
        try:
            from goals import update_goal
            kw = {"status": status}
            if progress is not None:
                kw["progress"] = progress
            update_goal(gid, **kw)
        except Exception:
            pass

    def _set_goal_progress(self, gid, progress):
        try:
            from goals import update_goal
            update_goal(gid, progress=progress)
        except Exception:
            pass

    # ---- Phase 6 Order 2：Goal 生命周期规范领域事件发射（单一来源，经 publish_domain）----
    def _emit_goal_domain(self, name: str, goal_id: int, **extra):
        """把 Goal 执行态映射为规范领域事件发到 SSE（前端 AppState 合约入口）。

        职责边界：本方法只做“运行态→规范信封”的发射，不承载任何业务判断；
        未知事件名由 publish_domain 拒绝（单一来源纪律，readiness §5）。
        """
        try:
            from eventbus import publish_domain

            if name not in ("GOAL_STARTED", "GOAL_RUNNING", "GOAL_COMPLETED", "GOAL_FAILED"):
                return
            from goals import get_goal

            g = get_goal(goal_id)
            if not g:
                return
            payload = {
                "goalId": g.id,
                "title": g.title,
                "status": g.status,
                "progress": g.progress,
                "priority": g.priority,
                "horizon": g.horizon,
                "dueDate": g.due_date,
            }
            payload.update(extra)
            publish_domain(name, payload, source="agent_runtime")
        except Exception as e:
            print(f"[runtime] 领域事件发布失败（已忽略）: {e}")

    # ---- Phase 6 Order 3：Agent / Task 生命周期规范事件发射（单一来源）----
    @staticmethod
    def _agent_id_for(goal_id: int) -> str:
        """Agent 编排体 id 与 Goal 绑定（Galaxy 中 Agent 是 Goal 轨道的卫星）。"""
        return f"a{goal_id}"

    def _emit_agent_domain(self, name: str, goal_id: int, **extra):
        """把 Agent 编排态映射为规范领域事件（AGENT_* 单一来源，经 publish_domain）。

        职责边界同 _emit_goal_domain：只发射，不承载业务判断。
        """
        try:
            from eventbus import publish_domain

            AGENT_NAMES = {
                "AGENT_CREATED", "AGENT_STARTED", "AGENT_THINKING", "AGENT_WORKING",
                "AGENT_WAITING", "AGENT_COMPLETED", "AGENT_FAILED",
            }
            if name not in AGENT_NAMES:
                return
            payload = {
                "agentId": self._agent_id_for(goal_id),
                "goalId": goal_id,
                "name": "小6编排体",
                "type": "orchestrator",
            }
            payload.update(extra)
            publish_domain(name, payload, source="agent_runtime")
        except Exception as e:
            print(f"[runtime] Agent 领域事件发布失败（已忽略）: {e}")

    def _emit_task_domain(self, name: str, goal_id: int, task_id: int, **extra):
        """把 Task 执行态映射为规范领域事件（TASK_* 单一来源，经 publish_domain）。

        职责边界同 _emit_goal_domain：只发射，不承载业务判断。
        """
        try:
            from eventbus import publish_domain
            TASK_NAMES = {
                "TASK_CREATED", "TASK_STARTED", "TASK_RUNNING",
                "TASK_COMPLETED", "TASK_FAILED",
            }
            if name not in TASK_NAMES:
                return
            payload = {
                "taskId": task_id,
                "goalId": goal_id,
                "agentId": self._agent_id_for(goal_id),
            }
            payload.update(extra)
            publish_domain(name, payload, source="agent_runtime")
        except Exception as e:
            print(f"[runtime] Task 领域事件发布失败（已忽略）: {e}")

    # ---- Phase 6 Order 4：Memory 生命周期规范事件发射（单一来源）----
    def _emit_memory_domain(self, name: str, goal_id: int, **extra):
        """把 Memory 生命周期态映射为规范领域事件（MEMORY_* 单一来源，经 publish_domain）。

        职责边界同 _emit_goal_domain：只发射，不承载业务判断。
        """
        try:
            from eventbus import publish_domain

            MEMORY_NAMES = {
                "MEMORY_CREATED", "MEMORY_UPDATED", "MEMORY_STORED",
                "MEMORY_LINKED", "MEMORY_ARCHIVED",
            }
            if name not in MEMORY_NAMES:
                return
            payload = {"goalId": goal_id}
            payload.update(extra)
            publish_domain(name, payload, source="agent_runtime")
        except Exception as e:
            print(f"[runtime] Memory 领域事件发布失败（已忽略）: {e}")

    # ---- Phase 6 Order 4：反思阶段入口事件 REFLECTING（单一来源）----
    def _emit_reflect_domain(self, name: str, goal_id: int, **extra):
        """反思阶段事件（REFLECTING 单一来源，经 publish_domain）。"""
        try:
            from eventbus import publish_domain

            if name not in ("REFLECTING",):
                return
            payload = {"goalId": goal_id}
            payload.update(extra)
            publish_domain(name, payload, source="agent_runtime")
        except Exception as e:
            print(f"[runtime] Reflect 领域事件发布失败（已忽略）: {e}")

    def _publish_state(self, event, goal_id=None, **extra):
        try:
            from eventbus import bus, TOPIC_HUD_STATE, publish_system
            fields = {"event": event, "state": self.state, "current_goal": self._current}
            if goal_id is not None:
                fields["goal_id"] = goal_id
            fields.update(extra)
            publish_system("agent_state", fields, source="agent_runtime")
            # agent:state 主题（独立消费者）保持原信封结构（含 xiao6_event）
            agent_state_envelope = dict(fields)
            agent_state_envelope["xiao6_event"] = "agent_state"
            bus.publish("agent:state", agent_state_envelope, source="agent_runtime")
            # Phase 11 全息 HUD：把 Agent 编排态映射为 HUD 光环状态，供前端光环/glance 订阅
            hud_state = self._hud_state_for(event)
            hud_payload = {"xiao6_event": "hud_state", "state": hud_state}
            if goal_id is not None:
                hud_payload["goal_id"] = goal_id
            if "progress" in extra:
                hud_payload["progress"] = extra["progress"]
            bus.publish(TOPIC_HUD_STATE, hud_payload, source="agent_runtime")
        except Exception:
            pass

    # Phase 11：Agent 编排态 -> 光环状态映射
    _THINKING_EVENTS = {PLANNING, EXECUTING, REFLECTING, "goal_submitted", "busy"}

    def _hud_state_for(self, event):
        ev = (event or "").upper()
        if self.state != IDLE or ev in self._THINKING_EVENTS:
            return "thinking"
        return "idle"


# ---------- 工具函数 ----------

def _parse_suggested(note: str) -> dict:
    """从 task.note 解析 plan_goal 预绑定的 suggested_tool（Round 2 格式）。"""
    m = re.search(r"suggested_tool=([\w.:]+)\s+args=(\{[^}]*\})", note or "")
    if not m:
        return {}
    tool = m.group(1)
    try:
        args = json.loads(m.group(2))
    except Exception:
        args = {}
    return {"tool": tool, "args": args}


def _extract_json(text):
    if not text:
        return None
    raw = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if m:
        raw = m.group(1).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    s, e = raw.find("{"), raw.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(raw[s:e + 1])
        except Exception:
            return None
    return None


# 进程级单例
runtime = AgentRuntime()
