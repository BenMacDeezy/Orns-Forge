#!/usr/bin/env python3
"""Customization-persistence boundary gate (fg-b0101, spec-4d2a).

Scans the plugin SOURCE tree (skills/, commands/, hooks/, tools/, agents/)
for file-write idioms whose destination resolves under the plugin's own
installed directory (`${CLAUDE_PLUGIN_ROOT}` / the repo's own source tree)
instead of project space (`.forge/`, git-tracked with the repo) or user
space (`~/.claude/...`). Per spec-4d2a's customization-persistence
contract: any Forge feature that stores a user- or project-level
customization must write it only under project space or user space, never
under the plugin's own installed directory (which an update overwrites
wholesale).

Run directly for a human-readable report + process exit code (0 clean,
1 on violation, printing offending `file:line`), or import
`scan_repo(repo_root)` from tools/test_validate_persistence_boundary.py for
pytest coverage.

WHAT THIS CATCHES
------------------
Python (parsed with the stdlib `ast` module):
  - `open(path, "w"/"a"/"x"/"w+"/...)`  (any mode string containing one of
    w/a/x, i.e. anything that isn't a pure read)
  - `<expr>.write_text(...)`  (pathlib.Path)
  - `shutil.copy/copy2/copyfile/move/copytree(src, dst)`  (dst arg)

Bash (`.sh` files, line-based regex — hooks/ is the only place they live
today, but any `.sh` under the scanned dirs is covered):
  - `>` / `>>` redirects (not `2>`/`&>` fd-only redirects, which usually
    target `/dev/null` and are not customization writes)
  - `cp` / `mv` / `tee` invocations (destination = last non-flag token)

For each write-idiom call site, the destination expression's *source
text* is classified:
  - references `CLAUDE_PLUGIN_ROOT` (bash env var, or a Python variable
    whose own assignment is itself `Path(__file__).resolve()...`-derived,
    i.e. "wherever this script lives") AND
  - contains none of the project-space/user-space escape markers
    (`.forge`, `CLAUDE_PROJECT_DIR`, `home()`, `HOME`, `USERPROFILE`,
    literal `~`)
  -> VIOLATION, reported as `file:line`.

Variable tracking (Python) is name-based and FLAT across the whole file --
`ast.walk()` visits every `Assign` node regardless of module/function
scope in source order, and a name is classified "plugin-root-like" if its
own assignment RHS contains `__file__`/`CLAUDE_PLUGIN_ROOT` directly, OR
references a name already classified plugin-root-like, OR is the result of
calling a function already determined (see below) to return a
plugin-root-rooted value. Because classification accumulates over a single
ordered pass, this DOES follow straight-line assignment chains of any
length (`root = Path(__file__)...`; `d = root / "x"`; `e = d / "y"` --
`e` is still caught), not merely one hop.

Interprocedural (Python), one hop: a module-level `def` whose `return`
statement's expression is itself classified plugin-root-rooted (by the
same rule above, since a function's local assignments are picked up by
the same flat, scope-unaware walk) marks that FUNCTION NAME as
plugin-root-rooted. A caller that assigns from it (`p = get_path()`) or
inlines it (`open(get_path(), "w")`) is then classified/flagged the same
way a direct variable reference would be. A function whose return value
is itself the result of calling ANOTHER such function (two hops of
indirection: `def get_it(): return get_path()`) is NOT tracked -- only one
hop into a caller is resolved.

Bash: a name is classified from its own simple `NAME=value` assignment
line, propagated to any later assignment whose RHS textually contains
`$NAME`/`${NAME}` (also unbounded straight-line chaining, same flat-pass
design as Python).

HOW MATCHING ACTUALLY WORKS (read this before trusting the miss-list below)
----------------------------------------------------------------------------
`_expr_is_violation` and the assignment classifiers do not model what
operations are applied to a rooted value -- they walk the ENTIRE subtree
of the write-destination expression (or, for an assignment, its RHS
expression) with `ast.walk` and flag it the moment ANY `ast.Name` node
inside that subtree matches a name already known to be plugin-root-rooted,
or ANY `ast.Call` node inside it calls a function already known to return
one. This is broader than "traces simple chains": it is caught regardless
of how deeply the rooted name is buried -- passed as a function argument
and returned back out (any number of parameter-threading hops, direct or
inlined, including through an intermediate function or a closure
`def`), embedded in an f-string/`.format()`/`%`-string, indexed out of a
list/dict/tuple literal, etc. -- because in every one of those forms the
original `ast.Name` token for the rooted variable still physically
appears somewhere in the destination expression's syntax tree, and that
is all this checks for. (Verified empirically: `open(helper(root), "w")`,
`open(f"{root}/x", "w")`, and `open(paths[0], "w")` with
`paths = [root / "a"]` are each flagged as a single violation.)

Destructuring assignment targets (`a, b = ...`, `[a, b] = ...`,
`a, *rest = ...`) are recursed into, not just plain `Name` targets: when
the RHS is itself a literal tuple/list of the SAME length as the target
(no `Starred` element on either side), pairing is POSITIONAL and precise
-- each target name is registered rooted only if its own paired RHS
element is independently rooted, so a non-rooted co-element in the same
unpacking is not swept in. Any other shape (arity mismatch, a `Starred`
target, or a non-literal RHS such as a function call returning a tuple)
falls back to registering every name in the target as rooted -- the same
safe-over-precise bias documented below for scope blindness. (Verified
empirically: `state_path, tmp_path = root/"a", root/"b"` then
`open(state_path, "w")` is flagged; `rooted_path, plain_path =
root/"a", "/tmp/b"` then `open(plain_path, "w")` is NOT flagged
[positional precision holds] but `open(rooted_path, "w")` IS; `a, *rest =
root/"a", root/"b", root/"c"` flags both `open(a, "w")` and
`open(rest[0], "w")`; `a, b = get_pair()` where `get_pair()` returns
`(root/"a", "/tmp/b")` flags `open(b, "w")` too -- the non-literal-RHS
fallback sweeping in a genuinely non-rooted co-element, an intentional
over-flag.)

WHAT THIS DOES NOT CATCH -- NOT AN EXHAUSTIVE LIST (documented per
verified case, not a completeness claim)
------------------------------------------------------------------------
This list has already been revised twice after a claimed miss turned out
to be caught once actually run against the scanner (function-parameter
threading, f-strings, dict/list-element destinations, and a 3-hop
straight-line chain were all wrongly listed as misses in earlier drafts
of this docstring; live-execution evidence corrected each one -- see
`tools/test_validate_persistence_boundary.py` for the pinning tests).
Given that history, this section states only misses that have themselves
been run against the live scanner and confirmed 0 violations; it does NOT
claim to be the complete set of everything this module fails to catch --
treat "not listed here" as unknown, not as "caught."

Confirmed non-Python/non-bash idiom classes this deliberately does not
attempt (never claimed to catch, not scanner gaps in the sense above):
  - Third-party library write methods that aren't stdlib write idioms
    (e.g. PIL's `Image.save()`, `json.dump(fh)` where `fh` came from an
    already-open file handle passed in from elsewhere, a CSV/DB driver's
    own write calls).
  - Writes performed via `subprocess`/`os.system`/shelling out to an
    external command.
  - Dynamic destinations built from command substitution in bash
    (`$(...)`).
  - Non-Python, non-bash source (no `.ps1`, `.js`, etc. scanning — none
    exist in the scanned dirs as of this writing).
  - Anything inside `tools/benchmark/fixture/` or other synthetic test
    fixtures that intentionally write to throwaway temp dirs unrelated to
    the plugin's own installed directory (these are excluded from the
    scan entirely — see EXCLUDE_DIRS).
  - Reads, deletes, or writes whose destination is entirely a runtime
    argument/return value with no textual trace in source (e.g. a path
    passed in over the network or stdin).

Verified misses (each individually run against the live scanner,
0 violations) as of this revision:
  - A rooted value stored via a non-`Name` assignment target -- e.g. a
    `Subscript`/attribute target (`_cache["p"] = Path(__file__).parent /
    "x"` -- the target is a `Subscript`, not a `Name` and not a
    `Tuple`/`List` destructuring target, so nothing is classified rooted)
    -- and read back out elsewhere (`dest = _cache["p"]; open(dest, "w")`)
    is a genuine miss: the write site's expression (`dest`) has no rooted
    Name anywhere upstream of it that this module tracked. (Verified
    empirically: 0 violations.)
  - Interprocedural chains two hops deep where the rooted expression
    itself is never spelled out again after the first hop: a function
    whose `return` statement is just a call to ANOTHER function that in
    turn returns a rooted expression (`def get_it(): return get_path()`)
    is not resolved -- `_classify_python_functions` only inspects a
    function's own `return` expression against names/functions already
    classified BEFORE that function is examined, so a return-of-a-call-
    to-another-rooted-function is one hop past what it resolves.
    (Verified empirically: 0 violations for `p = get_it(); open(p, "w")`
    where `get_it()` returns `get_path()`'s value.)

Scope blindness as a false-POSITIVE risk, not just a false-negative one:
because classification is name-based and flat across the whole file (not
truly scope-aware), a variable name reused for an unrelated, non-rooted
purpose in a different function can be misclassified as plugin-root-rooted
if the same name is rooted elsewhere in the file -- the detector is
intentionally biased toward over-flagging (a false alarm to manually
clear) rather than under-flagging (a silent miss). The destructuring
fallback above shares this same bias.

These gaps mean a clean run is evidence the CATCHABLE idiom classes above
are boundary-clean, not a certificate that no violation of any kind exists
anywhere in the tree.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN_DIRS = ["skills", "commands", "hooks", "tools", "agents"]

# Directories excluded from the scan even though they live under a scanned
# root: unit-test files exercise write idioms constantly (writing into
# tmp_path fixtures) and are not the plugin's runtime feature code; test
# fixture trees under tools/benchmark/fixture/ are synthetic sample repos
# used only to feed the benchmark harness, never real plugin write targets.
EXCLUDE_NAME_PREFIXES = ("test_",)
EXCLUDE_DIR_PARTS = {"fixture", "fixtures", "__pycache__"}

# Escape markers: any of these appearing in a destination expression's
# source text means the write resolves into project space or user space,
# not the plugin's installed directory -- not a violation.
ESCAPE_MARKERS = (
    ".forge",
    "CLAUDE_PROJECT_DIR",
    "home()",
    "HOME",
    "USERPROFILE",
    "~",
)

# Markers that make a Python/bash name (or a bare expression) "plugin-root
# rooted" -- i.e. resolves to the plugin's own installed directory.
PLUGIN_ROOT_MARKERS = ("CLAUDE_PLUGIN_ROOT", "__file__")

_WRITE_MODE_RE = re.compile(r"[wax]")


class Violation:
    def __init__(self, path: pathlib.Path, lineno: int, detail: str, repo_root: pathlib.Path = None):
        self.path = path
        self.lineno = lineno
        self.detail = detail
        self._repo_root = repo_root

    def __str__(self):
        rel = self.path
        root = self._repo_root if self._repo_root is not None else REPO_ROOT
        if self.path.is_absolute():
            try:
                rel = self.path.relative_to(root)
            except ValueError:
                rel = self.path  # outside root (shouldn't happen in normal use)
        return f"{rel}:{self.lineno}: {self.detail}"


def _iter_source_files(repo_root: pathlib.Path):
    for dirname in SCAN_DIRS:
        base = repo_root / dirname
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix not in (".py", ".sh"):
                continue
            if f.name.startswith(EXCLUDE_NAME_PREFIXES):
                continue
            if EXCLUDE_DIR_PARTS & set(f.relative_to(repo_root).parts):
                continue
            yield f


def _has_escape_marker(text: str) -> bool:
    return any(m in text for m in ESCAPE_MARKERS)


def _is_plugin_root_text(text: str) -> bool:
    return any(m in text for m in PLUGIN_ROOT_MARKERS)


# ---------------------------------------------------------------------------
# Python scanning (ast-based)
# ---------------------------------------------------------------------------

def _classify_python_vars(tree: ast.AST, source: str, rooted_funcs: frozenset = frozenset()) -> set:
    """Return the set of variable names (flat across the whole file --
    module scope and every function scope alike, see module docstring)
    whose OWN assignment RHS is plugin-root-rooted and carries no escape
    marker. RHS is rooted if it directly names `__file__`/
    `CLAUDE_PLUGIN_ROOT`, references a name already in this set (unbounded
    straight-line chaining, since the set accumulates over one ordered
    `ast.walk` pass), or calls a function already known (`rooted_funcs`)
    to return a plugin-root-rooted value."""
    plugin_root_names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        rhs_text = ast.get_source_segment(source, node.value) or ""
        if _has_escape_marker(rhs_text):
            continue
        rooted = _is_plugin_root_text(rhs_text)
        if not rooted:
            # Chained propagation: RHS built from a name we already know
            # is plugin-root-rooted (e.g. `OUT = PLUGIN_ROOT / "assets"`).
            for name_node in ast.walk(node.value):
                if isinstance(name_node, ast.Name) and name_node.id in plugin_root_names:
                    rooted = True
                    break
        if not rooted and rooted_funcs:
            # Interprocedural, one hop: RHS calls a function whose return
            # value is itself rooted (e.g. `p = get_path()`).
            for call_node in ast.walk(node.value):
                if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Name) \
                        and call_node.func.id in rooted_funcs:
                    rooted = True
                    break
        if rooted:
            for target in node.targets:
                _register_target(target, node.value, source, plugin_root_names, rooted_funcs)
    return plugin_root_names


def _register_target(target: ast.AST, rhs_value, source: str,
                      plugin_root_names: set, rooted_funcs: frozenset) -> None:
    """Register every Name inside an assignment target as rooted, recursing
    into destructuring targets (`a, b = ...`, `[a, b] = ...`, `a, *rest =
    ...`). When `rhs_value` is itself a literal `ast.Tuple`/`ast.List` of
    the SAME arity as a `ast.Tuple`/`ast.List` target with no `Starred`
    element, pairs positionally and registers each target name only if its
    own paired RHS element is independently rooted (precise -- a
    non-rooted co-element is not swept in). Any other shape (arity
    mismatch, a `Starred` target, a non-literal RHS) falls back to
    registering every Name in the target -- the safe-over-precise default
    matching this module's documented scope-blindness bias."""
    if isinstance(target, ast.Name):
        plugin_root_names.add(target.id)
        return
    if isinstance(target, ast.Starred):
        _register_target(target.value, None, source, plugin_root_names, rooted_funcs)
        return
    if isinstance(target, (ast.Tuple, ast.List)):
        has_starred = any(isinstance(e, ast.Starred) for e in target.elts)
        if (not has_starred and isinstance(rhs_value, (ast.Tuple, ast.List))
                and len(rhs_value.elts) == len(target.elts)):
            for t_elt, r_elt in zip(target.elts, rhs_value.elts):
                if _expr_is_violation(r_elt, source, plugin_root_names, rooted_funcs):
                    _register_target(t_elt, None, source, plugin_root_names, rooted_funcs)
        else:
            for elt in target.elts:
                _register_target(elt, None, source, plugin_root_names, rooted_funcs)


