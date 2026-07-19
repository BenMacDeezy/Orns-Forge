"""Validate a Forge project config file (forge.md) against docs/conventions.md.
Zero dependencies.

Unlike task/spec/memory files, forge.md carries no YAML frontmatter block --
it is a plain markdown document with `## Section` headers and `- key: value`
bullet lines (docs/conventions.md, "forge.md (project config)" and "Features
(forge.md)"). This validator checks:

  - `## Gates` must be present with non-empty `build`/`test`/`lint` lines.
    Values may be free-form shell commands, "(auto-detect)", or a
    "none (...)" explanation -- any non-empty value is accepted; a missing
    or malformed `## Gates` section is an error (conventions.md's
    "Malformed forge.md" recovery path, docs/conventions.md:114).
  - `## Queue` is OPTIONAL. If present, `claim-staleness-hours` (if set)
    must be a positive number (int or decimal) and `max-parallel-tasks`
    (if set) must be a positive integer.
  - `## Budgets` is OPTIONAL. If present, `session-token-cap` and
    `max-tasks-per-session` (if set) must each be "none" or a positive
    integer.
  - `## Features` is OPTIONAL -- a forge.md predating this section, or one
    that never mentions a given toggle, simply uses that toggle's default
    (docs/conventions.md, "Features (forge.md)"). If the section IS
    present, each line's value must be `on` or `off`; an unrecognized
    toggle *name* is a forward-compat WARNING, not an error (a newer Forge
    may ship toggles this validator doesn't know about yet).
"""
import re, sys, pathlib

GATE_KEYS = ["build", "test", "lint"]
KNOWN_FEATURES = {"natural-language-invocation", "continuous-loop",
                   "auto-queue-capture", "express-lane", "workflow-executor"}
ON_OFF = {"on", "off"}
ROUTING_MODELS = {"haiku", "sonnet", "opus", "fable"}
ROUTING_EFFORTS = {"low", "medium", "high"}

_FENCE_RE = re.compile(r"^ {0,3}`{3,}")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")
_INT_RE = re.compile(r"^\d+$")
# "<model>/<effort> — <reason>" (docs/conventions.md's documented Routing
# overrides line shape). The separator between effort and reason accepts
# either an em dash or a plain hyphen -- a hand-edited forge.md commonly
# substitutes the latter, and that's not itself a shape error worth flagging.
_ROUTING_REST_RE = re.compile(
    r"^(?P<model>[A-Za-z]+)/(?P<effort>[A-Za-z]+)\s*[—-]\s*(?P<reason>\S.*)$")


def _unquote(val):
    """Strip a single layer of matching leading/trailing quotes from a
    scalar. Mirrors validate_task.py's `_unquote` -- every sibling validator
    dequotes upstream (task/spec frontmatter parsing), so a hand-editor
    quoting a forge.md value by analogy (e.g. Features: `workflow-executor:
    "on"`) must not hit a confusing false-positive enum-mismatch error."""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _strip_html_comments(text):
    """Remove `<!-- ... -->` template comments (possibly multi-line) before
    line-based bullet parsing, so a comment's prose is never mistaken for a
    `- key: value` config line."""
    return _HTML_COMMENT_RE.sub("", text)


def _mask_fences(text):
    """Blank the contents of fenced ``` code blocks while preserving line
    count, so an example config shown inside a ```-fence is never mistaken
    for the real section."""
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
    # documentation/example fence *within* a real "## Gates" section would
    # let its example bullets be parsed by `_parse_items` as real Gates
    # configuration, satisfying the build/test/lint key check even with no
    # real unfenced Gates content at all.
    return masked[start:end]


def _parse_items(section_text, errors, section_name, strip_inline_comment=False):
    """Parse `- key: value` bullet lines within one section body.

    Non-bullet lines (prose, `(none)` placeholders) are silently ignored. A
    bullet-shaped line with no `:` is a malformed-line error. When
    `strip_inline_comment` is set, a trailing `  # comment` is stripped from
    the value (used for Features, whose template annotates each toggle).
    """
    items = {}
    seen = set()
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        if ":" not in content:
            errors.append(f"malformed {section_name} line: {raw_line.strip()!r}")
            continue
        key, val = content.split(":", 1)
        key = key.strip()
        val = val.strip()
        if strip_inline_comment:
            val = re.split(r"\s+#", val, maxsplit=1)[0].strip()
        val = _unquote(val)
        if key in seen:
            errors.append(f"duplicate {section_name} key: {key!r}")
        seen.add(key)
        items[key] = val
    return items


