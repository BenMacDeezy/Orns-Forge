"""Doc-pins for no-worktree degraded mode (2026-07-24, owner-directed).

When git worktrees are unavailable (OneDrive/Windows: `git worktree add`
returns 0 but materializes an empty tree), Forge must NOT exclude codex
mutating workers -- they run in-place exactly as a sequential Claude
worker does. These pins guard the kernel wiring (SYNC probe, GATE
fail-closed), the canonical reference, and the builder-agnostic verify
routing that makes codex-build + Claude-visual-verify a first-class combo.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
    conventions_corpus,
)

KERNEL = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
REF = REPO_ROOT / "skills" / "kernel" / "references" / "degraded-worktree-mode.md"


def _norm(text):
    return " ".join(text.split())


class TestDegradedWorktreeReference(unittest.TestCase):
    def test_reference_file_exists(self):
        self.assertTrue(REF.is_file(),
                        "degraded-worktree-mode.md must exist")

    def test_reference_covers_the_probe(self):
        v = _norm(_cached_read_text(REF))
        self.assertIn("Worktree-availability probe (SYNC)", v)
        # exit-0-but-empty is the OneDrive failure mode the probe must catch
        self.assertIn("can return\nexit 0 yet materialize an empty",
                      _cached_read_text(REF))
        self.assertIn("git worktree add", v)

    def test_reference_states_both_worker_kinds_run_in_place(self):
        v = _norm(_cached_read_text(REF))
        self.assertIn("Mutating workers run in-place — Claude AND codex", v)
        self.assertIn("workspace-write` sandbox is a codex feature", v)
        self.assertIn("it is NOT a git worktree", v)

    def test_reference_keeps_forge_dispatch_exclusion_load_bearing(self):
        v = _norm(_cached_read_text(REF))
        self.assertIn(".forge-dispatch/", v)
        self.assertIn("INTEGRATE-time exclusion is UNCHANGED and now load-bearing",
                      v)

    def test_reference_states_in_place_bounce_revert(self):
        v = _norm(_cached_read_text(REF))
        self.assertIn("Bounce reverts in-place", v)

    def test_reference_verify_is_builder_agnostic(self):
        v = _norm(_cached_read_text(REF))
        self.assertIn("Verify routing is builder-agnostic", v)
        self.assertIn("codex-build + Claude-visual-verify", v)

    def test_hard_rule_4_holds_in_place(self):
        v = _norm(_cached_read_text(REF))
        self.assertIn("Hard Rule 4 holds\nunchanged".replace("\n", " "), v)


class TestDegradedWorktreeKernelWiring(unittest.TestCase):
    def test_sync_has_the_probe(self):
        k = _norm(_cached_read_text(KERNEL))
        self.assertIn("Worktree probe + stale sweep", k)
        self.assertIn("references/degraded-worktree-mode.md", k)
        self.assertIn("runs DEGRADED", k)

    def test_gate_fails_closed_in_degraded_mode(self):
        # DEGRADED must make every parallel batch ineligible -- the whole
        # point is that no two mutating workers share one tree.
        k = _norm(_cached_read_text(KERNEL))
        self.assertIn("DEGRADED = sequential-only, no batch", k)

    def test_provider_stub_names_in_place(self):
        k = _norm(_cached_read_text(KERNEL))
        self.assertIn("worktree-OR-in-place mechanics", k)


class TestDegradedWorktreeConventions(unittest.TestCase):
    def test_section_exists_and_is_dated(self):
        self.assertIn(
            "## No-worktree degraded mode — 2026-07-24 (owner-directed)",
            conventions_corpus.corpus_text(),
        )

    def test_section_names_the_interpretation_bug(self):
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("interpretation bug", c)
        self.assertIn("codex mirrors that: in-place, no worktree", c)

    def test_section_states_degraded_overrides_parallel_first(self):
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("the ONE condition that overrides\nparallel-first"
                      .replace("\n", " "), c)


if __name__ == "__main__":
    unittest.main()
