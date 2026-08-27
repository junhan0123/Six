# S75 Startup Report
## Xiao6 v1.0.0 Real Startup Validation

---

## Startup Test Results

### Test 1: Clean Start
| 项目 | 状态 | 数据 |
|------|------|------|
| Port 8010 | ✅ PASS | 关闭状态，可正常启动 |
| Python compile | ✅ PASS | server.py config.py llm.py provider_registry.py |
| Server start | ✅ PASS | PID 46392 |
| Health check | ✅ PASS | ok=true |
| Model loaded | ✅ PASS | agnes-2.5-flash |
| Tools registered | ✅ PASS | 66 tools |
| Memory loaded | ✅ PASS | Profile=0, Notes=1 |
| Sessions loaded | ✅ PASS | 3 sessions |
| Config loaded | ✅ PASS | All env vars resolved |

### Test 2: Health Check
```json
{
  "status": "alive",
  "ok": true,
  "model": "agnes-2.5-flash",
  "provider": "agnes",
  "key_present": true,
  "ai_name": "小6"
}
```

### Test 3: API Endpoints
| Endpoint | Status | Note |
|----------|--------|------|
| /api/health | ✅ 200 | ok=true |
| /api/sessions | ✅ 200 | 3 sessions |
| /api/config | ✅ 200 | Config loaded |
| /api/chat | ⚠️ 401 | LLM API key issue |
| /api/traces | ❌ 404 | Not implemented |
| /api/memory/write | ❌ 404 | Not implemented |

---

## Known Issues

### P2: LLM API 401
- **现象**: POST /api/chat 返回 401 Unauthorized
- **根因**: AGNES_API_KEY 配置但 API 调用失败
- **影响**: 对话功能不可用
- **建议**: 检查 Key 有效性或轮换 Key

---

## Startup Time
- Compile time: < 1s
- Load time: ~3s
- Total startup: ~5s

---

END OF STARTUP REPORT
