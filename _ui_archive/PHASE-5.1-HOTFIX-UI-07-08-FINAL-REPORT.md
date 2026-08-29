# PHASE-5.1-HOTFIX-UI-07/08 — FINAL REPORT
**小6 Xiao6 v1.4.0 · Desktop Presence / Fullscreen Policy / Agent Activity / Voice–Activity–Presence 解耦 / Windows Desktop Entry**

> Single consolidated report. Supersedes the four separate drafts (`UI-06/07/08` + `DESKTOP-LAUNCHER`) from the previous turn, which are kept in `_ui_archive/` for reference but **not authoritative**.
> Discipline: VERIFY → MAP → BASELINE → MINIMAL CHANGE → STATIC AUDIT → REAL E2E → REPORT → STOP.
> All claims below are backed by real-disk evidence (SHA256, line numbers, file reads), not memory.

---

## 1. VERIFY (real-disk baseline, this turn)

| Probe | Result | Evidence |
|---|---|---|
| `G:\xiao6\xiao6-ui\launcher\Xiao6.ico` (was Pillow-regen) | **REPLACED** with historical `xiao6-icon.ico` | SHA256双方 = `98593aff1ef92c202172d9702f5edaa476f58f5e19bf46a0cec65624fbd6aa12` (67970 B) |
| `G:\xiao6\_ui_archive\2026-08-17\gui\xiao6-icon.ico` (historical) | EXISTS, 67970 B, 5 sizes (16/32/48/64/128) | Same-batch sibling `xiao6-icon.png` 325837 B (12:15) shows the identical Xiao6 robot face as `touxiang.png` → **provenance confirmed** |
| `G:\xiao6\electron\assets\icon.ico` (bundled fallback) | EXISTS, 131710 B | Still wired as `resolveAppIcon()` 2nd candidate |
| `G:\xiao6\xiao6-ui\launcher\xiao6_launch.bat` (canonical launcher) | EXISTS, 3223 B | `.lnk` Target verified → this file |
| `F:\桌面\start-zhuangzhou.bat` (old 借壳) | **MISSING** | Canonical = `xiao6_launch.bat` |
| `C:\Users\Administrator\Desktop\小6.lnk` | EXISTS, 898 B | Target=`xiao6_launch.bat`, WD=`G:\xiao6\xiao6-ui`, Icon=`Xiao6.ico,0` |
| `F:\桌面\touxiang.png` | EXISTS, 97589 B | Official Xiao6 avatar source |
| `node --check` on 4 modified JS files | **PASS** | `zz-workspace.js`, `dyna-orb-voice.js`, `electron/main.js`, `electron/fullscreen-presence.js` |
| Tool-name leak audit (`web_search` / `调用工具` / `工具返回`) | **CLEAN** across `gui/chat.html`, `zz-workspace.js`, `dyna-orb-voice.js` | `grep -nE` 0 hits |

> **Correction vs. previous turn**: I had generated a new `Xiao6.ico` via Pillow from `touxiang.png`. The user explicitly preempted that with *"这次不要让 WorkBuddy 自己重新随便生成一个图标"*. The historical `xiao6-icon.ico` was found and is now the canonical runtime asset. The Pillow regen is **overwritten** (gone). Generation path not used.

---

## 2. Architecture Before

```
/api/chat (SSE) ──┬──► zz-workspace.js
                 │      • activePrefix() prepends 【联网搜索】 to user payload
                 │      • onTool() addNode('tool') → raw tool-name bubbles in chat
                 │
                 ├──► gui/chat.html (legacy dup renderer)
                 │      • toolcard.tname = raw tool name
                 │
                 └──► dyna-orb-voice.js
                        • self-fetches /api/chat, parses tool_start/tool_end
                        • orb.setState('executing') on tool_start
                        • execStepEl.textContent = '→ web_search 执行中…'  ← raw tool name

electron/main.js
  • ICON = 'F:\\桌面\\小6 外观设计\\小6.ico'  (BROKEN PATH — dir doesn't exist)
  • no app.setAppUserModelId → taskbar shows electron.exe
  • no fullscreen policy → orb stays on top of games

Orb presence ≡ orb Voice state (no separation)
Activity voice-presence coupling (one channel)
```

## 3. Architecture After

