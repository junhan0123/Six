# 10 · 开发者能力指南（Developer Capability Guide）— Stage J

> **以后任何 AI（Claude / Cursor / Codex / ChatGPT / Gemini / WorkBuddy）开始开发前，必须先阅读此文件 + `08_CAPABILITY_BOOK.md` + `01_CAPABILITY_INVENTORY.md`。**
> 目的：避免重复造轮子、误建第二执行/权限/事件系统、踩已知重复/死代码坑。

---

## 〇、必读前置（红线，违反即破坏架构）

1. **单一执行入口** = `ai_core.execution.run`（EXEC-01）。新增执行必须走它，**禁止**新建第二 Runtime/Execution/EventBus/Permission。
2. **真正实现** = `tools.execute_tool`（EXEC-02）。`Execution.run` 只路由+簿记，不重写。
3. **单一权限** = `PolicyEngine` + `PermissionGuard`（PERM）。电脑能力必须经 `PermissionGuard`，Agent **严禁直连 executor**。
4. **单一事件总线** = `eventbus`（DOMAIN=71 + SYSTEM=22）。新增领域事件须与前端 `zz-events.js` 逐字一致；telemetry 走 SYSTEM 通道（snake_case），**禁止**新增 DOMAIN 名（触碰前端红线）。
5. **Local First**：禁止云同步/上传；外部数据仅只读拉取。
6. **F1 契约不扩张**：DOMAIN 事件名集合冻结，新增须 Review。

---

## 一、能力真相来源（Single Source of Truth）

| 文档 | 用途 |
|---|---|
| `01_CAPABILITY_INVENTORY.md` | 全量能力字段表（ID/状态/入口/权限/flag/重复/风险） |
| `02_CAPABILITY_CLASSIFICATION.md` | 19 分类法（新增能力必须归类） |
| `03_ENTRY_MAP.md` | 所有入口（页面/指令/快捷键/API/自动） |
| `04_CAPABILITY_LIFECYCLE.md` | 生命周期标签 |
| `05_DUPLICATE_REPORT.md` | 重复清单（勿再复制） |
| `06_UNUSED_REPORT.md` | 死代码/孤儿（勿依赖、勿复活） |
| `07_CAPABILITY_GRAPH.md` | 依赖关系图 |
| `08_CAPABILITY_BOOK.md` | 人读说明书 |

---

## 二、新增能力的正确姿势

1. **归类**：先定 19 类之一（02）。
2. **入口**：UI 走现有指令中心/面板；API 走 `server.py` 路由（localhost 门控）。
3. **执行**：调用 `Execution.run(name, args, ...)`，不要自己 `execute_tool`。
4. **工具**：若新增 Tool，注册进 `tools.TOOLS`/`TOOL_FUNCS`，并标权限（remote_allowed / PolicyEngine）。
5. **权限**：电脑/高危 → 经 `PermissionGuard` + `CapabilityRegistry`。
6. **事件**：telemetry → `publish_system`（SYSTEM 通道）；领域事件 → 必须先改前端 `zz-events.js` 并 Review。
7. **文档**：同步更新 `01`/`08` 与本目录文档。

---

## 三、已知坑（务必避开）

### 重复坑（见 05）
- **勿新建 Toast/Overlay/Modal**：已有 `OverlayManager`（权威），遗留 11+ 套待迁移，再建即第 N+1 套重复。
- **天气**：勿再加第三套，`weather.py` 与 `geo_weather.py` 已重复。
- **KWS**：`kws`/`kws_optimized`/`wakeword` 已三文件，勿再加。
- **JSON 抽取**：`goals`/`gde`/`agent_runtime` 三份近似，抽公共工具前勿复制第四份。
- **人格**：`persona_engine`(稳定) vs `personality`(动态) 已并存，新增人格逻辑先确认归哪层。

### 死代码坑（见 06，勿依赖/勿复活）
- `personalization.py`（无调用）、`perception_*`(未接线)、`scheduler.py`(孤儿)、各类 `.tmp`/`.bak.zzstep1`/`_smts_append.py` 等。
- `FEATURE_PERCEPTION`（悬空）、`FEATURE_PROACTIVE_ENGINE`（幻影）——别引用未定义开关。

### 配置坑
- **`FEATURE_*` 声明默认 ≠ 运行时默认**：`config.py` 顶部常量多为 `False`，但 `reload()` 用 `os.environ.get("FEATURE_X","true")` 覆盖 → 绝大多数实际默认**开启**。判断默认行为以运行时为准。
- `LOW_RISK_TOOLS` 含幽灵名(`profile_read`/`profile_write`/`reminder_add`)——白名单未覆盖真实工具名。
- `_INTENT_TOOLS` 含幽灵别名 `session_run`——永不被命中。

### 架构缺口（勿误以为已实现）
- **Planner / Workflow**：仅蓝图，代码无独立模块。Goal 的"怎么做"由 `plan_goal`+`_llm_dispatch` 内联。
- **Electron**：**不存在**。无托盘/IPC/原生菜单。所有"桌面"是浏览器+http.server。
- **感知识别层**：UIA/OCR/Vision 全 Mock，真实识别未接。

---

## 四、能力自检接口（开发者用）

| 接口 | 用途 |
|---|---|
| `/api/capabilities` | 能力清单 |
| `/api/audit` | 工具审计日志 |
| `/api/models` / `/api/test-llm` | 模型/连通测试 |
| `selfcheck.html` + `self_check.py` | 启动自检 |
| `DEV-04` 工具工厂(默认 off) | 运行时建工具(实验) |

---

## 五、开发前 Checklist

- [ ] 读过 `01`/`08`/`02`，能力已归类。
- [ ] 未新建第二 Execution/Permission/EventBus/Runtime。
- [ ] 执行走 `Execution.run`；真正实现在 `execute_tool`。
- [ ] 未复制已有重复系统(Toast/Overlay/天气/KWS/JSON抽取)。
- [ ] 未依赖死代码/孤儿模块。
- [ ] 新 Tool 注册并标权限；新事件走正确通道。
- [ ] 同步更新能力平台文档。

> 本指南与 `08_CAPABILITY_BOOK.md` 是小6能力的**权威起点**。任何开发必先读，再动手。
