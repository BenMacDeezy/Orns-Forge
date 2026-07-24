"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10908`: TestFgA10908VerificationInfrastructurePins.
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


class TestFgA10908VerificationInfrastructurePins(unittest.TestCase):
    """Covers fg-a10908's EARS clauses (constitution rule 3): persistent
    verification infrastructure — committed harnesses, one build/server per
    wave, cite-don't-restate environment invariants, the power-tools note,
    and the required CONTEXT PACK — is pinned across docs/conventions.md,
    the spawn-contract template, and the two verifier briefs so a future
    edit cannot silently drop any of it.
    """

    @staticmethod
    def _norm(path):
        # collapse whitespace so pins survive line-wrap changes
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        # EARS clause 6: dated section, validator-checkable phrasing.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Verification infrastructure — 2026-07-18 (fg-a10908)", c
        )

    def test_harness_commit_rule(self):
        # EARS clause 1.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "the NEXT agent RUNS it instead of hand-rolling a fresh one", c
        )
        self.assertIn(
            "Throwaway scaffolding is allowed only when the check is genuinely one-shot",
            c,
        )
        self.assertIn("the dispatch contract must say which", c)
        template = self._norm(
            "skills/kernel/references/spawn-contract-template.md"
        )
        self.assertIn("Committed harness(es) to RUN", template)
        self.assertIn("throwaway/one-shot", template)

    def test_one_build_server_per_wave(self):
        # EARS clause 2.
        c = self._norm("docs/conventions.md")
        self.assertIn("builds and starts ONE instance per wave", c)
        self.assertIn("passes the port/PID through the dispatch notes", c)
        self.assertIn("reuse it and never rebuild", c)
        self.assertIn("teardown is the kernel's, at wave end", c)
        template = self._norm(
            "skills/kernel/references/spawn-contract-template.md"
        )
        self.assertIn("Shared build/server for this wave", template)
        self.assertIn("reuse it, never rebuild", template)

    def test_cite_dont_restate_environment_invariants(self):
        # EARS clause 3.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "cites a committed reference file in the TARGET repo", c
        )
        self.assertIn("AGENTS.md", c)
        self.assertIn("rather than restating the prose per contract", c)
        template = self._norm(
            "skills/kernel/references/spawn-contract-template.md"
        )
        self.assertIn("Environment invariants: cite the target repo's committed reference file", template)
        self.assertIn("instead of restating port etiquette", template)

    def test_power_tools_note(self):
        # EARS clause 4.
        power_tools_example = (
            "Serena active: use find_referencing_symbols for impact checks; "
            "committed harness at scripts/verify-*"
        )
        c = self._norm("docs/conventions.md")
        self.assertIn(power_tools_example, c)
        self.assertIn(
            "so the scout's vetted shortlist reaches dispatch instead of dead-ending",
            c,
        )
        template = self._norm(
            "skills/kernel/references/spawn-contract-template.md"
        )
        self.assertIn("Power tools note, one line, when the scout/onboard has vetted", template)

    def test_context_pack_required_in_template(self):
        # EARS clause 5.
        c = self._norm("docs/conventions.md")
        self.assertIn("pre-computed CONTEXT PACK", c)
        self.assertIn("the committed harness paths to RUN", c)
        self.assertIn("the shared server port", c)
        self.assertIn(
            "any prior measurement tables that already settled facts", c
        )
        template = self._norm(
            "skills/kernel/references/spawn-contract-template.md"
        )
        self.assertIn("CONTEXT PACK is REQUIRED", template)
        self.assertIn(
            '(`docs/conventions.md`, "Verification infrastructure — 2026-07-18 (fg-a10908)")',
            template,
        )
        self.assertIn("CONTEXT PACK (pre-rooted — required, see above)", template)
        self.assertIn("Prior measurement tables:", template)

    def test_reuse_first_instruction_near_mission_in_both_verifier_briefs(self):
        # EARS clause 4 + 5: the panel members that actually pay the
        # scaffolding cost carry the reminder, not just the template.
        for path in ("agents/forge-verifier.md", "agents/forge-ui-verifier.md"):
            content = self._norm(path)
            self.assertIn("## Reuse-first (fg-a10908)", content)
            self.assertIn("never rebuild", content)
            self.assertIn(
                'docs/conventions.md`, "Verification infrastructure — 2026-07-18 (fg-a10908)',
                content,
            )
        # Placed near Mission, not buried: Mission heading precedes it and
        # nothing but the Reuse-first heading sits between them.
        verifier = _cached_read_text((REPO_ROOT / "agents/forge-verifier.md"))
        mission_idx = verifier.index("## Mission")
        reuse_idx = verifier.index("## Reuse-first (fg-a10908)")
        self.assertLess(mission_idx, reuse_idx)
        between = verifier[mission_idx:reuse_idx]
        self.assertEqual(between.count("## "), 1)

        ui_verifier = _cached_read_text((REPO_ROOT / "agents/forge-ui-verifier.md"))
        mission_idx = ui_verifier.index("## Mission")
        reuse_idx = ui_verifier.index("## Reuse-first (fg-a10908)")
        self.assertLess(mission_idx, reuse_idx)
        between = ui_verifier[mission_idx:reuse_idx]
        self.assertEqual(between.count("## "), 1)
