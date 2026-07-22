import contextlib, io, os, sys, tempfile, pathlib, unittest
from unittest import mock
import validate_task
from validate_task import validate, main, _sibling_task_ids

VALID = """---
id: fg-3fa9
title: Add rate limiting
state: ready
tier: standard
priority: 2
spec: null
blocks: []
blocked-by: []
claimed-by: null
parallel-safe: true
created: 2026-07-16
updated: 2026-07-16
---

## Acceptance criteria
- WHEN a client exceeds 10 attempts per minute, THE SYSTEM SHALL return 429.

## Execution plan
(pending)

## Routing record
(pending)

## Attempt log
(pending)

## Outcome
(pending)
"""

FULL_VALID = VALID.replace("tier: standard", "tier: full").replace(
    "spec: null", "spec: docs/specs/example.md")


class TestValidator(unittest.TestCase):
    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_valid_file_passes(self):
        self.assertEqual(validate(self._write(VALID)), [])

    def test_missing_frontmatter_fails(self):
        errs = validate(self._write("# no frontmatter\n"))
        self.assertTrue(any("frontmatter" in e for e in errs))

    def test_bad_state_fails(self):
        errs = validate(self._write(VALID.replace("state: ready", "state: doing")))
        self.assertTrue(any("state" in e for e in errs))

    def test_bad_id_fails(self):
        # "zz" fails both the legacy fg-xxxx hex shape AND the new
        # readable-name-id shape (too short, min 3 chars) -- unlike a
        # value such as "task-1", which the spec-f0c2 name-id convention
        # (see TestReadableNameIds, below) makes legitimately valid.
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: zz")))
        self.assertTrue(any("id" in e for e in errs))

    def test_active_requires_claim(self):
        errs = validate(self._write(VALID.replace("state: ready", "state: active")))
        self.assertTrue(any("claimed-by" in e for e in errs))

    def test_nonactive_forbids_claim(self):
        errs = validate(self._write(
            VALID.replace("claimed-by: null",
                          "claimed-by: sess-ab12 @ 2026-07-16T10:00:00Z")))
        self.assertTrue(any("claimed-by" in e for e in errs))

    def test_missing_section_fails(self):
        errs = validate(self._write(VALID.replace("## Outcome\n(pending)\n", "")))
        self.assertTrue(any("Outcome" in e for e in errs))

    def test_prose_only_section_reported_missing(self):
        # The "## Outcome" header is removed and its heading text appears only as
        # inline body prose. A whole-file substring check would let that prose
        # satisfy the presence test and instead surface a spurious "out of order"
        # error. The section must be reported as *missing*, not *misordered*.
        prose_only = VALID.replace(
            "## Outcome\n(pending)\n",
            "Nothing to note in the ## Outcome section yet.\n")
        self.assertNotEqual(prose_only, VALID)
        errs = validate(self._write(prose_only))
        self.assertTrue(any("missing section" in e and "Outcome" in e
                            for e in errs))
        self.assertFalse(any("order" in e for e in errs))

    def test_ready_requires_ears_clause(self):
        broken = VALID.replace(
            "- WHEN a client exceeds 10 attempts per minute, THE SYSTEM SHALL return 429.",
            "- make it work somehow")
        errs = validate(self._write(broken))
        self.assertTrue(any("EARS" in e for e in errs))

    def test_backlog_allows_empty_criteria(self):
        relaxed = VALID.replace("state: ready", "state: backlog").replace(
            "- WHEN a client exceeds 10 attempts per minute, THE SYSTEM SHALL return 429.",
            "(to be drafted)")
        self.assertEqual(validate(self._write(relaxed)), [])

    def test_shuffled_section_order_fails(self):
        # Swap the "Acceptance criteria" and "Execution plan" blocks; all five
        # sections are still present, only their order changes.
        shuffled = VALID.replace(
            "## Acceptance criteria\n"
            "- WHEN a client exceeds 10 attempts per minute, THE SYSTEM SHALL return 429.\n\n"
            "## Execution plan\n"
            "(pending)\n\n",
            "## Execution plan\n"
            "(pending)\n\n"
            "## Acceptance criteria\n"
            "- WHEN a client exceeds 10 attempts per minute, THE SYSTEM SHALL return 429.\n\n")
        self.assertNotEqual(shuffled, VALID)
        errs = validate(self._write(shuffled))
        self.assertTrue(any("order" in e for e in errs))

    def test_correct_order_has_no_order_error(self):
        errs = validate(self._write(VALID))
        self.assertFalse(any("order" in e for e in errs))

    def test_body_reference_to_later_section_not_flagged(self):
        # Real headers stay in correct order, but the Execution plan's body
        # prose literally mentions a later section's heading text. A naive
        # substring search for that heading would find this in-body mention
        # instead of the real "## Attempt log" header further down, and
        # wrongly conclude the headers are out of order.
        referencing = VALID.replace(
            "## Execution plan\n(pending)\n\n",
            "## Execution plan\n(pending) -- see ## Attempt log for progress "
            "and note it will be handled in ## Outcome.\n\n")
        self.assertNotEqual(referencing, VALID)
        errs = validate(self._write(referencing))
        self.assertFalse(any("order" in e for e in errs))

    def test_full_tier_null_spec_fails(self):
        broken = FULL_VALID.replace("spec: docs/specs/example.md", "spec: null")
        errs = validate(self._write(broken))
        self.assertTrue(any("spec" in e for e in errs))

    def test_full_tier_with_spec_passes(self):
        self.assertEqual(validate(self._write(FULL_VALID)), [])

    def test_standard_tier_null_spec_not_flagged_for_spec(self):
        errs = validate(self._write(VALID))
        self.assertFalse(any("spec" in e for e in errs))

    # -- fg-a11019: tier:full spec must exist and be status: approved --

    def _write_forge_task(self, tmp_dir, name, text):
        tasks_dir = pathlib.Path(tmp_dir, ".forge", "queue", "tasks")
        tasks_dir.mkdir(parents=True, exist_ok=True)
        p = tasks_dir / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def _write_forge_spec(self, tmp_dir, name, status):
        specs_dir = pathlib.Path(tmp_dir, ".forge", "specs")
        specs_dir.mkdir(parents=True, exist_ok=True)
        text = (
            "---\n"
            "id: spec-0001\n"
            "title: Example spec\n"
            f"status: {status}\n"
            "created: 2026-07-16\n"
            "approved-date: 2026-07-16\n"
            "---\n\n## Goal\nExample.\n")
        (specs_dir / name).write_text(text, encoding="utf-8")

    def test_full_tier_with_nonexistent_spec_file_under_dotforge_fails(self):
        tmp = tempfile.mkdtemp()
        task_text = FULL_VALID.replace(
            "spec: docs/specs/example.md", "spec: specs/does-not-exist.md")
        path = self._write_forge_task(tmp, "fg-3fa9-main.md", task_text)
        errs = validate(path)
        self.assertTrue(
            any("spec" in e and "not found" in e for e in errs), errs)

    def test_full_tier_spec_not_approved_fails(self):
        tmp = tempfile.mkdtemp()
        self._write_forge_spec(tmp, "draft-spec.md", "draft")
        task_text = FULL_VALID.replace(
            "spec: docs/specs/example.md", "spec: specs/draft-spec.md")
        path = self._write_forge_task(tmp, "fg-3fa9-main.md", task_text)
        errs = validate(path)
        self.assertTrue(
            any("approved" in e and "spec" in e for e in errs), errs)

    def test_full_tier_spec_exists_and_approved_passes(self):
        tmp = tempfile.mkdtemp()
        self._write_forge_spec(tmp, "approved-spec.md", "approved")
        task_text = FULL_VALID.replace(
            "spec: docs/specs/example.md", "spec: specs/approved-spec.md")
        path = self._write_forge_task(tmp, "fg-3fa9-main.md", task_text)
        self.assertEqual(validate(path), [])

    def test_full_tier_spec_outside_dotforge_tree_skips_check(self):
        # A task file with no resolvable `.forge/` ancestor (e.g. a
        # standalone fixture) can't have its `specs/` reference resolved --
        # the check must be skipped, not misreported as an error.
        self.assertEqual(validate(self._write(FULL_VALID)), [])

    def test_section_header_inside_fence_only_reported_missing(self):
        # "## Outcome" only appears inside a fenced code block, never as a
        # real header. It must still be reported missing, not treated as
        # present just because the text occurs somewhere in the file.
        fenced = VALID.replace(
            "## Outcome\n(pending)\n",
            "```\n## Outcome\n(pending)\n```\n")
        self.assertNotEqual(fenced, VALID)
        errs = validate(self._write(fenced))
        self.assertTrue(any("missing section" in e and "Outcome" in e
                            for e in errs))

    def test_blocked_by_multiline_list_parses(self):
        multiline = VALID.replace(
            "blocked-by: []",
            "blocked-by:\n  - fg-1111\n  - fg-2222")
        self.assertNotEqual(multiline, VALID)
        errs = validate(self._write(multiline))
        self.assertFalse(any("frontmatter" in e for e in errs))
        self.assertEqual(errs, [])

    def test_bom_prefixed_file_parses(self):
        errs = validate(self._write("﻿" + VALID))
        self.assertEqual(errs, [])

    def test_ears_section_uses_real_header_not_prose_mention(self):
        # A frontmatter comment line happens to read exactly like the real
        # "## Acceptance criteria" header and sits earlier in the file than
        # the genuine header. A search that isn't scoped to the document body
        # (or that isn't line-anchored) can latch onto this decoy and
        # mis-extract the section body, producing a false "needs EARS
        # clause" error even though the real section clearly has one.
        tricked = VALID.replace(
            "updated: 2026-07-16\n---",
            "updated: 2026-07-16\n## Acceptance criteria\n---")
        self.assertNotEqual(tricked, VALID)
        errs = validate(self._write(tricked))
        self.assertFalse(any("EARS" in e for e in errs))

    def test_quoted_state_scalar_unquoted(self):
        quoted = VALID.replace("state: ready", 'state: "ready"')
        self.assertNotEqual(quoted, VALID)
        errs = validate(self._write(quoted))
        self.assertEqual(errs, [])

    def test_nonexistent_path_reports_clean_error(self):
        ghost = str(pathlib.Path(tempfile.gettempdir()) /
                    "fg-does-not-exist-0001.md")
        errs = validate(ghost)
        self.assertEqual(len(errs), 1)
        self.assertIn("fg-does-not-exist-0001.md", errs[0])

    def test_four_char_id_passes(self):
        # Original id width still validates (backward-compatible).
        self.assertEqual(validate(self._write(VALID.replace(
            "id: fg-3fa9", "id: fg-3fa9"))), [])

    def test_six_char_id_passes(self):
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: fg-3fa9c1")))
        self.assertEqual(errs, [])

    def test_three_char_id_now_valid_as_name_id(self):
        # Pre-spec-f0c2 this failed as an off-length hex id (hex ids are
        # 4-8 chars after "fg-"). "fg-3fa" is 6 chars total, all lowercase
        # alnum/hyphen, starts/ends alnum, no "--" -- it now legitimately
        # satisfies the readable-name-id shape (see TestReadableNameIds),
        # so it is accepted, not because it's read as hex, but because it
        # happens to also be valid kebab-case.
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: fg-3fa")))
        self.assertEqual(errs, [])

    def test_nine_char_id_now_valid_as_name_id(self):
        # Same reasoning as test_three_char_id_now_valid_as_name_id: an
        # off-length (9-char) hex id is now accepted as a valid name id.
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: fg-3fa9c1a22")))
        self.assertEqual(errs, [])

    def test_schema_version_absent_is_ok(self):
        self.assertNotIn("schema-version", VALID)
        self.assertEqual(validate(self._write(VALID)), [])

    def test_schema_version_1_is_ok(self):
        stamped = VALID.replace("updated: 2026-07-16\n---",
                                "updated: 2026-07-16\nschema-version: 1\n---")
        self.assertNotEqual(stamped, VALID)
        self.assertEqual(validate(self._write(stamped)), [])

    def test_trivial_bugfix_title_warns_without_error(self):
        trivial_bug = VALID.replace("tier: standard", "tier: trivial").replace(
            "title: Add rate limiting", "title: Fix login crash")
        self.assertNotEqual(trivial_bug, VALID)
        warnings = []
        errs = validate(self._write(trivial_bug), warnings=warnings)
        self.assertEqual(errs, [])  # warning must not become an error
        self.assertTrue(any("bug fixes normally need tier: standard" in w
                            for w in warnings))

    def test_trivial_bugfix_criteria_warns(self):
        trivial_bug = VALID.replace("tier: standard", "tier: trivial").replace(
            "THE SYSTEM SHALL return 429.",
            "THE SYSTEM SHALL no longer be broken by a regression.")
        self.assertNotEqual(trivial_bug, VALID)
        warnings = []
        errs = validate(self._write(trivial_bug), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertTrue(warnings)

    def test_standard_tier_bugfix_language_does_not_warn(self):
        standard_bug = VALID.replace("title: Add rate limiting",
                                     "title: Fix login crash")
        self.assertNotEqual(standard_bug, VALID)
        warnings = []
        errs = validate(self._write(standard_bug), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_trivial_without_bugfix_language_does_not_warn(self):
        trivial_clean = VALID.replace("tier: standard", "tier: trivial")
        warnings = []
        errs = validate(self._write(trivial_clean), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_warning_word_boundary_no_false_positive(self):
        # "prefix" and "debug" contain fix/bug as substrings but must not
        # trip the \b-anchored bug-fix regex.
        trivial = VALID.replace("tier: standard", "tier: trivial").replace(
            "title: Add rate limiting", "title: Add prefix to debug output")
        warnings = []
        errs = validate(self._write(trivial), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_validate_without_warnings_arg_still_works(self):
        # Backward-compatible single-arg call (validate_all.py relies on it).
        trivial_bug = VALID.replace("tier: standard", "tier: trivial").replace(
            "title: Add rate limiting", "title: Fix login crash")
        self.assertEqual(validate(self._write(trivial_bug)), [])

    def test_schema_version_2_reports_upgrade_message(self):
        newer = VALID.replace("updated: 2026-07-16\n---",
                              "updated: 2026-07-16\nschema-version: 2\n---")
        self.assertNotEqual(newer, VALID)
        errs = validate(self._write(newer))
        self.assertTrue(any("newer Forge" in e and "schema-version 2" in e
                            and "upgrade" in e for e in errs))

    # -- claimed-by format --

    def test_claimed_by_bad_format_fails(self):
        broken = VALID.replace("state: ready", "state: active").replace(
            "claimed-by: null", "claimed-by: bob")
        errs = validate(self._write(broken))
        self.assertTrue(any("claimed-by" in e and "format" in e for e in errs))

    def test_claimed_by_missing_timestamp_fails(self):
        broken = VALID.replace("state: ready", "state: active").replace(
            "claimed-by: null", "claimed-by: sess-ab12")
        errs = validate(self._write(broken))
        self.assertTrue(any("claimed-by" in e and "format" in e for e in errs))

    def test_claimed_by_bad_session_hex_width_fails(self):
        broken = VALID.replace("state: ready", "state: active").replace(
            "claimed-by: null", "claimed-by: sess-ab1 @ 2026-07-16T10:00:00Z")
        errs = validate(self._write(broken))
        self.assertTrue(any("claimed-by" in e and "format" in e for e in errs))

    def test_claimed_by_valid_format_active_passes(self):
        ok = VALID.replace("state: ready", "state: active").replace(
            "claimed-by: null", "claimed-by: sess-ab12 @ 2026-07-16T10:00:00Z")
        self.assertEqual(validate(self._write(ok)), [])

    def test_claimed_by_null_not_format_checked(self):
        # null is the valid non-active value; the format regex must not fire
        # on it.
        errs = validate(self._write(VALID))
        self.assertFalse(any("format" in e for e in errs))

    # -- parallel-safe enum --

    def test_parallel_safe_yes_fails(self):
        broken = VALID.replace("parallel-safe: true", "parallel-safe: yes")
        errs = validate(self._write(broken))
        self.assertTrue(any("parallel-safe" in e for e in errs))

    def test_parallel_safe_capitalized_fails(self):
        broken = VALID.replace("parallel-safe: true", "parallel-safe: True")
        errs = validate(self._write(broken))
        self.assertTrue(any("parallel-safe" in e for e in errs))

    def test_parallel_safe_empty_fails(self):
        broken = VALID.replace("parallel-safe: true", "parallel-safe:")
        errs = validate(self._write(broken))
        self.assertTrue(any("parallel-safe" in e for e in errs))

    def test_parallel_safe_true_passes(self):
        self.assertEqual(validate(self._write(VALID)), [])

    def test_parallel_safe_false_passes(self):
        ok = VALID.replace("parallel-safe: true", "parallel-safe: false")
        self.assertEqual(validate(self._write(ok)), [])

    # -- blocked-by existence (warning, not error) --

    def _write_in(self, tmp_dir, name, text):
        p = pathlib.Path(tmp_dir, name)
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_blocked_by_unknown_id_warns(self):
        tmp = tempfile.mkdtemp()
        main_task = VALID.replace("blocked-by: []", "blocked-by: [fg-9999]")
        path = self._write_in(tmp, "fg-3fa9-main.md", main_task)
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])  # unresolved blocked-by is a warning, not an error
        self.assertTrue(any("fg-9999" in w and "blocked-by" in w for w in warnings))

    def test_blocked_by_known_id_no_warning(self):
        tmp = tempfile.mkdtemp()
        sibling = VALID.replace("id: fg-3fa9", "id: fg-9999")
        self._write_in(tmp, "fg-9999-sibling.md", sibling)
        main_task = VALID.replace("blocked-by: []", "blocked-by: [fg-9999]")
        path = self._write_in(tmp, "fg-3fa9-main.md", main_task)
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertFalse(any("blocked-by" in w for w in warnings))

    def test_blocked_by_multiple_ids_only_missing_ones_warn(self):
        tmp = tempfile.mkdtemp()
        sibling = VALID.replace("id: fg-3fa9", "id: fg-9999")
        self._write_in(tmp, "fg-9999-sibling.md", sibling)
        main_task = VALID.replace(
            "blocked-by: []", "blocked-by: [fg-9999, fg-8888]")
        path = self._write_in(tmp, "fg-3fa9-main.md", main_task)
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertTrue(any("fg-8888" in w for w in warnings))
        self.assertFalse(any("fg-9999" in w for w in warnings))

    def test_blocked_by_without_warnings_arg_no_scan(self):
        # Backward-compatible single-arg call must not attempt the scan (and
        # must not error even though fg-9999 doesn't exist anywhere).
        tmp = tempfile.mkdtemp()
        main_task = VALID.replace("blocked-by: []", "blocked-by: [fg-9999]")
        path = self._write_in(tmp, "fg-3fa9-main.md", main_task)
        self.assertEqual(validate(path), [])

    def test_inline_blocked_by_list_multiple_ids_parses(self):
        # Real queue files use inline "[fg-a, fg-b]" syntax (not the
        # multiline "- fg-a" form already covered above); it must parse into
        # a real list, not an opaque string.
        multi = VALID.replace("blocked-by: []", "blocked-by: [fg-1111, fg-2222]")
        errs = validate(self._write(multi))
        self.assertFalse(any("frontmatter" in e for e in errs))
        self.assertEqual(errs, [])

    def test_sibling_task_ids_reads_id_field(self):
        tmp = tempfile.mkdtemp()
        self._write_in(tmp, "fg-9999-sibling.md", VALID.replace(
            "id: fg-3fa9", "id: fg-9999"))
        path = self._write_in(tmp, "fg-3fa9-main.md", VALID)
        ids = _sibling_task_ids(path)
        self.assertIn("fg-9999", ids)

    # -- inquest C-7: unclosed inline list must error, not vanish --

    def test_unclosed_blocked_by_bracket_is_error(self):
        # 'blocked-by: [fg-0001, fg-0002' (no closing bracket) must not
        # silently parse to a raw string with zero errors -- that's exactly
        # how real dependency edges vanished from the DAG (inquest C-7).
        broken = VALID.replace(
            "blocked-by: []", "blocked-by: [fg-0001, fg-0002")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("blocked-by" in e and ("malformed" in e or "unclosed" in e)
                for e in errs),
            f"expected a malformed/unclosed blocked-by list error, got: {errs}")

    def test_unclosed_blocks_bracket_is_error(self):
        broken = VALID.replace("blocks: []", "blocks: [fg-0001, fg-0002")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("blocks" in e and ("malformed" in e or "unclosed" in e)
                for e in errs),
            f"expected a malformed/unclosed blocks list error, got: {errs}")

    def test_well_formed_inline_lists_still_no_malformed_error(self):
        # Guard against over-triggering: a normal, properly closed inline
        # list must never be flagged as malformed.
        ok = VALID.replace("blocked-by: []", "blocked-by: [fg-1111, fg-2222]")
        errs = validate(self._write(ok))
        self.assertFalse(
            any("malformed" in e or "unclosed" in e for e in errs),
            f"unexpected malformed-list error on well-formed list: {errs}")

    # -- inquest C-8: blocks needs the same sibling-existence warning as
    # blocked-by already has --

    def test_blocks_unknown_id_warns(self):
        tmp = tempfile.mkdtemp()
        main_task = VALID.replace("blocks: []", "blocks: [fg-9999]")
        path = self._write_in(tmp, "fg-3fa9-main.md", main_task)
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])  # unresolved blocks is a warning, not an error
        self.assertTrue(any("fg-9999" in w and "blocks" in w for w in warnings))

    def test_blocks_known_id_no_warning(self):
        tmp = tempfile.mkdtemp()
        sibling = VALID.replace("id: fg-3fa9", "id: fg-9999")
        self._write_in(tmp, "fg-9999-sibling.md", sibling)
        main_task = VALID.replace("blocks: []", "blocks: [fg-9999]")
        path = self._write_in(tmp, "fg-3fa9-main.md", main_task)
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertFalse(any("blocks" in w for w in warnings))

    def test_blocks_multiple_ids_only_missing_ones_warn(self):
        tmp = tempfile.mkdtemp()
        sibling = VALID.replace("id: fg-3fa9", "id: fg-9999")
        self._write_in(tmp, "fg-9999-sibling.md", sibling)
        main_task = VALID.replace("blocks: []", "blocks: [fg-9999, fg-8888]")
        path = self._write_in(tmp, "fg-3fa9-main.md", main_task)
        warnings = []
        errs = validate(path, warnings=warnings)
        self.assertEqual(errs, [])
        self.assertTrue(any("fg-8888" in w for w in warnings))
        self.assertFalse(any("fg-9999" in w and "blocks" in w for w in warnings))

