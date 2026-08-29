# PHASE-5.1-HOTFIX-UI-10 — COMPOSER CLEAR AFTER SEND — FINAL REPORT

**Project:** 小6 Xiao6 v1.4.0
**Scope:** 最小 UI 状态修复 —— 发送消息后输入框立即清空
**Status:** ✅ COMPLETE / VERIFIED / FROZEN
**Discipline:** 仅改 composer clear；未触碰后端 / orb / Electron / 其他 UI 层；UI-09 冻结契约保持
**Date:** 2026-08-18

---

## 1. Root Cause

主 Workspace 入口 `G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js` 中，composer 输入框为 `<input id="cmdInput" type="text">`。

- Enter 与点击发送**共用** `<form id="cmdForm">` 的 submit 事件（`zz-workspace.js:1033`）→ `submitCmd(v)` → `sendChat(text)`。
- `submitCmd()`（L369）在调用 `sendChat(text)` 后**从未清空 `cmdInput.value`** → 发送后输入框残留原文本（如「你好小6」）。这是**唯一根因**。
- `sendChat(text)`（L197）已接受 `text` 参数，并以 `content: text` 构造 payload（L222），**不依赖 `input.value`** → 清空 `cmdInput` 不影响请求内容。
- `submitCmd` 是 form / 语音（L354）/ 命令面板（L685）三者的**单一 choke point** → 在此一处加 clear 即可，无重复逻辑。

Legacy 入口 `G:\xiao6\xiao6-ui\gui\chat.html` 的 composer 为 `<textarea id="input">`，Enter（L567 `this.value=''`）与点击（L569 `el('input').value=''`）**均已清空** → 本就无 bug，**无需改动**。修复主入口后，两生产入口行为自然一致。

---

## 2. Before / After

**Before（bug）：**
```js
function submitCmd(text) {
  var view = document.body.dataset.view;
  if (view !== 'conversation') switchView('conversation');
  sendChat(text);          // 发送后 cmdInput.value 残留原文本
}
```

**After（fixed）：**
```js
function submitCmd(text) {
  var view = document.body.dataset.view;
  if (view !== 'conversation') switchView('conversation');
  var wasBusy = busy;       // UI-10: 进入 sendChat 前快照发送流状态
  sendChat(text);           // payload 使用 text，不依赖 input.value
  // UI-10: 仅在消息真实进入发送流后清空 composer；
  //        sendChat 在 busy 时 early-return → 不清空，避免丢失用户输入（不退化错误恢复）
  if (!wasBusy && text && String(text).trim()) {
    var ci = $('cmdInput'); if (ci) ci.value = '';
  }
}
```

---

## 3. Files Modified

| File | Change | Lines |
|------|--------|-------|
| `G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js` | `submitCmd()` 增加 `wasBusy` 快照 + 发送后清空 `cmdInput` | L369–381（+12 行） |
| `G:\xiao6\xiao6-ui\gui\chat.html` | **未改动**（已自带 Enter/点击清空，L567/L569） | — |

---

## 4. Exact file:line Evidence

### zz-workspace.js（主入口，已改）
- **L369** `function submitCmd(text) {`
- **L372** `var wasBusy = busy;   // UI-10: snapshot send-flow state BEFORE entering sendChat()`
- **L373** `sendChat(text);`
- **L378** `if (!wasBusy && text && String(text).trim()) {`
- **L379** `var ci = $('cmdInput'); if (ci) ci.value = '';`
- **L197** `function sendChat(text, opts) {` —— 已接受 `text` 参数
- **L222** `var payload = { messages: [{ role: 'user', content: text }], session_id: sessionId };` —— **payload 用 `text`，非清空后的 `input.value`** ✅
- **L210** `function ensureAssistant() {` —— UI-09 惰性建气泡函数（未改）
- **L256** `if (dc) { ensureAssistant(); reply += dc; stream.update(reply); scrollChat(); }` —— 首 delta 触发（未改）
- **L1033** `$('cmdForm').addEventListener('submit', ... submitCmd(v); });` —— Enter 与点击共用 choke point

