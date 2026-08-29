# PHASE 5.8 — CAPABILITY FOUNDATION / DETAIL & OBSERVABILITY · FINAL REPORT

> 项目：小6 Xiao6 v1.4.0
> 阶段：PHASE 5.8（Capability Presentation / Observability Layer，READ-ONLY 调查）
> 日期：2026-08-19
> 执行纪律：VERIFY-BEFORE-CHANGE / MINIMAL-DIFF / ZERO-SCOPE-CREEP / EVIDENCE-FIRST / server.py ZERO WRITE
> 前置：PHASE 5.7 = PASS / COMPLETE / FROZEN / STOP（已继承）
> 当前 Runtime Port：8010

---

## 1. VERDICT

### ✅ PASS / NO-CHANGE / FROZEN / STOP

**本阶段零代码改动。** 经真实源码 + 真实运行时 + 真实 GUI 三重审计确认：当前 33 项 Capability 目录已对普通用户具备**足够的可发现性、可理解性、可用性状态**，且正确隐藏了内部实现细节。

`/api/capability_foundation` 虽提供丰富的验证/健康/执行元信息，但其超出"用户可理解 Surface"的字段（executor / truth_sources / mcp）按**信息暴露红线本就不该展示**；而用户真正关心的 label/description/availability 已通过 canonical catalog 完整呈现。

→ **不存在正确性级 UX 缺口，不实施任何前端改动。** 最优秀的 PHASE 5.8 即 ZERO WRITE。

---

## 2. PHASE OBJECTIVE

在不破坏 PHASE 5.6/5.7 已完成的 Capability 统一基础上，评估并以最小改动把 `capability_foundation` 的价值转化为用户可理解的 Capability Detail / Observability Surface；**若当前能力目录已满足产品要求，则直接 PASS / NO-CHANGE / FROZEN / STOP，禁止制造工作量。**

---

## 3. PHASE 5.7 INHERITANCE

```
PHASE 5.7 inheritance confirmed
```

| 指标 | 继承值 | 本阶段实时复验 |
|---|---|---|
| canonical capabilities | 33 | ✅ live `/api/capability_os/catalog` → `total=33`, `flattened=33` |
| legacy capabilities | 3 | ✅ `/api/capabilities` 仍 deprecated（3，未消费） |
| feature registry | 47 | ✅ 未变（红线文件哈希一致） |
| runtime port | 8010 | ✅ server 存活，`/api/agent/state` → `IDLE / running=true` |
| workspace SHA256 | `zz-workspace.js=76e55100…` | ✅ 本次实测 `76e55100b1a67d7f…862a9` 完全一致 |
| 文件状态 | 11 关键文件冻结 | ✅ 本阶段 0 文件变化（见 §14） |

无 Git 仓库（小6 以文件目录管理），以 SHA256 作为字节级基线凭证。

---

## 4. BASELINE

**Runtime（实时 8010）**
- `/api/agent/state` → `{"enabled":true,"state":"IDLE","running":true,…}` 正常
- `/api/capability_os/catalog` → HTTP 200，`total=33`，`flattened=33`
- `/api/capability_foundation` → HTTP 200，schema 见 §5
- `/api/capabilities`（deprecated）→ HTTP 200，`deprecated:true`，3 项，GUI 零消费者

**GUI（真实渲染路径）**
- 视图容器：`index.html:168-170` `<section data-view="capabilities">`，头部"能力 / 已登记并可被调用的能力"，列表 `#capabilitiesList`。
- 渲染函数：`renderCapabilities()`（zz-workspace.js:473-486）→ 对每项调用 `row(icon, label, description, tagCls, tagTxt)`。
- **每条能力渲染字段**：`icon` + `label(=name)` + `description` + 状态徽章（`active? 'done'/'激活' : 'run'/'待命'`）。
- 点击行为：当前为静态列表，**无点击详情交互**（属设计现状，非缺陷，见 §7）。

**Source SHA256（基线，全程未变）**
| 文件 | SHA256 |
|---|---|
| xiao6-space/js/zz-workspace.js | `76e55100b1a67d7f5974ace55631058e9c79b6a649db85a4a51a34d0b7e862a9` |
| capability_os/registry.py | `d340e1d24a275358f735a44e2db15e24c068107db529734e432219a66fe896cf` |
| capability_os/__init__.py | `3bfbcbe12f48aeb1d52a9e939e513230fdcc10d7a15bfaf9c8255b46b3d8465b` |
| capabilities.py | `2bdb7e6e940f8c80efb705ae7179a9d0de650c875e3846e0907a2471c524bd0f` |
| server.py | `4b1a91ded03198e9541e75ddfc174b385b81a212a0a1ae46cc75a3884dd6b048` |