class TestQueueTasksDebrisWarning(unittest.TestCase):
    """Files in .forge/queue/tasks/ that are NOT *.md, or *.md files that are
    zero bytes, are invisible to the `*.md` glob every validator uses. main()'s
    default mode (no explicit paths) must surface them as a WARNING -- never
    an error, and never attempt to parse them -- so they don't sit as silent
    debris forever (docs/audits/2026-07-17-sweep2-hygiene.md, A2)."""

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

    def _build_repo(self):
        tmp = tempfile.mkdtemp()
        tasks_dir = pathlib.Path(tmp, ".forge", "queue", "tasks")
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "fg-3fa9-example.md").write_text(VALID, encoding="utf-8")
        return tmp, tasks_dir

    def test_zero_byte_md_file_warns_not_errors(self):
        tmp, tasks_dir = self._build_repo()
        (tasks_dir / "fg-e104-empty.md").write_text("", encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)  # a warning must never flip the exit code
        self.assertIn(
            "WARNING: non-task debris in queue/tasks: fg-e104-empty.md", out)

    def test_extensionless_file_warns_not_errors(self):
        tmp, tasks_dir = self._build_repo()
        (tasks_dir / "fg-e105--forge").write_text("junk", encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertIn(
            "WARNING: non-task debris in queue/tasks: fg-e105--forge", out)

    def test_uppercase_md_extension_not_flagged_as_debris(self):
        # BUG 14: the actual task-loading glob ("*.md") is case-insensitive
        # on Windows, but _task_dir_debris's suffix check was case-sensitive
        # -- a legitimately-named "fg-6001-upper.MD" validated fine via the
        # glob but was ALSO independently flagged as debris.
        tmp, tasks_dir = self._build_repo()
        (tasks_dir / "fg-6001-upper.MD").write_text(
            VALID.replace("id: fg-3fa9", "id: fg-6001"), encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertNotIn("non-task debris", out)
        self.assertIn("2 file(s) checked", out)

    def test_normal_run_unchanged(self):
        tmp, _ = self._build_repo()
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertNotIn("WARNING", out)
        self.assertIn("1 file(s) checked, 0 error(s), 0 warning(s)", out)

    def test_explicit_paths_do_not_scan_for_debris(self):
        # When explicit paths are passed, main() must not sweep the directory
        # for debris -- only default (no-argv) mode does.
        tmp, tasks_dir = self._build_repo()
        (tasks_dir / "fg-e104-empty.md").write_text("", encoding="utf-8")
        task_path = str(tasks_dir / "fg-3fa9-example.md")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main([task_path])
        self.assertEqual(code, 0)
        self.assertNotIn("WARNING", buf.getvalue())


class TestShardSchema(unittest.TestCase):
    """fg-a10811: additive, optional shard-by/max-shards/shard-key frontmatter
    fields. All three are OPTIONAL; SUPPORTED_SCHEMA stays 1; an unsharded
    task must validate byte-identically to today."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    # -- clause 1: unsharded task is unaffected (byte-identical baseline) --

    def test_unsharded_task_still_validates_clean(self):
        self.assertNotIn("shard-by", VALID)
        self.assertNotIn("max-shards", VALID)
        self.assertNotIn("shard-key", VALID)
        self.assertEqual(validate(self._write(VALID)), [])

    # -- clause 1: valid declarations of each shard-by kind --

    def test_shard_by_files_with_max_shards_passes(self):
        ok = VALID.replace("parallel-safe: true",
                           "parallel-safe: true\nshard-by: files\nmax-shards: 4")
        self.assertEqual(validate(self._write(ok)), [])

    def test_shard_by_items_with_max_shards_and_shard_key_passes(self):
        ok = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: items\nmax-shards: 3\n"
            "shard-key: file-list")
        self.assertEqual(validate(self._write(ok)), [])

    def test_shard_by_ranges_with_max_shards_and_shard_key_passes(self):
        ok = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: ranges\nmax-shards: 2\n"
            "shard-key: line-range")
        self.assertEqual(validate(self._write(ok)), [])

    # -- clause 4: shard-by: files needs no shard-key, and no file-locality
    # assertion happens here (that's deferred to shard-eligibility time) --

    def test_shard_by_files_without_shard_key_ok(self):
        ok = VALID.replace("parallel-safe: true",
                           "parallel-safe: true\nshard-by: files\nmax-shards: 2")
        self.assertNotIn("shard-key", ok)
        self.assertEqual(validate(self._write(ok)), [])

    # -- clause 1/2: max-shards is required once shard-by is declared --

    def test_shard_by_without_max_shards_fails(self):
        broken = VALID.replace("parallel-safe: true",
                               "parallel-safe: true\nshard-by: files")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-shards" in e for e in errs), errs)

    def test_shard_by_items_without_shard_key_fails(self):
        broken = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: items\nmax-shards: 3")
        errs = validate(self._write(broken))
        self.assertTrue(any("shard-key" in e for e in errs), errs)

    def test_shard_by_ranges_without_shard_key_fails(self):
        broken = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: ranges\nmax-shards: 3")
        errs = validate(self._write(broken))
        self.assertTrue(any("shard-key" in e for e in errs), errs)

    # -- clause 2: malformed values raise an error, never a silent skip --

    def test_shard_by_bad_literal_fails(self):
        broken = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: chunks\nmax-shards: 2")
        errs = validate(self._write(broken))
        self.assertTrue(any("shard-by" in e for e in errs), errs)

    def test_max_shards_less_than_2_fails(self):
        broken = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: files\nmax-shards: 1")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-shards" in e for e in errs), errs)

    def test_max_shards_non_int_fails(self):
        broken = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: files\nmax-shards: many")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-shards" in e for e in errs), errs)

    def test_shard_key_as_multiline_list_fails(self):
        # The multiline "- item" YAML list form is the general list-typed
        # parse path in _parse_frontmatter -- shard-key must reject it, not
        # silently accept a list where the splitter expects a scalar.
        broken = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: items\nmax-shards: 3\n"
            "shard-key:\n  - a\n  - b")
        errs = validate(self._write(broken))
        self.assertTrue(any("shard-key" in e for e in errs), errs)

    def test_shard_key_as_inline_bracket_list_fails(self):
        # Reuses the existing inline "[a, b]" flow-list parsing pattern
        # already scoped to blocks/blocked-by; shard-key opts into the same
        # pattern so a bracket-style list is caught too, not just the
        # multiline dash form.
        broken = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: items\nmax-shards: 3\n"
            "shard-key: [a, b]")
        errs = validate(self._write(broken))
        self.assertTrue(any("shard-key" in e for e in errs), errs)

    # -- clause 3: shard fields are orthogonal to parallel-safe; the
    # validator never selects/decides eligibility, only shape-checks --

    def test_shard_by_coexists_with_parallel_safe_true(self):
        ok = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: files\nmax-shards: 2")
        self.assertEqual(validate(self._write(ok)), [])

    def test_shard_by_coexists_with_parallel_safe_false(self):
        ok = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: false\nshard-by: files\nmax-shards: 2")
        self.assertEqual(validate(self._write(ok)), [])

    # -- SUPPORTED_SCHEMA stays 1 alongside shard fields --

    def test_shard_fields_with_explicit_schema_version_1_passes(self):
        ok = VALID.replace(
            "updated: 2026-07-16\n---",
            "updated: 2026-07-16\nschema-version: 1\n---").replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: files\nmax-shards: 2")
        self.assertEqual(validate(self._write(ok)), [])

    # -- no cmd: shard source (deferred per OQ2) --

    def test_cmd_field_is_not_a_recognized_shard_field(self):
        # cmd: as a shard source is explicitly deferred (OQ2 security
        # decision) -- a task declaring it alongside a valid shard-by must
        # not be silently accepted as a fourth shard field, but it also
        # isn't a field this validator knows about at all, so it is neither
        # required nor specially rejected -- it simply passes through
        # unvalidated, same as any other unrecognized key today.
        ok = VALID.replace(
            "parallel-safe: true",
            "parallel-safe: true\nshard-by: files\nmax-shards: 2\n"
            "cmd: echo hi")
        self.assertEqual(validate(self._write(ok)), [])


if __name__ == "__main__":
    unittest.main()


class TestScalarFieldBracketedValue(unittest.TestCase):
    """fg-9a0305: a bracketed value on a scalar field must degrade to a clean
    field-format error, never a TypeError crash (regression: global inline-list
    parsing turned `id: [x]` into a list and crashed ID_RE.match)."""

    def _write(self, text):
        d = tempfile.mkdtemp()
        p = pathlib.Path(d) / "fg-3fa9-x.md"
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_bracketed_id_reports_bad_id_not_crash(self):
        errs = validate(self._write(VALID.replace("id: fg-3fa9",
                                                  "id: [fg-3fa9]")))
        self.assertTrue(any("id" in e for e in errs),
                        f"expected a bad-id error, got: {errs}")

    def test_bracketed_blocked_by_still_parses_as_list(self):
        errs = validate(self._write(VALID.replace(
            "blocked-by: []", "blocked-by: [fg-aaaa, fg-bbbb]")))
        self.assertTrue(all("blocked-by" not in e for e in errs),
                        f"unexpected blocked-by errors: {errs}")


class TestUnicodeDecodeErrorIsCaught(unittest.TestCase):
    """BUG 1: UnicodeDecodeError is a ValueError subclass, not an OSError --
    a file written as UTF-16 (PowerShell's Out-File/Set-Content default)
    must report a clean per-file error, never crash validate() with an
    unhandled traceback."""

    def test_utf16_encoded_file_reports_clean_error_not_crash(self):
        f = tempfile.NamedTemporaryFile("wb", suffix=".md", delete=False)
        f.write(VALID.encode("utf-16"))
        f.close()
        errs = validate(f.name)
        self.assertEqual(len(errs), 1)
        self.assertIn("cannot read file", errs[0])


class TestMultilineListScopedToListFields(unittest.TestCase):
    """BUG 2: the multiline "  - item" continuation must only apply to the
    known list-shaped fields (blocks/blocked-by/shard-key) -- a scalar field
    hand-edited into block-list form must not silently become a Python
    list and crash a downstream `in STATES`-style check."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_state_as_multiline_list_reports_clean_error_not_crash(self):
        broken = VALID.replace("state: ready", "state:\n  - ready\n  - active")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))  # must not raise TypeError
        self.assertTrue(any("bad state" in e for e in errs), errs)

    def test_tier_as_multiline_list_reports_clean_error_not_crash(self):
        broken = VALID.replace(
            "tier: standard", "tier:\n  - standard\n  - full")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("bad tier" in e for e in errs), errs)

    # -- fg-a11030: a colon-containing stray continuation line under a
    # scalar field must not silently smuggle a garbage frontmatter key --

    def test_colon_containing_continuation_under_scalar_field_is_malformed(self):
        broken = VALID.replace(
            "state: ready", "state: ready\n  - subitem: sneaky")
        self.assertNotEqual(broken, VALID)
        fields, errors, _ = validate_task._parse_frontmatter(broken)
        self.assertNotIn("- subitem", fields)
        self.assertTrue(
            any("malformed frontmatter line" in e for e in errors), errors)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("malformed frontmatter line" in e for e in errs), errs)


