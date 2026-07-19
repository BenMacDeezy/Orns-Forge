---
description: Update the Forge plugin to the latest release and report old -> new version
argument-hint: ""
---

`/forge:update` runs the **real Claude Code plugin manager** — Forge never
fetches, writes, or executes plugin code from the network itself. This
command only sequences the CLI's own update commands and reports what they
did.

**Verified 2026-07-18 against `claude plugin --help` / `claude plugin update
--help` / `claude plugin marketplace update --help` on this machine** (quote
below is the exact help text this command is built from — if a future CLI
version's help text no longer matches, stop and report the mismatch instead
of guessing):

```
claude plugin marketplace update [options] [name]
  Update marketplace(s) from their source - updates all if no name specified

claude plugin update [options] <plugin>
  Update a plugin to the latest version (restart required to apply)
```

## What this command does

1. **Note the "old" version.** Read `version` from this session's own
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` — that's the code
   actually loaded right now, restart or not.
2. **Refresh the marketplace source.** Determine which marketplace Forge is
   installed from (the `@marketplace` suffix on the `forge@...` entry in
   `claude plugin list`), then run:
   `claude plugin marketplace update <marketplace-name>`
   — this pulls the marketplace's latest manifest/commit so the plugin
   manager can see a new release exists. If the marketplace name can't be
   determined, run `claude plugin marketplace update` with no name (updates
   all configured marketplaces) instead of guessing one.
3. **Update the plugin.** Run:
   `claude plugin update forge@<marketplace-name>`
   using the marketplace name resolved in step 2. (Live-verified
   2026-07-18: the bare form `claude plugin update forge` fails with
   "Plugin not found" even when only one marketplace ships forge — the
   full `forge@<marketplace>` key is required.)
4. **Note the "new" version.** After the update command completes, read the
   now-updated entry back out of `~/.claude/plugins/installed_plugins.json`
   (`forge@<marketplace-name>` → `version`) — this is the same mechanism
   `/forge:status`'s version-skew nudge (fg-a10907) already uses to compare
   installed-vs-loaded, so the two nudges stay consistent.
5. **Report `old -> new`** in one line, e.g.:
   `Forge updated: v0.10.0 -> v0.11.0.`
   If old and new are identical, say so plainly instead ("already on the
   latest version, vX.Y.Z — nothing to update").
6. **Nudge a restart at the next milestone boundary** — never mid-task,
   never mid-wave. One line, e.g.: "restart Claude Code the next time you're
   between tasks to pick this up (the CLI's own update requires a restart to
   apply)." **Never auto-restart.** This command has no mechanism to restart
   the host process and must not attempt one (no relaunch, no exec, no
   killing the session).

## What this command never does

- Never runs an update without the user explicitly invoking `/forge:update`
  (or the equivalent NL phrasing, gated the same as every other Forge
  command by `natural-language-invocation` in `.forge/forge.md`).
- Never invents a `claude plugin` flag or subcommand not shown in the CLI's
  own `--help` output. If the installed CLI's help text has drifted from
  what's quoted above, stop and report the drift instead of proceeding on a
  guess.
- Never writes to `.forge/`, transitions a task, or touches queue state —
  this is a plugin-manager operation, not a kernel one.
- Never fetches or executes anything itself beyond invoking the `claude
  plugin` subcommands above; all actual network/install work is the
  installed Claude Code CLI's own responsibility.

## Relationship to the SessionStart nudge

The one-line SessionStart nudge ("forge vX.Y.Z available — run
`/forge:update`", `tools/update_check.py` + `hooks/scripts/update-nudge.sh`)
only ever *tells you* a newer release exists on the public mirror — it never
runs an update itself. This command is the only thing that actually updates
anything, and only when you run it.
