# 06 · UX Bug Bash（缺陷清单）— Phase 5

> 阶段：AI OS Alpha Stabilization Program v1.0 · Phase 5
> 身份：Senior QA Architect + Senior Product Architect + Senior UX Engineer + AI OS Release Manager
> 模式：**Audit → Observe → Simulate → Verify → （仅建清单）→ STOP**（本 Phase **严禁直接修复**，所有修复统一留 P6 窗口）
> 日期：2026-08-06
> 上游：P0 预飞 / P1 用户旅程 / P2 每日工作流 / P3 Workspace 稳定性（04）/ P4 能力体验审计（05）
> 下游：P6 允许修复 / P7 回归 / P8 性能 / P9 就绪 / P10 文档

---

## 一、目的与纪律（P5 专属）

**目的**：将 P2/P3/P4 各阶段**已定位**的全部用户可见缺陷（含 1 项 🔴 P0）、既有 latent 缺陷、以及体验/一致性问题，**整合为单一、可追踪、按严重度排序的 Bug 清单**。本清单是 P6 修复的唯一输入契约。

**纪律（严守）**：
- ✅ **仅建清单，禁改任何代码 / 配置 / UI / CSS / JS / Python / 文档正文以外内容。**
- ✅ 本 Phase 不落地任何修复；修复方向仅作为 P6 的"建议项"记录。
- ✅ 不新增能力 / 不进禁区 / 不触碰冻结文档 / 不提交 Git（与全专项一致）。
- ✅ 每条 Bug 必须可追溯到上游 Phase 的具体 Finding（F# / EXP-# / P0），并给出**最小修复形态**（配置/文案/单行级，零行为新增）。

**Verified 事实**（本 Phase 复核确认，非臆测）：
- 🔴 P0 缺陷**已真实复现定位**：`xiao6-ui/tools.py:3286` 调 `_execution_run(p["name"], p["args"], allowed)`；而 `ai_core/execution/api.py:31` 签名为 `def run(name, args, *, allowed=None, ...)`（`allowed` 为 keyword-only）→ 位置传参触发 `TypeError`，对话执行写类工具即崩溃。全仓其余调用点（`server.py:2008` 用 `allowed=remote_allowed`、`agent_runtime.py:234`、`social_inbound.py:125`）形态正确，故此点是**唯一**破损调用。
- P3-F6 / P4-EXP-1 同源已确认：`briefing`/`weather` 在 `panel-manager.js` REG 误配 `overlayId:'zz-panel', host:true`，与真实 `OverlayManager.track` id 不符。

---

## 二、清单总览（严重度排序）

| Bug ID | 严重度 | 标题 | 来源 | 修复形态 | 阻断 Alpha？ |
|---|---|---|---|---|---|
| **BUG-001** | 🔴 P0 | 对话工具执行崩溃（`allowed` 位置参数错误） | P2 定位 / `tools.py:3286` | 单行（keyword 传参） | ✅ 阻断每日工作流 |
| **BUG-002** | 🔴 高 | briefing/weather「关闭所有面板」孤儿 | P3-F6 + P4-EXP-1（同源） | 单/双行 REG 配置 | ✅ 阻断"一键收拢"预期 |
| **BUG-003** | 🟠 中高 | `closeAllPanels` 双路径分裂 | P4-EXP-3 | 删手写白名单，收敛单一出口 | 间接（EXP-1 根因之一） |
| **BUG-004** | 🟠 中 | Command Dock 误导快捷键文案 | P4-EXP-2（`command-dock.js:36`） | 纯文案删除 | 否（降信任） |
| **BUG-005** | 🟡 中低 | Feature Flag 声明 ≠ 运行时默认 | P4-EXP-5（`config.py`） | 低风险一致性对齐 | 否（体验不确定） |
| **BUG-006** | 🟡 低 | `pin/togglePin/unpin` 死功能 | P3-F7 | 接线或标注未启用（二选一） | 否 |
| **BUG-007** | 🟡 低 | 折叠态不持久化（`registerCollapse`） | P3-F8 | 并入 `WorkspaceState.data` | 否 |
| INFO | — | P3-F9 R1 共享宿主歧义 | P3-F9 | = BUG-002 根因实证 | 不单列 |

> **Release Gate 关联**：BUG-001 决定 Gate 7（Daily Workflow）/ Gate 8（User Journey 无 P0）/ Gate 9（Regression）；BUG-002/003 决定 Gate 3（Workspace 未回退）；BUG-004/005 决定 Gate 4（Capability 未违反，经验暴露诚实性）。

---

## 三、逐条明细（含最小修复形态，P6 执行）

### 🔴 BUG-001 · P0（Critical）— 对话工具执行崩溃

