#!/usr/bin/env bash
# Forge budget guard (PreToolUse on Task/Agent dispatches).
#
# DOCUMENTED EXCEPTION to the fail-silent-hooks doctrine: unlike every other
# Forge hook, this one is ALLOWED TO BLOCK — it returns a deny decision when
# the session's dispatch count exceeds max-tasks-per-session (.forge/forge.md).
# It still fails silent on anything unexpected (no .forge/, unparseable or
# unset cap, unwritable counter): set +e, exit 0 with no output.
# The kernel's own dispatch count (forge:kernel, ROUTE + DISPATCH) is the
# portable enforcement mechanism; this hook is belt-and-suspenders.
set +e
input=$(cat 2>/dev/null)
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
[ -f .forge/forge.md ] || exit 0

# Parse the cap. "none", absent, or non-numeric -> silent no-op.
cap=$(grep -o 'max-tasks-per-session:[[:space:]]*[0-9][0-9]*' .forge/forge.md 2>/dev/null \
      | head -1 | grep -o '[0-9][0-9]*$')
[ -n "$cap" ] || exit 0
case "$cap" in *[!0-9]*) exit 0 ;; esac

# Session-scoped counter key: session id from the hook input. Without a
# session_id there is no reliable way to key a persistent per-session
# counter file. The former fallback ("ppid-$PPID-$(date)") had zero
# session-unique entropy - a fresh session invoked the same way (same
# PID-visible-to-the-hook, same day) would silently inherit whatever
# count a prior, unrelated (possibly dead) session left at that exact
# path and could be denied on its very first dispatch. Rather than risk
# a false block from this backstop hook, skip the persistent-file cap
# entirely when no session_id is present: the kernel's own dispatch
# count (forge:kernel, ROUTE + DISPATCH) is the portable enforcement
# mechanism and remains authoritative in that case.
key=$(printf '%s' "$input" \
      | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 \
      | sed 's/.*:[[:space:]]*"//; s/"$//')
[ -n "$key" ] || exit 0
key=$(printf '%s' "$key" | tr -cd 'A-Za-z0-9._-')
[ -n "$key" ] || exit 0

counter="${TMPDIR:-/tmp}/forge-dispatch-count-$key"
# TOCTOU guard: the fallback key (ppid+date) is predictable on a shared
# TMPDIR, so refuse to append through a pre-planted symlink/fifo/device -
# only ever write into a plain regular file (or create one fresh).
# NOTE: `-f` dereferences symlinks (true for a symlink pointing at a regular
# file), so the non-regular check alone does NOT catch a symlink planted at
# the predictable key - it would let the append below write through the
# link into the victim file. Reject symlinks explicitly, before the append.
# Residual, honestly stated: on POSIX this -L check closes the symlink
# attack. On Windows Git-bash, symlinks are commonly materialized as plain
# regular-file copies rather than true symlinks, so -L is false there - but
# that also means there is no symlink to attack in the first place. What
# remains everywhere is the narrow TOCTOU window between this check and the
# append (a link could theoretically be planted in between); a mkdir-based
# lock would close that race but is deliberately not added here, since this
# is a fail-silent advisory hook, not a security boundary.
[ -L "$counter" ] && exit 0
[ -e "$counter" ] && [ ! -f "$counter" ] && exit 0
printf '1\n' >> "$counter" 2>/dev/null || exit 0
n=$(grep -c . "$counter" 2>/dev/null)
[ -n "$n" ] || exit 0
case "$n" in *[!0-9]*) exit 0 ;; esac

if [ "$n" -gt "$cap" ]; then
  msg="Forge budget cap reached ($cap tasks) - end the loop with a session report."
  # Single-line ASCII, no quotes/backslashes -> JSON-safe.
  msg=$(printf '%s' "$msg" | tr -d '"\\')
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$msg"
  exit 0
fi
exit 0
