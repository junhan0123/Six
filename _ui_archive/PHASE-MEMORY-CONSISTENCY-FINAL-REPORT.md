# PHASE MEMORY-CONSISTENCY — FINAL REPORT

**项目**：小6 Xiao6 v1.4.0
**阶段**：PHASE 5.9 (PASS/FINDINGS-ONLY) → PHASE 5.9-P0-1 (PASS/COMPLETE) → **PHASE MEMORY-CONSISTENCY (TRACE E)**
**状态**：✅ PASS / COMPLETE / STOP
**授权范围**：仅 TRACE E 记忆一致性修复【方案 A】——单文件、最小读取路径修复
**实施纪律**：VERIFY-BEFORE-CHANGE → BASELINE → MINIMAL-DIFF → IMPLEMENT → PY_COMPILE → TEST → RUNTIME VERIFY → SHA256 AUDIT → REPORT → STOP
**修改文件**：仅 `memory_evolution/retrieval_policy.py`（1 个文件）

---

## 1. Baseline（实施前冻结基线，全部继承）

| 项 | 值 | 复核 |
|---|---|---|
| Runtime Port | 8010 | ✅ 未变 |
| Agent Loop | L4 | ✅ 未变 |
| Proactive | P3–P4 | ✅ 未变 |
| TOOLS / TOOL_FUNCS / READONLY_TOOLS | 62 / 62 / 28 | ✅ tools.py SHA 字节级一致 |
| CANONICAL / AVAILABLE CAPABILITIES | 33 / 27 | ✅ runtime catalog 实测一致 |
| FEATURE_REGISTRY | 47 | ✅ zz-workspace.js SHA 一致 |
| DB 计数 | learnings=81 / episodes=18 / memories=119 / mem_vectors=0 | ✅ SELECT 复核 |
| server.py / zz-workspace.js | 冻结 | ✅ SHA 未变 |

---

## 2. Root Cause（根因）

`record_learning` 写入的 `learnings` 表与所有「主动查询/检索」路径（`memories` 表 + `episodes` 表 + 向量库 note/memory scope）是**两套不互通的命名空间**：

- **写入**：自然语言「记住/记着/别再…」经 `_handle_chat` 正则路由 → `record_learning(text)` → `INSERT INTO learnings`（持久化 81 条）。
- **查询**：`retrieve_memories` → `memory_evolution.retrieve`（即 `DefaultEvolutionPolicy.retrieve`）→ 只召回 `memories`（memory_intelligence.recall 直读 memories 表）+ `episodes`（recall_episodes 读 episodes 表）。
- `learnings` 表**既不进向量索引，也不被任何检索路径读取**，仅被动注入 system prompt（`build_learnings_block`，最多 12 条、按权重）——故「记住 X」后主动「查询/回忆 X」查不到刚记住的内容（5.9 实证：返回 `p44_*` 旧 memory 而非「猎户座」）。

**本质**：写入走 learning store，查询走 memory/episode 检索库，命名空间结构性分离；非 TTL/importance 过滤、非异步延迟、非关键词映射错误。

---

## 3. Exact Change（精确改动）

**唯一文件**：`memory_evolution/retrieval_policy.py`
**唯一位置**：`DefaultEvolutionPolicy.retrieve` 中，在 step 2（episodes）之后、最终 `items.sort(...)` 之前，新增 **step 3（learnings 低权重回退召回）**。

新增代码（完整）：

```python
        # 3) 学习经验回退召回（TRACE E 修复）
        #    根因：record_learning 写入的 learnings 表此前不被任何检索读取，
        #    导致「记住 X」后主动「查询/回忆 X」查不到刚记住的内容。此处将其作为
        #    低权重第三来源并入统一排序；复用既有 memory_intelligence._tokenize，
        #    不引入第二套排序/检索系统。overlap=0（完全不相关）不入列。
        try:
            from memory import get_learnings
            from memory_intelligence import _tokenize

            qtoks = _tokenize(query) if query else set()
            if qtoks:
                for it in get_learnings(limit=200):
                    content = (it.get("content") or "")
                    if not content:
                        continue
                    ltoks = _tokenize(content)
                    if not ltoks:
                        continue
                    overlap = len(qtoks & ltoks) / len(qtoks)
                    if overlap <= 0.0:
                        continue  # 完全不相关 learning 不污染结果
                    # 低权重：上限 0.30（低于 memory 的 0.45 overlap 分量 + importance 基），
                    # 保证高相关 memory/episode 优先于 learning；相关 learning 仍高于无关项。
                    score = round(0.30 * overlap, 4)
                    items.append(ScoredItem(
                        source_kind="learning", ref_id=it.get("id"),
                        content=content[:200],
                        score=score,
                        importance=float(it.get("weight", 1.0)),
                        metadata={"type": it.get("type"), "status": "learning",
                                  "weight": it.get("weight")},
                    ))
        except Exception as e:
            print(f"[retrieval_policy] learnings 回退忽略: {e}")
        items.sort(key=lambda x: x.score, reverse=True)
        return items[:top_k]
```

