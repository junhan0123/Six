# PHASE-5.1 HOTFIX · UI-06 FINAL REPORT
**Frontend message-construction error + Tool-Event leak → Activity Architecture (minimal closure)**
Date: 2026-08-18 · Author: 阿枢

---

## 0. Scope & Red Lines (honored)
- **Goal:** (1) stop `activePrefix()` from polluting the user-message payload sent to `/api/chat`; (2) stop `onTool()` rendering raw tool names as **conversation chat bubbles**; (3) surface a minimal **Activity** state ("小6 正在处理…") during tool execution, cleared after the last tool ends.
- **Red lines honored:** NO backend writes (`server.py` / `server_handlers_chat.py` / `tools.py` / `agent_runtime.py` untouched); `dyna-orb.js` + `dyna-orb.html` left **FROZEN**; no Electron refactor; no new frameworks.
- **Out of scope:** visual redesign, Agent/Goal rework.

## 1. VERIFY (before change) — disk-real state
- `zz-workspace.js` L30 `toolModes={think:false,web:true,code:'auto'}` only drives **header/settings toggle highlight** (L591/L596), NOT a backend feature.
- `activePrefix()` (L193-199) produced `【联网搜索】` etc. and was prepended to `text` at L205-206 **before** the payload was built → both the user bubble AND the backend payload carried the label.
- `onTool()` (L261-272) created `addNode('tool')` bubbles rendering `调用工具 <b>{tool}</b> …` with the **raw tool name** in the conversation.
- **Backend grep:** no `.py` parses `【联网搜索】` (only unrelated `【…】` log prefixes). Removing the prefix is **safe**.
- `#banner` (`zz-banner`, L223) is a hidden transient element; `showBanner`/`hideBanner` (L46-47) are defined but **never called elsewhere** → safe to repurpose as the Activity indicator.

## 2. Changes — `xiao6-space/js/zz-workspace.js`
| Where | Before | After |
|---|---|---|
| L30 (closure vars) | — | added `var toolRunCount = 0;` (drives Activity indicator) |
| L46-47 | `hideBanner()` only | + `showActivity()` / `hideActivityIfIdle()` helpers (gate on `toolRunCount`) |
| L193-201 | `function activePrefix(){…}` + `function sendChat(` | removed `activePrefix` entirely (dead after edit) |
| L205-206 (in `sendChat`) | `var prefix=activePrefix(); if(prefix&&…) text=prefix+text;` | removed — user text sent **verbatim** |
| L261-272 (`onTool`) | `addNode('tool')` bubble with raw `esc(tool)` | **no conversation bubble**; increments/decrements `toolRunCount`; records in `agentLog` (→ "Agent 活动" panel); calls `showActivity()` / `hideActivityIfIdle()` |
| L291 (`finish`) | — | `toolRunCount=0; hideBanner();` (defensive clear) |

**Net effect:** the user's typed text reaches the backend unchanged; tool execution is an **Agent Activity** (visible in the dedicated "Agent 活动" panel via `agentLog`/`renderAgent`), and a minimal "小6 正在处理…" banner shows only while ≥1 tool runs, disappearing on the last `tool_end` / stream finish. The conversation itself only contains user + assistant messages.

## 3. Secondary alignment — `gui/chat.html` (legacy DSH desktop renderer)
- L431 `c.querySelector('.tname').textContent = tool || '工具';` → `'小6 正在处理…'` (UI-06: no raw tool-name leak on the legacy surface). *(Applied on retry after an EBUSY transient lock from the running shell.)*

## 4. Verification performed
- `node --check zz-workspace.js` → **SYNTAX_OK**.
- Grep confirms: `activePrefix` / `addNode('tool')` / `toolnode` fully removed; `toolRunCount` + `showActivity`/`hideActivityIfIdle` present; "小6 正在处理…" present.
- `gui/chat.html` grep confirms neutral label landed.
- Frozen files `dyna-orb.js` / `dyna-orb.html` **not touched**.

## 5. E2E status
- **Live Chat/Tool/Activity E2E could NOT run here:** backend `:8010` is **CLOSED** in this sandbox (no runtime, no display). Static + file/OS-level verification only.
- **Manual E2E checklist (user's interactive env):**
  1. Launch 小6 → open Advanced Workspace; send a message that triggers a tool (e.g. web search).
  2. Confirm the user bubble shows **only your typed text** (no `【联网搜索】` prefix).
  3. Confirm **no** "调用工具 X" bubble appears in the conversation.
  4. Confirm a transient "小6 正在处理…" indicator shows during tool run and clears when the assistant reply streams in.
  5. Open the "Agent 活动" tab → tool executions are logged there (internal, not conversation).

## 6. STOP
UI-06 is **frozen**. No further changes without explicit review.
