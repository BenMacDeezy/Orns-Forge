---
description: View and edit Forge settings (forge.md Features, Budgets, Queue)
argument-hint: "[natural-language edit, e.g. \"turn off auto loops\"]"
---

Read `.forge/forge.md` at the repo root (resolve root first — `forge:queue`,
Auto-init). If `.forge/` or forge.md is missing, say so in one line and offer
to auto-init (queue skill) before continuing.

1. **Render current settings.** Show every setting with its current value,
   grouped exactly as in forge.md:
   - **Features** — every toggle (`natural-language-invocation`,
     `continuous-loop`, `auto-queue-capture`, `express-lane`,
     `workflow-executor`) with `on`/`off` and its one-line meaning (from the
     config template / `docs/conventions.md` "Features (forge.md)").
   - **Budgets** — `max-tasks-per-session`, `session-token-cap` (note which is
     the enforced primary cap vs advisory).
   - **Queue** — `claim-staleness-hours`, `max-parallel-tasks`.
   **Missing `## Features` section:** an existing forge.md written before the
   Features section existed has no toggles on disk — treat every toggle as its
   default (the config template's values, all `on`), render them marked
   `(default — not yet in forge.md)`, and offer to write the section in.

2. **Offer edits — one structured question.** Per `docs/conventions.md`
   ("Asking the user questions"), put the edit decision to the user as ONE
   `AskUserQuestion` call: batch the related decisions (which toggles to flip,
   which values to change) as individual questions in that single call —
   current value marked, e.g. "continuous-loop: on (current) / off". Include a
   "No changes" path. Never merge unrelated settings into one option list.

3. **Apply.** For each changed setting, edit `.forge/forge.md` in place —
   write only the changed lines, preserve everything else (comments, unknown
   keys, section order). If the user opted to materialize a missing
   `## Features` section, write it from the config template with their chosen
   values, placed before `## Budgets`. Confirm with a short before → after
   list, and — if the change affects how `/forge:start` behaves
   (`continuous-loop`, a budget key, `workflow-executor`) — one line naming
   that effect on the next run; otherwise nothing else.

Natural-language edits are also valid input when `natural-language-invocation`
is `on`: `$ARGUMENTS` like "turn off auto loops" maps to the matching key
(`continuous-loop: off`), confirm the interpretation in the same structured
question before writing. If `$ARGUMENTS` is empty, just do steps 1–3.
