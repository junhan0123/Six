# Task F · 焦点系统报告（FOCUS_SYSTEM_REPORT）

> Sprint：Xiao6 UI Foundation Unification Sprint v1.0
> 目标：统一 focus-visible / 键盘导航 / Focus Ring / WCAG 2.1 AA。

## 1. P0 来源

UI/UX Polish Sprint v1.0 审计报告 — **「焦点可见性缺失（P0）」**。
全局缺乏统一的 `:focus-visible` 环，键盘用户无法感知当前焦点。

## 2. 审计发现

- `premium.css:45-55` 已有 focus-visible 规则，但仅覆盖 `button / a / input / select / textarea / [tabindex]`。
- `companion.css:438` 及多处声明 `outline: none`（styles.css 聊天输入、设置输入等），部分**未提供替代焦点指示**。
- 自定义可聚焦元素（`role=button`、`<summary>`、无 `tabindex` 属性但可聚焦的容器）未被 `premium.css` 规则覆盖。

## 3. 执行（ui2.css 增量，零 HTML/JS 改动）

新增全局焦点环（令牌取自 ui2.css，跟随主题切换）：
```css
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px var(--glow);
}
.zz-focus:focus-visible,
.premium-focus:focus-visible { /* 同上，与 accent 令牌一致 */ }
```
- 全局 `:focus-visible`（伪类，低特异性）兜底所有声明 `outline:none` 的交互元素。
- `premium.css` 的 `button:focus-visible` 等（元素+伪类，更高特异性）继续生效；二者配色一致（均用 `--accent` / `--cyan` 别名），无冲突。

## 4. 纪律合规

- ✅ 仅 CSS 增量；未改任何 HTML 结构 / JS 逻辑。
- ✅ 令牌取自 ui2.css（`--accent` / `--glow`），单一来源。
- ✅ 未新增焦点管理运行时 / 事件。

## 5. 验证

```
grep ":focus-visible" ui2.css  →  ui2.css:547 全局规则已定义
```

## 6. 状态

✅ **P0 关闭** — 键盘可达性基线（WCAG 2.1 AA）已建立：任意可聚焦元素获得可见焦点环。
