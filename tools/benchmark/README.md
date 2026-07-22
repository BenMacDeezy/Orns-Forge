# A/B benchmark: full Forge protocol vs single-agent baseline

## 1. What this is, and why it exists

This is the harness for the A/B experiment commissioned by
`docs/audits/2026-07-18-protocol-overhead-audit.md` (fg-a10209) and designed
in `docs/plans/2026-07-18-ab-benchmark-design.md` (fg-a10210, cited
throughout this README by decision number — D1–D8 — and task number — T1–T9
— never restated). It runs the same task brief through two arms on
identical starting trees — **arm A**: the full Forge kernel loop (route,
dispatch, verify, ship judges, bounce-and-reverify); **arm B**: a single
agent given the same brief and the same closing gate command, with no
adversarial verifier, no ship judge, and no bounce (D3) — then has a
blinded auditor score both arms' final diffs against a checklist frozen
before either arm ran (D5), and reports raw per-arm-run metrics (D6) under
pre-registered decision rules (D7).

**Why.** `docs/conventions.md`, "Verification economics — 2026-07-18
(fg-a10901)" is the NORMATIVE policy this experiment feeds: verification
pays only where it buys verdict independence or catches real risk, and that
section's panel-policy tightening was ratified from forensic reads of live
sessions, not from a controlled measurement. This benchmark is the one task
in the queue that replaces estimate with measurement (fg-a10209 recommendation
3) — its output is routing evidence for that judge-yield-driven policy, not
a replacement for it. A routing conclusion from this benchmark only ever
reaches the runtime protocol as an UNRATIFIED delta filed to
`docs/specs/2026-07-16-forge-design.md` §17 Changelog (same channel the
telemetry-driven recommendations already use) — never a self-applied change.

## 2. The repeatable recipe

Run this at every future protocol change to re-measure the cost/defect
delta under the new protocol shape. Every step below cites the design
section that governs it; do not re-derive the *why*, only follow the *how*.

### Step 0 — fixture baseline check (before touching anything else)

