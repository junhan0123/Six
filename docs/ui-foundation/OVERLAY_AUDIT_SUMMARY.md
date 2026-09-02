# Overlay Audit Summary — Xiao6 Frontend

> **Sprint**: Overlay System Preflight Audit v1.0
> **Mode**: Audit → Report → STOP（纯只读，禁改代码/CSS/JS/HTML）
> **Date**: 2026-08-05
> **身份**: Senior Frontend Architect + Design System Auditor
> **依据**: `xiao6-ui/DESIGN.md` §4.7 / §6.1 / §6.3 / §6.4 / §7 / §9；`xiao6-ui/` 源码静态扫描
> **纪律红线**: 禁止修改任何代码 / CSS / JS / HTML；禁止新增功能 / 优化；只允许读取、分析、记录。

---

## 0. 本文件定位

本总览汇总 5 份子报告的结论，作为 Overlay System Preflight 的**收口与闸门**。所有数据均来自静态扫描，未触碰任何源码。

| 子报告 | 文件 | 职责 |
|--------|------|------|
| A 数量清点 | `OVERLAY_INVENTORY_REPORT.md` | 10 类 Overlay 的 CSS/JS/HTML/事件绑定数量 |
| B 架构分析 | `OVERLAY_ARCHITECTURE_AUDIT.md` | z-index / 显隐 / 生命周期 / ESC / 焦点 / 遮罩 |
| C 重复分析 | `OVERLAY_DUPLICATION_REPORT.md` | Modal/Panel/Toast/Dropdown 重复族量化 |
| D 迁移规划 | `OVERLAY_MIGRATION_PLAN.md` | P0/P1/P2 风险分级 + 实施顺序 |
| E 设计对齐 | `OVERLAY_DESIGN_ALIGNMENT.md` | DESIGN.md 目标态 vs 现实差距矩阵 |

> ⚠️ **报告冲突提示（待 Review 厘清）**：`OVERLAY_COMPONENT_REPORT.md`（更早的 Component Sprint 产物）称「管理器单一 = overlay-runtime.js」。该结论是基于 DESIGN.md §4.7 的描述，**未实际检索代码**。本 Preflight 的 A/B 报告经逐文件 grep 证实：overlay-runtime.js 是纯数据层、无生产消费者；实际存在 ~20 个分散管理器。**以代码证据为准**，COMPONENT_REPORT 的「单一管理器」结论应被标记为过时/待修订，避免误导 Implementation Sprint。

---

## 1. 当前状态（Current State）

- **Overlay 管理器 ~20 个**，无中央协调器；「Modal/Panel/Dialog」同一范式被**重复实现 ~15 次**，各带独立 overlay div + 面板 + open/close + ESC + 点击外部关闭。
- **Toast 3 套**并存（app.js 全局 `window.toast` / error-boundary.js / mobile-app.js），视觉与行为不一致。
- **overlay-runtime.js 是纯数据层**（6 类 OVERLAY_TYPES + 5 态 OVERLAY_LIFECYCLE），仅 `getModel()`/`subscribe()`，**生产代码零消费者**（仅测试引用）。DESIGN.md §4.7 的「管理器单一」描述的是**目标态**，非现状。
- **z-index 令牌形同虚设**：`--z-*` 六档（base1/rail5/popover30/modal60/toast82/companion9999）几乎未被 overlay 引用，实际用硬编码字面量，出现 **9000 / 200 / 95 倒挂**（modal-mask=9000 脱离尺度；more-dropdown=200 压过一切面板；zz-panel=95 压过设置/系统提示）。
- **焦点管理系统性缺失**：焦点陷阱 / `inert` / 焦点归还 **全项目 0 处**；仅 command-palette / companion 打开时聚焦输入框。违背 WCAG 2.4.3 / 2.1.2 与 DESIGN §7 Do's #4。
- **Tooltip / Notification 完全缺位**：前者仅原生 `title` 属性；后者折叠进 toast / companion 气泡。二者均为 DESIGN §9 预留的 `zz-tooltip` / `zz-notification` 空壳，属**缺口非偏离**。
- **16+ 去中心化 ESC 监听器**，部分未带开启守卫（app.js:756、settings.js:128）。
- **5 种显隐范式并存**（`.show` / `.open` / `hidden` / body-class / `aria-hidden`+状态类），无统一原语。
- **遮罩模糊未令牌化**：DESIGN §6.4 定义 `--blur-glass:26px`，实际用 `blur(6px)`/`blur(10px)` 字面量；zz-panel 甚至无遮罩 div（与 modal 语义冲突）。

---

## 2. 主要问题（Top Problems）

