"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9c0305`: TestFg9c0305Pins.
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


class TestFg9c0305Pins(unittest.TestCase):
    """Doc-pins for fg-9c0305 (token-efficiency restructure): map trim +
    subsystems split, conditional kernel/queue references, and the
    freshness convention.

    Per `docs/audits/2026-07-18-sweep3-efficiency.md`, the audit's own
    stated budget for `architecture.md` is ~1-2k tokens (chars/4). This
    suite uses chars/4 as the same mechanical proxy the audit used, with a
    ceiling of 8000 chars (~2000 tokens) — the audit's own upper bound —
    so a future regression back toward the pre-fix 26,907 chars would fail
    this pin long before it got anywhere close.
    """

    MAP_ARCHITECTURE_CHAR_BUDGET = 8000  # ~2000 tokens @ chars/4

    def test_architecture_md_within_token_budget(self):
        """Verify .forge/map/architecture.md stayed within its ~1-2k token
        budget (skills/map/SKILL.md:32) after the subsystems split — the
        mechanical proxy is chars/4 against an 8000-char (~2000-token)
        ceiling, the audit's own stated upper bound.
        """
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = _cached_read_text(map_path)
        self.assertLess(
            len(content), self.MAP_ARCHITECTURE_CHAR_BUDGET,
            f"architecture.md is {len(content)} chars "
            f"(~{len(content) // 4} tokens) — over the "
            f"{self.MAP_ARCHITECTURE_CHAR_BUDGET}-char (~2000-token) budget "
            "ceiling; move deep-dive content to subsystems/*.md instead of "
            "growing this file inline.",
        )

    def test_architecture_md_subsystems_are_linked_and_exist(self):
        """Verify every `subsystems/<name>.md` link named in architecture.md
        actually exists on disk — the split must not silently dangle."""
        map_dir = REPO_ROOT / ".forge" / "map"
        arch_path = map_dir / "architecture.md"
        if not arch_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = _cached_read_text(arch_path)
        links = sorted(set(re.findall(r"`subsystems/([a-z0-9-]+\.md)`", content)))
        self.assertGreater(len(links), 0, "no subsystems/*.md links found in architecture.md")
        for name in links:
            self.assertTrue(
                (map_dir / "subsystems" / name).exists(),
                f"architecture.md links subsystems/{name} but the file is missing",
            )

    def _assert_reference_wired(self, skill_dir, reference_name, stub_phrase):
        """Shared helper: a references/<name>.md file exists, and the main
        SKILL.md contains both the reference's filename and its trigger
        stub phrase — i.e. the conditional load is actually wired, not
        just a dangling file."""
        ref_path = REPO_ROOT / "skills" / skill_dir / "references" / reference_name
        self.assertTrue(ref_path.exists(), f"{ref_path} missing")

        skill_content = _cached_read_text((REPO_ROOT / "skills" / skill_dir / "SKILL.md"))
        self.assertIn(
            f"references/{reference_name}", skill_content,
            f"skills/{skill_dir}/SKILL.md never mentions references/{reference_name}",
        )
        self.assertIn(
            stub_phrase, skill_content,
            f"skills/{skill_dir}/SKILL.md is missing the expected trigger "
            f"stub phrase {stub_phrase!r} for references/{reference_name}",
        )

    def test_kernel_trust_gate_reference_wired(self):
        self._assert_reference_wired("kernel", "trust-gate.md", "NORMATIVE")

    def test_kernel_workflow_executor_reference_wired(self):
        self._assert_reference_wired("kernel", "workflow-executor.md", "NORMATIVE")

    def test_kernel_parallel_dispatch_reference_wired(self):
        self._assert_reference_wired("kernel", "parallel-dispatch.md", "NORMATIVE")

    def test_kernel_routing_tuning_reference_wired(self):
        self._assert_reference_wired("kernel", "routing-tuning.md", "NORMATIVE")

    def test_kernel_verify_modes_reference_wired(self):
        self._assert_reference_wired("kernel", "verify-modes.md", "NORMATIVE")

    def test_kernel_new_references_state_when_to_load(self):
        """fg-b0402 EARS clause 4 guard: each of the two NEW kernel
        references (routing-tuning.md, verify-modes.md) must be cited with
        a 'read ... (NORMATIVE) when/WHEN ...'-style trigger phrase, not a
        bare pointer -- on-demand loading must state WHEN it binds."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertRegex(
            normalized,
            r"WHEN .*?read references/routing-tuning\.md \(NORMATIVE\)",
            "routing-tuning.md citation must state WHEN it loads",
        )
        self.assertRegex(
            normalized,
            r"read references/verify-modes\.md \(NORMATIVE\) when",
            "verify-modes.md citation must state WHEN it loads",
        )

    def test_queue_task_crud_reference_wired(self):
        self._assert_reference_wired("queue", "task-crud.md", "NORMATIVE")

    def test_queue_status_board_reference_wired(self):
        self._assert_reference_wired("queue", "status-board.md", "NORMATIVE")
        # The pre-existing status-board pin (TestCommandSurfacePins) already
        # checks "Status board" survives in the main file; this test adds
        # the reference-wiring half of the same guarantee.

    def test_queue_auto_capture_reference_wired(self):
        self._assert_reference_wired("queue", "auto-capture.md", "NORMATIVE")

    def test_kernel_and_queue_shrank_below_original_size(self):
        """Sanity pin: both SKILL.md mains should be meaningfully smaller
        than their pre-restructure sizes (31,617 / 14,295 chars per the
        efficiency audit), not just reorganized in place."""
        kernel_content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        queue_content = _cached_read_text((REPO_ROOT / "skills" / "queue" / "SKILL.md"))
        self.assertLess(len(kernel_content), 31617)
        self.assertLess(len(queue_content), 14295)

    def test_freshness_convention_documented(self):
        """Verify docs/conventions.md documents the last-verified freshness
        convention for date-sensitive skills."""
        content = conventions_corpus.corpus_text()
        self.assertIn("Freshness convention", content)
        self.assertIn("last-verified", content)
        self.assertIn("12 months", content)

    def test_at_least_one_frontend_skill_carries_last_verified_stamp(self):
        """Verify at least one frontend-cluster skill carries the
        last-verified stamp — the freshness convention isn't just
        documented, it's actually applied somewhere."""
        candidates = [
            "accessibility-wcag-aria", "core-web-vitals-for-ui",
            "design-tokens-pipeline", "responsive-container-queries",
            "anti-generic-design-restraint", "motion-design-principles",
            "native-motion-first", "spring-physics-and-list-animation",
            "gsap-scrolltrigger", "lottie-rive-vector-animation",
        ]
        stamped = []
        for name in candidates:
            skill_path = REPO_ROOT / "skills" / name / "SKILL.md"
            if skill_path.exists() and "last-verified" in _cached_read_text(skill_path):
                stamped.append(name)
        self.assertGreater(
            len(stamped), 0,
            "no frontend-cluster skill carries a last-verified stamp",
        )
        # All ten were stamped by fg-9c0305; assert the full set landed,
        # not just "at least one" — a stronger pin than the criterion
        # strictly requires, catching a partial-stamp regression too.
        self.assertEqual(
            len(stamped), len(candidates),
            f"expected all {len(candidates)} frontend skills stamped, got "
            f"{len(stamped)}: {stamped}",
        )