Confirm the fixture is still green at its pinned base, with no `.forge/`
leakage into it (T1's own acceptance criterion):

```
pytest tools/benchmark/fixture -q      # must be all-green (49 tests today)
ruff check tools/benchmark/fixture     # must be clean
```

`tools/benchmark/conftest.py`'s `pytest_ignore_collect` hook keeps this
suite invisible to the repo-wide `python -m pytest tools/ -q` gate (it is
allowed its own non-planted latent bugs, D1) while still collecting
normally when `tools/benchmark/fixture` is named explicitly, as above.
`mypy` is named in D1 as a third fixture gate but is not wired into
`tools/benchmark/fixture/pyproject.toml` or `requirements.txt` yet — see
§3, "mypy gate caveat."

### Step 1 — freeze check (checklist hashes)

Before any arm runs, confirm every checklist under
`tools/benchmark/ground-truth/checklists/*.checklist.json` still matches
its own recorded `content_sha256` and its entry in
`tools/benchmark/ground-truth/task-key.json`:

```python
from audit import checklist_content_hash
# for each checklist dict loaded from disk:
assert checklist_content_hash(checklist) == checklist["content_sha256"]
```

`audit.verify_checklist_integrity()` performs this exact check (and is
called automatically by `build_audit_packet` in step 5 — a checklist
edited after freezing raises `AuditError` there too, loudly, per D5's
"checklist frozen at design time" mechanism). If you are *extending* the
run (adding a task, e.g. moving toward 3/class per D2's "min viable first
run = 8, 2/class" — see `task-key.json`'s `not_built_this_run` for the 4
already-scoped-but-deferred candidates), author and freeze the new
checklist per §4 before any arm sees the new task.

### Step 2 — pin a base commit

The fixture (`tools/benchmark/fixture/`, package `ledgerkit`) is **not**
its own git repository — it is a subtree of this repo. The "pinned base"
`runner.py` worktrees from (D4) is a commit SHA of this repo's own history,
taken after step 0/1 are green:

```
git rev-parse HEAD          # record this as base_sha
```

`runner.create_worktree(repo_root, base_sha, dest)` (`repo_root` = this
repo's root) runs `git worktree add --detach <dest> <base_sha>` — every
arm-run gets a fresh worktree from that one SHA (D4: "no shared state");
`runner.remove_worktree` tears it down idempotently, even after a failure.

### Step 3 — run pairs

For each entry in `tools/benchmark/tasks/manifest.json` (today: 8 tasks,
2/class — `M1`, `M2`, `F1`, `F2`, `B1`, `B3`, `DOC1`, `DOC2`; the manifest's
`class_coverage` maps each to its class), build the two arm adapters and
run the pair:

```python
from arms import make_arm_a_adapter, make_arm_b_adapter
from runner import run_pair, write_run_record
from glue import flatten_pair_record

adapters = {
    "A": make_arm_a_adapter(
        brief_path=pathlib.Path(task["brief_path"]),
        gate_command=["python", "-m", "pytest", "tests/", "-q"],  # + ruff, per task.md "Done when"
        model_tier="sonnet/high",       # the builder tier under test
        dispatch=real_dispatch,         # T8's real dispatch wiring -- see below
    ),
    "B": make_arm_b_adapter(
        brief_path=pathlib.Path(task["brief_path"]),
        gate_command=["python", "-m", "pytest", "tests/", "-q"],
        model_tier="sonnet/high",       # same builder tier as arm A (D3)
        dispatch=real_dispatch,
    ),
}
pair_record = run_pair(
    task_id=task["task_id"], repo_root=repo_root, base_sha=base_sha,
    seed=<recorded per-run seed>, adapters=adapters, work_dir=bench_work_dir,
)
write_run_record(pair_record, work_dir / f"{task['task_id']}.run.json")
run_records = flatten_pair_record(pair_record)   # -> two metrics-ready RunRecords
```

`run_pair` draws and records the seeded arm order itself (`draw_arm_order`,
D3's "arm-order randomization + recording"); both `run_arm` calls happen on
a fresh worktree regardless of order (D4). **`dispatch` is the sole
model-in-the-loop seam** (arms.py module docstring): a
`Callable[[str, Path], DispatchResult]` that both adapters call with the
*exact same* `brief_text` for every call (build, verify, bounce,
re-verify), never a varied prompt — this is what `test_symmetry.py` proves
holds for every call, not just the first. `DispatchResult.tokens` carries
real per-call usage when `fg-a10212`'s `[tokens: NNNNN]` capture is wired
into `real_dispatch`; leave it `None` (never a stand-in for zero) when it
isn't, and `metrics.compute_tokens` will fall back to the proxy regime
automatically. Writing `real_dispatch` — the part that actually spawns a
builder for arm A's `dispatch`/`bounce` calls, a `forge-verifier`-class
spawn for arm A's `verify`/`re-verify` calls, and a single agent for arm
B's one `turn` call — is T8's execution-layer job; this repo's own tests
(`test_symmetry.py`) exercise the adapters and `run_pair` only against a
recording stub, never a real model call.

### Step 4 — normalize, shuffle, seal

For each pair's two final diffs (`pair_record["arms"]["A"]["diff"]` /
`["B"]["diff"]`):

```python
from blinding import shuffle_pair, write_sealed_key

presented, sealed_key = shuffle_pair(task_id, diff_a, diff_b, seed=<same seed>)
write_sealed_key(run_id, sealed_key)   # writes tools/benchmark/sealed/<run_id>.sealed.json
```

`shuffle_pair` normalizes both diffs (`blinding.normalize_diff`, stripping
`.forge/` hunks, `fg-xxxx` ids, agent-slug/persona/Attempt-log/telemetry
vocabulary — see blinding.py's module docstring for the full scrub list),
assigns each a deterministic opaque label (`make_label`), and returns them
in a seeded-random presentation order that carries no arm identity. The
`sealed_key` return value — the only place arm identity survives this
call — must never reach the auditor; `write_sealed_key` persists it to
`blinding.SEALED_KEY_DIR` (`tools/benchmark/sealed/`), merging into any
existing file for the same `run_id` rather than clobbering earlier pairs.

### Step 5 — spawn a blinded auditor per pair

```python
from audit import build_audit_packet

packet = build_audit_packet(task_id, presented, checklist)  # checklist from step 1
```

`build_audit_packet` runs the tamper check (`verify_checklist_integrity`)
and the fingerprint tripwire (`_check_fingerprint_free`, refusing loudly on
a surviving `fg-` id or `.forge/` path) before packaging anything. Fill one
instance of `tools/benchmark/auditor-contract.md`'s template per task pair
from that packet's fields exactly — never from a live repo path, the sealed
key, or a task-record file — and spawn it as a read-only
`forge-verifier`-class agent (opus/high per the contract's own `ROUTING:`
line) per `skills/kernel/references/spawn-contract-template.md`'s
structure. The contract's own `SCOPE` deny-list is the T7 enforcement of
D5's "the auditor spawn's contract excludes that path": it denies
`tools/benchmark/sealed/**`, `tools/benchmark/ground-truth/task-key.json`,
`tools/benchmark/ground-truth/ledgerkit-defects.sealed.json`, and any
`.forge/` path. One auditor spawn per pair, never batched (auditor-contract.md,
"Notes for whoever wires T8's real spawn").

### Step 6 — record scores

Parse the auditor's prose `LABEL: ... / CHECKLIST_RESULTS: ... /
ADDITIONAL_DEFECTS: ...` blocks (the auditor-contract.md OUTPUT CONTRACT)
into structured input and record them on a per-run `BlindedScoreLedger`:

```python
from audit import BlindedScoreLedger

ledger = BlindedScoreLedger(run_id)
ledger.record_scores(label, checklist_results, additional_defects)  # once per label
```

`record_scores` structurally validates against `metrics.VALID_STATUSES` /
`metrics.VALID_SEVERITIES` and raises `AuditError` on anything malformed —
it does no prose parsing itself (auditor-contract.md's parsing note). Do
this for every labeled diff in every pair before opening any seal.

### Step 7 — unseal

```python
scorecards = ledger.unseal(sealed_key_path, run_ids_by_task)
```

`run_ids_by_task` is `{task_id: pair_run_id}` for every pair in the run —
`pair_run_id` is `run_pair`'s own `run_id` return field, the same value
handed to `flatten_pair_record` in step 3 (audit.py module docstring, "the
`run_ids_by_task` — interface seam"). `unseal` refuses if any sealed-key
label lacks a recorded score, and refuses a second call on the same
`BlindedScoreLedger` instance — scoring must freeze strictly before the key
opens, and the key opens exactly once (D5).

### Step 8 — metrics tables

```python
from metrics import build_pair_rows, render_table

rows = build_pair_rows(run_records, scorecards)   # run_records: step 3's flattened lists
print(render_table(rows, fmt="text"))             # or fmt="json"
```

Or via the CLI: `python metrics.py --run-records <path> --scorecards <path>
[--json]`. `build_pair_rows` emits one row per arm-run — wall-clock, turns,
`tokens_regime`/`tokens_value` (measured or labeled proxy, D6), and for
arm A only, `defects_caught`/`defects_caught_count` alongside
`defects_escaped`/`defects_escaped_count` (arm B has no verifier stage by
construction, so its `defects_caught*` fields stay structurally `None`, not
zero). **No aggregate, no cross-arm sum, is ever produced here** — D7's
"no aggregate claim without the underlying rows" is enforced by this
module simply never computing one; any pooled-within-class or per-class
comparison belongs in the report layer (T8), against the pre-registered
R1/R2/R3 decision rules `docs/plans/2026-07-18-ab-benchmark-design.md`
D7 defines (cited, not restated here) and a dated report under
`docs/audits/`. A routing conclusion from those rules is filed as an
UNRATIFIED delta per §1 above — never self-applied.

## 3. The honesty ledger

Every disclosed limitation of this harness, in one place, so a future
report never has to rediscover them:

- **Accept-and-disclose blinding residual (coding-style leak).** Per the
  human's 2026-07-18 binding answer to design open question 3, no formatter
  pass runs over either arm's diff before audit. `blinding.py`'s own module
  docstring names the accepted risk explicitly: a determined auditor could
  guess arm identity from coding idiom that fingerprint-stripping can't
  launder. Not mitigated; must be named in any report's Limitations
  section.
- **Blinding residuals not stripped (accept-and-disclose, same class).**
  `blinding.py`'s module docstring lists, verbatim, what its normalizer
  deliberately leaves alone: bare "Forge"/"forge.md" mentions, `sess-<hex>`
  session ids (no such id class is in D5's scrub list), spawn-contract
  vocabulary (`ROUTING:`, `CONTEXT PACK`, etc. — dispatcher-prompt
  artifacts, not diff/tree content), lowercase persona names (`_PERSONA_RE`
  is case-sensitive by design), and the naive `#`-in-string-literal comment
  detector misclassifying a `#` inside a real string literal (e.g.
  `"#123"`) as a comment start.
- **Proxy-token labeling.** `metrics.compute_tokens` reports a `"measured"`
  regime only when at least one attempt carries real `[tokens]` data
  (`fg-a10212`); otherwise it falls back to a `"proxy"` regime — turns ×
  the model/effort weight table in `metrics.PROXY_WEIGHTS`, cited verbatim
  from `docs/audits/2026-07-18-protocol-overhead-audit.md` §A.3 ("Assumed
  weights (ESTIMATE, unverified)") — and always labels the row's `note`
  field with that provenance. `"unavailable"` (never a fabricated number)
  when neither measured data nor a usable `model_tier` exists.
- **Deferred 4 briefs.** D2 names 12 tasks (3/class); the human's binding
  answer scoped the first run to 8 (2/class). `tools/benchmark/ground-truth/task-key.json`'s
  `not_built_this_run` records the 4 left for a future 3/class extension
  and why each was skipped for the minimum run: `M3` (click major-version
  bump — no real click 9 exists to install against in this environment),
  `F3` (`--currency` flag — larger invented-scope risk than M1/M2/F1/F2),
  `B2` (`--since`/`--until` boundary defect, `D-002` — B1 and B3 were
  chosen instead as the two most behaviorally distinct bug classes), `DOC3`
  (CHANGELOG + rounding-semantics doc section — assumes B1's fix already
  landed in the same tree, which doesn't hold for an independent
  single-task arm-run from the shared pinned base; needs re-scoping first).
- **The mypy gate caveat.** D1 names `pytest` + `ruff` + `mypy` as the
  fixture's three gates. T1's attempt log records: "mypy not installed —
  D1's mypy gate unverified, future task." `tools/benchmark/fixture/pyproject.toml`
  and `requirements.txt` carry no mypy config or dependency today; only
  `pytest tests/` and `ruff check .` are wired and green at the pinned
  base. Anyone re-running this recipe after wiring mypy in must also add it
  to every `gate_command` passed to the arm adapters (step 3) — a
  gate the adapters weren't run against is a gate an arm was never held to.
- **Severity is instruction-level enforcement, not machine-enforced.**
  `audit.py`'s module docstring and `auditor-contract.md`'s OUTPUT CONTRACT
  both state the rule: a `defect-present` checklist item's severity is
  fixed by the checklist, and the auditor must echo it verbatim rather than
  assign its own. `audit.BlindedScoreLedger.record_scores` validates that a
  supplied severity is a member of `metrics.VALID_SEVERITIES`, but it
  cannot cross-check it against the checklist's own declared value for that
  `item_id`, because a label carries no task identity until `unseal()` —
  that is the whole point of blinding. Enforced by auditor instruction only
  until a future run wires the checklist through `unseal` explicitly to add
  a mechanical cross-check.

## 4. Fixture recipe — how `ledgerkit` was authored

If a future protocol change needs a 12-task/3-per-class run (extending
past D2's 8-task minimum), or a second synthetic fixture, follow the same
authorship discipline `tools/benchmark/fixture/` was built under (D1, D2):

1. **Author fresh, never vendor.** D1's rejected alternative — vendoring a
   small OSS project — is disqualifying because model recall of public code
   asymmetrically deflates arm B's escaped-defect rate (it can reconstruct
   a canonical fix from training memory) and can't carry planted defects
   with a ground-truth key. Every fixture module under
   `tools/benchmark/fixture/src/ledgerkit/` (`accounts.py`, `ledger.py`,
   `money.py`, `report.py`, `transactions.py`, `csv_import.py`, `cli.py`)
   was written for this benchmark, kept out of any public index, with real
   cross-module coupling and real gates rather than a greenfield toy (D1's
   accepted cost: "a synthetic repo can be too clean").
2. **Match the repo's own gate stack.** Python was chosen (D1, "not
   open — it matches the repo's own pytest gate and needs no new
   toolchain") specifically because this repo's own gate is
   `python -m pytest tools/ -q` (`.forge/forge.md`). `ruff` is a cheap real
   lint gate on top; `mypy` is named but not yet wired (§3).
3. **Plant defects with a sealed ground-truth key, before any checklist.**
   `tools/benchmark/ground-truth/ledgerkit-defects.sealed.json` records
   every planted defect (`D-001` through `D-005` today) with its class,
   location, root cause, trigger condition, why the fixture's own baseline
   tests miss it, and expected correct behavior — authored and sealed
   *before* any checklist references it, and kept outside
   `tools/benchmark/fixture/` entirely so no arm (A or B) can ever see it.
   Not every defect maps to a task in the current 8 (`D-004`, "fixture-
   original," is extra bug-fix-class material reserved for a 3rd bug-fix
   task or the 3/class extension).
4. **Derive each checklist from criteria + ground truth only, then freeze
   it.** Each `tools/benchmark/ground-truth/checklists/<task_id>.checklist.json`
   is derived purely from its `tools/benchmark/tasks/<task_id>/task.md`
   acceptance criteria plus the planted-defect entry it targets (per
   `tools/benchmark/ground-truth/task-key.json`'s `planted_defect_ids`) —
   never from any arm's diff, because no arm diff exists yet when a
   checklist is authored (D5 mechanism 3: "there is nothing to leak").
   Freeze discipline: compute `content_sha256` over canonical JSON of
   `{task_id, class, items}` (sorted keys, no whitespace — the exact
   formula `audit.checklist_content_hash` implements and every shipped
   checklist's own `content_sha256_note` field states) and record it in
   both the checklist file and `task-key.json`, **before the first arm
   runs**. A checklist item's `source` field (`"planted-defect"` or
   `"criteria"`) documents which half of "criteria + ground truth" it came
   from — see `B1.checklist.json` for the pattern.
5. **Keep checklists fingerprint-free.** No arm-identifying or
   verifier-referencing language (e.g. "the verifier should have caught
   this") belongs in a checklist — it is a pure correctness spec (D5).
6. **Isolate the fixture's own test suite from the repo gate.**
   `tools/benchmark/conftest.py`'s `pytest_ignore_collect` hook is what
   makes `python -m pytest tools/ -q` skip `tools/benchmark/fixture/`
   while `pytest tools/benchmark/fixture -q` still collects it directly —
   a plain `collect_ignore_glob` can't do both, because pytest applies an
   ancestor conftest's ignore rules even to an explicitly-named path (see
   that module's own docstring for why the hook checks
   `config.invocation_params.args` instead).
7. **Extending to 3/class**: build the 4 deferred tasks (§3) the same way —
   new/extended defect entries in `ledgerkit-defects.sealed.json` if a task
   needs one, a new `task.md` under `tools/benchmark/tasks/<id>/`, a new
   frozen+hashed checklist, and new entries in both `tasks/manifest.json`
   and `ground-truth/task-key.json` — before touching any arm.
