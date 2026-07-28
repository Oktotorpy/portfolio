# AAR — After Action Report

**Incident:** timeline-popup-offscreen
**Type:** 3
**Opened:** 2026-07-28
**Closed:** 2026-07-28
**Operational periods:** 1

## Outcome

All specialist-owned acceptance criteria of the period-1 202 met and independently verified by the Safety Officer (pass, 0 refutations): the `viewTop < 320` fixed heuristic and `translate(-50%, -100%)` bottom-anchoring are gone from `frontend/src/routes/+page.svelte` (verified as `-` lines in the diff); placement now runs through the pure helper `frontend/src/lib/popupPosition.js` (prefer-above → flip-below → hard clamp to `scrollY + topMargin`), called two-pass with the popup's measured height; both openers share the path; `viewH` survives only as a consumed helper argument; the mobile fixed-bottom branch is byte-identical; `node --test src/lib/popupPosition.test.js` (regenerating command) passed 8/8 for the specialist, the Safety Officer, and again after IC advisory edits; `npm run build` exit 0 (run independently by specialist, Safety Officer ×3, and IC post-advisory).

Criterion 7 (Owner UAT of the 201 repro): **pending by explicit Owner consent** (AskUserQuestion, 2026-07-28) — deferred to post-deploy verification on the live site, since the fix is merged-not-deployed at close time.

Integration commit: `85002d0` (regenerate: `git show 85002d0 --stat`) — 3 territory files + `.gitignore` (Safety-advisory fix folded in per SAFETY.md resolutions).

## What worked

- Extracting the geometry into a zero-import pure module made the invariant testable in a repo with no test runner — `node --test` against the file directly, no package.json change.
- Explicit document-space `top` (never bottom-anchored negative translate) made the top invariant survive under-measured popup heights by construction — the Safety Officer's adversarial probes (popupH 0/200/900, viewTop 5–795) all held.
- The two-pass hidden-measure-final render preserved both openers' call sites untouched.
- Single-specialist partition for a single-interface change: no false parallelism, trivially disjoint territory.

## Lessons

- A placement heuristic keyed on a fixed pixel threshold with unmeasured content height is a latent off-screen bug; clamp against the viewport in the same code path that positions.
- When a refactor changes positioning scheme (fixed → absolute), any implicit clamp of the old scheme must be re-derived for the new one — here the old `bottom: viewH - top` clamp was silently dropped and `viewH` survived as a dead variable that flagged the loss.
- In a no-test-runner frontend, a pure-function extraction + plain `node --test` is a cheap, durable verification harness — prefer it over introducing a framework for one invariant.

## Deviations this incident

None — executed as planned. From `214-LOG.md`: zero `SAFETY-HALT:` entries, zero deviation returns, one tasking-lint defect fixed pre-review (S1 forbidden glob overlapped its own territory — Dispatcher-side transcription fix), one `IAP-APPROVED` stamp (attempt 1/3).

## Memory routing

No project memory system documented in CLAUDE.md — skipped.

## Intake source closure

None — ad hoc intake (Owner chat report with screenshot, 2026-07-28). Nothing external to flag.

## Deploy status

Not deployed — register row `MERGED (deploy pending)`; ships via `/dcs-deploy` when the Owner batches a train. (Server build note from user memory: deploy.sh build requires nvm Node 24, not system v18.)

## Safety Officer's final verdict (verbatim, from SAFETY.md)

`{"verdict": "pass", "refutations": [], "advisories": [4 — see SAFETY.md for the verbatim advisory objects and IC resolutions], "checked": [21 independent checks — SAFETY.md holds the verbatim list]}`

The full verbatim return (including all four advisories and the complete `checked` array) is preserved unabridged in `SAFETY.md` in this directory; the verdict line above quotes its head rather than duplicating the 21-item body — SAFETY.md is the authoritative copy.
