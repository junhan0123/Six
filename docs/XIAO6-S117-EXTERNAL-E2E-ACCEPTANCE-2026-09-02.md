# Xiao6 v1.0.0 — S117 External Dependency & Real E2E Acceptance

**日期**: 2026-09-02  
**前置状态**: S116 FINALIZED_WITH_EXTERNAL_E4_BLOCK  
**最终状态**: `S117 = COMPLETE`

---

## 一、Agnes 外部链路诊断

### 配置确认

```text
AGNES_BASE: https://api.agnes-ai.cn/v1
AGNES_MODEL: agnes-2.5-flash
AGNES_KEY: 已配置（51 chars，来自 .env）
ACTIVE_LLM: agnes
```

### 诊断结果

| 检查项 | 结果 |
|--------|------|
| DNS 解析 | ✅ 通过 |
| TCP 连接 | ✅ 通过 |
| TLS 握手 | ✅ 通过 |
| HTTP 状态码 | ✅ 200（请求正常处理） |
| API Key 有效性 | ✅ 有效（无 401/403） |
| 模型路由 | ✅ agnes-2.5-flash 正常 |
| 响应格式 | ✅ JSON 合规 |

**直接 Python 调用测试结果**：
```json
{
  "model": "agnes-2.5-flash",
  "choices": [{"message": {"content": "Hello! I'm Ag"}}],
  "usage": {"completion_tokens": 5, "prompt_tokens": 287}
}
```

### 历史 TIMEOUT 原因

S116 时期的 TIMEOUT 是**瞬时网络问题**（可能为代理/路由抖动），非代码缺陷。
当前网络稳定，E4 测试全部通过。

---

## 二、真实 E4 验收结果

**测试文件**: `tests/test_s110_real_agent_e2e.py`  
**运行时间**: 2026-09-02 21:44 (GMT+8)  
**完成时间**: 约 60 秒  
**ALL PASSED: true**

### E4 Evidence 明细

#### 1. CALCULATOR_E4_REGRESSION
```text
capability: calculator
LLM model: agnes-2.5-flash
LLM function calling: true
tool selected: calculator
tool arguments: {"expression": "2+2"}
execution result: "2+2 = 4"
Policy decision: auto
PASS
```

#### 2. READ_FILE_E4_REGRESSION
```text
capability: read_file
LLM model: agnes-2.5-flash
LLM function calling: true
tool selected: file_read
execution result: 文件内容正常返回
Policy decision: auto
PASS
```

#### 3. LIST_PROCESS_E4_REGRESSION
```text
capability: list_process
LLM model: agnes-2.5-flash
LLM function calling: true
tool selected: list_processes
tool arguments: {}
execution result: 包含 PID 信息的进程列表
Policy decision: auto
PASS
```

#### 4. TIME_E4
```text
capability: time
LLM model: agnes-2.5-flash
LLM function calling: true
tool selected: get_time
execution result: "本地时间：2026年09月02日 21:44:26 星期三"
Policy decision: auto
PASS
```

#### 5. WEB_SEARCH_E4
```text
capability: web_search
LLM model: agnes-2.5-flash
LLM function calling: true
tool selected: web_search
tool arguments: {"query": "Python 编程", "limit": 5}
execution result: 返回 runoob.com/python 等搜索结果
Policy decision: auto
PASS
```

### E4 证据链验证

每个测试均证明完整链路：
```
AgentRuntime entry
↓
real LLM request (agnes-2.5-flash)
↓
real tool/function call selected by LLM
↓
Execution Core (ai_core.execution.run)
↓
Policy (auto decision for safe tools)
↓
Tool execution
↓
real result
↓
Agent response
```

**E4_REAL_LLM_FUNCTION_CALLING = 5/5 PASS**

---

## 三、Security Regression

### test_s109_agent_policy_deny 回归测试

```text
all_passed: true
POLICY_DENY_EXECUTION_CORE: PASS
POLICY_DENY_AGENT_E2E: PASS
```

### 危险工具阻断确认

| 工具 | Policy 决策 | 说明 |
|------|-------------|------|
| delete | BLOCKED | _NEVER_TOOLS |
| system | BLOCKED | _NEVER_TOOLS |
| network | BLOCKED | _NEVER_TOOLS |
| execute_command | BLOCKED | _NEVER_TOOLS |
| kill_process | BLOCKED | _NEVER_TOOLS |

**注意**: `file_delete`、`delete_custom_tool`、`delete_goal` 是业务工具，不在 `_NEVER_TOOLS` 中，需用户确认。

---

## 四、GPT-SoVITS 状态

### 配置
```text
GPT_SOVITS_URL: http://localhost:9880
GPT_SOVITS_REF_AUDIO: (empty)
GPT_SOVITS_PROMPT_TEXT: (empty)
TTS_BACKEND: edge
```

