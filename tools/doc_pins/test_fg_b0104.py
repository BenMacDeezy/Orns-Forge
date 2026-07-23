"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0104`: TestFgB0104ProfileWiringPins.
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


class TestFgB0104ProfileWiringPins(unittest.TestCase):
    """fg-b0104 (spec-4d2a): operator profile config + kernel gate wiring --
    skills/kernel/references/profile-wiring.md, the forge-config-template.md
    `## Operator profile` section, the kernel SYNC stub, the spec-skill
    floor citation, and the settings.md render line.

    Whitespace-normalized comparisons throughout (line wraps in the source
    prose are not semantically meaningful), same pattern as
    TestFgB0103OperatorProfileContainerPins._norm above."""

    WIRING_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "profile-wiring.md"
    )
    TEMPLATE_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references"
        / "forge-config-template.md"
    )
    KERNEL_SKILL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    SPEC_SKILL_PATH = REPO_ROOT / "skills" / "spec" / "SKILL.md"
    SETTINGS_PATH = REPO_ROOT / "commands" / "settings.md"

    @staticmethod
    def _norm(path):
        text = _cached_read_text(path)
        return " ".join(text.split())

    def _wiring(self):
        return self._norm(self.WIRING_PATH)

    def _template(self):
        return self._norm(self.TEMPLATE_PATH)

    def _kernel(self):
        return self._norm(self.KERNEL_SKILL_PATH)

    def _kernel_raw(self):
        return _cached_read_text(self.KERNEL_SKILL_PATH)

    def _spec_skill(self):
        return self._norm(self.SPEC_SKILL_PATH)

    def _settings(self):
        return self._norm(self.SETTINGS_PATH)

    # (1) default-mapping rule -- profile-wiring.md AND the template comment
    def test_default_mapping_rule_in_wiring_reference(self):
        content = self._wiring()
        self.assertIn(
            "`guided` for a fresh install (a repo with no prior "
            "Forge state), `full-auto` for an existing install (mapping "
            "its current behavior forward unchanged)",
            content,
        )

    def test_default_mapping_rule_in_config_template(self):
        content = self._template()
        self.assertIn("`stock:guided` for", content)
        self.assertIn("`stock:full-auto` for an existing install", content)

    # (2) precedence line
    def test_precedence_line(self):
        content = self._wiring()
        self.assertIn(
            "profile default < explicit forge.md value < FLOOR.",
            content,
        )

    # (3) floor-enforcement phrases -- profile-wiring.md AND the spec-skill
    # gate citation line
    def test_floor_enforcement_phrase_in_wiring_reference(self):
        content = self._wiring()
        self.assertIn(
            "no profile SHALL relax the trust boundary's first-touch "
            "confirm, raise `max-tasks-per-session` / `session-token-cap` "
            "beyond what the human set, or skip the spec approval gate.",
            content,
        )

    def test_floor_enforcement_citation_in_spec_skill(self):
        content = self._spec_skill()
        self.assertIn(
            "This gate is a FLOOR", content,
        )
        self.assertIn(
            "unconditional regardless of the active operator profile",
            content,
        )
        self.assertIn(
            "never removes or auto-answers this gate", content
        )

    # (4) pause-points-all-tiers phrase + the three concrete enforcement
    # points
    def test_pause_points_all_tiers_phrase(self):
        content = self._wiring()
        self.assertIn(
            "pause-point gating applies to ALL tiers, not only `tier: "
            "full`'s existing plan/ship-review steps",
            content,
        )
        self.assertIn(
            'review all plans" means every dispatch batch can pause.',
            content,
        )

    def test_three_concrete_pause_points_named(self):
        content = self._wiring()
        self.assertIn("**Dispatch batch**", content)
        self.assertIn("**INTEGRATE**", content)
        self.assertIn("**Plan/spec review**", content)

    # (5) graceful-degrade phrase
    def test_graceful_degrade_phrase(self):
        content = self._wiring()
        self.assertIn(
            "the gate degrades to a human-only gate with one stated note",
            content,
        )
        self.assertIn(
            "never silently skip the gate and never block on a "
            "provider that isn't there.",
            content,
        )

    # (6) kernel SYNC stub cites profile-wiring.md
    def test_kernel_sync_stub_cites_profile_wiring(self):
        content = self._kernel()
        self.assertIn("**Operator profile resolution.**", content)
        self.assertIn(
            "skills/kernel/references/profile-wiring.md", content
        )

    # (7) exact render string in settings.md
    def test_settings_renders_default_string(self):
        # Pin the fg-b0104 Operator-profile bullet specifically -- the bare
        # render string also pre-exists in the Features prose, so asserting
        # it alone would not regress on loss of this task's addition
        # (verifier finding, fixed kernel-inline at INTEGRATE).
        content = self._settings()
        self.assertIn("**Operator profile** — the `active:` pointer", content)
        self.assertIn("(default — not yet in forge.md)", content)

    # (8) kernel char count under 31,617
    def test_kernel_stays_under_char_budget(self):
        """The kernel SYNC delta for fg-b0104 is a short citation stub, not
        a restatement of profile-wiring.md -- confirm the file is still
        well under the 31,617-char ceiling (same assert style as
        TestFgC0113ProviderBudgetCapPins)."""
        content = self._kernel_raw()
        self.assertLess(len(content), 31617)
