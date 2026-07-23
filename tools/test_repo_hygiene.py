"""Smoke-pin tests for fg-a10912: .gitattributes line-ending normalization
and CONTRIBUTING.md contributor setup doc.

Per the task's EARS clause 4, this is repo hygiene, not orchestration
doctrine — no conventions.md pin class needed, just a cheap string-check
smoke pin that the two files exist and carry their load-bearing markers.
"""
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestGitattributesHygiene(unittest.TestCase):
    """Verify .gitattributes exists and carries its load-bearing rules."""

    def test_gitattributes_exists(self):
        self.assertTrue(
            (REPO_ROOT / ".gitattributes").exists(), ".gitattributes missing"
        )

    def test_gitattributes_has_text_auto_baseline(self):
        content = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("* text=auto", content)

    def test_gitattributes_bat_is_crlf(self):
        content = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.bat text eol=crlf", content)

    def test_gitattributes_ans_is_binary(self):
        content = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.ans -text", content)

    def test_gitattributes_sh_still_lf(self):
        """Pre-existing rule (*.sh text eol=lf) must survive the rewrite."""
        content = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.sh", content)
        self.assertIn("eol=lf", content)


class TestContributingHygiene(unittest.TestCase):
    """Verify CONTRIBUTING.md exists and covers the trust boundary."""

    def test_contributing_exists(self):
        self.assertTrue(
            (REPO_ROOT / "CONTRIBUTING.md").exists(), "CONTRIBUTING.md missing"
        )

    def test_contributing_mentions_trust_boundary(self):
        content = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("trust boundary", content.lower())
        self.assertIn("never auto-execute", content.lower())


if __name__ == "__main__":
    unittest.main()
