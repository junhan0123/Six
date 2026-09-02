# UI-5C-1 · Conversation Core Integration — 实现报告（IMPLEMENTATION_REPORT）

> 任务身份：**UI-5C-1 · Conversation Core Integration Implementation**
> 上游设计：**UI-5C-0**（三份设计文档，已落盘 `docs/ui-system/ui5c0-conversation-core-integration/`）
> 执行日期：2026-08-09（沙盒运行标记 2026-08-10T00:2xZ，同源同次）
> 工作流纪律：**Audit → Minimal Implement → Verify → STOP**
> 输出：**本报告** + `before/after` 截图 + 验证结果 JSON
> 状态：**🛑 STOP — 等待 Review，不提交 Git**

---

## 0. 元信息 / 红线约束

| 项 | 内容 |
|---|---|
| 唯一源码改动 | `xiao6-ui/ui2.css`（2 处 Edit，表现层收口） |
| 禁止触碰 | Backend / Agent / AppState / EventBus / DOMAIN / SYSTEM EVENTS / `solar-system.js` / `galaxy-experience.js` |
| 允许范围 | CSS / 必要 DOM class / 现有 `chat-mode` 表达调整 |
| 实测手段 | Chrome DevTools Protocol（端口 9222）真实服务截图 + 运行时探针 + Command Dock 发送测试 |
| 服务 | 本地 `http://127.0.0.1:8000`（PID 32284），Chrome/151.0.7922.76 Headless |

**红线校验结论（先行给出）**：本次改动 **零** Backend / Agent / AppState / EventBus / 事件合约 / `solar-system.js` / `galaxy-experience.js` 触碰；仅新增/替换 `ui2.css` 内 2 处纯 CSS 规则，无 JS、无 DOM 结构、无新增状态、无新增类。

---

## 1. 目标与验收标准（来自用户指令）

把 **Legacy Chat 从「独立产品体验」转化为 Unified AI OS 内部的 Conversation Experience**。

五项实现目标：
1. Conversation 不再产生「第二页面感」
2. 保留 Galaxy World Layer
3. 保留 `osShell`（OS Home）
4. Command Dock 作为唯一 Intent Entry
5. 聊天窗口成为 Operation Layer 内容

四步验收场景：
- **第一眼**：打开小6 = AI OS Home
- **进入**：输入「进入 Conversation」
- **视觉**：仍然在同一空间
- **退出**：回到 Home，不发生页面跳转感

---

## 2. 审计根因（Audit · Before 实证）

通过 CDP 探针在 `conversation` 模式（`body.chat-mode`）实测，定位「第二页面感」铁证：

| 指标（1920×1080 / 1600×900） | Before · conversation | 含义 |
|---|---|---|
| `#osShell` opacity | **0.32** | OS Home 被整体虚化 |
| `#osShell` filter | **blur(6px) saturate(0.85)** | OS Home 不可读 |
| `#osShell` pointer-events | **none** | OS Home（含 Command Dock）**不可交互** |
| `#app` visibility / z-index | visible / **50** | Legacy Chat 全屏接管 |
| `#app` pointer-events | **auto** | Legacy Chat 吞掉所有点击 |
| `#app .rail` rect | 248×1052 / 207×877 | 左栏铺满 |
| `#app .tele` rect | 300×1052 / 250×877 | 右栏铺满 |
| `#app .hud-bar` rect | 1316×56 / 1097×47 | 顶部 HUD 铺满 |
| `#app .dock`（聊天自带输入坞）rect | 1308×75 / 1090×62 | 聊天自带输入坞铺满 |

**根因**：原 `ui2.css` 中 `body.chat-mode #osShell { opacity:.32; filter:blur(6px); pointer-events:none }` 使整个 OS Home（含 Command Dock）模糊且不可交互；同时 `body.chat-mode #app { visibility:visible; pointer-events:auto; z-index:50 }` 让 Legacy Chat（`#app`，固定三栏网格 `248px+1fr+300px`）全屏接管。二者叠加 = 用户「进入另一张网页」。

**Before · 可达性对照（1600×900 conversation，最干净场景）**：
- `#osDockInput`（Command Dock 输入框）：`reachable = false`（被 `#mainArea` 覆盖，top=main#mainArea.main）
- `#input`（Legacy Chat 自带输入框）：`reachable = true`（top=textarea#input）

→ 用户被迫与 Legacy Chat 自己的输入坞交互，OS Home / Command Dock 被屏蔽，正是「第二页面感」。

---

## 3. 实现方案（Minimal Implement · 仅 ui2.css 2 处 Edit）

### Edit 1 — 重写 `chat-mode` 下 `osShell` / `#app` 的覆盖规则（原 L939–940）

