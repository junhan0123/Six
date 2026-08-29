# PHASE 5.5 — TOOL ↔ CAPABILITY MAP (TOOL-CAPABILITY-MAP)

> READ-ONLY / ZERO WRITE。数据来自真实源码 + live import（capability_os 注册表=33）+ execution_mapping。
> verify_status 由 verification.py 逻辑推导；标「待 live 确认」者为 builtin hasattr 未在本环境跑通（沙箱拦截 import）。

## A. TOOL 真相（tools.py）
- TOOLS = 62（tools.py:76，列表，62 个唯一 name）
- TOOL_FUNCS = 62（tools.py:3183，dict，键逐一对应）
- READONLY_TOOLS = 28（tools.py:3249）
- **62 个工具全部存在于 TOOL_FUNCS**（Q1=是）。

## B. 33 CANONICAL CAPABILITY → 执行体映射

executor 来源 = `capability_os.execution_mapping.CAPABILITY_EXECUTORS`（execution_mapping.py:43，33 条）。
exec_kind：tool | builtin | computer_action | context | umbrella | none

| cap_id | group | risk | perm | avail | exec_kind | exec_ref | callable | verify_status |
|--------|-------|------|------|-------|-----------|----------|----------|---------------|
| voice | Voice | LOW | auto | T | tool | asr_transcribe | T(在TOOL) | READY |
| memory | Memory | LOW | auto | T | tool | memory_search | T | READY |
| knowledge | Knowledge | LOW | auto | T | builtin | knowledge.search | T(知识.py:43) | READY |
| goals | Goals | LOW | auto | T | tool | set_goal | T | READY |
| perception | Perception | LOW | auto | T | builtin | perception.observe | 待live | READY/PARTIAL |
| computer_action | Computer Action | MED | confirm | T | umbrella | computer_action | T | READY |
| tools | Tools | LOW | auto | T | umbrella | tools | T | READY |
| world_pulse | World Pulse | LOW | auto | T | tool | get_hotspots | T | READY |
| user_model | User Model | LOW | auto | T | builtin | cognitive.user_model.load_user_model | T(user_model.py:62) | READY |
| self_diagnosis | Self Diagnosis | LOW | auto | T | builtin | self_diagnosis.run_check | 待live | READY/PARTIAL |
| time | Tools | LOW | auto | T | tool | get_time | T | READY |
| hotspot | World Pulse | LOW | auto | T | context | hotspot | T(in CAP) | DECLARED(context注入) |
| prefetch | World Pulse | LOW | auto | T | context | prefetch | T | DECLARED(context注入) |
| perception.screen | Computer Action | LOW | auto | T | builtin | perception.get_state | 待live | READY/PARTIAL |
| perception.window | Computer Action | LOW | auto | T | builtin | perception.get_state | 待live | READY/PARTIAL |
| perception.ocr | Computer Action | LOW | auto | T | builtin | perception | 待live | READY/PARTIAL |
| read_file | Computer Action | LOW | auto | T | tool | file_read | T | READY |
| capture_screen | Computer Action | LOW | auto | T | tool | scan_desktop | T | READY |
| get_window_info | Computer Action | LOW | auto | T | builtin | perception.get_state | 待live | READY/PARTIAL |
| list_process | Computer Action | LOW | auto | T | tool | list_processes | T | READY |
| open_application | Computer Action | MED | confirm | T | computer_action | open_application | T(白名单) | READY |
| open_folder | Computer Action | MED | confirm | T | computer_action | open_folder | T(白名单) | READY |
| open_file | Computer Action | MED | confirm | T | computer_action | open_file | T(白名单) | READY |
| search | Computer Action | MED | confirm | T | computer_action | search | T(白名单) | READY |
| copy_text | Computer Action | MED | confirm | T | computer_action | copy_text | T(白名单) | READY |
| focus_window | Computer Action | MED | confirm | T | computer_action | focus_window | T(白名单含) | READY |
| browser_navigate | Computer Action | MED | confirm | T | computer_action | browser_navigate | T(白名单含) | READY |
| modify_file | Computer Action | HIGH | block | F | none | — | F | BLOCKED |
| execute_command | Computer Action | HIGH | block | F | none | — | F | BLOCKED |
| kill_process | Computer Action | HIGH | block | F | none | — | F | BLOCKED |
| delete | Computer Action | CRITICAL | block | F | none | — | F | BLOCKED |
| system | Computer Action | CRITICAL | block | F | none | — | F | BLOCKED |
| network | Computer Action | CRITICAL | block | F | none | — | F | BLOCKED |

**统计**：33 项全部有 executor 映射（get_executor 无 None）。
- READY/可执行：27 项（含 context 注入型）
- BLOCKED（有意）：6 项（modify_file/execute_command/kill_process/delete/system/network）
- 无映射缺失 → **Q5=是（全部有真实执行路径或有意 BLOCKED）；Q6=否（无意外孤儿）**。

## C. Tool → Capability 逆向解析（tool_to_capability）

- 显式映射（execution_mapping.py:112）：asr_transcribe→voice、memory_search→memory、set_goal→goals、
  get_hotspots→world_pulse、get_time→time、file_read→read_file、list_processes→list_process、
  scan_desktop→capture_screen、open_application/open_folder/open_file/search/copy_text→computer_action、
  web_search/browser_read→tools。
- 其余 62 工具（calculator/remember/note_*/profile_*/reminder_*/file_*/task_* 等）→ 兜底 `tools` umbrella
  或同名 capability id（若 get_capability(name) 存在）。
- **所有 62 工具均可解析到一个已存在 capability（含 umbrella `tools`）→ 无悬空**（Q2=是，Q3=否）。

## D. context 注入型 vs 执行型
- `hotspot` / `prefetch` / `computer_action`(总览) 为 **context 注入**（非执行），经 capabilities.CAPABILITIES[id].build_context。
- 其余为真实执行体（tool/builtin/computer_action/umbrella）。
