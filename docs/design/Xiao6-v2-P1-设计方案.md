# Xiao6 v2 · P1 设计方案：用户模型 + 情节记忆（User Model + Episodic Memory）

> 版本：v2.0-P1-Design
> 阶段：B 设计（待 C 批准）
> 作者：Senior Developer（高级开发工程师）
> 关联文档：`Xiao6-v2-架构升级设计文档.md`、`Xiao6-v2-核心架构规范.md`
> 前置完成：Phase 1 Context Engine（Step1~5，`build_context_prompt` 门面 + 五阶段管线 + `SourceRegistry`，Flag `FEATURE_CONTEXT_ENGINE` 默认开）

---

## 一、背景与目标（Why / What）

### 1.1 现状缺口
Phase 1 已把"系统提示词组装"收口到 Context Engine，但当前唯一真正接入的来源是 `MemorySource`（仅委托旧 `memory.build_system_prompt`，含 `profile` 键值表 + `memory_summary` + 近期对话）。它有两个结构性短板：

1. **用户画像是扁平键值**（`profile` 表 key/value），无结构化、无自动演化，且依赖用户手动写。模型对"这个用户是谁、偏好什么、沟通风格如何"只能靠零散的 profile 行拼凑。
2. **没有情节记忆（Episodic Memory）**。用户过去做过的决定、承诺、项目里程碑、被纠正过的点，全部沉在 `chat_log` 里，被 `compress_memory` 压成一条摘要后细节丢失，无法"按需召回相关往事"。

### 1.2 目标（P1 范围）
为 Context Engine 新增两类认知来源，使每轮对话的系统提示词自动携带：

- **P1a 用户模型（User Model）**：结构化的、LLM 自动抽取并持续演化的用户画像（身份/专长/沟通风格/偏好/长期项目/价值观/被纠正记录）。
- **P1b 情节记忆（Episodic Memory）**：过去重要事件/决定/承诺/偏好的结构化条目，按**与当前输入的语义相关度**召回并注入。

两者均以新 `ContextSource` 注入，与现有 `MemorySource` 并存、互补、可独立开关。

### 1.3 非目标（明确不做，留待后续 Phase）
- 不重构 `memory.py` 本身（保持向后兼容，不碰其读路径）。
- 不做 World Model / Goal System（Phase 2+）。
- 不做基于 Embedding 的语义召回以外的多模态记忆。
- 不引入新的数据库文件；复用 `xiao6.db`，按需建表（本地优先原则）。

---

## 二、约束（来自 v2 核心架构规范，最高权威）

| 约束 | 条款 | 本方案对应处理 |
|---|---|---|
| 包目录职责 | §24.2：`cognitive/` 专放"为 Runtime 提供上下文的认知服务" | 新代码全部落 `cognitive/`（规范已规划 `cognitive/user_model.py`） |
| Feature Flag 命名 | `FEATURE_*` 形式，禁 `XXX_ENABLED` | 新增 `FEATURE_USER_MODEL`、`FEATURE_EPISODIC_MEMORY` |
| 禁止神模块 | §1.9 / §24.3：业务文件 ≤500 行 | 每个新文件 ≤500 行；超则拆 |
| 本地优先 | §1.3 | 数据落本地 SQLite，云 LLM 仅作抽取计算 |
| 增量演进 | §1.7 | 新增模块/来源/表，不推翻运行时 |
| 向后兼容 | §1.6 | 不改 `memory.py` 读路径、不改现有 API/表/桥；新来源 additive |
| 低耦合/无循环依赖 | §1.2/§1.10 | `cognitive/` 仅依赖 `db`/`llm`/`embed`/`config`，不依赖 `context`；`context` 单向懒惰 import `cognitive` |
| 防御性降级 | Phase1 既定 | 任一来源异常 → 不影响对话（见 §七） |

---

## 三、候选方案对比（Options）