**设计决策（依据真实 scoring，非机械套用 0.35）**：
- 复用既有 `_tokenize`（memory_intelligence，CJK 单字+bigram+ASCII 词，零新依赖）。
- `overlap = |q∩l| / |q|`（与 memory_intelligence.recall 同义，命中率口径）。
- `overlap <= 0.0` 直接 `continue` → **完全不相关 learning 不进入结果**（R2 守护）。
- `score = round(0.30 * overlap, 4)`：低权重上限 0.30，**低于 memory 的 0.45 overlap 分量 + importance 基**（memory 相关分通常 0.2–0.9），保证「高相关 memory/episode > learning」；相关 learning（overlap>0）仍高于无关项。
- FAIL-SOFT：`get_learnings` / `_tokenize` 异常 → 仅跳过 learnings，继续返回 memories+episodes（R7 守护）。
- 复用既有 `get_learnings(limit=200)`（只读 SELECT），不新建存储/索引/系统。

---

## 4. Before / After 调用链

**Before（修复前）**：
```
retrieve(query)
 ├─ step1: memory_intelligence.recall → memories        (source_kind=memory)
 ├─ step2: cognitive.episodic.recall_episodes → episodes (source_kind=episode)
 └─ sort → top_k
   ❌ learnings 表完全不在检索空间
```

**After（修复后）**：
```
retrieve(query)
 ├─ step1: memory_intelligence.recall → memories        (source_kind=memory)
 ├─ step2: cognitive.episodic.recall_episodes → episodes (source_kind=episode)
 ├─ step3: memory.get_learnings → learnings 回退召回     (source_kind=learning, 低权重, overlap>0 才入列)
 └─ 统一 sort(reverse) → top_k   ← learnings 参与同一排序/截断，无第二排序系统
```

**下游消费（已实现，未改动）**：
- `memory.retrieve_memories` (memory.py:858) → `_me.retrieve`（即 DefaultEvolutionPolicy）→ 原样返回 ScoredItem 列表。
- `context/retrieval.py` `UnifiedRetrieval`（Context Engine 真实注册源 memory_recall_source）→ 泛型消费 ScoredItem，`source_kind` 仅写入 metadata，**对新增 `"learning"` 100% 安全**，转为 ContextItem 注入上下文。
- `context/memory_evolution/context_source.py` `EvolvedMemorySource`（受 `FEATURE_MEMORY_EVOLUTION` 默认 OFF 门控，非 live 主路径）→ 同样泛型消费，learning 落 `【经历】` 标签但仍进上下文。

---

## 5. Diff Summary

| 文件 | 改动 | 类型 |
|---|---|---|
| `memory_evolution/retrieval_policy.py` | +28 行（step 3 learnings 回退） | 唯一修改 |
| 其余 12 个生产文件（server.py / tools.py / memory.py / db.py / policy_engine.py / ai_core/execution/api.py / server_handlers_chat.py / capabilities.py / capability_os/registry.py / agent_runtime.py / proactive.py / zz-workspace.js） | 0 行 | 冻结不变 |

---

## 6. Test Matrix（R1–R8 + R9–R12）

