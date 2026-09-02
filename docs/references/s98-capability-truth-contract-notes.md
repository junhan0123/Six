# S98 Capability Truth Contract 统一

**日期**: 2026-09-02
**基线**: S97 (Capability Reality Matrix)

## 一、S98 目标

建立 Registry → Verification → Executor → Policy → Real E2E 的五层可信链，消除 Truth Gap。

## 二、核心方法论

### 2.1 Capability 分类框架

| 类别 | 定义 | 示例 |
|------|------|------|
| 独立 Capability | 产品级能力，有明确入口和返回值 | voice, memory, knowledge |
| 子能力/Action | 父能力的具体实现，可通过工具覆盖 | read_file → tool_file_read |
| 危险能力 | Policy 永久 BLOCKED | delete, system, network |
| 未实现 | 真正缺失或故意不实现 | modify_file, execute_command |

### 2.2 状态判定规则

```
READY = Registry可用 + Verification PASS + Executor可达 + Policy正常 + Real E2E PASS
PARTIAL = 部分功能缺失或降级（有明确原因）
BLOCKED = CRITICAL/HIGH 能力被 Policy 拒绝
NOT_IMPL = 真正不存在或故意不实现
```

### 2.3 Mock vs Real E2E

| 类型 | 判定标准 | 状态影响 |
|------|----------|----------|
| Real E2E | 真实调用返回有效数据 | READY/PARTIAL |
| Mock E2E | 仅 Mock 可用，真实引擎缺失 | PARTIAL |
| 缓存数据 | 外部源不可用但有缓存 | READY（注明缓存） |

## 三、S98 关键发现

### 3.1 工具覆盖的能力（4项 NOT_IMPL → READY）

| 能力 ID | 原状态 | 新状态 | 覆盖方式 |
|---------|--------|--------|----------|
| read_file | NOT_IMPL | READY | tool_file_read（沙箱内） |
| list_process | NOT_IMPL | READY | tool_list_processes（psutil） |
| hotspot | NOT_IMPL | READY | prefetch.get_valid_prefetch() |
| perception.ocr | NOT_IMPL | READY | RapidOCR 真实安装 |

### 3.2 依赖缺失的能力（2项保持 PARTIAL）

| 能力 ID | 状态 | 缺失依赖 |
|---------|------|----------|
| capture_screen | PARTIAL | capture_provider 模块缺失 |
| get_window_info | PARTIAL | perception 模块缺失 |

### 3.3 故意不实现的能力（6项 NOT_IMPL）

| 能力 ID | 原因 |
|---------|------|
| modify_file | HIGH风险，Policy BLOCKED |
| execute_command | HIGH风险，Policy BLOCKED |
| kill_process | HIGH风险，Policy BLOCKED |
| open_folder | 无 executor |
| open_file | 无 executor |
| search | 无 executor（web_search是不同能力） |

## 四、Verification 探针设计

### 4.1 子能力探针映射

```python
_SUB_CAPABILITY_PROBES = {
    "perception.screen": _probe_sub_capability,      # → os_bridge.vision_displays
    "perception.window": _probe_sub_capability,      # → os_bridge.action_observe
    "perception.ocr": _probe_sub_capability,         # → ocr_provider + RapidOCR
    "read_file": _probe_sub_capability,              # → tools.file_read
    "list_process": _probe_sub_capability,           # → tools.list_processes
    "hotspot": _probe_sub_capability,                # → prefetch.get_valid_prefetch
    "prefetch": _probe_sub_capability,               # → prefetch module
    # ... 更多映射
}
```

### 4.2 探针返回结构

```python
{
    "id": "capability_id",
    "status": "ready|partial|blocked|not_implemented",
    "error": "错误描述",
    "details": {
        "executor": "执行器路径",
        "real_e2e": "PASS|FAIL|BLOCKED",
        "mock_e2e": "PASS|N/A",
        "note": "补充说明"
    }
}
```

## 五、API Contract for WorkBuddy UI

### 5.1 已接入 API（13项）

```
GET  /api/version
GET  /api/ready
GET  /api/health
POST /api/chat
GET  /api/stream
GET  /api/tools/list
GET  /api/memory/profile
GET  /api/capability_os/catalog
POST /api/capability_os/match
POST /api/capability_os/plan
GET  /api/capability_os/foundation
GET  /api/capability_os/verify
GET  /api/weather
```

### 5.2 待接入 API（18项未接入）

```
GET  /api/knowledge/search    - 知识搜索
GET  /api/goals/list          - 目标列表
POST /api/goals/create        - 创建目标
GET  /api/hotspots            - 热点数据
GET  /api/briefing            - 简报
GET  /api/sysmon              - 系统监控
GET  /api/memory/notes        - 记忆笔记
POST /api/capability_os/action/execute - 电脑操作执行
GET  /api/vision/displays     - 屏幕信息
GET  /api/action/capabilities - 可用动作目录
```

## 六、最终状态

```
READY:      14 (voice, memory, knowledge, goals, computer_action, tools, 
               world_pulse, user_model, time, read_file, list_process, 
               perception.ocr, hotspot, prefetch)
PARTIAL:     6 (perception, self_diagnosis, capture_screen, get_window_info, 
               perception.screen, perception.window)
BLOCKED:     3 (delete, system, network)
NOT_IMPL:   10 (open_folder, open_file, search, copy_text, open_application, 
              focus_window, browser_navigate, modify_file, execute_command, kill_process)
ERROR:       0
```

## 七、S97 → S98 变化

| 能力 | S97 | S98 | 变化 |
|------|-----|-----|------|
| read_file | NOT_IMPL | READY | 工具覆盖 |
| list_process | NOT_IMPL | READY | 工具覆盖 |
| hotspot | NOT_IMPL | READY | prefetch覆盖 |
| prefetch | NOT_IMPL | READY | 新增探针 |
| capture_screen | PARTIAL | PARTIAL | 确认缺失 |
| get_window_info | NOT_IMPL | PARTIAL | 确认缺失 |

## 八、核心经验

1. **VERIFY-BEFORE-CHANGE**: 先确认现有实现再决定修复
2. **工具覆盖识别**: 很多 NOT_IMPL 实际由 tools.TOOL_FUNCS 覆盖
3. **Mock/Real区分**: 不能把 MockOcrProvider 当成 Real E2E
4. **缓存≠实时**: hotspots 缓存可用但外部源 401/502，需注明
5. **不要伪造**: 缺失依赖就标记 PARTIAL，不要强行 READY
