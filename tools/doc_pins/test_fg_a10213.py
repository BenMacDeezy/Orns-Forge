"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10213`: TestFgA10213RoleLabelPins.
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

from . import test_fg_9f0101 as _fg_9f0101_mod  # noqa: E402 -- fg-a11040 shard cross-reference (import the module, not the class, so pytest does not re-collect the TestCase as a duplicate test item here)


class TestFgA10213RoleLabelPins(unittest.TestCase):
    """Doc-pins for fg-a10213 (dispatch label format): the spawn label
    drops the task id AND the verb/title tail, becoming exactly
    "<Persona> (<short-role>)" -- e.g. "Aegis (security)" -- with
    "<Persona> #N (<role>)" for swarm/shard disambiguation. Amends
    "Dispatch display labels — persona amendment — 2026-07" (its
    `<Persona> · <short task title>` format is superseded, not deleted --
    see TestFg9f0101PersonaPins.test_conventions_persona_section_has_label_format
    for the historical pin) via a tail-appended dated subsection, house
    pattern per "Ship-judge widening + Critical-security exploit bar —
    2026-07-18". Covers all 3 EARS clauses.
    """

    CHAR_CEILING = 31617
    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"

    # A couple of representative rows from the full persona->role mapping
    # (EARS clause 1) -- not re-listing all 20 here, that's the table pin.
    REPRESENTATIVE_ROLES = {
        "Aegis": "security",
        "Grud": "grunt",
    }

    # The full persona->role mapping, quoted verbatim from EARS clause 1 --
    # a separate axis from _fg_9f0101_mod.TestFg9f0101PersonaPins.CANONICAL_PERSONAS
    # (which maps agent SLUG -> persona, not persona -> role).
    CANONICAL_ROLES = {
        "Aegis": "security",
        "Vera": "verify",
        "Iris": "ui-verify",
        "Rook": "review",
        "Lex": "legal",
        "Brokk": "build",
        "Blue": "architect",
        "Hex": "debug",
        "Pixel": "ui",
        "Flux": "motion",
        "Tess": "test",
        "Sage": "research",
        "Tern": "migrate",
        "Scout": "scout",
        "Atlas": "map",
        "Page": "library",
        "Quill": "spec",
        "Doc": "triage",
        "Rune": "data",
        "Hound": "find",
        "Foil": "refute",
        "Gavel": "judge",
        "Grud": "grunt",
        "Roam": "mobile",
        "Lens": "mobile-verify",
    }

    def _conventions(self):
        return conventions_corpus.corpus_text()

    def _section(self):
        content = self._conventions()
        marker = "## Dispatch display labels — role-label amendment — 2026-07-18"
        self.assertIn(
            marker, content,
            "conventions.md is missing the fg-a10213 role-label amendment "
            "section",
        )
        return content.split(marker, 1)[1]

    def _normalized_section(self):
        return re.sub(r"\s+", " ", self._section())

    def test_conventions_has_role_label_heading(self):
        self.assertIn(
            "## Dispatch display labels — role-label amendment — 2026-07-18",
            self._conventions(),
        )

    def test_toc_lists_the_new_section_nested_under_topic(self):
        # TOC entry text must equal the heading verbatim (pin-enforced
        # elsewhere), nested three-deep under "Dispatch display labels".
        c = self._conventions()
        self.assertIn(
            "  - Dispatch display labels — role-label amendment — 2026-07-18",
            c,
        )

    def test_persona_amendment_has_amended_by_pointer(self):
        # Dated amendment + Amended-by pointer, house pattern.
        c = self._conventions()
        self.assertIn(
            '## Dispatch display labels — persona amendment — 2026-07\n\n'
            '> Amended by: "Dispatch display labels — role-label '
            'amendment — 2026-07-18"',
            c,
        )

    def test_label_format_no_task_id_no_verb_tail(self):
        """EARS clause 1: exact format string, plus the explicit no-task-id
        AND no-verb/title-tail rule (dropping BOTH the id and the task
        title/verb the persona amendment used to carry)."""
        normalized = self._normalized_section()
        self.assertIn("`<Persona> (<short-role>)`", normalized)
        self.assertIn("no task id", normalized)
        self.assertIn("no task title / verb phrasing", normalized)

    def test_representative_mappings_present(self):
        # EARS clause 1: a couple of representative persona->role rows,
        # plus the table anchor, inside the new section specifically.
        section = self._section()
        self.assertIn("| Persona | Role |", section)
        for persona, role in self.REPRESENTATIVE_ROLES.items():
            self.assertIn(f"| {persona} | {role} |", section)

    def test_full_persona_role_mapping_present(self):
        # All 20 roster personas get a role word; örn (orchestrator, no
        # agents/*.md file) explicitly carries none. Cross-check: every
        # persona named here is also a value in CANONICAL_PERSONAS
        # (slug -> persona), so the two axes can't silently drift apart.
        self.assertEqual(
            set(self.CANONICAL_ROLES),
            set(_fg_9f0101_mod.TestFg9f0101PersonaPins.CANONICAL_PERSONAS.values()),
        )
        section = self._section()
        for persona, role in self.CANONICAL_ROLES.items():
            self.assertIn(f"| {persona} | {role} |", section)
        normalized = self._normalized_section()
        self.assertIn("örn (orchestrator) carries no role word", normalized)

    def test_swarm_instance_number_rule(self):
        """EARS clause 2: swarm/shard disambiguation is by instance number
        only, "<Persona> #N (<role>)", never the task id."""
        normalized = self._normalized_section()
        self.assertIn('`<Persona> #N (<role>)`', normalized)
        self.assertIn("Grud #3 (grunt)", normalized)
        self.assertIn("never the task id", normalized)

    def test_harness_prefix_note(self):
        """EARS clause 3: the harness's own agent-TYPE prefix (e.g.
        "forge:forge-security") is explicitly named as harness-owned, NOT
        part of the Forge label, and the label must not duplicate it with
        a verb."""
        normalized = self._normalized_section()
        self.assertIn("forge:forge-security", normalized)
        self.assertIn("harness-owned", normalized)
        self.assertIn(
            "must never re-state or duplicate that harness prefix with a "
            "verb or description of its own",
            normalized,
        )

    def test_kernel_dispatch_line_uses_role_format(self):
        content = re.sub(
            r"\s+", " ", _cached_read_text(self.KERNEL_PATH)
        )
        self.assertIn(
            'Any human-visible dispatch label is "<Persona> (<role>)" — no '
            'task id, no verb/title tail',
            content,
        )

    def test_kernel_skill_within_char_ceiling(self):
        # Same hard ceiling as the other kernel-file pins (grep 31617) --
        # this task's label-prose replacement must land at or under it.
        content = _cached_read_text(self.KERNEL_PATH)
        self.assertLessEqual(len(content), self.CHAR_CEILING)

    def test_ship_skill_cites_role_label_for_judge_fanout(self):
        """Ship-fan-out judges (Rook/Aegis/Lex) get the same
        <Persona> (<role>) label — EARS clause 1's "ship fan-out" trigger."""
        content = re.sub(
            r"\s+",
            " ",
            _cached_read_text((REPO_ROOT / "skills" / "ship" / "SKILL.md")),
        )
        self.assertIn(
            "Each parallel-dispatched judge's display label is "
            "`<Persona> (<role>)`", content,
        )
        self.assertIn("Rook (review)", content)
        self.assertIn("Aegis (security)", content)
        self.assertIn("Lex (legal)", content)
        self.assertIn(
            '"Dispatch display labels — role-label amendment — 2026-07-18"',
            content,
        )
