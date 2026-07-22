# Project scope guard (reference)

Loaded by `skills/kernel/SKILL.md` SYNC (before "Repo root first" informs
any read/write) and by `skills/queue/SKILL.md`'s Auto-init (before any
add/close/promote write). NORMATIVE: this is the full guard procedure the
citing sentence points at, not a summary. Canonical rule text and rationale
live in `docs/conventions.md`, "Project scope guard — 2026-07-20
(project-scope-guard)" — this file is the operational how-to for that rule.

## Why

Origin (2026-07-20, user-reported): a session whose resolved project did
not match the folder the human actually meant silently read and wrote a
DIFFERENT project's `.forge/` — a project folder's Forge run resolved to
the Forge-dev-repo's queue instead of its own. Forge never persists an
absolute path into a project, so nothing on disk flags the mismatch on its
own; this guard is the check that catches it before any decision or write
depends on the wrong queue.

## The check

1. Resolve `project_dir` = `CLAUDE_PROJECT_DIR` (env var) if set and
   non-empty, else the session's cwd.
2. Resolve `project_dir`'s git toplevel (`git rev-parse --show-toplevel`
   run from `project_dir`). If git specifically reports that `project_dir`
   is not inside a git repo, this guard is inert (`no-git`) — the existing
   cwd-fallback rule (SYNC, "Repo root first") applies unchanged, nothing
   to compare. Any other failure to resolve the project toplevel (including
   unavailable git, unreadable paths, or dubious ownership) is `git-error`:
   kernel SYNC and queue writes MUST stop and ask; status MUST warn.
3. The `.forge/` about to be read or written MUST be
   `<that toplevel>/.forge`. Canonicalize that expected path and the actual
   `.forge/` path directly, even when the actual path does not exist, then
   require path equality (filesystem identity when available; normalized
   comparison with trailing separators removed and case-insensitivity on
   Windows). Do NOT compare the git toplevels that own the two paths: a
   nested same-repo `.forge/` is a mismatch, as is a nonexistent path aimed
   at another repo. Only `project_dir` may be nested: git resolves it to the
   project toplevel before the expected root-level `.forge/` is computed.
4. **Accelerator:** `python <plugin>/tools/scope_guard.py <.forge path>
   --project-dir <project dir>` prints `match`/`no-git` and exits 0, or
   prints `mismatch: expected <path> actual <path>` / `git-error: ...` and
   exits 1. This prose is the source of truth; if Python is unavailable,
   resolve only `git -C <project dir> rev-parse --show-toplevel`, form its
   root-level `.forge/`, canonicalize the expected and actual paths as
   above, and compare those paths directly.

## On mismatch or git-error — kernel SYNC and queue-skill writes

STOP before the result informs any decision and before any write. On a
mismatch, state BOTH paths plainly — the expected `.forge/`
(`<project_dir>`'s own toplevel) and the actual `.forge/` about to be
operated on — and ask the human which project they meant. On `git-error`,
state that the project toplevel could not be resolved and ask the human to
resolve or confirm the project before continuing. Never auto-pick: not "prefer
`CLAUDE_PROJECT_DIR`", not "prefer cwd", not "the one with more recent
activity". A stale claim, an in-flight loop, or a queued task in the
WRONG `.forge/` are exactly the kind of silent corruption this guard
exists to prevent, so guessing defeats the point as thoroughly as not
checking at all.

## On mismatch or git-error — read-only surfaces (`/forge:status`)

A read-only surface never blocks on this guard. For either `mismatch` or
`git-error`, `tools/status.py` wires `tools/scope_guard.py` into one
advisory line prepended to the board
(`SCOPE WARNING: ...`) and renders the rest of the board underneath it
unchanged — the human sees the mismatch without losing the query they
asked for.
