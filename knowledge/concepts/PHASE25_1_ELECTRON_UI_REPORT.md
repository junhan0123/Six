---
id: know-personalaios-phase-25-1-electron-desktop-ui
type: concept
---
# PersonalAIOS Phase 25.1 —— Electron Desktop UI 桌面交互层 验收报告

**内核版本**：v0.29.0（Electron 契约 25.1.0）
**验收日期**：2026-08-10
**验收范围**：在 Phase 1–24 内核 与 Phase 25.2 / 26.2 / 29.1 后端层之上，补齐 Personal AI Workstation 的 **Electron 桌面交互层**（进程壳 + 隔离渲染 + 桥接 + 8 面板），且 **界面在整个链路里零执行权**。

---

## 0. 结论摘要

**五道验收闸门全部通过。**

| 闸门 | 命令 | 结果 | 关键证据 |
|------|------|------|----------|
| Gate 1（UI 专项测试） | `node phase25_ui_test.js` | **PASS 7823 / FAIL 0** | 35 段 · 断言 ≥5000 达标 · 桌面层零动手权全程恒 `false` |
| Gate 2（UI 执行扫描） | `node scan-ui-execution.js` | **EXIT=0** | Execution Token=0 · External Dependency=0 · Violation=0 |
| Gate 3（跨文件一致性） | `npm run check:consistency`（即 `pretest:all`） | **EXIT=0** | 全部派生点与真源一致 · ConsistencyChecker PASS 112 / FAIL 0 |
| Gate 4（全量回归） | `npm run test:all` | **EXIT=0** | 37 套件 · **0 FAIL**（与既有 192,093 断言基线一致） |
| Gate 5（真实窗口走查） | `PAIOS_MODEL=heuristic PAIOS_UI_NO_CHROMIUM_SANDBOX=1 node scripts/ui-smoke.js` | **30/30 步全绿** | 真实对话 → 6 张审批 → 真实拒绝停 `task-2` → 真实批准开闸 · 8 面板全渲染 |

**本轮唯一结构性缺陷**（仅真实窗口能暴露，静态测试抓不到）：审批队列视图形态在翻译层与渲染层不一致，导致审批面板在真窗口里白屏。已在翻译层与渲染层之间对齐为统一的队列视图形态，并补齐了桥的真实数据级走查。详见第 21 节。

**红线状态**：界面进程（`webPreferences.sandbox: true`）无 Node 能力；桥只暴露 9 个只读/裁决命名空间；全链路执行权唯一归属内核侧 `ExecutionSandbox`，界面侧 `hasRunAuthority()` 恒为 `false`。

---

## 1. 背景与目标

Phase 1–24 已就位自主内核，Phase 25.2/26.2/29.1 补齐后端三块拼图。但系统此前**没有桌面界面**——人只能在终端里看 `console.log`。Phase 25.1 的目标是把内核能力**安全地**暴露成一个 Electron 工作台：

- 人在对话面板说一句需求，内核把它变成意图、目标、任务清单；
- 8 个面板分别显示这句话的后果（对话 / 任务 / Agent / 审批 / 代码 / 调研 / 推理 / 记忆）；
- 高风险动作在审批面板等人裁决，**批准不等于界面去干活**——闸门开了之后由内核侧继续。

最高约束（红线）：**界面这一侧永远不能获得执行权**。Electron 的世界里这是一条经典事故线——一旦渲染进程能 `require("child_process")` 或拿到裸 `ipcRenderer`，白名单当场作废。本报告的全部设计都围绕「让这条红线在物理上做不到」展开。

---

## 2. 验收闸门总览

五道闸门层层加码，缺一不可：