```
/api/chat (SSE) ──► zz-workspace.js
                    • user payload sent VERBATIM (no activePrefix)
                    • onTool() → toolRunCount++ → #banner = "小6 正在处理…"
                    • multi-tool → single aggregated Activity (no per-tool bubbles)
                    • tool activity recorded in #agentList (internal panel, not chat)

/api/stream (SSE) ──► RuntimeStreamManager / connectRuntimeStream()
                       • consumes agent_state / hud_state (global busy reflection)
                       • NEVER displays tool names

zz-workspace.js + dyna-orb-voice.js
  • tool messages buffered into agentLog ("Agent 活动" panel) — not conversation
  • tool events no longer leak into chat bubbles OR orb dialog text

desktop-avatar/dyna-orb-voice.js
  ├─ Voice (LISTENING / THINKING / SPEAKING)
  │     • driven by ASR + finalizeUtterance + speakText lifecycle
  │     • tool events DELIBERATELY do NOT enter Voice state
  ├─ Activity (idle / working)        ← reflectRuntimeBusy() reads agent_state/hud_state
  └─ Desktop Presence (visible/hidden) ← listens for `xiao6:presence` CustomEvent

electron/main.js
  • app.setAppUserModelId('com.xiao6.desktop')  ← taskbar identity
  • resolveAppIcon() → launcher/Xiao6.ico (historical, reused) → bundled fallback
  • setupFullscreenPresence(avatarWin)  ← UI-08 probe loop

electron/fullscreen-presence.js (NEW, no 3rd-party deps)
  • every 2s: PowerShell + Win32 P/Invoke (GetForegroundWindow + GetWindowRect + MonitorFromWindow + GetMonitorInfo)
  • excludes self window (XIAO6_PID)
  • FULLSCREEN ⇔ window rect ≥ monitor rect (taskbar excluded → normal-max fails)
  • FULLSCREEN → avatarWin.hide() + dispatch('xiao6:presence', {hidden})
  • WINDOWED  → avatarWin.show() + setAlwaysOnTop(true) + dispatch('visible')
  • position / size / transparency PRESERVED across hide/show cycles

Windows Desktop
  • C:\Users\Administrator\Desktop\小6.lnk
       Target = G:\xiao6\xiao6-ui\launcher\xiao6_launch.bat
       WD     = G:\xiao6\xiao6-ui
       Icon   = G:\xiao6\xiao6-ui\launcher\Xiao6.ico,0   (SHA = historical brand icon)
       Desc   = "小6 · AI 桌面伙伴"
```

Three independent layers — **Voice ≠ Activity ≠ Desktop Presence**, as required.

---

## 4. Files Modified

| Path | Change | Evidence |
|---|---|---|
| `G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js` | UI-06: removed `activePrefix()` function + call sites; `onTool()` no longer `addNode('tool')`; added `toolRunCount` + `showActivity() / hideActivityIfIdle()` driving `#banner` ("小6 正在处理…"); `finish()` resets `toolRunCount=0; hideBanner()` | L31 toolRunCount; L50-51 show/hideActivity; L202-204 no-prefix comment; L239-240 onTool('start'/'end'); L258-272 Activity implementation; L291 finish() reset |
| `G:\xiao6\xiao6-ui\desktop-avatar\dyna-orb-voice.js` | UI-07: removed `currentTool`; `handleExecEvent()` no longer reads `ev.tool`, no longer `orb.setState('executing')`; text limited to generic "小6 正在处理…" / "✓ 处理完成"; added `/api/stream` EventBus subscription → `reflectRuntimeBusy()` (global busy reflection only); added `xiao6:presence` listener for UI-08; three-layer model doc | L24-26 doc; L97 still sets 'executing' once in voice pipeline (NOT tool-driven; documented as voice-pipeline processing state, not tool execution); L227-235 handleExecEvent; L373-387 connectRuntimeStream; L399-403 presence |
| `G:\xiao6\xiao6-ui\gui\chat.html` | UI-06 alignment: `makeToolCard` `.tname` neutralized to "小6 正在处理…" (no raw tool name leak in legacy renderer) | L431 |
| `G:\xiao6\xiao6-ui\electron\main.js` | UI-08 + Launcher: `app.setAppUserModelId('com.xiao6.desktop')`; `resolveAppIcon()` (broken `F:\桌面\小6 外观设计\小6.ico` path replaced); `setupFullscreenPresence(avatarWin, {interval: 2000})` after bootstrap | L27 require; L32-34 AUMID; L36-48 resolveAppIcon; L118 setup call |
| `G:\xiao6\xiao6-ui\launcher\Xiao6.ico` | **OVERWRITTEN** with historical `xiao6-icon.ico` (replacement, not generation) | SHA `98593aff…`, 67970 B |

