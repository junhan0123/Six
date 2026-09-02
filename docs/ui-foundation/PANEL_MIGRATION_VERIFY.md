# Panel Migration Verify — Xiao6 Component System Sprint v1.0 · Phase 1 (Task F)

> **Sprint**: Component System Implementation Sprint v1.0 — Phase 1
> **Task**: F — Panel Migration Verify（低风险 Panel，静态验证）
> **日期**: 2026-08-05
> **验证方式**: 静态（本环境无法启动 Electron GUI；按 Phase 1 限制）

---

## 1. 验证范围

Phase 1 Panel「迁移」实质为 **DESIGN.md↔CSS 一致性修复**（blur 值对齐）+ 令牌化核实。无 CSS/HTML/JS 面板定义改动、无面板类重命名、无视觉变化。验证聚焦「改动正确性 + 无副作用」。

---

## 2. 验证清单（逐项）

| # | 验证项 | 方法 | 结果 |
|---|--------|------|------|
| V1 | DESIGN.md §4.2 glass-panel blur 已对齐实值 | Grep `DESIGN.md:125` | ✅ `blur(28px)`（匹配 premium.css:29 字面 28px） |
| V2 | DESIGN.md §6.4 blur 令牌说明已自洽 | Grep `DESIGN.md:210` | ✅ `--blur-glass:26px`（.os-panel 令牌）+ `.glass-panel` 字面 28px，2px 偏差记录 |
| V3 | `.glass-panel` 令牌覆盖未被破坏 | Grep `ui2.css:608` | ✅ `background: linear-gradient(160deg,var(--surface-2),var(--bg-2))` 在位 |
| V4 | `.os-panel` 令牌定义未被破坏 | Grep `ui2.css:302` | ✅ 全令牌（surface/border/radius-lg/blur-glass/space-3）在位 |
| V5 | `--line-strong`=`--border` 别名跨主题成立 | Grep `ui2.css`（11 处：`--line-strong:var(--border)` @63/95/109/123/138/153/166/179/192/205/220） | ✅ 全主题别名一致 → border 等价无误 |
| V6 | 无 CSS/HTML/JS 面板定义改动 | 本会话 Panel 动作仅 2 次 Edit（均 DESIGN.md） | ✅ 无其它文件触及 |
| V7 | 无面板类被删除/重命名 | 对比审计基线（D-§4，10 主族） | ✅ 全部类族仍存在 |
| V8 | 未扩大至 Feature/Modal/Overlay | 范围核对 | ✅ 仅 `.glass-panel`/`.os-panel` + DESIGN.md，未碰 P4/P5/P6 |

---

## 3. 改动集（精确）

| 文件 | 行 | 变更 |
|------|----|------|
| `DESIGN.md` | §4.2:125 | `blur(26px)` → `blur(28px)`（对齐 `.glass-panel` 实值） |
| `DESIGN.md` | §6.4:210 | 澄清 `--blur-glass`(26) 为 `.os-panel` 令牌；`.glass-panel` 字面 28px，2px 偏差记录 |

**无 CSS/HTML/JS 改动。** 符合「小步迁移、可回滚、可验证」。

---

## 4. 风险评估

| 维度 | 评估 |
|------|------|
| 视觉变化 | 无（仅规范文本修正；实渲模糊度不变） |
| 行为变化 | 无（文档-only） |
| 逻辑变化 | 无 |
| 回滚 | 简单：DESIGN.md 两行改回原值 |
| 回归面 | 极小：仅规范文档；面板 CSS 零改动 |

---

## 5. 限制声明

- 本环境**无法启动 Electron GUI**，故无法做像素级/主题切换/响应式回归。V1–V8 均为静态验证。
- 完整 GUI 回归建议在人工 Review 阶段于 Electron 中执行（Task G 同此限制）。

---

## 6. 结论

Panel 系统 Phase 1 实施**静态验证全部通过**：DESIGN.md↔CSS 一致性已修复（验收③）、令牌路由完好、无副作用、可回滚。高/中风险合并项未执行，符合纪律红线。

→ 进入 Task G（Regression Verification）。
