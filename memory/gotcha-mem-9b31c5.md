---
name: mem-9b31c5
type: gotcha
description: Claude Code Stop hooks fire at EVERY turn end, not once per session — a session idling between background-worker notifications stops many times, so any nudging/side-effectful Stop hook must debounce (marker file keyed by the stdin JSON session_id) (2026-07-18)
created: 2026-07-18T09:30:00Z
updated: 2026-07-18T09:30:00Z
agents: [forge-worker]
superseded-by: null
schema-version: 1
---

The Stop hook event fires whenever the assistant finishes a turn — including
every stop of a session that is merely idling between background-subagent
notifications. Forge's session-end LEARN reminder, written as if Stop meant
"session over", nagged identically on five consecutive stops of one working
session before this was caught (user pasted the transcript). Worse than
noise: injected Stop-hook context WAKES the agent for a fresh turn, so an
undebounced nudge burns a turn's tokens per fire; the affected kernel spent
those turns re-checking an advancing worker it would have been notified
about anyway. And a mid-wave Forge tree is dirty BY DESIGN (INTEGRATE
commits only after judges pass), so "uncommitted changes present" is
guaranteed true for the whole run — a precondition that can never go false
mid-session must not gate a per-stop message.

Rules: (1) treat Stop as "turn ended", never "session ended" — there is no
true session-end event a hook can rely on; (2) any Stop hook that emits a
user-visible nudge or performs a side effect must debounce itself: read the
hook's stdin JSON, extract `session_id`, and keep a marker file
(`${TMPDIR:-/tmp}/<plugin>-<purpose>-<session_id>`) so the behavior runs
once per session; fall back to a repo+day key when `session_id` is absent;
(3) say so in the message ("nudging once; will stay quiet") so a reader
knows silence later is deliberate, not broken; (4) this composes with the
fail-silent hook contract — the marker write itself must never error the
hook.
