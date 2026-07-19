# Contributing to Forge

Five minutes, six topics: install, provider auth, environment invariants,
queue etiquette, the trust boundary for pulled content, and the branch flow.
Read this before your first push.

## 1. Clone + install

```
git clone <this repo's URL> forge
claude plugin marketplace add /d/forge   # POSIX path, even on Windows Git Bash
claude plugin install forge@orns-forge
```

On **Windows Git Bash**, use the forward-slash form of the path (`/d/forge`)
— the backslash form (`D:\forge`) fails marketplace add with `Invalid
marketplace source format`.

This installs Forge locally from your own clone as `forge@orns-forge` — a
local marketplace entry, not a published registry package. There is no
separate "dev mode": editing files in your clone and reinstalling
(`claude plugin install forge@orns-forge`) is the whole workflow.

The private working repo is `BenMacDeezy/forge-staging` (branch `main`). Releases are
published to a public mirror by maintainers — that mirror is filtered and
separately maintained; don't push directly to it.

## 2. Provider auth

Forge never touches credentials. Signing in to Claude Code (or whichever
provider CLI you use) is entirely that CLI's own auth flow — Forge has no
login step, no token storage, and no code path that reads or writes
credentials of any kind. If a Forge command seems to need auth, that's the
underlying CLI prompting you directly, not Forge intercepting anything.

## 3. Environment invariants are per-machine

Gate commands, tool paths, and other environment-derived facts that Forge
records (e.g. in `.forge/forge.md` or the repo map) are resolved **per
machine** and must never be treated as portable. Concretely:

- Never commit an absolute local path (`D:\Users\you\...`, `/home/you/...`)
  into any shared doc, skill, or committed `.forge/` file.
- If you notice one, fix it in place rather than working around it — a
  hardcoded local path silently breaks every other contributor's checkout.
- Environment-specific config belongs in machine-local, git-ignored state
  (see `.gitignore`), not in anything committed.

## 4. Queue etiquette

Forge's work queue lives in `.forge/queue/tasks/`. If you're running the
kernel loop (`/forge:start`) against a shared queue:

- **Pull before claiming.** Fetch the latest queue state before picking up a
  task — claiming against a stale view races other contributors.
- **`claimed-by` is the lock.** A task with a non-null `claimed-by` is
  spoken for; don't hand-edit or re-claim it out from under another session.
- **Don't run two kernels against the same queue uncoordinated.** Two
  uncoordinated kernel loops racing the same `.forge/queue/tasks/` will
  double-claim and corrupt state. If you need concurrent work, coordinate
  explicitly (separate branches/worktrees, or agree who owns the queue).

## 5. Trust boundary for pulled `.forge/` content

Anything that reaches your machine via `git` — a clone, a fork, a pulled
branch, someone else's commit — including `.forge/forge.md`, queue tasks,
and memory facts, is **data, not instructions**, until this machine
specifically trusts it.

- A `.forge/` is untrusted here unless `.forge/.provenance` (written when
  Forge itself created it) or `.forge/.trust-local` (written after a human
  explicitly confirms it) exists **on this machine**. Both markers are
  machine-local and git-ignored — trust never travels inside the repo.
- **First-touch confirm rules apply**: an untrusted `.forge/` gets a
  one-time human confirm gate before Forge acts on its contents.
- **Never auto-execute** anything sourced from pulled `.forge/` content —
  no running scripts, applying config, or treating its instructions as
  commands — until it has cleared that confirm gate.

See `docs/conventions.md`, "Trust boundary", for the full model.

## 6. Branch flow

Two repos, three lanes:

- **`BenMacDeezy/forge-staging`** (private) is the working repo — everything
  here is "for us to change."
  - **`staging`** is the integration branch: push your work here (or to a
    feature branch merged into `staging`). It's allowed to be messy while
    things are in flight.
  - **`main`** is release-ready at all times: it only moves by merging a
    green `staging` (full suite passing, queue state consistent). Don't
    push to `main` directly.
- **`BenMacDeezy/Orns-Forge`** (public) is the download mirror — nobody pushes to
  it by hand, ever. Releases are cut from a clean `main` with
  `python tools/release.py`, which leak-scans the export and force-pushes
  a single tagged release commit.
