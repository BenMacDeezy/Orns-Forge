---
name: webgl-react-three-fiber
description: Build real-time interactive 3D on the web with Three.js via React Three Fiber (R3F) — scenes, particles, glTF model viewers, shaders, and scroll-driven camera work — as the heaviest tier of the motion stack, budgeted and lazy-loaded so it never sinks Core Web Vitals. Use when a UI needs genuine 3D (a rotatable product, a particle field, a shader background, a WebGL hero) that CSS 3D transforms cannot express. Do NOT use for card tilt / perspective hover (that's tailwind-v4 CSS 3D transforms) or a canned vector animation (that's lottie-rive). Triggers on "Three.js", "react-three-fiber", "R3F", "WebGL", "3D scene", "shader", "particles", "glTF/GLB model", "drei", "Spline", "3D hero".
---
<!-- last-verified: 2026-07 -->

# WebGL 3D with React Three Fiber

This is the top of the escalation ladder in `native-motion-first`: reach here
only when the motion is a **real-time interactive 3D scene** — particles,
geometry, shaders, a rotatable/animated model, camera-driven scroll — that no
lighter tier can express. It is also **the single heaviest thing you can put on
a page** (a Three.js + R3F bundle is ~150kb+ before your assets, plus a live
render loop), so every rule below is about paying for it only where it earns its
weight.

**Not a 3D job — use the lighter tier instead:**

| Effect | Right tool |
|---|---|
| Card tilt, perspective hover, flip | CSS 3D transforms — `tailwind-v4-composition-patterns` §3D transforms |
| Designer-authored vector/loop animation | `lottie-rive-vector-animation` |
| Scroll pin/scrub of DOM elements | `gsap-scrolltrigger` |
| A prerendered cinematic | a compressed `<video>`, not a live scene |

Motion *taste* (timing, easing, restraint) still defers to
`motion-design-principles`; this skill is the WebGL implementation layer.

## 1. Use React Three Fiber, not raw Three.js (in React)

In a React app, **React Three Fiber** is the default — it's Three.js expressed
as a declarative JSX scene graph, reconciled like the rest of your UI, instead of
imperative `scene.add()` calls fighting React's lifecycle:

```tsx
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";

<Canvas camera={{ position: [0, 0, 5] }} dpr={[1, 2]}>
  <ambientLight intensity={0.6} />
  <mesh rotation={[0.4, 0.2, 0]}>
    <boxGeometry args={[1, 1, 1]} />
    <meshStandardMaterial color="hotpink" />
  </mesh>
  <OrbitControls enablePan={false} />
</Canvas>
```

- **`@react-three/drei`** is the helper library you almost always want:
  `OrbitControls`, `Environment`, `useGLTF`, `Instances`, `ScrollControls`,
  `shaderMaterial`, `Html`, `PerformanceMonitor`. Don't hand-roll what drei ships.
- **`@react-three/postprocessing`** for bloom/DOF/vignette effect passes.
- Reach for **vanilla Three.js** only outside React (a non-React page, a worker).

## 2. Performance — treat it as a budget, not a component

- **Lazy-load and code-split the entire canvas.** `next/dynamic` (or
  `React.lazy` + `Suspense`) the component that mounts `<Canvas>` so the
  Three/R3F bundle is off the critical path and never blocks **LCP**. Paint a
  poster/fallback first; hydrate the scene after. This is the same rule as
  `react-performance` §2, and it is non-negotiable for a 3D hero.
- **`frameloop="demand"`** for scenes that only move on interaction — the render
  loop then runs on `invalidate()` instead of burning a 60fps rAF (and the
  battery) while nothing changes. Only use the default continuous loop for
  genuinely always-animating scenes.
- **Instance repeated geometry.** 2,000 particles or 500 identical objects =
  one `InstancedMesh` / drei `<Instances>` (one draw call), never 2,000 meshes.
- **Compress assets.** glTF geometry through **Draco** or **meshopt**; textures
  as **KTX2/Basis**. Keep poly counts and texture resolution mobile-sane — a
  desktop-sized scene will thermally throttle a phone.
- **Cap `dpr={[1, 2]}`** so retina/3x screens don't quietly render 4–9× the
  pixels.
- **Don't allocate in `useFrame`.** Reuse vectors/quaternions across frames;
  a `new THREE.Vector3()` per frame is GC pressure that shows up as jank.
- R3F auto-disposes most objects on unmount, but **manually-created textures /
  render targets leak** — dispose them yourself.

## 3. Accessibility & fallback — the canvas is a black box

A WebGL canvas is invisible to screen readers, absent without JS/WebGL, and
hostile under reduced-motion. Never trap content or meaning inside it:

- **`prefers-reduced-motion`** → freeze the scene at a settled pose or serve a
  static poster image, per the substitution rule in `motion-design-principles`.
  Check `matchMedia('(prefers-reduced-motion: reduce)')` and branch.
- **Provide a real DOM fallback** — poster image plus actual heading/text
  behind or beside the canvas — so the page still communicates with WebGL off
  or the context lost (`webglcontextlost` fires; unsupported GPUs exist). A
  purely decorative canvas gets `aria-hidden="true"`.
- **Core Web Vitals still apply**: reserve the canvas's box to avoid **CLS**,
  defer its bundle for **LCP**, and keep heavy setup off the main thread for
  **INP** — cross-ref `core-web-vitals-for-ui`.

## 4. Scroll-driven 3D

Drive camera/objects from scroll with drei's **`ScrollControls`/`useScroll`**,
or pair the canvas with **GSAP ScrollTrigger** when the scroll timeline also
sequences DOM elements — don't rebuild scroll math by hand. See
`gsap-scrolltrigger` for the pinning/scrubbing half.

## 5. Assets & sources

- **glTF/GLB** is the delivery format — `useGLTF` (drei) with a Draco loader.
  Run models through `gltf-transform` / `gltfjsx` to prune and generate typed
  components.
- **Spline** is a no-code authoring option: export glTF for the lightweight
  path, or `@splinetool/react-spline` for a quick hero (heavier runtime — budget
  it like any other 3D bundle).

## Sources

Adapted from:
- https://r3f.docs.pmnd.rs/ (React Three Fiber)
- https://drei.docs.pmnd.rs/ (drei helpers)
- https://threejs.org/docs/
- https://web.dev/articles/gltf (asset compression)
