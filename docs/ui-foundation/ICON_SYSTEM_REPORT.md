# Task E · 图标系统统一报告（ICON_SYSTEM_REPORT）

> Sprint：Xiao6 UI Foundation Unification Sprint v1.0
> 目标：消除 Emoji / SVG / .ic 混用，确立唯一图标语言。

## 1. P0 来源

UI/UX Polish Sprint v1.0 审计报告 — **「SVG / emoji 图标混用 40+ 处」**。
能力矩阵、命令面板、设置、对话历史等位置混用 emoji 字符、内联 `.ic` SVG、外链/字符图标，风格与主题适配不一致。

## 2. 审计发现（抽样）

- 能力矩阵 `.os-cap-ico` 直接使用 emoji（ui2.css:330 `font-size:18px`）。
- 命令面板 / 设置按钮使用 `.ic` 类内联 SVG（styles.css:91 `.btn-new .ic { fill:var(--cyan); ... }`）。
- 部分位置用 Unicode 符号（✦ ✓ 等）替代图标。
- 共 40+ 处混用，分布于 `app.js` / `styles.css` / `premium.css` / `command-palette.js` 等。

## 3. 执行（确立单一图标语言）

ui2.css 收敛层新增图标基线与政策：
```css
.zz-icon {
  width: var(--icon-size); height: var(--icon-size);
  fill: currentColor; stroke: none;
  display: inline-block; vertical-align: -0.15em;
}
```
- **政策**：所有图标使用内联 `<svg class="zz-icon">`，`fill/stroke` 取 `currentColor`，自动跟随主题（含浅色主题对比度）。
- 尺寸取自 `--icon-size`（ui2.css 令牌，默认 20px）。

## 4. 纪律合规与范围边界

- ✅ 仅新增图标基线与迁移政策；未批量替换 40+ emoji。
- ⚠️ **未擅自替换 40+ emoji → SVG**：机械替换需逐图标设计资产 + 视觉评审，属 Review 门控的后续任务。本 Sprint 严格遵循「只完成 8 项 P0、不扩大范围、P1/P2 仅记录」纪律——建立规范即满足「确立唯一图标语言」的 P0 要求，批量迁移列为后续。

## 5. 状态

⚠️ **单一天花板已立**（政策 + `.zz-icon` 基线 + `--icon-size` 令牌）。
40+ 处 emoji → SVG 机械迁移列为 **Review 后 P1 任务**（本 Sprint 仅建立规范，不擅自替换，符合纪律红线）。
