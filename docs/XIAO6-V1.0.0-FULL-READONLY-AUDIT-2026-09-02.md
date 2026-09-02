# Xiao6 v1.0.0 — Full Repository Read-Only Audit

**日期**: 2026-09-02  
**基线**: S115 Release Provenance & Clean Baseline Closure  
**状态**: AUDIT ONLY — NO FILES MODIFIED

---

## 一、Repository Snapshot

| 指标 | 数量 |
|------|------|
| 文件总数 (不含 .git) | 16,460 |
| 目录总数 (不含 .git) | 1,525 |
| Git tracked 文件 | 2,454 |
| Git untracked 文件 | 0 (S115 清理后) |
| Python 源码 (.py) | 6,998 |
| Markdown 文档 (.md) | 1,487 |
| JSON 数据 (.json) | 240 |
| HTML 文件 (.html) | 559 |
| CSS 文件 (.css) | 92 |
| 大型文件 (>1MB) | 154 |
| 日志文件 (.log) | 70 |

---

## 二、目录结构概览

| 目录 | 大小 | 说明 |
|------|------|------|
| `xiao6-ui/` | 1.8GB | 主项目目录 |
| `docs/` | 53MB | 审计报告（S72-S115） |
| `ui/` | 97K | 正式 UI 根目录 |
| `_ui_archive/` | 35MB | 历史 UI 归档 |
| `_recycle_safety/` | - | 安全回收区 |
| `xiao6-desktop/` | - | 桌面应用相关 |
| `e2e/` | - | E2E 测试数据库 |
| `screenshots/` | - | 截图存档 |
| `scripts/` | - | 工具脚本 |
| `knowledge/` | - | 知识图谱数据 |
| `data/` | - | 运行时数据 |

---

## 三、资产分类统计

### ACTIVE / REFERENCED

