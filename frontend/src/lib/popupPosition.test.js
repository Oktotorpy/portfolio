// Framework-free unit tests for popupPosition.js.
// Run with: node --test src/lib/popupPosition.test.js
// Uses only node:test + node:assert — no test-runner package, no package.json change.

import { test } from 'node:test';
import assert from 'node:assert';
import { computePopupStyle } from './popupPosition.js';

// Shared "typical" desktop dimensions used across several cases.
const GAP = 12;
const POPUP_W = 360;

test('marker near page top + tall 600px popup, unscrolled (the 201 regression shape)', () => {
  const scrollY = 0;
  const topMargin = 8; // minimum allowed
  const result = computePopupStyle({
    markerViewTop: 40,
    markerHeight: 40,
    markerCenterX: 500,
    scrollX: 0,
    scrollY,
    viewW: 1200,
    viewH: 800,
    popupW: POPUP_W,
    popupH: 600,
    gap: GAP,
    topMargin,
    bottomMargin: 16,
  });

  assert.ok(topMargin >= 8);
  assert.ok(result.top >= scrollY + topMargin);
  assert.ok(!/translate\([^)]*-100%/.test(result.transform), 'must never use a negative Y translate');
  assert.strictEqual(result.transform, 'translateX(-50%)');
});

test('same shape, scrolled (scrollY 1500) — matches IAP hand-check top >= 1508', () => {
  const scrollY = 1500;
  const topMargin = 8;
  const result = computePopupStyle({
    markerViewTop: 40,
    markerHeight: 40,
    markerCenterX: 500,
    scrollX: 0,
    scrollY,
    viewW: 1200,
    viewH: 800,
    popupW: POPUP_W,
    popupH: 600,
    gap: GAP,
    topMargin,
    bottomMargin: 16,
  });

  assert.ok(topMargin >= 8);
  assert.ok(result.top >= scrollY + topMargin);
  assert.ok(result.top >= 1508, `expected top >= 1508, got ${result.top}`);
  assert.strictEqual(result.transform, 'translateX(-50%)');
});

test('marker mid-page + short 200px popup (fits above, no flip needed)', () => {
  const scrollY = 0;
  const topMargin = 20;
  const result = computePopupStyle({
    markerViewTop: 400,
    markerHeight: 40,
    markerCenterX: 500,
    scrollX: 0,
    scrollY,
    viewW: 1200,
    viewH: 800,
    popupW: POPUP_W,
    popupH: 200,
    gap: GAP,
    topMargin,
    bottomMargin: 16,
  });

  assert.ok(topMargin >= 8);
  assert.ok(result.top >= scrollY + topMargin);
  // Pins the above-preference: 400 - 12 - 200 = 188, no flip below.
  assert.strictEqual(result.top, 400 - GAP - 200);
});

test('marker mid-page + tall 600px popup in an 800px viewport (clamps to lower max bound)', () => {
  const scrollY = 0;
  const topMargin = 20;
  const bottomMargin = 16;
  const viewH = 800;
  const popupH = 600;
  const result = computePopupStyle({
    markerViewTop: 400,
    markerHeight: 40,
    markerCenterX: 500,
    scrollX: 0,
    scrollY,
    viewW: 1200,
    viewH,
    popupW: POPUP_W,
    popupH,
    gap: GAP,
    topMargin,
    bottomMargin,
  });

  assert.ok(topMargin >= 8);
  assert.ok(result.top >= scrollY + topMargin);
  // Should be clamped down to the max bound since the flipped-below position
  // (400 + 40 + 12 = 452) would overflow the viewport bottom.
  const expectedMaxTop = Math.max(scrollY + topMargin, scrollY + viewH - popupH - bottomMargin);
  assert.strictEqual(result.top, expectedMaxTop);
});

test('marker near viewport bottom, short 200px popup', () => {
  const scrollY = 0;
  const topMargin = 20;
  const result = computePopupStyle({
    markerViewTop: 750,
    markerHeight: 40,
    markerCenterX: 500,
    scrollX: 0,
    scrollY,
    viewW: 1200,
    viewH: 800,
    popupW: POPUP_W,
    popupH: 200,
    gap: GAP,
    topMargin,
    bottomMargin: 16,
  });

  assert.ok(topMargin >= 8);
  assert.ok(result.top >= scrollY + topMargin);
});

test('marker near viewport bottom, tall 600px popup', () => {
  const scrollY = 0;
  const topMargin = 20;
  const result = computePopupStyle({
    markerViewTop: 750,
    markerHeight: 40,
    markerCenterX: 500,
    scrollX: 0,
    scrollY,
    viewW: 1200,
    viewH: 800,
    popupW: POPUP_W,
    popupH: 600,
    gap: GAP,
    topMargin,
    bottomMargin: 16,
  });

  assert.ok(topMargin >= 8);
  assert.ok(result.top >= scrollY + topMargin);
});

test('degenerate case: popupH > viewH - topMargin - bottomMargin — top invariant wins', () => {
  const scrollY = 0;
  const topMargin = 20;
  const bottomMargin = 16;
  const viewH = 200;
  const popupH = 300; // 300 > 200 - 20 - 16 (=164): impossible to satisfy both bounds
  const result = computePopupStyle({
    markerViewTop: 100,
    markerHeight: 40,
    markerCenterX: 500,
    scrollX: 0,
    scrollY,
    viewW: 1200,
    viewH,
    popupW: POPUP_W,
    popupH,
    gap: GAP,
    topMargin,
    bottomMargin,
  });

  assert.ok(topMargin >= 8);
  assert.ok(result.top >= scrollY + topMargin);
  // The lower bound must win exactly: top pinned to scrollY + topMargin.
  assert.strictEqual(result.top, scrollY + topMargin);
});

test('horizontal clamp still yields left within [popupW/2+16, viewW+scrollX-popupW/2-16] (T6, unchanged)', () => {
  const viewW = 1000;
  const scrollX = 0;
  const popupW = POPUP_W;
  const lowerBound = popupW / 2 + 16;
  const upperBound = viewW + scrollX - popupW / 2 - 16;

  // Marker far off-screen to the left.
  const left = computePopupStyle({
    markerViewTop: 400,
    markerHeight: 40,
    markerCenterX: -500,
    scrollX,
    scrollY: 0,
    viewW,
    viewH: 800,
    popupW,
    popupH: 200,
    gap: GAP,
    topMargin: 20,
    bottomMargin: 16,
  }).left;
  assert.ok(left >= lowerBound && left <= upperBound);
  assert.strictEqual(left, lowerBound);

  // Marker far off-screen to the right.
  const right = computePopupStyle({
    markerViewTop: 400,
    markerHeight: 40,
    markerCenterX: 5000,
    scrollX,
    scrollY: 0,
    viewW,
    viewH: 800,
    popupW,
    popupH: 200,
    gap: GAP,
    topMargin: 20,
    bottomMargin: 16,
  }).left;
  assert.ok(right >= lowerBound && right <= upperBound);
  assert.strictEqual(right, upperBound);
});
