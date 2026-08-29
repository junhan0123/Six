# 《Xiao6 v2 · Phase 2 设计方案：EventBus + 世界模型 + 更多认知 Source》

> 版本：v2-Phase2 设计稿（B 设计 · 待 C 批准）
> 作者：Senior Developer（高级开发工程师）
> 日期：2026-07-31
> 依据：《Xiao6-v2-核心架构规范.md》（最高宪法）+ 《Xiao6-v2-架构升级设计文档.md》（实施计划）
> 前置：P0（Context Engine 骨架）+ P1（用户模型 + 情节记忆）已落地并通过自审/验证

---

## 一、目标与范围

在 P1 已建立的 **Context Engine 门面（`context/` 包 + `SourceRegistry` + `ContextSourceProvider` 协议）** 与 **认知数据层（`cognitive/` 包）** 之上，补齐 v2 宪法的两块地基与一类扩展：

1. **EventBus（`eventbus.py`）** —— 系统唯一模块间通信脊柱，取代 `proactive.SUBSCRIBERS` 全局队列与跨模块直发（宪法 §15、§1.5、§22.2）。
2. **世界模型（`world_state.py`）** —— 把散落的天气/位置/系统/Git/项目/网络/作息聚成统一只读 `WorldSnapshot`，按域 TTL 缓存，供 Context Engine 注入（宪法 §6、§4.1）。
3. **更多认知 Source** —— 在 P1 的 `UserModelSource` / `EpisodicSource` 适配器模式上，新增 `WorldStateSource`（`ContextSource.WORLD`）与 `PersonalitySource`（`ContextSource.PERSONALITY`），并**固化 Source 扩展契约**，让后续 Goal / Knowledge Graph / Long-Term Memory 增强以同一姿势接入。

**不做（明确边界）**：
- 不碰 `server.py` 的路由骨架大拆分（那是设计文档 Phase 1.4，留待后续独立 PR）。
- 不实现完整 Goal System / Knowledge Graph（仅定义 Source 接入契约，依赖各自子系统就绪后补 Source 适配器）。
- 不重写前端（仅 SSE 推送通道在后端桥接层切换，前端 SSE 报文格式**零改动**）。

---

## 二、关键决策（4 项，待批准）

| # | 决策 | 理由 / 依据 |
|---|---|---|
| D1 | **EventBus 作为常驻基础设施，无独立开关；但 SSE 迁移（proactive/scene/server 改用 EventBus）由 `FEATURE_EVENTBUS` 门控，默认 ON，可瞬切回 `SUBSCRIBERS` 旧路径** | 基础设施本身纯新增、零行为变化；行为变化（SSE 桥）需可瞬切回退（v2 增量/兼容原则）。 |
| D2 | **世界模型与人格引擎默认 ON（`FEATURE_WORLD_MODEL` / `FEATURE_PERSONALITY`），关闭即不向 Prompt 注入对应块，用户路径零变化** | 沿用 P1 Flag 范式；默认开以便验收，任一来源异常都被 `SourceRegistry.collect` 隔离（P1 已验证）。 |
| D3 | **`world_state.py` / `personality.py` / `eventbus.py` 置于 `xiao6-ui/` 根目录（扁平），与现有 `memory.py`/`db.py`/`config.py` 一致；不先行目录重整** | 避免在一个外科手术式 PR 里顺带搬目录（增加回退面）。宪法 §24.1 的目标目录（`cognitive/`）由后续"Server 模块化 / 目录规范化"统一归位。已在本文 §八标注为已知偏差。 |
| D4 | **人格引擎首版以"当前行为等价"为目标**：默认五维参数产出与现有 `config.SYSTEM_PROMPT` 基线一致的提示词；并复用 P1 已抽取的 `user_model.communication_style` 做轻量种子** | 宪法 §19.2/§19.3 要求人格动态生成且不得写死；但过渡期必须"无感切换"，故默认参数映射回现状，后续再开放设置面板调参（§七 备注）。 |

---

## 三、架构总览（Phase 2 增量视图）