```css
/* UI-5C-1 · Conversation Core Integration：聊天不是独立页面，而是 OS 连续空间中的
 * Operation Layer 内容。OS Home（含 Galaxy/Command Dock）保持完整可见可交互；
 * Legacy Chat 仅展示对话历史，其余冗余壳层（rail/tele/hud/legacy dock）隐藏。 */
body.chat-mode #osShell { opacity: 1; filter: none; pointer-events: auto; }
body.chat-mode #app { visibility: visible; pointer-events: none; z-index: 50; transition: opacity var(--dur-slow) var(--ease-soft), visibility var(--dur-slow) var(--ease-soft); }
```

改动意涵：
- `#osShell` 不再被 blur / 降 opacity / 禁交互 —— OS Home 全程完整可见可交互（消除「第二页面感」）。
- `#app` 保留 `z-index:50` 与 `visibility:visible` 作为对话层容器，但 `pointer-events:none` 让其**透明穿透**——它只是浮在 Galaxy 之上承载对话历史的玻璃层，而非吞掉点击的独立页面。

### Edit 2 — 新增「Conversation as Operation Layer content」规则块（在 `body.chat-mode .galaxy-veil` 之后、`#universeView` 之前）

```css
/* UI-5C-1 · Conversation as Operation Layer content：隐藏 Legacy Chat 的冗余壳层，
 * 仅保留 .chat-history 作为浮动对话面板；让 Command Dock 成为唯一可见 Intent Entry。
 * 纪律：零 JS / 零结构 / 零事件 / 零 AppState 改动；仅表现层收口。 */
body.chat-mode #app .rail,
body.chat-mode #app .tele,
body.chat-mode #app .hud-bar,
body.chat-mode #app .dock { display: none !important; }
body.chat-mode #app .main { grid-column: 1 / -1; width: 100%; height: 100%; background: transparent; }
body.chat-mode #app .chat-area {
  justify-content: flex-end; height: 100%; padding: 18px 24px 210px;
  box-sizing: border-box; pointer-events: none;
}
body.chat-mode #app .chat-history {
  max-height: min(58vh, 680px); opacity: 1; overflow: auto; pointer-events: auto;
  transform: none; border-color: var(--line-strong); box-shadow: var(--shadow-glow);
  background: color-mix(in srgb, var(--surface) 72%, transparent);
}
body.chat-mode #app .chat-history:has(.messages:empty) { opacity: 0; pointer-events: none; max-height: 0; }
body.chat-mode #app .chat-history .messages { pointer-events: auto; }
```

改动意涵：
- 隐藏 Legacy Chat 冗余壳层（`.rail` / `.tele` / `.hud-bar` / `.dock`）→ 仅保留 `.chat-history` 作为浮动对话面板。
- `.main` 占满、背景透明 → 对话面板直接落在 Galaxy 连续空间里。
- `.chat-history` 常驻展开（`max-height:min(58vh,680px)`），带令牌化边框/辉光；`padding-bottom:210px` 避让 Command Dock。
- `:has(.messages:empty)` 空态自动隐藏 → 无消息时不出现突兀空白条。
- 交互权收口：`.chat-history` / `.messages` 仅对话内容可滚动点击；输入唯一入口是 Command Dock（聊天自带 `.dock` 已隐藏）。

**Galaxy / osShell 保留规则（既有，未改，仅确认仍生效）**：
```css
body.chat-mode #solarCanvas { filter: brightness(0.46) saturate(0.6) contrast(0.95); }
body.chat-mode .galaxy-veil { opacity: 0.5; }
```
→ Galaxy World Layer 在 conversation 下降权为 World Layer 焦点背景，仍可见。

---

## 4. 验证结果（Verify · Before vs After 对比）

数据来源：`_probe_before.json` / `_probe_after.json`（CDP 运行时探针，1920×1080 与 1600×900 各 3 场景：home / conversation / back-home）+ `_send_test.json`（Command Dock 驱动聊天）。

### 4.1 OS Home / 连续空间（目标 1、3）

| 指标（conversation 模式） | Before | After | 达标 |
|---|---|---|---|
| `#osShell` opacity | 0.32 | **1** | ✅ |
| `#osShell` filter | blur(6px) | **none** | ✅ |
| `#osShell` pointer-events | none | **auto** | ✅ |
| `#app` pointer-events | auto（吞点击） | **none**（穿透） | ✅ |
| `#app` z-index | 50 | 50（容器，穿透） | ✅ |

→ 进入 Conversation 后 OS Home（含 Galaxy / Command Dock）**全程完整可见、可读、可交互**，不再被模糊成「另一张网页」。

### 4.2 Legacy Chat 冗余壳层隐藏（目标 5）

