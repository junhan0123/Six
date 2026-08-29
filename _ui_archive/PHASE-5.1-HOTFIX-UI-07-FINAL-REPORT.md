# PHASE-5.1 HOTFIX · UI-07 FINAL REPORT
**Desktop Orb wrong coupling → three-layer state model (decouple from chat SSE tool events)**
Date: 2026-08-18 · Author: 阿枢

---

## 0. Scope & Red Lines (honored)
- **Goal:** decouple `dyna-orb-voice.js` from its self-`fetch('/api/chat')` parsing of `tool_start`/`tool_end` → `orb.setState('executing')` + **showing raw tool names**; re-subscribe to `agent_runtime.py`'s `agent:state`/`hud_state` EventBus; establish a **three-layer** model (Voice / Activity / Desktop Presence); **orb must NEVER show raw tool names**.
- **Red lines honored:** no backend writes; `dyna-orb.js`/`dyna-orb.html` FROZEN; no frameworks.

## 1. VERIFY (before change) — disk-real state
- `dyna-orb-voice.js` L219-230 `handleExecEvent()` did `execStepEl.textContent='→ '+currentTool+' 执行中…'` and `orb.setState('executing')` on every `tool_start`/`tool_end` → **raw tool name leaked** into the orb's exec dialog.
- `chatStream()` L164-167 called `handleExecEvent(j)` on any `xiao6_event`.
- **Critical VERIFY finding (from UI-04 / agent_runtime.py):** `agent_runtime._publish_state` emits `agent:state`/`hud_state` **ONLY inside the Agent/Goal orchestration loop — NOT in the chat `run_fc_loop`.** Therefore the orb **cannot** receive tool-execution Activity from the EventBus during a normal voice chat. → The orb's **Activity layer during voice chat must be driven by its own reply-waiting lifecycle**; the EventBus subscription is a *global busy reflection* (Goal mode) and must never surface tool names.

## 2. Changes — `desktop-avatar/dyna-orb-voice.js`
| Where | Change |
|---|---|
| Top (L7 area) | Added **three-layer model doc comment** (Voice / Activity / Presence) |
| `handleExecEvent()` (L219-230) | Rewritten: on `tool_start` → `execStepEl='小6 正在处理…'`; on `tool_end` → `'✓ 处理完成'`. **No raw tool name. No `orb.setState`.** |
| `var currentTool=''` (L190) | **Removed** (no longer referenced) |
| New: `connectRuntimeStream()` / `reflectRuntimeBusy()` | Subscribes to `/api/stream` EventSource; on `hud_state`/`agent_state` with busy-ish state, sets orb `'thinking'` **only if idle** (global reflection, never tool names). Auto-reconnect. |
| New: `xiao6:presence` listener | `document.addEventListener('xiao6:presence', …)` toggles `xiao6-presence-hidden` body class — the **Desktop Presence** seam consumed by UI-08. |
| `finalizeUtterance()` | `orb.setState('executing')` (L97) kept as the **generic processing visual** (no name). Voice flow: thinking → executing → speaking → done. |

**Net effect:** the orb no longer displays or acts on raw tool names. Tool events reduce to a generic "处理中 → 完成" indicator. The orb reflects global runtime busy state via the EventBus subscription without leaking names. The Presence layer is a passive receiver of `xiao6:presence` (owned by `main.js`, UI-08).

## 3. Verification performed
- `node --check dyna-orb-voice.js` → **SYNTAX_OK**.
- Grep confirms: `currentTool` gone; `handleExecEvent` shows only generic text; `xiao6:presence` + `connectRuntimeStream` present; no raw-tool-name path remains.

## 4. E2E status
- **Live Voice/Orb E2E could NOT run here** (backend `:8010` CLOSED; no mic/display). Static + file-level verification only.
- **Manual E2E checklist (user's interactive env):**
  1. Launch 小6, speak a request that triggers a tool.
  2. Watch the orb + exec dialog: confirm it shows "小6 正在处理…" → "✓ 处理完成" and **never** a raw tool name (e.g. `search_web`).
  3. Confirm orb visual states cycle idle→listening→thinking/executing→speaking→done without tool-name text.
  4. (Optional) Trigger a Goal/Agent run; confirm the orb reflects global busy via `hud_state` without names.

## 5. STOP
UI-07 is **frozen**. No further changes without explicit review.
