---
description: Install (patch + launcher shim) or restore the örn banner takeover, or check its status
argument-hint: "install | restore (--restore) | status"
---

`/forge:banner` has exactly ONE install mode — there is no separate
splash-only path. Installing means: **patch the block-art escapes out of
your locally installed Claude Code CLI** (byte-length-safely, reversible)
**and** install a first-in-PATH `claude` launcher shim that prints the
Örn's Forge splash before handing off to the real CLI. Every install goes
through the confirm below first; declining installs nothing at all — not
the patch, not the shim.

## `/forge:banner` or `/forge:banner install` — the confirm-then-install flow

1. Run `python tools/banner_install.py install` (no `--yes`) and show the
   user its output **verbatim**. This is a dry run — it writes nothing —
   and reports exactly:
   - the **binary path** that would be patched — resolved from either an
     npm-global install (a `claude`/`claude.cmd`/`claude.ps1` shim pointing
     at a `cli.js` bundle) or a **native bundled install** (a single large
     executable, e.g. `~/.local/bin/claude.exe`, patched directly — there
     is no further shim to chase for those). Every candidate is also
     required to contain a Claude-Code-specific identity marker in its own
     bytes (e.g. `@anthropic-ai/claude-code` or `Claude Code`) before it is
     accepted — a file merely named/sized/shaped like a claude entry point
     is never enough; no marker means target-not-found, not a guess,
   - the **target's whole-file sha256** — remember this exact value,
   - how many art-escape sequences it found and which of the two known
     encodings dominates the file: the literal 6-ASCII-byte escape TEXT
     (`▀` etc — the form observed in a real native install, 488
     occurrences vs only 7 of the other form) or the UTF-8-encoded
     3-byte character itself. Only the dominant form is patched. A count
     that clears the plausibility floor but still looks low is flagged
     `low-count` and refused without an explicit `--force`,
   - the **offsets journal path** — a small sidecar recording the exact
     original bytes at each patched offset (not a full second copy of the
     binary) that `--restore` replays to reconstruct the original exactly,
   - the **stamp path** that tracks the patch (keyed by the pre-patch and
     post-patch whole-file **hashes**, not by CLI version — version travels
     along as informational metadata only) so it can auto-repatch after a
     Claude Code update and be undone later,
   - the disclosure text: this is an **unofficial, local, cosmetic patch**
     to files Anthropic ships — not supported or endorsed by them, and a
     Claude Code update will require a repatch (the installed shim does
     this automatically on your next launch). If Anthropic ships an
     official theming/branding setting, switch to that instead of this
     patch.
2. Ask the user to confirm, in these words or close to them: **"Patch
   `<binary path>` and install the launcher shim? This modifies a file
   Anthropic ships, reversibly for journaled installs
   (`/forge:banner --restore` undoes it exactly). Proceed?"**
3. Only on an explicit yes, run `python tools/banner_install.py install
   --yes --target "<binary path from step 1>" --expect-hash "<whole-file
   sha256 from step 1>"` — passing the literal value `none` for BOTH flags
   if step 1 reported `target-not-found` (no patchable binary at all) —
   and reply with its output verbatim, one line per surface it touched —
   never summarize away a surface it reported on. **`--target`/
   `--expect-hash` are REQUIRED with `--yes`** — this binds the exact file
   and exact bytes the human just approved to the exact write that
   happens; if the resolved target or its hash differ from what was
   confirmed (a PATH change, an update, a swap — anything between preview
   and confirmation), the tool refuses to patch rather than silently
   patching something different than what was shown.
4. On decline (or no clear yes), install **nothing** — do not run
   `install --yes`, do not partially install the shim without the patch,
   and say so plainly.

**No patch-only partials**: if the launcher CLI itself can't be resolved
on PATH at all, the ENTIRE install is refused — nothing is written, not
even a binary patch that might otherwise have been resolvable through the
native-install-root fallback. When the launcher CAN be resolved, writes
happen shims-first, patch-last: if any individual shim surface fails, the
patch step is skipped and the partial-shim state is reported honestly
rather than leaving a patched binary behind a broken/incomplete shim
install.

**Graceful degrade**: if a future Claude Code build encodes its startup
art in neither known form, the patch step is skipped automatically (no
binary write happens) and the tool still installs the splash launcher
shim, with one plain warning that the patch itself didn't apply. This is
reported in the tool's own output, not silently swallowed. The same is
true if python or `banner.py` itself can't be resolved at install time:
the generated shim launches `claude` directly, with no splash and no
auto-repatch call, rather than failing to install at all.

**No patch-only partials, extended (placeholder-path guard):** the claude
CLI path resolved from PATH is also checked that it exists as a real file
(`Path.is_file()`) before anything is written — a resolved path that turns
out to be a stale/hand-edited/broken entry refuses the whole install with a
plain message, exactly like `claude` not being found on PATH at all. The
shim body generators themselves carry the same check as a second,
independent gate.

