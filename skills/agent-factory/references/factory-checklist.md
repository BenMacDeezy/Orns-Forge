# Agent factory checklist (gate before first use)

A generated agent must pass ALL of these or it is not written (spec §6.4):

1. **Single mission** — one job, stated in one sentence. If it needs "and", split it.
2. **Output contract defined** — a concrete structured final-message shape the
   kernel can consume as data, not prose.
3. **Forbidden actions stated** — explicit prohibitions, always including
   "never touch `.forge/`".
4. **Routing default justified** — `model / effort` with one line of reasoning
   tied to the router's complexity/risk/ambiguity scoring (spec §4.2). No
   implicit inheritance.
5. **No roster duplication** — no standing-roster agent (spec §6.2) already
   covers this job. If one does, use it instead of minting a new agent.

Record the check outcome (pass/fail per item) in the loop/session report. A fail
on any item aborts creation.
