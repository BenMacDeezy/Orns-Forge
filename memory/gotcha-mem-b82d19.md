---
name: mem-b82d19
type: gotcha
description: parallel audit finders racing a concurrent writer yield stale findings — re-check each finding against post-integrate state
created: 2026-07-17T23:38:38Z
updated: 2026-07-17T23:38:38Z
superseded-by: null
schema-version: 1
---

Parallel audit finders racing a concurrent writer in the same tree produce
findings that may already be stale at synthesis time (a 2026-07-17 finder
flagged a gap the in-flight build had already closed). At integrate, re-check
each finding against post-integrate state before queueing fixes, and prefer
read-only finders + one writer per disjoint scope per wave.
