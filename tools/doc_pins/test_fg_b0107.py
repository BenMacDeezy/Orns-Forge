"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0107`: TestFgB0107ProfileComparisonPins.
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


class TestFgB0107ProfileComparisonPins(unittest.TestCase):
    """fg-b0107 (spec-4d2a): the profile-comparison doc page --
    docs/profile-comparison.md -- one comparison table across the three
    shipped stock autonomy profiles plus one Mermaid flowchart per profile
    showing gate-pause placement at the exact kernel-loop steps
    profile-wiring.md names (steps 3/5/7: PLAN/DISPATCH/INTEGRATE), an
    honest Providers-domain status note, a picker pointer, and a cross-link
    from docs/architecture.md's Subsystems list."""

    DOC_PATH = REPO_ROOT / "docs" / "profile-comparison.md"
    ARCHITECTURE_PATH = REPO_ROOT / "docs" / "architecture.md"

    @staticmethod
    def _doc():
        return _cached_read_text(TestFgB0107ProfileComparisonPins.DOC_PATH)

    @staticmethod
    def _architecture():
        return _cached_read_text(TestFgB0107ProfileComparisonPins.ARCHITECTURE_PATH)

    def test_doc_page_exists_at_task_boundary_path(self):
        self.assertTrue(
            self.DOC_PATH.is_file(),
            "docs/profile-comparison.md must exist at the fg-b0107 task "
            "boundary path",
        )

    def test_comparison_table_has_all_three_profile_columns(self):
        content = self._doc()
        self.assertIn("`full-auto`", content)
        self.assertIn("`guided`", content)
        self.assertIn("`high-touch`", content)
        self.assertIn("**Pause points**", content)
        self.assertIn("**Wave size**", content)
        self.assertIn("**Verification panel**", content)
        self.assertIn("**Who it's for**", content)

    def test_comparison_table_pause_points_values_match_stock_content(self):
        # Verbatim-transcription pin: these values must match the shipped
        # stock profile bodies in operator-profiles.md exactly (fg-b0105).
        content = self._doc()
        self.assertIn("`none`", content)
        self.assertIn("`plan`, `integrate`", content)
        self.assertIn("`plan`, `dispatch`, `integrate`", content)

    def test_comparison_table_wave_size_and_panel_values_match_stock_content(self):
        content = self._doc()
        self.assertIn("`unchanged`", content)
        self.assertIn("`capped-1`", content)
        self.assertIn("`quiet`", content)
        self.assertIn("`summary`", content)
        self.assertIn("`full`", content)

    def test_fresh_and_existing_install_default_cited(self):
        content = self._doc()
        self.assertIn("fresh-install default", content)
        self.assertIn("existing-install default", content)

    def test_exactly_three_mermaid_flowcharts_present(self):
        content = self._doc()
        self.assertEqual(
            content.count("```mermaid"),
            3,
            "exactly one Mermaid flowchart per shipped stock profile "
            "(full-auto / guided / high-touch)",
        )
        self.assertEqual(content.count("flowchart TD"), 3)

    def test_each_flowchart_walks_all_eight_kernel_loop_steps(self):
        content = self._doc()
        blocks = re.findall(r"```mermaid\n(.*?)```", content, re.S)
        self.assertEqual(len(blocks), 3)
        for block in blocks:
            for step in [
                "1. SYNC",
                "2. PULL",
                "3. PLAN",
                "4. GATE",
                "5. ROUTE + DISPATCH",
                "6. VERIFY",
                "7. INTEGRATE",
                "8. LEARN",
            ]:
                self.assertIn(
                    step, block,
                    f"step {step!r} missing from a flowchart block",
                )

    def test_full_auto_flowchart_has_no_pause_diamonds(self):
        content = self._doc()
        full_auto_start = content.index("### `full-auto`")
        guided_start = content.index("### `guided`")
        full_auto_section = content[full_auto_start:guided_start]
        self.assertNotIn("PAUSE_", full_auto_section)

    def test_guided_flowchart_pauses_at_plan_and_integrate_only(self):
        content = self._doc()
        guided_start = content.index("### `guided`")
        high_touch_start = content.index("### `high-touch`")
        guided_section = content[guided_start:high_touch_start]
        self.assertIn("PAUSE_PLAN", guided_section)
        self.assertIn("PAUSE_INTEGRATE", guided_section)
        self.assertNotIn("PAUSE_DISPATCH", guided_section)

    def test_high_touch_flowchart_pauses_at_plan_dispatch_and_integrate(self):
        content = self._doc()
        high_touch_start = content.index("### `high-touch`")
        providers_start = content.index("## Providers domain")
        high_touch_section = content[high_touch_start:providers_start]
        self.assertIn("PAUSE_PLAN", high_touch_section)
        self.assertIn("PAUSE_DISPATCH", high_touch_section)
        self.assertIn("PAUSE_INTEGRATE", high_touch_section)
        self.assertIn("capped-1", high_touch_section)

    def test_pause_placement_cites_steps_3_5_7(self):
        content = self._doc()
        self.assertIn("after step 3 (PLAN)", content)
        self.assertIn("before step 5 (ROUTE + DISPATCH)", content)
        self.assertIn("before step 7 (INTEGRATE)", content)

    def test_providers_domain_status_is_honest_schema_shipped_dispatch_pending(self):
        content = self._doc()
        self.assertIn("## Providers domain", content)
        self.assertIn("schema and stock content are shipped", content)
        self.assertIn("no dispatch\npath reads it yet", content)
        self.assertIn("fg-c0106", content)
        self.assertIn("fg-c0111", content)

    def test_picker_pointer_present(self):
        content = self._doc()
        self.assertIn("/forge:settings", content)
        self.assertIn("commands/settings.md", content)

    def test_cites_sources_of_truth_without_restating_container_format(self):
        # This page must cite the container format / precedence / wiring
        # files rather than re-deriving their normative content.
        content = self._doc()
        self.assertIn("skills/kernel/references/operator-profiles.md", content)
        self.assertIn("skills/kernel/references/profile-wiring.md", content)
        self.assertIn("commands/settings.md", content)

    def test_cross_linked_from_architecture_subsystems_list(self):
        content = self._architecture()
        self.assertIn("profile-comparison.md", content)
        self.assertIn("Operator profiles", content)