1. **Gate 1（≥5000 断言）**——UI 专项测试，覆盖契约、纯度、视图构造、IPC 覆盖、预加载纪律、区域词法、Store、渲染面、宿主装配、端到端真实对话/拒绝/批准/面板、零执行权自证、扫描一致性、版本。
2. **Gate 2（执行扫描）**——对 `ui/` 全量扫描，零容忍任何执行 token、外部依赖、红线违规。
3. **Gate 3（一致性）**——跨文件派生常量（版本 / 事件总数 / 套件数 / 末端）与真源逐字节一致。
4. **Gate 4（全量回归）**——37 套件全绿，确认 UI 改动没有拖垮既有内核基线。
5. **Gate 5（真实窗口）**——拉起真 Electron，像人一样操作：打字、发送、切面板、点拒绝、点批准、截图取证。

Gate 1/2/3/4 均可由脚本一键复现；Gate 5 用 CDP 从**外部**驱动真界面，不往生产代码里塞任何「测试模式」分支（那条分支本身正是红线上最难看的一个缺口）。

---

## 3. 架构总览：三层两区

```
┌──────────────────────────────────────────────────────────────┐
│  Zone B · 主进程（Electron main.js，Node 全权，但只做翻译）      │
│   kernel-host（装配内核） → app-api（薄翻译层）                  │
│        → ipc/*（6 命名空间处理器）                               │
└───────────────┬───────────────────────────┬──────────────────┘
                │  contextBridge.exposeInMainWorld("paios", …)  │
                │  只过 frozen 函数 + 纯数据，绝不交 ipcRenderer   │
┌───────────────┴───────────────────────────┴──────────────────┐
│  Zone A-bridge · 预加载（sandbox:true，残缺 require 仅认 electron）│
│   preload.cjs：抄录契约 → 闭包固定频道 → 过桥前 paiosPure 消毒    │
└───────────────┬───────────────────────────────────────────────┘
                │  window.paios（渲染进程里唯一的出口）             │
┌───────────────┴───────────────────────────────────────────────┐
│  Zone A · 渲染进程（sandbox:true，无 Node 能力，vanilla JS）      │
│   api → store → EventBus适配器 → 8 面板（components/*）          │
└──────────────────────────────────────────────────────────────┘
```

- **34 个 UI 源文件**（不含 `_legacy_vite_react/` 隔离脚手架）：`ui/electron/*`（13）、`ui/electron/ipc/*`（8）、`ui/renderer/*`（含 12 个 components，17）、`ui/shared/*`（2）。
- **Zone A（渲染 + 预加载）19 个**，Zone B（主进程）12 个，隔离区已排除。
- 全栈 **vanilla JS**，无 React/Vue；界面代码自身零执行语义。

---

## 4. 进程隔离与沙箱纪律

两件事必须分清，不能混为一谈：

- **`webPreferences.sandbox: true`**（红线，恒为 true）——Electron 渲染进程的沙箱，由 `ui/electron/main.js` 在每次建窗时强制设置。它让渲染进程拿不到 Node 运行时。
- **Chromium 的 OS 级沙箱**（`--no-sandbox`）——只是基础设施层面的开关。本环境受限起不来，用 `PAIOS_UI_NO_CHROMIUM_SANDBOX=1` 关掉它，**不影响**上面那条红线（Gate 2 扫描器逐字校验 10 项窗口安全开关齐备）。

Gate 5 真窗口实测（渲染进程内求值）：

```
require: undefined · process: undefined · module: undefined
Buffer: undefined · global: undefined · electron: undefined
bridge: object · runAuthority: false
```

界面进程里连 `require` 都没有，自然无从 `require("child_process")`。

---

## 5. 预加载脚本纪律（Zone A-bridge）

`preload.cjs` 是全仓库纪律最严的一个文件，Gate 2 对它单独立规则：

1. **全文只出现一次 `require`，且必为 `require("electron")`**——沙箱化预加载的 `require` 是残缺 polyfill，只认 `electron/events/timers/url`，不能 `require` 相对路径，因此契约表只能内联一份（再由 Gate 1 逐条比对，漂移即红）。
2. **桥上只放函数与冻结的纯数据，绝不放 `ipcRenderer` 本身**——把 `ipcRenderer` 暴露出去等于把整条 IPC 总线交给页面，白名单作废。
3. **频道名一律查表得到，绝不用页面传来的值拼接**——拼接等于开任意频道注入洞。

