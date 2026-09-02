# Xiao6 v1.0.0-rc1 Product Acceptance Report

**版本**: v1.0.0-rc1  
**测试日期**: 2026-08-28  
**测试人员**: Hermes Agent (Agnes)  
**基线**: commit 93e2a6b, tag v1.0.0-rc1

---

## 执行摘要

| 维度 | 结果 |
|------|------|
| 自动化测试 | 89/89 PASS ✅ |
| 基础功能 | 部分通过 ⚠️ |
| 核心架构 | 正常 ✅ |
| 发布建议 | **有条件发布** ⚠️ |

---

## A. 基础 Agent 能力

### A1. 普通聊天
| 测试项 | 结果 | 说明 |
|--------|------|------|
| 自我介绍 | ✅ PASS | 响应正常，SSE 流式输出 |
| 简单对话 | ✅ PASS | "你好" 响应正确 |
| 英文对话 | ✅ PASS | "hello" 响应正确 |
| 复杂问题解释 | ⚠️ PARTIAL | 响应内容有时偏离主题 |

**发现问题**:
- **严重**: AI 身份错误 - 响应显示 "我是 Agnes，由 Sapiens AI 开发"，应为 "小6"
- **原因**: System Prompt 中 `AI_DISPLAY_NAME` 配置未生效或 LLM 未遵循

### A2. 多轮上下文
| 测试项 | 结果 | 说明 |
|--------|------|------|
| 多轮对话 | ❌ FAIL | 连续请求超时 |
| 上下文保持 | ❌ FAIL | 新会话无法读取历史记忆 |
| 编码处理 | ❌ FAIL | 中文响应出现乱码 |

**发现问题**:
- **严重**: 多轮上下文测试多次超时（15-30s）
- **原因**: LLM API 响应缓慢或 Agent Runtime 阻塞
- **严重**: Memory 数据库为空（0 条记录），记忆无法持久化

### A3. 任务理解
| 测试项 | 结果 | 说明 |
|--------|------|------|
| 模糊目标澄清 | ⚠️ PARTIAL | Intent Gateway 分类不准确 |
| Goal 生成 | ✅ PASS | 长任务正确创建 Goal |
| 意图分类 | ⚠️ PARTIAL | "帮我整理周报" 被分类为 skip 而非 create |

**发现问题**:
- **中等**: Intent Gateway 对中文长任务分类不稳定
- **中等**: 部分本应创建 Goal 的任务被误判为 skip

---

## B. Tool 执行能力

### B1. 查询时间
| 测试项 | 结果 | 说明 |
|--------|------|------|
| get_time | ✅ PASS | 工具执行成功，返回正确时间 |

### B2. 计算操作
| 测试项 | 结果 | 说明 |
|--------|------|------|
| calculator | ✅ PASS | 42×18=756，计算正确 |

### B3. 文件操作
| 测试项 | 结果 | 说明 |
|--------|------|------|
| file_read | ✅ PASS | 可列出目录内容 |
| file_write | ⚠️ PARTIAL | Goal 创建成功但执行状态卡住 |
| 危险操作拦截 | ❓ 未验证 | 测试被中断 |

### B4. 多步骤任务
| 测试项 | 结果 | 说明 |
|--------|------|------|
| 任务拆解 | ✅ PASS | 3-step goal 创建成功 |
| 执行进度 | ⚠️ PARTIAL | Goal #43 状态 active，progress 0% |
| 状态流转 | ⚠️ PARTIAL | 未见 completed 状态 |

**发现问题**:
- **中等**: Goal 创建后执行卡住，状态不流转
- **可能原因**: LLM API 限流（429）导致执行中断

---

## C. Memory 能力

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 写入长期记忆 | ❌ FAIL | 数据库 memories 表为空（0 条） |
| 查询记忆 | ❌ FAIL | 超时 |
| 新会话读取 | ❌ FAIL | 无历史记录 |
| remember 工具 | ✅ PASS | 工具调用成功，但未落库 |

**发现问题**:
- **严重**: Memory 系统未正常工作
- **原因**: `remember` 工具虽被调用，但未写入 `memories` 表
- **影响**: 用户无法持久化记忆，每次会话都是全新开始

---

## D. UI 能力

### D1. 前端资源
| 资源 | 状态 |
|------|------|
| `/zz-space/index.html` | ✅ 200 OK |
| `/zz-space/css/zz-workspace.css` | ✅ 200 OK |
| `/zz-space/js/zz-workspace.js` | ✅ 200 OK |

### D2. API 端点
| 端点 | 方法 | 状态 |
|------|------|------|
| `/api/health` | GET | ✅ 200 |
| `/api/goals` | GET | ✅ 200 |
| `/api/agent/state` | GET | ✅ 200 |
| `/api/memory/query` | POST | ✅ 200 |

### D3. Intent Gateway
| 测试项 | 结果 |
|--------|------|
| 长任务分类 | ⚠️ 不稳定 |
| 短任务分类 | ✅ 正确 skip |

