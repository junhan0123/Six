# ICON_USAGE_SPEC — 小6 Icon 使用规范（唯一权威）

> **Sprint**: Xiao6 Icon System Migration Sprint v1.0
> **生效日期**: 2026-08-05
> **约束力**: 本规范为小6前端 Icon 体系**唯一入口标准**。任何新增/修改 Icon 必须遵循，禁止引入第二套 Icon 基础类。

---

## 1. 唯一入口类：`.zz-icon`

小6所有图标（除第 4 节声明的遗留别名）**必须**通过 `.zz-icon` 引用 SVG Sprite：

```html
<!-- 标准填充/描边图标 -->
<svg class="zz-icon stroke"><use href="#zz-gear"></use></svg>

<!-- 纯填充图标（如实心 logo） -->
<svg class="zz-icon f"><use href="#zz-lotus"></use></svg>
```

- 图标定义集中存放于 `index.html` 的隐藏 `<svg id="zzIconSprite">`（67 个 `<symbol>`）。
- 引用语法：`<use href="#zz-<id>"/>`，`<id>` 必须与 sprite 中 `id="zz-<id>"` 完全一致。
- **禁止**在任何新代码中写死 `<svg><path d="..."/></svg>` 内联图标（遗留 `.ic` 除外，见第 4 节）。

---

## 2. 尺寸（单一令牌）

所有图标尺寸由 `ui2.css` 的 `--icon-size` 令牌统一控制：

```css
:root { --icon-size: 20px; }   /* ui2.css:35 */

.zz-icon {
  width: var(--icon-size);
  height: var(--icon-size);
  display: inline-block;
  vertical-align: -0.15em;
}
```

- 全站图标统一 20px 基线，禁止在组件内写死 `width/height` 像素值覆盖。
- 如需局部放大，使用 `transform: scale()` 或覆盖 `--icon-size`（作用域限定），不得引入新尺寸令牌外的硬编码。

---

## 3. 颜色（主题继承）

```css
.zz-icon { fill: currentColor; stroke: none; }                 /* 填充型 */
.zz-icon.stroke {
  fill: none; stroke: currentColor;
  stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round;
}
```

- 图标颜色**继承 `currentColor`**，自动跟随父元素文字色 → 暗色/亮色主题无需为图标单独配色。
- **禁止**写死 `fill:#xxx` / `stroke:#xxx`（破坏主题兼容，违反验收标准⑤）。
- 主题切换时图标随文字色即时变化，无需 JS 干预。

---

## 4. 遗留别名：`.ic`（仅存量，禁新增）

既有 `class="ic"` 内联 SVG 通过 `ui2.css` 末加载的别名层零改动接管：

```css
.ic {
  width: var(--icon-size); height: var(--icon-size);
  display: inline-block; vertical-align: -0.15em;
  fill: none; stroke: currentColor;
  stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round;
}
.ic.f { fill: currentColor; stroke: none; }
```

- `.ic` 与 `.zz-icon.stroke` **视觉等价**（描边风），存量 17 处自动合规。
- **规则**：`.ic` 仅允许存在于已迁移的存量代码；新代码一律写 `.zz-icon.stroke`，不得新增大写 `.ic` 实例。

---

## 5. 交互状态

```css
.zz-icon:hover, .ic:hover      { filter: brightness(1.2); }
.zz-icon:active, .ic:active    { transform: translateY(1px); }
.zz-icon[disabled], .zz-icon.is-disabled,
.ic[disabled], .ic.is-disabled { opacity: .4; }
```

- hover：亮度 +20%，无位移。
- active：下移 1px，提供按压反馈。
- disabled：透明度 0.4，不可点击态。
- 状态仅通过 CSS 伪类/属性控制，不新增 JS 状态类（除非必要）。

---

## 6. 使用方式速查

| 场景 | 写法 |
|------|------|
| 导航/设置图标（描边） | `<svg class="zz-icon stroke"><use href="#zz-gear"/></svg>` |
| 实心 logo/标记 | `<svg class="zz-icon f"><use href="#zz-lotus"/></svg>` |
| 与文字同行 | 直接置于 `<button>`/`<span>` 内，自动 `vertical-align` 对齐 |
| 遗留存量（不重构） | 维持 `class="ic"`，由 CSS 别名接管 |

---

## 7. 禁止项（硬性）

1. ❌ 新增第二套 Icon 基础类（如 `.icon`/`.ui-icon`/`.svg-ic`）。
2. ❌ 用 emoji 作 UI 控制图标（验收标准①；域/内容 emoji 除外，见映射表第 3 节）。
3. ❌ 写死图标 `fill`/`stroke` 颜色（必须用 `currentColor`）。
4. ❌ 在组件内硬编码图标像素尺寸（必须用 `--icon-size`）。
5. ❌ 新代码使用 `class="ic"`（仅存量别名，禁增量）。
6. ❌ 引用不存在的 `#zz-<id>`（导致空白图标；新增前先定义 `<symbol>`）。

---

## 8. 新增图标流程

1. 在 `index.html` `#zzIconSprite` 内新增 `<symbol id="zz-<newid>" viewBox="0 0 24 24"><path d="..."/></symbol>`（24×24 视图，描边风 `fill:none` 或填充风）。
2. 引用处写 `<svg class="zz-icon stroke"><use href="#zz-<newid>"/></svg>`。
3. 更新 `ICON_MAPPING_TABLE.md` 第 5 节 symbol 全集。
4. 运行引用校验：确认 `#zz-<newid>` 在 sprite 中存在（零孤儿）。
5. **本 Sprint 后**：新增图标属 P1/常规维护，不触发冻结纪律，但须保持单一入口。
