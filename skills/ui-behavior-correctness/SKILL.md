---
name: ui-behavior-correctness
description: Behavioral correctness for overlays and interactive UI — stacking contexts, top-layer dropdowns/menus/tooltips, viewport-aware collision/placement, dismissal and focus rules, plus Playwright audit recipes that prove it. Use when building or reviewing a dropdown, menu, tooltip, popover, select, combobox, or any overlay/z-index/collision work.
---
<!-- last-verified: 2026-07 -->

# UI behavior correctness

Looks-right is not behaves-right: a dropdown can be pixel-perfect in a
screenshot and still render behind a card, clip at the viewport edge, or trap
focus wrong. This skill is the behavior layer for overlays — stacking, the
top-layer default, collision/placement, and dismissal/focus — plus the
Playwright recipes that prove each one, because a screenshot alone never
proves an overlay is actually on top and actually reachable.

## 1. Stacking truth

- **UB-01 Stacking-context creators.** A new stacking context is created by:
  the root element; `position: absolute`/`relative` with `z-index` other than `auto`; `position: fixed` or `sticky` (unconditionally — no z-index needed); a flex/grid
  item with `z-index` set; `opacity < 1`; `transform`/`scale`/`rotate`/
  `translate`/`filter`/`backdrop-filter`/`clip-path`/`mask`/`perspective`
  other than `none`; `mix-blend-mode` other than `normal`; `isolation:
  isolate`; `contain: layout|paint|strict|content`; `container-type:
  size|inline-size`; `will-change` naming any of the above; and top-layer
  membership. Any one of these on a wrapper (a hover card, an animated nav,
  a `container-type` grid cell) silently traps everything positioned inside.
- **UB-02 No z-index escalation.** A stacking context is self-contained:
  child `z-index` only competes against siblings *inside the same context*.
  A dropdown with `z-index: 9999` nested in an ancestor that loses to a
  sibling at the parent level still renders behind that sibling — the 9999
  never leaves its parent's context. This is the actual cause of "dropdown
  behind the card," and raising the number further can't fix it. Rule:
  overlays escape via top layer or portal, never via z-index escalation.

## 2. Top-layer first

