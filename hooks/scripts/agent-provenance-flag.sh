#!/usr/bin/env bash
# Forge dispatch-provenance flag (PreToolUse on Task/Agent dispatches).
# fg-b0310, spec-b71f3a. FAIL-SILENT, NEVER BLOCKS: unlike budget-guard.sh
# (the ONE documented exception to the fail-silent-hooks doctrine), this
# hook never returns a deny decision -- it always exits 0. It only appends
# a line to .forge/telemetry/dispatch-provenance.log so the session report
# can surface dispatches that don't resolve to a Forge agent file. See
# docs/conventions.md, "Dispatch-provenance flag — 2026-07-19".
set +e
input=$(cat 2>/dev/null)
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
[ -d .forge ] || exit 0

# Extract subagent_type from tool_input. Same flat-regex field-grab style
# budget-guard.sh uses for session_id -- not a full JSON parser, just a
# targeted extraction tolerant of key ordering/whitespace, matching the
# {"tool_name":"Task","tool_input":{"subagent_type":"...", ...}} envelope
# budget-guard.sh already parses from this same PreToolUse Task|Agent hook.
subtype=$(printf '%s' "$input" \
  | grep -o '"subagent_type"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 \
  | sed 's/.*:[[:space:]]*"//; s/"$//')
[ -n "$subtype" ] || exit 0

# The harness's own generic/catch-all subagent_type is the documented
# archive-tier transport (docs/conventions.md, "Universal Forge-agent
# dispatch — 2026-07-19": "uses the harness's generic/catch-all
# subagent_type as transport, injecting the full
# .forge/agents/archive/<name>.md file's content as the spawn contract").
# A generic dispatch is therefore legitimate on its face. The invariant
# that actually matters -- that the injected PROMPT really is an
# archive-tier file's content, not an improvised one -- is a property of
# the prompt body, which this hook cannot see or verify from tool_input's
# subagent_type field alone. That is a documented limit of this hook's
# vantage point, not an oversight: generic types are never flagged.
# "general-purpose" and "Explore" are the two generic/catch-all types
# docs/conventions.md cites by name for this transport; anything else --
# including other harness-builtin or third-party-plugin agent types that
# are not part of Forge's own roster/project-local set -- is judged as a
# NAMED dispatch below and must resolve to a Forge agent file to pass.
case "$subtype" in
  general-purpose|Explore) exit 0 ;;
esac

# Roster agent: agents/<name>.md under the plugin root, referenced with
# the "forge:" prefix convention (subagent_type "forge:forge-worker" ->
# agents/forge-worker.md under CLAUDE_PLUGIN_ROOT).
name="$subtype"
case "$subtype" in
  forge:*) name="${subtype#forge:}" ;;
esac

# Bounce fix (fg-b0310, verifier P2/high): reject any resolved `name`
# that carries a path separator (`/` or the Windows separator `\` --
# this hook runs under Git Bash on Windows) or a `..` segment BEFORE it
# ever reaches a file-existence check. Without this, a subagent_type like
# "../../some/real/file" (or the `forge:` -prefixed / backslash-shaped
# equivalents) can walk `$name` outside the intended agents directories
# and match an unrelated .md file elsewhere on disk, silently treating a
# non-forge dispatch as resolved (no flag written). A traversal-shaped
# name is never a legitimate agent name, so it always falls straight
# through to the FLAGGED path below -- it is judged unresolved, not
# silently dropped. The never-blocks invariant is unaffected either way:
# this only changes whether a line gets logged, never the exit code.
case "$name" in
  */*|*\\*|*..*) name="" ;;
esac

if [ -n "$name" ]; then
  plugin_root="${CLAUDE_PLUGIN_ROOT:-}"
  if [ -n "$plugin_root" ] && [ -f "$plugin_root/agents/$name.md" ]; then
    exit 0
  fi

  # Project-local agent (factory-minted or hand-authored): canonical copy
  # under .forge/agents/, harness-discoverable mirror under .claude/agents/.
  if [ -f ".forge/agents/$name.md" ] || [ -f ".claude/agents/$name.md" ]; then
    exit 0
  fi
fi

# Named, non-forge, resolves to no Forge agent file anywhere Forge looks
# -> flag. Append-only; never denies, never touches the dispatch itself.
logdir=".forge/telemetry"
mkdir -p "$logdir" 2>/dev/null || exit 0
[ -d "$logdir" ] || exit 0
log="$logdir/dispatch-provenance.log"
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
[ -n "$ts" ] || exit 0
# Sanitize subtype for a single safe log line -- subagent_type is
# model-controlled input, not trusted.
safe_subtype=$(printf '%s' "$subtype" | tr -d '\n\r' | tr -cd 'A-Za-z0-9:_./-')
[ -n "$safe_subtype" ] || exit 0
printf '%s %s\n' "$ts" "$safe_subtype" >> "$log" 2>/dev/null
exit 0
