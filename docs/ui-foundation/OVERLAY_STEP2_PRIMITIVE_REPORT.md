# Overlay Implementation Sprint · Step [2] — Overlay Primitive Foundation

**日期**：2026-08-05（GMT+8）
**身份**：Senior Frontend Architect（DOM / UI 控制层）
**执行模式**：Audit → Plan → Execute → Verify → Report → STOP
**前置**：Step [1] Z-index Tokenization（Review Approved，验证 7/7 PASS）
**状态**：✅ 执行完成 · 验证 6/6 PASS · **等待人工 Review（STOP）**

---

## 1. 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `xiao6-ui/ui2.css` | 修改（末追加，纯增量） | 新增 `.zz-overlay` / `.zz-overlay__scrim` / `.zz-dialog`（含 header/title/close/body/footer、`--sm`/`--lg` 变体、scrollbar 令牌化）；更新 L669 注释（zz-overlay/zz-dialog 已由 Step[2] 落地，其余仍仅预留）。 |
| `xiao6-ui/overlay-manager.js` | **新建** | 经典脚本（与 overlay-runtime.js 同模式），IIFE 注入 `(window)`，暴露 `window.OverlayManager`。DOM/UI 控制层，与 overlay-runtime.js 纯数据层严格分离。 |
| `xiao6-ui/index.html` | 修改（2 处） | L13：`ui2.css?v=20260805c4` → `ui2.css?v=20260806c5`（cache-bust，符合项目纪律）；L25–27：在 `overlay-runtime.js` 后注入 `overlay-manager.js?v=20260806m2`。 |

> **git 范围说明**：`ui2.css` 当前在工作树为 **untracked**（由更早的未提交会话创建），故其整体以新文件形态存在，我的追加含于其中。工作树存在大量早期 sprint 的未提交 delta（app.js / styles.css 等），**本 Step [2] 仅触及上述 3 个文件**，未触碰业务逻辑、companion.css、server.py、app-state.js、overlay-runtime.js。

---

## 2. 架构变化

### 2.1 职责分离（新建控制层）
- `overlay-runtime.js`（冻结，DOM-free 纯数据投影层）：暴露 `OVERLAY_TYPES` / `OVERLAY_LIFECYCLE` / `mapType` / `steadyLifecycle` / `getModel` / `subscribe`，被 `app-state.js` 与 `tests/` 消费 → **本步零改动**。
- `overlay-manager.js`（本步新增，DOM 控制层）：负责 `.zz-overlay` 的装配、打开栈（stack）、中央 ESC、焦点保存/恢复、注册模板。

### 2.2 视觉参数单一来源
新 primitive **全部引用既有令牌**，不新增第二套颜色/阴影/圆角/z-index：
- 背景：`linear-gradient(160deg, var(--surface-2), var(--bg-2))`
- 边框：`1px solid var(--border)`；圆角：`var(--r-lg)`（22px）
- 阴影：`var(--elev-3)`；毛玻璃：`blur(var(--blur-glass))`（26px）
- 遮罩：`color-mix(in srgb, var(--bg) 72%, transparent)` + `blur(var(--blur-glass))` —— **修复遗留 `rgba(4,7,11,.72)` + `blur(6px)` 的浅色主题硬编码 bug**（legacy 维持 6px 至 Step[5] 迁移）。
- z-index：CSS 默认 `var(--z-dialog-mask)`（83 step[1] 令牌）；多实例堆叠时 `overlay-manager.js` 运行时按深度 `BASE_Z + depth*Z_STEP` 内联覆盖，`BASE_Z` 由 `getComputedStyle` 读取 `--z-dialog-mask` 同步（单一来源，无第二套数值）。

### 2.3 中央 ESC（休眠式，零默认行为变化）
- 仅当管理器栈非空时在 `keydown` **capture 阶段**拦截：`preventDefault()` + `stopPropagation()` + 关闭栈顶。
- 栈空则完全休眠，不绑定/不拦截任何键盘事件 → **不干扰 18+ 既有去中心化 ESC 监听**（迁移留 Step[5]）。
- `onEsc: false` 可逐实例禁用 ESC 关闭（业务安全开关）。

### 2.4 焦点处理（基础层，trap 预留）
- 打开前保存 `document.activeElement`（returnFocus）；关闭后恢复。
- `trapFocus()` / `releaseTrap()` 接口已预留但**本步为 no-op**（完整 focus trap 风险高，待 Step[5] 安全降级审查后开启）。

