"""Blinding for the A/B benchmark's audit stage (fg-a10404, benchmark T4).

Implements design D5 (docs/plans/2026-07-18-ab-benchmark-design.md, "D5 --
Blinded audit: normalize -> shuffle -> sealed key; checklist frozen at
design time") -- read that section for the *why*; this module is the *how*
for mechanisms 1 and 2 (mechanism 3, the frozen per-task checklist, is T2's
file). Per the human's 2026-07-18 binding answer to the design's open
question 3: blinding = accept-and-disclose. No formatter pass runs over
either arm's diff here; the residual coding-style leak D5 flags (a
determined auditor might guess arm from idiom even after fingerprint
stripping) is an accepted, disclosed limitation -- it is NOT laundered by
this module, and the eventual report's Limitations section must name it.

Three responsibilities, run in this order for every task pair:

1. normalize_diff() / normalize_tree() -- strip protocol fingerprints from a
   unified diff or a final file tree: `.forge/` artifacts (whole file/hunk
   dropped), `fg-xxxx` task-record references, forge-*/persona-name
   verifier language, Attempt-log phrasing, EARS-clause echoes, commit
   trailers, and branch/worktree-run path segments (`bench/wt/...`).
   Stripping is scoped to metadata (diff headers, commit-message preamble,
   trailers, and comment spans) -- a non-comment code/context line is never
   touched, so a hunk carrying no fingerprinted comment comes out
   byte-identical to its input. This is deliberately narrower than a
   "redact this word everywhere" pass: several persona names (Doc, Blue,
   Page, Rune, ...) are ordinary English words that could legitimately
   appear in real ledgerkit source, and D5 itself scopes the language strip
   to "comments and commit messages" -- never code semantics.

2. shuffle_pair() -- normalize both arms' diffs, give each an opaque label
   deterministic from a recorded seed (same (task, seed) -> same label,
   every run), and present the pair in a seeded-random order. The returned
   presentation carries no arm identity; only the second return value does.

Bounce 1 (fg-a10404 verify FAIL, JUDGMENT) widened the fingerprint list to
mirror tools/telemetry.py's own recognized grammar -- a de-blind attack
recovered arm identity from Attempt-log/Routing-record vocabulary that the
first pass didn't strip: TIER_RE (`sonnet/high`-style tokens), VERDICT_RE
(`PASS`/`FAIL`/`ESCALATE`, including `PASS-after-filter`), TAG_RE
(`MECHANICAL`/`JUDGMENT`), JUDGE_YIELD_RE (`judge-yield: ... raised=N
survived=N changed=N` lines), free-standing verify/verdict/bounce/
re-verify/judge vocabulary, and in-comment `.forge/...` path references
(the whole prefix, not just an embedded fg-id). See _TIER_RE etc. below.

Residuals NOT stripped (verifier-classified as outside D5's explicit
"protocol fingerprints" list; accept-and-disclose, same as the coding-style
leak above -- must be named in the eventual report's Limitations section
alongside it, not silently assumed clean):
  - bare "Forge" / "forge.md" mentions (not a protocol marker on their own;
    a real ledgerkit doc could legitimately say "for" or reference an
    unrelated "forge" concept -- stripping the bare word risks the code-
    byte-identity guarantee for no clear fingerprint gain).
  - `sess-<hex>`-style session ids (no such id class appears in D5's list;
    add if/when the design names one).
  - spawn-contract vocabulary (`ROUTING:`, `CONTEXT PACK`, etc.) -- these
    are dispatcher-prompt artifacts, not diff/tree content D5 describes.
  - lowercase persona names (`_PERSONA_RE` is case-sensitive by design --
    the roster's own casing is always capitalized in practice; a
    deliberately-lowercased fingerprint is a residual gap, not a design
    goal, since case-insensitive persona matching would start colliding
    with ordinary lowercase English words like "doc", "page", "blue").
  - the naive `#`-in-string-literal comment detector (`_is_comment_only` /
    the `content.find("#")` split): a `#` inside a real string literal
    (e.g. `"#123"`) is misclassified as a comment start and its tail gets
    scrubbed. Acceptable for the Python-only synthetic `ledgerkit` fixture
    (D1) but not fully general.

3. write_sealed_key() -- persist the label -> (task, arm) map returned by
   shuffle_pair() to SEALED_KEY_DIR/<runid>.sealed.json.

   *** THIS IS THE T7 DENY PATH ***
   `tools/benchmark/sealed/` (SEALED_KEY_DIR below) MUST appear in the
   blinded-auditor spawn contract's denylist (T7; D5: "the auditor spawn's
   contract excludes that path"). This module does not and cannot enforce
   that denial itself -- a spawn contract is configured outside this
   module's reach -- so this docstring plus the SEALED_KEY_DIR constant are
   the single documented source of the exact path T7 must deny.
   Note for whoever authors T7/T3: design doc D5 illustrates the sealed-key
   path as `bench/keys/<runid>.sealed.json`; this task's spawn contract
   instead pinned `tools/benchmark/sealed/` as the actual path to use and
   deny. Whichever component (runner.py, T3) ends up calling
   write_sealed_key(), it must not override `base_dir` away from
   SEALED_KEY_DIR, or T7's denylist and the real write path will diverge --
   flagged for the verifier and for T7's author to reconcile explicitly.
"""
import hashlib
import json
import pathlib
import random
import re

