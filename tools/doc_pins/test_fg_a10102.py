"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10102`: TestFgA10102RoutingTuningPins.
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


class TestFgA10102RoutingTuningPins(unittest.TestCase):
    """Doc-pins for fg-a10102 (Evolve analogue: routing-tuning
    recommendations): the conventions section's heading, thresholds, and
    fable-exclusion sentence; the kernel LEARN paragraph's exact-name
    citation of that section and its never-self-apply sentence.

    `--recommend`'s ceiling behavior (opus/high -> "already at ceiling",
    never fable) is covered by tools/test_telemetry.py's unit tests, not
    pinned here — this class covers only the doc/prose surface.
    """

    def test_conventions_has_routing_tuning_section_heading(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "## Routing-tuning recommendations (Evolve analogue) — 2026-07",
            content,
        )

    def test_conventions_routing_tuning_section_in_toc(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "- Routing-tuning recommendations (Evolve analogue) — 2026-07",
            content,
        )

    def test_conventions_routing_tuning_section_has_thresholds(self):
        # Behavioral cross-check (2026-07-18 pin audit): the documented
        # thresholds must equal the real constants in tools/telemetry.py, so a
        # constant change can't silently strand the doc's numbers.
        import telemetry

        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Routing-tuning recommendations (Evolve analogue) — 2026-07"
        )[1]
        self.assertIn(
            f"dispatches ≥ {telemetry.RECOMMEND_MIN_DISPATCHES}", section
        )
        self.assertIn(
            "first-attempt FAIL-or-bounce rate ≥ "
            f"{telemetry.RECOMMEND_MIN_FAIL_RATE:.0%}",
            section,
        )
        self.assertIn(
            "changeable only by a human editing this section", section
        )

    def test_conventions_routing_tuning_section_has_fable_exclusion(self):
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Routing-tuning recommendations (Evolve analogue) — 2026-07"
        )[1]
        self.assertIn(
            "`fable` is never a recommendation target", section
        )
        self.assertIn(
            "Model\nvocabulary — fable amendment (2026-07-17)", section
        )

    def test_conventions_routing_tuning_section_has_delta_format_and_honesty(self):
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Routing-tuning recommendations (Evolve analogue) — 2026-07"
        )[1]
        self.assertIn("UNRATIFIED delta", section)
        self.assertIn(
            "### Proposed\ndelta — <date> — from <task-id> — UNRATIFIED", section
        )
        self.assertIn(
            "the identical human gate every other\nspec delta already goes through",
            section,
        )
        self.assertIn("Honesty rule", section)
        self.assertIn("no recommendations", section)

    def test_kernel_learn_cites_routing_tuning_section_by_exact_name(self):
        # fg-b0402: the Routing-tuning-recommendations paragraph moved
        # verbatim from skills/kernel/SKILL.md to
        # skills/kernel/references/routing-tuning.md -- pin STRING
        # unchanged, only the file read.
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "routing-tuning.md"))
        self.assertIn(
            '"Routing-tuning recommendations (Evolve analogue) — 2026-07"',
            content,
        )

    def test_kernel_learn_has_never_self_apply_sentence(self):
        # fg-b0402: moved verbatim to references/routing-tuning.md; pin
        # STRINGS unchanged, only the file read.
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "routing-tuning.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "The kernel NEVER edits the ROUTE + DISPATCH table, any task's "
            "Routing record, or `forge.md` on the",
            normalized,
        )
        self.assertIn("filing the UNRATIFIED delta is the entire", normalized)

    def test_kernel_learn_has_fable_never_recommended_sentence(self):
        # fg-b0402: moved verbatim to references/routing-tuning.md; pin
        # STRING unchanged, only the file read.
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "routing-tuning.md"))
        self.assertIn("`fable` is never recommended:", content)

    def test_kernel_learn_mentions_recommend_flag_and_trigger_condition(self):
        # fg-b0402: moved verbatim to references/routing-tuning.md; pin
        # STRINGS unchanged, only the file read.
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "routing-tuning.md"))
        self.assertIn("tools/telemetry.py --recommend`", content)
        self.assertIn("this session did protocol work", content)
