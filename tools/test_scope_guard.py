"""Tests for tools/scope_guard.py (project-scope-guard task, 2026-07-20):
the deterministic accelerator behind the kernel/queue "the `.forge/` being
operated on must belong to THIS project" guard.

Uses real `git init` temp repos (not mocked subprocess calls) so the
behavior pinned here is the actual `git rev-parse --show-toplevel`
resolution the guard depends on, not an assumption about its output shape.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scope_guard  # noqa: E402


def _init_repo(path):
    subprocess.run(
        ["git", "init", "-q", str(path)], check=True, capture_output=True
    )


class ResolveProjectDirTests(unittest.TestCase):
    def test_env_var_wins_when_set(self):
        self.assertEqual(
            scope_guard.resolve_project_dir(
                env={"CLAUDE_PROJECT_DIR": "/some/project"}, cwd="/elsewhere"
            ),
            "/some/project",
        )

    def test_falls_back_to_cwd_when_unset(self):
        self.assertEqual(
            scope_guard.resolve_project_dir(env={}, cwd="/elsewhere"),
            "/elsewhere",
        )

    def test_falls_back_to_cwd_when_empty_string(self):
        self.assertEqual(
            scope_guard.resolve_project_dir(
                env={"CLAUDE_PROJECT_DIR": ""}, cwd="/elsewhere"
            ),
            "/elsewhere",
        )


class GitToplevelTests(unittest.TestCase):
    def test_returns_none_outside_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(scope_guard.git_toplevel(d))

    def test_returns_resolved_toplevel_inside_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            top = scope_guard.git_toplevel(d)
            self.assertEqual(top, str(pathlib.Path(d).resolve()))


class CheckScopeTests(unittest.TestCase):
    def test_nonexistent_expected_forge_is_a_match(self):
        # Canonical path equality does not depend on the leaf existing.
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            forge_dir = pathlib.Path(d) / ".forge"
            result = scope_guard.check_scope(forge_dir, project_dir=d)
            self.assertTrue(result.match)
            self.assertEqual(result.reason, "match")
            self.assertEqual(result.expected, str(forge_dir.resolve()))
            self.assertEqual(result.actual, str(forge_dir.resolve()))

    def test_no_git_is_inert(self):
        # project_dir is not inside a git repo at all -- existing
        # cwd-fallback behavior applies, guard does not fire.
        with tempfile.TemporaryDirectory() as d:
            forge_dir = pathlib.Path(d) / ".forge"
            forge_dir.mkdir()
            result = scope_guard.check_scope(forge_dir, project_dir=d)
            self.assertTrue(result.match)
            self.assertEqual(result.reason, "no-git")

    def test_match_at_toplevel(self):
        # project_dir IS the toplevel, forge_dir IS <toplevel>/.forge.
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            forge_dir = pathlib.Path(d) / ".forge"
            forge_dir.mkdir()
            result = scope_guard.check_scope(forge_dir, project_dir=d)
            self.assertTrue(result.match)
            self.assertEqual(result.reason, "match")

    def test_nested_subdir_match_is_zero_friction(self):
        # Only project_dir nesting is zero-friction; actual state remains
        # fixed at the repository root.
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            forge_dir = pathlib.Path(d) / ".forge"
            forge_dir.mkdir()
            subdir = pathlib.Path(d) / "packages" / "app"
            subdir.mkdir(parents=True)
            result = scope_guard.check_scope(forge_dir, project_dir=str(subdir))
            self.assertTrue(result.match)
            self.assertEqual(result.reason, "match")

    def test_nested_same_repo_forge_is_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            subdir = pathlib.Path(d) / "packages" / "app"
            forge_dir = subdir / ".forge"
            forge_dir.mkdir(parents=True)
            result = scope_guard.check_scope(
                forge_dir, project_dir=str(subdir)
            )
            self.assertFalse(result.match)
            self.assertEqual(result.reason, "mismatch")
            self.assertEqual(
                result.expected,
                str((pathlib.Path(d) / ".forge").resolve()),
            )
            self.assertEqual(result.actual, str(forge_dir.resolve()))

    def test_nonexistent_forge_aimed_at_another_repo_is_mismatch(self):
        with tempfile.TemporaryDirectory() as project_repo, \
                tempfile.TemporaryDirectory() as other_repo:
            _init_repo(project_repo)
            _init_repo(other_repo)
            forge_dir = pathlib.Path(other_repo) / ".forge"
            self.assertFalse(forge_dir.exists())
            result = scope_guard.check_scope(
                forge_dir, project_dir=project_repo
            )
            self.assertFalse(result.match)
            self.assertEqual(result.reason, "mismatch")
            self.assertEqual(result.actual, str(forge_dir.resolve()))

    def test_project_toplevel_git_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            forge_dir = pathlib.Path(d) / ".forge"
            with mock.patch.object(
                scope_guard,
                "git_toplevel",
                side_effect=scope_guard.GitToplevelError(
                    "detected dubious ownership"
                ),
            ):
                result = scope_guard.check_scope(
                    forge_dir, project_dir=d
                )
            self.assertFalse(result.match)
            self.assertEqual(result.reason, "git-error")
            self.assertIsNone(result.expected)
            self.assertEqual(result.actual, str(forge_dir.resolve()))

    def test_different_repo_mismatch(self):
        # project_dir resolves to repo A's toplevel, but the .forge/ in
        # question belongs to a DIFFERENT repo B -- the wrong-workstation
        # bug this task exists to catch.
        with tempfile.TemporaryDirectory() as project_repo, \
                tempfile.TemporaryDirectory() as other_repo:
            _init_repo(project_repo)
            _init_repo(other_repo)
            forge_dir = pathlib.Path(other_repo) / ".forge"
            forge_dir.mkdir()
            result = scope_guard.check_scope(
                forge_dir, project_dir=project_repo
            )
            self.assertFalse(result.match)
            self.assertEqual(result.reason, "mismatch")
            self.assertEqual(
                result.expected,
                str((pathlib.Path(project_repo) / ".forge").resolve()),
            )
            self.assertEqual(result.actual, str(forge_dir.resolve()))

    def test_env_and_cwd_flow_through_when_project_dir_omitted(self):
        with tempfile.TemporaryDirectory() as project_repo, \
                tempfile.TemporaryDirectory() as other_repo:
            _init_repo(project_repo)
            _init_repo(other_repo)
            forge_dir = pathlib.Path(other_repo) / ".forge"
            forge_dir.mkdir()
            result = scope_guard.check_scope(
                forge_dir,
                env={"CLAUDE_PROJECT_DIR": project_repo},
                cwd="/unused",
            )
            self.assertFalse(result.match)
            self.assertEqual(result.reason, "mismatch")


class MainCliTests(unittest.TestCase):
    def test_main_prints_match_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            forge_dir = pathlib.Path(d) / ".forge"
            forge_dir.mkdir()
            code = scope_guard.main([str(forge_dir), "--project-dir", d])
            self.assertEqual(code, 0)

    def test_main_prints_mismatch_and_exits_one(self):
        with tempfile.TemporaryDirectory() as project_repo, \
                tempfile.TemporaryDirectory() as other_repo:
            _init_repo(project_repo)
            _init_repo(other_repo)
            forge_dir = pathlib.Path(other_repo) / ".forge"
            forge_dir.mkdir()
            code = scope_guard.main(
                [str(forge_dir), "--project-dir", project_repo]
            )
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
