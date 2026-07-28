# 201 — Incident Brief

**Incident:** timeline-popup-offscreen
**Opened:** 2026-07-28
**Type:** 3

## Symptom

Owner report (chat, with screenshot): on the public timeline homepage (desktop), hovering/clicking a marker near the top of the timeline opens the project popup rendered partly outside the visible screen — its top edge is clipped past the viewport top and the card overlaps the sticky top nav bar. Screenshot shows project "Votvot Heads&Tails" (2024 row) with its media thumbnails cut off at the screen's top edge.

## Evidence

- `frontend/src/routes/+page.svelte:311-339` — `positionPopup(event)` desktop branch: `if (viewTop < 320)` places popup below the marker; else places it above with `top: pageY - 12` + `transform: translate(-50%, -100%)`. The popup's real rendered height is never measured and the resulting top edge is never clamped against `scrollY`/viewport top. — source: analyst A code read, confirmed by analyst B.
- `frontend/src/routes/+page.svelte:328` — horizontal position IS clamped (`Math.max/Math.min` against viewport width); no vertical equivalent exists. The defect is asymmetric by omission. — source: analyst B code read.
- `frontend/src/routes/+page.svelte:314` — `const viewH = window.innerHeight` is declared and never used (single grep match in file): dead remnant of the pre-refactor `position: fixed` scheme that consumed it for a bottom clamp. — source: analyst A grep.
- `frontend/src/routes/+page.svelte:296-309` — both `openProjectPopup` and `openRolePopup` call the same `positionPopup`; role-marker popups share the defect. Job markers have no popup (only hover dimming + static label) and are unaffected. — source: analyst A code read.
- `frontend/src/routes/+page.svelte:872-877` — `.popup-card { max-height: 80vh; overflow-y: auto; z-index: 91 }`: popup height is content-dependent (image mosaic, video, shorts pairs per CLAUDE.md "Project Popup") and can far exceed the static 320px threshold. — source: analyst B code read.
- `frontend/src/lib/components/PublicShell.svelte:162-172` — `.main-nav { position: sticky; top: 0; z-index: 10 }`; popup z-index 91 > nav z-index 10, so an above-viewport popup renders on top of the nav. Not a stacking bug — purely positioning. — source: analyst B code read.
- Mobile path immune: `+page.svelte:319` uses `position: fixed; bottom: 68px` (isMobile = width ≤ 768). — source: analyst B code read.
- No automated tests exercise popup positioning (glob for test/spec files under frontend/src: zero project files). — source: analyst A glob.
- Analysts diverge on origin only: analyst A dates the regression to commit `61afb98` (fixed→absolute refactor dropped the implicit `bottom: viewH - top` clamp); analyst B shows `if (top < 320)` already present in the popup's first implementation `d0154be` ("feat: reworked Timeline", 2026-02-12). Immaterial to the fix — the unclamped code path at HEAD (`c094a78` at intake) is agreed. — source: git show/log by both analysts.

## Reproduction path

1. Load `/` at desktop viewport (>768px).
2. Position scroll so a project dot's `rect.top` ≥ 320 while the dot sits in the upper region of the page (topmost/2024 row qualifies with nav pinned).
3. Click/hover a dot whose project carries rich media (e.g. "Votvot Heads&Tails" — mosaic + video inflate popup height well past ~400px).
4. `positionPopup` takes the "place above" branch: popup bottom anchors just above the dot, card grows upward unmeasured → top edge lands above y=0, clipped by viewport, overlapping the sticky nav.

(Static code-path trace by both analysts; not executed in a live browser during the stem — no dev server was started.)

## Blast radius (best guess at intake)

- `frontend/src/routes/+page.svelte` — `positionPopup()` + related popup markup/CSS. Sole edit target: grep confirms popup logic exists nowhere else, popup is not a shared component.
- `frontend/src/lib/components/PublicShell.svelte` — read-only context (sticky nav geometry); not expected to need edits.

## Prior art

None found. `git log --all --oneline | grep -i popup` → zero commits; popup positioning never the explicit subject of a fix across 16 timeline-touching commits. Project memory (MEMORY.md entries: deploy-build-node-version, election-pipeline-status, xray-reality-vpn, cinevote, qr-sat) — none relevant. Note for planning: deploy-build-node-version.md matters at deploy time (build needs nvm Node 24, not system v18).

## Type + rationale

**Proposed type:** 3
**Rationale:** Well-scoped bug: one edit-target file, clear root cause (unmeasured popup height + missing vertical clamp), fix pattern known; but untested UI math affecting two popup kinds (project + role) warrants a plan and independent Safety verification — not Type 5 express lane, and nothing architectural for Type 1.
**Owner confirmation:** confirmed as proposed (AskUserQuestion, 2026-07-28).

## Intake source (for /dcs-close to route back to)

Owner chat report with screenshot, 2026-07-28 (`/dcs-run` invocation + follow-up message "When hovering over a job on this portfolio website, pop up window is rendered outside of visible screen").
