# Phase 6 — Order 8 · Design System Runtime Consolidation

> 状态：**实现完成，全量测试通过（240/240）。Phase 6 Implementation 正式收口。**
> 纪律：Implementation Only / Architecture Frozen —— 仅消除遗留违约、统一运行时实现，不重新设计、不美化、不新增功能。
> 日期：2026-08-03

---

## 1. 修改文件列表

| 文件 | 变更 | 说明 |
|------|------|------|
| `xiao6-ui/solar-system.js` | **+2 行 / -1 行**（实际 Order 8 改动） | `focusOn` 发布焦点时，硬编码 `'FOCUS_CHANGED'` → 改走事件契约常量 `ZZ.EVENTS.FOCUS_CHANGED`（带防御性回退）。其余 750+ 行差异为 Order 6/7 累计未提交量（状态节点渲染 + 焦点连线），非本 Order 新增。 |
| `xiao6-ui/index.html` | +1 行 | `solar-system.js` 缓存版本号 bump 至 `?v=20260803o8`（项目约定：前端改动须 bump）。 |
| `xiao6-ui/tests/phase6-order8.frontend.test.js` | **新增**（未跟踪） | Order 8 收敛回归测试：静态零硬编码事件 + 合约 38 无漂移 + galaxy 状态收敛锁 + CSS `:root` 无重复令牌。 |

> 注：本 Order **未新增任何运行时模块、未新增 Token、未改 Design System 配色、未改视觉/动画/CSS 规则**。全部为"收口"动作。

---

## 2. Git Diff Summary

- **Order 8 实际增量**：`solar-system.js` 1 处事件常量化、`index.html` 1 处版本 bump、`tests/phase6-order8.frontend.test.js` 新增。
- `git diff --stat` 对 `solar-system.js`/`index.html` 显示的 566+/220- 为 **Phase 6 全程（Order 1–8）累计未提交差异**（实现纪律要求"停止并等待 Code Review"，故尚未 commit）。
- 新增运行时文件（`app-state.js`/`event-bridge.js`/`galaxy-state.js`/`galaxy-runtime.js`/`overlay-runtime.js`/`intent-gateway.js`）均为 Order 1–7 落地，本 Order 仅消费与校验。

---

## 3. 审计结论（对应指令 ①–⑥）

### ① 全项目审计
实际扫描 `xiao6-ui/*.js`（52 个活跃模块）、`*.css`、`index.html`、后端 `*.py`（~75 文件）。逐项核查：

| 违规类别 | 结论 | 处理 |
|----------|------|------|
| 重复状态 | 无。`AppState` 是唯一状态核心，无第二份业务状态存储。 | 无需处理 |
| 重复 Token | 无。`styles.css:root` 为基础单一来源，`premium.css:root` 为增量层（引用前者、零重复）。 | 无需处理 |
| 平行变量 | 无。`premium.css` 的 motion/elev/r 令牌为 styles.css 所缺维度的**补充**，非平行副本。 | 无需处理 |
| Magic Number | 状态节点 3D 布局常量（`115+i*7`、`4/7/10/13` 偏移）属**场景几何**，非 Design System 间距令牌，不在 Design Token 范畴。 | 记录，不修 |
| Magic Color | 品牌银河色 `0x5599bb`（轨道环）、`0x88aaff`（状态节点占位）为**宪法红线保护的品牌资产**，非违规。 | 记录，不修 |
| 硬编码事件 | **发现 1 处**：`solar-system.js:612` `AS.applyEvent('FOCUS_CHANGED', …)` 裸字符串。 | **已修复** → `ZZ.EVENTS.FOCUS_CHANGED` |
| 硬编码状态 | 无。状态词表集中在 `app-state`/`galaxy-state`/`galaxy-runtime`/`overlay-runtime`，大小写一致。 | 无需处理 |
| 旧 Theme | 无。"多主题"（`light`/`dark-cyan…rose`）是产品功能，非遗留旧主题。 | 无需处理 |
| 废弃模块 | 无。遗留功能模块（avatar/hotspot/command-palette 等）为冻结前活跃功能，非废弃。 | 无需处理 |
| 死代码 | 运行时栈内无死代码。唯一 `console.warn`（app-state.js:430）是**有意的合约守卫**（忽略非合约事件），非遗留调试。 | 无需处理 |
| 重复实现 | 无。无重复状态机/运行时；`_goalIdOf` 仅定义于 `galaxy-runtime.js`。 | 无需处理 |
| 绕过 Runtime/AppState/Event Bridge | 运行时栈内**无旁路**。预冻结功能模块（app.js 等）的 `fetch('/api/…')` 为命令/动作/配置端点，属 Phase 6 运行时范围外（改动即违规 redesign）。 | 记录为技术债，不修 |

