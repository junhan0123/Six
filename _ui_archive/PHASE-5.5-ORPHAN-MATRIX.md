# PHASE 5.5 — ORPHAN AUDIT MATRIX (STEP 7)

> READ-ONLY / ZERO WRITE。仅记录，不修复。
> 区分：ACTIVE（生产在用）/ TEST（仅测试）/ ARCHIVE（已归档）/ DOCUMENTATION（仅文档引用）

## 1. TOOL ORPHAN（工具孤立）

**结论：无孤儿。**

- TOOLS=62（tools.py:76），TOOL_FUNCS=62（tools.py:3183），名称逐一对应、唯一。
- 每个工具经 `tool_to_capability` 都能解析到某 capability id：已知映射
  （execution_mapping.py:112 TOOL_TO_CAPABILITY：asr_transcribe→voice、memory_search→memory、
  set_goal→goals、get_hotspots→world_pulse、get_time→time、file_read→read_file、
  list_processes→list_process、scan_desktop→capture_screen、open_*/search/copy_text→computer_action、
  web_search/browser_read→tools）+ 兜底：未知工具→`tools` umbrella（execution_mapping.py:186）。
- 因此 **不存在「Tool→不存在 Capability」**（Q3=否）。

## 2. CAPABILITY ORPHAN（能力孤立）

**结论：无映射缺失；6 项为有意 BLOCKED，非孤儿。**

- 33 项 canonical capability **全部** 在 `CAPABILITY_EXECUTORS`（execution_mapping.py:43，33 条）有执行体映射 → `get_executor` 对 33 项均非 None。
- 6 项 `kind="none"`（delete/system/network/modify_file/execute_command/kill_process）为**有意**永久拒绝（CRITICAL/HIGH 占位），执行体即「无执行体」——这是安全设计，不是缺失。
- `focus_window` / `browser_navigate`：kind=computer_action，ref 在 `computer_action/safety.WHITELIST`（safety.py:28-36 **已包含**二者）。
  - ⚠️ execution_mapping.py:88-89 注释称「声明 MEDIUM，但不在 computer_action 白名单」——**注释陈旧错误**（见 P3）。实际 callable=True。
- **不存在「Capability→无 Tool/无 Executor/无 matcher/无 planner/不可触达」**（Q6=否，除有意 BLOCKED 外）。

## 3. FEATURE ORPHAN（功能孤立）

47 项 FEATURE_REGISTRY（zz-workspace.js:628-675）按 vis 分类：
- default(14)：web-ui / capabilities / memory / conversations / important-dates / notes /
  knowledge / tasks / goals / weather / hotspots / geo / briefing / agent-state
- advanced(16)：capability-os / asr-status / wakeword / system-prompt / user-model /
  personal-ai / episodes / perception-* / proactive-* / self-awareness / hud-state
- hidden(14)：start-all / avatar-ui / open-project / health / ready / boot-state / sysmon /
  logs / selfcheck / version / export-data / open-config / open-docs / github
- conditional(3)：calendar / focus-app / clipboard

**已知问题（非全部功能逐一 backend 校验，范围内发现）：**
- **`capabilities`（default）** → 读 `/api/capabilities`（deprecated）→ 仅 3 legacy 项。
  这是本审计核心 divergence（见 FINAL-AUDIT §核心断点）。功能本身 ACTIVE，但数据源错误（deprecated endpoint 仍是默认能力数据源）。
- **`capability-os`（advanced）** → `/api/capability_os/catalog`（33，正确）。ACTIVE 且正确。
- 其余功能（memory/knowledge/tasks/goals/weather/hotspots 等）均映射到真实 `/api/*` 端点，未发现 404/dead 引用。
- 未发现 Feature→纯 DOCUMENTATION/ARCHIVE 的孤儿（47 项均有对应渲染分支或 API）。

## 4. API ORPHAN（接口孤立）

| API | 生产者 | 生产消费者 | 状态 |
|-----|--------|-----------|------|
| `/api/capabilities` | server.py:471 | **DEFAULT `capabilities` feature**（zz-workspace.js:86/94/406/468/577/601/792） | ACTIVE（但 deprecated，返回 3） |
| `/api/capability_os/catalog` | server.py:489 | advanced `capability-os` feature (zz-workspace.js:717) | ACTIVE（33） |
| `/api/capability_foundation` | server.py:496 | **无 GUI 消费者**（grep `zz-workspace.js`+`index.html` 为空） | **API ORPHAN（P2）** |
| `/api/capability_os/match` | server_handlers_capability.py:48 | 未发现 GUI 消费者（可能为外部/测试用） | 疑似 ORPHAN（待定，未定罪） |
| `/api/capability_os/plan` | server_handlers_capability.py:66 | 未发现 GUI 消费者 | 疑似 ORPHAN（待定，未定罪） |

**`/api/capability_foundation`** 返回 33 canonical 富投影（foundation_view, __init__.py:121），
但**无任何生产 UI 消费**——属于「存在但无消费者」的 API 孤立。建议：要么接入 UI，要么标注为内部/调试接口。

## 5. 汇总表

| 类别 | 孤儿数 | 说明 |
|------|--------|------|
| TOOL | 0 | 62=62，全部可解析到 capability |
| CAPABILITY | 0（映射缺失）| 6 项有意 BLOCKED，非孤儿 |
| FEATURE | 0 | 但 `capabilities` 数据源错误（→divergence，P1） |
| API | 1（定罪）| `/api/capability_foundation` 无消费者（P2）；match/plan 疑似待定 |
