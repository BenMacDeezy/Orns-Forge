---
description: Run an adversarial five-phase document court over one spec/PRD/plan
argument-hint: "<path> [--focused \"<delta scope>\"]"
---

Run one court pass over the document at the path in `$ARGUMENTS`, optionally
narrowed by `--focused "<delta scope>"`.

- **Human-ask only.** Like `/forge:inquest`, this command itself is the
  trigger (or an accepted recommendation card's acceptance) — never a loop,
  wave, or standing-consent toggle. State the charter (target document,
  fixed-constraints source, `--focused` scope if given) before the first
  PROSECUTION spawn — same discipline as `docs/conventions.md`, "Run charter
  (2026-07-17)."
- **Read-only, judge-shaped dispatches throughout.** Every role below is a
  plain `Agent` dispatch (no new agent definition files) restricted to
  read-only tools (`Read, Grep, Glob, Bash`), the same convention
  `forge-verifier`/`forge-security` already use — nothing in this command
  edits the target document; only the human, later, applies amendments.
- **Model routing is the orchestrator's call, never this command's.** This
  command never names or defaults a model. Route per document class and
  stakes: judgment-heavy stages (PROSECUTION, DEFENSE, JUDGMENT, VERDICT)
  merit stronger tiers on high-stakes documents; CLERK is mechanical and
  routes cheap regardless of stakes; a routine, low-stakes document may run
  its judgment stages on the cheap tier too. Use the kernel's existing
  MECHANICAL/JUDGMENT vocabulary (`skills/kernel/SKILL.md`) to make that
  call, not a hardcoded model name.
- **Fixed constraints and real scale are required inputs, not assumptions.**
  If the invocation doesn't supply them, ask ONE structured question
  (`AskUserQuestion`, per `docs/conventions.md`, "Asking the user
  questions") before PROSECUTION spawns. Fixed constraints are never
  themselves on trial — every prosecutor treats them as given, not as a
  charge to bring.
- **Cost gate — fires only on the human's own ask, never automatically.**
  Same trust-boundary discipline as every other NL-gated Forge surface
  (`docs/conventions.md`, "Trust boundary — specs + NL scoping amendment"):
  if the human asks for a cost estimate before committing, state the
  agent-count estimate — `prosecutors + 1 (clerk) + charges (defense) +
  areas (judgment) + 1 (chief justice)` — and proceed only on confirmation.
  Absent that ask, this is not an automatic pre-flight step.

## The five phases

1. **PROSECUTION.** 5–9 jurisdiction-partitioned prosecutors, dispatched in
   parallel. Partition by document type (e.g. for a spec: scope, EARS
   criteria, risks/rollback, dependencies, non-goals) — ALWAYS include one
   what's-missing jurisdiction whose brief is silence itself. Each
   prosecutor gets a specific brief naming concrete failure classes to hunt,
   capped at 4–6 charges. A charge is filed only if it has all four:
   falsifiable claim, quoted-text-or-silence evidence, a concrete
   consequence scenario (no scenario = inadmissible, not filed), and a
   right-sized recommendation. In `--focused` mode, run fewer prosecutors
   scoped to the delta only — prior rulings from an earlier pass on the same
   document are off-limits for relitigation. **Prior rulings are discovered,
   not assumed**: before scoping a focused pass, the orchestrator globs
   `<target-stem>-court-*.md` in the target's directory, reads every match's
   OVERRULED RECORD and sustained-charges list, and includes both verbatim
   in each prosecutor's brief as the off-limits docket — a rule with no
   discovery step is decorative, and a prosecutor who never saw the prior
   verdict cannot honor it.
2. **CLERK.** One mechanical pass merges every prosecutor's docket, collapses
   duplicate charges into their strongest single version, and drops or
   softens nothing — routes cheap (MECHANICAL tier) regardless of the
   document's stakes.
3. **DEFENSE.** One counsel per surviving charge, honest-defense rules in
   spirit: concede charges that are valid, default uncertainty to valid (never
   argue a coin flip as innocent), cite where the document already covers
   the claim, and disproportionate-ceremony objections are allowed (a charge
   demanding more process than the document's stakes warrant can be argued
   down on those grounds alone).
4. **JUDGMENT.** One judge per jurisdiction/area, and every judge reads the
   target document THEMSELVES — never hearsay from the prosecutor or
   defense's characterization of it. Each charge is ruled sustained /
   sustained-as-modified (the judge writes the better remedy, not just a
   verdict) / overruled. Strict in both directions — a judge sustains
   nothing on rhetoric alone and overrules nothing just because the defense
   objected.
5. **VERDICT.** One chief justice synthesizes across every judge's rulings:
   an executive summary, sustained charges ordered by severity with exact
   remedies, the OVERRULED RECORD with reasons (a first-class deliverable —
   this is what prevents the same overruled charge from being relitigated
   in a future pass), and an ordered amendment plan. Save the verdict as a
   dated file next to the target document (same directory, filename
   `<target-stem>-court-<YYYY-MM-DD>.md`). **Verdict-file collision check —
   runs before the write.** If a file already exists at that exact path (a
   same-day re-trial, focused or full), a court is NEVER allowed to
   silently overwrite a prior verdict — the OVERRULED RECORD it contains is
   the anti-relitigation deliverable this command exists to preserve.
   Instead, suffix the new file `<target-stem>-court-<YYYY-MM-DD>-2.md`
   (`-3`, ... — same rename-on-collision convention as queue ids) and open
   it with a one-line pointer to the file it supersedes; the prior verdict
   is never modified or deleted.

**Amendments are never auto-applied.** The verdict is a report; actually
editing the target document is a separate, explicit human step this command
never takes on its own.

Reply with: the charter, the verdict file's path, the executive summary, and
a one-line pointer to the OVERRULED RECORD section for anti-relitigation
reference on any future pass.
