# Coordination gate — session presence manifests (reference)

NORMATIVE. Implements decomposition item 1 of `.forge/specs/2026-07-19-
multi-operator-coordination.md` (spec-f0c2), "Session presence manifests"
AC section, GOVERNED where it conflicts by that spec's own "Amendments —
2026-07-20 (ratification)" section (staleness threshold below; the
notification channel design point 4 is DROPPED at ratification and is not
referenced anywhere in this file). This file is the schema and write/read/
staleness procedure `skills/kernel/SKILL.md`'s SYNC/PULL/INTEGRATE anchors
cite rather than restate — the citation lines themselves are decomposition
item 2's boundary (`fg-f0102`, serialized behind this file), not this
file's. It ships no wiring into the kernel loop of its own; a reference
file with no citing anchor yet is inert until item 2 lands.

## 1. Manifest file and location

One file per operator, per repo: `.forge/coordination/<operator-handle>.md`.
`.forge/coordination/` is a plain directory of these manifest files — no
subdirectories, no per-machine split (an operator running two machines
against the same repo still writes to one `<operator-handle>.md`; the
`machine label` field below is what distinguishes which machine last wrote
it, not a second path segment).

## 2. Schema

Plain Markdown, front-matter-style key list (same flavor as a queue task's
frontmatter block, not YAML-validated here — this file defines field
presence and meaning; a machine-checkable schema, if one is ever added, is
`tools/validate_config.py`'s concern, not this file's). Required fields:

- **`operator`** — the operator handle (section 4 below) this manifest
  belongs to; MUST match the `<operator-handle>` in the file's own path.
- **`machine label`** — a short human-chosen string identifying which
  machine last wrote this manifest (e.g. `ben-laptop`, `ben-desktop`) —
  distinguishes the same operator running from two machines without a
  second manifest file.
- **`branch`** — the current branch the session is working from.
- **`claimed task ids`** — the task ids this session currently holds a live
  claim on (empty list when none); this is the field PULL's peer-read
  (section 6) treats as off-limits for the wave.
- **`in-flight wave boundary file paths`** — the boundary path(s) named in
  the Execution plan of every task this session currently has dispatched
  in an active wave (empty list when no wave is in flight); PULL's
  peer-read treats these paths as off-limits for the wave exactly like
  claimed task ids.
- **`started`** — an ISO 8601 UTC timestamp (`date -u
  +%Y-%m-%dT%H:%M:%SZ`, same format `docs/conventions/trust-and-security.md`
  already uses for `.provenance`/`.trust-local`) set once, at session
  start, and never rewritten afterward.
- **`updated`** — an ISO 8601 UTC timestamp, rewritten at every milestone
  boundary (section 5); this is the field the staleness rule (section 7)
  reads.
- **`ended`** — an ISO 8601 UTC timestamp, absent while the session is in
  flight and written exactly once at session end (section 5). Absence of
  this field, not deletion of the file, is what marks a session still
  running — a peer reading a manifest with no `ended` field and a fresh
  `updated` field treats it as a live session; the same manifest is never
  deleted on end, only updated with this one additional field, so the
  historical record of who ran when survives past the session itself.

No other fields are part of this schema. A future task extending it (e.g.
richer per-task detail) amends this section rather than inventing a
parallel file.

## 3. Write procedure

- **Session start:** write `.forge/coordination/<own-handle>.md` fresh —
  `operator`, `machine label`, `branch`, `claimed task ids` empty, `in-flight
  wave boundary file paths` empty, `started` and `updated` both set to the
  same current UTC timestamp, no `ended` field. If a manifest already
  exists at this path from a prior session (no `ended` field, meaning it
  either crashed or is still genuinely running elsewhere), do not silently
  overwrite the identity fields — this is the crash-vs-concurrent-session
  ambiguity the staleness rule (section 7) exists to resolve, not this
  step's job to guess at.
- **Milestone-boundary update:** at a task claim, a wave dispatch, or an
  INTEGRATE, rewrite `claimed task ids`, `in-flight wave boundary file
  paths`, and `updated` (fresh current UTC timestamp) on the session's own
  manifest before proceeding to the next step. This is a kernel-owned
  `.forge/` write (Hard Rule 4) performed by the session itself, on its own
  file only — a session never writes to a peer's manifest.
