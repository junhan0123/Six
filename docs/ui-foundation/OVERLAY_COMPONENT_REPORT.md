# Task D · Overlay 组件审计（OVERLAY_COMPONENT_REPORT）

> Sprint：Xiao6 Component System Sprint v1.0
> 范围：Dialog / Modal / Toast / Notification / Popover
> **本 Task 仅分析，不重构（纪律红线）** — 确认是否存在重复 Overlay 系统，明确风险

---

## 1. 审计范围与方法

- 扫描 `overlay-runtime.js` 及相关 `*overlay` / `.modal-card` / `.toast` 定义与使用。
- 排除：`python/Doc`、`vendor`、测试桩。
- 目标：回答「是否存在第二套 Overlay 系统？」

---

## 2. 当前 Overlay 结构

### 2.1 管理器（唯一）✅
- **`overlay-runtime.js`** — 中央 Overlay 运行时，统一负责：开关、层级（z-index）、进入/离开动画、焦点陷阱、ESC 关闭。
- 所有弹窗（设置/系统提示/能力/引导）均经此管理器，无第二套独立管理器。

### 2.2 背景层（4 个容器）
| 容器 | 位置 | 用途 |
|------|------|------|
| `.settings-overlay` | index.html:461 | 设置背景 |
| `.sysprompt-overlay` | index.html:1137 | 系统提示背景 |
| `.cap-overlay` | index.html:1150 | 能力背景 |
| `.onb-overlay` | index.html:1173 | 引导背景（hidden 默认） |

均经 `overlay-runtime.js` 控制显隐（`.show` / `aria-hidden`）。

### 2.3 内容层（分散）⚠️
| 内容类 | 定义位置 | 承载组件 |
|--------|----------|----------|
| `.modal-card` | styles.css:2475 + premium.css 装饰 | Dialog/Modal 主体 |
| `.onb-card` | premium.css:183 + ui2.css:576 | 引导内容 |
| `.toast` (+.show) | styles.css:532 | Toast/Notification |
| `.proactive-toast` | ui2.css:367 上下文 | 主动通知 |

### 2.4 分布统计
- styles.css：44 行（modal/overlay/modal-card 定义）
- app.js：29 行（overlay 管理调用）
- userprofile.js：12 行（用户资料 overlay）
- premium.css：6 行（装饰 ::before/::after/header）
- weather-modal-preview.html：2 行（天气模态预览，独立页面）

---

## 3. 是否存在「第二套 Overlay 系统」？

**结论：否（单一管理器）。** 但存在**内容层/背景层分散**问题：

| 检查项 | 结果 |
|--------|------|
| 第二套 Overlay 运行时 | ❌ 不存在（仅 overlay-runtime.js） |
| 第二套背景层机制 | ❌ 不存在（4 个 `*overlay` 均受同一管理器） |
| 内容层样式统一 | ⚠️ 不统一（modal-card/onb-card/toast 分散在 styles.css/premium.css/ui2.css） |
| Dialog vs Modal 区分 | ⚠️ 无区分（Dialog 即 Modal 的 modal-card 形态，无独立 Dialog 组件） |
| Popover | ❌ 无（Dropdown/Menu 用独立 ad-hoc 实现，见 Task A §3.11/3.12） |

---

## 4. 风险明确（供 Review）

| 风险 | 等级 | 说明 |
|------|------|------|
| 内容层样式分散 | 中 | modal-card 装饰在 premium.css、结构在 styles.css，改一处需跨文件核对 |
| Dialog/Modal 无类型区分 | 中 | 未来若需不同尺寸/行为的对话框，缺乏扩展点 |
| Popover 缺失 | 低 | Dropdown/Menu 用 ad-hoc，非 Overlay 系统，一致性弱 |
| 天气模态预览独立页 | 低 | weather-modal-preview.html 与主样式可能漂移（需 Task G 核对） |

---

## 5. 本 Sprint 处理边界

- ⛔ **不重构** Overlay 系统（纪律红线：Task D 仅分析）。
- ✅ 仅确认「单一管理器、无第二套」结论，记录内容层分散风险供后续 Sprint。
- ✅ Task F 迁移**不包含**任何 Overlay/Dialog/Modal（仅 Button/Panel 低风险试点）。
- ✅ Task G 验证将覆盖 Dialog/Overlay 的显示与主题兼容（不改代码，仅验证现状无回归）。

---

## 6. 纪律合规

- ✅ 仅分析、记录，未改动任何 HTML/JS/CSS。
- ✅ 未新增/重构 Overlay 运行时、未改动画/层级逻辑。
- ✅ 未改变用户流程与信息架构。
