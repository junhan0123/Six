# Task E · 组件命名规范（COMPONENT_NAMING_SPEC）

> Sprint：Xiao6 Component System Sprint v1.0
> 目标：统一 class / CSS token / component name / state name；确立 `zz-` 前缀
> 本 Task 立规范（不强制改写现有代码，改写按 Task F 门控推进）

---

## 1. 命名总则

| 规则 | 规定 |
|------|------|
| 前缀 | 所有组件 class 以 **`zz-`** 开头（如 `zz-button` `zz-panel` `zz-dialog`） |
| 令牌前缀 | CSS 自定义属性以语义分组：`--color-*` `--space-*` `--r-*` `--elev-*` `--motion-*` `--accent` 等（已在 ui2.css） |
| 组件名 | 小写下划线/连字符：`zz-toggle` `zz-panel` `zz-modal-card` |
| 状态名 | 用 BEM 修饰或语义属性：`--entering` `--leaving` `--open` `:checked` `:disabled` `:focus-visible` `is-on` |
| 禁止 | 禁止继续新增无 `zz-` 前缀的通用组件类（如 `.btn-new` `.settings-save-btn` `.glass-panel` 等历史类冻结，仅经别名收敛） |

---

## 2. 现有类 → 规范命名映射（目标态）

### Primitive
| 现有类 | 规范名（zz-） | 处置 |
|--------|---------------|------|
| `.btn` (+.primary/.ghost/.danger) | `zz-button` (+`--primary`/`--ghost`/`--danger`) | 天花板（现用 `.btn`，未来迁 `zz-button`） |
| `.btn-new` | → `zz-button` | 别名收敛（Task F） |
| `.onb-next` | → `zz-button--primary` | 别名收敛（Task F） |
| `.settings-save-btn` | → `zz-button` | 留 Review（风险中） |
| `.zz-panel` | `zz-panel` | 维持（官方语义基准） |
| `.os-panel` | → `zz-panel`（视觉对齐） | 别名（Task F 试点） |
| `.glass-panel` | `zz-panel`（视觉基准候选） | 维持 |
| `.settings-panel` | → `zz-panel` 变体 | 留 Review |
| `.modal-card` | `zz-modal-card` | 划 Composite |
| `.settings-input` | `zz-input` | Task E 命名补全 |
| `.settings-select` | `zz-select` | Task E 命名补全 |
| `.zz-toggle` | `zz-toggle` | ✅ 已统一 |
| `.toast` | `zz-toast` | 未来别名 |
| `.proactive-toast` | `zz-toast`（通知型） | 未来别名 |

### Composite（缺失组件 · 预留命名，本 Sprint 不实现）
| 规范名 | 现有 ad-hoc | 说明 |
|--------|-------------|------|
| `zz-dialog` | modal-card + overlay | 预留 |
| `zz-modal` | modal-card + overlay | 预留（与 dialog 区分尺寸） |
| `zz-dropdown` | `.more-dropdown` | 预留 |
| `zz-menu` | `.more-menu-wrap` / `.quick-menu` | 预留（注意 `zz-menu` 现为图标 symbol，组件实现时需换 id 或加后缀） |
| `zz-tabs` | `.settings-tab` / `.mem-tabs` | 预留 |
| `zz-tooltip` | `.hint` | 预留 |
| `zz-overlay` | `*overlay` 容器 | 预留（overlay-runtime.js 内容层） |

> ⚠️ 冲突提示：`zz-menu` 当前是图标 sprite symbol id（index.html:176）。若未来实现 Menu 组件，组件容器不得复用 `zz-menu`，建议图标保持 `zz-menu`、组件用 `zz-menu-root` 或重命名图标为 `zz-icon-menu`。

---

## 3. State 命名规范

| 状态 | 规范写法 | 示例 |
|------|----------|------|
| 进入/离开 | `--entering` / `--leaving` | `.zz-panel--entering` |
| 打开/关闭 | `--open` / `[aria-hidden="false"]` | `.settings-panel.open` |
| 激活 | `is-on` / `active` | `.quick-menu button.is-on` |
| 禁用 | `:disabled` / `--disabled` | `button:disabled` |
| 危险 | `--danger` | `.zz-button--danger` |
| 监听/发送（专属） | 维持语义 | `.os-dock-btn.listening` |

---

## 4. 禁止事项（纪律）

- ⛔ 禁止新增无 `zz-` 前缀的「通用组件类」。新组件一律 `zz-*`。
- ⛔ 禁止为同一组件创建第二套 class（如同时有 `.zz-panel` 与 `.my-panel`）。
- ⛔ 禁止在 `styles.css` 新增组件定义（收敛至 `ui2.css` 令牌天花板）。
- ⛔ 禁止用内联 `style=` 写组件视觉（除动态计算的极少数运行时值）。

---

## 5. 执行门控

- 本 Task 仅立规范，**不机械改写**。
- 旧类改写经 Task F 试点（低风险子集）与 Review 门控（中/高风险子集）。
- 缺失组件实现留待后续 Sprint，本 Sprint 仅预留命名，不新增功能/架构。

---

## 6. 纪律合规

- ✅ 仅立命名规范，未改任何文件。
- ✅ 规范与现有 `zz-` 体系（zz-icon/zz-toggle/zz-panel）一致。
- ✅ 未新增功能/组件/页面。