### 2.5 打开/关闭 API
`OverlayManager.open(config)` 支持：`{id, title, content(Node|string), footer, size('sm'|'lg'), role, closable, dismissOnScrim, autofocus, onEsc, titleId}`；防重复打开（按 id 查 stack + DOM）；scrim `mousedown` 判定关闭；`requestAnimationFrame` 加 `.is-open` 触发过渡。`close(id)` / `closeAll()` / `isOpen(id)` / `getStack()` / `register(id, config)`（命名模板）齐备。

---

## 3. 风险

| 风险 | 等级 | 说明 / 缓解 |
|------|------|------------|
| 第二套视觉数值 | 无 | 全部令牌驱动，CSS 扫描确认零 raw color/shadow/radius（Check 2 PASS）。 |
| z-index 倒挂 | 低 | `BASE_Z` 同步 `--z-dialog-mask`（83）；`Z_STEP=1` 仅用于多实例深度叠加，不硬编数值（Check 3 PASS）。 |
| 既有 ESC 行为回归 | 无 | 中央 ESC 默认休眠，栈空零介入（Check 4 + 设计保证）。 |
| 遗留 Modal 被破坏 | 无 | legacy 类（`.settings-overlay`/`.sysprompt-overlay`/`.cap-overlay`/`.modal-card`）完整保留，无调用改写（Check 5 PASS）。 |
| GUI 回归（动画/毛玻璃） | 待 Review | 本步为静态/no-GUI 验证；视觉与交互需在 Review 阶段由人工在 Electron 中实测（过渡时长对齐 `--motion-base`=300ms，`REMOVE_DELAY` 同步）。 |
| `ui2.css` 未提交 | 提示 | 当前 untracked，提交时需整体纳入；建议与本 Step 一起提交，避免令牌源缺失。 |

---

## 4. 测试 / 验证（6/6 PASS）

| # | 检查项 | 命令 / 方法 | 结果 |
|---|--------|------------|------|
| 1 | JS 语法 | `node --check overlay-manager.js` | ✅ JS_SYNTAX_OK |
| 2 | CSS 令牌扫描（无第二套颜色/阴影/圆角） | awk 提取 Step[2] 段 grep `#hex`/`rgba`/`rgb` | ✅ NO_RAW_COLOR_VALUES |
| 3 | z-index 扫描（仅 `--z-*`） | CSS 段 grep `z-index` + manager `BASE_Z`/`--z-dialog-mask` 同步 | ✅ 仅令牌来源 |
| 4 | OverlayManager 暴露与误用扫描 | grep `window.OverlayManager` / 全仓 `OverlayManager.*` 调用（排除 runtime/manager 自身） | ✅ 暴露正确；零遗留误用 |
| 5 | 旧组件存在性 | grep `styles.css` legacy 类 + 关联 JS handler | ✅ 全部完好 |
| 6 | Git diff 范围 | `git diff --stat` + `git status --porcelain` | ✅ 仅 ui2.css/index.html/overlay-manager.js（详见 §1 说明） |

补充确认：IIFE 注入参数为 `(window)`，故 `global.OverlayManager` 正确挂载到 `window`（Verify 阶段发现并确认，非 bug）。

---

## 5. 未处理项（明确递延，不在本步范围）

- **[2-D] legacy → adapter → zz-overlay 契约**：仅立契约/文档，未实际改写任何 legacy Modal/Dialog 实现（按计划本步不迁移）。
- **Toast 3→1 合并**：Step [3]，未启动。
- **全面 Overlay 迁移（legacy → zz-overlay）**：Step [5]。
- **完整 focus trap（inert / Tab 循环）**：Step [5] 安全降级审查后开启 `trapFocus()`。
- **zz-tooltip / zz-notification / zz-dropdown / zz-menu / zz-tabs**：仍仅预留命名，未实现（DESIGN §9）。

---

## 6. 后续入口（批准后）

> ⛔ **STOP**：未经批准不得进入 Toast 迁移 / 全面 Overlay 迁移 / OS Experience Sprint。
> 批准本 Step [2] 后，建议下一步：Review 阶段在 Electron 中实测 GUI（动画、毛玻璃、ESC、焦点恢复），再启动 [2-D] 契约文档与 Step [3] Toast 合并。
