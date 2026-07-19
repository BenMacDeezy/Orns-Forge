---
description: Install, uninstall, or check status of the örn banner launcher shim (opt-in, not automatic)
argument-hint: "install | uninstall | status"
---

Run `python tools/banner_install.py` with the subcommand from `$ARGUMENTS`
(default to `status` if `$ARGUMENTS` is empty or unrecognized):

- `/forge:banner install` -> `python tools/banner_install.py install`
- `/forge:banner uninstall` -> `python tools/banner_install.py uninstall`
- `/forge:banner status` -> `python tools/banner_install.py status`

Reply with the tool's own output verbatim, one line per shell surface it
touched — never summarize away a surface it reported on.

**Why this command exists instead of an automatic hook:** a SessionStart
hook's stdout becomes model context, not terminal output — Claude Code has
no mechanism for a hook to paint the user's actual terminal. `hooks.json`
used to wire `banner.sh` into SessionStart on that mistaken assumption; it
ran every session, burned tokens rendering ASCII art into context, and the
user never saw it. That hook has been removed. The banner is real, but it
only shows up through an **opt-in launcher shim** installed by this command
— a `claude` wrapper (PowerShell function, cmd.exe doskey macro, or
bash/zsh function, whichever shells are present) that prints the banner to
the real terminal and then hands off to the real CLI.

**What `install` does, per shell surface:**

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
visible in. It lives inside the exact same -p/--print skip-guard as
before: print-mode invocations get neither. If the animation can't run (no
TTY, VT enable failure, any exception), `--anim` degrades to a static
wordmark print plus a short ~1.5s sleep and never blocks the launch beyond
that.

**The welcome-area hook** (`hooks/scripts/orn-motd.sh`, wired into
`hooks.json`'s `SessionStart`) is separate from this command and always
active once the plugin is installed — it shows a small örn in the startup
**welcome area** (the scrollback above the input line) via
`{"systemMessage": ...}`, the user-DISPLAY channel, at ~zero context cost.
It's the display-channel replacement for the old `banner.sh`, which only
had the model-context channel available and never had a visual payoff.
Respects the same `startup-banner: off` Feature toggle in `.forge/forge.md`
this launcher shim's banner call does (checked inside `banner.py`).
`/forge:banner install` also detects and deregisters a hand-wired
**user-level** duplicate of this same hook (a `SessionStart` entry
referencing `orn-motd` in `~/.claude/settings.json`) so the art doesn't
print twice — it only ever removes the settings.json entry, never the
script file it points at.

**Out of scope, by design**: Win+R "claude" (the Windows Run dialog)
launches `claude.exe` directly and bypasses every shim above — there is no
interception point for that path, and this command does not attempt to wrap
the executable itself.

`/forge:banner uninstall` removes exactly the marker-guarded blocks, the
generated shim files, and this tool's own `AutoRun` segment — nothing else
in your profile, rc files, or registry is touched. `/forge:banner status`
reports what is currently installed, per surface, without changing anything.
