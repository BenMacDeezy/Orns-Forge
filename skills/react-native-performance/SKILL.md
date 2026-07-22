---
name: react-native-performance
description: Make React Native/Expo apps hit 60fps — virtualize long lists, keep animation and gestures off the JS thread, ship the New Architecture + Hermes, and stop re-renders. Covers what web React perf does NOT: the JS-thread/UI-thread split, list virtualization (FlashList/Legend List over ScrollView.map), native-driven animation, and mobile image/startup cost. Use when a RN screen janks while scrolling or animating, a list stutters, startup is slow, or you're choosing a list component. Triggers on "React Native performance", "FlatList slow", "FlashList", "dropped frames", "JS thread", "Hermes", "New Architecture", "Reanimated worklet", "RN list jank", "Expo performance".
---
<!-- last-verified: 2026-07 -->

# React Native performance

Native perf has one governing model the web doesn't: **two threads**. The **JS
thread** runs your React code and event handlers; the **UI (main) thread** draws
frames at 60/120fps. Anything that blocks the JS thread — a heavy re-render, a
`map()` over 500 rows, a JSON parse — starves the frame the UI thread is trying
to paint, and the user sees stutter. Every rule below is about keeping one
thread from starving the other.

The React-level re-render rules from `react-performance` (§3) apply here
unchanged — memoize at boundaries, derive don't mirror, no components-in-components.
This skill adds the native-only concerns.

## 1. Lists — the #1 source of jank

**Never render a long list by mapping into a `ScrollView`** — it mounts every
row up front, blowing memory and the JS thread. Use a virtualizing list that
renders only what's on screen:

- **`FlashList` (Shopify) or Legend List** are the current default for any list
  that scrolls beyond a screen — dramatically less blank-cell flicker and memory
  than `FlatList` because they recycle views instead of unmounting/remounting.
  `FlatList` is the baseline that ships with RN; reach past it for large or
  media-heavy lists.
- **Whichever you use:**
  - **Memoize `renderItem` and the row component** (`React.memo`) — and never
    pass inline functions/objects/arrays as row props, or memo is defeated every
    render.
  - **Stable `keyExtractor`** returning a real id — never the array index.
  - Provide item-size hints (`estimatedItemSize` in FlashList; `getItemLayout`
    in FlatList) so the list can place rows without measuring.
  - Tune `windowSize` / `maxToRenderPerBatch` for very long lists; enable
    `removeClippedSubviews` on Android.

## 2. Keep animation and gesture off the JS thread

A `setState`-per-frame animation runs on the JS thread and drops frames the
moment anything else is busy. Native-driven animation runs on the UI thread and
survives a busy JS thread:

- **Reanimated worklets** run animation logic on the UI thread — this is the
  native equivalent of the compositor-thread rule in web motion. Pair with
  **react-native-gesture-handler** for gestures that stay smooth under load.
- With the legacy `Animated` API, always set **`useNativeDriver: true`** (works
  for transform/opacity — the same "only animate transform and opacity" rule as
  the web).
- Motion *taste* (duration, easing, spring feel) still defers to
  `motion-design-principles`; wiring/patterns live in `react-native-foundations`.
  This section is only the perf reason to go native-driven.

## 3. Ship the New Architecture + Hermes

- **New Architecture** (Fabric renderer + JSI + TurboModules, bridgeless) is the
  default from React Native 0.76+ and in current Expo SDKs. It replaces the old
  serialized async **bridge** with synchronous JSI calls — no more
  serialize/deserialize tax on every native call. Confirm it's enabled; don't
  ship a new app on the legacy bridge.
- **Hermes** (the default JS engine) precompiles to bytecode: faster
  time-to-interactive, lower memory, smaller startup cost than JSC. Keep it on.
- Consequence under the old bridge that still bites: **`console.log` in a
  release build is expensive** (it crosses the bridge/serializes). Strip logs in
  production (babel `transform-remove-console`).

## 4. Images and startup

- **Use `expo-image`** (or FastImage) over the core `<Image>` for lists and
  above-the-fold media — disk/memory caching, better decode, `contentFit`, and
  placeholder/blurhash support. Request an appropriately sized image; never
  decode a 4000px asset into a 100px thumbnail.
- **Startup**: lazy-load heavy screens behind navigation (don't import the whole
  app graph at boot), defer non-critical work with **`InteractionManager
  .runAfterInteractions()`** so it runs after the current transition/gesture
  finishes instead of competing with it, and keep the first screen's JS small.

## Quick triage

| Symptom | Most likely cause | Fix |
|---|---|---|
| Scroll stutters | non-virtualized or unmemoized list | FlashList + memoized `renderItem` |
| Animation janks under load | animating on JS thread | Reanimated worklet / `useNativeDriver` |
| Slow cold start | large boot bundle, JSC | Hermes on, lazy screens, trim boot graph |
| Whole UI freezes briefly | heavy sync work on JS thread | chunk it, or `runAfterInteractions` |
| Blank cells while scrolling | rows unmount/remount | recycling list + size hints |

## Sources

Adapted from:
- https://reactnative.dev/docs/performance
- https://reactnative.dev/architecture/landing-page (New Architecture)
- https://shopify.github.io/flash-list/
- https://docs.swmansion.com/react-native-reanimated/