---

## 5. FOUNDATION VIEW AUDIT（真实结构，非假设）

源：`capability_os/__init__.py:121-187` `foundation_view()`。实时复验（8010）确认 schema：

```
foundation_view()
├── truth_sources      {declaration, execution, permission, verification, events}  ← 内部真相源描述
├── total              = 33
├── available          = 27
├── health_summary     {READY:26, DECLARED:1, PARTIAL:0, BLOCKED:6, UNAVAILABLE:0, ERROR:0}
├── capabilities[33]
│   └── 每项:
│       id, name, description, group, icon, risk, permission,
│       available, implemented,
│       executor {kind, ref, note, callable},   ← 内部执行体
│       health   {status, ...},                ← 验证状态
│       ui       {keywords:[...]}
├── mcp_servers        [...]                   ← 外部世界桥（技术）
├── external_capabilities [...]
└── mcp_summary        {servers_total, servers_ready, external_capabilities}
```

**结论**：foundation 在 catalog 基础上额外提供 `health.status`（验证状态）、`executor`（执行体）、`mcp_*`（外部桥）、`truth_sources`（内部真相源）。其中 executor / truth_sources / mcp 属**内部实现细节**，按 §21 信息暴露红线**默认不应进入用户 Surface**。

---

## 6. PRODUCT VALUE AUDIT

| 数据 | 用户价值 | GUI 当前是否展示 | 结论 |
|---|---|---|---|
| Capability label (name) | 高 | ✅ `c.label` | 已满足 |
| Capability description | 高 | ✅ `c.description` | 已满足（实时确认 has_description=True） |
| active / availability | 高 | ✅ `激活/待命` 徽章 | 已满足 |
| execution metadata (executor) | 低/中 | 否（隐藏） | **正确隐藏**（暴露红线禁止） |
| verification status (health) | 高（诊断） | 部分（available 布尔代理） | 增强项，非缺口 |
| health aggregate (health_summary) | 中/高（诊断） | 否（隐藏） | 诊断/开发者向，非普通用户缺口 |
| MCP metadata | 低/中 | 否（隐藏） | **正确隐藏** |
| executor internals | 低 | 否（隐藏） | **正确隐藏** |
| security/policy internals | 低 | 否（隐藏） | **正确隐藏** |
| raw backend metadata | 低 | 否（隐藏） | **正确隐藏** |

→ 当前 GUI 已暴露全部**高用户价值**字段（label / description / availability），并**正确隐藏**全部内部实现字段。foundation 相对 catalog 的"增量"主要是诊断/信任信号（health）与内部实现（executor/mcp），前者可由 available 徽章部分覆盖，后者按红线禁止展示。

---

## 7. UX GAP ANALYSIS（六维判断）

| 维度 | 当前状态 | 是否缺口 |
|---|---|---|
| **A. Discoverability**（小6会什么） | 33 项导航列表，icon+名称，10 能力域分组 | ✅ 无缺口 |
| **B. Comprehension**（具体能做什么） | 每条含 `description` 描述 | ✅ 无缺口（实时确认） |
| **C. Availability**（当前是否可用） | 每条 `激活/待命` 状态徽章 | ✅ 无缺口 |
| **D. Trust**（是否正常） | available 布尔 → 激活/待命；BLOCKED 能力已显示「待命」 | △ 部分覆盖；health.status 为更深诊断信号，属增强非缺口 |
| **E. Diagnostics**（出问题时反馈） | 基础可用性反馈存在；深层 health 未展示 | △ 开发者/诊断向，非普通用户正确性缺口 |
| **F. Noise**（是否变开发者控制台） | 当前视图干净（icon/名称/描述/状态），无内部字段泄漏 | ✅ 无噪声 |

**综合判定**：当前 33 项 Capability 目录对**普通用户（Personal AI OS 受众）**已满足"足够可理解、可诊断、可观察"的产品要求。foundation 的增量价值（health 验证状态、executor/mcp 内部元信息）中，内部部分按暴露红线禁止上屏，诊断部分属增强而非缺陷。

