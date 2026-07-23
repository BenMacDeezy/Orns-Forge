---
name: visual-polish-and-craft
description: The polish/iteration layer that runs on built UI — spacing rhythm, optical alignment, typography craft, contrast hierarchy beyond the WCAG floor, and a screenshot-critique-fix loop before hand-off. Use when polishing UI, doing visual QA, told to "make it look better/professional," reviewing spacing/alignment/typography, running a design critique, or taking a final pass before ship.
---

# Visual polish and craft

The execution-layer pass that catches what "meets every functional requirement"
misses: the last 10% that separates built-and-working from impeccable. Run this
*after* a direction is chosen and code exists — it never picks the direction, it
sharpens the execution of one already made.

## 1. Hard rules

Each rule is checkable, not a vibe. Cite the ID when flagging a violation.

- **VP-01 Contrast floor + hierarchy.** ≥4.5:1 body text, ≥3:1 large text (WCAG
  AA floor) — but the floor is not the ceiling. Build a visible hierarchy above
  it: primary text reads darker/heavier than secondary, secondary darker than
  tertiary, disabled state visibly (not just technically) distinct.
- **VP-02 Line length.** Body copy measures 65–75ch. Wider lines lose the
  reader's place on the return sweep.
- **VP-03 Hero type ceiling.** Fluid display type via `clamp()`, capped around
  `~6rem` — scale with the viewport, don't let a clamp's max run unbounded.
- **VP-04 Tight-tracking floor.** Display letter-spacing never goes tighter
  than `-0.04em`. Past that, characters lose their own shapes.
- **VP-05 Radius consistency.** One border-radius scale for the whole surface.
  A component inventing its own radius value is drift, not a decision.
- **VP-06 Z-index discipline.** Named layers (e.g. `--z-nav`, `--z-modal`,
  `--z-toast`), never an arbitrary `9999` stacked to win a fight.
- **VP-07 Reduced motion, mandatory.** Any motion ships a
  `prefers-reduced-motion` substitution. Not optional, not "if there's time."
- **VP-08 Spacing rhythm.** One spacing scale, reused. Flag mixed arbitrary
  values in the same section (`13px` next to `17px` next to `22px`) — that's
  the tell of eyeballed, not derived, spacing.
- **VP-09 Optical over box alignment.** Icons and glyphs are centered
  optically, not just by their bounding box (a triangle "play" icon needs a
  few px of right-shift to *look* centered). Hanging punctuation where the
  stack supports it.

## 2. Banned patterns

Named so a critique pass can cite them instead of describing them fresh:

- **gradient-text** — gradient fill as the default way to emphasize a
  heading or metric.
- **glass-default** — glassmorphism (blur + translucency) reached for as the
  default surface treatment rather than a deliberate choice.
- **card-grid-clone** — 3+ cards in a grid with zero differentiation between
  them (same icon treatment, same copy shape, same everything).
- **eyebrow-everywhere** — the same small caps kicker tacked above each and
  every heading, whether or not that section actually needs a category
  label. The repetition is the giveaway: no human information architect
  earns identical treatment for a hero, a testimonials block, and a footer
  CTA alike — the pattern reads as autopilot, not a decision made per
  section.
- **hero-metric-template** — treating an oversized number set against a
  wash of gradient color as the automatic opening move for a hero,
  propped up with a caption and a scatter of secondary stats regardless
  of whether this particular product has a number worth building an
  entrance around.
- **side-stripe-border** — a heavy strip of saturated color run down one
  flank of a card, standing in for real visual hierarchy. It's become
  such a reflexive shorthand for "here's a card" that seasoned reviewers
  can often name the generator on sight.
- **sketchy-svg-default** — hand-drawn/sketchy-style decorative SVGs reached
  for as default texture rather than a considered illustration choice.
- **grid-texture-crutch** — a two-axis hairline grid-line background used as
  generic surface texture outside an actual canvas/map/blueprint context.

## 3. Per-model defect tells

Known model-family tendencies worth extra scrutiny — scan for these FIRST when
reviewing generated UI, before the general pass. These are drawn from
Impeccable's provider-gated detector rules (opt-in `--gpt` / `--gemini`
flags in the upstream tool), not general folklore:

| Family | Tell | What it looks like |
|---|---|---|
| GPT-family | Hairline border + wide diffuse shadow | Ghost-card look — a thin border *and* a soft wide shadow on the same element, committing to neither a defined edge nor a soft elevation. |
| GPT-family | Repeating-gradient stripes / grid-line background | Decorative texture crutch outside any canvas/map context. |
| GPT-family | "Theater" framing copy | Dismissing something as "theater" instead of stating plainly what it does. |
| Gemini-family | Raw `<img>` hover transform | Scaling or rotating a plain image on hover as the default micro-interaction. |
| Cross-model | Uniform 3-card feature grid | `card-grid-clone` (§2) shows up disproportionately as the default "explain three things" layout. |
| Cross-model | Systematic over-rounding | Every corner on every element pulled to the same large radius regardless of size or role — an observed tendency, not yet a cited detector rule; verify against VP-05 instead of taking it on faith. |

## 4. State design, not just state handling

Handling a state means it renders. Designing it means it's good:

- **Empty states** get a designed moment: icon/illustration, one line of
  guidance, one primary action. Not a bare "No items."
- **Loading states** match the final layout — skeletons over spinners
  whenever the layout is already known, so nothing reflows when data lands
  (pairs with `core-web-vitals-for-ui`'s CLS space-reservation rule).
- **Error states** are recoverable by design: state what went wrong, state
  what to do next. Never apologize, never go vague about the cause.
- **Micro-copy**: buttons carry verbs ("Save changes," "Publish"), never
  "Submit." The verb on a control has to survive into whatever confirms
  it — click "Archive" and the confirmation should say "Archived," not
  drift into a different word for the same action.

## 5. The polish loop

1. **Screenshot** what was built.
2. **Critique** against §1–§4 by rule ID — "VP-08 violated, spacing jumps
   13px→22px mid-section" beats "spacing feels off."
3. **Fix** the cited violations.
4. **Re-screenshot** and confirm.

Two passes minimum before calling it done. Many of §1's rules are statically
checkable by inspection — contrast ratios, line length, radius/spacing values
against the scale — before spending a visual pass at all (the deterministic-
precheck concept, credited to Impeccable's 46-rule detector; no code shipped
here, just the idea: check what can be checked mechanically before relying on
a screenshot).

## 6. Boundary

`anti-generic-design-restraint` owns direction-level taste — picking the
palette/type/layout concept and vetoing genericness before code exists. This
skill owns execution-level polish — the last 10% once a direction is already
chosen and built. `frontend-design` (external, Anthropic) leads craft
direction where it's present; this skill never re-litigates its aesthetic
call, only sharpens its execution.

Concretely: if a review finds the *palette* is a generic default (§2's
`ai-color-palette`-style cluster, cream-and-terracotta, near-black-plus-acid),
that's a direction problem — send it back to `anti-generic-design-restraint`,
don't try to fix it here. If the palette is fine but the spacing drifts, the
contrast lacks hierarchy, or a hover state animates a raw `<img>`, that's
this skill's job. A single review pass may hand off in both directions in
sequence; it should never try to re-decide the direction while polishing it.

## 7. Emerging effects library — Canvas UI (watch, not a default)

`Canvas UI` (canvasui.dev, `DavidHDev/canvas-ui`, MIT + Commons Clause) is a
shadcn-registry copy-paste library of ~24 GPU effect components (Particle
Reveal, Glass, Shatter, Liquid, VHS) by David Haz, the React Bits author —
credible maintainer, but NEW (as of 2026-07: ~670 stars, ~20 commits, no
track record yet). Reach for it only as a canned WebGL-overlay effect when
you'd otherwise hand-roll `webgl-react-three-fiber`, under three caveats:

- **Do NOT rely on its headline "html-in-canvas" (DOM-as-render-target) mode
  in production** — it needs Chrome/Edge 140+ behind
  `#enable-experimental-web-platform-features`; everywhere real it silently
  falls back to a plain WebGL overlay. Treat that overlay as the only
  shippable path.
- **License is source-available, not OSI-open** (Commons Clause: use freely in
  your own app, commercial or not; never resell the components). Clear it
  through `dependency-license-audit` if the project has license constraints.
- It's copy-paste source, so no runtime dependency (a supply-chain plus), but
  review the pulled code at install time like any shadcn registry (the #7747
  rule).

Reassess its maturity before it becomes a default; until then it is a pointer,
not a recommendation.

## Sources

Adapted from, never verbatim:
- pbakaus/impeccable (Apache-2.0) — banned-pattern set, per-model gated
  detector rules, and the deterministic-precheck-before-visual-pass concept.
- anthropics/skills `frontend-design` (Apache-2.0) — state/micro-copy voice
  rules ("Save changes," not "Submit"; errors that state what happened and
  what to do) and the screenshot-critique-fix loop.
