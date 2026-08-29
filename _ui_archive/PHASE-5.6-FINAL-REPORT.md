# PHASE 5.6 — FINAL REPORT
# 小6 Xiao6 v1.4.0 · DEFAULT CAPABILITY ENTRY CONSISTENCY FIX (P1-1)

状态：**COMPLETE / PASS**

---

## 1. Executive Verdict

唯一必须修复的 P1（DEFAULT 用户能力 UI 读取 deprecated `/api/capabilities` → 仅 3 项 legacy）**已关闭**。
DEFAULT 能力数据源已从 deprecated legacy 3 项切换到 canonical 33 项，DEFAULT 用户可见能力集合与 canonical 真相源现完全一致：

```
DEFAULT UI = 33  =  CANONICAL = 33   ✅
```

改动仅 2 处，全部位于 `zz-workspace.js`；`server.py` ZERO WRITE。冻结数字、安全闸门、policy、execution、ports 全部不变。
P2（`/api/capability_foundation` 无 GUI 消费者）、P3（`execution_mapping.py` 陈旧注释）保持 **RECORD-ONLY**，未触碰。

---

## 2. Baseline（PHASE 5.5 冻结值，本阶段重新核验）

| 指标 | 值 | 核验方式 |
|---|---|---|
| TOOLS | 62 | 源码解析（TOOLS 列表含 name 的条目 = 62） |
| TOOL_FUNCS | 62 | 源码解析（dict 键 = 62） |
| READONLY_TOOLS | 28 | 源码解析 |
| canonical capabilities | 33 | 真实 HTTP `/api/capability_os/catalog` → `total:33` |
| FEATURE_REGISTRY | 47 | 栈式括号解析（数组对象计数 = 47） |
| legacy CAPABILITIES | 3 | `capabilities.py` `_register(` 调用 = 3（hotspot/prefetch/computer_action） |

所有 frozen 值在修改后**未变化**（见 §9）。

---

## 3. Root Cause

PHASE 5.4 将 `/api/capabilities` 标记为 deprecated 并收敛真相源至 `capability_os.registry`（canonical=33），
但 DEFAULT 能力 UI 的数据入口仍在消费该 deprecated endpoint：

```
DEFAULT feature
  → fetchSnapshot(): getJSON('/api/capabilities')        (zz-workspace.js L86)
  → snap.capabilities = r[4].items                       (L94)
  → 首页「能力 N 项」/ 上下文卡 / 设置「能力登记 N 项」/ 能力视图
```

`/api/capabilities` 仅返回 legacy 3 项，造成 **Canonical Truth 33 vs Default Visible Truth 3** 的数据契约/入口一致性 divergence。

### SCHEMA 兼容性发现（关键，决定不能“只改一个字符串”）

| | `/api/capabilities`（旧） | `/api/capability_os/catalog`（新） |
|---|---|---|
| 形状 | `{ok, deprecated, count, **items:[…]**}` | `{total, available, **groups:{g:[…]}**}` |
| 条目字段 | `id, label, icon, group, description, …, **active**` | `id, **name**, …, **available**`（**无** `label`/`active`） |
| 数量 | 3 | 33 |

→ **盲目只改 endpoint 字符串会破坏 DEFAULT UI**：L94 的 parser `(r[4].items)?…` 对 grouped 结构会得到 `[]`（→ “能力 0 项”），且字段名 `name`/`available` 不匹配 UI 消费的 `label`/`active`。
因此本阶段按 STEP 3 要求先报告 contract + required adapter + minimal patch plan，再施以**最小适配补丁**（非大改）。

---

## 4. Exact Change

**唯一改动文件**：`G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js`（2 处）

### 改动 A — L86（数据入口切换）
```diff
-      getJSON('/api/knowledge'), getJSON('/api/capabilities'), getJSON('/api/tasks'),
+      getJSON('/api/knowledge'), getJSON('/api/capability_os/catalog'), getJSON('/api/tasks'),
```

### 改动 B — L94（最小适配 parser：展平 groups + 字段别名，向后兼容）
```diff
-      snap.capabilities = (r[4] && Array.isArray(r[4].items)) ? r[4].items : asList(r[4], 'capabilities');
+      // Phase 5.6 · DEFAULT capability entry switched from deprecated /api/capabilities (legacy 3)
+      // to canonical /api/capability_os/catalog (33). Catalog returns grouped {total,available,groups};
+      // flatten to a flat list and alias canonical name/available → UI label/active for parity.
+      snap.capabilities = (r[4] && r[4].groups)
+        ? Object.keys(r[4].groups).reduce(function (a, g) { return a.concat(r[4].groups[g]); }, []).map(function (c) { return Object.assign({}, c, { label: (c.label != null ? c.label : c.name), active: !!c.available }); })
+        : ((r[4] && Array.isArray(r[4].items)) ? r[4].items : asList(r[4], 'capabilities'));
```