def validate(path, warnings=None):
    """Validate one forge.md config file. Returns the error list.

    If `warnings` is a list, advisory warning strings (e.g. an unrecognized
    Features toggle name) are appended to it. Warnings never affect the
    returned errors or the exit code.
    """
    errors = []
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        return [f"{path}: cannot read file: {e}"]

    text = _strip_html_comments(text)

    routing_body = _section_body(text, "## Routing overrides")
    if routing_body is not None:
        for raw_line in routing_body.splitlines():
            line = raw_line.strip()
            if not line or line == "(none)":
                continue
            pattern, sep, rest = line.partition(":")
            m = _ROUTING_REST_RE.match(rest.strip()) if sep else None
            if not sep or not pattern.strip() or not m:
                errors.append(
                    f"malformed Routing overrides line: {raw_line.strip()!r} "
                    "(want '<area or path pattern>: <model>/<effort> — <reason>')")
                continue
            model = m.group("model").lower()
            effort = m.group("effort").lower()
            if model not in ROUTING_MODELS:
                errors.append(
                    f"bad Routing overrides model: {m.group('model')!r} "
                    f"(want one of: {', '.join(sorted(ROUTING_MODELS))})")
            if effort not in ROUTING_EFFORTS:
                errors.append(
                    f"bad Routing overrides effort: {m.group('effort')!r} "
                    f"(want one of: {', '.join(sorted(ROUTING_EFFORTS))})")

    gates_body = _section_body(text, "## Gates")
    if gates_body is None:
        errors.append("missing section: ## Gates")
    else:
        gates = _parse_items(gates_body, errors, "Gates")
        for key in GATE_KEYS:
            if not gates.get(key, "").strip():
                errors.append(f"Gates missing or empty key: {key}")

    queue_body = _section_body(text, "## Queue")
    if queue_body is not None:
        queue = _parse_items(queue_body, errors, "Queue")
        if "claim-staleness-hours" in queue:
            v = queue["claim-staleness-hours"]
            if not _NUMBER_RE.match(v) or float(v) <= 0:
                errors.append(
                    f"bad claim-staleness-hours: {v!r} (want a positive number)")
        if "max-parallel-tasks" in queue:
            v = queue["max-parallel-tasks"]
            if not _INT_RE.match(v) or int(v) <= 0:
                errors.append(
                    f"bad max-parallel-tasks: {v!r} (want a positive integer)")

    budgets_body = _section_body(text, "## Budgets")
    if budgets_body is not None:
        budgets = _parse_items(budgets_body, errors, "Budgets")
        for key in ("session-token-cap", "max-tasks-per-session"):
            if key not in budgets:
                continue
            v = budgets[key]
            if v == "none":
                continue
            if not _INT_RE.match(v) or int(v) <= 0:
                errors.append(
                    f'bad {key}: {v!r} (want "none" or a positive integer)')

    features_body = _section_body(text, "## Features")
    if features_body is not None:
        features = _parse_items(features_body, errors, "Features",
                                strip_inline_comment=True)
        for key, val in features.items():
            if key not in KNOWN_FEATURES and warnings is not None:
                warnings.append(
                    f"{path}: unrecognized Features toggle {key!r} "
                    "(forward-compat: ignored, not an error)")
            if val not in ON_OFF:
                errors.append(
                    f"bad Features value for {key!r}: {val!r} (want on|off)")

    return [f"{path}: {e}" for e in errors]


def main(argv):
    # See validate_task.py's main() for why: em dashes in some messages
    # would otherwise crash under a legacy Windows OEM codepage.
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    if argv:
        paths = argv
    else:
        default = pathlib.Path(".forge/forge.md")
        paths = [str(default)] if default.exists() else []
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
