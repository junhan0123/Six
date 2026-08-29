# Low Risk Migration Verify — Phase 2 Task D 报告

> **阶段**：Component System Sprint v1.0 · Phase 2（Input System）
> **执行身份**：DesignMdArchitect（Diana）
> **前置**：Task A（审计）、Task B（对齐+令牌路由）、Task C（焦点核验）
> **日期**：2026-08-05
> **方法**：静态代码核验（本环境无 Electron GUI，无像素回归）。比对迁移前后计算值、确认高风险类未被改动。

---

## 1. 迁移范围回顾（Task B 已执行）

| 组 | 类 | 文件 | 是否迁移 |
|----|----|------|---------|
| A 低风险 | `.settings-input` / `.settings-select` / `.settings-textarea` / `.sc-input` / `.wx-city-input`×2 / `.mem-search` / `.memq-search` / `.memq-input` / `.settings-check input` / `.onb-input` | styles.css / premium.css | ✅ 已令牌路由 |
| B 高风险 | `#input` / `.hs-chat-input textarea` / `.cp-input` / `.wc-cd-input` / `.os-dock input` / `.cmd-bubble-input` | styles.css / ui2.css / companion.css | ⛔ 刻意不迁移（只记录） |

---

## 2. 低风险迁移值等价核验

每个路由均为「裸值 → 同名令牌」或「遗留变量 → 已别名 NEW 变量」，计算值逐字节一致：

| 类 | 路由前 | 路由后 | 等价性 |
|----|--------|--------|--------|
| `.settings-input` | `bg rgba(5,7,10,.6)` | `var(--input-bg)` = `rgba(5,7,10,.6)` | ✅ |
| `.settings-input` | `border var(--line)` | `var(--input-border)` = `var(--border)` | ✅ |
| `.settings-input` | `color var(--txt)` | `var(--text)`（别名） | ✅ |
| `.settings-input:focus` | `border-color var(--cyan)` | `var(--input-focus-border)` = `var(--accent)`（别名） | ✅ |
| `.settings-textarea` | `bg rgba(255,255,255,.05)` | `var(--input-bg-soft)` | ✅ |
| `.sc-input` | `border var(--line)` → `var(--input-border)`；`color var(--txt)`→`var(--text)`；focus `var(--cyan)`→`var(--accent)` | ✅（bg `.55` 刻意保留） |
| `.wx-city-input`×2 | `bg var(--void)`→`var(--bg)`；`border var(--line)`→`var(--input-border)`；`color var(--txt)`→`var(--text)`；focus `var(--cyan)`→`var(--accent)` | ✅ |
| `.mem-search` | `bg rgba(0,0,0,.35)`→`var(--input-bg-deep)`；`border var(--line)`→`var(--input-border)`；`color var(--txt)`→`var(--text)` | ✅ |
| `.memq-search` | `bg rgba(255,255,255,.05)`→`var(--input-bg-soft)`；`border var(--line)`→`var(--input-border)` | ✅ |
| `.memq-input` | `color var(--txt)`→`var(--text)`；`placeholder var(--dim2)`→`var(--input-placeholder)` | ✅ |
| `.settings-check input` | `accent-color var(--cyan)`→`var(--accent)` | ✅ |
| `.onb-input` | `border var(--line-strong)`→`var(--input-border)`；focus `var(--cyan)`→`var(--input-focus-border)` | ✅ |

> 残留 `var(--cyan)` 引用（styles.css 行 182/427/486/2460/2484/2496/2529/2567/2586/2786/2900/3028）均为**按钮/开关类**（tts-toggle / sc-choice / mic-btn / mem-btn / modal-close / hs-tts / theme-opt / zz-task-close / settings-save-btn），不在 Input 迁移范围，正确保留。

---

## 3. 高风险类未改动核验（证据）

| 类 | 当前实值（grep 证据） | 状态 |
|----|----------------------|------|
| `#input` | `styles.css:490` `outline:0; background:transparent; color:var(--txt); ::placeholder var(--dim2)` | ⛔ 未动 |
| `.hs-chat-input textarea` | `styles.css:770` `bg rgba(255,255,255,.05); border var(--line); ::placeholder var(--dim)` | ⛔ 未动 |
| `.cp-input` | `styles.css:2154` `bg transparent; border 0`; `:2155 ::placeholder var(--dim2)` | ⛔ 未动 |
| `.wc-cd-input` | `styles.css:2136` `bg var(--void); border var(--line)` | ⛔ 未动 |
| `.os-dock input` | `ui2.css:455` `bg transparent; border 0; color var(--text)`（令牌天花板，本就合规） | ⛔ 未动 |
| `.cmd-bubble-input` | `companion.css:429` `bg rgba(0,0,0,.25); border var(--companion-chrome-border)` | ⛔ 未动（Companion 隔离层） |

> 注：仓库存在 `styles.css.tmp` / `companion.css.tmp` 等备份文件；本 Sprint 仅编辑正式文件，未触碰任何 `.tmp`。

---

## 4. 令牌与缓存核验

- **令牌定义**：`ui2.css:85-96` 12 个 `--input-*` 令牌已落地（additive，`:root` 单点）。
- **缓存炸弹**：`index.html` 三处 `?v=` 已 bump — `styles.css?s2→s3`、`premium.css?p2→p3`、`ui2.css?c2→c3`，确保浏览器拉取新文件。
- **语法**：所有编辑为等价文本替换 + 新增块，无 CSS 语法破坏（`:root` 闭合 `}` 保留，令牌块在闭合前插入）。

---

## 5. 可回滚性

- 全部改动为可逆文本替换 + 缓存 bump；`git diff` 可逐行审视。
- 无新增文件、无删除、无 JS / HTML 结构改动（仅 `index.html` 三处 `?v=` 版本号）。

---

## 6. 结论

- ✅ 8 类低风险输入完成令牌路由，计算值逐字节等价（零视觉变化）。
- ✅ 6 类高风险输入确认未改动（聊天核心 / Command Palette / 指令坞 / Companion）。
- ✅ 令牌单点定义 + 缓存 bump 到位，可回滚。
- ✅ 符合 Phase 2 红线：零视觉/行为变化、不新增功能/架构、可回滚、静态验证。

> **状态**：Task D 完成（零新增代码改动，仅核验）。下一步 → Task E（Regression Verification）。
