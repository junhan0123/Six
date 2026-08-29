# PHASE 5.5 · MAP-B — Capability → Execution 映射

> canonical 能力 = **33** 项。状态由 `verification.verify_capability` 真实链推导（静态复现：registry 元数据 + executor_callable 真实检查）。
> 状态分布：{'READY': 27, 'BLOCKED': 6}

| 能力 id | 名称 | group | risk | permission | available | executor.kind | executor.ref | callable | 状态 | 理由 |
|---|---|---|---|---|---|---|---|---|---|---|
| delete | 删除 | Computer Action | CRITICAL | block | False | none |  | False | **BLOCKED** | available=False or permission=block |
| execute_command | 执行命令 | Computer Action | HIGH | block | False | none |  | False | **BLOCKED** | available=False or permission=block |
| kill_process | 结束进程 | Computer Action | HIGH | block | False | none |  | False | **BLOCKED** | available=False or permission=block |
| modify_file | 修改文件 | Computer Action | HIGH | block | False | none |  | False | **BLOCKED** | available=False or permission=block |
| network | 网络操作 | Computer Action | CRITICAL | block | False | none |  | False | **BLOCKED** | available=False or permission=block |
| system | 系统操作 | Computer Action | CRITICAL | block | False | none |  | False | **BLOCKED** | available=False or permission=block |
| browser_navigate | 浏览器导航 | Computer Action | MEDIUM | confirm | True | computer_action | browser_navigate | True | **READY** | registered+callable+perm-ok |
| capture_screen | 截取屏幕 | Computer Action | LOW | auto | True | tool | scan_desktop | True | **READY** | registered+callable+perm-ok |
| computer_action | 电脑操作 | Computer Action | MEDIUM | confirm | True | umbrella | computer_action | True | **READY** | registered+callable+perm-ok |
| copy_text | 复制文本 | Computer Action | LOW | auto | True | computer_action | copy_text | True | **READY** | registered+callable+perm-ok |
| focus_window | 聚焦窗口 | Computer Action | MEDIUM | confirm | True | computer_action | focus_window | True | **READY** | registered+callable+perm-ok |
| get_window_info | 获取窗口信息 | Computer Action | LOW | auto | True | builtin | perception.get_state | True | **READY** | registered+callable+perm-ok |
| goals | 目标 | Goals | LOW | auto | True | tool | set_goal | True | **READY** | registered+callable+perm-ok |
| hotspot | 热点上下文 | World Pulse | LOW | auto | True | context | hotspot | True | **READY** | registered+callable+perm-ok |
| knowledge | 知识库 | Knowledge | LOW | auto | True | builtin | knowledge.search | True | **READY** | registered+callable+perm-ok |
| list_process | 列举进程 | Computer Action | LOW | auto | True | tool | list_processes | True | **READY** | registered+callable+perm-ok |
| memory | 记忆 | Memory | LOW | auto | True | tool | memory_search | True | **READY** | registered+callable+perm-ok |
| open_application | 打开应用 | Computer Action | MEDIUM | confirm | True | computer_action | open_application | True | **READY** | registered+callable+perm-ok |
| open_file | 打开文件 | Computer Action | MEDIUM | confirm | True | computer_action | open_file | True | **READY** | registered+callable+perm-ok |
| open_folder | 打开文件夹 | Computer Action | MEDIUM | confirm | True | computer_action | open_folder | True | **READY** | registered+callable+perm-ok |
| perception | 屏幕感知 | Perception | LOW | auto | True | builtin | perception.observe | True | **READY** | registered+callable+perm-ok |
| perception.ocr | 屏幕文字识别 | Computer Action | LOW | auto | True | builtin | perception | True | **READY** | registered+callable+perm-ok |
| perception.screen | 屏幕感知 | Computer Action | LOW | auto | True | builtin | perception.get_state | True | **READY** | registered+callable+perm-ok |
| perception.window | 窗口感知 | Computer Action | LOW | auto | True | builtin | perception.get_state | True | **READY** | registered+callable+perm-ok |
| prefetch | 预取背景（天气/新闻） | World Pulse | LOW | auto | True | context | prefetch | True | **READY** | registered+callable+perm-ok |
| read_file | 读取文件 | Computer Action | LOW | auto | True | tool | file_read | True | **READY** | registered+callable+perm-ok |
| search | 搜索文件 | Computer Action | LOW | auto | True | computer_action | search | True | **READY** | registered+callable+perm-ok |
| self_diagnosis | 启动自检 | Self Diagnosis | LOW | auto | True | builtin | self_diagnosis.run_check | True | **READY** | registered+callable+perm-ok |
| time | 时间 | Tools | LOW | auto | True | tool | get_time | True | **READY** | registered+callable+perm-ok |
| tools | 工具 | Tools | LOW | auto | True | umbrella | tools | True | **READY** | registered+callable+perm-ok |
| user_model | 用户画像 | User Model | LOW | auto | True | builtin | cognitive.user_model.load_user_model | True | **READY** | registered+callable+perm-ok |
| voice | 语音 | Voice | LOW | auto | True | tool | asr_transcribe | True | **READY** | registered+callable+perm-ok |
| world_pulse | 世界脉动 | World Pulse | LOW | auto | True | tool | get_hotspots | True | **READY** | registered+callable+perm-ok |
