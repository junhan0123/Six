# UI-v4 Phase 8 — Verify

All checks below were executed against the **live** v4 instance at `http://127.0.0.1:8121/v4/`
on the Phase 8 deliverables. Environment: Node v22.22.2. Date: 2026-08-10.

Discipline reminder: Verify is read-only. No backend, runtime, or legacy-UI file was modified.

---

## 1. Syntax — `node --check` (7/7 OK)

| File | Result |
|---|---|
| `js/ai-core.js` | OK |
| `js/boot.js` | OK |
| `js/context-layer.js` | OK |
| `js/data-adapter.js` | OK |
| `js/intent-line.js` | OK |
| `js/overlay.js` | OK |
| `js/world-understanding.js` | OK |

## 2. CSS balance

`ui-v4.css`: `{` = 129, `}` = 129 → **BALANCED**.

## 3. Color authority — 8 states from `avatar-state.META` (8/8 matched)

Harness loaded the real `avatar-state.js` and `ai-core.js`, then compared
`V4Core.meta(st).color` against `AvatarState.META[st].color` for all 8 states:

| State | avatar-state.META | used by v4 | Match |
|---|---|---|---|
| IDLE | `#5fb3c8` | `#5fb3c8` | ✅ |
| WAITING | `#f0b35e` | `#f0b35e` | ✅ |
| THINKING | `#8b9bff` | `#8b9bff` | ✅ |
| PLANNING | `#c08bff` | `#c08bff` | ✅ |
| EXECUTING | `#56d364` | `#56d364` | ✅ |
| COMPLETED | `#56d3a0` | `#56d3a0` | ✅ |
| ERROR | `#ff6b6b` | `#ff6b6b` | ✅ |
| OFFLINE | `#8a93a6` | `#8a93a6` | ✅ |

No color literal exists in `ai-core.js`; all four `--core-*` variables are derived via `rgba()`.

## 4. Semantic harness (live API) — 12/12 PASS

Drives the real `data-adapter.js` + `context-layer.js` + `ai-core.js` with live endpoint data.

```
PASS  memories is non-empty array (X-1 fixed)            count=34
PASS  goals is array                                     count=7
PASS  knowledge.docs is array                            count=45
PASS  pickGoal returns a single top goal (X-3 fixed)     title=总结当前项目状态 progress=83
PASS  distinct goal count reasonable                     distinct=1 raw=7
PASS  8-state colors 100% from avatar-state.META         8/8 matched
PASS  AI Core voice: 8 human phrases, no machine wording 8/8 human
PASS  Context sentences contain NO arabic digits / percent
PASS  Context sentences contain NO latin letters (no slug leak)
PASS  memory de-noise strips machine prefixes            sample=河南三支一扶笔试存在组织作弊犯罪
PASS  knowledge domains mapped to Chinese (no ASCII slug leak)  [决策,概念,人和关系,项目]
PASS  progressWord emits no digits across range          0:刚开了个头 5:才起步 34:才起步 50:推到一半了 66:推到一半了 99:快收尾了 100:基本落定了
```

**Sample composed Context (live data):**
```
我正在推进<em>总结当前项目状态</em>，快收尾了。
我还记着你留意过<em>河南三支一扶笔试存在组织作弊犯罪</em>。
关于你的<em>决策</em>和<em>概念</em>，我大致有数了。
```
→ no digit, no `%`, no English slug.

## 5. HTTP 200 — all v4 resources serve

| Resource | Status |
|---|---|
| `/v4/` | 200 |
| `/v4/ui-v4.css` | 200 |
| `/v4/js/ai-core.js` | 200 |
| `/v4/js/context-layer.js` | 200 |
| `/v4/js/data-adapter.js` | 200 |
| `/v4/js/intent-line.js` | 200 |
| `/v4/js/overlay.js` | 200 |
| `/v4/js/boot.js` | 200 |
| `/v4/js/world-understanding.js` | 200 |

Root `/` serves the v4 space (redirect to `/v4/`, reversible) — 200.

## 6. Class / id consistency

Every `getElementById('X')` in `v4/js/*` has a matching `id="X"` in `index.html`.

JS queries: `aiCore, aiCoreState, aiCoreDoing, contextLayer, intentLine, intentInput,
intentSend, overlaySpace, overlayTitle, overlayKicker, overlayBody`
HTML ids: `presenceSpace, aiCore, aiCoreState, aiCoreDoing, contextLayer, intentLine,
intentInput, intentSend, ambientNav, overlaySpace, overlayKicker, overlayTitle, overlayBody`
→ **PASS** (every JS id present; `presenceSpace`/`ambientNav` are CSS/event-driven, not queried).

## 7. Old-UI isolation (red line: 不恢复旧 UI)

- `index.html` contains **no** `<script>` for `app.js` / `main-orb.js` / `galaxy` / `three`.
  The only match for those tokens is an explicit comment (line 82) stating we do **not** load them.
- `v4/js/*` contains **no** reference to `galaxy` / `main-orb` / `THREE` / `/app.js`.
- v4 reuses only capability singletons: `sse-manager.js`, `zz-events.js`, `avatar-state.js`,
  `intent-gateway.js`.

→ **PASS**: legacy runtime is fully isolated; v4 is additive presentation only.

## 8. Red-line self-audit (final)

| Red line | Result |
|---|---|
| 不恢复旧 UI | ✅ (§7) |
| 不修改 Backend | ✅ (only GET; §IMPLEMENTATION §4) |
| 不修改 Agent Runtime | ✅ (only subscribes `agent_state`) |
| 不新增 Event | ✅ (reuses existing SSE event name) |
| 不新增页面 | ✅ (single space; overlay is in-place) |
| 不引入 Dashboard | ✅ (3 sentences, zero stat cards) |
| 不增加功能 | ✅ (re-expresses existing data) |

---

## Conclusion

All 12 semantic checks, 7 syntax checks, CSS balance, HTTP 200s, id consistency, and old-UI
isolation pass. The three P0 data distortions (X-1 memories empty, X-2 English slug leak,
X-3 wrong goal) are fixed and verified. v4 now reads as **小6 himself** — a single calm space
with one light core, three natural sentences, and one entry line.

**Status: VERIFIED. STOP — awaiting Review.**