def _classify_python_functions(tree: ast.AST, source: str, plugin_root_names: set) -> frozenset:
    """Return the set of function names whose body contains at least one
    `return <expr>` where `<expr>` is plugin-root-rooted per
    `plugin_root_names` (which already includes that function's own local
    assignments, since classification is scope-flat -- see module
    docstring). One hop only: a function returning the result of calling
    ANOTHER rooted-returning function is not resolved here."""
    rooted_funcs = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                if _expr_is_violation(stmt.value, source, plugin_root_names):
                    rooted_funcs.add(node.name)
                    break
    return frozenset(rooted_funcs)


def _expr_is_violation(node: ast.AST, source: str, plugin_root_names: set,
                        rooted_funcs: frozenset = frozenset()) -> bool:
    text = ast.get_source_segment(source, node) or ""
    if _has_escape_marker(text):
        return False
    if _is_plugin_root_text(text):
        return True
    for name_node in ast.walk(node):
        if isinstance(name_node, ast.Name) and name_node.id in plugin_root_names:
            return True
    for call_node in ast.walk(node):
        if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Name) \
                and call_node.func.id in rooted_funcs:
            return True
    return False


def _open_call_is_write(call: ast.Call) -> bool:
    mode_text = None
    if len(call.args) >= 2:
        arg = call.args[1]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            mode_text = arg.value
        else:
            return False  # non-literal mode -- can't classify, don't flag
    for kw in call.keywords:
        if kw.arg == "mode":
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                mode_text = kw.value.value
            else:
                return False
    if mode_text is None:
        return False  # default mode is "r" -- a read, not a write
    return bool(_WRITE_MODE_RE.search(mode_text))


