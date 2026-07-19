"""Validate Forge spec files against docs/conventions.md. Zero dependencies."""
import re, sys, pathlib

REQUIRED_FIELDS = ["id", "title", "status", "created", "approved-date"]
STATUSES = {"draft", "approved", "superseded"}
SECTIONS = ["## Goal", "## Non-goals", "## Acceptance criteria", "## Risks",
            "## Task decomposition", "## Changelog"]
ID_RE = re.compile(r"^spec-[0-9a-f]{4,8}$")
CLARIFY = "[NEEDS CLARIFICATION]"
SUPPORTED_SCHEMA = 1

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)
_FENCE_RE = re.compile(r"^ {0,3}`{3,}")
_LIST_ITEM_RE = re.compile(r"^[ \t]+-\s?(.*)$")


def _unquote(val):
    """Strip a single layer of matching leading/trailing quotes from a scalar."""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


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
        if list_m and last_key is not None:
            item = _unquote(list_m.group(1).strip())
            existing = fields.get(last_key)
            if isinstance(existing, list):
                existing.append(item)
            else:
                fields[last_key] = [item] if existing in ("", None) else [existing, item]
            continue
        if ":" not in line:
            errors.append(f"malformed frontmatter line: {line.strip()!r}")
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = _unquote(val.strip())
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
    return text[start:end]


def validate(path):
    errors = []
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    except OSError as e:
        return [f"{path}: {e}"]

    fm, fm_errors, body = _parse_frontmatter(text)
    if fm is None:
        return [f"{path}: missing or malformed frontmatter"]
    errors.extend(fm_errors)

    for field in REQUIRED_FIELDS:
        if field not in fm:
            errors.append(f"missing field: {field}")
    if "id" in fm and not ID_RE.match(fm["id"]):
        errors.append(f"bad id: {fm['id']!r} (want spec-xxxx hex)")
    if fm.get("status") not in STATUSES:
        errors.append(f"bad status: {fm.get('status')!r}")

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

    approved_date = fm.get("approved-date", "null")
    if fm.get("status") in ("approved", "superseded") and approved_date in ("null", ""):
        errors.append(f"{fm.get('status')} spec requires non-null approved-date")
    if fm.get("status") == "draft" and approved_date not in ("null", ""):
        errors.append("draft spec must have approved-date: null")

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

    section_body = _section_body(body, "## Acceptance criteria")
    if section_body is None or "THE SYSTEM SHALL" not in section_body:
        errors.append("Acceptance criteria needs at least one EARS clause "
                      "(THE SYSTEM SHALL)")

    if fm.get("status") == "approved" and CLARIFY in text:
        errors.append("approved spec must not contain [NEEDS CLARIFICATION] markers")

    return [f"{path}: {e}" for e in errors]


def main(argv):
    paths = argv or [str(p) for p in
                     pathlib.Path(".forge/specs").glob("*.md")]
    all_errors = []
    for p in paths:
        all_errors.extend(validate(p))
    for e in all_errors:
        print(e)
    print(f"{len(paths)} file(s) checked, {len(all_errors)} error(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
