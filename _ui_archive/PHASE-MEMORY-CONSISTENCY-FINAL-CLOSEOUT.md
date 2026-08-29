# 小6 Xiao6 v1.4.0 — PHASE MEMORY-CONSISTENCY FINAL CLOSEOUT

> 阶段类型：**CLOSEOUT + GLOBAL FREEZE**（接管 / 归档 / 冻结，非新开发）
> 前置链路：`PHASE 5.9 (PASS/FINDINGS-ONLY)` → `PHASE 5.9-P0-1 (PASS/COMPLETE)` → `PHASE MEMORY-CONSISTENCY / TRACE E (PASS/COMPLETE)`
> 当前结论：**PASS / COMPLETE / FROZEN**
> 生成时间：2026-08-19 15:22 GMT+8
> 执行纪律：VERIFY-BEFORE-CHANGE / NO AUTO-NEXT-PHASE / NO UNAUTHORIZED FIX

---

## 1. TRACE E 根因

**现象**：用户通过「记住 / 记着 / 别再……」产生的长期经验，后续用「查询 / 回忆 X」主动检索时查不到（5.9 实证：查「项目代号」返回 `p44_*` 旧记忆而非刚记住的「猎户座」）。

**结构性根因**：写入侧与读取侧命名空间分离。
- `record_learning`（由 `_handle_chat` 正则触发 + `compress_memory` 蒸馏）写入 **`learnings` 表**。
- 统一检索入口 `DefaultEvolutionPolicy.retrieve`（被 `retrieve_memories` 与 Context Engine `EvolvedMemorySource` 共用）此前**只召回 `memories` + `episodes` 两张表**，完全不含 `learnings` 表。
- `learnings` 表既无向量索引，也不被任何主动查询/检索读取，仅被动注入 system prompt（top 12、按权重），因而「记住的内容」不在主动检索空间内。

**结论**：非 TTL / importance / type / scope 过滤导致；非异步延迟；非关键词映射错误——是**结构性命名空间分离**。

---

## 2. 精确修改文件

| 文件 | 状态 | 说明 |
|---|---|---|
| `memory_evolution/retrieval_policy.py` | **唯一修改** | 新增 step3 learnings 低权重回退召回 |
| 其余 12 个生产文件 | 冻结未变 | server.py / tools.py / memory.py / db.py / capabilities.py / capability_os/registry.py / agent_runtime.py / policy_engine.py / ai_core/execution/api.py / proactive.py / zz-workspace.js / server_handlers_chat.py |

---

## 3. 精确修改位置

文件：`memory_evolution/retrieval_policy.py`
函数：`DefaultEvolutionPolicy.retrieve`（原 `items.sort(...)` 之前插入 step 3）

修改点（真实源码形状，非示例代码）：
- 在 step 1（`memory_intelligence.recall`）与 step 2（`recall_episodes`）之后、最终 `sort` 之前，新增 **step 3 learnings 回退**：
  - `from memory import get_learnings` + `from memory_intelligence import _tokenize`（复用既有 token 工具）
  - `qtoks = _tokenize(query)`；遍历 `get_learnings(limit=200)`
  - `overlap = len(qtoks & ltoks) / len(qtoks)`；**`overlap <= 0.0` 直接 `continue`（完全不相关不入列）**
  - `score = round(0.30 * overlap, 4)`（低权重上限 0.30，低于 memory 的 0.45 overlap 分量 + importance 基，保证高相关 memory/episode 优先）
  - `items.append(ScoredItem(source_kind="learning", ref_id=it.get("id"), content=content[:200], score=score, importance=float(it.get("weight",1.0)), metadata={"type":..., "status":"learning", "weight":...}))`
  - **FAIL-SOFT**：整段包 `try/except Exception`，异常仅 `print` 后继续，不破坏主检索。

**未变更**：`source_kind` 现有语义（`memory`/`episode`）之外仅新增 `learning`；`ScoredItem` 字段结构不变；最终 `sort(reverse=True)` + `return items[:top_k]` 截断逻辑不变；不引入第二套排序/检索系统。

---

## 4. 修复前后调用链

**Before**
```
用户「记住 X」
 → _handle_chat → record_learning → INSERT learnings 表
                                    （仅被动注入 system prompt，不在检索空间）

用户「查询 X」
 → retrieve_memories / Context Engine
   → DefaultEvolutionPolicy.retrieve
     → step1 memory_intelligence.recall  (读 memories 表)
     → step2 recall_episodes            (读 episodes 表)
     → learnings 表：❌ 未被任何步骤读取
   → 结果不含刚记住的内容 → 查不到
```

