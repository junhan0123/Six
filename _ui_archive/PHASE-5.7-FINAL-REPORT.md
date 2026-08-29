# PHASE 5.7 — CAPABILITY ENTRY SURFACE UNIFICATION · FINAL REPORT

> 项目：小6 Xiao6 v1.4.0
> 阶段：PHASE 5.7（收口，READ-ONLY 调查 + 纪律化最小改动）
> 日期：2026-08-19
> 执行纪律：VERIFY-BEFORE-CHANGE / MINIMAL-DIFF / ZERO-SCOPE-CREEP / server.py ZERO WRITE
> 基线（冻结）：TOOLS=62 · TOOL_FUNCS=62 · READONLY_TOOLS=28 · CANONICAL_CAPABILITIES=33 · LEGACY_CAPABILITIES=3 · FEATURE_REGISTRY=47 · Runtime Port=8010

---

## 1. VERDICT — ✅ PASS / 无需任何代码改动

PHASE 5.7 的既定目标（消除命令坞 `feat:capabilities` → `/api/capabilities` → legacy 3 项的用户入口不一致）**经实证为伪问题**。用户可见的 Capability 入口已于 PHASE 5.6 全部统一到 canonical 33，**本阶段零代码改动**，仅做调查、回归与归档。

---

## 2. PHASE OBJECTIVE（回顾）

- 消除最后一个疑似入口不一致：命令坞 `feat:capabilities` → `/api/capabilities` → 3 项 legacy。
- 要求：所有用户可见的 Capability 入口都进入 canonical 33。
- 红线（禁止改动）：`tools.py` / `capabilities.py` / `registry.py` / `__init__.py` / `agent_runtime.py` / `config.py` / `policy` / `execution` / `electron` / `server.py` / `ports`。

---

## 3. PREMISE RE-EXAMINATION（VERIFY-BEFORE-CHANGE 的价值）

任务书假定 `feat:capabilities` 是 `/api/capabilities` 的活跃消费者。在动任何代码之前，本阶段先静态核验该命令是否真实存在——**结论：不存在。**

证据链：
- `FEATURE_REGISTRY`（zz-workspace.js:632-680）中 `capabilities` 定义为 `{ id: 'capabilities', name: '能力目录', cat: 'A', vis: 'default' }`（L644）。
- 命令坞派生循环（L711-716）：
  ```js
  FEATURE_REGISTRY.forEach(function (f) {
    if (f.vis === 'advanced' || f.vis === 'conditional') {   // ← 仅 advanced / conditional
      COMMANDS.push({ id: 'feat:' + f.id, ... run: function () { openFeature(f.id); } });
    }
  });
  ```
- `capabilities` 的 `vis` 为 `'default'`，**不满足 `advanced || conditional` 条件 → `feat:capabilities` 命令从未被生成**。

→ 任务书的前提（"feat:capabilities 活跃消费 /api/capabilities"）不成立。这正是 VERIFY-BEFORE-CHANGE 纪律避免"无谓改动"的核心价值。

---

## 4. ROOT CAUSE（入口不一致的真正源头）

真正的"不一致"并非运行时消费，而是**一处死代码路径**：

- `featureRoute(id)`（L732-734）对未映射 id 回退到 `/api/<id>`：
  ```js
  function featureRoute(id) {
    if (FEATURE_API_MAP[id]) return FEATURE_API_MAP[id];
    return '/api/' + String(id || '').replace(/-/g, '/');   // ← 'capabilities' 会回退到 /api/capabilities
  }
  ```
- 但 `featureRoute` 只被 `openFeature(id)`（L736）调用，而 `openFeature` 只被 `feat:f.id` 命令（L714）触发。
- 由于 `feat:capabilities` 不存在，`openFeature('capabilities')` 在活跃用户入口中**永远不会被调用** → `/api/capabilities` 回退分支是**死代码**，不构成真实入口。

换言之：用户真正能触达的 Capability 入口，没有任何一条会打到 deprecated `/api/capabilities`。

---

## 5. COMMAND DOCK ENTRY SURFACE ANALYSIS（全量枚举）

命令坞中与 Capability 相关的全部入口（L696-710 手写 + L711-716 派生）：

| 命令 id | 触发动作 | 数据来源 | 渲染项数 |
|---|---|---|---|
| `capabilities`（L701，手写） | `switchView('capabilities')` | `snap.capabilities`（L86/L94 已置为 catalog） | **33（canonical）** |
| `knowledge`（L709，手写） | `switchView('capabilities')` | 同上 | **33（canonical）** |
| `feat:<advanced/conditional>`（L714） | `openFeature(f.id)` | `FEATURE_API_MAP` 或回退 | 不涉及 capabilities |

- `switchView('capabilities')` 渲染的是 `snap.capabilities`，其在启动加载（L86）即 `getJSON('/api/capability_os/catalog')`，经 L94 解析器展平为 **33 项 canonical 能力**（已含 `label`/`active` 别名映射）。
- 没有任何用户可见入口调用 `openFeature('capabilities')`。

**→ 所有用户可见 Capability 入口 = canonical 33，已统一。**

---

## 6. ACTIVE DEPRECATED CONSUMERS = 0

静态 + 实时双重证明 `zz-workspace.js` 对 `/api/capabilities` 的**活跃消费 = 0**：

