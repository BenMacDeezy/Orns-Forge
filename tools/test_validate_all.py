import contextlib
import io
import os
import pathlib
import tempfile
import unittest

from validate_all import main

VALID_TASK = """---
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

INVALID_TASK = VALID_TASK.replace("state: ready", "state: doing")

VALID_SPEC = """---
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

INVALID_SPEC = VALID_SPEC.replace("status: draft", "status: wip")

VALID_MEMORY = """---
name: prefer-line-anchored-regex
description: Section checks must be line-anchored, not substring.
type: gotcha
created: 2026-07-17T12:00:00Z
updated: 2026-07-17T12:00:00Z
superseded-by: null
---

A whole-file substring test lets a heading named in prose escape the
missing-section check.
"""

INVALID_MEMORY = VALID_MEMORY.replace("type: gotcha", "type: idea")

VALID_CONFIG = """# Forge config

## Routing overrides
(none)

## Budgets
- session-token-cap: none
- max-tasks-per-session: none

## Queue
- claim-staleness-hours: 0.5
- max-parallel-tasks: 3

## Gates
- build: none (no build step)
- test: python -m pytest tools/ -q
- lint: none (no linter configured)
"""

INVALID_CONFIG = VALID_CONFIG.replace(
    "## Gates\n- build: none (no build step)\n"
    "- test: python -m pytest tools/ -q\n"
    "- lint: none (no linter configured)\n", "")


