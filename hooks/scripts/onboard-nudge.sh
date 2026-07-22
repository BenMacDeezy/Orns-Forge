#!/usr/bin/env bash
# Forge onboard-offer nudge hook (onboard-offer-nudge, 2026-07-20):
# SessionStart, fail-silent, advisory-only offer to run /forge:onboard when
# the CURRENT project is a substantial dev repo with no .forge/ yet.
#
# Origin: a fresh project (no .forge/) ran an entire PRD/court/plan cycle on
# another workstation without the CLAUDE.md "offer /forge:onboard once when
# substantial dev work begins" clause ever firing -- a loud competing
# SessionStart hook outweighed the quiet judgment-based instruction. This
# hook makes the offer mechanical instead: cheap, deterministic, and
# impossible to drown out (docs/conventions/dispatch-and-routing.md,
# "Onboard-offer nudge hook -- 2026-07-20").
#
# FAIL SILENT, NON-LOAD-BEARING, matching every other Forge SessionStart
# hook's doctrine (see hooks/hooks.json's top-level description): any
# problem/uncertainty along the way -> exit 0 with NO stdout. No network,
# target <200ms wall clock -- every step below is local git/filesystem work
# only.
#
# NEVER writes into the target repo. The nudge's entire behavior is
# printing one advisory line; the only file this script ever writes is its
# own dedupe marker, which lives OUTSIDE the repo in machine-local temp
# state (mirrors tools/update_check.py's _cache_path() convention) --
# never inside the target repo's working tree, since that repo by
# definition has no .forge/ to write into here.
set +e

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# Already onboarded -> nothing to offer.
[ -d .forge ] && exit 0

# --- dedupe check FIRST: once per project-path+day, ZERO git calls ---------
# The marker EXISTENCE check runs before every git subprocess and the
# heuristic scan, and is keyed on the project directory ($PWD after the cd
# above) rather than the git toplevel — deriving the toplevel needs two
# `git rev-parse` calls the 2026-07-20 grouped re-verify measured at ~100ms
# each on this platform, which kept the "fast" deduped path at ~236ms vs
# the ~60ms .forge-present benchmark. SessionStart hooks run with cwd = the
# project root, so the project-dir key is stable per project+day (a moved
# project re-earns one nudge at its new path, which is correct). The marker
# is only WRITTEN further down, after the heuristic actually fires — a repo
# that isn't substantial yet today stays unmarked and can still earn the
# nudge later the same day.
# FORGE_ONBOARD_NUDGE_STATE_DIR is an injectable override (tests point this
# at a scratch tempdir instead of touching real machine temp state).
state_base="${FORGE_ONBOARD_NUDGE_STATE_DIR:-${TMPDIR:-${TEMP:-${TMP:-/tmp}}}/forge-onboard-nudge-state}"
# Pure-bash slug + date: the deduped fast path must fork NOTHING — the
# round-3 re-verify measured each external fork (tr, date, git) at
# 45-105ms on this platform, so the path uses parameter substitution and
# printf's %(...)T builtin instead. Same per-character transformation the
# old `tr -c` produced, so existing marker keys stay valid.
slug="${PWD//[^A-Za-z0-9._-]/_}"
today=
TZ=UTC printf -v today '%(%Y-%m-%d)T' -1 2>/dev/null
# bash <4.2 (e.g. macOS's default 3.2) lacks %(...)T — fall back to one
# date fork there rather than losing the nudge entirely.
[ -z "$today" ] && today=$(date -u +%Y-%m-%d 2>/dev/null)
[ -z "$today" ] && exit 0
marker="$state_base/${slug}.${today}"
[ -e "$marker" ] && exit 0

# Not a git repo at all -> not a dev repo by this heuristic's definition.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
repo_top=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$repo_top" ] && exit 0

# --- heuristic: substantial source content --------------------------------
# A recognized project manifest at repo root, OR >=10 tracked files with a
# common source-code extension (deliberately extension-filtered: a repo
# with ten tracked docs/images/license files is not "substantial source").
manifest=0
for f in package.json pyproject.toml Cargo.toml go.mod; do
  if [ -f "$repo_top/$f" ]; then
    manifest=1
    break
  fi
done
if [ "$manifest" -eq 0 ]; then
  for f in "$repo_top"/*.sln; do
    [ -f "$f" ] && manifest=1 && break
  done
fi

substantial=0
if [ "$manifest" -eq 1 ]; then
  substantial=1
else
  count=$(cd "$repo_top" && git ls-files 2>/dev/null \
    | grep -icE '\.(c|cc|cpp|cs|cxx|go|h|hpp|java|jsx|kt|lua|m|mjs|mm|php|py|rb|rs|scala|sh|swift|ts|tsx)$')
  if [ -n "$count" ] && [ "$count" -ge 10 ] 2>/dev/null; then
    substantial=1
  fi
fi
[ "$substantial" -eq 1 ] || exit 0

# --- opt-out Feature (onboard-nudge: on by default) ------------------------
# Read from the PLUGIN's OWN forge.md, never the target project's (which by
# definition has no .forge/ here) -- same regex shape orn-motd.sh's
# hook_mode() uses for `startup-banner`, applied to this hook's global
# on/off switch instead of a per-target-project one.
plugin_forge_md="${CLAUDE_PLUGIN_ROOT:-}/.forge/forge.md"
if [ -f "$plugin_forge_md" ]; then
  if grep -qiE '^[[:space:]]*-?[[:space:]]*onboard-nudge:[[:space:]]*off[[:space:]]*$' \
       "$plugin_forge_md" 2>/dev/null; then
    exit 0
  fi
fi

# --- dedupe marker write: machine-local, outside the repo ------------------
# (Existence was already checked above, before the heuristic scan.)
mkdir -p "$state_base" 2>/dev/null || exit 0
: > "$marker" 2>/dev/null || exit 0

msg="Örn: this repo has no .forge/ — Forge is installed; run /forge:onboard to use its queue/spec/verification machinery here, or ignore this."
# Single-line, JSON-safe (strip quotes/backslashes, matching every sibling
# hook's own systemMessage/additionalContext sanitation).
msg=$(printf '%s' "$msg" | tr -d '"\\')
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
exit 0
