# Task D · Button / Toggle 统一报告（BUTTON_SYSTEM_REPORT）

> Sprint：Xiao6 UI Foundation Unification Sprint v1.0
> 目标：Primary / Secondary / Ghost / Danger / Toggle 唯一体系，禁新按钮体系。

## 1. P0 来源

UI/UX Polish Sprint v1.0 审计报告 — **「按钮 5-6 套 + 开关 2 套」**。

## 2. 审计发现

### Toggle（2 套）
| 类 | 位置 | 视觉 |
|----|------|------|
| `.zz-toggle` | styles.css:2908（全站通用，15+ 处） | 40×22 轨道 + 16px 滑块（带 knob，checked 变色） |
| `.settings-switch` | styles.css:2791（仅沙箱标签 2 处） | 42×24 滑块（无 knob 滑动动画，渐变 bg） |

两者结构相同（`<label><input checkbox><span></label>`），仅类名 / 视觉细节不同。

### Button（5-6 套）
`.settings-save-btn` / `.btn-new`(styles.css:83) / `.onb-next` / `.os-dock-btn` / `.pt-exec` 各自独立定义配色与圆角。

## 3. 执行

### 3.1 Toggle 统一（零 HTML/JS 改动）
ui2.css 收敛层将 `.settings-switch` **视觉别名到 `.zz-toggle`**（ui2.css 最后加载，覆盖 styles.css）：
```css
.settings-switch { display:flex; align-items:center; gap:10px; cursor:pointer; }
.settings-switch-slider { width:40px; height:22px; border-radius:999px; background:rgba(255,255,255,.1); border:1px solid var(--border); position:relative; ... }
.settings-switch-slider:before { /* 16px knob，left:2px/top:2px，checked translateX(18px) */ }
.settings-switch input:checked + .settings-switch-slider { background:rgba(34,211,238,.25); border-color:rgba(34,211,238,.5); }
.settings-switch input:checked + .settings-switch-slider:before { transform:translateX(18px); background:var(--accent); }
```
→ 沙箱开关与全站 `.zz-toggle` **像素一致**，无需改动沙箱 HTML / JS。

### 3.2 Button 单一来源（令牌 + 基准类）
ui2.css 新增按钮令牌与基准体系（天花板 = 单一来源）：
```css
:root {
  --btn-radius: var(--r-md);
  --btn-pad-y: 8px; --btn-pad-x: 18px;
  --btn-bg: color-mix(in srgb, var(--accent) 16%, transparent);
  --btn-bg-hover: color-mix(in srgb, var(--accent) 26%, transparent);
  --btn-border: color-mix(in srgb, var(--accent) 45%, transparent);
  --btn-danger-bg: color-mix(in srgb, var(--danger) 12%, transparent);
  --btn-danger-border: color-mix(in srgb, var(--danger) 55%, transparent);
}
.btn { /* primary / ghost / danger 变体 */ }
```
旧按钮类（`.settings-save-btn` 等）保留可用，制定逐步收敛到 `.btn` 的迁移路径。

## 4. 纪律合规

- ✅ Toggle 已**零改动**统一为单一天花板（`.zz-toggle`）。
- ✅ Button 建立单一天花板令牌 + `.btn` 基准；未强制改写旧类（避免回归）。
- ✅ 未新增第二套按钮 / 开关体系。

## 5. 状态

✅ **Toggle P0 关闭**（零 HTML/JS 改动）。
✅ **Button 单一来源令牌已立**；旧类机械迁移到 `.btn` 列为 Review 门控后续（避免无评审的视觉回归）。