- **Session end:** write `ended` (fresh current UTC timestamp) to the
  session's own manifest — queue drained, budget cap reached, or an
  explicit stop all trigger this identically. `claimed task ids` and
  `in-flight wave boundary file paths` SHOULD reflect their true final
  state (normally empty, since a session that reaches end has released or
  completed its claims) but `ended` being present is the authoritative
  finished-signal regardless of what those two fields still say.

## 4. Operator-handle

A short kebab-case name (e.g. `ben`, `dbcoup`) a human picks once per
machine and Forge persists in project or user space per the existing
customization-persistence contract (`docs/customization-persistence.md`).
This file defines only the manifest contract the handle feeds into — the
handle-minting prompt/persistence flow itself (when it fires, where
exactly it's stored, its charset/length rules) is decomposition item 3's
convention (`fg-f0103`, sibling work under the same spec), cited here
without restating. Until that item lands, an operator-handle sourced any
other way (a manually-set config value, a fallback default) is equally
valid input to this file's schema — this file only requires that
whatever string is used matches the manifest's own `operator` field and
its filename.

## 5. Read procedure (PULL's pull-before-claim step)

WHEN PULL is about to compute a claimable set, THE SYSTEM SHALL first read
every file under `.forge/coordination/` except its own manifest and (when
present) `roster.md` itself, which is not a peer manifest — see §11 for the
roster-gating narrowing this procedure is subject to when a roster file
exists. For each peer manifest read:

- if the manifest's `updated` timestamp is within the staleness threshold
  (section 7) of the current time, treat every id in its `claimed task ids`
  and every path in its `in-flight wave boundary file paths` as off-limits
  for this wave — excluded from the claimable set and from this session's
  own wave-boundary selection, identically to how the queue's own
  claim-timestamp already excludes another session's live claim;
- if the manifest carries an `ended` timestamp, its claimed-ids and
  wave-boundary-paths lists are informational only (a finished session
  holds nothing) — do not exclude anything on their account regardless of
  how fresh `ended` is;
- if the manifest's `updated` timestamp is older than the staleness
  threshold and it carries no `ended` field, apply the staleness rule
  (section 7) instead of excluding.

This is a read of committed files already available from the last SYNC
pull (`docs/conventions.md`, offline-merge convention background) — no new
network or locking call. Because `.forge/coordination/` is git-tracked
(section 8), reading "every peer manifest" means every file present in the
session's own working tree after that pull, not a live query against
peers' machines.

## 6. Staleness rule

**Pin — staleness-threshold:** peer-manifest staleness is **4 hours**,
deliberately reusing the queue's own `claim-staleness-hours` vocabulary
(`skills/queue/SKILL.md`, `forge.md`'s `## Queue` section,
`claim-staleness-hours` default `0.5`) — one staleness concept spans both
a stale task claim and a stale peer manifest, not two independently-tuned
numbers. This value is fixed by spec-f0c2's Amendments section (which
GOVERNS over the spec body's earlier "[resolved 2026-07-20: 4 hours]"
placeholder) and is not itself a `forge.md`-configurable key the way
`claim-staleness-hours` is — a future task may choose to expose it as one,
but this file does not.

WHEN a peer manifest's `updated` timestamp is older than 4 hours AND it
carries no `ended` field, THE SYSTEM SHALL treat that manifest as
ADVISORY ONLY: do not exclude the task ids or wave-boundary paths it names
from the claimable set, but log one session-report note identifying the
stale operator handle, its age, and what it named, so a human reviewing
the session can see that a possibly-crashed peer's claims were not
honored as a hard exclusion. This is the same shape as a stale queue claim
degrading to reclaimable rather than permanently locking a task — a
crashed machine's manifest must never permanently block a peer.

## 7. `.forge/coordination/` housekeeping

