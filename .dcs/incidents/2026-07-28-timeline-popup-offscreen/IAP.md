# IAP — Incident Action Plan

**Incident:** timeline-popup-offscreen
**Type:** 3
**Operational period:** 1
**Links:** `202-OBJECTIVES.md` · `204-TASKING/S1.md` (203-ORG.md skipped — default Type 3 activation: IC + Planning Chief + 1 specialist matching the single 204 tasking + Safety Officer, plain parallel)

## Objectives (summary of 202)

**Goal:** On the desktop timeline, project and role popups always render fully inside the visible viewport — the popup's top edge never lands above the visible screen, regardless of marker position, scroll offset, or popup content height. Mobile's fixed-bottom behavior is unchanged.

Acceptance criteria (full text in 202-OBJECTIVES.md; "top edge" means the *effective rendered* top edge — declared `top` minus any negative Y translate; the tactics eliminate negative Y translate so declared == effective):

1. `positionPopup()` no longer relies on the fixed `viewTop < 320` threshold with unmeasured popup height; computed popup-card top edge in document space ≥ `scrollY` + margin (≥8px) for both placements; insufficient room above ⇒ flip/clamp.
2. Both openers (`openProjectPopup`, `openRolePopup`) reach the fixed logic via the shared `positionPopup` path.
3. Dead `viewH` removed or genuinely consumed (grep-verifiable).
4. Mobile popup path (`position: fixed; bottom: 68px`) unchanged by the diff.
5. Positioning math testable via `node --test` over a pure helper; invariant asserted for the six representative shapes (201 regression shape included).
6. `npm run build` succeeds in the worktree's frontend/.
7. [Owner] UAT after merge: 201 reproduction fully visible.

## Tactics (from the Planning Chief)

