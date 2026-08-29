# PHASE 5.1-HOTFIX-UI-09 / STREAMING CONVERSATION ORDER & RESPONSE GATING — FINAL REPORT

**Status:** ✅ COMPLETE / VERIFIED (static) / FROZEN pending live Chromium E2E
**Date:** 2026-08-18
**Owner:** 阿枢（🧠）· Senior Frontend Engineer role for this hotfix
**Scope:** Chat render timing only — no backend, no orb visual, no UI-10.

---

## 1. Product Goal Freeze

UI-09 收口「聊天渲染时序」——核心问题：

> **assistant 气泡在用户刚点发送时就立刻出现（空气泡 / 占位），而此时后端还在
> 跑工具或思考，真正的回复还没到。**

目标：把「Assistant 聊天气泡」的创建时机，从 **send-time（急切）** 改为
**first-real-delta（惰性）**。用户只和「小6」对话，不需要在气泡里看到
`tool_start` / `tool_end` / `tool_result` 这类底层执行痕迹。

交付后交互模型（golden path）：

```
用户发送 ──► [user 气泡] 立即出现
                │
                ├─ tool_start ─────────► Activity 层：#banner "小6 正在处理…"（无聊天气泡）
                ├─ tool_end   ─────────► Activity 层：计数 -1，归零则隐藏 banner（无聊天气泡）
                │
                └─ 第一个 choices[0].delta.content 到达
                                  │
                                  ▼
                         [assistant 气泡] 此刻才创建，并从此逐字 append（真流式）
                                  │
                                  ▼
                            [DONE] / finish() ──► finalize markdown，TTS 朗读，flush panel/modal/scene
```

---

## 2. Problem / Root Cause

**Root cause = 急切（eager）的 assistant 节点创建。**

| 文件 | 行（修改前） | 问题 |
|------|------------|------|
| `xiao6-space/js/zz-workspace.js` | L207 `var an = addNode('assistant')` | `sendChat()` 一进入就创建了空 assistant 气泡并标 `.streaming` |
| `gui/chat.html` | L457 `var bubble = appendMsg('assistant', '', true)` | 同样在 `send()` 一开始就创建空 assistant 气泡 |

后果：
- 气泡在工具执行 / 思考阶段就「挂」在聊天区，内容为空或只有后续 append。
- 视觉上给人「小6 已经回复了」的错觉，与真实流式进度错位。
- 若后端直接报错（无任何 delta），会留下一个空/错误占位气泡。

**已确认的非问题（沿用，不改动）：**
- `onTool()` 早已只驱动 Activity 层（`showActivity()` / `hideActivityIfIdle()`），从不创建气泡 —— UI-06 已正确，UI-09 仅继承。
- 流式 append 逻辑（`stream.update(reply)` / `bubble.textContent = full`）本身正确，必须**保留真流式**而非改成分批替换。
- `gui/chat.html` 经 `server_p20.log` 核实**生产可达**（`GET /gui/chat.html 200` @ 18/Aug），故必须同步修改，不能只改主 UI。

---

## 3. VERIFY (before-change state)

真实磁盘核对（非摘要推断）：
- 读取 `zz-workspace.js` L186–341：确认 L207 eager 创建 + L290 `finish()` 无条件 `an.node.classList.remove('streaming')`；`onTool` L259–270 仅 Activity。
- 读取 `gui/chat.html` L405–515：确认 L457 空气泡 + L486–491 `full += delta; bubble.textContent = full` 流式。
- grep `chat.html` / `XIAO6_CHAT_PATH` / `/gui/` 全仓：确认 `gui/chat.html` 生产可达。
- grep Activity helpers：L47–51 `showBanner/hideBanner/showActivity/hideActivityIfIdle` 存在可复用。

---

## 4. Message-Flow Map (post-change)

```
SSE event                →  handler                       →  layer
─────────────────────────────────────────────────────────────────────
user send               →  addNode('user')               →  CONVERSATION
tool_start              →  onTool('start') → showActivity →  ACTIVITY (#banner)
tool_end                →  onTool('end')   → hideActivityIfIdle → ACTIVITY
approval                →  addNode('approval')           →  CONVERSATION (control, not reply)
panel/modal/scene       →  panelBuffer.push              →  buffered → flush at finish()
choices.delta.content   →  ensureAssistant() + append    →  CONVERSATION (lazy, 真流式)
[DONE] / stream end     →  finish() finalize             →  CONVERSATION finalize + TTS + flush
error (before any δ)    →  showBanner(err) / history log →  ACTIVITY (no assistant bubble)
```

---

## 5. Target Interaction Model

