/**
 * Pure, framework-free desktop popup positioning helper.
 *
 * Imports NOTHING — no `$lib`, `$app`, `svelte`, or DOM globals — so this
 * module can be loaded by plain Node with no node_modules present (used by
 * popupPosition.test.js via `node:test`).
 *
 * All inputs are plain numbers/booleans; all outputs are document-space
 * (i.e. relative to the top of the full scrollable page, not the viewport).
 *
 * Placement rule:
 *  1. Prefer placing the popup above the marker.
 *  2. If "above" would violate the top invariant (top < scrollY + topMargin),
 *     flip to below the marker.
 *  3. Hard-clamp the result into
 *     [scrollY + topMargin, max(scrollY + topMargin, scrollY + viewH - popupH - bottomMargin)].
 *     When the viewport is too short to satisfy both bounds, the top
 *     invariant (lower bound) wins.
 *
 * `top` is always an explicit document-space value — never a negative Y
 * translate — so any post-measurement content growth (e.g. late-loading
 * images) expands the popup downward only, bounded by the component's own
 * `max-height: 80vh; overflow-y: auto`.
 */
export function computePopupStyle({
  markerViewTop,
  markerHeight,
  markerCenterX,
  scrollX,
  scrollY,
  viewW,
  viewH,
  popupW,
  popupH,
  gap,
  topMargin,
  bottomMargin,
}) {
  const markerDocTop = markerViewTop + scrollY;

  const minTop = scrollY + topMargin;
  const maxTop = Math.max(minTop, scrollY + viewH - popupH - bottomMargin);

  // 1. Prefer above the marker.
  let top = markerDocTop - gap - popupH;

  // 2. Flip below when "above" would violate the top invariant.
  if (top < minTop) {
    top = markerDocTop + markerHeight + gap;
  }

  // 3. Hard-clamp; Math.max applied last means the top invariant always wins
  //    when the viewport is too short for both bounds (minTop === maxTop
  //    in the degenerate case, or minTop > the naive clamp result).
  top = Math.max(minTop, Math.min(maxTop, top));

  // Horizontal clamp (unchanged behaviour, moved here verbatim).
  const pageX = markerCenterX + scrollX;
  const left = Math.max(popupW / 2 + 16, Math.min(viewW + scrollX - popupW / 2 - 16, pageX));

  const position = 'absolute';
  const transform = 'translateX(-50%)';
  const maxWidth = `${popupW}px`;
  const style = `position: ${position}; top: ${top}px; left: ${left}px; transform: ${transform}; max-width: ${maxWidth};`;

  return { position, top, left, transform, maxWidth, style };
}
