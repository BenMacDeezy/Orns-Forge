"""Pins for the 2026-07-22 provider-security documentation audit fixes."""

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(relative_path):
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _flat(relative_path):
    return " ".join(_read(relative_path).split())


class TestAuditFixProviderDocs(unittest.TestCase):
    """Pins the gate, budget, reachability, and pilot-clearance amendments."""

    PROVIDER_JUDGES = "skills/kernel/references/provider-judges.md"
    OPERATOR_PROFILES = "skills/kernel/references/operator-profiles.md"
    SETTINGS = "commands/settings.md"
    CONFIGURATION = "docs/features/configuration.md"

    def test_worker_dispatch_requires_every_gate_layer(self):
        content = _flat(self.PROVIDER_JUDGES)
        self.assertIn(
            "### 7.1a. Worker dispatches pass the SAME gate layers — "
            "2026-07-22",
            content,
        )
        self.assertIn(
            "A Phase-2 worker dispatch requires ALL of: the global "
            "`providers` Feature on; that provider's own forge.md `## "
            "Providers` toggle on (missing = OFF); the provider's TOFU "
            "trust marker present; the budget check per section 7.6 as "
            "amended; PLUS the pilot gate",
            content,
        )
        self.assertIn(
            "A toggled-off provider never dispatches as a worker regardless "
            "of profile role resolution.",
            content,
        )
        self.assertIn(
            "use section 1a's `provider-gate-blocked:` labeled-line format "
            "by citation",
            content,
        )

    def test_checkpoint_model_amends_section_7_6(self):
        content = _flat(self.PROVIDER_JUDGES)
        self.assertIn("**Checkpoint-model amendment — 2026-07-22.**", content)
        self.assertIn(
            "`max-provider-dispatches-per-session: none` plus "
            "`provider-dispatch-checkpoint-every: 10`",
            content,
        )
        self.assertIn(
            "posts the one-line checkpoint with per-provider counts and the "
            "exact model slugs used, then continues unless the human objects",
            content,
        )
        self.assertIn("Provider rate-limit errors are surfaced verbatim.", content)
        self.assertIn(
            "A NUMERIC `max-provider-dispatches-per-session` value retains "
            "the original hard-cap semantics above unchanged.",
            content,
        )

    def test_tier_repin_is_reachable_and_structurally_sibling(self):
        content = _read(self.PROVIDER_JUDGES)
        self.assertIn(
            "> Amended by section 9 (2026-07-22): the tier map below is the "
            "historical record; section 9's re-pin governs.",
            content,
        )
        self.assertRegex(
            content,
            re.compile(
                r"^## 9\. Tier re-pin \+ owner-allowed model set — "
                r"2026-07-22$",
                re.MULTILINE,
            ),
        )
        self.assertNotRegex(
            content,
            re.compile(r"^### 9\. Tier re-pin", re.MULTILINE),
        )

    def test_skill_materialization_is_required_from_worker_dispatch(self):
        content = _flat(self.PROVIDER_JUDGES)
        self.assertIn(
            "Every worker dispatch under this section ALSO executes section "
            "8's skill-materialization contract and its INTEGRATE exclusion "
            "— section 8 is a REQUIRED step of worker dispatch, not an "
            "optional sibling.",
            content,
        )

    def test_pilot_clearance_marker_and_settings_only_write_rule(self):
        marker = ".forge/.trust-providers/<provider>.pilot-cleared.local"
        for path in (
            self.PROVIDER_JUDGES,
            self.OPERATOR_PROFILES,
            self.SETTINGS,
        ):
            with self.subTest(path=path):
                content = _flat(path)
                self.assertIn(marker, content)
                self.assertIn("settings", content)
                self.assertIn("NEVER writes the marker without that flow", content)

        settings = _flat(self.SETTINGS)
        self.assertIn("docs/pilots/2026-07-19-grok-pilot.md", settings)
        self.assertIn("docs/pilots/2026-07-19-antigravity-smoke.md", settings)
        self.assertIn("structured CLEAR/KEEP-CLOSED question", settings)
        self.assertIn("an absent marker means the pilot gate remains closed", settings)

    def test_settings_view_uses_checkpoint_default(self):
        content = _flat(self.SETTINGS)
        self.assertIn(
            "`max-provider-dispatches-per-session` (default `none`",
            content,
        )
        self.assertIn(
            "`provider-dispatch-checkpoint-every` (default `10`)",
            content,
        )
        self.assertIn(
            "setting a NUMERIC cap retains the original hard-cap semantics",
            content,
        )

    def test_configuration_mirror_uses_checkpoint_default(self):
        content = _read(self.CONFIGURATION)
        flat = " ".join(content.split())
        self.assertIn("- max-provider-dispatches-per-session: none", content)
        self.assertIn("- provider-dispatch-checkpoint-every: 10", content)
        self.assertIn(
            "`max-provider-dispatches-per-session` (default `none`)", flat
        )
        self.assertIn(
            "`provider-dispatch-checkpoint-every` (default `10`)", flat
        )
        self.assertIn(
            "a NUMERIC value retains the original hard-cap semantics", flat
        )


if __name__ == "__main__":
    unittest.main()
