# 小6 Xiao6 v1.4.0 — PHASE MEMORY VECTOR INDEX RECOVERY
# READ-ONLY ROOT CAUSE AUDIT

> 阶段类型：**READ-ONLY ROOT CAUSE AUDIT**（接管 / 归档 / 冻结边界内，禁止任何写入）
> 授权目标：查清 `mem_vectors = 0` 的真实根因，制定最小、安全、可验证的后续修复方案
> 生成时间：2026-08-19 15:30 GMT+8
> 执行纪律：VERIFY-BEFORE-CHANGE / NO WRITE / NO BACKFILL / NO CODE CHANGE / NO DEP INSTALL / NO AUTO-NEXT-PHASE

---

## 1. Executive Summary

`mem_vectors = 0` 的真实根因是**部署缺失（IMPLEMENTATION / INITIALIZATION GAP）**：本地向量嵌入模型 **`BAAI/bge-small-zh-v1.5` 的 ONNX 权重文件完全不存在**于部署目录 `G:\xiao6\xiao6-ui\models\embed\`（该目录不存在；`models/` 下仅有 `vosk`、`whisper`）。

据此：
- `embed.model_ready()` (`embed.py:178`) 返回 `False`；
- 启动预热 `_warmup_embed()` (`server.py:969` daemon 线程) 在 `if not embed.model_ready(): 跳过预热; return`（`server.py:1070-1072`）**提前返回，`backfill_all()` 从未执行**；
- `cognitive.episodic.add_episode` 的向量索引（`episodic.py:51`，`if model_ready(): add_vector(...)`）因同一守卫**从未索引**；
- `memory.py` 写入 canonical memory 时**完全不调用任何向量索引**（grep 零命中）→ 记忆除一次性回填外无任何索引路径；
- `tool_memory_search`（`tools.py:2189`）在 `model_ready()=False` 时**优雅返回"语义检索模型尚未就绪"消息**（不崩溃）；
- `recall_episodes`（`episodic.py:64`）`if not model_ready(): return []` → episodes 存在但**不可语义召回**。

**决定性证据**：生产解释器（envs/default 与 bundled `python/`）的 `numpy`/`onnxruntime`/`tokenizers` **全部 OK**；`find` 全项目（排除库）**无任何 bge/onnx 模型文件**。因此根因是**单一缺失的模型权重 artifact**，不是依赖缺失、不是 schema 损坏、不是调用链断裂。

**分类（按授权 §18）**：`IMPLEMENTATION / INITIALIZATION GAP`（部署 artifact 缺失，表现为依赖/运行时失败；依赖库齐全，仅权重缺失）。非 DATA CORRUPTION；非 DESIGN-INTENTIONAL（代码明确设计为启动时构建向量）。

**影响边界（按授权 §15，不夸大）**：仅**向量语义层**失效（`tool_memory_search` 与 `recall_episodes`）；**canonical memory 检索（token-overlap，无向量）与 TRACE E learnings 召回完全正常**，Agent Loop / GoalSystem / Proactive / GUI 不受影响。

---

## 2. Current Baseline

| 项 | 值 | 来源 |
|---|---|---|
| 项目根 | `G:\xiao6\xiao6-ui` | pwd |
| Python（PATH） | 3.13.14 | `python --version` |
| 运行进程 | PID 40092 监听 `127.0.0.1:8010` | netstat |
| `/api/health` | HTTP 200 | curl |
| `/api/agent/state` | `enabled=true, state=IDLE, running=true, consecutive_failures=0` | curl |
| `/api/capability_os/catalog` | `total=33, available=27` | curl |
| DB 位置 | `G:\xiao6\xiao6-ui\xiao6.db`（756 KB，mtime 2026-08-19 15:32） | ls + SELECT |
| DB 计数 | learnings=81 / episodes=18 / memories=119 / mem_vectors=0 | SELECT |
| TOOLS / TOOL_FUNCS / READONLY | 62 / 62 / 28 | 冻结 tools.py SHA + 运行时 |
| CANONICAL / AVAILABLE | 33 / 27 | catalog |
| FEATURE_REGISTRY | 47 | 冻结 zz-workspace.js SHA |
| Runtime Port | 8010（未改） | netstat |

---

## 3. mem_vectors Schema

位置：`db.py:154-160`

```sql
CREATE TABLE IF NOT EXISTS mem_vectors(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    ref_id INTEGER NOT NULL,
    vec BLOB NOT NULL,
    ctime TEXT,
    UNIQUE(scope, ref_id))
