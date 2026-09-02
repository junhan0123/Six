# Overlay Implementation Sprint · Step [3] — Toast System Unification

**报告日期**：2026-08-05
**身份**：Senior Frontend Architect（Overlay 子系统）
**执行模式**：Audit → Plan → Execute → Verify → Report → STOP
**状态**：✅ 完成 · **STOP — 等待 Review**（未经批准不得进入 Dialog 全迁移 / Focus Trap / OS Experience Sprint）

---

## 0. 一句话结论

将小6前端原本 **3 套相互独立的 Toast**（主 `window.toast` / 错误兜底 `ZZErrorToast` / 移动端 `toast`）收敛为 **统一 `.zz-toast` Primitive**，全部经 `OverlayManager.toast()` 渲染；旧调用签名 100% 兼容，未改动任何业务逻辑 / 业务调用 / Runtime / Memory / EventBus，未删除旧 Toast，未扩展 Overlay 范围。

---

## 1. 权限边界（红线）

| 维度 | 状态 |
|------|------|
| ✅ CSS 修改（ui2.css 追加 `.zz-toast` 表现层） | 已做 |
| ✅ Overlay JS 修改（overlay-manager.js 扩展 Toast 子系统） | 已做 |
| ✅ Toast Adapter（legacy ↓ adapter ↓ OverlayManager ↓ zz-toast） | 已做 |
| ✅ Legacy 路由（旧接口签名兼容） | 已做 |
| ❌ 修改业务逻辑 / 业务调用 | 未触碰 |
| ❌ 修改 Runtime / Memory / EventBus | 未触碰 |
| ❌ 删除旧 Toast | 保留（仅加路由守卫 + 回退分支） |
| ❌ 扩展 Overlay 范围（移动端全量迁移等） | 移动端仅加 **compat-guard**，行为不变 |

---

## 2. 审计盘点（Audit 产出）

| # | 系统 | 来源 | 调用方式 | 原表现 | 收敛后 |
|---|------|------|----------|--------|--------|
| A | 主 Toast | `app.js:306` `function toast(msg)` → `window.toast`（L2447） | `toast(msg)` / `window.toast(msg)`（30+ 处消费者：memory.js / screen.js / app.js 内部） | 操作 `#toast` DOM，`.show` + 3200ms | → `OverlayManager.toast({type:'info', message, legacyDismissMs:3200})` |
| B | 错误兜底 | `error-boundary.js:6` `function toast(msg,kind)` → `window.ZZErrorToast`（L34） | `ZZErrorToast(msg[,kind])`；捕获 `error`/`unhandledrejection`，网络错 30s 去抖 | 动态建 `#zz-error-toast`，fixed bottom:24px z-index:99999，warn=琥珀/其他=红，6000ms | → `OverlayManager.toast({type: kind==='warn'?'warning':'error', message, legacyDismissMs:6000})` |
| C | 移动端 | `mobile-app.js:15` `function toast(msg)` | `toast(msg)`（移动壳内 banner 等） | `$("toast")` + show/hide(`.hidden`)，2600ms | **compat-guard**：`OverlayManager` 在场则路由，否则保留原 show/hide（移动壳无 overlay-manager → **零行为变化**） |

**明确排除（非本步范畴）**：
- `insight-panel.js` 的 `addToast`（`.proactive-toast` + `pt-*`）—— 属 Notification 缺口（ui2.css L666 明文 `.pt-exec → 保留（主动通知专属）`），Step[3] 不收敛，避免与本 Sprint 既有 Component 决策冲突及超范围。
- `styles.css` / `mobile-app.html` / `selfcheck.html` 内各自的 `.toast` 旧样式——保留未动；新 `.zz-toast` 为独立命名空间，不与 `#toast` 选择器冲突。

---

## 3. 交付物清单（已落地）

| 文件 | 改动 | 性质 |
|------|------|------|
| `xiao6-ui/ui2.css` | 末尾追加 `.zz-toast` / `.zz-toast__*` / `#zzToastRoot` / `@keyframes zz-spin`（约 +130 行，`??` 未跟踪文件内的增量） | 纯表现层，全部令牌驱动 |
| `xiao6-ui/overlay-manager.js` | 扩展 Toast 子系统：`toast()` / `dismissToast()` / `setToastProgress()` + 内部 `getToastRoot/buildToastEl/findToast` + `TOAST_*` 常量（约 +190 行，`??` 未跟踪） | Overlay JS（允许） |
| `xiao6-ui/app.js` | `toast(msg)` 函数体改为路由到 `OverlayManager.toast()`，保留 `#toast` 回退分支 | Legacy 路由（允许） |
| `xiao6-ui/error-boundary.js` | `toast(msg,kind)` 顶部加 `OverlayManager` 路由守卫，保留原 DOM 回退 | Legacy 路由（允许） |
| `xiao6-ui/mobile-app.js` | `toast(msg)` 加 compat-guard（在场路由 / 缺席回退） | Legacy 兼容守卫 |
| `xiao6-ui/index.html` | `ui2.css?v=20260806c5→c6`、`overlay-manager.js?v=20260806m2→m3` 缓存版本 bump | 版本刷新 |
| `xiao6-ui/mobile-app.html` | `mobile-app.js` 加 `?v=20260806t1` 版本 bump | 版本刷新 |

---

## 4. 设计决策（统一规范）

### 4.1 分类映射（success / warning / error / info / loading / progress）
统一 6 类变体，左缘 3px 强调色取自语义令牌：
- `success → --ok` · `warning → --warn` · `error → --danger` · `info/loading/progress → --accent`
- `loading` 用旋转 SVG 圆环（`zz-spin` 0.9s linear）；`progress` 额外渲染 `.zz-toast__progress` 轨道，`setProgress(p)` 动态填充宽度。

