---
name: accessibility-wcag-aria
description: The enforceable accessibility bar for frontend work — build to WCAG 2.2 AA (also ISO/IEC 40500:2025), use the ARIA Authoring Practices Guide as the per-widget source of truth for roles/keyboard/focus, meet contrast minimums (4.5:1 text, 3:1 large text and UI), and give every interactive control an accessible name (icon-only buttons always need aria-label). Use when building or reviewing any interactive component, adding a dialog/menu/tabs/combobox, checking color contrast, wiring keyboard interaction, or auditing UI for accessibility.
---

<!-- last-verified: 2026-07 -->

# Accessibility: WCAG 2.2 AA + ARIA APG

Accessibility is a build-time requirement, not a later audit. The bar is **WCAG
2.2 Level AA** — meet it as you write the component, using the ARIA Authoring
Practices Guide for the exact roles, states, and keyboard behavior each widget
needs. Bake it in; retrofitting a11y onto shipped UI is far costlier.

## The enforceable bar: WCAG 2.2 AA

- **WCAG 2.2 AA** is the target for essentially all product and regulatory
  contexts (it is also published as **ISO/IEC 40500:2025**, the citable standard
  in procurement and legal requirements). Design and review against 2.2 AA
  criteria specifically.
- **WCAG 3.0 is a far-off working draft** — different model, not stable, not
  actionable. Do **not** design to 3.0 or cite it as a requirement; note it only
  as a future direction. When someone says "WCAG compliant," they mean 2.2 AA.
- AA is the operative level. A is too weak to be the goal; AAA is aspirational
  for specific criteria, not a blanket target.

## Per-widget source of truth: the ARIA APG

The **ARIA Authoring Practices Guide** (`w3.org/WAI/ARIA/apg/patterns/`) is the
best per-widget reference — roughly 30 patterns, each with a working reference
implementation, the required roles/states/properties, and a **keyboard
interaction table**. Before building any composite widget (dialog, menu, tabs,
combobox, disclosure, listbox, slider, tree), open its APG pattern and follow it
rather than improvising ARIA.

Worked example — **Dialog (modal)**:

- `role="dialog"` with **`aria-modal="true"`**, plus `aria-labelledby` (or
  `aria-label`) pointing at the title.
- **Focus moves into the dialog** on open (the dialog or its first focusable
  element) and is **trapped** — Tab/Shift+Tab cycle within it, never reaching the
  inert page behind.
- **Escape closes** the dialog.
- On close, **focus returns to the element that invoked it**, so keyboard and
  screen-reader users are not dumped at the top of the page.

Every APG pattern carries this level of specificity; treat the keyboard table as
a checklist. Note: `aria-*` attributes add semantics but never behavior — you
still implement the focus and key handling yourself (or inherit it from a
primitive like Radix that already encodes the APG pattern).

## Contrast minimums

Meet WCAG 2.2 **1.4.3** (text) and **1.4.11** (non-text) at AA:

- **≥ 4.5:1** for normal-size text.
- **≥ 3:1** for **large text** — defined as **≥ 18pt / 24px**, or **≥ 14pt /
  18.5px when bold**.
- **≥ 3:1** for **UI components and meaningful graphics** — control borders,
  focus indicators, icons, chart strokes, and state boundaries that a user must
  perceive to operate the interface.

Verify actual rendered foreground-on-background pairs (including hover, disabled,
and placeholder states), not just the primary token. Do not rely on color alone
to convey state (2.2 **1.4.1**) — pair it with text, shape, or an icon.

## Every control needs an accessible name

Each interactive element must expose a non-empty **accessible name** to assistive
tech (WCAG 2.2 **4.1.2**). Prefer a visible text label — it is testable and
serves sighted users too.

- **Icon-only buttons/links always need an explicit name**: add
  `aria-label="Close"` (or visually hidden text). An icon glyph or SVG is not a
  name; without one the control announces as "button," which is useless.
- Associate form inputs with a real `<label for>` (or `aria-labelledby`);
  `placeholder` is **not** an accessible name and disappears on input.
- Keep the accessible name consistent with any visible label so voice-control
  users can target it (2.2 **2.5.3 Label in Name**).
- Ensure a **visible keyboard focus indicator** (2.2 **2.4.7**) and that every
  interactive element is reachable and operable by keyboard (2.2 **2.1.1**).

Quick pre-ship pass for any interactive component: keyboard-operable end to end,
visible focus, correct APG roles/states, all contrast pairs met, and every
control has an accessible name — with icon-only buttons the first thing to
check.

---
Adapted from:
- WAI-ARIA Authoring Practices Guide, Patterns — https://www.w3.org/WAI/ARIA/apg/patterns/
- WCAG overview and standards — https://www.w3.org/WAI/standards-guidelines/wcag/