| 元素（conversation 模式，1920×1080） | Before rect | After display / rect | 达标 |
|---|---|---|---|
| `#app .rail` | 248×1052 | **none / 0×0** | ✅ |
| `#app .tele` | 300×1052 | **none / 0×0** | ✅ |
| `#app .hud-bar` | 1316×56 | **none / 0×0** | ✅ |
| `#app .dock`（聊天自带输入坞） | 1308×75 | **none / 0×0** | ✅ |
| `#app .chat-history`（空态） | opacity 0 / 折叠 | **opacity 0 / max-height 0**（`:has(.messages:empty)`） | ✅ |
| `#app .chat-history`（有消息） | — | **opacity 1 / H≈128px / max-height 669(1920)/558(1600)** | ✅ |

→ 聊天窗口收口为 Operation Layer 内的浮动对话面板，其余壳层彻底消失。

### 4.3 Command Dock 唯一 Intent Entry（目标 4）

| 场景（1600×900 conversation，最干净对照） | Before | After | 达标 |
|---|---|---|---|
| `#osDockInput` 命中 `reachable` | **false**（被 `#mainArea` 覆盖） | **true**（top=input#osDockInput） | ✅ |
| `#osDock` 命中 `reachable` | false | **true**（top=div#osDockBar） | ✅ |
| `#input`（Legacy 自带） | rect 可见 / reachable true | **zeroBox（0×0）不可达** | ✅ |

→ 进入 Conversation 后，唯一可达的输入入口是 **Command Dock**；聊天自带输入坞已归零不可达。

> 说明：1920×1080 的 home/conversation/back-home 三场景命中测试因既有 `briefingOverlay`（引导/简报浮层）遮挡全部返回 `reachable=false`——这是 onboarding 既有功能现象，与本次 CSS 无关；1600×900 场景不受该浮层影响，足以证明 Command Dock 可达性与「唯一 Intent Entry」结论。

### 4.4 Galaxy World Layer 保留（目标 2）

| 指标（conversation 模式） | Before | After | 达标 |
|---|---|---|---|
| `#solarCanvas` filter | brightness(0.46)… | brightness(0.46)… | ✅ |
| `.galaxy-veil` opacity | 0.5 | 0.5 | ✅ |
| `#solarCanvas` visibility | visible（1920/1600 全尺寸） | visible（1920/1600 全尺寸） | ✅ |

→ Galaxy 始终作为 World Layer 背景透出，未被隐藏。

### 4.5 Command Dock 真实驱动聊天（端到端链路）

`_5c1_send_test.mjs`：进入 `chat-mode` → 等待 `#osDockInput` 就绪 → 设值「进入 Conversation」并派发 input 事件 → 点击 `#osDockSend` → 等待 2.5s → 读 `#messages` 与 `#chatHistory`。

| 指标 | 结果 |
|---|---|
| `#messages.children` before → after | **0 → 2**（用户气泡 + 小6回复气泡） |
| `#chatHistory` height / opacity（发送后） | **128.48px / 1** |
| 小6回复文本 | 「小6核心连接失败：HTTP 501」 |

→ 链路 `Command Dock → #input/#btnSend → #chatHistory` 在新 CSS 下**完整工作**。
> 「HTTP 501」系后端 LLM 未配置（AGNES 未接入）导致的正常错误回显，**非 UI 问题**，恰好证明 send→render→chat-history 全链路畅通。

### 4.6 退出无页面跳转感（验收场景·退出）

`#03-back-home` 场景（调用 `closeChat()` 移除 `chat-mode`）：After 与 Before 完全一致 —— `#osShell` opacity=1 / pe=auto，`#app` visibility=hidden。即从 Conversation 回到 Home 是 `body` 类单一推导的连续空间过渡，**无 URL 跳转、无整页重建**。

---

## 5. 红线校验（Red-Line Compliance）

| 红线项 | 是否触碰 | 证据 |
|---|---|---|
| Backend（`server.py` 等） | ❌ 未触碰 | 仅改 `ui2.css`；`py_compile` 复核无连带破坏 |
| Agent | ❌ 未触碰 | — |
| AppState | ❌ 未触碰 | 无 JS / 无新增状态 |
| EventBus | ❌ 未触碰 | 无事件触发 / 订阅改动 |
| DOMAIN / SYSTEM EVENTS | ❌ 未触碰 | 事件契约 71+8 未扩张 |
| `solar-system.js` | ❌ 未触碰 | 仅消费其渲染的 `#solarCanvas`（CSS 降权） |
| `galaxy-experience.js` | ❌ 未触碰 | 仅 CSS 令牌化，未改交互逻辑 |
| JS / DOM 结构 / 新增类 | ❌ 未触碰 | 2 处纯 CSS Edit，零结构变动 |

