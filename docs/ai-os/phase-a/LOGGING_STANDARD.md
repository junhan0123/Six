# 小6 AI OS 2.0 — Phase A 任务九：统一日志标准（LOGGING_STANDARD）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务九（Unified Logging / 横切子系统）→ 输出本报告
> 上游: `CORE_AUDIT.md`（F5 特征开关不一致）、`CORE_LIFECYCLE_REPORT.md`（BOOT/RECOVERING/READY 状态广播）、`RECOVERY_REPORT.md`（恢复度量钩子）、`METRICS_REPORT.md`（结构化字段复用）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：建立 AI Core 统一的、结构化、可审计、隐私安全的日志标准，消除当前散落在各模块 `print(...)` 的不可控输出，为 Lifecycle / Health / Metrics / Recovery 四大横切子系统提供一致的观测面。

**关键边界**：
- 本任务是**横切子系统**（与 Lifecycle / Health / Metrics / Recovery 同级），属于 AI Core（L5）支撑能力，非 UI / Electron / Design 改动。
- **增量原则**：仅在既有 `print()` 调用点之上建立统一 `logging` 封装，**不改写业务逻辑**，不新增第二条输出通道（红线 ADR-001 单 Runtime、单进程）。
- **不在范围**：Knowledge/Memory 引擎日志（Phase B/C）；前端 JS 日志（属 Presentation Layer，另有规范）；日志上报远端（Local-First 原则，仅本地落盘 + stdout）。

---

## 2. 现状审计（已落地 vs 缺口）

### 2.1 已落地（无）

- **全项目零 `import logging`**：除 `xiao6-ui/python/Lib/` 下打包的 Python 标准库外（非业务代码），所有业务 `.py` 均无结构化日志框架。
- 观测完全依赖 `print()` 直写 stdout，无法按级别过滤、无法脱敏、无法聚合、崩溃时丢失上下文。

### 2.2 缺口（本任务补）

| 编号 | 缺口 | 证据 | 后果 |
|------|------|------|------|
| L1 | 无统一日志模块 | 无任何 `import logging` | 无法分级、无法检索、无法关联 |
| L2 | `agent_runtime.py` 散落 10 处 `[runtime]` 裸 print | 行 110/130/176/370/397/567/598/621/642/656 | 异常/事件失败被静默吞掉，无级别 |
| L3 | `server.py` 启动/恢复关键路径 6 处裸 print | 行 2604/2608/2632/2634/2691/2693 | 启动健康状态无结构化记录 |
| L4 | 敏感字段直出 | `server.py:2604` 仅 WARN 文案；`llm.py` / `asr.py` 等可能携带 key/内容 | 隐私合规风险（Local-First 红线） |
| L5 | `FEATURE_AGENT_RUNTIME` 默认值不一致 | `agent_runtime.py:11` 注释「默认 off」；`config.py:64` 默认 `True`；`config.py:233` env 默认 `"true"` | 文档与实装矛盾（**仅标记，不修改**，留待后续修正） |
| L6 | 日志与生命周期/事件无桥接 | 无 | 无法从日志反推内核状态机 |

**附：`agent_runtime.py` 待迁移的 10 处打印点**

| 行 | 原文片段 | 目标级别 | 脱敏 |
|----|----------|----------|------|
| 110 | `目标 #{goal_id} 执行异常: {e}` | ERROR | 否（goal_id 为内部 id） |
| 130 | `目标 #{goal_id} 拆解为空，跳过执行` | WARN | 否 |
| 176 | `连续 N 个 Goal 全部失败，清空队列` | WARN | 否 |
| 370 | `LLM 派发失败: {e}` | ERROR | 是（剥离响应体） |
| 397 | `汇报失败: {e}` | ERROR | 否 |
| 567 | `领域事件发布失败（已忽略）: {e}` | WARN | 否 |
| 598 | `Agent 领域事件发布失败（已忽略）: {e}` | WARN | 否 |
| 621 | `Task 领域事件发布失败（已忽略）: {e}` | WARN | 否 |
| 642 | `Memory 领域事件发布失败（已忽略）: {e}` | WARN | 否 |
| 656 | `Reflect 领域事件发布失败（已忽略）: {e}` | WARN | 否 |

---

## 3. 设计：统一日志模块 `ai_core/logging.py`

### 3.1 模块定位（红线 ADR-001 / ADR-006）

