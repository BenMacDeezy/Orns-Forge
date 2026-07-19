---
name: mem-b7e3d5
type: gotcha
description: A single-observation intermittent test failure is not actionable without a captured artifact — the debugger's Iron Law (no fix without a proven root cause) ruled not-reproduced after 58 adversarial runs; the durable move is a capture protocol, not a guessed fix (2026-07-18)
created: 2026-07-18T23:00:00Z
updated: 2026-07-18T23:00:00Z
---

test_audit.py::test_raises_on_checklist_missing_hash was observed failing ONCE
inside the full suite by a docs worker, then never again: 25 warm-cache runs,
20 cold-cache runs (pycache wiped), and 13 targeted pairwise reorderings all
green. Eight pollution hypotheses were each killed with evidence (no
ground-truth writes from tests, single module copies, no import-time side
effects, test_audit collects FIRST of 878 tests so order pollution is
structurally excluded, seeded local RNGs, explicit tmp base_dirs, no
concurrent pytest, assertion path has no dict/set iteration).

**The lesson:** when a flake has exactly one observation and no artifact, do
NOT ship a speculative "isolation" fix — it would launder an unproven
hypothesis into the suite as fact. Record a capture protocol instead and move
on. Protocol for recurrence: `python -m pytest tools/ -q -v --tb=long > run.log
2>&1` + timestamp + process list, then re-dispatch the debugger WITH the
artifact. (agents: forge-debugger, forge-worker, kernel)
