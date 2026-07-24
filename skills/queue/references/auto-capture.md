# Auto-capture (reference)

Loaded by `skills/queue/SKILL.md` only when forge.md's Features set
`auto-queue-capture: on` (the default) AND the user describes a concrete,
task-shaped piece of work in conversation. NORMATIVE — moved verbatim from
the queue skill, not summarized. Conversational-aside handling never fires
inside a `/forge:start` kernel-loop session (which processes queue tasks,
not free-form chat), so this file is not read there; when the toggle is
`off`, it is never read at all.

## Auto-capture (Features: auto-queue-capture)

When forge.md's Features set `auto-queue-capture: on` and the user describes a
concrete, task-shaped piece of work in conversation WITHOUT asking for
immediate execution ("we should really dedupe those imports someday"), OFFER
to capture it: one structured question (`AskUserQuestion` per
`docs/conventions.md`, "Asking the user questions") proposing the drafted
title, a `ready`/`backlog` placement, and a suggested tier — accept / edit /
skip. Never silently create tasks from conversation, and make at most ONE
offer per idea — a declined offer is not re-raised. Vague musings that aren't
task-shaped get no offer.
