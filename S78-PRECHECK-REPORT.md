# S78 PRECHECK REPORT

## 1. Git Status
- Branch: `master`
- HEAD: `27aac02` Add S77 final summary
- Working tree: Clean (untracked report files only)
- Commits: 91a6fe6 → eadcb35 → 4a15830 → f5acc35 → d6d2f11 → 27aac02

## 2. Runtime Status
- Runtime: **STOPPED** (S77 进程已终止)
- Port: 8010 (available)
- Previous PID: `proc_e1df58292da1` (killed)

## 3. Provider Configuration

### A. API Key 来源
| 来源 | 状态 | Fingerprint |
|------|------|-------------|
| Environment Variable | ✅ SET | `sk-S68lp...4fj3` |
| .env file | ✅ SET | `sk-Rpu6g...WB4L` |
| **状态** | ❌ **都无效** | |

### B. Base URL
| 来源 | 值 |
|------|-----|
| config.py 默认 | `https://apihub.agnes-ai.com/v1` |
| .env / start_xiao6.sh | `https://api.agnes-ai.cn/v1` |
| Runtime 实际使用 | `https://api.agnes-ai.cn/v1` ✅ |

### C. Model
- `agnes-2.5-flash` ✅

## 4. Key 优先级链

```
启动脚本 unset AGNES_API_KEY
    ↓
load_env() 读取 .env → setdefault() 写入 os.environ
    ↓
reload() 从 os.environ 读取
    ↓
config.AGNES_KEY = AGNES_API_KEY
    ↓
llm.py resolve_provider() → Authorization: Bearer {AGNES_KEY}
```

**问题**: 当前 shell 已有 `AGNES_API_KEY` 环境变量（旧 Key），
`setdefault()` 不会覆盖，导致 Runtime 使用旧 Key 而非 .env 中的新 Key。

## 5. 当前环境状态

| 配置项 | 值 | 状态 |
|--------|-----|------|
| AGNES_BASE_URL | `https://api.agnes-ai.cn/v1` | ✅ 正确 |
| AGNES_MODEL | `agnes-2.5-flash` | ✅ 正确 |
| AGNES_API_KEY (ENV) | `sk-S68lp...4fj3` | ❌ 401 |
| AGNES_API_KEY (.env) | `sk-Rpu6g...WB4L` | ❌ 401 |

## 6. S77 状态继承
- 401 Fail-Fast 修复: ✅ 已提交 (`d6d2f11`)
- S68-S71 回归: ✅ 全部 PASS

---

**结论**: 
- 代码路径正确
- 配置结构正确
- **外部 Key 失效**（两个 Key 都已过期/无效）
