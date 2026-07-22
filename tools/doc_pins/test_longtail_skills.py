"""Doc-pin regression tests for the longtail craft-skill batch (2026-07-21):
`i18n-and-localization`, `payment-integration-discipline`,
`email-and-templating`, `seo-fundamentals`. Sharded into its own module
(fg-a11040 convention: one module per task-id/task-batch prefix, so
concurrent tasks appending pins land in separate files instead of
conflicting at a shared tail) rather than appended to an existing shard.

Pins, per the spawn contract for this batch:
- each of the four SKILL.md files exists with a scope one-liner near the top
- payment-integration-discipline's forge-security money/payment trigger
  sentence and its PCI never-raw-card sentence
- seo-fundamentals' explicit SEO/Core-Web-Vitals duty-split sentence
"""
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import REPO_ROOT, _read_path  # noqa: E402

SKILLS_DIR = REPO_ROOT / "skills"


def _skill_text(skill_id):
    return _read_path(SKILLS_DIR / skill_id / "SKILL.md")


def _normalized(text):
    return re.sub(r"\s+", " ", text)


class TestLongtailSkillsExist(unittest.TestCase):
    """Each of the four skills exists as skills/<task-id>/SKILL.md with a
    frontmatter name matching its directory and a scope one-liner near the
    top of the body (mirrors the house craft-skill shape, e.g.
    skills/observability-logging-metrics-tracing/SKILL.md)."""

    SKILL_IDS = (
        "i18n-and-localization",
        "payment-integration-discipline",
        "email-and-templating",
        "seo-fundamentals",
    )

    def test_all_four_skill_files_exist(self):
        for skill_id in self.SKILL_IDS:
            path = SKILLS_DIR / skill_id / "SKILL.md"
            self.assertTrue(
                path.is_file(),
                f"expected {path} to exist for the longtail skills batch",
            )

    def test_all_four_have_matching_frontmatter_name(self):
        for skill_id in self.SKILL_IDS:
            text = _skill_text(skill_id)
            self.assertIn(f"name: {skill_id}", text)

    def test_i18n_scope_one_liner(self):
        text = _normalized(_skill_text("i18n-and-localization"))
        self.assertIn(
            "Scope: i18n-and-localization — message extraction, ICU "
            "pluralization, RTL layout, and date/number formatting for "
            "user-facing strings.",
            text,
        )

    def test_payment_scope_one_liner(self):
        text = _normalized(_skill_text("payment-integration-discipline"))
        self.assertIn(
            "Scope: payment-integration-discipline — Stripe/RevenueCat "
            "integration shape, the mobile IAP regulatory surface, "
            "PCI-scope avoidance, and webhook idempotency.",
            text,
        )

    def test_email_scope_one_liner(self):
        text = _normalized(_skill_text("email-and-templating"))
        self.assertIn(
            "Scope: email-and-templating — transactional email provider "
            "selection, react-email/MJML templating, and SPF/DKIM/DMARC "
            "deliverability basics.",
            text,
        )

    def test_seo_scope_one_liner(self):
        text = _normalized(_skill_text("seo-fundamentals"))
        self.assertIn(
            "Scope: seo-fundamentals — meta/OG tags, structured data, and "
            "sitemap/robots for discoverability and correct crawling/"
            "sharing.",
            text,
        )


class TestPaymentSecurityTriggerAndPciPins(unittest.TestCase):
    """payment-integration-discipline must name the forge-security
    money/payment trigger explicitly (this is a NAMED trigger in the
    verification-economics conventions, per agents/forge-security.md) and
    must state the PCI-scope never-raw-card-data rule in wording aligned
    with Forge's standing credential prohibition."""

    def _text(self):
        return _normalized(_skill_text("payment-integration-discipline"))

    def test_states_forge_security_trigger_fires(self):
        text = self._text()
        self.assertIn(
            "Any task that touches payments fires the forge-security "
            "review trigger.", text,
        )
        self.assertIn(
            "Money/payment is a NAMED trigger in the verification-"
            "economics conventions", text,
        )

    def test_states_never_touch_raw_card_data(self):
        text = self._text()
        self.assertIn(
            "This code NEVER touches, stores, or logs raw card data",
            text,
        )
        self.assertIn(
            "the primary account number (PAN), CVV, or full magnetic-"
            "stripe/chip track data.", text,
        )

    def test_aligns_pci_wording_with_standing_credential_prohibition(self):
        text = self._text()
        self.assertIn(
            "This mirrors Forge's standing prohibition on ever handling "
            "credentials directly", text,
        )

    def test_pairs_with_feature_legal_risk_checklist(self):
        text = self._text()
        self.assertIn(
            "This skill pairs with `skills/feature-legal-risk-checklist`",
            text,
        )

    def test_forge_security_agent_actually_names_money_payment_trigger(self):
        """Cross-check the cited trigger actually exists in
        agents/forge-security.md, so this pin fails if that agent's
        trigger list ever drops the money/payment case out from under the
        citation."""
        security_agent = _read_path(REPO_ROOT / "agents" / "forge-security.md")
        self.assertIn("money/payment", security_agent)
        self.assertIn(
            "Verification economics — 2026-07-18", security_agent,
        )


class TestSeoCoreWebVitalsDutySplitPin(unittest.TestCase):
    """seo-fundamentals must state the explicit duty-split sentence with
    core-web-vitals-for-ui (perf half stays there, per the spawn
    contract)."""

    def test_states_duty_split_sentence(self):
        text = _normalized(_skill_text("seo-fundamentals"))
        self.assertIn(
            "This skill owns discoverability — meta/OG tags, structured "
            "data, and sitemap/robots; `core-web-vitals-for-ui` owns the "
            "performance half (LCP, INP, CLS)", text,
        )

    def test_core_web_vitals_skill_still_owns_the_perf_metrics(self):
        """Cross-check core-web-vitals-for-ui still actually documents
        LCP/INP/CLS, so the duty-split claim doesn't silently go stale if
        that skill's content changes."""
        cwv_text = _skill_text("core-web-vitals-for-ui")
        for metric in ("LCP", "INP", "CLS"):
            self.assertIn(metric, cwv_text)


class TestSkillsRegisteredOnRosterSurface(unittest.TestCase):
    """The four skills must be registered where sibling craft skills are
    indexed: forge-worker's Attached skills section (the roster surface)
    and the skill-libraries map doc."""

    SKILL_IDS = (
        "i18n-and-localization",
        "payment-integration-discipline",
        "email-and-templating",
        "seo-fundamentals",
    )

    def test_forge_worker_attaches_all_four(self):
        worker = _read_path(REPO_ROOT / "agents" / "forge-worker.md")
        for skill_id in self.SKILL_IDS:
            self.assertIn(f"- {skill_id} —", worker)

    def test_skill_libraries_map_mentions_all_four(self):
        map_doc = _read_path(
            REPO_ROOT / ".forge" / "map" / "subsystems" / "skill-libraries.md"
        )
        for skill_id in self.SKILL_IDS:
            self.assertIn(f"`{skill_id}`", map_doc)
