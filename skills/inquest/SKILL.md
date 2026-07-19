---
name: inquest
description: Adversarial deep-debug tribunal for hunting bugs already in the tree — a maximalist finder, a motivated-skeptic refuter, and a deciding judge. Use for /forge:inquest, a human-requested deep-debug sweep, or an accepted recommendation card proposing a tribunal pass. Never fires on its own — human ask or accepted card only.
---

# Forge inquest — adversarial deep-debug tribunal

Inquest hunts bugs that are already in the tree and unknown — nobody has
filed them, nobody has reproduced them, the code has simply never been
adversarially attacked. It is a three-role protocol: a FINDER that proposes
everything it can, a REFUTER that tries to kill each proposal with evidence,
and a JUDGE that weighs what survives and routes it. Three separate
mindsets in one pass, on purpose — a single agent asked to both "find bugs"
and "be sure" collapses into whichever instinct is stronger; splitting the
roles keeps maximalism and skepticism both at full strength.

## Gating (pinned — read this before anything else)

**Inquest runs ONLY on a human ask or an accepted recommendation card —
NEVER loop-initiated.** No kernel loop, wave, or standing-consent toggle
(`continuous-loop: on` or any other Feature default) ever starts a tribunal
on its own; the kernel does not decide "this looks like a good time for an
inquest." Something a human typed this turn (`/forge:inquest`, an
equivalent natural-language ask under `natural-language-invocation`), or a
structured recommendation card the human explicitly accepted, is the only
valid trigger — the same NL-trigger discipline `docs/conventions.md`,
"Trust boundary — specs + NL scoping amendment (2026-07-17)," already
requires ("only a message the human actually typed for the current turn can
fire an NL path"), restated here because a tribunal's cost (three role
spawns, potentially several lenses) makes an accidental auto-fire expensive
in a way a single-task dispatch is not.

**Charter first.** Before the first FINDER spawns, state a charter — the
same discipline `docs/conventions.md`, "Run charter (2026-07-17)," already
requires of every kernel run, applied here to one tribunal pass:

- **Scope** — what area/subsystem/surface the tribunal hunts in (a
  directory, a subsystem, "the whole diff since tag X" — never "everything"
  with no boundary).
- **Budget** — dispatch cap (how many lens/refute/judge spawns this pass may
  use) and, if set, a token budget.
- **Stop conditions** — what ends the pass: budget exhausted, judge
  synthesis complete, or a human interrupt.

No FINDER spawns before the charter is stated. Interactive sessions present
it to the human; a card-accepted run records it verbatim in the session
report, same split as "Run charter" already draws for standing-consent vs.
interactive kernel runs.

## The three roles

