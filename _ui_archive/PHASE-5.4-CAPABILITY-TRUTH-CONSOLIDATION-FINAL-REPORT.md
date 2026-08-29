# PHASE 5.4 — CAPABILITY TRUTH CONSOLIDATION · FINAL REPORT

> 小6 Xiao6 v1.4.0 · 能力真相源收口 / 遗留兼容层退化 (LEGACY COMPAT SHIM + DEPRECATE LEGACY API)  
> 生成时间：2026-08-18 · 模式：AUTONOMOUS / VERIFY-BEFORE-CHANGE / EVIDENCE-FIRST / MINIMAL-DIFF  
> 裁决：**COMPLETE / PASS**



---

## 1. 执行摘要 (Executive Summary)

PHASE 5.4 将唯一的「冗余能力真相源」`capabilities.py` 从 LEGACY CAPABILITY SOURCE 收敛为  
**LEGACY COMPATIBILITY SHIM**（仅保留上下文注入逻辑 + 显式 shim 标记 + 转发适配器），并将  
遗留端点 `GET /api/capabilities` 以 `deprecated:true` 方式标记（含 RFC8597 `Deprecation` 头），  
GUI 兼容零破坏。

证据充分、全部回归通过：

- 真实 live import 验证 `capability_details()` 仍返回 3 项（hotspot/prefetch/computer_action）；
- 真实 live import 验证 canonical 注册表 `len = 33`，且 3 项上下文能力仍被合并进 canonical；
- CRITICAL 占位（delete/system/network）保持 `available=False + permission=block`；
- 7 个 in-scope 文件 SHA256 比对：**仅 capabilities.py 与 server.py 变化**，5 个红线/保护文件字节级不变。

---

## 2. 任务范围与目标 (Scope & Objective)

**唯一目标（两项）**：

1. 将 `capabilities.py` 从「LEGACY CAPABILITY SOURCE」退化为「LEGACY COMPATIBILITY SHIM」——  
   转发到 canonical `capability_os.registry`，**不新建第二真相源**。
2. **DEPRECATE（非删除）** `GET /api/capabilities`，以 `deprecated:true` 标记，GUI 兼容不破坏。

**非目标**：不触碰 tools.py / registry.py（默认）/ **init**.py / zz-workspace.js / agent_runtime.py /  
electron/main.js / config.py / policy / ports / chat.html。

---

## 3. 冻结事实基线 (Frozen Facts Baseline)

| 维度                                 | 值                                                                             |
| ---------------------------------- | ----------------------------------------------------------------------------- |
| TOOLS                              | 62                                                                            |
| TOOL_FUNCS                         | 62                                                                            |
| READONLY_TOOLS                     | 28                                                                            |
| canonical (capability_os.registry) | 33                                                                            |
| FEATURE_REGISTRY (zz-workspace.js) | 47                                                                            |
| capabilities.py 托管能力               | 3 (hotspot / prefetch / computer_action)                                      |
| API 端点（能力相关）                       | 3 (/api/capabilities, /api/capability_os/catalog, /api/capability_foundation) |

**关键约束（秘密事实）**：`registry.py._build()`（L343-344）在合并时读取  
`caps.CAPABILITIES.items()` 并用 `setdefault` 合并 3 个上下文能力。因此 canonical=33  
**依赖于 capabilities.py 保留其 3 个 CAPABILITIES**。若清空 capabilities.py，canonical 会掉到 31，  
且需改 registry.py（红线）。→ shim 必须**保留数据**而非清空。

---

## 4. 执行模式与纪律 (Mode & Discipline)

- AUTONOMOUS / VERIFY-BEFORE-CHANGE：所有改动前重读真实源码 + 捕获 SHA256 baseline。
- EVIDENCE-FIRST：本报告的每一项结论均来自真实重读或 live 运行，不依赖历史摘要。
- MINIMAL-DIFF：仅在白名单文件（capabilities.py + server.py）上做最小纯兼容改动。
- 修改前若实际源码与冻结事实不一致则 STOP —— 本次实测与冻结事实完全一致，未触发 STOP。