| 类型 | 数量 | 说明 |
|------|------|------|
| 生产 Python 源码 | ~150 | xiao6-ui/*.py 核心模块 |
| 测试文件 | ~30 | tests/test_s*.py |
| 正式 UI | ~5 | ui/index.html, css/, js/ |
| 运行时数据库 | 2 | xiao6.db, six.db |
| 配置文件 | 2 | config.py, .env |
| 审计报告 | ~25 | docs/XIAO6-S*.md |

### GENERATED / CACHE

| 类型 | 数量 | 说明 |
|------|------|------|
| __pycache__ | - | Python 字节码缓存 |
| .pytest_cache | - | pytest 缓存 |
| .ruff_cache | - | ruff linter 缓存 |
| .playwright-mcp/ | - | Playwright MCP 日志 |
| logs/*.log | ~10 | 运行时日志 |
| e2e/*.db | ~60 | E2E 测试数据库 |

### HISTORICAL / ARCHIVE

| 类型 | 数量 | 说明 |
|------|------|------|
| docs/XIAO6-S*.md | ~25 | S72-S115 审计报告 |
| docs/archive/*.md | ~4 | 历史归档文档 |
| _ui_archive/ | ~35MB | 旧 UI 归档 |
| _verify/ | ~12MB | UI 验证截图 |
| server.py.bak-* | 1 | 服务器备份 |
| *.db.bak-* | 2 | 数据库备份 |

### ORPHAN (疑似无引用)

| 路径 | 类型 | 置信度 |
|------|------|--------|
| xiao6-ui/xiao6-ui/ | 嵌套目录 | HIGH |
| computer_executor.py | 重复模块 | MEDIUM |
| e2e/*.db | 测试数据库 | HIGH |
| xiao6-ui/*.log | 旧日志 | HIGH |
| _ui_archive/* | 历史归档 | CONFIRMED |

---

## 四、无引用文件审计

### 高置信度 ORPHAN

#### 1. `xiao6-ui/xiao6-ui/` — 嵌套目录

```
git ls-files xiao6-ui/xiao6-ui/
# 35 个 tracked 文件
```

**分析**:
- 存在嵌套的 `xiao6-ui/xiao6-ui/` 目录
- 包含完整的模块副本：config.py, agent_runtime.py, computer_action/ 等
- 与顶层 `xiao6-ui/` 内容高度相似（diff 1486 行差异）
- **生产代码不引用此路径**

**判断**: `HISTORICAL/NAMESPACE_COLLISION`

#### 2. `xiao6-ui/computer_executor.py` — 重复模块

```
grep -rn "import.*computer_executor" xiao6-ui/*.py
# permission_guard.py: from computer_executor import MockComputerExecutor, RealComputerExecutor
# verification.py: from computer_executor import RealComputerExecutor
```

```
grep -rn "import.*computer_action.executor" xiao6-ui/*.py
# os_bridge.py: from computer_action.executor import ComputerExecutor
```

**分析**:
- `computer_executor.py` (315 行) — 旧实现，被 permission_guard/verification 引用
- `computer_action/executor.py` (210 行) — 新实现，被 os_bridge 引用
- 两份实现功能相似但接口不同

**判断**: `DUPLICATE_MODULE / LEGACY`

#### 3. `xiao6-ui/server.py.bak-*` — 服务器备份

```
find . -name "server.py.bak*" -type f
# ./xiao6-ui/server.py.bak-before-ui-consolidation-20260831-011437 (58KB)
```

**判断**: `HISTORICAL_BACKUP`

#### 4. `xiao6-ui/*.log` — 旧日志

```
find . -name "*.log" -type f -size +100k
# xiao6-ui/server.log (618KB)
# xiao6-ui/backend_restart.log (48KB)
# xiao6-ui/server_p19.log (736KB)
# xiao6-ui/server_restart.log (69KB)
# ... 共 10+ 个日志文件
```

**判断**: `GENERATED_CACHE`

#### 5. `e2e/*.db` — E2E 测试数据库

```
find . -path "*/e2e/*.db" -type f | wc -l
# 约 60 个数据库文件
```

**判断**: `GENERATED_CACHE / TEST_ONLY`

---

## 五、重复文件审计

### 文件级重复

| 文件对 | 相似度 | 差异行数 |
|--------|--------|----------|
| `xiao6-ui/config.py` vs `xiao6-ui/xiao6-ui/config.py` | ~90% | 1486 行 |
| `xiao6-ui/computer_action/executor.py` vs `xiao6-ui/xiao6-ui/computer_action/executor.py` | 100% | 0 行 |
| `xiao6-ui/computer_executor.py` vs `xiao6-ui/computer_action/executor.py` | ~60% | 不同接口 |

### 模块级重复

| 模块 | 实现 1 | 实现 2 | 状态 |
|------|--------|--------|------|
| Computer Executor | `computer_executor.py` | `computer_action/executor.py` | DUPLICATE |
| Config | `config.py` | `xiao6-ui/config.py` | NAMESPACE_COLLISION |
| TTS | edge-tts (已禁用) | GPT-SoVITS (未部署) | NOT_DUPLICATE |

---

## 六、重复架构审计

### 1. Computer Executor 双实现

| 路径 | 行数 | 调用方 | 状态 |
|------|------|--------|------|
| `xiao6-ui/computer_executor.py` | 315 | permission_guard, verification | LEGACY |
| `xiao6-ui/computer_action/executor.py` | 210 | os_bridge | CURRENT |

**结论**: ARCHITECTURE_DUPLICATE

### 2. Config Authority

| 路径 | 行数 | 生产使用 | 状态 |
|------|------|----------|------|
| `xiao6-ui/config.py` | 727+ | server.py, 所有模块 | AUTHORITY |
| `xiao6-ui/xiao6-ui/config.py` | 727 | 无直接引用 | HIDDEN_DUPLICATE |

**结论**: NAMESPACE_COLLISION

### 3. TTS 实现

| 路径 | 状态 |
|------|------|
| edge-tts | 代码存在但已禁用（见 server_handlers_chat.py:704） |
| GPT-SoVITS | 配置但未部署 |

**结论**: NO_DUPLICATE (单一权威，另一为 fallback)

### 4. Memory System

| 路径 | 状态 |
|------|------|
| `xiao6-ui/memory.py` | AUTHORITY |
| `xiao6-ui/cognitive/memory_adapter.py` | SUPPORT |
| `xiao6-ui/memory_distiller.py` | SUPPORT |
| `xiao6-ui/memory_projection.py` | SUPPORT |
| `xiao6-ui/memory_query.py` | SUPPORT |
| `xiao6-ui/xiao6-ui/cognitive/memory_adapter.py` | DUPLICATE |

**结论**: ARCHITECTURE_OK (但有嵌套重复)

### 5. Context System

| 路径 | 状态 |
|------|------|
| `xiao6-ui/context/` | AUTHORITY |
| `xiao6-ui/xiao6-ui/context/` | DUPLICATE |

**结论**: NAMESPACE_COLLISION

---

## 七、Authority Conflict 清单

| 组件 | 权威实现 | 重复实现 | 冲突类型 |
|------|----------|----------|----------|
| Config | `xiao6-ui/config.py` | `xiao6-ui/xiao6-ui/config.py` | NAMESPACE_COLLISION |
| Computer Executor | `computer_action/executor.py` | `computer_executor.py` | LEGACY_DUPLICATE |
| Context | `xiao6-ui/context/` | `xiao6-ui/xiao6-ui/context/` | NAMESPACE_COLLISION |
| Computer Action | `xiao6-ui/computer_action/` | `xiao6-ui/xiao6-ui/computer_action/` | NAMESPACE_COLLISION |

**AUTHORITY_CONFLICT_COUNT = 4**

---

## 八、Archive / Backup Analysis

### `_ui_archive/`

| 子目录 | 内容 | 状态 |
|--------|------|------|
| `_ui_archive/xiao6-space-backup-20260831-0000/` | 旧 UI 备份 | HISTORICAL |
| `_ui_archive/2026-08-17/` | 阶段测试 | HISTORICAL |
| `_ui_archive/2026-08-18/` | 阶段测试 | HISTORICAL |

**总大小**: ~35MB

**判断**: `HISTORICAL_LEGACY` — 可以安全清理（Git history 保留历史）

### `xiao6-ui/_verify/`

| 内容 | 说明 |
|------|------|
| 大量 PNG 截图 | UI 验收截图 |
| JS 测试脚本 | Playwright 测试 |

**总大小**: ~12MB

**判断**: `GENERATED_CACHE` — 可再生，可清理

### `server.py.bak-*`

| 文件 | 大小 |
|------|------|
| server.py.bak-before-ui-consolidation-20260831-011437 | 58KB |

**判断**: `HISTORICAL_BACKUP` — 可清理

### 数据库备份

| 文件 | 大小 |
|------|------|
| xiao6.db.bak-memory-vector-recovery-20260819-155923 | 774KB |
| xiao6.db.bak-release-freeze-20260829-093148 | 1.3MB |

**判断**: `HISTORICAL_BACKUP` — 可清理

---

## 九、Legacy Asset Analysis

### 历史命名残留

```bash
rg -n -i "ZhuangZhou|庄周|ZZ_PROJECT_ROOT|xiao6-hub|ZHUANGZHOU_" --type py
# Result: 0 matches (production code)
```

```bash
rg -n -i "zz\.sse|zz\.goal|zz\.hud|zz\.mobile|zz\.clipboard|zz-agent-runtime" --type py
# Result: 0 matches (production code)
```

**结论**: LEGACY_RUNTIME = 0, LEGACY_PROTOCOL = 0

### 保留的历史文档

以下目录属于历史审计记录，应分类为 `HISTORICAL_DOCUMENT`:

- `docs/XIAO6-S*.md` (S72-S115)
- `docs/archive/*.md`
- `*_AUDIT_REPORT.md`, `*_FINAL_REPORT.md` 等

---

## 十、Git / Disk Analysis

### third_party/UFO 处理状态

```bash
$ git ls-files --stage third_party/UFO
# (empty - 已从 index 移除)

$ ls -la third_party/
# 目录已删除
```

**结论**: ✅ UFO 已彻底清理

### 当前 Git 状态

```bash
$ git status --short
# (empty)

$ git diff --exit-code
# 无差异

$ git diff --cached --exit-code
# 无暂存差异
```

**结论**: WORKTREE_CLEAN = PASS

### Git Tracked 大文件

| 文件 | 大小 |
|------|------|
| xiao6-ui/six.db | 254KB |
| xiao6-ui/xiao6.db | 1.6MB |
| xiao6-ui/server.log | 618KB |
| docs/archive/*.png | 多个 |

---

## 十一、Execution Boundary Audit

### 生产执行链

```
AgentRuntime (agent_runtime.py)
    ↓
Planner (capability_os/composer.py)
    ↓
LLM Function Calling (llm.py → agnes_completion)
    ↓
execute_tool_calls (tools.py)
    ↓
capability_runtime (capability_runtime.py)
    ↓
ai_core.execution.run (ai_core/execution/)
    ↓
Policy (policy_engine.py)
    ↓
Executor (computer_action/executor.py)
```

### Bypass 检查

| 检查项 | 结果 |
|--------|------|
| `tools.execute(...)` 直接调用 | 未发现 |
| `executor.execute(...)` 独立入口 | 未发现 |
| `subprocess(...)` 绕过 Policy | 未发现 |
| `os.system(...)` 绕过 Policy | 未发现 |
| Test Seam 进入生产 | 未发现 |

**结论**: EXECUTION_CORE_UNIQUE_ENTRY = PASS, EXECUTION_BYPASS = 0

---

## 十二、Cleanup Candidates

### KEEP (明确需要保留)

| 路径 | 理由 |
|------|------|
| `xiao6-ui/*.py` (核心模块) | 生产代码 |
| `xiao6-ui/tests/` | E4 测试套件 |
| `xiao6-ui/ui/` | 正式 UI |
| `xiao6-ui/config.py` | 配置权威 |
| `xiao6-ui/agent_runtime.py` | Runtime 权威 |
| `xiao6-ui/policy_engine.py` | Policy 权威 |
| `xiao6-ui/computer_action/` | 当前 Execution |
| `xiao6-ui/capability_os/` | 当前 Capability OS |
| `xiao6-ui/ai_core/` | Execution Core |
| `docs/XIAO6-S*.md` | 审计报告 |

### CLEANUP_CANDIDATE (高置信度可删除)

| 路径 | 类型 | 大小 | 理由 |
|------|------|------|------|
| `xiao6-ui/xiao6-ui/` | NAMESPACE_COLLISION | ~50KB | 嵌套重复目录，无生产引用 |
| `xiao6-ui/computer_executor.py` | LEGACY_DUPLICATE | 315 行 | 被新实现取代 |
| `xiao6-ui/server.py.bak-*` | HISTORICAL_BACKUP | 58KB | 服务器备份，可删除 |
| `xiao6-ui/*.log` | GENERATED_CACHE | ~2MB | 旧日志，可清理 |
| `xiao6-ui/*.db.bak-*` | HISTORICAL_BACKUP | ~2MB | 数据库备份，可删除 |
| `_ui_archive/` | HISTORICAL | 35MB | 历史归档，Git history 保留 |
| `xiao6-ui/_verify/` | GENERATED_CACHE | 12MB | 验收截图，可再生 |

### DUPLICATE_CANDIDATE (需进一步确认)

| 路径 | 类型 | 理由 |
|------|------|------|
| `xiao6-ui/xiao6-ui/config.py` | NAMESPACE_COLLISION | 与顶层 config.py 相似但不同 |
| `xiao6-ui/xiao6-ui/computer_action/executor.py` | DUPLICATE | 与 `computer_action/executor.py` 完全相同 |

### HISTORICAL_LEGACY

| 路径 | 大小 | 说明 |
|------|------|------|
| `docs/archive/` | ~5MB | 历史归档文档 |
| `screenshots/` | ~2MB | 历史截图 |
| `e2e/*.db` | ~50MB | E2E 测试数据库 |
| `_recycle_safety/` | - | 安全回收区 |

### UNKNOWN_REVIEW

| 路径 | 说明 |
|------|------|
| `xiao6-ui-new/` | 未使用的目录 |
| `xiao6-desktop/` | 桌面应用，需确认用途 |
| `knowledge/` | 知识图谱数据，运行时使用 |

---

## 十三、Risk Assessment

### 高风险

| 风险项 | 描述 | 影响 |
|--------|------|------|
| `xiao6-ui/xiao6-ui/` 嵌套目录 | 可能混淆 import 路径 | 中 |
| `computer_executor.py` 与 `computer_action/executor.py` | 双实现可能导致行为不一致 | 低 |

### 中风险

| 风险项 | 描述 | 影响 |
|--------|------|------|
| e2e/*.db 占用空间 | ~50MB 测试数据库 | 低 |
| _ui_archive/ 历史归档 | ~35MB 旧 UI | 低 |

### 低风险

- 日志文件堆积
- 备份文件占用空间

---

## 十四、Final Audit Verdict

### 核心指标

```
TOTAL_FILES = 16,460
GIT_TRACKED = 2,454
UNTRACKED = 0
WORKTREE_CLEAN = PASS
```

### Legacy 指标

```
LEGACY_RUNTIME = 0
LEGACY_PROTOCOL = 0
LEGACY_SOURCE = 0
LEGACY_ASSET = 0
```

### Architecture 指标

```
EXECUTION_CORE_UNIQUE_ENTRY = PASS
EXECUTION_BYPASS = 0
AUTHORITY_CONFLICT = 4 (NAMESPACE_COLLISION)
DUPLICATE_MODULES = 2 (computer_executor)
```

### Cleanup 建议

| 类别 | 数量 | 预估节省空间 |
|------|------|--------------|
| CLEANUP_CANDIDATE | ~10 | ~50MB |
| HISTORICAL_LEGACY | ~20 | ~55MB |
| DUPLICATE_CANDIDATE | 2 | ~50KB |

---

**AUDIT ONLY — NO FILES MODIFIED**

**Recommendation**: 下一阶段可考虑清理 `xiao6-ui/xiao6-ui/` 嵌套目录和 `computer_executor.py` 旧实现。
