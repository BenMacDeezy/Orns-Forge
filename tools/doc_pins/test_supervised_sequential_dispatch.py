"""Doc-pins for supervised sequential dispatch (2026-07-24, owner-directed).

A live session foreground-blocked on a synchronous sequential worker that
ran 30+ min / 80+ tool calls with no watchdog flag -- because the watchdog
only runs on an idle-wait fallback wakeup, which a blocked kernel never
reaches. These pins guard the fix: sequential workers dispatch in the
background and are awaited (so the watchdog supervises), plus the new
runaway-commands ceiling.
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


def _norm(text):
    return " ".join(text.split())


class TestSupervisedSequentialConventions(unittest.TestCase):
    def test_section_exists_and_is_dated(self):
        self.assertIn(
            "## Supervised sequential dispatch — 2026-07-24 (owner-directed)",
            conventions_corpus.corpus_text(),
        )

    def test_section_distinguishes_sequential_from_synchronous(self):
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("Sequential ≠ synchronous", c)

    def test_section_requires_background_await_never_foreground_block(self):
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("dispatched in the BACKGROUND and\nawaited"
                      .replace("\n", " "), c)
        self.assertIn("NEVER foreground-blocked", c)

    def test_section_explains_why_the_watchdog_never_ran(self):
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("a foreground-blocked kernel never idle-\nwaits"
                      .replace("\n", " "), c)
        self.assertIn("the watchdog\nNEVER RUNS".replace("\n", " "), c)

    def test_section_defines_runaway_commands_threshold(self):
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("`runaway-commands` (default 50)", c)
        self.assertIn("watchdog-runaway-commands", c)


class TestSupervisedSequentialKernelWiring(unittest.TestCase):
    def test_kernel_dispatches_sequential_in_background_awaited(self):
        k = _norm(_cached_read_text(KERNEL))
        self.assertIn("A sequential worker runs in the BACKGROUND, awaited "
                      "(never foreground-blocked)", k)
        self.assertIn("Supervised sequential dispatch — 2026-07-24", k)


class TestRunawayCommandsWatchdog(unittest.TestCase):
    def _watchdog(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import watchdog  # noqa: E402
        return watchdog

    def test_default_is_fifty(self):
        self.assertEqual(self._watchdog().DEFAULTS["runaway-commands"], 50)

    def test_check_runaway_accepts_command_budget(self):
        # Signature guard: the ceiling is optional (back-compat) but present.
        import inspect
        params = inspect.signature(self._watchdog().check_runaway).parameters
        self.assertIn("command_budget", params)


if __name__ == "__main__":
    unittest.main()