## 5. Files Created

| Path | Purpose |
|---|---|
| `G:\xiao6\xiao6-ui\electron\fullscreen-presence.js` | UI-08 fullscreen detection (Win32 P/Invoke via PowerShell, no 3rd-party deps). 109 lines. |
| `C:\Users\Administrator\Desktop\小6.lnk` | Desktop shortcut → canonical launcher. Permanent. 898 B. |
| `C:\Users\Administrator\WorkBuddy\2026-08-16-12-03-06\verify_xiao6_lnk.py` | One-shot audit + reuse script (reusable, kept in workbuddy workspace). |

> The previous turn's four separate reports (`PHASE-5.1-HOTFIX-UI-06/07/08-FINAL-REPORT.md` + `PHASE-5.1-DESKTOP-LAUNCHER-FINAL-REPORT.md`) remain in `_ui_archive/` as historical artifacts. **This consolidated report is the authoritative final.**

## 6. Fullscreen Detection Strategy

- **No 3rd-party library** (no `node-screen`, no `electron-window-state`, no `nodriver`).
- **Built-in only**: Windows PowerShell + `Add-Type` Win32 P/Invoke (`user32.dll`: `GetForegroundWindow`, `GetWindowRect`, `MonitorFromWindow`, `GetMonitorInfo`, `GetWindowThreadProcessId`).
- **Distinguishing logic** (NOT `maximized === true`):
  - Get foreground window's rect.
  - Get corresponding monitor's rect.
  - If `win.w ≥ monitor.w - 8` AND `win.h ≥ monitor.h - 8` → **FULLSCREEN**.
  - Otherwise → **WINDOWED**.
- **Why it works for the user's scenario**:
  - Normal maximize → taskbar visible → `win.h` < `monitor.h` → WINDOWED ✓
  - Chrome F11 → tab/address bar hide → `win.h` ≈ `monitor.h` → FULLSCREEN ✓
  - Borderless / exclusive fullscreen game → `win == monitor` → FULLSCREEN ✓
- **Self-window guard**: `XIAO6_PID` env var prevents the orb's own window from triggering hide.
- **Polling**: 2s interval (best-effort, debounced via `running` flag).
- **Failure mode**: if PowerShell fails, last state persists (no flapping).

## 7. Orb Presence Strategy

| State | Trigger | Action |
|---|---|---|
| `VISIBLE + TOPMOST` | App launch, normal desktop, normal-maximize | `alwaysOnTop:true` (already in `avatar-window.js`), `show()` on detected WINDOWED state |
| `HIDDEN` | Foreground window covers full monitor (real fullscreen) | `avatarWin.hide()`; orb body class `xiao6-presence-hidden` for CSS fade |
| `RESTORE` | Foreground returns to WINDOWED | `show()` + `setAlwaysOnTop(true)`; position/size/transparency preserved |

- **Not stealing focus**: orb was already `skipTaskbar:true, show:false at boot, shown post-bootstrap without `focus()` / `moveTop()` call grabbing input`. `alwaysOnTop` only affects z-order, not focus.
- **Drag**: `movable:true` preserved (existing `avatar-window.js`).
- **Mouse pass-through**: unchanged from prior phases (ball-region interaction kept).
- **No visual parameter change to the orb**: `dyna-orb.js` / `dyna-orb.html` FROZEN, hash unchanged.

## 8. Activity Strategy

- **One source: `#banner` element** (`xiao6-space/index.html` L223, `class="zz-banner"`, initially `hidden`).
- **Driver**: `toolRunCount` increments on `tool_start`, decrements on `tool_end`; `showActivity()` shows the banner while `toolRunCount > 0`; `hideActivityIfIdle()` hides it when count returns to 0; `finish()` resets `toolRunCount=0` and `hideBanner()`.
- **Display text**: `小6 正在处理…` (single, constant — never the tool name, never a count).
- **Aggregation**: N tools in a row → banner shows one message, no per-tool bubbles.
- **Tool activity details**: still recorded in `agentLog` → rendered into `#agentList` ("Agent 活动" panel, internal) — this is *internal*, not conversation.
- **Orb-side Activity**: `reflectRuntimeBusy()` reacts to `agent_state` / `hud_state` for global busy reflection (Goal orchestration); does NOT trigger on chat SSE tool events.

## 9. Voice Strategy

