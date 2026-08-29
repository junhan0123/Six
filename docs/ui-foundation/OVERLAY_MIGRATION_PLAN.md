# Overlay Migration Plan — Xiao6 Frontend

> **Sprint**: Overlay System Preflight Audit v1.0 · **Mode**: Audit → Report → STOP（本报告仅规划，**不执行**）
> **Date**: 2026-08-05 · **目的**: 为后续 Overlay Implementation Sprint 提供风险分级与执行顺序

---

## 0. 纪律边界（沿用 Phase 1/2 红线）

- **禁止新增功能 / 业务逻辑 / Runtime / EventBus / 通信协议**。
- **迁移策略沿用「单值来源 + 别名兼容层」**：以 `ui2.css` 为令牌天花板，旧类经令牌别名收敛（零 HTML/JS 视觉改动优先）。
- **不可突破 DESIGN.md §7 Don'ts**：不改既有视觉方向（尺寸/配色/圆角），仅经令牌路由。
- 本 Preflight 产出**规划**，待人工 Review 批准后，方进入 Implementation Sprint。

---

## 1. 风险分级定义

| 等级 | 含义 | 回归面 | 策略 |
|------|------|--------|------|
| **P0** | 高 | 多文件、多模块、行为耦合深 | 必须先建统一原语 + 单测 + GUI 验收，再逐模块路由 |
| **P1** | 中 | 局部、接口清晰 | 可直接路由，需回归调用方 |
| **P2** | 低 | 增量、加性 | 可随 Implementation 顺带收口 |

---

## 2. P0 — 高风险（必须先做原语，再迁移）

### P0-1 统一 Overlay/Dialog 原语（`zz-overlay` + `zz-dialog`）
- **涉及文件**：settings.js / sysprompt.js / capabilities-view.js / memory.js / memory-panel.js / memory-query.js / hotspot.js / doc.js / map.js / review.js / tasks.js / video.js / weather.js / onboarding.js / app.js(chatArea,zzPanel) + styles.css/premium.css 对应类。
- **影响范围**：~15 套面板/模态的开关、ESC、点击外部、动画、内容挂载。
- **迁移建议**：
  1. 在 `ui2.css` 落地 `--z-modal`/`--z-toast`/`--z-popover` 令牌并让 overlay 引用（先解决 Inventory §1.2 的 9000/200/95 倒挂）。
  2. 建立 `zz-overlay`（遮罩+backdrop 令牌）与 `zz-dialog`（内容层）原语，含统一 open/close/ESC/点击外部/焦点陷阱/inert。
  3. 各模块改为调用原语 API，**保留各自内容渲染函数**（不改视觉/行为，仅换壳）。
  4. 必须 GUI 验收（Electron 真实窗口，参考 Phase 8.6 puppeteer CDP 方案）。

### P0-2 Z-index 重新分级（令牌化）
- **涉及**：styles.css 全部 overlay 字面 z-index（9000/200/95/90/85/86/83/82/81/80/61/60/56/55）。
- **影响**：任何堆叠顺序变化都可能引发「下拉盖不住面板」「面板盖住模态」等视觉回归。
- **迁移建议**：以 `--z-*` 令牌重建 6 档尺度（base/rail/popover/modal/toast/companion），按 Inventory §1.2 映射逐档替换，逐屏回归。

### P0-3 中央 ESC / 焦点分发器
- **涉及**：16+ 全局 `keydown` Escape 监听（见 Architecture §4）。
- **影响**：移除分散监听、引入中央 dispatcher + focus trap + inert，会改变键盘可达性基线。
- **迁移建议**：单例 `OverlayManager` 维护「当前栈顶 overlay」，`keydown` 仅注册一次；open 时 `inert` 背景 + 焦点陷阱 + 记录 opener 焦点，close 时 restore。需 WCAG AA 回归。

---

## 3. P1 — 中风险（接口清晰，直接路由）

