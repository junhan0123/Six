# Icon System Report — Xiao6 RC Polish Sprint v1.0

> **身份**：Senior Frontend Engineer + Design System Guardian
> **任务**：P2 统一 Icon System
> **日期**：2026-08-05
> **纪律**：仅 Icon 引用方式收敛 / 风格漂移记录 / 零视觉变更；无功能 / 逻辑 / 架构变更。

---

## 1. 扫描基线（Audit）

全项目扫描 `xiao6-ui/*.html` + `*.css` 的 SVG 使用与 `.ic` 图标体系：

| 维度 | 结果 |
|---|---|
| `index.html` 内联 `<svg>` | 12 个，**全部** `class="ic"` + `viewBox="0 0 24 24"` |
| 内联 SVG 统一率 | **100%（12/12）** |
| `styles.css` 中 `.ic` 选择器 | 18 处（单一基样式来源） |
| `companion.html` emoji / SVG | 0（仅 `avatar-state.js` 经 CSS 渲染，无内联图标） |
| `mobile-app / selfcheck / weather-modal-preview` | 0 内联图标 |
| 其他 CSS（`premium / companion / exec / runtime-viz / ui2`） | 0 内联 `<svg>` |

**结论**：图标已 100% 收敛于 `.ic` 描边 SVG 体系，无散落 emoji 或异风格图标。

---

## 2. 风格漂移（Style Drift）

`.ic` 基样式（`styles.css:23`）本次已 token 化：

```css
.ic {
  width: var(--icon-size); height: var(--icon-size);
  fill: none; stroke: currentColor; stroke-width: 1.7;
  stroke-linecap: round; stroke-linejoin: round;
}
```

子类局部属性覆盖（审计发现，**均为按图标语义的有意变体，非体系冲突**）：

- **width 覆盖**：`24px`×1（`.brand-mark` 品牌大图标）、`22px`×2、`18px`×3、`15px`×1
- **height 覆盖**：`22px`×2、`18px`×2、`15px`×1
- **stroke 覆盖**：`none`×2（装饰描边隐藏）、`var(--txt)`×1
- **fill 覆盖**：`currentColor`×3、`var(--cyan)`×3（`#btnImage` 等强调图标）、`var(--txt)`×1、`#03121a`×1
- **内联覆盖**：`index.html:256` 关闭叉号 `stroke-width:2`（比基样 1.7 粗，视觉权重更高）；`index.html:326` 服务器图标 `fill:currentColor`（实心填充变体）

上述覆盖均为「同一 `.ic` 体系内的尺寸 / 颜色语义变体」，并非引入第二套图标风格。

---

## 3. 统一引用方式（Execute）

- **已做（零视觉变更）**：`.ic` 基样式 `width/height` 由硬编码 `20px` 改为 `var(--icon-size)`（`--icon-size: 20px`，在 `ui2.css :root` 定义层新增，作为 Design Token v2 统一刻度之一）。视觉输出完全等价，仅引用方式统一到 Design Token。
- **不做**：未对 12 个内联 SVG 做结构重写（已 100% 统一，重写无收益且引入风险）；未删除子类属性覆盖（属有意语义变体，删除会破坏既有视觉）。

---

## 4. 统一率统计

| 指标 | 数值 |
|---|---|
| 内联 SVG 统一到 `.ic` | **100%（12/12）** |
| `.ic` 选择器集中（`styles.css` 单一基样式来源） | 18 处 |
| `companion` 散落图标 / emoji | 0 |
| 基样式 token 化 | ✅ `width/height → var(--icon-size)` |

---

## 5. 验证（Verify）

- ✅ **视觉等价**：`20px → var(--icon-size)=20px`，渲染像素一致。
- ✅ **CSS 括号平衡**：`styles.css / companion.css` 等 6 文件 `count('{') == count('}')` 断言通过。
- ✅ **`var()` 解析**：`--icon-size` 在 `ui2.css :root` 单一定义，无未定义引用（除预存 `--sw` 外，非本次引入）。
- ✅ **前端测试**：16 套 PASS / 0 新增失败；`node --check` 全部 JS OK。
- ✅ **纪律 grep 清洁**：无 `Runtime/EventBus/Agent`、`/api/` fetch 改动。

---

## 6. 结论

Icon System 在 RC 起点已高度统一（内联 SVG 100% 用 `.ic`，主界面 18 处 `.ic` 选择器集中，`companion` 零散落图标）。本次仅做**零视觉变更**的统一引用（基样式 token 化），无破坏性重写。

**建议（非 RC 范围，留待日常维护）**：后续可建 `icons.css` 收口子类属性覆盖，将 `width/fill/stroke` 局部覆盖也路由到统一刻度，进一步降低风格漂移面。

**0 回归。**