### chat.html（legacy 入口，未改，仅作一致性证据）
- **L450** `async function send(text){`
- **L457** `var bubble = null;   // UI-09: lazily created on first real choices.delta.content`
- **L567** `if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(this.value); this.value=''; autoGrow(); ... }` —— Enter 已清空
- **L569** `el('sendBtn').addEventListener('click', function(){ var v=el('input').value; el('input').value=''; autoGrow(); send(v); });` —— 点击已清空

---

## 5. Send Flow

```
用户输入 "你好小6"
   ↓
cmdForm submit (L1033)  [Enter 与点击共用]
   ↓
v = $('cmdInput').value
   ↓
submitCmd(v)
   ├─ snapshot wasBusy = busy
   ├─ switchView('conversation')  (若不在对话视图)
   ├─ sendChat(text)
   │     └─ payload = { messages:[{role:'user', content: text}], ... }   ← 用发送前保存的 text
   │     └─ 发起现有 SSE 请求
   └─ if (!wasBusy && text.trim())  $('cmdInput').value = ''   ← 发送后清空
   ↓
首个真实 choices.delta.content
   ↓
ensureAssistant()  (L256, UI-09 惰性)  → 创建 assistant bubble
   ↓
持续流式追加 → 完成
```

---

## 6. Composer Clear Flow

```
send 进入发送流
   ↓
wasBusy 快照 (L372)
   ↓
sendChat(text)  ← payload 使用 text
   ↓
clear 守卫: !wasBusy && text 非空  (L378)
   ↓
$('cmdInput').value = ''  (L379)
   ↓
composer 状态:
   - value === ""            ✓
   - 原生 placeholder 恢复    ✓ (input 自带 placeholder 属性，清空后自动显示)
   - 焦点策略: 保持项目原有行为，未强制 refocus / 未改 focus 逻辑  ✓
```

> 说明：`cmdInput` 是 `<input type="text">`（单行，**非 textarea**），不存在 `resetComposer` / `autoResize` / `updateComposerState` 任何可复用 helper（已 grep 确认），故直接 `value = ''` 即为等价最小修复；无需新建 helper、无重复 clear 逻辑。

---

## 7. UI-09 Regression Check ✅

UI-09 冻结契约**未被破坏**：

| 契约项 | 状态 | 证据 |
|--------|------|------|
| 发送瞬间只有 user bubble，无空 assistant bubble | ✅ | `submitCmd` 仅清空 input，不创建 assistant 节点 |
| 无提前 assistant 占位（如「在呢老板…」） | ✅ | `ensureAssistant()` 未在任何预占位位置调用 |
| 首 delta → `ensureAssistant()` → 真流式追加 | ✅ | L256 未改动，仍为首 delta 触发 |
| `tool_start`/`tool_end` → Activity 而非 Conversation | ✅ | 本次改动未触碰 Activity / tool routing 逻辑 |
| `chat.html` 惰性 `bubble=null` 保留 | ✅ | L457 未改动 |

清空操作发生在 `sendChat` **之后**，而 `sendChat` 在 `busy` 时 early-return（不进入 SSE），此时 `wasBusy` 快照为 `true` → **不清空**，从而避免丢失用户正在输入的文本（不引入新的错误恢复系统，仅复用既有 busy 守卫语义）。

---

## 8. Syntax Verification ✅

| 检查项 | 命令 / 方式 | 结果 |
|--------|------------|------|
| zz-workspace.js 语法 | `node --check $(cygpath -w 'G:/xiao6/xiao6-ui/xiao6-space/js/zz-workspace.js')` | `ZZ_WORKSPACE_SYNTAX_OK` |
| chat.html inline script | 提取 `<script>` 经 `vm.Script` 编译 | `ALL_INLINE_SCRIPTS_OK` |
| 无重复 composer clear | `grep` `cmdInput').value = ''` | 仅 **1 处**（本次新增 submitCmd L379）；另有 paletteInput（无关）、`/` 命令分支前置 `return`（不走发送）——均非 composer 重复 clear |
| payload 用发送前 text | `grep` `content: text` | ✅ L222 使用 `text` 参数，非清空后的 `input.value` |
| UI-09 惰性契约 | `grep` `ensureAssistant` / `if (dc)` | ✅ L210 定义、L256 首 delta 触发，未改 |

