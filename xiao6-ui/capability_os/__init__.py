#!/usr/bin/env python3
"""庄周 · 能力操作系统（Capability OS Layer）—— Phase 23 · 包门面

这是庄周的「能力自知 / 能力匹配 / 能力组合 / 权限控制」层。
它【不执行任何能力】，只描述、匹配、编排、标注权限，并复用既有入口与 Guard。

对外 API：
  bootstrap()             —— 构建统一注册表（幂等，只读）
  list_capabilities()    —— 全部能力（Capability 模型）
  available_capabilities()
  match(goal)             —— 目标 → 候选能力（打分）
  route(cap_ids)          —— 排序 + 权限标注
  compose(task)           —— 组合多能力计划
  get_state()             —— 运行时状态（活跃能力 / 可用性快照）
  tool_to_capability(tool_name) —— 工具名 → 能力 id（供 UI 事件映射）
"""

from __future__ import annotations

from .registry import (
    Capability, get_registry, get_capability, list_capabilities,
    available_capabilities, get_groups, Risk, Permission,
)
from .matcher import match, match_ids, best_match, explain as explain_match
from .router import route, explain_route
from .composer import compose
from .capability_state import CapabilityState, get_state
from .execution_mapping import (
    get_executor, executor_callable, tool_to_capability as map_tool_to_capability,
)
from .verification import (
    verify_capability, verify_all, health_summary,
    READY, DECLARED, PARTIAL, BLOCKED, UNAVAILABLE, ERROR,
)
from .discovery import (
    is_external_mcp, external_capability_ids, list_executable_capabilities,
    dispatch_tool_list, ensure_external_capabilities, EXTERNAL_PREFIX,
    discoverable_skill_handles,
)

__all__ = [
    "Capability", "get_registry", "get_capability", "list_capabilities",
    "available_capabilities", "get_groups", "Risk", "Permission",
    "match", "match_ids", "best_match", "explain_match",
    "route", "explain_route", "compose",
    "CapabilityState", "get_state", "bootstrap", "tool_to_capability",
    # —— Phase 40 · Capability Foundation ——
    "get_executor", "executor_callable", "map_tool_to_capability",
    "verify_capability", "verify_all", "health_summary",
    "READY", "DECLARED", "PARTIAL", "BLOCKED", "UNAVAILABLE", "ERROR",
    "foundation_view", "verify_capabilities",
    # —— Phase 41 · MCP Host / External Tool Bridge ——
    "execute_capability",
    # —— Phase B · 统一能力调用入口（产品化闭环，委派既有执行链）——
    "invoke_capability",
    # —— Phase 42 · Capability Discovery（只读聚合适配器）——
    "is_external_mcp", "external_capability_ids", "list_executable_capabilities",
    "dispatch_tool_list", "ensure_external_capabilities", "EXTERNAL_PREFIX",
    # —— Phase 45 · Skill 作为能力包发现层（只读聚合，不新建第二真相源）——
    "discoverable_skill_handles",
]


# —— 工具名 → 能力 id 映射（供 UI 订阅 tool_started 时显示「正在用能力 X」）——
# 覆盖 Phase 23.4 测试与常见工具；其余工具回退到 group=Tools 的通用「工具」能力。
_TOOL_TO_CAPABILITY = {
    "get_time": "time",
    "tick_now": "time",
    "asr_transcribe": "voice",
    "memory_search": "memory",
    "add_knowledge": "knowledge",
    "archive_knowledge": "knowledge",
    "hotspots": "world_pulse",
    "weather": "world_pulse",
    "set_goal": "goals",
    "plan_goal": "goals",
    "list_goals": "goals",
    "open_application": "computer_action",
    "open_folder": "computer_action",
    "open_file": "computer_action",
    "search": "computer_action",
    "copy_text": "computer_action",
    "web_search": "tools",
    "browser_read": "tools",
}


def bootstrap() -> None:
    """构建统一能力注册表（幂等）。仅在导入期/启动期调用一次。

    纯只读聚合，不修改任何系统状态、不执行任何能力。
    """
    get_registry()


def tool_to_capability(tool_name: str) -> str:
    """工具名 → 能力 id。未知工具回退到 'tools'（通用工具能力）。"""
    if not tool_name:
        return "tools"
    name = tool_name.lower()
    if name in _TOOL_TO_CAPABILITY:
        return _TOOL_TO_CAPABILITY[name]
    # 电脑动作能力 id 与工具名常一致（open_folder 等）
    if get_capability(name) is not None:
        return name
    return "tools"


def catalog_view() -> dict:
    """供 /api/capabilities 返回的目录视图。"""
    groups = get_groups()
    return {
        "total": len(list_capabilities()),
        "available": len(available_capabilities()),
        "groups": {
            g: [c.to_dict() for c in caps] for g, caps in groups.items()
        },
    }


