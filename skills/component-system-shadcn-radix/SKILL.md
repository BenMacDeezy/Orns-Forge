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

shadcn components are thin styled wrappers over an unstyled, composable
primitive layer that ships correct **WAI-ARIA** semantics, keyboard
interaction, focus management, and typeahead for you. When you build a
component not covered by a registry, build it on the matching primitive
rather than re-deriving roving-tabindex or focus-trap logic.

- **Base UI is the default primitive library for new projects as of
  July 2026** — the shadcn/ui changelog states projects created on
  `shadcn/create` were already picking Base UI over Radix 2:1 before the
  switch, and Base UI reached v1.6.0 (Jun 2026) with the team calling it
  stable. `npx shadcn@latest init -b base` scaffolds on Base UI.
- **Radix stays fully supported, never deprecated** — every component still
  ships for both primitive libraries. Pass `-b radix` to `init` to scaffold
  on Radix instead (`npx shadcn@latest init -b radix`); an existing
  Radix-based project is not stranded.
- **`asChild` (Radix) and `render` (Base UI) are the same composition escape
  hatch under different names** — each merges the primitive's behavior and
  props onto the child/render element you pass instead of rendering the
  primitive's own wrapper node, so a styled component gets full trigger
  wiring with no extra DOM and no `<button>` nested inside a `<button>`.
  Treat them as the same concept when reading either library's docs.
  Migration between the two is NOT a CLI feature: shadcn ships it as a
  separately-installed coding-agent skill (`npx skills add shadcn/ui`,
  then explicitly ask your agent to migrate a component) — mechanical
  renames like `asChild` -> `render` are auto-applied by that skill, but
  behavior changes are flagged for a human decision, never silently
  patched [ui.shadcn.com/docs/changelog/2026-07-base-ui-default, "Why a
  skill and not a codemod?"].
- Because primitives are unstyled, they impose no design opinion — all visual
  decisions live in your tokens/classes, which is exactly why shadcn can layer
  a design system on top without fighting the primitive, whichever one is
  underneath.

## Third-party registries carry supply-chain risk

A `registry.json` you didn't author is a way to get **unreviewed code
execution in your project**, not just styled components — treat an
unaudited registry the same way you'd treat an unreviewed npm package:

- **Never pass `--overwrite` against an unfamiliar registry.** It silently
  replaces files you may have already vetted or customized with whatever
  the registry ships next, no diff, no second look.
- **Before installing, view the item's file list and dependency list** —
  the same way you'd check `package.json` scripts before `npm install`.
  Watch specifically for dev-dependency script runners (postinstall hooks,
  build scripts) riding along with what looks like a plain UI component;
  shadcn-ui/ui Discussion #7747 documents this exact registry-injection
  vector.
- **Hand-vendor when in doubt** — copy the file(s) you actually need into
  the repo yourself instead of pointing the CLI at a registry you can't
  fully audit.
- Origin UI, Aceternity, Magic UI, and Park UI show up often in
  recommendations, but treat their current maintenance/security posture as
  **unverified — check directly before use**, not as a standing
  recommendation from this skill.

## Situational alternatives to the shadcn/Radix/Base-UI stack

The shadcn+primitive stack is the default, not the only answer — reach for
one of these when the situation calls for it:

- **React Aria Components** — when accessibility depth is the binding
  constraint on a complex interaction (date pickers, grids, drag-and-drop),
  Adobe's React Aria has the deepest ARIA-pattern coverage of any of these
  options.
- **Ark UI** — when the team ships to more than one framework (React, Vue,
  Solid) from a shared component-logic layer; it's the multi-framework
  headless option where shadcn/Radix/Base UI are React-only.
- **Mantine** — a capable full component library, but its client-heavy
  architecture is an explicit **non-fit for RSC-first Next.js App Router
  projects**; don't reach for it there.

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
- shadcn/ui changelog (Base UI default, Jul 2026) — https://ui.shadcn.com/docs/changelog
- Base UI — https://base-ui.com/
- shadcn-ui/ui Discussion #7747 (registry supply-chain risk) — https://github.com/shadcn-ui/ui/discussions/7747
- React Aria Components — https://react-spectrum.adobe.com/react-aria/
- Ark UI — https://ark-ui.com/
- Mantine — https://mantine.dev/
