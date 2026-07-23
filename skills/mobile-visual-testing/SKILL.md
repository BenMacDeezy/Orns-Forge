---
name: mobile-visual-testing
description: Drive and screenshot a running React Native/Expo app on a real device surface for visual verification — adb/xcrun-simctl screenshot capture, Maestro YAML flows (free local CLI only, Maestro Cloud is paid and out of scope), screenshot-diff conventions per platform/device size, and the mobile-specific flake sources (animation settle, keyboard state, permission dialogs) that produce false failures. The device analogue of webapp-visual-testing. Use whenever a Forge agent must confirm rendered mobile output rather than trust the code — forge-mobile-verifier's render-and-observe step, or a forge-mobile self-check before handoff.
---

# Mobile visual testing (device-surface)

Reading the diff is not evidence on mobile either. Evidence is a screenshot
of the thing actually rendering on an emulator/simulator, captured the way
`forge-mobile-verifier` requires — never a browser, never inferred from code.
This skill is the HOW; the calling agent's contract decides when to invoke it.

## Tool ladder

1. **adb (Android) / xcrun simctl (iOS, macOS hosts only) — always available
   first choice** when a booted emulator/simulator exists. Check
   `adb devices` or `xcrun simctl list | grep Booted` before assuming
   neither is running.
   - **Android**: `adb exec-out screencap -p > shot.png` captures the current
     screen without leaving a file on-device; drive interaction with
     `adb shell input tap <x> <y>` / `adb shell input swipe ...`; watch
     `adb logcat` in the same session to catch red-screen JS errors and
     native crashes while you interact.
   - **iOS**: `xcrun simctl io booted screenshot shot.png`; launch/deep-link
     with `xcrun simctl launch`/`openurl`; tail the simulator's log stream
     for JS/native errors during the session.
2. **Maestro — free local CLI only.** Maestro (Apache-2.0, mobile.dev) is a
   YAML-flow UI test runner that drives real interaction (tap, swipe, input,
   assertions) instead of raw coordinate taps, with built-in retry/tolerance
   for animation timing. **Maestro Cloud (parallel hosted device runs,
   priced per concurrent device) is a separate paid product and is
   explicitly out of scope for this skill — author and run flows with the
   free local `maestro` CLI against a local emulator/simulator/device only;
   never assume or reach for cloud execution.**
   - Install: follow `docs.maestro.dev`'s CLI install guide (the CLI is a
     single free download; no account or payment required to author/run
     flows locally).
   - A flow is a YAML file: an `appId` header, `---`, then a command list —
     `launchApp`, `tapOn` (by `text:`/`id:`/coordinates), `inputText`,
     `assertVisible`, `swipe`, `waitForAnimationToEnd`, `hideKeyboard`,
     `takeScreenshot`, `runFlow` (subflows), `repeat`.
   - Run with `maestro test <flow>.yaml`; capture evidence with
     `takeScreenshot: <name>` steps inline in the flow, or `maestro record`
     for a full session video.
   - Prefer Maestro flows over raw adb/simctl taps when the interaction is
     more than "launch and screenshot" — its selector-based waits absorb
     minor layout/animation timing variance that a hardcoded coordinate tap
     does not.
3. **Neither a booted device/simulator nor Maestro available.** State plainly
   — "visual verification UNAVAILABLE on this host" (the exact flag
   `forge-mobile-verifier` reports) — and fall back to gate-level + static
   verification with explicitly reduced confidence. Never fabricate or infer
   a visual pass from code alone, and never substitute a browser.

## Screenshot-diff conventions

- **Name files predictably**: `<task>-<state>-<platform>-<device-class>.png`
  (e.g. `checkout-empty-android-phone.png`) so a reviewer can tell what a
  file shows from its name alone — same discipline as `webapp-visual-testing`.
- **Per-platform, not per-breakpoint.** Mobile has no CSS breakpoints; diff
  by **platform** (iOS vs Android — divergent chrome, safe areas, native
  controls) and **device class** (phone vs tablet, notched vs non-notched)
  instead. Don't reuse a web breakpoint list here.
- **Capture every acceptance-relevant state** named in the task: default,
  loading, empty, error, and any permission/navigation state explicitly in
  scope — a missing state is a gap to report, not one to assume away.
- **One capture per settle**, not one per frame — screenshot after the UI
  has stopped moving (see flake sources below), never mid-transition unless
  the task is specifically about transition frames.

## Mobile-specific flake sources

These produce false failures/passes if not controlled for — they have no
web equivalent:

- **Animation settle.** A screenshot taken before a transition/layout
  animation finishes captures an intermediate frame, not the real state.
  Use Maestro's `waitForAnimationToEnd` (it has built-in animation-timing
  tolerance) before `takeScreenshot`, or an explicit wait keyed to a
  concrete signal (element visible/stable) — never a fixed sleep as the only
  guard.
- **Keyboard state.** The on-screen keyboard changes visible layout (and on
  iOS can shift the whole view). Capture with keyboard both shown (mid text
  entry) and dismissed (`hideKeyboard`) when the task touches an input, and
  don't let an unexpectedly-open keyboard silently shift what a later
  screenshot in the same flow captures.
- **Permission dialogs.** A first-run camera/location/notification prompt
  interrupts a flow non-deterministically. Set permissions ahead of time
  (Maestro's `setPermissions`, or `adb shell pm grant`/simulator's
  `simctl privacy`) rather than hoping the dialog doesn't appear mid-flow —
  an un-handled permission dialog is one of the most common causes of a
  flaky mobile test that passes locally and fails in CI.
- **Cold start vs warm state.** The first launch after install differs from
  a relaunch (onboarding, permission prompts, splash timing) — be explicit
  about which one a captured state represents.

## Discipline

- Every claim in a verdict cites the screenshot/flow-run it came from —
  "renders correctly on Android" without a file behind it is an assertion,
  not a finding.
- This skill only observes. It is the render-and-observe methodology behind
  `forge-mobile-verifier`'s judge-only role and `forge-mobile`'s own
  pre-handoff self-check — neither edits source code while using it; only
  the verifier issues a PASS/FAIL verdict.
- If the emulator/simulator won't boot, ports are already bound, or the app
  crashes on launch: report the blocker plainly and stop. Don't retry into a
  stale device state, and don't reuse an old screenshot to fill the gap.

## Sources

Adapted from (2026-07):
- https://docs.maestro.dev/ (Maestro CLI docs, Apache-2.0) — free local CLI,
  YAML flow commands, `setPermissions`, `waitForAnimationToEnd`.
- https://maestro.dev/cloud — confirms Maestro Cloud (per-concurrent-device
  pricing) is a separate paid product, not the free CLI this skill covers.
- `webapp-visual-testing` (this repo) — sibling methodology, re-scoped from
  browser rendering to device rendering.
