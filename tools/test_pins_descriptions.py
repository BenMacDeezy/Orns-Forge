"""Doc-pin regression tests for fg-9e0102: trigger-preserving description
tightening across five padded skill frontmatter descriptions (per
docs/audits token finder F2, top-5 item 5).

Each of the five descriptions below had a "Use when..." sentence that
re-paraphrased its own quoted "Triggers —" list (or, for the two skills with
no separate Triggers list, re-paraphrased its own capability list). The
padding was cut; every quoted trigger phrase and every activation-critical
scope/boundary clause was kept verbatim. These tests pin the retained
phrases directly against the frontmatter description line (not the body),
so a future edit that quietly drops a trigger while "cleaning up" the
description fails loudly here instead of silently degrading activation.
"""
import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read_description(skill_name):
    """Extract the frontmatter `description:` value for a skill.

    Confirms the frontmatter block itself parses (starts with `---`, ends
    with `---`) before pulling the description line out of it — a stronger
    check than a bare substring search, since it would fail if the
    frontmatter delimiters themselves were ever mangled.
    """
    skill_path = REPO_ROOT / "skills" / skill_name / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8")

    frontmatter_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    assert frontmatter_match is not None, f"{skill_path} frontmatter block not found/parseable"
    frontmatter = frontmatter_match.group(1)

    desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    assert desc_match is not None, f"{skill_path} frontmatter has no description: line"
    return desc_match.group(1).strip()


class TestDescriptionTighteningPins(unittest.TestCase):
    """One test per tightened skill: frontmatter parses, description is
    nonempty, and every retained trigger phrase / scope clause survives."""

    def test_differential_debugging_and_bisection_description(self):
        desc = _read_description("differential-debugging-and-bisection")
        self.assertTrue(desc, "description is empty")
        for phrase in (
            "this used to work",
            "worked yesterday",
            "regression",
            "flaky test",
            "heisenbug",
            "only fails in CI",
            "only fails on prod",
            "can't reproduce locally",
            "shrink the repro",
            "minimal repro",
            "race condition",
        ):
            self.assertIn(phrase, desc, f"trigger phrase {phrase!r} missing")
        # Scope words from the capability half of the description, not just
        # the quoted Triggers list.
        self.assertIn("git bisect", desc)
        self.assertIn("delta debugging", desc)
        self.assertIn("concurrency stress", desc)

    def test_forge_secure_diff_review_description(self):
        desc = _read_description("forge-secure-diff-review")
        self.assertTrue(desc, "description is empty")
        # "Diff-scoped" is the arbitration anchor (see the body's "Scope
        # arbitration" paragraph, pinned separately in test_doc_pins.py) —
        # it must lead the description unchanged.
        self.assertTrue(desc.startswith("Diff-scoped"))
        self.assertIn("OWASP", desc)
        self.assertIn("CWE Top 25", desc)
        self.assertIn("STRIDE", desc)
        self.assertIn("money/financial-logic checklist", desc)
        self.assertIn("when forge-security starts a review", desc)
        self.assertIn(
            "authentication, input handling, secrets/credentials, or money/payment flows",
            desc,
        )

    def test_lottie_rive_vector_animation_description(self):
        desc = _read_description("lottie-rive-vector-animation")
        self.assertTrue(desc, "description is empty")
        for phrase in (
            "Lottie animation",
            "dotLottie",
            ".riv file",
            "Rive state machine",
            "designer sent an animation",
            "animated illustration",
            "onboarding animation",
        ):
            self.assertIn(phrase, desc, f"trigger phrase {phrase!r} missing")
        # Quoted request phrasings embedded in the (former) Use-when
        # sentence — not under the Triggers label, but still quoted, so
        # still load-bearing.
        self.assertIn('"make this Lottie/Rive file play"', desc)
        self.assertIn('"add an interactive animated character/icon"', desc)
        # Scope words unique to the Use-when sentence, not paraphrased
        # anywhere in the Triggers list — must survive the cut.
        self.assertIn("micro-interaction animations", desc)
        self.assertIn("animated icons", desc)

    def test_coverage_gap_analysis_description(self):
        desc = _read_description("coverage-gap-analysis")
        self.assertTrue(desc, "description is empty")
        for phrase in (
            "increase test coverage",
            "what's not tested",
            "coverage gaps",
            "untested branches",
            "legacy code has no tests",
            "characterization tests",
            "is this well tested",
        ):
            self.assertIn(phrase, desc, f"trigger phrase {phrase!r} missing")
        # Quoted phrases inside the Use-when sentence itself.
        self.assertIn('"improve coverage"', desc)
        self.assertIn('"find untested edge cases"', desc)
        # The weak-assertions scope clause is not paraphrased by any
        # Triggers entry — it must survive the cut.
        self.assertIn(
            "coverage report shows lines executed but the assertions look weak",
            desc,
        )

    def test_source_vetting_and_citation_discipline_description(self):
        desc = _read_description("source-vetting-and-citation-discipline")
        self.assertTrue(desc, "description is empty")
        # This skill has no quoted Triggers list at all — the pin targets
        # the capability terms and the unique Use-when scope clauses instead.
        self.assertIn("primary-vs-secondary source hierarchy", desc)
        self.assertIn("Confirmed/Inferred/Assumed", desc)
        self.assertIn("claim-level", desc)
        self.assertIn("producing a research brief", desc)
        self.assertIn(
            "before citing a source in an implementation guidance document",
            desc,
        )
        self.assertIn("when forge-researcher is about to finalize a brief", desc)


if __name__ == "__main__":
    unittest.main()
