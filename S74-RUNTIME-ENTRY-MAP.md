# S74 Runtime Entry Map
## Xiao6 v1.0.0 Startup Analysis

---

## Entry Points

### Primary Windows Launcher
| 项目 | 值 |
|------|-----|
| 文件 | `start-xiao6.bat` |
| 路径 | `G:/xiao6/xiao6-ui/` |
| Python | `python server.py` |
| Port | **8010** |
| Electron | `launcher/electron-bin/electron.exe` |
| Hardcoded path | `G:\Xiao6` (local dev) |

### Linux/Mac Launchers
| 文件 | Port | 状态 |
|------|------|------|
| `start_xiao6.sh` | 8010 | ✅ |
| `start-server.sh` | 8010 | ✅ 已修复 |

### PowerShell Launcher
| 文件 | Port | 状态 |
|------|------|------|
| `launcher/start.ps1` | 8010 | ✅ |

---

## Runtime Flow

```
start-xiao6.bat
    ↓
Check port 8010 (socket connect)
    ↓
If not running: python server.py
    ↓
Wait for /api/health
    ↓
Start Electron desktop avatar
    ↓
Open browser http://localhost:8010/xiao6-space/index.html
```

---

## Port Consistency

| 来源 | 端口 | 状态 |
|------|------|------|
| config.py (module level) | 8010 | ✅ |
| config.py reload() | env 8010 | ✅ |
| server.py main() | config.PORT | ✅ |
| server.py fallback | 8010 | ✅ |
| start-xiao6.bat | 8010 | ✅ |
| start_xiao6.sh | 8010 | ✅ |
| start-server.sh | 8010 | ✅ |

**权威端口**: 8010

---

## Hardcoded Path Analysis

| 位置 | 硬编码路径 | 类型 |
|------|-----------|------|
| start-xiao6.bat L12 | `G:\Xiao6\xiao6-ui` | LOCAL-DEVELOPMENT-CONSTRAINT |
| start-xiao6.bat L49 | `G:\Xiao6\xiao6-ui\launcher\electron-bin\` | LOCAL-DEVELOPMENT-CONSTRAINT |
| start-xiao6.bat L19 | `%USERPROFILE%\.workbuddy\binaries\python\` | LOCAL-DEVELOPMENT-CONSTRAINT |

**结论**: 硬编码路径为本机开发约束，不改。

---

## Electron Version

| 组件 | 版本 |
|------|------|
| xiao6-ui/package.json | 31.0.0 (devDep) |
| xiao6-desktop/pet/package.json | 31.0.0 (devDep) |

**状态**: 版本一致，无 drift。

---

END OF RUNTIME ENTRY MAP
