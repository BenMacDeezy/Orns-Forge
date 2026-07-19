import io, os, sys, tempfile, pathlib, unittest
from unittest import mock
import validate_spec
from validate_spec import validate, main

DRAFT = """---
id: spec-a3f1
title: Auth hardening
status: draft
created: 2026-07-17
approved-date: null
---

## Goal
Harden the auth endpoints against abuse.

## Non-goals
- Rewriting the session store.

## Acceptance criteria
- WHEN a client exceeds 10 auth attempts per minute, THE SYSTEM SHALL return 429.

## Risks
- Lockout of legitimate users -> tune the threshold.

## Task decomposition
- [ ] Add rate limiter -- tier: full -- middleware on auth routes.

## Changelog
(none)
"""

APPROVED = DRAFT.replace("status: draft", "status: approved").replace(
    "approved-date: null", "approved-date: 2026-07-17")


class TestSpecValidator(unittest.TestCase):
    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_valid_draft_passes(self):
        self.assertEqual(validate(self._write(DRAFT)), [])

    def test_valid_approved_passes(self):
        self.assertEqual(validate(self._write(APPROVED)), [])

    def test_missing_frontmatter_fails(self):
        errs = validate(self._write("# no frontmatter\n"))
        self.assertTrue(any("frontmatter" in e for e in errs))

    def test_bad_status_fails(self):
        errs = validate(self._write(DRAFT.replace("status: draft", "status: wip")))
        self.assertTrue(any("status" in e for e in errs))

    def test_bad_id_fails(self):
        errs = validate(self._write(DRAFT.replace("id: spec-a3f1", "id: spec-1")))
        self.assertTrue(any("id" in e for e in errs))

    def test_approved_requires_approved_date(self):
        broken = APPROVED.replace("approved-date: 2026-07-17", "approved-date: null")
        errs = validate(self._write(broken))
        self.assertTrue(any("approved-date" in e for e in errs))

    def test_draft_forbids_approved_date(self):
        broken = DRAFT.replace("approved-date: null", "approved-date: 2026-07-17")
        errs = validate(self._write(broken))
        self.assertTrue(any("approved-date" in e for e in errs))

    def test_missing_section_fails(self):
        errs = validate(self._write(DRAFT.replace(
            "## Risks\n- Lockout of legitimate users -> tune the threshold.\n\n", "")))
        self.assertTrue(any("Risks" in e for e in errs))

    def test_prose_only_section_reported_missing(self):
        # The "## Risks" header is removed and its heading text appears only as
        # inline body prose. A whole-file substring check would let that prose
        # satisfy the presence test and instead surface a spurious "out of
        # order" error. The section must be reported as *missing*, not
        # *misordered*.
        prose_only = DRAFT.replace(
            "## Risks\n- Lockout of legitimate users -> tune the threshold.\n\n",
            "Nothing to note in the ## Risks section yet.\n\n")
        self.assertNotEqual(prose_only, DRAFT)
        errs = validate(self._write(prose_only))
        self.assertTrue(any("missing section" in e and "Risks" in e
                            for e in errs))
        self.assertFalse(any("order" in e for e in errs))

    def test_out_of_order_sections_fail(self):
        shuffled = DRAFT.replace(
            "## Goal\nHarden the auth endpoints against abuse.\n\n"
            "## Non-goals\n- Rewriting the session store.\n\n",
            "## Non-goals\n- Rewriting the session store.\n\n"
            "## Goal\nHarden the auth endpoints against abuse.\n\n")
        self.assertNotEqual(shuffled, DRAFT)
        errs = validate(self._write(shuffled))
        self.assertTrue(any("order" in e for e in errs))

    def test_acceptance_needs_ears(self):
        broken = DRAFT.replace(
            "- WHEN a client exceeds 10 auth attempts per minute, THE SYSTEM SHALL return 429.",
            "- make auth safer")
        errs = validate(self._write(broken))
        self.assertTrue(any("EARS" in e for e in errs))

    def test_approved_with_clarification_fails(self):
        broken = APPROVED.replace(
            "## Goal\nHarden the auth endpoints against abuse.",
            "## Goal\nHarden the auth endpoints. [NEEDS CLARIFICATION] which endpoints?")
        errs = validate(self._write(broken))
        self.assertTrue(any("NEEDS CLARIFICATION" in e for e in errs))

    def test_draft_with_clarification_passes(self):
        ok = DRAFT.replace(
            "## Goal\nHarden the auth endpoints against abuse.",
            "## Goal\nHarden the auth endpoints. [NEEDS CLARIFICATION] which endpoints?")
        self.assertEqual(validate(self._write(ok)), [])

    def test_section_header_inside_fence_only_reported_missing(self):
        # "## Risks" only appears inside a fenced code block, never as a real
        # header. It must still be reported missing.
        fenced = DRAFT.replace(
            "## Risks\n- Lockout of legitimate users -> tune the threshold.\n\n",
            "```\n## Risks\n- Lockout of legitimate users -> tune the threshold.\n```\n\n")
        self.assertNotEqual(fenced, DRAFT)
        errs = validate(self._write(fenced))
        self.assertTrue(any("missing section" in e and "Risks" in e
                            for e in errs))

    def test_superseded_requires_approved_date(self):
        superseded = DRAFT.replace("status: draft", "status: superseded")
        errs = validate(self._write(superseded))
        self.assertTrue(any("approved-date" in e for e in errs))

    def test_superseded_with_approved_date_passes(self):
        superseded = APPROVED.replace("status: approved", "status: superseded")
        self.assertEqual(validate(self._write(superseded)), [])

    def test_bom_prefixed_file_parses(self):
        errs = validate(self._write("﻿" + DRAFT))
        self.assertEqual(errs, [])

    def test_ears_section_uses_real_header_not_prose_mention(self):
        # A frontmatter comment line reads exactly like the real
        # "## Acceptance criteria" header and sits earlier in the file. It
        # must not be mistaken for the real, line-anchored header.
        tricked = DRAFT.replace(
            "created: 2026-07-17\n"
            "approved-date: null\n"
            "---",
            "created: 2026-07-17\n"
            "approved-date: null\n"
            "## Acceptance criteria\n"
            "---")
        self.assertNotEqual(tricked, DRAFT)
        errs = validate(self._write(tricked))
        self.assertFalse(any("EARS" in e for e in errs))

    def test_quoted_status_scalar_unquoted(self):
        quoted = DRAFT.replace("status: draft", 'status: "draft"')
        self.assertNotEqual(quoted, DRAFT)
        errs = validate(self._write(quoted))
        self.assertEqual(errs, [])

    def test_nonexistent_path_reports_clean_error(self):
        ghost = str(pathlib.Path(tempfile.gettempdir()) /
                    "spec-does-not-exist-0001.md")
        errs = validate(ghost)
        self.assertEqual(len(errs), 1)
        self.assertIn("spec-does-not-exist-0001.md", errs[0])

    def test_six_char_id_passes(self):
        errs = validate(self._write(DRAFT.replace("id: spec-a3f1", "id: spec-a3f1c2")))
        self.assertEqual(errs, [])

    def test_three_char_id_fails(self):
        errs = validate(self._write(DRAFT.replace("id: spec-a3f1", "id: spec-a3f")))
        self.assertTrue(any("bad id" in e for e in errs))

    def test_nine_char_id_fails(self):
        errs = validate(self._write(DRAFT.replace("id: spec-a3f1", "id: spec-a3f1c2b34")))
        self.assertTrue(any("bad id" in e for e in errs))

    def test_schema_version_absent_is_ok(self):
        self.assertNotIn("schema-version", DRAFT)
        self.assertEqual(validate(self._write(DRAFT)), [])

    def test_schema_version_1_is_ok(self):
        stamped = DRAFT.replace("approved-date: null\n---",
                                "approved-date: null\nschema-version: 1\n---")
        self.assertNotEqual(stamped, DRAFT)
        self.assertEqual(validate(self._write(stamped)), [])

    def test_schema_version_2_reports_upgrade_message(self):
        newer = DRAFT.replace("approved-date: null\n---",
                              "approved-date: null\nschema-version: 2\n---")
        self.assertNotEqual(newer, DRAFT)
        errs = validate(self._write(newer))
        self.assertTrue(any("newer Forge" in e and "schema-version 2" in e
                            and "upgrade" in e for e in errs))

    # -- BUG 1: UnicodeDecodeError caught cleanly --

    def test_utf16_encoded_file_reports_clean_error_not_crash(self):
        f = tempfile.NamedTemporaryFile("wb", suffix=".md", delete=False)
        f.write(DRAFT.encode("utf-16"))
        f.close()
        errs = validate(f.name)
        self.assertEqual(len(errs), 1)
        self.assertIn("cannot read file", errs[0])

    # -- BUG 2: multiline list continuation must not apply to spec scalars --

    def test_status_as_multiline_list_reports_clean_error_not_crash(self):
        broken = DRAFT.replace(
            "status: draft", "status:\n  - draft\n  - approved")
        self.assertNotEqual(broken, DRAFT)
        errs = validate(self._write(broken))  # must not raise TypeError
        self.assertTrue(any("bad status" in e for e in errs), errs)

    # -- fg-a11030: a colon-containing stray continuation line under a
    # scalar field must not silently smuggle a garbage frontmatter key --

    def test_colon_containing_continuation_under_scalar_field_is_malformed(self):
        broken = DRAFT.replace(
            "status: draft", "status: draft\n  - subitem: sneaky")
        self.assertNotEqual(broken, DRAFT)
        fields, errors, _ = validate_spec._parse_frontmatter(broken)
        self.assertNotIn("- subitem", fields)
        self.assertTrue(
            any("malformed frontmatter line" in e for e in errors), errors)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("malformed frontmatter line" in e for e in errs), errs)

    # -- BUG 4: defensive isinstance guard on id --

    def test_id_as_list_reports_clean_error_not_crash(self):
        path = self._write(DRAFT)
        fields, errors, body = validate_spec._parse_frontmatter(DRAFT)
        fields["id"] = ["spec-a3f1"]
        with mock.patch.object(validate_spec, "_parse_frontmatter",
                               return_value=(fields, errors, body)):
            errs = validate(path)  # must not raise TypeError
        self.assertTrue(any("bad id" in e for e in errs), errs)

    # -- BUG 7: EARS check must not see fenced example content --

    def test_ears_clause_inside_fence_within_section_not_counted(self):
        # The real "## Acceptance criteria" header is present and unfenced,
        # but its only EARS-shaped content is inside a fenced code example,
        # not real filled-in criteria.
        fenced = DRAFT.replace(
            "## Acceptance criteria\n"
            "- WHEN a client exceeds 10 auth attempts per minute, "
            "THE SYSTEM SHALL return 429.\n",
            "## Acceptance criteria\n"
            "Example:\n```\n- WHEN a client exceeds 10 auth attempts per "
            "minute, THE SYSTEM SHALL return 429.\n```\n")
        self.assertNotEqual(fenced, DRAFT)
        errs = validate(self._write(fenced))
        self.assertTrue(any("EARS" in e for e in errs), errs)

    # -- BUG 8: [NEEDS CLARIFICATION] mention inside a fence is not a bypass
    # trigger --

    def test_clarify_marker_inside_fence_does_not_false_positive(self):
        mentioned = APPROVED.replace(
            "## Changelog\n(none)\n",
            "## Changelog\n```\nConvention: write [NEEDS CLARIFICATION] "
            "when unsure.\n```\n")
        self.assertNotEqual(mentioned, APPROVED)
        errs = validate(self._write(mentioned))
        self.assertFalse(any("NEEDS CLARIFICATION" in e for e in errs), errs)

    # -- BUG 10: title required-field check only checked presence --

    def test_empty_title_fails(self):
        broken = DRAFT.replace("title: Auth hardening", "title:")
        self.assertNotEqual(broken, DRAFT)
        errs = validate(self._write(broken))
        self.assertTrue(any("title" in e for e in errs), errs)

    # -- BUG 20: schema-version lower bound --

    def test_schema_version_zero_fails(self):
        broken = DRAFT.replace("approved-date: null\n---",
                               "approved-date: null\nschema-version: 0\n---")
        self.assertNotEqual(broken, DRAFT)
        errs = validate(self._write(broken))
        self.assertTrue(any("bad schema-version" in e for e in errs), errs)

    def test_schema_version_negative_fails(self):
        broken = DRAFT.replace("approved-date: null\n---",
                               "approved-date: null\nschema-version: -5\n---")
        self.assertNotEqual(broken, DRAFT)
        errs = validate(self._write(broken))
        self.assertTrue(any("bad schema-version" in e for e in errs), errs)

    # -- fg-a11021: a non-numeric schema-version must hit the
    # `except (TypeError, ValueError)` branch, not just the int-range checks --

    def test_schema_version_non_numeric_fails(self):
        broken = DRAFT.replace("approved-date: null\n---",
                               "approved-date: null\nschema-version: abc\n---")
        self.assertNotEqual(broken, DRAFT)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("bad schema-version" in e and "abc" in e and
                "integer" in e for e in errs), errs)

    # -- BUG 19: em-dash output must not crash under a legacy codepage --

    def test_em_dash_message_does_not_crash_under_legacy_codepage(self):
        tmp = tempfile.mkdtemp()
        specs_dir = pathlib.Path(tmp, ".forge", "specs")
        specs_dir.mkdir(parents=True)
        newer = DRAFT.replace("approved-date: null\n---",
                              "approved-date: null\nschema-version: 2\n---")
        (specs_dir / "2026-07-17-example.md").write_text(newer, encoding="utf-8")

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
