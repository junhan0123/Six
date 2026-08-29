# Regression Verification — Xiao6 Component System Sprint v1.0 · Phase 1 (Task G)

> **Sprint**: Component System Implementation Sprint v1.0 — Phase 1
> **Task**: G — Regression Verification（6 界面回归）
> **日期**: 2026-08-05
> **验证方式**: 静态（本环境无法启动 Electron GUI；按 Phase 1 限制）
> **维度**: Button / Panel / 主题 / 响应式 / Focus

---

## 1. 回归矩阵

| 界面 | 使用的 Button 类 | 使用的 Panel 类 | 状态 | 风险 |
|------|------------------|----------------|------|------|
| **首页** (`index.html`+`app.js`) | `.btn-new` / `-open-btn`×5 / `.mic-btn`×4 / `.send-btn` / `.tts-stop-btn` / `.mem-btn`×9 / `.settings-save-btn`×~18 / `.onb-next` | `.glass-panel` / `.settings-panel` / `.zz-panel`(档案浮层) / `.os-panel`(Workspace) | ✅ 全部类在基线内，未改 | 🟢 |
| **Galaxy** (`#solarCanvas`/`#universeView`) | （无 Button/Panel CSS，纯 Three.js 画布） | （无） | ✅ 未触碰 Galaxy/Three.js | 🟢 |
| **聊天** (history/input/approvals) | `.send-btn` / `.mic-btn` / `.speak-btn`(朗读) / `.appr-btn`(批准/拒绝) | `.zz-panel`(档案/智能体卡) / `.glass-panel` | ✅ 基线完整 | 🟢 |
| **Workspace** (`.os-panel`/`.glass-panel` 容器) | （容器内按钮均属上述类） | `.os-panel` / `.glass-panel`（令牌驱动） | ✅ 令牌化完好 | 🟢 |
| **设置** (`.settings-panel`) | `.settings-save-btn`(+`.danger`)/`.settings-row-btn` | `.settings-panel` / `.zz-toggle`(=`.settings-switch` 别名) | ✅ `.settings-save-btn` 未合并（递延，完好）；Toggle 已别名统一 | 🟢 |
| **Command Palette** (`command-palette.js`/`command-dock.js`) | `.os-dock-btn`(Dock 5 实例) / palette 自有类 | （palette 自有容器） | ✅ G3 保留，未改 | 🟢 |

---

## 2. 横切验证（5 维度）

| 维度 | 验证 | 结果 |
|------|------|------|
| **Button** | `.btn` 四变体（ui2.css:591-601）+ `.btn:disabled`(:604) 在位；G2 令牌路由（styles.css:87 / premium.css:224）完好；34 类族无删除 | ✅ |
| **Panel** | `.glass-panel`(ui2.css:608) / `.os-panel`(ui2.css:302) 令牌化完好；`.zz-panel`(styles.css:3122) 完好；DESIGN.md↔CSS 一致 | ✅ |
| **主题** | `--line-strong:var(--border)` 跨全主题成立（ui2.css 11 处：63/95/109/123/138/153/166/179/192/205/220）→ border 等价；9 套主题令牌未动 | ✅ |
| **响应式** | 本会话未编辑任何 `@media` / 断点规则（仅 ui2.css `.btn:disabled` + DESIGN.md 文本 + index.html 缓存版本） | ✅ 未回归 |
| **Focus** | 全局 `:focus-visible`（ui2.css:547-551）+ `button:focus-visible`（premium.css:46）完好；`.btn` 继承 | ✅ |

---

## 3. 改动影响面汇总

| 文件 | 改动 | 影响面 |
|------|------|--------|
| `ui2.css` | +`.btn:disabled`（:602-604） | 仅 disabled 态按钮（当前无 `.btn` 处于该态）→ 零实渲影响 |
| `index.html` | `ui2.css?v=` c1→c2 | 缓存失效，无视觉变化 |
| `DESIGN.md` | §4.2:125 + §6.4:210 blur 对齐 | 规范文本，零渲染影响 |

**其余 199KB `styles.css`、其余 CSS/HTML/JS：零改动。**

---

## 4. 风险与回滚

- **风险等级**：🟢 低。所有改动为 additive CSS 规则 + 规范文本 + 缓存 bump。
- **回滚**：`ui2.css` 删 :602-604 + `index.html` 版本回 c1 + `DESIGN.md` 两行复原。
- **回归结论**：6 界面 × 5 维度静态验证**全部通过**，无视觉/行为/主题/响应式/Focus 回归。

---

## 5. 限制声明

- 本环境**无法启动 Electron GUI**，故无法做像素级/交互级回归。上述为静态验证（Grep + 复读 + 会话动作核对）。
- 完整 GUI 回归建议在人工 Review 阶段于 Electron 中执行（含主题切换、焦点环、disabled 实机态、响应式断点）。

---

## 6. 结论

Phase 1 全部 6 界面回归**静态验证通过**：Button/Panel 基线完整、令牌路由完好、主题/响应式/Focus 无回归。符合纪律红线与验收标准。

→ 进入 Final（COMPONENT_PHASE1_SUMMARY.md + STOP）。
