---
name: spring-physics-and-list-animation
description: Physics-based and list-diff animation in React — React Spring for drag/gesture-driven and organically interruptible motion, AutoAnimate for one-line list add/remove/reorder animation. Use when animating drag interactions, gesture-driven UI, or a list/grid whose children get added, removed, or reordered. Triggers — "spring animation", "react-spring", "drag animation", "AutoAnimate", "animate list changes", "animate reorder", "interruptible animation", "gesture animation".
---

<!-- last-verified: 2026-07 -->

# Spring physics and list animation

Two narrow, complementary tools: one for physically-driven interruptible
motion, one for the specific case of "a list changed, animate the diff."
Neither replaces general enter/exit orchestration — see the decision rule.

## React Spring (`@react-spring/web`)

Framer Motion (`motion`, see `motion-react`) is the default for React
gestures/drag; reach for React Spring only when you need physically
interruptible motion mid-gesture.

Configure motion with **spring physics** (`tension`/`friction`, or the
named presets like `config.wobbly`/`config.stiff`) instead of
duration/easing curves. That's the right mental model specifically because
spring-driven motion is **interruptible mid-flight without a visible
snap**: a drag released, then re-grabbed, then released again, retargets
smoothly because the spring is always resolving toward a target from its
*current* velocity, not replaying a fixed timeline from t=0. A
duration/easing tween can't do this — interrupting one produces a jump cut.

Reach for React Spring specifically for:

- **Drag and gesture-driven UI** — pair with `@use-gesture/react` for
  pointer tracking, feed the gesture's live delta into `useSpring`'s
  target values so the element visually follows the pointer and then
  springs to rest on release.
- **Organic, physically-plausible motion** — anything that should feel
  like it has mass and can be pushed around, versus motion that should
  feel mechanically precise (use CSS/WAA for the latter — see
  `native-motion-first`).

```js
import { useSpring, animated } from '@react-spring/web';

function Card({ dragging, x, y }) {
  const style = useSpring({
    x, y,
    scale: dragging ? 1.05 : 1,
    config: { tension: 300, friction: 20 },
  });
  return <animated.div style={style} />;
}
```

### Accessibility

React Spring doesn't check `prefers-reduced-motion` on its own. Two levers,
use both:

- **`useReducedMotion()`** — a hook that returns whether the user prefers
  reduced motion, for conditionally choosing a config (e.g. an
  instant-snap config vs. the wobbly one) per-animation.
- **`Globals.assign({ skipAnimation: true })`** — a single global switch
  set once at app init (reading the same media query) that makes *every*
  React Spring animation in the app resolve instantly. Prefer this at the
  root for a blanket policy; use the hook when specific animations need
  finer-grained control than an all-or-nothing switch.

## AutoAnimate (`@formkit/auto-animate`)

A one-line retrofit for the single case of list/grid children being added,
removed, or reordered — you are not choreographing an animation, you're
telling the DOM "animate whatever diff happens here":

```js
import { useAutoAnimate } from '@formkit/auto-animate/react';

function List({ items }) {
  const [parent] = useAutoAnimate();
  return (
    <ul ref={parent}>
      {items.map((item) => <li key={item.id}>{item.text}</li>)}
    </ul>
  );
}
```

That's the entire integration surface — no per-element animation props, no
enter/exit variants to define. It works on **third-party markup** too
(a component library's list you don't control the internals of), because
it observes DOM mutations on the parent rather than requiring each child to
opt in individually. This is also its ceiling: zero-config means minimal
control over timing/easing per element — reach for it when the default
"smoothly animate the diff" look is good enough, not when a specific
choreography is required.

## Decision rule

- **AutoAnimate** — the only requirement is "list changed, animate the
  add/remove/reorder diff," and default timing is acceptable. Fastest to
  add, least code, works on markup you didn't author.
- **React Spring** — the animation needs custom physics or must respond to
  a live gesture/drag input, especially where the motion must stay
  interruptible.
- **Neither** — general enter/exit orchestration of unrelated elements
  (a modal opening while a backdrop fades while a toast slides in) is a
  Motion/CSS orchestration problem, not a physics or list-diff problem;
  forcing either tool to cover it usually means fighting the tool instead
  of using it.

Adapted from: https://react-spring.dev/docs/utilities/use-reduced-motion
Adapted from: https://auto-animate.formkit.com
