# UI-v4 Phase 8 — Implementation

**Phase:** Identity Refinement (Phase 8 of v4)
**Identity:** Senior Product Designer + Frontend Architect
**Scope:** v4 **presentation layer only**. No backend, no agent runtime, no new events, no new pages, no dashboard, no new features.
**Discipline chain:** Audit → Design → Implement → Verify → Document → STOP.

This file records exactly what changed, the function signatures that matter, and the
evidence that every red line was respected.

---

## 0. Red-line compliance (summary, full proof in §5)

| Red line | Status | Proof |
|---|---|---|
| 不恢复旧 UI | ✅ | v4 only reuses capability singletons; never loads `app.js`/`main-orb.js`/galaxy/three (see §5.4) |
| 不修改 Backend | ✅ | Only `GET` reads of existing endpoints; zero writes from v4 JS |
| 不修改 Agent Runtime | ✅ | v4 only *subscribes* to existing `agent_state` SSE; `AvatarState.derive` untouched |
| 不新增 Event | ✅ | Reuses `ZZSSE.onMessage` + existing `xiao6_event === 'agent_state'`; no new event names |
| 不新增页面 | ✅ | Single `<main>` space; Overlay is in-place focus, not a route |
| 不引入 Dashboard | ✅ | No stat panels; Context is 3 sentences, not metric cards |
| 不增加功能 | ✅ | Only re-expresses existing data (goals/memories/knowledge) in human language |

---

## 1. `index.html` (97 lines)

**What changed:** Rewritten as a single calm space. DOM is minimal and semantic.

Structure (top → bottom inside `<main id="presenceSpace" class="space">`):
- `.space__field` — ambient environment field (blur + grain), `aria-hidden`, carries no information.
- `.presence` (`#aiCore`, `data-state="idle"`) — the AI Core:
  - `.orb` → `.orb__aura` / `.orb__ring` / `.orb__core` (pure CSS light core; **no avatar image, no robot face, no logo**).
  - `.presence__kicker` / `.presence__name` ("小6") / `.presence__state` (`#aiCoreState`, `aria-live="polite"`) / `.presence__doing` (`#aiCoreDoing`).
- `.context` (`#contextLayer`, `hidden`) — three natural sentences.
- `.intent` (`#intentLine` form) → `#intentInput` + `#intentSend` (the only entry point).
- `.ambient` (`#ambientNav`) — 5 silent dots; labels appear only on hover.
- `.overlay` (`#overlaySpace`, `hidden`) → `.sheet` with `#overlayKicker` / `#overlayTitle` / `#overlayBody`.

Scripts loaded (reused singletons, in order):
`../sse-manager.js` → `../zz-events.js` → `../avatar-state.js` → `../intent-gateway.js`
then v4: `data-adapter → ai-core → context-layer → intent-line → world-understanding → overlay → boot`.

**Red-line proof:** The single explicit comment in the file (line 82) states we deliberately do
**not** load the legacy `app.js` / `main-orb.js`. No extra `<script>`, route, or page added.

---

## 2. `ui-v4.css` (507 lines)

**What changed:** Full visual-language rewrite — Apple + Claude + Linear register.

Key decisions:
- Palette: `--bg #08090c`; 4-step gray ramp `--text #edeff3` → `--text-faint #606774`.
- Single accent driven entirely by `--core-*` CSS variables (injected by `ai-core.js`):
  `--core-color / --core-soft / --core-glow / --core-line`.
- Light core: 3 layers sized with `--aura / --ring / --core` + negative margins (centered),
  so the `transform` property is free for the breathing animation (no transform/animation conflict).
- 8-state rhythm via `[data-state=…]` → different `animation-duration` and ring-sweep visibility.
  Ring sweep uses `conic-gradient` masked into a ring under `@supports (mask:)`.
- Grain: inline `feTurbulence` data-URI (zero network).
- `.space` uses flex column centering + `padding-bottom:132px` (no magic grid offsets).
- **Bug fixed:** a duplicated `--text-dim` line had a Cyrillic `а` inside `#949bа7`; removed the
  duplicate and normalized to `#949ba7`.

**Red-line proof:** No dashboard/stat styling; no images/logos; all color comes from one variable set.

---

## 3. `js/ai-core.js` (125 lines) — AI Core Identity

**Public API (attached to `window.V4Core`):**
```js
V4Core.applyState(raw)            // raw runtime state -> sets --core-* vars + data-state + voice
V4Core.setDoing(text, autoHideMs) // transient secondary line (optimistic feedback, auto-hide)
V4Core.getState()                 // current AvatarState key
V4Core.voice(st)                  // human phrase for a normalized state
V4Core.meta(st)                   // {label,color} — sourced ONLY from AvatarState.META
```

Key behaviors:
- `STATE_MAP` normalizes `agent_runtime` orchestration states
  (`idle/waiting/thinking/planning/executing/reflecting/completed/error/failed/disabled/offline`)
  → 8 AvatarState keys. `disabled`/`offline` → `OFFLINE`.
- `VOICE` — 8 first-person phrases, **no** "中/状态/系统" machine wording:
  `IDLE:'在这里，随时开始'`, `WAITING:'等你确认一下'`, `THINKING:'正在想这件事'`,
  `PLANNING:'正在把它拆开'`, `EXECUTING:'正在做'`, `COMPLETED:'刚做完一件事'`,
  `ERROR:'卡住了，想请你看一眼'`, `OFFLINE:'暂时离线'`.
