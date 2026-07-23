#!/usr/bin/env bash
# Forge Task|Agent dispatch hook — single entry point (2026-07-23).
#
# WHY THIS EXISTS: budget-guard.sh and agent-provenance-flag.sh were registered
# as two separate PreToolUse commands on the same `Task|Agent` matcher, so every
# agent dispatch paid TWO bash process spawns. On Windows (Git Bash) a spawn is
# tens to hundreds of milliseconds, and with `max-parallel-tasks: auto` the
# kernel can fire a full wave of dispatches at once — the exact hot path where
# that doubling shows up as hook-timeout noise. This dispatcher reads stdin ONCE
# and runs both checks in ONE process.
#
# Both scripts remain independently executable and independently tested; they
# expose their logic as a function and only self-run when executed directly
# (the `BASH_SOURCE`/`$0` guard at the bottom of each). Neither may `exit` from
# inside its function — that would kill this process and silently skip the
# sibling check.
#
# ORDER: provenance first, budget second. Both run unconditionally, preserving
# the pre-merge behavior where two independent hooks each saw every dispatch —
# a budget denial must still leave a provenance line. Only budget-guard emits
# stdout (its deny decision); provenance is append-to-log only, so there is no
# output-merge conflict.
#
# FAIL-SILENT: this wrapper never introduces a failure of its own. If either
# script is missing or unsourceable, the other still runs and the dispatch is
# allowed through.
set +e

input="$(cat 2>/dev/null)"

# Both scripts cd into CLAUDE_PROJECT_DIR themselves; same target, harmless
# twice. Run each in the current shell so `input` is passed as an argument
# rather than re-read from an already-consumed stdin.
_dir="$(dirname "${BASH_SOURCE[0]}")"

if [ -f "$_dir/agent-provenance-flag.sh" ]; then
  # shellcheck source=/dev/null
  . "$_dir/agent-provenance-flag.sh" 2>/dev/null
  if command -v forge_agent_provenance >/dev/null 2>&1; then
    ( forge_agent_provenance "$input" ) >/dev/null 2>&1
  fi
fi

if [ -f "$_dir/budget-guard.sh" ]; then
  # shellcheck source=/dev/null
  . "$_dir/budget-guard.sh" 2>/dev/null
  if command -v forge_budget_guard >/dev/null 2>&1; then
    forge_budget_guard "$input"
  fi
fi

exit 0