```
┌─────────────────────────────────────────────────────────────┐
│  现有 context/（Context Engine 门面，P0/P1 已建）            │
│    SourceRegistry                                            │
│      ├─ MemorySource          (已注册)                       │
│      ├─ UserModelSource       (P1, FEATURE_USER_MODEL)       │
│      ├─ EpisodicSource        (P1, FEATURE_EPISODIC_MEMORY)  │
│      ├─ WorldStateSource  ★新增 (FEATURE_WORLD_MODEL)        │
│      └─ PersonalitySource ★新增 (FEATURE_PERSONALITY)        │
├─────────────────────────────────────────────────────────────┤
│  ★新增 cognitive 适配器（context/world_source.py,            │
│                    context/personality_source.py）           │
│     —— 仅读取各自数据模块，try/except 隔离，不发业务调用     │
├─────────────────────────────────────────────────────────────┤
│  ★新增 数据/服务层（扁平）                                   │
│    world_state.py   → WorldSnapshot + 按域 TTL 缓存          │
│                      publish WorldStateChanged               │
│    personality.py    → PersonalityParams + render_prompt     │
│                      publish PersonalityChanged              │
│    eventbus.py       → 唯一脊柱（pub/sub + 线程池 + 重试 + DL）│
├─────────────────────────────────────────────────────────────┤
│  迁移点（D1）                                                │
│    proactive.py / scene.py / server.py(SSE 桥)               │
│     旧：直发 SUBSCRIBERS 全局队列                            │
│     新：publish 领域事件 → 单一 SSE 桥 subscribe → 扇出队列  │
└─────────────────────────────────────────────────────────────┘
        所有状态变更经 EventBus；禁止跨模块直接调用（§1.5/§22.2）
```

依赖方向（单向 DAG，无环，§1.10）：
`context/world_source.py` → `world_state`（新）；`context/personality_source.py` → `personality`（新）；`world_state` / `personality` → `eventbus`（发布事件）；`proactive`/`scene`/`server` → `eventbus`（订阅/发布）。`eventbus` 不反向依赖任何业务模块。

> 注：`ContextSource` 枚举（P0 已预置）已含 `WORLD="world"`、`GOAL`、`WEATHER`、`KNOWLEDGE` 等；本方案直接复用 `WORLD`，并为人格新增 `PERSONALITY="personality"`（models.py 一行）。

---

## 四、各 Step 详细设计（为什么 / 影响 / 新增 / 兼容 / 风险 / Rollback）

### Step 2.1 — EventBus（`eventbus.py`，常驻基础设施）

- **为什么**：宪法 §15 铁律——模块间唯一通信脊柱，取代 `proactive.SUBSCRIBERS` 全局可变列表（§1.5、§22.2），并为后续所有模块（World/Goal/User/Personality/Proactive）解耦。
- **新增**：`eventbus.py`（纯标准库，无新依赖）。
  - `Event`：dataclass — `event_id(uuid4)`、`topic`、`timestamp`、`source`、`payload: dict`、`priority: int=5`、`correlation_id`。
  - `EventBus`：
    - `subscribe(topic, cb, async_=False, priority=5) -> token`；`unsubscribe(token)`。
    - `publish(topic, payload, *, source="", correlation_id=None, priority=5)`，或 `publish_event(event)`。
    - 派发：`sync` 订阅者内联执行（**必须 <100ms**，§15.5）；`async_` 订阅者投入 `ThreadPoolExecutor`（标准库，无新依赖）。
    - 重试：订阅者抛错按 `priority` 重试 0–3 次；耗尽进 **Dead-Letter** 队列（内存列表 + 可选落 `meta` 表供 Dashboard，§21.2）。
    - 约束：payload **仅 dict**（禁止不可序列化对象，§15.5）；结构化日志，禁打密钥/PII（§25.1、§13）。
  - 进程级单例 `bus = EventBus()`。
- **影响（迁移）**：
  - `proactive.py`：移除对 `SUBSCRIBERS` 的直发；改为 `bus.publish("ProactivePush", {...})`（保留旧 `SUBSCRIBERS` 分支，**由 `FEATURE_EVENTBUS` 选择**）。
  - `scene.py`：同理改为 `bus.publish("SceneCard", {...})`。
  - `server.py` SSE 桥（`SUBSCRIBERS.append/remove` + 推送循环）：改为在连接建立时 `bus.subscribe("SseDispatch", _fanout_to_queue)`（或订阅各域事件汇总到 `SseDispatch`），断开时 `unsubscribe`。**SSE 报文格式不变**（前端零改动，§7 兼容）。
