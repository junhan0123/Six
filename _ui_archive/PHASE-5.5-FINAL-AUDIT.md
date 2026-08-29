# PHASE 5.5 — FINAL AUDIT REPORT (CAPABILITY CONSUMPTION & ENTRY CONSISTENCY)

> 项目：小6 Xiao6 v1.4.0
> 阶段：PHASE 5.5（STEP 5→6→7 完成）
> 模式：READ-ONLY / VERIFY-BEFORE-DOCUMENT / ZERO WRITE / EVIDENCE-FIRST
> 日期：2026-08-19
> 纪律：完成审计后 STOP；不修复、不进入 PHASE 5.6、不修改任何生产代码。

---

## 0. VERDICT

```
Verdict      : COMPLETE / FINDINGS
TOOL         : 62 (全部存在于 TOOL_FUNCS)
CAPABILITY   : 33 canonical (live import 确认) + 3 legacy shim
FEATURE      : 47 (FEATURE_REGISTRY 数组)
P0           : 0   ← 无安全越界；BLOCKED 能力三重闸门全部命中，无危险执行路径
P1           : 1   ← 默认能力 UX 数据契约 / 入口一致性 divergence（3 vs 33）
P2           : 1   ← /api/capability_foundation 无生产消费者（API 孤立）
P3           : 1   ← execution_mapping.py 注释陈旧（focus_window/browser_navigate 已在白名单）
```

**裁决依据（section 15 五问）：**
- 实际用户影响：中（默认能力面板显示「能力 3 项」而非 33，误导但不崩溃）
- 数据契约错误程度：高（两个用户可见能力集合：默认 3 / 规范 33；deprecated endpoint 仍是默认数据源）
- 影响执行？**否**（执行走 tools.TOOL_FUNCS + policy_engine，独立于 snap.capabilities）
- 影响安全？**否**（P0=0）
- 仅 presentation？**不完全**——是真实的「入口/数据源不一致」（deprecated 端点仍为默认能力数据源），非纯 cosmetic。

→ 故定为 **P1**（应修，但非安全/执行破坏性缺陷）。

---

## 1. 已重新 VERIFY 的冻结基线（非盲信 handoff）

| 项 | 值 | 证据 |
|----|----|------|
| TOOLS | 62 | tools.py:76（列表 62 唯一 name） |
| TOOL_FUNCS | 62 | tools.py:3183 |
| READONLY_TOOLS | 28 | tools.py:3249 |
| CANONICAL CAPABILITIES | 33 | capability_os.registry **live import** = 33 |
| LEGACY CAPABILITIES | 3 | capabilities.py:20 CAPABILITIES={hotspot,prefetch,computer_action}; :23 LEGACY_COMPAT_SHIM=True |
| FEATURE_REGISTRY | 47 | xiao6-space/js/zz-workspace.js:628-675（数组，47 项） |
| 3 API | 确认 | server.py:471 /api/capabilities(deprecated) :489 /api/capability_os/catalog :496 /api/capability_foundation |

GUI 真实消费链（zz-workspace.js，handoff 引述行号全部命中）：
- L86 `getJSON('/api/capabilities')` → L94 `snap.capabilities = r[4].items` → 3 legacy
- L406「能力 N 项」/ L468 `renderCapabilities()` / L577 `snap.capabilities.slice(0,6)` / L601 `kvRow('能力登记', N+' 项')` / L792 filter
- L715-717 `FEATURE_API_MAP['capability-os'] = '/api/capability_os/catalog'`（advanced）

---

## 2. 12 问回答（section 16）