class TestDefensiveTypeGuards(unittest.TestCase):
    """BUG 4 / BUG 5: defense-in-depth isinstance guards on `id` and `title`
    even if some future/edge parse path (not just the multiline-list shape
    covered by BUG 2) hands `_parse_frontmatter` a non-string value for
    either field -- validate() must report a clean error, not crash."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_id_as_list_reports_clean_error_not_crash(self):
        path = self._write(VALID)
        fields, errors, body = validate_task._parse_frontmatter(VALID)
        fields["id"] = ["fg-3fa9"]
        with mock.patch.object(validate_task, "_parse_frontmatter",
                               return_value=(fields, errors, body)):
            errs = validate(path)  # must not raise TypeError
        self.assertTrue(any("bad id" in e for e in errs), errs)

    def test_title_as_list_reports_clean_error_not_crash(self):
        trivial = VALID.replace("tier: standard", "tier: trivial")
        path = self._write(trivial)
        fields, errors, body = validate_task._parse_frontmatter(trivial)
        fields["title"] = ["Fix", "login", "crash"]
        with mock.patch.object(validate_task, "_parse_frontmatter",
                               return_value=(fields, errors, body)):
            errs = validate(path, warnings=[])  # must not raise TypeError
        self.assertIsInstance(errs, list)


class TestBlocksMustBeList(unittest.TestCase):
    """BUG 11: an unbracketed scalar (e.g. `blocks: fg-0002`) must not be
    silently accepted -- downstream tools/queue_graph.py wraps the whole
    string as ONE opaque list element, breaking the dependency DAG."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_bare_scalar_blocks_fails(self):
        broken = VALID.replace("blocks: []", "blocks: fg-0002")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("blocks" in e and "list" in e for e in errs), errs)

    def test_bare_scalar_blocked_by_fails(self):
        broken = VALID.replace("blocked-by: []", "blocked-by: fg-0001, fg-0002")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("blocked-by" in e and "list" in e for e in errs), errs)

    def test_bracketed_blocks_still_passes(self):
        ok = VALID.replace("blocks: []", "blocks: [fg-0001]")
        errs = validate(self._write(ok))
        self.assertFalse(any("must be a bracketed list" in e for e in errs), errs)


