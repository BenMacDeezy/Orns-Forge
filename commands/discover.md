---
description: Define a project charter — vision, users, stack, roadmap — before building features
argument-hint: "[project description]"
---

Invoke the `forge:discover` skill and run the discovery interview.

- If $ARGUMENTS is given, use it to pre-seed the first question ("what are
  you building and what problem does it solve") instead of asking it cold —
  confirm/refine it with the user rather than skipping it.
- Lean core interview first (~5 questions, one at a time), branching deeper
  only where complexity signals (multiple user types, integrations,
  scale/perf, regulatory/security, novel architecture) warrant it.
- If the repo already has code or a map, offer existing-repo mode: draft the
  charter by reverse-engineering `.forge/map/` + README + code, then walk the
  user through confirming each section.
- If `.forge/project.md` already exists, do NOT clobber it — show it and
  offer to update or append a revision instead.
- Draft `.forge/project.md` from the template, then gate on human approval
  before it becomes the project's source of truth.
- Once approved: write stack/architecture decisions to project memory (via
  `forge:memory`), tighten `.forge/constitution.md` by appending rules for
  stated constraints (never removing seed rules, never clobbering an edited
  constitution), and do NOT auto-queue anything.
- Reply with: charter path, status, and — once approved — recommend
  `/forge:spec "<milestone 1>"` as the next step.
