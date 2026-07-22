"""Validate Forge task files against docs/conventions.md ("Task files",
docs/conventions/artifact-formats.md, fg-b0401). Zero dependencies."""
import re, sys, pathlib

# Ensure the sibling validate_spec module resolves under both invocation
# forms (direct script run and `python -m`), mirroring validate_all.py's
# same sys.path guard.
_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import validate_spec

REQUIRED_FIELDS = ["id", "title", "state", "tier", "priority", "spec", "blocks",
                   "blocked-by", "claimed-by", "parallel-safe", "created", "updated"]
STATES = {"backlog", "ready", "active", "blocked", "done", "dropped"}
TIERS = {"trivial", "standard", "full"}
PRIORITIES = {"1", "2", "3", "4"}
SECTIONS = ["## Acceptance criteria", "## Execution plan", "## Routing record",
            "## Attempt log", "## Outcome"]
ID_RE = re.compile(r"^fg-[0-9a-f]{4,8}$")
# Readable name ids (spec-f0c2 Amendments — 2026-07-20, item 2): kebab-case,
# 3-40 chars total, first/last char alnum -- '--' runs are rejected
# separately below rather than in the regex, so the two shape rules stay
# independently readable/testable.
NAME_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
SUPPORTED_SCHEMA = 1
BUGFIX_RE = re.compile(r"\b(fix|bug|regression|broken|crash)\b", re.I)
CLAIMED_BY_RE = re.compile(
    r"^sess-[0-9a-f]{4} @ \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$")

# The only frontmatter fields that are ever list-shaped -- both the inline
# "[a, b]" bracket parsing AND the multiline "  - item" continuation parsing
# are scoped to this exact set, so a scalar field (e.g. `state`, `id`,
# `title`) hand-edited into either list shape degrades to a clean per-field
# error downstream instead of crashing on `TypeError: unhashable type: 'list'`
# (fg-9a0305 covered the inline case; the multiline case is the same bug).
_LIST_FIELDS = ("blocks", "blocked-by", "shard-key")

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)
_FENCE_RE = re.compile(r"^ {0,3}`{3,}")
_LIST_ITEM_RE = re.compile(r"^[ \t]+-\s?(.*)$")
_ID_LINE_RE = re.compile(r"(?m)^id:\s*(.+?)\s*$")


def _unquote(val):
    """Strip a single layer of matching leading/trailing quotes from a scalar."""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _parse_inline_list(val):
    """Parse a '[a, b, c]' inline flow-style YAML list into a Python list.

    Empty items (e.g. a trailing comma) are preserved as empty strings so
    callers can flag them as a shape error rather than silently dropping
    them. An empty "[]" parses to an empty list.
    """
    inner = val[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(",")]


def _is_name_id(val):
    """True if `val` is a valid readable name id: kebab-case, 3-40 chars,
    first/last char alnum, no '--' run anywhere (spec-f0c2 Amendments item 2).
    """
    return bool(isinstance(val, str) and NAME_ID_RE.match(val) and "--" not in val)


def _is_valid_id(val):
    """True if `val` is either a legacy hex id (fg-xxxx, grandfathered
    permanently -- never renamed) or a new-style readable name id."""
    return bool(isinstance(val, str) and (ID_RE.match(val) or _is_name_id(val)))


def _name_id_near_miss(val):
    """True if `val` looks like a botched attempt at a readable name id --
    same shape (alnum/hyphen/underscore/space, 3-40 chars, alnum ends) but
    disqualified only by uppercase, underscores, or spaces: normalizing
    those away would make it a valid name id. Used to WARN (never fail) with
    a more specific nudge than the bare "bad id" error.
    """
    if not isinstance(val, str) or not (3 <= len(val) <= 40):
        return False
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_ -]*[A-Za-z0-9]$", val):
        return False
    if not (any(c.isupper() for c in val) or "_" in val or " " in val):
        return False
    normalized = val.lower().replace("_", "-").replace(" ", "-")
    return _is_name_id(normalized)


def _sibling_task_ids(path):
    """Return the set of frontmatter `id` values found in every *.md file
    in `path`'s own directory (path's own id included -- harmless, since
    callers only look up ids referenced by *other* fields like blocked-by).
    """
    ids = set()
    try:
        directory = pathlib.Path(path).resolve().parent
    except OSError:
        return ids
    for p in directory.glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        m = _ID_LINE_RE.search(text)
        if m:
            ids.add(_unquote(m.group(1)))
    return ids