- **现象**：用户在对话中触发需执行的工具（写类工具，如 `add_knowledge`、文件/系统/电脑控制等）时，后端抛 `TypeError: run() takes 2 positional arguments but 3 were given`（或等价），工具执行失败，对话中断。
- **位置**：`xiao6-ui/tools.py:3286`
  ```python
  def run_one(p):
      return p, str(_execution_run(p["name"], p["args"], allowed))   # ← allowed 被位置传参
  ```
- **根因**：`ai_core/execution/api.py:31` 的 `run(name, args, *, allowed=None, ...)` 中 `allowed` 为 **keyword-only**（`*` 之后）。`tools.py:3286` 将 `allowed` 作为第 3 个位置参数传入，违反签名。
- **影响**：**阻断"对话即执行"这一核心每日工作流路径**——小6作为"每天可真正使用的 AI OS"的关键能力失效。属 🔴 P0。
- **最小修复形态（P6，单行，零行为新增）**：
  ```python
  return p, str(_execution_run(p["name"], p["args"], allowed=allowed))
  ```
  与 `server.py:2008` `_execution_run(name, args, allowed=remote_allowed)` 形态对齐即可。
- **验证前提（P7）**：修复后须用对话触发至少 1 个写类工具（如 `add_knowledge`）验证不再抛 `TypeError`，且只读工具路径（`agent_runtime.py` / `reflector.py` / `social_inbound.py`）不受影响。

---

### 🔴 BUG-002 · 高（High）— briefing/weather「关闭所有面板」孤儿

- **现象**：指令中心执行「关闭 所有面板」后，**每日简报（briefing）与天气（weather）浮层仍保持打开**。
- **位置**：`xiao6-ui/panel-manager.js` REG 表（约 `:90-93`）
  ```js
  weather:   { overlayId: 'zz-panel', host: true },   // 实际不 track zz-panel
  briefing:  { overlayId: 'zz-panel', host: true },   // 实际 track('briefing')
  ```
- **根因（P3-F6 + P4-EXP-1 同源）**：
  - `weather` 实际经 `weather.js` 切换 `body.weather-mode` + `#weather-panel`（独立节点，从不 `track`），与 `zz-panel` 无关；
  - `briefing` 真实 `OverlayManager.track('briefing', …)`（`app.js:1655`），id 为 `'briefing'`，与 REG 的 `'zz-panel'` 不符；
  - → `PanelManager.isOpen('briefing')` 查 `OverlayManager.isOpen('zz-panel')`（恒 false）→ `closeAll` 跳过；`isOpen('weather')` 在 agent-profile 打开时误报。
- **影响**：用户"一键收拢全部浮层"预期落空，造成「关不掉」困惑；削弱 Gate 3（Workspace 未回退）。
- **最小修复形态（P6，配置级，零行为新增）**：
  ```js
  weather:  { btnId: 'wxOpenBtn' },                              // 移除错误 host/zz-panel
  briefing: { btnId: 'btnBriefing', overlayId: 'briefing' },     // zz-panel → 真实 briefing
  ```
  `agent-profile` 保持 `{ overlayId: 'zz-panel' }` 不变（唯一正确的 `zz-panel` 使用者）。
- **验证前提（P7）**：打开 briefing + weather + 任一模块面板 → 指令中心「关闭所有面板」→ 三者均关闭；`isOpen('weather')` 在 agent-profile 打开时不再误报。

---

### 🟠 BUG-003 · 中高（Medium-High）— `closeAllPanels` 双路径分裂

- **现象**：`command-palette.js:98-102` `closeAllPanels()` 同时依赖 (a) 手写 `*-mode` 体类白名单与 (b) `PanelManager.closeAll()`，两路径不一致即产生关闭孤儿（**BUG-002 即后果**）。
- **位置**：`xiao6-ui/command-palette.js:98-102`
  ```js
  function closeAllPanels() {
    ['hotspot','weather','sysmon','term','doc','memory','map','memq'].forEach(m =>
      document.body.classList.remove(m + '-mode'));        // (a) 手写白名单，无 briefing
    if (window.ZZSettings) window.ZZSettings.close();
    if (window.PanelManager) window.PanelManager.closeAll(); // (b) 依赖 REG overlayId 正确
  }
  ```
