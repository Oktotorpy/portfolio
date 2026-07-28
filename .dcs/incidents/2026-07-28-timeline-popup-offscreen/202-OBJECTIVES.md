# 202 — Objectives (Operational Period 1)

**Incident:** timeline-popup-offscreen
**Period:** 1

## Goal

On the desktop timeline, project and role popups always render fully inside the visible viewport — the popup's top edge never lands above the visible screen, regardless of marker position, scroll offset, or popup content height. Mobile's fixed-bottom behavior is unchanged.

## Acceptance criteria (the Definition of Done)

1. `positionPopup()` placement no longer relies on the fixed `viewTop < 320` threshold with unmeasured popup height: the computed popup-card top edge in document space is ≥ `window.scrollY` + margin (margin ≥ 8px) for both "above" and "below" placements; when there is insufficient room above the marker, placement flips or clamps so the invariant holds.
2. Both popup openers (`openProjectPopup`, `openRolePopup`) reach the fixed logic — the shared `positionPopup` path is preserved (verify: both call sites still route through the corrected positioning code).
3. The dead `viewH` variable (`frontend/src/routes/+page.svelte:314` at intake) is removed or genuinely used by the new logic — verify: `grep -n "viewH" frontend/src/routes/+page.svelte` returns either nothing or only lines where it is actually consumed.
4. The mobile popup path (`position: fixed; bottom: 68px`, isMobile branch) is unchanged by the diff.
5. The positioning math is extracted/testable enough that an automated check runnable in the specialist's own harness (e.g. `node --test` over a pure positioning helper) asserts criterion 1's invariant for representative cases: marker near page top with tall popup (the 201 regression shape), marker mid-page, marker near viewport bottom, short (~200px) and tall (~600px) popup heights, scrolled and unscrolled.
6. `npm run build` completes successfully in the incident worktree's `frontend/`.
7. [Owner] UAT after merge: the 201 reproduction (topmost-row rich-media project dot, e.g. "Votvot Heads&Tails") shows the popup fully visible — checked at close per the IAP verification plan.

## Out of scope this period

- Popup content/styling redesign (card layout, media presentation).
- Mobile popup layout changes.
- Nav z-index / stacking changes in PublicShell.svelte.
- ProjectCard work-type pages (separate media presentation code).

## Chief feedback (filled in after /dcs-plan spawns the Planning Chief)

- (a) Criterion 1's "top edge" resolved to mean the *effective rendered* top edge (declared `top` minus any negative Y translate); tactics eliminate negative Y translate so declared == effective — criterion text unchanged, meaning pinned. IC accepted.
- (b) Environment precondition surfaced: worktree frontend/ has no node_modules; criterion 6 requires `npm ci` (registry access) first. Verified at lint 2026-07-28: node_modules absent, node v24.13.1 / npm 11.8.0 present. Offline harness ⇒ specialist deviation, not a skip.
- (c) Criterion 5 proves the math, not the wiring — wiring evidenced by grep/diff, closed by criterion 7 (Owner UAT). Accepted as designed.
- (d) Under-measured first-tick popup height (unloaded images) covered by tactic T3 (explicit top, growth expands downward) — no 202 change needed.