| 阶段 | 聊天区（CONVERSATION） | Activity 层 |
|------|----------------------|-------------|
| 发送瞬间 | 仅 user 气泡 | （无变化） |
| 工具执行中 | 无 assistant 气泡 | "小6 正在处理…" banner |
| 首个真实 delta 到达 | assistant 气泡**此刻创建**，逐字 append | banner 仍可能在（工具未完） |
| 全部完成 | markdown finalize，可读 | banner 隐藏 |
| 全程无 delta（报错） | **不创建** assistant 气泡 | banner 显示错误（zz）/ 历史记录错误（chat.html） |

---

## 6. State Model

```
tool_start  ──► Activity: toolRunCount++ ; showActivity()        // 绝不创建 assistant 气泡
tool_end    ──► Activity: toolRunCount-- ; hideActivityIfIdle()  // 绝不创建 assistant 气泡
delta.content (first) ──► ensureAssistant() 创建气泡 + 启动 StreamingMarkdown
delta.content (subseq) ──► stream.update(reply)  // 追加，不替换
finish()    ──► if(an) stream.finalize() + 去 .streaming           // 无 an 则不 finalize（无空气泡）
              ──► if(reply) resultLog.unshift(...)                  // 空回复不写结果卡
              ──► if(reply && autoSpeak) speakText(reply)
              ──► flushRuntimePanels(panelBuffer)
error       ──► if(an) 在气泡内显示错误；else 仅 Activity/历史，不建气泡
```

---

## 7. Activity Lifecycle（独立于气泡）

- `tool_start` → `toolRunCount++` → `agentLog.unshift(...)` → `showActivity()` → `#banner "小6 正在处理…"`。
- `tool_end` → 标记 `ongoing:false` → `toolRunCount--` → `hideActivityIfIdle()`（归零才隐藏）。
- `finish()` → `toolRunCount = 0` → `hideBanner()`。
- Error（无 delta）→ `showBanner('请求失败 · 请检查核心服务')`（zz）/ `console.error`+历史（chat.html）。
- **`小6 正在处理…` 始终只在 Activity 层，绝不进入 Conversation。**

---

## 8. Files Modified

| 文件 | 改动 | 行 |
|------|------|----|
| `G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js` | 删除 send-time eager `addNode('assistant')`；新增 `ensureAssistant()`；`handle()` 首个 delta 调用它；`finish()`/`catch` 守卫空气泡；`resultLog` 仅非空写入 | L206–218, L256, L254(catch), L289–295(finish) |
| `G:\xiao6\xiao6-ui\gui\chat.html` | 删除 send-time eager `appendMsg('assistant','',true)`；首个 delta 惰性创建；`catch`/`finally` 守卫 `bubble` 为 null | L456–459, L487, L507–514 |

**未改动（确认 frozen）：** `dyna-orb.js` / `dyna-orb.html`（UI-03-B 参数锁定）、所有后端
（`server.py` / `server_handlers_chat.py` / `tools.py` / `agent_runtime.py`）、`electron/main.js`、
`fullscreen-presence.js`、UI-07/08 产出。

---

## 9. The Minimal Change（核心 diff 说明）

**zz-workspace.js**
```js
// BEFORE (eager, at send-time)
var an = addNode('assistant'); an.node.classList.add('streaming');
var meta = ...; var body = ...; an.bub.appendChild(meta); an.bub.appendChild(body);
var stream = new StreamingMarkdown(body);

// AFTER (lazy)
var an = null, body = null, stream = null;
function ensureAssistant() {
  if (an) return an;
  an = addNode('assistant'); an.node.classList.add('streaming');
  var meta = ...; body = ...; an.bub.appendChild(meta); an.bub.appendChild(body);
  stream = new StreamingMarkdown(body);
  return an;
}
// handle() 首个 delta：
if (dc) { ensureAssistant(); reply += dc; stream.update(reply); scrollChat(); }
// finish() 守卫：
if (an) { stream.finalize(); an.node.classList.remove('streaming'); }
// catch 守卫：
if (an) { ...show error in bubble... } else { showBanner('请求失败 · 请检查核心服务'); }
// resultLog 守卫：
if (reply) resultLog.unshift({ t: Date.now(), text: reply });
```

**gui/chat.html**
```js
// BEFORE
var bubble = appendMsg('assistant', '', true);
// AFTER
var bubble = null;
// 首个 delta：
if(!bubble) bubble = appendMsg('assistant', '', true);
// catch/finally 守卫 bubble 为 null（不渲染空气泡，仅写历史/console）
```

---

## 10. Verification Steps（已执行）

1. **语法检查** — `node --check zz-workspace.js` ✅ PASS。
2. **chat.html 内联脚本语法** — 提取 `<script>` 经 `vm.Script` 编译 ✅ `ALL_INLINE_SCRIPTS_OK`。
3. **无急切创建** — grep `addNode('assistant')` 全仓：live 代码仅 L212（在 `ensureAssistant` 内）；`gui/chat.html` 仅 L487（首个 delta）。旧 L207 / L457 已消失。
4. **调用点核对** — `ensureAssistant` 定义 L210，唯一调用 L256（首个 delta）。
5. **泄漏审计** — `gui/chat.html` grep `web_search|调用工具|工具返回|activePrefix` → 无命中。
   `zz-workspace.js` 中 `tool_start/tool_end` 仅经 `onTool` → Activity，无气泡。