### 3.1 用户模型存储形态
- **方案 A（选定）：单 JSON 文档行**。表 `user_model(id=1, data JSON, confidence, updated)`。读取 O(1)、渲染简单、LLM 抽取产出天然就是结构化 JSON。
- 方案 B：键值表（沿用 `profile`）。缺点：无法表达嵌套结构（沟通风格、反馈历史），且与手动 profile 混淆。
- 方案 C：独立 `user_profile.db`。缺点：新增 DB 基础设施，违背"增量、复用现有连接"原则。

### 3.2 情节记忆召回策略
- **方案 X（选定，P1）：语义向量召回**。复用现有 `embed.py`（本地 ONNX，`semantic_search`/`index_memory`），对每条 episode 建向量，按 `embed_query(user_text)` 余弦相似度取 top-k，再叠加 importance + recency 衰减。优点：真正"相关往事"召回，零新依赖。
- 方案 Y：关键词重叠。优点极简，缺点语义召回差（"想看球赛"匹配不到"世界杯面板"）。
- 方案 Z：纯 recency/importance 排序。无相关性，注入噪声大。

### 3.3 抽取触发方式
- **方案 M（选定）：复用聊天落库钩子 + 阈值触发**。在 `_handle_chat` 助手轮落库后，best-effort（后台线程、try/except）调用 `cognitive.maybe_extract()`。阈值（如 chat_log > 40 轮）触发一次统一抽取 pass，顺带**复活 `compress_memory()` 死代码**（同一 LLM 调用同时产出 summary 更新 + 用户模型增量 + 新 episodes，省成本）。
- 方案 N：定时任务。缺点：需新增调度，且"对话刚发生"时抽取最准。
- 方案 P：每条消息都抽。成本过高，否决。

---

## 四、选定方案总览

```
                    ┌─────────────────────────────────────┐
                    │  cognitive/  (新包, §24.2 认知服务层) │
                    └─────────────────────────────────────┘
   chat 落库钩子 ──► maybe_extract()  [后台线程, 阈值触发]
        │                │ 一次 LLM pass 产出三件套
        │                ├─► memory.compress_memory()  (复活, 写 memory_summary)
        │                ├─► upsert user_model         (写 user_model 表)
        │                └─► insert episodes + index    (写 episodes 表 + embed 向量)
        │
   build_context_prompt(user_text)  ──► LegacyContextBuilder
        │                                     │ 注册(Flag 门控)
        ├─ MemorySource        (已有, 委托 memory.build_system_prompt)
        ├─ UserModelSource     (新, 读 user_model → 【用户模型】块)   FEATURE_USER_MODEL
        └─ EpisodicSource      (新, embed 语义召回 top-k → 【相关经历】块) FEATURE_EPISODIC_MEMORY
```

---

## 五、数据模型（SQLite，`xiao6.db`，本地优先）

```sql
-- 用户模型：单行 JSON 文档（沿用 memory_summary 同库）
CREATE TABLE IF NOT EXISTS user_model (
  id        INTEGER PRIMARY KEY CHECK (id = 1),
  data      TEXT    NOT NULL,   -- JSON: 见 §5.1
  confidence REAL DEFAULT 0.5,
  updated   TEXT
);

-- 情节记忆条目
CREATE TABLE IF NOT EXISTS episodes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT    NOT NULL,
  summary       TEXT    NOT NULL,
  category      TEXT,             -- decision | commitment | project_state | preference | fact | event
  importance    REAL DEFAULT 0.5, -- [0,1]
  created       TEXT    NOT NULL,
  last_accessed TEXT,
  access_count  INTEGER DEFAULT 0
);
-- 向量由 embed.py 管理（scope="episode", ref_id=episodes.id），无需本表加列。
```

### 5.1 `user_model.data` JSON 结构（初版，可演进）
```json
{
  "identity":            { "name": "", "role": "", "org": "" },
  "expertise":           ["前端", "全栈"],
  "communication_style": { "verbosity": "concise", "formality": "casual", "humor": "welcome" },
  "preferences":         { "languages": ["Python"], "frameworks": ["Laravel"] },
  "recurring_projects":  ["小6", "白龙马"],
  "values":              ["本地优先", "隐私合规", "自主拍板"],
  "feedback":            ["标记要小且无发光", "别加多余 Markdown"]
}
```
- LLM 抽取产出 JSON 增量，与现有 `data` 做**浅合并 + 数组去重**，不整体覆盖（避免丢失旧事实）。
- `confidence` 随抽取次数缓慢上升（如 `min(0.95, confidence + 0.05)`）。