| ID | 场景 | 结果 |
|---|---|---|
| R1a | `record_learning("猎户座 TRACE_E_TEST 星座定位知识")` → `retrieve("TRACE_E_TEST")` | ✅ learning 命中（top_k=8 直接 surfacing） |
| R1b | `retrieve("猎户座 星座", k=50)` | ✅ learning 进入检索集合（证明「进入统一检索入口」） |
| R2 | 完全无关查询 | ✅ 测试 learning 不误入 |
| R2-rev | `retrieve("ZZQT_TEST_TOKEN")` | ✅ 该 learning 命中 |
| R3 | 已有 memory 查询 | ✅ memory 正常命中 |
| R4 | episode 集成代码未被破坏 | ✅ (monkeypatch) source_kind=episode 正确并入；**live episode 语义召回因 mem_vectors=0 预存失效（RECORD-ONLY，超出本范围）** |
| R5 | 混合查询，高相关 memory + learning 共存 | ✅ memory max=0.6596 ≥ learning max=0.3000（memory 优先） |
| R6 | `memory.retrieve_memories` → Context Engine 适配器 | ✅ learning 经 `UnifiedRetrieval` 转为 ContextItem 消费进上下文 |
| R7 | `get_learnings` 模拟异常 | ✅ retrieve 不崩溃，返回 memories+episodes（FAIL-SOFT） |
| R8 | 数据计数零污染 | ✅ 清理后 learnings=81 / episodes=18 / memories=119（与基线一致） |
| R9 | 能力基线 | ✅ tools.py 字节级一致 → TOOLS=62 / TOOL_FUNCS=62 / READONLY_TOOLS=28 |
| R10 | Runtime | ✅ 8010 /api/health=200 /api/agent/state=running/IDLE |
| R11 | 安全回归 smoke | ✅ policy_engine.py / ai_core/execution/api.py / server_handlers_chat.py SHA 全部匹配 P0-1 冻结值 → CONFIRM/AUTO/BLOCK/NEVER 语义零改动 |
| R12 | 冻结文件 SHA | ✅ server.py `4b1a91de…` / zz-workspace.js `76e55100…` 未变 |

**OVERALL: ALL PASS**（R1–R12 全绿）。

---

## 7. Runtime Verification

- `GET /api/health` → **HTTP 200**
- `GET /api/agent/state` → `{"enabled":true,"state":"IDLE","running":true,"consecutive_failures":0}`（与预期核心状态一致）
- `GET /api/capability_os/catalog` → `total=33, available=27`（CANONICAL/AVAILABLE 基线未变）
- Port **8010** 监听正常，未改回 8000。

---

## 8. DB Count Verification（仅 SELECT，零写入）

| 表 | 修复前 | 修复后（清理测试数据） | 结论 |
|---|---|---|---|
| learnings | 81 | 81 | ✅ 零污染 |
| episodes | 18 | 18 | ✅ |
| memories | 119 | 119 | ✅ |
| mem_vectors | 0 | 0 | ✅ 未触碰 |

测试过程所用 2 个唯一标签（`TRACE_E_TEST` / `ZZQT_TEST_TOKEN`）的学习条目，已在 R8 阶段按标签 `DELETE` 清理并验证计数回归基线。全程无任何 `INSERT`（除测试 fixture 且已回滚）/ `UPDATE` / `ALTER` / `CREATE` / `DROP` 作用于生产数据。

---

## 9. SHA256 Audit

| 文件 | BEFORE | AFTER | 状态 |
|---|---|---|---|
| **`memory_evolution/retrieval_policy.py`** | `0f3d1a25…252eb` | `80abeaf3…26f1` | 🔶 唯一变更（本次修复） |
| server.py | — | `4b1a91de…6b048` | ✅ 冻结未变 |
| tools.py | — | `bb5ee850…38013` | ✅ 冻结未变（TOOLS 基线不变） |
| capabilities.py | — | `2bdb7e6e…bd0f` | ✅ 冻结未变 |
| capability_os/registry.py | — | `d340e1d…896cf` | ✅ 冻结未变 |
| agent_runtime.py | — | `64a8d26…56c6a` | ✅ 冻结未变 |
| policy_engine.py | — | `e2ee57f7…7991` | ✅ P0-1 值，未变 |
| ai_core/execution/api.py | — | `039b4332…eb161` | ✅ P0-1 值，未变 |
| proactive.py | — | `e3febfef…4a61` | ✅ 冻结未变 |
| zz-workspace.js | — | `76e55100…62a9` | ✅ 冻结未变 |
| server_handlers_chat.py | — | `aeb69818…6d50c` | ✅ P0-1 值，未变 |

**结论：仅授权文件发生变化，其余 12 个生产文件字节级一致。**

---

## 10. Regression（回归）

