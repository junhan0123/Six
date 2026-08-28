# S78 AUTH DIAGNOSIS REPORT

## 1. Key 注入链路追踪

### 完整链路
```
.env / 环境变量
    ↓
load_env(".env") → setdefault() 写入 os.environ
    ↓
reload() → 从 os.environ 读取 AGNES_API_KEY
    ↓
config.AGNES_KEY
    ↓
resolve_provider("agnes") → api_key
    ↓
llm.py agnes_completion() → Authorization: Bearer {api_key}
    ↓
POST https://api.agnes-ai.cn/v1/chat/completions
```

### 关键发现

**load_env() 使用 setdefault()**:
```python
def load_env(path=".env"):
    with open(path, encoding="utf-8") as f:
        for line in f:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)  # ← 只设置不存在的 key
```

**问题**: 如果环境变量已有 `AGNES_API_KEY`，`.env` 中的新 Key 会被忽略。

**start_xiao6.sh 修复**:
```bash
unset AGNES_API_KEY          # 清除环境变量
export AGNES_API_KEY="${AGNES_API_KEY:-}"  # 允许 .env 写入
```

**Windows 启动脚本未同步此修复**:
- `launcher/start_xiao6.bat` 没有 `unset AGNES_API_KEY` 逻辑
- 导致 Windows 环境下旧 Key 持续生效

---

## 2. Auth Probe 结果

### Case A: ENV Key (sk-S68lp...4fj3)
```
POST https://api.agnes-ai.cn/v1/chat/completions
Authorization: Bearer sk-S68lp...4fj3
Result: HTTP 401
Response: {"error":{"message":"无效的令牌 (request id: 202608280425309619013473KtAXNdx)"}}
```
**结论**: KEY_INVALID

### Case B: .env Key (sk-Rpu6g...WB4L)
```
POST https://api.agnes-ai.cn/v1/chat/completions
Authorization: Bearer sk-Rpu6g...WB4L
Result: HTTP 401
Response: {"error":{"message":"无效的令牌 (request id: 20260828042623234632917bjmIAN7n)"}}
```
**结论**: KEY_INVALID

---

## 3. 错误分类

| 检查项 | 结果 |
|--------|------|
| DNS | ✅ PASS |
| TCP | ✅ PASS |
| TLS | ✅ PASS |
| Base URL | ✅ 正确 |
| Authorization 格式 | ✅ Bearer token |
| Key 有效性 | ❌ 两个 Key 都无效 |
| Provider 端点 | ✅ 可达 |

**分类**: `EXTERNAL_AUTH_FAILURE`
**根因**: API Key 已过期/被吊销/无效

---

## 4. 代码路径验证

### Chat Handler
- ✅ 存在: `server_handlers_chat.py`
- ✅ 路由注册: `POST /api/chat`
- ✅ 调用链: `_handle_chat()` → `agnes_completion()`

### llm.py
- ✅ Provider resolution: `resolve_provider("agnes")`
- ✅ Auth header: `Authorization: Bearer {api_key}`
- ✅ 401 fail-fast: ✅ 已修复（不重试）

### Error Classification
- ✅ 401 → `AUTH_FAILURE`
- ✅ 429 → `RATE_LIMITED`
- ✅ 5xx → `PROVIDER_SERVER_FAILURE`

---

## 5. 结论

| 项目 | 状态 |
|------|------|
| 代码路径 | ✅ 正确 |
| Key 注入机制 | ✅ 正确（但 Windows 启动脚本需修复） |
| Auth Header | ✅ 正确构造 |
| Base URL | ✅ 正确 |
| Model | ✅ 正确 |
| **外部 Key** | ❌ **失效** |
| **Real Chat** | ⏸️ **BLOCKED_EXTERNAL_AUTH** |

---

**这不是代码 Bug，是凭证失效。**

需要用户从 Agnes AI 控制台获取有效 API Key 并更新 `.env`。
