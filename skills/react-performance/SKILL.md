---
name: react-performance
description: Make React/Next.js render fast — eliminate data waterfalls, cut bundle size, and stop needless re-renders, as implementation constraints rather than a post-hoc profiling pass. Use when a React app feels slow, a route's data loads in a chain instead of in parallel, a bundle is too big, a list or form re-renders on every keystroke, or you reach for useMemo/memo/useTransition. Complements core-web-vitals-for-ui (which owns the INP/LCP/CLS field thresholds); this skill owns the React-level causes. Triggers on "React performance", "re-render", "useMemo/memo/useCallback", "waterfall", "bundle size", "code splitting", "useTransition", "Server Component perf", "slow list".
---
<!-- last-verified: 2026-07 -->

# React performance

React perf is three problems, in priority order: **waterfalls** (work that
should be parallel runs in a chain), **bundle** (shipping JS the user doesn't
need yet), and **re-renders** (recomputing/repainting components that didn't
change). Fix them in that order — a waterfall costs whole seconds, a stray
`useMemo` costs microseconds.

Field thresholds (INP/LCP/CLS) live in `core-web-vitals-for-ui`; this skill is
the React-level *cause* layer under those metrics. For the exhaustive,
rule-by-rule rewrite catalog (65+ rules across 8 categories, with before/after
diffs), invoke **`vercel:react-best-practices`** — this skill is the decision
layer that tells you which class of fix the symptom points to.

## 1. Eliminate waterfalls — CRITICAL

A waterfall is sequential `await`s that don't depend on each other. This is the
single most expensive mistake because each hop adds a full round-trip.

- **Parallelize independent fetches.** Kick off everything that can start now,
  then await together — never `await a; await b` when `b` doesn't need `a`.

  ```tsx
  // waterfall: b waits for a for no reason
  const user = await getUser(id);
  const posts = await getPosts(id);
  // parallel
  const [user, posts] = await Promise.all([getUser(id), getPosts(id)]);
  ```

- **Only await at the point of use.** Start the promise early, pass it down,
  and `await` (or `use()`) it where the value is actually needed — don't block
  a whole component tree on data only its leaf reads.
- **Compose Server Components to fetch in parallel.** Sibling RSCs each fetching
  their own data run concurrently; a parent that fetches everything and drills
  props serializes them. Push each fetch to the component that renders it, and
  wrap independent slow regions in their own `<Suspense>` so a fast region
  paints without waiting on a slow one.
- **Dedupe per-request reads** with `React.cache()` (RSC) so the same query
  fired from three components hits the source once.

## 2. Cut the bundle — CRITICAL

Shipping less JavaScript improves every downstream metric (parse, hydrate, INP).

- **Never barrel-import.** `import { X } from "@lib"` where `@lib/index` re-exports
  200 modules can pull the whole library into the bundle. Import from the deep
  path (`@lib/x`) or use a library with real tree-shaking.
- **Dynamic-import heavy, below-the-fold, or conditional UI** — charts, editors,
  modals, anything not needed for first paint — with `next/dynamic` or
  `React.lazy` + `<Suspense>`. Load it on intent (hover/focus/route-approach),
  not eagerly.
- **Defer non-critical third-party scripts** (analytics, chat widgets) with
  `next/script` strategies (`lazyOnload`/`afterInteractive`) so they never sit
  on the critical path.

## 3. Stop needless re-renders — MEDIUM

Reach here only after 1 and 2. Most "React is slow" reports are actually a
waterfall or a bundle problem wearing a re-render costume. When re-renders *are*
the issue:

- **Compute derived state during render** — don't mirror props into state with an
  effect, and don't store what you can derive. An effect that `setState`s from a
  prop is a double render and a bug magnet.
- **Lazy-init expensive initial state**: `useState(() => build())`, not
  `useState(build())` — the latter runs `build()` on every render and throws the
  result away.
- **Never declare a component inside another component** — it's a new type each
  render, so React unmounts and remounts the whole subtree (state lost, DOM
  thrashed). Hoist it out.
- **Use functional updates** (`setCount(c => c + 1)`) so the callback doesn't
  close over stale state and doesn't need the value in its dependency array.
- **Memoize at boundaries, not everywhere.** `React.memo` a component only when
  it's expensive *and* re-renders with unchanged props; `useMemo`/`useCallback`
  only to keep a referentially-stable value that a memoized child or an effect
  dep depends on. Wrapping a primitive expression (`useMemo(() => a + b)`) costs
  more than it saves. **React Compiler** (RC in React 19) auto-memoizes — if it's
  enabled, delete manual memos rather than stacking them.
- **Narrow effect dependencies** to the exact primitives read; depending on a
  whole object re-fires the effect on every unrelated change.

## 4. Yield to keep interactions responsive — MEDIUM

Concurrent React keeps the main thread free during expensive updates (this is
the INP lever from `core-web-vitals-for-ui`, expressed in React):

- **`useTransition`** marks a state update non-urgent, so typing/clicking stays
  responsive while an expensive re-render (filtering a big list, switching a
  heavy tab) happens in the background. Prefer it over hand-rolled loading flags.
- **`useDeferredValue`** lets an expensive derived view lag behind a fast input —
  the input updates every keystroke; the heavy list catches up when idle.
- For very long static lists, CSS **`content-visibility: auto`** skips rendering
  off-screen rows for near-free virtualization before you reach for a windowing
  library.

## Anti-patterns that mask as optimization

- Sprinkling `useMemo`/`useCallback`/`memo` everywhere "to be safe" — adds
  allocation and dependency-tracking cost, hides the real waterfall.
- `useEffect` for anything that isn't an external side effect (derive during
  render; handle interactions in event handlers).
- Reaching for a windowing library before trying `content-visibility`.

## Sources

Adapted from:
- https://react.dev/reference/react/useTransition
- https://react.dev/learn/you-might-not-need-an-effect
- Vercel "React Best Practices" (v1.0, Jan 2026) — the `vercel:react-best-practices` skill, exhaustive rule catalog
