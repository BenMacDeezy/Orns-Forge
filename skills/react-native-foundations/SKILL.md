---
name: react-native-foundations
description: Build React Native/Expo UI that feels native on both platforms — Expo-first setup, expo-router navigation, Reanimated + Gesture Handler, safe-area insets, per-platform conventions, mobile accessibility, and RN styling (StyleSheet/NativeWind). This is the mobile counterpart to the web frontend skills: what changes when there's no DOM, no CSS cascade, and two OS design languages. Use when starting an RN/Expo app, adding a screen or navigation, styling a mobile component, handling notches/keyboard, or making a mobile UI accessible. Triggers on "React Native", "Expo", "expo-router", "NativeWind", "safe area", "mobile navigation", "Pressable", "iOS vs Android", "mobile accessibility", "React Navigation".
---
<!-- last-verified: 2026-07 -->

# React Native foundations

Mobile is not "web in a smaller viewport." There's no DOM, no CSS cascade, no
media queries, and **two design languages** (iOS Human Interface Guidelines,
Android Material) whose conventions users expect you to honor. This skill is the
platform layer; performance lives in `react-native-performance`.

**Map from the web skills you already know:**

| Web skill / concept | React Native equivalent |
|---|---|
| CSS / Tailwind | `StyleSheet.create` or **NativeWind** (Tailwind syntax for RN) |
| ARIA roles/attributes | `accessibilityRole` / `accessibilityLabel` props |
| CSS media / container queries | `useWindowDimensions()`, `Platform`, flex — no queries |
| `div` + CSS | `View` (flex) / `Text` (all text must be inside `<Text>`) |
| Router (Next.js) | **expo-router** (file-based) over React Navigation |
| `prefers-reduced-motion` | `AccessibilityInfo.isReduceMotionEnabled()` |

## 1. Start with Expo

For new apps, **default to Expo** (managed workflow), not bare `react-native
init`. You get EAS Build/Submit/Update (OTA), a large first-party module set
(`expo-image`, `expo-router`, `expo-font`…), and config plugins for native
changes without leaving JS. Drop to a dev build / prebuild only when a native
dependency needs it — you rarely have to eject fully anymore.

## 2. Navigation: expo-router

**expo-router** (file-based routing built on React Navigation) is the default —
files in `app/` become routes, with typed links and deep-linking for free. Know
the three navigator shapes and pick per UX, matching platform norms:

- **Stack** — push/pop screens (iOS swipe-back gesture; Android hardware back).
- **Tabs** — top-level sections (bottom tab bar is the mobile convention).
- **Drawer** — secondary/less-frequent destinations.

Always handle the **Android hardware back button** and iOS **edge-swipe** — they
exist on mobile and have no web equivalent; don't build flows that trap the user.

## 3. Layout & styling

- **Flexbox is the only layout system**, and the default `flexDirection` is
  **`column`** (not `row` like the web) — the single most common RN layout
  surprise. There is no grid, no float, no cascade; styles are per-component
  objects, not inherited.
- **NativeWind** brings Tailwind class syntax to RN if the team wants token
  parity with a web app — but it's a compile-to-StyleSheet layer, not the web
  Tailwind engine, so `tailwind-v4-composition-patterns` transfers only in
  spirit (utility mental model), not 1:1 (no `@theme` CSS vars, no container
  queries). Plain `StyleSheet.create` is the zero-dependency baseline.
- **Component system: NativeWind + react-native-reusables is the default
  reference** — the mobile counterpart to `component-system-shadcn-radix`'s
  web pick, and the same copy-in philosophy: the CLI vendors component
  source into the repo instead of installing an opaque dependency. ~36 of
  shadcn's 51 components are ported (MIT license, released Mar 2026).
  **Tamagui** is the alternative when a team wants one component codebase
  shared across web *and* native rather than a per-platform copy-in.
  **gluestack-ui** carries a maintenance-trajectory **amber flag** — check
  its release cadence and open-issue trend before adopting for a new
  project.
- **Responsive** = `useWindowDimensions()` + `Platform.select()`, not
  breakpoints. Design for the smallest target first.

## 4. Safe areas & keyboard — the hardware realities

- **Never hardcode top/bottom padding for notches.** Use
  `react-native-safe-area-context` — `useSafeAreaInsets()` for values you can
  compose, `SafeAreaView` for a wrapper — so content clears the notch, status
  bar, and home indicator on every device.
- Wrap forms in **`KeyboardAvoidingView`** (with the right `behavior` per
  platform) so the keyboard doesn't cover the focused input.

## 5. Touch & gesture

- **`Pressable`** is the modern touchable — it exposes pressed state for
  feedback and replaces the older `TouchableOpacity`/`TouchableHighlight`. Give
  small controls **`hitSlop`** so the tap target meets the physical minimum
  (see §6).
- For anything beyond a tap — swipe, drag, pinch, pan — use
  **react-native-gesture-handler** with **Reanimated** so the gesture runs on the
  UI thread (the perf reason is in `react-native-performance` §2). Feedback
  convention differs by OS: iOS opacity/scale, Android ripple (`android_ripple`
  on `Pressable`).

## 6. Accessibility — different API, same bar

The `accessibility-wcag-aria` *principles* hold (names, roles, contrast, focus
order), but the *mechanism* is RN props, not ARIA/DOM, and screen readers are
**VoiceOver** (iOS) / **TalkBack** (Android):

- Every interactive element needs an **`accessibilityRole`** and an
  **`accessibilityLabel`** (the icon-only-button rule from the web applies —
  there's no visible text to fall back on). Use `accessibilityState` for
  selected/disabled/checked.
- **Minimum touch target ≈ 44×44 pt (iOS HIG) / 48×48 dp (Android)** — enforce
  with `hitSlop` or min sizes, not by trusting the visual size.
- Respect **Dynamic Type / font scaling** — don't disable `allowFontScaling`;
  test large system font sizes so layouts don't clip.
- Branch motion on `AccessibilityInfo.isReduceMotionEnabled()` (the RN
  `prefers-reduced-motion`), per the substitution rule in
  `motion-design-principles`.

## 7. Honor platform conventions

Use `Platform.OS` / `Platform.select()` to diverge where users expect it —
navigation transitions, back behavior, date/time pickers, share sheets, feedback
style, and default typography all differ between iOS and Android. A screen that
looks identically "custom" on both often feels wrong on both; lean on native
components (or platform-adaptive libraries) for these.

## Verification note

`webapp-visual-testing` (browser screenshots) does **not** cover RN — verify on
an iOS Simulator / Android emulator or Expo Go, and check both platforms plus a
notched device and a large-font setting before hand-off.

## Sources

Adapted from:
- https://docs.expo.dev/
- https://reactnative.dev/docs/accessibility
- https://reactnative.dev/docs/platform-specific-code
- https://docs.swmansion.com/react-native-gesture-handler/
- react-native-reusables (NativeWind port of shadcn/ui, Mar 2026) — https://github.com/founded-labs/react-native-reusables
- Tamagui — https://tamagui.dev/
- gluestack-ui — https://gluestack.io/
