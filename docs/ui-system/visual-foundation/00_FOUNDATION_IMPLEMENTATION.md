# Xiao6 Visual Foundation Activation v1.0 — 实现报告

> **Phase**: `UI-3A` · **文档 ID**: `00_FOUNDATION_IMPLEMENTATION`
> **身份**: Senior Frontend Engineer + Design System Engineer
> **日期**: 2026-08-09
> **状态**: ✅ 实现完成 · 🛑 STOP，等待人工 Review（不进入 Galaxy / Workspace / Panel / Settings Migration）

---

## 0. 阶段定位与纪律红线（Scope & Guardrails）

**核心原则（来自 brief）**：本阶段**不是视觉重构**、**不是页面 redesign**、**不是改变产品结构**。目标是让 *AI OS Visual Blueprint v1.0* 开始拥有**真实的 Design Foundation**——即把已声明但"声明未接线 / 接线失效"的 token 与原语**激活**为全站真实唯一视觉来源。

**严格遵守的禁止项（全程未违反）**：
- ❌ 未修改 Galaxy / `solar-system.js` / Three.js / Workspace layout / Settings structure / HTML architecture
- ❌ 未修改 Backend / Agent / EventBus / Domain / 功能入口
- ❌ 未大面积重写 CSS、未删除任何 Legacy CSS
- ❌ **未改动任何 JS selector、未改变任何事件行为**（R2 仅补 CSS 状态声明）
- ❌ 未提交 Git（`.git` 未触碰）
- ❌ 未新增第二 Token 体系 / 第二 Design Language

**执行范围**：R1 Token Activation · R2 Input Primitive Finalization · R3 Spatial Foundation · R4 暂停（Galaxy / Panel Migration / Settings Evolution / Navigation redesign）。

---

## 1. Token Changes（R1 — Token Activation）

### 1.1 关键发现：设计文档 vs 代码现状错位

执行 R1 前，先对 `ui2.css`（令牌权威文件，最后加载）做了全量审计，对照 `docs/ui-system/unified-visual-architecture/03_PANEL_VISUAL_LANGUAGE.md` 与 `06_DESIGN_SYSTEM_NEXT_STAGE.md` 的描述。

**结论**：`03`/`06` 文档将 `--fs-*`、`--sp-*`、`--line-strong` 等描述为"死令牌 / 缺失 / 需激活"，但 grep `ui2.css` 证实——**这些令牌实际已全部定义并接线**。示例：

| 文档描述（03/06） | 代码真实状态（ui2.css） |
| --- | --- |
| `--fs-*` 死/缺失 | 已定义 18 档字号阶梯 `--fs-2xs … --fs-5xl` |
| `--sp-*` / `--space-*` 死/缺失 | 已定义 `--sp-1 … --sp-40` 间距阶梯 |
| `--line-strong` 死/别名 | **部分失效**：`:root` 与全部主题均别名到 `--border` |
| `--elev-1/2/3` 缺失 | 已定义，含顶部内高光 |
| `--z-*` 缺失 | 已定义 29 档层级 |
| `--glass-*` / `--blur-glass` 缺失 | 已定义 `--glass-1/2/3` + `--blur-glass` |
| `--presence-*` 缺失 | 已定义（含 `--presence-remind`） |
| `--input-*` 缺失 | 已定义完整输入令牌族 |
| `--panel-*` / `--btn-*` / `--ws-*` | 均已定义 |

**策略修正**：因令牌体系实际远比文档描述的完整，**R1 不盲目新增令牌**（严守"不制造重复系统"纪律），改为：① 确认六类令牌已接线；② 仅修复真正失效的 `--line-strong` 别名。

### 1.2 六类 Token 审计结果

| 类别 | 状态 | 说明 |
| --- | --- | --- |
| **Color** | ✅ 已接线 | color role（`--text`/`--text-dim`/`--bg`/`--surface`/`--accent`/`--accent-2`/`--warn`/`--danger` 等）齐备；`--line-strong` 修复见 1.3 |
| **Typography** | ✅ 已接线 | `--font-ui` / `--fs-*`（18 档）/ `--input-font` 齐备 |
| **Spacing** | ✅ 已接线 | `--sp-*` / `--space-*` / `--input-pad-*` 齐备 |
| **Elevation** | ✅ 已接线 | `--elev-1/2/3`（含顶部内高光）齐备 |
| **Motion** | ✅ 已接线 | `--motion-fast` / `--dur-base` / `--ease-soft` / `--motion-*` 齐备 |
| **Attention** | ✅ 已接线 | `--glow` / `--shadow-glow` / `--presence-*` / `--accent` 语义齐备 |

