"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0103`: TestFgC0103ProvidersOptInAndTrustGatePins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
    _CONVENTIONS_PATH_RESOLVED,
    _WORD_TO_INT,
    validate_task,
    shard_task,
    conventions_corpus,
)


class TestFgC0103ProvidersOptInAndTrustGatePins(unittest.TestCase):
    """Pins for fg-c0103 (spec-e8a3, "Per-repo opt-in and per-provider
    trust"): the `providers` Feature's OFF default, the once-per-provider-
    per-repo-per-machine TOFU confirmation, and the /forge:settings entry
    point that walks both gates.
    """

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    SETTINGS_PATH = REPO_ROOT / "commands" / "settings.md"
    TEMPLATE_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references"
        / "forge-config-template.md"
    )

    def _conventions_content(self):
        return _read_path(self.CONVENTIONS_PATH)

    def _settings_content(self):
        return _cached_read_text(self.SETTINGS_PATH)

    def test_providers_feature_off_default_in_conventions(self):
        """The Features table row for `providers` states OFF-by-default,
        the one exception among the Features vocabulary (every other
        toggle defaults on)."""
        content = self._conventions_content()
        self.assertIn("| `providers` | off |", content)
        self.assertIn(
            "OFF by default for every repo that has not explicitly "
            "turned it on",
            content,
        )

    def test_providers_feature_off_default_in_config_template(self):
        content = _cached_read_text(self.TEMPLATE_PATH)
        self.assertIn("- providers: off", content)

    def test_settings_command_lists_providers_toggle(self):
        content = self._settings_content()
        self.assertIn("`workflow-executor`, `providers`", content)

    def test_once_per_provider_per_repo_per_machine_phrase_in_conventions(
        self,
    ):
        content = self._conventions_content()
        self.assertIn(
            "once per provider, per repo, per machine", content
        )

    def test_once_per_provider_per_repo_per_machine_phrase_in_settings(
        self,
    ):
        content = self._settings_content()
        self.assertIn(
            "once per provider per repo per machine", content
        )

    def test_conventions_states_dispatching_sends_repo_content_risk_line(
        self,
    ):
        content = self._conventions_content()
        self.assertIn(
            "dispatching sends repo content to another vendor", content
        )

    def test_settings_states_dispatching_sends_repo_content_risk_line(self):
        content = self._settings_content()
        self.assertIn(
            "dispatching sends repo content to another vendor", content
        )

    def test_conventions_defines_per_provider_trust_marker_path(self):
        content = self._conventions_content()
        self.assertIn(
            ".forge/.trust-providers/<provider-id>.local", content
        )

    def test_settings_command_is_the_providers_entry_point(self):
        """settings.md explicitly owns the providers walk rather than a
        separate commands/providers.md (Attempt log states the reasoning)."""
        content = self._settings_content()
        self.assertIn("Per-provider trust confirm (`providers`", content)
        self.assertIn("/forge:providers", content)

    def test_settings_requires_providers_on_before_provider_confirm(self):
        content = self._settings_content()
        self.assertIn("require `providers: on` first", content)

    def test_settings_step4_ensures_trust_providers_gitignore_entry(self):
        """Bounce fix: the gitignore-ensure for `.forge/.trust-providers/`
        must live at the real toggle site (settings.md step 5), not be
        attributed to forge:onboard (which has no providers awareness)."""
        content = self._settings_content()
        self.assertIn("ensure `.forge/.trust-providers/`", content)
        self.assertIn("append the line idempotently", content)

    def test_trust_shard_names_settings_as_the_gitignore_mechanism(self):
        """No drift: the trust shard must point at the same mechanism
        (settings.md step 5, toggle time) rather than forge:onboard."""
        content = self._conventions_content()
        self.assertIn(
            "`commands/settings.md` step 5", content
        )
        self.assertIn(
            "is the real toggle site", content
        )
        self.assertIn(
            "not current behavior", content
        )
