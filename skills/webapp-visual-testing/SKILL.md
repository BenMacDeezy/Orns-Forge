---
name: webapp-visual-testing
description: Drive and screenshot a running web app for visual verification — launch a dev server for QA, capture UI states and breakpoints, read browser console/network output during a UI check. Use whenever a Forge agent must confirm rendered output rather than trust the code (forge-ui-verifier's visual-evidence step, or a forge-ui/forge-animator self-check before handoff).
---

# Webapp Visual Testing

Reading the diff is not evidence. Evidence is a screenshot of the thing
actually rendering, plus the console/network state at that moment. This skill
is the HOW behind "render and observe" — it does not decide when to invoke
that step; the calling agent's contract does.

## Tool ladder

Try each tier in order; do not skip ahead just because it's more familiar.

1. **Browser MCP (first choice).** Check whether one is connected via
   `ToolSearch` (`mcp__Claude_Browser__*` or `mcp__claude-in-chrome__*`) before
   assuming it isn't there. If connected: `preview_start`/`navigate` to load
   the surface, `computer` to click/hover/resize/screenshot, `read_page` to
   inspect the DOM, `read_console_messages`/`read_network_requests` for
   errors. This is faster and more precise than scripting a browser by hand —
   prefer it whenever available.
2. **Repo-native Playwright via Bash (second choice).** No browser MCP
   connected → drive a headless browser yourself. This is the
   webapp-testing methodology: launch the app's own dev server, drive it
   headless, screenshot to files, read the files back with `Read`
   (multimodal). Concrete pattern:
   - **Start**: `subprocess.Popen(["npm", "run", "dev"], ...)` (or the
     project's actual dev command) — do not assume a command, read
     `package.json`/README first.
   - **Wait for ready by polling the port, never by sleeping a fixed
     duration.** Attempt a socket connect to `localhost:<port>` every ~0.5s
     up to a timeout (~30s default); proceed the instant it accepts a
     connection, fail loudly if the timeout elapses.
   - **Drive headless**: `chromium.launch(headless=True)`, `page.goto(url)`,
     then `page.wait_for_load_state('networkidle')` before any inspection —
     inspecting before networkidle on a dynamic app is the most common
     failure mode and yields false negatives.
   - **Capture** to a predictable temp path (e.g.
     `<scratchpad>/screenshots/<task>-<state>-<viewport>.png`), then `Read`
     each file back — a screenshot never taken is not evidence.
   - **Harvest console/network** during the same session: attach a
     `page.on("console", ...)` / `page.on("pageerror", ...)` listener before
     navigating, and pull failed requests from the network log; report actual
     errors seen, not "should be fine."
   - **Teardown even on failure.** Wrap the drive logic in try/finally:
     `terminate()` the server process with a short grace period (~5s), escalate
     to `kill()` if it doesn't exit. A crashed automation script must not leave
     a dev server orphaned.
   - If the repo already has visual-regression tooling (Chromatic, Percy, a
     Playwright test suite with its own runner), prefer running that over a
     bespoke script.
3. **Neither available.** State plainly in the output — "no visual evidence
   available" — and judge from code + gates with explicitly reduced
   confidence. Do not silently fall back to a code read and call it verified;
   a code read is never visual evidence of rendered behavior.

## What to capture for a verification pass

Match this to the fields the calling agent's output contract asks for:

- **Every acceptance-relevant state**: default, hover, focus, empty, loading,
  error — whichever the task's acceptance criteria name. Missing a named
  state is a gap to report, not one to assume away.
- **Breakpoints**: the ones the task specifies; absent that, 375px (mobile),
  768px (tablet), 1280px (desktop).
- **`prefers-reduced-motion` on AND off**, for any motion-bearing task — one
  capture per setting, so a verdict can compare them rather than trust a
  description.
- **Keyboard traversal evidence**: screenshots showing the focus ring at each
  tab stop along the interactive path, not just a claim that "focus is
  visible."

## Discipline

- Name evidence files predictably and include the state/viewport in the name
  — a reviewer (human or agent) should be able to tell what a file shows from
  its name alone.
- Every claim in a verdict or report cites the screenshot it came from. "Layout
  holds at 768px" without a file behind it is an assertion, not a finding.
- This skill only observes. Never edit source code while using it — that
  holds for `forge-ui-verifier` (whose role is judge-only) and equally for
  `forge-ui`/`forge-animator` running a pre-handoff self-check: the same
  capture flow applies, but findings go into that worker's own report for the
  verifier to check, never into a PASS/FAIL verdict — only the verifier issues
  those.

## Fail-honest

If the dev server won't start, the port is already in use, or the build is
broken: report the blocker plainly and stop. Do not retry into a stale server
on the wrong port, and do not fabricate or reuse an old screenshot to fill the
gap — a missing capture reported honestly is worth more than a false PASS.

## Sources

Adapted from: [anthropics/skills webapp-testing](https://github.com/anthropics/skills/tree/main/skills/webapp-testing)
(Apache-2.0) — methodology and server-lifecycle pattern re-scoped to Forge's
verifier/self-check roles; not reproduced verbatim.
