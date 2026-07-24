# Sensitive-domain classifier — pre-dispatch primary control + post-return backstop (reference)

NORMATIVE. Implements `docs/specs/2026-07-22-phase2-external-workers.md`,
"Fail-closed pre-dispatch classifier + post-return rejection backstop
(C2 correction, N2)", for decomposition item
`bm-pre-dispatch-classifier-post-return-backstop`. **Naming note
(reconciled 2026-07-22 by `bm-atomic-doc-fix-canonical-route`):** the
canonical live queue task carrying this scope is
`bm-sensitive-classifier-backstop` (`.forge/queue/tasks/
bm-sensitive-classifier-backstop.md`). The spec's original decomposition
list used the pre-rename id
`bm-pre-dispatch-classifier-post-return-backstop`;
`skills/kernel/references/provider-judges.md` section 7.1's citation has
now been updated to the canonical id. Both spellings name the same task
and both resolve to this file. This file is the mechanics doc reached from
`skills/kernel/SKILL.md`'s ROUTE provider-routing stub via
`provider-judges.md` §7.1 (chain step 2 classification) and §8/§8.5
(post-return backstop-rejection check) — SKILL.md is at its own capacity
ceiling and carries citation-only stubs; this file carries the full prose.

## 1. Scope and citation boundary

This file builds ONLY the two controls the spec section above defines:
section 2 below (the PRE-dispatch classifier, PRIMARY) and section 3 below
(the post-return rejection backstop). It does not restate, and a reader
should go elsewhere for:

- **The trigger-domain data itself** (the seven forge-security trigger
  domains, their ids, labels, and regex patterns) — canonical source is
  `tools/route_table.py`'s `trigger_domains()` accessor, matching the same
  list `docs/conventions/verification.md`'s "Aegis (security): named
  trigger only" panel-policy section already names for a different
  purpose (spawning `forge-security`). Read that module and that section;
  this file never re-types the seven domains or their patterns.
- **The five-step precedence chain's order** — canonical source is
  `tools/route_table.py`'s `precedence_chain()` accessor. This file's
  classifier is chain step 2's decision function; it does not restate
  step order, step 1's override mechanics, step 3's provider gates, or
  steps 4/5.
- **The un-forgeable authorization envelope** that lets an authenticated
  human cross the sensitive-domain carve-out at chain step 1 —
  `bm-sensitive-override-provenance`'s scope, cited not built here. This
  file's classifier and backstop never grant that crossing; they are the
  control the crossing is an exception TO.
- **Worktree/diff handling mechanics** — `skills/kernel/references/
  parallel-dispatch.md`, cited for how a worktree diff is materialized
  and inspected; this file states WHEN a diff must be rejected, not HOW
  a diff is technically read.
- **The `codex exec` dispatch shape itself** — `provider-judges.md`
  section 7.3, cited for the exact CLI invocation this file's section 3.1
  reasons about.

## 2. PRIMARY control — fail-closed PRE-dispatch classifier

### 2.1 Classifier inputs (concrete, exhaustive — no others)

WHEN the kernel's ROUTE step classifies a task against the forge-security
trigger domains, BEFORE any dispatch decision is made, THE SYSTEM SHALL
classify the task from these CONCRETE inputs, and no others:

- the task's title and description text;
- its full `## Acceptance criteria` text;
- its `## Execution plan` text, specifically any referenced file paths or
  glob patterns named there;
- any named dependency the task's scope introduces.

No other field, file, or inference source feeds the classifier — not the
task's Attempt log, not its Routing record, not the diff a prior attempt
produced, not free reasoning about what the task "probably also touches."
An input outside this list is never grounds to classify a task either way.

### 2.2 Matching mechanics against `route_table.py`'s trigger domains

THE SYSTEM SHALL match each input in section 2.1 against every trigger
domain `tools/route_table.py`'s `trigger_domains()` returns, in the
following two distinct ways depending on that domain's `pattern` field:

- **Regex-pattern domains (six of the seven).** Where a domain's
  `pattern` is a non-`None` string, THE SYSTEM SHALL treat that pattern as
  a case-insensitive substring/alternation match against the input text —
  a hit anywhere in title/description, Acceptance-criteria text, or
  Execution-plan paths/globs counts as that domain matched. This is a
  plausibility test, not a precision one: section 2.3's fail-closed
  default exists precisely because this match is loose by design.
- **The `new-dependency` domain (`pattern: None`, by design, not an
  omission).** THE SYSTEM SHALL NOT run this domain through the regex
  path at all — `tools/route_table.py`'s own docstring states its pattern
  is `None` because it is "matched by NAME (a new package/dependency
  name appearing among the task's named dependencies)." Concretely: THE
  SYSTEM SHALL treat this domain as matched whenever section 2.1's
  "named dependency" input names a package/library the task's scope
  introduces that the codebase does not already depend on — a name
  comparison against the task's current dependency manifest, never a
  regex applied to prose. A task naming no new dependency never matches
  this one domain on that input; a task naming one does, unconditionally,
  regardless of what the name itself is.

### 2.3 Fail-closed default — ambiguous → sensitive (hard rule)

WHEN a task PLAUSIBLY touches any trigger domain per section 2.2 — a
match found anywhere, even loosely or partially, in any section-2.1
input — THE SYSTEM SHALL classify the task sensitive-domain and it NEVER
dispatches externally: Claude builds it, full stop, with no external
attempt made at all.

