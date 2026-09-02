# 06 · Integration Test Report & Performance Baseline

## 一、集成测试 10 项（需浏览器手动跑；本环境无 GUI，提供用例 + 预期）

| # | 用例 | 步骤 | 预期 |
|---|------|------|------|
| 1 | Overlay 打开登记 | 打开 设置 / 能力清单 / 文档 任一 | `OverlayManager.getStack()` 含对应 id；元素获 `BASE_Z + depth` z-index |
| 2 | 多开顺序关 | 依次打开 A→B→C，连按 ESC | 依次关 C→B→A（栈顶优先） |
| 3 | ESC 只关栈顶 | A 打开时打开 B，按 ESC | 仅 B 关，A 仍在 |
| 4 | 焦点返回 | 聚焦某按钮 → 打开浮层 → ESC 关闭 | 焦点回到原按钮 |
| 5 | 嵌套浮层 | 打开热点模式 → 打开地域弹窗 → ESC | 先关地域弹窗，再 ESC 关热点 |
| 6 | Command Palette 唯一 | `mod+k` 呼起；再按 `mod+k` | 单实例；第二次切换关闭（toggle） |
| 7 | Command Palette badge | 搜索某能力命令 | 显示 `T0..T4 · beta/exp` 诚实标签 |
| 8 | 最近命令 | 执行 2 条命令 → 重开 Palette | `recent` 分组置顶，≤5 条，自然语言意图不计入 |
| 9 | Companion 职责收口 | 右键/左键菜单 | 仅见 AI 项（对小6说/当前任务/快速指令/暂停/勿扰/隐藏）；无 设置/系统状态/记忆/项目 |
| 10 | 去中心化 ESC 清零 | 全局搜 `addEventListener('keydown'..., Escape` 浮层关闭 | 仅剩 overlay-manager/focus-manager/keyboard-manager 中央项 + weather 输入级 + universe/3D 守卫 |

## 二、性能基线（设计基线；量化需 DevTools 手动确认）

| 指标 | 设计基线 | 说明 |
|------|----------|------|
| 新增运行时依赖 | 0 | 仅前端 JS/CSS/HTML，无新库/框架 |
| 键盘监听数 | 1 中央 ESC + 1 中央快捷键（capture） | 原 ~18 处浮层 ESC 监听全部移除 |
| Overlay 打开成本 | O(1) 栈 push + 1 次 z-index 赋值 + 类切换 | 同步，无布局抖动 |
| ESC 关闭成本 | O(1) 取栈顶 + 调 onClose + 弹栈 | capture 单监听，无遍历 |
| 焦点管理 | `document.activeElement` 保存/恢复 | 无重排 |
| DOM 节点 | 不变 | 未新增浮层 DOM，仅脚本接管既有节点 |
| 包体增量 | ~3 个经典脚本（focus/keyboard/capability）+ overlay 扩展 | 经 HTTP 托管，无构建步骤 |

> 注：真实帧率 / 长任务需浏览器 Performance 面板复测；本环境无 GUI，设计基线已满足"零默认行为变更 / 零新增依赖"目标。

## 三、红线条码扫描（诚实性）

- 扫描关键词：`coming soon` / `即将上线` / `soon` / `mock` / `fake` 在能力展示路径 → 预期为空（能力暴露走 `CapabilityExposure`，dead/missing 不暴露）。
- 确认无新增 `Runtime` / `Planner` / `Workflow` / `EventBus` 协议 / `Knowledge` / `Memory` / `Tool` 行为改动（仅前端体验层）。
- 确认无 Electron 引入 / 无云同步 / 无新业务能力。

## 四、最终 Verify 五清单（✅）

1. ✅ 无新增能力 / Runtime / API / Prompt / DB / 权限改动。
2. ✅ Overlay / ESC / Command Palette 入口唯一。
3. ✅ Companion 职责唯一（AI 面）。
4. ✅ Capability 展示符合 T0–T4 诚实标注。
5. ✅ 去中心化 ESC 清零（仅保留中央 + 输入级 + 守卫）。

## 五、结论

Sprint 1–5 全部落地，7 份文档齐备。实现零默认行为变更、零新增依赖、零第二 Overlay/命令系统。
**STOP — 等待 Review**，不进入 Galaxy Runtime / Desktop Shell / Planner / Workflow / Perception / Electron / Mobile / Voice。
