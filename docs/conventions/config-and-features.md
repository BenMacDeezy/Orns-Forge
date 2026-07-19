# Config and features

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## forge.md (project config)

> Amended by: "Budget keys — amendment (2026-07-17)", "UI+motion task splitting, empty-repo gates-pending, and finder dispatch — 2026-07-18"

```markdown
# Forge config

## Routing overrides
<!-- optional lines: "<pattern or area>: <model>/<effort> — <reason>" -->
(none)

## Budgets
- session-token-cap: none
- max-tasks-per-session: none

## Queue
- claim-staleness-hours: 2

## Gates
- build: (auto-detect)
- test: (auto-detect)
- lint: (auto-detect)
```

Values under Gates may be exact shell commands; `(auto-detect)` tells the kernel to infer from the repo (package.json scripts, Makefile, etc.) and write what it found back into this file.

**Malformed forge.md.** If `.forge/forge.md` exists but cannot be parsed (missing `## Gates` section, unreadable values, truncated file), the kernel does not proceed with undefined gates: it re-infers gates from the repo exactly as it would for `(auto-detect)`, writes the recovered file back, and notes the recovery in the session report. If gates cannot be inferred either (no recognizable build/test tooling), the kernel halts before dispatching any task and reports a clear message asking a human to fill in `.forge/forge.md` manually.

## Asking the user questions (interactive skills)

Any Forge skill that stops to ask the user a decision — `discover`, `onboard`,
the `spec` pipeline's clarifications and approval, and any gated offer — must
**prefer the structured question tool** (Claude Code's `AskUserQuestion`, which
renders selectable option cards, supports a recommended default, allows
multi-select, and always adds an automatic "Other" for free input) over a
free-form prose question **whenever the answer is one of a small, enumerable
set of choices.** Use the structured format for:

- yes/no or recommended-default **gates** — "Run project discovery now?",
  "Approve this draft?", "Install this from the scout shortlist?";
- picking among **known alternatives** — stack/framework choices, an
  architecture pattern, a task's `tier` or `priority`, which milestone to spec
  next;
- any `[NEEDS CLARIFICATION]` whose resolution is effectively multiple-choice
  (offer the candidate answers as options).

Rules for structured questions:

- **Recommendation first.** Where the skill has a recommended answer, make it
  the first option and label it `(recommended)`.
- **One decision per question.** Keep each question to a single decision; you
  may batch a few genuinely related decisions into one `AskUserQuestion` call
  (each as its own question) rather than a long back-and-forth, but never
  merge unrelated decisions into one option list.
- **Don't force-fit open prompts.** Reserve free-text prose questions (asked
  one at a time) for **genuinely open-ended** prompts where enumerating options
  would be artificial — e.g. discovery's "What are you building, and what
  problem does it solve?" or "Who is it for?". For those, ask in prose; do not
  invent throwaway options just to use the tool.

Availability: the structured tool exists when a skill runs **interactively in
the main session**. In a headless/agent context where it isn't available, fall
back to prose questions with the same discipline (one decision at a time,
recommendation stated, candidate answers listed inline).

## Budget keys — amendment (2026-07-17)

Amends the forge.md example above:

- `max-tasks-per-session` is the **PRIMARY enforced cap**: the kernel counts
  dispatches per session and stops with a session report when it is reached.
  A PreToolUse hook (`budget-guard.sh`) may additionally deny dispatches past
  the cap — the one documented exception to the fail-silent-hooks doctrine;
  the kernel's own count remains the portable mechanism.
- `session-token-cap` is **advisory only**: the model may stop early on its
  own spend estimate; it is not the enforcement mechanism. Both keys remain.
- New Queue key: `max-parallel-tasks` (default 3) caps a parallel-dispatch
  batch (see Parallel dispatch, above).

## Features (forge.md)

> Amended by: "Trust boundary — specs + NL scoping amendment (2026-07-17)"

forge.md carries a `## Features` section of behavior toggles (`on`/`off`).
The config template (`skills/kernel/references/forge-config-template.md`)
holds the defaults; a forge.md written before this section existed simply has
no toggles on disk — **every missing toggle behaves as its default**, and
`/forge:settings` offers to write the section in. `/forge:settings` is the
canonical viewer/editor for all of forge.md's settings.