WHEN classification is AMBIGUOUS — the section-2.1 inputs are incomplete,
vague, or a trigger-domain match is plausible but not certain — THE
SYSTEM SHALL default to sensitive-domain (Claude builds). This is the
hard rule this file exists to state plainly: **when in doubt, Claude.**
The false-negative control is structural, not a matter of classifier
confidence tuning: an ambiguous or under-specified task is NEVER the case
that gets externally dispatched by default; only a task the classifier is
confident is ordinary is. This sensitive-domain classification is chain
step 2 (`tools/route_table.py`'s `precedence_chain()`) — it outranks
chain step 4's automatic `role-worker` default and is checked before it,
per `provider-judges.md` section 7.1's own statement of that ordering
(cited here, not restated).

### 2.4 Known limitation — the classifier is LEXICAL, not semantic (2026-07-22, bm-atomic-doc-fix-canonical-route)

The section-2.2 matcher keys on the trigger-domain patterns in
`route_table.TRIGGER_DOMAINS` — it is a lexical/pattern control, not a
semantic understanding of what the task does. A task can be genuinely
security-sensitive while its title, AC text, exec-plan paths, and named
deps carry NONE of the trigger patterns. The worked example: a task
titled "Scope record queries by tenant" with AC "cross-tenant records
must never be returned", editing an ordinary existing source file, adding
no dependency — a tenant-isolation / IDOR concern that touches none of the
seven named trigger domains lexically. The classifier can confidently
call it ordinary, and the section-3 backstop is not guaranteed to catch
it either, because the backstop also fires on named trigger domains
appearing in the returned diff.

This blind spot is NOT closed by tuning the classifier or adding more
keywords — a lexical control cannot enumerate every semantically-sensitive
shape. The mitigation is operator-driven and MUST be documented for the
human: **when you queue a task you know is security-sensitive but whose
text carries no obvious trigger keyword, hand-flag it with
`provider: claude-only`** (the per-task override, `validate_task.py`),
which forces a Claude builder via chain step 1 regardless of what the
classifier decides. Treat the automatic classifier as a floor that
catches the obvious cases, not a ceiling that catches all of them.

## 3. BACKSTOP control — post-return rejection, never a mid-build stop

### 3.1 Honest limitation — external dispatch is one uninterruptible CLI call

THE SYSTEM SHALL treat section 2 as the PRIMARY control and this section
as exactly that — a backstop for a classification section 2 MISSED, never
a substitute for it, never a claim that dispatch can be interrupted once
started.

Stated plainly, because the guarantee below depends on this being true: an
external-provider dispatch (`provider-judges.md` section 7.3's `codex exec
--json -o <output-file> ... --sandbox workspace-write --ask-for-approval
never "<worker prompt>"`) is a single CLI invocation that runs to
completion and writes its output file before Forge's kernel gets control
back. There is no mid-flight inspection point at which Forge could
interrupt it, and nothing in this file or the spec it implements claims
one exists. An external provider MAY fully PROCESS a misclassified
sensitive task end to end — this file's control activates only once that
CLI call has already returned.

### 3.2 Reject / discard / rebuild

WHEN an external-provider dispatch RETURNS — the CLI call has already
completed and its output/diff is now available for inspection — AND that
diff reveals the task touched a sensitive trigger domain section 2 did
not catch at dispatch time, THE SYSTEM SHALL:

1. REJECT the entire external diff outright — discarded, never partially
   kept, never integrated in any form, regardless of how much of the diff
   is unrelated to the missed trigger domain;
2. REBUILD the task from scratch on a Claude `forge-worker` — codex's
   output for that task is never shipped, in whole or in part.

There is no partial-acceptance path: a diff that is 90% ordinary work and
10% sensitive-domain work is rejected in full, exactly as a diff that is
entirely sensitive-domain work would be. The backstop's unit of decision
is the whole diff, never a hunk, a file, or a line.

### 3.3 Attempt log recording

THE SYSTEM SHALL record a distinct `post-return-rejection` note in the
task's Attempt log stating which trigger domain the diff revealed and
that section 2's classifier missed it at dispatch time. This note feeds
the classifier's own future tuning through the kernel's existing LEARN
step (`skills/kernel/SKILL.md`, section 8) and its memory/spec-delta
routing — cited here, not rebuilt: this file does not define a new
learning mechanism, it only states that a `post-return-rejection` note is
the trigger LEARN consumes.

### 3.4 What this explicitly does NOT claim

THE SYSTEM SHALL NOT claim, in this file or in any doc citing it, that a
worker is halted before completing a sensitive portion of its work, that
dispatch is interrupted mid-flight, or that Forge inspects a provider's
output before the provider's own CLI call returns. This is a strictly
weaker, honestly-stated guarantee than an "immediate mid-build halt" would
be — C2's review of the spec's first revision flagged that stronger claim
as unbuildable (a single `codex exec` invocation has no mid-flight
inspection point Forge could interrupt at), and this file's control is
the two-part replacement the spec adopted instead: section 2's PRE-dispatch
classifier as the actual line of defense, section 3's post-return
reject/discard/rebuild as what catches what section 2 missed, never a
claim of catching it sooner than the CLI call's own return.

## 4. Citation stubs for consumers

The classification and backstop mechanics here are reached from
`skills/kernel/SKILL.md`'s ROUTE provider-routing stub through
`provider-judges.md` §7.1 (chain step 2 classification, section 2 above)
and §8/§8.5 (backstop-rejection check once an external dispatch's diff is
available, section 3 above). SKILL.md is at its line budget and does not
restate this prose — this file is the complete mechanics that citation
chain points to.