# The T7 deny path -- see module docstring above. Consumed by whoever wires
# the blinded-auditor spawn contract's path denylist; keep this constant
# and that denylist in sync by hand (no automated cross-check exists across
# a spawn contract and a Python constant).
SEALED_KEY_DIR = "tools/benchmark/sealed"

# Forge agent slugs (tools/telemetry.py AGENT_SLUGS). Restated rather than
# imported: this module stays dependency-free of the live protocol runtime
# (docs/conventions.md, "scripts are accelerators" -- Python being absent
# or drifting must never break blinding). Keep in sync with telemetry.py by
# hand if the roster changes.
_AGENT_SLUGS = (
    "forge-worker", "forge-verifier", "forge-ui-verifier", "forge-reviewer",
    "forge-security", "forge-legal", "forge-architect", "forge-debugger",
    "forge-ui", "forge-animator", "forge-test-writer", "forge-researcher",
    "forge-migrator", "forge-scout", "forge-mapper", "forge-librarian",
    "forge-spec-writer", "forge-triage", "forge-data",
)

# Roster persona display names (fg-9f0101, docs/conventions.md "Dispatch
# display labels -- persona amendment"). Several are ordinary English words
# (Doc, Blue, Page, Rune, Hex, Tern, Sage, Scout, Atlas, ...) -- stripping
# is scoped to comment/metadata text only (see _neutralize call sites), so
# real code content that happens to use one of these words is untouched.
_PERSONA_NAMES = (
    "Orn", "Brokk", "Vera", "Iris", "Rook", "Aegis", "Lex", "Blue", "Hex",
    "Pixel", "Flux", "Tess", "Sage", "Tern", "Scout", "Atlas", "Page",
    "Quill", "Doc", "Rune",
)

