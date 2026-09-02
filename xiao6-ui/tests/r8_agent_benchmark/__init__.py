# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark — R8-P1 Agent Reliability Benchmark Suite

子套件：
  A. single_tool        — calculator / get_time 单工具执行
  B. multi_step_goal    — submit_goal → plan_goal → ExecutionPolicy → run() → Tool → Verify → completed
  C. failure_recovery   — tool exception / timeout / policy deny → ERROR_TAXONOMY / Recovery Router / Retry

全部经真实执行链（ai_core.execution.run / agent_runtime），不绕过 ExecutionPolicy、
不直连 execute_tool（除被测工具经 TOOL_FUNCS 注册的真实入口外）。
"""
