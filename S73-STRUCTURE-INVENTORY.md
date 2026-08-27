# S73 Structure Inventory
## Xiao6 v1.0.0 Project Structure Audit

---

## File Statistics (G:/xiao6/xiao6-ui)

| Category | Count | Notes |
|----------|-------|-------|
| Python files | ~600+ | Core runtime + tests |
| JavaScript files | ~100+ | Frontend + Electron |
| HTML files | ~20+ | UI entry points |
| CSS files | ~30+ | Stylesheets |
| JSON files | ~50+ | Config + data |
| MD files | ~200+ | Documentation + reports |
| TXT files | ~30+ | Logs + temp |
| LOG files | ~20+ | Runtime logs |
| DB files | ~5+ | SQLite databases |
| Backup files | ~100+ | Migration/phase backups |
| Test files | ~50+ | Unit tests |

---

## Directory Structure

### Core Runtime
- `server.py` - Main HTTP server (UTF-8)
- `config.py` - Configuration (PORT=8010, no hardcoded secrets)
- `agent/` - Agent system (S68-S71 core)
- `ai_core/` - AI lifecycle management
- `context/` - Context engineering (S71)
- `memory/` - Memory system (S68)
- `data/` - Runtime data storage
- `electron/` - Desktop Electron app
- `launcher/` - Startup scripts

### Tests
- `test_s*.py` - S68-S71 test suites
- `test_s62_configuration.py` - Configuration tests

### Documentation
- `docs/` - Technical documentation
- `PHASE-*.md` - Phase completion reports
- `*.md` - Various audit reports

### Backups & Legacy
- `backups/` - UI backups
- `*.migration-bak*` - Migration backups
- `*.phase*-backup*` - Phase backups
- `_archive/` - Archive directory
- `_audit/` - Audit outputs
- `_verify/` - Verification outputs

### Dead Items
- `nul` - Empty file (deleted)
- `$null` - Empty file (deleted)
- `xiao6-ui-new/` - Empty Git repo (dead project)

---

## Runtime Critical Files

| File | Status | Notes |
|------|--------|-------|
| server.py | ✅ RUNTIME-CRITICAL | Main server, UTF-8 encoded |
| config.py | ✅ RUNTIME-CRITICAL | Config with env vars |
| agent/*.py | ✅ RUNTIME-CRITICAL | Agent system |
| start-xiao6.bat | ✅ RUNTIME-CRITICAL | Windows launcher |
| start_xiao6.sh | ✅ RUNTIME-SUPPORT | Linux/Mac launcher |
| start-server.sh | ✅ RUNTIME-SUPPORT | Server-only startup |

---

## Non-Critical (Safe to Archive)

| Item | Category | Action |
|------|----------|--------|
| nul | Dead artifact | ✅ Deleted |
| $null | Dead artifact | ✅ Deleted |
| xiao6-ui-new/ | Dead project | SAFE-TO-ARCHIVE |
| *.migration-bak* | Historical | Keep for recovery |
| *.phase*-backup* | Historical | Keep for recovery |
| _archive/ | Historical | Keep |
| _verify/ | Historical | Keep |
| _audit/ | Historical | Keep |

---

## Notes

1. **No mass migration** - Structure preserved as-is
2. **Historical reports unchanged** - PHASE-*.md files preserved
3. **Legacy names retained** - ZHUANGZHOU_* env vars documented
4. **Port unified** - All references now use 8010
5. **Secrets removed** - No hardcoded keys in tracked files

---

END OF INVENTORY