- **兼容**：HTTP API / DB / 工具契约全不变；`window.ZZ*` 前端桥（UI 模块间）暂不在本 Step 动（§7 允许保留别名），仅替换后端 SSE 直发。
- **风险**：中（SSE 是实时通道，迁移错会丢推送）。缓解：双路径 `FEATURE_EVENTBUS` 可瞬切；curl SSE 回归清单（§六）。
- **Rollback**：`FEATURE_EVENTBUS=false` 即回旧 `SUBSCRIBERS` 路径；或 revert 提交。

### Step 2.2 — 世界模型（`world_state.py` + `context/world_source.py`）

- **为什么**：宪法 §6 + §4.1（World State 为 Context 来源之一）；现状天气/位置/系统/Git 散落各模块全局态（如 `server.py` 直接 `import weather; weather._LAST=None`，设计文档 P3 已标记风险）。
- **新增**：
  - `world_state.py`：
    - `WorldSnapshot` dataclass：time/date/weekday/tz、location{city,lat,lon,type}、weather{temp,cond,aqi,alert}、device、cpu/gpu/mem、git_status{branch,dirty,last_commit}、current_project、network{reachable,latency,proxy}、work_hours/rest_hours（来自 user_model + config）、events_today（Phase 2 先留 None，待 Goal/Task 接入）。
    - 采集器 + **按域 TTL 缓存**（§11 禁无 TTL 缓存）：time=实时；weather/location=600s；system=30s；git/project=300s；network=60s。统一 `_cache: dict[str, (val, expires)]`。
    - `snapshot() -> WorldSnapshot`：time 实时，其余读缓存（过期则惰性刷新）。
    - 显著变化（位置/天气预警/网络中断/项目切换）`bus.publish("WorldStateChanged", delta)`（§6.3）。
    - 迁移 `weather._LAST`：`weather.py` 保留 provider 函数；WorldModel 调其并缓存；移除 `server.py` 的 `weather._LAST=None` 突变（由 `world_state.refresh("weather")` 取代）。
  - `context/world_source.py`：`WorldStateSource(ContextSourceProvider)`，`collect(ctx)` 读 `world_state.snapshot()` → 渲染紧凑【世界状态】块（时间/天气/位置/作息）→ `ContextItem(source=ContextSource.WORLD, ...)`。**内部 try/except 隔离**（沿用 P1 范式）。
- **影响**：`context/builder.py` 在 Flag 门控下 `registry.register(WorldStateSource())`；`context/models.py` 无需改枚举（复用 `WORLD`）；`config.py` 增 `FEATURE_WORLD_MODEL`（global 行 + ENV_KEYS，仿 P1）。
- **兼容**：`/api/weather` 等仍可用（内部来源改为 WorldModel 缓存）；Prompt 仅在 Flag ON 时多一块【世界状态】。
- **风险**：中（采集器需 `sysmon`/`geo_weather`/`git` 调用）。缓解：全部 TTL 缓存 + 采集失败降级到上一次快照（不阻塞对话，§3.2 降级原则）。
- **Rollback**：`FEATURE_WORLD_MODEL=false` 即不注册该 Source；或 revert。

### Step 2.3 — 人格引擎（`personality.py` + `context/personality_source.py`）

- **为什么**：宪法 §19（Personality 五维动态生成，不得写死）；§4.1 将 Personality 列为 Context 来源。
- **新增**：
  - `personality.py`：
    - `PersonalityParams` dataclass：professionalism / proactivity / technical_depth / verbosity / seriousness（0–1）。
    - `generate(user_model=None, world=None, goals=None) -> PersonalityParams`：**默认参数 = 当前行为等价**（高专业、中技术深度、偏高严肃、中解释长度、低主动），并**种子自 P1 `user_model.communication_style`**（verbosity/humor 映射，使已抽取画像生效）。
    - `render_prompt(params) -> str`：产出人格指令块（如"简洁直接、技术准确、不过度展开"）。
    - `bus.publish("PersonalityChanged", params_dict)`（供 Dashboard，§21.2）。
  - `context/personality_source.py`：`PersonalitySource(ContextSourceProvider)`，`collect(ctx)` → `personality.generate(...)` → `ContextItem(source=ContextSource.PERSONALITY, ...)`。
  - `context/models.py`：枚举加 **`PERSONALITY = "personality"`**（一行；`@unique` 不冲突）。
