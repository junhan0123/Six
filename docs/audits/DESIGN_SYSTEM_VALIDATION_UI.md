# 小6 Phase 6 — Design System 设计验证（UI Designer 视角）

> 验证人：UI Designer（像素君）· 日期：2026-08-03
> 性质：对 `PROJECT_AUDIT_FINAL.md` 的**设计系统 / 可达性补充验证**，**只读审计**，不修改任何冻结文档、不进入新 Phase。
> 目的：为最终 Code Review 提供 UI / WCAG 视角的独立核对。

---

## 1. 令牌单一来源纪律 — ✅ 确认成立

| 层 | 文件:位置 | 令牌数 | 重复 | 结论 |
|----|-----------|--------|------|------|
| 基础层（唯一来源） | `styles.css:6-23` `:root` | 15 | 0 | `--void --void2 --panel --panel-solid --glass --line --line-strong --cyan --teal --amber --red --txt --dim --dim2 --glow` |
| 增量层 | `premium.css:10-28` `:root` | 12 | 0 | `--ease-*/--motion-*/--elev-*/--r-*`，全部**引用基础层**（`var(--panel)`/`var(--line)`/`var(--cyan)`…），无平行重定义 |
| 跨文件 | — | — | 0 | 基础层与增量层**零命名冲突** |

- 主题变体（`body[data-theme="light"/dark-*]`）与逐元素别名（`--qc-c` 定义在 `.quick-chip` 局部作用域、`--bc` 在热点模块局部）均为**合法令牌重定义 / 局部别名**，非平行全局体系。
- **驳斥"浅色系白底白字"假设**：`body[data-theme="light"]` 在 `styles.css:2950` 已正确重定义 `--txt:#0f172a; --dim:#475569; --dim2:#64748b`，文本令牌随主题切换，单一来源纪律成立。

---

## 2. 可达性（WCAG 2.1 AA）实测 — dev 审计缺失项

> dev 审计 §5/§6 声称"WCAG AA"但**未计算实际对比度**。以下为实测结果（算法：WCAG 2.1 相对亮度对比度）。

### 2.1 已达标项 ✅

| 项 | 结果 |
|----|------|
| 焦点可见性 | `premium.css:64-74` `:focus-visible` → `outline:2px solid var(--cyan)` + `box-shadow 4px` 光环，键盘可达性 AA ✓ |
| 减弱动效 | `premium.css:129-145` 双重关闭：`@media (prefers-reduced-motion:reduce)` **与** `body.reduced-motion` 类，并隐藏 `.premium-bg` ✓（ exemplary） |
| 深色正文 | `--txt #E6EDF3` on `--void` = **17.07:1**；`--dim #8B98A9` on void = **6.88:1** ✓（均 ≥4.5） |
| 深色强调色 | `--cyan` 11.16:1 / `--teal` 10.83:1 / `--amber` 11.12:1 / `--red` 6.17:1 ✓ |
| 浅色正文 | `--txt #0f172a` on `#f0f4f8` = **16.15:1**；`--dim #475569` = **6.86:1** ✓ |

### 2.2 发现 A（真实缺陷，深色主题）— `--dim2` 小字对比度不足

- 当前值 `--dim2:#5C6B7A` 在 `#05070A` 上 = **3.69:1**（仅为"大字号"级，非 AA 正文级 4.5:1）。
- 该令牌被用在**小字号正文**：
  - `.brand-sub` 10px（`styles.css:98`）
  - `.rail-label` 11px（`styles.css:112`）
  - `.conv-del` 15px（`styles.css:123`）
- **影响**：上述位置在深色主题下不满足 WCAG AA 4.5:1。
- **建议修复（视觉层令牌值微调，非架构改动）**：将 `--dim2` 提亮至 `#6B7B8C`（4.65:1）或 `#728395`（5.18:1）；或更省事——这三处改用 `--dim`（已 6.88:1）。

### 2.3 发现 B（真实缺陷，浅色主题）— 强调色未为浅底重定义

- 浅色主题重定义了文本令牌，但**未重定义强调色** `--cyan/--teal`（仍为 `#22D3EE`/`#2DD4BF`）。
- 当强调色**作为文字**出现在浅底（如 `.hud-tag{color:var(--cyan)}` on `var(--panel)` 浅白）：
  - `--cyan #22D3EE` on `#f2f6fa` = **1.66:1** ❌
  - `--teal #2DD4BF` on `#f0f4f8` = **1.68:1** ❌
- **影响**：浅色主题下强调文字远低于 AA（即便大字号也仅 3:1）。
- **建议修复**：浅色主题追加 `--cyan:#0e7490`（4.85:1）/ `--teal:#0f766e`（4.95:1）或 `--teal:#115e59`（6.86:1）。

---

## 3. 令牌引用一致性 — ✅

- `premium.css` 所有组件类仅消费基础令牌（`var(--panel)/var(--line)/var(--cyan)/var(--red)/var(--dim)`…），无平行定义。
- `color-mix(in srgb, var(--red) …)` / `var(--qc-c)` 等均为基于既有令牌的派生，符合单一来源。

---

## 4. 结论与给 Code Review 的建议

1. **令牌单一来源 + 运行时一致性**：确认成立，与 `PROJECT_AUDIT_FINAL.md §5` 一致；主题/局部别名均合法。
2. **可达性**：深色/浅色**正文**、焦点、减弱动效均达标；但发现 **2 处 AA 未达标**（均为**视觉层令牌值微调**，非架构/运行时问题）：
   - A. 深色 `--dim2` 小字 3.69:1 → 提亮至 `#6B7B8C` 或改用 `--dim`。
   - B. 浅色强调文字（cyan/teal）≈1.6:1 → 浅色主题追加深色强调变体。
3. **纪律处理**：因 Order 8 明确"禁止重新设计颜色 / 禁止新增 Token"，本报告**仅标注缺陷，不改动冻结文档**。建议将 A、B 两项作为 **Code Review 通过后的 Design System 小修**（属 Phase 后期 hotfix 或 P4 精修，不触发新 Phase）。
4. **红线合规**：银河本体 Magic Color（`0x5599bb`/`0x88aaff`）刻意不纳入 Design Token，作为宪法保护的品牌资产保留——正确。

**一句话**：Phase 6 运行时与 Design System 令牌架构**一致、单一来源、合规**；唯一实质短板是 2 处 WCAG AA 对比度未达标（视觉令牌微调即可修复），建议 Code Review 一并登记为后续可达性修复项。