---

## 六、模块设计（cognitive/ 新包，每文件 ≤500 行）

### 6.1 `cognitive/__init__.py`
导出 `maybe_extract`、`UserModelSource`、`EpisodicSource`，并惰性 import 以避免与 `context` 形成循环（实际无环：`cognitive` 不 import `context`）。

### 6.2 `cognitive/user_model.py`（~180 行）
- `load_user_model() -> dict`：读 `user_model` 单行，解析 JSON，空则返回默认骨架。
- `upsert_user_model(delta: dict)`：浅合并 + 数组去重，写回，更新 `updated`/`confidence`。
- `render_user_model_block() -> str`：渲染紧凑 `【用户模型】` 文本，硬上限 ~350 token（超出截断数组字段）。
- 提供 `UserModelSource`（实现 `ContextSourceProvider.collect`）：读模型 → 若为空返回 `[]`，否则返回单条 `ContextItem(source=USER, content=block, priority=0.7, importance=0.8, ...)`。

### 6.3 `cognitive/episodic.py`（~230 行）
- `add_episode(title, summary, category, importance)`：插入 `episodes` 并 `embed.index_memory` 等价地 `add_vector("episode", id, embed_doc(summary))`。
- `recall_episodes(user_text, top_k=5) -> list[(Episode, score)]`：
  1. `qv = embed.embed_query(user_text)`；
  2. `semantic_search("episode", qv, top_k=top_k*2, min_score=0.2)` 取候选；
  3. 叠加得分：`final = 0.6*cos + 0.25*importance + 0.15*recency_decay(created)`；
  4. 取 top_k，更新 `last_accessed`/`access_count`（best-effort）。
- `render_episodes_block(eps) -> str`：渲染 `【相关经历】` 列表，硬上限 ~600 token。
- 提供 `EpisodicSource.collect`：调用 `recall_episodes(ctx.user_text)` → 每条（或合并为一条）`ContextItem(source=EPISODIC, priority=0.6, user_relevance=cos, ...)`。

### 6.4 `cognitive/extractor.py`（~250 行）
- `THRESHOLD = 40`（复用旧 `MEM_THRESHOLD` 量级）。
- `maybe_extract()`：
  - `count = SELECT COUNT(*) FROM chat_log`；若 `< THRESHOLD` 直接返回。
  - 取最旧待压缩轮次 + 现有 `user_model` + 现有 episodes 摘要，构造一次 LLM 调用（复用 `llm.agnes_completion`，`stream=False`，带 JSON 输出约束），要求返回：
    ```json
    {
      "summary_update": "…对长期服务用户有价值的要点…",
      "user_model_delta": { …§5.1 增量… },
      "episodes": [ {"title":"…","summary":"…","category":"decision","importance":0.8}, … ]
    }
    ```
  - 解析后：调用 `memory.compress_memory()`（复活死代码，写 `memory_summary`）；`upsert_user_model(delta)`；逐条 `add_episode(...)`。
  - 全部包在 `try/except` 内，失败仅日志记录，绝不阻断聊天。
  - 用**后台线程**执行，避免拖慢 `_handle_chat` 的流式响应。

---

## 七、集成点与 Flag / 回退

### 7.1 来源注册（`context/builder.py`，小改）
```python
import config
if getattr(config, "FEATURE_USER_MODEL", False):
    registry.register(UserModelSource())
if getattr(config, "FEATURE_EPISODIC_MEMORY", False):
    registry.register(EpisodicSource())
```
（`context/sources.py` 现有占位 `User`/`Weather` 等保持不动；新来源类直接写在 `cognitive/`，`builder` 从 `cognitive` 引入。）

