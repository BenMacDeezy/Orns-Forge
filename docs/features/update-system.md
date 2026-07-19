# Update system (session-start nudge + `/forge:update`)

Canonical protocol: [`docs/conventions.md`](../conventions.md) references
this work by its task id, `fg-a10914`; the concrete implementation is
`tools/update_check.py`, `hooks/scripts/update-nudge.sh`, and
`commands/update.md` (read those for the literal command sequence — this
page is the narrative summary, not a paraphrase of their security-floor
comments). See also [Releasing](../releasing.md) for the release pipeline
that this system is the client-side counterpart to.

## Two pieces, two jobs

- **The SessionStart nudge** only ever *tells you* a newer release exists.
  It never runs an update itself.
- **`/forge:update`** is the only thing that actually updates anything, and
  only when a human runs it.

## The SessionStart nudge

`hooks/scripts/update-nudge.sh` is a thin, fail-silent wrapper around
`tools/update_check.py`. On every session start it prints **at most one
line** — `forge vX.Y.Z available — run /forge:update` — when a newer
release exists on the public mirror, and stays completely silent otherwise.

- **Version-compare only, by design.** The module's own stated security
  floor: it never executes, evals, or writes anything fetched from the
  remote. The only thing it ever reads from the remote is a list of git tag
  names (`git ls-remote --tags`), each strictly validated against
  `^v?\d+\.\d+\.\d+$` before being treated as a version at all. The only
  thing it ever writes to disk is its own throttle-cache timestamp file,
  machine-local, never inside the repo.
- **24h-throttled.** A cache file's mtime gates every remote check; a fresh
  cache means an immediate, silent no-op, so this never fires more than
  once per day per machine regardless of how many sessions start.
- **Fail-silent, unconditionally.** Every failure path — network error,
  timeout, malformed remote data, missing or unparseable `plugin.json`,
  `git` missing — returns `None` and prints nothing. The nudge can never
  block or delay a session start.
- **Bounded wall-clock, even against a wedged transport.** The remote check
  is capped at 2 seconds two ways at once: git's own transport-timeout
  knobs, and a hard `communicate(timeout=...)` that, on expiry, reaps the
  **entire** process tree (not just the direct `git` child) — a fix for a
  git http(s) transport-helper grandchild that can otherwise hold the
  session up to ~10s past the intended cap on a firewalled/unroutable
  mirror host.
- **Strict semver, nothing coerced.** A partial version, a 4-segment
  version, the literal string `"latest"`, or a malformed tag is rejected
  outright, never partially parsed.

## `/forge:update`

Sequences the **real Claude Code plugin manager** — Forge never fetches,
writes, or executes plugin code from the network itself; this command only
runs the CLI's own update subcommands and reports what they did:

1. Read the "old" version from the currently-loaded
   `.claude-plugin/plugin.json`.
2. `claude plugin marketplace update <name>` — refresh the marketplace
   source so the plugin manager can see a new release exists.
3. `claude plugin update forge@<marketplace-name>` — update the plugin
   (the bare `forge` form is verified to fail; the full `forge@<marketplace>`
   key is required).
4. Read the "new" version back out of `installed_plugins.json` — the same
   mechanism `/forge:status`'s version-skew nudge already uses, so the two
   nudges stay consistent with each other.
5. Report `old -> new` in one line, or say plainly that it's already on the
   latest version.
6. Nudge a restart **at the next milestone boundary** — never mid-task,
   never mid-wave — since the CLI's own update requires a restart to apply.
   **Never auto-restarts**: no relaunch, no exec, no killing the session.

`/forge:update` never writes to `.forge/`, transitions a task, or touches
queue state — it is a plugin-manager operation, not a kernel one — and it
never invents a `claude plugin` flag beyond what the installed CLI's own
`--help` output shows; a drifted CLI surface is reported, not guessed
around.

## Silent until the mirror exists

Both pieces are silent no-ops until `tools/update_check.py`'s `MIRROR_URL`
points at a real public mirror — a placeholder or unset value makes
`check_for_update` return `None` unconditionally. This is why the update
system shipped (`fg-a10914`) before it went live: `fg-a10915` is the task
that later set the real mirror URL and flipped the nudge on. See
[Releasing](../releasing.md) for that sequencing in full.