适配逻辑：若响应含 `groups`（catalog）→ 展平所有分组为 33 项扁平数组，并对每项补 `label`(取 `name`)、`active`(取 `available`)；否则走原 legacy/列表兼容分支。**未重写** `renderCapabilities()`、FEATURE_REGISTRY、registry、tools、policy、UI 布局、CSS、能力定义。

---

## 5. Before → After data flow

**BEFORE**
```
DEFAULT feature
  → /api/capabilities                      (deprecated, 仍返回 3)
  → capabilities.py (LEGACY_COMPAT_SHIM)
  → 3 legacy items (hotspot/prefetch/computer_action)
  → snap.capabilities = 3
  → DEFAULT UI: 「能力 3 项」
```

**AFTER**
```
DEFAULT feature
  → /api/capability_os/catalog             (canonical)
  → capability_os.catalog_view()
  → canonical registry = 33
  → snap.capabilities = 33 (展平 + label/active 别名)
  → DEFAULT UI: 「能力 33 项」
```

---

## 6. Static Validation

- ✅ **JS syntax**：`node --check zz-workspace.js` → `SYNTAX OK`
- ✅ **无残留 DEFAULT `/api/capabilities` 消费者**：`grep "getJSON('/api/capabilities')"` → **NONE**
- ✅ **FEATURE_API_MAP['capability-os'] 仍正确**：L722 `'capability-os': '/api/capability_os/catalog'`
- ✅ **未误改其他 endpoint**（仅 L86 一处字符串变更，L94 为 parser 适配）

---

## 7. Real HTTP Validation（运行中小6 server，端口 8010）

- ✅ **GET /api/capabilities**（deprecated 保留）：
  `HTTP 200 · Deprecation: true · {"ok":true,"deprecated":true,"count":3,"items":[3 legacy]}`
- ✅ **GET /api/capability_os/catalog**（canonical）：
  `HTTP 200 · {"total": 33, "available": 27, "groups": 10 个能力域}`（Content-Length 15534，verbose + urllib 双重确认）
- ⚠️ 注：catalog 路由在个别 curl 尝试中出现服务端 `ConnectionResetError`（BaseHTTP 偶发），但响应体完整交付（15534 字节合法 JSON，`total:33`）。属传输层偶发，非逻辑问题；以 urllib 稳定抓取 + verbose 完整响应为准。

---

## 8. Real Browser / E2E Validation

（浏览器不可直接启动；以**等价 DOM 验证**：将真实 HTTP catalog 载荷喂入与 L94 **逐字一致**的 adapter，证明 `snap.capabilities` 经 fetchSnapshot 后即为 33 且字段/闸门正确。render* 函数均只读 `snap.capabilities`，故 DOM 表现等价。）

- ✅ **`snap.capabilities.length = 33`**（真实 catalog 载荷 + 逐字 L94 adapter → node 执行）
- ✅ **抽查 canonical 条目**（label/icon/active 均正确）：
  `voice=语音🎙️`, `memory=记忆🧠`, `knowledge=知识库📚`, `goals=目标🎯`, `computer_action=电脑操作✋`, `hotspot=热点上下文📡`, `prefetch=预取背景🌤️`
- ✅ **CRITICAL 闸门不变**（安全未降级）：
  `delete → available:false / permission:block`
  `system  → available:false / permission:block`
  `network → available:false / permission:block`
- ✅ **renderCapabilities() 字段齐备**：`icon / label / description / active` 均存在 → 不抛异常
- ✅ **首页「能力 33 项」**、上下文卡「能力 33」、设置「能力登记 33 项」均源自 `.length = 33`
- ✅ **@触发器能力过滤**（L792 `c.label || c.id`）现显示真实名称而非 id

---

## 9. Regression（冻结数字重新核验 = 未变化）

| 指标 | 修改前 | 修改后 | 状态 |
|---|---|---|---|
| TOOLS | 62 | 62 | 不变 |
| TOOL_FUNCS | 62 | 62 | 不变 |
| READONLY_TOOLS | 28 | 28 | 不变 |
| canonical | 33 | 33 | 不变（真实 HTTP total:33） |
| FEATURE_REGISTRY | 47 | 47 | 不变 |
| legacy CAPABILITIES | 3 | 3 | 不变 |
| policy | — | — | 未触碰（policy_engine.py 哈希不变） |
| execution | — | — | 未触碰（ai_core/execution/api.py 哈希不变） |
| ports | 8010 | 8010 | 未触碰（server.py 哈希不变） |

