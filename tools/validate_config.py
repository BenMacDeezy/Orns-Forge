"""Validate a Forge project config file (forge.md) against docs/conventions.md
("forge.md (project config)", docs/conventions/config-and-features.md, fg-b0401).
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
  - `## Budgets` is OPTIONAL. If present, `session-token-cap`,
    `max-tasks-per-session`, and `max-provider-dispatches-per-session`
    (if set) must each be "none" or a positive integer.
  - `## Features` is OPTIONAL -- a forge.md predating this section, or one
    that never mentions a given toggle, simply uses that toggle's default
    (docs/conventions.md, "Features (forge.md)"). If the section IS
    present, each line's value must be `on` or `off`; an unrecognized
    toggle *name* is a forward-compat WARNING, not an error (a newer Forge
    may ship toggles this validator doesn't know about yet).
  - `## Providers` is OPTIONAL (provider-toggles, 2026-07-21) -- a flat
    per-provider `- <provider>: on|off` toggle table, layered UNDER the
    global `providers` Feature above. Each value must be `on` or `off`; an
    unrecognized provider id is a forward-compat WARNING, not an error. A
    missing section, or a provider id the section omits, means that
    provider is OFF -- the one place a missing key does NOT resolve to a
    documented "default" line, because the posture being mirrored (the
    `providers` Feature's own default-off) already IS off.
"""
import re, sys, pathlib

GATE_KEYS = ["build", "test", "lint"]
KNOWN_FEATURES = {"natural-language-invocation", "continuous-loop",
                   "auto-queue-capture", "express-lane", "workflow-executor",
                   "providers"}