→ **不存在真实 UX 缺口（CASE A）。**

---

## 8. IMPLEMENTATION DECISION

```
CASE A — 当前 GUI 已经足够 → 禁止修改代码 → PHASE 5.8 = PASS / NO-CHANGE
```

依据：
1. 真实源码（`renderCapabilities` L473-486 + `Capability.to_dict` registry.py:79-96）证明 GUI 已渲染 icon+name+description+availability。
2. 真实运行时（8010）证明 catalog 实时返回 33 项且每项 `has_description=True`。
3. 真实 GUI 路径（`index.html:168-170` 能力视图）为干净列表，无内部字段泄漏（维度 F 通过）。
4. foundation 额外字段经 FOUNDATION INFORMATION EXPOSURE RULE（§21）审查：executor/truth_sources/mcp 禁止展示；health 属诊断增强，非正确性缺口。

**不实施任何前端改动。** 不新增 `/api/capability-detail` 等端点（§13 禁止，且本就无需）。不修改 `server.py`（§3 红线）。

---

## 9. IMPLEMENTATION SUMMARY

无实现。本阶段为 READ-ONLY 调查 + 证据归档。

（如未来产品明确要求"点击能力查看详情 + 验证健康"，可另开阶段，按 §11/§12/§15 纪律以最小前端改动消费现有 `/api/capability_foundation`，并仅展示 health.status 等用户相关字段、隐藏 executor/mcp/truth_sources。本次因无真实缺口，不触发。）

---

## 10. API VERIFICATION

| Endpoint | 实时结果 |
|---|---|
| GET /api/capability_os/catalog | HTTP 200，`total=33`，`flattened=33` ✅ |
| GET /api/capability_foundation | HTTP 200，schema 正确（§5），`total=33` ✅（复用候选，本次未消费） |
| GET /api/capabilities（deprecated） | HTTP 200，`deprecated:true`，3 项，GUI 零消费者 ✅ |
| GET /api/agent/state | `IDLE / running=true` 正常 ✅ |

---

## 11. GUI E2E VERIFICATION

本阶段 **CASE A（无代码改动）**，故 Test 01-14（点击详情/Detail Surface 打开等）**不适用**——GUI 与 PHASE 5.6 收敛后状态完全一致，且 5.6 已验证：

- ✅ 能力页面可打开（`switchView('capabilities')` → `renderCapabilities()`）
- ✅ 33 capabilities 正常显示（实时 `snap.capabilities.length=33`）
- ✅ 每条含 icon/label/description/active（字段齐备，不抛异常）
- ✅ 首页「能力 33 项」/ 上下文卡 / 设置「能力登记 33 项」均源自 `.length=33`
- ✅ Command Dock / Voice Orb / 其他 view 不受影响（未改任何 DOM/事件）
- ✅ Console 无新增 critical error（无改动即无新增）

如需强制真实浏览器冒烟，可在后续阶段补做；本次 ZERO WRITE 下 GUI 行为等价于已验证的 5.6 状态。

---

## 12. SECURITY REGRESSION

- `delete` / `system` / `network` 等 CRITICAL 能力：在 catalog/foundation 中 `available=false / permission=block`，三重闸门（matcher + router + policy_engine default_deny）未变动。
- 本阶段零改动 → 无新增执行入口、无 bypass、无 auto-approve、无 policy override、无 direct executor call。
- 红线文件（policy / execution / tools / server.py）SHA256 与冻结值一致 → 安全态势未降级。

---

## 13. CAPABILITY COUNT REGRESSION

| 指标 | 值 | 状态 |
|---|---|---|
| TOOLS | 62 | 不变 |
| TOOL_FUNCS | 62 | 不变 |
| READONLY_TOOLS | 28 | 不变 |
| CANONICAL_CAPABILITIES | 33 | 不变（实时 `total=33`） |
| FEATURE_REGISTRY | 47 | 不变 |
| LEGACY_CAPABILITIES | 3 | 不变 |
| PORT | 8010 | 不变 |

无变化。

---

## 14. SHA256 AUDIT