def _forge_root(path):
    """Return the resolved `.forge/` directory `path` (a task file) lives
    under, or None if no ancestor directory is literally named `.forge`
    (case-insensitive, matching the case-insensitive `.forge`-ancestry
    convention used elsewhere, e.g. validate_all.py's `_route_paths`).

    Callers use this to resolve a `spec:` field's `specs/<file>.md` path
    (documented as relative to `.forge/`, docs/conventions.md:310). A task
    file that isn't nested under any `.forge/` (e.g. a standalone fixture in
    a test's own temp directory) yields None -- callers must then skip the
    spec-existence/status check entirely rather than raise or misreport,
    since there is no `.forge/` to resolve the reference against.
    """
    try:
        resolved = pathlib.Path(path).resolve()
    except OSError:
        return None
    for parent in resolved.parents:
        if parent.name.lower() == ".forge":
            return parent
    return None


def _parse_frontmatter(text):
    """Parse the '---' frontmatter block.

    Returns (fields, errors, body) where:
      - fields is None (and body is None) if no frontmatter block is found
        at all -- callers treat that as "missing or malformed frontmatter".
      - errors is a list of targeted per-line problems (malformed line,
        duplicate key) found *within* an otherwise-parseable block; these no
        longer null out the whole parse.
      - body is the text following the closing '---' fence, i.e. everything
        that isn't frontmatter. Section/header detection must search body,
        never the raw frontmatter block, so a decoy heading-like line inside
        a frontmatter comment can never be mistaken for a real doc header.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None, [], None
    fields = {}
    errors = []
    seen = set()
    last_key = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        list_m = _LIST_ITEM_RE.match(line)
        if list_m and last_key in _LIST_FIELDS:
            item = _unquote(list_m.group(1).strip())
            existing = fields.get(last_key)
            if isinstance(existing, list):
                existing.append(item)
            else:
                fields[last_key] = [item] if existing in ("", None) else [existing, item]
            continue
        if list_m:
            # A continuation-shaped line under a non-list `last_key` is
            # malformed regardless of whether it happens to contain a colon
            # -- letting a colon-containing continuation fall through to
            # ordinary key:value parsing would silently smuggle a garbage
            # frontmatter key in with zero errors (fg-a11030).
            errors.append(f"malformed frontmatter line: {line.strip()!r}")
            continue
        if ":" not in line:
            errors.append(f"malformed frontmatter line: {line.strip()!r}")
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        # Inline-list parsing is scoped to the known list-typed fields only:
        # a bracketed value on a scalar field (e.g. `id: [x]`) must stay a
        # string so the field's own format check reports it cleanly instead
        # of a type crash downstream (fg-9a0305).
        if key in _LIST_FIELDS and \
                val.startswith("[") and val.endswith("]"):
            val = _parse_inline_list(val)
        elif key in _LIST_FIELDS and \
                (val.startswith("[") or val.endswith("]")):
            # An unclosed/unopened inline list (e.g. a dropped closing
            # bracket) must never silently degrade to a raw string -- that
            # opaque string then fails every `isinstance(x, list)` check
            # downstream and both the dependency and its DAG edge vanish
            # without a trace (inquest C-7).
            errors.append(
                f"malformed {key!r} inline list: {val!r} (unclosed bracket)")
            val = _unquote(val)
        else:
            val = _unquote(val)
        if key in seen:
            errors.append(f"duplicate frontmatter key: {key!r}")
        seen.add(key)
        fields[key] = val
        last_key = key
    return fields, errors, text[m.end():]


def _mask_fences(text):
    """Blank the contents of fenced ``` code blocks while preserving line
    count and character offsets, so a heading that only appears inside a
    code sample never counts as a real section header."""
    lines = text.splitlines(keepends=True)
    out = []
    in_fence = False
    for line in lines:
        body = line.rstrip("\r\n")
        ending = line[len(body):]
        if _FENCE_RE.match(body):
            in_fence = not in_fence
            out.append(line)
        elif in_fence:
            out.append(" " * len(body) + ending)
        else:
            out.append(line)
    return "".join(out)


def _has_section(text, section):
    """True only if `section` appears as a real line-start header outside any
    fenced code block -- not as inline prose and not inside a ``` sample."""
    masked = _mask_fences(text)
    return re.search(r"(?m)^" + re.escape(section) + r"\s*$", masked) is not None


def _section_body(text, section):
    """Return the text between `section`'s real (line-anchored, fence-aware)
    header and the next top-level '## ' header, or None if no real header
    for `section` is present."""
    masked = _mask_fences(text)
    m = re.search(r"(?m)^" + re.escape(section) + r"\s*$", masked)
    if not m:
        return None
    start = m.end()
    next_m = re.search(r"(?m)^## ", masked[start:])
    end = start + next_m.start() if next_m else len(text)
    # Return the FENCE-MASKED substring, not the original -- otherwise a
    # documentation/example fence *within* a real section (e.g. a fenced
    # EARS-clause sample under "## Acceptance criteria") would let its
    # example text satisfy content checks that must only see real, unfenced
    # section content.
    return masked[start:end]


def validate(path, warnings=None):
    """Validate one task file. Returns the error list (unchanged contract).

    If `warnings` is a list, advisory warning strings are appended to it.
    Warnings never affect the returned errors or the exit code.
    """
    errors = []
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        return [f"{path}: cannot read file: {e}"]

    fm, fm_errors, body = _parse_frontmatter(text)
    if fm is None:
        return [f"{path}: missing or malformed frontmatter"]
    errors.extend(fm_errors)

    for field in REQUIRED_FIELDS:
        if field not in fm:
            errors.append(f"missing field: {field}")
    if "id" in fm and not _is_valid_id(fm["id"]):
        errors.append(
            f"bad id: {fm['id']!r} (want a legacy fg-xxxx hex id, or a "
            "readable kebab-case name id: 3-40 chars, "
            "[a-z0-9][a-z0-9-]*[a-z0-9], no '--', e.g. database-migration)")
        if warnings is not None and _name_id_near_miss(fm["id"]):
            warnings.append(
                f"{path}: id {fm['id']!r} looks like a near-miss on a "
                "readable name id (uppercase/underscore/space) -- want "
                "lowercase kebab-case, e.g. database-migration")
    elif (
        "id" in fm
        and warnings is not None
        and isinstance(fm["id"], str)
        and fm["id"].startswith("fg-")
        and not ID_RE.match(fm["id"])
    ):
        # fg-a11030-era typo guard: a hex-looking id with a non-hex char
        # (fg-c01o1) is now a VALID name id -- warn so the author notices
        # the likely typo instead of silently minting a pseudo-hex name.
        warnings.append(
            f"{path}: id {fm['id']!r} starts with the legacy 'fg-' prefix "
            "but is not a valid hex id -- accepted as a readable name id; "
            "if a hex id was intended, check for typos, and prefer "
            "descriptive names without the legacy prefix for new ids")
    if not fm.get("title"):
        errors.append("title must be non-empty")
    if fm.get("state") not in STATES:
        errors.append(f"bad state: {fm.get('state')!r}")
    if fm.get("tier") not in TIERS:
        errors.append(f"bad tier: {fm.get('tier')!r}")
    if fm.get("priority") not in PRIORITIES:
        errors.append(f"bad priority: {fm.get('priority')!r}")
    if fm.get("tier") == "full" and fm.get("spec") in (None, "null", ""):
        errors.append("full tier requires non-null spec")
    elif fm.get("tier") == "full" and isinstance(fm.get("spec"), str):
        # Existence + approved-status check (fg-a11019): only meaningful
        # when the task file is nested under a real `.forge/` (see
        # `_forge_root`'s docstring) -- a standalone fixture outside any
        # `.forge/` tree has no `specs/` to resolve the reference against,
        # so the check is skipped rather than misreported.
        forge_root = _forge_root(path)
        if forge_root is not None:
            spec_path = forge_root / fm["spec"]
            if not spec_path.is_file():
                errors.append(
                    f"tier full spec file not found: {fm['spec']!r} "
                    f"(resolved to {spec_path})")
            else:
                try:
                    spec_text = spec_path.read_text(encoding="utf-8-sig")
                except (OSError, UnicodeDecodeError) as e:
                    errors.append(f"tier full spec file unreadable: "
                                  f"{fm['spec']!r} ({e})")
                else:
                    spec_fm, _, _ = validate_spec._parse_frontmatter(spec_text)
                    spec_status = spec_fm.get("status") if spec_fm else None
                    if spec_status != "approved":
                        errors.append(
                            f"tier full spec must be status: approved "
                            f"(spec: {fm['spec']!r} is {spec_status!r})")
    if "parallel-safe" in fm and fm["parallel-safe"] not in ("true", "false"):
        errors.append(
            f"bad parallel-safe: {fm['parallel-safe']!r} (want true or false)")

    # blocks/blocked-by must resolve to an actual list -- a bare unbracketed
    # scalar (e.g. `blocks: fg-0002`) parses as a raw string, which
    # downstream tools/queue_graph.py then wraps as ONE opaque list element,
    # silently breaking the dependency DAG with no error reported anywhere.
    for field in ("blocks", "blocked-by"):
        val = fm.get(field)
        if val not in (None, "") and not isinstance(val, list):
            errors.append(
                f"{field} must be a bracketed list, e.g. [fg-0001, fg-0002] "
                f"(got {val!r})")

    # -- shard-by / max-shards / shard-key (fg-a10811) --
    # All three are OPTIONAL and orthogonal to parallel-safe -- a task may
    # declare both; the predicate that SELECTS shard-eligible tasks lives in
    # the kernel/conventions, not here. This block only shape-checks: a task
    # that omits all three fields takes none of these branches and validates
    # exactly as it did before this change. NO cmd: shard source in v1
    # (deferred per the OQ2 security decision) -- it is deliberately never
    # referenced below.
    shard_by_raw = fm.get("shard-by")
    shard_by = None
    if shard_by_raw not in (None, ""):
        if isinstance(shard_by_raw, str) and shard_by_raw in \
                ("files", "items", "ranges"):
            shard_by = shard_by_raw
        else:
            errors.append(
                f"bad shard-by: {shard_by_raw!r} "
                "(want one of: files, items, ranges)")

    max_shards_raw = fm.get("max-shards")
    if shard_by is not None and max_shards_raw in (None, ""):
        errors.append("shard-by requires max-shards (an integer >= 2)")
    if max_shards_raw not in (None, ""):
        max_shards_int = None
        if isinstance(max_shards_raw, str):
            try:
                max_shards_int = int(max_shards_raw)
            except ValueError:
                max_shards_int = None
        if max_shards_int is None or max_shards_int < 2:
            errors.append(
                f"bad max-shards: {max_shards_raw!r} (want an integer >= 2)")

    if shard_by in ("items", "ranges"):
        shard_key_raw = fm.get("shard-key")
        if shard_key_raw in (None, ""):
            errors.append(
                f"shard-by: {shard_by} requires shard-key "
                "(a scalar string, not a list)")
        elif not isinstance(shard_key_raw, str):
            errors.append(
                f"bad shard-key: {shard_key_raw!r} "
                "(want a scalar string, not a list)")

    schema_version = fm.get("schema-version")
    if schema_version not in (None, ""):
        try:
            schema_version = int(schema_version)
        except (TypeError, ValueError):
            errors.append(f"bad schema-version: {fm['schema-version']!r} "
                          "(want an integer)")
        else:
            if schema_version > SUPPORTED_SCHEMA:
                errors.append(
                    f"produced by a newer Forge (schema-version "
                    f"{schema_version} > {SUPPORTED_SCHEMA}) — upgrade the plugin")
            elif schema_version < 1:
                errors.append(
                    f"bad schema-version: {schema_version!r} "
                    "(want an integer >= 1)")

    claimed = fm.get("claimed-by", "null")
    if fm.get("state") == "active" and claimed in ("null", ""):
        errors.append("active task requires claimed-by")
    if fm.get("state") != "active" and claimed not in ("null", ""):
        errors.append("non-active task must have claimed-by: null")
    if (isinstance(claimed, str) and claimed not in ("null", "")
            and not CLAIMED_BY_RE.match(claimed)):
        errors.append(
            f"bad claimed-by format: {claimed!r} "
            "(want 'sess-xxxx @ <ISO-8601>', e.g. "
            "'sess-ab12 @ 2026-07-16T10:00:00Z')")

    for section in SECTIONS:
        if not _has_section(body, section):
            errors.append(f"missing section: {section}")

    if all(_has_section(body, section) for section in SECTIONS):
        masked = _mask_fences(body)
        positions = []
        for section in SECTIONS:
            m = re.search(r"(?m)^" + re.escape(section) + r"\s*$", masked)
            positions.append(m.start() if m else -1)
        if positions != sorted(positions):
            for i in range(1, len(positions)):
                if positions[i] < positions[i - 1]:
                    errors.append(
                        f"section out of order: {SECTIONS[i]!r} must come after "
                        f"{SECTIONS[i - 1]!r} (expected order: "
                        f"{' -> '.join(SECTIONS)})")
                    break

    if fm.get("state") in STATES - {"backlog"}:
        section_body = _section_body(body, "## Acceptance criteria")
        if section_body is None or "THE SYSTEM SHALL" not in section_body:
            errors.append("needs at least one EARS clause (THE SYSTEM SHALL) "
                          "for non-backlog state")

    if warnings is not None and fm.get("tier") == "trivial":
        criteria = _section_body(body, "## Acceptance criteria") or ""
        title = fm.get("title", "")
        if not isinstance(title, str):
            title = ""
        if BUGFIX_RE.search(title) or BUGFIX_RE.search(criteria):
            warnings.append(
                f"{path}: trivial tier with bug-fix language — bug fixes "
                "normally need tier: standard + a regression test "
                "(constitution rule)")

    if warnings is not None:
        for field in ("created", "updated"):
            val = fm.get(field)
            if isinstance(val, str) and val and not DATE_RE.match(val):
                warnings.append(
                    f"{path}: {field} does not look like an ISO-8601 date: "
                    f"{val!r}")

    # blocks gets the same sibling-existence warning blocked-by already has
    # (inquest C-8) -- a dangling forward reference is just as much a sign
    # of drift as a dangling backward one, and the two fields describe the
    # same edge from opposite ends.
    sibling_ids = None
    for field in ("blocked-by", "blocks"):
        refs = fm.get(field)
        if warnings is not None and isinstance(refs, list) and refs:
            if sibling_ids is None:
                sibling_ids = _sibling_task_ids(path)
            for bid in refs:
                bid = bid.strip() if isinstance(bid, str) else bid
                if bid and bid not in sibling_ids:
                    warnings.append(
                        f"{path}: {field} references {bid!r}, which has no "
                        "matching task file in this directory (offline "
                        "merges can be legitimately in flux)")

    return [f"{path}: {e}" for e in errors]


def _task_dir_debris(task_dir):
    """Return warning strings for entries in `task_dir` that are invisible to
    every validator's `*.md` glob: non-`.md` files, and `.md` files that are
    zero bytes. These are debris (e.g. a truncated `/forge:add` write), not
    malformed tasks -- they are surfaced as a WARNING, never an error, and
    never parsed (docs/audits/2026-07-17-sweep2-hygiene.md, Part A2).

    Only file entries are considered; a missing or unreadable directory
    yields no warnings (never raises)."""
    warnings = []
    try:
        entries = sorted(pathlib.Path(task_dir).iterdir())
    except OSError:
        return warnings
    for entry in entries:
        if not entry.is_file():
            continue
        is_debris = entry.suffix.lower() != ".md" or entry.stat().st_size == 0
        if is_debris:
            warnings.append(f"non-task debris in queue/tasks: {entry.name}")
    return warnings


def main(argv):
    # Some print() calls below carry em dashes; a legacy Windows OEM codepage
    # (cp437/cp850, still common as a non-interactive/piped-stdout default)
    # can't encode them and would otherwise crash mid-report with an
    # unhandled UnicodeEncodeError. Degrade to replacement characters
    # instead of crashing; best-effort only (never fatal if unsupported).
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    task_dir = pathlib.Path(".forge/queue/tasks")
    # A zero-byte *.md file matches the glob but is debris, not a task --
    # skip it here so it is only ever reported once, as a warning below, and
    # never handed to validate() to be parsed into a "malformed frontmatter"
    # error.
    paths = argv or [str(p) for p in task_dir.glob("*.md")
                     if p.stat().st_size > 0]
    all_errors = []
    all_warnings = []
    for p in paths:
        all_errors.extend(validate(p, warnings=all_warnings))
    if not argv:
        all_warnings.extend(_task_dir_debris(task_dir))
    for e in all_errors:
        print(e)
    for w in all_warnings:
        print(f"WARNING: {w}")
    print(f"{len(paths)} file(s) checked, {len(all_errors)} error(s), "
          f"{len(all_warnings)} warning(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
