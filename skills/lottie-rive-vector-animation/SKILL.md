---
name: lottie-rive-vector-animation
description: Designer-authored vector/illustration animation — dotLottie (the actively-maintained successor to lottie-web) for playback of After Effects/Lottie JSON exports, and Rive for visually-authored interactive state machines. Use for micro-interaction animations, animated icons, or any "make this Lottie/Rive file play" or "add an interactive animated character/icon" request. Triggers — "Lottie animation", "dotLottie", ".riv file", "Rive state machine", "designer sent an animation", "animated illustration", "onboarding animation".
---

<!-- last-verified: 2026-07 -->

# Lottie/dotLottie and Rive: vector animation

Both tools play back animation authored visually by a designer (After
Effects + Bodymovin/LottieFiles export, or the Rive editor) rather than
animation coded by hand. Neither is a general UI-transition tool — see the
use-case boundary below before reaching for either.

## dotLottie is now the default, not lottie-web

`lottie-web` is on maintenance mode — it still works but isn't where new
capability lands. For new work, default to **dotLottie**
(`@lottiefiles/dotlottie-web`):

- WASM/Rust runtime built on **ThorVG**, rendering via **WebGL2/WebGPU**
  where available. The plain `DotLottie` class renders on the **main thread**;
  for **off-main-thread rendering**, use the separate `DotLottieWorker` class
  instead. That off-main-thread mode is why it outperforms lottie-web's
  SVG/Canvas main-thread rendering, especially with multiple animations on one page.
- The `.lottie` file format itself is a zip container (JSON + assets),
  smaller and easier to distribute than raw Lottie JSON, though the
  runtime plays both.
- Only reach for `lottie-web` specifically when a project already depends
  on its plugin ecosystem (e.g. certain expression interactivity) that
  dotLottie hasn't ported yet — check before assuming, don't default to
  lottie-web out of habit.

```js
import { DotLottie } from '@lottiefiles/dotlottie-web';

const dotLottie = new DotLottie({
  canvas: document.querySelector('#animation'),
  src: '/animations/success.lottie',
  loop: true,
  autoplay: false, // see a11y section — never autoplay unconditionally
});
```

## Rive: when the animation needs to be interactive and stateful

Reach for **Rive** (rive.app), not Lottie, the moment the animation needs
*branching logic* rather than a fixed timeline:

- Authored in the Rive editor as a **state machine** — states connected by
  transitions gated on **boolean, number, and trigger inputs** that your
  app code sets at runtime. A single `.riv` file can encode "idle → hover →
  pressed → success/error," not just one linear play.
- The same `.riv` file runs across **web, iOS, and Android** via Rive's
  native runtimes — one asset, no per-platform re-export, which matters
  the moment an animated component needs to exist in more than one client.
- Authoring requires the **Rive editor** (rive.app) — you cannot hand-code
  a state machine from scratch the way you can tween CSS. If no `.riv`
  asset exists yet, that's a design-tooling dependency to flag, not
  something to fake in code.

```js
import { useRive, useStateMachineInput } from '@rive-app/react-canvas';

const { rive, RiveComponent } = useRive({
  src: '/animations/button.riv',
  stateMachines: 'ButtonSM',
  autoplay: false,
});
const isHovered = useStateMachineInput(rive, 'ButtonSM', 'hover');
```

## Neither has built-in prefers-reduced-motion — gate it yourself

Unlike the View Transitions API, **neither Lottie/dotLottie nor Rive checks
`prefers-reduced-motion` for you.** An unconditional `autoplay: true` or
`loadAnimation()` call will play full motion for users who've asked the OS
to reduce it. Gate manually at the call site:

```js
const reduceMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches;

dotLottie.setLoop(!reduceMotion);
if (!reduceMotion) dotLottie.play();
// else: render the first/last frame as a static image instead
```

For Rive state machines, the equivalent is not disabling autoplay but
constraining which transitions fire — e.g. skip idle "breathing" loops but
still allow the state change a boolean/trigger input represents, since that
state change often carries information, not just decoration.

## Use-case boundary

- **Lottie/dotLottie** — illustrated micro-interactions, onboarding
  sequences, success/error/empty-state illustrations, animated icons: a
  designer-authored *linear* sequence played back, looped, or scrubbed.
- **Rive** — anything on top of that where the animation must *branch* on
  application state: an interactive mascot, a multi-step progress
  character, a game-like UI element with distinct visual states driven by
  real inputs.
- **Neither** — general UI-state transitions (button hover, panel
  expand/collapse, route change, list reorder). Those belong to
  `native-motion-first` or `spring-physics-and-list-animation`; pulling in
  a vector-animation runtime for a plain CSS-scale hover state is the wrong
  tool for the job even though it would technically work.

Adapted from: https://developers.lottiefiles.com/docs/dotlottie-web
Adapted from: https://rive.app/docs/runtimes/web
Adapted from: https://help.rive.app/runtimes/state-machines
