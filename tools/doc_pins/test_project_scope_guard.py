"""Doc-pin regression tests for `project-scope-guard` (2026-07-20): the
kernel/queue guard that the `.forge/` being operated on must belong to
THIS project (project = CLAUDE_PROJECT_DIR or cwd; toplevel via `git
rev-parse --show-toplevel`). Follows the sharded, one-module-per-task
convention `tools/doc_pins/test_fg_*.py` already establishes so concurrent
tasks appending pins land in separate files instead of conflicting at a
shared tail.

Pins the stop-and-ask rule (kernel SYNC and queue-skill writes), direct
canonical-path equality, the git-error stop rule, never-auto-pick,
zero-friction-on-match, and the advisory-only status.py variant.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
)


class TestProjectScopeGuardConventionsPins(unittest.TestCase):
    """Pins the dated conventions section (docs/conventions.md TOC +
    shards manifest + the section body in docs/conventions/
    trust-and-security.md, read transparently through the fg-b0401 corpus
    loader via _read_path)."""

    def _corpus(self):
        return _read_path("docs/conventions.md")

    def test_toc_lists_the_new_section(self):
        c = self._corpus()
        self.assertIn(
            "- Project scope guard — 2026-07-20 (project-scope-guard)", c
        )

    def test_manifest_maps_to_trust_and_security_shard(self):
        c = self._corpus()
        self.assertIn(
            "- `Project scope guard — 2026-07-20 (project-scope-guard)` "
            "-> `docs/conventions/trust-and-security.md`",
            c,
        )

    def test_section_heading_is_dated_and_scoped(self):
        c = self._corpus()
        self.assertIn(
            "## Project scope guard — 2026-07-20 (project-scope-guard)", c
        )

    def test_stop_and_ask_rule(self):
        c = self._corpus()
        self.assertIn(
            "STOP on any scope mismatch", c
        )
        self.assertIn(
            "state BOTH paths plainly — the expected `.forge/` (project's "
            "own toplevel)\nand the actual `.forge/` about to be operated "
            "on",
            c,
        )
        self.assertIn("ask the human which\nproject they meant", c)

    def test_never_auto_pick_rule(self):
        c = self._corpus()
        self.assertIn(
            'Never auto-pick either side: not "prefer\n'
            '`CLAUDE_PROJECT_DIR`", not "prefer cwd", not "the one with '
            'more recent\nactivity"',
            c,
        )

    def test_zero_friction_on_match(self):
        c = self._corpus()
        self.assertIn("**Zero friction on match.**", c)
        self.assertIn(
            "`project_dir` may equal the project toplevel or\n"
            "be nested anywhere within it",
            c,
        )
        self.assertIn(
            "Project-directory nesting does not permit a nested `.forge/`",
            c,
        )

    def test_canonical_path_equality_not_owning_toplevels(self):
        c = self._corpus()
        self.assertIn(
            "MUST be canonical-path-equal to `<that toplevel>/.forge`", c
        )
        self.assertIn(
            "Do\nNOT compare the owning git toplevels", c
        )
        self.assertIn(
            "a nested same-repo `.forge/` and a\n"
            "nonexistent `.forge/` aimed at another repo are both mismatches",
            c,
        )

    def test_git_error_stops_writes_and_warns_on_status(self):
        c = self._corpus()
        self.assertIn(
            "resolution failure is `git-error`: kernel/queue MUST stop "
            "and ask, while\nstatus emits an advisory warning",
            c,
        )
        self.assertIn(
            "On `git-error`, state that the project toplevel could not be "
            "resolved",
            c,
        )

    def test_advisory_only_status_variant(self):
        c = self._corpus()
        self.assertIn("**Advisory-only on read-only surfaces.**", c)
        self.assertIn(
            "`/forge:status` never blocks on\nthis guard", c
        )
        self.assertIn("`SCOPE WARNING: ...`", c)

    def test_accelerator_cited(self):
        c = self._corpus()
        self.assertIn("tools/scope_guard.py", c)
        self.assertIn("prints `match`/`no-git` and exits 0", c)
        self.assertIn("`git-error: ...` and exits 1", c)


class TestProjectScopeGuardReferenceFile(unittest.TestCase):
    """Pins the NORMATIVE reference file both SYNC and the queue-skill
    write-path check cite, and that the citations actually point at it."""

    REFERENCE_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "scope-guard.md"
    )
    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    QUEUE_PATH = REPO_ROOT / "skills" / "queue" / "SKILL.md"
    STATUS_PATH = REPO_ROOT / "tools" / "status.py"
    CHAR_CEILING = 31617

    def _reference(self):
        return _cached_read_text(self.REFERENCE_PATH)

    def _kernel(self):
        return _cached_read_text(self.KERNEL_PATH)

    def _queue(self):
        return _cached_read_text(self.QUEUE_PATH)

    def test_reference_file_exists_and_is_normative(self):
        content = self._reference()
        self.assertIn("NORMATIVE", content)
        self.assertIn("# Project scope guard (reference)", content)

    def test_reference_requires_direct_canonical_path_equality(self):
        content = self._reference()
        self.assertIn(
            "Canonicalize that expected path and the actual\n"
            "   `.forge/` path directly, even when the actual path does not exist",
            content,
        )
        self.assertIn(
            "Do NOT compare the git toplevels that own the two paths", content
        )

    def test_reference_requires_git_error_stop_and_status_warning(self):
        content = self._reference()
        self.assertIn(
            "kernel SYNC and queue writes MUST stop and ask; status MUST warn",
            content,
        )
        self.assertIn(
            "## On mismatch or git-error — kernel SYNC and queue-skill writes",
            content,
        )

    def test_kernel_cites_the_reference_before_repo_root_use(self):
        content = self._kernel()
        self.assertIn(
            "**Project scope guard.** Before this resolution informs any "
            "read or\n  write, confirm `<root>/.forge` belongs to THIS "
            "project (`CLAUDE_PROJECT_DIR`\n  or cwd) — "
            "`skills/kernel/references/scope-guard.md` (NORMATIVE).",
            content,
        )
        self.assertIn(
            "On a\n  mismatch: STOP, state both `.forge/` paths, ask the "
            "human — never\n  auto-pick. On a project-toplevel `git-error`: "
            "STOP and ask the human to\n  resolve or confirm the project.",
            content,
        )
        repo_root_idx = content.index("**Repo root first**")
        guard_idx = content.index("**Project scope guard.**")
        pull_idx = content.index("### 2. PULL")
        self.assertLess(repo_root_idx, guard_idx)
        self.assertLess(guard_idx, pull_idx)

    def test_kernel_skill_within_char_ceiling(self):
        content = _cached_read_text(self.KERNEL_PATH)
        self.assertLessEqual(len(content), self.CHAR_CEILING)

    def test_queue_skill_cites_the_reference_before_writes(self):
        content = self._queue()
        self.assertIn(
            "**Project scope guard.** Before this resolution informs any "
            "add/close/promote write, confirm `<root>/.forge` belongs to "
            "THIS project — same check, same procedure as `forge:kernel`'s "
            "SYNC step: `skills/kernel/references/scope-guard.md` "
            "(NORMATIVE).",
            content,
        )
        self.assertIn(
            "On a mismatch: STOP, state both `.forge/` paths, ask the "
            "human — never auto-pick. On a project-toplevel `git-error`: "
            "STOP and ask the human to resolve or confirm the project.",
            content,
        )
        auto_init_idx = content.index("## Auto-init")
        guard_idx = content.index("**Project scope guard.**")
        create_idx = content.index("## Create / Edit / Cancel a task")
        self.assertLess(auto_init_idx, guard_idx)
        self.assertLess(guard_idx, create_idx)

    def test_status_py_imports_the_accelerator_module(self):
        content = _cached_read_text(self.STATUS_PATH)
        self.assertIn("import scope_guard", content)
        self.assertIn("def scope_warning(", content)
        self.assertIn("SCOPE WARNING", content)


if __name__ == "__main__":
    unittest.main()
