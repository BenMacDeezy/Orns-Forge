---
name: mem-c3d871
type: gotcha
description: "adapted, never verbatim" tasks reliably produce lightly-reworded lifts — verify by fetching the live upstream and diffing phrasings (2026-07-18 sweep-3)
created: 2026-07-18T02:30:00Z
updated: 2026-07-18T02:30:00Z
agents: [forge-verifier, forge-worker]
superseded-by: null
schema-version: 1
---

When a task says "adapt and cite, never verbatim", workers reliably ship
lightly-reworded copies anyway: synonym swaps and re-punctuation of the
source's distinctive phrasing, list order, and coined terms. In the
2026-07-18 sweep-3 wave, 4 such passages shipped in one skill and survived
the worker's own self-check; the verifier caught them only by FETCHING the
live upstream sources and diffing phrase-by-phrase — trusting the worker's
"adapted, not copied" claim would have passed them.

Rules: (1) verifiers of cited-adaptation work must pull the actual upstream
text and compare, never accept the claim; (2) the tell is a shared
distinctive 5+ word run, a preserved list order, or a coined phrase; (3) the
bounce fix is genuine re-derivation (different sentence shape, different
example, own imagery), not another synonym pass; (4) when pinning rewritten
passages in regression tests, pin the stable IDs, never the rewritten prose
— exact-prose pins would re-verbatim-lock the text against future rewrites.