### D4. SSE 实时事件
| 测试项 | 结果 |
|--------|------|
| tool_start/tool_end | ✅ 正常 |
| Goal 创建事件 | ✅ 正常 |
| 连接稳定性 | ⚠️ 偶发 ConnectionAbortedError |

---

## E. 稳定性

### E1. 连续运行测试（30s）
| 指标 | 结果 |
|------|------|
| 成功请求 | 部分 |
| 超时次数 | 多次 |
| 错误类型 | HTTP 429（限流） |

### E2. 服务器日志异常
```
[LLM HTTPError] provider=agnes attempt=0 code=429 reason=Too Many Requests
[LLM] 命中 429 限流，退避 8s 并临时降速心跳
ConnectionAbortedError: [WinError 10053] 你的主机中的软件中止了一个已建立的连接
```

**发现问题**:
- **严重**: Agnes API 免费版限流（429 Too Many Requests）
- **影响**: 高频请求时服务不可用
- **环境**: 测试环境 API Key 限额不足

---

## 问题分类汇总

### P0 - 阻塞发布（必须修复）

| # | 问题 | 类型 | 影响 |
|---|------|------|------|
| 1 | AI 身份错误（显示 Agnes 而非小6） | Bug | 用户体验严重受损 |
| 2 | Memory 系统未正常工作（memories 表为空） | Bug | 核心功能失效 |
| 3 | Agnes API 限流（429）导致服务不可用 | 环境问题 | 生产环境可能复现 |

### P1 - 影响体验（建议修复）

| # | 问题 | 类型 | 影响 |
|---|------|------|------|
| 4 | 多轮对话超时 | Bug | 用户体验差 |
| 5 | 中文响应乱码 | Bug | 可读性差 |
| 6 | Intent Gateway 分类不稳定 | 设计限制 | 任务创建不可预测 |
| 7 | Goal 执行状态卡住 | Bug | 任务无法完成 |

### P2 - 优化项（可延后）

| # | 问题 | 类型 | 影响 |
|---|------|------|------|
| 8 | vosk 模块未安装 | 环境限制 | KWS 不可用 |
| 9 | 知识索引加载失败 | Bug | 功能降级 |
| 10 | 热点数据源 401 | 环境问题 | 数据不完整 |

---

## 当前能力等级评估

### L1 - 基础可用（核心功能正常）
- ✅ HTTP 服务启动正常
- ✅ Health check 正常
- ✅ 简单聊天响应正常
- ✅ Tool 调用正常（get_time, calculator）
- ✅ Goal 创建正常
- ✅ 静态资源加载正常

### L2 - 核心功能受限（部分失效）
- ⚠️ Memory 系统未工作
- ⚠️ 多轮对话不稳定
- ⚠️ AI 身份标识错误
- ⚠️ API 限流影响可用性

### L3 - 高级功能缺失（未测试或失败）
- ❌ 记忆持久化
- ❌ 长任务完整执行
- ❌ 跨会话上下文保持

**综合评级**: **L1.5** - 基础功能可用，但核心体验缺陷明显

---

## 发布建议

### 可以发布给用户的功能
1. ✅ 简单对话（单次问答）
2. ✅ 工具调用（时间、计算）
3. ✅ Goal 创建与查询
4. ✅ 静态 UI 界面

### 不能宣传的功能
1. ❌ Memory 持久化（实际未工作）
2. ❌ 多轮对话（不稳定）
3. ❌ 长任务自动执行（经常卡住）
4. ❌ 跨会话上下文（未实现）

### v1.0.0 正式版前必须修复的问题

#### 必须修复（P0）
1. **AI 身份修复** - System Prompt 中 AI_DISPLAY_NAME 未生效
2. **Memory 系统修复** - remember 工具调用后未写入数据库
3. **API 限流处理** - 增加重试策略或切换付费计划

#### 应该修复（P1）
4. **多轮对话超时** - 排查 LLM 响应延迟原因
5. **中文编码问题** - 修复 SSE 响应编码
6. **Intent Gateway 优化** - 提高中文长任务分类准确率
7. **Goal 执行链修复** - 确保 goal 状态能正确流转至 completed

---

## 测试环境

| 项目 | 值 |
|------|-----|
| 操作系统 | Windows 11 |
| Python 版本 | 3.11.15 |
| 服务器端口 | 8000 |
| API 提供商 | Agnes (agnes-2.5-flash) |
| 测试时长 | ~20 分钟 |
| API 请求数 | ~50 次 |

---

## 附录：测试命令记录

```bash
# 启动服务器
python server.py > server_rc2.log 2>&1

# 健康检查
curl -s http://127.0.0.1:8000/api/health

# 简单聊天
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"你好"}]}'

# 查询 Goal
curl -s http://127.0.0.1:8000/api/goals

# 检查 Agent 状态
curl -s http://127.0.0.1:8000/api/agent/state

# 查看数据库
python -c "import sqlite3; conn = sqlite3.connect('zhuangzhou.db'); 
print(conn.execute('SELECT COUNT(*) FROM memories').fetchone()[0])"
```

---

Report generated: 2026-08-28 22:25
Tested by: Hermes Agent (Agnes)
