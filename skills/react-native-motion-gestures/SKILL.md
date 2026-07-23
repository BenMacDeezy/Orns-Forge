---
name: react-native-motion-gestures
description: Build native-driven animation and gesture interactions in React Native/Expo with Reanimated 4 + Gesture Handler 3 — worklets, shared values, layout animations, shared-element transitions, and gesture composition (simultaneous/exclusive/race), plus the worklet/JS-thread interop pitfalls (stale closures, runOnJS boundaries) that cause silent bugs. The RN analogue of the web motion suite. Use when a task animates a RN screen, wires a pan/pinch/swipe/drag gesture, composes multiple gestures on one view, or a worklet reads a stale prop/state value. Triggers on "Reanimated", "shared value", "useAnimatedStyle", "worklet", "Gesture Handler", "runOnJS", "layout animation", "shared element transition", "RN swipe/drag/pinch".
---
<!-- last-verified: 2026-07 -->

# React Native motion + gestures (Reanimated 4 + Gesture Handler 3)

This is the RN analogue of the web motion suite: **worklets replace the
compositor thread** as the thing that keeps animation smooth under a busy JS
thread. `react-native-performance` (§2) already states the perf reason to go
native-driven — this skill is the HOW: worklet mechanics, gesture composition,
and the interop pitfalls that produce bugs which look like "it just doesn't
update."

## 1. Worklets and shared values

A **worklet** is a JS function that Reanimated can run on the **UI thread**
instead of the JS thread — most Reanimated APIs (`useAnimatedStyle`, gesture
callbacks, `withTiming`/`withSpring`) are auto-workletized; mark a function
worklet explicitly with a `"worklet";` directive at its top when you pass a
plain function somewhere Reanimated expects to run it on the UI thread.

- **`useSharedValue`** creates a shared value — data that lives outside
  React's render cycle and is readable/writable from both threads via its
  `.value` property. Mutating `.value` does **not** trigger a React re-render;
  it drives native-thread animation directly. Never read/write `.value`
  during render — only inside worklets, effects, or event handlers.
- **`useAnimatedStyle`** returns a style object recomputed on the UI thread
  whenever the shared values it reads change — this is the primary way
  a shared value becomes visible pixels. Only `transform` and `opacity`
  changes stay off the layout-recalculation path (same "animate transform/
  opacity only" rule as web).
- **Layout animations** (`entering`/`exiting`/`layout` props, e.g.
  `FadeIn`, `SlideOutRight`, `LinearTransition`) run automatically on
  mount/unmount/reflow without manual shared-value wiring — reach for these
  before hand-rolling enter/exit animation.
- **Shared-element transitions** (`react-native-screens` shared element API,
  or Reanimated's layout-animation-based approach) animate a view smoothly
  between two screens during navigation — verify the navigator you're using
  actually supports the transition primitive before assuming it's wired.

## 2. Gesture composition (Gesture Handler 3)

Gesture Handler 3 replaced the v2 builder methods with **hooks**; the v2
builders remain available under a `Legacy`-prefixed API for migration, but
new code should use the hooks:

| v2 (builder, still supported as `Legacy*`) | v3 (hook, current) | Behavior |
|---|---|---|
| `Gesture.Simultaneous(a, b)` | `useSimultaneousGestures(a, b)` | Both gestures can be active at once — pan+pinch+rotate on a photo. |
| `Gesture.Exclusive(a, b)` | `useExclusiveGestures(a, b)` | Priority order; a later gesture only activates once earlier ones fail — single-tap vs double-tap. |
| `Gesture.Race(a, b)` | `useCompetingGestures(a, b)` | First to activate wins and cancels the rest — long-press vs pan. |

- These hooks compose gestures **attached to the same component**. For
  gestures on **different** components, use `requireToFail` (delay until a
  named handler fails), `simultaneousWith` (recognize together across
  components), or `block` (the reverse relation — useful when a gesture
  should yield to an ancestor `ScrollView`).
- Every composed gesture still needs a `GestureDetector` wrapping the view it
  applies to — composing gestures doesn't remove that requirement.
- Gesture callbacks (`.onUpdate`, `.onEnd`, etc.) run as worklets on the UI
  thread by default — read/write shared values inside them directly; do not
  reach for `runOnJS` unless you specifically need to call non-worklet JS.

## 3. Worklet/JS-thread interop pitfalls

- **Stale closures.** A worklet captures the values in scope **at the time
  it's created**, not live React state — a gesture handler defined in a
  component body closes over the *props at that render*. If a worklet reads
  a prop/state that can change, derive it from a shared value (mutate the
  shared value in an effect when the source updates) instead of trusting the
  captured JS variable to be current.
- **`runOnJS` boundary.** Calling a non-worklet JS function (navigation,
  `setState`, an analytics call, a callback prop that isn't itself a
  worklet) from inside a worklet **requires** `runOnJS(fn)(args)` — calling
  it directly throws or silently no-ops depending on the build. `runOnJS`
  is asynchronous and queues onto the JS thread; do not expect its result
  back on the UI thread in the same tick.
- **`runOnUI`** is the inverse — force a worklet onto the UI thread from JS
  when you need explicit control (e.g. batching several shared-value writes
  in one UI-thread pass instead of one bridge hop each).
- **Don't `console.log` inside a hot worklet path** (every frame of a
  gesture) in a release build — same bridge-crossing cost warning as
  `react-native-performance` §3, and worse per-frame.
- Motion **taste** (duration, easing, spring feel) defers to
  `motion-design-principles`; this skill is mechanics only.

## Quick triage

| Symptom | Most likely cause | Fix |
|---|---|---|
| Animated value doesn't update on prop change | stale closure in worklet | mirror the prop into a shared value, update it in an effect |
| "value used as worklet is not a worklet" / silent no-op calling JS from a gesture | called JS function directly from worklet | wrap in `runOnJS(fn)(...)` |
| Two gestures fight (only one ever activates) | wrong composition hook | `useSimultaneousGestures` if both should run together, `useExclusiveGestures`/`useCompetingGestures` if only one should win |
| Pan gesture never fires inside a ScrollView | ScrollView eating the gesture | `block`/`simultaneousWith` to declare the relation explicitly |
| Layout animation doesn't play on list reorder | missing `layout` prop on the row | add `layout={LinearTransition}` (or equivalent) to the animated row component |

## Sources

Adapted from (2026-07, Reanimated 4.x / Gesture Handler 3.x):
- https://docs.swmansion.com/react-native-reanimated/docs/fundamentals/glossary/
  — worklets, shared values.
- https://docs.swmansion.com/react-native-gesture-handler/docs/fundamentals/gesture-composition/
  — `useSimultaneousGestures`/`useExclusiveGestures`/`useCompetingGestures`.
- https://docs.swmansion.com/react-native-gesture-handler/docs/guides/upgrading-to-3/
  — v2→v3 API mapping, `Legacy*` backward-compat.
