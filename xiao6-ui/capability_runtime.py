#!/usr/bin/env python3
"""庄周 · 默认 Chat 统一 Capability Execution 适配器（P1 · Phase 47.4）

职责（最小侵入，严格不新建第二套执行/权限/注册表）：
- 这是「默认 Chat」能力的**唯一收敛点**：普通聊天里需要执行的能力，统一经本模块，
  再委派既有单一执行链，不再存在一条独立于 Agent Runtime / Capability OS 的旁路 Tool 执行体系。
- 能力选择真相源：capability_os.discovery.dispatch_tool_list()（本地 TOOL_FUNCS + 外部
  external.mcp.* + skill:* 句柄，单一可见能力清单）。
- 执行入口：仍走 ai_core.execution.run（policy_engine default_deny 门）→ tools.execute_tool。
  对「已注册且可执行」的能力（tool/builtin 类），优先经 capability_os.invoke_capability
  （能力级门面，零内联执行，委派 execute_tool）；umbrella/none/computer_action/未注册/动态工具
  回退 execute_tool（行为 100% 兼容 P1 前）。
- 结果契约：统一包装为 CapabilityResult（向后兼容——旧调用方拿到的仍是 str / 原始返回值）。

红线（与全系统一致）：
- 任何能力不得 Capability → Tool 直连绕过 Policy；所有执行入口都过 ai_core.execution.run 的 policy 门。
- default_deny=True 保留；HIGH/CRITICAL 由 Policy block；MEDIUM 本地 chat 保持 auto（设计内）。
- 不复制 Policy / Permission / EventBus / Memory / Registry；全部复用既有模块。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# —— 回退开关：config.FEATURE_CAPABILITY_RUNTIME=False 时，本模块全部委托回 P1 前行为 ——
def _feature_enabled() -> bool:
    try:
        import config
        return bool(getattr(config, "FEATURE_CAPABILITY_RUNTIME", True))
    except Exception:
        return True


# ─────────────────────────────────────────────────────────────────────────────
# CapabilityResult：统一执行结果契约（P1 · §六）
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class CapabilityResult:
    """默认 Chat 统一能力执行结果。

    字段（P1 §六，可按真实代码扩展）：
      success        —— 是否成功
      capability_id  —— 能力 id（tool_to_capability 解析；未知回退 'tools'）
      execution_id   —— 执行实例 id（若有；默认空）
      data           —— 结构化结果（成功时为原始返回值）
      message        —— 面向用户的成功消息
      error          —— 失败描述
      error_type     —— 错误分类：policy_denied / approval_required / execution_failed /
                        timeout / network / not_found / validation / unknown
      retryable      —— 是否可重试（network/timeout/file 类）
      requires_approval —— 是否因权限需审批（被拒/等待确认）
      metadata       —— 扩展字段
    """

    success: bool = True
    capability_id: str = "tools"
    execution_id: str = ""
    data: Any = None
    message: str = ""
    error: str = ""
    error_type: str = ""
    retryable: bool = False
    requires_approval: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, name: str, cap_id: str, raw: Any) -> "CapabilityResult":
        """把既有 execute_tool / invoke_capability 的原始返回值（通常为 str）包装为 CapabilityResult。

        失败判定复用 execute_tool 的返回约定前缀（不修改既有返回值语义）：
          "工具执行失败" / "未知工具" / "未知技能" / "外部 MCP 能力执行失败" /
          "能力 ... 无执行体映射" / "在远程会话中不可用" / "被权限策略阻止" /
          "被安全策略阻止" / "用户拒绝执行" / "为永久拒绝占位"。
        """
        text = raw if isinstance(raw, str) else str(raw)
        # 注意：execute_tool 失败返回形如「工具 X 被安全策略阻止：...」/「工具 X 在远程会话中不可用...」，
        # 标记在字符串中部，必须用子串 in 而非 startswith 判定。
        fail_markers = (
            "工具执行失败", "未知工具", "未知技能", "外部 MCP 能力执行失败",
            "无执行体映射", "在远程会话中不可用", "被权限策略阻止",
            "被安全策略阻止", "用户拒绝执行", "为永久拒绝占位",
        )
        success = not any(m in text for m in fail_markers)
        if success:
            return cls(
                success=True, capability_id=cap_id or name, data=raw,
                message=text, metadata={"tool": name},
            )
        etype = _classify_error_type(text)
        return cls(
            success=False, capability_id=cap_id or name, data=raw,
            error=text, error_type=etype,
            retryable=etype in ("network", "timeout", "file"),
            requires_approval=etype in ("policy_denied", "approval_required"),
            metadata={"tool": name},
        )

    def to_tool_message(self) -> str:
        """回填 LLM function-calling tool 消息的文本（与 P1 前 execute_tool 返回的 str 一致）。"""
        if isinstance(self.data, str):
            return self.data
        return self.message or self.error or str(self.data)


def _classify_error_type(text: str) -> str:
    """把失败文本映射到 P1 §六 错误分类（复用现有 Policy / Error 语义）。"""
    t = (text or "").lower()
    if "被权限策略阻止" in text or "被安全策略阻止" in text or "在远程会话中不可用" in text:
        return "policy_denied"
    if "用户拒绝执行" in text or "为永久拒绝占位" in text:
        return "approval_required"
    if "超时" in text or "timed out" in t or "timeout" in t:
        return "timeout"
    if "连接" in text or "connection" in t or "network" in t:
        return "network"
    if "未找到" in text or "no such" in t or "not found" in t:
        return "not_found"
    if "未知工具" in text or "未知技能" in text or "未知能力" in text or "无执行体映射" in text:
        return "validation"
    if "工具执行失败" in text:
        return "execution_failed"
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# 选择 + 执行桥
# ─────────────────────────────────────────────────────────────────────────────
def select_capabilities(text: str, allowed: Optional[Any] = None) -> list:
    """默认 Chat 下发给 LLM 的可见能力（tool schema）清单。

    以 capability_os.discovery.dispatch_tool_list() 为可见能力真相源，再经 select_tools
    做低延迟裁剪（纯函数启发式，不增新选择逻辑）。行为兼容 P1 前的 select_tools(text, allowed)。
    """
    if not _feature_enabled():
        from tools import select_tools
        return select_tools(text, allowed=allowed)
    from capability_os import discovery
    from tools import select_tools
    visible = set(discovery.dispatch_tool_list())  # 本地 TOOL_FUNCS + external.mcp.* + skill:*
    if allowed is not None:
        visible &= set(allowed)
    # dispatch_tool_list ⊇ TOOLS，故交集不会丢既有工具；select_tools 仍做延迟启发式裁剪
    return select_tools(text, allowed=list(visible) if visible else None)


def execute(name: str, args: Any = None, *, allowed: Optional[Any] = None,
            permission_mode: str = "none", goal_id: Optional[int] = None) -> CapabilityResult:
    """默认 Chat 的统一能力执行桥（P1 收敛点）。

    纪律：
    - 会话白名单（远程 allowed）在边界先校验，与 execute_tool 同语义、安全不退化。
    - 已注册且可执行能力（tool/builtin）→ capability_os.invoke_capability（委派 execute_tool → ai_core.execution.run）。
    - umbrella/none/computer_action/未注册/动态工具 → 直落 execute_tool（P1 前行为，零回归）。
    - 所有路径最终都过 ai_core.execution.run 的 policy 门（default_deny=True）。
    """
    if not _feature_enabled():
        # R8-P0：回退开关只影响能力选择，不再允许直连 execute_tool 绕过 Policy；
        # 统一经 ai_core.execution.run（policy 门，default_deny）执行。
        from ai_core.execution import run as _execution_run
        raw = _execution_run(name, {"args": args or {}}, allowed=allowed)
        from capability_os import tool_to_capability
        return CapabilityResult.from_raw(name, tool_to_capability(name), raw)

    # 1) 会话白名单（远程会话受约束；本地 allowed=None 不限制）
    if allowed is not None and name not in allowed:
        from capability_os import tool_to_capability
        cap_id = tool_to_capability(name)
        return CapabilityResult(
            success=False, capability_id=cap_id, data=None,
            error=f"工具 {name} 在远程会话中不可用（受白名单限制）",
            error_type="policy_denied", requires_approval=True, metadata={"tool": name},
        )

    # 2) 解析能力 id（capability_os 为能力真相源；仅用于 CapabilityResult.capability_id 标注）
    from capability_os import tool_to_capability
    cap_id = tool_to_capability(name)
    # 3) 统一执行入口：必须经 ai_core.execution.run 的 policy 门（default_deny），
    #    与 P1 前 run_fc_loop 行为严格一致——严禁直连 execute_tool 绕过 Policy。
    #    capability_os.invoke_capability 亦委派 execute_tool，会跳过该 policy 门，
    #    故默认 Chat 执行统一走 _execution_run（唯一 policy 门），不在此分叉。
    from ai_core.execution import run as _execution_run
    # R8-P0：参数契约 run(task, context={"args": args})，工具参数不得丢失
    raw = _execution_run(name, {"args": args or {}}, allowed=allowed)
    return CapabilityResult.from_raw(name, cap_id, raw)