- `applyState()` injects exactly 4 variables derived from `AvatarState.META[st].color`
  via `rgba(hex,a)` — **no color literal lives in this file**.
- `speak()` does a 150ms "breath" cross-fade; first frame (`current===null`) lands immediately
  (fixes the open-screen blank window).

**Red-line proof:** Zero color literals; 0 new events; only consumes existing `agent_state`.

---

## 4. `js/data-adapter.js` (77 lines) — P0 fix X-1

**Public API (`window.V4Data`):** `getJSON`, `asList`, `fetchSnapshot`, `fetchGraph`,
`onAgentState`, `ensureSSE`.

**Fix X-1 (memories were always empty):** `/api/memories` returns a **bare array**, not
`{memories:[]}`. Added `asList(v, key)`:
```js
function asList(v, key) {
  if (Array.isArray(v)) return v;
  if (v && Array.isArray(v[key])) return v[key];
  return [];
}
```
`fetchSnapshot()` now resolves goals/memories/knowledge uniformly. Result: memories = **34** live
items (was 0).

**Discipline:** read-only `GET`; intent writes go through `intent-gateway`, never here.

---

## 5. `js/context-layer.js` (193 lines) — Context Layer reframe (P0 X-2, X-3)

**Public API (`window.V4Context`):** `render`, `refresh`, `compose`,
plus pure functions for verification: `_pickGoal`, `_pickMemory`, `_cleanMemory`,
`_progressWord`, `_domainLabels`.

**Three sentences (no numbers, no slugs):**
1. **正在** — `pickGoal(goals)` → most-progressed, de-duplicated goal + `progressWord(p)`.
   - `pickGoal` de-dups by title (keeps higher progress), sorts progress↓ then updated↓.
   - `progressWord(p)` → `刚开了个头 / 才起步 / 推到一半了 / 快收尾了 / 基本落定了`.
   - **Fix X-3:** old code used `goals[0]` (a progress:0 duplicate); now picks the real top
     (title "总结当前项目状态", progress 83). Distinct count 7 → 1.
2. **我记得** — `pickMemory(memories)` by `salience`↓ + `memoryPhrase(m)` swaps phrasing by
   `event_type` ("我还记着你留意过…" / "定下过…" / "想做…" / "记着…").
   - **Fix:** `cleanMemory()` strips machine prefixes
     (`/^hotspot event:/i`, `/^memory:/i`, `/^用户提到热点:/`, `/^用户:/`).
3. **我理解** — `domainLabels(docs)` maps English slug → Chinese, **drops** pure-ASCII unmapped
   slugs.
   - **Fix X-2:** `concept` no longer leaks; domains render as 决策/概念/人和关系/项目.

Key entities wrapped in `<em>` for emphasis. `refresh()` is rate-limited (5s) so state jitter
doesn't hammer the backend.

**Red-line proof:** no digit/percent ever emitted (verified), no English slug in output
(verified), no dashboard markup.

---

## 6. `js/intent-line.js` (104 lines) — Intent Line

**Fixes I-1 / I-2:**
- Main send button `.is-ready` ghost: disabled/transparent until input has content.
- IME safety: `compositionstart`/`compositionend` set a `composing` flag; Enter is ignored mid-composition.
- `PLACEHOLDER` rotates 8 Zhuang-Zhou-voice hints by state.
- Crash fix: `String(input.value||'').trim()` guards `undefined`.

Only writes through `ZZIntentGateway.dispatch → POST /api/agent/intent` (existing contract).

---

## 7. `js/overlay.js` (193 lines) — Overlay (fixes O-1…O-3)

- Title gets a personal kicker (`我记住的` / `我在推进的` / `关于我`…).
- `.row` layout; hover lift only ~1.8% brightness; memory rows reuse `_cleanMemory`.
- Empty states rewritten in human voice.
- Focus management: open focuses close key, close restores prior focus, clicking the same
  trigger again collapses.

No new route/page — in-place focus within the same space.

---

## 8. `js/world-understanding.js` (90 lines)

- Double-ring layout: important nodes on the outer ring (labeled), secondary nodes inner
  (unlabeled). Labels align left/right/middle by angle to avoid overlap.
- Pure visualization of existing memory graph; no new data source.

---

## 9. `js/boot.js` (36 lines)

- Context appears 420ms after load (gentle entrance).
- Snapshot failure → fallback `OFFLINE` + empty Context (never flashes an error panel).

---

## 10. File size ledger

```
xiao6-ui/v4/index.html                97
xiao6-ui/v4/ui-v4.css               507
xiao6-ui/v4/js/ai-core.js           125
xiao6-ui/v4/js/boot.js               36
xiao6-ui/v4/js/context-layer.js    193
xiao6-ui/v4/js/data-adapter.js      77
xiao6-ui/v4/js/intent-line.js      104
xiao6-ui/v4/js/overlay.js          193
xiao6-ui/v4/js/world-understanding.js 90
total                                    1422
```

All changes are confined to `xiao6-ui/v4/` and its `js/`. No backend, runtime, or legacy-UI
file was touched.
