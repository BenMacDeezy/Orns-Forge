"""Pins for the human-ratified marginal-gain stop rules (2026-07-22).

The operator extended the consensus-loop "lean: escalate-only" ruling to
all verification: repetition is capped, the first adversarial look and
every ratified floor stay untouched. These pins keep the four rules and
their floor-preserving preamble from drifting.
"""
import unittest

from ._common import REPO_ROOT, _cached_read_text


class TestMarginalGainStopRulesPins(unittest.TestCase):
    def _verification(self):
        return _cached_read_text(
            REPO_ROOT / "docs" / "conventions" / "verification.md")

    def test_section_and_index(self):
        self.assertIn(
            "## Marginal-gain stop rules — 2026-07-22 (human-ratified)",
            self._verification())
        index = _cached_read_text(REPO_ROOT / "docs" / "conventions.md")
        self.assertIn(
            "- Marginal-gain stop rules — 2026-07-22 (human-ratified)",
            index)
        self.assertIn(
            "- `Marginal-gain stop rules — 2026-07-22 (human-ratified)` -> "
            "`docs/conventions/verification.md`", index)

    def test_floors_untouched_preamble(self):
        content = self._verification()
        self.assertIn("never touch the first look, the grouped-verification "
                      "floor, the named\nsecurity triggers, or the human "
                      "spec gate", content)

    def test_lifetime_judgment_cap(self):
        content = self._verification()
        self.assertIn("**Lifetime judgment cap.**", content)
        self.assertIn("THE SYSTEM SHALL NOT dispatch a third judgment pass",
                      content)
        self.assertIn("escalates to the human as a plain-English\n  blocker, "
                      "never another model round", content)

    def test_never_reverify_judges_own_fix(self):
        content = self._verification()
        self.assertIn("**Never re-verify a judge's own fix.**", content)
        self.assertIn("without re-spawning the judge\n  to confirm its own "
                      "prescription", content)

    def test_cosmetic_never_costs_a_dispatch(self):
        content = self._verification()
        self.assertIn("**Cosmetic findings never cost a dispatch.**", content)
        self.assertIn("it never re-queues a\n  judgment pass", content)

    def test_no_auto_chained_sweeps(self):
        content = self._verification()
        self.assertIn("**No auto-chained sweeps.**", content)
        self.assertIn("A shipped wave never\n  automatically triggers a "
                      "follow-up audit of itself", content)
        self.assertIn("the human pulls the trigger", content)


if __name__ == "__main__":
    unittest.main()
