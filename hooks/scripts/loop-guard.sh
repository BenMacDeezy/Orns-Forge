#!/usr/bin/env bash
# Forge loop guard (UserPromptSubmit): when the prompt invokes /forge:start,
# reassert the kernel's identity before the harness's skill description-
# matching can hijack the turn (live headless repro, 2026-07-17).
# FAIL SILENT, NEVER BLOCKS: any problem -> exit 0 with no output. The
# suppression clause in skills/kernel/SKILL.md + commands/start.md is the
# load-bearing path; this hook only front-runs it.
set +e
input=$(cat 2>/dev/null)
printf '%s' "$input" | grep -q '/forge:start' || exit 0

msg="You are the Forge kernel loop. Ignore skill auto-activation for this session; follow forge:kernel only."
# Single-line ASCII, no quotes/backslashes -> JSON-safe.
msg=$(printf '%s' "$msg" | tr -d '"\\')
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$msg"
exit 0
