# 03 · Phase 2 — Daily Workflow Simulation（每日工作流模拟）

> 专项：AI OS Alpha Stabilization Program v1.0
> 阶段：Phase 2 Daily Workflow Simulation
> 方法：隔离端口启动真实后端（Xiao6_PORT=8011），smoke 测试每日链路端点 + 真实模拟核心对话工作流
> 日期：2026-08-06
> 纪律：模拟/观察；修复留待 P6。

---

## 1. 模拟环境

- 启动：`python server.py`（系统 Python 3.11.9），端口 8011 隔离，避免影响用户既有 8000 实例。
- 自检（self_check）：`ok=true`，62 工具挂载，SQLite `xiao6.db` 就绪，Agnes 密钥已配置，知识索引 46 节点/35 关系校验通过，13 台设备已注册。

## 2. 端点 Smoke（每日链路后端腿）

| 端点 | 结果 | 说明 |
|------|------|------|
| `GET /` | ✅ 200，91,842 字节，DOCTYPE 正常 | 首页实体完整（非空白；curl 测 size=0 为测量怪象） |
| `GET /api/health` | ✅ `{"status":"alive","ok":true}` | 62 工具、46 知识节点、self_check 全 ok |
| `GET /api/config` | ✅ 200，返回 LLM/TTS/Feature 配置 | 运行时配置可读 |
| `GET /api/briefing` | ✅ 200 | 每日简报可用 |
| `POST /api/chat`（纯 LLM） | ✅ 返回流式内容 | 不触发工具时对话正常 |
| `POST /api/chat`（触发工具） | 🔴 **失败** | 见 §3 P0 |

## 3. 🔴 P0 — 核心每日旅程断裂（对话工具执行）

**现象**：任何触发工具调用的对话，后端返回
```
data: {"error": "run() takes 2 positional arguments but 3 were given"}
```
纯 LLM 对话（不调工具）正常，但凡涉及 `get_time`/`get_weather`/`reminder_set`/`file_*`/`set_goal` 等工具的消息全部失败。

**真实 traceback**：
```
File "tools.py", line 3286, in run_one
    return p, str(_execution_run(p["name"], p["args"], allowed))
TypeError: run() takes 2 positional arguments but 3 were given
```

**根因**：Execution Platform（Phase 3）将 `execute_tool` 调用统一改为 `_execution_run`（即 `ai_core.execution.run`）。但 `tools.py:3286` 写成
```python
_execution_run(p["name"], p["args"], allowed)   # allowed 为第 3 个位置参数
```
而 `Execution.run(name, args, *, allowed=None, ...)` 的 `allowed` 是**仅关键字参数**（keyword-only）。位置传入 3 个参数 → `TypeError`。

**影响范围（已界定）**：
- `execute_tool_calls` 仅被 `run_fc_loop`（对话路径）调用 → 仅对话工具执行受影响。
- 其余 `_execution_run` 调用点均合规：`agent_runtime.py:234`(2 参)、`reflector.py:89`(2 参)、`server.py:2008`(`allowed=` 关键字)、`social_inbound.py:125`(2 参)。
- 目标/复盘/社交入站路径不受影响。

**修复点（P6）**：单行修复 —— `tools.py:3286` 改为
```python
return p, str(_execution_run(p["name"], p["args"], allowed=allowed))
```

**严重度**：P0。小6的核心价值在于"对话→工具→结果"闭环；此缺陷使闭环在工具步断裂，**修复前无法每日使用**。

## 4. 次级观察（非阻塞）

| # | 观察 | 性质 |
|---|------|------|
| O1 | 后台线程 `_listen_loop_vosk` 抛 `FileNotFoundError`（VOSK 模型缺失） | 非致命；语音/唤醒词属 Mock 禁区，不影响文本对话 |
| O2 | 热点数据源外部 API 返回 502/404/405 | 服务端容忍并标记 OK；热点面板可能部分为空，不崩溃 |
| O3 | `self_check` 显示 `model: agnes-2.5-flash` | 运行配置；与文档 `agnes-2.0-flash` 描述不一致，但功能正常，仅记录 |

## 5. Phase 2 结论

⏳ **每日工作流模拟：后端/UI 托管/纯对话均可用，但「对话→工具」闭环因 P0 回归断裂。** 这是能否"每日使用"的决定性阻塞项，已精确定位为 `tools.py:3286` 单行签名不匹配，修复留 P6。

> 注：模拟期间启动的后端进程（端口 8011）将在 P4 后关闭；P6 修复后于 P7 重启做回归验证。

**进入 Phase 3：Workspace Stability。**
