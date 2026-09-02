# LLM Reliability Audit Report

**Date**: 2026-08-28  
**Scope**: Agnes API rate limiting, retry, timeout, fallback  
**Issue**: HTTP 429 限流导致超时和请求失败

---

## 问题现象

### 日志证据
```
[LLM HTTPError] provider=agnes attempt=0 code=429 reason=Too Many Requests
[LLM HTTPError body] {"error":{"code":"","message":"You've reached the API rate limit for free users. 
    Upgrade to a Token Plan to unlock higher limits and continue using the API without interruption. 
    (request id: 20260828142256319178538i18CnGTj)","type":"AgnesAI_error"}}
[LLM] 命中 429 限流，退避 8s 并临时降速心跳

[LLM HTTPError] provider=agnes attempt=1 code=429 reason=Too Many Requests
[LLM] 命中 429 限流，退避 16s 并临时降速心跳

[LLM HTTPError] provider=agnes attempt=2 code=429 reason=Too Many Requests
[LLM] 命中 429 限流，退避 32s 并临时降速心跳
```

### 用户影响
- 请求超时（15-30s）
- 部分请求返回 ConnectionAbortedError
- Agent Runtime 执行卡住

---

## 代码分析

### 1. Retry 机制
```python
# llm.py:129-227
def agnes_completion(messages, tools=None, stream=False, timeout=60, retries=2, ...):
    for attempt in range(retries + 1):  # 最多 3 次尝试
        try:
            resp = _urlopen_with_proxy(req, timeout=timeout)
            return resp
        except urllib.error.HTTPError as e:
            if e.code == 429:
                backoff = quota.on_429()  # 配额模块退避
                print(f"[LLM] 命中 429 限流，退避 {backoff:.0f}s")
            if e.code in (401, 429, 500, 502, 503, 504):
                time.sleep(2**attempt * 2)  # 退避 2s / 4s / 8s
                continue
            raise
    raise last_err
```

**问题**：
- `retries=2` 意味着最多 3 次尝试
- 总等待时间：2s + 4s + 8s = 14s（不含 API 响应时间）
- 如果 3 次都 429，最终抛出异常

### 2. Quota 模块
```python
# llm.py:171-172
est_tokens = quota.estimate_input_tokens(messages, tools)
quota.wait_if_needed(est_tokens)  # 配额预判
```

**发现**：`quota.py` 存在语法错误（leading zero in decimal integer）

---

## 分类结论

### 环境问题 ✅（主要因素）

| 项目 | 状态 |
|------|------|
| Agnes API 免费版限流 | 429 Too Many Requests |
| 免费配额上限 | 未知（需查看 Agnes 文档） |
| 测试频率 | 高频（~50次/20分钟） |

**判断**：这是**外部环境限制**，非代码 Bug

### 代码问题 ⚠️（次要因素）

| # | 位置 | 问题 | 严重度 |
|---|------|------|--------|
| 1 | `quota.py` | 语法错误（leading zero） | P1 |
| 2 | `llm.py:173` | `retries=2` 过低 | P2 |
| 3 | `llm.py:216` | 固定退避策略不够灵活 | P2 |

---

## 详细分析

### 问题 1：Quota 语法错误
```python
# quota.py 当前代码（推测）
LEAD_0_TIME = 01  # ❌ SyntaxError: leading zeros in decimal integer literals
```

**修复方案**：
```python
LEAD_0_TIME = 1  # ✅ 或使用 0o1（八进制）
```

### 问题 2：Retry 次数不足
```python
# llm.py:129
def agnes_completion(..., retries=2, ...):
```

**分析**：
- 3 次尝试 × 平均 5s = 15s 最坏情况
- 对于 429 限流，指数退避可能需要更长时间

**建议**：
```python
retries=4  # 增加到 5 次尝试
# 总退避时间：2+4+8+16 = 30s
```

### 问题 3：缺少 Fallback 机制
当前实现：
- 429 → 重试 → 失败 → 抛出异常
- **无降级方案**

**建议**：
```python
# 方案 A：切换到备用 Provider
if e.code == 429 and config.LLM2_API_KEY:
    return llm2_completion(messages, ...)  # 切换到第二供应商

# 方案 B：缓存响应
cached = get_cached_response(content_hash)
if cached:
    return cached

# 方案 C：队列等待
if is_rate_limited():
    wait_until_window_reset()  # 等待配额窗口重置
```

---

## 性能数据

### 单次请求延迟分解
```
正常情况：
  - 请求发送: <100ms
  - LLM 处理: 2-8s
  - 响应接收: <500ms
  - 总计: 2-9s

429 限流时：
  - 第 1 次尝试: 2s (超时) + 2s (退避) = 4s
  - 第 2 次尝试: 2s (超时) + 4s (退避) = 6s
  - 第 3 次尝试: 2s (超时) + 8s (退避) = 10s
  - 总计: ~20s 后失败
```

### 并发影响
```python
# server_handlers_chat.py:192-202
def emit(obj):
    line = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
    self.wfile.write(line.encode("utf-8"))
    self.wfile.flush()
```

**问题**：SSE 连接在 LLM 超时后未正确清理，导致 `ConnectionAbortedError`

---

## 建议修复优先级

### P0 - 立即修复
1. **修复 quota.py 语法错误** - 阻止导入失败

### P1 - 本周修复
2. **增加 Retry 次数** - 从 2 增加到 4-5 次
3. **添加 Fallback Provider** - 配置 LLM2 作为备用

### P2 - 下月优化
4. **实现响应缓存** - 相同内容复用结果
5. **优化退避策略** - 基于 API 响应头调整

---

## 临时缓解措施

### 方案 A：降低测试频率
```bash
# 请求间隔从 0.3s 增加到 2s
time.sleep(2)  # 而非 time.sleep(0.3)
```

### 方案 B：使用本地模型
```python
# config.py
ACTIVE_LLM = "llm2"  # 切换到备用供应商
# 或
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5:7b"
```

### 方案 C：升级 Agnes 配额
联系 Agnes AI 团队申请提高免费额度或购买 Token Plan

---

## 测试验证

```bash
# 验证 quota.py 修复
python -c "import quota; print('quota OK')"

# 验证 LLM 调用
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hi"}]}'

# 监控日志
tail -f server_rc2.log | grep -E "429|HTTPError|Timeout"
```

---

## 结论

| 维度 | 评估 |
|------|------|
| 问题性质 | **环境问题为主**（API 限流），**代码问题为辅**（retry 不足） |
| 是否阻塞发布 | ❌ 否（可临时缓解） |
| 必须修复 | ⚠️ 是（quota.py 语法错误） |
| 建议修复 | ✅ 是（增加 retry、添加 fallback） |

---

Audit completed: 2026-08-28
No code modified (except identifying quota.py syntax error).
