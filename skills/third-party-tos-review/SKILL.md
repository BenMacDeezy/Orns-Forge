---
name: third-party-tos-review
description: Reviewing the terms of service, usage terms, or API terms of a third-party API/service/model/data source before integrating it. Use before adding a new external API, LLM/model provider, data vendor, or SaaS integration, or when asked "is this API's ToS ok", "can we use this data source", or "check the terms of service".
---

# Third-party ToS review

You review a third-party's terms and hand back a clause-cited findings table.
You quote, you never paraphrase into a stronger claim than the text supports,
and you never conclude "this is fine to sign" — that's counsel's call once
the deal has real stakes.

## 1. Fetch the current terms — record retrieval date and URL

Terms change without notice. Use WebFetch to pull the live ToS/API-terms
page (not a cached memory of "what X's terms usually say"), and record in
the output:

- the exact URL fetched,
- the retrieval date (today),
- the terms' own "last updated"/effective date if the page states one.

If the provider has separate documents (general ToS, API-specific terms,
acceptable-use policy, data-processing addendum), fetch and review each one
relevant to the integration — don't review only the general ToS and assume
it covers API-specific restrictions.

## 2. Red-flag checklist

Walk every category below against the fetched text. Skip a category only if
the terms genuinely don't address it (say so — "not addressed in reviewed
terms" is itself a finding, not silence).

- **Data-usage rights** — does the provider claim rights over data you send
  it (license grant, training-use clause)? Look explicitly for language
  letting the provider use submitted inputs/outputs to train or improve
  their models — this is the single most consequential clause for an AI/data
  integration.
- **Use-case restrictions** — "no AI training," "no competitive use," field-
  of-use limits, rate limits tied to plan tier. Confirm the intended
  integration doesn't fall inside a prohibited use case.
- **Attribution requirements** — does using the API/data/output require a
  visible credit, logo, or "powered by" notice?
- **Liability / indemnification** — does the agreement shift liability onto
  you (you indemnify the provider for claims arising from your use), or cap
  the provider's own liability in a way that matters for this integration's
  criticality?
- **Termination / change-of-terms notice** — what notice period, if any,
  applies before the provider can change terms or terminate access? A
  "terms may change at any time without notice" clause is itself a risk
  finding for anything load-bearing.
- **Data-residency / export terms** — where is data processed/stored, and
  does that intersect with any data-residency or export-control requirement
  the integrating project has?
- **Sublicensing of outputs** — who owns content the API/model generates,
  and can you sublicense or commercially use it? This is frequently
  different from who owns the input you sent.

## 3. Output framing

One row per category above:

| Category | Verdict | Clause (quoted, ≤15 words, with section ref) |
|---|---|---|

Tag each row GREEN / YELLOW / RED:

- **RED** — a restriction or liability shift that blocks or seriously
  complicates the intended use (e.g. "no AI training" clause on a dataset
  you intend to train on; unlimited indemnification for a load-bearing
  integration).
- **YELLOW** — a restriction or obligation that's manageable but must be
  tracked (attribution requirement, rate limit, notice period).
- **GREEN** — no material restriction found for the intended use.

Then an **overall verdict** line summarizing the category rows (not a new
judgment — a roll-up of the RED/YELLOW/GREEN pattern above).

## Rule — quote and cite, never inflate

Every YELLOW or RED row carries the actual clause text, quoted, capped at
roughly 15 words, with a section number or heading reference so a human can
find it in the source. Never paraphrase a clause into a claim stronger than
its literal text — e.g. a clause permitting the provider to use inputs "to
improve service quality" is not the same claim as "the provider trains
models on your data," even though the second may be a reasonable inference;
state the quote and let the inference be explicit and separate, not folded
into the quote itself.

---
This skill produces engineering-side license/compliance analysis, not legal
advice. Findings must be verified with qualified counsel before relying on
them for shipping, licensing, or contractual decisions. Cite sources for
every non-obvious judgment so a human can independently verify.

---
Adapted from: general contract-review practice for API/data-vendor terms of
service (data-usage/training-use clauses, use-case restrictions, liability
and indemnification allocation, termination-notice terms, output-ownership
and sublicensing terms).
