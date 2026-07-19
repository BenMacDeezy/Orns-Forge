# tools/test_validate_memory_bleed.py
"""Craft-memory bleed check tests (fg-a10203).

`validate_memory.validate(path, warnings=...)` scopes bleed detection to the
plugin-level craft store ONLY (`<plugin-root>/memory/*.md`, derived from
path: parent dir named "memory" whose own parent is NOT ".forge"). Project
store facts (`.forge/memory/*.md`) never run these checks, no matter what
they contain -- see docs/conventions.md, "Craft-memory bleed check —
2026-07".

Warnings are advisory only: they never appear in the returned error list and
never change validate()'s pass/fail contract, mirroring validate_task.py's
warnings-list pattern.
"""
import pathlib
import tempfile
import unittest

from validate_memory import validate

FACT_TEMPLATE = """---
name: {name}
description: test fact for craft-memory bleed check
type: gotcha
created: 2026-07-18T12:00:00Z
updated: 2026-07-18T12:00:00Z
superseded-by: null
---

{body}
"""


class TestCraftMemoryBleedCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = pathlib.Path(self.tmp.name)

        # Craft (plugin-level) store: <plugin-root>/memory/*.md
        self.plugin_root = root / "plugin-root"
        self.craft_dir = self.plugin_root / "memory"
        self.craft_dir.mkdir(parents=True)
        # A real file in the plugin tree, for the "legit reference" fixture.
        tools_dir = self.plugin_root / "tools"
        tools_dir.mkdir()
        (tools_dir / "validate_task.py").write_text("# stub\n", encoding="utf-8")

        # Project store: <project-root>/.forge/memory/*.md
        self.project_dir = root / "some-project" / ".forge" / "memory"
        self.project_dir.mkdir(parents=True)

    def _write_craft(self, name, body):
        path = self.craft_dir / f"{name}.md"
        path.write_text(FACT_TEMPLATE.format(name=name, body=body),
                        encoding="utf-8")
        return str(path)

    def _write_project(self, name, body):
        path = self.project_dir / f"{name}.md"
        path.write_text(FACT_TEMPLATE.format(name=name, body=body),
                        encoding="utf-8")
        return str(path)

    # -- warns: each bleed class, in isolation, produces exactly one warning --

    def test_absolute_path_outside_plugin_warns(self):
        path = self._write_craft(
            "bleed-c-path",
            "See C:\\Users\\someone\\notes.txt for the original writeup.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("C:\\Users\\someone\\notes.txt", warnings[0])
        self.assertIn(path, warnings[0])

    def test_drive_letter_other_project_path_warns(self):
        path = self._write_craft(
            "bleed-d-path",
            "Compare against D:\\other-repo\\src\\main.py for context.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("D:\\other-repo\\src\\main.py", warnings[0])

    def test_github_handle_warns(self):
        path = self._write_craft(
            "bleed-handle",
            "Ask hockeyben for the context behind this decision.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("hockeyben", warnings[0])

    def test_nonexistent_plugin_file_reference_warns(self):
        path = self._write_craft(
            "bleed-missing-file",
            "See tools/nonexistent.py for the old implementation.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("tools/nonexistent.py", warnings[0])

    # -- does not warn: legit cross-references and out-of-scope store --

    def test_legit_github_issue_url_does_not_warn(self):
        path = self._write_craft(
            "legit-url",
            "Filed as https://github.com/anthropics/forge/issues/42 upstream.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_legit_real_plugin_file_reference_does_not_warn(self):
        path = self._write_craft(
            "legit-file",
            "See tools/validate_task.py for the established pattern.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_project_store_fact_with_project_path_does_not_warn(self):
        # Same offending content as the craft-store fixtures above, but
        # filed in the PROJECT store -- the check is craft-store-scoped
        # only, so nothing fires here.
        path = self._write_project(
            "proj-fact",
            "Ask hockeyben; see C:\\Users\\someone\\some-project\\main.py "
            "and tools/nonexistent.py.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    # -- combination + contract preservation --

    def test_multiple_bleeds_in_one_fact_count_exactly(self):
        path = self._write_craft(
            "bleed-combo",
            "Ask hockeyben; see C:\\Users\\someone\\notes.txt and "
            "D:\\other-repo\\x.py for the old version.")
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(len(warnings), 3)

    def test_default_call_without_warnings_param_is_unaffected(self):
        # The pre-existing call contract (no warnings= argument) must keep
        # working exactly as before: errors only, bleed content never
        # leaks into the error list, no crash.
        path = self._write_craft(
            "bleed-no-warn-param",
            "Ask hockeyben about C:\\Users\\someone\\notes.txt.")
        errs = validate(path)
        self.assertEqual(errs, [])

    def test_warnings_never_change_error_contract_on_malformed_fact(self):
        # A malformed craft fact (bad type) still reports the same error
        # whether or not bleed content is also present, and the bleed
        # warning is still collected independently.
        bad = FACT_TEMPLATE.format(
            name="bleed-and-bad-type",
            body="Ask hockeyben for details.").replace(
                "type: gotcha", "type: idea")
        path = self.craft_dir / "bleed-and-bad-type.md"
        path.write_text(bad, encoding="utf-8")
        warnings = []
        errs = validate(str(path), warnings=warnings)
        self.assertTrue(any("type" in e for e in errs))
        self.assertEqual(len(warnings), 1)
        self.assertIn("hockeyben", warnings[0])


if __name__ == "__main__":
    unittest.main()
