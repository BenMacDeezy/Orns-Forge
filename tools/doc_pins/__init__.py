"""Sharded doc-pin regression tests (fg-a11040).

Each module here holds the doc-pin test classes for one task-id prefix
(e.g. test_fg_9c0304.py -> TestFg9c0304Pins), split out of the former
monolithic tools/test_doc_pins.py so concurrent tasks appending new pins
land in separate files instead of conflicting at a shared tail. Shared
helpers (REPO_ROOT, cached file readers, the conventions corpus loader)
live in _common.py. Cross-cutting classes (TestDocPins,
TestCommandSurfacePins, TestCourtCommandPins, command-count/README/surface
pins) stay in the thinned tools/test_doc_pins.py so external references to
that path keep working.
"""