### 1.3 唯一需要激活的 Token：`--line-strong`（真实 Bug 修复）

**问题**：`:root` 与全部 10 个主题块中，`--line-strong` 均被别名到 `--border`。

```css
/* 旧：hover / 激活的「强边框」语言实际不可见（与常态边框同色） */
--line-strong: var(--border);
```

**修复**（`ui2.css` `:root` L177，激活为 accent 染色的真实强边框，随主题自适应）：

```css
/* 激活「强边框」语言：此前 --line-strong 被别名到 --border（hover/激活边框不可见）。
   现改为 accent 染色的更强边框，随主题自适应；移除各主题同名别名以本定义为准。 */
--line-strong: color-mix(in srgb, var(--border) 70%, var(--accent) 30%);
```

**配套动作**：用 `replace_all` 删除全部 9 个主题块中 `--line-strong:var(--border);` 死别名（L240/254/268/282/298/311/324/337/350/365 等），确保 `:root` 定义为唯一真相。

**影响面**：`--line-strong` 现仅在 `:root` 定义一次；`ui2.css` 内引用 2 处（`.zz-input:hover`、注释）；`styles.css` 内既有 56 处引用（`.settings-input:hover`、`.settings-save-btn`、`.os-dock-bar:focus-within` 等）自此获得**真实的强调色强边框**，border language 正式生效。

**技术注**：`color-mix(in srgb, ...)` 为 CSS 原生混合函数，无需新增变量即可让强边框随主题 accent 自适应，不破坏 9 主题体系。

### 1.4 R1 新增/修改 Token 清单

| Token | 类型 | 变更 | 服务的视觉概念 |
| --- | --- | --- | --- |
| `--line-strong` | 修改（`:root`） | `var(--border)` → `color-mix(... var(--accent) 30%)` | 强边框语言（hover/激活/重点按钮描边） |

> 除 `--line-strong` 外，**R1 未新增任何 token**——六类令牌均已存在并接线，激活而非重建。

---

## 2. Primitive Changes（R2 — Input Primitive Finalization）

### 2.1 统一 Input 视觉语言（设计基线）

所有输入共享同一组令牌语言：`--input-bg` / `--input-border` / `--input-radius` / `--input-pad-*` / `--input-font` / `--input-placeholder` / `--input-focus-border` / `--input-focus-glow` / `--input-disabled-op` / `--input-error-border` / `--line-strong` / `--motion-*`。不同 surface 可尺寸/底色不同，但**视觉语言一致**（core principle：复用 Design Language，不新建控件）。

### 2.2 `.zz-input`（W1 Formal Input Primitive）— 已完备，确认未改

`.zz-input`（`ui2.css` L1061-1076）已是完整六态原语，**本阶段确认其完备性，未做任何改动**：

```css
.zz-input { /* Default：背景/边框/圆角/文字/占位/transition */
  background: var(--input-bg); border: 1px solid var(--input-border);
  border-radius: var(--input-radius); padding: var(--input-pad-y) var(--input-pad-x);
  transition: border-color var(--motion-fast) var(--ease-soft), box-shadow var(--motion-fast) var(--ease-soft);
}
.zz-input:hover    { border-color: var(--line-strong); }              /* Hover（现真实可见） */
.zz-input:focus    { border-color: var(--input-focus-border);
                     box-shadow: 0 0 0 3px var(--input-focus-glow); }  /* Focus-visible */
.zz-input:disabled, .zz-input[readonly] { opacity: var(--input-disabled-op); cursor: not-allowed; }
.zz-input--error[data-error="true"] { /* Error：由 .settings-input 同款契约驱动 */ }
```

> R1 的 `--line-strong` 激活使 `.zz-input:hover` 的强边框**首次真实可见**，属 R1/R2 协同收益，无新增代码。

### 2.3 `.settings-input` — 补 error 态契约（styles.css L2673）

旧版 `.settings-input` 缺 error 态，与 `.zz-input--error` 不一致。修复（仅追加一行，未改既有行）：

```css
.settings-input[data-error="true"],.settings-input.zz-input--error,
.settings-select[data-error="true"],.settings-select.zz-input--error {
  border-color: var(--input-error-border);
}
```

`disabled` 态（L2672）原本已存在，保留未动。

