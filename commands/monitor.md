---
description: Open a live side-terminal HUD of all Claude + external-provider (codex) agent activity
---

**What this does.** Opens a SEPARATE terminal window running
[`agenthud`](https://github.com/neochoon/agenthud) — a live, read-only
heads-up display that auto-detects and merges the on-disk session logs of
every agent CLI on this machine (Claude Code under `~/.claude`, Codex under
`~/.codex/sessions`, and others) into one unified tree, refreshing as agents
work.

**Why a side terminal, not the agent-activity widget.** Claude Code's native
agent-activity area is populated only by in-harness Claude subagents; an
external provider dispatched as a background `codex exec` shell task cannot
appear there without wrapping every dispatch in a babysitter Claude agent
(which would burn the tokens routing externally is meant to save). Because
`codex exec` writes its own rollout JSONL under `~/.codex/sessions`, a
session-reading HUD like agenthud surfaces those dispatches **live, alongside
the Claude subagents**, with zero extra Claude cost. This command is the
supported way to get the unified "who's building right now" view.

**Requirement:** Node.js 20+ (`node --version`). agenthud is run via `npx`,
so no global install is needed. If Node is missing, tell the user to install
Node 20+ and stop — do not attempt a workaround.

**Do this (script-only, no LLM ceremony):**

1. Confirm Node 20+ is available (`node --version` via Bash). If not, report
   the missing prerequisite and stop.
2. Launch `npx -y agenthud` in a NEW, DETACHED terminal window — never in
   this session's shell (it is a long-running TUI). Pick the launcher for the
   current OS:
   - **Windows:** prefer Windows Terminal —
     `wt -w -1 new-tab --title AgentHUD cmd /k "npx -y agenthud"`; if `wt`
     is not found, `start "AgentHUD" cmd /k "npx -y agenthud"`.
   - **macOS:**
     `osascript -e 'tell application "Terminal" to do script "npx -y agenthud"'`.
   - **Linux:** try a common emulator in order (`x-terminal-emulator`,
     `gnome-terminal`, `konsole`) with `-- npx -y agenthud`.
3. If no detached-terminal launcher is available on this platform, DO NOT
   fake it: print the exact one-liner `npx -y agenthud` and tell the user to
   run it themselves in a new terminal.
4. Report which launcher was used (or the fallback), and one line on what the
   HUD shows: live per-agent `[working]`/`[waiting]` state read from each
   agent's session tail, codex and Claude side by side. Then stop — the HUD
   runs independently; this session does not manage or poll it.

**Notes.** The HUD is read-only — it never steers or stops agents. It reads
session logs already on disk, so it needs no hooks, no `.forge/` state, and
no changes to this repo. Closing its window ends it; nothing to clean up.