_FG_ID_RE = re.compile(r"\bfg-[0-9a-f]{4,8}\b", re.I)
_AGENT_SLUG_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(s) for s in _AGENT_SLUGS) + r")\b"
)
_PERSONA_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in _PERSONA_NAMES) + r")\b"
)
# Precise Attempt-log grammar (docs/conventions.md "Telemetry vocabulary",
# tools/telemetry.py DISPATCH_RE/VERIFY_RE/BOUNCE_RE) rather than a bare
# "attempt \d+" -- a generic dev comment like "# attempt 3 different
# strategies" must not be treated as a protocol fingerprint.
_ATTEMPT_LOG_RE = re.compile(
    r"attempt \d+:?\s*(?:dispatched|verify|re-verify|verdict|\(bounce)",
    re.I,
)
_EARS_RE = re.compile(r"WHEN\b.*THE SYSTEM SHALL\b.*")
_RUN_PATH_RE = re.compile(r"bench/wt/[\w./-]+")
_TRAILER_RE = re.compile(r"(?i)^co-authored-by:.*$")
_BRANCH_HEADER_RE = re.compile(r"(?i)^(?:branch|from):\s*.*$")
# An in-comment reference to a .forge/ path (e.g. "see .forge/queue/tasks/
# fg-xxxx.md") -- distinct from the whole-hunk .forge/ drop in
# normalize_diff, which handles an actual .forge/ *file diff*. This catches
# the path when it's merely *mentioned* inside a comment/message line, so
# the fg-id inside it isn't the only thing stripped (bounce 1, finding 2).
# Matches both path separators (bounce 2, MECHANICAL): this repo lives at
# D:\forge on Windows, so a comment referencing a Windows-style
# ".forge\queue\tasks\..." path is just as realistic as the POSIX form and
# must not survive as an unambiguous Forge-repo prefix either.
_FORGE_PATH_RE = re.compile(r"\.forge[\\/][\w.\\/-]*")

# --- Mirrored from tools/telemetry.py (source of truth for the Attempt-log
# / Routing-record grammar, docs/conventions.md "Telemetry vocabulary").
# Bounce 1 (verify FAIL, JUDGMENT): a de-blind attack recovered arm
# identity from exactly these telemetry-recognized tokens surviving
# normalization. Kept as literal copies rather than an import so this
# module stays dependency-free of the live protocol runtime
# (docs/conventions.md "scripts are accelerators"); keep both files' regex
# literals in sync by hand if that grammar changes. ---
_TIER_RE = re.compile(r"\b(haiku|sonnet|opus|fable)/(low|medium|high)\b")
_VERDICT_RE = re.compile(r"\b(PASS|FAIL|ESCALATE)\b")
_PASS_AFTER_FILTER_RE = re.compile(r"\bPASS-after-filter\b", re.I)
_TAG_RE = re.compile(r"\b(MECHANICAL|JUDGMENT)\b", re.I)
_JUDGE_YIELD_RE = re.compile(
    r"^judge-yield:\s*([a-z][a-z0-9-]*)\s+raised=(\d+)\s+survived=(\d+)\s+changed=(\d+)\s*$",
    re.I,
)

# Free-standing verify/verdict/bounce/re-verify/judge vocabulary (bounce 1,
# finding 3+4): the Attempt-log/Routing-record grammar above only catches
# these words in their strict structural forms (e.g. "attempt N verify:").
# Prose like "the verifier should have caught this ... via bounce" or
# "judge yielded PASS" carries the same fingerprint outside that grammar.
# Scoped, like everything else here, to comment/metadata spans only.
_VOCAB_WORDS = (
    "verify", "verifies", "verified", "verifying",
    "verifier", "verifiers",
    "re-verify", "re-verifies", "re-verified", "re-verifying",
    "verdict", "verdicts",
    "bounce", "bounces", "bounced", "bouncing",
    "judge", "judges", "judged", "judging",
)
_VOCAB_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in _VOCAB_WORDS) + r")\b", re.I
)

_DIFF_GIT_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)")