**Legacy-artifact preflight:** before writing anything, install also scans
for broken legacy banner-shim artifacts left behind by an unclean prior
install/uninstall of **ours** (see the legacy scan under `/forge:banner
status` below for the full gating-vs-informational distinction). Only a
**gating** finding — one this plugin can unambiguously attribute to itself —
refuses the install and tells you to run `/forge:banner --restore` first to
clear it, then re-run install; layering a fresh install on top of broken
leftovers of ours is exactly how two conflicting `claude` shims end up
active at once. A merely **informational** finding (some unrelated
program's own broken AutoRun entry, with nothing to do with forge) never
blocks install.

## `/forge:banner --restore`

Run `python tools/banner_install.py restore` (the positional action; the
legacy `uninstall` action name still works too) and reply with its output
verbatim. This **replays the offsets journal to reconstruct the original
binary byte-for-byte** (verified against the journal's own whole-file hash
before anything is written), removes the launcher shim/wrapper from every
shell surface, removes the cmd.exe AutoRun entry, and deletes the
journal + stamp files — nothing else is touched. It discovers the journal
even with no stamp present (a stamp that never got its final "applied"
flip, was deleted, or failed to write) by scanning for a journal whose
recorded post-patch hash matches the target's current bytes. Always
available, no confirm needed (it only ever reverts state this plugin
created). If the binary changed since it was patched in a way the journal
doesn't recognize (most likely a Claude Code update landed without an
auto-repatch), or if replaying the journal doesn't reproduce the recorded
original bytes, or if an existing journal fails its own integrity check
(stale/tampered/corrupt), the tool refuses to write anything and reports
that explicitly instead of corrupting anything; the shim/AutoRun cleanup
still proceeds regardless. Restore also removes any FORGE-TAGGED shim/
AutoRun-cmd file it finds regardless of whether it's currently broken —
this is what clears every **gating** legacy-artifact finding (the ones the
install preflight above refuses on: an artifact carrying our own tag, or an
AutoRun entry that is ours by filename/location). It does **not** touch an
**informational** finding — an AutoRun entry referencing some unrelated
program's own missing file has nothing to do with forge, is never removed
by restore, and never blocked your install in the first place; see
`/forge:banner status`'s legacy scan below for how the two are labeled
differently.

**Reversibility applies to journaled installs only.** `--restore` can only
undo a patch it has a valid journal for. It cannot undo a write that
predates the journal mechanism, or one where both the journal and stamp
were lost/corrupted with no recoverable evidence — in either case
`--restore` refuses rather than guesses, and the affected file is left as
is (a subsequent Claude Code update naturally overwrites it with pristine
bytes regardless).

## `/forge:banner status`

Run `python tools/banner_install.py status` and reply with its output
verbatim — reports the binary-patch state (from the stamp file) plus every
shell surface, without changing anything.

**Legacy scan (report-only):** status also scans for broken legacy artifacts
from a prior, unclean install/uninstall and reports each one it finds as a
`legacy scan: ...` line (or a single `legacy scan: no broken legacy
banner-shim artifacts found` line when clean):

- a `claude.bat` (or other forge-tagged shim) whose embedded target `claude`
  path no longer exists on disk ("broken legacy shim"),
- a `forge-autorun.cmd` whose doskey macro references a `claude.bat` that no
  longer exists,
- (a **READ-ONLY**, guarded registry query — never a write) an HKCU AutoRun
  value referencing a file path that no longer exists.

Every finding is labeled one of two ways, and the label matters:

- **`legacy scan: ...`** — a **gating** finding this plugin can
  unambiguously attribute to itself (carries our tag, or the AutoRun path is
  named `forge-autorun.cmd` or lives inside our own shim directory). This is
  the kind `/forge:banner install` refuses on and `/forge:banner --restore`
  clears.
- **`legacy scan (informational, not ours): ...`** — a missing quoted AutoRun
  path with **no connection to forge** (some other program's own stale
  AutoRun entry, for example). Reported for awareness only: it never blocks
  `/forge:banner install`, and `/forge:banner --restore` does not touch it
  (there is nothing of ours to clear).

**Real-incident ground truth, so you recognize this if you ever see it:** a
broken legacy shim manifests as **`claude` failing to launch from an
interactive `cmd.exe` window, while `where claude` still reports the correct,
working install path.** This is not a contradiction — it's `doskey` winning:
the AutoRun-loaded `doskey claude=...` macro intercepts the `claude` command
*before* PATH resolution ever runs in an interactive session, so a stale
macro pointing at a deleted/moved `claude.bat` breaks the command even
though PATH itself was never touched. `where claude` only ever reports PATH
resolution, so it looks "correct" while the shell is actually broken. If you
hit this, run `/forge:banner --restore` to clear the stale shim/AutoRun
entry, then reinstall if you still want the banner.