- **影响**：`context/builder.py` Flag 门控注册；`config.py` 增 `FEATURE_PERSONALITY`。
- **兼容**：默认参数映射回现状 → **无感切换**（关闭 Flag 与现状逐字节一致）。设置面板调参（§19.3 多 Profile）留作后续，本 Step 仅预留 `generate` 的 override 入参。
- **风险**：低（纯新增 + 默认等价）。
- **Rollback**：`FEATURE_PERSONALITY=false` 即不注入；或 revert。

### Step 2.4 — 固化"更多认知 Source"扩展契约（文档 + 模板）

- **为什么**：用户点名"更多认知 Source"；需把 P1 适配器范式**显式契约化**，让 Goal / Knowledge Graph / Long-Term Memory 增强零摩擦接入。
- **契约（强制）**：
  1. 每个 Source = 一个实现 `ContextSourceProvider.collect(ctx) -> list[ContextItem]` 的类。
  2. 数据/逻辑放在对应服务模块（`world_state`/`personality`/`goals`/`memory`…），**适配器只读取、不写业务**；禁止适配器直调其他模块业务函数（§1.5/§22.2）。
  3. `collect` 内部 **try/except 隔离**，单源失败不影响其他来源与对话（P1 `SourceRegistry.collect` 已逐源隔离）。
  4. 在 `context/builder.py` **按 Feature Flag 注册**；Flag 默认 ON、可瞬切。
  5. 状态变更通过 EventBus 发布，不反向依赖 Context Engine。
  6. 枚举值复用 `ContextSource`（已含 GOAL/KNOWLEDGE 等），新增须显式加到 `models.py`。
- **路线图 Source（本方案不实现，仅列接入点）**：
  - `GoalSource`（`ContextSource.GOAL`）→ 依赖 Goal System（设计文档 Phase 2.2，后续独立 PR）。
  - `KnowledgeGraphSource`（`ContextSource.KNOWLEDGE`）→ 依赖 Knowledge Graph（宪法 §14，后续）。
  - `LongTermMemorySource` 增强 → 扩展现有 `MemorySource` 纳入语义记忆（§5.1），小改。

---

## 五、关键契约与接口（草案）

```python
# eventbus.py（节选）
@dataclass
class Event:
    event_id: str
    topic: str
    timestamp: float
    source: str
    payload: dict
    priority: int = 5
    correlation_id: str | None = None

class EventBus:
    def subscribe(self, topic: str, cb, *, async_: bool = False, priority: int = 5) -> str: ...
    def unsubscribe(self, token: str) -> bool: ...
    def publish(self, topic: str, payload: dict, *,
                source: str = "", correlation_id: str | None = None,
                priority: int = 5) -> None: ...

# world_state.py（节选）
@dataclass
class WorldSnapshot:
    time: str; date: str; weekday: str; tz: str
    location: dict; weather: dict; device: dict
    cpu: float; gpu: float; mem: float
    git_status: dict; current_project: str | None
    network: dict; work_hours: dict; rest_hours: dict
    events_today: list | None = None

def snapshot() -> WorldSnapshot: ...          # time 实时，其余 TTL 缓存
def refresh(domain: str | None = None) -> None: ...  # 主动失效（取代 weather._LAST）

# personality.py（节选）
@dataclass
class PersonalityParams:
    professionalism: float = 0.8
    proactivity: float = 0.2
    technical_depth: float = 0.6
    verbosity: float = 0.4        # 实现修正：<0.5 走"简洁"分支，对齐现状基线（草案 0.5 会因阈值相等误走"详尽"）
    seriousness: float = 0.8

def generate(user_model=None, world=None, goals=None,
             override: PersonalityParams | None = None) -> PersonalityParams: ...
def render_prompt(p: PersonalityParams) -> str: ...
```

---

## 六、测试与验收

**单元（无真实依赖，可独立跑，§8 宪法）**：
- `eventbus`：sync/async 派发、重试次数、Dead-Letter、payload 非 dict 拒绝。
- `world_state`：TTL 命中/过期、采集器失败降级、snapshot 不触发外部调用（mock 采集器）。
- `sources`：`WorldStateSource`/`PersonalitySource` 在 Flag ON/OFF 时分别产出/不产出 `ContextItem`；异常被隔离。

**集成（实况，隔离临时 DB，不碰生产 xiao6.db）**：
- SSE 回归：开启 `FEATURE_EVENTBUS` 后，`proactive` 推送仍经 SSE 到达（curl/前端观测）；关闭则走旧 `SUBSCRIBERS`，行为一致。
- Prompt 注入：构造 `build_context_prompt("今天天气如何")`：
  - `FEATURE_WORLD_MODEL=true` → 输出含【世界状态】块；
  - `FEATURE_PERSONALITY=true` → 含人格指令块；
  - 任一切 false → 对应块消失（**瞬时回退验证**）。