class TestValidateAll(unittest.TestCase):
    def _build_repo(self, task_text, spec_text, memory_text=None, config_text=None):
        tmp = tempfile.mkdtemp()
        tasks_dir = pathlib.Path(tmp, ".forge", "queue", "tasks")
        specs_dir = pathlib.Path(tmp, ".forge", "specs")
        memory_dir = pathlib.Path(tmp, ".forge", "memory")
        tasks_dir.mkdir(parents=True)
        specs_dir.mkdir(parents=True)
        memory_dir.mkdir(parents=True)
        (tasks_dir / "fg-3fa9-example.md").write_text(task_text, encoding="utf-8")
        (specs_dir / "2026-07-17-example.md").write_text(spec_text, encoding="utf-8")
        # MEMORY.md is the running index, not a fact file — must be excluded
        # from validation even when malformed.
        (memory_dir / "MEMORY.md").write_text("not a fact file\n", encoding="utf-8")
        if memory_text is not None:
            (memory_dir / "gotcha-example.md").write_text(memory_text, encoding="utf-8")
        if config_text is not None:
            (pathlib.Path(tmp, ".forge") / "forge.md").write_text(
                config_text, encoding="utf-8")
        return tmp

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

    def test_task_only_fail(self):
        tmp = self._build_repo(INVALID_TASK, VALID_SPEC)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 1)
        self.assertIn("fg-3fa9-example.md", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertEqual(len(summary_lines), 1)
        self.assertIn("2 file(s) checked, 1 error(s)", summary_lines[0])

    def test_spec_only_fail(self):
        tmp = self._build_repo(VALID_TASK, INVALID_SPEC)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 1)
        self.assertIn("2026-07-17-example.md", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertEqual(len(summary_lines), 1)
        self.assertIn("2 file(s) checked, 1 error(s)", summary_lines[0])

    def test_both_fail(self):
        tmp = self._build_repo(INVALID_TASK, INVALID_SPEC)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 1)
        self.assertIn("fg-3fa9-example.md", out)
        self.assertIn("2026-07-17-example.md", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertEqual(len(summary_lines), 1)
        self.assertIn("2 file(s) checked, 2 error(s)", summary_lines[0])

    def test_both_clean(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertEqual(len(summary_lines), 1)
        self.assertIn("2 file(s) checked, 0 error(s)", summary_lines[0])

    def test_memory_fail_reported(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC, memory_text=INVALID_MEMORY)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 1)
        self.assertIn("gotcha-example.md", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertEqual(len(summary_lines), 1)
        self.assertIn("3 file(s) checked, 1 error(s)", summary_lines[0])

    def test_memory_md_index_excluded_even_if_malformed(self):
        # MEMORY.md ("not a fact file\n") is always written by _build_repo and
        # would fail validate_memory's frontmatter check if it were included.
        tmp = self._build_repo(VALID_TASK, VALID_SPEC, memory_text=VALID_MEMORY)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertNotIn("MEMORY.md", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertIn("3 file(s) checked, 0 error(s)", summary_lines[0])

    def _run_with_args(self, tmp, argv):
        cwd = os.getcwd()
        os.chdir(tmp)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = main(argv)
        finally:
            os.chdir(cwd)
        return code, buf.getvalue()

    def test_explicit_path_args_honored(self):
        # Only the task path is passed explicitly; the (invalid) spec file
        # sitting in the same repo must NOT be picked up via globbing.
        tmp = self._build_repo(VALID_TASK, INVALID_SPEC)
        task_path = str(pathlib.Path(tmp, ".forge", "queue", "tasks",
                                     "fg-3fa9-example.md"))
        code, out = self._run_with_args(tmp, [task_path])
        self.assertEqual(code, 0)
        self.assertNotIn("2026-07-17-example.md", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertIn("1 file(s) checked, 0 error(s)", summary_lines[0])

    def test_nonexistent_path_reports_clean_error(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC)
        ghost = str(pathlib.Path(tmp, ".forge", "queue", "tasks", "ghost.md"))
        code, out = self._run_with_args(tmp, [ghost])
        self.assertEqual(code, 1)
        self.assertIn("ghost.md", out)

    def test_duplicate_task_id_reported(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC)
        tasks_dir = pathlib.Path(tmp, ".forge", "queue", "tasks")
        (tasks_dir / "fg-3fa9-duplicate.md").write_text(VALID_TASK, encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 1)
        self.assertIn("duplicate id", out)

    def test_duplicate_spec_id_reported(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC)
        specs_dir = pathlib.Path(tmp, ".forge", "specs")
        (specs_dir / "2026-07-18-dup.md").write_text(VALID_SPEC, encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 1)
        self.assertIn("duplicate id", out)

    def test_config_absent_not_counted(self):
        # No forge.md written -- existing behavior (2 files: task + spec)
        # must be unaffected by the new wiring.
        tmp = self._build_repo(VALID_TASK, VALID_SPEC)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertIn("2 file(s) checked, 0 error(s)", summary_lines[0])

    def test_config_valid_counted_and_clean(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC, config_text=VALID_CONFIG)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertIn("3 file(s) checked, 0 error(s)", summary_lines[0])

    def test_config_invalid_reported(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC, config_text=INVALID_CONFIG)
        code, out = self._run_in(tmp)
        self.assertEqual(code, 1)
        self.assertIn("forge.md", out)
        self.assertIn("Gates", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertIn("3 file(s) checked, 1 error(s)", summary_lines[0])

    def test_queue_tasks_debris_warns_in_default_sweep(self):
        # A zero-byte .md file and an extensionless file in queue/tasks/ are
        # invisible to the *.md glob; validate_all's default task sweep must
        # surface them as warnings (never errors, never parsed) -- mirrors
        # validate_task.py's own main() default-mode behavior.
        tmp = self._build_repo(VALID_TASK, VALID_SPEC)
        tasks_dir = pathlib.Path(tmp, ".forge", "queue", "tasks")
        (tasks_dir / "fg-e104-empty.md").write_text("", encoding="utf-8")
        (tasks_dir / "fg-e105--forge").write_text("junk", encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertIn(
            "WARNING: non-task debris in queue/tasks: fg-e104-empty.md", out)
        self.assertIn(
            "WARNING: non-task debris in queue/tasks: fg-e105--forge", out)

    def test_explicit_config_path_routes(self):
        tmp = self._build_repo(VALID_TASK, VALID_SPEC, config_text=INVALID_CONFIG)
        config_path = str(pathlib.Path(tmp, ".forge", "forge.md"))
        code, out = self._run_with_args(tmp, [config_path])
        self.assertEqual(code, 1)
        self.assertIn("forge.md", out)
        summary_lines = [l for l in out.splitlines() if "file(s) checked" in l]
        self.assertIn("1 file(s) checked, 1 error(s)", summary_lines[0])
        # No other repo files should be swept in via globbing.
        self.assertNotIn("fg-3fa9-example.md", out)


if __name__ == "__main__":
    unittest.main()
