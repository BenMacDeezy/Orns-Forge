# tools/validate_memory.py
"""Validate Forge memory fact files against docs/conventions.md. Zero dependencies.

The optional `agents` field (fg-9a0101) tags a fact for auto-inclusion in a
named agent's spawn contracts. It must be a flat list of non-empty agent-name
strings -- a nested list (e.g. `[[a, b], c]`, or a multiline item that is
itself a `[a, b]`-shaped string) is rejected as "agents must be a flat list"
rather than silently mangled by the inline-list parser. An explicit empty
list (`agents: []`) is valid and equivalent to the field being absent
entirely -- both mean "no agent tags", and both validate with zero errors.

Craft-memory bleed check (fg-a10203): when `validate(path, warnings=...)` is
called on a fact in the plugin-level craft store (see `_craft_plugin_root`),
advisory WARNINGS -- never errors -- are appended for content that looks
like it bled in from a specific project: an absolute filesystem path outside
the plugin root, the repo owner's GitHub handle, or a reference to a plugin-
tree file that doesn't exist. See docs/conventions.md, "Craft-memory bleed
check — 2026-07" for the canonical pattern list and rationale.
"""
import re, sys, pathlib

REQUIRED_FIELDS = ["name", "description", "type", "created", "updated",
                   "superseded-by"]
TYPES = {"decision", "gotcha", "postmortem", "preference", "reference"}
SUPPORTED_SCHEMA = 1

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)
_LIST_ITEM_RE = re.compile(r"^[ \t]+-\s?(.*)$")

# The only frontmatter field that is ever list-shaped -- the multiline
# "  - item" continuation parsing is scoped to this set, so a scalar field
# (e.g. `type`, `name`, `description`) hand-edited into block-list form
# doesn't silently become a Python list and crash a downstream check.
_LIST_FIELDS = ("agents",)

# -- Craft-memory bleed patterns (docs/conventions.md, "Craft-memory bleed
# check — 2026-07") -- canonically a human-edited list, never derived from
# git config/environment, so the set of what counts as "bleed" is an
# explicit, reviewable decision rather than something that silently drifts
# with whoever's machine last touched it.
_URL_RE = re.compile(r"https?://\S+")
_DRIVE_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/][^\s\"')\]}><]*")
_FILE_REF_RE = re.compile(
    r"\b[\w][\w\-]*(?:/[\w\-.]+)+\.(?:py|md|ya?ml|json|sh|ts|tsx|js|jsx|txt|toml|cfg)\b")
# The repo owner's GitHub handle(s) -- edit this list by hand.
CRAFT_BLEED_HANDLES = ("hockeyben", "BenMacDeezy")
_HANDLE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(h) for h in CRAFT_BLEED_HANDLES) + r")\w*",
    re.I)


def _craft_plugin_root(path):
    """Return the plugin root Path if `path` is a fact in the plugin-level
    craft store (`<plugin-root>/memory/*.md`), else None.

    Derived from the path alone, same trick `docs/conventions.md`'s
    "Validator coverage" paragraph already relies on: a fact's parent
    directory named `memory` whose OWN parent is not `.forge` is the craft
    store; `.forge/memory/*.md` is always the project store and is never in
    scope for bleed checks. The `.forge` comparison is case-insensitive --
    a directory literally named `.Forge` (possible on a case-insensitive-
    but-preserving filesystem) must still be recognized as the project
    store, not misclassified as the craft store.
    """
    resolved = pathlib.Path(path).resolve()
    parent = resolved.parent
    if parent.name == "memory" and parent.parent.name.lower() != ".forge":
        return parent.parent
    return None


def _mask(text, pattern):
    """Blank out every match of `pattern` in `text`, preserving length, so a
    later scan can't re-match content already claimed by an earlier one
    (e.g. an already-flagged absolute path's own file extension shouldn't
    also trigger the file-reference check)."""
    return pattern.sub(lambda m: " " * len(m.group(0)), text)


def _is_outside(plugin_root, fragment):
    try:
        pathlib.Path(fragment).resolve().relative_to(plugin_root.resolve())
        return False
    except (ValueError, OSError):
        return True


