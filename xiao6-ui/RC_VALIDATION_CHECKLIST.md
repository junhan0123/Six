# Xiao6 v1.0.0-rc1 RC Validation Checklist

**Base**: commit 93e2a6b, tag v1.0.0-rc1
**Date**: 2026-08-28
**Goal**: 验证真实使用体验，不扩展架构

---

## P0 - 阻塞发布

### 1. 启动链
- [ ] 服务能正常启动（端口 8000）
- [ ] `/api/health` 返回 200 + 完整状态
- [ ] 所有核心模块加载无致命错误

### 2. Agent Runtime ✅
- [ ] Goal System 能创建目标
- [ ] Goal 能进入执行状态
- [ ] Agent 闭环能运行（Intent → Plan → Execute → Observe）

### 3. Execution Core ✅
- [ ] 工具执行正常（get_time, calculator 等）
- [ ] Function Calling 闭环工作
- [ ] 结果能正确返回给 LLM

### 4. Policy FAIL CLOSED ✅
- [ ] 高危工具需要审批
- [ ] 低危工具可自动执行
- [ ] Policy Engine 正确拦截未授权操作

### 5. Failure Recovery ✅
- [ ] 执行失败时能重试或降级
- [ ] 异常状态能被捕获

### 6. Execution Trace ✅
- [ ] 每次执行有 trace_id
- [ ] 步骤可追溯

### 7. GoalSystem ✅
- [ ] 目标 CRUD 正常
- [ ] 状态流转正确（pending → running → completed）

### 8. IntentGateway ✅
- [ ] 短文本 → skip
- [ ] 长任务 → create goal

### 9. Approval Flow ✅
- [ ] 审批单能生成
- [ ] Handler 能 resolve
- [ ] per-goal 批准生效

### 10. zz-space UI ✅
- [ ] 前端页面可访问
- [ ] API 端点能响应

### 11. API Surface ✅
- [ ] `/api/chat` 可调用
- [ ] `/api/goals/*` CRUD 正常
- [ ] `/api/agent/*` 路由正确

### 12. 启动链 ✅
- [ ] 完整启动日志无崩溃
- [ ] 依赖项检查通过

### 13. 静态安全修复 ✅
- [ ] API Key 不暴露给前端
- [ ] 环境变量安全读取

### 14. VERSION/PORT 统一 ✅
- [ ] VERSION 文件 = 1.0.0-rc1
- [ ] 端口统一为 8000

---

## P1 - 影响体验

### 15. Chat 真实对话
- [ ] 发送消息能收到响应
- [ ] 响应内容合理
- [ ] 多轮对话 context 保持

### 16. 多步骤任务
- [ ] 复杂任务能分解执行
- [ ] 步骤间状态正确传递

### 17. Memory/Context 行为
- [ ] 记忆能保存和检索
- [ ] Context 注入正确

### 18. Tool 执行反馈
- [ ] 工具结果格式正确
- [ ] 错误信息清晰

### 19. 长任务稳定性
- [ ] 长时间运行不崩溃
- [ ] 内存使用可控

---

## P2 - 优化项（已知问题）

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| 1 | `vosk` 模块未安装 | KWS 语音唤醒不可用 | 已知限制，非阻塞 |
| 2 | `knowledge_runtime.cache.DocCache` 导入失败 | 知识索引不完整 | 核心功能不受影响 |
| 3 | `FEISHU_WS_URL` 未配置 | 飞书长连接跳过 | 预期行为 |
| 4 | `self_diagnosis.startup_check` 不存在 | 自检跳过 | 非致命 |
| 5 | `proactive_agent` 模块缺失 | 主动智能 V2 降级 | 配置开关可控制 |
| 6 | `beta_boot.mark_backend_ready` 不存在 | Beta Boot 跳过 | 非致命 |
| 7 | HOTDATA_KEY 未配置 | 热点数据源 401 | 非阻塞 |

---

## 测试命令

```bash
# 健康检查
curl -s http://127.0.0.1:8000/api/health | python -m json.tool

# 测试 Chat
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"你好"}]}'

# 查看 Goals
curl -s http://127.0.0.1:8000/api/goals | python -m json.tool

# 创建 Goal
curl -s -X POST http://127.0.0.1:8000/api/agent/goal \
  -H "Content-Type: application/json" \
  -d '{"title":"RC验证测试","description":"验证v1.0.0-rc1基线"}'
```

---

## 验收标准

- P0 全部通过 → 可以发布
- P1 有阻塞 → 打回修复
- P2 记录但不阻塞发布

---

## 执行记录

### 启动验证
```
[✓] Server started on http://127.0.0.1:8000
[✓] Health check: ok=true (partial - P2 issues)
[✓] Tools registered: 62
[✓] Agnes API: configured
[✓] TTS: edge-tts available
[✓] Weather: Open-Meteo OK
```

### 测试结果
(TODO: 补充实际测试结果)

---

## 结论

RC Validation: **IN PROGRESS**

下一步：
1. 执行 P0 全部测试用例
2. 执行 P1 体验测试
3. 记录 P2 已知问题
4. 出具最终验收报告
