# Antigravity CLI Phase 0 smoke test — 2026-07-19

Task: `fg-c0105` (bm-antigravity-smoke-test), spec-e8a3 "Provider-specific
enablement gates" (Antigravity clause, `.forge/specs/2026-07-19-provider-profiles.md`
lines 271-276, 330-335, 400-406, 479-482).

Goal: clear or confirm the single-source-reported non-TTY stdout/hang bug in
Antigravity CLI's headless mode, with a recorded pass/fail, before the
EXPERIMENTAL provider slot may ever be considered for automated dispatch.

## 1. What exists on this host

`agy` is not on PATH (`where agy` → no match). A search of npm globals,
`%LOCALAPPDATA%`, and `Program Files` found exactly one Antigravity-related
install:

- `C:\Users\flopp\AppData\Local\Programs\Antigravity\` — the **Google
  Antigravity desktop IDE** (Electron/VS Code fork, `product.json` version
  1.107.0, `ideVersion` 2.0.1, `applicationName: antigravity`,
  `aliasName: agy`).
- Launcher scripts: `bin\antigravity` (sh) and `bin\antigravity.cmd`, both on
  PATH via `AppData\Local\Programs\Antigravity\bin`.
- `bin\antigravity.cmd` invokes `Antigravity.exe` with
  `ELECTRON_RUN_AS_NODE=1` against `resources\app\out\cli.js`.

**This is not the same artifact as the `agy` terminal-agent CLI** documented
at `antigravity.google/docs/cli-using` and shipped from
`github.com/google-antigravity/antigravity-cli` (confirmed real: public org,
1,648 stars, 133 forks, created 2026-05-13, verified via
`api.github.com/repos/google-antigravity/antigravity-cli`). That CLI is a
separate downloadable binary (`agy`) with its own `--print`/`-p` headless
mode. It is **not installed on this host** — no `agy` binary, no npm package,
no reference to it outside the IDE's own alias metadata.

## 2. Live probes (this host's installed IDE launcher)

All probes run with `stdin < /dev/null`, non-interactive, 10s hard timeout,
non-mutating (no writes to any repo).

| # | argv | exit code | stdout arrived? | wall time | notes |
|---|------|-----------|------------------|-----------|-------|
| 1 | `antigravity.cmd --version` | 1 | yes (error text) | ~0.25s | `Error: Cannot find module '...\resources\app\out\cli.js'` — the launcher script's own `cli.js` target does not exist in this install; this is a broken/mismatched packaging, not app behavior. |
| 2 | `antigravity.cmd --help` | 1 | yes (same error) | ~0.18s | Identical `MODULE_NOT_FOUND` on `cli.js`. No CLI entrypoint reachable through the documented launcher on this install. |
| 3 | `Antigravity.exe --help` (bypassing the broken wrapper, calling the Electron binary directly) | 124 (killed by timeout) | **no** | 10.45s (hit the timeout) | Did **not** print help or exit. Instead it booted the full IDE stack under a non-TTY: opened a DevTools websocket, spawned `language_server.exe --standalone ... --enable_sidecars`, opened a local HTTPS UI server on `127.0.0.1:<port>`, and kept running until the language server crashed (exit 143) and began an auto-restart loop. Process tree was fully reaped by the timeout kill — verified via `tasklist` after, no orphaned `Antigravity.exe`/`language_server.exe`. |

No probe of an actual headless "reply OK" prompt was possible: there is no
reachable `--print`/`-p`/headless mode on this install — every invocation
path either errors before reaching app logic (probes 1-2) or launches the
full interactive GUI application (probe 3), which has no prompt-mode flag
documented in the one page fetched (`antigravity.google/docs/cli-using`
returned no rendered body content to this fetcher — client-rendered page,
content not confirmed either way).

## 3. Primary-source research on the reported bug

The task brief describes the bug as "single-source-reported." That is no
longer accurate as of this test — multiple independent sources confirm it:

- **GitHub issue**: [`google-antigravity/antigravity-cli#76`](https://github.com/google-antigravity/antigravity-cli/issues/76)
  — "agy --print / -p silently drops stdout when run with a non-TTY (pipe,
  subprocess, redirect)." Opened by `rdfitted` 2026-05-21. 29 comments from
  multiple independent reporters (`yaoshengzhe` — maintainer,
  `allahsan`, `pasunboneleve`) reproducing variants on **both Windows and
  macOS**, across Node/Python/PowerShell/Git-Bash callers. Confirmed via
  unauthenticated `api.github.com` fetch (metadata only, not repo content):
  state `closed`, `state_reason: completed`, `closed_at: 2026-07-12`.
