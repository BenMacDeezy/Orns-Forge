"""Combined task+spec+memory validation entry point. Zero dependencies.

Runs validate_task.validate (over .forge/queue/tasks/*.md),
validate_spec.validate (over .forge/specs/*.md), and validate_memory.validate
(over .forge/memory/*.md, excluding MEMORY.md), prints one combined summary
line, and exits non-zero if any set has any error.

When given explicit path arguments, those paths are validated instead of the
default globs: each path is routed to task/spec/memory validation by its
parent directory name (".../queue/tasks/*", ".../specs/*", ".../memory/*").
A path that can't be routed is reported as a clean error line rather than
silently ignored or globbed over.
"""
import re, sys, pathlib

# Ensure the sibling validator modules resolve under both invocation forms:
# `python tools/validate_all.py` (puts tools/ on sys.path[0] already) and
# `python -m tools.validate_all` (puts the repo root on sys.path instead).
# Prepending this script's own directory is harmless in the former case and
# required for the latter.
_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import validate_task
import validate_spec
import validate_memory
import validate_config

TASK_GLOB = ".forge/queue/tasks/*.md"
SPEC_GLOB = ".forge/specs/*.md"
MEMORY_GLOB = ".forge/memory/*.md"
CONFIG_DEFAULT = ".forge/forge.md"

_ID_LINE_RE = re.compile(r"(?m)^id:\s*(.+?)\s*$")


def _validate_set(paths, validate_fn, warnings=None):
    """Run `validate_fn` over every path in `paths`, collecting errors.

    Any exception raised by `validate_fn` for a given file (including an
    unforeseen crash the sub-validator itself doesn't guard against) is
    caught and converted into a per-file error entry, so one malformed file
    can never take down the whole batch and lose results for every other
    file being validated in the same run.
    """
    errors = []
    for p in paths:
        try:
            if warnings is not None:
                errors.extend(validate_fn(p, warnings=warnings))
            else:
                errors.extend(validate_fn(p))
        except Exception as e:
            errors.append(f"{p}: internal validator error: {e!r}")
    return errors


def _route_paths(argv):
    """Classify explicit path args by parent directory name (or, for
    forge.md, by filename) into task/spec/memory/config buckets. Returns
    (tasks, specs, memories, configs, unroutable).

    "tasks" and "specs" are ONLY ever meaningful under a real `.forge/`
    tree (`.forge/queue/tasks/`, `.forge/specs/`) -- an unrelated file whose
    parent directory merely happens to be named "specs" must not be
    force-routed into the rigid Forge spec schema, producing a confusing
    wall of false-positive errors. "memory" is deliberately NOT gated the
    same way: it validly spans both the project store (`.forge/memory/`)
    and the plugin-level craft store (`<plugin-root>/memory/`, a sibling of
    `.forge`, never nested inside it) -- validate_memory.py's own
    `_craft_plugin_root` already tells those two apart correctly.
    """
    tasks, specs, memories, configs, unroutable = [], [], [], [], []
    for p in argv:
        path = pathlib.Path(p)
        parent = path.parent.name
        name = path.name
        # Case-insensitive, matching validate_memory.py's
        # `_craft_plugin_root` -- a directory literally named `.Forge` is
        # possible on a case-insensitive-but-preserving filesystem (e.g.
        # Windows) and must still be recognized as a real `.forge/` ancestor
        # (fg-a11034).
        under_forge = any(part.lower() == ".forge"
                          for part in path.resolve().parts)
        if parent == "tasks" and under_forge:
            tasks.append(p)
        elif parent == "specs" and under_forge:
            specs.append(p)
        elif parent == "memory":
            if name.lower() != "memory.md":
                memories.append(p)
        elif name == "forge.md":
            configs.append(p)
        else:
            unroutable.append(p)
    return tasks, specs, memories, configs, unroutable


def _extract_id(path):
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    m = _ID_LINE_RE.search(text)
    if not m:
        return None
    return validate_task._unquote(m.group(1))


def _find_collisions(paths):
    """Report files that share the same frontmatter id within one path set."""
    errors = []
    seen = {}
    for p in paths:
        id_ = _extract_id(p)
        if not id_:
            continue
        if id_ in seen:
            errors.append(f"{p}: duplicate id {id_!r} (also used by {seen[id_]})")
        else:
            seen[id_] = p
    return errors


def main(argv):
    # See validate_task.py's main() for why: em dashes in some messages
    # would otherwise crash under a legacy Windows OEM codepage.
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    route_errors = []
    if argv:
        task_paths, spec_paths, memory_paths, config_paths, unroutable = _route_paths(argv)
        for p in unroutable:
            route_errors.append(
                f"{p}: cannot determine validator (expected a path under "
                f".../queue/tasks/, .../specs/, .../memory/, or named "
                f"forge.md)")
    else:
        # A zero-byte *.md file matches the glob but is debris, not a task --
        # excluded here so it's only ever reported once, as a warning below
        # (mirrors validate_task.py's own main() default-mode filtering).
        task_paths = [str(p) for p in pathlib.Path().glob(TASK_GLOB)
                     if p.stat().st_size > 0]
        spec_paths = [str(p) for p in pathlib.Path().glob(SPEC_GLOB)]
        memory_paths = [str(p) for p in pathlib.Path().glob(MEMORY_GLOB)
                        if p.name.lower() != "memory.md"]
        config_paths = [CONFIG_DEFAULT] if pathlib.Path(CONFIG_DEFAULT).exists() else []

    all_warnings = []
    task_errors = _validate_set(task_paths, validate_task.validate,
                                warnings=all_warnings)
    spec_errors = _validate_set(spec_paths, validate_spec.validate)
    memory_errors = _validate_set(memory_paths, validate_memory.validate,
                                  warnings=all_warnings)
    config_errors = []
    for p in config_paths:
        try:
            config_errors.extend(
                validate_config.validate(p, warnings=all_warnings))
        except Exception as e:
            config_errors.append(f"{p}: internal validator error: {e!r}")
    if not argv:
        all_warnings.extend(
            validate_task._task_dir_debris(pathlib.Path(TASK_GLOB).parent))
    collision_errors = _find_collisions(task_paths) + _find_collisions(spec_paths)

    all_errors = (route_errors + task_errors + spec_errors + memory_errors
                  + config_errors + collision_errors)
    for e in all_errors:
        print(e)
    for w in all_warnings:
        print(f"WARNING: {w}")

    total_files = len(task_paths) + len(spec_paths) + len(memory_paths) + len(config_paths)
    print(f"{total_files} file(s) checked, {len(all_errors)} error(s), "
          f"{len(all_warnings)} warning(s)")

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
