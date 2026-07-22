"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9e0101`: TestFg9e0101LatencyPins.
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


class TestFg9e0101LatencyPins(unittest.TestCase):
    """Doc-pins for fg-9e0101 (kernel dedup stubs + description rewrite; ship
    -review overlap; verifier-tagged mechanical bounces; canonical latency
    conventions section).

    Covers all 4 EARS clauses: (1) the three dedup stubs keep a pointer
    phrase AND at least one inline enforcement condition, so a future edit
    can't silently gut a stub down to a bare cross-reference with no
    enforcement content left; (2) the ship-overlap parallel fan-out sentence
    survives in both the kernel and the workflow script; (3) both verifier
    agents carry the MECHANICAL|JUDGMENT tag contract; (4) the canonical
    dated conventions section exists, named exactly so it can be cited.
    """

    def test_kernel_finder_stub_has_pointer_and_enforcement_condition(self):
        # fg-b0402: the finder/kernel-synthesis detail moved verbatim from
        # skills/kernel/SKILL.md to skills/kernel/references/verify-modes.md
        # -- pin STRING unchanged, only the file read.
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "verify-modes.md"))
        self.assertIn('"Report tasks (finder pattern),"', content)
        self.assertIn("which is NORMATIVE", content)
        # (a)/(b)/(c) enforcement conditions kept inline, not just the pointer
        self.assertIn(
            "finder — verification:\n   kernel synthesis",
            content,
            "finder stub must keep the (a) Routing-record-declares-it "
            "enforcement condition inline, not just a pointer",
        )
        self.assertIn(
            "re-checked against the CURRENT tree state",
            content,
            "finder stub must keep the (b) stale-finding re-check "
            "enforcement condition inline, not just a pointer",
        )

    def test_kernel_gates_pending_stub_has_pointer_and_enforcement_condition(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertIn('"Empty-repo gates-pending\n  mode"', content)
        self.assertIn("which is NORMATIVE", content)
        # trigger + exit kept inline, not just the pointer
        self.assertIn("do NOT halt", content)
        self.assertIn(
            "dispatch only tasks whose acceptance criteria are\n  self-contained",
            content,
            "GATES-PENDING stub must keep the trigger/behavior condition "
            "inline, not just a pointer",
        )
        self.assertIn(
            "exit\n  GATES-PENDING the moment real tooling lands",
            content,
            "GATES-PENDING stub must keep the exit condition inline, not "
            "just a pointer",
        )

    def test_kernel_ship_stub_has_pointer_and_governs_language(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertIn("invoke `forge:ship`; its\n  checklist governs", content)
        self.assertIn("skills/ship/SKILL.md`'s checklist, which is NORMATIVE", content)

    def test_kernel_description_trigger_phrases_survive(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        description_line = content.splitlines()[2]
        self.assertTrue(description_line.startswith("description:"))
        for phrase in (
            "/forge:start",
            "work through the queue",
            "keep going",
            "run the loop",
            "process the backlog",
            "change forge settings",
            "turn off <toggle>",
        ):
            self.assertIn(
                phrase, description_line,
                f"kernel description rewrite dropped trigger phrase {phrase!r}",
            )
        self.assertIn("routes to /forge:settings", description_line)

    def test_ship_overlap_parallel_fan_out_sentence_present(self):
        """Pins EARS clause 2 as amended by fg-a10901: the judges a task
        DOES take dispatch as ONE parallel batch with the verifier, and the
        done bar is unchanged (any failing verdict consumed still fails).
        The kernel's old standalone "Ship overlap" bullet was folded into
        the "Verification economics" bullet at ratification 2026-07-18."""
        kernel_content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertIn("Verification economics (fg-a10901)", kernel_content)
        self.assertIn("as ONE parallel batch", kernel_content)
        self.assertIn("still fails the task", kernel_content)

        ship_skill_content = _cached_read_text((REPO_ROOT / "skills" / "ship" / "SKILL.md"))
        self.assertIn("Ship overlap", ship_skill_content)

        workflow_content = _cached_read_text((REPO_ROOT / "workflows" / "forge-ship.md"))
        self.assertIn("Ship overlap", workflow_content)
        self.assertIn(
            "EARS-clause verification is the verifier's surface, ", workflow_content,
            "reviewer's do-not-re-verify line must become a scope "
            "instruction, not a sequencing claim, under ship overlap",
        )

    def test_verifier_agents_have_mechanical_judgment_tag_contract(self):
        for agent_file in ("forge-verifier.md", "forge-ui-verifier.md"):
            content = _cached_read_text((REPO_ROOT / "agents" / agent_file))
            self.assertIn("MECHANICAL", content)
            self.assertIn("JUDGMENT", content)
            self.assertIn(
                "MECHANICAL | JUDGMENT", content,
                f"{agent_file} output contract must show the FAIL NOTES tag "
                "as a literal MECHANICAL | JUDGMENT choice",
            )

    def test_kernel_integrate_has_mechanical_bounce_routing(self):
        """Pins EARS clause 3: MECHANICAL first bounce MAY route to
        haiku/low quoting FAIL NOTES verbatim; re-verification stays at the
        original equal-or-higher tier; second bounce always original tier."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertIn("MECHANICAL bounce routing", content)
        self.assertIn("haiku/low", content)
        self.assertIn("quoting the FAIL NOTES verbatim", content)
        self.assertIn("original\n  equal-or-higher tier", content)
        self.assertIn(
            "second bounce of any\n  kind, always redispatches at the original tier",
            content,
        )

    def test_conventions_has_canonical_latency_section(self):
        """Pins EARS clause 4: one canonical dated conventions section
        covering all four latency rules, named exactly so it can be cited."""
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "## Latency rules — ship-review overlap, mechanical bounces, "
            "batch gates, sliding-window dispatch — 2026-07",
            content,
        )
        self.assertIn("Ship-review overlap", content)
        self.assertIn("Mechanical-tagged bounces", content)
        self.assertIn("Single-gate batch INTEGRATE", content)
        self.assertIn("Sliding-window dispatch", content)
        # sliding-window rule's concurrency-window semantics
        self.assertIn("concurrency window on simultaneous spawns", content)
        # single-gate batch INTEGRATE rule's core mechanics
        self.assertIn("gate commands ONCE against the\nfully-merged result", content)
        self.assertIn("merged-gates run\nremains authoritative", content)
