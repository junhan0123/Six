# S75 Runtime Entry Map
## Xiao6 v1.0.0 Startup Path Analysis

---

## Entry Points Classification

### PRIMARY ENTRY
| 文件 | 路径 | 用途 |
|------|------|------|
| start-xiao6.bat | G:/xiao6/xiao6-ui/start-xiao6.bat | Windows 完整启动 |

### SECONDARY ENTRY
| 文件 | 路径 | 用途 |
|------|------|------|
| start_xiao6.sh | G:/xiao6/xiao6-ui/start_xiao6.sh | Linux/Mac 完整启动 |
| start-server.sh | G:/xiao6/xiao6-ui/start-server.sh | 仅启动 server |

### LEGACY ENTRY
| 文件 | 状态 |
|------|------|
| launcher/start.ps1 | 保留但不使用 |

### DEVELOPMENT ENTRY
| 文件 | 用途 |
|------|------|
| python server.py | 直接启动后端 |

---

## Startup Flow

```
User
  ↓
start-xiao6.bat
  ↓
Check port 8010 (socket connect)
  ↓
If not running: python server.py
  ↓
Wait for /api/health (max 15s)
  ↓
Start Electron desktop avatar
  ↓
Open browser http://localhost:8010/xiao6-space/index.html
```

---

## Runtime Components

| 组件 | 路径 | 状态 |
|------|------|------|
| Python server | server.py | ✅ 运行中 |
| Port | 8010 | ✅ 监听中 |
| Agent Runtime | agent/*.py | ✅ 加载 |
| Memory | memory.py | ✅ 可用 |
| Session | sessions.py | ✅ 可用 |
| Context | context/*.py | ✅ 可用 |
| Permission | permission_guard.py | ✅ 可用 |
| Trace | unified_trace.py | ✅ 可用 |

---

END OF RUNTIME ENTRY MAP