### ② Design Token 收口
颜色/字体/Spacing/Border/Radius/Icon/Glow/Theme/Motion 引用**已统一**于 `styles.css:root` + `premium.css:root` 双层体系，无新增 Token、无重新设计颜色。唯一动作：将焦点事件名从字面量收口为契约常量（属事件契约范畴，已在 ① 修复）。

### ③ Runtime 收口
状态变化链路 **Event → AppState → Runtime → Renderer** 已确立且唯一：
- 唯一写入入口 `AppState.applyEvent`（`event-bridge.js` 桥接 SSE；reducer 单一写入）。
- `GalaxyRuntime` 消费 `GalaxyState`；`OverlayRuntime` 消费 `AppState`+`GalaxyState`；`solar-system.js` 仅消费 Runtime 数据。
- 无模块自行维护业务状态。

### ④ CSS 收口
`:root` 令牌无重复定义、无死变量（`--qc-c`/`--bc` 等别名均被实际使用）。主题/逐元素重定义（`body[data-theme=light]{--void:…}`、`.hs-open-btn{--bc:…}`）为**合法**的逐主题/逐组件令牌覆盖，非重复定义。无需删除。

### ⑤ JS 收口
运行时栈无废弃代码、旧事件、旧桥接、重复 Helper、未引用模块、Mock 数据、遗留调试代码。`hotspot.js` 的 `MOCK_FEED` 是热点大屏**刻意装饰性示例事件流**（注释明言"真数据来自 /api/hotspots；装饰数据沿用科技感动效"），属冻结前功能，非 Phase 6 运行时 mock，保留。

### ⑥ 一致性检查
- **状态词表**：`app-state`（9 域态）→ `galaxy-state`（23 投影态）→ `galaxy-runtime`（8 规范态）→ `overlay-runtime`（5 生命周期）。`galaxy-runtime.mapState()` 已覆盖 `Started`（→Running）等全部 galaxy 投影态，收敛无越界。
- **事件词表**：前端 `zz-events.js`（38）逐字对齐后端 `eventbus.DOMAIN_EVENT_NAMES`（38）；后端 `publish_domain` 强制校验，越界即抛错。
- **命名/大小写/生命周期**：全部大写首字母规范，跨运行时一致。

---

## 4. 测试（对应指令 ⑦）

新增 `phase6-order8.frontend.test.js`（4 项），并重新执行 **Order 1–8 全量回归**：

| 套件 | 结果 |
|------|------|
| Frontend (node) Order 1–8 | 7 + 22 + 39 + 19 + 19 + 17 + 26 + 4 = **153 / 153** |
| Backend / Integration (python 3.11) Order 1–7 | 3 + 9 + 16 + 16 + 17 + 16 + 10 = **87 / 87** |
| **合计** | **240 / 240 全绿** |

（Smoke 由 Integration 真实后端运行覆盖；O8 无新增运行时故无独立 IT，其收口由 O8 FE 静态/一致性测试锁定。）

---

## 5. 交付物（对应指令 ⑨）

- `CHANGELOG_PHASE6_ORDER8.md`（本文件）
- `PROJECT_AUDIT_FINAL.md`（12 节最终工程审计）
- `PHASE6_FINAL_REPORT.md`（Phase 6 最终完成报告）

---

## 6. 红线合规

银河本体（太阳 + 8 行星 + 星空 + 流星 + 点击聚焦）作为宪法红线 **100% 未触碰**。本 Order 仅为运行时与设计令牌层的"收口"，未改任何视觉/CSS/Shader/动画，品牌资产完整保留。