### 7.2 枚举扩展（`context/models.py`，极小改）
`ContextSource` 增加 `EPISODIC = "episodic"`（已有 `USER`，复用即可；episode 用独立枚举值更清晰）。

### 7.3 触发钩子（`server.py` `_handle_chat`，小改）
在助手轮落库之后（现有 `save_turn(session_id,"assistant",content)` 附近），加：
```python
try:
    import threading, cognitive
    threading.Thread(target=cognitive.maybe_extract, daemon=True).start()
except Exception:
    pass
```
非阻塞、best-effort。

### 7.4 防御性降级（建议增强 `SourceRegistry.collect`）
现状 `registry.collect` 不吞异常（一处来源抛错会传播到 `build`，靠门面 `try/except` 整体退回 legacy prompt）。为让 P1 新来源"单点故障不影响其他来源"，**建议**把 `SourceRegistry.collect` 改为逐来源 `try/except`，单来源出错 → 日志记录 + 返回 `[]`，其余来源正常。此改动极小且提升鲁棒性，提请批准（若坚持"与旧版一致不吞没"，则保留门面级回退即可，新来源自身也已内部 try/except）。

### 7.5 Flag 默认值与切换
`config.py` 新增：
```python
FEATURE_USER_MODEL: bool = False
FEATURE_EPISODIC_MEMORY: bool = False
```
默认 **OFF**（增量、A/B 安全）。验证通过后改默认 `True`，或用 `update_env_file` 运行时瞬切（沿用 `FEATURE_CONTEXT_ENGINE` 同款机制）。

---

## 八、API 暴露（additive，向后兼容）

- `GET /api/user_model` → 返回 `user_model.data` JSON（供 Developer Dashboard 调试/可观测，对齐 §1.12）。
- `GET /api/episodes?limit=20` → 返回 episodes 列表（按 `last_accessed`/`created` 降序）。
- 可选（P1b 次级）：`remember` 工具（`tools.py` 新增，写一条显式 episode），支持"记住这个"。**不阻塞主流程，可放 Round 3**。

---

## 九、实现轮次拆分（严守 ≤3 改 / ≤5 新 / ≤500 行）

- **Round 1（认知层 + 来源定义）**
  - 新：`cognitive/__init__.py`、`cognitive/user_model.py`、`cognitive/episodic.py`、`cognitive/extractor.py`
  - 改：`context/models.py`(加 EPISODIC)、`context/sources.py`(加两 Source 适配类)、`config.py`(加 2 Flag)
- **Round 2（接入主路径 + 触发 + API）**
  - 改：`context/builder.py`(Flag 注册)、`server.py`(触发钩子 + 两个 GET 端点)  ← 2 个已有文件
  - （可选增强：`SourceRegistry.collect` 单源隔离）
- **Round 3（可选收尾）**
  - 改：`tools.py`(新增 `remember` 工具，若采纳)
  - 前端：Developer Dashboard 增加只读"🧠 用户画像"面板（可选，不阻塞）
  - 自审（E）+ 总结（F）

---

## 十、风险与缓解

| 风险 | 缓解 |
|---|---|
| LLM 抽取成本 | 阈值触发（~40 轮一次），且一次 pass 同时产出 3 类结果；失败不重试 |
| 误抽取/幻觉用户事实 | `user_model_delta` 仅浅合并 + 数组去重；渲染上限 token；可经 `/api/user_model` 人工核查 |
| embed 模型未下载导致召回失败 | `embed.model_ready()` 守卫；不可用时 `recall_episodes` 降级为空（不影响对话） |
| 新来源拖慢首 token | 来源在 `build` 阶段同步采集（与 MemorySource 同路径）；内容有硬 token 上限，且 unlimited 预算下不影响裁剪；抽取本身在后台线程，不进响应关键路径 |
| 循环依赖 | `cognitive` 只依赖 `db/llm/embed/config/memory`(惰性)，不依赖 `context`；`context` 单向 import `cognitive` |
| 破坏现有功能 | 不改 `memory.py` 读路径；新表 IF NOT EXISTS；Flag 默认 OFF |