- 新建 `ai_core/logging.py`，**纯标准库 `logging`**，零第三方依赖、同进程、同 Runtime。
- 提供 `get_logger(name)` 工厂 + 全局 `configure_logging(level, log_file)` 初始化函数，由 `server.py` 在 `main()` 早期调用一次（与 Lifecycle 的 `boot()` 协同，不在其内新建子系统）。
- **禁止**创建第二个日志后端 / 异步日志进程 / 远端上报（Local-First + 单 Runtime）。

```python
# ai_core/logging.py（设计骨架，Phase A 实现落地）
import logging, json, os, re
from logging.handlers import RotatingFileHandler

_SENSITIVE_KEYS = ("AGNES_API_KEY", "API_KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE")
_KEY_RE = re.compile(r"(" + "|".join(_SENSITIVE_KEYS) + r")\s*[=:]\s*\S+", re.I)
_CONTENT_RE = re.compile(r"(user_message|prompt|content|system)\"?:.{0,200}", re.I)

def _redact(msg: str) -> str:
    """Local-First 隐私脱敏：密钥值、长文本体一律掩码。"""
    if not isinstance(msg, str):
        msg = str(msg)
    msg = _KEY_RE.sub(r"\1=***REDACTED***", msg)
    msg = _CONTENT_RE.sub(r"\1:***REDACTED***", msg)
    return msg

class _CoreFormatter(logging.Formatter):
    """结构化单行 JSON，便于本地 grep / 后续分析。"""
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "core_state": getattr(record, "core_state", None),
            "event": getattr(record, "event", None),
            "msg": _redact(record.getMessage()),
        }
        return json.dumps(payload, ensure_ascii=False)

def configure_logging(level=logging.INFO, log_file=None, max_bytes=5_000_000, backups=3):
    root = logging.getLogger("ai_core")
    root.setLevel(level)
    root.handlers.clear()
    sh = logging.StreamHandler()
    sh.setFormatter(_CoreFormatter())
    root.addHandler(sh)
    if log_file:  # Local-First：仅本地文件，不触网
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
        fh.setFormatter(_CoreFormatter())
        root.addHandler(fh)
    return root

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"ai_core.{name}")
```

### 3.2 日志级别

| 级别 | 数值 | 语义 | 示例 |
|------|------|------|------|
| DEBUG | 10 | 内核内部细节（队列长度、LLM 原始 token 计数） | `_queue` 快照 |
| INFO | 20 | 正常生命周期事件（启动、READY、恢复完成） | `Agent Runtime 已启动` |
| WARN | 30 | 可自愈的非致命异常（领域事件发布失败已忽略） | `连续 N 个 Goal 失败，清空队列` |
| ERROR | 40 | 需关注但内核存活的故障（LLM 派发失败） | `LLM 派发失败` |
| CRITICAL | 50 | 内核不可用 / 拒绝服务（DB 不可打开） | 触发 `STOPPING` |

### 3.3 结构化字段

每条日志固定携带：`ts`（ISO8601 本地时区）、`level`、`logger`（形如 `ai_core.runtime`）、`core_state`（可选，取自 Lifecycle 当前态）、`event`（可选，关联 `publish_system` 事件名）、`msg`（已脱敏）。JSON 单行输出，保证 stdout 与本地文件同构、可被简单 `grep`/`jq` 解析。

### 3.4 敏感字段脱敏（Local-First 红线）

- `_redact()` 强制掩码：`AGNES_API_KEY` / `API_KEY` / `TOKEN` / `SECRET` / `PASSWORD` / `COOKIE` 的赋值值。
- 对话 `user_message` / `prompt` / `content` / `system` 等长文本体截断掩码（保留字段名，抹去内容）。
- 文件绝对路径中的用户名段（`/Users/Administrator/...`）**不**脱敏（本地单用户，无跨用户泄露风险），但远端同步时由上游策略处理（不在本任务）。

### 3.5 与生命周期 / 事件总线桥接（F1 安全）

- 日志模块**不**自定义任何 SYSTEM 事件名。内核状态变化（BOOT/RECOVERING/READY/STOPPING）的对外广播**仍走既有** `publish_system("agent_state", {...})` 信封（见 `CORE_LIFECYCLE_REPORT` §7），日志仅作为该信封的**本地旁路镜像**。
- `core_state` 字段由 Lifecycle 在状态切变时通过 `logging.LoggerAdapter` 注入，**复用**同一信封语义，绝不复活/新增事件契约（F1 红线：SYSTEM namespace 不扩）。
- 度量字段（`recovery.count` 等，见 `METRICS_REPORT`）通过同一 JSON 信封的 `msg` 上下文承载，不与 Metrics 端点冲突。