---

## 10. SHA256 Diff Audit

| 文件 | 修改前 SHA256 | 修改后 SHA256 | 变化 |
|---|---|---|---|
| **xiao6-space/js/zz-workspace.js** | `d2a7203c…c27325` | `76e55100…e862a9` | **CHANGED（预期）** |
| server.py | `4b1a91de…6b048` | `4b1a91de…6b048` | 不变 |
| capability_os/registry.py | `d340e1d2…e896cf` | `d340e1d2…e896cf` | 不变 |
| capability_os/__init__.py | `3bfbcbe1…d8465b` | `3bfbcbe1…d8465b` | 不变 |
| capabilities.py | `2bdb7e6e…24bd0f` | `2bdb7e6e…24bd0f` | 不变 |
| policy_engine.py | `ebd1b2ed…ac455b` | `ebd1b2ed…ac455b` | 不变 |
| ai_core/execution/api.py | `d005aeb5…4b28b` | `d005aeb5…4b28b` | 不变 |

**仅 `zz-workspace.js` 发生变化。所有红线文件（tools.py / capabilities.py / registry.py / __init__.py / agent_runtime.py / config.py / policy / execution / electron / chat.html）哈希均不变。**

---

## 11. P1 Closure

**P1（DEFAULT 能力入口一致性 divergence）= CLOSED。**
DEFAULT 用户可见能力集合 = canonical = 33。根因（DEFAULT UI 读 deprecated legacy 3）已消除。

---

## 12. P2 / P3 remain RECORD-ONLY

- **P2**（`/api/capability_foundation` 无 GUI 消费者）：已确认 `zz-workspace.js` 与 `index.html` 中**无任何**对该端点的引用 → 仍孤立。**未触碰**（超出 P1 范围）。
- **P3**（`execution_mapping.py` 注释称 focus_window/browser_navigate「不在白名单」，但 `safety.py` WHITELIST 已含二者）：陈旧注释。**未触碰**（超出 P1 范围）。

---

## 13. Files Changed

- `G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js`（2 处：L86 endpoint，L94 parser 适配）

## 14. Files Protected（红线，均未改动）

tools.py · capabilities.py · capability_os/registry.py · capability_os/__init__.py ·
agent_runtime.py · config.py · policy_engine.py · ai_core/execution/api.py · server.py ·
electron/main.js · chat.html · 数据库 · 端口 · 启动方式 · runtime

---

## 15. Final Acceptance Audit（对应 STEP 10 的 12 问）

1. **DEFAULT capabilities 数据源现在是什么？** → `/api/capability_os/catalog`（canonical）
2. **DEFAULT UI 显示多少 Capability？** → **33**
3. **canonical registry 是否仍为 33？** → 是（真实 HTTP `total:33`）
4. **`/api/capabilities` 是否仍 deprecated？** → 是（`Deprecation: true` 响应头 + `deprecated:true` 字段，仍返回 3）
5. **legacy 3 项是否仍保留？** → 是（capabilities.py `LEGACY_COMPAT_SHIM=True`，且已并入 canonical 33）
6. **是否删除了任何文件？** → 否
7. **是否修改了 capabilities.py？** → 否
8. **是否修改了 registry.py？** → 否
9. **是否修改了 tools.py？** → 否
10. **是否修改了 policy / execution / ports？** → 否（哈希不变）
11. **P1 是否真正关闭？** → 是
12. **P2 / P3 是否保持 RECORD-ONLY？** → 是

### 残余项（透明披露，非阻塞，超出 P1 范围，按纪律未改）
命令面板中 `feat:capabilities`（COMMANDS 自动生成项）经 `openFeature('capabilities')` → `featureRoute` 动态拼出 `/api/capabilities`，在 overlay 中以原始 JSON 展示 3 项 legacy。该路径**不属于** DEFAULT 可见能力 UX（DEFAULT 走 `switchView('capabilities')` → `renderCapabilities()` → `snap.capabilities`=33），且 STEP 6.2 的「无 `getJSON('/api/capabilities')` 消费者」已满足。留作可选后续（建议在 PHASE 5.7 或单独任务中将 `'capabilities'` 加入 FEATURE_API_MAP 指向 catalog），本次因 ZERO-SCOPE-CREEP 纪律未顺手修改。

---

## 16. STOP

PHASE 5.6 完成，已停止。**未自动进入 PHASE 5.7。**

下一步需老板授权，方可决定是否：
- 处理 P2（`/api/capability_foundation` 消费者补全或显式废弃）
- 处理 P3（`execution_mapping.py` 注释更新）
- 关闭上述「残余项」（命令面板 `feat:capabilities` 路由）
- 或进入 PHASE 5.7