- 兼容：前端 SSE 报文结构不变；`weather._LAST` 突变已移除，天气接口正常。

**性能（§26）**：World `snapshot()` 走缓存，单次 < 5ms；Context Engine 装配 < 2s；EventBus `publish` 非阻塞。

---

## 七、实施进度与任务拆分（遵循 v2 六阶段 + 纪律）

> 纪律：每轮 ≤3 已有文件 / ≤5 新文件 / ≤500 行；小步提交可 revert；六阶段 A分析→B设计→C批准→D实现→E自审→F总结。

- **A 分析**：本文 §一~§四（已完成，本稿即 A+B）。
- **B 设计**：本文（待 C 批准）。
- **C 批准**：待老板拍板（本稿交付后即此步）。
- **D 实现**（获批后，分 3 个子轮）：
  - 轮 2.1：`eventbus.py`（新）+ `config.FEATURE_EVENTBUS` + proactive/scene/server SSE 桥迁移。
  - 轮 2.2：`world_state.py`（新）+ `context/world_source.py`（新）+ `context/models.py` 加 `PERSONALITY` + `context/builder.py` 注册 + `config.FEATURE_WORLD_MODEL`。
  - 轮 2.3：`personality.py`（新）+ `context/personality_source.py`（新）+ `context/builder.py` 注册 + `config.FEATURE_PERSONALITY`。
- **E 自审**：逐文件契约核对 + 隔离 DB 端到端验证（仿 P1 自审，挖 Flag/双写/竞态类缺陷）。
- **F 总结**：收口文档。

**备注（D4 后续）**：设置面板人格多 Profile 调参（§19.3）不在本 Phase 2 范围，列为 Phase 2.5 或并入前端迭代。

---

## 八、偏差与备注

1. **目录偏差（D3）**：方案把 `world_state.py`/`personality.py`/`eventbus.py` 放根目录扁平，而宪法 §24.1 目标目录将它们置于 `cognitive/` 与根 `eventbus.py`。理由：外科手术式 PR 不顺带搬目录，降低回退面；后续"Server 模块化 / 目录规范化"统一归位。属已知、可控偏差。
2. **Phase 命名对齐**：设计文档把 EventBus/WorldModel 列为"Phase 1 Step 1.1/1.2"，把 UserModel 列为"Phase 2.3"。本项目增量序列为 P0(Context Engine)→P1(UserModel+Episodic)→**本 Phase 2(EventBus+World+更多 Source)**。本方案以"增量演进"原则（§1.7）重新切分，不与设计文档的 Phase 标签冲突；宪法只约束原则，不约束 Phase 编号。
3. **Goal/Knowledge Graph 不在本 Phase**：仅固化 Source 契约与枚举占位，待各自子系统就绪后补适配器（§四 Step 2.4）。
4. **`weather._LAST` 全局态**：明确迁移到 `world_state.refresh()`，消除 `server.py` 直接变异模块全局（设计文档 P3 风险项）。

---

## 九、宪法符合性自检（关键条款）

| 宪法条款 | 本方案符合性 |
|---|---|
| §1.5 / §15 / §22.2 事件驱动、EventBus 为唯一脊柱 | ✅ 新增 `eventbus.py`；proactive/scene/server 改经 EventBus；禁跨模块直发 |
| §1.9 / §24.3 禁 God Module（≤500 行） | ✅ 各新文件单一职责，均 < 500 行 |
| §1.10 禁循环依赖 | ✅ 依赖单向：context 适配器 → 服务模块 → eventbus |
| §4 / §17 Context 必须由 Context Engine 生成 | ✅ 新 Source 经 `SourceRegistry` 注入，无模块手写 System Prompt |
| §6 世界模型 + §4.1 Context 来源 | ✅ WorldStateSource 对应 `ContextSource.WORLD` |
| §11 禁无 TTL 缓存 | ✅ WorldModel 全域 TTL 缓存 |
| §7 / §1.6 向后兼容 | ✅ Flag 默认 ON 且等价现状；SSE 报文零改动；`weather._LAST` 安全迁移 |
| §1.7 增量演进 | ✅ 纯新增 + Flag 门控，可瞬切回退 |
| §8 本地优先 | ✅ WorldModel 本地缓存；外部读取结果本地化 |
| §12/§25 可观测、结构化日志、禁密钥/PII | ✅ EventBus 带 event_id/correlation_id；日志禁打密钥 |
| §15.5 禁不可序列化对象入总线 | ✅ payload 仅 dict |

