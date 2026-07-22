# Memory

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## Project memory files (`.forge/memory/`) — Phase 2

> Amended by: "Memory — agents tag + craft memory (2026-07-17)"

One fact per file plus a `MEMORY.md` index (spec §8). Git-tracked and project-scoped: memory travels with the repo and is shared by every model, machine, and agent. **Facts are never deleted** — outdated facts are marked superseded so contradictions resolve without silent loss (bitemporal-lite).

### Layout

```
.forge/memory/
├── MEMORY.md            # index: one line per fact
└── <type>-<slug>.md     # one fact per file
```

### Fact file frontmatter (flat YAML, all required, exact names)

| Field | Type / values | Notes |
|---|---|---|
| name | string (kebab-case) | short unique handle |
| description | string | one line; this is the text that appears in `MEMORY.md` |
| type | decision \| gotcha \| postmortem \| preference \| reference | fact class |
| created | ISO-8601 UTC | real `date -u`, never a placeholder |
| updated | ISO-8601 UTC | touch on every edit |
| superseded-by | path or null | points to the newer fact; the old file is never deleted |

Fact types (spec §8):

- **decision** — why X, including the reasoning and the alternatives considered.
- **gotcha** — a trap that cost time.
- **postmortem** — written whenever a task bounces twice; captures the reasoning, not just the outcome.
- **preference** — a standing project preference.
- **reference** — a durable pointer (doc, command, external resource).

Filename: `<type>-<kebab-slug>.md` (slug derived from `name`, max 40 chars). Body: free-form markdown — the fact itself, with enough context to act on it without the session that learned it.

### MEMORY.md index

```
# Project memory index

- [<name>](<file>) — <type> — <description>
- [<name>](<file>) — <type> — <description>  (superseded → <newer-file>)
```

One line per fact. Superseded facts stay listed, tagged `(superseded → <file>)`. The librarian maintains this file; the kernel LEARN step appends a line when it writes a new fact.

## Memory — agents tag + craft memory (2026-07-17)

Amends "Project memory files" above with two additions: an optional
per-fact tagging field, and a second, plugin-level memory store.

**`agents:` field.** A fact file's frontmatter may carry an OPTIONAL
`agents:` field: a flat YAML list of roster agent names (e.g.
`[forge-debugger, forge-worker]`, or the equivalent multi-line `- item`
form), meaning "this fact concerns that agent's kind of work." It is not in
the required-fields table above — a fact with no `agents:` field validates
exactly as it always has, and is recalled by kernel judgment as before.
When present, `validate_memory.py` requires it to be a list of non-empty
strings; a bare scalar (not a list) or a list containing an empty/blank
item is a validation error. The kernel's LEARN step sets the tag when a
fact clearly concerns a specific roster role's craft (`forge:memory`,
"Agent-tagged recall"); a `MEMORY.md` index line for a tagged fact shows
its tags, e.g. `- [name](file) — gotcha — description (agents:
forge-debugger)`. An explicit empty list (`agents: []`) is valid and
treated identically to the field being absent — both mean "no agent tag",
not a validation error.

**Mechanical-include rule.** Tagging has one enforced consequence: every
spawn contract's CONTEXT MANDATORILY includes every memory fact whose
`agents:` list names the agent being spawned (excerpt or full body if
short) — this is mechanical, not a router judgment call. Judgment-selected
facts are added after, within the contract's existing ~1k-token cap; tagged
facts get priority if the budget requires trimming
(`skills/kernel/references/spawn-contract-template.md`, Context budget).

**Craft memory (plugin-level).** A second memory store lives at
`<plugin-root>/memory/` (`memory/MEMORY.md` plus `<type>-<slug>.md` fact
files at the plugin's git root — the same directory that holds `skills/`,
`agents/`, `tools/`), title `# Forge craft memory — plugin-level,
project-agnostic`. Scope: **project-agnostic** lessons only — environment
gotchas, cross-project techniques, harness behaviors — never anything
specific to one project. It is git-tracked with the plugin, so it ships to
every project that installs Forge, and is written only by the kernel's
LEARN step (never by workers), same authorship rule as project memory.
Facts arrive there by **promotion**: when a project fact filed at LEARN is
clearly project-agnostic, the kernel COPIES it (never moves it) into craft
memory as a new fact file, noting in the copy which project fact it was
promoted from. The project-scoped original is untouched. The
never-delete/supersede discipline applies identically inside craft memory.

**Validator coverage.** `tools/validate_memory.py` validates both stores —
it takes fact-file paths as arguments (or, with none, defaults to globbing
`.forge/memory/*.md`), so running it against `memory/*.md` at the plugin
root validates craft-memory facts with the identical rule set, including
the optional `agents:` field.

## Craft-memory bleed check — 2026-07

Response to fg-a10203. Craft memory (`<plugin-root>/memory/`, "Memory —
agents tag + craft memory (2026-07-17)," above) is the ONE store shared
across every project that installs Forge — nothing mechanical stopped a
project-specific detail from riding along in a fact promoted there, until
now. `tools/validate_memory.py` adds a craft-store-scoped bleed check.

**Craft-store scoping.** The check runs only when `validate(path,
warnings=...)` is called on a fact whose path resolves to the craft store:
parent directory named `memory` whose OWN parent is not `.forge` — the same
path-derived distinction "Validator coverage," above, already draws between
the two stores. A `.forge/memory/*.md` project fact is never in scope, no
matter what it contains — project paths belong there by definition.

**Patterns (canonically a hand-edited list, never derived from git config
or the environment).** Four bleed classes, each a WARNING naming the
offending fragment: (1) an absolute filesystem path outside the plugin
root; (2) a drive-letter path pointing at another local project (the same
absolute-path check — an `X:\...` fragment that doesn't resolve under the
plugin root); (3) the repo owner's GitHub handle
(`validate_memory.CRAFT_BLEED_HANDLES`, edited by hand); (4) a repo-relative
file reference (e.g. `tools/nonexistent.py`) that does not exist anywhere
under the plugin root. URLs (`https://...`) are masked out before any of
these patterns run, so a legitimate external cross-reference — a GitHub
issue link, for instance — never trips the file-reference or path checks.

**Warning, never error.** Legitimate cross-references exist — the URL
example above, or a fact correctly citing a real plugin file
(`tools/validate_task.py`) — so a match is advisory, not a defect. Bleed
findings go out on the same separate warnings channel `validate_task.py`
already established (`validate(path, warnings=...)`, printed as `WARNING:`
lines, never appended to the returned error list): the existing error
contract is unchanged, and exit code is unaffected by warnings, mirroring
`validate_task.py`'s own warnings-list pattern exactly.

**LEARN gate.** Promotion to craft memory requires resolving every bleed
warning FIRST — fix the fact (drop or generalize the offending fragment) or
keep it project-local instead of promoting it — and the resolution is
recorded in the session report. See `skills/kernel/SKILL.md`, LEARN step,
"Promotion to craft memory."

