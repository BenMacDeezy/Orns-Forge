#!/usr/bin/env bash
# Forge session-end LEARN reminder. FAIL SILENT, NEVER BLOCKS the stop (no
# decision:block) - the kernel LEARN step is the load-bearing path. Only nudges
# when uncommitted changes suggest work whose learnings may be uncaptured.
# Debounced ONCE PER SESSION: Stop fires at every turn end, and a session
# idling between background-worker notifications stops many times - the
# nudge is only useful the first time, after that it is noise.
set +e

# session_id arrives in the hook's stdin JSON; fall back to a repo-day key.
input=$(cat 2>/dev/null)
sid=$(printf '%s' "$input" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
[ -z "$sid" ] && sid=$(printf '%s' "${CLAUDE_PROJECT_DIR:-$PWD}-$(date +%Y%m%d)" | tr '/\\: .' '_____')
marker="${TMPDIR:-/tmp}/forge-learn-nudge-${sid}"
[ -f "$marker" ] && exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
[ -d .forge ] || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

dirty=$(git status --porcelain 2>/dev/null | head -1)
[ -z "$dirty" ] && exit 0

# fg-a10906: a dirty tree while a Forge task is claimed (claimed-by set) is
# an in-flight background worker/bounce holding the tree on purpose - not a
# loose end. Stay silent AND do not touch the marker, so the nudge can still
# fire later in the same session once the claim clears. Any error in this
# check (missing dir, unreadable files, odd content) must fall through to
# the existing nag behavior below - never crash, never block the stop.
if [ -d .forge/queue/tasks ]; then
    if grep -l '^claimed-by:[[:space:]]*sess-' .forge/queue/tasks/*.md >/dev/null 2>&1; then
        exit 0
    fi
fi

touch "$marker" 2>/dev/null

msg="Forge: uncommitted changes present at session end - if this session learned something durable, run the kernel LEARN step to file a memory fact before finishing (nudging once; will stay quiet for the rest of this session)."
msg=$(printf '%s' "$msg" | tr -d '"\\')
printf '{"hookSpecificOutput":{"hookEventName":"Stop","additionalContext":"%s"}}\n' "$msg"
exit 0