def _neutralize(text):
    """Redact protocol-fingerprint spans from a single line of text (a
    message line, or the comment portion of a hunk-content line). Never
    called on a whole multi-line blob -- keeps every regex's match scope to
    one line, so there is no risk of a runaway multi-line match swallowing
    unrelated content.
    """
    # Placeholder tokens are deliberately chosen so NONE of them contains a
    # whole word any later regex in this pipeline would itself flag (e.g.
    # "[verdict]" would be re-caught by _VOCAB_RE's "verdict" entry two
    # lines later, double-bracketing it) -- each sub below runs exactly
    # once over the string, never re-matched by a subsequent pass.

    # Whole-line telemetry grammar first (judge-yield:), before any other
    # sub disturbs the anchored ^...$ shape it matches on.
    text = _JUDGE_YIELD_RE.sub("[telemetry-line]", text)
    # In-comment .forge/ path mentions before the bare fg-id strip, so the
    # whole path prefix is consumed as one token (bounce 1, finding 2)
    # rather than leaving ".forge/queue/tasks/" behind once only the
    # embedded id is gone.
    text = _FORGE_PATH_RE.sub("[forge-path]", text)
    text = _FG_ID_RE.sub("[task-ref]", text)
    text = _AGENT_SLUG_RE.sub("[agent]", text)
    text = _PERSONA_RE.sub("[persona]", text)
    text = _ATTEMPT_LOG_RE.sub("[attempt-log]", text)
    text = _EARS_RE.sub("[ears-clause]", text)
    text = _RUN_PATH_RE.sub("[run-path]", text)
    text = _TIER_RE.sub("[model-tier]", text)
    # PASS-after-filter before the bare PASS/FAIL/ESCALATE strip -- VERDICT_RE
    # would otherwise consume "PASS" and leave a stray "-after-filter"
    # behind (same ordering rationale as tools/telemetry.py PASS_AFTER_FILTER_RE).
    text = _PASS_AFTER_FILTER_RE.sub("[outcome]", text)
    text = _VERDICT_RE.sub("[outcome]", text)
    text = _TAG_RE.sub("[class-tag]", text)
    text = _VOCAB_RE.sub("[protocol-term]", text)
    return text


def _is_comment_only(text):
    return text.lstrip().startswith("#")


def _scrub_message_line(line):
    """Scrub a line that lives outside any diff hunk (commit-message
    preamble, diff/index/+++/--- /@@ headers). Returns None if the whole
    line is pure metadata worth dropping outright (a co-author trailer or a
    Branch:/From: header) rather than merely redacting a span within it.
    """
    if _TRAILER_RE.match(line) or _BRANCH_HEADER_RE.match(line):
        return None
    return _neutralize(line)


def _scrub_hunk_content_line(line):
    """Scrub a diff hunk content line (starts with '+', '-', or ' ').
    Fingerprint stripping is scoped to the comment portion of the line --
    a whole-line comment gets fully neutralized, an inline `# ...` tail
    gets neutralized while the code before it is untouched, and a line with
    no '#' at all is returned byte-identical (D5: "strips metadata, never
    alters semantics").
    """
    marker, content = line[0], line[1:]
    if _is_comment_only(content):
        return marker + _neutralize(content)
    hash_idx = content.find("#")
    if hash_idx == -1:
        return line
    return marker + content[:hash_idx] + _neutralize(content[hash_idx:])


def normalize_diff(diff_text):
    """Strip protocol fingerprints from a unified diff (D5 mechanism 1).
    See module docstring for the full scrub list. `None`/`""` pass through
    unchanged (never raises on the "no diff" case a clean arm-run can
    legitimately produce).
    """
    if not diff_text:
        return diff_text

    lines = diff_text.split("\n")
    trailing_newline = diff_text.endswith("\n")
    if trailing_newline:
        lines = lines[:-1]  # split() gives a trailing "" for a final \n

    out = []
    skipping = False
    for line in lines:
        m = _DIFF_GIT_RE.match(line)
        if m:
            a_path, b_path = m.group(1), m.group(2)
            skipping = a_path.startswith(".forge/") or b_path.startswith(".forge/")
            if skipping:
                continue
            out.append(_neutralize(line))
            continue
        if skipping:
            continue  # still inside the dropped file's diff block
        if line[:1] in ("+", "-", " ") and not line.startswith(("+++ ", "--- ")):
            out.append(_scrub_hunk_content_line(line))
            continue
        scrubbed = _scrub_message_line(line)
        if scrubbed is not None:
            out.append(scrubbed)

    text = "\n".join(out)
    if trailing_newline and out:
        text += "\n"
    return text