---

**Why a shim instead of a hook**: a SessionStart hook's stdout becomes
model context, not terminal output — Claude Code has no mechanism for a
hook to paint the user's actual terminal. `hooks.json` used to wire
`banner.sh` into SessionStart on that mistaken assumption; it ran every
session, burned tokens rendering ASCII art into context, and the user never
saw it. That hook has been removed. The banner is real, but it only shows
up through an **opt-in launcher shim** installed by this command — a
`claude` wrapper (PowerShell function, cmd.exe doskey macro, or bash/zsh
function, whichever shells are present) that prints the banner to the real
terminal and then hands off to the real CLI.

**What `install --yes` does, per shell surface** (shims are written FIRST,
the binary patch runs LAST — see "No patch-only partials" above):

- **PowerShell**: appends (or upgrades, if one is already there) a
  marker-guarded `claude` function in `$PROFILE` for every PowerShell host
  found on PATH (`powershell`, `pwsh`). Python is invoked **directly** —
  never piped through `Out-Host`, which would buffer output and break the
  `--anim` splash's cursor-up redraw loop; `-p`/`--print` invocations skip
  it entirely; a `try`/`catch` means a banner failure never blocks the
  actual launch. Re-running `install` is idempotent — a matching block is
  left alone, a *different* block bounded by the same markers (including
  one installed by hand) is upgraded in place.
- **cmd.exe**: a `.bat` shim alone is not enough — if `claude.exe`'s own
  directory sits on the **system** PATH, cmd finds it before any user-PATH
  shim. The actual mechanism is a `doskey` macro loaded through the
  `HKCU\Software\Microsoft\Command Processor\AutoRun` registry value,
  pointing at a small shim script. `doskey` macros only expand in an
  *interactive* session, so `cmd /c` calls and scripts that invoke `claude`
  are unaffected automatically. The registry key is created if absent; an
  existing `AutoRun` value (yours or someone else's) is chained rather than
  clobbered, and re-running `install` will not chain the same segment twice.
- **bash/zsh**: an equivalent marker-guarded `claude` function is appended
  to `~/.bashrc` / `~/.zshrc` when those files exist.

The banner script itself (`tools/banner.py`) is resolved from the
**installed plugin cache** (`~/.claude/plugins/installed_plugins.json` ->
`forge@forge-local` -> `installPath`) at install time, not hardcoded to a
dev checkout; if python or `banner.py` can't be found, the generated shim
silently skips the banner and launches `claude` plain.

**The animated splash IS the hold**: the Claude TUI switches to an
alternate screen buffer immediately on launch, wiping the console — so
every generated shim body calls `python tools/banner.py --anim` (a
truecolor thin-line ÖRN'S FORGE wordmark with a 30-frame white-hot gleam
sweep, self-timed at ~2.6s) instead of a static print plus a separate
sleep; the animation's own runtime is the only window the art is actually
visible in. If the animation can't run (no TTY, VT enable failure, any
exception), it degrades to a static wordmark print plus a short ~1.5s
sleep and never blocks the launch beyond that.

**Auto-repatch after updates**: every generated shim body, right alongside
the `--anim` call and inside the same `-p`/`--print` skip-guard, also calls
`python tools/banner.py --recheck-patch`. This is a total no-op for anyone
who hasn't run `/forge:banner install` (it checks for the stamp file and
returns immediately if absent). Once installed, it silently compares the
CLI bundle's current whole-file hash to the stamped patched-hash on every
`claude` launch: a match means already patched, no-op; a mismatch means
the build changed (a Claude Code update) and re-runs the FULL preview +
low-count-floor + journal-validation pipeline before repatching — it
never blind-patches on a hash mismatch alone, and never passes `--force`
on its own. Never prints anything, never blocks the launch.

**The welcome-area hook** (`hooks/scripts/orn-motd.sh`, wired into
`hooks.json`'s `SessionStart`) is a **separate, unchanged, zero-cost
surface** — not part of this takeover. It always shows a small örn in the
startup **welcome area** (the scrollback above the input line) via
`{"systemMessage": ...}`, the user-DISPLAY channel, once the plugin is
installed. Respects the same `startup-banner: off` Feature toggle in
`.forge/forge.md` the launcher shim's banner call does (checked inside
`banner.py`). `/forge:banner install` also detects and deregisters a
hand-wired **user-level** duplicate of this same hook (a `SessionStart`
entry referencing `orn-motd` in `~/.claude/settings.json`) so the art
doesn't print twice — it only ever removes the settings.json entry, never
the script file it points at.

**Out of scope, by design**: Win+R "claude" (the Windows Run dialog)
launches `claude.exe` directly and bypasses every shim above — there is no
interception point for that path, and this command does not attempt to wrap
the executable itself.
