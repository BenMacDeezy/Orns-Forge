"""Isolation boundary for the throwaway ledgerkit fixture (fg-a10401 / D4).

`tools/benchmark/fixture/` ships a small synthetic Python package with its
own pytest suite (planted-defect ground truth for the A/B benchmark). That
suite must stay invisible to the repo-wide `pytest tools/ -q` gate (it is
not part of the Forge tool suite and is deliberately allowed to carry its
own planted defects) while still being directly runnable on its own via
`pytest tools/benchmark/fixture -q`.

A static `collect_ignore_glob` can't do both: pytest applies an ancestor
conftest's collect_ignore rules even when the ignored subtree is passed
explicitly on the command line, so a blanket ignore would also silence the
direct-run gate. Instead this hook ignores the fixture tree only when it
was *not* explicitly named in the invocation args -- i.e. it disappears
from a bare `pytest tools/ -q`, but a `pytest tools/benchmark/fixture ...`
(or any invocation naming a path under it) collects normally.
"""
import pathlib

_FIXTURE_DIR = (pathlib.Path(__file__).parent / "fixture").resolve()


def pytest_ignore_collect(collection_path, config):
    path = pathlib.Path(collection_path).resolve()
    if path != _FIXTURE_DIR and _FIXTURE_DIR not in path.parents:
        return None  # outside the fixture tree: no opinion

    invocation_args = [str(a) for a in config.invocation_params.args]
    explicitly_requested = False
    for a in invocation_args:
        if not a or a.startswith("-"):
            continue
        resolved = pathlib.Path(a).resolve()
        if resolved == _FIXTURE_DIR or _FIXTURE_DIR in resolved.parents:
            explicitly_requested = True
            break
    return not explicitly_requested