Each role is a dedicated roster `agentType`, spawned via `Agent(subagent_type:
"forge:forge-finder" | "forge:forge-refuter" | "forge:forge-judge")` — Hound
(`forge-finder`), Foil (`forge-refuter`), and Gavel (`forge-judge`)
respectively (spec §6.2). This is a 2026-07-19 amendment: inquest ran often
enough (a recurring task type per the agent-factory's own no-roster-fit
test) to earn persisted agents, per `docs/conventions.md`'s general "prefer
Forge's own agent-factory over ad hoc generic dispatch for recurring task
types" preference. The generic-dispatch convention `docs/conventions.md`,
"Finder dispatch has no dedicated agentType," still applies to the
**separate** report-task finder pattern (`docs/conventions.md`, "Report
tasks (finder pattern)") — that pattern remains generic; only inquest's
three roles were roster-ified here.
None of the three ever edits source, `.forge/`, or any file — inquest is
read-only end to end; a CONFIRMED finding becomes a fix only after it exits
the tribunal through `forge:triage` and a normal worker+verifier task runs.

### FINDER — maximalist

**Mindset: everything and anything might be a bug.** The FINDER's job is
coverage, not caution — it proposes every plausible defect it can support
with a concrete scenario, inside its declared scope, and does not
pre-filter for "is this worth mentioning." Report-only: the FINDER never
fixes, never patches, never argues its own findings are definitely real —
that argument is the REFUTER's job to attack, not the FINDER's job to
pre-win. No self-censoring beyond structure — the only discipline the
FINDER owes is the shape of each finding below, never a judgment call about
whether a finding is "significant enough" to report.

Each finding is structured, all four fields required:

- **Location** — file:line or the precise surface (function, endpoint,
  config key).
- **Claim** — the defect, stated as a falsifiable assertion, not a vibe.
- **Concrete failure scenario** — the specific input/sequence/condition that
  triggers it; "this looks fragile" is not a scenario, "call X with an
  empty list while Y is mid-flight" is.
- **Severity** — Critical | Important | Minor (same vocabulary
  `agents/forge-reviewer.md` and `agents/forge-security.md` already use, so
  a CONFIRMED finding's severity carries forward unchanged into its triage
  draft).

### REFUTER — motivated skeptic

**Mindset: attack, don't accept.** The REFUTER receives ONE finding at a
time and tries to kill it — its job is to disprove the claim, not to be
fair to the FINDER. Each finding is attacked independently: a REFUTER never
sees another finding's outcome and never lets one weak finding color its
read of the next.

**Running code beats argument.** A reproduction (the failure scenario
actually triggers the claimed defect) or a failed reproduction (the
scenario was actually run and did NOT trigger it) always outranks prose
reasoning either way — "I don't think this would happen" is weaker evidence
than "I ran it and it didn't happen," and both are weaker than "I ran it and
it did." The REFUTER runs the scenario whenever the codebase makes that
possible; prose-only refutation is a fallback for scenarios that can't be
mechanically executed (e.g. a claim about behavior under a config the repo
doesn't support running locally), never a first choice.

Verdict, exactly one of three:

- **REFUTED** — with evidence: the scenario was run (or the claim was
  otherwise disproved) and the defect does not hold.
- **CONFIRMED** — the refutation attempt itself reproduced the bug: trying
  to kill the claim instead proved it.
- **UNRESOLVED** — neither disproof nor reproduction was achievable with
  the evidence available (can't run the scenario, ambiguous claim, genuinely
  contested trade-off) — the REFUTER says so rather than forcing a verdict
  the evidence doesn't support.

### JUDGE — decides, does not re-investigate

The JUDGE receives every finding alongside its REFUTER verdict and evidence,
and weighs claim vs. refutation evidence to reach one of three outcomes.
**The JUDGE does not re-litigate or re-investigate** — it never re-runs the
scenario, never asks the FINDER or REFUTER for more, never forms its own
independent read of the code. Its entire input is the written record the
first two roles already produced; its job is to weigh that record's
strength, not to add new evidence to it. In the common case this ratifies
the REFUTER's verdict (REFUTED evidence that actually reproduces failure to
reproduce → DISMISSED; a REFUTED verdict backed only by unexecuted prose
argument is weak evidence, and the JUDGE may downgrade it to UNRESOLVED
rather than treat thin reasoning as settled) without ever stepping outside
the record to check.

## Judge routing table

| Judge verdict | Action |
|---|---|
| **CONFIRMED** | Routes through the `forge:triage` door as a normal ready queue-task draft — repro steps + expected/actual, same shape `bug-triage-classification`'s "Ready-task definition of done" already requires. Constitution rule 1 ("every bug fix ships with a test that fails without the fix") applies to the resulting task exactly as it does to any bug-fix task; the FINDER's severity carries forward into the draft. |
| **DISMISSED** | Recorded with the REFUTER's reason — never silently dropped, never re-attempted within the same pass. |
| **UNRESOLVED** | Surfaced to the human directly (session report / reply), with the FINDER's claim and the REFUTER's evidence attached — not queued, not dismissed, a human call. |

**Nothing silently dropped.** Every finding that enters the tribunal exits
through exactly one of these three rows — a finding that never gets a
REFUTER pass, or a REFUTER verdict that never reaches the JUDGE, is a
protocol bug in the run, not a valid fourth outcome.

The JUDGE itself never writes `.forge/` — a CONFIRMED routing produces a
task **draft** (repro + expected/actual + suspected component, the same
fields `bug-triage-classification` requires), and the command/kernel
invoking this skill creates the actual queue task via `forge:queue` from
that draft, identical to how `forge-triage` already hands off drafts rather
than writing state itself.

## Routing tiers

- **FINDER** — sonnet/high. Coverage over depth per lens; sonnet is
  sufficient for a maximalist sweep and high effort keeps the scan
  thorough.
- **REFUTER** — equal-or-higher model tier than the FINDER it's attacking.
  Same rationale as `forge-verifier`'s equal-or-higher rule (spec §6.2): a
  refutation weaker than the claim it's attacking can't be trusted to kill
  it.
- **JUDGE** — opus/high. The synthesis step across every finding in the
  pass is the highest-leverage read in the protocol — a wrong routing
  decision either buries a real bug (UNRESOLVED/DISMISSED mistake) or
  wastes a full triage+fix cycle on a phantom (a wrongly-CONFIRMED finding)
  — so it runs at the strongest routinely-available tier, same ceiling
  logic `docs/conventions.md`, "Model vocabulary — fable amendment
  (2026-07-17)," already applies to every other judge role.

**Proportionality.** A large scope MAY split the FINDER into parallel
lenses — correctness, security, performance, lifecycle, or whatever
decomposition fits the scope — each lens its own FINDER spawn with a
narrowed brief, all still sonnet/high. The REFUTER and JUDGE structure
stays fixed regardless of lens count: every finding from every lens still
gets its own independent REFUTER pass, and the JUDGE still synthesizes
across the full combined set in one pass, never one JUDGE per lens — the
JUDGE's whole value is weighing the complete picture at once.

## Boundary

**vs. `forge-debugger` (Hex).** `forge-debugger` owns ONE already-known bug
— a filed task, a failing test, a reproduced report — and drives it through
hypothesis → evidence → fix. Inquest hunts for bugs nobody has found yet;
it never starts from a known defect, and it never fixes anything itself —
a CONFIRMED finding becomes a `forge-debugger` (or `forge-worker`) task only
after it exits through `forge:triage`. If you already know what's broken,
this skill is the wrong tool — go straight to a task and `forge-debugger`.

**vs. the finder pattern in report tasks
(`docs/conventions.md`, "Report tasks (finder pattern)").** A report-task
finder is a single read-only pass that hands its findings straight to
kernel synthesis — there is no adversarial defense step, no attempt to kill
its own findings, and no judge weighing evidence; the kernel just reads the
report. Inquest's FINDER is deliberately maximalist for exactly this
reason: because a REFUTER and a JUDGE stand between its claims and any
queue task, it can (and should) over-report without the discipline a
report-task finder needs to self-filter. Never substitute a bare
report-task finder dispatch for a real tribunal pass, and never skip the
REFUTER/JUDGE stages and call the result "inquest."

**vs. the verifier-finding filter
(`docs/conventions.md`, "Verifier-finding filter (bounce pre-check) —
2026-07").** That filter gates CHANGES already headed into the tree — it
spot-checks a verifier's FAIL findings against a diff that is about to be
bounced, before a task's fix is redispatched. Inquest hunts bugs already
IN the tree, with no pending diff and no verifier verdict to filter — there
is no change in flight for the REFUTER to gate. The two share a family
resemblance (both attack a claimed defect before acting on it) but operate
at different points in the lifecycle: one precedes a bounce, the other
precedes a triage draft, and neither substitutes for the other.