class TestSchemaVersionLowerBound(unittest.TestCase):
    """BUG 20: only the upper bound was checked -- schema-version: 0 or a
    negative number must also be rejected."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_schema_version_zero_fails(self):
        broken = VALID.replace("updated: 2026-07-16\n---",
                               "updated: 2026-07-16\nschema-version: 0\n---")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("bad schema-version" in e for e in errs), errs)

    def test_schema_version_negative_fails(self):
        broken = VALID.replace("updated: 2026-07-16\n---",
                               "updated: 2026-07-16\nschema-version: -5\n---")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("bad schema-version" in e for e in errs), errs)

    # -- fg-a11021: a non-numeric schema-version must hit the
    # `except (TypeError, ValueError)` branch, not just the int-range checks --

    def test_schema_version_non_numeric_fails(self):
        broken = VALID.replace("updated: 2026-07-16\n---",
                               "updated: 2026-07-16\nschema-version: abc\n---")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(
            any("bad schema-version" in e and "abc" in e and
                "integer" in e for e in errs), errs)


class TestCreatedUpdatedFormat(unittest.TestCase):
    """BUG 21: created/updated only had presence checked, never format --
    a non-date value must produce a warning."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_bad_created_and_updated_warn(self):
        broken = VALID.replace("created: 2026-07-16", "created: not-a-date").replace(
            "updated: 2026-07-16", "updated: also-not-a-date")
        self.assertNotEqual(broken, VALID)
        warnings = []
        errs = validate(self._write(broken), warnings=warnings)
        self.assertEqual(errs, [])  # a warning, not an error
        self.assertTrue(any("created" in w for w in warnings), warnings)
        self.assertTrue(any("updated" in w for w in warnings), warnings)

    def test_valid_dates_do_not_warn(self):
        warnings = []
        errs = validate(self._write(VALID), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertFalse(any("does not look like" in w for w in warnings))


class TestOutputEncodingSafety(unittest.TestCase):
    """BUG 19: em dashes in printed messages must never crash main() under a
    legacy Windows OEM codepage (cp437/cp850) that can't encode them."""

    def test_em_dash_message_does_not_crash_under_legacy_codepage(self):
        tmp = tempfile.mkdtemp()
        tasks_dir = pathlib.Path(tmp, ".forge", "queue", "tasks")
        tasks_dir.mkdir(parents=True)
        newer = VALID.replace("updated: 2026-07-16\n---",
                              "updated: 2026-07-16\nschema-version: 2\n---")
        (tasks_dir / "fg-3fa9-example.md").write_text(newer, encoding="utf-8")

        self.assertRaises(UnicodeEncodeError, "—".encode, "cp437")

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


class TestReadableNameIds(unittest.TestCase):
    """spec-f0c2 Amendments — 2026-07-20, item 2: new task ids may be a
    human-readable kebab-case name (3-40 chars, [a-z0-9][a-z0-9-]*[a-z0-9],
    no leading/trailing '-', no '--' run), in addition to the legacy
    fg-xxxx hex id, which stays valid and grandfathered forever."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    def test_readable_name_id_passes(self):
        errs = validate(self._write(
            VALID.replace("id: fg-3fa9", "id: database-migration")))
        self.assertEqual(errs, [])

    def test_short_name_id_passes(self):
        # 3 chars is the documented floor.
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: abc")))
        self.assertEqual(errs, [])

    def test_max_length_name_id_passes(self):
        name = "a" * 40
        errs = validate(self._write(VALID.replace("id: fg-3fa9", f"id: {name}")))
        self.assertEqual(errs, [])

    def test_over_length_name_id_fails(self):
        name = "a" * 41
        errs = validate(self._write(VALID.replace("id: fg-3fa9", f"id: {name}")))
        self.assertTrue(any("id" in e for e in errs))

    def test_too_short_name_id_fails(self):
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: ab")))
        self.assertTrue(any("id" in e for e in errs))

    def test_leading_hyphen_name_id_fails(self):
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: -abc")))
        self.assertTrue(any("id" in e for e in errs))

    def test_trailing_hyphen_name_id_fails(self):
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: abc-")))
        self.assertTrue(any("id" in e for e in errs))

    def test_double_hyphen_name_id_fails(self):
        errs = validate(self._write(VALID.replace("id: fg-3fa9", "id: ab--cd")))
        self.assertTrue(any("id" in e for e in errs))

    def test_legacy_hex_ids_still_valid(self):
        # Grandfathering is load-bearing: every currently-shipped shape must
        # stay valid forever.
        for legacy in ("fg-3fa9", "fg-a100", "fg-a11034", "fg-9a0305"):
            with self.subTest(legacy=legacy):
                errs = validate(self._write(
                    VALID.replace("id: fg-3fa9", f"id: {legacy}")))
                self.assertEqual(errs, [])

    def test_near_miss_uppercase_warns_and_errors(self):
        warnings = []
        errs = validate(self._write(
            VALID.replace("id: fg-3fa9", "id: Database-Migration")),
            warnings=warnings)
        self.assertTrue(any("id" in e for e in errs))
        self.assertTrue(any("near-miss" in w for w in warnings), warnings)

    def test_near_miss_underscore_warns_and_errors(self):
        warnings = []
        errs = validate(self._write(
            VALID.replace("id: fg-3fa9", "id: database_migration")),
            warnings=warnings)
        self.assertTrue(any("id" in e for e in errs))
        self.assertTrue(any("near-miss" in w for w in warnings), warnings)

    def test_near_miss_space_warns_and_errors(self):
        warnings = []
        errs = validate(self._write(
            VALID.replace("id: fg-3fa9", "id: database migration")),
            warnings=warnings)
        self.assertTrue(any("id" in e for e in errs))
        self.assertTrue(any("near-miss" in w for w in warnings), warnings)

    def test_hex_lookalike_id_valid_but_warns(self):
        """fg-f0103 P2 follow-up: a typo'd pseudo-hex id ('fg-c01o1') is a
        VALID name id (no error) but must produce the hex-lookalike warning
        so the author notices the likely typo."""
        warnings = []
        errs = validate(self._write(
            VALID.replace("id: fg-3fa9", "id: fg-c01o1")),
            warnings=warnings)
        self.assertFalse(any("bad id" in e for e in errs), errs)
        self.assertTrue(
            any("not a valid hex id" in w for w in warnings), warnings)

    def test_valid_name_id_does_not_near_miss_warn(self):
        warnings = []
        errs = validate(self._write(
            VALID.replace("id: fg-3fa9", "id: database-migration")),
            warnings=warnings)
        self.assertEqual(errs, [])
        self.assertFalse(any("near-miss" in w for w in warnings), warnings)

    def test_bad_id_without_warnings_list_does_not_crash(self):
        # warnings=None (the default) must be a no-op, not a crash, for the
        # near-miss check same as every other warnings-gated check here.
        errs = validate(self._write(
            VALID.replace("id: fg-3fa9", "id: Database_Migration")))
        self.assertTrue(any("id" in e for e in errs))
