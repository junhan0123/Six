# S74 Structure Debt
## Xiao6 v1.0.0 Project Structure Analysis

---

## File Count Summary (G:/xiao6/xiao6-ui)

| Category | Count | Notes |
|----------|-------|-------|
| Python files | ~600+ | Core + tests |
| JavaScript files | ~100+ | Frontend + Electron |
| HTML files | ~20+ | UI entry points |
| CSS files | ~30+ | Stylesheets |
| JSON files | ~50+ | Config + data |
| MD documentation | ~200+ | Reports + docs |
| TXT files | ~30+ | Logs + temp |
| LOG files | ~20+ | Runtime logs |
| DB files | ~5+ | SQLite databases |
| Backup files | ~100+ | Migration/phase backups |
| Test files | ~50+ | Unit tests |

---

## Root Directory Analysis

### Top-Level Files (G:/xiao6/)
- VERSION, AI_BOOTSTRAP.md, LEGACY_NAME_REGISTER.md
- S72-*.md, S73-*.md, S74-*.md (audit reports)
- Desktop/, docs/, e2e/, knowledge/, scripts/

### Top-Level Directories
- xiao6-ui/ - Main application (600+ Python files)
- xiao6-desktop/ - Desktop app (pet/)
- xiao6-ui-new/ - Dead project (empty Git repo)
- _recycle_safety/ - Safety backups
- _ui_archive/ - UI archives

---

## Structure Debt Categories

### P0: Blocking (需立即处理)
无

### P1: High (应尽快处理)
- **release/config.py 端口不一致** ✅ 已修复
- **xiao6-desktop/pet/package.json 版本不一致** ✅ 已修复

### P2: Medium (计划处理)
- 历史报告中的 8000 端口记录（不改，仅记录）
- backup/*.migration-bak* 文件（保留，不入库）

### P3: Low (可选处理)
- _archive/, _verify/, _audit/ 目录整理
- xiao6-ui-new/ 归档

---

## Future Migration Plan (DEFERRED)

### Suggested Structure
```
xiao6/
├── backend/          # server.py, agent/, memory/, context/
├── frontend/         # electron/, css/, js/
├── tests/            # test_*.py
├── docs/             # PHASE-*.md, S*-*.md
├── scripts/          # launchers, tools
├── archive/          # backups, migrations
└── data/             # runtime data
```

### Why Deferred
1. 可能破坏现有 import paths
2. 可能影响 launcher 脚本
3. 可能影响 test discovery
4. S68-S73 已稳定运行，无回归风险
5. 当前结构虽乱但功能正常

**Recommendation**: STRUCTURE REFACTOR = DEFERRED TO S80+

---

## Recommendations

1. **保持现状**: 当前结构可运行，核心能力稳定
2. **文档先行**: 未来重构前先写 migration guide
3. **分批迁移**: 如要重构，每次只移一个模块
4. **保留备份**: 重构前做完整备份

---

END OF STRUCTURE DEBT