ON_OFF = {"on", "off"}
ROUTING_MODELS = {"haiku", "sonnet", "opus", "fable"}
ROUTING_EFFORTS = {"low", "medium", "high"}
# skills/kernel/references/settings-schema.md's Providers rows for
# `codex-default-model` and `codex-default-effort` are the canonical
# owner-allowed vocabulary; keep validator acceptance aligned with them.
CODEX_MODELS = {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.5"}
CODEX_EFFORTS = {"low", "medium", "high", "xhigh"}

# Operator-profile container (fg-b0103, spec-4d2a, skills/kernel/references/
# operator-profiles.md). KNOWN_PROFILE_DOMAINS names the top-level ## domain
# sections this container knows about today; a domain section outside this
# set is a forward-compat WARNING, never an error -- a future domain spec
# (fg-a10902's providers, or any later one) may add sections this validator
# doesn't know about yet, same shape as KNOWN_FEATURES above.
KNOWN_PROFILE_DOMAINS = {"Autonomy", "Providers"}
PROFILE_KINDS = {"stock", "preset", "custom"}

# Providers domain: key-level validation (fg-c0110, spec-e8a3), extending
# the container-only checks above now that fg-c0101's Providers schema
# exists (skills/kernel/references/operator-profiles.md, "Providers domain:
# schema (fg-c0101)" -- key vocabulary and closed enums cited below are
# that section's contract, not invented here).
#
# PROVIDER_ENUM also doubles as the known-provider-id set for forge.md's OWN
# `## Providers` per-provider toggle section (provider-toggles, 2026-07-21,
# docs/conventions/config-and-features.md "Per-provider dispatch toggles")
# -- a flat `- <provider>: on|off` toggle table, validated below in
# `validate()`. That section is a DIFFERENT surface from a profile file's
# `## Providers` DOMAIN section validated by `_validate_providers_domain`
# (enabled-providers/role-*/tier-* keys) -- both share this one closed
# provider-id set so they never drift apart.
PROVIDER_ENUM = {"codex", "grok", "antigravity"}
PROVIDER_MODELS = {"codex": CODEX_MODELS, "grok": set(), "antigravity": set()}
PROVIDER_EFFORTS = {"codex": CODEX_EFFORTS, "grok": set(), "antigravity": set()}
# Naming grok/antigravity in enabled-providers is pilot-gated: profile
# files must not be able to pre-enable what the picker itself still
# refuses until a human reviews that provider's pilot-test evidence
# (operator-profiles.md's own text says this is "accepted and stored,
# never itself the thing that clears the gate" at the schema-description
# layer; this task adds the validator-level hard-stop that document
# explicitly leaves to a future task).
PILOT_GATED_PROVIDERS = {"grok": "fg-c0104", "antigravity": "fg-c0105"}
PROVIDER_ROLE_KEYS = {"role-plan-refuter", "role-spec-review",
                       "role-co-verifier", "role-worker"}
_PROVIDER_TIER_KEY_RE = re.compile(
    r"^(?P<provider>[a-z0-9]+)-tier-(mechanical|judgment)$")

# Removed Providers-domain keys degrade to the stock default for that key
# with exactly one stated warning line, never an error (spec-e8a3,
# "Overlay-profile model" AC: "a custom profile referencing a removed
# provider capability SHALL degrade to the current stock default for that
# key with one stated warning line"). Empty today -- no Providers key has
# been removed yet; a future removal adds `{key: <replacement note>}` here.
# Maps a removed key name to a short human-readable replacement/default
# note used in the one-line warning.
REMOVED_PROVIDER_KEYS = {}

# The exact literal full-bypass flag, and the auto-approve / sandbox
# markers used to detect an auto-approve flag present without its required
# workspace-scoped sandbox pairing, per docs/conventions/trust-and-
# security.md "Provider dispatch security rules -- 2026-07-19 (fg-c0112,
# spec-e8a3)". Checked against every value in a `## Providers` section,
# not just known keys, so a hostile or careless future dispatch-args value
# is caught at profile-validate time.
_FULL_BYPASS_MARKERS = ("--dangerously-bypass-approvals-and-sandbox",)
_AUTO_APPROVE_MARKERS = ("--ask-for-approval never", "--always-approve")
_SANDBOX_MARKER = "--sandbox"

_FENCE_RE = re.compile(r"^ {0,3}`{3,}")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")
_INT_RE = re.compile(r"^\d+$")
# "<model>/<effort> — <reason>" (docs/conventions.md's documented Routing
# overrides line shape). The separator between effort and reason accepts
# either an em dash or a plain hyphen -- a hand-edited forge.md commonly
# substitutes the latter, and that's not itself a shape error worth flagging.
_ROUTING_REST_RE = re.compile(
    r"^(?P<target>[A-Za-z0-9.-]+(?:/[A-Za-z0-9.-]+){1,2})\s*[—-]\s*(?P<reason>\S.*)$")


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


def _iter_top_sections(text):
    """Return an ordered list of (heading, body) for every fence-aware,
    line-anchored top-level '## ' heading in `text` -- unlike
    `_section_body`, which looks up ONE known section name, this walks the
    whole document, needed because a profile file's domain sections are not
    a fixed known set (operator-profiles.md's `## Autonomy` / `## Providers`
    plus any forward-compat name a future domain spec adds)."""
    masked = _mask_fences(text)
    heading_re = re.compile(r"(?m)^## (.+?)\s*$")
    matches = list(heading_re.finditer(masked))
    sections = []
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(masked)
        sections.append((name, masked[start:end]))
    return sections


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
            target = rest.strip().split(None, 1)[0].split("/")
            if len(target) == 2:
                model, effort = (part.lower() for part in target)
                if model not in ROUTING_MODELS:
                    errors.append(
                        f"bad Routing overrides model: {model!r} "
                        f"(want one of: {', '.join(sorted(ROUTING_MODELS))})")
                if effort not in ROUTING_EFFORTS:
                    errors.append(
                        f"bad Routing overrides effort: {effort!r} "
                        f"(want one of: {', '.join(sorted(ROUTING_EFFORTS))})")
            else:
                provider, slug, effort = (part.lower() for part in target)
                if provider not in PROVIDER_ENUM:
                    errors.append(f"bad Routing overrides provider: {provider!r} "
                                  "(want a known ## Providers id)")
                elif slug not in PROVIDER_MODELS[provider]:
                    errors.append(f"bad Routing overrides {provider} slug: {slug!r} "
                                  "(not owner-allowed)")
                if provider in PROVIDER_EFFORTS and effort not in PROVIDER_EFFORTS[provider]:
                    errors.append(f"bad Routing overrides {provider} effort: {effort!r} "
                                  "(not in that provider's vocabulary)")

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
        for key in ("session-token-cap", "max-tasks-per-session",
                    "max-provider-dispatches-per-session"):
            if key not in budgets:
                continue
            v = budgets[key]
            if v == "none":
                continue
            if not _INT_RE.match(v) or int(v) <= 0:
                errors.append(
                    f'bad {key}: {v!r} (want "none" or a positive integer)')
        if "provider-dispatch-checkpoint-every" in budgets:
            v = budgets["provider-dispatch-checkpoint-every"]
            if not _INT_RE.match(v) or int(v) <= 0:
                errors.append(
                    f"bad provider-dispatch-checkpoint-every: {v!r} "
                    "(want a positive integer)")

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

    # forge.md's own `## Providers` per-provider toggle section
    # (provider-toggles, 2026-07-21). OPTIONAL -- a forge.md with no
    # `## Providers` section, or one that omits a given provider id,
    # treats that provider as OFF (docs/conventions/config-and-features.md,
    # "Per-provider dispatch toggles" -- the one place a missing key does
    # NOT mean its template default; it mirrors the `providers` Feature's
    # own default-off posture instead). An unrecognized provider id is a
    # forward-compat WARNING, never an error, same shape as KNOWN_FEATURES
    # above.
    providers_body = _section_body(text, "## Providers")
    if providers_body is not None:
        provider_toggles = _parse_items(providers_body, errors, "Providers",
                                        strip_inline_comment=True)
        for key, val in provider_toggles.items():
            if key in PROVIDER_ENUM:
                if val not in ON_OFF:
                    errors.append(
                        f"bad Providers value for {key!r}: {val!r} (want on|off)")
                elif key in PILOT_GATED_PROVIDERS and val == "on" and warnings is not None:
                    marker = f".forge/.trust-providers/{key}.pilot-cleared.local"
                    warnings.append(
                        f"{path}: Providers toggle {key!r} is on, but remains "
                        f"undispatchable until pilot-clearance marker {marker} exists")
            elif key == "codex-default-model":
                if val not in CODEX_MODELS:
                    errors.append(f"bad Providers codex-default-model: {val!r} "
                                  "(not owner-allowed)")
            elif key == "codex-default-effort":
                if val not in CODEX_EFFORTS:
                    errors.append(f"bad Providers codex-default-effort: {val!r} "
                                  "(want one of: low, medium, high, xhigh)")
            elif warnings is not None:
                warnings.append(
                    f"{path}: unrecognized Providers toggle {key!r} "
                    "(forward-compat: ignored, not an error)")

    return [f"{path}: {e}" for e in errors]


def _check_provider_dispatch_security(key, value, errors):
    """Hard-reject (never warn) a Providers-domain value that would emit
    the full-bypass flag combination -- spec-e8a3's Risks mitigation and
    docs/conventions/trust-and-security.md's "Provider dispatch security
    rules" (fg-c0112) are both explicit that this is a validate-time
    rejection, not just a dispatch-time one. Two shapes are caught: an
    explicit full-bypass flag, or an auto-approve/no-confirm flag present
    without its required workspace-scoped sandbox pairing in the same
    value. Matching is case-insensitive in both directions -- a provider
    CLI's flag casing is not itself a security boundary, so an uppercased
    or mixed-case bypass/auto-approve flag must be caught exactly like the
    lowercase form, and an uppercased --SANDBOX must count as a valid
    pairing exactly like the lowercase form (never stricter on the escape
    than on the trap). Appends to `errors` (unprefixed -- the caller's
    caller adds the file path); returns nothing."""
    lowered = value.lower()
    for marker in _FULL_BYPASS_MARKERS:
        if marker in lowered:
            errors.append(
                f"Providers {key!r} emits a full-bypass flag ({marker!r}) "
                "-- docs/conventions/trust-and-security.md 'Provider "
                "dispatch security rules' forbids a full-bypass flag that "
                "disables both sandbox and approval together; pair "
                "auto-approve only with a workspace-scoped sandbox flag "
                "instead")
            return
    if (any(marker in lowered for marker in _AUTO_APPROVE_MARKERS)
            and _SANDBOX_MARKER not in lowered):
        errors.append(
            f"Providers {key!r} uses an auto-approve flag unpaired with a "
            "workspace-scoped sandbox flag -- docs/conventions/trust-and-"
            "security.md 'Provider dispatch security rules' requires "
            "auto-approve to pair only with that CLI's own workspace-"
            "scoped sandbox mode (e.g. '--sandbox workspace-write "
            "--ask-for-approval never'), never left unpaired")


def _validate_providers_domain(items, errors, warnings, path):
    """Key-level validation for one `## Providers` domain section
    (fg-c0110, spec-e8a3): closed-enum checks for the domain's own key
    vocabulary (operator-profiles.md, "Providers domain: schema
    (fg-c0101)"), the pilot-gate hard-stop, and the security rejection
    above. Unknown/renamed keys warn, never fail (forward-compat); a
    removed-capability key degrades to its stock default with exactly one
    stated warning line. `errors` entries are unprefixed (the caller wraps
    them with `path` on return); `warnings` entries must include `path`
    themselves, matching every other warning `validate_profile` emits."""
    for key, value in items.items():
        _check_provider_dispatch_security(key, value, errors)

        if key == "enabled-providers":
            if value.strip() == "none":
                continue
            for entry in (e.strip() for e in value.split(",")):
                if not entry:
                    continue
                if entry not in PROVIDER_ENUM:
                    errors.append(
                        f"bad enabled-providers entry: {entry!r} (want "
                        "'none' or a comma-separated subset of: "
                        f"{', '.join(sorted(PROVIDER_ENUM))})")
                elif entry in PILOT_GATED_PROVIDERS:
                    errors.append(
                        f"enabled-providers names {entry!r}, which is "
                        "pilot-gated behind "
                        f"{PILOT_GATED_PROVIDERS[entry]} -- a profile file "
                        "cannot pre-enable a provider the picker itself "
                        "still refuses until a human reviews that "
                        "provider's pilot-test evidence and clears the gate")
        elif key in PROVIDER_ROLE_KEYS:
            if value != "claude-only" and value not in PROVIDER_ENUM:
                errors.append(
                    f"bad {key} value: {value!r} (want claude-only or one "
                    f"of: {', '.join(sorted(PROVIDER_ENUM))})")
        elif _PROVIDER_TIER_KEY_RE.match(key):
            provider = _PROVIDER_TIER_KEY_RE.match(key).group("provider")
            if provider not in PROVIDER_ENUM and warnings is not None:
                warnings.append(
                    f"{path}: unrecognized Providers key {key!r} "
                    "(forward-compat: warned, not an error)")
        elif key in REMOVED_PROVIDER_KEYS:
            if warnings is not None:
                warnings.append(
                    f"{path}: Providers key {key!r} is a removed provider "
                    "capability -- degrading to the stock default "
                    f"({REMOVED_PROVIDER_KEYS[key]})")
        elif warnings is not None:
            warnings.append(
                f"{path}: unrecognized Providers key {key!r} "
                "(forward-compat: warned, not an error)")


def validate_profile(path, warnings=None):
    """Validate one operator-profile container file
    (`skills/kernel/references/operator-profiles.md`'s format; fg-b0103,
    spec-4d2a) -- a `.forge/profiles/<name>.md` custom overlay, or a stock/
    preset profile skeleton shipped read-only in the plugin. Returns the
    error list; advisory forward-compat warnings (unrecognized domain
    section name) go to `warnings` if given, same convention as `validate()`
    above.

    Checks the CONTAINER only:
      - `## Meta` present, with a positive-integer `schema-version`, a
        `kind` in {stock, preset, custom}, a non-empty `name`, and -- for
        `kind: custom` only -- a non-"(none)" `base` naming the stock/
        preset profile this file's sections store deltas over.
      - every other top-level `## ` section is parsed as `- key: value`
        bullets; a malformed line or an in-section duplicate key is an
        error. A section name outside `KNOWN_PROFILE_DOMAINS` is a WARNING
        (forward-compat), never an error. A duplicate SECTION name (two
        `## Autonomy` headings) is an error.
    Domain-owned key/value semantics (what `## Autonomy` keys mean) are
    out of scope here by design -- each domain spec owns its own key
    vocabulary, exactly as KNOWN_FEATURES above only names Features toggle
    NAMES, not their meaning.
    """
    errors = []
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        return [f"{path}: cannot read file: {e}"]

    text = _strip_html_comments(text)
    sections = _iter_top_sections(text)

    meta_bodies = [body for name, body in sections if name == "Meta"]
    if not meta_bodies:
        return [f"{path}: missing section: ## Meta"]
    if len(meta_bodies) > 1:
        errors.append("duplicate section: ## Meta")
    meta = _parse_items(meta_bodies[0], errors, "Meta")

    sv = meta.get("schema-version", "")
    if not _INT_RE.match(sv) or int(sv) <= 0:
        errors.append(f"Meta missing or invalid schema-version: {sv!r}")

    kind = meta.get("kind")
    if kind not in PROFILE_KINDS:
        errors.append(
            f"Meta bad kind: {kind!r} "
            f"(want one of: {', '.join(sorted(PROFILE_KINDS))})")

    if not meta.get("name", "").strip():
        errors.append("Meta missing or empty key: name")

    if kind == "custom":
        base = meta.get("base", "").strip()
        if not base or base == "(none)":
            errors.append(
                "Meta: kind: custom requires a base "
                "(the stock/preset name this profile's deltas overlay)")

    seen_domains = set()
    for dname, dbody in sections:
        if dname == "Meta":
            continue
        if dname in seen_domains:
            errors.append(f"duplicate section: ## {dname}")
        seen_domains.add(dname)
        if dname not in KNOWN_PROFILE_DOMAINS and warnings is not None:
            warnings.append(
                f"{path}: unrecognized profile domain section {dname!r} "
                "(forward-compat: parsed, not an error)")
        items = _parse_items(dbody, errors, dname)
        if dname == "Providers":
            _validate_providers_domain(items, errors, warnings, path)

    return [f"{path}: {e}" for e in errors]


def _is_profile_path(path):
    """True when `path` names a file directly inside a `.forge/profiles/`
    directory -- the storage location operator-profiles.md fixes for custom
    overlay profiles. Used by main() to route an explicit path argument to
    `validate_profile()` instead of the `.forge/forge.md` validator."""
    p = pathlib.Path(path)
    return p.parent.name == "profiles" and p.parent.parent.name == ".forge"


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
        if _is_profile_path(p):
            all_errors.extend(validate_profile(p, warnings=all_warnings))
        else:
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