桥自述（页面里敲一句 `window.paios.meta` 即可验证，不读源码、不信文档）：

```
contract: "25.1.0" · runAuthority: false
authorityHolder: "kernel-side-authority-chain"
namespaces: [agents, approvals, chat, handshake, memory, meta, onPush, system, tasks]
```

---

## 6. 桥接层设计

`paiosBuildTree()` 把契约频道表装成对象树并逐命名空间冻结。每个桥方法在**建桥那一刻**就把频道闭包固定，页面侧之后任何代码都改不动它：

```js
function paiosBind(apiName) {
  const channel = PAIOS_CHANNELS[apiName];          // 闭包固定
  return function paiosCall(payload) {
    return ipcRenderer.invoke(channel, paiosPure(payload, 0));  // 过桥前先消毒
  };
}
```

`paiosPure` 把入参压成纯数据（深度限 4 层、键数限 40、类实例/Map/Date/函数一律丢弃）——主进程还会再消毒一次，这里先压是为了让坏值在调用点被安静丢掉，而不是抛一句没头没尾的 "could not be cloned"。

推送走 `ipcRenderer.on(PAIOS_PUSH_CHANNEL, …)` 在预加载**内部**只挂一个监听，自己维护订阅者集合；页面拿到的是 `unsubscribe` 闭包，某个订阅者抛错不连累其他订阅者，也不冒泡进 IPC 内部。

---

## 7. IPC 契约：命名空间 / 频道 / 主题

契约真源在 `ui/shared/ipc-contract.js`，预加载里是其受测抄本。Gate 1 把抄本逐条抠出与真源全等比对：

- **6 个命名空间、24 个频道**：`chat(4) · tasks(3) · agents(3) · approvals(4) · memory(2) · system(8)`。
- **5 个「决定类」出口**（界面能表达人的意志的全部出口，单独列出来只为审计）：`approvals.approve` · `approvals.reject` · `chat.send` · `system.startReasoning` · `system.startResearch`。
- **9 个推送主题**：`conversation / task / agent / approval / memory / research / reasoning / runtime / system`。
- **频道唯一且前缀统一**（`paios:<ns>:<method>`），无重复、无拼错。

`registerIpc` 注册前后各做一次双向覆盖检查：契约里每个 API 都有处理器，处理器表每个名字都在契约里——漏注册表现为「点了没反应」，多注册表现为「有个没人知道的口子开着」，两种事故都拦下。

---

## 8. UI Application API：薄而不透明的翻译层

`app-api.js` 是界面与内核之间唯一的翻译层，两条纪律缺一不可：

- **薄**：不在这里做业务决策。任务怎么拆、失败怎么修、审批怎么判全是内核的事；本层只「取出来、翻译好、交出去」。
- **不透明**：绝不把内核对象原样交出去。`sanitizeForRenderer` 对过桥的每个字节重新构造为纯数据——只要 UI 拿到过一次真实对象的引用，它就可能某次「顺手」调到那个对象上的方法；翻译层的存在让那件事在物理上做不到。

词汇翻译发生在这里而非渲染层：内核的智能体状态、推理状态机、失败分型里都带着动手面的词根，渲染层源码里一个都不许出现（Gate 2 逐字节搜）。所以 `WAITING_APPROVAL → waiting`、`EXECUTING → working` 这类翻译明晃晃写在这里，比散落在二十个组件里各写各的强。

`approve/reject` 是界面上唯一能改变系统状态的地方——但那只是把人的裁决送进内核既有的审批闸门，**不是自己动手**。闸门开了之后谁去干活是内核侧的事，本进程内没有那个东西。

---