---

## 十一、验收标准（Definition of Done）

1. `FEATURE_USER_MODEL=True` 时，系统提示词含 `【用户模型】` 块，且内容与 `/api/user_model` 一致。
2. 连续对话 >40 轮后，`user_model` 表被自动填充/演化；`episodes` 表出现条目且已被 `embed` 索引。
3. `FEATURE_EPISODIC_MEMORY=True` 时，提及与某 episode 语义相关的话题，提示词出现 `【相关经历】` 块（由 `semantic_search` 召回）。
4. 任一 Flag=False → 对应来源不注册、提示词无该块，对话行为不变。
5. 强行让 `UserModelSource.collect` 抛错 → 对话不中断（单源隔离或门面回退生效）。
6. 每个新文件 ≤500 行；无神模块；`node --check`/Python 语法通过；重启 8000 后无导入错误。

---

## 十二、待批准决策点（请老板拍板）

1. **Flag 默认**：P1 上线即默认 ON，还是默认 OFF 先灰度？（建议默认 OFF，验证后再翻）
2. **`SourceRegistry.collect` 单源隔离**：是否采纳 §7.4 的逐源 try/except 增强？（建议采纳）
3. **`remember` 显式记忆工具**：P1 是否一并做（Round 3），还是留到后续？（建议 P1 先做自动抽取，工具后置）
4. **前端面板**：是否需要 P1 即做只读"🧠 用户画像"面板，还是仅 API + 后端，面板留 Phase 2？

> 批准后将进入 D 实现（按 Round 1→2→3 小步提交，每轮可 revert）。

---

## 十三、实现记录（2026-07-31 · D 实现已完成）

按用户「开始」指令落地，并对原方案 4 个待定项做了如下决断（用户授权自主拍板）：

1. **Flag 默认 ON**（`config.py` 中 `FEATURE_USER_MODEL` / `FEATURE_EPISODIC_MEMORY` 经 env 默认 `"true"`，可瞬切 OFF）。理由：用户要「开始」即验收，且有来源隔离 + 异步抽取托底，稳定性可控。
2. **采纳 SourceRegistry 逐源 try/except 隔离**（§7.4 增强已落地）。
3. **`remember` 工具放进 P1**（Round 3 完成）。
4. **前端 🧠 画像面板后置**（本轮仅后端 + API + remember 工具）。

### 偏差说明（相对原 §六~§九）
- **抽取器自管压缩**：`extractor.maybe_extract()` 在一次 LLM pass 中同时产出「摘要更新 + 用户模型增量 + 新 episodes」，并就地完成旧对话压缩（写入 `memory_summary` + 删除已压缩 `chat_log` 行），**不复活独立 `compress_memory()`**，省一次 LLM 成本。原 `compress_memory()` 仍在 `_handle_chat` 后台线程独立运行，作为总轮次超额时的安全网（与认知抽取互不冲突）。
- **Source 适配器位置**：`UserModelSource` / `EpisodicSource` 放在 `context/cognitive_sources.py`（而非 `cognitive/` 内），以严格遵守「cognitive 不反向依赖 context」的硬约束（单向依赖）。
- **轮次拆分实际落地**：Round1 认知层 4 新文件（`cognitive/`）+ 改 `context/models.py`(EPISODIC)/`context/sources.py`(隔离)/`config.py`(Flag+白名单)；Round2 `context/builder.py`(注册)+`db.py`(两表)+`server.py`(端点+触发)；Round3 `tools.py`(remember)。每轮均守 ≤3 改 / ≤5 新 / ≤500 行。

### 验证
- `py_compile` 全文件通过。
- 临时实例（端口 8011，复用真实 DB，只读新端点）冒烟：`/api/health` 显示 **56 个工具（含 remember）**、自检全绿；`/api/user_model` 返回默认骨架 JSON；`/api/episodes` 返回 `{"episodes":[]}`。embed 本地 ONNX 模型已就绪，语义召回实测生效。临时实例已精准关闭，未影响主 8000 服务。

