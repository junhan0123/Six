# Overlay Implementation Sprint — Step [1] Z-index 令牌化 · 完成报告

- **日期**：2026-08-05（续做）
- **步骤**：`OVERLAY_MIGRATION_PLAN.md §5` 顺序首步 `[1] P0-2 Z-index 令牌化`
- **纪律**：零行为变更优先 · 单值来源 + 别名兼容层 · 可回滚 · 静态验证（GUI 属 LIVE 边界，未编造）
- **状态**：✅ 静态验收全部 PASS · 等待进入 Step [2]

---

## 1. 改了什么

| 文件 | 改动 |
|------|------|
| `ui2.css` | 将原「死令牌」单行 6 档（`--z-base:1 … --z-companion:9999`）扩为 **29 个命名令牌的完整单调阶梯**（覆盖主窗口全部 z-index 实值）。`--z-modal` / `--z-toast` 改为指向 `--z-overlay` 的兼容别名。 |
| `styles.css` | **62 处**裸数字 `z-index:N` 全部路由为 `z-index: var(--z-<tier>)`。数值不变。 |
| `premium.css` | **1 处** `.onb-overlay z-index:9999` → `var(--z-onboarding)`。 |
| `index.html` | 三个 CSS 缓存版本 bump：`s3→s4`、`p3→p4`、`c3→c4`（强制刷新）。 |

**备份**：`styles.css.bak.zzstep1` / `premium.css.bak.zzstep1`（同目录）。

---

## 2. Z-index 令牌阶梯（单一来源 · 数值 1:1 对应现状）

| 图层 | 令牌 | 值 | 用途 / 路由到的旧选择器 |
|------|------|----|------------------------|
| 基线 | `--z-ground` | 0 | `.bg-glow` 等背景辉光 |
| 背景 | `--z-base` | 1 | `.premium-bg` |
| 舞台 | `--z-stage` | 2 | `.app` / `.orb-canvas-main` / 内层 hud |
| 舞台装饰 | `--z-stage-deco` | 3 | `.loc-readout` |
| 语音球 | `--z-orb` | 4 | `.orb-wrap` |
| 轨道 | `--z-rail` | 5 | 布局模块 / 热点内层遮罩 |
| 浮起 | `--z-raised` | 7 | 浮起面板 |
| 内容 | `--z-content` | 18 | `.chat-history` / `.scene-layer` |
| HUD | `--z-hud` | 20 | HUD 读数 |
| 气泡 | `--z-popover` | 30 | tooltip / `.tele-open` / `.wx-suggest` |
| 扫描线 | `--z-scanlines` | 40 | `.scanlines` |
| 浮动标签 | `--z-float` | 55 | `.mem-tag` 浮标 |
| **模态底层** | `--z-overlay` | 60 | 全屏面板（mem/video/map/doc/review/sysmon/term/wc/briefing）+ `.toast` |
| 模态底层+ | `--z-overlay-raised` | 61 | `.memq-panel` |
| 设置遮罩 | `--z-mask` | 80 | `.settings-overlay` |
| 设置面板 | `--z-panel` | 81 | `.settings-panel` |
| 对话遮罩 | `--z-dialog-mask` | 82 | `.sysprompt-overlay` / `.cap-overlay` / `.mic-overlay` |
| 对话面板 | `--z-dialog` | 83 | `.sysprompt-panel` / `.cap-panel` |
| 任务遮罩 | `--z-task-mask` | 85 | `.zz-task-overlay` |
| 任务面板 | `--z-task` | 86 | `.zz-task-panel` |
| 指令面板 | `--z-command` | 90 | `.cp-overlay` |
| 抽屉 | `--z-drawer` | 95 | `.zz-panel` |
| 顶层 | `--z-top` | 100 | 热重载 / 地球提示 |
| 下拉 | `--z-menu` | 200 | `.more-dropdown` |
| **模态遮罩** | `--z-modal-mask` | 9000 | `.modal-mask`（主窗口最高） |
| 桌宠 | `--z-companion` | 9999 | 独立 Electron 窗口层级 |
| 引导 | `--z-onboarding` | 9999 | `.onb-overlay`（premium.css） |
| 兼容别名 | `--z-modal` | =60 | 指 `--z-overlay` |
| 兼容别名 | `--z-toast` | =60 | 指 `--z-overlay`（Step[5] 再提层） |

> 旧审计所谓的「9000/200/95 倒挂」现已**命名化**：数字原样保留为令牌值，堆叠顺序零变化；语义归并（如把 toast 从 60 提层）留待 Step [5]，且必须经 GUI 验收。

---

## 3. 静态验收（见 `zz_verify_zindex.py`）

| 项 | 结果 |
|----|------|
| 无残留裸数字 z-index（styles/premium） | PASS（0 处） |
| 所有引用令牌均已定义 | PASS（26 引用 / 29 定义，0 悬空） |
| 三文件花括号平衡 | PASS |
| ui2.css 最后加载（cascade 胜出） | PASS |

---

## 4. 零行为变更论证

- 每个令牌的值 == 被替换前的裸数字，CSS 自定义属性在计算期解析，解析结果与旧值逐位相同。
- `--z-modal` / `--z-toast` 原值为 60 / 82，但二者在原代码中**均未被引用**（死令牌）；将其改为指向 `--z-overlay`（=60）仅影响「未来若有人引用这两个别名」的语义，不对任何现存渲染产生作用。`.toast` 实际一直位于 60，本次仍落 60，行为不变。
- 未改动任何 HTML / JS / 选择器名 / 视觉属性。

---

## 5. 范围外（明确递延）

- **`companion.css`（z-index 1/2/3/10/11/12/13）**：属独立 Electron 桌宠窗口的**内部栈**，不与主窗口 overlay 竞争。按 `OVERLAY_MIGRATION_PLAN` 留 Step [6] 经 IPC 复用主窗 `zz-*` 原语，本次未动。
- **实际堆叠重排**（如 toast 提层、合并 60/61、消歧 modal 语义）：属 Step [5] 语义归并，需 Electron GUI 真机验收，本次不做。

---

## 6. 回滚预案

```bash
cd G:/xiao6/xiao6-ui
cp -f styles.css.bak.zzstep1      styles.css
cp -f premium.css.bak.zzstep1     premium.css
# index.html 将三处 ?v= 回退 s4→s3 / p4→p3 / c4→c3
# 或使用 git：git checkout -- xiao6-ui/styles.css xiao6-ui/premium.css xiao6-ui/ui2.css xiao6-ui/index.html
```

---

## 7. 下一步

→ **Step [2]**：在 `ui2.css` 落地 `zz-overlay` / `zz-dialog` 原语（遮罩 + backdrop + ESC + 点击外部 + 焦点陷阱 + inert），为 Step [3] 中央分发器与后续 legacy 路由提供统一基类。建议审批后继续。