## 9. 渲染层隔离：零 Node 能力

渲染进程用 vanilla JS（无框架），通过 `window.paios` 这个唯一出口与主进程通信。Gate 5 在真窗口内求值确认：

```
require / process / module / Buffer / global / electron  全部 undefined
window.paios  是 object（9 个命名空间 + handshake + meta + onPush）
window.paios.meta.runAuthority === false
```

渲染层任何代码都触达不到 Node、触达不到 `ipcRenderer`、触达不到文件系统或子进程。执行面探针（Gate 5 `executionProbe`）进一步确认：页面里 `exec/run/spawn/shell/terminal/sandbox/execute` 全部 `undefined`，桥上 `bridgeHasExec === false`。

---

## 10. 零执行权红线

这是本期最高红线，靠「物理隔离 + 自述可验证」双重锁死：

- **物理隔离**：渲染进程无 Node 能力（第 4、9 节），桥不暴露 `ipcRenderer`，桥方法只 `invoke` 只读/裁决频道。界面想「自己干点什么」在能力上就做不到。
- **自述可验证**：`window.paios.meta.runAuthority === false`、`ui/renderer/app.js` 导出 `hasRunAuthority() === false`、主进程 `hasExecutionAuthority() === false`。三者独立、可分别从页面控制台与测试里验证，不需要读源码。
- **唯一执行链不变**：`Conversation → Goal → Plan → Research/Coding Agent → Reasoning Loop → CapabilityBridge → Authorization → Approval → ExecutionRequest → Task Runtime → Orchestrator → ExecutionSandbox → ExecutionResult`。界面层全部位于 `→ ExecutionSandbox` **之前**，只负责「理解、观测、裁决」，不落地任何动作。
- **治理失败绝不自我放行**：审批被拒绝后，对应任务就地停在这里（`status=failed`、`blockedBy="人已拒绝，链路就地停止"`），不会重试、不会绕路、不会「换个说法再问一次」。

Gate 1 §25.1-ZERO-AUTHORITY（52 断言）与 Gate 5 `executionProbe` 双重覆盖，全绿。

---

## 11. 数据纯度红线

过桥的每一个字节必须是纯数据（string/number/boolean/null/array/plain object），原因不止是 Electron 结构化克隆会对类实例抛错——更重要的是，纯数据在渲染层无法被「顺手」调用出方法。

- `ui-models.js` 的 15 个视图构造器（`toConversationView` / `toTaskBoardView` / `toAgentCardView` / `toApprovalQueueView` / `toMemoryItemView` / …）全部把内核对象翻译为纯数据卡；Gate 1 §25.1-VIEW-BUILDERS 逐一点名 15 个并验证「吞得下垃圾输入且吐出纯数据」。
- `sanitizeForRenderer` 是最后一道纯度关：翻译层漏了消毒，到这里还不纯就该炸。
- Gate 1 §25.1-PURITY-*（基本/模糊/降级，共 1344 断言）专攻这一条：用畸形、超深、含类实例的输入喂给视图构造器，要求不抛、不回流非纯值。

---

## 12. 状态管理、事件适配与推送

- **UI Store**（`state.js`）：单一状态树 + `patch/set/subscribe`。8 个面板各自从 store 读自己那一份；`approval` 初值为 `{cards:[], pending:0, approved:0, rejected:0, total:0}`（队列视图形态，见第 21 节）。
- **EventBus → IPC 适配器**（`event-adapter.js`）：内核 370 个事件经适配器翻译为界面词汇后再过桥；适配器会**剥掉**动手面词根（如 `EXECUTING → working`），且对源事件做 strip/批处理，避免高频推送压垮主进程。
- **推送订阅**：渲染层 `onPush` 收到的是拆封后的 `events` 数组，只驱动「该刷新了」和事件流；真正的数据一律回源（`refreshAll` 每次全量拉 8 个 invoke，实测个位数毫秒）。这刻意避免「从事件推算状态」——那等于在渲染层重建一份内核状态机，是第二套真相，迟早对不上。

