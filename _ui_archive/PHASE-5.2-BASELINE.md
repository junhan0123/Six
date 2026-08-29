# PHASE 5.2 — BASELINE (Pre-Change Snapshot)
# 小6 Xiao6 v1.4.0 · Desktop Product UX FINAL ACCEPTANCE & CONSOLIDATED FIX

> Baseline captured BEFORE any Edit/Write in this phase. All values below are
> real disk state, measured with `sha256sum` / `ls` / `node --check` on 2026-08-18.
> Frozen deliverables from prior phases (UI-06/07/08/09/10 + PHASE 5.1 FINAL) are
> verified present and UNCHANGED.

## 1. Date & Environment
- Captured: 2026-08-18 12:46 GMT+8 (session clock)
- OS: Windows (win32), Git-Bash shell
- Node (managed): 22.22.2 — `C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2/node.exe`
- Python venv (official): `C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
- VCS: **NOT a git repository** (`git rev-parse` → fatal: not a git repository).
  → Version identity is by file SHA256, not commit hash.

## 2. Canonical Launcher
- Path: `G:\xiao6\xiao6-ui\launcher\xiao6_launch.bat`
- Behavior (verified by read):
  - Sets ROOT=`G:\Xiao6\xiao6-ui`, LOGDIR=`%ROOT%\launcher\logs`
  - Uses official venv python; falls back to `python` only if missing
  - Probes `127.0.0.1:8010`; if free, starts `server.py` (minimized) and waits up to 40×0.5s
  - Starts Electron from `%ROOT%\launcher\electron-bin\electron.exe` (skip if already running)
  - Opens web UI `http://localhost:8010/xiao6-space/index.html`
- sha256: `84efe20eddf05897c3e94b4b1b43efb07b9343a0d7851fdfb6dceaf911c8f235`

## 3. Icon (brand asset — DO NOT REGENERATE)
- Path: `G:\xiao6\xiao6-ui\launcher\Xiao6.ico`
- **sha256: `98593aff1ef92c202172d9702f5edaa476f58f5e19bf46a0cec65624fbd6aa12`** ✅ matches
  the frozen red-line value. Unchanged.

## 4. Shortcut
- Path: `C:\Users\Administrator\Desktop\小6.lnk`
- Exists (size 898 B, mtime 2026-08-18 16:02). Target resolves via launcher. ✅

## 5. Port & Protocol
- Backend HTTP port: **8010** (frozen; no change permitted)
- Protocol: stdlib `http.server` SSE (`/api/chat`, `/api/health`, `/api/ready`, `/api/speak`, `/api/asr`, `/api/stream`)
- Electron `resolveBackendPort` honors `XIAO6_PORT`, defaults 8010, offset fallback on conflict.

## 6. UI Entry Points
- Primary web UI: `G:\xiao6\xiao6-ui\xiao6-space\index.html` (loads `js/zz-workspace.js?v=31`)
  - sha256: `ba9d434417d762f3df01aa7088684ab632669ec1d224772155aa6744e1609937`
- Legacy chat entry: `G:\xiao6\xiao6-ui\gui\chat.html` (already self-clears input on send)
  - sha256: `473f1944519c3c9580846a9811d32d7bea7149095e10c6046d3f51d32f111a10`
- Voice Orb: `G:\xiao6\xiao6-ui\desktop-avatar\dyna-orb.html` + `dyna-orb-voice.js`

## 7. Frozen Source Files — Verification (read + sha256 + syntax)
| File | sha256 | node --check | Notes |
|---|---|---|---|
| xiao6-space/js/zz-workspace.js | `d2a7203cf4f79d152d1fb67e0145a14f270c6d2e984d01de6f873ef555c27325` | OK | UI-09 (L210 ensureAssistant, L222 payload uses `text`) + UI-10 (L369-381 submitCmd clears cmdInput only after send, busy-safe) present & intact |
| desktop-avatar/dyna-orb-voice.js | `72dace22f962c77e698512b6bf91953427231c3b8ac1979db9ef91da90f90f78` | OK | UI-07 three-layer model; NEVER surfaces raw tool names; reflects `xiao6:presence`; SSE chat without tool-name leakage |
| electron/main.js | `ee6c238b51292804d32665be386d38fd32b661adc36fe5029feafb2a9b523a45` | OK | AUMID `com.xiao6.desktop`; `resolveAppIcon()` prefers `launcher/Xiao6.ico`; port 8010; single-instance lock |
| electron/fullscreen-presence.js | `68f15a7b2ca5ed2d617408db4315b831e29e9d04997fd856bad1dfec771d5a3b` | OK | PowerShell+Win32 P/Invoke true-fullscreen detection; dispatches `xiao6:presence`; hides orb on true fullscreen |
| desktop-avatar/dyna-orb.js | `8f62061cb1f196e5cdce3eeb7bbfb37a582a6d0fc078fb2d2e0722baa8ab3407` | OK | Frozen (do not modify) |
| launcher/xiao6_launch.bat | `84efe20eddf05897c3e94b4b1b43efb07b9343a0d7851fdfb6dceaf911c8f235` | n/a | Canonical launcher |
| server.py | `0517fa729a4e9a138400f34889863b974170ede0cea2a74f3cd609bcad0680d6` | n/a | Backend — FROZEN (P0/P1 only, with record-first) |

## 8. Four-Layer Separation Model (verified present in code)
- **Voice**: orb state machine IDLE/LISTENING/RECOGNIZING/THINKING/SPEAKING/ERROR/DONE (`dyna-orb-voice.js`)
- **Activity**: `showActivity()`「小6 正在处理…」banner while tools run; tool events → generic indicator only, NEVER tool names
- **Conversation**: `#chatList` bubbles; `tool_*` SSE events routed to Activity, NEVER into conversation text
- **Presence**: `xiao6:presence` signal from `fullscreen-presence.js` → orb hides over true fullscreen

## 9. Red-Line Pre-Conditions (all satisfied at baseline)
- [x] Xiao6.ico SHA256 unchanged (`98593aff…`)
- [x] No backend (server.py) modifications since PHASE 5.1
- [x] dyna-orb.js / dyna-orb.html unmodified
- [x] UI-09 / UI-10 changes present and intact (see §7)
- [x] Shortcut `小6.lnk` present, target = launcher
- [x] Port 8010 unchanged
- [x] No React/Vue/Three.js/Lottie introduced into runtime paths
- [x] Real streaming preserved (lazy bubble + first-delta creation)

---
*Baseline is a read-only snapshot. No files were modified to produce it.*