```

- **主键**：`id` 自增
- **唯一约束**：`UNIQUE(scope, ref_id)` → `add_vector` 用 `ON CONFLICT(scope,ref_id) DO UPDATE` 覆盖（`embed.py:126`）
- **向量字段**：`vec` BLOB，`float32` 字节（`embed._vec_to_blob`/`_blob_to_vec`，`embed.py:108-113`）
- **维度**：`_dim = 512`（`embed.py:25`）；`semantic_search` 含 `if v.shape[0] != _dim: continue` 维度校验（`embed.py:163`）
- **scope 合法值（代码实际使用）**：`'note'`（笔记）、`'memory'`（记忆）、`'episode'`（情节）；`'knowledge'` 为 P4 设计残留（当前无写入路径）
- **索引/外键/metadata**：无显式二级索引；无外键（ref_id 为逻辑引用，跨表由 `_fetch_text` 按 scope 回查 `notes`/`memories`）；无 metadata 列

SELECT 实测：`SELECT scope,COUNT(*) FROM mem_vectors GROUP BY scope` → `{}`（所有 scope 均为 0）。

---

## 4. Vector Write Path

唯一底层写入函数：`embed.add_vector(scope, ref_id, vec)`（`embed.py:116-131`），`ON CONFLICT(scope,ref_id) DO UPDATE`。

调用方（真实代码）：
- `embed.index_note(nid, text)`（`embed.py:183`）→ `add_vector("note", ...)`
- `embed.index_memory(mid, text)`（`embed.py:194`）→ `add_vector("memory", ...)`
- `cognitive.episodic.add_episode`（`episodic.py:51-54`）→ `if model_ready(): add_vector("episode", eid, embed_doc(summary))`（best-effort）
- `embed.backfill_all`（`embed.py:266/275`）→ 批量 `add_vector("note"/"memory", ...)`

**关键缺口**：`memory.py`（canonical memory 写入权威）经 grep **零命中** `index_memory`/`add_vector`/`embed`/`model_ready` → **canonical memory 创建时不自动建向量**。向量唯一来源是 `backfill_all`（一次性、启动、模型门控）。

---

## 5. Vector Read Path

- `embed.semantic_search(scope, query_vec, top_k, min_score)`（`embed.py:149-169`）→ `SELECT ref_id,vec FROM mem_vectors WHERE scope=?`，numpy 余弦
- `embed.memory_search(query, scopes=("note","memory"))`（`embed.py:232-248`）→ 调 `semantic_search`
- `cognitive.episodic.recall_episodes`（`episodic.py:72`）→ `semantic_search("episode", ...)`
- `memory_v2/semantic.py`（FLAG-GATED 实验性 `MEMORY_V2_ENABLE`，默认 off）只读 `mem_vectors` scope='memory'
- `data_manager.py` / `beta_health.py` 仅导出/健康统计读取（只读）

读取均依赖 `mem_vectors` 有数据；当前为空 → 全部召回返回 `[]` / 无结果。

---

## 6. Embedding Generation Path

文件：`embed.py`

- 模型：`BAAI/bge-small-zh-v1.5` ONNX 量化版（Xenova 移植），**dim=512**，~24MB，**纯本地 CPU**（`onnxruntime` + `tokenizers`，无需 transformers）— `embed.py:1-8`
- 模型路径（硬编码，无 env 覆盖）：
  - `_MODEL_DIR = <embed.py 目录>/models/embed`（`embed.py:15`）
  - `_TOKENIZER_PATH = models/embed/tokenizer.json`（`embed.py:16`）
  - `_QUANT_ONNX = models/embed/onnx/model_quantized.onnx`；回退 `_FULL_ONNX = models/embed/onnx/model.onnx`（`embed.py:17-18`）
- 生成入口：`embed_texts`（`embed.py:74`）→ `_ensure_model`（`embed.py:28-44`）懒加载 tokenizer + `ort.InferenceSession(providers=["CPUExecutionProvider"])`；CLS 池化 + L2 归一化（`embed.py:66-71`）
- `model_ready()`（`embed.py:178-179`）= `os.path.exists(_QUANT_ONNX) or os.path.exists(_FULL_ONNX)`
- 失败处理：`_ensure_model` 在模型缺失时 `Tokenizer.from_file` 抛异常；所有上层调用均 FAIL-SOFT（见 §8/H）
- 配置依赖：**`config.py` 与 `.env` 均无 embedding 相关配置**（grep 空）→ 模型必须物理存在于 `models/embed`，无配置替代路径
- 依赖库：`numpy` / `onnxruntime` / `tokenizers` —— **生产解释器（envs/default、bundled python/）三者均 OK**（import 检查通过）

---

## 7. Backfill Path

函数：`embed.backfill_all()`（`embed.py:251-281`）

逻辑：
1. `n = COUNT(*) FROM mem_vectors`；**`if n > 0: return 0`**（幂等：仅当向量库为空才回填）
2. 扫描 `notes` 全表 → `add_vector("note", nid, embed_doc(text))`（逐行 try/except 静默）
3. 扫描 `memories` 全表 → `add_vector("memory", mid, embed_doc(text))`（逐行 try/except 静默）
4. **不扫描 `episodes`**（episodes 仅由 `add_episode` 写时 best-effort 索引）

唯一调用方：`server.py:969` `_warmup_embed` daemon 线程（在 `main()` 启动）：
```python
def _warmup_embed():
    try:
        import embed
        if not embed.model_ready():
            print("[embed] 模型缺失，跳过预热")   # ← 当前永远走这里
            return
        embed.embed_doc("预热")
        try:
            n = embed.backfill_all()
            ...
