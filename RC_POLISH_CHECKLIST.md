# RC Polish Checklist — Xiao6 RC Polish Sprint v1.0

> **身份**：Senior Frontend Engineer + Design System Guardian
> **任务**：P4 自动回归验证
> **日期**：2026-08-05
> **纪律**：仅自动化验证 / 文档；无功能 / 逻辑 / 架构变更。
> **目标**：验证 9 大子系统 + 全局工程纪律，确保 RC Polish **0 回归**。

---

## A. 子系统回归矩阵

| 子系统 | 标识符 / 文件 | 静态存在 | 前端回归 | 缓存炸弹 | 结论 |
|---|---|---|---|---|---|
| **Electron 壳** | `electron/main.js`、`preload.js`（Companion 第二窗口 + `companion:action` IPC 桥） | ✅ | 16 PASS / 0 新增失败 | — | ✅ |
| **Web 预览** | `index.html` + `*.css`（无壳直开） | ✅ | 16 PASS / 0 新增失败 | 已 bump（见 §C） | ✅ |
| **设置中心** | `settings` 面板（`.settings` / `settings-` 选择器） | ✅ | 0 新增失败 | 已 bump | ✅ |
| **Command Palette** | `command-palette.js`（指令坞 / Quick Command） | ✅ | 0 新增失败 | 已 bump | ✅ |
| **Galaxy** | `solar-system.js` / `#solarCanvas`（太阳系背景） | ✅ | 0 新增失败 | 已 bump | ✅ |
| **Workspace** | `.app`×15 / `.chat-area`×7（主工作区） | ✅ | 0 新增失败 | 已 bump | ✅ |
| **Dialog** | `.modal`×57（对话框） | ✅ | 0 新增失败 | 已 bump | ✅ |
| **Overlay** | `overlay` 运行时层 | ✅ | 0 新增失败 | 已 bump | ✅ |
| **Notification** | `notification` / `toast`（通知） | ✅ | 0 新增失败 | 已 bump | ✅ |

> 说明：前端测试套件覆盖上述 9 子系统关键交互；本次 CSS / Icon / Token 收敛均经缓存炸弹强制刷新，确保加载到统一后的样式。**0 新增失败**。

---

## B. 全局工程验证

| 检查项 | 方法 | 结果 |
|---|---|---|
| CSS 括号平衡 | 6 文件 `count('{') == count('}')` 断言 | ✅ 通过 |
| `var()` 解析 | 新令牌均在 `ui2.css :root` 定义 | ✅（除预存 `--sw` 3 处，非本次引入） |
| JS 语法 | `node --check`：main / preload / app / companion / avatar-* | ✅ 全部 OK |
| 前端测试 | 16 套 PASS | ✅ 0 新增失败（3 预存在失败与本次无关） |
| 纪律 grep | 改动文件无 `new Runtime/EventBus/Memory/Agent/Tool`、`/api/` fetch、架构变更 | ✅ 清洁 |

---

## C. 缓存炸弹（强制刷新，避免旧 CSS 缓存）

`index.html` 已更新 `?v=`：

| 资源 | 旧 | 新 |
|---|---|---|
| `styles.css` | … | `20260805s2` |
| `premium.css` | … | `20260805p2` |
| `runtime-viz.css` | … | `20260805r1` |
| `execution-channel.css` | … | `20260805e1` |
| `ui2.css` | … | `20260805u5` |

---

## D. 纪律红线符合性

| 红线（禁止） | 检查结果 |
|---|---|
| 新增业务功能 | ✅ 无 |
| 修改业务逻辑 / 交互流程 | ✅ 无 |
| 修改架构 / API / 数据结构 | ✅ 无 |
| 修改 EventBus / Goal Runtime / Memory Runtime | ✅ 无 |
| 修改 Golden State | ✅ 无 |

| 允许项 | 执行 |
|---|---|
| UI 一致性收敛 | ✅ Motion / Icon / Token |
| Design Token 收敛 | ✅ 定义层 + 别名 |
| Icon System 收敛 | ✅ 零视觉变更 |
| Motion System 收敛 | ✅ 265 时长 + 21 缓动路由 |
| 样式重复清理 | ✅ 3 重复令牌消除 |
| 文档更新 | ✅ 5 份报告 |
| 自动化验证 | ✅ 本清单 + 各报告 Verify 节 |

---

## E. 结论

9 大子系统静态存在性 ✅、前端回归 0 新增失败 ✅、全局工程检查全绿 ✅、缓存炸弹已 bump ✅、纪律红线零触碰 ✅。

**RC Polish：0 回归，可进入人工 Review。**