- **根因（P4-EXP-3）**：Overlay 统一化（D9）已建 `OverlayManager` 但未收口——两套关闭语义并存；任何新增面板若只接 REG 不加体类、或反之，都会被漏掉。
- **影响**：面板关闭语义碎片化，是架构级体验债；修复 BUG-002 后此路径仍脆弱。
- **最小修复形态（P6，架构收敛，零行为新增）**：以 `PanelManager.closeAll()` 为**唯一**关闭收敛点（修复 BUG-002 后 REG 覆盖所有面板），`closeAllPanels` 退化为：
  ```js
  function closeAllPanels() {
    if (window.ZZSettings) window.ZZSettings.close();
    if (window.PanelManager) window.PanelManager.closeAll();
  }
  ```
  删除手写体类白名单（依赖 BUG-002 修复后覆盖完整）。
- **验证前提（P7）**：回归 (a)(b) 收敛后「关闭所有面板」对全部 REG 面板一致生效。

---

### 🟠 BUG-004 · 中（Medium）— Command Dock 误导快捷键文案

- **现象**：`command-dock.js:36` 渲染 `Ctrl/Cmd+U 打开宇宙视图 · ⌘/Ctrl+K 快捷命令 · 支持拖拽文件`，但全仓**无 `Ctrl/Cmd+U` 处理器**（P3 入口地图已标「疑似未实现/死快捷键」）。
- **位置**：`xiao6-ui/command-dock.js:36`
- **影响**：向用户**承诺不存在的能力**，按键/点击无反应 → 误导、降低信任；与"暴露诚实"原则冲突（Gate 4 扣分项）。
- **最小修复形态（P6，纯文案，零行为新增）**：删除 `Ctrl/Cmd+U 打开宇宙视图` 片段，保留其余真实提示（`⌘/Ctrl+K 快捷命令 · 支持拖拽文件`）。**不实现宇宙视图**（属禁区）。
- **验证前提（P7）**：Dock 文案无死快捷键承诺；`Ctrl/Cmd+K` 仍可用。

---

### 🟡 BUG-005 · 中低（Medium-Low）— Feature Flag 声明 ≠ 运行时默认

- **现象**：`config.py` 顶部常量多为 `False`，但 `reload()` 以 `os.environ.get("FEATURE_X","true")` 覆盖 → 多数 flag **实际运行时默认开启**（P4-EXP-5 / P0 报告 §2.3 已记）。
- **位置**：`xiao6-ui/config.py`（`reload()` 覆盖逻辑）。
- **影响**：用户在设置中切换某 flag，若其运行时默认被 env 强制，可能出现「关不掉/开不稳」的体验不确定感；对每日使用影响有限但存在，属配置一致性问题。
- **最小修复形态（P6，低风险一致性对齐）**：统一 `config.py` 声明默认与 `reload()` 运行时默认（如将 env 默认改为与声明一致，或文档化"运行时默认以 env 为准"）。**不改功能行为、不触权限/架构红线。**
- **验证前提（P7）**：设置面板开关的"开/关"与运行时行为一致；不引入新 flag。

---

### 🟡 BUG-006 · 低（Low，不阻塞）— `pin/togglePin/unpin` 死功能

- **现象（P3-F7）**：`PanelManager.pin/togglePin/unpin` 全仓无任何 UI 消费者调用；`WorkspaceState.pinnedPanelIds` 永不被填充，`ws-pinned` 类不出现。"固定面板"为死功能。
- **影响**：无功能回归，不阻塞 Alpha 每日使用；但若用户从文档/预期知此功能会落空。
- **最小修复形态（P6，二选一，均允许范围）**：
  1. **接线**（体验修复）：在某面板 header 增加"固定"按钮调用 `PanelManager.pin(id)`；或
  2. **标注未启用**：在文档/设置中标注"固定面板尚未启用"，避免预期落空。
  - 推荐 (2)（风险最低），除非 P6 决定一并接线。
- **验证前提（P7）**：若选 (1) 则面板固定/取消生效且持久化；若选 (2) 则文档准确。

---

### 🟡 BUG-007 · 低（Low，不阻塞）— 折叠态不持久化

- **现象（P3-F8）**：`registerCollapse` 仅 `memory.js` 用于记忆面板侧栏/大纲折叠；折叠态存于 `panel-manager.js` 模块级 `_collapseState`，**未并入 `WorkspaceState.data`**，而 `collapse/expand` 调用的 `WorkspaceState.save()` 不序列化 `_collapseState` → 刷新后折叠状态不恢复。
- **影响**：仅记忆面板折叠受影响，极小，不阻塞。
- **最小修复形态（P6，状态修复）**：将 `_collapseState` 并入 `WorkspaceState.data.collapseState` 并在 `save/load` 中序列化；或折叠态改由 `WorkspaceState` 统一持有。
- **验证前提（P7）**：记忆面板折叠 → 刷新 → 折叠态恢复。

---

### ℹ️ INFO · P3-F9 — R1 共享宿主歧义（不单列）