---

## 十、结论与待批准项

Phase 2 在 P1 地基上**低成本、低风险**地补齐 v2 两大陆基（EventBus + 世界模型）并扩展认知 Source 体系，全程遵守增量/兼容/事件驱动宪法。所有行为变化均可经 Feature Flag 瞬时回退，所有新文件单一职责、可独立测试。

**请老板审阅并批准（C 批准）以下 4 项决策（D1–D4）与三个 Step（2.1/2.2/2.3）**；批准后我即进入 D 实现，按 §七子轮小步落地并做 E 自审。

> **状态更新（2026-07-31）**：C 已批准（用户「Phase 2 开干」），D 实现全部子轮（2.1/2.2/2.3）已落地并各自隔离验证全绿，E 自审已完成，本文增补 §十一（E 自审）与 §十二（F 总结）。

---

## 十一、E 自审（实现后复核）

> 纪律：逐文件契约核对 + 隔离临时 DB 端到端验证；挖 Flag/双写/竞态类缺陷。所有临时验证脚本与临时 DB 均已清理，未污染生产 `xiao6.db`。

### E.1 逐文件契约核对

| 文件 | 类型 | 职责 | 契约符合性 |
|---|---|---|---|
| `eventbus.py` | 新 | EventBus 单例、pub/sub、重试+死信、TTL 无关 | ✅ 纯标准库；`payload` 仅 dict（§15.5）；`subscribe/unsubscribe/publish`；`TOPIC_SSE="zz.sse"` 统一汇聚；`enabled()` 门控；`publish_sse()` 便捷入口 |
| `world_state.py` | 新 | WorldSnapshot + 按域 TTL 缓存 + 采集器降级 | ✅ 全域 TTL（weather/location=600s, system=30s, git/project=300s, network=60s）；`snapshot()` 实时 time + 缓存；`refresh(domain)` 取代 `weather._LAST`；采集失败降级旧值/默认 |
| `personality.py` | 新 | PersonalityParams 五维 + `generate()` + `render_prompt()` | ✅ 默认等价现状（verbosity=0.4 对齐"简洁"）；种子自 P1 `user_model.communication_style`；`publish_changed()` 经 bus 发 `PersonalityChanged` |
| `context/world_source.py` | 新 | `WorldStateSource(ContextSourceProvider)` | ✅ `collect` 调 `world_state.snapshot()`+`render_world_block()`；`ContextItem(source=WORLD)`；try/except 隔离 |
| `context/personality_source.py` | 新 | `PersonalitySource(ContextSourceProvider)` | ✅ 复用 P1 `load_user_model`/`is_empty` 种子；`ContextItem(source=PERSONALITY)`；try/except 隔离 |
| `context/models.py` | 改 | 枚举加 `PERSONALITY` | ✅ 在 `EPISODIC`/`WORKFLOW` 间加 `PERSONALITY="personality"`，`@unique` 不冲突 |
| `context/builder.py` | 改 | Flag 门控注册两 Source | ✅ `if FEATURE_WORLD_MODEL: registry.register(WorldStateSource())`；`if FEATURE_PERSONALITY: registry.register(PersonalitySource())` |
| `config.py` | 改 | 三 Flag 声明 + `global` + env 默认 + ENV_KEYS | ✅ **吸取 P1 致命教训**：`reload()` 的 `global` 行补 `FEATURE_EVENTBUS/WORLD_MODEL/PERSONALITY`；env 默认 `"true"`（ON）；`ENV_KEYS` 白名单加三键；模块导入即 `load_env()+reload()`（行 219–220） |
| `proactive.py` | 改 | SSE 双路径 | ✅ `_use_eventbus()` + `_dispatch_sse()`：bus 成功 `publish_sse` 否则回退 `SUBSCRIBERS` 直发；保留 `SUBSCRIBERS/SUBSCRIBERS_LOCK` 全局 |
| `scene.py` | 改 | SSE 双路径 | ✅ 同 proactive 模式；仍 `from proactive import SUBSCRIBERS, SUBSCRIBERS_LOCK` |
| `server.py` | 改 | SSE 桥 + 天气缓存同步 | ✅ `_handle_stream` 连接时 `bus.subscribe(TOPIC_SSE, cb)`、断开 `unsubscribe`（Flag ON）；否则 `SUBSCRIBERS.append/remove`；`_handle_chat` 天气失效处 Flag ON 时 `world_state.refresh("weather")`，**保留旧 `weather._LAST=None` 行**（弹窗兼容） |

