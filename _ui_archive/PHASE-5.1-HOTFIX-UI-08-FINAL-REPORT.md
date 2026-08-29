# PHASE-5.1 HOTFIX · UI-08 FINAL REPORT
**Fullscreen / Launcher / Icon / Taskbar E2E — Orb Desktop Presence policy**
Date: 2026-08-18 · Author: 阿枢

---

## 0. Scope & Red Lines (honored)
- **Goal:** Orb **VISIBLE + TOPMOST** on normal desktop and normal maximized apps (browser / VS Code / File Explorer). Orb **HIDDEN** when the foreground window is a **true fullscreen** app (F11 browser, borderless/exclusive fullscreen game); restore VISIBLE+TOPMOST on exit. Distinguish normal-maximize vs real-fullscreen. **NO 3rd-party library.**
- **Red lines honored:** no npm/3rd-party dependency; no Electron refactor beyond the required presence hook; `dyna-orb.js`/`dyna-orb.html` FROZEN.

## 1. Approach (no 3rd-party lib)
Detecting a true-fullscreen foreground window on Windows **without** a native module is done with **Windows PowerShell + Win32 P/Invoke via `Add-Type`** — both built into the OS. A small C# snippet (compiled in-process by PowerShell) calls `GetForegroundWindow` / `GetWindowRect` / `MonitorFromWindow` / `GetMonitorInfo` / `GetWindowThreadProcessId`.
- **Heuristic:** if the foreground window's rectangle covers the entire monitor (±8px, taskbar excluded) **and** is not our own process → **FULLSCREEN** → hide orb. Otherwise → **WINDOWED/SELF** → ensure orb visible + TOPMOST.
- A normally maximized window leaves the taskbar visible → its rect ≠ monitor rect → treated as windowed (orb stays). This cleanly separates "normal maximize" from "real fullscreen".

## 2. Changes
### New file `electron/fullscreen-presence.js`
- `setupFullscreenPresence(avatarWin, {interval:2000})`: spawns `powershell.exe` (hidden) every 2s; parses `FULLSCREEN`/`WINDOWED`/`SELF`; on FULLSCREEN → `avatarWin.hide()` + dispatch `xiao6:presence` `hidden` to the orb renderer; else → `avatarWin.show()` + `setAlwaysOnTop(true)` + dispatch `visible`. Skips overlapping probes (`running` guard). No-op on non-Windows.

### `electron/main.js` wiring
| Line | Change |
|---|---|
| L27 | `const { setupFullscreenPresence } = require('./fullscreen-presence');` |
| L34 | `app.setAppUserModelId('com.xiao6.desktop');` (stable AUMID → taskbar shows 小6, not electron.exe) |
| L38-48 | `resolveAppIcon()` — prefers `launcher/Xiao6.ico`, falls back to `G:\xiao6\electron\assets\icon.ico`; replaces the **broken** `F:\桌面\小6 外观设计\小6.ico` path |
| L118 | `setupFullscreenPresence(avatarWin, { interval: 2000 });` after orb window creation |
| L127 | `workspaceWin.setIcon(ICON)` so the taskbar shows Xiao6.ico |

### `desktop-avatar/dyna-orb-voice.js` (Presence seam, from UI-07)
- `document.addEventListener('xiao6:presence', …)` toggles `xiao6-presence-hidden` body class (passive; main.js owns the decision).

## 3. Verification performed
- `node --check main.js` → **MAIN_OK**; `node --check fullscreen-presence.js` → **FP_OK**.
- Grep confirms `setAppUserModelId`, `setupFullscreenPresence`, `resolveAppIcon`, `setIcon(ICON)`, and the require are all present and correctly placed.
- Logic review: `hide()`/`show()` preserve `alwaysOnTop`; `self` PID exclusion avoids self-hide when the orb/workspace is focused.

## 4. E2E status
- **Live fullscreen E2E could NOT run here** (no display / no fullscreen game in sandbox; backend `:8010` CLOSED). Static + file/OS-level verification only.
- **Manual E2E checklist (user's interactive env, Windows):**
  1. Launch 小6 → orb visible + on top of desktop and of a maximized browser/VS Code/Explorer.
  2. Open a fullscreen game (or press F11 in Chrome) → orb **disappears**.
  3. Exit fullscreen → orb **reappears** on top.
  4. Taskbar shows **Xiao6.ico** (not electron.exe) for the running app.

## 5. STOP
UI-08 is **frozen**. No further changes without explicit review.