```
→ 因 `model_ready()`=False，`backfill_all()` **从未被调用**。即使被调用，因模型缺失，`embed_doc` 会逐行抛异常被静默吞掉，仍产生 0 向量。

**结论**：backfill 路径（A）从未执行（初始化缺失 + 模型门控）；即便执行也因模型缺失而无效（运行时/依赖失败）。

---

## 8. tool_memory_search Path

函数：`tool_memory_search(args)`（`tools.py:2189-2212`）

链路：
- `from embed import memory_search, model_ready`
- `if not model_ready(): return "语义检索模型尚未就绪（缺少 bge ONNX 模型）。"`（`tools.py:2198-2199`）→ **优雅返回提示，不崩溃**
- 否则 `memory_search(q, top_k=...)`（`embed.py:232`）→ `embed_query`（`embed.py:92` → `embed_texts(is_query=True)`，带 bge 检索指令前缀）→ `semantic_search(scope, qv)` 遍历 `("note","memory")`
- `top_k` 默认 5（上限 10），`min_score=0.2`（余弦阈值）
- 空结果 → `"没有找到语义相关的记忆。"`；异常 → `"语义检索失败：{e}"`

**mem_vectors=0 时实际行为**：`model_ready()`=False → 返回"模型尚未就绪"提示（选项 D 的变体：明确报错提示而非静默空）。**不是 fallback 到 SQL/memories/episodes**。

---

## 9. recall_episodes Path

函数：`recall_episodes(user_text, top_k=5)`（`episodic.py:58-103`）

- `if not user_text or not model_ready(): return []`（`episodic.py:64-65`）→ **mem_vectors=0 根因下直接返回 `[]`**
- 否则 `qv = embed_query(user_text)`（异常 → `return []`）
- `semantic_search("episode", qv, top_k*3, min_score=0.18)`（`episodic.py:72`）
- 综合得分 `0.6*余弦 + 0.25*importance + 0.15*recency_decay`
- 依赖 `mem_vectors(scope='episode')` 有数据

**明确区分**（按授权 §10）：
- `episodes` 表 **存在 18 条**数据（事实数据完好）
- 但 `episodes` **不可被语义召回**（向量缺失 → `recall_episodes` 返回 `[]`）
- 写入时 `add_episode` 的向量索引因 `model_ready()` 守卫从未执行

---

## 10. Migration / Initialization History

- `mem_vectors` 由 `db.py:154` `CREATE TABLE IF NOT EXISTS` 在 DB 初始化时建表（schema 稳定，无 `ALTER` 痕迹）
- 无独立 migration 脚本针对向量；`embed.py` 为参考实现（bge ONNX 本地 RAG）
- `first_launch.py:113 backfill_missing_keys()` 回填的是**环境变量/配置键**，与向量无关
- `/api/memory/backfill`（`server_handlers_memory.py:248`）调用的是 `memory_intelligence.backfill_salience()`（salience 字段回填），**非向量 backfill** —— 注意与 `embed.backfill_all` 区分
- 设计文档（P4 系列）明确 `mem_vectors` 为"语义向量投影（Projection）"，应由 `embed.py` + 启动时 `backfill_all` 填充
- **推断**：新数据库创建了 `mem_vectors` 表，但**模型权重从未部署到 `models/embed/`**，且启动回填因模型门控被跳过 → 向量始终为空（非历史数据迁移遗漏，而是部署 artifact 缺失）

---

## 11. Dependency / Environment Audit

| 依赖 | 生产可用性 | 证据 |
|---|---|---|
| 生产解释器 | envs/default（start-xiao6.bat 首选）或 bundled `python/` | start-xiao6.bat:6-7 |
| `numpy` | OK（两解释器） | import 检查 |
| `onnxruntime` | OK | import 检查 |
| `tokenizers` | OK | import 检查 |
| `torch` | 已装（bundled）但 embed.py 不依赖 | 目录 listing |
| **bge ONNX 模型权重** | **MISSING** | `models/embed` 不存在；`find` 无 bge/onnx 模型文件（排除库） |
| 网络需求（推理） | 无（纯本地 CPU） | embed.py:43 CPUExecutionProvider |
| 配置覆盖 | 无（路径硬编码） | config.py/.env grep 空 |

**结论**：Python 依赖齐备；唯一缺口是模型权重 artifact。区分清楚：**A 生产（server 实际运行）、B WorkBuddy managed（envs/default）、C bundled（python/）三者 embedding 依赖一致且齐全**；本阶段未安装任何依赖（遵守纪律），也无需安装。

> 备注：PID 40092 的命令行 introspection 在当前环境被安全策略拦截（返回空），无法 100% 确认其具体解释器路径；但 start-xiao6.bat 指向 envs/default，且该解释器依赖齐全，足以判定生产环境满足 embedding 库依赖。

---

## 12. Data Consistency Audit（纯 SELECT，无写入）

| 检查 | 结果 |
|---|---|
| `mem_vectors` 总计数 | 0 |
| 各 scope 计数 | `{}`（note/memory/episode/knowledge 全为 0） |
| `memories` 总数 | 119 |
| `memories` 可嵌入（title+content 非空） | 119（全部 eligible） |
| `episodes` 总数 | 18 |
| `episodes` 可嵌入（summary 非空） | 18（全部 eligible） |
| `notes` 总数 | 16 |
| 孤儿向量（无对应主表行） | 0（向量表为空，自然无孤儿） |
| 缺向量的 memory | 119（全部缺） |
| 缺向量的 episode | 18（全部缺） |
| learnings 是否需向量 | 否（由 TRACE E token-overlap 召回，不经向量） |

**结论**：主表数据完整无损坏；向量缺失是"从未生成"而非"丢失/损坏"。理论需建向量 ≈ 119(memory)+18(episode)+16(note)=153 条。

---

## 13. Root Cause Tree

```
MEM_VECTORS = 0
│
├── Schema ............................ PASS
│     mem_vectors 表存在、结构正确、UNIQUE(scope,ref_id)、dim=512（db.py:154）
│
├── Initialization ................... FAIL
│     _warmup_embed 接入启动(server.py:969) 但 model_ready 守卫跳过；
│     memory.py 写入不自动索引（无 add_vector 调用）→ 仅 backfill 唯一来源
│
├── Backfill ......................... FAIL
│     backfill_all 仅 server.py:969 调用，且被 model_ready 门控从未执行；
│     即便执行也因模型缺失逐行静默失败；且不含 episodes
│
├── Embedding ........................ FAIL  ← 主根因
│     models/embed/ 目录不存在；tokenizer.json + model_quantized.onnx 缺失；
│     model_ready()=False（embed.py:178）
│
├── Dependencies ..................... PASS
│     numpy/onnxruntime/tokenizers 在生产解释器均 OK（import 检查）
│
├── Configuration .................... PASS
│     config.py/.env 无 embedding 配置；路径硬编码 models/embed；非配置错误
│
├── Scope ............................ PASS
│     note/memory/episode/knowledge 语义一致；非 scope 不匹配导致
│
├── Data migration ................... PASS / UNKNOWN
│     表由 db.py 初始化建好；无遗漏 migration；向量从未生成（部署缺失，非迁移遗漏）
│
└── Runtime integration .............. FAIL
      model_ready() 守卫使所有读写路径（warmup/backfill/add_episode/
      tool_memory_search/recall_episodes）短路 → 全返回空/提示