---

## 十四、E 自审修正（2026-07-31 · 自审阶段）

D 实现完成后补做 v2 六阶段的 **E 自审**。通过逐文件重读 + 跨模块契约核对（`agnes_completion` 响应结构、`embed.semantic_search` 签名、`BuildContext.user_text`、`config.reload` global 列表、`memory.compress_memory` 实际接线）+ 隔离临时 DB 的端到端冒烟，发现并修复 **2 个关键缺陷**（此前 <40 轮冒烟无法暴露）：

### 缺陷 1（致命）：Feature Flag 运行时恒为 False，P1 整特性被"静默关闭"
- **根因**：`config.reload()` 对 `FEATURE_USER_MODEL` / `FEATURE_EPISODIC_MEMORY` 的赋值**未加入 `global` 声明**（reload 顶部 global 列表只含 `FEATURE_CONTEXT_ENGINE` 等，漏了这两个）。Python 函数内无 `global` 的同名赋值会创建局部变量，模块级 `config.FEATURE_USER_MODEL` 永远停在声明默认值 `False`。
- **后果**：`builder.py` 按 Flag 注册认知来源时 `getattr(config,...)` 恒为 False → 来源从不注册 → 系统提示词永不注入 `【用户模型】`/`【相关经历】`；后台抽取虽被触发但子写入又按 Flag 门控，等于整特性完全不工作。此前冒烟仅查"工具数=56"与空端点，未断言 Flag 值，故漏检。
- **修复**：`config.py` 的 `global` 行补入 `FEATURE_USER_MODEL, FEATURE_EPISODIC_MEMORY`。实证：`import config` 后两 Flag 现为 `True`。
- **关联验收点**：§十一 第 1/3/4 条依赖 Flag 正确解析，此前全部不成立。

### 缺陷 2（严重）：`maybe_extract` 与 `compress_memory` 双写 / 竞争删除
- **根因（并修正 §十三 偏差说明的一处错误判断）**：`server.py:_handle_chat` 每轮后台**同时**启动 `compress_memory()`（写 `memory_summary` + 删最旧 `chat_log` 行）与 `maybe_extract()`。原 §十三 称"互不冲突"是**错误**的——两者并发写同一 `memory_summary(id=1)` 行（后写覆盖、内容策略不同→信息丢失），且都 `DELETE ... LIMIT prune`，存在竞态：若抽取线程在压缩线程删后再删，会把**最近的 24 条在聊上下文误删**。
- **修复**：明确职责切分——`memory.compress_memory` 仍是唯一的"长期摘要 + 旧轮次压缩"所有者；`extractor.maybe_extract` **不再写 `memory_summary`、不再删 `chat_log`**，只专注其独有职责（用户模型增量 + 新 episodes），并按各自 Flag 门控落库。`_SYS` 提示词移除 `summary_update` 字段。`server.py` 触发处也改为仅在至少一个 Flag 开启时才起线程。
- **影响**：消除竞态与双写；`chat_log` 仍有 `compress_memory` 兜底压缩，无回归。

### 自审后的端到端验证（隔离临时 DB，不污染生产库）
- 临时 DB 跑 15 项断言（14 项功能通过；1 项为断言字符串笔误：`str(ContextSource.USER)` 是 `"ContextSource.USER"` 而非 `"user"`，已由"prompt 实际含【用户模型】+Laravel"与 facade 注入两条断言反证通过）。
- 关键链路实证：Flag=True → `LegacyContextBuilder` 注册 `user_model`+`episodic` → `build_context_prompt("用 Laravel 写后台")` 输出**确实包含 `【用户模型】` 块且含 Laravel**；`add_episode`→`recall_episodes("部署 Laravel…")` 命中（相关度 0.805，标题匹配）；`list_episodes`/`render_episodes_block` 正常。
- 全程未触碰真实 `xiao6.db`（临时库用完即删）。