- Root cause per maintainer comment (`yaoshengzhe`, 2026-07-02): on Windows,
  the original redirect logic opened `CONOUT$` for BubbleTea rendering; under
  a piped/subprocess stdout this pointed at the invisible console instead of
  the caller's pipe, silently discarding `--print` output.
- A second, related failure mode surfaced in the same thread
  (`allahsan`, `pasunboneleve`): `agy -p` reading stdin could hang
  indefinitely as a subprocess, and server-side errors (e.g. quota) were
  swallowed with exit 0 and empty stdout — indistinguishable from a genuine
  empty answer.
- Maintainer-stated fix history: **1.0.15** fixed the Windows `CONOUT$`
  stdout-drop; **1.1.1** (closing comment, 2026-07-12) "Fixed print mode
  (--print / -p) silently exiting with a success code and empty output when
  a request failed server-side... Fixed agy -p hanging when run inside a
  shell script or subprocess by no longer reading stdin when a prompt is
  provided via a flag."
- **Latest release** at time of this test: `1.1.4`, published
  **2026-07-18** (one day before this smoke test), per
  `api.github.com/repos/google-antigravity/antigravity-cli/releases/latest`.
  Its changelog still touches this exact area: "Fixed headless (-p /
  --print) runs so they now honor persisted settings.json policies,
  including permissions, file access, sandbox mode, auto-execution, and
  artifact review." Confidence: **Confirmed** (fetched directly from GitHub
  API, not reproduced live — no working `agy` binary on this host to
  re-verify against 1.1.4).

## 4. Verdict

**FAIL / BLOCKED** on clearing the non-TTY stdout/hang bug for automated
dispatch purposes. Two independent findings support this:

1. **No live clearing was possible.** The only Antigravity artifact reachable
   on this host is the desktop IDE, not the `agy` terminal CLI the spec and
   the upstream bug reports describe. The live smoke is therefore
   **blocked-on-human-install** of the actual `agy` CLI — per this task's
   rules, installing new software from the internet is not something this
   agent may do unilaterally (falls under "downloading or executing files
   from untrusted sources," prohibited without a human performing the
   install themselves).
2. **What is reachable behaves badly under non-TTY invocation anyway.** The
   installed IDE's own `antigravity`/`agy`-aliased launcher either errors out
   on a broken packaging path or — when invoked directly — silently starts
   the full interactive GUI/language-server stack and never returns under a
   non-TTY, needing an external kill at the 10s timeout (probe 3 above).
   That is an independent, locally-reproduced hang, distinct from but
   consistent with the upstream reports.
3. Upstream research confirms the specific bug was real (multi-source, not
   single-source) and was fixed in two stages (1.0.15, 1.1.1), but the
   latest release (1.1.4, shipped 1 day before this test) still lists
   headless-mode fixes in the same subsystem — the area has not gone quiet
   long enough to trust unverified, and this host cannot re-verify it live.

**Standing rule restated**: per spec-e8a3's task decomposition
(`bm-antigravity-smoke-test`) and non-goals section, the Antigravity
EXPERIMENTAL profile slot **stays undispatchable** until a human reviews
this evidence. On this FAIL verdict, the fallback is **defer-entirely** —
Antigravity is not enabled as a dispatch target in this pass. No dispatch
code (`tools/providers.py` or otherwise) was touched by this task.

## 5. Next step for a human reviewer

To actually clear this gate, a human needs to install the real `agy` CLI
(`github.com/google-antigravity/antigravity-cli`, latest 1.1.4) on a test
host and re-run the same probe matrix (`--version`, `--help`,
`agy --print "reply OK" < /dev/null > out.txt`, 10s timeout) to confirm
current, real behavior — this pass could only confirm the bug's documented
history, not clear it live.