### 3.6 迁移计划（增量、零逻辑改动）

**第一批（本任务设计，Phase A 实现落地）** — 仅替换打印、不改行为：

1. `server.py` 启动路径 6 处（2604/2608/2632/2634/2691/2693）→ `ai_core.server` logger：
   - 2604 `[WARN] 未检测到 AGNES_API_KEY` → `logger.warning(...)`（文案不打印 key 值，已脱敏）。
   - 2608 `[恢复] N 个被中断的多步任务已标记为可续` → `logger.info(..., extra={"event":"recover_tasks"})`。
   - 2632/2634 自检异常 → `logger.warning` / `exception`。
   - 2691 `Agent Runtime 已启动` → `logger.info(..., extra={"core_state":"ready"})`。
   - 2693 启动失败 → `logger.error(..., extra={"core_state":"stopping"})`。
2. `agent_runtime.py` 10 处（见 §2.2 表）→ `ai_core.runtime` logger，按目标级别映射；异常路径用 `logger.exception` 自动带 traceback。

**第二批（后续 Sprint，不在 Phase A）** — 其余散落 print（共 32 处 server.py + knowledge.py:8 / notes.py:11 / llm.py:5 / asr.py:4 / social_*:10 / 等）按相同工厂逐步替换，**不阻塞** AI Core 验收。

### 3.7 配置接入（`config.py`）

- 新增 `LOG_LEVEL: str = "INFO"`（env `LOG_LEVEL` 覆盖）、`LOG_FILE: str | None = "<datadir>/ai_core.log"`（env `LOG_FILE`，`None` 则仅 stdout）。
- `server.py:main()` 在 `listen()` 之后、`recover_tasks()` 之前调用 `configure_logging(config.LOG_LEVEL, config.LOG_FILE)`，**确保**恢复日志可被捕获（呼应 `RECOVERY_REPORT` G4 致命失败需有记录）。

---

## 4. 红线合规表

| 红线 | 判定 | 说明 |
|------|------|------|
| ADR-001 单 Runtime | ✅ 合规 | `ai_core/logging.py` 纯标准库、同进程，无第二后端 |
| 单状态写入入口 | ✅ 合规 | 日志只写本地文件/stdout，不写入 AppState/DB |
| 单 EventBus | ✅ 合规 | 不新增 SYSTEM 事件；状态广播复用 `publish_system("agent_state")` |
| 单 Permission | ✅ 合规 | 日志模块无权限判定，只读上下文 |
| F1 契约漂移 | ✅ 合规 | SYSTEM namespace 零扩展（仅信封旁路镜像） |
| Local-First | ✅ 合规 | 仅本地文件落盘，无远端上报、无网络触发 |
| 无 God Module | ✅ 合规 | 日志为横切工具，不持有核心状态/编排逻辑 |
| 增量演化 | ✅ 合规 | 仅包裹既有 print 点，不改写业务逻辑 |
| 无 UI/Electron/Design 改动 | ✅ 合规 | 纯后端 Python，前端零改动 |
| 提前实现 Knowledge/Memory 引擎 | ✅ 合规 | 不涉及 |
| F5 特征开关不一致 | ⚠️ 标记 | `FEATURE_AGENT_RUNTIME` 默认 off(注释) vs True(实装) — **仅标注，不修改**，归后续修正 |

---

## 5. STOP 声明

本报告为 **Phase A 任务九（Logging）** 的设计交付，属 AI Core 横切子系统。

- ✅ 已建立统一 `ai_core/logging.py` 设计：结构化 JSON、五级级别、敏感字段脱敏、Local-First 本地落盘。
- ✅ 已给出 `agent_runtime.py`（10 处）+ `server.py`（6 处）第一批迁移清单，增量替换、零逻辑改动。
- ✅ F1 安全：状态广播复用既有 `publish_system("agent_state")` 信封，不新增事件契约。
- ⚠️ F5 不一致仅标记不修正，归后续 Sprint。

**STOP —— 待人工 Review。未经批准不得：进入 Phase B、不得提前实现 Knowledge Engine、不得新增 AI 功能、不得扩大范围、不得修改 `FEATURE_AGENT_RUNTIME` 默认值（除非作为独立修正任务）。**
