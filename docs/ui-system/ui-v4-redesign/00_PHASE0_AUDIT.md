# UI-v4 Clean Reconstruction · Phase 0 — 完整审计与旧 UI 删除清单

> 身份：Senior Product Designer + Senior Frontend Architect + AI OS Experience Designer
> 阶段纪律：Audit → Design → Implementation → Verify → Document（不中途停止）
> 本阶段只产出清单，不删任何文件；Phase 7 才执行下线。

---

## 1. 审计范围与方法

- 实测 `G:\Xiao6\xiao6-ui\` 根目录全部 CSS/JS/HTML。
- 结合 v3 设计文档（`ui-v3-redesign/00_UI_V3_AUDIT_FINAL.md`）结论。
- 实时能力核查：`/api/goals`、`/api/memories`(+`/graph`)、`/api/knowledge`、`/api/agent/state`、`/api/stream`(SSE)、`zz-events.js`(事件单一来源)、`avatar-state.js`(8态调色板)、`sse-manager.js`(SSE单例)、`command-dock.js:sendText`(复用链路)。

---

## 2. 当前旧 UI 表现层文件清单（根目录）

### 2.1 旧 CSS（表现层，v4 不继承其布局规则）
| 文件 | 角色 | v4 处置 |
|---|---|---|
| `ui2.css` | 设计 token 地基（270 token、z-index 14 级、圆角、缓动） | **保留文件**；仅取 token 值，布局规则不继承 |
| `ui4b-explore-transition.css` | UI-4 补丁 | 删除（视觉依赖） |
| `ui4b-first-screen.css` | UI-4 补丁 | 删除 |
| `ui4c-unified-home.css` | UI-4 补丁 | 删除 |
| `ui4c-visible-upgrade.css` | UI-4 补丁 | 删除 |
| `ui4d-home-experience.css` | UI-4 补丁 | 删除 |
| `ui5d-first-screen-polish.css` | UI-5 补丁 | 删除 |
| `ui-v2-readout.css` | P0-B 增量补丁 | 删除（被 v4 取代） |
| `ui-v2-workspace.css` | P1 增量补丁 | 删除（被 v4 取代） |
| `companion.css` / `premium.css` / `runtime-viz.css` / `spatial-runtime.css` / `execution-channel.css` / `styles.css` | 旧视图样式 | 保留文件（供 companion/execution 旧视图用，v4 不加载） |

### 2.2 旧 JS（表现/交互层）
| 文件 | 角色 | v4 处置 |
|---|---|---|
| `main-orb.js` / `main-cognitive.js` | 旧首页启动器 | **不再被 v4 加载** |
| `app.js` | 旧 UI 总启动 + SSE 消费 + 全部旧面板 | **v4 不加载**（避免双 UI） |
| `panel-manager.js` / `overlay-manager.js` / `overlay-runtime.js` | 旧面板/覆盖层管理 | v4 不加载（v4 自带 overlay） |
| `command-dock.js` | 旧指令坞；`sendText`→`zz:command` | **复用其链路**：v4 直接 `dispatchEvent(new CustomEvent('zz:command',{detail:{text}}))`，不加载该文件本体 |
| `galaxy-experience.js` / `galaxy-runtime.js` / `solar-system.js` | 3D 太阳系 | **删除视觉依赖**（solar-system.js 删；galaxy-state.js 数据层保留） |
| `capability-matrix.js` / `capability-registry.js` / `capabilities-view.js` / `capability-exposure.js` | 能力矩阵/面板 | v4 不加载（非 Dashboard 心智） |
| `hud-context.js` / `hud-ring.js` | HUD 光环 | v4 不加载 |
| `os-shell` 相关渲染（`avatar-renderer.js` 旧首页部分等） | 旧首页结构 | v4 不加载旧首页 |

### 2.3 旧 HTML
| 文件 | 角色 | v4 处置 |
|---|---|---|
| `index.html` | 旧 os-shell 首页（含 P0-B/P1 注入） | **旧入口保留文件**；Phase 7 将其改为指向 `/v4/`（可逆重定向），不删除 |
| `companion.html` / `mobile-app.html` / `selfcheck.html` / `weather-modal-preview.html` | 其他视图 | 保留，v4 无关 |

---

## 3. 必须保留的核心能力代码（严禁删除/修改）

| 类别 | 文件/端点 | 说明 |
|---|---|---|
| Agent Runtime | `ai_core/**`、`goals.py`、`memory.py`、`knowledge*.py`、`intent-gateway.py` | 不改逻辑 |
| 统一状态核心 | `app-state.js`（文件保留；v4 不加载其消费链，仅后端 AppState 仍为真源） | 不新增第二状态系统 |
| 事件总线 | `eventbus.py` + `zz-events.js`（事件单一来源） | 不修改协议、不新增事件 |
| Goal/Memory/Knowledge | 后端系统 + `/api/goals` `/api/memories` `/api/knowledge` | 不改逻辑 |
| SSE | `/api/stream` + `sse-manager.js` | v4 复用该单例 |
| 工具系统 | `tool*`、`computer-action.js`、`permission-guard.py` | 不改 |
| 状态呈现 | `avatar-state.js`（8态调色板，纯函数） | v4 复用其 META |
| 数据层 | `galaxy-state.js`（关系投影数据层） | 保留；v4 World Understanding 复用其数据语义（经 `/api/memories/graph`） |

---

## 4. 旧 UI 删除清单（Phase 7 执行，本阶段不执行）

**视觉依赖（从旧 `index.html` 的 `<head>` 移除链接，文件保留于磁盘）：**
1. `ui4b-explore-transition.css`、`ui4b-first-screen.css`、`ui4c-unified-home.css`、`ui4c-visible-upgrade.css`、`ui4d-home-experience.css`、`ui5d-first-screen-polish.css`
2. `ui-v2-readout.css`、`ui-v2-workspace.css`（P0-B/P1 增量，已被 v4 取代）
3. 旧 `index.html` 中 `.os-shell` 整段 DOM（保留于文件，仅由 v4 入口接管首屏）

**不再加载的脚本（旧 `index.html` 中的 `<script>`）：**
4. `main-orb.js` / `main-cognitive.js` / `app.js`（v4 自行引导，仅加载 sse-manager/zz-events/avatar-state + v4 组件）

**入口切换（Phase 7）：**
5. 旧 `index.html` 改为极简重定向到 `/v4/`（可逆：删除重定向即恢复）。

**保留不动：** `ui2.css`（token 来源，不加载其布局）、`companion.*`、`*.html` 其他视图、所有后端代码。

---

## 5. 审计结论

- 旧 UI 的"三心智"（Home/Galaxy/Chat）与五代 CSS 叠加是**结构性病灶**；v4 采用**全新独立层** `v4/`，彻底不继承旧布局。
- 所有真实能力（3 API + SSE + 8态 + 事件契约 + 关系数据）均可被 v4 **零复制复用**。
- 红线确认：未改 Agent Runtime / EventBus / AppState / 不新增事件 / 不新增状态系统 / 未删核心能力代码。

---

*Phase 0 完成。下一步 Phase 1：v4 新 UI 骨架。*
