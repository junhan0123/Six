# 07 — Workspace Performance（仅 UI）

> Sprint #623 · 性能优化，**仅 UI 层**；不触碰后端 / Runtime / 渲染管线。

## 1. 本 Sprint 的性能立场

统一工作空间是**收口与重组**，不是新增渲染。性能收益来自"去重"与"复用"，而非新增机制：

| 项 | 说明 |
|----|------|
| 零新增监听器 | `PanelManager.init()` 仅绑定一次按钮 click；不新增 `keydown` / `resize` / `mutation` 监听（Companion 已有的 `MutationObserver` 为既有，未改） |
| 零轮询 | 未引入任何 `setInterval` 文件监视 / 状态轮询（知识层 Watcher 属独立 Sprint，不在此） |
| O(REG) 一次性包裹 | `init()` 遍历 17 个注册项包裹 `open`/`close`，运行时开销可忽略 |
| 状态读取无重渲染 | `WorkspaceState` 为纯 localStorage 读写，`focus`/`pin` 仅更新内存 + 持久化，不触发全树重渲染 |
| 复用 OverlayManager | 浮层开关 / 焦点 / z-index 继续走既有高效路径，无重复 DOM 查询 |

## 2. 明确不做（防越界）

- 不做虚拟列表 / 懒加载（属各面板自身优化，不在 v2.0 范围）。
- 不优化 Three.js / 太阳系渲染（Background 层，属 Galaxy Runtime，禁止进入）。
- 不引入新的状态订阅框架（复用 `AppState.subscribe` / `OverlayManager`）。

## 3. 可观测性建议

- `WorkspaceState` 读写频率极低（仅用户操作），无需性能埋点。
- 若后续发现某面板 open 卡顿，应在该面板模块内优化，不归咎于统一层。

> 下一步：#624 Workspace UX Polish（Loading/Empty/Skeleton/Transition）。