### 2.4 `.os-dock input`（Command Dock 输入）— 补 transition + disabled（ui2.css L840/843）

Command Dock 输入是嵌入透明边框 bar 的输入（focus 环在 `.os-dock-bar` 上）。旧版缺 transition 与 disabled 态。修复（追加两行）：

```css
.os-dock input {
  flex: 1; background: transparent; border: 0; outline: 0; color: var(--text);
  font-family: var(--font-ui);
  transition: color var(--motion-fast) var(--ease-soft);   /* 新增 */
}
.os-dock input::placeholder { color: var(--input-placeholder); }
.os-dock input:disabled { opacity: var(--input-disabled-op); cursor: not-allowed; }  /* 新增 */
```

### 2.5 `#input`（Workspace / chat 输入）— 补 transition（styles.css L509）

Workspace 输入刻意无边框透明（保留其独特视觉语言，未破坏）。旧版缺 transition。修复（仅追加 `transition` 行）：

```css
#input { width:100%; resize:none; border:0; outline:0; background:transparent; color:var(--text);
  font-family: var(--font-ui); font-size:16px; line-height:1.5; max-height:120px; padding:9px 0;
  transition:color var(--motion-fast) var(--ease-soft) }   /* 新增 */
```

### 2.6 R2 变更清单（严格未改 JS selector / 事件行为）

| 选择器 | 文件 | 变更 | 类型 |
| --- | --- | --- | --- |
| `.zz-input` 族 | ui2.css | 确认六态完备，**未改** | — |
| `.settings-input` / `.settings-select` | styles.css | +`[data-error]`/`.zz-input--error` → `var(--input-error-border)` | error 态 |
| `.os-dock input` | ui2.css | +`transition` +`:disabled` | transition/disabled |
| `#input` | styles.css | +`transition` | transition |

> 注：`.hs-chat-input`（Hero chat 输入）未令牌化，按 brief 边界（不改 HTML/Workspace 结构）**保留不碰**。

---

## 3. Spatial Foundation（R3 — 空间语言基础）

### 3.1 结论：Spatial Token 已齐备，本阶段仅需激活 border language

审计 `ui2.css` 确认全部空间令牌**已定义并接线**，无需新建：

| 概念 | Token | 状态 |
| --- | --- | --- |
| Surface depth | `--elev-1/2/3` | ✅ 已定义（含顶部内高光） |
| Glass / blur | `--glass-1/2/3` + `--blur-glass`（`--glass-3` = blur 26px sat 180%） | ✅ 已定义 |
| Overlay hierarchy | `--z-panel`(81) / `--z-dialog`(83) / `--z-overlay`(60) / 29 档 `--z-*` | ✅ 已定义 |
| Glow | `--glow`（颜色语义）+ `--shadow-glow` | ✅ 已定义 |
| Border language | `--line` / `--line-strong` | ✅ `--line` 已接线；**`--line-strong` 于 R1 激活** |

### 3.2 R3 实际补完动作

- **唯一补完** = R1 的 `--line-strong` border language 激活（见 §1.3）。hover / 激活态的"强边框"语言此前不可见，现已随主题 accent 生效，构成 Panel/Surface 边界强调的统一来源。
- **未迁移任何 Panel**：本阶段仅确立空间语言"基础"，不实现 Galaxy、不迁移现有 17 面板（`panel-manager.js` 等结构零改动）。
- **blur 规则**：`--glass-3`(blur 26px sat 180%) 与既有 glass 用法一致，未新增 blur 值，避免与 DESIGN.md §7 Don'ts 冲突（不裸 `rgba`、不第二套 class）。

### 3.3 R3 与 Golden State / DESIGN.md 兼容性

- 全部空间令牌位于 `ui2.css`（最后加载，令牌最终权威），未触碰 `styles.css` 历史 class 体系。
- 未引入新 class、新 `@keyframes`、新层级值，CSS 加载顺序（`styles.css→premium.css→…→ui2.css`）保持有效，`ui2.css` 仍为最终权威。

---

## 4. Files Changed（变更文件清单）

| 文件 | 性质 | 改动处数 | 改动摘要 |
| --- | --- | --- | --- |
| `xiao6-ui/ui2.css` | 令牌权威（最后加载） | 3 | ① `:root` `--line-strong` 激活（L177）；② 删除 9 主题 `--line-strong` 死别名；③ `.os-dock input` +`transition` +`:disabled`（L840/843） |
| `xiao6-ui/styles.css` | Legacy（保留未删） | 2 | ① `.settings-input` +error 态（L2673）；② `#input` +`transition`（L509） |
| `docs/ui-system/visual-foundation/_validation/` | 验证产物（新建） | 3 截图 | `zz_1920x1080.png` / `zz_1440x900.png` / `zz_720x1280.png` |