### E.2 单元/隔离验证结果（临时 DB，不碰生产）

| 子轮 | 验证脚本（已清理） | 结果 |
|---|---|---|
| 2.1a EventBus + Flag | 9 项断言 | ✅ 9/9 ALL_GREEN（sync/async 派发、重试、Dead-Letter、payload 非 dict 拒绝、enabled() 门控） |
| 2.1b SSE 双路径 | 隔离断言 | ✅ ALL_GREEN（proactive/scene `publish_sse` 与 SUBSCRIBERS 回退均可达） |
| 2.2 世界模型 | 16 项断言 | ✅ 16/16 ALL_GREEN（TTL 命中/过期、采集器失败降级、`snapshot()` 不触发外部调用、prompt 注入【世界状态】块、`refresh` 失效） |
| 2.3 人格引擎 | 17 项断言 | ✅ 17/17 ALL_GREEN（默认等价现状、verbosity=0.4 渲染"简洁"、communication_style 种子映射、`render_prompt` 五维、异常隔离） |
| **合计** | | **42+ 断言全绿** |

### E.3 真机端到端验证（临时端口 + 临时 DB 起真实 server 进程）

用裸 socket 客户端（urllib 对无 `Content-Length` 长连接会缓冲到 EOF，不可靠）开 `/api/stream`，同进程调 `proactive.push_proactive`：

- **A) `FEATURE_EVENTBUS=true`**：`push_proactive` → `bus.publish(TOPIC_SSE)` → `_handle_stream` 订阅回调 → 队列 → SSE 写出 → 客户端收到含 marker `E2E-A-bus-*` 的 `data:` 行。**PASS**。
- **B) `FEATURE_EVENTBUS=false`**：回退 `SUBSCRIBERS` 全局队列直发 → SSE 写出 → 客户端收到含 `E2E-B-fallback-*` 的 `data:` 行。**PASS**。
- **结论**：EventBus→SSE 全链路 + 旧路径回退均验证通过，**SSE 报文格式零改动**（前端零改动，§7 兼容）。

### E.4 实现相对方案的微调（透明记录）

1. **SSE 桥拓扑收敛**：方案 §四描述 `proactive→bus.publish("ProactivePush")`、`scene→bus.publish("SceneCard")`、`server 订阅 SseDispatch`。实现统一为单汇聚主题 `TOPIC_SSE="zz.sse"` + `publish_sse()` 便捷入口，server 仅 `subscribe` 一次。语义等价、更简洁，符合 §四"汇总到 SseDispatch"意图。
2. **人格默认 verbosity 0.5 → 0.4**：§五草案写 0.5；实现改为 **0.4**（<0.5 走"简洁"分支）。因 D4 要求默认等价现状（`SYSTEM_PROMPT` 强调"简洁"），且 0.5 精确等于阈值会误走"详尽"分支。已重测（见 E.2 2.3）。
3. **TOPIC 命名风格**：实现用 `zz.sse`（小写点分），与草案示例大写不同，仅命名统一，无语义差异。
4. **`weather._LAST` 迁移策略**：未删除旧模块全局（聊天流弹窗 `last_weather` 依赖），改为"旧行保留 + Flag ON 时 `world_state.refresh("weather")` 同步失效"，双写共存安全（见 `server.py` 1163–1179）。

### E.5 宪法符合性复核（实现落地后补证据）

