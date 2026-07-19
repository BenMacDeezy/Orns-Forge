---
name: onboard
description: Set up Forge end to end in any repository — init .forge/, build the map, seed the constitution and forge.md, run a scout pass, and generate a root AGENTS.md. Use on /forge:onboard, or offer it when working in a repo that has no .forge/ directory.
---

# Forge onboard

One command turns a cold repo into a Forge-ready one (spec §11). Every step is
**idempotent**: never overwrite a file that already exists — report it and move on.

## Steps

Resolve the repo root before any step touches `.forge/` (`forge:queue`, Auto-init) — onboard a subdirectory of an existing repo-root `.forge/` reuses it rather than initializing a second one.

1. **Init `.forge/`** (via `forge:queue` auto-init): create `.forge/queue/tasks/`
   and `.forge/forge.md` (from the kernel's
   `skills/kernel/references/forge-config-template.md`). Resolve `(auto-detect)`
   gates now — inspect the repo (package.json scripts, Makefile, pyproject, Cargo,
   go.mod, etc.), and write the real build/test/lint commands back into
   `forge.md`. If `forge.md` already exists, do NOT clobber it — only fill gate
   values still left as `(auto-detect)`, and leave a fully-resolved file untouched.
   If this step actually creates `.forge/` (it didn't already exist), write the
   first-party provenance marker `.forge/.provenance` per `docs/conventions.md`
   ("Trust boundary") — this is what lets later sessions on this machine tell
   that Forge itself made this `.forge/`, without which it's treated as
   untrusted. Also ensure the target repo's `.gitignore` lists BOTH
   `.forge/.provenance` and `.forge/.trust-local` (append whichever line(s) are
   missing if `.gitignore` exists; create a two-line `.gitignore` with both if
   none exists) — both are machine-local trust markers (`.provenance` written
   by Forge on init, `.trust-local` written later only when a human confirms
   an untrusted `.forge/`, fg-7b03) and neither may ever be committed.
   Idempotent like every other onboard step: never duplicate either line,
   never touch a `.gitignore` that already has it.
2. **Build the map** — run the `forge:map` skill to produce `.forge/map/`
   (architecture, index, conventions, hotspots).
3. **Seed the constitution** — if `.forge/constitution.md` is absent, write a
   starter from the spec skill's `references/constitution-template.md` for the
   user to edit.
4. **Offer discovery (gated)** — if `.forge/project.md` doesn't already exist,
   ask via a structured `AskUserQuestion` gate (per `docs/conventions.md`,
   "Asking the user questions") — "Run project discovery now to define vision,
   stack, and roadmap?" with "Yes, run discovery now (recommended)" first and
   "Skip for now" second, not a free-form prose question. If accepted, run the
   `forge:discover`
   skill now, and ensure the stack & architecture are defined (established if
   absent, confirmed if present) — for existing repos, step 2's map build
   already produced the code-level `architecture.md`; discovery's Stack &
   Architecture pass adds the stack breadth, rationale, and user confirmation
   on top of it. This step is skippable — if declined, note that it can be
   run later via `/forge:discover`. If `.forge/project.md` already exists,
   skip the offer and report it as already present, same as any other
   idempotent step.
5. **Scout pass** — invoke the `forge:scout` skill (or spawn `forge-scout`,
   sonnet/medium) to produce a vetted, ranked shortlist. Present it; install
   NOTHING and edit no config.
6. **Generate root `AGENTS.md`** — from `references/agents-md-template.md`,
   re-exporting the project conventions (spec §7.5). Fill the build/test/lint
   commands from the resolved `forge.md` Gates; if `.forge/map/conventions.md`
   exists, embed or link it. If an `AGENTS.md` already exists, do NOT overwrite —
   append a clearly marked "## Forge" section instead, and if a `## Forge`
   section is already present (a prior onboard), report it and change nothing so
   re-runs stay a true no-op.
7. **Report** — created vs. already-present per file, the scout shortlist, map
   status, whether discovery ran, and the next command (`/forge:add`,
   `/forge:spec`, or `/forge:start`).

## Safety

- Existing `forge.md`, `constitution.md`, `AGENTS.md`, and map files are never
  clobbered.
- Onboard installs nothing and commits nothing on its own beyond the `.forge/`
  scaffolding and `AGENTS.md`; the scout shortlist is advisory and install-free.
- `.forge/.provenance` and `.forge/.trust-local` are both machine-local and
  git-ignored — never committed. `.provenance` is written once, at first init,
  and never touched again — it records the original act of creation, not a
  running log; onboard writes it. `.trust-local` is only written on a human's
  explicit trust confirmation (fg-7b03), never by onboard. `.gitignore`'s two
  lines for them are each added idempotently (never duplicated).

## New or empty repository

If the repo has no source files yet (empty folder, or only .git/README), do not
improvise questions per step — run this path instead:

1. Recommend running discovery now rather than improvising a single question.
   Put it as a structured `AskUserQuestion` gate (per `docs/conventions.md`,
   "Asking the user questions") — "This looks like a new project — run project
   discovery (`forge:discover`) to define vision, users, stack, and roadmap
   before we set anything up?" with "Yes, run discovery (recommended)" first
   and "Skip — I'll answer one quick question instead" second. This replaces
   the old one-question improvisation; discovery's adaptive interview covers it
   properly. If accepted, run the `forge:discover` skill now and use its output
   (stack, constraints) for the steps below. If declined, fall back to asking
   one open question up front (prose is right here — it's open-ended) — "What
   are you building here, and with what stack (if you know yet)?" — and note
   that `/forge:discover` remains available later for the full charter.
2. Init `.forge/` as normal, but leave Gates as `(auto-detect)` with the note
   `# no code yet — re-resolve after first commit of source`.
3. SKIP the map build — there is nothing to map. Note in the report that the
   map builds automatically the first time the kernel or `/forge:map` runs
   against real code.
4. Seed the constitution as normal (it is code-independent); if discovery
   ran and produced stated constraints, it has already tightened this file
   per its own protocol — don't redo that work here.
5. Scout runs against the stated intent (stack from discovery, or the
   fallback answer), not the file tree — still a proposal-only shortlist. If
   there's no stack answer yet, skip scout and note it.
6. Generate a minimal AGENTS.md (project intent + "gates pending first code").
7. Report, and recommend the new-project flow explicitly: if discovery ran
   and produced an approved charter, recommend `/forge:spec "<milestone 1>"`
   from its roadmap; otherwise recommend `/forge:discover` (or `/forge:spec`
   directly for a single well-understood feature) — the map, gates, and
   scout all get richer as code lands.