- **UB-03 Top-layer first.** The top layer sits above the whole document,
  outside every stacking context — the default for dropdowns, menus,
  tooltips, and selects, not a `z-index` value or a hand-rolled
  `createPortal` (which still inherits `<body>`'s own stacking context).
  - `popover="auto"` (light-dismissible) / `popover="manual"` — non-modal,
    top layer, free Esc + outside-click dismiss. **Baseline: Newly available
    since 2025-01-27** (Chrome, Firefox, Safari 18.3+); not yet Widely
    available (~mid-2027) — verify your target matrix, but default to it.
    [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API).
  - `<dialog>` + `showModal()` for modals — **Baseline Widely available
    since March 2022**: top layer, `::backdrop`, focus trap, inert
    background, Esc closes. `closedby` fine-tunes light-dismiss but has
    less mature support — feature-detect it. [MDN
    `<dialog>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog).
  - **Fallback rule**: only hand-roll a portal + manual highest-z context
    (accepting UB-01/UB-02's trap risk) below the Baseline floor above —
    and prefer a primitive that already made that call (§5) over
    hand-rolling it yourself.

## 3. Collision + placement

- **UB-04 Anchor positioning.** `anchor-name` on the trigger +
  `position-anchor`/`position-area`/`anchor()` ties placement to the trigger
  without JS measurement. **As of 2026-07**: Chrome/Edge 125+, Safari 26+,
  Firefox 145+ (no longer flag-gated), ~82% global usage — but Baseline only
  since Oct 2025–Apr 2026, so **not yet Widely available**; Chrome/Safari
  still diverge on containing-block overflow (block-axis-only vs both axes).
  Feature-detect with `CSS.supports("anchor-name: --a")`. [MDN anchor
  positioning](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_anchor_positioning),
  [caniuse](https://caniuse.com/css-anchor-positioning),
  [OddBird update](https://www.oddbird.net/2025/10/13/anchor-position-area-update/).
- **UB-05 JS fallback: floating-ui.** Where native anchor positioning isn't
  supported, or placement logic needs more control, use
  [floating-ui](https://floating-ui.com) middleware instead of hand-rolled
  `getBoundingClientRect` math: `offset()` (anchor gap), `flip()` (swap side
  on collision), `shift()` (nudge back inside viewport), `size()` (cap
  overlay dimensions to available space), `arrow()` (pointer element),
  `autoPlacement()` (no fixed preferred side), `hide()` (anchor scrolled out
  of view). `autoUpdate()` keeps position synced on scroll/resize.
- **UB-06 Collision + spacing.** Native `position-try-fallbacks` and
  floating-ui's `flip`+`shift`+`size` are equivalents — pick one per
  project. Always pair with: a fixed offset gap from the anchor, a minimum
  viewport padding so a flipped/shifted overlay never touches the edge, and
  respect for clipping ancestors (top-layer placement escapes this
  automatically; a hand-rolled portal must avoid rendering inside one).
- **UB-07 Scroll behavior.** Decide per overlay type: menus/dropdowns
  typically **close** when the trigger scrolls out of its container
  (`position-visibility: anchors-visible`, or floating-ui `hide()` + a
  close handler); tooltips **reposition-and-follow** while the trigger is
  visible; a persistent panel may do neither. Pick it before building.

## 4. Dismissal + focus

- **UB-08 Dismissal per type.** Menus/popovers: Esc and outside-click both
  close (`popover="auto"` gives both free; hand-rolled needs explicit
  listeners for each). Dialogs: Esc closes unless suppressed; light-dismiss
  is governed by `closedby`. Tooltips: dismiss on focus-out/`mouseleave`
  with a short delay, never on outside-click alone.
- **UB-09 Focus management.** Focus trap is for **modals only** —
  `showModal()` gives this natively; menus/tooltips must never trap focus
  (roving tabindex instead, per the widget's ARIA APG pattern). Return focus
  to the invoking trigger on close, always. Scroll-lock the body for modals
  only. Deeper per-widget roles/keyboard tables are
  `accessibility-wcag-aria`'s territory — this skill states only the
  overlay-class dismiss/focus/trap rules above.

## 5. When to not hand-roll

- **UB-10 Use the primitive when one exists.** If the project runs
  shadcn/Radix, its `DropdownMenu`/`Popover`/`Select`/`Tooltip`/`Dialog`
  primitives already solve UB-01–UB-09 — portal placement, collision
  middleware, focus scoping, dismissal — to the ARIA APG pattern. Reach for
  it; don't re-derive this skill's logic when `component-system-shadcn-radix`
  already ships it. Hand-rolling per §2–§4 is only for when no matching
  primitive exists in the project's stack.

## 6. Playwright behavioral audit recipes

Runnable via Bash (`npx playwright test` or a standalone script). Server
lifecycle, headless driving, and screenshot capture follow
`webapp-visual-testing`'s tool ladder; this section owns only the
behavioral assertions layered on top of it.

**(a) open-overlay-assert-top-layer-and-unclipped** — proves the overlay is
actually on top, not just visually plausible in a screenshot.
```js
await page.getByRole('button', { name: 'Open menu' }).click();
const overlay = page.getByRole('menu');
const box = await overlay.boundingBox();
const vp = page.viewportSize();
expect(box.x).toBeGreaterThanOrEqual(0);
expect(box.y).toBeGreaterThanOrEqual(0);
expect(box.x + box.width).toBeLessThanOrEqual(vp.width);
expect(box.y + box.height).toBeLessThanOrEqual(vp.height);
const [cx, cy] = [box.x + box.width / 2, box.y + box.height / 2];
const onTop = await page.evaluate(([x, y]) =>
  document.elementFromPoint(x, y)?.closest('[role="menu"]') !== null, [cx, cy]);
expect(onTop).toBe(true);
```
Failure smell: `boundingBox` fits the viewport but `elementFromPoint` hits a
different element — occluded (UB-01/UB-02) despite "looking" on top.

**(b) viewport-edge-flip** — proves collision handling flips/shifts.
```js
await page.evaluate(() => {
  const t = document.querySelector('#trigger');
  t.style.position = 'fixed'; t.style.right = '0px';
});
await page.getByTestId('trigger').click();
const box = await page.getByRole('menu').boundingBox();
expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width);
```
Failure smell: the overlay clips or extends past the edge — flip/shift or
`position-try-fallbacks` isn't wired up.

**(c) scroll-reposition** — proves the declared scroll behavior (UB-07).
```js
await page.getByTestId('trigger').click();
await page.mouse.wheel(0, 400);
await expect(page.getByRole('menu')).toBeHidden(); // close-on-scroll case
```
Failure smell: the overlay stays open at a stale position while the trigger
has scrolled away underneath it.

**(d) esc-and-outside-click-dismissal**
```js
await page.getByTestId('trigger').click();
await page.keyboard.press('Escape');
await expect(page.getByRole('menu')).toBeHidden();
await page.getByTestId('trigger').click();
await page.mouse.click(10, 10);
await expect(page.getByRole('menu')).toBeHidden();
```
Failure smell: either path leaves the overlay open — a missing Esc/outside-
click handler, or a hand-rolled overlay that skipped `popover="auto"`.

**(e) tab-order-and-return-focus**
```js
await page.getByTestId('trigger').focus();
await page.keyboard.press('Enter');
await page.keyboard.press('Tab');
await expect(page.getByRole('menuitem').first()).toBeFocused();
await page.keyboard.press('Escape');
await expect(page.getByTestId('trigger')).toBeFocused();
```
Failure smell: focus lands in the page body after close instead of back on
the trigger, or Tab escapes the menu into background content — the
return-focus/trap half of UB-09.

## Boundary

`visual-polish-and-craft`'s VP-06 (named z-index layers, never arbitrary
`9999`) is a naming discipline for cases where manual `z-index` is still the
right tool; this skill governs the more common failure — when the fix is
escaping to the top layer or a collision-aware primitive instead of any
`z-index` value. The two never conflict: this skill deepens VP-06, it
doesn't override it. `webapp-visual-testing` owns the capture mechanics
(server lifecycle, headless driving, screenshot naming) the §6 recipes run
on — cite it, don't restate it. `accessibility-wcag-aria` owns the
per-widget ARIA APG roles/keyboard tables; this skill states overlay-class
dismiss/focus/trap rules (§4) one level above that.
`component-system-shadcn-radix` owns the primitives (§5) — reach for its
Radix/shadcn components before hand-rolling anything here. In short: this skill owns interaction BEHAVIOR
— stacking, top-layer, collision, dismissal, focus — not visual polish, not
capture tooling, not per-widget ARIA depth, not component sourcing.

---
Adapted from, never verbatim:
- MDN Popover API, `<dialog>`, CSS anchor positioning, stacking-context docs
  (CC-BY-SA 2.5) — support-status facts and stacking-context mechanics.
- web.dev Baseline blog posts — Baseline timeline facts.
- caniuse.com (css-anchor-positioning) — support percentages/versions.
- floating-ui.com (MIT) — middleware vocabulary and behavior.
- OddBird anchor-positioning update (Oct 2025) — cross-browser caveat detail.
