# Overlay Design-System Alignment — Xiao6 Frontend

> **Sprint**: Overlay System Preflight Audit v1.0 · **Mode**: Audit → Report → STOP
> **Date**: 2026-08-05 · **依据**: `xiao6-ui/DESIGN.md` 全文 vs 源码静态扫描

---

## 0. 审计纪律声明

纯只读。对照 DESIGN.md（唯一设计真相来源）与现有实现，列出**差距**。不做任何修改。

---

## 1. DESIGN.md 对 Overlay 的既有陈述

| 章节 | 原文要点 | 现实对照 |
|------|----------|----------|
| §4.7 Modals/Dialogs/Overlay | 「**管理器单一**：`overlay-runtime.js`；容器 `.settings-overlay`/`.sysprompt-overlay`/`.cap-overlay`/`.onb-overlay`。内容层 `.modal-card`。」 | ❌ **管理器并不单一**——实际 ~20 个独立 JS 管理器；`overlay-runtime.js` 是纯数据层，**无生产消费者**（仅测试引用）。 |
| §4.7 | 「详见 `OVERLAY_COMPONENT_REPORT.md`（仅分析，未重构）。」 | ⚠️ 该文件若存在，为前次组件分析；本 Preflight 可视为其更新版（路径 `docs/ui-foundation/`）。 |
| §6.3 Z-index Scale | `--z-base:1; --z-rail:5; --z-popover:30; --z-modal:60; --z-toast:82; --z-companion:9999` | ❌ 实际 overlay 几乎全部硬编码字面量，**令牌未被引用**；`modal-mask=9000`、`zz-panel=95`、`more-dropdown=200` 倒挂（见 Architecture §1）。 |
| §6.4 Backdrop | `--blur-glass:26px`（.os-panel 等）；遮罩层半透明 `--bg` + blur。 | ⚠️ 实际遮罩用 `blur(6px)`/`blur(10px)` 字面量（settings/sysprompt/cap overlay），与令牌偏差远超容差。 |
| §6.1 Shadow | `--elev-1/2/3`（含顶部 1px 内高光）；「通知卡片用 `0 12px 30px rgba(0,0,0,.35)`」。 | ⚠️ 各 overlay 阴影自定义（`.modal-card::before/::after`、`.zz-panel-card::before`），未统一路由到 `--elev-*`。 |
| §7 Do's #2 | 新组件一律 `zz-` 前缀；落入 `ui2.css` 令牌天花板。 | ❌ 15+ 套非 `zz-` overlay 类散落 `styles.css`。 |
| §7 Don'ts #1 | 禁止在 `styles.css` 新增组件 class。 | ❌ 现状即大量 overlay class 定义在 styles.css（历史累积，待收口）。 |
| §7 Don'ts #2 | 禁止为同一组件建第二套 class。 | ❌ 同一 Modal/Panel 语义 ~15 套 class。 |
| §7 Do's #4 | 永远保留 `:focus-visible` 全局环，保证键盘可达（WCAG AA）。 | ❌ overlay 打开后**无焦点陷阱/inert**，Tab 可逃出（Architecture §6）。 |
| §9.1 Quick Reference | 缺失组件（**仅命名，勿实现**）：`zz-dialog` `zz-dropdown` `zz-menu` `zz-tabs` `zz-tooltip` `zz-modal-card` `zz-overlay`。 | ⚠️ 这些 zz- 原语**均未实现**；当前 overlay 全为遗留非 zz- 类。本 Preflight 即为其落地前置。 |
| §9.1 | 主题切换：`body[data-theme]`；accent 变体。 | ✅ overlay 沿用 `--surface`/`--border`/`--accent` 令牌（颜色维度基本对齐）。 |

---

## 2. 差距矩阵（DESIGN vs 现实）

| 维度 | DESIGN 期望 | 现实 | 对齐度 |
|------|-----------|------|--------|
| 管理器数量 | 单一（overlay-runtime） | ~20 个分散 | ❌ |
| overlay-runtime 落地 | 数据层→渲染消费者 | 无消费者（仅测试） | ❌ |
| Z-index | 令牌 6 档 | 硬编码 + 9000/200/95 倒挂 | ❌ |
| Backdrop blur | `--blur-glass:26px` | 6/10px 字面量 | ⚠️ |
| Shadow | `--elev-*` | 自定义 ::before/::after | ⚠️ |
| 组件前缀 | `zz-` | 非 zz- 遗留类 | ❌ |
| 焦点管理 | `:focus-visible` + 键盘可达 | 无 trap/inert | ❌ |
| Tooltip/Notification | `zz-tooltip`/`zz-notification` 预留命名 | 完全缺位 | ⚪ 缺口（非偏离） |
| 颜色令牌 | `--surface`/`--border`/`--accent` | overlay 基本引用 | ✅ |

---

## 3. 关键冲突点

1. **§4.7「管理器单一」与现实严重不符**——DESIGN 描述的是**目标态**（Order 7 架构冻结时的意图），但实现停留在 Order 7 之前的碎片化状态。`overlay-runtime.js` 作为「单一管理器」仅完成了数据层，渲染层始终未建（架构冻结），导致 ~20 个 legacy 管理器并存。
2. **§6.3 z-index 令牌是「死令牌」**——定义后未被任何 overlay 引用，反被 9000 等字面量架空。Implementation 第一要务是**让令牌活起来**。
3. **§9 预留的 7 个 zz- overlay 原语全是空壳**——本 Preflight 的核心价值，就是为首批量落地（zz-overlay/zz-dialog/zz-menu，及补缺 zz-tooltip/zz-notification）扫清障碍。
4. **§7 Don'ts 与现状自相矛盾**——DESIGN 已禁止「styles.css 新增类 / 第二套 class」，但现状正是其禁止态；说明 DESIGN 是**收敛目标**，而非现状描述。审计应以此为目标态校准。

---

## 4. 对齐建议（输入 Implementation Sprint）

1. **令牌活化**：`--z-*` 六档 + `--blur-glass` 必须被 overlay 引用（先解决 9000/200/95 倒挂）。
2. **原语落地**：按 §9 预留命名实现 `zz-overlay`（遮罩+backdrop+ESC+点击外部+焦点陷阱+inert）与 `zz-dialog`（内容层），`zz-menu` 统一下拉/菜单，`zz-tooltip`/`zz-notification` 补缺。
3. **legacy 路由**：15+ 套遗留 overlay 经「单值来源 + 别名兼容层」路由到 zz- 原语，**零视觉变化**（沿用 Phase 1/2 策略）。
4. **a11y 补强**：所有 overlay 打开即陷阱 + 背景 inert + 关闭 restore，达成 §7 Do's #4 的 WCAG AA 基线。
5. **overlay-runtime 衔接**：可选让 `zz-overlay` 渲染器消费 `OverlayRuntime.getModel()`，实现「领域节点→信息层」投影（Order 7 原意闭环），但非必须。

---

## 5. 结论

DESIGN.md 在 Overlay 维度**描述的是目标态，而非现状**。现实是：管理器碎片化（~20）、z-index 令牌失效、焦点管理缺失、zz- 原语全空。本 Preflight 已量化全部差距，可作为 Implementation Sprint 的**验收基线**——未来每落地一项 zz- 原语 + 路由一批 legacy，即向 DESIGN 目标态收敛一步。

→ 进入 [OVERLAY_AUDIT_SUMMARY.md](./OVERLAY_AUDIT_SUMMARY.md) 总览与 STOP 声明。
