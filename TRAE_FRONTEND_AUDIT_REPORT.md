# TRAE Frontend Audit Report — Xiao6 v1.0.0

> 审计日期：2026-08-28 ｜ 方式：全盘 Glob/Read + git log --all --name-only + git fsck --dangling 逐 blob 特征扫描
> 约束遵守：未修改、未恢复、未删除任何文件。

## 1. 判定：**PARTIAL**（前端资产丢失，但可恢复）

当前工作区与 git HEAD 均为 0 前端文件，server 引用链断裂（运行时 UI 不可用）；但多处备份/悬空对象保存了前端资产，可拼合恢复。

## 2. 工作区与 HEAD 现状（缺失证据）

- `git ls-tree -r HEAD | grep '\.(js|html|css)$'` → **0 个**（189 个被追踪文件中无任何前端资产）。
- 工作区 `G:\xiao6\xiao6-ui` 根目录：仅 `_p39a_verify.js`（验证脚本）；无 index.html / styles.css / app.js。
- 服务端引用断裂：
  - `server.py:925` 路由 `/` 与 `/index.html` → `_serve_file("index.html")`；`server.py:757-764` 文件缺失时返回 `404 {"error":"missing index.html"}`。
  - 曾被 `start-xiao6.bat` 引用的 `/xiao6-space/index.html`：`xiao6-space/` 目录不存在；且 `start-xiao6.bat` 本身已被删除。
- Electron 入口断裂：`xiao6-ui/package.json` 已删除，`launcher/electron-bin/electron.exe` 无应用 asar（仅 `resources/default_app.asar` Electron 默认欢迎页）；`launcher/launcher_config.json` 缺失 → `launcher/start.ps1:21` 读取 `$cfg.pid_files.electron` 直接失败。

## 3. 可恢复资产清单（按 UI 世代）

| 世代 | 位置 | 内容 | 完整度 |
|---|---|---|---|
| Galaxy/Avatar 世代（2026-08-17 归档） | `G:\xiao6\_ui_archive\2026-08-17\root-legacy\` | **80 个 .js**（app.js、app-state.js、galaxy-runtime/state/experience.js、avatar-*.js、memory*.js、capability-*.js、sse-manager.js、event-bridge.js 等）+ styles.css、ui2/ui4b/ui4c/ui5d、spatial-runtime.css、premium.css 等多份 css + mobile-app.html、weather-modal-preview.html | JS/CSS 全套，**缺主 index.html** |
| Advanced Workspace 世代（2026-08-18 快照） | `G:\xiao6\xiao6-ui\_audit\snapshot_20260818_101404_4p1d_pre / _103427_4p1e_pre / _104636_4p1f_pre\` | `index.html`（"小6 · Advanced Workspace"）+ `zz-workspace.js` + `zz-workspace.css` ×3 递进快照 | **三件套完整**（单一文件体系） |
| zz-space 世代 | `G:\xiao6\_ui_archive\2026-08-18\gui\` | zz-space.js、zz-space.css、three.min.js、lottie/ | 部分碎片 |
| Desktop avatar | `G:\xiao6\xiao6-ui\_archive\`（orb/gem/liquid）+ `xiao6-desktop\pet\`（pet.html/js/css 完整） | 桌宠浮窗资产 | pet 世代完整（但未入库） |

## 4. Git 对象库取证（关键恢复来源）

- `git fsck --dangling`：**906 个 dangling blob**。
- 逐 blob 内容特征扫描（DOCTYPE/<html/zz-workspace/app.js/styles.css/galaxy/avatar/小6）：**104 个前端特征 blob**。
- 含义：曾执行过 `git add`（前端文件进入 object 库）后又被 reset/未提交——前端内容（含 index.html 类文件）仍在 `.git/objects` 中，`git cat-file -p <blob>` 可直接导出；在 `git gc --prune` 执行前恢复窗口有效。
- `git log --all --name-only`：历史 commit 中**从未追踪过任何 .html**（前端从未被 commit，仅停留在 add 阶段的悬空对象）。

## 5. 恢复可行性分析

1. **无需重新设计**：Advanced Workspace 世代在 `_audit` 快照中三件套齐全，可直接回填 `xiao6-ui/` 根目录即可满足 `server.py:925` 的 `/` 路由；Galaxy 世代 80 个 JS 亦完整保留。
2. **主要缺口**：Galaxy 世代的主 `index.html` —— 从 906 个 dangling blob 中按内容筛选（104 个候选内）或采用 zz-workspace 快照替代。
3. **风险**：三个 UI 世代（zz-space → Galaxy → Advanced Workspace）并存且无"哪一代是 canonical"的决策记录；恢复前必须先定代，否则会拼出混合怪物。
4. **前置依赖**：恢复前端同时需恢复 `xiao6-ui/package.json`（Electron 入口）与 `launcher/launcher_config.json`（start.ps1 配置），否则桌面路径仍不可用。

## 6. 结论

| 检查项 | 结论 |
|---|---|
| index.html / app.js / styles.css / xiao6-space / static / js/ / css/（工作区+HEAD） | 全部缺失 |
| 前端状态 | **PARTIAL** |
| 可从 git object 恢复 | ✅（104 个前端特征 dangling blob） |
| 备份来源 | ✅ `_ui_archive/root-legacy`（80 js）+ `_audit/snapshot_*`（完整三件套） |
| 需要重新设计 | ❌ 不需要；需要的是"选代 + 回填 + 恢复 package.json/launcher_config" |