def normalize_tree(files):
    """Strip protocol fingerprints from a final file tree (D5 mechanism 1,
    applied to the tree form of an arm's output rather than a diff).
    `files` is a mapping of repo-relative path -> file content (str).
    Returns a new mapping with:
    - every path under `.forge/` dropped entirely (same rationale as the
      dropped-hunk case in normalize_diff: defense in depth against a
      `.forge/` artifact leaking into an arm's final tree, on top of D4's
      isolation which should already keep it out).
    - comment-only / inline-comment spans fingerprint-scrubbed line by
      line, using the identical rule normalize_diff applies to hunk-content
      lines.
    - every other line byte-identical to the input.
    """
    out = {}
    for path, content in files.items():
        if path == ".forge" or path.startswith(".forge/") or "/.forge/" in path:
            continue
        lines = content.split("\n")
        trailing_newline = content.endswith("\n")
        if trailing_newline:
            lines = lines[:-1]
        scrubbed = []
        for line in lines:
            if _is_comment_only(line):
                scrubbed.append(_neutralize(line))
                continue
            hash_idx = line.find("#")
            if hash_idx == -1:
                scrubbed.append(line)
            else:
                scrubbed.append(line[:hash_idx] + _neutralize(line[hash_idx:]))
        new_content = "\n".join(scrubbed)
        if trailing_newline:
            new_content += "\n"
        out[path] = new_content
    return out


def make_label(task_id, arm, seed):
    """Deterministic opaque label for a (task, arm) pair, derived from
    `seed`. Same (task_id, arm, seed) always yields the same label
    (reproducible runs, D3's manifest-recording requirement); a different
    seed yields a different label, so a label alone -- without the sealed
    key -- never leaks which arm it names.
    """
    digest = hashlib.sha256(f"{seed}:{task_id}:{arm}".encode("utf-8")).hexdigest()
    return f"diff-{digest[:4]}"


def shuffle_pair(task_id, diff_a, diff_b, seed):
    """Normalize both arms' diffs, assign each an opaque deterministic
    label, and return them in a seeded-random presentation order (D5
    mechanism 2).

    Returns (presented, sealed_key):
      presented   -- [(label, normalized_diff), (label, normalized_diff)]
                      in presentation order; carries NO arm identity.
      sealed_key  -- {label: {"task": task_id, "arm": "A"|"B"}} -- the only
                      place arm identity survives this call. The caller is
                      responsible for persisting it via write_sealed_key()
                      to SEALED_KEY_DIR, and for never handing it (or this
                      return value) to the blinded auditor.
    """
    label_a = make_label(task_id, "A", seed)
    label_b = make_label(task_id, "B", seed)
    entries = [
        (label_a, normalize_diff(diff_a), "A"),
        (label_b, normalize_diff(diff_b), "B"),
    ]
    rng = random.Random(f"{seed}:{task_id}")
    rng.shuffle(entries)

    presented = [(label, diff) for label, diff, _arm in entries]
    sealed_key = {
        label: {"task": task_id, "arm": arm} for label, _diff, arm in entries
    }
    return presented, sealed_key


def write_sealed_key(runid, sealed_key, base_dir=SEALED_KEY_DIR):
    """Persist a label -> (task, arm) map to
    <base_dir>/<runid>.sealed.json (default SEALED_KEY_DIR -- the exact T7
    deny path; see module docstring). A run covers many task pairs, each
    calling shuffle_pair() once, so this merges into any existing file for
    the same runid rather than clobbering earlier pairs' entries. Malformed
    or missing existing content is treated as empty rather than raising --
    a corrupt prior write must not block sealing the current pair.
    """
    base_dir = pathlib.Path(base_dir)
    path = base_dir / f"{runid}.sealed.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = {}

    existing.update(sealed_key)
    path.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
    return path
