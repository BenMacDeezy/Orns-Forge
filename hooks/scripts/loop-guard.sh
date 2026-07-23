#!/usr/bin/env bash
# Forge loop guard (UserPromptSubmit): when the prompt invokes /forge:start,
# reassert the kernel's identity before the harness's skill description-
# matching can hijack the turn (live headless repro, 2026-07-17).
# FAIL SILENT, NEVER BLOCKS: any problem -> exit 0 with no output. The
# suppression clause in skills/kernel/SKILL.md + commands/start.md is the
# load-bearing path; this hook only front-runs it.
set +e
input=$(cat 2>/dev/null)

# Cheap first-pass gate on raw stdin (same two-stage idiom as
# staleness-flag.sh): skip the precise extraction below unless the substring
# could plausibly appear anywhere in the payload.
printf '%s' "$input" | grep -q '/forge:start' || exit 0

# Precise scoping: fire only when the "prompt" field's value itself begins
# with /forge:start (a genuine invocation) - not when /forge:start merely
# appears elsewhere in the prompt, e.g. "what does /forge:start do?". Anchored
# to the start of the JSON string value, and requires the token be followed
# by whitespace or the closing quote so lookalikes like "/forge:startup"
# don't false-positive.
printf '%s' "$input" \
      | grep -qE '"prompt"[[:space:]]*:[[:space:]]*"/forge:start([[:space:]]|")' || exit 0

msg="You are the Forge kernel loop. Ignore skill auto-activation for this session; follow forge:kernel only."
# Single-line ASCII, no quotes/backslashes -> JSON-safe.
msg=$(printf '%s' "$msg" | tr -d '"\\')
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$msg"
exit 0