### 缺陷 3（中）：`DEFAULT_MODEL` 被 `upsert` 原地污染（重启验证阶段发现）
- **发现时机**：重启后端后做**实况验证**（见 §十五），在测试进程里 `upsert` 一条标记数据后删除，再断言 `is_empty(load_user_model())` 期望为 `True`，却得到 `False`。顺藤摸瓜定位到根因。
- **根因**：`load_user_model()` 用 `dict(DEFAULT_MODEL)` 做**浅拷贝**，`upsert_user_model()` 对嵌套字典字段（`identity`/`communication_style`/`preferences`）走 `base.update(v)` 时，直接修改了与模块级 `DEFAULT_MODEL` **共享**的嵌套对象。首次 `upsert` 后，骨架被永久写入测试值；即便之后删掉 DB 行，`load_user_model()` 仍返回被污染的骨架 → `is_empty` 误报非空。
- **后果**：生产环境里若用户清空记忆（删 `user_model` 行），再次 `load` 会得到被污染的默认骨架；且同进程内 `is_empty` 判断失真。正常有 DB 行时不影响（读 DB），但属潜在正确性缺陷。
- **修复**：`load_user_model()` 两处返回改为 `copy.deepcopy(DEFAULT_MODEL)`（新增 `import copy`）。实证：`upsert` 后 `DEFAULT_MODEL['identity']` 不变；删除行后 `load` 返回独立空骨架，`is_empty=True`。

### 结论
P1（用户模型 + 情节记忆）经自审 + 重启实况验证后**确认可验收**：Flag 解析正确、来源注入生效、语义召回生效、无双写竞态、骨架不被污染。剩余 Phase 2 项（前端 🧠 只读画像面板）见 §十六实现。
- 行为预期：聊天轮次累计 >40 后，下一轮会自动触发抽取，填充 `user_model` 与 `episodes` 表，best-effort 不影响对话。

## 十五、F 总结（P1 全周期收口 · 2026-07-31）

### 目标
给 Context Engine 加两类认知来源——**结构化用户画像（User Model）**与**按需语义召回的情节记忆（Episodic Memory）**，使每轮系统提示词自动携带、严守 v2 架构宪法（cognitive/ 新包、FEATURE_* Flag、≤500 行、本地优先、不碰 memory.py 读路径、向后兼容）。

### 六阶段回顾
- **A 分析 → B 设计**：产出本方案文档（§一~§十二），含 4 个待拍板决策点。
- **C 批准**：老板授权"自主拍板执行细节"，据此做出 4 项决断（Flag 默认 ON / 抽取器自管压缩→后改为不碰压缩 / 前端面板后置 / 采纳 SourceRegistry 逐源隔离）。
- **D 实现**：4 个新文件（cognitive/ 包：user_model / episodic / extractor / __init__）+ 7 个既有文件改动（context/models、context/sources、context/builder、config、db、server、tools）+ 设计文档实现记录。
- **E 自审**：逐文件重读 + 跨模块契约核对 + 隔离临时 DB 端到端冒烟，挖出 **3 个缺陷**（Flag 死变量、双写竞态、骨架污染）并全部修复。
- **F 总结**：即本节。

### 关键决策与偏差
1. Flag **默认 ON**（`.env` 不设时 env 默认 `"true"`，可瞬切 OFF）—— 验收可观测。
2. 抽取器**不接管** `memory_summary`/`chat_log` 压缩（修正 D 阶段"自管压缩"偏差）—— 避免与既有 `compress_memory` 双写竞态；`extractor` 只干用户模型 + episodes 本职。
3. 前端 🧠 只读画像面板**后置**到 Phase 2（本轮仅后端 + API + `remember` 工具）。
4. 依赖方向：cognitive 单向依赖 db/embed/config，Source 适配器放 `context/cognitive_sources.py`，保单向、防循环。
5. 语义召回**零新依赖**——复用既有 `embed.py` 本地 bge-small-zh ONNX 向量。