---

## 5. 红线 / 白名单 (Red-lines & Whitelist)

**红线（KEEP，仅 DELETE-CANDIDATE，本次 0 改动）**：  
tools.py · registry.py · capability_os/**init**.py · zz-workspace.js · agent_runtime.py ·  
electron/main.js · config.py · policy · ports · gui/chat.html。

**白名单（允许改动）**：

- `capabilities.py`（→ LEGACY COMPAT SHIM）
- `server.py`（→ /api/capabilities 加 deprecated 标记）
- registry.py 仅在确有必要时作最小纯兼容 accessor（本次**未改动**）。

---

## 6. STEP 1 — VERIFY-BEFORE-CHANGE 证据 (SHA256 Baseline)

实测 7 个 in-scope 文件 SHA256，与冻结 baseline **逐一吻合**，确认可安全进入修改：

| 文件              | 冻结 baseline    | 实测（本会话前）       | 一致 |
| --------------- | -------------- | -------------- | -- |
| tools.py        | bb5ee85…8013   | bb5ee85…8013   | ✅  |
| server.py       | 0517fa72…680d6 | 0517fa72…680d6 | ✅  |
| capabilities.py | 9d14666…9f0319 | 9d14666…9f0319 | ✅  |
| registry.py     | d340e1d…896cf  | d340e1d…896cf  | ✅  |
| **init**.py     | 3bfbcbe…8465b  | 3bfbcbe…8465b  | ✅  |
| zz-workspace.js | d2a7203…27325  | d2a7203…27325  | ✅  |
| chat.html       | 473f1944…11a10 | 473f1944…11a10 | ✅  |

---

## 7. STEP 2 — capabilities.py → LEGACY COMPAT SHIM (Diff Summary)

**改动 A（模块头 + 标记）**：docstring 改为「LEGACY COMPATIBILITY SHIM · Phase 5.4 收口」，  
明确本文件**非真相源**、真相源是 `capability_os.registry`、本模块仅保留上下文注入逻辑、  
`/api/capabilities` 已 deprecated。保留 `CAPABILITIES = {}`，新增 `LEGACY_COMPAT_SHIM = True`。

**改动 B（转发适配器）**：追加 `canonical_forward_view()`，把本垫片托管的 3 个能力「转发」到  
canonical 对应声明，证明本垫片仅为兼容适配（非第二真相源）。

**保留（硬约束）**：`CAPABILITIES`(3) 与 `active_capability_blocks` / `capability_details` /  
`capability_summary` / `_register` 全部保留 —— 因为 registry.py(L343)、**init**.py(L246)、  
server.py(L473)、server_handlers_capability.py(L16)、tests/phase40…(L214) 均依赖它们。

---

## 8. STEP 3 — server.py /api/capabilities → DEPRECATED (Diff Summary)

`server.py` L471-487 `/api/capabilities` handler：

- 返回体增加 `"deprecated": True`；
- 经 `_send(..., headers={"Deprecation": "true"})` 追加 RFC8597 `Deprecation` 头；
- 响应形状保持 `{"ok":True,"count":N,"items":[...]}`（包裹式）—— GUI 仍读 `.items`，零破坏。
- `server.py:27 import capabilities` 保持不动（白名单内）。

---

## 9. STEP 4 — 回归验证结果 (Regression Verification · LIVE)

运行 `phase54-step4-verifier.py` + `phase54-trace.py`（置于 `_ui_archive` 分析区，不入产品树）：

| 检查项                                              | 结果                                       |
| ------------------------------------------------ | ---------------------------------------- |
| `py_compile capabilities.py`                     | OK                                       |
| `py_compile server.py`                           | OK                                       |
| `import capabilities`                            | OK                                       |
| `LEGACY_COMPAT_SHIM`                             | True                                     |
| `capability_details()` 返回数                       | 3 (hotspot / prefetch / computer_action) |
| `/api/capabilities` 体含 `deprecated`              | True                                     |
| `/api/capabilities` 体含 `items`                   | True (list)                              |
| `canonical_forward_view().source`                | capability_os.registry                   |
| `canonical_forward_view()` 转发 3 项                | hotspot / prefetch / computer_action     |
| **canonical 注册表 `len`**                          | **33** ✅                                 |
| canonical 含 hotspot / prefetch / computer_action | True / True / True                       |
| GUARD delete                                     | (available=False, permission=block)      |
| GUARD system                                     | (available=False, permission=block)      |
| GUARD network                                    | (available=False, permission=block)      |

**Harness 透明度说明**：首次以假模块名加载 `registry.py` 时 `@dataclass` 报  
`'NoneType' object has no attribute '__dict__'`——经 traceback 确认为**纯 harness 假名加载产物**  
（dataclass 经 `sys.modules.get(cls.__module__)` 解析注解，假名模块未注册）。改用真实子模块名  
`capability_os.registry`（stub 包而不执行重型 `__init__`）后，**canonical=33 干净复现**。该错误  
**非产品缺陷**。

---

## 10. 真相源收敛结论 (Truth-source Consolidation)

4 个概念层，现仅 1 个真相源：

- (A) `tools.py` = TOOL 模式 + TOOL_FUNCS 派发真相 (62/62) — 未碰。
- (B) `capability_os.registry` = **canonical 产品能力真相 (33)** — 唯一权威，未碰。
- (C) `zz-workspace.js` FEATURE_REGISTRY = UI 可见性真相 (47) — 未碰。
- (D) `capabilities.py` = **已退化为 LEGACY COMPAT SHIM**（保留注入逻辑 + 显式标记 + 转发适配器），  
  不再持有独立存在性真相，经 `canonical_forward_view()` 证明一一对应 canonical。
- 其余 API 投影（catalog_view / foundation_view / /api/capabilities）非独立真相源；  
  `/api/capabilities` 已 deprecated，新消费方应改 `/api/capability_os/catalog` 或  
  `/api/capability_foundation`。

---

## 11. GUI 兼容性分析 (GUI Compatibility)

- `zz-workspace.js` 未改动（SHA256 与冻结 baseline 一致）。
- L86 `getJSON('/api/capabilities')` 在 `fetchSnapshot` 的 `Promise.all` 中消费；
- L94 `snap.capabilities = (r[4] && Array.isArray(r[4].items)) ? r[4].items : asList(r[4], 'capabilities')`  
  —— 原生兼容包裹式 `{"items":[...]}` 响应，`deprecated` 字段被忽略，读 `.items` 不受影响；
- L468 `renderCapabilities()` 渲染 `snap.capabilities`（c.icon/label/description/active）—— 字段未变。
- 结论：**GUI 兼容零破坏**，能力视图照常渲染 3 项。

---

## 12. 消费方依赖图谱 (Consumer Dependency Graph)

`capabilities` 被以下消费方引用（grep 全仓 `capabilit`/`build_context_prefix`）：

- `capability_os/registry.py:343` — `caps.CAPABILITIES.items()`（合并进 canonical，依赖保留）
- `capability_os/__init__.py:246` — `import capabilities as caps` 取 context kind
- `execution_mapping.py:169` — 引用
- `server.py:27,473` — `import capabilities` + `/api/capabilities` 调用 `capability_details()`
- `server_handlers_capability.py:16` — blanket 导入，实际仅用 canonical 路由
- `tests/phase40-capability-foundation.test.py:214` — 期望 `len(items) >= 3`

→ 因保留 `CAPABILITIES` + detail/summary/blocks 函数，**所有消费方无破坏**。

---

## 13. 能力守卫保持 (Capability Guards)

- CRITICAL 占位：delete / system / network 在 canonical 中 `available=False + permission=block`  
  → matcher/router 在语义层即拒绝，不进执行路径（live 验证通过）。
- LOW 种子：`_COMPUTER_ACTION_LOW_SEED` = 9 项（read_file / capture_screen / get_window_info /  
  list_process / perception.screen / perception.window / perception.ocr / search / copy_text），  
  `bootstrap_policy_seeds()` 断言 `seed == _COMPUTER_ACTION_LOW_SEED` 守卫未漂移（canonical=33  
  复现时该断言通过）。
- MCP 单独出口（`foundation_view` L151-186）未并入 33 项真相，保持独立，未改动。

---

## 14. 风险与缓解 (Risks & Mitigations)

| 风险                                                | 状态  | 缓解                                                                              |
| ------------------------------------------------- | --- | ------------------------------------------------------------------------------- |
| 误将 shim 理解为「清空 capabilities.py」导致 canonical 掉到 31 | 规避  | 重读 registry.py:343 发现依赖，保留 CAPABILITIES(3)                                      |
| 改 /api/capabilities 破坏 GUI                        | 规避  | 响应保持包裹式 `.items`，仅加 `deprecated` 字段                                             |
| 触碰红线文件（registry.py/**init**.py/zz-workspace.js）   | 规避  | 仅白名单改动；SHA256 证明 5 保护文件不变                                                       |
| 项目 venv `import tools` 失败                         | 规避  | 改用静态审查 + py_compile + live import（capabilities/capability_os.registry 不经 tools） |
| harness 假名加载触发 dataclass 错误                       | 已澄清 | 以真实子模块名复现 canonical=33                                                          |

---

## 15. 未决项 / 后续 (Open Items / Follow-ups)

- `capabilities.py.migration-bak-20260817` 遗留备份文件存在，本次未读未删；如确认 shim 稳定，  
  可考虑在后续 PHASE 清理（非本阶段职责）。
- 长期迁移：待所有消费方切换到 canonical 端点后，方可移除 `capabilities.py` 的 `CAPABILITIES`  
  与注入函数（届时 canonical 需改为自持 3 项上下文能力，避免 33→31 回归）。
- chat.html 对能力系统 0 引用，维持 KEEP。

---

## 16. 裁决 (Verdict)

**COMPLETE / PASS**

- ✅ 目标 1：`capabilities.py` 已退化为 LEGACY COMPAT SHIM（标记 + 转发适配器 + 数据保留）。
- ✅ 目标 2：`/api/capabilities` 已 DEPRECATE（`deprecated:true` + `Deprecation` 头，GUI 零破坏）。
- ✅ 冻结事实全部守恒：canonical=33、TOOLS=62、TOOL_FUNCS=62、READONLY_TOOLS=28、  
  FEATURE_REGISTRY=47、CAPABILITIES=3、endpoints=3。
- ✅ 红线零触碰：7 文件 SHA256 比对仅 2 个白名单文件变化，5 保护文件字节级不变。
- ✅ 回归全绿：py_compile / live import / canonical=33 / 3 项保留 / 守卫 intact。

---

### 附录 — 改后 SHA256（与 §6 冻结 baseline 比对）

| 文件              | 改后 SHA256      | 相比冻结        |
| --------------- | -------------- | ----------- |
| tools.py        | bb5ee85…8013   | 不变          |
| server.py       | 4b1a91de…6b048 | **已改（白名单）** |
| capabilities.py | 2bdb7e6e…bd0f  | **已改（白名单）** |
| registry.py     | d340e1d…896cf  | 不变          |
| **init**.py     | 3bfbcbe…8465b  | 不变          |
| zz-workspace.js | d2a7203…27325  | 不变          |
| chat.html       | 473f1944…11a10 | 不变          |

### 附录 — 验证脚本

- `G:\xiao6\_ui_archive\phase54-step4-verifier.py`（主回归：compile + import + 响应体构造 + 转发适配器）
- `G:\xiao6\_ui_archive\phase54-trace.py`（canonical=33 复现 + 守卫 + harness 假名问题澄清）