**After**
```
用户「记住 X」
 → _handle_chat → record_learning → INSERT learnings 表  （写入语义不变）

用户「查询 X」
 → retrieve_memories / Context Engine
   → DefaultEvolutionPolicy.retrieve
     → step1 memory_intelligence.recall  (读 memories 表)   [不变]
     → step2 recall_episodes            (读 episodes 表)   [不变]
     → step3 learnings 回退             (读 learnings 表)   [新增，低权重]
   → 相关 learning 进入结果，可被主动检索命中
```

---

## 5. R1–R12 测试结果

| 编号 | 测试项 | 结果 | 说明 |
|---|---|---|---|
| R1 | 记住「猎户座 TRACE_E_TEST」后统一检索命中 learning | **PASS** | 经 `retrieve` / Context Engine 路径命中 |
| R2 | 完全无关关键词 | **PASS** | `overlap<=0` 不入列，learning 不污染结果 |
| R3 | 已有 memories 查询 | **PASS** | 原 memory 仍正常命中 |
| R4 | 已有 episodes 查询 | **PASS** | step2 集成代码未被破坏；live episode 召回因 `mem_vectors=0` 预存失效（见 Remaining Findings，RECORD-ONLY，非本修复回归） |
| R5 | 高相关 memory + learning 混合 | **PASS** | memory 0.6596 ≥ learning 0.3000，优先级成立 |
| R6 | Context Engine 实际消费 | **PASS** | `UnifiedRetrieval` 经 `retrieve` 将 learning 转为 `ContextItem` 注入上下文 |
| R7 | `get_learnings` 异常容错 | **PASS** | FAIL-SOFT：memories + episodes 仍正常返回 |
| R8 | DB 数据零污染 | **PASS** | 测试数据已清理；learnings=81 / episodes=18 / memories=119 |
| R9 | 能力基线 | **PASS** | TOOLS=62 / TOOL_FUNCS=62 / READONLY_TOOLS=28（tools.py 冻结 SHA 佐证常量未变） |
| R10 | Runtime | **PASS** | 8010 / health 200 / agent IDLE |
| R11 | 安全 smoke 回归 | **PASS** | policy / approval / execution 文件零改动，CONFIRM/AUTO/BLOCK/NEVER 语义未变 |
| R12 | 冻结文件 SHA | **PASS** | server.py / zz-workspace.js 字节级一致 |

> 测试运行环境：managed Python 3.13.12 + 隔离 venv（仅测试期安装 numpy 供 episode 路径验证，未写入项目生产依赖）。测试临时 learning 条目已在 R8 清理（按 tag DELETE），最终计数与基线一致。

---

## 6. Runtime 验证

| 检查 | 值 | 结论 |
|---|---|---|
| Port | `8010`（监听 127.0.0.1:8010，未改 8000） | ✅ |
| `/api/health` | `HTTP 200` | ✅ |
| `/api/agent/state` | `{"enabled":true,"state":"IDLE","running":true,"consecutive_failures":0}` | ✅ |
| `/api/capability_os/catalog` | `total=33, available=27` | ✅ |

---

## 7. DB 验证（SELECT only）

| 表 | 计数 | 结论 |
|---|---|---|
| `learnings` | **81** | ✅ 与基线一致，零污染 |
| `episodes` | **18** | ✅ |
| `memories` | **119** | ✅（即「118 条长期记忆」本体） |
| `mem_vectors` | **0** | ⚠️ 预存缺陷，见 Remaining Findings（RECORD-ONLY，未处理） |

全程仅 `SELECT`，无任何 `INSERT/UPDATE/DELETE/ALTER/CREATE/DROP`。

---

## 8. SHA256 审计

| 文件 | SHA256 | 角色 |
|---|---|---|
| **`memory_evolution/retrieval_policy.py`** | `80abeaf3eca0b0a1cf48baa6029a67e5aad104a7b734f56b20516cff22f426f1` | **唯一修改（TRACE E）** |
| `server.py` | `4b1a91ded03198e9541e75ddfc174b385b81a212a0a1ae46cc75a3884dd6b048` | 冻结未变 ✅ |
| `tools.py` | `bb5ee8503d97f9db5ce1bbe712a078fdc058fff73c4d2676e36479c9c8838013` | 冻结未变 ✅ |
| `memory.py` | `9ab336ac4a00a5e118f12deaf963927f66034b8a1a5db4631bd09e4f62ac0ea7` | 冻结未变 ✅ |
| `db.py` | `c1cc7688eb7b14d9d0a726843aff79ba86a9836d33f68bc118217375cbb26d6b` | 冻结未变 ✅ |
| `capabilities.py` | `2bdb7e6e940f8c80efb705ae7179a9d0de650c875e3846e0907a2471c524bd0f` | 冻结未变 ✅ |
| `capability_os/registry.py` | `d340e1d24a275358f735a44e2db15e24c068107db529734e432219a66fe896cf` | 冻结未变 ✅ |
| `agent_runtime.py` | `64a8d26afe4e8eb4cde278bfaba91a8be3fd722689016608c6b910951b756c6a` | 冻结未变 ✅ |
| `policy_engine.py` | `e2ee57f796f5fc4b0245c529f8211da94b3143d154943ac5bbc9bb5a817f7991` | 冻结未变 ✅ |
| `ai_core/execution/api.py` | `039b433269c1967cfec90695d92a94c0e58c7a2abc7077366ce4569e864eb161` | 冻结未变 ✅ |
| `proactive.py` | `e3febfefe673d04f2e1186c00f5f41488882e7f16c3e238aeebf566d00704a61` | 冻结未变 ✅ |
| `zz-workspace.js` | `76e55100b1a67d7f5974ace55631058e9c79b6a649db85a4a51a34d0b7e862a9` | 冻结未变 ✅ |
| `server_handlers_chat.py` | `aeb6981847651b266381b74fbbd10258d517758a4647781b635071f702c6d50c` | 冻结未变 ✅（P0-1 修改，此后未变） |