- T1 — Extract geometry into framework-free pure module `frontend/src/lib/popupPosition.js` (one exported function; document-space `top`; `translateX(-50%)` only; zero imports so plain Node imports it with no node_modules).
- T2 — Replace `viewTop < 320` with measured-height placement: prefer above; flip below when above violates the top invariant; hard-clamp `top` into [scrollY + topMargin, max(scrollY + topMargin, scrollY + viewH − popupH − bottomMargin)]; top invariant wins when the viewport is too short.
- T3 — Always explicit document-space `top`, never `translate(-50%, -100%)` — under-measured content then grows downward only (bounded by `.popup-card`'s `max-height: 80vh; overflow-y: auto`).
- T4 — Two-pass render: provisional `visibility: hidden` style (estimated height) → `await tick()` → measure real height via `bind:this` → final style from the same helper. `positionPopup` becomes async; openers unchanged.
- T5 — Two separate refs (`projectPopupEl`, `rolePopupEl`) across the two popup `{#if}` blocks; measure `projectPopupEl ?? rolePopupEl`; null-ref path still assigns a visible style.
- T6 — Existing horizontal clamp moves into the helper unchanged; `isMobile` early return stays in the component, textually first.
- T7 — `topMargin` derived from `.main-nav` measured height + 8 (fallback 12) — read in the component, passed as a number; helper stays pure.
- T8 — `viewH` deleted or genuinely consumed as a helper input.
- T9 — Svelte 4 syntax on Svelte 5 compiler; no new dependency; no config/package changes.

## File-territory partition

| Specialist | Territory | Forbidden |
|---|---|---|
| S1 | `frontend/src/routes/+page.svelte`, `frontend/src/lib/popupPosition.js`, `frontend/src/lib/popupPosition.test.js` | `frontend/src/lib/components/**`, `frontend/src/lib/api.js`, `frontend/src/lib/stores.js`, `frontend/src/lib/utils.js`, `frontend/src/lib/data.server.js`, `frontend/src/params/**`, `frontend/src/routes/**/+page.server.js`, `frontend/src/routes/[slug=notadmin]/**`, `frontend/src/routes/admin/**`, `frontend/src/routes/+layout.svelte`, `frontend/src/app.css`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/svelte.config.js`, `frontend/vite.config.js`, `backend/**`, `deploy/**`, `CLAUDE.md`, `.dcs/**` |

**Partition status:** disjoint — single tasking, parallel execution trivially satisfied. (Chief considered a helper/component two-way split and rejected it: shared interface contract + build dependency would make it false-parallel for a ~60-line change.)

## Risks

- ENVIRONMENT — worktree frontend/ has no node_modules (verified at lint, 2026-07-28); criterion 6 needs `npm ci` reaching the npm registry from the specialist harness. If blocked: deviation, not a workaround. `node --test` evidence is unaffected (zero-dependency by design). Local toolchain verified at lint: node v24.13.1, npm 11.8.0.
- MEASUREMENT — first-tick popup height under-estimates (images have no intrinsic height until load). T3 (explicit top, no bottom-anchoring) makes the top invariant survive post-measurement growth by construction. Residual, accepted this period: very tall media popups may extend past the viewport bottom — bounded by existing `max-height: 80vh` + internal scroll; popup redesign is out of scope.
- NO BROWSER — `node --test` proves the math, not the wiring; wiring is evidenced by grep/diff inspection, finally closed by Owner UAT (202#7). Safety Officer must not read green tests as covering the wiring.
- COUPLING — T7 reads `.main-nav` across a component boundary (scoped-class hash appends, selector matches today); mitigated by `?.` + numeric fallback. Degrade path: `TOP_MARGIN = 12` constant still satisfies 202#1.
- FLASH — two-pass render must keep the provisional pass hidden and always assign a final visible style (including the null-ref path).
- DIALECT — Svelte 4 syntax on Svelte 5 compiler; `npm run build` is the backstop.
- The 320px threshold could be load-bearing in some unseen way (zero tests exist); horizontal regression would be invisible to the unit test — hence the explicit "horizontal clamp unchanged" test case and T6's verbatim-move instruction.

## Verification plan

1. STRUCTURAL — `git diff --stat` touches exactly three files: `frontend/src/routes/+page.svelte`, `frontend/src/lib/popupPosition.js` (new), `frontend/src/lib/popupPosition.test.js` (new). Any fourth file is a partition breach and a fail.
2. UNIT INVARIANT (202#1, #5) — `node --test src/lib/popupPosition.test.js` from frontend/ exits 0, zero failures, six shapes visibly covered. Safety Officer reads the test file, not just output: the assertion must be literally `top >= scrollY + topMargin` with `topMargin >= 8` — anything weaker is a fail even if green. Hand spot-check: 201 shape (markerViewTop ~40, popupH 600, viewH 800, scrollY 1500) must return top ≥ 1508 and transform with no negative Y translate.
3. SHARED PATH (202#2) — grep confirms both openers still call `positionPopup`, one desktop placement path feeding the helper. Project-popup-only fix is a fail.
4. DEAD CODE (202#3) — `grep -n "viewH" frontend/src/routes/+page.svelte` empty or consuming-lines-only.
5. MOBILE UNTOUCHED (202#4) — `git diff -U0` shows no ± line touching `position: fixed; bottom: 68px`; the line still exists. Reindentation counts as touching.
6. BUILD (202#6) — `npm ci && npm run build` in frontend/ exits 0 with adapter-node output. npm unreachable ⇒ criterion OPEN, period cannot close green.
7. INTEGRATED REPRO (202#7, Owner, at close) — desktop >768px: topmost-row rich-media dot near screen top → popup fully visible, top edge below sticky nav, thumbnails uncut. Also: (a) role marker near page top, (b) mid-page dot still prefers above-placement (catches an over-broad "always below" fix — do not skip), (c) dot near viewport bottom, (d) ≤768px popup still pins to fixed bottom.
8. RESIDUAL, recorded not blocking — bottom-edge overflow for very tall media popups; no browser-level automated coverage (candidate future objective).

## Deviation history (this period)

none