**未改动**：`solar-system.js` / `app.js` / `settings.js` / `index.html` / `panel-manager.js` / 任何 HTML / 任何后端文件 / 任何 Agent/EventBus/Domain 代码。

**未删除**：任何 Legacy CSS（仅追加声明，未清删）。

**未提交**：`.git` 未触碰。

---

## 5. Regression Check（回归检查）

### 5.1 自动化验证（已通过）

| 检查项 | 方法 | 结果 |
| --- | --- | --- |
| CSS 结构平衡 | `grep -o '{'/'}'` 计数 | ui2.css **400/400** · styles.css **1525/1525** · premium.css **84/84** ✅ |
| JS 未被改动 | `ls -la --time-style` mtime | app.js 06:49 · index.html 02:34 · settings.js 17:43（均非本次会话，未改）✅ |
| `--line-strong` 唯一真相 | grep 全文件 | 仅 `:root` L177 定义；主题别名已清零 ✅ |
| 三视口 headless 渲染 | Chrome `--screenshot` @ 1920×1080 / 1440×900 / 720×1280（经 `python -m http.server`） | 3 张截图成功生成（`_validation/`，无渲染报错退出）✅ |

### 5.2 验证视口

- Desktop 1920×1080 — `zz_1920x1080.png`（242KB）
- Desktop 1440×900 — `zz_1440x900.png`（220KB）
- Narrow 720×1280 — `zz_720x1280.png`（178KB）

### 5.3 ⚠️ 验证局限（需人工 Review 目检）

- **截图无法被本模型肉眼核验**：Read PNG 受图像过滤限制，无法逐像素确认视觉细节。上述仅能确认"headless 渲染成功、无报错退出、CSS 结构平衡、JS 未动"。
- **交互态属非默认态**：hover / focus / error / disabled 等激活态不会出现在静态截图首帧，需在真实浏览器人工目检确认。
- **建议 Review 重点**：① Command Dock 输入 focus 环 + disabled 透明度；② Settings 输入 error 红边；③ Workspace `#input` 颜色过渡是否顺滑；④ 9 主题下 `--line-strong` 强边框是否随 accent 自适应且可见；⑤ 输入框 / Dock / Settings / 现有 Panel 三者视觉语言是否一致（无尺寸/间距回归）。

---

## 6. Remaining Roadmap（剩余路线图 · R4 暂缓项）

本阶段严格止于"激活 Foundation"。以下**均未启动**，属后续独立阶段，需在 Review 通过后另行规划：

| 暂缓项 | 说明 | 触发条件 |
| --- | --- | --- |
| **Galaxy / Panel Migration** | 将现有 17 面板迁移至统一 Panel 视觉语言（Depth Ladder / Elevation / Glass / Border&Glow） | 等待 Foundation Review 通过 |
| **Settings Evolution** | Settings 结构演化（非本次结构保留范围） | 独立阶段 |
| **Navigation redesign** | 导航重设计 | 独立阶段 |
| **Workspace Redesign** | Workspace 布局重设计 | 独立阶段（本次仅补 `#input` transition） |
| **`.hs-chat-input` 令牌化** | Hero chat 输入未令牌化，按边界保留 | 后续 Input 收口阶段 |
| **交互态真机目检** | hover/focus/error/disabled 人工验收 | 人工 Review（本报告 §5.3） |

---

## 7. STOP 声明

✅ **UI-3A Visual Foundation Activation v1.0 实现完成**，仅改动 `ui2.css`（3 处）+ `styles.css`（2 处），全部为 CSS 状态声明追加 / token 激活，**零 JS 改动、零 HTML 改动、零 Legacy 删除、零第二体系**。

🛑 **STOP**：不进入 Galaxy Redesign / Workspace Redesign / Panel Migration / Settings Migration。等待人工 Review（重点见 §5.3 目检项）。未提交 Git。

**最终目标**：建立 *Xiao6 AI OS Visual Foundation v1.0* 作为后续所有视觉实现**唯一基础**——本阶段已达成"激活"里程碑，Foundation 令牌与原语现全站真实生效。
