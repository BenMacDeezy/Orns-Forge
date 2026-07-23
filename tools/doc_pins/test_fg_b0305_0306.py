"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0305_0306`: TestFgb0305_0306PromotionRetentionPins.
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


class TestFgb0305_0306PromotionRetentionPins(unittest.TestCase):
    """Doc-pins for fg-b0305 (usage-based promotion) + fg-b0306 (retention/
    pruning scope extension) — the two land together in one
    docs/conventions.md append per spec-b71f3a's own collision mitigation.

    Covers: skills/agent-factory/SKILL.md's new "Promotion" section
    (threshold, never-automatic, placement mirroring commands/agent.md,
    headless surfacing, approve mechanics, decline-with-doubling-backoff,
    tools-never-widened) and the "Pruning" section's minimal archive-tier
    scope extension; docs/conventions.md's one dated section covering both
    task's normative text, its TOC entry, and its Amended-by/Amends
    cross-links on "Ephemeral agent tier"; and agents/forge-librarian.md
    carrying the promotion-proposal pass while its off-critical-path
    constraint stays verbatim-intact.
    """

    SKILL_PATH = REPO_ROOT / "skills" / "agent-factory" / "SKILL.md"
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    LIBRARIAN_PATH = REPO_ROOT / "agents" / "forge-librarian.md"
    CONVENTIONS_HEADING = (
        "## Agent promotion and retention — 2026-07-19 "
        "(fg-b0305+fg-b0306, spec-b71f3a)"
    )

    def _skill_normalized(self):
        content = _cached_read_text(self.SKILL_PATH)
        return content, re.sub(r"\s+", " ", content)

    def test_skill_has_promotion_heading_symmetric_to_pruning(self):
        content, _ = self._skill_normalized()
        self.assertIn("## Promotion (usage-earned, human-ratified)", content)
        self.assertIn("## Pruning", content)
        # Promotion must precede Pruning (symmetric counterpart, sits next to it).
        self.assertLess(
            content.index("## Promotion (usage-earned, human-ratified)"),
            content.index("## Pruning"),
        )

    def test_skill_promotion_has_threshold_phrase(self):
        _, normalized = self._skill_normalized()
        self.assertIn(
            "3+ dispatches within any rolling 14-day window", normalized
        )
        self.assertIn("tools/agent_usage.py", normalized)
        self.assertIn("count_dispatches", normalized)
        self.assertIn("--window-days", normalized)

    def test_skill_promotion_is_never_automatic(self):
        _, normalized = self._skill_normalized()
        self.assertIn(
            "forge-librarian` files the promotion PROPOSAL — never "
            "automatic", normalized,
        )

    def test_skill_promotion_has_placement_mirroring_agent_command(self):
        _, normalized = self._skill_normalized()
        self.assertIn(
            "mirroring `/forge:agent`'s own \"Placement\" question "
            "(`commands/agent.md`)", normalized,
        )
        self.assertIn("recommended default", normalized)
        self.assertIn("project-agnostic", normalized)

    def test_skill_promotion_has_headless_surfacing(self):
        _, normalized = self._skill_normalized()
        self.assertIn(
            "No blocking gate — record the proposal prominently in the "
            "session report instead", normalized,
        )

    def test_skill_promotion_has_approve_mechanics(self):
        _, normalized = self._skill_normalized()
        self.assertIn("Move archive → destination", normalized)
        self.assertIn("mirror to `.claude/agents/`", normalized)
        self.assertIn("lifecycle: standing", normalized)
        self.assertIn(
            "promoted: <ISO-8601 date> — evidence: N dispatches in M days",
            normalized,
        )

    def test_skill_promotion_has_telemetry_slug_registration(self):
        # fg-b0307: On APPROVE mechanics now include registering the
        # promoted agent's slug into tools/telemetry.py's AGENT_SLUGS.
        _, normalized = self._skill_normalized()
        self.assertIn(
            "add the promoted agent's slug to `tools/telemetry.py`'s "
            "`AGENT_SLUGS` so its dispatches attribute in telemetry from "
            "promotion onward", normalized,
        )

    def test_skill_promotion_has_decline_doubling_backoff(self):
        _, normalized = self._skill_normalized()
        self.assertIn("forge:memory", normalized)
        self.assertIn(
            "never re-propose until usage has doubled again from the "
            "count at decline", normalized,
        )

    def test_skill_promotion_has_tools_never_widened(self):
        _, normalized = self._skill_normalized()
        self.assertIn("Tools never widen at promotion.", normalized)
        self.assertIn(
            "copied verbatim from the ephemeral original — never widened",
            normalized,
        )

    def test_skill_pruning_scope_names_archive_tier(self):
        """The Pruning section's scope sentence extension is minimal — one
        clause naming the archive tier and citing the conventions section,
        not a rewrite of the whole section."""
        content = _cached_read_text(self.SKILL_PATH)
        pruning_section = content.split("## Pruning")[1]
        normalized = re.sub(r"\s+", " ", pruning_section)
        self.assertIn(".forge/agents/archive/*.md", normalized)
        self.assertIn(
            "Agent promotion and retention — 2026-07-19 "
            "(fg-b0305+fg-b0306, spec-b71f3a)", normalized,
        )
        self.assertIn("human-approved only", normalized)

    def test_conventions_has_dated_heading(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn(self.CONVENTIONS_HEADING, content)

    def test_conventions_section_covers_both_tasks(self):
        content = _read_path(self.CONVENTIONS_PATH)
        section = content.split(self.CONVENTIONS_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("### Usage-based promotion (fg-b0305)", normalized)
        self.assertIn(
            "### Retention and pruning scope extension (fg-b0306)",
            normalized,
        )
        self.assertIn(
            "the spec's own collision mitigation", normalized
        )

    def test_conventions_toc_lists_new_section_nested_under_ephemeral_tier(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn(
            "    - Agent promotion and retention — 2026-07-19 "
            "(fg-b0305+fg-b0306, spec-b71f3a)",
            content,
        )

    def test_conventions_ephemeral_tier_has_amended_by_pointer(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn(
            '## Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)\n\n'
            '> Amended by: "Agent promotion and retention — 2026-07-19 '
            '(fg-b0305+fg-b0306, spec-b71f3a)"',
            content,
        )

    def test_conventions_new_section_has_amends_pointer(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn(
            self.CONVENTIONS_HEADING + '\n\n'
            '> Amends: "Ephemeral agent tier — 2026-07-19 '
            '(fg-b0301, spec-b71f3a)" (above).',
            content,
        )

    def test_conventions_new_section_is_tail_appended(self):
        """This section must never be spliced mid-document -- every
        heading present when fg-b0305/fg-b0306 landed (i.e. everything up
        to and including "Customization persistence contract — 2026-07-18
        (fg-b0101)", the TOC entry immediately preceding this one at the
        time) must still precede it. Later tasks (e.g. onboard-offer-nudge,
        2026-07-20) tail-append their OWN sections after this one, so this
        no longer needs to be the file's literal last heading -- only
        never inserted before its own predecessor, which is what
        tail-append discipline actually guarantees."""
        content = _read_path(self.CONVENTIONS_PATH)
        headings = re.findall(r"^## .+$", content, re.MULTILINE)
        idx = headings.index(self.CONVENTIONS_HEADING)
        predecessor = "## Customization persistence contract — 2026-07-18 (fg-b0101)"
        self.assertIn(predecessor, headings)
        self.assertLess(headings.index(predecessor), idx)

    def test_conventions_retention_subsection_has_90_day_threshold(self):
        """AC-Retention 2's two defining, mechanically-checkable facts —
        the 90-day age threshold and the never-crossed-the-promotion-
        threshold condition — must both survive in the Retention
        subsection specifically, not just somewhere in the file."""
        content = _read_path(self.CONVENTIONS_PATH)
        section = content.split(
            "### Retention and pruning scope extension (fg-b0306)"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("90 days", normalized)
        self.assertIn("never crossed the promotion threshold", normalized)
        self.assertIn("human-approved only", normalized)

    def test_librarian_has_promotion_pass(self):
        content = _cached_read_text(self.LIBRARIAN_PATH)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("tools/agent_usage.py", normalized)
        self.assertIn("promotion PROPOSAL", normalized)
        self.assertIn("pruning candidate", normalized)

    def test_librarian_duty4_has_90_day_threshold(self):
        """Same AC-Retention 2 pin as the conventions Retention subsection,
        applied to the librarian's own duty-4 wording — both surfaces
        must state the mechanical age/threshold facts, not just cite
        each other."""
        content = _cached_read_text(self.LIBRARIAN_PATH)
        section = content.split(
            "### 4. Agent promotion & retention"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("90 days", normalized)
        self.assertIn("never crossed the promotion threshold", normalized)

    def test_librarian_off_critical_path_constraint_verbatim_intact(self):
        """The librarian's off-critical-path constraint (frontmatter
        description + Mission) must survive this extension byte-for-byte."""
        content = _cached_read_text(self.LIBRARIAN_PATH)
        self.assertIn(
            "description: Consolidates project memory, checks/refreshes "
            "map freshness, and does queue hygiene — off the critical "
            "path (session start or idle), never inside a task dispatch. "
            "Use with a complete contract.",
            content,
        )
        self.assertIn(
            "You are the librarian. You run maintenance, never task work: "
            "memory\nconsolidation, map freshness, and queue hygiene.",
            content,
        )

    def test_librarian_never_widens_tools_or_promotes_unilaterally(self):
        content = _cached_read_text(self.LIBRARIAN_PATH)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Never move, mirror, or promote an agent file yourself — "
            "propose only", normalized,
        )