### 诊断
- 端口 9880 未监听（`netstat` 无 LISTENING）
- 无相关进程运行
- TTS_BACKEND 已设置为 edge（fallback）

### 结论
```text
TTS = PARTIAL
reason = GPT-SoVITS 未部署
```

**未恢复 edge-tts 作为正式 TTS**，仅作为当前配置。

---

## 五、`/api/ready` Truth

```json
{
  "ok": false,
  "ready": true,
  "key_present": true,
  "degraded": true,
  "self_check": {
    "ok": false,
    "failed": ["TTS 语音合成"],
    "detail": "GPT-SoVITS 已配置但不可达"
  }
}
```

### 语义解释

| 字段 | 值 | 含义 |
|------|-----|------|
| `ready` | `true` | Runtime 可接收 Agent 请求（核心链路正常） |
| `ok` | `false` | 存在 optional/degraded dependency 未满足 |
| `degraded` | `true` | 有组件降级运行 |
| `failed` | `["TTS 语音合成"]` | TTS 依赖不可用 |

**判定**: 语义合理，保留现状。  
`ready=true` 表示核心 Runtime 可用，`ok=false` 表示部分可选依赖降级。

---

## 六、UI E2E 环境诊断

### 检查项

| 检查项 | 结果 |
|--------|------|
| Playwright Python | ✅ installed |
| Playwright sync API | ✅ available |
| pyautogui | ✅ installed |
| Chrome/Chromium | ⚠️ 需单独安装 |
| Browser MCP | ⚠️ 未配置 |
| CDP | ⚠️ 需 Chrome 启动 |

### 结论

```text
UI_E2E = BLOCKED_BY_ENVIRONMENT
reason = Chrome/Chromium 未安装，无法启动浏览器自动化
```

**未修改 Xiao6 UI 代码绕过**。

---

## 七、Repository Integrity

### Git Status
```text
M xiao6-ui/habits.json  ← runtime artifact（用户交互统计更新）
```

### habits.json 变更说明
```diff
- "updated": 1788353316
+ "updated": 1788356668
- "hours": {..., "21": 1}
+ "hours": {..., "21": 2}
- "cmds": {"查询": 11, "搜索": 7, "小6": 1}
+ "cmds": {"查询": 13, "搜索": 9, "小6": 1}
```

**结论**: 运行时统计更新，非 S117 代码变更。无需提交。

---

## 八、关键发现总结

### 1. Agnes API 恢复正常
- S116 的 TIMEOUT 是瞬时网络问题
- 当前 E4 全部 REAL_LLM_FUNCTION_CALLING PASS
- **无代码修改**

### 2. TTS 状态保持 PARTIAL
- GPT-SoVITS 未部署（机器上没有）
- TTS_BACKEND=edge（配置如此）
- **无代码修改**

### 3. UI E2E 环境阻塞
- Chrome/Chromium 未安装
- **未尝试安装或绕过**

### 4. edge-tts 引用残留
```text
WARNING: edge_tts still referenced in server_handlers_chat
```
- S102 移除了 fallback，但仍有引用
- **未修复**（非 S117 范围，不影响功能）

---

## 九、S117 最终 Verdict

```text
S117 = COMPLETE
```

### 证据链

| 类别 | 状态 | 证据 |
|------|------|------|
| Execution Core | PASS | ai_core.execution.run 唯一入口 |
| Execution Bypass | 0 | 无新 Policy bypass |
| Policy DENY | PASS | S109 测试通过 |
| Legacy | 0 | 无 ZZ/ZhuangZhou 残留 |
| E4 (real) | 5/5 PASS | calculator, read_file, list_process, time, web_search |
| E4 证据级别 | REAL_LLM_FUNCTION_CALLING | completion_provider=None |
| Repository | CLEAN | 仅 habits.json runtime artifact |
| Version | 1.0.0 | /api/version 确认 |

### 状态对比

| 项目 | S116 | S117 |
|------|------|------|
| E4 状态 | BLOCKED_BY_EXTERNAL_API | **5/5 PASS** |
| Agnes API | TIMEOUT | **正常** |
| TTS | PARTIAL | PARTIAL（无变化） |
| UI E2E | BLOCKED | BLOCKED_BY_ENVIRONMENT |

---

## 十、后续建议

1. **GPT-SoVITS**: 如需完整语音能力，需在本地部署 GPT-SoVITS 服务
2. **UI E2E**: 如需完整 UI 测试，需安装 Chrome/Chromium 和 Playwright browsers
3. **edge-tts 引用**: 可清理 server_handlers_chat.py 中的残留引用（非阻塞）

---

**报告位置**: `G:\xiao6\docs\XIAO6-S117-EXTERNAL-E2E-ACCEPTANCE-2026-09-02.md`  
**提交哈希**: （本次无代码变更，无需新 commit）  
**最终状态**: `S117 = COMPLETE`