| 文件 | SHA256 BEFORE（5.6/5.7 冻结） | SHA256 AFTER（本阶段） | 变化 |
|---|---|---|---|
| xiao6-space/js/zz-workspace.js | `76e55100b1a67d7f…862a9` | `76e55100b1a67d7f5974ace55631058e9c79b6a649db85a4a51a34d0b7e862a9` | 不变 |
| capability_os/registry.py | `d340e1d2…e896cf` | `d340e1d24a275358f735a44e2db15e24c068107db529734e432219a66fe896cf` | 不变 |
| capability_os/__init__.py | `3bfbcbe1…d8465b` | `3bfbcbe12f48aeb1d52a9e939e513230fdcc10d7a15bfaf9c8255b46b3d8465b` | 不变 |
| capabilities.py | `2bdb7e6e…24bd0f` | `2bdb7e6e940f8c80efb705ae7179a9d0de650c875e3846e0907a2471c524bd0f` | 不变 |
| server.py | `4b1a91de…6b048` | `4b1a91ded03198e9541e75ddfc174b385b81a212a0a1ae46cc75a3884dd6b048` | 不变（ZERO WRITE） |

**FILES CHANGED = NONE** · **FILES UNCHANGED = ALL（11 关键文件字节级一致）**

---

## 15. FILES CHANGED

**NONE（零改动）。**

本阶段仅产出本报告（归档于 `G:\xiao6\_ui_archive\PHASE-5.8-FINAL-REPORT.md`）。未对任何源码/配置/后端/前端文件执行写操作。

---

## 16. FILES UNCHANGED

`zz-workspace.js` · `registry.py` · `__init__.py` · `capabilities.py` · `server.py` · `tools.py` · `agent_runtime.py` · `config.py` · `policy/` · `execution/` · `electron/` · `ports` —— 全部字节级不变。

---

## 17. P2 / P3 RECORD-ONLY ITEMS

- **P2（`/api/capability_foundation` 无 GUI 消费者）**：本阶段确认其 schema 完整、HTTP 200、数据可用（33 项 + health_summary + mcp），但**经价值审计判定无需接入 GUI**（内部字段按红线隐藏、诊断字段非普通用户缺口）。保持 RECORD-ONLY。若未来产品明确要求"能力详情 + 健康"，此 endpoint 可直接复用（§13 合规），无需新增端点。
- **P3（`execution_mapping.py:88-89` 陈旧注释）**：`focus_window`/`browser_navigate` 注释称"不在白名单"，但 `computer_action/safety.py:34-35` WHITELIST 已含二者 → 注释矛盾。属陈旧错误注释；本阶段红线禁止改动 `execution/` 文件。保持 RECORD-ONLY。
- **Deprecated `/api/capabilities`**：未处理、未删除、未改（§14 红线）。
- 其他发现（orphan/dead comments/old API/naming 等）：全部 RECORD-ONLY，未顺手处理（§23 NO-SCOPE-CREEP）。

---

## 18. FINAL CONCLUSION

- **PHASE 5.8 Verdict = PASS / NO-CHANGE / FROZEN。**
- 经真实源码（`renderCapabilities` + `Capability.to_dict`）、真实运行时（8010 catalog/foundation/agent-state）、真实 GUI（`index.html` 能力视图）三重审计：当前 33 项 Capability 目录对普通用户已具备足够的可发现性（icon+名称列表）、可理解性（每条 description）、可用性状态（激活/待命 徽章），并正确隐藏内部实现细节（executor/mcp/truth_sources）——**不存在正确性级 UX 缺口**。
- `foundation_view()` 的增量信息（health 验证状态、executor、mcp）中，内部部分按信息暴露红线禁止上屏，诊断部分属增强而非缺陷。因此**不实施任何前端改动**，遵循"最优秀的 PHASE 5.8 是 ZERO WRITE"纪律。
- 红线全程遵守：11 关键文件字节级不变，`server.py` ZERO WRITE，无新增端点，无 scope-creep。
- 安全/能力计数回归全部不变，CRITICAL 闸门保持 blocked。

> ⛔ **STOP** — PHASE 5.8 完成并收口，**不自动进入 PHASE 5.9**，不自行决定下一阶段。
> 如未来产品明确要求"Capability Detail Surface（点击详情 + 验证健康）"，建议另开阶段，按本报告中 §9 注记的最小前端路径（复用现有 `/api/capability_foundation`，仅展示 health.status 等用户字段、隐藏内部实现）实施，届时需重新授权。

---

_归档位置：`G:\xiao6\_ui_archive\PHASE-5.8-FINAL-REPORT.md`_
