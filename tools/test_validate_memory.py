# tools/test_validate_memory.py
import tempfile, unittest
from validate_memory import validate

VALID = """---
name: prefer-line-anchored-regex
description: Section checks in validate_task.py must be line-anchored, not substring.
type: gotcha
created: 2026-07-17T12:00:00Z
updated: 2026-07-17T12:00:00Z
superseded-by: null
---

A whole-file substring test lets a heading named in prose escape the
missing-section check. Anchor with `(?m)^## ...$`. Discovered on fg-a7c2.
"""


class TestMemoryValidator(unittest.TestCase):
    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_valid_fact_passes(self):
        self.assertEqual(validate(self._write(VALID)), [])

    def test_missing_frontmatter_fails(self):
        errs = validate(self._write("just a note with no frontmatter\n"))
        self.assertTrue(any("frontmatter" in e for e in errs))

    def test_bad_type_fails(self):
        errs = validate(self._write(VALID.replace("type: gotcha", "type: idea")))
        self.assertTrue(any("type" in e for e in errs))

    def test_missing_name_fails(self):
        errs = validate(self._write(
            VALID.replace("name: prefer-line-anchored-regex", "name:")))
        self.assertTrue(any("name" in e for e in errs))

    def test_missing_description_fails(self):
        errs = validate(self._write(VALID.replace(
            "description: Section checks in validate_task.py must be "
            "line-anchored, not substring.", "description:")))
        self.assertTrue(any("description" in e for e in errs))

    def test_missing_field_fails(self):
        errs = validate(self._write(VALID.replace("type: gotcha\n", "")))
        self.assertTrue(any("type" in e for e in errs))

    def test_empty_body_fails(self):
        head = VALID.split("---\n\n")[0] + "---\n\n"
        errs = validate(self._write(head))
        self.assertTrue(any("body" in e for e in errs))

    def test_superseded_pointer_ok(self):
        errs = validate(self._write(
            VALID.replace("superseded-by: null", "superseded-by: decision-x.md")))
        self.assertEqual(errs, [])

    def test_bad_superseded_pointer_fails(self):
        errs = validate(self._write(
            VALID.replace("superseded-by: null", "superseded-by: yes")))
        self.assertTrue(any("superseded-by" in e for e in errs))

    def test_bom_prefixed_file_parses(self):
        errs = validate(self._write("﻿" + VALID))
        self.assertEqual(errs, [])

    def test_quoted_type_scalar_unquoted(self):
        quoted = VALID.replace("type: gotcha", 'type: "gotcha"')
        self.assertNotEqual(quoted, VALID)
        errs = validate(self._write(quoted))
        self.assertEqual(errs, [])

    def test_nonexistent_path_reports_clean_error(self):
        import tempfile as _tempfile, pathlib as _pathlib
        ghost = str(_pathlib.Path(_tempfile.gettempdir()) /
                    "memory-does-not-exist-0001.md")
        errs = validate(ghost)
        self.assertEqual(len(errs), 1)
        self.assertIn("memory-does-not-exist-0001.md", errs[0])

    def test_schema_version_absent_is_ok(self):
        self.assertNotIn("schema-version", VALID)
        self.assertEqual(validate(self._write(VALID)), [])

    def test_schema_version_1_is_ok(self):
        stamped = VALID.replace("superseded-by: null\n---",
                                "superseded-by: null\nschema-version: 1\n---")
        self.assertNotEqual(stamped, VALID)
        self.assertEqual(validate(self._write(stamped)), [])

    def test_schema_version_2_reports_upgrade_message(self):
        newer = VALID.replace("superseded-by: null\n---",
                              "superseded-by: null\nschema-version: 2\n---")
        self.assertNotEqual(newer, VALID)
        errs = validate(self._write(newer))
        self.assertTrue(any("newer Forge" in e and "schema-version 2" in e
                            and "upgrade" in e for e in errs))

    def test_untagged_fact_still_passes(self):
        self.assertNotIn("agents", VALID)
        self.assertEqual(validate(self._write(VALID)), [])

    def test_agents_inline_list_tag_passes(self):
        tagged = VALID.replace(
            "superseded-by: null\n---",
            "superseded-by: null\nagents: [forge-debugger, forge-worker]\n---")
        self.assertNotEqual(tagged, VALID)
        self.assertEqual(validate(self._write(tagged)), [])

    def test_agents_multiline_list_tag_passes(self):
        tagged = VALID.replace(
            "superseded-by: null\n---",
            "superseded-by: null\nagents:\n  - forge-debugger\n  - forge-worker\n---")
        self.assertNotEqual(tagged, VALID)
        self.assertEqual(validate(self._write(tagged)), [])

    def test_agents_scalar_not_list_fails(self):
        bad = VALID.replace(
            "superseded-by: null\n---",
            "superseded-by: null\nagents: forge-debugger\n---")
        errs = validate(self._write(bad))
        self.assertTrue(any("agents" in e and "list" in e for e in errs))

    def test_agents_empty_item_fails(self):
        bad = VALID.replace(
            "superseded-by: null\n---",
            "superseded-by: null\nagents: [forge-debugger, ]\n---")
        errs = validate(self._write(bad))
        self.assertTrue(any("agents" in e for e in errs))

    def test_agents_empty_list_is_valid_and_equivalent_to_absent(self):
        # An explicit empty list must validate identically to the field
        # being absent entirely -- no error either way.
        tagged = VALID.replace(
            "superseded-by: null\n---", "superseded-by: null\nagents: []\n---")
        self.assertNotEqual(tagged, VALID)
        self.assertEqual(validate(self._write(tagged)), [])
        self.assertEqual(validate(self._write(tagged)), validate(self._write(VALID)))

    def test_agents_nested_inline_list_fails(self):
        bad = VALID.replace(
            "superseded-by: null\n---",
            "superseded-by: null\nagents: [[forge-debugger, forge-worker], forge-triage]\n---")
        errs = validate(self._write(bad))
        self.assertTrue(any("agents" in e and "flat list" in e for e in errs))

    def test_agents_nested_multiline_list_fails(self):
        bad = VALID.replace(
            "superseded-by: null\n---",
            "superseded-by: null\nagents:\n  - [forge-debugger, forge-worker]\n  - forge-triage\n---")
        errs = validate(self._write(bad))
        self.assertTrue(any("agents" in e and "flat list" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