| 宪法条款 | 实现证据 |
|---|---|
| §1.5 / §15 / §22.2 事件驱动、EventBus 唯一脊柱 | `proactive/scene/server` 经 `bus`；`enabled()` 门控，关闭即回 `SUBSCRIBERS`；无跨模块直发 |
| §1.9 / §24.3 禁 God Module（≤500 行） | 各新文件单行职责，最大 `world_state.py` < 500 行 |
| §1.10 禁循环依赖 | 依赖单向：context 适配器 → `world_state`/`personality` → `eventbus`；`eventbus` 不反向依赖任何业务模块 |
| §4 / §17 Context 由 Context Engine 生成 | 新 Source 经 `SourceRegistry` 注入，无模块手写 System Prompt |
| §6 世界模型 + §4.1 Context 来源 | `WorldStateSource` ↔ `ContextSource.WORLD`；全域 TTL 缓存 |
| §11 禁无 TTL 缓存 | WorldModel 按域 TTL；实测 `snapshot()` 走缓存 < 5ms |
| §7 / §1.6 向后兼容 | Flag 默认 ON 且等价现状；SSE 报文零改动；`weather._LAST` 安全迁移 |
| §1.7 增量演进 | 纯新增 + Flag 门控，可瞬切回退 |
| §15.5 禁不可序列化对象入总线 | `publish_sse`/`publish` 仅接受 `dict` payload，类型层约束 |

### E.6 风险与回退确认

- **三个 Flag 默认 ON**（`config.reload()` env 默认 `"true"`，模块导入即生效）。任一置 `false` 可瞬时/重启回退：
  - **EventBus SSE 路径**：`enabled()` 运行时实时读取 → **真正瞬时回退**（`FEATURE_EVENTBUS=false` 即切回 `SUBSCRIBERS`）。
  - **Context Source 注册**：在 `context/builder.py __init__` 导入时决定 → 回退需重启（与 P1 `FEATURE_*` 既有约定一致）。
- **双写安全**：`weather._LAST` 旧行与 `world_state.refresh` 共存，聊天流弹窗 `last_weather` 不受影响（已验证）。
- **采集失败降级**：WorldModel 任一采集器异常时降级到上一次快照/默认，不阻塞对话（§3.2 降级原则）。

---

## 十二、F 总结

### F.1 交付清单

**新增 5 文件**：
- `eventbus.py` — EventBus 基础设施（进程单例 `bus`、`TOPIC_SSE`、`enabled()`、`publish_sse()`）
- `world_state.py` — WorldSnapshot + 按域 TTL 缓存 + 采集器降级
- `personality.py` — PersonalityParams 五维 + `generate()` + `render_prompt()` + `publish_changed()`
- `context/world_source.py` — `WorldStateSource`
- `context/personality_source.py` — `PersonalitySource`

**修改 6 文件**：
- `config.py`（三 Flag 声明/`global`/env 默认/`ENV_KEYS`）
- `context/models.py`（枚举加 `PERSONALITY`）
- `context/builder.py`（Flag 门控注册两 Source）
- `proactive.py`（SSE 双路径 `_dispatch_sse`）
- `scene.py`（SSE 双路径）
- `server.py`（SSE 桥 `bus.subscribe/unsubscribe` + 天气缓存同步失效）

### F.2 验证结论

- **单元/隔离**：42+ 断言全绿（2.1a 9/9、2.1b、2.2 16/16、2.3 17/17）。
- **真机端到端**：A（EventBus→SSE）PASS、B（SUBSCRIBERS 回退→SSE）PASS，SSE 报文格式零改动。
- **宪法**：§1.5/§15/§22.2/§6/§11/§7/§1.7/§1.10/§15.5 等全部符合（见 E.5）。
- **性能**：World `snapshot()` 走缓存 < 5ms；EventBus `publish` 非阻塞；Context 装配 < 2s（§26 达标）。

### F.3 后续事项（非阻塞）

1. **重启 8000 后端**（系统 Py3.11）让 Phase 2 生效——旧进程不热加载，须 kill 旧 PID 后重拉（netstat 定位 → taskkill /F → 后台重拉）。
2. **前端 🧠 画像面板实测（需用户配合）**：浏览器 `Ctrl+F5` 清缓存后，点左侧 rail「🧠 画像」chip，确认侧栏弹出并渲染。无头环境无法自动点按，待老板实测反馈。
3. **真实环境 >40 轮对话观察自动抽取**：属 P1 环节，已在先前验证，非阻塞。

### F.4 当前状态

- Phase 2 全部子轮（2.1/2.2/2.3）实现 + E 自审完成，**待 git 提交**。
- 三个 Feature Flag 默认 ON，等价现状，可瞬时/重启回退。
- 目录偏差（根目录扁平 vs 宪法目标 `cognitive/`）为已知、可控偏差（见 §八.1），留待"Server 模块化/目录规范化"统一归位。

> 本设计为 B 设计稿，未经 C 批准不进代码。
