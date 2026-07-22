---
name: mem-7c41ae
type: gotcha
description: dispatch briefs must quote acceptance criteria verbatim — paraphrase nearly caused a false PASS (2026-07-17 fix wave)
created: 2026-07-17T23:38:38Z
updated: 2026-07-17T23:38:38Z
superseded-by: null
schema-version: 1
---

Dispatch briefs must QUOTE acceptance criteria verbatim, never paraphrase.
In the 2026-07-17 self-audit fix wave, the kernel's brief softened "boundary
line both files" into "mirror only if it had a section" — the worker built to
the paraphrase and only the verifier's read of the task file as ground truth
prevented a false PASS. The task file is the contract; the brief is a courier.