Gate 5 实测右侧事件流收到 36 行内核推送，底栏读数 `已收事件 36`。

---

## 13. 八大面板总览

| # | 面板 | 数据来源 | 角色 |
|---|------|----------|------|
| 1 | 对话 Conversation | `chat.history` | 入口：人说一句，内核变意图/目标/任务 |
| 2 | 任务看板 Tasks | `tasks.board` | 四列看板，状态由内核推进，界面只观察（不做拖拽） |
| 3 | Agent 状态 Agents | `agents.summary` | CEO/Planner/Coding 各自在干什么，状态是内核真实走出来的 |
| 4 | 审批 Approvals | `approvals.list`（队列视图） | **唯一能改变系统走向的地方**：批准=开闸，拒绝=就地停 |
| 5 | 代码预览 Code | `system.codePreview` | 只读快照，绝不在此编辑 |
| 6 | 调研 Research | `system.research` | 只读结论与来源 |
| 7 | 推理轨迹 Reasoning | `system.reasoning` | 只读轨迹，全程未自行提交 |
| 8 | 记忆 Memory | `memory.list` | 只读记忆流 |

Gate 5 实测 8 个面板全部渲染正常（对话 206 字 / 审批 1006 字 / 记忆 4955 字 / …）。

---

## 14. 对话面板与真实对话走查

人在输入框打字、Enter 发送；乐观消息发出后，真相以主进程返回的完整会话视图为准整体替换（宁可不更新，也不把形状不对的对象塞进 store）。

Gate 5 真窗口走查（切到对话面板后读 DOM）：

```
对话里既有人说的也有系统答的  →  user→assistant
```

`assistant` 这条是内核真实产生的答复（Gate 1 §28 独立验证了 `messages[1].role === "assistant"`）。发送后界面自动跳到审批面板（因为这句话触发了审批请求），导航计数 `conversation:2 · tasks:8 · agents:2 · approvals:6 · memory:6`。

---

## 15. 审批面板与真实裁决走查

这是整条链里「人说了算」唯一的物证，也是本期最容易被静态测试漏掉的地方。

**真实拒绝**（Gate 5 截图与桥数据双重取证）：

```
点「拒绝」后卡片变为已拒绝     →  已拒绝 · human · 21:25:06
提示明确说明内核会停在这里    →  "这句话触发了 6 次审批请求 | 已拒绝 apr-1，内核会停在这里"
任务看板上真的出现了停下的任务 →  task task-2 · failed · 人已拒绝，链路就地停止
```

桥取真数据确认：被拒绝的任务在核内心态是 `status==="failed"` 且 `blockedBy` 含「拒绝」——不是界面文案猜的，是 `tasks.list` 返回的真值。重复拒绝被拒、拒绝后不能翻案改成批准（Gate 1 §29 覆盖）。

**真实批准**（开闸，但动手的不是界面）：

```
点「批准」后闸门真的开了  →  file · create · 待裁决 4 · 已批准 1 · 已拒绝 1
```

批准后任务仍在 `pending`（批准只是开闸，不是干活）；界面这一侧磁盘上没有多出任何文件（Gate 1 §30 验证 `wsDir/target.scope` 不存在）。批准之后不能重复批准、不能翻案改成拒绝。

---

## 16. 任务看板与 Agent 状态面板

- **任务看板**：四列看板，列定义来自内核任务状态（非界面自编）。卡片刻意不做拖拽——任务状态由内核推进，界面拖一下改不了它，做出来只给人「我能改」的错觉。Gate 5 看板计数 `tasks=8`，被拒绝的 `task-2` 落在失败列且标「被阻断」。
- **Agent 状态**：状态是内核在真实工作中走出来的（`trace` 非空，说明状态机真的动过），不是界面点出来的。Gate 1 §31 验证 `agents.length >= 2` 且每个 `trace` 元素都是界面词汇。