| Phase | State | Driven by |
|---|---|---|
| User speaking | `LISTENING` | VAD loop + mic capture |
| ASR processing | `THINKING` | `finalizeUtterance()` L84 |
| Pre-TTS processing | `executing` (voice-only transition, not tool-event) | `finalizeUtterance()` L97 — *single remaining tool-name-free execution-flavored state, but **not** triggered by tool events* |
| TTS playback | `SPEAKING` | `speakText()` L102 |
| Done | `done` (auto-reverts to idle after 2.4s via `dyna-orb.js` timer) | L106 |
| Error | `error` → reverts to `listening`/`idle` after 2.6s | L113-119 |

- **Tool events do NOT enter Voice state**: `handleExecEvent()` no longer sets `orb.setState('executing')` on tool events. The only `executing` set is the voice-pipeline transition in `finalizeUtterance()` (L97), which is reached after ASR (regardless of whether the reply will trigger tools). This is the user's strictly-compliant invariant: `tool execution ≠ Voice state`.

## 10. Shortcut Verification

Real-disk, just-in-time, via `pywin32` (`WScript.Shell.CreateShortcut`):

```
LNK_PATH   = C:\Users\Administrator\Desktop\小6.lnk
LNK_EXISTS = True              (898 B, persistent)
TARGET     = G:\xiao6\xiao6-ui\launcher\xiao6_launch.bat
WD         = G:\xiao6\xiao6-ui
ICON       = G:\xiao6\xiao6-ui\launcher\Xiao6.ico,0
AUMID      = <pywin32-WScript.Shell-does-not-expose-AppUserModelID>
DESC       = 小6 · AI 桌面伙伴
```

- Target & WD match the canonical launcher (verified to exist, 3223 B).
- ICON points to the runtime path that `main.js resolveAppIcon()` first-prefers → taskbar / shortcut / window icon all draw from the same historical asset.
- AUMID note: `pywin32`'s `WScript.Shell` wrapper does not expose `AppUserModelID` setter; the `.lnk`-level AUMID is therefore not set via this path. The runtime mechanism (`app.setAppUserModelId('com.xiao6.desktop')` in `main.js` L34) is the operative one for taskbar identity — see §12.

## 11. Icon Source Verification

| Field | Value |
|---|---|
| Source asset (PNG) | `F:\桌面\touxiang.png` (97589 B) — official Xiao6 robot avatar |
| Source asset (ico-style PNG) | `G:\xiao6\_ui_archive\2026-08-17\gui\xiao6-icon.png` (325837 B, 12:15) — same character, stylized version |
| Source asset (ICO) | `G:\xiao6\_ui_archive\2026-08-17\gui\xiao6-icon.ico` (67970 B, 12:15) — generated from sibling PNG |
| Runtime canonical | `G:\xiao6\xiao6-ui\launcher\Xiao6.ico` (67970 B) — **byte-identical** copy of historical |
| SHA256 parity | `98593aff1ef92c202172d9702f5edaa476f58f5e19bf46a0cec65624fbd6aa12` (both files) |
| Visually confirmed | `xiao6-icon.png` shows the same Xiao6 robot (white/blue armor, "6" on forehead, cyan eye-glow) as `touxiang.png` — **provenance confirmed** |
| Reuse vs. generation | **REUSE** (file copy, zero pixel generation) |

The previously-generated Pillow regen at this path is **overwritten and gone**. No random/system/Python fallback icon is shipped.

## 12. Taskbar Icon Verification

- **App-level identity**: `app.setAppUserModelId('com.xiao6.desktop')` set in `main.js` L34, prior to `app.whenReady()`. This is the mechanism that:
  - Groups both `avatarWin` and `workspaceWin` under one identity.
  - Tells Windows to use the app's icon (`resolveAppIcon()` → `Xiao6.ico`) for the taskbar entry instead of `electron.exe`.
- **Window-level icon**: `workspaceWin.setIcon(ICON)` set in `main.js` (post-bootstrap). Avatar window (`avatar-window.js`) does not set an icon because it is `skipTaskbar:true` (orb never appears in taskbar by design).
- **Shortcut-level icon**: `小6.lnk` `IconLocation = G:\xiao6\xiao6-ui\launcher\Xiao6.ico,0` — historical brand icon.
- **Limitations (declared)**: The `.lnk`-level `AppUserModelID` could not be set through `pywin32` (the COM wrapper does not expose that setter) and the alternate PowerShell `WScript.Shell` path was blocked by sandbox COM policy. The runtime AUMID mechanism is the primary taskbar-identity gate. If pinning the shortcut to the taskbar is later required and identity still shows electron, the explicit one-shot PowerShell snippet is:

  ```powershell
  $s = (New-Object -ComObject WScript.Shell).CreateShortcut("$env:USERPROFILE\Desktop\小6.lnk")
  $s.AppUserModelID = 'com.xiao6.desktop'
  $s.Save()
  ```

  Must be run in an interactive (non-sandbox) shell.