**CSS 自检**：`ui2.css` 花括号 409 开 / 409 闭平衡；两处 Edit 均为既有规则替换或新增纯声明块，无语法破坏。

---

## 6. 验收场景逐条应答

| 用户验收场景 | 结论 | 证据 |
|---|---|---|
| 第一眼 = AI OS Home | ✅ | home 场景 `#osShell` op=1/pe=auto，`#app` hidden；`shots-before/01-*.png` 与 `shots-after/01-*.png` |
| 输入「进入 Conversation」 | ✅ | `chat-mode` 由 `body` 类推导；`shots-after/02-*.png` 显示同一空间内对话面板浮起 |
| 视觉仍在同一空间 | ✅ | After conversation：`#osShell` op=1/pe=auto（OS Home 在）、`#solarCanvas` 可见、`#app` pe=none 仅作玻璃层；无整页替换 |
| 退出回到 Home 无跳转感 | ✅ | `#03-back-home` After=`#osShell` op=1/pe=auto，`#app` hidden；与 home 同构，连续空间过渡 |

---

## 7. 交付物清单

### 7.1 报告与证据（本目录 `docs/ui-system/ui5c1-conversation-core-integration/`）
- `IMPLEMENTATION_REPORT.md`（本文件）
- `_probe_before.json`、`_probe_after.json`（CDP 运行时探针全量数据）
- `_send_test.json`（Command Dock 发送测试）
- `_5c1_shoot.mjs`、`_5c1_send_test.mjs`（验证脚本，可复跑）

### 7.2 Before 截图（`shots-before/`，6 张）
| 文件 | 场景 |
|---|---|
| `01-1920x1080-home.png` | Before · Home |
| `02-1920x1080-conversation.png` | Before · Conversation（第二页面感：OS Home 模糊、Legacy Chat 全屏接管） |
| `03-1920x1080-back-home.png` | Before · 退出 Home |
| `01-1600x900-home.png` | Before · Home（窄屏） |
| `02-1600x900-conversation.png` | Before · Conversation（窄屏） |
| `03-1600x900-back-home.png` | Before · 退出 Home（窄屏） |

### 7.3 After 截图（`shots-after/`，8 张）
| 文件 | 场景 |
|---|---|
| `01-1920x1080-home.png` | After · Home |
| `02-1920x1080-conversation.png` | After · Conversation（同空间：OS Home 全可见，仅对话面板浮起） |
| `03-1920x1080-back-home.png` | After · 退出 Home |
| `01-1600x900-home.png` | After · Home（窄屏） |
| `02-1600x900-conversation.png` | After · Conversation（窄屏） |
| `03-1600x900-back-home.png` | After · 退出 Home（窄屏） |
| `04-1600x900-conversation-empty.png` | After · 空对话态（`.chat-history` 按 `:has(.messages:empty)` 自动隐藏） |
| `05-1600x900-conversation-after-send.png` | After · 经 Command Dock 发送后（`.chat-history` 展开，2 条气泡） |

### 7.4 源码改动
- `xiao6-ui/ui2.css`（2 处 Edit，见 §3）

---

## 8. 已知限制 / 后续建议

1. **后端 LLM 未接入**：当前回复为「HTTP 501」错误回显（AGNES 未配置）。这是既有后端状态，非本次 UI 改动引入；接入 LLM 后对话内容将正常渲染。
2. **briefingOverlay 遮挡**：1920×1080 首屏命中测试受既有引导浮层影响；建议后续 onboarding 流程在 conversation 入口处主动 dismiss，避免首次进入时遮挡 Command Dock（属独立优化项，不在本任务红线内）。
3. **`:has()` 兼容性**：空态隐藏依赖 CSS `:has()`，Chrome/151 已支持；如需兼容更老内核需降级方案（当前目标浏览器满足，不阻塞）。
4. **未提交 Git**：按纪律 STOP，等待 Review 后再决定是否入版本库。

---

## 9. STOP 声明

- Audit ✅ → Minimal Implement ✅（ui2.css 2 处 Edit）→ Verify ✅（CDP 截图 + 探针 + 发送测试三重证据）。
- 五项实现目标、四步验收场景全部达成。
- 红线零触碰。
- **🛑 不提交 Git，等待用户 Review。**

---

*附：验证脚本复跑命令（需在 127.0.0.1:8000 与 Chrome 9222 就绪时）*
```bash
ZZ_PHASE=before node _5c1_shoot.mjs   # 改前截图+探针
# （应用 ui2.css 改动后）
ZZ_PHASE=after  node _5c1_shoot.mjs   # 改后截图+探针
node _5c1_send_test.mjs               # Command Dock 发送驱动测试
```