---

## 17. 其余面板：代码 / 调研 / 推理 / 记忆

四块全部**只读**，是内核工作的投影：

- **代码预览**：`system.codePreview` 返回文件快照；权限拒绝路径上的文件不会出现在界面里。
- **调研**：`system.research` 返回结论 + 带引用的来源；来源间矛盾如实上报。
- **推理轨迹**：`system.reasoning` 返回全程轨迹，`neverSubmitted` 为真（推理循环只提议、不自行提交）。
- **记忆**：`memory.list` 返回记忆流。

Gate 5 实测四块均渲染正常（代码预览 98 字 / 调研 45 字 / 推理轨迹 48 字 / 记忆 4955 字），且窗口里找不到任何动手面入口（`executionProbe` 列表为空）。

---

## 18. 扫描结果（Gate 2）

`scan-ui-execution.js` 对 `ui/`（隔离区已排除）31 个源文件做三区扫描：

```
Zone A 渲染面 / Zone B 主进程面     19 / 12
遗留脚手架已隔离                    = ui/_legacy_vite_react/ ✓
Zone A 执行 token 零容忍            = 生效 ✓
动态求值面（eval / Function / 动态）  = 已封 ✓
HTML 注入面（innerHTML 族）         = 已封 ✓
零新增第三方依赖                    = 生效 ✓
桥面纪律（require 唯一 · 不桥总线）  = 生效 ✓
窗口安全开关（10 项）               = 齐备 ✓
桥抄本与契约全等                    = 生效 ✓
契约自洽（6 域 · 24 频道 · 5 决定类）= 生效 ✓
频道唯一且前缀统一                  = 生效 ✓
纯数据红线                          = 生效 ✓
零执行权自证（覆盖 7 个模块）        = 生效 ✓
执行权归属                          = 内核侧唯一执行链 ✓
EventBus 事件总数                   = 370 ✓

✓ 桌面层纯净：Execution Token = 0 · External Dependency = 0 · Violation = 0
```

退出码 `EXIT=0`。

---

## 19. 测试套件结果（Gate 1 & Gate 4）

**Gate 1（`phase25_ui_test.js`，35 段）**：

```
Phase 25.1 Electron Desktop UI 桌面交互层：PASS 7823 / FAIL 0（共 35 段，51ms）
断言规模：7823 条（要求 ≥ 5000）· 桌面层零动手权：全程恒 false
```

覆盖：契约核心 / 频道 / 主题-面板 / 辅助函数 / 纯度（基本·模糊·降级）/ 视图词汇 / 15 视图构造器 / 看板模糊 / 审批队列排序模糊 / 翻译表 / 事件主题 / 风险 / 事件适配器（剥离·批处理）/ 传输 / IPC 覆盖 / IPC 守卫 / 预加载对等 / 预加载纪律 / Zone A 词法 / Store（基本·模糊）/ 渲染面 / DOM 纯 / 宿主装配 / 端到端（对话·拒绝·批准·面板）/ 零执行权 / 扫描一致性 / 版本 / 测试自证。

**Gate 4（`npm run test:all`，含 `pretest:all` 即 Gate 3）**：

```
37 套件 · 0 FAIL（EXIT=0，与既有 192,093 断言基线一致）
[FAIL] 行数 = 0 · 非 0 失败套件数 = 0
```

`pretest:all` 先跑 `check-consistency.js`，输出 `✓ 全部派生点与真源一致`（ConsistencyChecker PASS 112 / FAIL 0），通过后才跑 37 个套件。UI 层改动（第 21 节）未拖垮任何既有内核套件。

---

## 20. 真实窗口走查证据（Gate 5）

`scripts/ui-smoke.js` 用 Node 22 自带 `WebSocket` + `fetch`（零依赖）通过 CDP 从外部驱动真 Electron，证据写入 `docs/gate5/ui-smoke-evidence.json`，截图存 `docs/gate5/ui-smoke-approvals.png` 与 `ui-smoke-tasks.png`。

