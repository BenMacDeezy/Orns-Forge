#!/usr/bin/env bash
# Forge update-nudge hook (fg-a10914): thin wrapper invoking
# tools/update_check.py, which does the throttled (24h), fail-silent
# remote-vs-installed version compare and prints AT MOST one line
# ("forge vX.Y.Z available — run /forge:update") when a newer release
# exists on the public mirror.
#
# FAIL SILENT, NON-LOAD-BEARING, matching every other Forge SessionStart
# hook's doctrine (see hooks/hooks.json's top-level description): any
# problem (python missing, update_check.py missing/raising, git missing,
# network unreachable) -> exit 0, no stdout, never blocks or delays the
# session. This script itself never talks to the network — that is all
# inside update_check.py's own timeout-capped, exception-swallowing code
# path (hard cap <=2s on the remote call).
set +e

script="${CLAUDE_PLUGIN_ROOT}/tools/update_check.py"
[ -f "$script" ] || exit 0

py=""
for c in python python3 py; do
  command -v "$c" >/dev/null 2>&1 && { py="$c"; break; }
done
[ -z "$py" ] && exit 0

out=$("$py" "$script" 2>/dev/null)
rc=$?
[ $rc -ne 0 ] && exit 0
[ -z "$out" ] && exit 0

# Single-line ASCII-ish, no quotes/backslashes -> JSON-safe; keep only the
# first line even if something unexpected produced more.
msg=$(printf '%s' "$out" | tr -d '"\\' | head -1)
[ -z "$msg" ] && exit 0
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
exit 0