- 全仓扫描 `zz-workspace.js`：唯一匹配 `/api/capabilities` 的位置是 **L94 的注释**（记录 5.6 切换历史），代码中**零活跃调用**。
- 实时验证：8010 server 存活，`/api/capability_os/catalog` 返回 200、`total=33`、`flattened=33`；deprecated `/api/capabilities` 虽仍存活（返回 `deprecated:true` 的 3 项 legacy），但 **GUI 侧无引用路径到达它**。

---

## 7. DEPRECATED ENDPOINT STATUS（按设计保留，不在本阶段范围）

- `server.py:471-484` 定义 `/api/capabilities`，响应体带 `deprecated:true` 与 RFC8597 `Deprecation: true` 头，返回 legacy 3 项。
- 该端点是**向后兼容垫片**，按设计保留；本阶段红线明确禁止改动 `server.py`（ZERO WRITE）。
- 其存在不影响 GUI 一致性（无消费者），属于"设计内遗留"，建议在未来 deprecation 收口阶段（非 5.7）评估下线。

---

## 8. P2 — `capability_foundation` VIEW 无消费者（RECORD-ONLY）

- `capability_os/__init__.py` 的 `foundation_view()` 提供比 `catalog_view()` 更丰富的导出（含 executor、verification health、MCP 元信息）。
- 全仓扫描确认：**当前无任何 GUI/前端模块消费 `/api/capability_foundation`**。
- 处置：**RECORD-ONLY**。不扩大范围接入；建议未来在"能力详情"面板可选接入 foundation 视图以增强可观测性（属 5.8+ 范畴，待授权）。

---

## 9. P3 — `execution_mapping.py` 陈旧注释（RECORD-ONLY）

- `capability_os/execution_mapping.py:88-89` 注释称 `focus_window` / `browser_navigate`"声明 MEDIUM，但不在 computer_action 白名单"。
- 但实测 `computer_action/safety.py:34-35` 的 `WHITELIST` **已包含** `focus_window` 与 `browser_navigate`。
- → 该注释与真实白名单**矛盾**，属陈旧错误注释；但本阶段红线禁止改动 `execution` 相关文件。
- 处置：**RECORD-ONLY**。记录待修项，建议未来清理注释（不改动行为）。

---

## 10. SCOPE RED LINES COMPLIANCE（红线全程遵守）

| 禁止改动文件 | 本阶段实际状态 |
|---|---|
| `tools.py` | 未触碰 |
| `capabilities.py` | 未触碰 |
| `registry.py` | 未触碰 |
| `capability_os/__init__.py` | 未触碰 |
| `agent_runtime.py` | 未触碰 |
| `config.py` | 未触碰 |
| `policy/` | 未触碰 |
| `execution/` | 未触碰 |
| `electron/` | 未触碰 |
| `server.py` | **ZERO WRITE**（端点保留） |
| `ports` | 未触碰 |

→ **11 个关键文件字节级不变，零越界。**

---

## 11. REGRESSION（实时回归，全部通过）

基于仍在运行的 8010 runtime（PHASE 5.6 遗留）：

| 检查项 | 结果 |
|---|---|
| `/api/capability_os/catalog` 可访问性 | HTTP 200 ✅ |
| `catalog.total` | 33 ✅ |
| `groups` 数 | 10 ✅ |
| 展平后 capabilities 数 | **33** ✅ |
| deprecated `/api/capabilities` 隔离（无 GUI 消费者） | ✅ |
| PHASE 5.6 CRITICAL 闸门（delete/system/network）仍 blocked | 沿用 5.6 验证 ✅ |
| `snap.capabilities.length`（GUI 侧） | 33（canonical）✅ |

---

## 12. SHA256 AUDIT（字节级不变）

| 文件 | SHA256 | 状态 |
|---|---|---|
| `xiao6-ui/xiao6-space/js/zz-workspace.js` | `76e55100b1a67d7f5974ace55631058e9c79b6a649db85a4a51a34d0b7e862a9` | 与 5.6 收口一致 ✅ |
| `tools.py` | `bb5ee850…`（继承自 5.6） | 未变 ✅ |
| `capabilities.py` | `2bdb7e6e…`（继承自 5.6） | 未变 ✅ |
| 其余 8 个关键文件 | — | 字节级不变 ✅ |

→ **本阶段零文件发生任何字节变化。**

---

## 13. FILES CHANGED

**NONE（零改动）。**

本阶段仅产出本报告（归档于 `G:\xiao6\_ui_archive\PHASE-5.7-FINAL-REPORT.md`），未对任何源码/配置/后端文件执行写操作。

---

## 14. CONCLUSION & STOP

- **PHASE 5.7 结论**：命令坞不存在 `feat:capabilities` 入口（其 `vis:'default'` 不满足派生条件），故"命令坞 → /api/capabilities → 3 项"的入口不一致**从未真实存在**。所有用户可见 Capability 入口已于 PHASE 5.6 统一到 canonical 33，本阶段**无需改动任何代码**。
- **P2 / P3** 均为 RECORD-ONLY 记录项，不扩大范围。
- **红线**：全程遵守，11 关键文件字节级不变，`server.py` ZERO WRITE。
- **Verdict**：✅ PASS。

> ⛔ **STOP** — 按任务纪律，PHASE 5.7 已完成并收口，**不自动进入 PHASE 5.8**。
> 如需推进 5.8（建议方向：P2 接入 foundation 视图 / P3 清理陈旧注释 / deprecated 端点收口评估），请明确授权后另开阶段。

---

_归档位置：`G:\xiao6\_ui_archive\PHASE-5.7-FINAL-REPORT.md`_