**30 步全绿**，关键节点：

| 步骤 | 证据 |
|------|------|
| 渲染进程无 Node 能力 | require/process/module/Buffer/global/electron 全 `undefined` |
| 桥只暴露约定命名空间 | agents,approvals,chat,handshake,memory,meta,onPush,system,tasks |
| 真实对话 | 角色链 `user→assistant` |
| 真实审批请求 | 6 张卡 |
| 真实拒绝停任务 | `task-2 · failed · 人已拒绝，链路就地停止` |
| 真实批准开闸 | `待裁决 4 · 已批准 1 · 已拒绝 1` |
| 执行面探针 | exec/run/spawn/shell/terminal/sandbox/execute 全 `undefined`，`bridgeHasExec=false` |
| 8 面板 | 全部渲染正常 |

启动环境两条（本环境特有，不影响红线）：剥离全局 `ELECTRON_RUN_AS_NODE`（否则 Electron 退化成普通 Node 报误导性 `does not provide an export named 'BrowserWindow'`）；`PAIOS_UI_NO_CHROMIUM_SANDBOX=1` 关掉 Chromium OS 级沙箱（不影响 `webPreferences.sandbox`）。

---

## 21. 本轮修复的缺陷

### 21.1 [翻译层↔渲染层] 审批队列视图形态不一致——真窗口才暴露的白屏

`getApprovals()` 原本返回 `approvalManager.list().map(_approvalView)` 的**裸数组**，而渲染层的 `state.approvals`（`{cards, pending, approved, rejected, total}`）与 `approvals.js` 组件（`q.cards.map(...)`）期望的是 `toApprovalQueueView` 产出的**队列视图**。`toApprovalQueueView` 在 `ui-models.js` 里早已存在却从未接线。

后果：Gate 1 静态测试全绿（它各自断言裸数组 / 队列视图），但真窗口里审批面板一渲染就抛 `[store] 订阅者异常： Cannot read properties of undefined (reading 'map')`——**这是本轮唯一一处只有真实窗口能抓到的真 bug**。

**修复（未动 `core/*` 与根 `main.js`）**：
- `ui/shared/ui-models.js` 的 `toApprovalCardView` 改为兼容两套字段命名：内核原始记录用 `risk_level` / `metadata.taskId` / `resolvedBy`，测试/界面构造用 `risk` / `taskId` / `decidedBy`；并补上 `taskId` 字段（之前缺失，导致 Gate 1「审批关联到具体任务」断言无法在队列视图形态下成立）。
- `ui/electron/app-api.js` 的 `getApprovals()` 改为返回 `toApprovalQueueView(approvalManager.list())`，与渲染层期待对齐。
- `phase25_ui_test.js` 端到端三段（§28 对话/§29 拒绝/§30 批准）改为断言队列视图形态（`cards.length` / `cards.filter(...)` / `cards[0]` / `cards[1]`）。
- `scripts/ui-smoke.js` 两处走查修正：对话角色检查先切到对话面板再读 `.msg`（渲染层只挂活跃面板，审批活跃时对话不在 DOM）；「停下的任务」检查改为读桥真数据 `tasks.list`（`status==="failed" && blockedBy 含"拒绝"`），替换原本对 DOM 文案子串 `"拒绝"` 的脆弱匹配（任务卡只渲染「被阻断」chip，不含该子串）。

### 21.2 [环境] Electron 启动两处坑（前序会话已定位，本轮复跑确认）

- 全局 `ELECTRON_RUN_AS_NODE=1` 会把 Electron 二进制退化成普通 Node → 在 spawn 的子进程里剥离该变量。
- 受限环境 Chromium OS 级沙箱起不来 → `PAIOS_UI_NO_CHROMIUM_SANDBOX=1` 关掉它；`webPreferences.sandbox` 红线不受影响。