The directory is git-tracked (committed, not gitignored) — unlike the
machine-local trust markers (`docs/conventions/trust-and-security.md`,
"Trust boundary"), presence visibility is the entire point, so peers must
see it through the normal repo history, not merely locally. Ended
manifests (an `ended` field present) MAY be pruned by `forge-librarian` per
the project's existing retention conventions
(`docs/conventions/agents-lifecycle.md`, "Retention and pruning scope
extension") — human-approved deletion only, off the critical path, never
a live session's own job — cited here without restating that flow's
mechanics. A manifest is never deleted as a side effect of the write
procedure above; only the librarian's existing pruning path removes one.

## 8. Non-goals of this file

No notification
channel of any kind — dropped entirely at ratification (Amendments item
3) and out of scope permanently, not merely deferred.

## 9. Kernel-step anchor mapping (`fg-f0102`)

`skills/kernel/SKILL.md` cites this file at four anchors, each triggering
exactly the write/read procedure named here — no other kernel step touches
`.forge/coordination/`:

- **SYNC** -> write/refresh own manifest (§3, "Session start").
- **PULL**, before the wave is computed -> read every peer manifest and
  exclude their claimed task ids / wave-boundary paths from the claimable
  set (§5 read procedure, §6 staleness rule) — the pull-before-claim step.
- **Milestone boundary** (a task claim, a wave dispatch, or an INTEGRATE)
  -> update own manifest's `claimed task ids`, `in-flight wave boundary
  file paths`, and `updated` (§3, "Milestone-boundary update").
- **Session end** (queue drained, budget cap, or an explicit stop) -> mark
  own manifest `ended` (§3, "Session end").

## 10. Sync cadence (`fg-f0104`)

WHEN SYNC runs, THE SYSTEM SHALL pull `staging` (`CONTRIBUTING.md` §6)
before PULL computes a wave or any task is claimed. WHEN an INTEGRATE
completes, THE SYSTEM SHALL push the integration commit to `staging` —
never `main` (`CONTRIBUTING.md` §6) — before the next claim. WHEN that
push is rejected as diverged, THE SYSTEM SHALL pull, apply `fg-e103`'s
offline-merge convention (`docs/conventions/artifact-formats.md`,
"Offline merge convention") to any conflicting file, and retry, never
force-pushing or dropping the commit.

**Precedence.** The above are multi-operator DEFAULTS. An explicit human
instruction to push elsewhere (e.g. this repo's own standing main+staging
push) takes precedence over the `staging`-only default for that push.

## 11. Roster gating (`fg-f0106`)

Implements spec-f0c2's "Clarifications resolved — 2026-07-19" item 4 (the
"presence scope" refinement): §5's peer-manifest read procedure is narrowed
by a committed team roster, gating which operator handles are trusted
without ever letting an unrostered or unreadable roster lock a peer out.

**Roster file:** `.forge/coordination/roster.md`, git-tracked (committed,
not gitignored — same visibility rule as `.forge/coordination/` itself,
§7). Minimal shape: one operator handle per bullet line (`- <handle>`, the
same kebab-case handle format §4 defines), no other required structure —
one line per trusted operator, nothing else parsed from the file.

**WHEN `.forge/coordination/roster.md` exists**, THE SYSTEM SHALL apply §5's
read procedure (claim-exclusion, §6 staleness rule) only to peer manifests
whose `operator` field matches a handle listed in the roster. A peer
manifest whose `operator` is not listed in the roster SHALL be logged as
exactly one session-report note (naming the unrostered handle and what its
manifest named) and SHALL NOT be honored for claim-exclusion — an
unrostered manifest can never lock a rostered peer out of the claimable
set, regardless of how fresh its `updated` timestamp is.

**WHEN no roster file exists** at `.forge/coordination/roster.md`, THE
SYSTEM SHALL honor every manifest per §5 exactly as before this section
existed — open-by-default, current behavior unchanged.

**Failure direction:** a malformed or unreadable roster file (unparseable,
empty, permissions error, or any other read failure) SHALL degrade to
open-by-default — treated identically to no roster file existing, plus one
session-report note naming the failure — and SHALL NEVER degrade to
lockout. Roster gating only ever narrows which manifests are honored for
claim-exclusion; a broken roster must never result in excluding more than
an intact roster (or no roster at all) would.

§8 previously deferred roster/allowlist gating as a non-goal of this file;
that gate is now built by this task (`fg-f0106`) and lives here instead.