- **代码回归**：无。仅 `retrieval_policy.py` 增加 step 3；step 1/2 代码零改动；模块结构、ScoredItem 字段、排序/截断逻辑不变。
- **安全回归**：无。`policy.evaluate` / `request_approval` / `resolve` / `ai_core.execution.run` 三文件 SHA 与 P0-1 冻结值完全一致；CONFIRM（无批准不执行）、AUTO、BLOCK、NEVER 语义未被触碰。
- **功能回归**：memories / episodes 检索路径经 R3/R4 验证正常；Context Engine 记忆注入经 R6 验证正常消费 learning。
- **数据回归**：R8 计数零污染。
- **能力/端口/运行时回归**：R9/R10/R12 全绿。
- ⚠️ **测试环境说明（透明披露）**：为运行 episode 路径验证（recall_episodes 依赖 numpy），在 WorkBuddy 隔离 venv（`C:\Users\Administrator\.workbuddy\binaries\python\envs\default`）安装了 numpy 2.4.6，仅用于本验证，未触碰项目文件或生产环境，不影响项目交付物。

---

## 11. Remaining Findings（遗留，按纪律保持 RECORD-ONLY，不擅自修复）

| 项 | 类别 | 说明 | 与本次关系 |
|---|---|---|---|
| **mem_vectors = 0** | 独立缺陷 | 向量库完全为空 → `tool_memory_search`（embed 语义检索）与 `recall_episodes`（语义召回）当前均失效。属独立向量初始化/backfill 问题，与 TRACE E 根因（learnings 命名空间分离）正交。 | 严格超出 TRACE E 授权范围，记录为 RECORD-ONLY；按纪律**未修**（未 backfill、未改 embed.py / tools.py / vector schema）。 |
| TRACE E | 已修复 | learnings 已并入统一检索入口。 | 本次已闭环。 |
| P2 | 继承 | `foundation_view` 无 GUI consumer。 | 未触碰。 |
| P3 | 继承 | `execution_mapping.py` 注释与 `safety.py` whitelist 语义陈旧矛盾。 | 未触碰。 |
| P0-1-L1 | 继承 | `run_shell` IMDS curl 仍属 CONFIRM 而非 NEVER。 | 未触碰（已受审批保护）。 |
| P0-1-L2/L3/L4 | 继承 | GOAL 审批 UI / 前端 onApproval 依赖 / approval timeout=300s。 | 未触碰。 |

---

## 12. Final Verdict

**✅ PASS / COMPLETE / STOP**

完成判定（全部满足）：
1. ✅ 「记住 X」产生的 learning 可被统一 `retrieve` / `retrieve_memories` 命中（R1/R1b/R6）。
2. ✅ Context Engine 真实路径（`UnifiedRetrieval` → `memory.retrieve_memories`）可消费该 learning（R6）。
3. ✅ memories 正常（R3）。
4. ✅ episodes 集成代码未被破坏（R4；live 语义召回因 mem_vectors=0 预存失效，超出范围）。
5. ✅ 不相关 learning 不污染结果（R2；`overlap<=0` 不入列）。
6. ✅ learning 低权重（上限 0.30），不压过高相关 canonical memory（R5：memory 0.6596 ≥ learning 0.3000）。
7. ✅ `get_learnings` 异常不破坏主检索（R7 FAIL-SOFT）。
8. ✅ 数据零迁移、零污染（R8）。
9. ✅ TOOLS/CAPS/FEATURES 不变（R9）。
10. ✅ server.py / zz-workspace.js SHA 不变（R12）。
11. ✅ 仅授权文件变化（R9 SHA Audit）。
12. ✅ py_compile PASS；真实运行验证 PASS（R10）；未引入第二套 Memory/Recall 系统。
13. ✅ 测试矩阵 ALL PASS（R1–R12）。

**实施边界严守**：仅改 `retrieval_policy.py`；未实施方案 B；未改 `tool_memory_search`；未处理 `mem_vectors=0`；未新增表/索引/迁移；未改 record_learning/episodes/memories 写入语义；未动 Agent Loop / Context Engine 架构 / 权限审批执行系统；未扩大至 5.10；未顺手修复任何 RECORD-ONLY finding。

---

**NO AUTO-NEXT-PHASE. WAITING FOR BOSS AUTHORIZATION.**

老板，TRACE E 记忆一致性修复已完成并验证通过。请指示下一步——例如审批归档、或授权进入其他候选（如独立处理 `mem_vectors=0`，或 TRACE E 之外的 P2/P3 等 RECORD-ONLY 项）。
