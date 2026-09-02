# Task B · 组件分类体系（COMPONENT_ARCHITECTURE）

> Sprint：Xiao6 Component System Sprint v1.0
> 目标：建立四层组件分类架构，明确归属与依赖方向（仅规划，不改动代码）

---

## 1. 四层架构总览

```
┌─────────────────────────────────────────────────────────────┐
│  Application 应用层  （业务面板/场景容器，直接消费下层）          │
│   Workspace / Galaxy / Settings / Capability / Memory / ...   │
├─────────────────────────────────────────────────────────────┤
│  Composite 组合层 （多 Primitive 组合 + 行为）                  │
│   Dialog · Modal · Overlay · Notification(Toast) · Menu ·     │
│   Dropdown · Tabs · Tooltip · Command Item                    │
├─────────────────────────────────────────────────────────────┤
│  Primitive 原语层 （最小可复用 UI 单元，令牌驱动）              │
│   Button · Panel · Card · Input · Textarea · Select · Toggle  │
├─────────────────────────────────────────────────────────────┤
│  Foundation 基础层 （非组件，全局原子）                         │
│   Design Token · Icon(.zz-icon) · Motion · Color/Theme        │
└─────────────────────────────────────────────────────────────┘
```

**依赖方向（硬性）**：上层 → 下层，禁止反向（Primitive 不得依赖 Composite；Application 不得绕过 Primitive 直接写样式）。

---

## 2. 各层组件清单与现状

### Foundation（基础层）
| 原子 | 状态 | 位置 |
|------|------|------|
| Design Token | ✅ 单一权威 = `ui2.css :root` + `[data-theme]` | ui2.css |
| Icon | ✅ `.zz-icon` 单一图标语言（Phase 1 完成） | ui2.css / index.html sprite |
| Motion | ✅ `--motion-*` / `--ease-*` | ui2.css |
| Color/Theme | ✅ 深/浅/系统三主题 | ui2.css |

### Primitive（原语层）
| 组件 | 状态 | 统一基准 | 备注 |
|------|------|----------|------|
| Button | 🔴 碎片 ≥11 | `.btn`（ui2.css:562） | 天花板已立，少采用 |
| Panel | 🔴 碎片 8 | 待定（`.zz-panel`/`.glass-panel`） | Phase 1 已令牌化 |
| Card | ⚠️ = Panel 子形态 | 随 Panel | — |
| Input | 🟡 3 类名 | 待补 `.zz-input` | 结构单，风险低 |
| Textarea | 🟢 单实现 | `.hs-chat-input textarea` | 无需合并 |
| Select | 🟢 单实现 | `.settings-select` | 无需合并 |
| Toggle | ✅ 已统一 | `.zz-toggle` | Phase 1 完成（范例） |

### Composite（组合层）
| 组件 | 状态 | 实现位置 | 说明 |
|------|------|----------|------|
| Dialog | ❌ 无正式类 | Overlay 子系统 | modal-card + overlay-runtime.js |
| Modal | ⚠️ 耦合 Overlay | `.modal-card` + `*overlay` | 见 Overlay |
| Overlay | 🟡 单一管理器 | `overlay-runtime.js` | 内容层分散（Task D 审计） |
| Notification(Toast) | 🟡 2 套 | `.toast` / `.proactive-toast` | 低风险可别名 |
| Menu | ❌ 无正式类 | `.more-menu-wrap` / `.quick-menu` | ad-hoc |
| Dropdown | ❌ 无正式类 | `.more-dropdown` | ad-hoc |
| Tabs | ❌ 无正式类 | `.settings-tab` / `.mem-tabs` | ad-hoc |
| Tooltip | ❌ 无正式类 | `.hint` | ad-hoc |
| Command Item | 🟢 既有 | Command Palette | 复用 Primitive |

### Application（应用层）
| 面板 | 当前承载类 | 归属层 |
|------|-----------|--------|
| Workspace Panel | `.zz-panel` / `.os-panel` | Primitive(Panel) |
| Galaxy Panel | `.glass-panel` | Primitive(Panel) |
| Settings Panel | `.settings-panel` / `.settings-card` | Primitive(Panel) |
| Capability Panel | `.cap-overlay` + 内容 | Composite(Overlay) |
| Memory Panel | `.memory-panel` | Application |
| Onboarding | `.onb-overlay` + `.onb-card` | Composite(Overlay)+Primitive |

---

## 3. 文件归属约定（目标态）

| 层 | 应驻留文件 | 说明 |
|----|-----------|------|
| Foundation 令牌 | `ui2.css` | 唯一权威，末加载覆盖 |
| Primitive 通用类 | `ui2.css`（增量层）或 `styles.css` 收敛后迁入 | 单一天花板 |
| Feature 专属样式 | `premium.css` / `companion.css` / `execution-channel.css` / `runtime-viz.css` | 仅 feature 内使用 |
| 巨型遗留 `styles.css` | 逐步收敛，不再新增组件定义 | 199KB，技术债来源 |
| Overlay 行为 | `overlay-runtime.js` | 唯一管理器 |

> **禁令**：禁止在 `styles.css` 新增组件 class 定义；新组件一律走 `ui2.css` 令牌天花板 + `zz-` 命名。

---

## 4. 缺失组件的处理原则（本 Sprint）

Dialog / Dropdown / Menu / Tabs / Tooltip **本 Sprint 不实现**（纪律红线：不新增功能/架构）。
在架构中**预留位置**（Composite 层），命名规范（Task E）预留 `zz-dialog` / `zz-dropdown` / `zz-menu` / `zz-tabs` / `zz-tooltip`，待后续 Sprint 实现时直接落入，避免再次出现 ad-hoc 命名。

---

## 5. 纪律合规

- ✅ 仅规划分类，未改动任何文件。
- ✅ 架构遵循「单一来源 / 依赖单向」原则。
- ✅ 未新增页面/组件/架构（缺失组件仅预留，不实现）。
