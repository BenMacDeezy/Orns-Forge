---
name: tailwind-v4-composition-patterns
description: Tailwind CSS v4 idioms and the variant-composition trio — CSS-first config via @theme (no tailwind.config.js, tokens auto-exposed as CSS vars), native container queries as first-class utilities, class-variance-authority + tailwind-merge + clsx for typed conditional class composition, and new v4 utilities (@starting-style entrance animations, 3D transforms). Use when configuring theme tokens, building a variant-driven component, composing conditional className logic, writing responsive/container-relative layout, or animating a dialog/popover entrance without JS.
---
<!-- last-verified: 2026-07 -->

# Tailwind v4 composition patterns

Tailwind v4 moves configuration into CSS and makes container queries and entrance
animations first-class. The house style for components is: define tokens in
`@theme`, drive variants with class-variance-authority, and resolve the final
class string with `tailwind-merge` over `clsx`. Follow that and components stay
themeable, conflict-free, and typed.

**Token source-of-truth arbitration:** when a project runs a DTCG token
pipeline (`design-tokens-pipeline`), that pipeline is authoritative for token
ORIGIN (colors/spacing/type ramps) — `@theme` consumes from it, never
redefines it. Only hand-author `@theme` values directly when no DTCG pipeline
exists.

## CSS-first config: `@theme`, not `tailwind.config.js`

v4 configures the design system **in CSS**. There is no `tailwind.config.js` by
default — you declare tokens in an `@theme` block, and Tailwind both generates
the matching utilities and exposes each token as a **CSS custom property** under
the same name:

```css
@import "tailwindcss";
@theme {
  --color-brand-500: oklch(0.62 0.19 255);
  --font-display: "Inter", sans-serif;
  --spacing-gutter: 1.5rem;
}
```

`--color-brand-500` now backs the `bg-brand-500` / `text-brand-500` utilities
**and** is readable as `var(--color-brand-500)` anywhere — inline styles, arbitrary
values, third-party CSS, or JS. Prefer `oklch()` for color tokens (perceptually
uniform, wider gamut). Define tokens once in `@theme`; do not duplicate them in a
JS config that no longer exists.

## Container queries are first-class utilities

Container queries ship in core — **no `@tailwindcss/container-queries` plugin**.
Mark a container with `@container`, then size children to the *container*, not the
viewport:

- `@sm:grid-cols-2 @lg:grid-cols-4` — respond to the container's width.
- `@max-md:hidden` — the `@max-*` variants apply below a container breakpoint.
- Name containers (`@container/sidebar`) and target them (`@lg/sidebar:flex`)
  when nesting.

Reach for these whenever a component must adapt to the space it is dropped into
(cards, sidebars, dashboard tiles) rather than to the page — that is most
reusable components, so default to container queries over viewport `sm:`/`md:`
unless the layout genuinely tracks the viewport.

## The composition trio: cva + tailwind-merge + clsx

Three small libraries, each with one job — compose them, don't substitute one
for another:

- **class-variance-authority (cva)** — declare a component's **typed variant
  API** (`variant`, `size`, …) with `variants`, `compoundVariants`, and
  `defaultVariants`. `VariantProps<typeof x>` gives you the prop types for free.
- **clsx** — build a class string from **conditional** parts
  (`clsx(base, isActive && "…", { "…": flag })`). Truthy-only, no conflict logic.
- **tailwind-merge (`twMerge`)** — **resolve conflicting utilities** so the last
  wins: `twMerge("px-2 px-4") === "px-4"`. Plain string concatenation would keep
  both and let cascade order decide — a bug. This is what lets a caller's
  `className` override a component default.

The canonical `cn()` helper (the one shadcn vendors) is exactly
`twMerge(clsx(inputs))`. Order matters: **clsx first** to assemble candidates,
**twMerge last** to dedupe. Put caller-supplied `className` last in the clsx
inputs so it survives the merge:

```ts
export const cn = (...i: ClassValue[]) => twMerge(clsx(i));
// className={cn(cardVariants({ variant, size }), className)}
```

cva produces the variant classes, `cn` folds in conditionals and the override.
Never build variant logic out of hand-written ternary soup when cva expresses it
declaratively and type-safely.

## New v4 utilities worth reaching for

- **`starting:` (`@starting-style`)** — JS-free enter transitions. Combine the
  visibility variant with a `starting:` starting state so an element animates
  *in* when it appears: e.g. a popover opened via the `open` state animates from
  `starting:open:opacity-0 starting:open:scale-95` to its resting state, driven
  purely by CSS. Use for dialog/popover/tooltip entrances instead of wiring an
  animation library or manual timers.
- **3D transforms** — `rotate-x-*`, `rotate-y-*`, `rotate-z-*`, `perspective-*`,
  `transform-3d`, and `backface-hidden` are now core utilities. Use them for card
  flips and subtle depth without dropping to custom CSS.

Rule of thumb: before writing custom CSS or pulling in an animation dependency,
check whether a v4 utility (`starting:`, container variants, 3D transforms)
already expresses it — v4 absorbed a lot that used to need plugins or JS.

---
Adapted from:
- Tailwind CSS v4 announcement — https://tailwindcss.com/blog/tailwindcss-v4
- class-variance-authority — https://cva.style
- tailwind-merge — https://github.com/dcastil/tailwind-merge
