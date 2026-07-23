---
name: source-vetting-and-citation-discipline
description: Rigor layer for cited research briefs — primary-vs-secondary source hierarchy, checking docs against the project's actual dependency version (not just recency), contradiction resolution between credible sources, claim-level (not paragraph-level) citation, an adversarial self-check pass, and a Confirmed/Inferred/Assumed confidence rubric. Use when producing a research brief, before citing a source in an implementation guidance document, or when forge-researcher is about to finalize a brief.
---

# Source vetting and citation discipline

Complements the deep-research skill: that skill drives the search fan-out,
this one is the discipline you apply to what comes back before it goes in a
brief. A brief with three unvetted links is worse than one with one vetted
claim — false confidence costs more than an admitted gap.

## Source hierarchy (highest to lowest trust)

1. **Official docs / changelogs / source code** of the library or API in
   question — admissible as authoritative on its own for any claim about
   current behavior.
2. **Official examples / reference implementations** (maintainer repos,
   official quickstarts) — admissible alone for "how do I call this," but
   cross-check against docs for anything version-sensitive.
3. **Reputable third-party writeups** (well-known engineering blogs,
   conference talks, maintainer-adjacent authors) — admissible for design
   rationale and gotchas, never alone for "what does the API do now."
4. **Stack Overflow / forums / random blog posts** — admissible only as a
   lead to verify against tier 1–2, or when nothing higher exists and you
   label it accordingly. Never the sole citation for a load-bearing claim.

Prefer the lowest-numbered tier that actually answers the question. Don't
cite a blog post for something the official changelog states directly.

## Recency is not enough — version-match every doc claim

"Is this current" is the wrong question; "does this match what THIS project
actually depends on" is the right one. Before trusting a doc:

1. Read the project's actual pinned version (lockfile, `package.json`,
   `requirements.txt`, `go.mod`, etc.) — not the latest release, not what the
   doc assumes.
2. Check the doc's version scope: does it say "as of vX," or is it undated?
   Undated docs for fast-moving libraries are a yellow flag.
3. If the pinned version predates a breaking change the doc describes, the
   doc is wrong for this project even though it's the newest thing you found.
   Note the mismatch explicitly rather than silently applying it.

## Contradiction resolution

When two credible sources disagree, never silently pick the one that
confirms your recommendation. Instead:

1. State both claims and their sources.
2. Diagnose the likely cause: version drift (one source predates a change),
   scope mismatch (one covers a different runtime/config/edge case), or a
   genuine unresolved ambiguity upstream.
3. If diagnosable, say which applies to this project's version and why. If
   not, surface it as an open question rather than guessing.

## Claim-level citation

Cite at the level of the discrete implementation claim, not the paragraph or
the brief. Each bullet in IMPLEMENTATION GUIDANCE gets its own source
(URL + section, or `file:line` for codebase claims) — a reader should be able
to verify any single line without re-reading the whole brief. A paragraph
mixing three claims under one trailing citation is not acceptable; split it.

## Adversarial self-check (before finalizing)

Before writing the brief's ANSWER, spend one more search pass actively
looking for the strongest evidence AGAINST your top recommendation — a known
issue, a maintainer deprecation note, a "don't do this" post. If you find
real counter-evidence, fold it into PITFALLS or reconsider the
recommendation; don't finalize a brief you haven't tried to break.

## Confidence calibration

Label every finding, not just the brief overall:

- **Confirmed:** official/primary source, version-matched to this project,
  and independently corroborated by a second source or by reading the
  actual source code.
- **Inferred:** consistent with official sources but not spelled out
  verbatim — reasoned from adjacent documented behavior or source code.
- **Assumed:** no primary source found; based on a single secondary source,
  unclear recency, or pattern-matching from a different but similar case.
  Flag this loudly — it's a gap, not a finding.

## Output discipline: BLUF, never a search log

Lead with the recommended decision, then the evidence, then open questions.
Never narrate the search process ("I looked at X, then tried Y..."). This
matches forge-researcher's output contract: `ANSWER (brief)` comes before
`IMPLEMENTATION GUIDANCE`, and every guidance line carries its own
`confidence <high|med|low>` tag plus source — high only when the claim is
Confirmed by this rubric.

---
Adapted from: general research-integrity practice (source hierarchy,
claim-level citation, contradiction handling, adversarial self-check,
confidence calibration). Complements the built-in deep-research skill, which
this skill assumes runs first for search fan-out and initial synthesis.