6. **Activity 独立** — `onTool` 仍只调 `showActivity/hideActivityIfIdle`，未触碰气泡逻辑。

---

## 11. Real Chromium E2E — BLOCKED（沙箱限制）

同 UI-07/08：当前沙箱无显示 / 无麦克风 / 后端 `:8010` 未起 / 无真实游戏全屏环境，
**无法跑真实 Chromium E2E**。静态核对（语法 + 逻辑 + grep）全部通过，但运行时时序需真机验收。

**手动验收 recipe（真机 Windows）：**
1. 启动后端 `:8010` + 打开 `xiao6-space/index.html`（主 UI）。
2. 发送一条**会触发工具**的消息（如带联网搜索的提问）。
   - 预期：user 气泡出现；`#banner` 显示「小6 正在处理…」；**聊天区此时无 assistant 气泡**。
3. 观察首个 `choices.delta.content` 到达瞬间：**assistant 气泡此刻才出现**并逐字增长。
4. 全程不得出现空 assistant 气泡 / 「在呢老板…」类占位。
5. 发送一条**后端直接报错**的消息（断网/服务挂）：预期无 assistant 气泡，仅 banner/历史报错。
6. 同步在 `gui/chat.html` 重复上述 2–5，确认一致。

---

## 12. Test Cases（A–F）

| Case | 输入 | 预期 | 结果 |
|------|------|------|------|
| A | 普通问答（无工具） | user 气泡 → 首个 delta 才建 assistant 气泡 → 流式 | 静态 PASS，待 E2E |
| B | 触发工具的消息 | 工具期仅 Activity banner，无 assistant 气泡；delta 到才建 | 静态 PASS，待 E2E |
| C | 多工具串行 | 每个 tool_start/end 只动 Activity；气泡仅建一次（首个 delta） | 静态 PASS，待 E2E |
| D | 工具中即出错（无 delta） | 无 assistant 气泡；banner/历史报错 | 静态 PASS，待 E2E |
| E | approval 事件 | 建 approval 控制卡，**不**建 assistant 气泡 | 静态 PASS，待 E2E |
| F | panel/modal/scene | 缓冲，finish() 时 flush，不中断流式 | 静态 PASS，待 E2E |

---

## 13. UI Invariants（1–8，确认仍成立）

1. ✅ 真流式保留（append，非替换）。
2. ✅ 无空 assistant 气泡（惰性 + 守卫）。
3. ✅ 无 tool_start/end/result 作为 assistant 消息。
4. ✅ 无「在呢老板…」类提前占位。
5. ✅ `小6 正在处理…` 仅 Activity 层。
6. ✅ Voice / Activity / Presence / Conversation 四层解耦未破坏。
7. ✅ orb 视觉零改动（UI-03-B 锁定）。
8. ✅ 无后端改动。

---

## 14. Red-Line Audit

| 红线 | 状态 |
|------|------|
| 不改后端（server*.py / tools.py / agent_runtime.py） | ✅ 未触碰 |
| 不改 orb 视觉（dyna-orb.js/.html） | ✅ 未触碰 |
| Voice/Activity/Presence 解耦 | ✅ 保持 |
| 最小改动 zz-workspace.js + 同步 gui/chat.html | ✅ 仅此两文件 |
| 不泄漏工具名到对话 | ✅ grep 无命中 |
| 不引入第三方库 | ✅ 纯原生 JS |
| 不顺手优化 / 不做 UI-10 | ✅ 严格收口 |

---

## 15. Remaining Issues / Open Items

1. **Live Chromium E2E BLOCKED** — 沙箱无显示/麦克风/后端/游戏环境，真机验收 pending（见 §11 recipe）。
2. `gui/chat.html` 在「无 delta 即报错」时不渲染可见气泡，仅写历史 + `console.error`。这是严格遵循「首个 delta 前不建 assistant 气泡」的取舍；若你希望在 chat.html 也显式报错气泡，可单独开一轮（不属 UI-09 红线，但会改变当前行为，需你拍板）。
3. 建议下一步：**做一次完整 UI/UX 总体验收**（聊天 / Activity / 语音球 / 桌面常驻 / 全屏隐藏 / 启动入口 作为一个产品体验一次验收），发现真问题再集中收口——而非继续不停地 hotfix。

---

## 16. STOP

UI-09 已按规收口：聊天渲染时序修正（惰性 assistant 气泡）、真流式保留、Activity 独立、
无泄漏、无后端/orb 改动、两文件语法与逻辑静态验证通过。**本轮回停在报告交付，等真机 E2E 验收与你的下一步指令。**