_SHUTIL_DEST_ARG = {
    "copy": 1, "copy2": 1, "copyfile": 1, "move": 1, "copytree": 1,
}


def _scan_python_file(path: pathlib.Path, repo_root: pathlib.Path) -> list:
    violations = []
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return violations

    pass1_names = _classify_python_vars(tree, source)
    rooted_funcs = _classify_python_functions(tree, source, pass1_names)
    plugin_root_names = _classify_python_vars(tree, source, rooted_funcs=rooted_funcs)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        # open(path, "w"...)
        if isinstance(func, ast.Name) and func.id == "open":
            if _open_call_is_write(node) and node.args:
                target = node.args[0]
                if _expr_is_violation(target, source, plugin_root_names, rooted_funcs):
                    violations.append(Violation(
                        path, node.lineno,
                        f"open(...) write targets plugin-root path: "
                        f"{ast.get_source_segment(source, target)}",
                        repo_root=repo_root,
                    ))
            continue

        # <expr>.write_text(...)
        if isinstance(func, ast.Attribute) and func.attr == "write_text":
            target = func.value
            if _expr_is_violation(target, source, plugin_root_names, rooted_funcs):
                violations.append(Violation(
                    path, node.lineno,
                    f".write_text(...) targets plugin-root path: "
                    f"{ast.get_source_segment(source, target)}",
                    repo_root=repo_root,
                ))
            continue

        # shutil.copy/copy2/copyfile/move/copytree(src, dst)
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) \
                and func.value.id == "shutil" and func.attr in _SHUTIL_DEST_ARG:
            dest_idx = _SHUTIL_DEST_ARG[func.attr]
            dest = None
            if len(node.args) > dest_idx:
                dest = node.args[dest_idx]
            else:
                for kw in node.keywords:
                    if kw.arg in ("dst", "destination", "dest"):
                        dest = kw.value
            if dest is not None and _expr_is_violation(dest, source, plugin_root_names, rooted_funcs):
                violations.append(Violation(
                    path, node.lineno,
                    f"shutil.{func.attr}(...) targets plugin-root path: "
                    f"{ast.get_source_segment(source, dest)}",
                    repo_root=repo_root,
                ))

    return violations


