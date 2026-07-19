---
name: component-system-shadcn-radix
description: How to build a component layer on shadcn/ui + Radix instead of reinventing it — shadcn as a CLI code-distributor (init/add/view/search, registry.json, registry:base whole-design-system installs), the official shadcn MCP server for agent-driven component installs, Radix Primitives (unstyled, WAI-ARIA-correct, asChild composition), and Radix Colors' 12-step accessible scales. Use when adding a UI component (dialog, dropdown, combobox, toast…), setting up or consuming a component registry, wiring the shadcn MCP, choosing a primitive to build on, or picking accessible color tokens.
---
<!-- last-verified: 2026-07 -->

# Component system: shadcn/ui + Radix

Default posture for any new interactive component: **install from a registry,
own the code, restyle the tokens** — do not hand-roll a dialog/menu/combobox
from raw `<div>`s. shadcn distributes the source into the repo; Radix supplies
the unstyled, accessible behavior underneath. You get to keep and edit the code
without an opaque dependency.

## shadcn/ui is a code distributor, not an npm dependency

You do not `import { Button } from "shadcn"`. The CLI copies component **source
files** into the project (typically `components/ui/`), and from then on they are
your files to edit. Core commands (`pnpm dlx shadcn@latest …`, or the npm/yarn/bun
equivalent):

- `init` — scaffold `components.json`, CSS variables, and the `cn()` util.
- `add <name>` — vendor a component's source into the repo (e.g. `add button dialog`).
- `view <name>` — inspect a registry item's files/deps before installing.
- `search <query>` — find items across configured registries.

Because it is copy-in source, upgrades are diffs you review, not version bumps
you pray over. Never re-fetch and clobber a component the project has since
customized — treat a vendored file as owned code.

## registry.json turns any repo into a component source

A `registry.json` (schema at `ui.shadcn.com/schema/registry.json`) plus item
JSON files makes **any** repo a shadcn registry the CLI can install from. This is
how you ship an internal component library: publish the registry, and every
consuming app runs `shadcn add <your-item>` against it. Configure extra sources
in `components.json` so `add`/`search` resolve them.

- Item `type`s scope what an install pulls in: `registry:ui` (a single
  component), `registry:block` (a multi-file composite), `registry:theme`
  (tokens), `registry:hook`, `registry:lib`, and more.
- **`registry:base` (2026)** distributes a whole design system — tokens,
  primitives, and conventions — in a single install, so a new app adopts the
  system's foundation in one command instead of vendoring pieces one by one.
  Reach for it when standing up an app on an existing internal system.

## Prefer the official shadcn MCP server over reimplementing copy logic

The official MCP server (`ui.shadcn.com/docs/mcp`) lets an agent browse and
install registry items by natural language — "add a dialog", "find a data-table
block", "show me what's in the sidebar block" — resolving against the configured
registries (official + internal). When it is available, **use it** instead of
scripting `add`/`view` by hand or, worse, writing a component from scratch:
it already knows the item graph, dependencies, and file targets. Fall back to
the CLI only when the MCP is not wired up.

## Radix Primitives: the accessible behavior underneath

shadcn components are thin styled wrappers over **Radix Primitives** — unstyled,
composable components that ship correct **WAI-ARIA** semantics, keyboard
interaction, focus management, and typeahead for you. When you build a component
not covered by a registry, build it on the matching Radix primitive rather than
re-deriving roving-tabindex or focus-trap logic.

- **`asChild`** is the key composition escape hatch: it merges the primitive's
  behavior and props onto the child element you pass instead of rendering
  Radix's own wrapper node. `<Dialog.Trigger asChild><MyButton /></Dialog.Trigger>`
  gives `MyButton` all the trigger wiring with no extra DOM and no `<button>`
  nested inside a `<button>`. Use it to attach primitive behavior to your own
  styled elements and to avoid invalid nesting.
- Because primitives are unstyled, they impose no design opinion — all visual
  decisions live in your tokens/classes, which is exactly why shadcn can layer
  a design system on top without fighting the primitive.

## Radix Colors: 12-step accessible scales

Pair with **Radix Colors** — each hue is a 12-step scale engineered for
accessible, predictable roles rather than arbitrary hex picks:

- **1–2** app/subtle backgrounds; **3–5** component backgrounds (normal /
  hover / active / selected); **6–8** borders and separators; **9** the solid,
  saturated brand step (highest-chroma, the one for primary fills); **10** its
  hover; **11** low-contrast accessible text; **12** high-contrast text.
- Every hue ships a matched dark scale using the **same step numbers**, so a
  component styled by step role themes light↔dark for free.
- Step 9 is the anchor: it is the "pure" color of the hue and the only step
  guaranteed high-chroma, which is why brand fills map to 9 and hover to 10.

Combined rule of thumb: reach for a registry item first, drop to a Radix
primitive when none fits, and reach for a raw element only when neither does —
and in all three, drive color by Radix step role, not by eyeballed hex.

**Token source-of-truth arbitration:** when a project runs a DTCG token
pipeline (`design-tokens-pipeline`), that pipeline is authoritative for token
ORIGIN (colors/spacing/type ramps). Radix Colors scales are the source only
when no DTCG pipeline exists.

---
Adapted from:
- shadcn/ui Registry — https://ui.shadcn.com/docs/registry
- shadcn/ui MCP server — https://ui.shadcn.com/docs/mcp
- Radix Primitives overview — https://www.radix-ui.com/primitives/docs/overview/introduction
- Radix Colors — https://github.com/radix-ui/colors
