# tools/trust.py
"""Deterministic trust-decision accelerator for a `.forge/` directory.

This is an accelerator, not the source of truth: the kernel prose in
skills/kernel/SKILL.md ("Trust check") and docs/conventions.md ("Trust
boundary") define the trust model. This module just gives the kernel a
mechanically-checkable way to compute the same decision instead of eyeballing
directory contents. If Python is unavailable, the kernel checks marker
presence manually (same fallback pattern as tools/validate_*.py: the system
must not depend on the script).

The rule, restated: a `.forge/` is UNTRUSTED iff NEITHER `.forge/.provenance`
NOR `.forge/.trust-local` is present. It is TRUSTED iff either (or both) is
present. Zero dependencies, stdlib only.
"""
import datetime
import pathlib
import sys


def is_trusted(forge_dir) -> bool:
    """Return True iff `.forge/.provenance` or `.forge/.trust-local` exists
    under forge_dir. This is the canonical, deterministic encoding of the
    Forge trust decision (docs/conventions.md, "Trust boundary")."""
    forge_dir = pathlib.Path(forge_dir)
    return (forge_dir / ".provenance").exists() or (forge_dir / ".trust-local").exists()


def _parse_iso8601(value):
    """Parse an ISO-8601 date (`YYYY-MM-DD`) or UTC timestamp
    (`YYYY-MM-DDTHH:MM:SSZ`) into an aware UTC datetime. Returns None for
    anything empty or unparseable -- callers must treat that as "skip",
    never raise."""
    if not value:
        return None
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _frontmatter_field(path, field):
    """Extract `field: value` from a file's YAML frontmatter (the block
    between the first pair of `---` lines). Returns None if the file has no
    frontmatter fence or the field is absent -- never raises on a malformed
    file."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    except OSError:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    prefix = field + ":"
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _trust_local_confirmed(trust_local_path):
    """Extract the `confirmed:` value from `.forge/.trust-local`. Unlike
    task/spec files, `.trust-local` is plain `key: value` lines with no YAML
    frontmatter fence (docs/conventions.md, "Trust boundary") -- read it
    directly rather than through _frontmatter_field."""
    try:
        text = pathlib.Path(trust_local_path).read_text(encoding="utf-8-sig")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("confirmed:"):
            return line.split(":", 1)[1].strip()
    return None


def new_since_confirm(forge_dir):
    """Return the ids (sorted) of ready/backlog queue tasks and specs whose
    frontmatter `created` timestamp is newer than `.forge/.trust-local`'s
    `confirmed` timestamp -- i.e. `.forge/` content that arrived (via a
    later pull/merge) after this machine's human last confirmed trust.

    ACCELERATOR for the kernel's prose rule (skills/kernel/SKILL.md, "New
    since last trust confirm"): same pattern as is_trusted() above -- a
    mechanically-checkable encoding of a rule the kernel prose already
    defines as the source of truth, not a new one. This does not gate or
    block anything itself; the kernel surfaces the result in the session
    report only (visible surfacing, not a blocking gate).

    - No `.forge/.trust-local` -> [] (nothing to compare against yet; matches
      the kernel's "skip this check entirely when no .trust-local exists").
    - A task/spec with a missing or malformed `created` field is skipped, not
      raised on and not flagged -- one bad file must never hide every other
      flag or crash the check.
    - Only tasks in state `ready` or `backlog` are considered (per the kernel
      prose); specs are considered regardless of status.
    """
    forge_dir = pathlib.Path(forge_dir)
    trust_local = forge_dir / ".trust-local"
    if not trust_local.exists():
        return []
    confirmed = _parse_iso8601(_trust_local_confirmed(trust_local))
    if confirmed is None:
        return []

    flagged = []

    task_dir = forge_dir / "queue" / "tasks"
    if task_dir.is_dir():
        for path in sorted(task_dir.glob("*.md")):
            state = _frontmatter_field(path, "state")
            if state not in ("ready", "backlog"):
                continue
            created = _parse_iso8601(_frontmatter_field(path, "created"))
            if created is None or created <= confirmed:
                continue
            flagged.append(_frontmatter_field(path, "id") or path.stem)

    spec_dir = forge_dir / "specs"
    if spec_dir.is_dir():
        for path in sorted(spec_dir.glob("*.md")):
            created = _parse_iso8601(_frontmatter_field(path, "created"))
            if created is None or created <= confirmed:
                continue
            flagged.append(_frontmatter_field(path, "id") or path.stem)

    return flagged


def main(argv):
    if argv and argv[0] == "--new-since":
        forge_dir = argv[1] if len(argv) > 1 else ".forge"
        for id_ in new_since_confirm(forge_dir):
            print(id_)
        return 0

    forge_dir = argv[0] if argv else ".forge"
    trusted = is_trusted(forge_dir)
    print("trusted" if trusted else "untrusted")
    return 0 if trusted else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