def foundation_view() -> dict:
    """统一 Capability Foundation 视图（单一真相出口，供 UI / 测试 / 调试消费）。

    返回结构即「UI 数据契约」：所有能力状态（READY/DECLARED/PARTIAL/BLOCKED/...）
    均由真实后端（声明真相源 + 执行真相源 + 权限真相源 + 运行时验证）决定，
    前端不得自行定义能力真相（spec §11）。
    """
    from .verification import verify_capability
    caps = list_capabilities()
    out_caps = []
    for c in caps:
        ref = get_executor(c.id)
        ref_d = ref.to_dict() if ref else {"kind": "none", "ref": "", "note": "无映射"}
        ref_d["callable"] = executor_callable(ref) if ref else False
        v = verify_capability(c.id)
        out_caps.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "group": c.group,
            "icon": c.icon,
            "risk": c.risk,
            "permission": c.permission,
            "available": c.available,
            "implemented": c.implemented,
            "executor": ref_d,
            "health": v,
            "ui": {"keywords": list(c.keywords)},
        })
    statuses = [o["health"]["status"] for o in out_caps]
    # Phase 41 · 外部世界桥状态（不并入既有 33 项能力真相，单独出口）
    mcp = {}
    try:
        from mcp_host import ensure_loaded
        host = ensure_loaded()
        mcp = host.servers_view()
    except Exception as e:
        mcp = {"servers": [], "total": 0, "ready": 0,
               "external_capabilities": [], "error": str(e)}
    return {
        "truth_sources": {
            "declaration": "capability_os.registry",
            "execution": "tools.TOOL_FUNCS + ai_core.execution.run + mcp_host.MCPExecutor",
            "permission": "policy_engine + permission_guard",
            "verification": "capability_os.verification",
            "events": "eventbus (SYSTEM_EVENT_NAMES) + SSE tool_start/tool_end",
        },
        "total": len(out_caps),
        "available": sum(1 for c in caps if c.available),
        "health_summary": {
            READY: statuses.count(READY),
            DECLARED: statuses.count(DECLARED),
            PARTIAL: statuses.count(PARTIAL),
            BLOCKED: statuses.count(BLOCKED),
            UNAVAILABLE: statuses.count(UNAVAILABLE),
            ERROR: statuses.count(ERROR),
        },
        "capabilities": out_caps,
        # —— Phase 41 新增出口（外部世界桥）——
        "mcp_servers": mcp.get("servers", []),
        "external_capabilities": mcp.get("external_capabilities", []),
        "mcp_summary": {
            "servers_total": mcp.get("total", 0),
            "servers_ready": mcp.get("ready", 0),
            "external_capabilities": len(mcp.get("external_capabilities", [])),
        },
    }


def verify_capabilities() -> dict:
    """运行时验证汇总（spec §8 / §17-E）。"""
    return {"summary": health_summary(), "capabilities": verify_all()}


def execute_capability(cap_id: str, args: Any = None, *,
                       auto_approve: bool = False, goal_id: int = None,
                       timeout: float = None) -> Any:
    """Phase 41 · 统一外部能力执行入口（仅 external.mcp.*）。

    纪律：所有 MCP 执行仍走既有单一执行链——
      tools.execute_tool → capability_os.execute_capability → mcp_host.MCPExecutor
      → MCP Host → MCP Server → 结果；权限经 policy_engine（§十三）。
    本函数只做「能力 id → MCP Executor」的路由，不复制、不绕过既有执行内核。
    """
    from .execution_mapping import get_executor
    ref = get_executor(cap_id)
    if ref is None or ref.kind != "mcp":
        return f"能力 {cap_id} 不是可执行的 MCP 外部能力（kind={getattr(ref, 'kind', None)}）"
    from mcp_host import execute_mcp_capability_sync
    return execute_mcp_capability_sync(
        cap_id, args or {}, auto_approve=auto_approve, goal_id=goal_id, timeout=timeout)


def invoke_capability(cap_id: str, args: Any = None, *,
                     auto_approve: bool = False, goal_id: int = None,
                     timeout: float = None) -> Any:
    """Phase B · 统一能力调用入口（产品化闭环）。

    纪律（严格，不新建第二执行系统）：
    - 所有执行委派既有单一执行链——
        tool / builtin / computer_action -> tools.execute_tool
            (C1 -> C2 policy_engine/permission_guard -> C3 eventbus -> C4 memory)
        mcp                            -> execute_capability（既有 Phase41 路径，含 policy_gate）
        context                        -> 只读上下文注入（非执行）
        umbrella                       -> 聚合型描述，不直执行
        none                           -> 永久拒绝声明（CRITICAL/未实现）
    - 本函数不复制、不绕过任何既有执行内核；invoke 层零内联执行逻辑。
    """
    from .execution_mapping import get_executor
    ref = get_executor(cap_id)
    if ref is None:
        return f"能力 {cap_id} 无执行体映射（未注册或未发现）"
    kind = ref.kind
    if kind == "mcp":
        return execute_capability(
            cap_id, args, auto_approve=auto_approve, goal_id=goal_id, timeout=timeout)
    if kind == "none":
        return f"能力 {cap_id} 为永久拒绝占位（CRITICAL/未实现），不可执行"
    if kind == "umbrella":
        return {
            "invoked": False, "kind": "umbrella",
            "note": "聚合型能力，请调用其下子能力", "ref": ref.ref,
        }
    if kind == "context":
        try:
            import capabilities as caps
            c = caps.CAPABILITIES.get(ref.ref)
            if c is not None and hasattr(c, "build_context"):
                return {"invoked": True, "kind": "context",
                        "context": c.build_context()}
            return {"invoked": False, "kind": "context",
                    "note": "无 build_context 方法"}
        except Exception as e:
            return f"上下文能力 {cap_id} 注入失败: {e}"
    # tool / builtin / computer_action -> 统一经 ai_core.execution.run（C1 单点汇聚，
    # Policy 闸门先裁决，再委派 tools.execute_tool）；R8-P0 严禁直连 execute_tool 绕过 Policy。
    tool_name = ref.ref
    try:
        from ai_core.execution import run as _execution_run
        return _execution_run(tool_name, {"args": args or {}}, allowed=None)
    except Exception as e:
        return (f"能力 {cap_id}（{kind}:{tool_name}）经 ai_core.execution.run 调用失败: {e}")


# 导入即构建（轻量、只读）
bootstrap()
