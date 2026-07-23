"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0105`: TestFgB0105AutonomyStockProfilePins.
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


class TestFgB0105AutonomyStockProfilePins(unittest.TestCase):
    """fg-b0105 (spec-4d2a): the autonomy-domain stock profile content --
    the three stock profiles (full-auto / guided / high-touch), their
    pause-points/wave-size values, and the fresh/existing-install default
    mapping, all in skills/kernel/references/operator-profiles.md."""

    REFERENCE_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "operator-profiles.md"
    )

    @staticmethod
    def _content():
        return _cached_read_text(TestFgB0105AutonomyStockProfilePins.REFERENCE_PATH)

    def test_all_three_stock_profile_headings_present(self):
        content = self._content()
        self.assertIn("### Stock profile: `full-auto`", content)
        self.assertIn("### Stock profile: `guided`", content)
        self.assertIn("### Stock profile: `high-touch`", content)

    def test_high_touch_wave_cap(self):
        content = self._content()
        self.assertIn("wave-size: capped-1", content)
        self.assertIn('"high-touch caps waves at 1"', content)

    def test_guided_and_full_auto_wave_size_unchanged(self):
        content = self._content()
        self.assertIn('"full-auto unchanged"', content)
        self.assertIn(
            '"guided keeps full wave sizes with its own pause\npoints"',
            content,
        )
        self.assertEqual(content.count("wave-size: unchanged"), 3)

    def test_fresh_and_existing_install_default_mapping(self):
        content = self._content()
        self.assertIn(
            "**a fresh Forge install with no\nprior `.forge/` state "
            "defaults its active autonomy profile to `guided`**",
            content,
        )
        self.assertIn(
            "**an existing install that already has `.forge/` state "
            "predating operator\nprofiles defaults to `full-auto`**",
            content,
        )

    def test_pause_points_apply_across_every_tier(self):
        content = self._content()
        self.assertIn(
            "apply across every task tier, not\n  only `tier: full`",
            content,
        )

    def test_pause_points_per_profile(self):
        # Hostile-edit trip wire: each profile's exact pause-points value,
        # so relaxing high-touch's pause set (or any other profile's) away
        # from its spec-4d2a-resolved list fails this pin.
        content = self._content()
        self.assertIn("pause-points: none", content)
        self.assertIn("pause-points: plan, integrate", content)
        self.assertIn("pause-points: plan, dispatch, integrate", content)
