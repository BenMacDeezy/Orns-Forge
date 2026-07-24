# tools/test_validate_memory.py
import contextlib, io, os, sys, tempfile, pathlib, unittest
import validate_memory
from validate_memory import validate, main

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

    # -- BUG 1: UnicodeDecodeError caught cleanly --

    def test_utf16_encoded_file_reports_clean_error_not_crash(self):
        f = tempfile.NamedTemporaryFile("wb", suffix=".md", delete=False)
        f.write(VALID.encode("utf-16"))
        f.close()
        errs = validate(f.name)
        self.assertEqual(len(errs), 1)
        self.assertIn("cannot read file", errs[0])

    # -- BUG 2: multiline list continuation must not apply to memory scalars --

    def test_type_as_multiline_list_reports_clean_error_not_crash(self):
        broken = VALID.replace(
            "type: gotcha", "type:\n  - gotcha\n  - decision")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))  # must not raise TypeError
        self.assertTrue(any("bad type" in e for e in errs), errs)

    # -- fg-a11030: a colon-containing stray continuation line under a
    # scalar field must not silently smuggle a garbage frontmatter key --

    def test_colon_containing_continuation_under_scalar_field_is_malformed(self):
        broken = VALID.replace(
            "type: gotcha", "type: gotcha\n  - subitem: sneaky")
        self.assertNotEqual(broken, VALID)
        fields, errors, _ = validate_memory._parse_frontmatter(broken)
        self.assertNotIn("- subitem", fields)
        self.assertTrue(
            any("malformed frontmatter line" in e for e in errors), errors)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("malformed frontmatter line" in e for e in errs), errs)

    # -- BUG 9: name/description must be a string, not just truthy --

    def test_name_as_inline_bracket_list_fails_cleanly(self):
        # `name: [a, b]` parses to a non-empty list (truthy), which the old
        # `if not fm.get("name")` check silently let through.
        bad = VALID.replace(
            "name: prefer-line-anchored-regex", "name: [a, b]")
        self.assertNotEqual(bad, VALID)
        errs = validate(self._write(bad))  # must not raise, must report
        self.assertTrue(
            any("name" in e and "string" in e for e in errs), errs)

    def test_description_as_inline_bracket_list_fails_cleanly(self):
        bad = VALID.replace(
            "description: Section checks in validate_task.py must be "
            "line-anchored, not substring.",
            "description: [a, b]")
        self.assertNotEqual(bad, VALID)
        errs = validate(self._write(bad))
        self.assertTrue(
            any("description" in e and "string" in e for e in errs), errs)

    # -- BUG 13: MEMORY.md exclusion must be case-insensitive --

    def _run_in(self, tmp):
        cwd = os.getcwd()
        os.chdir(tmp)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = main([])
        finally:
            os.chdir(cwd)
        return code, buf.getvalue()

    def test_differently_cased_memory_index_excluded(self):
        tmp = tempfile.mkdtemp()
        memory_dir = pathlib.Path(tmp, ".forge", "memory")
        memory_dir.mkdir(parents=True)
        (memory_dir / "Memory.md").write_text("not a fact file\n",
                                              encoding="utf-8")
        (memory_dir / "gotcha-example.md").write_text(VALID, encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertIn("1 file(s) checked, 0 error(s)", out)

    # -- BUG 20: schema-version lower bound --

    def test_schema_version_zero_fails(self):
        broken = VALID.replace("superseded-by: null\n---",
                               "superseded-by: null\nschema-version: 0\n---")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("bad schema-version" in e for e in errs), errs)

    def test_schema_version_negative_fails(self):
        broken = VALID.replace("superseded-by: null\n---",
                               "superseded-by: null\nschema-version: -5\n---")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("bad schema-version" in e for e in errs), errs)

    # -- fg-a11021: a non-numeric schema-version must hit the
    # `except (TypeError, ValueError)` branch, not just the int-range checks --

    def test_schema_version_non_numeric_fails(self):
        broken = VALID.replace("superseded-by: null\n---",
                               "superseded-by: null\nschema-version: abc\n---")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("bad schema-version" in e and "abc" in e and
                "integer" in e for e in errs), errs)

    # -- BUG 19: em-dash output must not crash under a legacy codepage --

    def test_em_dash_message_does_not_crash_under_legacy_codepage(self):
        tmp = tempfile.mkdtemp()
        memory_dir = pathlib.Path(tmp, ".forge", "memory")
        memory_dir.mkdir(parents=True)
        newer = VALID.replace(
            "superseded-by: null\n---",
            "superseded-by: null\nschema-version: 2\n---")
        (memory_dir / "gotcha-example.md").write_text(newer, encoding="utf-8")

        cp437_stream = io.TextIOWrapper(io.BytesIO(), encoding="cp437",
                                        errors="strict")
        cwd = os.getcwd()
        os.chdir(tmp)
        real_stdout = sys.stdout
        sys.stdout = cp437_stream
        try:
            code = main([])  # must not raise UnicodeEncodeError
        finally:
            sys.stdout = real_stdout
            os.chdir(cwd)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
