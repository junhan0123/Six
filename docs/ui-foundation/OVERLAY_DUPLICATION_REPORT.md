# Overlay Duplication Report — Xiao6 Frontend

> **Sprint**: Overlay System Preflight Audit v1.0 · **Mode**: Audit → Report → STOP
> **Date**: 2026-08-05 · **依据**: 源码静态扫描 + DESIGN.md §7 Do's/Don'ts

---

## 0. 审计纪律声明

纯只读。仅记录重复事实与位置，不做任何合并/重构（属后续 Implementation Sprint）。

---

## 1. 重复总览

| 重复族 | 实例数 | 严重度 | 说明 |
|--------|--------|--------|------|
| **Modal/Panel/Dialog 通用范式** | **~15** | 🔴 P0 | 「遮罩 div + 居中/固定面板 + open/close + ESC + 点击外部」被逐模块重写 |
| **Toast** | **3** | 🟠 P1 | app.js 全局 / error-boundary.js / mobile-app.js 各一套 |
| **Dropdown/Menu** | 2（主窗 more-dropdown + companion quick-menu） | 🟡 P2 | 跨窗口，可后续统一为 `zz-menu` |
| **Tooltip** | 0（缺位） | ⚪ 缺口 | 无组件，仅原生 title |
| **Notification** | 0（缺位） | ⚪ 缺口 | 折叠进 toast / companion 气泡 |

---

## 2. Modal/Panel 重复族（核心重复，~15 套）

每套均含：① 独立 overlay 容器（CSS）② 面板容器（CSS）③ JS open/close ④ 独立 ESC 监听 ⑤ 独立点击外部关闭。清单：

| 实例 | 文件 | overlay 类 | panel 类 | z-index |
|------|------|-----------|----------|---------|
| 通用 Modal | app.js + styles.css | `.modal-mask`(L2500) | `.modal-card`(L2508) | 9000 |
| 设置 | settings.js | `.settings-overlay`(L2741) | `.settings-panel`(L2745) | 80/81 |
| 系统提示 | sysprompt.js | `.sysprompt-overlay`(L2803) | `.sysprompt-panel`(L2807) | 82/83 |
| 能力 | capabilities-view.js | `.cap-overlay`(L2820) | `.cap-panel`(L2824) | 82/83 |
| 记忆网络 | memory-panel.js | (body mem-mode) | `.mem-panel`(L2363) | 60 |
| 记忆查询 | memory-query.js | (body memq-mode) | `.memq-panel`(L3597) | 61 |
| 热点 | hotspot.js | (body hotspot-mode) | `.hotspot-panel`(L618) | — |
| 文档 | doc.js | (动态) | `.doc*` | — |
| 地图 | map.js | (动态) | `.map*` | — |
| 简报 | review.js | (动态) | `.review*` | — |
| 任务 | tasks.js | (动态) | `.tasks*` | — |
| 视频 | video.js | (动态) | `.video*` | — |
| 天气 | weather.js | (动态 modal) | — | — |
| 引导 | onboarding.js | `.onb-overlay` | `.onb-card` | — |
| 组件面板 | app.js(zzPanel) | (无遮罩) | `.zz-panel`(L3122) | 95 |
| 终端 | terminal-stream.js | `.term-panel`(L2039) | 同 | 60 |
| 天气卡 | (styles.css L2109) | `.wc-panel` | 同 | 60 |
| 聊天抽屉 | app.js(chatArea) | — | `.os-chat-drawer` | 25 |

> 其中 `settings/sysprompt/cap` 三者**结构几乎 identical**（overlay + panel + `.show`+`.open` + ESC + 点击外部），仅内容不同——是最高价值的合并候选。

---

## 3. Toast 重复（3 套）

| 实例 | 位置 | 特征 | 调用方 |
|------|------|------|--------|
| **全局 toast** | `app.js:306` `toast(msg)` | 操作 `#toast`，`.show` + 3200ms 自动隐藏；挂 `window.toast` 全局 | 全项目 30+ 处（`window.toast(...)`） |
| **error-boundary toast** | `error-boundary.js:6` `toast(msg, kind)` | 独立本地定义，kind 区分样式 | error-boundary.js 内部 |
| **mobile toast** | `mobile-app.js:15` `toast(msg)` | 独立本地定义，`show/hide(.hidden)` | mobile-app.js 内部 |

> 三套**视觉与行为不一致**（时长 3200ms vs 2600ms？位置/样式各异），且 error-boundary / mobile 未复用全局 `window.toast`。违背 DESIGN.md §7 Do's #2「单一职责 / 统一组件」。

---

## 4. Dropdown / Menu 重复

- 主窗：`.more-dropdown`（app.js:2140-2206）+ `#moreDropdown`（index.html:277）。
- companion 窗口：`.quick-menu`（companion.js:340-560，右键 contextmenu 触发）。
- 二者交互范式相同（toggle + 外部点击关闭 + 选项列表），但**跨窗口、跨代码库**，当前不可直接合并；建议 Implementation 阶段统一为 `zz-menu` 原语，companion 经 IPC 复用主窗组件（延续 Phase 8「Companion 零 fetch、复用既有系统」纪律）。

---

## 5. 与 DESIGN.md 纪律的冲突

DESIGN.md §7 明确：
- **Do's #2**：新组件一律 `zz-` 前缀。
- **Don'ts #1**：禁止在 `styles.css` 新增组件 class。
- **Don'ts #2**：禁止为同一组件建第二套 class（如 `.zz-panel` 与 `.my-panel` 并存）。

现实：
- 15+ 套非 `zz-` 前缀的 overlay 组件类散落 `styles.css`（违反 Don'ts #1/#2）。
- 同一「Modal/Panel」语义存在 ~15 套 class（违反 Don'ts #2）。
- DESIGN.md §9 预留 `zz-dialog`/`zz-dropdown`/`zz-menu`/`zz-tabs`/`zz-tooltip`/`zz-modal-card`/`zz-overlay` 为「仅命名，勿实现」——本 Preflight 正是为后续**落地这些 zz- 原语、收口 15 套遗留**做准备。

---

## 6. 重复量化结论

1. **最高价值合并**：`settings` / `sysprompt` / `cap` 三件套（结构同构）→ 单一 `zz-dialog` 原语。
2. **次高价值**：`term-panel` / `wc-panel` / `mem-panel` / `memq-panel` / `doc` / `map` / `review` / `tasks` / `video` / `hotspot` → 统一 `zz-panel`/`zz-overlay` 原语（zz-panel 已存在，可扩展为通用）。
3. **Toast**：3→1，路由 error-boundary/mobile 到 `window.toast`。
4. **Dropdown/Menu**：主窗 `.more-dropdown` + companion `.quick-menu` → `zz-menu`。
5. **缺口（非重复，但需补）**：`zz-tooltip`、`zz-notification` 当前不存在，属 DESIGN 预留未实现项。

→ 进入 [OVERLAY_MIGRATION_PLAN.md](./OVERLAY_MIGRATION_PLAN.md) 评估迁移风险与顺序。
