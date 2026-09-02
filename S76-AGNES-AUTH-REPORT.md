# S76 AGNES AUTH DIAGNOSTIC REPORT

## Diagnostic Steps

### Step 1: API Key Source
- Runtime reads from: `config.AGES_KEY` (env var `AGNES_API_KEY`)
- Config base URL: `config.AGES_BASE` (env var `AGNES_BASE_URL`)
- `.env` contains: `AGNES_API_KEY=***`, `AGNES_BASE_URL=https://api.agnes-ai.cn/v1`

### Step 2: Request Configuration
- Base URL: `https://api.agnes-ai.cn/v1`
- API path: `/chat/completions`
- Auth header: `Authorization: Bearer <key>`
- Model: `agnes-2.5-flash`
- Timeout: Default urllib timeout

### Step 3: Real API Request
```bash
curl -X POST https://api.agnes-ai.cn/v1/chat/completions \
  -H "Authorization: Bearer <redacted>" \
  -H "Content-Type: application/json" \
  -d '{"model":"agnes-2.5-flash","messages":[{"role":"user","content":"hi"}]}'
```

### Step 4: Response Analysis
- HTTP Status: **401 Unauthorized**
- Response body: `{"error":{"code":"","message":"无效的令牌 (request id: ...)","type":"AgnesAI_error"}}`

### Step 5: Root Cause Determination

**Category: G - External Service Refusal**

The API key exists and is structurally valid (starts with `sk-`), but the external service rejects it as invalid/expired.

### Possible Causes
1. API key rotated/expired on Agnes AI side
2. Key associated with different tenant/project
3. Base URL changed to `api.agnes-ai.cn` but key still valid on `apihub.agnes-ai.com`

### Decision
- NOT a code bug (server.py, config.py, llm.py all correct)
- NOT a config bug (base_url and key present)
- EXTERNAL DEPENDENCY FAILURE

## AGNES_AUTH_STATUS: EXTERNAL_DEPENDENCY_FAILURE

## Actions Taken
- Did NOT modify auth logic
- Did NOT hardcode new key
- Did NOT mock success response
- Did NOT bypass 401 check
- Documented as known limitation

## RECOMMENDATION
Rotate or regenerate AGNES_API_KEY from Agnes AI platform.