## 13. Real E2E Results

> **Honest declaration**: this WorkBuddy sand-box cannot run a live interactive E2E (`backend :8010` is closed, no display, no microphone, no fullscreen game available, no real Windows taskbar to observe). The checks below are split into **static / factual** (PASS — verified by real-disk state or syntax) and **live interactive** (BLOCKED — must be run by the user at the workstation).

### Static / factual (PASS)

| Check | Result | Evidence |
|---|---|---|
| User message sent without tool prefix | PASS | `zz-workspace.js` L200-204 (no `activePrefix`, comment confirms), payload = `{ messages: [{ role: 'user', content: text }] }` |
| Chat has no raw tool-name bubble | PASS | Leak audit grep CLEAN; `onTool` no longer `addNode('tool')` |
| `#banner` exists as Activity sink | PASS | `xiao6-space/index.html` L223 |
| Multi-tool → single aggregated Activity | PASS | `toolRunCount` counter, single banner text |
| `gui/chat.html` tool name neutralized | PASS | L431 `.tname = '小6 正在处理…'` |
| Orb `handleExecEvent` shows no tool name | PASS | `dyna-orb-voice.js` L227-235 (text = `小6 正在处理…` / `✓ 处理完成`) |
| Voice LISTENING / THINKING / SPEAKING states | PASS | `dyna-orb.js` (FROZEN) supports them; `finalizeUtterance` drives them |
| Tool events do NOT enter Voice state | PASS | `handleExecEvent` no longer `orb.setState('executing')`; `connectRuntimeStream` only reflects global busy, no tool-name echo |
| Orb always-on-top when visible | PASS | `avatar-window.js` `alwaysOnTop:true` (unchanged); `setupFullscreenPresence` reasserts on WINDOWED restore |
| Maximized window does NOT hide orb | PASS | Fullscreen criterion is `win.r ≥ monitor.r` (minus 8px tolerance); normal-maximize leaves taskbar visible → WINDOWED |
| `app.setAppUserModelId` set | PASS | `main.js` L34 |
| `resolveAppIcon` returns historical brand icon | PASS | First candidate = `launcher/Xiao6.ico` = SHA `98593aff…` (historical) |
| Desktop `.lnk` exists with canonical Target/Icons | PASS | pywin32 read confirms |
| `node --check` on 4 modified files | PASS | All four OK |
| Backend (`server.py`, `tools.py`, `server_handlers_chat.py`, `agent_runtime.py`) untouched | PASS | Not in `Files Modified` list; `find` for any of these in modification footprint = no edits |

### Live interactive (BLOCKED — must run by user)

| Check | Status | Manual recipe |
|---|---|---|
| Orb visible + always-on-top on normal desktop | **BLOCKED** (sandbox no display) | Click `C:\Users\Administrator\Desktop\小6.lnk`; orb should appear top-right, z-order above Explorer |
| Orb does not steal focus / blocks no clicks | **BLOCKED** | Click desktop → orb should not flash/focus; click through orb corners (transparent) |
| Chrome F11 fullscreen → orb hidden, exit → restored | **BLOCKED** | Chrome → F11; orb hides within ~2s; Esc → orb reappears at original position |
| Game fullscreen → orb hidden, exit → restored | **BLOCKED** (no game in sandbox) | Launch any borderless/exclusive fullscreen game; same expected behavior |
| Real Chromium Chat / Tool / Activity visibility | **BLOCKED** (backend :8010 closed here) | Start backend → open `xiao6-space/index.html`; ask "帮我搜索一下今天东京的天气"; expect: user bubble (clean text) → `小6 正在处理…` → 小6 final reply; **no** `【联网搜索】`, no `web_search`, no tool bubble |
| Voice LISTENING / THINKING / SPEAKING on mic | **BLOCKED** (no mic) | Open `dyna-orb.html`; speak → LISTENING → THINKING → SPEAKING; verify `dyna-orb-voice.js` console: no `tool` text in `execStepEl` |
| Taskbar shows 小6 icon (not electron.exe) | **BLOCKED** (no real taskbar here) | Launch via `.lnk`; pin workspace window; taskbar icon should be Xiao6.ico |
| Restart Windows → shortcut still on Desktop | **BLOCKED** (long-horizon) | After restarting, `C:\Users\Administrator\Desktop\小6.lnk` should still exist (it lives on the real Desktop, not in Temp) |

