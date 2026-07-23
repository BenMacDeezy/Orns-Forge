---
name: design-tokens-pipeline
description: The single source of truth for design values — author tokens in W3C DTCG format, build them through Style Dictionary into CSS custom properties, and consume them 1:1 in Tailwind v4's @theme. Use when setting up a token system, naming or aliasing tokens, wiring a Figma/Penpot export into code, or deciding where a color/spacing/type value should live. Triggers on "design tokens", "DTCG", "Style Dictionary", "@theme", "token pipeline", "where does this color come from".
---

<!-- last-verified: 2026-07 -->

# Design tokens pipeline

One source of truth for every design value. Author once in DTCG, build once with
Style Dictionary, consume everywhere as CSS custom properties. Never hand-write a
hex or spacing value into a component — it belongs in a token.

## 1. DTCG format (stable since 2025.10)

The W3C Design Tokens Community Group format reached its first stable version on
**2025-10-28**. Author every token as an object with two required keys:

- **`$value`** — the raw value (or an alias).
- **`$type`** — one of the standard types below.

```json
{
  "color": { "brand": { "500": { "$value": "#3B5BFF", "$type": "color" } } },
  "space": { "md": { "$value": "16px", "$type": "dimension" } }
}
```

**Aliasing** references another token by dotted path in curly braces — the way you
avoid duplicating a value:

```json
{ "button": { "bg": { "$value": "{color.brand.500}", "$type": "color" } } }
```

Types you will use: `color`, `dimension`, `fontFamily`, `duration`,
`cubicBezier`, `shadow`, and the composite `typography` (bundles fontFamily,
fontSize, fontWeight, lineHeight, letterSpacing into one token).

**`duration` and `cubicBezier` are shared with animation work** — the same tokens
that feed transitions are consumed by `motion-design-principles` and the motion
libraries. Author easing curves and timing bands here once; don't let motion code
invent its own.

## 2. The pipeline

```
DTCG tokens (.json)
   → Style Dictionary v4 (DTCG-aware build)
   → CSS custom properties (:root { --color-brand-500: … })
   → Tailwind v4 @theme { --color-brand-500: … }  (consumed 1:1)
```

- **Style Dictionary v4** understands `$value`/`$type` natively — no custom
  parser. Point it at the DTCG source and emit a CSS custom-properties file.
- The generated CSS variables drop straight into **Tailwind v4's `@theme` block**.
  Tailwind reads them 1:1: a `--color-brand-500` variable becomes the
  `bg-brand-500` / `text-brand-500` utilities with no remapping layer.
- This keeps one direction of flow. Design tools and code both read the same
  DTCG file; nothing downstream redefines a value.

## 3. Target the DTCG ecosystem

10+ design tools now import/export DTCG — **Figma, Penpot, Sketch, Framer** among
them. Treat DTCG as the reasonable default interchange target: a designer's export
and the codebase's source are the same shape, so a token round-trips without a
translation step. Prefer it over tool-proprietary token formats unless a specific
tool in the workflow can't emit DTCG.

## Source-of-truth arbitration

When a project runs this DTCG token pipeline, it is authoritative for token
ORIGIN (colors, spacing, type ramps) — Tailwind `@theme` and Radix Colors both
consume from it. Radix Colors scales are the source only when no DTCG pipeline
exists.

## 4. Discipline

- Every design value gets a token; components reference tokens, never literals.
- Alias semantic tokens (`button.bg`) to primitive tokens (`color.brand.500`) so
  a rebrand touches the primitive layer only.
- Keep `$type` accurate — Style Dictionary transforms (e.g. px→rem) key off it.
- Establish the token scale before generating screens; don't grow it ad hoc.
- Choosing the actual values (font pairings, palette construction):
  `references/curated-palettes-and-pairings.md` is curated reference data to
  inform token choices — never a pick-a-style generator.

## Sources

Adapted from:
- https://www.designtokens.org/tr/drafts/format/
- https://styledictionary.com/info/dtcg/
