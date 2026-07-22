---
description: Uninstall Forge — sequence claude plugin removal, clean up shims, offer .forge/ removal, print an itemized report
argument-hint: ""
---

`/forge:uninstall` runs the **real Claude Code plugin manager** — Forge
never fetches, writes, or executes plugin code from the network itself. This
command only sequences the CLI's own removal commands, cleans up what Forge
itself installed outside the plugin cache, and reports exactly what
happened — the same relationship `/forge:update` already has to `claude
plugin update` (see `commands/update.md`).

**Interactive-only — no scripted or unattended form.** There is no
`--yes`/`--force` flag and none will be added: every irreversible step below
is gated on an explicit human confirmation in this session. If invoked from
a non-interactive context where a structured confirm cannot be shown, stop
and report that `/forge:uninstall` requires an interactive session instead
of guessing an answer or proceeding unconfirmed.

## What this command does

1. **Resolve the installation.** Determine the installed `forge@<marketplace>`
   entry the same way `/forge:update` does (`claude plugin list`), and read
   this session's own `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`
   `version` for the report.

2. **Sequence the real CLI's removal commands.** Never invent a `claude
   plugin` flag or subcommand not shown in the installed CLI's own
   `--help` output — if it has drifted from what this command expects, stop
   and report the drift instead of guessing:
   - `claude plugin uninstall forge@<marketplace-name>` (or the CLI's
     documented equivalent) removes the plugin installation itself.
   - `claude plugin marketplace remove <marketplace-name>` removes the
     marketplace entry — but **only if this session's own flow added that
     marketplace** (e.g. this session ran `claude plugin marketplace add`
     earlier while installing or updating Forge). A marketplace entry that
     predates this session, or that this session did not itself add, is
     left alone: Forge does not know what else depends on it and must not
     assume it is safe to remove.

3. **Remove Forge-installed shims and hooks.** Run
   `python tools/banner_install.py uninstall` (the same tool
   `/forge:banner uninstall` uses, per `commands/banner.md`) to remove the
   marker-guarded PowerShell/cmd.exe/bash/zsh launcher blocks, the
   generated shim files, the `AutoRun` registry segment, and the
   hand-wired `~/.claude/settings.json` `orn-motd` duplicate if one was
   deregistered. This is the only shim-cleanup Forge performs — no other
   user-space file is touched (`docs/customization-persistence.md`, "Banner
   launcher shim (örn banner)" row).

4. **Offer `.forge/` removal via one structured confirm.** Once steps 1-3
   are done, ask a single `AskUserQuestion` (per `docs/conventions.md`,
   "Asking the user questions (interactive skills)") scoped to exactly one
   decision:
   - "Remove this repo's `.forge/` directory too?" with options
     `Keep .forge/ (recommended)` and `Remove .forge/`.
   - **Declining leaves `.forge/` fully intact** — no queue task, spec,
     memory file, constitution, or config under it is touched.
   - Only on explicit `Remove .forge/` does this command delete the
     directory, and only for **this repo's own `.forge/`** — the one at
     this repo's root, resolved from the current working directory. It
     never filesystem-scans for, nor touches, any other repo's `.forge/`
     directory (per-repo trust model — every repo's Forge installation is
     independently trusted and independently removed).

5. **Print an exact itemized removed-list.** One line per thing actually
   removed this run, e.g.:
   ```
   Forge uninstalled (was v0.11.0):
   - plugin: forge@forge-local (claude plugin uninstall)
   - marketplace: forge-local (added this session, removed)
   - banner shim: PowerShell $PROFILE, ~/.bashrc, AutoRun registry segment
   - .forge/: removed (confirmed)
   ```
   Never list something as removed that wasn't — a skipped marketplace
   entry, a declined `.forge/` removal, or a shim surface `banner_install.py
   uninstall` reported as already-absent are reported as "not removed" /
   "kept", not folded silently into the removed list.

## What this command never does

- Never runs without the user explicitly invoking `/forge:uninstall` (or
  the equivalent NL phrasing, gated the same as every other Forge command
  by `natural-language-invocation` in `.forge/forge.md`).
- Never accepts or checks for a `--yes`/`--force` flag — no scripted,
  CI, or non-interactive path exists for this command, by design.
- Never deletes `.forge/` without the explicit structured confirmation in
  step 4 — declining always leaves it fully intact.
- Never filesystem-scans for or touches any other repo's `.forge/`
  directory — `.forge/` handling is scoped to the current repo only.
- Never modifies any file under project space beyond what the human
  explicitly confirmed for removal, nor any file under user space that
  Forge did not itself install (`docs/customization-persistence.md` is the
  source of truth for which user-space surfaces Forge owns — the banner
  shim only).
- Never invents a `claude plugin` flag or subcommand not shown in the
  CLI's own `--help` output. If the installed CLI's help text has drifted
  from what this command expects, stop and report the drift instead of
  proceeding on a guess.
- Never fetches or executes plugin code itself beyond invoking the `claude
  plugin` subcommands above; all actual removal work is the installed
  Claude Code CLI's own responsibility.
