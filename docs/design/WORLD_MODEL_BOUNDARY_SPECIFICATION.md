# World Model Boundary Specification — Xiao6 v1.4

> World Model 边界规范 | Project Intelligence System v1.4 · Phase 4
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；不修改 World Model 实现、不引入持久知识、不触碰 GOLDEN_STATE。

---

## 1. 目的与定位

ARCHITECTURE_MAP 定义 **Computer World Model** 为「当前世界态势」——由 Perception 层（Capture / UIA / OCR / Vision / Fusion）生产，经 EventBus 写 AppState，投影为 PerceptionState / World Model。其本质是**观察态、动态、易变**。

但 v1.4 Phase 1 §3.3 揭示：**World Model 与 Knowledge 的「稳定/动态」界限未显式**。本 Phase 固化 World Model 的：

1. **负责什么**（环境/设备/位置/时间/资源/外部态）。
2. **不负责什么**（禁长期知识污染、禁用户长期记忆、禁 Goal）。
3. **观察态 → 稳定知识的升级纪律**（何时可经治理成为 Knowledge KU）。

> World Model 边界是认知层纪律，不改变 Perception/World Model 实现。

---

## 2. World Model 负责域（Allowed）

| 维度 | 内容 | 载体 | 性质 |
|------|------|------|------|
| **环境** | 屏幕内容、前台应用、音频/光照/温湿度传感器 | PerceptionState / worldaware_cache.json | 观察态 |
| **设备** | 本机状态、外接设备、网络连通性 | PerceptionState | 观察态 |
| **位置** | 设备/用户当前物理位置（瞬时） | PerceptionState | 观察态（注：用户**常住地**是 User Fact，归 Memory） |
| **时间** | 当前时刻、时区、日程触发点 | 系统时钟 / 上下文 | 观察态（注：用户**时区偏好**是 User Preference，归 Memory） |
| **资源** | CPU/内存/磁盘占用、电量、进程 | PerceptionState | 观察态 |
| **外部态** | GDELT 热点、USGS 地震、OpenSky 航班、Open-Meteo 天气 | 外部数据源缓存 | 观察态（外部拉取） |

> 共同特征：**实时、易变、由感知生产、经事件流动、投影为只读态**。World Model 不「拥有」这些信息为长期知识。

---

## 3. World Model 禁存域（Forbidden）— 硬约束

| # | 禁存类别 | 理由 | 正确归属 |
|---|----------|------|----------|
| 1 | **项目稳定知识**（架构/红线/事件数/决策） | 属 Knowledge，World Model 是动态态势，不承载稳定事实 | Knowledge（KU L100–L30） |
| 2 | **用户长期事实/偏好**（常住地/语言偏好/习惯） | 属 User Model（Memory），是稳定用户态，非瞬时感知 | Memory（profile） |
| 3 | **当前 Goal / 任务进度** | 属 Goal System 任务态 | Goal System |
| 4 | **已完成经验/洞察** | 属 Memory learnings / 经治理 Knowledge | Memory / Knowledge |
| 5 | **长期「世界规律」冒充实时态** | 如「台北位于地震带」是稳定事实，非此刻地震事件；前者须升级为 Knowledge | Knowledge（经治理） |

> 红线 #1/#2 是最高频误用：把「屏幕显示 X」与「项目事实 X」混为一谈。World Model 只答「**此刻**是什么」，Knowledge 答「**一直**是什么」。

---

## 4. 观察态 → 稳定知识的升级纪律

World Model 的某些观察**可能**值得成为长期知识，但**禁止静默冻结**。升级路径：

```
World Model 观察（实时态）
  ↓ 是否稳定、可复用、跨会话有意义？
  ├─ 否 → 留在 World Model（观察态缓存，可过期）
  └─ 是 → 走 Knowledge 治理（v1.3 Phase 10 六步）：
            Create(12 Metadata + Payload) → Review → Classify
            → Assign Authority(按 source) → Link Relations → Freeze
            ↓
         成为 Knowledge KU（带 source/authority），脱离 World Model 易失态
```

- **绝不**把 World Model 缓存直接当作 Knowledge 消费（防低权威冒充，呼应 v1.3 Phase 10 红线 #5）。
- **source 必须登记**（v1.3 Phase 3 §3.3）：观察升级为 KU 时，`source` 指向权威文档（如 Phase8 感知规范 / GOLDEN_STATE），不得无 source。
- 外部态（天气/地震）**默认不升级**为 Knowledge——除非形成「项目级稳定规则」（如「热点 3D 地球标记须用 THREE.RingGeometry 正圆环」源自 Phase8 规范，属 Knowledge L90）。

---

## 5. 与相邻系统的硬边界

### 5.1 World Model vs Knowledge（核心边界）
- **World Model**：动态态势（此刻屏幕/天气/设备）。
- **Knowledge**：稳定事实（事件=71 / 红线 / 决策）。
- **边界**：知识不消费实时感知（v1.3 Phase 9 §3.2）；World Model 观察态不持久化为知识（§4）。

### 5.2 World Model vs Memory（User Model）
- **World Model**：瞬时位置/时区/环境。
- **Memory**：用户常住地/时区偏好/习惯（稳定）。
- **边界**：瞬时观察≠长期用户态；升级需去实时性后归 User Fact（Memory）。

### 5.3 World Model vs Goal System
- **World Model**：执行环境态势（「屏幕当前状态」）。
- **Goal System**：任务目标与进度。
- **边界**：Goal 执行可**读取** World Model（Verification 复用 Perception 快照），但不将 Goal 存入 World Model。

### 5.4 World Model vs Event System
- World Model 由 Perception Runtime **经 EventBus 生产**（`PERCEPTION_*` / `COMPUTER_WORLD_SYNC` 事件）。
- World Model 自身**不发射**领域事件；它是事件的**消费者/投影结果**。

### 5.5 World Model vs Context Engine
- World Model 是 Context Engine 的**三并列输入源之一**（与 Memory / Knowledge）；Context Engine 读 World Model 投影，不写。

---

## 6. 与 GOLDEN_STATE / 现有基线的兼容性

- ✅ World Model 观察态由 Perception 生产、经 EventBus、投影只读——与 ARCHITECTURE_MAP、DECISION_001/002 一致。
- ✅ 不引入第二存储；观察缓存（worldaware_cache.json）非「知识库」，不替代 Knowledge。
- ✅ 与 v1.3 Phase 9 §3.2（知识不消费实时感知）完全一致。
- ✅ 不触碰 GOLDEN_STATE 红线、Vision 不 Control 纪律。

---

## 7. 设计纪律确认

✅ 仅固化 World Model 边界规范，未改代码/World Model 实现。
✅ 明确 6 维负责域 + 5 类禁存域。
✅ 建立「观察态 → 稳定知识」升级纪律，防静默冻结。
✅ 与 Knowledge / Memory / Goal / Event / Context Engine 硬边界固化。
✅ 不触碰 GOLDEN_STATE 红线、不引入第二存储。

> Phase 4 完成。下一步：Phase 5 定义 Knowledge System Boundary Specification（任务 #209）。
