#!/usr/bin/env bash
# Forge session-start injector: map freshness status + memory index pointer,
# or (repo has no .forge/ yet) a one-line nudge to run /forge:onboard.
# FAIL SILENT, NON-LOAD-BEARING: any problem -> exit 0 with no output. The
# kernel SYNC step performs this same check itself when the hook is absent.
set +e
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# No .forge/ -> this script stays silent. The onboard offer is owned by
# onboard-nudge.sh (substantial-repo heuristic, once-per-day dedupe,
# opt-out Feature) -- printing an ungated line here too would double-voice
# every session forever (2026-07-20 consolidation, onboard-offer-nudge).
[ -d .forge ] || exit 0

msg=""

arch=".forge/map/architecture.md"
if [ -f "$arch" ]; then
  # Full-40-char SHA only, matching the header format docs/conventions.md
  # ("Repo map files (`.forge/map/`) — Phase 2", docs/conventions/
  # artifact-formats.md, fg-b0401) mandates (2026-07-18 drift audit: {7,40}
  # silently accepted abbreviated SHAs the doc's own format definition calls
  # malformed).
  sha=$(grep -o 'forge-map-commit: [0-9a-f]\{40\}' "$arch" 2>/dev/null \
        | head -1 | awk '{print $2}')
  head=$(git rev-parse HEAD 2>/dev/null)
  if [ -n "$sha" ] && [ -n "$head" ]; then
    if [ "$sha" = "$head" ] || git merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then
      behind=$(git rev-list --count "$sha..HEAD" 2>/dev/null)
      if [ -z "$behind" ] || [ "$behind" = "0" ]; then
        msg="Forge: repo map is fresh (.forge/map/architecture.md)."
      else
        msg="Forge: repo map is $behind commit(s) behind HEAD - run /forge:map to refresh."
      fi
    else
      msg="Forge: repo map commit is not an ancestor of HEAD (diverged/rewritten history) - run /forge:map to refresh."
    fi
  elif [ -z "$sha" ]; then
    msg="Forge: repo map header missing or malformed (.forge/map/architecture.md) - run /forge:map to refresh."
  fi
else
  msg="Forge: no repo map yet - run /forge:map to build one."
fi

idx=".forge/memory/MEMORY.md"
if [ -f "$idx" ]; then
  # Scoped to real fact-index entries ("- [name](file.md) - type - desc"),
  # not every top-level bulleted line -- a "## Notes" section (or similar)
  # with its own "- " bullets must not inflate this count.
  n=$(grep -cE '^- \[[^][]+\]\([^()]+\)' "$idx" 2>/dev/null)
  msg="$msg Memory index: $idx ($n fact(s))."
fi

# Root AGENTS.md is the onboard-step-6a signal this repo has been through
# Forge onboarding at least once; reinforce that dispatch stays in-ecosystem.
[ -f AGENTS.md ] && msg="$msg Subagent dispatch in this repo routes through Forge agents, not ad hoc calls."

[ -z "$msg" ] && exit 0
# Single-line ASCII, no quotes/backslashes -> JSON-safe.
msg=$(printf '%s' "$msg" | tr -d '"\\')
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
exit 0
