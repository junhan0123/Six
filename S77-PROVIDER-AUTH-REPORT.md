# S77 PROVIDER AUTH REPORT

## Provider Configuration Chain

### Step 1: Environment Variables
```
.env: AGNES_API_KEY=*** (REDACTED)
.env: AGNES_BASE_URL=https://api.agnes-ai.cn/v1
.env: AGNES_MODEL=agnes-2.5-flash
```

### Step 2: config.py Loading
```python
AGNES_BASE = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1").rstrip("/")
AGNES_KEY = os.environ.get("AGNES_API_KEY", "")
AGNES_MODEL = os.environ.get("AGNES_MODEL", "agnes-2.5-flash")
```

### Step 3: provider_registry.py Mapping
```python
PROVIDER_SPECS["agnes"] = {
    "config_attrs": {"base": "AGNES_BASE", "key": "AGNES_KEY", "model": "AGNES_MODEL"},
    "env_keys": {"base": "AGNES_BASE_URL", "key": "AGNES_API_KEY", "model": "AGNES_MODEL"},
}
```

### Step 4: llm.py Authorization
```python
_headers["Authorization"] = "Bearer " + _key
req = urllib.request.Request(_base + "/chat/completions", ...)
```

## HTTP Request Diagnostic

### Actual Request
```
POST https://api.agnes-ai.cn/v1/chat/completions
Headers:
  Content-Type: application/json
  Authorization: Bearer sk-**** (REDACTED)
Body: {"model":"agnes-2.5-flash","messages":[...]}
```

### Response
```
HTTP 401 Unauthorized
Body: {"error":{"code":"","message":"无效的令牌 (request id: ...)","type":"AgnesAI_error"}}
```

## Root Cause Classification

| Check | Result |
|-------|--------|
| DNS resolution | ✅ PASS |
| TCP connection | ✅ PASS |
| TLS | ✅ PASS |
| HTTP Status | 401 |
| Key format | ✅ Valid (sk-*) |
| Base URL | ✅ Correct |
| Auth header | ✅ Correct (Bearer) |
| Model | ✅ agnes-2.5-flash |
| **Key validity** | ❌ INVALID/EXPIRED |

## Decision
- **CODE**: PASS — 所有代码路径正确
- **CONFIG**: PASS — 环境变量加载正确
- **NETWORK**: PASS — 连接正常
- **AUTH**: BLOCKED_EXTERNAL — API Key 已失效

## Fix Applied
Modified `llm.py`: 401 不再重试，立即失败
- Before: 3 retries × (2s, 4s) = ~14s timeout
- After: Immediate failure on 401

## RESULT: BLOCKED_EXTERNAL_AUTH