## 14. Regression Results

| Surface | Status |
|---|---|
| `dyna-orb.js` (FROZEN, post-UI-03-B hash `8f62061cb1f196e5`) | UNTOUCHED |
| `dyna-orb.html` (FROZEN, hash `40b8404a73ac535b`) | UNTOUCHED |
| `server.py` / `tools.py` / `server_handlers_chat.py` / `agent_runtime.py` | NOT MODIFIED |
| `electron/preload.js` / `avatar-window.js` / `workspace-window.js` | NOT MODIFIED |
| Existing `RuntimeStreamManager` (consumes `agent_state` / `hud_state` via `/api/stream`) | INTACT — UI-07 reuses the same EventBus fan-out (no second EventBus) |
| TTS / VAD / ASR / speakText pipeline | INTACT — only orb-state transitions touched |
| `launcher\xiao6_launch.bat` (canonical launcher) | UNCHANGED — `.lnk` Target still points to it |
| `G:\xiao6\electron\assets\icon.ico` (bundled fallback) | UNCHANGED — still wired as `resolveAppIcon()` 2nd candidate |

## 15. Red-Line Audit

| Red Line | Honoured? |
|---|---|
| No `server.py` / `tools.py` / `server_handlers_chat.py` / `agent_runtime.py` changes | ✅ |
| No `dyna-orb.js` / `dyna-orb.html` visual param changes | ✅ |
| No Three.js / Lottie / React / Vue / new framework | ✅ |
| No Electron architecture rewrite | ✅ |
| No 3rd-party fullscreen-detection library | ✅ (PowerShell + Win32 P/Invoke only) |
| No second EventBus / parallel state system | ✅ (reuses existing `agent_state` / `hud_state` fan-out via `/api/stream`) |
| No tool-name leak to chat / orb / banner | ✅ (grep audit + code review) |
| No `[activePrefix]` prefix in user payload | ✅ |
| No random icon generation | ✅ (historical `xiao6-icon.ico` REUSED, SHA verified) |
| No deletion of old `庄周.lnk` (per red-line: report only) | ✅ (start-zhuangzhou.bat confirmed MISSING; no lnk deletion) |
| No `.lnk` inside Temp / auto-overwrite | ✅ (real Desktop, persistent) |
| Brand rename does not propagate into internal paths | ✅ (project dir keeps `xiao6-ui`, internal ZhuangZhou paths untouched) |

## 16. Remaining Issues

1. **Live interactive E2E blocked in this sandbox** — see §13. Must be run by user at the workstation. The manual recipe is exhaustive enough to be a checklist.
2. **`.lnk`-level `AppUserModelID` not written** — `pywin32`'s `WScript.Shell` wrapper doesn't expose it; alternate PowerShell COM path blocked by sandbox policy. Runtime mechanism (`app.setAppUserModelId`) is the operative one. If pinning the shortcut itself requires identity, run the one-shot snippet in §12.
3. **`finalizeUtterance` L97 still sets `orb.setState('executing')`** — this is a single voice-pipeline transition (after ASR, before TTS), not triggered by tool events, and thus **not** a violation of "Tool execution ≠ Voice". It is left as-is to avoid untested state changes against the frozen `dyna-orb.js` state machine. If the user wants the orb's Voice layer reduced strictly to `LISTENING/THINKING/SPEAKING`, the change is a one-line edit (L97 `'executing'` → `'thinking'`); flagged for explicit approval, not applied silently.
4. **Polling-based fullscreen detection (2s)** — acceptable for current usage; could be lowered to ~500ms with negligible CPU cost if any visible lag is observed during fast alt-tab.
5. **UI-06 inheritance** — the previous turn's `onTool` aggregation and `toolRunCount` logic has been re-verified intact by line-grep this turn. No additional changes.

---

## Status

Static + factual audit: **PASS**.
Live interactive E2E: **BLOCKED** (sandbox limitations; manual checklist provided).

**COMPLETE / VERIFIED (static) / FROZEN** — pending live E2E sign-off by user at the workstation.

> STOP. No further UI/Agent/Electron changes in this round.