| # | 问题 | 严重度 | 根源 |
|---|------|--------|------|
| P1 | ~20 个分散管理器，Modal/Panel ~15 套重复 | 🔴 P0 | 无统一原语，逐模块重写 |
| P2 | z-index 令牌失效 + 9000/200/95 倒挂 | 🔴 P0 | 硬编码字面量，令牌未引用 |
| P3 | 焦点陷阱 / inert / 焦点归还全为 0 | 🔴 P0 | DESIGN 目标态未落地 |
| P4 | Toast 3 套重复且行为不一致 | 🟠 P1 | 未复用 `window.toast` |
| P5 | 16+ ESC 监听去中心化、部分未守卫 | 🟠 P1 | 无中央分发器 |
| P6 | 5 种显隐范式并存无原语 | 🟠 P1 | 历史累积 |
| P7 | 遮罩 blur 未令牌化、zz-panel 无遮罩 | 🟡 P2 | 视觉令牌未路由 |
| P8 | Tooltip/Notification 缺位（zz- 空壳） | ⚪ 缺口 | DESIGN §9 预留未实现 |
| P9 | overlay-runtime 数据层无消费者 | ⚪ 缺口 | 渲染层冻结未建 |

---

## 3. 推荐实施顺序（Recommended Sequence）

进入 Overlay Implementation Sprint 后，按 `OVERLAY_MIGRATION_PLAN.md §5` 执行：

```
[1] P0-2  Z-index 令牌化（先立六档尺度，零行为变化）
  ↓
[2] P0-1  建 zz-overlay / zz-dialog 原语（统一遮罩+backdrop+ESC+点击外部+焦点陷阱+inert）
  ↓
[3] P0-3  中央 OverlayManager + ESC/Focus 分发器（替换 16+ 监听）
  ↓
[4] P1-1  Toast 3→1 路由（error-boundary / mobile 复用 window.toast）
  ↓
[5] 逐模块路由（settings→sysprompt→cap→mem*→hotspot→doc→map→review→tasks→video→weather→onb→zz→term/wc→chat）
  ↓
[6] P1-3 / P2-1 / P2-2 收尾（遮罩令牌 / zz-menu / 补 zz-tooltip·zz-notification）
```

每步须：静态审计脚本（参考 Phase 2 `C:/tmp/zz_audit.py`）+ Electron GUI 验收（参考 Phase 8.6 puppeteer CDP 方案）+ 回滚预案。

---

## 4. 禁止事项（Red Lines — 重申）

- ⛔ 本 Preflight 不执行任何代码改动（仅读、分析、记录）。
- ⛔ 不新增功能 / 页面 / 架构 / Runtime / EventBus / 通信协议。
- ⛔ 不擅自改变 overlay 视觉方向（尺寸/配色/圆角/blur 偏差）——视觉变更须单独评审。
- ⛔ 不经统一原语直接「机械改 z-index 数字」——必须先立令牌尺度（[1] 优先）。
- ⛔ companion 窗口不得自建 overlay 系统，须经 IPC 复用主窗 `zz-*` 原语（延续 Phase 8 纪律）。
- ⛔ 不得机械合并类名（沿用 Phase 1/2 红线，留 Review 门控）；迁移用「单值来源 + 别名兼容层」，零 HTML/JS 视觉改动优先。

---

## 5. STOP 闸门声明

> **本 Preflight 审计已全部完成（6 份报告落盘）。立即 STOP，等待人工 Review。**
>
> - 未经批准：**不得修改任何 Overlay 代码/CSS/JS/HTML**。
> - 未经批准：**不得进入 Overlay Implementation Sprint**。
> - 后续动作：由人工 Review 本总览 + 5 份子报告 → 批准实施顺序 → 启动 Overlay Implementation Sprint（从 [1] z-index 令牌化起）。
> - 待 Review 厘清项：① `OVERLAY_COMPONENT_REPORT.md` 的「单一管理器」结论过时（以本审计代码证据为准）；② DESIGN.md §4.7「管理器单一」应标注为「目标态」而非现状描述，避免后续误解。

---

## 6. 交付清单（Deliverables）

```
docs/ui-foundation/
├── OVERLAY_INVENTORY_REPORT.md      ✅ A 数量清点
├── OVERLAY_ARCHITECTURE_AUDIT.md    ✅ B 架构分析
├── OVERLAY_DUPLICATION_REPORT.md    ✅ C 重复分析
├── OVERLAY_MIGRATION_PLAN.md        ✅ D 迁移规划
├── OVERLAY_DESIGN_ALIGNMENT.md      ✅ E 设计对齐
└── OVERLAY_AUDIT_SUMMARY.md         ✅ 本文件（总览 + STOP）
```

审计模式：Audit → Report → STOP。✅ 已完成，待 Review。