def _craft_bleed_warnings(path, body, plugin_root):
    warnings = []
    masked = _mask(body, _URL_RE)

    for m in _DRIVE_PATH_RE.finditer(masked):
        frag = m.group(0).rstrip(" \t.,;:'\")]}")
        if not frag or not _is_outside(plugin_root, frag):
            continue
        warnings.append(
            f"{path}: craft-memory bleed — absolute path outside plugin "
            f"root: `{frag}`")
    masked = _mask(masked, _DRIVE_PATH_RE)

    for m in _HANDLE_RE.finditer(masked):
        warnings.append(
            f"{path}: craft-memory bleed — repo owner's GitHub handle: "
            f"{m.group(0)!r}")
    masked = _mask(masked, _HANDLE_RE)

    for m in _FILE_REF_RE.finditer(masked):
        frag = m.group(0)
        if (plugin_root / frag).exists():
            continue
        warnings.append(
            f"{path}: craft-memory bleed — file reference not found in "
            f"plugin tree: {frag!r}")

    return warnings


def _unquote(val):
    """Strip a single layer of matching leading/trailing quotes from a scalar."""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _parse_inline_list(val):
    """Parse a '[a, b, c]' inline flow-style YAML list into a Python list.

    Empty items (e.g. a trailing comma) are preserved as empty strings so
    callers can flag them as a shape error rather than silently dropping
    them.
    """
    inner = val[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(",")]


def _parse_frontmatter(text):
    """Parse the '---' frontmatter block.

    Returns (fields, errors, body). fields/body are None if no frontmatter
    block is found at all. errors holds targeted per-line problems
    (malformed line, duplicate key) that no longer null out the whole parse.
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
        if val.startswith("[") and val.endswith("]"):
            val = _parse_inline_list(val)
        else:
            val = _unquote(val)
        if key in seen:
            errors.append(f"duplicate frontmatter key: {key!r}")
        seen.add(key)
        fields[key] = val
        last_key = key
    return fields, errors, text[m.end():]


def validate(path, warnings=None):
    """Validate one memory fact file. Returns the error list (unchanged
    contract).

    If `warnings` is a list, advisory craft-memory-bleed warning strings are
    appended to it (craft-store-scoped only; see `_craft_plugin_root`).
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
    if not isinstance(fm.get("name"), str) or not fm.get("name"):
        errors.append("name must be a non-empty string")
    if not isinstance(fm.get("description"), str) or not fm.get("description"):
        errors.append("description must be a non-empty string")
    if fm.get("type") not in TYPES:
        errors.append(f"bad type: {fm.get('type')!r} "
                      f"(want one of {sorted(TYPES)})")

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

    sb = fm.get("superseded-by", "null")
    if sb not in ("null", "") and not (isinstance(sb, str) and sb.endswith(".md")):
        errors.append("superseded-by must be null or a .md path")

    if "agents" in fm and fm["agents"] not in (None, ""):
        agents = fm["agents"]
        if not isinstance(agents, list):
            errors.append(f"agents must be a flat YAML list, got {agents!r}")
        elif any(isinstance(item, str) and ("[" in item or "]" in item)
                for item in agents):
            # A nested list -- inline "[[a, b], c]" (which the flow-list
            # parser mangles into fragments like "[a") or a multiline item
            # that is itself "[a, b]" -- always leaves a stray bracket
            # character in some item. Flag it explicitly rather than
            # silently validating the mangled fragments.
            errors.append(
                f"agents must be a flat list (nested list found): {agents!r}")
        else:
            for item in agents:
                if not isinstance(item, str) or not item.strip():
                    errors.append(
                        f"agents list contains a non-empty-string item: {item!r}")

    if not body.strip():
        errors.append("fact body must be non-empty")

    if warnings is not None:
        plugin_root = _craft_plugin_root(path)
        if plugin_root is not None:
            warnings.extend(_craft_bleed_warnings(path, body, plugin_root))

    return [f"{path}: {e}" for e in errors]


def main(argv):
    # See validate_task.py's main() for why: em dashes in some messages
    # would otherwise crash under a legacy Windows OEM codepage.
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    paths = argv or [str(p) for p in
                     pathlib.Path(".forge/memory").glob("*.md")
                     if p.name.lower() != "memory.md"]
    all_errors = []
    all_warnings = []
    for p in paths:
        all_errors.extend(validate(p, warnings=all_warnings))
    for e in all_errors:
        print(e)
    for w in all_warnings:
        print(f"WARNING: {w}")
    print(f"{len(paths)} file(s) checked, {len(all_errors)} error(s), "
          f"{len(all_warnings)} warning(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