P1 报告 R1 担忧"weather/briefing/agent-profile 共享 `zz-panel` 导致 `isOpen` 歧义"。实测仅 `agent-profile` 真正 `track('zz-panel')`；weather/briefing 各自独立实现。**该歧义正是 BUG-002 的根因实证**，已由 BUG-002 修复覆盖，不单列动作项。

---

## 四、修复窗口映射（→ P6）

| Bug ID | 修复文件 | 修复类型 | 风险 | 是否必须（P6） |
|---|---|---|---|---|
| BUG-001 | `tools.py:3286` | 单行 keyword 传参 | 极低 | ✅ 必须（P0） |
| BUG-002 | `panel-manager.js` REG | 配置级 | 极低 | ✅ 必须（Gate 3/4） |
| BUG-003 | `command-palette.js` `closeAllPanels` | 架构收敛 | 低 | ✅ 建议（配合 BUG-002） |
| BUG-004 | `command-dock.js:36` | 纯文案 | 极低 | ✅ 建议（Gate 4） |
| BUG-005 | `config.py` `reload()` | 一致性对齐 | 低 | 🟡 评估（可选） |
| BUG-006 | `panel-manager.js` / 文档 | 接线或标注 | 低 | 🟡 可选 |
| BUG-007 | `panel-manager.js` + `WorkspaceState` | 状态修复 | 低 | 🟡 可选 |

> **全部修复均为 UI / 配置 / 文案 / 状态层，零能力新增、零行为语义扩张、不触任何冻结红线（L0 Golden State / Governance / Architecture / Capability / Permission / EventBus / DB Schema）。** 符合 P0 报告 §3 允许范围。

---

## 五、严重度与 Release Gate 判定（P5 时点）

| Release Gate | P5 清单影响 | 当前状态 |
|---|---|---|
| Gate 1 Architecture 未违反 | 清单修复均不触架构 | 🔒 不受影响 |
| Gate 2 Capability 未违反 | BUG-004 属暴露诚实扣分项 | ⏳ 修 BUG-004 后 FULL |
| Gate 3 Workspace 未回退 | BUG-002/003 削弱 `closeAll` | ⏳ 修 BUG-002/003 后 FULL |
| Gate 4 Companion 未扩张 | 无 Companion 扩张 | 🔒 不受影响 |
| Gate 5 Golden State 未违反 | 无触碰 | 🔒 不受影响 |
| Gate 6 Product Constitution 未违反 | 无触碰 | 🔒 不受影响 |
| Gate 7 Daily Workflow 可连续完成 | **BUG-001 阻断对话执行** | 🔴 FAIL（修 BUG-001 后验证） |
| Gate 8 User Journey 无 P0 | **BUG-001 = P0** | 🔴 FAIL（修 BUG-001 后验证） |
| Gate 9 Regression 全 PASS | 依赖 P7 回归 | ⏳ P7 验证 |

**P5 总裁决**：清单整合完成——**1 项 P0（BUG-001）+ 2 项 High（BUG-002/003）+ 2 项 Medium（BUG-004/005）+ 2 项 Low（BUG-006/007）**。所有项均可在 P6 以"配置/文案/单行/状态"级修复收口，且**无任何项要求新增能力或进入禁区**。P0 必须由 P6 优先修复并 P7 回归，否则 Gate 7/8/9 无法满足、Alpha 不可宣布 Ready。

---

## 六、下一步与 STOP

**P6 允许修复（按优先级）**：
1. 🔴 **BUG-001**（`tools.py:3286` → `allowed=allowed`）—— **最高优先，P0**。
2. 🔴 **BUG-002**（`panel-manager.js` REG briefing/weather 配置修正）+ 🟠 **BUG-003**（`closeAllPanels` 收敛）。
3. 🟠 **BUG-004**（`command-dock.js:36` 删误导文案）。
4. 🟡 BUG-005 / 006 / 007（评估/可选）。

**P7 回归**：P6 修复后**重启隔离后端 `:8011`**（P2 启动，task `sW2LjI` 仍运行，P6 后重启），覆盖：① 对话执行写类工具（BUG-001）② 关闭所有面板含 briefing/weather（BUG-002/003）③ Dock 文案（BUG-004）④ 设置 flag 一致性（BUG-005）⑤ 固定/折叠持久化（BUG-006/007）。

**P8 性能审计（仅 UI）/ P9 就绪 / P10 文档（11 份落 `docs/releases/alpha-v1/`）** 顺次推进。

---

🛑 **本 Phase 5 为纯清单构建，已完成、7 条 Bug 全部可追溯、修复形态明确 —— STOP，移交 P6（允许修复）。** 全程零代码改动，未触碰任何冻结文档/红线；清单即 P6 的唯一输入契约。