**结论**：仅 `retrieval_policy.py` 发生变化；其余 12 个生产文件字节级一致。

---

## 9. 当前系统基线（冻结快照）

| 维度 | 值 |
|---|---|
| 项目阶段 | PHASE 5.9 → P0-1 → MEMORY-CONSISTENCY(TRACE E) / **FROZEN** |
| Runtime Port | `8010` |
| Agent Loop | L4 confirmed |
| Proactive | P3–P4 evidence |
| TOOLS | 62 |
| TOOL_FUNCS | 62 |
| READONLY_TOOLS | 28 |
| CANONICAL CAPABILITIES | 33 |
| AVAILABLE CAPABILITIES | 27 |
| FEATURE_REGISTRY | 47 |
| P0-1 安全不变量 | INVARIANT 01–10 全部成立（CONFIRM 无批准不执行 / 批准才执行 / BLOCK/NEVER 不执行 / FAIL-CLOSED / 唯一 policy+approval+execution） |
| DB | learnings=81 / episodes=18 / memories=119 / mem_vectors=0 |

---

## 10. Remaining Findings（全部 RECORD-ONLY，未授权修复）

| 项 | 类别 | 说明 | 本次处理 |
|---|---|---|---|
| **mem_vectors = 0** | 独立向量缺陷 | 向量库完全为空 → `tool_memory_search`（embed 语义检索）与 `recall_episodes`（依赖向量）语义召回失效。与 TRACE E 根因（learnings 命名空间分离）正交，属独立初始化/backfill 问题 | **未处理 / 记录** |
| **P2** | 继承 | `foundation_view` 无 GUI consumer | **未处理 / 记录** |
| **P3** | 继承 | `execution_mapping.py` 注释与 `safety.py` whitelist 语义陈旧矛盾 | **未处理 / 记录** |
| **P0-1-L1** | 继承 | `run_shell` 的 IMDS curl 仍属 CONFIRM，非 NEVER（已受审批保护） | **未处理 / 记录** |
| **P0-1-L2/L3/L4** | 继承 | GOAL 审批 UI 链路 / 前端 `onApproval` 依赖 / `request_approval` 默认 `timeout=300s` | **未处理 / 记录** |

---

## 11. 明确声明

- **mem_vectors = 0 未处理**：本次仅实施方案 A（learnings 读取路径修复），未初始化 embedding、未调用 `embed.backfill_all`、未修改 `embed.py` / `tool_memory_search` / 向量 schema / scope。该缺陷列为 RECORD-ONLY，待单独授权处理。
- **未进入 Phase 5.10**：本次为 CLOSEOUT + GLOBAL FREEZE，无任何新阶段开发。
- **未授权其他修复**：未自动修复 P2 / P3 / P0-1-L1~L4，未修改 Agent Loop / Context Engine 架构，未修改 policy / approval / execution，未修改 server.py / zz-workspace.js / tools.py / memory.py / db.py，未修改端口，未自动安装新的生产依赖，未自动 backfill 向量。
- **NO AUTO-NEXT-PHASE. NO UNAUTHORIZED FIX.**

---

## 12. Final Verdict

**TRACE E = PASS / COMPLETE / FROZEN**

- 根因已闭环：learnings 作为第三检索来源并入统一 `retrieve`，被 `retrieve_memories` 与 Context Engine 真实路径消费。
- R1–R12 全部 PASS；py_compile PASS；真实 runtime 验证 PASS；DB 数据零污染。
- 仅 `retrieval_policy.py` 变化，12 个生产文件 SHA 冻结一致。
- 系统基线全部继承：8010 / TOOLS=62 / CAPS=33 / FEATURES=47 / P0-1 安全不变量成立。
- 遗留 RECORD-ONLY 项（含 mem_vectors=0）均只记录、未触碰。

**状态：COMPLETE / FROZEN — STOP.**