| Toggle | Default | Meaning |
|---|---|---|
| `natural-language-invocation` | on | Forge skills fire from plain conversation ("work through the queue", "queue this", "let's build X"). `off` = skills activate only on explicit `/forge:*` commands. |
| `continuous-loop` | on | Completing a wave re-checks the queue once for newly-ready tasks (dependencies may have resolved) and continues. `off` = the kernel processes exactly one wave per invocation, then stops with the session report. |
| `auto-queue-capture` | on | Task-shaped ideas mentioned in conversation without an execution ask are OFFERED for capture into the queue — one structured offer per idea, never a silent task creation. `off` = capture only on explicit ask. |
| `express-lane` | on | Standard-tier ideas skip the spec pipeline via one structured confirm card (`forge:spec`, "Express lane"). Never applies to `tier: full` — full-tier work always takes the spec approval gate. |
| `workflow-executor` | on | Parallel-eligible waves and full-tier ship reviews run as deterministic Workflow scripts when the harness offers the Workflow tool (`forge:kernel`, "Executor"). `off` (or tool absent) = the sequential markdown loop, identical behavior. |

**Consent rule:** `continuous-loop: on` constitutes standing human
authorization for the loop to continue pulling waves — the human granted it
by enabling the setting; the kernel still stops at `max-tasks-per-session`,
empty queue, or interrupt. No toggle ever overrides a budget cap, the spec
approval gate for full-tier work, or the trust boundary.

## Freshness convention (date-sensitive skills) — 2026-07-18

Response to `docs/audits/2026-07-18-sweep3-efficiency.md` (task fg-9c0305).
Some skills document guidance that is **ecosystem-dependent** — it describes
the current shape of a fast-moving external surface (a framework version, a
library's API, a tool's default behavior) rather than a timeless Forge
protocol rule. That guidance can go stale silently: nothing about the skill
file itself signals "this was true as of when," so a consumer has no way to
tell a freshly-verified recommendation from one nobody has re-checked in a
year.

**Which skills this applies to.** Date-sensitive skills — concretely, the
frontend/animation cluster (component/framework/tooling guidance tied to a
specific library's current API or defaults) and scout shortlists (vetted
tool/MCP/skill recommendations, which age as the ecosystem moves) — carry a
freshness stamp. Skills whose content is a Forge-internal protocol rule
(kernel, queue, spec, ship, trust boundary, etc.) are not date-sensitive in
this sense and do not require one; timeless guidance doesn't need a
re-verify clock.

**The stamp.** A date-sensitive skill carries a `last-verified: YYYY-MM`
marker — either a frontmatter field or, matching the pattern already in use
across several frontend-cluster skills, an HTML comment on the first line
after the closing frontmatter `---` and before the H1 title:

```
---
name: <skill-name>
description: ...
---

<!-- last-verified: 2026-07 -->

# <Skill title>
```

**Consumer rule.** Treat guidance carrying a `last-verified` stamp older
than **~12 months** as re-verify-before-trusting, not as ground truth to
act on unchecked — the ecosystem it describes may have moved. A skill with
no stamp at all is not implicitly exempt; it simply hasn't been brought
under this convention yet, and should be treated with the same caution as
a stale stamp until it is. Re-verifying and updating the stamp is a normal,
low-ceremony edit — bump the `YYYY-MM` to the current month once the
content has been checked against the current ecosystem state, no other
process required.

## Capability-gap audits (equip) — 2026-07

`forge:equip` (`/forge:equip`) is the project's capability-gap diff engine:
it inventories the actual capability surface (skills, agent roster +
attachments, MCP servers confirmed connected via tool-listing evidence — a
config file merely naming one is never sufficient, `skills/equip/SKILL.md`
INVENTORY (c)), and stack-relevant CLIs), diffs that against
`.forge/project.md`, the map, and backlog themes, and presents ranked
find/create/wire/skip proposals via structured option cards. Equip
**decides whether and why a gap exists; it never fills one itself** — a
FIND action hands the specific tool decision to `forge:scout` (which then
applies its own vet-every-candidate and license rules), a CREATE action
becomes a normal queued task built and verified like any other queue work,
and a WIRE action runs `/forge:seed` or surfaces a disabled MCP for the
human to enable. Equip edits no MCP/`~/.claude`/project config itself, same
hard rule as scout.

Equip is **repeatable maintenance**, not the one-time setup `forge:onboard`
performs, and it **consumes** an existing project charter rather than
interviewing for one (`forge:discover`'s job) — no charter, or an
unapproved `draft` one, routes to discover/onboard first instead of equip
inventing goals from the file tree.

**Skip-decision memory.** When a human picks SKIP on a proposed gap, equip
records it as a `decision` fact via `forge:memory` (what was skipped, why,
when) so re-runs read it back and don't re-nag on an already-decided gap —
the same idempotent-re-run discipline every other Forge audit pass follows.