# ---------------------------------------------------------------------------
# Bash scanning (line-based regex)
# ---------------------------------------------------------------------------

_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(\S.*)$")
# Redirect: one or two `>` not preceded by a digit/`&` (fd redirect) and not
# followed by `&` (e.g. `>&2`). Captures the destination token.
_REDIRECT_RE = re.compile(r'(?<![0-9&])(>{1,2})(?!&)\s*"?([^\s"|;&]+)"?')
_CP_MV_TEE_RE = re.compile(r'(?:^|[\s;|&])(cp|mv|tee)\s+(.+)$')


def _bash_classify_vars(lines: list) -> dict:
    names = {}
    for line in lines:
        m = _ASSIGN_RE.match(line)
        if not m:
            continue
        name, rhs = m.group(1), m.group(2)
        if _has_escape_marker(rhs):
            names[name] = False
            continue
        rooted = _is_plugin_root_text(rhs)
        if not rooted:
            for other, other_rooted in names.items():
                if other_rooted and f"${other}" in rhs:
                    rooted = True
                    break
        names[name] = rooted
    return {n for n, rooted in names.items() if rooted}


def _bash_token_is_violation(token: str, plugin_root_names: set) -> bool:
    if _has_escape_marker(token):
        return False
    if _is_plugin_root_text(token):
        return True
    for name in plugin_root_names:
        if f"${name}" in token or f"${{{name}}}" in token:
            return True
    return False


