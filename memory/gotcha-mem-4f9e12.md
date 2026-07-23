---
name: mem-4f9e12
description: a regression test must go red when its fix is reverted — two vacuous tests passed with fixes removed (2026-07-17); prove revert-red before trusting a pin
type: gotcha
created: 2026-07-18T00:40:20Z
updated: 2026-07-18T00:40:20Z
superseded-by: null
schema-version: 1
agents:
  - forge-test-writer
  - forge-verifier
---

A regression test that passes with its fix reverted pins nothing. Two cases
in one day (2026-07-17): a grep -- guard test whose probe filename GNU grep
happily option-absorbed either way, and a symlink-guard test that skipped on
the dev platform (false green on the only platform where the threat lived).
Discipline: before trusting a pin, revert the fix (mentally or in a temp
copy) and confirm the test fails; where platform skips are unavoidable, add
an always-runs source-level companion assertion. Bash detail that caused one
of these: `-f` dereferences symlinks — refusing symlinks needs `-L`.
