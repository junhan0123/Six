# S73 Runtime Map
## Xiao6 v1.0.0 Runtime Dependency Analysis

---

## Runtime Critical (A)

| File/Module | Type | Status | Notes |
|-------------|------|--------|-------|
| server.py | Main entry | RUNTIME-CRITICAL | HTTP server, port 8010 |
| config.py | Config | RUNTIME-CRITICAL | ENV vars, no hardcoded secrets |
| agent/ | Agent system | RUNTIME-CRITICAL | S68-S71 core |
| agent_runtime.py | Runtime | RUNTIME-CRITICAL | Agent orchestration |
| context/facade.py | Context | RUNTIME-CRITICAL | S71 Prompt Architecture |
| memory/ | Memory | RUNTIME-CRITICAL | S68 Memory Verification |
| data/ | Data | RUNTIME-CRITICAL | Runtime storage |
| electron/ | Desktop | RUNTIME-CRITICAL | Electron entry point |
| launcher/electron-bin/ | Binary | RUNTIME-CRITICAL | Electron executable |

## Runtime Support (B)

| File | Type | Status | Notes |
|------|------|--------|-------|
| start-xiao6.bat | Launcher | RUNTIME-SUPPORT | Primary Windows launcher |
| start_xiao6.sh | Launcher | RUNTIME-SUPPORT | Linux/Mac launcher |
| start-server.sh | Launcher | RUNTIME-SUPPORT | Server-only startup |
| launcher/start.ps1 | Launcher | RUNTIME-SUPPORT | PowerShell launcher |
| first_launch.py | Setup | RUNTIME-SUPPORT | First launch wizard |

## Test Only (C)

| File | Type | Status | Notes |
|------|------|--------|-------|
| test_s68_capabilities.py | Test | TEST-ONLY | S68 regression |
| test_s69_session_integrity.py | Test | TEST-ONLY | S69 regression |
| test_s70_shared_context.py | Test | TEST-ONLY | S70 regression |
| test_s71_prompt_architecture.py | Test | TEST-ONLY | S71 regression |
| test_s62_configuration.py | Test | TEST-ONLY | Config validation |

## Documentation (D)

| Item | Type | Status | Notes |
|------|------|--------|-------|
| docs/ | Docs | DOCUMENTATION | Technical docs |
| PHASE-*.md | Reports | DOCUMENTATION | Phase completion reports |
| S72-*.md | Reports | DOCUMENTATION | Engineering baseline |
| S73-*.md | Reports | DOCUMENTATION | This audit |

## Historical (H)

| Item | Type | Status | Notes |
|------|------|--------|-------|
| backups/ | Backups | HISTORICAL | UI version backups |
| _archive/ | Archive | HISTORICAL | Archived code |
| _audit/ | Audit | HISTORICAL | Audit outputs |
| _verify/ | Verify | HISTORICAL | Verification outputs |
| *.migration-bak* | Backups | HISTORICAL | Migration snapshots |
| *.phase*-backup* | Backups | HISTORICAL | Phase backups |

## Backup (B)

| Item | Type | Status | Notes |
|------|------|--------|-------|
| .env.bak | Secret backup | SECRET-CONTAINING | Do not commit |
| .env.local.phase*-backup | Secret backup | SECRET-CONTAINING | Do not commit |
| config.py.phase*-backup | Config backup | HISTORICAL | Config versions |
| *.db.bak* | DB backup | HISTORICAL | Database snapshots |

## Unknown (U) - DO NOT MOVE

| File/Directory | Type | Status | Action |
|----------------|------|--------|--------|
| _recycle_safety/ | Safety | UNKNOWN | Keep, do not delete |
| knowledge_backup_*.db | DB | UNKNOWN | Potential runtime dependency |
| pending_proactive_backup_*.db | DB | UNKNOWN | Potential runtime dependency |

## Dead Project (D)

| Item | Type | Status | Action |
|------|------|--------|--------|
| xiao6-ui-new/ | Git repo | DEAD-PROJECT | SAFE-TO-ARCHIVE |

---

## Summary

- **Runtime Critical**: 9 items (core functionality)
- **Runtime Support**: 5 items (launchers)
- **Test Only**: 5 items (verification)
- **Documentation**: 4 categories
- **Historical**: 6 categories (preserved for recovery)
- **Backup**: 4 categories (secret-bearing or historical)
- **Unknown**: 2 items (keep, do not move)
- **Dead Project**: 1 item (safe to archive)

---

END OF RUNTIME MAP
