"""Doc-pin regression tests for the fullstack-pair skill build (batched sibling
tasks auth-session-patterns + forms-and-validation, wt-skillsb, 2026-07-21):
- both SKILL.md files exist with a scope-defining description one-liner
- auth-session-patterns names the forge-security auth/token/secret dispatch
  trigger and carries the independent-vetting caveat for any cited library
- forms-and-validation cross-references accessibility-wcag-aria for
  error-state accessibility
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestFullstackPairSkillsExist(unittest.TestCase):
    """Both SKILL.md files exist and register a scope-defining one-liner."""

    def test_auth_session_patterns_skill_file_exists(self):
        path = REPO_ROOT / "skills" / "auth-session-patterns" / "SKILL.md"
        self.assertTrue(path.exists(), f"missing {path}")

    def test_forms_and_validation_skill_file_exists(self):
        path = REPO_ROOT / "skills" / "forms-and-validation" / "SKILL.md"
        self.assertTrue(path.exists(), f"missing {path}")

    def test_auth_session_patterns_scope_one_liner(self):
        content = _cached_read_text(
            REPO_ROOT / "skills" / "auth-session-patterns" / "SKILL.md"
        )
        self.assertIn("name: auth-session-patterns", content)
        self.assertIn("OAuth/OIDC flows", content)
        self.assertIn("session-vs-token storage per platform", content)
        self.assertIn("refresh-token rotation", content)
        self.assertIn("CSRF", content)
        self.assertIn("RBAC", content)

    def test_forms_and_validation_scope_one_liner(self):
        content = _cached_read_text(
            REPO_ROOT / "skills" / "forms-and-validation" / "SKILL.md"
        )
        self.assertIn("name: forms-and-validation", content)
        self.assertIn("React Hook Form + Zod/Valibot", content)
        self.assertIn(
            "cross-platform (web + React Native) validation UX", content
        )
        self.assertIn("accessible error states", content)


class TestAuthSessionPatternsSecurityTrigger(unittest.TestCase):
    """auth-session-patterns must name the forge-security dispatch trigger
    and carry an independent-vetting caveat for every cited library — per
    the task's acceptance criteria, never vendor-claim-only."""

    def test_names_forge_security_dispatch_trigger(self):
        content = _cached_read_text(
            REPO_ROOT / "skills" / "auth-session-patterns" / "SKILL.md"
        )
        self.assertIn(
            "**`auth` / `token` / `secret` is a named `forge-security` "
            "dispatch trigger**",
            content,
        )
        self.assertIn("Verification economics", content)

    def test_independent_vetting_caveat_present(self):
        content = _cached_read_text(
            REPO_ROOT / "skills" / "auth-session-patterns" / "SKILL.md"
        )
        self.assertIn(
            "starting point, not an endorsement taken on\n"
            "the vendor's word.",
            content,
        )
        self.assertIn("independently verify", content)

    def test_cross_references_forge_secure_diff_review(self):
        content = _cached_read_text(
            REPO_ROOT / "skills" / "auth-session-patterns" / "SKILL.md"
        )
        self.assertIn("forge-secure-diff-review", content)


class TestFormsAndValidationAccessibilityCrossReference(unittest.TestCase):
    """forms-and-validation must tie error-state accessibility explicitly to
    accessibility-wcag-aria, per the task's acceptance criteria."""

    def test_cross_references_accessibility_wcag_aria(self):
        content = _cached_read_text(
            REPO_ROOT / "skills" / "forms-and-validation" / "SKILL.md"
        )
        self.assertIn("accessibility-wcag-aria", content)
        self.assertIn("aria-invalid", content)
        self.assertIn("aria-describedby", content)
        self.assertIn("do not rely on color alone", content)

    def test_accessibility_wcag_aria_skill_exists(self):
        # The cross-referenced skill must actually exist in this repo.
        path = REPO_ROOT / "skills" / "accessibility-wcag-aria" / "SKILL.md"
        self.assertTrue(path.exists(), f"missing {path}")


class TestFullstackPairSkillsRegisteredInIndexes(unittest.TestCase):
    """Both skills are registered wherever sibling craft skills are
    indexed: README skill count, and the map's architecture + skill-library
    subsystem doc."""

    def test_readme_skill_count_counts_this_pair(self):
        # Concurrent sibling batches merged in the same wave (final count
        # 57); disk/README/map consistency is owned by test_fg_a10101's
        # test_skill_count_consistent, so this pin only asserts the README
        # states SOME count >= 50 (48 + this pair).
        readme = _cached_read_text(REPO_ROOT / "README.md")
        import re
        m = re.search(r"\*\*(\d+) skills", readme)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)), 50)

    def test_skill_libraries_subsystem_lists_both_skills(self):
        content = _cached_read_text(
            REPO_ROOT / ".forge" / "map" / "subsystems" / "skill-libraries.md"
        )
        self.assertIn("auth-session-patterns", content)
        self.assertIn("forms-and-validation", content)

    def test_actual_skill_dirs_include_both(self):
        self.assertTrue(
            (REPO_ROOT / "skills" / "auth-session-patterns" / "SKILL.md").exists()
        )
        self.assertTrue(
            (REPO_ROOT / "skills" / "forms-and-validation" / "SKILL.md").exists()
        )



class TestFormsResolverClaimCorrected(unittest.TestCase):
    """2026-07-21 grouped-verify P1 fix: the original claim routed Valibot
    through zodResolver's 'Standard Schema path', which does not exist
    (zodResolver type-guards on Zod only). Pin the corrected guidance so
    the wrong claim can never return."""

    def test_correct_resolver_per_library(self):
        content = _cached_read_text(
            REPO_ROOT / "skills" / "forms-and-validation" / "SKILL.md")
        self.assertIn("valibotResolver", content)
        self.assertIn("standardSchemaResolver", content)
        self.assertIn("only accepts Zod schemas", content)
        self.assertNotIn(
            "wired through `zodResolver`'s Standard Schema path", content)


if __name__ == "__main__":
    unittest.main()
