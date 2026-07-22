#!/usr/bin/env bash
# Forge staleness flagger: on a git commit, flag map index.md sections whose
# files changed. FAIL SILENT, NEVER BLOCKS (advisory systemMessage only; no
# permission decision). Baseline: SYNC's hash check already covers drift.
set +e
input=$(cat 2>/dev/null)

# Cheapest possible gate, on raw stdin, before any cd or git work: the
# overwhelming majority of Bash calls are not `git commit` and must not pay
# for the cd + precise command-extraction grep below. Anchored to the
# "command" JSON field specifically (rather than a bare substring anywhere in
# the payload) so an unrelated field - e.g. a description mentioning the
# phrase "git commit" - can't trip the gate; the precise extraction below is
# still the authority, this is only a cheaper first pass.
printf '%s' "$input" | grep -q '"command"[[:space:]]*:[[:space:]]*"[^"]*git commit' || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# Precise command extraction now that the cheap raw-stdin check passed.
cmd=$(printf '%s' "$input" \
      | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1)
printf '%s' "$cmd" | grep -q 'git commit' || exit 0

idx=".forge/map/index.md"
[ -f "$idx" ] || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

changed=$(git diff --cached --name-only 2>/dev/null)
[ -z "$changed" ] && changed=$(git diff --name-only 2>/dev/null)
[ -z "$changed" ] && exit 0

# Path/name tokens actually present in index.md, extracted once. A changed
# file is only "referenced" when it appears as one of these whole tokens
# (e.g. a backtick-wrapped path or bare filename) - not merely as a raw
# substring of some unrelated token. Otherwise a changed file like
# `utils.py` would false-match an index line mentioning `old_utils.py`
# (since "utils.py" is a substring of "old_utils.py"), firing a spurious
# nudge that claims index.md documents a file it never actually mentions.
idx_tokens=$(grep -oE '[A-Za-z0-9_./+@~-]+' "$idx" 2>/dev/null)

stale=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if printf '%s\n' "$idx_tokens" | grep -qxF -- "$f" 2>/dev/null; then
    stale="$stale $f"
  fi
done <<EOF
$changed
EOF

[ -z "$stale" ] && exit 0
msg="Forge: map index.md references changed file(s):$stale - consider /forge:map after commit."
msg=$(printf '%s' "$msg" | tr -d '"\\')
printf '{"systemMessage":"%s"}\n' "$msg"
exit 0
