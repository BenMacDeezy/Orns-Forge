---
name: responsive-container-queries
description: Build responsive UI from the component out, not the viewport in — container size queries, fluid typography with clamp(), and Grid-vs-Flexbox layout choice. Use when a component must adapt to its container rather than the page width, when sizing type to scale smoothly between breakpoints, or when picking a layout primitive. Triggers on "container query", "@container", "responsive component", "fluid typography", "clamp()", "grid or flexbox".
---

<!-- last-verified: 2026-07 -->

# Responsive container queries

Media queries ask how big the *viewport* is; container queries ask how big the
*component's container* is. A card in a sidebar and the same card in a hero should
lay out differently because their containers differ — the viewport can't tell you
that. Reach for container queries whenever a component is reused at different
widths.

## 1. Container size queries — production-safe, zero polyfill

Baseline support: **Chrome/Edge 105+, Safari 16+, Firefox 110+**. No polyfill
needed; ship them directly.

```css
.card-wrap { container-type: inline-size; }      /* establish a query container */

@container (width > 700px) {
  .card { grid-template-columns: 1fr 2fr; }       /* responds to the wrap, not the page */
}
```

- **`container-type: inline-size`** makes an element a query container measured on
  its inline (usually horizontal) axis. Set it on the parent you want to measure
  against, then query with `@container`.
- **Scoped container units** resolve against the nearest query container, not the
  viewport: `cqw` / `cqh` (1% of container width / height), `cqi` / `cqb`
  (inline / block size). Use these instead of `vw`/`vh` inside a component so the
  value tracks the container.

## 2. Fluid typography with clamp()

Scale type smoothly between a floor and a ceiling instead of snapping at
breakpoints:

```css
font-size: clamp(1rem, 0.75rem + 1.5vw, 1.5rem);   /* min, preferred, max */
```

**CRITICAL — build clamp() from `rem`, never from `px` or a bare `vw`.** A
preferred term expressed only in viewport units doesn't respond to the user's
browser font-size setting, so the text can't reach 200% zoom and you **break WCAG
1.4.4 (Resize Text)**. Anchor the min and max in `rem`, and keep a `rem` component
in the preferred term (as above: `0.75rem + 1.5vw`) so zoom still enlarges it.
Verify by zooming the browser to 200% — the text must grow.

## 3. Grid for 2D, Flexbox for 1D

Pick the layout primitive by dimensionality, not habit:

- **CSS Grid** for **two-dimensional** layout — rows *and* columns that must align
  to each other. Card galleries, dashboards, any layout where things line up both
  ways.
- **Flexbox** for **one-dimensional** alignment — a single row or column
  distributing space along one axis. Toolbars, nav bars, button clusters,
  stacking a label above a control.

Using Flexbox to fake a grid (wrapping rows that don't align column-to-column) is
the usual smell; if items in row 2 should align with items in row 1, that's Grid.

## 4. Putting it together

A responsive component: give its wrapper `container-type: inline-size`, lay the
component out with Grid or Flexbox as the dimensionality dictates, size internal
spacing/type with `cq*` units and `rem`-based `clamp()`, and switch layout at
`@container` breakpoints. The component is now self-contained — drop it in any
column width and it adapts on its own.

## Sources

Adapted from:
- https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries
- https://www.oddbird.net/2025/02/12/fluid-type/