---

## 22. 接线与登记

| 项目 | 变更 |
|------|------|
| `package.json` `start` | `node main.js` → `electron ui/electron/main.js`（CLI 仍可用 `start:cli`） |
| `package.json` `test:all` 末端 | 追加 `&& node phase25_ui_test.js`（37 套件） |
| 新增脚本 | `test:phase25_1`、`check:ui:execution`、`smoke:ui` |
| `ui/` 新增 | 34 个源文件（electron 壳 + 预加载 + IPC + 翻译层 + 渲染层 + 共享契约/模型） |
| 契约 | `UI_CONTRACT_VERSION = 25.1.0` · 6 命名空间 · 24 频道 · 5 决定类 · 9 推送主题 |
| EventBus | 复用内核 370 事件（界面侧只消费，不新增内核事件） |
| `docs/gate5/` | Gate 5 真窗口走查证据 JSON + 2 张截图 |

**未触碰**：`core/*` 与根 `main.js` 始终未被本阶段改动；UI 层所有逻辑都在 `ui/` 与根级测试脚本内，红线「界面无执行权」在物理与契约两层都成立。

---

## 23. 已知问题

- **审批面板排序依赖 `createdAt`（ms）**：`toApprovalCardView` 直接 `num(src.createdAt, 0)`，未做秒→毫秒归一。内核 `human_control/ApprovalManager` 已存 ms，故显示与排序正确；若未来某条审批记录以秒入库，时间显示会偏差（不影响排序不变量与红线）。低风险，暂不改动以避免动绿色基线。
- **Chromium OS 级沙箱在本环境需 `--no-sandbox`**：仅本受限环境如此，生产机器上应移除 `PAIOS_UI_NO_CHROMIUM_SANDBOX` 以启用 OS 级沙箱；`webPreferences.sandbox` 红线不受此开关影响。
- **`phase25_ui_test.js` 断言数稳定为 7823**：与既有内核套件（Phase 20 学习层因挂钟时间在 110–112 间微抖，见 `PHASE25_29_MVP_REPORT.md` §4.1）无关，UI 层自身不依赖挂钟。

---

## 24. 复现步骤与交付清单

### 复现（五道闸门）

```bash
cd /Users/yaowei/WorkBuddy/PersonalAIOS

node phase25_ui_test.js                                                    # Gate 1  → PASS 7823 / FAIL 0
node scan-ui-execution.js                                                 # Gate 2  → EXIT=0
npm run check:consistency                                                 # Gate 3  → EXIT=0（亦由 pretest:all 自动跑）
npm run test:all                                                          # Gate 4  → EXIT=0（37 套件 / 0 FAIL）
PAIOS_MODEL=heuristic PAIOS_UI_NO_CHROMIUM_SANDBOX=1 node scripts/ui-smoke.js   # Gate 5  → 30/30 步全绿
```

### 交付清单

- `ui/electron/`：main.js · app-api.js · event-adapter.js · kernel-host.js · preload.cjs · ipc/{index,transport,chat,task,agent,approval,memory,system}.js（13）
- `ui/renderer/`：app.js · api.js · state.js · dom.js · index.html · styles/app.css · components/{conversation,tasks,agents,approvals,code,research,reasoning,memory,sidebar,topbar,statusbar,feed}.js（17）
- `ui/shared/`：ipc-contract.js · ui-models.js（2）
- `phase25_ui_test.js`（Gate 1，7823 断言 / 35 段）
- `scan-ui-execution.js`（Gate 2）
- `scripts/ui-smoke.js`（Gate 5 CDP 驱动）
- `docs/gate5/ui-smoke-evidence.json` + 2 张走查截图
- 本报告

**验收结论：五道闸门全部通过，Electron 桌面交互层就位；界面在整个链路里零执行权，唯一执行链完整且未被界面侧绕过。Phase 25.1 完成，不自动进入后续 Phase。**
