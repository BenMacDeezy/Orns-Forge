---
name: motion-react
description: Framer Motion (now "Motion") for React — component animation, gestures, exit transitions, and shared-element layout. Use when animating React components, adding whileHover/whileTap/drag gestures, animating mount/unmount with AnimatePresence, building shared-element transitions with layoutId, or importing from framer-motion in a React codebase. Triggers on "animate this component", "framer motion", "motion.div", "AnimatePresence", "shared element transition", "drag gesture in React".
---
<!-- last-verified: 2026-07 -->

# Motion for React (Framer Motion)

Defer duration/easing/stagger choices to `motion-design-principles` — this
skill is the React implementation layer, not the taste layer.

Framer Motion (`motion`) is the default for React gestures/drag; reach for
React Spring (`spring-physics-and-list-animation`) only when the motion must
stay physically interruptible mid-gesture.

## 1. 2025 rebrand — get the import right

Framer Motion rebranded to **Motion** and split from Framer the design tool.
The package and import path both changed:

```tsx
// current
import { motion, AnimatePresence } from "motion/react";

// old (framer-motion package) — still works but is the legacy import
import { motion, AnimatePresence } from "framer-motion";
```

New code should import from `motion/react`. If a codebase still has
`framer-motion` in `package.json`, that's fine (it's the same engine under
new ownership) but new imports should target `motion/react` going forward —
flag the mismatch rather than silently perpetuating the old package name.

## 2. Core API

```tsx
<motion.div
  animate={{ x: 100, opacity: 1 }}
  transition={{ type: "spring", stiffness: 300, damping: 30 }}
/>
```

- `initial` / `animate` / `exit` describe *states*, not keyframe timelines —
  Motion interpolates between them.
- `transition` picks bezier (`type: "tween"`, with `duration`/`ease`) or
  spring (`type: "spring"`, with `stiffness`/`damping` or `bounce`/`duration`)
  per the spring-vs-bezier rule from `motion-design-principles`.

### AnimatePresence — the #1 source of bugs

Exit animations **require** wrapping the conditionally-rendered element in
`<AnimatePresence>` — without it, React just unmounts the element instantly
and `exit` never plays:

```tsx
<AnimatePresence>
  {isOpen && (
    <motion.div
      key="panel"                 // required on every child, especially in lists
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    />
  )}
</AnimatePresence>
```

The two recurring bugs are the same root cause: **forgetting
`AnimatePresence` entirely**, or **forgetting a stable `key`** on list items
inside it (without a key, React can't tell which item left the list, so the
wrong item's exit animation plays or none does). Every mapped list of
`motion.*` elements needs an explicit, stable `key` — index keys break this
the moment the list reorders.

### layoutId — shared-element transitions

```tsx
<motion.div layoutId="card-hero" />   // in the collapsed view
<motion.div layoutId="card-hero" />   // in the expanded view
```

Two elements sharing a `layoutId`, mounted at different times (e.g. a card
that becomes a detail view), auto-animate position/size between their two
layouts — no manual FLIP math. Only one can be mounted at a time per
`layoutId`; the swap is what triggers the transition.

## 3. Where Motion is the right tool — and where it isn't

- **Strong fit**: React component mount/unmount transitions, gesture-driven
  interaction (`whileHover`, `whileTap`, `drag`), `whileInView` for
  scroll-triggered reveals, shared-element/layout transitions.
- **Weak fit**: heavy scroll-scrubbed timelines (progress tied precisely to
  scroll position across many elements) and complex SVG morphing/path
  drawing sequences — reach for `gsap-scrolltrigger` instead. Motion's
  scroll tools (`useScroll`, `whileInView`) cover simple reveal-on-scroll;
  they aren't built for pinning + multi-stage scrubbed storytelling.

## 4. Accessibility

```tsx
import { useReducedMotion } from "motion/react";

const shouldReduceMotion = useReducedMotion();
const animate = shouldReduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1, rotate: 0 };
```

`useReducedMotion()` reads the OS-level `prefers-reduced-motion` preference
reactively. Use it to branch animate/transition values per the
substitution rule in `motion-design-principles` (swap scale/rotate for
opacity, ~100–150ms) — don't just delete the `animate` prop, or the state
change becomes imperceptible instead of merely non-jarring.

## 5. Bundle size

The modular `animate()` function (not the full `motion` component API) is
~2.3kb and tree-shakeable — reach for it over the full component API when
animating outside React (e.g. a vanilla DOM node, or a perf-sensitive path)
without pulling in the whole library.

## Sources

Adapted from:
- https://motion.dev/docs/react-quick-start
- https://motion.dev/docs/react-accessibility
- https://motion.dev/docs/gsap-vs-motion