### 4.2 位置 / 堆叠 / 层级
- 容器 `#zzToastRoot`：`fixed` 底部居中（`bottom: var(--space-3)`，`left:50%` + `translateX(-50%)`）；`z-index: var(--z-toast)`（= `--z-overlay` = 60，单一令牌来源）；`pointer-events:none`（穿透页面），子项 `.zz-toast` 自开 `pointer-events:auto`。
- 堆叠：`flex-direction: column`，新条 append 至底部（贴近视口底），旧条上移；`MAX_TOASTS=4`，超限自动 dismiss 最旧。
- **层级提升延后**：`--z-toast` 当前 = 60（与 overlay 同层）。审计发现旧 error-boundary 用 z-index 99999（高于一切）。统一值 60 是令牌单一来源；**Toast 提层（使其浮于 Dialog 之上）留待 Step[5] 经 GUI 验收后处理**，本步不擅自改层级语义。

### 4.3 生命周期 / 关闭
- 自动消失时长优先级：`dismissMs` > `legacyDismissMs` > 按 type 默认值（`info/success 3200` · `warning 5000` · `error 6000` · `loading/progress 0` 即常驻）。
- 关闭行为：右上角 `.zz-toast__close`（24px，复用 `.zz-dialog__close` 图标语言）→ `dismissToast(id)`；可选 `action` 按钮点击后执行 `onClick` 并自动关闭；`loading/progress` 默认 `closable` 仍可用（允许手动关闭常驻条）。
- 动画：进入 rAF 加 `.is-in`（opacity/translateY/scale 过渡，`--motion-base`+`--ease-premium`）；退出移除 `.is-in`（`TOAST_EXIT_MS=260` 与过渡对齐后移除 DOM）；`prefers-reduced-motion` 时零延迟直删。

### 4.4 令牌纪律（零第二套）
全部视觉参数取自既有令牌：`--surface-2 / --bg-2 / --border / --text / --text-dim / --muted / --ok / --warn / --danger / --accent / --radius-md / --radius-sm / --elev-2 / --blur-glass / --space-1 / --space-2 / --space-3 / --fs-13 / --fs-12 / --motion-base / --motion-fast / --ease-premium / --ease-soft / --z-toast`。**未新增任何颜色 / 阴影 / 圆角 / z-index 数值**。

---

## 5. 验证结果（5 项，全部 PASS）

| # | 检查项 | 方法 | 结果 |
|---|--------|------|------|
| 1 | JS 语法 | `node --check` 对 4 个脚本 | ✅ overlay-manager.js / app.js / error-boundary.js / mobile-app.js 全部 OK |
| 2 | CSS 令牌引用 | 核对新增 `.zz-toast` 块全部 `var(--*)` 均在 `:root`（L54-108）定义 | ✅ 无未定义令牌；无第二套硬编码数值 |
| 3 | Toast 调用扫描 | `grep -rn "toast("` 全仓 | ✅ 仅 3 套（A/B/C）+ 明确排除 proactive；无遗漏第 4 套 |
| 4 | Legacy 调用兼容 | 比对签名：`toast(msg)` / `toast(msg,kind)` / `toast(msg)` | ✅ 签名保留，内部消费者（memory.js / screen.js 等）零改动即获统一渲染 |
| 5 | Git diff 范围 | `git diff --stat` + 逐文件精确 diff | ✅ 仅 7 个目标文件；app.js/index.html 的大体量 diff 为 **既有未提交工作树状态**（改名/重排/格式化），非本步引入 |

> **范围说明**：工作树存在大量既有未提交变更（几十个 `R` 改名、`??` 未跟踪文件）。Step[3] 净贡献严格限定于上表 7 文件；`ui2.css` 与 `overlay-manager.js` 本身为未跟踪文件（Step[2] 创建未提交），本步仅追加内容。

---

## 6. 风险与遗留（明确标注）

1. **`--z-toast` 层级 = 60（与 overlay 同层）**：旧 error-boundary 曾用 99999。统一后错误 toast 不再浮于一切之上。**已知、有意、留 Step[5] 处理**（需 GUI 验收提层）。
2. **移动端为 no-op 守卫**：`mobile-app.html` 未加载 `overlay-manager.js`/`ui2.css`，故移动端 `toast()` 走原 show/hide 分支，**视觉/行为完全不变**。代码路径已就绪，待后续若移动壳接入 Overlay 体系时自动生效（不超范围）。
3. **`#toast` 旧元素保留**：`index.html:401` 的 `<div class="toast" id="toast">` 不再被 app.js 切换（改为统一渲染），但保留以兼容潜在直接引用；无副作用。
4. **零 GUI 验收**：本步为静态/语法/扫描验证，未启动 Electron 实机点检（符合 Sprint 静态纪律）。视觉回归待 Review 后 GUI 验收。

---

## 7. 下一步（待 Review 批准）

- ⛔ 未经批准 **不** 进入：Dialog 全迁移 / Focus Trap / OS Experience Sprint。
- 建议批准后：Step[4] 或按 MIGRATION_PLAN 推进剩余 Overlay 模块路由（Modal/Panel 收口）；Step[5] 处理 `--z-toast` 提层 + 焦点相关收尾；最后统一 `zz-tooltip` / `zz-notification`（含 proactive 迁移）。

---

*本报告与 Step[2] 同属 Overlay Implementation Sprint；遵循 Single Source Rule，Design Token 权威 = `ui2.css :root`。*
