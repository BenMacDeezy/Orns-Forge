---
description: Update the Forge plugin to the latest release and report old -> new version
argument-hint: "[--version vX.Y.Z]"
---

`/forge:update` runs the **real Claude Code plugin manager** — Forge never
fetches, writes, or executes plugin code from the network itself. This
command only sequences the CLI's own update commands and reports what they
did. **The single exception** is the read-only schema-version inspection
during `--version` rollback (see "Proactive schema-version compatibility
check" below): it reads one constant off the target tag and executes
nothing — see that section for the full scope of the exception.

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
  installed Claude Code CLI's own responsibility. **The single exception**
  is the read-only schema-version inspection during `--version` rollback
  (see "Proactive schema-version compatibility check" below) — it reads
  one constant off the target tag and executes nothing fetched; no other
  path in this command ever touches the network directly.

## Version rollback: `/forge:update --version vX.Y.Z`

`/forge:update --version vX.Y.Z` rolls back (or forward, to any specific
tagged release) the **installed plugin version** against the public
mirror's tags. Per `fg-a10913`'s release convention, every public release
is a single squashed commit tagged `v<version>` with **fresh history per
release** (each tag's commit has no shared ancestry with the previous
release's tag — the private repo's `.forge/` history structurally cannot
leak through it). Rolling back to `vX.Y.Z` means installing exactly the
tree that tag points at, nothing else.

**Scope — plugin version rollback only.** This flow rolls back which
*version of the Forge plugin code* is installed. It is never a mechanism
for recovering mid-task execution state (in-flight queue claims, partial
diffs, a wave that was interrupted) — that concern is `fg-a10302` and it
stays deferred/backlog per the spec's Non-goals. Rolling the plugin back
one version does not rewind `.forge/` queue state, which is this repo's
own working history and is untouched by which plugin version is installed.

1. **Parse the version.** Accept `--version vX.Y.Z` (leading `v` optional
   on input, normalize to `vX.Y.Z` for tag lookup). If the argument isn't
   `--version`, or the value doesn't match `^v?\d+\.\d+\.\d+$`, stop and
   report the malformed argument instead of guessing a tag.
2. **Run the proactive schema-version compatibility check before touching
   anything** — see "Proactive schema-version compatibility check" below.
   If it fires, stop before step 3; do not install.
3. **Version-pinned install, where the installed CLI supports it.** If
   `claude plugin update --help` (already read once per the Verified
   header above) shows a version-pinned argument (e.g. an `--version` or
   `@version` form), drive it directly:
   `claude plugin update forge@<marketplace-name> --version X.Y.Z` (or the
   CLI's equivalent syntax), pointed at the public mirror's `vX.Y.Z` tag.
   Then continue with steps 4-6 of "What this command does" above (note
   new version, report `old -> new`, nudge restart) exactly as the
   latest-version path does.
4. **Documented-manual fallback, where it doesn't.** If the installed
   CLI's `claude plugin update --help` has no version-pinned argument,
   this command does **not** invent one (same rule as "What this command
   never does" above — never guess a flag the CLI doesn't advertise).
   Instead it prints the manual steps and stops:
   - Point the `forge` marketplace entry at the public mirror's `vX.Y.Z`
     tag (the mirror repo and its tag convention are `fg-a10913`'s —
     `https://github.com/BenMacDeezy/Orns-Forge.git`, tag `vX.Y.Z`).
   - Run `claude plugin marketplace update <marketplace-name>` followed by
     `claude plugin update forge@<marketplace-name>` once the marketplace
     source is repointed at that tag.
   - Restart Claude Code at the next milestone boundary to pick it up.
   This is a report-and-stop path, not a partial automation — never runs
   half the flow and leaves the marketplace source in a mixed state.

### Proactive schema-version compatibility check

Before any rollback install completes (steps 3/4 above), check whether the
**target** version `vX.Y.Z` would leave this repo's `.forge/` task, spec,
and memory files ahead of what that version's validators support.

**This is the sole, narrowly-scoped exception to the standing "never
fetches or executes anything from the network" rule stated at the top of
this file and in "What this command never does"** — both of those
sentences point here, and this is the only place that exception lives.
Its scope is exactly this and nothing more: a **read-only** inspection
that reads one constant (`SUPPORTED_SCHEMA`) out of the target `vX.Y.Z`
tag's `tools/validate_task.py` and never executes any fetched content —
no cloning-and-running, no importing, no `eval`, no shelling out to
anything from the fetched tree. Grep the single `SUPPORTED_SCHEMA = <int>`
line (or equivalent read-only tree inspection, e.g. `git show
<tag>:tools/validate_task.py` piped through a plain-text constant
extraction) and stop there.

- Read the `SUPPORTED_SCHEMA` constant the target version's
  `tools/validate_task.py` / `tools/validate_spec.py` /
  `tools/validate_memory.py` would ship, via the read-only inspection
  described immediately above — never by cloning and running code from
  the target tag.
- Compare it against the highest `schema-version` present across this
  repo's current `.forge/` task, spec, and memory files.
- If the target version's supported schema is lower than what's present,
  surface the existing `fg-e106` compatibility message **verbatim** —
  reused exactly as `tools/validate_task.py`, `tools/validate_spec.py`,
  and `tools/validate_memory.py` already emit it, never paraphrased:

  ```
  produced by a newer Forge (schema-version {schema_version} > {SUPPORTED_SCHEMA}) — upgrade the plugin
  ```

  with `{schema_version}` and `{SUPPORTED_SCHEMA}` filled in from the
  comparison above, then **stop before installing**. This is the same
  message a human would otherwise only discover later as a validator
  error the next time `tools/validate_all.py` runs against a downgraded
  plugin — this command surfaces it proactively, before the rollback
  completes, instead of letting that happen.
- If the target version's supported schema is equal to or higher than
  what's present, proceed with the install (step 3 or 4).

## Relationship to the SessionStart nudge

The one-line SessionStart nudge ("forge vX.Y.Z available — run
`/forge:update`", `tools/update_check.py` + `hooks/scripts/update-nudge.sh`)
only ever *tells you* a newer release exists on the public mirror — it never
runs an update itself. This command is the only thing that actually updates
anything, and only when you run it.