```

**唯一主根因**：`Embedding` 分支 FAIL —— 模型权重 artifact 缺失 → `model_ready()=False` 级联短路全部写入与读取路径。

**分类**：`IMPLEMENTATION / INITIALIZATION GAP`（部署 artifact 缺失）。表现亦属运行时/依赖失败（权重依赖未满足），但依赖**库**齐全，仅**权重文件**缺失。

---

## 14. Actual User Impact

| 组件 | 状态 | 说明 |
|---|---|---|
| `tool_memory_search`（用户"查询/回忆"工具） | **失效** | 返回"语义检索模型尚未就绪"提示，无语义召回 |
| `recall_episodes`（情节语义召回） | **失效** | `model_ready`=False → `return []`；18 条 episodes 不可语义召回，且在 Context Engine `retrieve` step2 贡献为 0 |
| `memory.retrieve_memories` / Context Engine canonical | **正常** | 走 `memory_intelligence.recall` token-overlap（无向量）+ TRACE E learnings，不受影响 |
| `learnings` 召回 | **正常** | TRACE E 经 token-overlap，不依赖向量 |
| `memories` / `episodes` 数据 | **完好** | 无损坏、无丢失 |
| Agent Loop / GoalSystem / Proactive | **无影响** | 不依赖向量层 |
| GUI | **无影响** | — |

**精确结论**：**canonical memory retrieval 正常；仅 vector semantic retrieval 失效**。不得表述为"Memory 系统整体不可用"。

---

## 15. Risk Assessment

- **当前风险**：仅影响向量语义检索；无生产崩溃、无数据损坏、无安全边界影响（policy/approval/execution 未触碰）。影响属于"功能降级"而非"故障"。
- **修复风险（未来执行时）**：
  - 低风险：部署模型 artifact + 重启触发回填，零代码改动（路径已硬编码匹配）
  - 模型错配风险：必须是 bge-small-zh-v1.5 ONNX dim=512；错模型会被 `semantic_search` 维度校验（`embed.py:163`）静默丢弃
  - 写库风险：`backfill_all` 会向生产 DB 写 `mem_vectors`（INSERT/UPDATE）→ 需 DB 备份 + 计数验证 + 回滚预案
  - episodes 不被 `backfill_all` 覆盖 → 需单独 episode 索引步骤（见 §16/§17）

---

## 16. Candidate Repair Plans

> 仅提出方案，禁止本阶段实施。所有方案前提：获取并部署 `bge-small-zh-v1.5` ONNX 权重到 `models/embed/`。

**方案 A — 最小增量 backfill**
- 修改文件：无（仅部署模型 + 重启触发 `backfill_all`）
- 影响 DB：写 `note`+`memory` 向量（~135 条）
- 不覆盖 episodes；episodes 需后续写入才索引
- 风险：低；不完整（episodes 仍空）

**方案 B — 完整 vector rebuild**
- 修改文件：扩展 `backfill_all` 或新增 episode 索引步骤（覆盖 note/memory/episode）
- 影响 DB：写 ~153 条
- 风险：低；最完整

**方案 C — 只恢复 memories**
- 修改文件：无（仅部署模型 + 仅对 memories 索引）
- 影响 DB：写 119 条
- 风险：低；notes/episodes 仍空

**方案 D — 恢复 memories + episodes（+notes）**
- 修改文件：无代码改动（若复用 `backfill_all` 覆盖 note/memory + 一次性 episode 索引脚本/调用）
- 影响 DB：写 ~153 条
- 风险：低；覆盖用户侧两个主要召回面（记忆+情节）
- 回滚：恢复 DB 备份即可

**方案 E（推荐）— D + 安全门**
- 在 D 基础上强制 §18 全部安全门（备份/计数/SHA/dry-run/回滚）
- 修改文件：理想零代码改动；若需补 episode 索引，仅小幅扩展 `backfill_all` 或独立一次性脚本，并记录该文件新旧 SHA
- 风险：最低（受控）

---

## 17. Recommended Repair Plan

**推荐：方案 D / E（恢复 memories + episodes + notes，受控执行）。**

理由（授权 §17 优先级）：
1. 最小修改：模型部署到既定路径 `models/embed/`，**无需改 embed.py/config/server.py**；回填复用既有 `backfill_all` + 一次性 episode 索引
2. 零架构变化：复用现有 `embed.py` + `mem_vectors` + `DefaultEvolutionPolicy`/`recall_episodes`
3. 不破坏现有 119 memories / 18 episodes：回填为只读主表 + 写向量投影，主表零改动
4. 可恢复：DB 备份 + 向量表可清空重建
5. 可验证：前后 count 对比（0 → ~153）、runtime smoke、工具命中验证
6. 未来可增量维护：修复后建议补"记忆写入时增量索引"的设计缺口（见 Remaining Findings）

**执行前必须满足 §18 安全门**；执行属下一授权阶段，本阶段不做。

---

## 18. Required Pre-Repair Safety Gates

1. **DB 备份**：`cp xiao6.db xiao6.db.bak-<timestamp>`（回填前）
2. **记录前计数**：mem_vectors=0 / memories=119 / episodes=18 / notes=16
3. **模型获取与校验**：将 `tokenizer.json` + `onnx/model_quantized.onnx` 部署到 `models/embed/`；确认确为 bge-small-zh-v1.5（dim 512）；确认无代码改动需求（路径匹配 `embed.py:15-18`）
4. **Dry-run（纯内存、不写 DB、不下载）**：在生产解释器执行 `import embed; v = embed.embed_doc("测试"); print(len(v))` → 期望 `512`、无异常（证明模型可加载、依赖可用）
5. **受控回填**：调用 `embed.backfill_all()`（覆盖 note+memory）+ 一次性 episode 索引循环（覆盖 18 条）；验证后计数 ≈ 119+16+18 = 153
6. **Runtime smoke**：`/api/health=200`、`/api/agent/state=IDLE`；`tool_memory_search` 返回命中；`recall_episodes` 返回条目
7. **回滚**：从备份恢复 DB；验证 mem_vectors 回到 0；重启
8. **SHA 审计**：若仅部署模型文件 → 零代码文件变化；若扩展 `backfill_all` → 记录该文件新旧 SHA，确认仅此文件变化；冻结文件（server.py/tools.py/memory.py/db.py 等）SHA 不变

---

## 19. Frozen Files / SHA Audit

本阶段 **READ-ONLY，未修改任何生产文件**。当前真实 SHA（重新计算）：

| 文件 | SHA256 | 状态 |
|---|---|---|
| server.py | `4b1a91ded03198e9541e75ddfc174b385b81a212a0a1ae46cc75a3884dd6b048` | 冻结未变 ✅ |
| tools.py | `bb5ee8503d97f9db5ce1bbe712a078fdc058fff73c4d2676e36479c9c8838013` | 冻结未变 ✅ |
| memory.py | `9ab336ac4a00a5e118f12deaf963927f66034b8a1a5db4631bd09e4f62ac0ea7` | 冻结未变 ✅ |
| db.py | `c1cc7688eb7b14d9d0a726843aff79ba86a9836d33f68bc118217375cbb26d6b` | 冻结未变 ✅ |
| capabilities.py | `2bdb7e6e940f8c80efb705ae7179a9d0de650c875e3846e0907a2471c524bd0f` | 冻结未变 ✅ |
| capability_os/registry.py | `d340e1d24a275358f735a44e2db15e24c068107db529734e432219a66fe896cf` | 冻结未变 ✅ |
| agent_runtime.py | `64a8d26afe4e8eb4cde278bfaba91a8be3fd722689016608c6b910951b756c6a` | 冻结未变 ✅ |
| policy_engine.py | `e2ee57f796f5fc4b0245c529f8211da94b3143d154943ac5bbc9bb5a817f7991` | 冻结未变 ✅ |
| ai_core/execution/api.py | `039b433269c1967cfec90695d92a94c0e58c7a2abc7077366ce4569e864eb161` | 冻结未变 ✅ |
| proactive.py | `e3febfefe673d04f2e1186c00f5f41488882e7f16c3e238aeebf566d00704a61` | 冻结未变 ✅ |
| zz-workspace.js | `76e55100b1a67d7f5974ace55631058e9c79b6a649db85a4a51a34d0b7e862a9` | 冻结未变 ✅ |
| server_handlers_chat.py | `aeb6981847651b266381b74fbbd10258d517758a4647781b635071f702c6d50c` | 冻结未变 ✅ |
| memory_evolution/retrieval_policy.py | `80abeaf3eca0b0a1cf48baa6029a67e5aad104a7b734f56b20516cff22f426f1` | TRACE E 冻结未变 ✅ |
| embed.py | `599e95d20e070f7020dfc620d9ee00430ed53e63922bd4949f42f88a50b5e1e2` | 本阶段只读审计，未变 ✅ |

---

## 20. Remaining Findings

| 项 | 类别 | 说明 | 处理 |
|---|---|---|---|
| **mem_vectors=0（本阶段主题）** | 根因已定位 | 模型权重缺失（IMPLEMENTATION/INITIALIZATION GAP）；待授权修复 | 记录；待修 |
| **设计缺口：无增量索引** | 设计脆弱性（RECORD-ONLY） | canonical memory 写入不自动建向量；`backfill_all` 仅启动一次性且 `if n>0 return 0`，新记忆/情节写入后不会获得向量；`backfill_all` 不覆盖 episodes | 记录；修复时一并考虑 |
| **P2** | 继承 | `foundation_view` 无 GUI consumer | 未授权修复 |
| **P3** | 继承 | `execution_mapping.py` 注释与 `safety.py` whitelist 语义陈旧矛盾 | 未授权修复 |
| **P0-1-L1** | 继承 | `run_shell` IMDS curl 仍属 CONFIRM 非 NEVER | 未授权修复 |
| **P0-1-L2/L3/L4** | 继承 | GOAL 审批 UI / `onApproval` 依赖 / `approval timeout=300s` | 未授权修复 |
| **TRACE E learnings** | 已冻结 | learnings 经 token-overlap 召回，不依赖向量，正常 | 不受影响 |

---

## 21. Final Verdict

**A. AUDIT PASS / ROOT CAUSE CONFIRMED / READY FOR REPAIR AUTHORIZATION**

- 根因：`models/embed/` 模型权重 artifact 缺失 → `model_ready()=False` → 启动回填被门控跳过、episode 索引被门控跳过、memory 写入无自动索引 → `mem_vectors=0`
- 证据链完整（file:line + 真实 SELECT + 真实 import 检查 + 真实 runtime）
- 依赖库齐全，仅为权重缺失；分类 `IMPLEMENTATION/INITIALIZATION GAP`
- 影响精确：仅向量语义层（tool_memory_search、recall_episodes）降级；canonical memory 与 learnings 召回正常
- 推荐修复方案 D/E，含 §18 安全门，零代码改动或最小扩展

---

## 最终输出纪律确认

- 未修改任何代码（server.py / tools.py / memory.py / db.py / embed.py / retrieval_policy.py / Context Engine / Agent Loop / 等）
- 未执行 backfill / 未写 DB / 未安装依赖 / 未下载模型 / 未重启服务 / 未改端口
- 未进入 Phase 5.10 / 未自动执行推荐方案

**READ-ONLY AUDIT COMPLETE**
**NO WRITE**
**NO BACKFILL**
**NO CODE CHANGE**
**NO AUTO-NEXT-PHASE**
**WAITING FOR BOSS AUTHORIZATION**