### 缺陷修复清单
| # | 严重度 | 缺陷 | 修复 |
|---|--------|------|------|
| 1 | 致命 | Flag 运行时恒 False（漏写 `global`）→ 整特性静默关闭 | reload 补 `global` 声明 |
| 2 | 严重 | `maybe_extract` 与 `compress_memory` 双写 + 竞争删除 | 职责切分，抽取器不再碰 summary/chat_log |
| 3 | 中 | `upsert` 浅拷贝污染 `DEFAULT_MODEL` 骨架 | `load` 改 `deepcopy` |

### 验证结论（重启后实况，生产库零污染）
- 后端（系统 Python 3.11）重启加载修复后代码：`/api/health` 56 工具（含 `remember`）、自检全绿、Flag=`True/True`。
- 实况断言全绿：Flag 解析正确；`build_context_prompt` 注入 `【用户模型】` 块（含 Laravel/张总）；`recall_episodes` 命中（相关度 0.685）；`/api/user_model`、`/api/episodes` 端点返回正确结构。
- 骨架污染修复后：`is_empty(load_user_model())` 在清理后正确返回 `True`。
- 验证过程写入的标记数据 **全部回滚**（仅删本轮新增 + 按标题兜底删），生产 `xiao6.db` 的 `user_model`/`episodes` 保持原状（空）。

### 遗留 / 后续
- **Phase 2 前端 🧠 只读画像面板**：见 §十六（已在本轮一并实现）。
- 真实环境累计对话 >40 轮后首次自动触发抽取，建议观察 `user_model`/`episodes` 自动演化是否符合预期。
- ctx 来源优先级/预算（priority/importance/recency 权重）可按实测调参。

## 十六、Phase 2 实现：前端 🧠 用户画像只读面板（2026-07-31）

> 后端认知层已就绪（API：`/api/user_model`、`/api/episodes`、`remember` 工具）。前端补一个**只读**可视化面板，让老板直观看到小6"记住了什么"。

### 实现要点（2026-07-31 落地）
- **新文件 `userprofile.js`**（ES Module，遵循 `window.ZZxxx` 桥约定）：对外暴露 `window.ZZUserProfile = { open, refresh }`；自行绑定 rail chip 点击事件。
  - 拉取 `/api/user_model` 与 `/api/episodes?limit=30`（`Promise.allSettled` 容错，单端失败不阻断）。
  - 渲染复用既有 `.zz-panel-*` 玻璃拟态样式（`section / name / tagline / tags / list / footer`），新增 `.up-ep*` 情节卡片样式（青绿左边框 + 分类标签 + 标题 + 摘要 + 时间/重要度）。
  - 空态友好：用户模型为空显示"小6还在了解你…"；情节为空显示"暂无相关经历…"提示。
  - 内置 `↻ 刷新` 按钮，重新拉取。
- **`index.html`**：在 rail「快捷能力」chip-row 增加 `🧠 画像` chip（`id="btnUserProfile"`）；按既有约定新增 `<script type="module" src="userprofile.js?v=20260731b">`（置于 `app.js` 之前）；`styles.css?v` 由 `20260731za` 升到 `20260731zb` 强制刷新。
- **`styles.css`**：追加 `.up-loading / .up-refresh / .up-ep* ` 一组样式，沿用 `--cyan`/`--teal`/`--txt` token 与玻璃拟态。
- **未改后端**：Phase 2 纯前端，复用既有 API 与 `window.ZZPanel.open/update`（`app.js` 已暴露），无需重启后端（静态文件由 server 直读磁盘）。

### 验证
- `node --check userprofile.js` 通过；离线复刻渲染函数校验：空骨架渲染长度 0（走 fallback）、填充态正确渲染姓名/专长标签/沟通风格/偏好/情节卡片（含分类小写、重要度 0.80），无 `undefined`/未转义泄漏。
- 实况（已重启后端、修复后）：`/userprofile.js`、`/index.html`、`/styles.css` 均 200 且含对应标记；`/api/user_model` 返回 7 个键骨架；`/api/episodes` 返回空（尚无抽取数据，符合预期）。
- 浏览器侧交互（点击 🧠 画像 chip 弹出侧栏）需在前端页面手动验证一次（无头环境无法自动点按）。