def _last_dest_token(rest: str) -> str:
    """For `cp a b`, `mv a b`, `tee a` -- best-effort last-token extraction,
    skipping trailing pipe/redirect fragments and leading flags."""
    rest = rest.split("#", 1)[0].strip()
    for stopper in ("|", "&&", ";"):
        if stopper in rest:
            rest = rest.split(stopper, 1)[0]
    tokens = [t for t in rest.split() if not t.startswith("-")]
    return tokens[-1].strip('"') if tokens else ""


def _scan_bash_file(path: pathlib.Path, repo_root: pathlib.Path) -> list:
    violations = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations
    lines = text.splitlines()
    plugin_root_names = _bash_classify_vars(lines)

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        for m in _REDIRECT_RE.finditer(line):
            dest = m.group(2)
            if _bash_token_is_violation(dest, plugin_root_names):
                violations.append(Violation(
                    path, i, f"redirect `{m.group(1)}` writes to plugin-root path: {dest}",
                    repo_root=repo_root,
                ))

        m = _CP_MV_TEE_RE.search(line)
        if m:
            cmd, rest = m.group(1), m.group(2)
            dest = _last_dest_token(rest)
            if dest and _bash_token_is_violation(dest, plugin_root_names):
                violations.append(Violation(
                    path, i, f"`{cmd}` writes to plugin-root path: {dest}",
                    repo_root=repo_root,
                ))

    return violations


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def scan_repo(repo_root: pathlib.Path) -> list:
    violations = []
    for f in _iter_source_files(repo_root):
        if f.suffix == ".py":
            violations.extend(_scan_python_file(f, repo_root))
        elif f.suffix == ".sh":
            violations.extend(_scan_bash_file(f, repo_root))
    return violations


def main() -> int:
    violations = scan_repo(REPO_ROOT)
    if violations:
        print(f"=== Persistence boundary violations ({len(violations)}) ===")
        for v in violations:
            print(f"FAIL: {v}")
        print(
            "\nWrite target(s) above resolve under the plugin's own "
            "installed directory (${CLAUDE_PLUGIN_ROOT}). Per the "
            "customization-persistence contract, user- or project-level "
            "customizations must be written only under project space "
            "(.forge/) or user space (~/.claude/...)."
        )
        return 1
    print("Persistence boundary: PASS (no plugin-root writes detected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