---

## 9. Real E2E Results

**沙箱限制声明：** 当前环境无显示 / 无真实 Electron GUI / 无麦克风，无法执行像素级真机走查。下列为**真实代码路径的功能级 E2E**——用桩 DOM 加载**真实** `zz-workspace.js`（含本次修改），驱动 `submitCmd()` 跑完整发送链路。

> 不将静态 / headless 功能测试冒充为 LIVE GUI E2E。

### HEADLESS FUNCTIONAL E2E（加载真实 zz-workspace.js）

| Case | 输入 | 预期 | 结果 |
|------|------|------|------|
| **A** 普通对话 | "你好" | 发送后 `cmdInput.value === ""`；user node +1；assistant bubble 仅首 delta 才出现（+1，无空气泡） | ✅ PASS |
| **B** 触发工具 | "现在几点了" | 发送后清空；工具阶段仅 Activity（无 assistant 空气泡）；首个 delta 才建 assistant bubble（相对 B 基线 +1） | ✅ PASS |
| **C** 空输入 | ""（或纯空白） | 不发送；输入框保持空 | ✅ PASS（sendChat 对空/blank 文本 early-return） |
| **D** Enter 发送 | "你好"（按 Enter） | 经 `cmdForm` submit 共用 `submitCmd` → 与点击行为完全一致 | ✅ PASS |

**结论：** `STATIC PASS` + `HEADLESS FUNCTIONAL E2E PASS`。
**LIVE GUI E2E：** ⛔ BLOCKED（沙箱无 Electron 显示）。建议在工作站用 `start-xiao6.bat` 启动做最终肉眼验收，预期与本轮一致。

---

## 10. Red-Line Audit ✅

| 红线项 | 是否触碰 | 说明 |
|--------|----------|------|
| UI redesign / CSS redesign | ❌ | 未改任何 CSS / 布局 |
| 聊天架构重构 | ❌ | 仅 `submitCmd` 增加 clear，发送链路结构不变 |
| Streaming 重构 | ❌ | `ensureAssistant` / `stream.update` 未改 |
| Activity 重构 | ❌ | `#banner` Activity 逻辑未改 |
| Voice 修改 | ❌ | `dyna-orb-voice.js` 未改 |
| Presence 修改 | ❌ | `xiao6:presence` 逻辑未改 |
| Electron 修改 | ❌ | `electron/main.js` 未改 |
| Backend 修改 | ❌ | `server.py` / `server_handlers_chat.py` / `tools.py` / `agent_runtime.py` 未改 |
| Port / TTS / Runtime 修改 | ❌ | 未触碰 |
| 新增框架 / 依赖 | ❌ | 无 |
| UI-09 契约 | ❌（保持） | 见 §7 |

**改动唯一性：** 仅 `zz-workspace.js` 的 `submitCmd()`（L369–381），+12 行；`gui/chat.html` 零改动。

---

## 11. Remaining Issues

1. **LIVE GUI E2E 未做**（沙箱无 Electron 显示）—— 功能级 headless E2E 已全绿，建议工作站肉眼验收。
2. **`wasBusy` 守卫语义**：当上一条助手回复仍在进行（`busy === true`）时，新提交不清除 `cmdInput`（避免丢失用户正在输入的文本）。这与 `sendChat` 既有 busy 拦截行为一致，未引入新错误恢复系统。
3. 无 P0 / P1 运行阻断；无遗留代码债务。

---

## STOP

UI-10 已完成并冻结。仅解决「发送消息后输入框保留内容」这一件事。

- 不进入 UI-11。
- 不修改 TTS / Port / Runtime。
- 不顺手修其他问题。

**交付物：** `G:\xiao6\_ui_archive\PHASE-5.1-HOTFIX-UI-10-FINAL-REPORT.md`