| Q | 问题 | 回答 |
|---|------|------|
|Q1|62 TOOL 全部存在于 TOOL_FUNCS？|**是**（62=62，名称唯一对应）|
|Q2|62 TOOL 全部有 Capability mapping？|**是**（经 tool_to_capability，未知→`tools` umbrella，无悬空）|
|Q3|是否存在 Tool→不存在 Capability？|**否**|
|Q4|33 Capability 全部有合法 registry entry？|**是**（live import 33 全在 _REGISTRY）|
|Q5|33 Capability 全部具真实 execution path？|**是**（27 可执行 + 6 有意 BLOCKED；无映射缺失）|
|Q6|是否存在 Capability→无 Tool/无 Executor？|**否**（get_executor 对 33 均非 None；6 项 none 为有意设计）|
|Q7|47 Feature 全部对应真实 backend？|**基本是**；`capabilities` 用 deprecated 端点（→divergence），其余映射真实 /api/*，未发现 404|
|Q8|是否仍存在 Feature→deprecated/404 API？|**是**——`capabilities` feature 用 deprecated `/api/capabilities`（核心 divergence）；无 404|
|Q9|/api/capabilities 当前多少 ACTIVE 生产消费者？|**≥1 ACTIVE 默认消费者**：DEFAULT `capabilities` feature（首页+能力视图）经 snap.capabilities 读取（L86/94/406/468/577/601/792）。这正是问题本身|
|Q10|catalog_view/foundation_view 严格来自 canonical=33？|**是**（catalog_view→get_groups/list_capabilities；foundation_view→verify_capability(get_registry)，均=33）|
|Q11|MCP 是否独立于 canonical 33？|**是**（MCP_EXECUTORS 独立 dict，execution_mapping.py:102；discovery.dispatch_tool_list 聚合 TOOL_FUNCS+external.mcp.*+skill:*，运行时发现，不在 33 内，按设计）|
|Q12|用户意图→execution 真实链路是否闭环？|**是**（Chat/ComputerAction/Goal 三路径均收敛到 ai_core.execution.run 的 policy 门→tools.execute_tool→verification；闭环确认）|

---

## 3. 核心断点（最大已知 divergence）

```
DEFAULT CAPABILITY UX           CANONICAL CAPABILITY UX
        ↓                                ↓
  /api/capabilities             /api/capability_os/catalog
  (deprecated, server.py:471)   (canonical, server.py:489)
        ↓                                ↓
  legacy 3 项                       canonical 33 项
  (hotspot/prefetch/               (voice/memory/knowledge/goals/
   computer_action)                 perception/21×computer_action/
                                     tools/world_pulse/user_model/
                     → 无 UI 消费者   self_diagnosis/time)
                                     ↑
                            /api/capability_foundation (33)
                                     → 无 UI 消费者 (P2)
```

**同一个产品存在两个用户可见能力集合：默认 3（legacy）vs 规范 33（canonical）。**
默认能力面板「能力 N 项」的 N=3，严重低估了产品真实能力面（33）。

---

## 4. P 级明细

### P0 = 0
无安全越界。BLOCKED 能力（delete/system/network/modify_file/execute_command/kill_process）
经三重闸门全部拦截（已 dry-run 实证）：
1. 语义层：matcher→blocked=True；router→safe_to_execute=False
2. 工具层：policy_engine.evaluate("file_delete"/"kill_process")→block（永久禁止名单）
3. 执行体层：execution_mapping kind="none"→executor_callable=False→verify BLOCKED
不存在「BLOCKED 能力落入危险执行路径」的断点。

### P1 = 1
**默认能力 UX 数据契约 / 入口一致性 divergence。**
- 现象：DEFAULT `capabilities` feature 读取 deprecated `/api/capabilities`（返回 3 legacy），
  呈现「能力 3 项」；CANONICAL 真相为 33（catalog/foundation）。
- 影响：用户/运营看到的默认能力面缺 30/33 项；误导但不影响执行与安全。
- 位置：server.py:471 + zz-workspace.js:86/94/406/468/577/601/792 + FEATURE_API_MAP:715-717。
- 处置：**仅记录，待老板授权后修复**（建议：默认能力数据源切到 /api/capability_os/catalog 或 foundation_view）。

### P2 = 1
**`/api/capability_foundation` 无生产消费者（API 孤立）。**
- 返回 33 canonical 富投影（foundation_view, __init__.py:121），但 GUI 无任何 getJSON 消费（grep 空）。
- 建议：要么接入 UI，要么标注为内部/调试接口。

### P3 = 1
**execution_mapping.py:88-89 注释陈旧。**
- 注释称 focus_window/browser_navigate「不在 computer_action 白名单」，
  但 computer_action/safety.py:28-36 的 WHITELIST **已包含二者** → 实际 callable=True。
- 仅文档/注释不一致，无执行风险。

---

## 5. 路径修正（相对 handoff 假设，已确证）

1. `matcher/router/compose` **不在** LLM 热路径；是 `/api/capability_os/match|plan` 的 API 级能力建议/编排服务。
2. `ai_core/execution.py` 实为包 `ai_core/execution/`，主入口 `api.py:31 run()`。
3. `zz-workspace.js` 真实路径 = `xiao6-space/js/zz-workspace.js`（handoff 写的 `xiao6-ui/zz-workspace.js` 已迁移）。
4. `read_file` 是 flat tool `file_read`（走 Chat 路径），非 computer_action 白名单 op；handoff 将其表述为 computer_action 不够精确。

---

## 6. 完成声明 / STOP

- STEP 0–7 全部完成，所有结论基于真实源码 + live import + 安全 dry-run。
- 未修改任何生产代码（tools.py / capabilities.py / capability_os/ / server.py / zz-workspace.js / agent_runtime.py / policy / runtime / config / 端口均未动）。
- 未删除/移动/重命名文件，未安装依赖，未修复发现的问题（RECORD-ONLY）。
- **STOP：等待老板授权后再决定是否进入 PHASE 5.6 及修复 P1（默认能力数据源切换）。**