### P1-1 Toast 统一（3→1）
- **涉及**：app.js:306（全局 `window.toast`）/ error-boundary.js:6 / mobile-app.js:15。
- **影响**：error-boundary、mobile-app 改用 `window.toast`；mobile-app 为独立页面上下文，需确认 `window.toast` 可用或提供轻量桥。
- **迁移建议**：error-boundary 直接 import/call 全局 toast；mobile-app 评估是否共用同一 `#toast` 元素或保持本地但统一样式令牌。

### P1-2 显隐范式归一
- **涉及**：5 种范式（`.show`/`.open`/`hidden`/body-class/`aria-hidden`）。
- **影响**：新原语落地后，旧模块开关调用改为原语方法；`hidden` 属性与 body-class 范式逐步淘汰。
- **迁移建议**：随 P0-1 一并替换，不单独成 Sprint。

### P1-3 遮罩模糊令牌化
- **涉及**：`blur(6px)`/`blur(10px)`/`blur(28px)` 字面量 vs `--blur-glass:26px`。
- **影响**：视觉微调（blur 偏差），属「视觉变化」红线敏感区。
- **迁移建议**：仅在 P0-1 建立 `zz-overlay` 时统一引用 `--blur-glass`；遗留偏差如实保留或单独提视觉变更评审，**不擅自改值**。

---

## 4. P2 — 低风险（增量 / 加性，可顺带）

### P2-1 Dropdown/Menu 统一为 `zz-menu`
- 主窗 `.more-dropdown` + companion `.quick-menu` → 跨窗口复用（companion 经 IPC，延续 Phase 8 纪律）。
- 风险低（加性组件），但跨窗口协调需谨慎。

### P2-2 补齐 `zz-tooltip` / `zz-notification`
- 当前 Tooltip/Notification **缺位**（Inventory §1）。DESIGN.md §9 将其列为「仅命名，勿实现」——属**预留缺口**，非重复。
- 建议：Implementation Sprint 末尾作为加性组件补入，**不强制本 Sprint**。

### P2-3 overlay-runtime.js 数据层落地
- 纯数据模型（6 类/5 态）当前无渲染消费者（Inventory §3）。
- 建议：未来 `zz-overlay` 渲染器可选消费 `OverlayRuntime.getModel()` 驱动「领域节点→信息层」投影（Phase 6 Order 7 原意），但**非本 Sprint 必须**。

---

## 5. 推荐实施顺序

```
Sprint 入口（已在此 Preflight STOP）
  ↓ 人工 Review 批准
[1] P0-2  Z-index 令牌化（先立尺度，零行为变化）
  ↓
[2] P0-1  建 zz-overlay / zz-dialog 原语（含统一 ESC/点击外部/焦点陷阱/inert）
  ↓
[3] P0-3  中央 OverlayManager + ESC/Focus 分发器（替换 16+ 监听）
  ↓
[4] P1-1  Toast 3→1 路由
  ↓
[5] 逐模块路由（settings→sysprompt→cap→mem*→hotspot→doc→map→review→tasks→video→weather→onb→zz→term/wc→chat）
  ↓
[6] P1-3 / P2-1 / P2-2 收尾（遮罩令牌 / zz-menu / tooltip·notification 补齐）
```

> 每步须：静态审计脚本（参考 Phase 2 `C:/tmp/zz_audit.py`）+ Electron GUI 验收（参考 Phase 8.6）+ 回滚预案。

---

## 6. 禁止事项（红线重申）

- ⛔ 不在本 Preflight 执行任何代码改动（本报告仅规划）。
- ⛔ 不新增功能/页面/架构/Runtime/EventBus。
- ⛔ 不擅自改变 overlay 视觉方向（尺寸/配色/圆角/blur 偏差），视觉变更须单独评审。
- ⛔ 不经过统一原语直接「机械改 z-index 数字」——必须先立令牌尺度。
- ⛔ companion 窗口不得自建 overlay 系统，须经 IPC 复用主窗 `zz-*` 原语（延续 Phase 8 纪律）。

→ 进入 [OVERLAY_DESIGN_ALIGNMENT.md](./OVERLAY_DESIGN_ALIGNMENT.md) 对照 DESIGN.md 差距。
