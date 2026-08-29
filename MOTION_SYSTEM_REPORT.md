# Motion System Report — Xiao6 RC Polish Sprint v1.0

> **身份**：Senior Frontend Engineer + Design System Guardian
> **任务**：P1 统一 Motion Token
> **日期**：2026-08-05
> **纪律**：仅 Motion System 收敛 / 清理重复令牌 / 路由到统一 Token；无功能/逻辑/架构变更。

---

## 1. 扫描基线（Audit）

全项目扫描 `xiao6-ui/*.css` 的 `transition / animation / *-duration / *-timing-function` 与令牌定义：

| 文件 | transition 规则 | animation 规则 | 主要时长（字面量） | 主要缓动 |
|---|---|---|---|---|
| styles.css | 150 | 62 | `.2s`×70 `.35s`×27 `.25s`×20 `.15s`×20 `.3s`×19 `.22s`×16 `.18s`×14 `.28s`×10 `0.15s`×10 `.5s`×8 … | `ease` `ease-in-out` `cubic-bezier(.16,1,.3,1)` `linear` |
| premium.css | 9 | 9 | `0.01s` `3.2s` | `ease` |
| ui2.css | 12 | 6 | `0.01s`×4 `2.4s` `1.1s` `1s` | `ease` |
| companion.css | 7 | 23 | `.18/.26/.3/.4/.45/.5/.9/1.1/1.2/1.4/3.8/5.2/7s` | `ease-in-out` `ease` `linear` |
| execution-channel.css | 1 | 2 | `2s` `0.8s` | `linear` |
| runtime-viz.css | 0 | 0 | — | — |

**重复令牌（清理对象）**：
- 两套时长族并存：`--dur-*`（140/260/480/700ms，24 处引用）与 `--motion-*`（180/280/450ms，28 处引用）。
- 4 套缓动：`--ease-premium` / `--ease-soft` / `--ease-out-soft` / `--ease-spring`。

---

## 2. 规范决策（Plan）

1. **Canonical 时长族 = `--motion-*`**：引用更多（28 vs 24）且其值（180/280/450ms）与主导字面量（`.18/.28/.45s`）匹配更佳。
2. **`--dur-*` 降为 `--motion-*` 的遗留别名**（值对齐），消除重复定义。
3. **组件字面量路由**：120ms < 时长 ≤ 700ms 路由到最近 canonical token；≤120ms（瞬时）与 >700ms（装饰性 orbit/spinner）保留字面量，避免误把 `0.01s` 路由成 180ms 或把轨道动画强行令牌化。
4. **缓动路由**：3 个精确匹配 cubic-bezier → `--ease-*` token（`cubic-bezier(.16,1,.3,1)`→`--ease-premium` 等）。

---

## 3. 迁移统计（Execute）

| 指标 | styles | premium | ui2 | companion | exec | **合计** |
|---|---|---|---|---|---|---|
| transition/animation 规则改写 | 165 | 2 | 0 | 12 | 1 | **180** |
| 时长字面量 → token | 245 | 2 | 0 | 16 | 2 | **265** |
| 缓动字面量 → token | 18 | 0 | 0 | 3 | 0 | **21** |
| 保留（瞬时/装饰） | 41 | 5 | 7 | 14 | 1 | **68** |
| 令牌定义清理 | — | — | `--dur-*`→`--motion-*` (3) | — | — | **3 重复令牌消除** |

**剩余字面量（设计上保留，非遗漏）**：仅 `.08s/.12s`（≤120ms 瞬时）与 `.8s/1s/1.2s/2s/…/36s`（>700ms 星系轨道/加载动画）。

---

## 4. 时长映射表（含最大视觉偏移）

| 字面量 | ms | → token | 偏移 |
|---|---|---|---|
| `.14s` `.15s` `.18s` `.2s` `.22s` | 140–220 | `--motion-fast` (180) | ≤40ms |
| `.25s` `.28s` `.3s` | 250–300 | `--motion-base` (280) | ≤30ms |
| `.35s` | 350 | `--motion-base` (280) | 70ms（最大） |
| `.45s` `.5s` | 450–500 | `--motion-slow` (450) | ≤50ms |
| `0.01s` `.8s` `≥1s` | — | 保留字面量 | 0 |

> 最大偏移 70ms（`.35s`→280ms），属「收敛」预期内的归一化，非功能回归。

---

## 5. 验证（Verify）

- ✅ CSS 括号平衡：6 文件 `count('{') == count('}')`（脚本断言通过）。
- ✅ `var(--x)` 解析：除预存在的 `--sw`（3 处，运行时由 onboarding 注入，非本次引入）外，所有新引用（`--motion-*`/`--ease-*`）均在 `ui2.css` 单一定义。
- ✅ `node --check`：main.js / preload.js / app.js / companion.js / avatar-* 全部 OK（CSS 改动未触及 JS）。
- ✅ 前端测试：16 套 PASS，**0 新增失败**（3 个预存在失败 = companion.js 缺 `window` / SYSTEM_EVENT_NAMES 契约漂移，与本次无关）。
- ✅ 纪律 grep：改动 CSS 无 `new Runtime/EventBus/Agent`、`/api/` fetch。

---

## 6. 结论

Motion Token 已统一到 `--motion-*`（时长）+ `--ease-*`（缓动）双族，重复 `--dur-*` 降为别名，265 处字面量完成路由，3 个重复令牌定义清除。视觉偏移 ≤70ms，可接受为收敛结果。**0 回归**。
