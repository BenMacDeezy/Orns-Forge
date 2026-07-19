"""Doc-pin regression tests for fg-9b0303: arbitration paragraphs + map freshness
(per decision-prose-task-rule3-tests)."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_task  # noqa: E402 -- fg-a10813 bounce-2 max-shards pin
import shard_task  # noqa: E402 -- fg-a10814 manifest-key behavioral pin

# Spelled-out number words the Commands prose might use (kept generous —
# only "sixteen" is expected today, but the count will drift as commands
# are added/removed, so cover a realistic range rather than hardcoding one).
_WORD_TO_INT = {
    word: n
    for n, word in enumerate(
        [
            "zero", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve", "thirteen",
            "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen", "twenty", "twenty-one", "twenty-two", "twenty-three",
            "twenty-four", "twenty-five", "twenty-six", "twenty-seven",
            "twenty-eight", "twenty-nine", "thirty", "thirty-one",
            "thirty-two", "thirty-three", "thirty-four", "thirty-five",
            "thirty-six", "thirty-seven", "thirty-eight", "thirty-nine",
            "forty", "forty-one", "forty-two", "forty-three", "forty-four",
        ]
    )
}


class TestDocPins(unittest.TestCase):
    """Mechanical regression tests for prose decision content and map freshness."""

    def test_secure_diff_review_has_cybersecurity_arbitration(self):
        """Verify forge-secure-diff-review SKILL.md contains scope arbitration and cybersecurity.

        Also pins a semantic anchor ("diff-scoped") from the paragraph body,
        not just the heading — a heading alone is gameable (someone could
        rename/gut the paragraph under "Scope arbitration" and still pass).
        Anchoring on body text forces the actual arbitration rule to survive.
        """
        skill_path = REPO_ROOT / "skills" / "forge-secure-diff-review" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("Scope arbitration", content)
        self.assertIn("cybersecurity", content)
        self.assertIn("diff-scoped", content)

    def test_anti_generic_has_frontend_design_precedence(self):
        """Verify anti-generic-design-restraint SKILL.md contains precedence vs frontend-design.

        Also pins "vetoes" — the semantic core of the precedence rule (this
        skill only vetoes genericness, it doesn't choose direction). The
        heading alone doesn't distinguish a real precedence rule from an
        empty or reworded section; the body fragment does.
        """
        skill_path = REPO_ROOT / "skills" / "anti-generic-design-restraint" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("Precedence vs", content)
        self.assertIn("frontend-design", content)
        self.assertIn("vetoes", content)

    def test_bug_triage_has_queue_boundary(self):
        """Verify bug-triage-classification SKILL.md contains boundary vs forge:queue.

        Also pins "nothing to reproduce or classify" — the actual dividing
        line the boundary paragraph draws (task-shaped TODOs have nothing to
        reproduce, so they skip triage). Without this, the heading plus a bare
        mention of "forge:queue" elsewhere in the file could satisfy the test
        without the boundary rule itself being intact.
        """
        skill_path = REPO_ROOT / "skills" / "bug-triage-classification" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("Boundary vs", content)
        self.assertIn("forge:queue", content)
        self.assertIn("nothing to reproduce or classify", content)

    def test_map_freshness_header_is_real_commit(self):
        """Verify .forge/map/architecture.md forge-map-commit header points to a real commit."""
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = map_path.read_text(encoding="utf-8")
        match = re.search(r"forge-map-commit: ([0-9a-f]{40})", content)
        self.assertIsNotNone(match, "forge-map-commit header not found in architecture.md")

        sha = match.group(1)
        result = subprocess.run(
            ["git", "cat-file", "-t", sha],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.stdout.strip(), "commit", f"SHA {sha} is not a valid commit")

    def test_map_mentions_current_surface(self):
        """Verify architecture.md contains v0.7.1 surface mentions (case-insensitive)."""
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = map_path.read_text(encoding="utf-8").lower()
        self.assertIn("workflow", content)
        # "craft memory" or "Craft memory" -> check for both variants case-insensitive
        self.assertTrue(
            "craft memory" in content,
            "craft memory not found in architecture.md"
        )
        self.assertIn("fable", content)

    def test_map_command_count_consistent(self):
        """Verify the map's spelled-out command count, its entry-point bullet
        list, and the actual commands/*.md files all agree.

        Three independent surfaces claim to describe "how many commands
        Forge has": the Commands prose (spelled out, e.g. "Sixteen thin
        slash-command entry points"), the per-command entry-point bullet
        list (lines starting "- `/forge:"), and the real command files on
        disk. They can silently drift from each other when a command is
        added/removed and only one surface gets updated — this pin catches
        that drift instead of trusting any single surface.
        """
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = map_path.read_text(encoding="utf-8")

        prose_match = re.search(
            r"\b([A-Za-z]+(?:-[A-Za-z]+)?)\s+thin slash-command entry points",
            content,
        )
        self.assertIsNotNone(
            prose_match,
            "Commands prose ('<N> thin slash-command entry points') not found",
        )
        word = prose_match.group(1).lower()
        self.assertIn(
            word, _WORD_TO_INT,
            f"unrecognized spelled-out number {word!r} in Commands prose",
        )
        prose_count = _WORD_TO_INT[word]

        entry_bullets = re.findall(r"^- `/forge:\w+", content, re.MULTILINE)
        entry_count = len(entry_bullets)

        actual_files = list((REPO_ROOT / "commands").glob("*.md"))
        actual_count = len(actual_files)

        self.assertEqual(
            prose_count, entry_count,
            f"Commands prose says {prose_count} but the entry-point bullet "
            f"list has {entry_count} lines",
        )
        self.assertEqual(
            prose_count, actual_count,
            f"Commands prose says {prose_count} but commands/*.md has "
            f"{actual_count} files",
        )


class TestCommandSurfacePins(unittest.TestCase):
    """Doc-pins for fg-9b0302: README surface, memory read section, verify safety."""

    def test_readme_lists_all_commands(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        commands = sorted(p.stem for p in (REPO_ROOT / "commands").glob("*.md"))
        for name in commands:
            self.assertIn(name, readme,
                          f"command {name!r} missing from README")

    def test_memory_skill_has_read_section(self):
        t = (REPO_ROOT / "skills" / "memory" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Reading & searching", t)

    def test_verify_command_is_report_only(self):
        t = (REPO_ROOT / "commands" / "verify.md").read_text(encoding="utf-8")
        self.assertIn("never transitions a task", t)

    def test_status_board_single_sourced_in_queue_skill(self):
        self.assertIn("Status board",
                      (REPO_ROOT / "skills" / "queue" / "SKILL.md").read_text(encoding="utf-8"))


class TestFg9c0304Pins(unittest.TestCase):
    """Doc-pins for fg-9c0304: UI/motion agent attachments + handoff citation,
    discover onboard-first card, and command next-step pointers.

    The citation pin doubles as a regression pin for the FAIL-NOTE-1 fix
    (agents/forge-ui.md and agents/forge-animator.md previously cited
    docs/conventions.md as "UI+motion splitting", which is NOT a substring of
    the corrected "UI+motion task splitting" — the missing "task " makes this
    pin revert-red: reverting the citation fix makes these assertions fail
    again, they don't just degrade to a looser match.
    """

    def test_forge_ui_has_attached_skills_and_citation(self):
        content = (REPO_ROOT / "agents" / "forge-ui.md").read_text(encoding="utf-8")
        self.assertIn("visual-polish-and-craft", content)
        self.assertIn("webapp-visual-testing", content)
        self.assertIn("UI+motion task splitting", content)

    def test_forge_animator_has_attached_skills_and_citation(self):
        content = (REPO_ROOT / "agents" / "forge-animator.md").read_text(encoding="utf-8")
        self.assertIn("visual-polish-and-craft", content)
        self.assertIn("webapp-visual-testing", content)
        self.assertIn("UI+motion task splitting", content)

    def test_forge_ui_verifier_has_attached_skills(self):
        content = (REPO_ROOT / "agents" / "forge-ui-verifier.md").read_text(encoding="utf-8")
        self.assertIn("visual-polish-and-craft", content)
        self.assertIn("webapp-visual-testing", content)

    def test_discover_has_onboard_first_nudge(self):
        content = (REPO_ROOT / "skills" / "discover" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Onboard-first nudge", content)
        self.assertIn("Set up Forge fully first (onboard", content)
        self.assertIn("Just run discovery (minimal init)", content)

    def test_triage_command_points_to_forge_start(self):
        content = (REPO_ROOT / "commands" / "triage.md").read_text(encoding="utf-8")
        self.assertIn("/forge:start", content)

    def test_spec_command_points_to_forge_start(self):
        content = (REPO_ROOT / "commands" / "spec.md").read_text(encoding="utf-8")
        self.assertIn("/forge:start", content)


class TestFg9c0301_0302Pins(unittest.TestCase):
    """Doc-pins for fg-9c0301 (visual-polish-and-craft + design-tokens-pipeline
    reference) and fg-9c0302 (webapp-visual-testing).

    fg-9c0301's own bounce reworded four near-verbatim passages in
    visual-polish-and-craft/SKILL.md (eyebrow-everywhere, hero-metric-template,
    side-stripe-border, and the micro-copy example sentence) so the wording is
    genuinely re-derived rather than a lightly-synonym-swapped copy of the
    mined sources. Deliberately do NOT pin those passages by their new
    wording here — doing so would just re-verbatim-lock a different string
    and defeat future rewrites. Pin the stable pattern IDs instead; the prose
    around them is free to keep changing.
    """

    def test_visual_polish_has_all_nine_hard_rule_ids(self):
        """Verify every VP-01..VP-09 hard-rule ID is still present.

        Catches a rule being silently dropped, renumbered, or merged into
        another during future edits to the hard-rules section.
        """
        content = (REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for n in range(1, 10):
            self.assertIn(f"VP-{n:02d}", content, f"VP-{n:02d} missing from hard rules")

    def test_visual_polish_has_boundary_vs_anti_generic(self):
        """Verify the §6 Boundary section still draws the direction-vs-execution
        line against anti-generic-design-restraint.

        Pins "owns direction-level taste" — the actual dividing line the
        boundary paragraph draws, not just a mention of the other skill's
        name — so a future edit can't gut the boundary rule while leaving
        the cross-reference intact.
        """
        content = (REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("anti-generic-design-restraint", content)
        self.assertIn("owns direction-level taste", content)

    def test_visual_polish_has_banned_pattern_ids(self):
        """Verify the three banned-pattern IDs touched by the fg-9c0301 rewrite
        still exist by ID, independent of whatever prose currently describes
        them (the prose was rewritten once already and may be rewritten
        again; the ID is the stable contract)."""
        content = (REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("eyebrow-everywhere", content)
        self.assertIn("hero-metric-template", content)
        self.assertIn("side-stripe-border", content)

    def test_visual_polish_has_both_source_citations(self):
        """Verify both Adapted-from citations in the Sources section survive:
        pbakaus/impeccable and anthropics/skills frontend-design, each tagged
        with their actual license."""
        content = (REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("pbakaus/impeccable (Apache-2.0)", content)
        self.assertIn("anthropics/skills `frontend-design` (Apache-2.0)", content)

    def test_design_tokens_curated_palettes_reference_exists(self):
        """Verify the design-tokens-pipeline curated-palettes-and-pairings
        reference exists, cites its MIT source, and still refuses to mine the
        source's by-industry pick-list shape.

        Pins "does not mine that shape of data" — the sentence stating the
        deliberate omission — so a future edit can't quietly turn this file
        into the by-industry lookup table anti-generic-design-restraint
        exists to veto.
        """
        ref_path = (
            REPO_ROOT
            / "skills"
            / "design-tokens-pipeline"
            / "references"
            / "curated-palettes-and-pairings.md"
        )
        self.assertTrue(ref_path.exists(), "curated-palettes-and-pairings.md missing")
        content = ref_path.read_text(encoding="utf-8")
        self.assertIn("nextlevelbuilder/ui-ux-pro-max-skill (MIT)", content)
        self.assertIn("does not mine that shape of data", content)

    def test_webapp_visual_testing_has_tool_ladder(self):
        """Verify the three-tier tool ladder (browser-MCP-first,
        Playwright-second, neither-available) is intact by its actual
        heading text, plus the Apache-2.0 source citation."""
        content = (REPO_ROOT / "skills" / "webapp-visual-testing" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Browser MCP (first choice)", content)
        self.assertIn("Repo-native Playwright via Bash (second choice)", content)
        self.assertIn("Neither available.", content)
        self.assertIn("anthropics/skills webapp-testing", content)
        self.assertIn("(Apache-2.0)", content)

    def test_webapp_visual_testing_has_default_breakpoints(self):
        """Verify the 375/768/1280 default breakpoint trio survives — the
        fallback used when a task doesn't specify its own breakpoints."""
        content = (REPO_ROOT / "skills" / "webapp-visual-testing" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("375px", content)
        self.assertIn("768px", content)
        self.assertIn("1280px", content)


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

        content = map_path.read_text(encoding="utf-8")
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

        content = arch_path.read_text(encoding="utf-8")
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

        skill_content = (REPO_ROOT / "skills" / skill_dir / "SKILL.md").read_text(
            encoding="utf-8"
        )
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
        kernel_content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        queue_content = (REPO_ROOT / "skills" / "queue" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertLess(len(kernel_content), 31617)
        self.assertLess(len(queue_content), 14295)

    def test_freshness_convention_documented(self):
        """Verify docs/conventions.md documents the last-verified freshness
        convention for date-sensitive skills."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
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
            if skill_path.exists() and "last-verified" in skill_path.read_text(encoding="utf-8"):
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


class TestFg9d0101EquipPins(unittest.TestCase):
    """Doc-pins for fg-9d0101 (/forge:equip): the skill exists with its trust
    preamble and proposes-only/consent anchors, the command exists and is
    listed in the README, and the equip-vs-scout/discover/onboard/seed
    boundary section is present in conventions.md — mirrors the pin style
    used for other command+skill additions (e.g. TestFg9c0304Pins) so a
    future rewrite of the surrounding prose can't silently gut the load-
    bearing anchors this test checks for.
    """

    def test_equip_skill_has_trust_preamble(self):
        content = (REPO_ROOT / "skills" / "equip" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Trust preamble", content)
        self.assertIn(
            "untrusted iff neither `.forge/.provenance` nor `.forge/.trust-local` exists",
            content,
        )

    def test_equip_skill_has_proposes_only_consent_anchor(self):
        content = (REPO_ROOT / "skills" / "equip" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## 4. CONSENT", content)
        self.assertIn(
            "Nothing is installed, created, queued, or enabled without explicit approval",
            content,
        )

    def test_equip_skill_has_gap_classes_and_action_menu(self):
        content = (REPO_ROOT / "skills" / "equip" / "SKILL.md").read_text(encoding="utf-8")
        for cls in ("MISSING", "WEAK", "MISWIRED"):
            self.assertIn(cls, content)
        for action in ("FIND", "CREATE", "WIRE", "SKIP"):
            self.assertIn(f"**{action}**", content)

    def test_equip_command_exists(self):
        cmd_path = REPO_ROOT / "commands" / "equip.md"
        self.assertTrue(cmd_path.exists(), "commands/equip.md missing")
        content = cmd_path.read_text(encoding="utf-8")
        self.assertIn("forge:equip", content)

    def test_readme_has_equip_row(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/forge:equip", readme)

    def test_conventions_has_equip_boundary_section(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn("## Capability-gap audits (equip)", content)
        self.assertIn("decides whether and why a gap exists", content)
        self.assertIn("forge:discover", content)
        self.assertIn("forge:onboard", content)
        self.assertIn("forge:seed", content)
        self.assertIn("forge:scout", content)

    def test_equip_inventory_section_pinned(self):
        """Pins the INVENTORY section heading and evidence-only MCP fragment
        so future rewrites can't silently remove the capability inventory
        requirement or the definition that 'connected' is evidence-only."""
        content = (REPO_ROOT / "skills" / "equip" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## 1. INVENTORY", content)
        self.assertIn(
            "Evidence-only: an MCP server counts as",
            content,
        )

    def test_equip_no_charter_path_pinned(self):
        """Pins the no-charter-yet section heading and the lower-confidence
        labeling requirement so future rewrites can't drop the degraded-pass
        pathway or remove the accountability that non-charter-derived findings
        must be labeled as lower-confidence."""
        content = (REPO_ROOT / "skills" / "equip" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## No charter yet", content)
        self.assertIn(
            "in that pass clearly as **lower-confidence**",
            content,
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
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(encoding="utf-8")
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
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(encoding="utf-8")
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
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("invoke `forge:ship`; its\n  checklist governs", content)
        self.assertIn("skills/ship/SKILL.md`'s checklist, which is NORMATIVE", content)

    def test_kernel_description_trigger_phrases_survive(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(encoding="utf-8")
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
        kernel_content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Verification economics (fg-a10901)", kernel_content)
        self.assertIn("as ONE parallel batch", kernel_content)
        self.assertIn("still fails the task", kernel_content)

        ship_skill_content = (REPO_ROOT / "skills" / "ship" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Ship overlap", ship_skill_content)

        workflow_content = (REPO_ROOT / "workflows" / "forge-ship.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Ship overlap", workflow_content)
        self.assertIn(
            "EARS-clause verification is the verifier's surface, ", workflow_content,
            "reviewer's do-not-re-verify line must become a scope "
            "instruction, not a sequencing claim, under ship overlap",
        )

    def test_verifier_agents_have_mechanical_judgment_tag_contract(self):
        for agent_file in ("forge-verifier.md", "forge-ui-verifier.md"):
            content = (REPO_ROOT / "agents" / agent_file).read_text(encoding="utf-8")
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
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(encoding="utf-8")
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
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
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


class TestFg9e0103BatchWindowPins(unittest.TestCase):
    """Doc-pins for fg-9e0103 (parallel-batch INTEGRATE moves to a single
    gate run + bisect-on-failure; sliding-window dispatch replaces the wave
    barrier; both cite the canonical conventions section fg-9e0101 landed).

    Covers all 3 EARS clauses: (1) single-gate batch INTEGRATE — merge all
    worktrees one at a time conflict-checked per merge, run gates ONCE on
    the merged result, bisect per-merge in completion order only on
    failure, merged-gates-is-authoritative unchanged; (2) sliding-window
    dispatch — max-parallel-tasks is a concurrency window, surplus workers
    dispatch the moment a slot frees, .forge/ writes/merges stay serialized
    and kernel-owned; (3) both rules are cited by the conventions section's
    exact name wherever they're read.
    """

    CONVENTIONS_SECTION = (
        "Latency rules — ship-review overlap, mechanical bounces, "
        "batch gates, sliding-window dispatch — 2026-07"
    )

    def test_parallel_dispatch_has_single_gate_and_bisect_rule(self):
        content = (
            REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
        ).read_text(encoding="utf-8")
        self.assertIn("run the gate suite ONCE against the", content)
        self.assertIn("not once per task", content)
        self.assertIn(
            "bisects by re-running gates per-merge in the same completion "
            "order",
            content,
        )
        self.assertIn(
            "merged-gates run remains authoritative\n  over any per-worktree "
            "gate pass",
            content,
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertEqual(
            normalized.count(re.sub(r"\s+", " ", self.CONVENTIONS_SECTION)), 2,
            "parallel-dispatch.md must cite the canonical conventions "
            "section by exact name at both the INTEGRATE and "
            "ROUTE+DISPATCH spots",
        )

    def test_parallel_dispatch_has_sliding_window_rule(self):
        content = (
            REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Sliding-window dispatch.", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "not a hard cap on how many eligible tasks a session may "
            "eventually run", normalized,
        )
        self.assertIn(
            "dispatch each surplus task's worker the moment an "
            "in-flight worker's slot frees", normalized,
        )

    def test_kernel_gate_no_longer_has_wait_for_next_batch(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            "surplus eligible\n  tasks wait for the next batch.", content,
            "GATE's surplus sentence still contradicts the sliding-window "
            "rule (fg-9e0103)",
        )
        self.assertIn(
            "dispatch as slots free", content,
            "sliding-window dispatch behavior must be documented"
        )
        # Extract the GATE's "Parallel eligibility" section from kernel SKILL.md
        gate_match = re.search(
            r"\*\*Parallel eligibility \(wave-level\)\.\*\*.*?(?=\n###|\n## |\Z)",
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(gate_match, "GATE 'Parallel eligibility' section not found")
        gate_section = gate_match.group(0)
        self.assertNotIn(
            "batch size ≤",
            gate_section,
            "GATE 'Parallel eligibility' section must not have batch size as "
            "an eligibility condition (fg-9e0103 requirement)",
        )
        # Check parallel-dispatch.md's eligibility scope sentence
        dispatch_content = (
            REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
        ).read_text(encoding="utf-8")
        # Extract the top-of-file scope sentence (lines 1-6)
        dispatch_scope = dispatch_content.split("\n\n")[0]
        self.assertNotIn(
            "batch size ≤",
            dispatch_scope,
            "parallel-dispatch.md eligibility scope sentence must not list "
            "batch size as an eligibility condition (fg-9e0103 requirement)",
        )

    def test_forge_wave_prose_aligned_to_single_gate_bisect(self):
        content = (REPO_ROOT / "workflows" / "forge-wave.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "the kernel runs the gate suite ONCE\nagainst the fully-merged "
            "result", content,
        )
        self.assertIn("the kernel bisects by re-running gates", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(re.sub(r"\s+", " ", self.CONVENTIONS_SECTION), normalized)


class TestFg9e0201LowRiskVerifyPins(unittest.TestCase):
    """Doc-pins for fg-9e0201 (low-risk verification sub-tier): the canonical
    dated conventions section, kernel VERIFY mode-2 routing paragraph, and
    forge-verifier's ESCALATE contract addition.

    Covers all 4 EARS clauses: (1) qualification + reduced-protocol section
    exists and is cited by exact name from kernel SKILL.md; (2) ESCALATE is
    present as a third VERDICT value scoped to low-risk mode only, with
    mandatory-escalation-on-doubt language; (3) the sampling-audit rule is
    documented; (4) the disqualification list (skills/, agents/, hooks/,
    workflows/, .forge/ protocol files) and the UI-never-qualifies carve-out
    both survive verbatim enough to catch a future edit gutting them.
    """

    def test_conventions_has_low_risk_verify_section(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "## Low-risk verification (standard sub-class) — 2026-07", content
        )

    def test_conventions_low_risk_section_has_disqualification_list(self):
        """Pins the explicit disqualification list — hooks/ and workflows/
        must both appear, not just skills/ and agents/ — so a future edit
        can't quietly narrow the disqualified set."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(
            "## Low-risk verification (standard sub-class) — 2026-07"
        )[1]
        self.assertIn("hooks/", section)
        self.assertIn("workflows/", section)
        self.assertIn("skills/", section)
        self.assertIn("agents/", section)
        self.assertIn(".forge/", section)

    def test_conventions_low_risk_section_has_ui_never_qualifies(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "UI/animation tasks never qualify as low-risk verification", content
        )
        self.assertIn("output is behavioral by definition", content)

    def test_conventions_low_risk_section_has_normative_prose_disqualifier(self):
        """Pins the content-based disqualifier (fix for the leak found in
        verification: a docs/-only edit to normative protocol/trust/consent/
        verification-rule prose must NOT qualify just because it sits under
        docs/). Anchors the operative sentence plus the self-referential
        carve-out naming this section itself, so a future edit can't quietly
        drop either half."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(
            "## Low-risk verification (standard sub-class) — 2026-07"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("NORMATIVE prose never qualifies, regardless of path", normalized)
        self.assertIn(
            "a task editing this Low-risk verification section always gets "
            "full verification",
            normalized,
        )
        self.assertIn(
            "Only non-normative documentation (README files, code comments, "
            "non-normative reference data) qualifies",
            normalized,
        )

    def test_conventions_low_risk_section_has_escalate_on_doubt(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn("mandatory on doubt", content)
        self.assertIn("when uncertain, ESCALATE", content)
        self.assertIn("sampling audit", content)
        self.assertIn("low-risk\nverify: qualified", content)

    def test_conventions_low_risk_section_in_toc(self):
        """The set-compare TOC pin (tools/test_pins_conventions_toc.py)
        already catches a missing TOC entry generically; this pin nails
        down the exact bullet text for this specific section so the two
        test files agree on what "in the TOC" means for fg-9e0201."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "- Low-risk verification (standard sub-class) — 2026-07", content
        )

    def test_kernel_has_low_risk_routing_paragraph_with_exact_citation(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Low-risk verify routing", content)
        self.assertIn(
            '"Low-risk verification (standard sub-class) — 2026-07"', content
        )
        self.assertIn("VERDICT: ESCALATE", content)
        self.assertIn("sampling audit", content)

    def test_kernel_low_risk_routing_mirrors_normative_prose_disqualifier(self):
        """Pins the one-sentence mirror of the content-based disqualifier in
        the kernel's routing paragraph — it must cite the conventions
        section's rule by name rather than diverge from it, and state
        plainly that the kernel checks diff CONTENT, not just paths."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('"NORMATIVE prose never\n   qualifies"', content)
        self.assertIn(
            "the kernel checks the CONTENT of the diff, not\n   just its path",
            content,
        )

    def test_kernel_low_risk_routing_does_not_contradict_hard_rule_3(self):
        """Pins the explicit statement that this stays mode 2 — a separate
        verifier spawn — and does not contradict Hard Rule 3."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("does not contradict Hard Rule 3", content)

    def test_verifier_has_low_risk_mode_section(self):
        content = (REPO_ROOT / "agents" / "forge-verifier.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Low-risk mode", content)
        self.assertIn("mandatory on doubt", content.replace("**", ""))

    def test_verifier_output_contract_has_scoped_escalate(self):
        """Verifies ESCALATE is added as a third VERDICT value AND scoped to
        low-risk mode only, plus the ESCALATE REASON line exists."""
        content = (REPO_ROOT / "agents" / "forge-verifier.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "VERDICT: PASS | FAIL | ESCALATE   (ESCALATE valid only in low-risk mode)",
            content,
        )
        self.assertIn("ESCALATE REASON:", content)
        self.assertIn(
            "and full mode\nnever returns ESCALATE.", content,
        )


class TestFg9f0102ForgeDirPins(unittest.TestCase):
    """Doc-pins for fg-9f0102 (.forge/ layout visibility): the canonical
    README template exists and states the plugin-vs-project split, queue's
    Auto-init wires it in alongside .provenance, spec/discover each carry a
    one-line pointer to queue's rule instead of restating it, and
    /forge:status offers to backfill a missing README.md.

    Covers all 3 EARS clauses: (1) auto-init writes .forge/README.md from
    the template, explaining project vs plugin contents including the
    .forge/agents/ carve-out; (2) /forge:status offers to add a missing
    README once, never nagging twice a session; (3) the template is
    single-sourced in the queue skill's references, cited (not duplicated)
    by the other auto-init paths.
    """

    def test_template_exists_and_has_plugin_vs_project_anchor(self):
        """The canonical template exists and explicitly draws the
        plugin-vs-project line — the actual sentence a user reads, not just
        a heading — so a future edit can't quietly gut the distinction this
        task exists to state."""
        tpl_path = (
            REPO_ROOT / "skills" / "queue" / "references"
            / "forge-dir-readme-template.md"
        )
        self.assertTrue(tpl_path.exists(), "forge-dir-readme-template.md missing")
        content = tpl_path.read_text(encoding="utf-8")
        self.assertIn(
            "agents, skills, commands, and hooks are NOT in this folder",
            content,
        )
        self.assertIn("shared by all your projects", content)

    def test_template_has_project_local_agent_carveout_and_entries(self):
        """Pins the /forge:agent project-local carve-out plus a sample of
        the one-line-per-entry inventory (queue/tasks/, map/, forge.md)."""
        tpl_path = (
            REPO_ROOT / "skills" / "queue" / "references"
            / "forge-dir-readme-template.md"
        )
        content = tpl_path.read_text(encoding="utf-8")
        self.assertIn("/forge:agent", content)
        self.assertIn("`queue/tasks/`", content)
        self.assertIn("`map/`", content)
        self.assertIn("`forge.md`", content)
        self.assertIn(".trust-local", content)

    def test_queue_auto_init_wires_readme_template(self):
        """Verify queue's Auto-init writes README.md from the template
        alongside .provenance, on the same trigger, never overwriting an
        existing one — the actual wiring, not just a mention of the
        filename."""
        content = (REPO_ROOT / "skills" / "queue" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("references/forge-dir-readme-template.md", content)
        self.assertIn(
            "Never overwrite an existing `.forge/README.md`.", content
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "on that same first-ever-`.forge/` trigger, also write "
            "`.forge/README.md`",
            normalized,
        )

    def test_spec_and_discover_have_readme_pointer_lines(self):
        """spec and discover each cite queue's README rule with a one-line
        pointer rather than restating the template wiring."""
        spec_content = (REPO_ROOT / "skills" / "spec" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        discover_content = (
            REPO_ROOT / "skills" / "discover" / "SKILL.md"
        ).read_text(encoding="utf-8")

        spec_normalized = re.sub(r"\s+", " ", spec_content)
        discover_normalized = re.sub(r"\s+", " ", discover_content)

        self.assertIn(
            "It also writes `.forge/README.md` from the template on that "
            "same trigger, same rule as queue's.",
            spec_normalized,
        )
        self.assertIn(
            "It also writes `.forge/README.md` from the template on that "
            "same trigger, same rule as queue's.",
            discover_normalized,
        )
        # Neither restates the template's own filename/path — that stays
        # single-sourced in queue's Auto-init section.
        self.assertNotIn("forge-dir-readme-template.md", spec_content)
        self.assertNotIn("forge-dir-readme-template.md", discover_content)

    def test_status_command_offers_missing_readme_once(self):
        """/forge:status offers to backfill a missing README.md, pointing at
        the same canonical template, with the never-twice-a-session rule
        stated inline."""
        content = (REPO_ROOT / "commands" / "status.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "If `.forge/` exists but `.forge/README.md` doesn't, offer once",
            normalized,
        )
        self.assertIn("forge-dir-readme-template.md", normalized)
        self.assertIn("never repeat this offer twice", normalized)


class TestFg9f0101PersonaPins(unittest.TestCase):
    """Doc-pins for fg-9f0101 (agent persona display-name layer): all 19
    roster agents carry a unique `display-name:` frontmatter field, the
    canonical mapping is stated once in docs/conventions.md as a dated
    amendment (heading + TOC + amended-by + table anchor + label format +
    display-layer-only sentence), and the kernel/queue-status-board cite it.
    Extended by fg-a10802 to 20 roster agents (forge-grunt/Grud added; the
    new row is pinned in the tail "Grud routing" conventions section, not
    by editing this table).
    """

    AGENTS_DIR = REPO_ROOT / "agents"

    CANONICAL_PERSONAS = {
        "forge-worker": "Brokk",
        "forge-verifier": "Vera",
        "forge-ui-verifier": "Iris",
        "forge-reviewer": "Rook",
        "forge-security": "Aegis",
        "forge-legal": "Lex",
        "forge-architect": "Blue",
        "forge-debugger": "Hex",
        "forge-ui": "Pixel",
        "forge-animator": "Flux",
        "forge-test-writer": "Tess",
        "forge-researcher": "Sage",
        "forge-migrator": "Tern",
        "forge-scout": "Scout",
        "forge-mapper": "Atlas",
        "forge-librarian": "Page",
        "forge-spec-writer": "Quill",
        "forge-triage": "Doc",
        "forge-data": "Rune",
        "forge-grunt": "Grud",
    }

    def _agent_files(self):
        return sorted(self.AGENTS_DIR.glob("*.md"))

    def _display_name(self, path):
        content = path.read_text(encoding="utf-8")
        # Frontmatter is the block between the first two `---` lines.
        parts = content.split("---", 2)
        self.assertGreaterEqual(
            len(parts), 3, f"{path.name}: no frontmatter block found"
        )
        frontmatter = parts[1]
        m = re.search(r"^display-name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        return m.group(1) if m else None

    def test_exactly_20_roster_agents_matching_canonical_slugs(self):
        files = self._agent_files()
        self.assertEqual(len(files), 20)
        self.assertEqual(
            {f.stem for f in files}, set(self.CANONICAL_PERSONAS)
        )

    def test_every_agent_file_has_display_name(self):
        missing = [f.name for f in self._agent_files() if self._display_name(f) is None]
        self.assertEqual(missing, [], f"agent files missing display-name: {missing}")

    def test_display_names_match_canonical_mapping(self):
        found = {f.stem: self._display_name(f) for f in self._agent_files()}
        self.assertEqual(found, self.CANONICAL_PERSONAS)

    def test_display_names_are_unique(self):
        found = [self._display_name(f) for f in self._agent_files()]
        self.assertEqual(
            len(found),
            len(set(found)),
            f"duplicate persona names found: {found}",
        )

    def test_display_name_immediately_follows_name_line(self):
        """One-line diff per file: display-name sits directly after name:,
        nothing else in the agent file changes."""
        for f in self._agent_files():
            lines = f.read_text(encoding="utf-8").splitlines()
            name_idx = next(
                i for i, line in enumerate(lines) if line.startswith("name: ")
            )
            self.assertTrue(
                lines[name_idx + 1].startswith("display-name: "),
                f"{f.name}: display-name must immediately follow the name: line",
            )

    def test_conventions_has_persona_amendment_heading(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "## Dispatch display labels — persona amendment — 2026-07", content
        )

    def test_conventions_persona_amendment_in_toc(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "  - Dispatch display labels — persona amendment — 2026-07", content
        )

    def test_conventions_base_section_has_amended_by_pointer(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            '## Dispatch display labels — 2026-07\n\n'
            '> Amended by: "Dispatch display labels — persona amendment — 2026-07"',
            content,
        )

    def test_conventions_persona_table_anchor_and_full_mapping(self):
        """Table anchor (`| Slug | Persona |`) plus every one of the 19
        canonical slug->persona rows, plus örn as the orchestrator row —
        all inside the persona amendment section specifically."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        self.assertIn("| Slug | Persona |", section)
        self.assertIn("| örn |", section)
        for slug, persona in self.CANONICAL_PERSONAS.items():
            self.assertIn(f"| {slug} | {persona} |", section)

    def test_conventions_persona_section_has_label_format(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        self.assertIn("`<Persona> · <short task title>`", section)
        self.assertIn("Brokk · Fix README typo", section)

    def test_conventions_persona_section_has_display_layer_only_sentence(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("Personas are display-layer only.", normalized)
        self.assertIn(
            "a persona name never appears where a slug is load-bearing",
            normalized,
        )

    def test_conventions_orn_is_orchestrator_persona(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("örn is the orchestrator persona", normalized)
        self.assertIn("It is not backed by an `agents/*.md` file.", normalized)
        self.assertIn(
            "The kernel introduces itself as örn at the top of session "
            "reports and run charters",
            normalized,
        )

    def test_kernel_introduces_itself_as_orn(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "the session report and the run charter (SYNC, above) open "
            "with the kernel introducing itself as its **örn** persona.",
            normalized,
        )

    def test_kernel_cites_persona_amendment_for_dispatch_labels(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            'Any human-visible dispatch label leads with the agent\'s '
            'persona (`docs/conventions.md`, "Dispatch display labels — '
            'persona amendment — 2026-07")',
            normalized,
        )

    def test_queue_status_board_cites_persona_slug_format(self):
        content = (REPO_ROOT / "skills" / "queue" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("`Persona (slug)`", normalized)
        self.assertIn(
            '"Dispatch display labels — persona amendment — 2026-07"',
            normalized,
        )


class TestFg9f0103ReadmePins(unittest.TestCase):
    """Doc-pins for fg-9f0103 (product-grade README): hero logo reference,
    mermaid architecture diagram, quickstart anchor, and the full 19-persona
    roster table all survive in README.md.

    Reuses TestFg9f0101PersonaPins.CANONICAL_PERSONAS as the single source
    of truth for the 19 persona names rather than re-listing them, so the
    two pin suites can't silently drift apart.
    """

    def test_readme_has_logo_reference(self):
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("assets/logo-light.png", content)

    def test_readme_has_mermaid_architecture_diagram(self):
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("```mermaid", content)
        self.assertIn("flowchart", content)

    def test_readme_has_quickstart_anchor(self):
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/forge:onboard", content)
        self.assertIn("## Quickstart", content)

    def test_readme_has_all_20_personas(self):
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for slug, persona in TestFg9f0101PersonaPins.CANONICAL_PERSONAS.items():
            self.assertIn(persona, content, f"persona {persona!r} ({slug}) missing from README")
            self.assertIn(f"`{slug}`", content, f"slug {slug!r} missing from README")

    def test_readme_hero_is_theme_aware(self):
        """Verify the README hero uses a <picture> element with a
        prefers-color-scheme dark source, so the logo actually adapts to
        the reader's theme instead of being a single static image."""
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("<picture>", content)
        self.assertIn("prefers-color-scheme: dark", content)

    def test_readme_references_both_theme_logo_variants(self):
        """Verify both theme-variant logo files are referenced from the
        README (not just created on disk) and that both files exist."""
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("assets/logo-dark.png", content)
        self.assertIn("assets/logo-light.png", content)
        self.assertTrue((REPO_ROOT / "assets" / "logo-dark.png").exists())
        self.assertTrue((REPO_ROOT / "assets" / "logo-light.png").exists())

    def test_readme_tests_badge_uses_drift_proof_floor(self):
        """Verify the tests badge uses a floor format (e.g. "400+") rather
        than an exact count, so it doesn't silently go stale as waves add
        tests — pins the literal badge substring used in the hero.
        Floor raised 400->980 at the 2026-07-18 v0.12.0 release point."""
        content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("tests-980%2B-brightgreen", content)


class TestFgA10101TelemetryPins(unittest.TestCase):
    """Doc-pins for fg-a10101: /forge:telemetry command surface, wired into
    README + the map's count-consistency pin, plus its own NORMATIVE
    vocabulary section and skill boundary line."""

    def test_telemetry_command_and_skill_files_exist(self):
        self.assertTrue((REPO_ROOT / "commands" / "telemetry.md").exists())
        self.assertTrue((REPO_ROOT / "skills" / "telemetry" / "SKILL.md").exists())
        self.assertTrue((REPO_ROOT / "tools" / "telemetry.py").exists())

    def test_readme_lists_telemetry_command(self):
        # "20 commands" (not 19): fg-a10904 added commands/banner.md,
        # bumping the count. This pin lives in a test file, not README.md
        # itself -- fg-a10904 does not touch README (fg-a10903 owns README
        # this wave; the count is already updated there to "20 commands"),
        # it only keeps this hardcoded companion pin in sync with it.
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/forge:telemetry", readme)
        self.assertIn("20 commands", readme)

    def test_map_command_count_is_twenty(self):
        """Regression companion to test_map_command_count_consistent above:
        pins the literal spelled-out word so a future drift back to
        "nineteen" without updating the count fails here even if the
        3-way pin's arithmetic happened to still agree by coincidence.

        Bumped 19->20 by fg-a10904 (commands/banner.md added the
        `/forge:banner` entry point; this is the commands-count surface the
        task's bounce scope item 4 required fixing -- the pin lives in
        .forge/map/architecture.md, NOT README.md, so no coordination with
        fg-a10903 (README owner) was needed). Bumped 20->21 at the
        2026-07-18 map refresh (commands/update.md added /forge:update,
        fg-a10914); the sibling pin's capture regex also gained hyphen
        support, since no non-hyphenated English word for 21 exists."""
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = map_path.read_text(encoding="utf-8")
        self.assertIn("Twenty-one thin slash-command entry points", content)

    def test_conventions_has_telemetry_vocabulary_section(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn("## Telemetry vocabulary — 2026-07", content)
        self.assertIn("attempt N: dispatched", content)
        self.assertIn("attempt N verify:", content)
        self.assertIn("attempt N (bounce,", content)
        self.assertIn("MECHANICAL", content)
        self.assertIn("JUDGMENT", content)
        self.assertIn("kernel-inline", content)

    def test_telemetry_skill_has_boundary_vs_status_and_coverage_rule(self):
        content = (REPO_ROOT / "skills" / "telemetry" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Boundary vs `/forge:status`", content)
        self.assertIn("current state", content)
        self.assertIn("history across attempts", content)
        self.assertIn("Honest-coverage rule", content)
        self.assertIn("never silently dropped and never crashes", content)

    def test_telemetry_command_is_read_only(self):
        content = (REPO_ROOT / "commands" / "telemetry.md").read_text(encoding="utf-8")
        self.assertIn(
            "never writes `.forge/`, transitions a task, or\ncommits anything",
            content,
        )

    def test_skill_count_consistent(self):
        """Verify the skill count — README claim, map prose, and actual
        skill directories on disk — all agree.

        Three independent surfaces claim to describe "how many skills Forge
        has": the README prose (e.g. "42 skills"), the map's intro paragraph
        (spelled out, e.g. "Forty-two skills"), and the real skill directories
        with SKILL.md files on disk. They can silently drift from each other
        when a skill is added/removed and only one surface gets updated —
        this pin catches that drift.
        """
        # Count actual skill directories with SKILL.md files
        actual_skills = list((REPO_ROOT / "skills").glob("*/SKILL.md"))
        actual_count = len(actual_skills)

        # Parse count from README (format: "**42 skills")
        readme_content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_match = re.search(r"\*\*(\d+)\s+skills\b", readme_content)
        self.assertIsNotNone(
            readme_match,
            "README prose ('<N> skills') not found",
        )
        readme_count = int(readme_match.group(1))

        # Parse count from map prose (format: "Forty-two skills, nineteen...")
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        map_content = map_path.read_text(encoding="utf-8")
        map_match = re.search(
            r"\b([A-Za-z-]+)\s+skills,\s+twenty\s+routed\s+agents",
            map_content
        )
        self.assertIsNotNone(
            map_match,
            "Map prose ('<N> skills, twenty routed agents') not found",
        )
        word = map_match.group(1).lower()
        self.assertIn(
            word, _WORD_TO_INT,
            f"unrecognized spelled-out number {word!r} in map prose",
        )
        map_count = _WORD_TO_INT[word]

        # Assert all three agree
        self.assertEqual(
            actual_count, readme_count,
            f"Actual skills on disk: {actual_count}, but README claims {readme_count}",
        )
        self.assertEqual(
            actual_count, map_count,
            f"Actual skills on disk: {actual_count}, but map prose says {map_count}",
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
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "## Routing-tuning recommendations (Evolve analogue) — 2026-07",
            content,
        )

    def test_conventions_routing_tuning_section_in_toc(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "- Routing-tuning recommendations (Evolve analogue) — 2026-07",
            content,
        )

    def test_conventions_routing_tuning_section_has_thresholds(self):
        # Behavioral cross-check (2026-07-18 pin audit): the documented
        # thresholds must equal the real constants in tools/telemetry.py, so a
        # constant change can't silently strand the doc's numbers.
        import telemetry

        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
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
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
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
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
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
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"Routing-tuning recommendations (Evolve analogue) — 2026-07"',
            content,
        )

    def test_kernel_learn_has_never_self_apply_sentence(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "The kernel NEVER edits the ROUTE + DISPATCH table, any task's "
            "Routing record, or `forge.md` on the",
            normalized,
        )
        self.assertIn("filing the UNRATIFIED delta is the entire", normalized)

    def test_kernel_learn_has_fable_never_recommended_sentence(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`fable` is never recommended:", content)

    def test_kernel_learn_mentions_recommend_flag_and_trigger_condition(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("tools/telemetry.py --recommend`", content)
        self.assertIn("this session did protocol work", content)


class TestFgA10201VerifierFindingFilterPins(unittest.TestCase):
    """Doc-pins for fg-a10201 (Dex-style verifier-finding filter): the
    canonical dated conventions section (heading, reproduce-on-inspection
    rule, PASS-after-filter honesty sentence, telemetry-counts-it-as-FAIL
    sentence, mem-b82d19 lineage), plus kernel INTEGRATE's citing paragraph
    ahead of the MECHANICAL bounce-routing text.

    Covers all 3 EARS clauses: (1) spot-check-before-bounce with
    reproduce-on-direct-inspection and the SURVIVES/CHALLENGED/FILTERED
    per-finding outcomes; (2) PASS-after-filter recorded in the Attempt log,
    never silently; (3) the rule lives canonically in one dated conventions
    section, cited (not restated) from kernel INTEGRATE, with mem-b82d19
    named as the same discipline.
    """

    SECTION_HEADING = "## Verifier-finding filter (bounce pre-check) — 2026-07"

    def test_conventions_has_section_heading(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(self.SECTION_HEADING, content)

    def test_conventions_section_in_toc(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "- Verifier-finding filter (bounce pre-check) — 2026-07", content
        )

    def test_conventions_section_has_reproduce_on_inspection_and_outcomes(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "the claimed defect must reproduce on direct inspection",
            normalized,
        )
        self.assertIn("**SURVIVES**", normalized)
        self.assertIn("**CHALLENGED**", normalized)
        self.assertIn("**FILTERED**", normalized)
        self.assertIn("never silently dropped", normalized)
        self.assertIn(
            "A bounce dispatches only for surviving findings, quoted",
            normalized,
        )

    def test_conventions_section_has_pass_after_filter_honesty(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("PASS-after-filter", normalized)
        self.assertIn(
            "recorded in the Attempt log with the reason", normalized,
        )
        self.assertIn(
            "full filter rationale", normalized,
        )
        self.assertIn("never silently", normalized)

    def test_conventions_section_has_telemetry_counts_as_fail_sentence(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "a verifier whose\nfindings all filtered is still counted"
            .replace("\n", " "),
            normalized,
        )
        self.assertIn("counted by `tools/telemetry.py` as a FAIL", normalized)

    def test_conventions_section_names_mem_b82d19_lineage(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("mem-b82d19", normalized)
        self.assertIn(
            "the same discipline applied to verifier", normalized,
        )

    def test_kernel_cites_section_before_mechanical_bounce_routing(self):
        """The filter paragraph cites the conventions section by exact name
        and appears BEFORE the MECHANICAL bounce routing paragraph — filter
        first, then route what survives."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '"Verifier-finding filter (bounce\n  pre-check) — 2026-07"',
            content,
        )
        filter_idx = content.index("Verifier-finding filter.")
        mechanical_idx = content.index("MECHANICAL bounce routing (latency rule).")
        self.assertLess(
            filter_idx, mechanical_idx,
            "filter-before-routing anchor violated: the filter paragraph "
            "must appear before the MECHANICAL bounce routing paragraph",
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("Filter FAIL NOTES first, then route what survives", normalized)

    def test_kernel_skill_within_char_ceiling(self):
        """Sanity pin: kernel SKILL.md must stay under the 31,617-char
        ceiling established by fg-9c0305 (TestFg9c0305Pins) — this task's
        addition must be minimal-touch, not a regression back toward the
        pre-restructure size."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertLess(len(content), 31617)


class TestFgA10202GraphPins(unittest.TestCase):
    """Doc-pins for fg-a10202 (queue dependency DAG): the tool + its test
    file exist, `/forge:status --graph` is documented in commands/status.md,
    and the queue skill's Status board section offers the graph for
    multi-task waves, naming tools/queue_graph.py."""

    def test_queue_graph_tool_exists(self):
        self.assertTrue((REPO_ROOT / "tools" / "queue_graph.py").is_file())

    def test_queue_graph_test_file_exists(self):
        self.assertTrue((REPO_ROOT / "tools" / "test_queue_graph.py").is_file())

    def test_status_command_documents_graph_flag(self):
        content = (REPO_ROOT / "commands" / "status.md").read_text(encoding="utf-8")
        self.assertIn("--graph", content)
        self.assertIn("tools/queue_graph.py", content)

    def test_queue_skill_status_board_offers_graph(self):
        content = (REPO_ROOT / "skills" / "queue" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        section = content.split("## Status board")[1].split("## Timestamps")[0]
        self.assertIn("tools/queue_graph.py", section)
        self.assertIn("3+", section)


class TestFgA10203CraftBleedPins(unittest.TestCase):
    """Doc-pins for fg-a10203 (craft-memory bleed check): the canonical
    dated conventions section (heading, patterns anchor, warning-channel
    anchor), the kernel LEARN sentence citing it by exact name, and the
    char-ceiling ancestry this task had to fit under (already covered by
    test_kernel_skill_within_char_ceiling, above).
    """

    SECTION_HEADING = "## Craft-memory bleed check — 2026-07"

    def test_conventions_has_craft_bleed_section(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(self.SECTION_HEADING, content)

    def test_conventions_craft_bleed_section_in_toc(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn("  - Craft-memory bleed check — 2026-07", content)

    def test_conventions_craft_bleed_has_patterns_anchor(self):
        """Pins the craft-store-scoping rule and the hand-edited-pattern-list
        anchor -- the actual mechanism, not just the heading -- so a future
        edit can't quietly turn this into a vague description."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn(
            "parent directory named `memory` whose OWN parent is not "
            "`.forge`",
            section,
        )
        self.assertIn("canonically a hand-edited list", section)
        self.assertIn("validate_memory.CRAFT_BLEED_HANDLES", section)

    def test_conventions_craft_bleed_has_warning_channel_anchor(self):
        """Pins the warning-not-error rationale (legit cross-references
        exist) and the never-appended-to-errors / exit-code-unaffected
        guarantee, mirroring validate_task.py's pattern by name."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("Legitimate cross-references exist", normalized)
        self.assertIn(
            "never appended to the returned error list", normalized
        )
        self.assertIn("exit code is unaffected by warnings", normalized)
        self.assertIn("validate_task.py", normalized)

    def test_conventions_craft_bleed_has_learn_gate(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn("Promotion to craft memory requires resolving every "
                      "bleed\nwarning FIRST", section)

    def test_kernel_learn_cites_craft_bleed_section_by_exact_name(self):
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            '`docs/conventions.md`, "Craft-memory bleed check — 2026-07"',
            content,
        )

    def test_kernel_learn_promotion_gate_sentence_present(self):
        """Pins the LEARN-gate sentence itself: promotion requires resolving
        bleed warnings first, fix-or-keep-local, recorded in the session
        report -- not just a bare citation."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Promotion requires resolving all bleed warnings first "
            "(fix the fact or keep it project-local), recorded in the "
            "session report",
            normalized,
        )

    def test_validator_module_has_bleed_check_functions(self):
        """Sanity pin that the implementation exists where the docs say it
        does: validate_memory.py exposes the craft-store detector, the
        hand-edited handle list, and validate() accepts warnings=."""
        content = (REPO_ROOT / "tools" / "validate_memory.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("_craft_plugin_root", content)
        self.assertIn("CRAFT_BLEED_HANDLES", content)
        self.assertIn("def validate(path, warnings=None):", content)


class TestFgA10204InquestPins(unittest.TestCase):
    """Doc-pins for fg-a10204 (/forge:inquest adversarial deep-debug
    tribunal): the skill exists with its never-loop-initiated gate and
    three role contracts, the refuter's verdict bins, the judge's
    triage-routing table, the command and workflow files exist, and the
    conventions.md boundary + NORMATIVE verdict-vocabulary section survives
    alongside its TOC line. Command/skill count pins moving 18->19 are
    covered separately (TestFgA10101TelemetryPins.test_map_command_count_is_
    nineteen and test_readme_lists_telemetry_command, both updated by this
    same task) rather than re-pinned here.
    """

    def test_inquest_skill_exists_and_never_loop_initiated(self):
        skill_path = REPO_ROOT / "skills" / "inquest" / "SKILL.md"
        self.assertTrue(skill_path.exists(), "skills/inquest/SKILL.md missing")
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("NEVER loop-initiated", content)
        self.assertIn("human ask or an accepted recommendation card", content)

    def test_inquest_skill_has_charter_requirement(self):
        content = (REPO_ROOT / "skills" / "inquest" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Charter first", content)
        self.assertIn("**Scope**", content)
        self.assertIn("**Budget**", content)
        self.assertIn("**Stop conditions**", content)

    def test_inquest_skill_has_three_role_contracts(self):
        content = (REPO_ROOT / "skills" / "inquest" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("### FINDER", content)
        self.assertIn("### REFUTER", content)
        self.assertIn("### JUDGE", content)
        # FINDER: maximalist mindset + structured-finding fields
        self.assertIn("everything and anything might be a bug", content)
        self.assertIn("**Location**", content)
        self.assertIn("**Claim**", content)
        self.assertIn("**Concrete failure scenario**", content)
        self.assertIn("**Severity**", content)
        # JUDGE: weighs, never re-investigates
        self.assertIn("does not re-litigate or re-investigate", content)

    def test_inquest_skill_has_refuter_verdict_bins(self):
        """Pins the refuter's exact three-way verdict vocabulary plus the
        running-code-beats-argument rule, not just the headings."""
        content = (REPO_ROOT / "skills" / "inquest" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("**REFUTED**", content)
        self.assertIn("**CONFIRMED**", content)
        self.assertIn("**UNRESOLVED**", content)
        self.assertIn("Running code beats argument", content)
        self.assertIn(
            "outranks prose reasoning", re.sub(r"\s+", " ", content)
        )

    def test_inquest_skill_judge_routes_via_triage(self):
        """Pins the judge routing table: CONFIRMED -> forge:triage draft,
        DISMISSED -> recorded with reason, UNRESOLVED -> surfaced to human,
        and the nothing-silently-dropped guarantee."""
        content = (REPO_ROOT / "skills" / "inquest" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Routes through the `forge:triage` door", content)
        self.assertIn("Constitution rule 1", content)
        self.assertIn("Recorded with the REFUTER's reason", content)
        self.assertIn("Surfaced to the human directly", content)
        self.assertIn("Nothing silently dropped", content)

    def test_inquest_skill_has_routing_tiers_and_boundary(self):
        content = (REPO_ROOT / "skills" / "inquest" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("sonnet/high", content)
        self.assertIn(
            "equal-or-higher model tier than the FINDER it's attacking",
            content,
        )
        self.assertIn("opus/high", content)
        self.assertIn("Proportionality", content)
        self.assertIn("vs. `forge-debugger`", content)
        self.assertIn("vs. the finder pattern in report tasks", content)
        self.assertIn("vs. the verifier-finding filter", content)

    def test_inquest_command_exists(self):
        cmd_path = REPO_ROOT / "commands" / "inquest.md"
        self.assertTrue(cmd_path.exists(), "commands/inquest.md missing")
        content = cmd_path.read_text(encoding="utf-8")
        self.assertIn("forge:inquest", content)

    def test_inquest_workflow_exists(self):
        wf_path = REPO_ROOT / "workflows" / "forge-inquest.md"
        self.assertTrue(wf_path.exists(), "workflows/forge-inquest.md missing")
        content = wf_path.read_text(encoding="utf-8")
        self.assertIn("forge-inquest", content)
        self.assertIn("parallel(", content)
        self.assertIn("pipeline(", content)

    def test_conventions_has_inquest_section_and_toc_line(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Inquest tribunal — 2026-07", content)
        self.assertIn("- Inquest tribunal — 2026-07", content)

    def test_conventions_inquest_section_has_normative_verdict_vocabulary(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        section = content.split("## Inquest tribunal — 2026-07")[1]
        self.assertIn("Verdict vocabulary — NORMATIVE", section)
        self.assertIn("`REFUTED`", section)
        self.assertIn("`CONFIRMED`", section)
        self.assertIn("`UNRESOLVED`", section)
        self.assertIn("`DISMISSED`", section)

    def test_conventions_inquest_section_has_boundary(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        section = content.split("## Inquest tribunal — 2026-07")[1]
        self.assertIn("forge-debugger", section)
        self.assertIn("finder pattern in report tasks", section)
        self.assertIn("verifier-finding filter", section)


class TestFgA10206ShipFilterPins(unittest.TestCase):
    """Doc-pins for fg-a10206 (widen the verifier-finding filter to ship
    judges + Critical-security exploit bar): the amendment heading + TOC
    nesting + Amended-by pointer on the original section, the widened
    ship-judge trigger phrase, the Critical-security exploit-bar sentence
    (including the never-FILTERED fail-safe direction), the legal
    cite-check-only scope limit, and the one citing line in
    skills/ship/SKILL.md's bounce path.
    """

    SECTION_HEADING = (
        "## Ship-judge widening + Critical-security exploit bar — 2026-07-18"
    )

    def test_conventions_has_amendment_section_and_toc_nesting(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(self.SECTION_HEADING, content)
        self.assertIn(
            "  - Ship-judge widening + Critical-security exploit bar — "
            "2026-07-18",
            content,
        )

    def test_conventions_original_section_has_amended_by_pointer(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        original_idx = content.index(
            "## Verifier-finding filter (bounce pre-check) — 2026-07"
        )
        amendment_idx = content.index(self.SECTION_HEADING)
        self.assertLess(
            original_idx, amendment_idx,
            "amendment section must be tail-appended after the original",
        )
        original_section = content[original_idx:amendment_idx]
        self.assertIn(
            '> Amended by: "Ship-judge widening + Critical-security '
            'exploit bar — 2026-07-18"',
            original_section,
        )

    def test_conventions_amendment_has_widened_ship_judge_trigger(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "`forge-reviewer` returns CHANGES REQUESTED, `forge-security` "
            "returns CHANGES REQUESTED, or `forge-legal` returns "
            "BLOCK-RECOMMENDED",
            normalized,
        )
        self.assertIn("the kernel applies the SAME filter defined above", normalized)
        self.assertIn(
            "still counted by `tools/telemetry.py` as the `SHIP: FAIL` "
            "verdict of record",
            normalized,
        )

    def test_conventions_amendment_has_critical_security_exploit_bar(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "the cited location existing is insufficient for SURVIVES on "
            "its own",
            normalized,
        )
        self.assertIn(
            "the outcome is CHALLENGED, never FILTERED — fail-safe: doubt "
            "keeps a Critical alive, it never silently dies",
            normalized,
        )

    def test_conventions_amendment_has_legal_cite_check_only_scope(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "the kernel verifies ONLY that the cited source (license "
            "text, dependency manifest, third-party notice) exists and "
            "says what the finding claims it says",
            normalized,
        )
        self.assertIn(
            "The kernel never re-judges the underlying legal risk "
            "assessment itself",
            normalized,
        )

    def test_ship_skill_cites_amendment_in_bounce_path(self):
        content = (REPO_ROOT / "skills" / "ship" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            'REVIEW/SECURITY/LEGAL findings pass through the finding '
            'filter before a FAIL becomes a bounce — '
            '`docs/conventions.md`, "Ship-judge widening + '
            'Critical-security exploit bar — 2026-07-18".',
            normalized,
        )


class TestFgA10208IdleWaitPins(unittest.TestCase):
    """Doc-pins for fg-a10208 (idle-wait discipline): the canonical dated
    conventions section (heading + TOC line), its never-polls and no-op-turn
    NORMATIVE bullets, the single-scheduled-fallback-wakeup clause, and the
    kernel's one citing sentence in ROUTE + DISPATCH naming the section by
    exact name.

    The kernel char-ceiling pin already exists
    (TestFgA10201VerifierFindingFilterPins.test_kernel_skill_within_char_ceiling)
    and is intentionally not duplicated here — this task's own trim-to-fit
    work is covered by that pre-existing assertion staying green.
    """

    SECTION_HEADING = "## Idle-wait discipline — 2026-07"

    def test_conventions_has_section_heading(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(self.SECTION_HEADING, content)

    def test_conventions_section_in_toc(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn("- Idle-wait discipline — 2026-07", content)

    def test_conventions_section_has_never_polls_sentence(self):
        """Pins the exact no-polling-worker-transcripts clause, including
        the literal substring "never polls" the task contract requires."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("never polls", normalized)
        self.assertIn(
            "The kernel never polls worker transcripts turn-by-turn",
            normalized,
        )

    def test_conventions_section_has_no_op_turn_sentence(self):
        """Pins the no-op-turn behavior for a stray wakeup/hook fire that
        carries no new notification: at most one status line, no
        worker-output reads."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "ends the turn as a no-op — at most one short status line, no",
            normalized,
        )
        self.assertIn("worker-output reads", normalized)

    def test_conventions_section_has_fallback_wakeup_clause(self):
        """Pins the single-scheduled-fallback-wakeup clause (>= 20 minutes,
        harness-permitting) so a future edit can't quietly drop the hang
        safety net or loosen it into a recurring poll."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("At most ONE long fallback wakeup", normalized)
        self.assertIn(">= 20 minutes, harness-permitting", normalized)

    def test_conventions_section_names_mem_9b31c5_lineage(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn("mem-9b31c5", section)

    def test_kernel_cites_idle_wait_section_by_exact_name(self):
        """Pins the kernel's one citing sentence in ROUTE + DISPATCH, naming
        the conventions section by exact heading text."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            '`docs/conventions.md`, "Idle-wait discipline — 2026-07"',
            normalized,
        )

    def test_kernel_dispatch_counting_cites_budget_keys_amendment(self):
        """Pins fg-a10208's restored pointer on the Dispatch counting
        paragraph (ROUTE + DISPATCH, step 5): the count-is-portable /
        budget-guard-is-a-backstop-only distinction, and the exact-name
        citation of the conventions section it lives in. Bounce fix for a
        verifier finding that a prior trim deleted this distinction with no
        replacement (mem-e4a917)."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("budget-guard", normalized)
        self.assertIn(
            '`docs/conventions.md`, "Budget keys — amendment (2026-07-17)"',
            normalized,
        )


class TestFgA10207ArchitectRefuterPins(unittest.TestCase):
    """Doc-pins for fg-a10207 (architect-plan refuter): the canonical dated
    conventions section (heading + TOC line), the checklist-cited-not-
    restated anchor, the checklist-gated trigger sentence, the no-match
    proceed-as-today sentence, the irreconcilable-disagreement-to-human
    sentence, the kernel PLAN citation by exact section name, and
    forge-architect's output-contract refuted-plan note.

    Covers all 3 EARS clauses: (1) checklist-gated trigger runs ONE refuter
    pass at equal-or-higher tier attacking DECISIONS/TRADE-OFFS/BLAST
    RADIUS before decomposition, verdict handed to the kernel alongside the
    architect's OPEN QUESTIONS; (2) no match -> proceed as today, no
    refuter, no added cost; (3) irreconcilable disagreement -> both
    positions surfaced to the human, kernel never silently picks.
    """

    SECTION_HEADING = "## Architect-plan refuter — 2026-07"

    def test_conventions_has_section_heading_and_toc_line(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(self.SECTION_HEADING, content)
        self.assertIn("- Architect-plan refuter — 2026-07", content)

    def test_conventions_section_cites_checklist_not_restated(self):
        """Pins that the checklist is cited by name/location (tier-escalation
        checklist in skills/spec/SKILL.md) rather than copied into this
        section — a future edit can't quietly turn this into a stale
        duplicate of the categories already listed in skills/spec/SKILL.md."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("tier-escalation checklist", normalized)
        self.assertIn("skills/spec/SKILL.md", normalized)
        self.assertIn("never repeats those items", normalized)
        # The checklist's own category words must NOT be duplicated here.
        for word in ("auth/authz", "PII/user data", "money/payments"):
            self.assertNotIn(word, normalized)

    def test_conventions_section_has_checklist_gated_trigger_sentence(self):
        """EARS clause 1: checklist-gated trigger runs ONE refuter pass at
        equal-or-higher tier attacking DECISIONS/TRADE-OFFS/BLAST RADIUS
        before decomposition, verdict handed to the kernel alongside the
        architect's own OPEN QUESTIONS."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN a `forge-architect` plan's BOUNDARIES or BLAST RADIUS "
            "touches the tier-escalation checklist, THE SYSTEM SHALL run "
            "ONE refuter pass",
            normalized,
        )
        self.assertIn("equal-or-higher model tier", normalized)
        self.assertIn(
            "attacking the plan's DECISIONS, TRADE-OFFS, and BLAST RADIUS "
            "before decomposition",
            normalized,
        )
        self.assertIn(
            "handed to the kernel alongside the architect's own OPEN "
            "QUESTIONS",
            normalized,
        )

    def test_conventions_section_has_no_match_proceeds_as_today_sentence(self):
        """EARS clause 2: no checklist match -> proceed exactly as today, no
        refuter, no added cost."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN the plan does not touch the checklist, THE SYSTEM SHALL "
            "proceed exactly as today — no refuter pass, no added cost",
            normalized,
        )

    def test_conventions_section_has_disagreement_to_human_sentence(self):
        """EARS clause 3: irreconcilable disagreement -> both positions
        surfaced to the human, kernel never silently picks a side."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN the refuter and the architect disagree irreconcilably, "
            "THE SYSTEM SHALL surface BOTH positions to the human",
            normalized,
        )
        self.assertIn("the kernel never silently picks a side", normalized)

    def test_conventions_section_has_no_finder_no_judge_scope_note(self):
        """Pins the scope-limiting sentence: this is one pass, not a full
        tribunal — no FINDER, no JUDGE role."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("One pass, not a tribunal", normalized)
        self.assertIn("no FINDER", normalized)
        self.assertIn("no JUDGE", normalized)

    def test_kernel_plan_cites_architect_refuter_section_by_exact_name(self):
        """Pins the kernel's one citing sentence in PLAN (where architect
        output is consumed), naming the conventions section by exact
        heading text."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            '`docs/conventions.md`, "Architect-plan refuter — 2026-07"',
            normalized,
        )
        self.assertIn("tier-escalation checklist", normalized)
        self.assertIn("run ONE refuter pass", normalized)

    def test_kernel_skill_within_char_ceiling(self):
        """Sanity pin: this task's addition must stay under the 31,617-char
        ceiling (same ceiling TestFgA10201VerifierFindingFilterPins and
        TestFgA10208IdleWaitPins already pin) — a duplicate assertion here
        keeps this task's own fit-under-budget claim independently checked."""
        content = (REPO_ROOT / "skills" / "kernel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertLess(len(content), 31617)

    def test_forge_architect_has_refuted_plan_output_contract_note(self):
        """Pins forge-architect's output-contract note: a plan may be
        refuted; the architect responds to the refuter exchange, never
        revises silently."""
        content = (REPO_ROOT / "agents" / "forge-architect.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            '`docs/conventions.md`, "Architect-plan refuter — 2026-07"',
            normalized,
        )
        self.assertIn(
            "respond to the refuter's challenge", normalized,
        )
        self.assertIn("never silently revise the plan", normalized)


class TestFgA10601DesignFoundationPins(unittest.TestCase):
    """Doc-pins for fg-a10601 (parallel design-foundation track): the
    `.forge/design/foundation.md` artifact format lands in
    docs/conventions.md as a dated section (with TOC entry), the
    design-direction step wires into `skills/spec/SKILL.md` at the same
    kickoff point as decomposition, the propose-2-3-directions rule and the
    same-gate presentation rule survive, the forge-ui/forge-animator
    binding lines exist, and the no-UI-no-ceremony carve-out is stated
    explicitly in both the format section and the agent contracts.

    Covers all 4 EARS clauses: (1) artifact + parallel-with-decomposition
    kickoff timing; (2) 2-3 distinct directions proposed by the design lead
    at the SAME human gate as decomposition, human picks/steers, chosen
    direction written to the file; (3) forge-ui/forge-animator spawn
    binding to the foundation, craft skills pull FROM it; (4) no UI work ->
    no forced foundation.
    """

    SECTION_HEADING = (
        "## Design foundation artifact (`.forge/design/foundation.md`) — "
        "2026-07-18"
    )

    def test_conventions_has_artifact_format_section_and_toc_entry(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(self.SECTION_HEADING, content)
        self.assertIn(
            "- Design foundation artifact (`.forge/design/foundation.md`) "
            "— 2026-07-18",
            content,
        )

    def test_conventions_artifact_section_has_frontmatter_and_body_sections(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn("| status | draft \\| approved \\| superseded |", section)
        for heading in (
            "## Visual identity",
            "## Token system",
            "## Layout language",
            "## Component patterns",
            "## Interaction personality",
            "## Candidate directions",
            "## Amendments",
        ):
            self.assertIn(heading, section)
        self.assertIn(
            "color / type / spacing / radius / shadow / motion", section
        )
        self.assertIn(
            "skills/spec/references/design-foundation-template.md", section
        )

    def test_conventions_artifact_section_has_kickoff_parallel_timing(self):
        """EARS clause 1: authored AT KICKOFF, in PARALLEL with the
        technical decomposition, never a later phase."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn(
            "established AT KICKOFF, in\nPARALLEL with the technical "
            "decomposition — never a later, bolted-on phase",
            section,
        )

    def test_conventions_artifact_section_has_same_gate_and_propose_rule(self):
        """EARS clause 2: 2-3 DISTINCT directions, SAME gate as
        decomposition, human picks/steers, chosen direction written."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("2-3 DISTINCT professional design directions", normalized)
        self.assertIn(
            "presented to the human at the SAME approval gate as the "
            "technical decomposition", normalized,
        )
        self.assertIn("the spec pipeline's one human gate", normalized)
        self.assertIn("never a separate design-approval step", normalized)
        self.assertIn("The human picks one, steers a synthesis", normalized)

    def test_conventions_artifact_section_has_no_ui_carveout(self):
        """EARS clause 4: no UI work -> no forced foundation, no ceremony."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN no project or spec has UI work, THE SYSTEM SHALL NOT "
            "create `.forge/design/foundation.md`", normalized,
        )
        self.assertIn("no ceremony where it does not apply", normalized)

    def test_conventions_artifact_section_has_binding_rule(self):
        """EARS clause 3: forge-ui/forge-animator spawn binds to the
        foundation; craft skills pull tokens/patterns FROM it."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(encoding="utf-8")
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN a `forge-ui` or `forge-animator` task dispatches in a "
            "project that has `.forge/design/foundation.md`, THE SYSTEM "
            "SHALL bind the spawn contract to it", normalized,
        )
        self.assertIn("visual-polish-and-craft", normalized)
        self.assertIn("ui-behavior-correctness", normalized)
        self.assertIn("component-system-shadcn-radix", normalized)
        self.assertIn("pull tokens/patterns FROM the foundation", normalized)

    def test_spec_skill_has_design_direction_step_wired_at_kickoff(self):
        """The design-direction step lives in skills/spec/SKILL.md,
        directly after Pre-compute decomposition (step 4) and before the
        Approval gate (step 5) — parallel with decomposition, same
        kickoff point, not a later phase."""
        content = (REPO_ROOT / "skills" / "spec" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("### Design direction (UI work only)", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Runs at the same kickoff point, in PARALLEL with the "
            "decomposition above", normalized,
        )
        self.assertIn("2-3 DISTINCT professional design directions", normalized)
        self.assertIn(
            "Design foundation artifact (`.forge/design/foundation.md`) "
            "— 2026-07-18",
            normalized,
        )
        # The subsection sits between step 4's own heading and step 5's.
        idx_step4 = content.index("## 4. Pre-compute decomposition")
        idx_design = content.index("### Design direction (UI work only)")
        idx_step5 = content.index("## 5. Approval gate")
        self.assertTrue(idx_step4 < idx_design < idx_step5)

    def test_spec_skill_approval_gate_presents_directions_at_same_gate(self):
        """EARS clause 2's same-gate presentation, expressed in the
        pipeline that actually runs the gate (not just the format doc)."""
        content = (REPO_ROOT / "skills" / "spec" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "present them at this SAME gate, alongside the spec body and "
            "decomposition", normalized,
        )
        self.assertIn("never a separate design-approval ask", normalized)
        self.assertIn(
            "Write the chosen direction into `.forge/design/foundation.md`",
            normalized,
        )

    def test_spec_skill_design_direction_has_no_ui_carveout(self):
        content = (REPO_ROOT / "skills" / "spec" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "THE SYSTEM SHALL NOT force a design foundation", normalized
        )
        self.assertIn("no ceremony where it does not apply", normalized)

    def test_forge_ui_has_foundation_binding_and_design_lead_capability(self):
        content = (REPO_ROOT / "agents" / "forge-ui.md").read_text(encoding="utf-8")
        self.assertIn("## Design-lead capability (spec kickoff)", content)
        self.assertIn("## Foundation binding", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("2-3 DISTINCT professional design directions", normalized)
        self.assertIn(
            "THE SYSTEM SHALL bind this task to it", normalized,
        )
        self.assertIn("pull tokens/patterns FROM the foundation", normalized)
        # ui-behavior-correctness is pinned to a single occurrence elsewhere
        # in this file (tools/test_pins_ui_behavior.py); the binding
        # paragraph must not repeat the literal skill name, only its craft
        # (overlay/dismissal discipline) — assert the count stays exactly
        # one so this pin and that one can never silently drift apart.
        self.assertEqual(content.count("ui-behavior-correctness"), 1)

    def test_forge_animator_has_one_line_foundation_binding(self):
        """forge-animator.md gets exactly ONE added line for the binding
        invariant — pin the line's presence and that it's a single bullet
        under Rules, not a whole new section."""
        content = (REPO_ROOT / "agents" / "forge-animator.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "pull motion tokens/patterns FROM it, same binding as "
            "`forge-ui`",
            content,
        )
        # Single-line invariant: no new "## " section heading was added.
        self.assertNotIn("## Foundation binding", content)

    def test_design_foundation_seed_template_exists(self):
        tpl_path = (
            REPO_ROOT / "skills" / "spec" / "references"
            / "design-foundation-template.md"
        )
        self.assertTrue(tpl_path.exists(), "design-foundation-template.md missing")
        content = tpl_path.read_text(encoding="utf-8")
        for heading in (
            "## Visual identity",
            "## Token system",
            "## Layout language",
            "## Component patterns",
            "## Interaction personality",
            "## Candidate directions",
            "## Amendments",
        ):
            self.assertIn(heading, content)


class TestFgA10602IrisDesignConformancePins(unittest.TestCase):
    """Doc-pins for fg-a10602 (Iris design-conformance check): extends
    `agents/forge-ui-verifier.md`'s output contract so a foundation-exists
    verify checks conformance through the normal verdict + finding-filter
    path, a no-foundation verify neither hard-fails nor silent-passes but
    elevates 2-3 proposed directions to the human, and the whole thing stays
    proportionate — elevate/propose, no bounce-loop on subjective taste,
    human's chosen direction is the arbiter, Iris judges application only.
    docs/conventions.md gets one APPENDED dated section (with TOC entry)
    describing the elevation as a human question channel, not a bounce.

    Covers all 3 EARS clauses in fg-a10602-iris-design-conformance.md:
    (1) foundation exists -> conformance check, real finding, normal path;
    (2) no foundation -> not hard-fail, not silent-pass, elevate 2-3
    directions; (3) proportionate — elevate/propose, human direction is
    arbiter, Iris never imposes her own.
    """

    VERIFIER_PATH = REPO_ROOT / "agents" / "forge-ui-verifier.md"
    CONVENTIONS_SECTION_HEADING = (
        "## Design-conformance elevation (Iris) — 2026-07-18"
    )

    def _verifier_text(self):
        return self.VERIFIER_PATH.read_text(encoding="utf-8")

    def _conventions_section(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(self.CONVENTIONS_SECTION_HEADING, content)
        return content.split(self.CONVENTIONS_SECTION_HEADING, 1)[1]

    # --- EARS clause 1: foundation exists -> conformance check, real
    # finding, normal verdict + finding-filter path -------------------

    def test_verifier_has_design_conformance_section(self):
        content = self._verifier_text()
        self.assertIn("## Design conformance", content)

    def test_verifier_checks_conformance_when_foundation_exists(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "WHEN the project has `.forge/design/foundation.md`", normalized
        )
        self.assertIn(
            "check the rendered output against it as part of the "
            "acceptance bar", normalized,
        )
        self.assertIn(
            "do the foundation's tokens, visual identity, and layout "
            "language actually show up", normalized,
        )

    def test_verifier_conformance_gap_is_real_finding_not_silent_pass(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "A conformance gap is a real finding — run it through the same "
            "MECHANICAL/JUDGMENT tag discipline as any other defect",
            normalized,
        )
        self.assertIn("never fold it away as a silent pass", normalized)

    def test_output_contract_has_design_conformance_field(self):
        content = self._verifier_text()
        self.assertIn(
            "DESIGN CONFORMANCE: <foundation exists → tokens/identity/"
            "layout applied vs bare defaults, findings folded into FAIL "
            "NOTES like any other defect | no foundation → see ELEVATION>",
            content,
        )

    def test_verdict_fail_list_includes_conformance_gap(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "a design-conformance gap against an established foundation, "
            "or a constitution `no` = VERDICT: FAIL", normalized,
        )

    # --- EARS clause 2: no foundation -> not hard-fail, not silent-pass,
    # elevate 2-3 directions -------------------------------------------

    def test_verifier_elevates_when_no_foundation(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("WHEN no foundation file exists", normalized)
        self.assertIn("do not hard-fail the task for it", normalized)
        self.assertIn("do not silently pass over the gap", normalized)
        self.assertIn(
            "propose 2-3 concrete design directions derived from the "
            "project's concept", normalized,
        )
        self.assertIn(
            "framed as a question for the human", normalized,
        )

    def test_output_contract_has_elevation_field(self):
        content = self._verifier_text()
        self.assertIn(
            "ELEVATION: <no foundation exists → 2-3 concrete design "
            "directions proposed from the project concept, framed as a "
            "question for the human, never a task bounce | foundation "
            "exists → n/a>",
            content,
        )

    def test_missing_foundation_never_drives_verdict_alone(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("A missing foundation never drives VERDICT on its own", normalized)
        self.assertIn(
            "A missing foundation file is never, by itself, a FAIL — it "
            "drives ELEVATION instead", normalized,
        )

    # --- EARS clause 3: proportionate — elevate/propose, no bounce-loop,
    # human direction is arbiter, Iris judges application only ---------

    def test_verifier_states_proportionality_no_bounce_loop(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Keep this proportionate: elevate and propose, never "
            "bounce-loop the task on subjective taste", normalized,
        )

    def test_verifier_states_human_direction_is_arbiter(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Once a foundation exists, the human's chosen direction is "
            "the arbiter", normalized,
        )
        self.assertIn(
            "judge only whether the shipped work APPLIES that direction",
            normalized,
        )
        self.assertIn(
            "never fail work for missing a direction of your own that no "
            "human chose", normalized,
        )

    # --- Wording-constraint guard: ui-behavior-correctness must stay a
    # single occurrence in forge-ui-verifier.md (pinned by
    # tools/test_pins_ui_behavior.py); this task must not add a second. --

    def test_ui_behavior_correctness_still_exactly_one_occurrence(self):
        content = self._verifier_text()
        self.assertEqual(content.count("ui-behavior-correctness"), 1)

    # --- Elevation surfaces as a human question channel, not a bounce --

    def test_conventions_has_toc_entry(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "- Design-conformance elevation (Iris) — 2026-07-18", content
        )

    def test_conventions_section_describes_human_question_not_bounce(self):
        section = self._conventions_section()
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "The channel is a human question, not a bounce-loop.",
            normalized,
        )
        self.assertIn(
            "it is a decision only a human can make, so the kernel "
            "surfaces Iris's proposed directions to the human the same "
            "way any other Forge decision point asks one",
            normalized,
        )
        self.assertIn(
            "ELEVATION is not a task-level defect the kernel routes back "
            "to the worker for a redo", normalized,
        )
        self.assertIn(
            "The task's own verdict and integration proceed independently "
            "of when or whether that question gets answered", normalized,
        )

    def test_conventions_section_ties_conformance_path_to_normal_verdict(self):
        section = self._conventions_section()
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "can drive VERDICT: FAIL through the normal path — no "
            "separate design-only failure mode, no silent pass",
            normalized,
        )

    def test_conventions_section_states_proportionality(self):
        section = self._conventions_section()
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "This is elevate-and-propose, never a bounce-loop on "
            "subjective taste", normalized,
        )
        self.assertIn(
            "the human's chosen direction is the sole arbiter", normalized,
        )


class TestFgA10813ShardConventionsPins(unittest.TestCase):
    """Doc-pins for fg-a10813 (T3 of the fg-a10801 sharded fan-out
    decomposition): the ONE canonical dated docs/conventions.md section
    covering the shard-by/max-shards/shard-key frontmatter fields (schema:
    fg-a10811), the shard->dispatch->merge->verify protocol, the mandatory
    worktree-per-shard isolation rule, and the #1..#N/slug-unchanged
    display convention; the shard-eligibility predicate documented as
    SEPARATE from wave eligibility with shard-by:files restricted to
    per-file-local operations; the OQ1 nesting resolution (supported by
    schema+loop, single shared window, "allowed != always-chosen"); and the
    OQ2 cmd: deferral tied to the existing "trust cannot travel" rule. Also
    pins the two refuter-reconciliation invariants: skip-per-shard-verify
    tied to the existing Low-risk verification predicate (not a blanket
    mechanical exemption), and shard INTEGRATE being atomic for the task
    (inverting parallel-batch INTEGRATE).

    Covers all 4 EARS clauses of fg-a10813-shard-conventions.md.
    """

    SECTION_HEADING = "## Sharded fan-out — 2026-07-18"

    def _section(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(self.SECTION_HEADING, content)
        return content.split(self.SECTION_HEADING, 1)[1]

    def _normalized_section(self):
        return re.sub(r"\s+", " ", self._section())

    # --- EARS clause 1: one canonical section -- frontmatter fields +
    # shard->dispatch->merge->verify protocol + mandatory worktree
    # isolation + #1..#N/slug-unchanged display -------------------------

    def test_conventions_has_toc_entry(self):
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("- Sharded fan-out — 2026-07-18", content)

    def test_section_has_frontmatter_fields(self):
        section = self._section()
        self.assertIn("`shard-by`", section)
        self.assertIn("`max-shards`", section)
        self.assertIn("`shard-key`", section)

    def test_section_has_shard_dispatch_merge_verify_protocol_heading(self):
        section = self._section()
        self.assertIn(
            "### Shard → dispatch → merge → verify protocol", section
        )

    def test_section_states_worktree_isolation_mandatory(self):
        normalized = self._normalized_section()
        self.assertIn(
            "### Worktree-per-shard isolation — MANDATORY", normalized
        )
        self.assertIn(
            'Every shard worker MUST dispatch under Agent-tool '
            '`isolation: "worktree"`.', normalized,
        )
        self.assertIn(
            "Parallel identical-slug workers must never share a mutating "
            "tree", normalized,
        )

    def test_section_states_display_convention(self):
        normalized = self._normalized_section()
        self.assertIn(
            "A sharded swarm displays with the dispatched slug unchanged",
            normalized,
        )
        self.assertIn("`#1..#N`", normalized)
        self.assertIn(
            "disambiguated by instance number, never by task id", normalized,
        )

    # --- EARS clause 2: shard-eligibility predicate SEPARATE from wave
    # eligibility; shard-by:files restricted to per-file-local ops -------

    def test_section_states_wave_eligibility_is_mechanical(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Wave eligibility (\"Parallel dispatch (Waves amendment, "
            "2026-07-17)\", above) is a **mechanical scope-overlap check**",
            normalized,
        )

    def test_section_states_shard_eligibility_adds_conservative_judgment(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Shard eligibility is NOT the same predicate applied at a "
            "smaller grain — it ADDS a conservative judgment call on top",
            normalized,
        )
        self.assertIn("**no cross-slice dependency**", normalized)
        self.assertIn("when uncertain, do NOT shard", normalized)

    def test_section_restricts_files_sharding_to_per_file_local(self):
        normalized = self._normalized_section()
        self.assertIn(
            "`shard-by: files` is RESTRICTED in v1 to provably "
            "per-file-local operations", normalized,
        )
        self.assertIn(
            "**textually-clean-but-semantically-broken**", normalized
        )
        self.assertIn("must NOT be sharded by `files`", normalized)

    # --- EARS clause 3: nesting (OQ1) -- supported by schema+loop, single
    # shared window with >=1 slot reserved per wave task, "allowed !=
    # always-chosen" -----------------------------------------------------

    def test_section_states_nesting_supported_by_schema_and_loop(self):
        normalized = self._normalized_section()
        self.assertIn(
            "nesting is **SUPPORTED by schema and loop from day one**",
            normalized,
        )
        self.assertIn("**SAME single sliding-window cap**", normalized)
        self.assertIn(
            "**≥1 slot reserved per distinct wave task**", normalized
        )

    def test_section_states_allowed_not_always_chosen(self):
        normalized = self._normalized_section()
        self.assertIn('"Allowed ≠ always-chosen."', normalized)
        self.assertIn(
            "does not auto-select a double fan-out where the "
            "no-cross-slice-dependency judgment is unproven", normalized,
        )

    # --- EARS clause 4: cmd: shard sources DEFERRED (OQ2), tied to the
    # existing "trust cannot travel" rule ---------------------------------

    def test_section_states_cmd_deferred_to_future_task(self):
        normalized = self._normalized_section()
        self.assertIn(
            "**v1 ships `inline-list` and glob shard sources only.**",
            normalized,
        )
        self.assertIn(
            "is explicitly deferred to a future task", normalized
        )

    def test_section_ties_cmd_deferral_to_trust_cannot_travel_rule(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Trust cannot travel with content arriving after the first "
            "confirm — merges widen blast radius", normalized,
        )
        self.assertIn(
            "would dispatch on the next `continuous-loop` wave with "
            "**no re-gate**", normalized,
        )

    def test_trust_cannot_travel_phrase_is_the_real_existing_rule(self):
        """The quoted phrase must actually exist in the pre-existing Trust
        boundary section, not just be repeated in the new section -- this
        pin fails if the cited rule's own wording ever drifts out from
        under the citation."""
        content = (REPO_ROOT / "docs" / "conventions.md").read_text(
            encoding="utf-8"
        )
        boundary_heading = (
            "## Trust boundary — specs + NL scoping amendment (2026-07-17)"
        )
        self.assertIn(boundary_heading, content)
        boundary_section = content.split(boundary_heading, 1)[1].split(
            "## Sharded fan-out", 1
        )[0]
        self.assertIn(
            "Trust cannot travel with content arriving after the first "
            "confirm", boundary_section,
        )

    # --- Extra invariant: "skip per-shard EARS verify" tied to the
    # EXISTING Low-risk verification predicate, not a blanket
    # mechanical -> optional exemption ------------------------------------

    def test_section_ties_skip_verify_to_low_risk_predicate_not_blanket(self):
        normalized = self._normalized_section()
        self.assertIn(
            '"Per-shard verifier spawns are optional for mechanical work" '
            '(above) is **not** a blanket "mechanical work → optional '
            'verify" rule', normalized,
        )
        self.assertIn(
            "It is the EXISTING **Low-risk verification (standard "
            "sub-class) — 2026-07** predicate", normalized,
        )

    # --- Extra invariant: shard INTEGRATE is ATOMIC for the task,
    # inverting parallel-batch INTEGRATE -- and needs its own stub -------

    def test_section_states_shard_integrate_is_atomic(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Parallel-batch INTEGRATE is explicitly **not** all-or-nothing",
            normalized,
        )
        self.assertIn("Shard INTEGRATE **inverts** that rule", normalized)
        self.assertIn(
            "a **second** failure of the same shard blocks the **whole "
            "task**", normalized,
        )

    def test_section_notes_separate_integrate_stub_needed_but_out_of_scope(self):
        normalized = self._normalized_section()
        self.assertIn(
            "why shard dispatch needs its own INTEGRATE kernel stub",
            normalized,
        )
        self.assertIn(
            "That stub is out of scope here (T5, fg-a10816).", normalized
        )

    # --- fg-a10813 bounce-2 fix: max-shards/shard-by is DIRECTIONAL, not
    # both-or-neither -- ties the doc's claim to the real validator
    # (tools/validate_task.py), and guards against the doc re-claiming a
    # symmetric requirement that was never shipped -----------------------

    def test_max_shards_alone_is_accepted_not_rejected_by_validator(self):
        """The doc previously claimed max-shards is "both-or-neither" with
        shard-by (a symmetric/bidirectional requirement). The shipped
        validator only enforces the FORWARD direction -- shard-by present
        requires max-shards -- and accepts max-shards alone with no
        shard-by (fg-a10811's shipped shape check). This pin proves that
        directional behavior against the real validate() entrypoint, and
        separately proves the doc no longer makes the false symmetric
        claim. It must go RED if either the doc reverts to "both-or-neither"
        or the validator changes to reject max-shards-alone."""
        task_text = (
            "---\n"
            "id: fg-3fa9\n"
            "title: Add rate limiting\n"
            "state: ready\n"
            "tier: standard\n"
            "priority: 2\n"
            "spec: null\n"
            "blocks: []\n"
            "blocked-by: []\n"
            "claimed-by: null\n"
            "parallel-safe: true\n"
            "max-shards: 4\n"
            "created: 2026-07-16\n"
            "updated: 2026-07-16\n"
            "---\n\n"
            "## Acceptance criteria\n"
            "- WHEN a client exceeds 10 attempts per minute, THE SYSTEM "
            "SHALL return 429.\n\n"
            "## Execution plan\n(pending)\n\n"
            "## Routing record\n(pending)\n\n"
            "## Attempt log\n(pending)\n\n"
            "## Outcome\n(pending)\n"
        )
        self.assertNotIn("shard-by", task_text)  # no shard-by declared

        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(task_text)
            task_path = f.name

        errors = validate_task.validate(task_path)
        shard_errors = [e for e in errors if "shard" in e]
        self.assertEqual(
            shard_errors, [],
            "max-shards alone (no shard-by) must validate with zero "
            "shard-related errors -- validation is directional, not "
            f"both-or-neither. Got errors: {errors!r}",
        )

        # The doc must not claim a symmetric/bidirectional requirement.
        self.assertNotIn("both-or-neither", self._section())


class TestFgA10814ShardDispatchPins(unittest.TestCase):
    """Doc-pins for fg-a10814 (T4a): the "Shard expansion" subsection added
    to skills/kernel/references/parallel-dispatch.md, extending the shipped
    parallel-wave dispatch machinery to cover intra-task shard fan-out
    (fg-a10801). Covers all 4 EARS clauses plus a behavioral pin proving the
    {index, shard_by, items} manifest-key contract the doc pins actually
    matches what tools/shard_task.py (fg-a10812) returns -- this task is the
    first consumer of that splitter, so this is where the keys become
    contract, not just a docstring claim. Does NOT touch
    skills/kernel/SKILL.md (T5/fg-a10816's citation stubs are out of scope
    here) or merge/verify/bisect/atomicity semantics (fg-a10815/T4b).
    """

    REF_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
    )

    def _section(self):
        content = self.REF_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "## Shard expansion", content,
            "parallel-dispatch.md is missing the fg-a10814 'Shard "
            "expansion' section",
        )
        return content.split("## Shard expansion", 1)[1]

    def _normalized_section(self):
        return re.sub(r"\s+", " ", self._section())

    def test_worktree_isolation_is_mandatory(self):
        """EARS clause 1 (part): worktree isolation per shard is MANDATORY,
        identical-slug workers, under the existing wave machinery."""
        section = self._section()
        self.assertIn('isolation: "worktree"', section)
        self.assertIn("**MANDATORY**", section)
        self.assertIn("identical-slug worker", section)
        self.assertIn("EXISTING parallel-wave machinery", section)

    def test_single_shared_window_and_manifest_keys_documented(self):
        """EARS clause 1 (part): ONE shared sliding-window cap, plus the
        {index, shard_by, items} manifest-key contract is documented."""
        normalized = self._normalized_section()
        self.assertIn("ONE sliding-window concurrency cap", normalized)
        self.assertIn("no second, shard-private window", normalized)
        section = self._section()
        self.assertIn("tools/shard_task.py", section)
        for key in ("index", "shard_by", "items"):
            self.assertIn(f'"{key}"', section)

    def test_nesting_guardrail_single_window_reserved_slot(self):
        """EARS clause 2: wave siblings + all shards count against the one
        window; >=1 slot reserved per distinct wave task (OQ1)."""
        normalized = self._normalized_section()
        self.assertIn(
            "DISPATCH counts wave siblings AND all shards of every nested "
            "task against the single sliding-window cap", normalized,
        )
        self.assertIn("at least 1 slot per distinct wave", normalized)
        self.assertIn("OQ1", normalized)

    def test_attempt_log_sequential_kernel_owned_never_concurrent(self):
        """EARS clause 3 (part): kernel-owned SEQUENTIAL writes on main, one
        task file, N slice results serialized, never concurrent writers."""
        normalized = self._normalized_section()
        self.assertIn("**SEQUENTIAL**", normalized)
        self.assertIn("never concurrent writers", normalized)
        self.assertIn(
            "N shard-jobs map to one task file, never N task files",
            normalized,
        )

    def test_display_format_pinned(self):
        """EARS clause 3 (part): display shows "<Persona> #1..#N (<role>)",
        slug unchanged, instance-number disambiguation, never task-id, per
        fg-a10213."""
        normalized = self._normalized_section()
        self.assertIn('`"<Persona> #1..#N (<role>)"`', normalized)
        self.assertIn("slug itself stays unchanged", normalized)
        self.assertIn("instance number, never by task id", normalized)
        self.assertIn("fg-a10213", normalized)

    def test_sync_sweep_cited_no_new_path(self):
        """EARS clause 4: dead-session shard worktrees are collected by the
        EXISTING SYNC stale-worktree sweep, no new sweep path."""
        normalized = self._normalized_section()
        self.assertIn("EXISTING SYNC stale-worktree sweep", normalized)
        self.assertIn("no new recovery path", normalized)
        self.assertIn("does not need to distinguish the two", normalized)

    def test_forward_pointer_to_t4b_scope_boundary(self):
        """Scope boundary: exactly one forward-pointer line to fg-a10815
        (T4b) for merge/verify/bisect/atomicity semantics -- this section
        must not write those semantics itself."""
        normalized = self._normalized_section()
        self.assertIn(
            "Shards complete → see merge/verify contract in fg-a10815 (T4b)",
            normalized,
        )
        self.assertIn("bisect-on-failure", normalized)

    def test_manifest_keys_documented_match_shipped_splitter(self):
        """Behavioral pin: the {index, shard_by, items} keys pinned in the
        doc as the dispatch contract must be the REAL keys
        tools/shard_task.py (fg-a10812) returns -- red if either the doc's
        pinned keys or the module's actual output drifts.
        """
        section = self._section()
        documented_keys = {"index", "shard_by", "items"}
        for key in documented_keys:
            self.assertIn(f'"{key}"', section)

        slices = shard_task.split_shards("items", 2, ["b", "a", "c"])
        self.assertTrue(slices, "shard_task.split_shards returned no slices")
        for sl in slices:
            self.assertEqual(
                set(sl.keys()), documented_keys,
                f"shard_task.py slice keys {set(sl.keys())} != documented "
                f"{documented_keys}",
            )


class TestFgA10815ShardMergeVerifyPins(unittest.TestCase):
    """Doc-pins for fg-a10815 (T4b): the "Shard merge, verify, bisect,
    atomicity" subsection added to skills/kernel/references/parallel-
    dispatch.md -- the judgment-heavy safety half of the sharded fan-out
    epic (fg-a10801). Covers all 4 EARS clauses (merge/conflict-bounce,
    verify-model tied to the Low-risk predicate, bisect + coupling
    misattribution, INTEGRATE atomicity), the refuter revisions R-D4a,
    R-D4b, and R-D7 (fg-a10801, "Refuter verdict + kernel reconciliation"),
    the fg-a10801 EARS clause-2 reconciliation, Grud/grunt inheritance, and
    a cross-doc integrity pin against the Low-risk verification predicate
    section this task ties skip-verify to. Does NOT touch dispatch/
    expansion semantics (fg-a10814/T4a) -- that section is untouched by
    this task.
    """

    REF_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
    )
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"

    SECTION_HEADING = "## Shard merge, verify, bisect, atomicity (fg-a10815)"

    def _section(self):
        content = self.REF_PATH.read_text(encoding="utf-8")
        self.assertIn(
            self.SECTION_HEADING, content,
            "parallel-dispatch.md is missing the fg-a10815 'Shard merge, "
            "verify, bisect, atomicity' section",
        )
        return content.split(self.SECTION_HEADING, 1)[1]

    def _normalized_section(self):
        return re.sub(r"\s+", " ", self._section())

    def _low_risk_predicate_section(self):
        content = self.CONVENTIONS_PATH.read_text(encoding="utf-8")
        heading = "## Low-risk verification (standard sub-class) — 2026-07"
        self.assertIn(
            heading, content,
            "docs/conventions.md is missing the Low-risk verification "
            "predicate section this task ties skip-verify to",
        )
        rest = content.split(heading, 1)[1]
        return rest.split("\n## ", 1)[0]

    def _normalized_low_risk_predicate_section(self):
        return re.sub(r"\s+", " ", self._low_risk_predicate_section())

    def test_forward_pointer_still_resolves(self):
        """The fg-a10814 forward-pointer line ("see merge/verify contract
        in fg-a10815 (T4b)") now resolves to a real section immediately
        after it -- this task fulfills that pointer without editing it."""
        content = self.REF_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "Shards complete → see merge/verify contract in fg-a10815 (T4b)",
            content,
        )
        pointer_idx = content.index(
            "Shards complete → see merge/verify contract in fg-a10815 (T4b)"
        )
        section_idx = content.index(self.SECTION_HEADING)
        self.assertLess(
            pointer_idx, section_idx,
            "fg-a10815 section must come AFTER the fg-a10814 forward "
            "pointer that names it",
        )

    def test_merge_conflict_bounce_is_verbatim_reuse(self):
        """EARS clause 1: disjoint outputs merge with a conflict CHECK; a
        surprise conflict bounces to blocked, never speculatively resolved
        -- verbatim reuse of the wave conflict-bounce, cited by name."""
        normalized = self._normalized_section()
        self.assertIn("**verbatim reuse**", normalized)
        self.assertIn("do not resolve speculatively", normalized)
        self.assertIn("NEVER", normalized)
        self.assertIn("`blocked`", normalized)
        self.assertIn("INTEGRATE — Parallel batch", normalized)
        self.assertIn("**Merge conflict:**", normalized)

    def test_verify_model_tied_to_low_risk_predicate_not_blanket(self):
        """EARS clause 2 / R-D4a: skip-verify is tied to the EXISTING
        Low-risk predicate, never a blanket mechanical->optional rule."""
        normalized = self._normalized_section()
        self.assertIn(
            "every EARS clause pin-covered, no protocol-file touch, gates "
            "cover the change", normalized,
        )
        self.assertIn(
            "Low-risk verification (standard sub-class) — 2026-07", normalized,
        )
        self.assertIn("**NEVER** a", normalized)
        self.assertIn(
            'blanket "mechanical work → optional verify" rule', normalized,
        )

    def test_gates_green_counterexample(self):
        """EARS clause 2: the canonical rename-X->Y-deletes-X counterexample
        -- gates green because nothing references it, criterion unmet."""
        normalized = self._normalized_section()
        self.assertIn("Gates-green ≠ acceptance-met", normalized)
        self.assertIn("mechanical rename", normalized)
        self.assertIn("instead *deletes* `X`", normalized)
        self.assertIn("passes every gate green", normalized)
        self.assertIn('"rename X to Y") is unmet', normalized)

    def test_verify_mode_per_shard_or_merged_when_predicate_unmet(self):
        """EARS clause 2: when the predicate is not satisfied, an
        EARS-clause verifier runs -- per-shard for disjoint outputs, or
        once over the merged result -- with when each applies stated."""
        normalized = self._normalized_section()
        self.assertIn("not fully satisfied**, an EARS-clause verifier", normalized)
        self.assertIn("**per-shard** for disjoint outputs", normalized)
        self.assertIn("**once over the merged result**", normalized)

    def test_grud_shards_inherit_rule_explicitly(self):
        """Grud/grunt shards inherit the verify-model rule explicitly --
        no looser bar for a mechanical-tier slug (closes the D4a/D8 hole
        the parent task names)."""
        normalized = self._normalized_section()
        self.assertIn("Grud/grunt", normalized)
        self.assertIn("**inherit this rule explicitly**", normalized)
        self.assertIn("mechanical-tier slug does not", normalized)

    def test_clause2_reconciliation_modes_not_free_choice(self):
        """Reconciles fg-a10801 EARS clause 2 ("per-shard for disjoint
        outputs, or once over the merged result") against this task's
        verify model: the two options are modes selected by the Low-risk
        predicate, not a free choice."""
        normalized = self._normalized_section()
        self.assertIn(
            '"per-shard for disjoint outputs, or once over the merged '
            'result"', normalized,
        )
        self.assertIn(
            "**modes selected by the Low-risk predicate above, not a "
            "free choice**", normalized,
        )
        self.assertIn(
            "disjoint-output shard-sets **MAY** verify once-over-merged "
            "**ONLY** under the Low-risk predicate", normalized,
        )

    def test_bisect_coupling_misattribution(self):
        """EARS clause 3 / R-D4b: cross-slice coupling causes bisect to
        blame the last-merged slice; re-dispatch reproduces the failure;
        the 2nd failure blocks the WHOLE task, pointing at the slice SET."""
        normalized = self._normalized_section()
        self.assertIn("**cross-slice coupling**", normalized)
        self.assertIn("blames the **last-merged slice**", normalized)
        self.assertIn("**reproduces the failure**", normalized)
        self.assertIn("slice's **2nd failure**", normalized)
        self.assertIn("**WHOLE task blocks**", normalized)
        self.assertIn("**coupling-shaped, not slice-local**", normalized)
        self.assertIn("**slice SET**", normalized)

    def test_bisect_composes_with_eligibility_restriction(self):
        """States why coupling misattribution composes with the v1
        shard-by:files eligibility restriction (textually-clean-but-
        semantically-broken coupling is what that restriction guards)."""
        normalized = self._normalized_section()
        self.assertIn("Shard-eligibility predicate", normalized)
        self.assertIn("**textually-clean-but-semantically-broken**", normalized)
        self.assertIn("per-file-local", normalized)

    def test_atomicity_inversion_stated_explicitly(self):
        """EARS clause 4 / R-D7: shard INTEGRATE is ATOMIC for the task,
        explicitly inverting the reused parallel-batch INTEGRATE rule."""
        normalized = self._normalized_section()
        self.assertIn("a batch is not an all-or-nothing unit", normalized)
        self.assertIn("**Shard INTEGRATE inverts that rule.**", normalized)
        self.assertIn("INTEGRATE is **ATOMIC for the", normalized)
        self.assertIn(
            "whole task is done, or the whole task is blocked", normalized,
        )
        self.assertIn(
            "one deliverable in pieces", normalized,
        )

    def test_integrate_stub_must_cite_this_section(self):
        """R-D7: the kernel's new shard INTEGRATE stub (fg-a10816) must
        cite THIS section, not the batch-INTEGRATE stub, for shards."""
        normalized = self._normalized_section()
        self.assertIn("fg-a10816", normalized)
        self.assertIn("**MUST", normalized)
        self.assertIn("cite THIS section**", normalized)
        self.assertIn("not the batch-INTEGRATE stub", normalized)

    def test_low_risk_predicate_cited_verbatim_matches_conventions(self):
        """Cross-doc integrity pin (behavioral-adjacent): the Low-risk
        verification predicate bullets this section cites must actually
        exist, character-for-character, in docs/conventions.md's Low-risk
        verification section -- red if either doc's wording drifts out of
        sync with the other."""
        predicate_section = self._normalized_low_risk_predicate_section()
        our_section = self._normalized_section()

        quoted_bullets = [
            "docs/config-only, zero runtime-behavior change",
            "Every EARS clause is covered by a passing pin or regression "
            "test",
            "touches NONE of `skills/`, `agents/`, `hooks/`, `workflows/`, "
            "or `.forge/` protocol files",
        ]
        for bullet in quoted_bullets:
            self.assertIn(
                bullet, predicate_section,
                f"docs/conventions.md Low-risk verification section no "
                f"longer contains the bullet this task cites verbatim: "
                f"{bullet!r}",
            )
            self.assertIn(
                bullet, our_section,
                f"parallel-dispatch.md fg-a10815 section no longer cites "
                f"the conventions.md predicate bullet verbatim: {bullet!r}",
            )


class TestFgA10816KernelStubPins(unittest.TestCase):
    """Doc-pins for fg-a10816 (T5, final task of the fg-a10801 sharded
    fan-out epic): the THREE kernel citation stub sites
    skills/kernel/SKILL.md carries for sharding -- GATE (shard-eligibility
    predicate, docs/conventions.md "Sharded fan-out"), DISPATCH (shard
    expansion, parallel-dispatch.md fg-a10814), and the NEW INTEGRATE stub
    (R-D7: shard INTEGRATE is ATOMIC for the task, parallel-dispatch.md
    fg-a10815) -- plus the three-stub-site structural invariant, the
    pre-existing char-ceiling pin this task's additions had to fit under,
    and the len()-not-wc-bytes measurement caveat (EARS clause 2). Does NOT
    touch conventions.md or parallel-dispatch.md content (fg-a10813/814/815
    own that); this task only wires + pins the kernel-side citations.
    """

    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617

    GATE_STUB = (
        'Shard eligibility (GATE, not wave): `docs/conventions.md`, '
        '"Shard-eligibility predicate." NORMATIVE.'
    )
    DISPATCH_STUB = (
        'Shard expansion (fg-a10814): '
        '`skills/kernel/references/parallel-dispatch.md` — '
        'worktree/shard, 1 window, #N. NORMATIVE.'
    )
    INTEGRATE_STUB = (
        '- Shard INTEGRATE is ATOMIC (inverts the batch rule above): '
        '`skills/kernel/references/parallel-dispatch.md` '
        '(fg-a10815, R-D7). NORMATIVE.'
    )
    BATCH_INTEGRATE_STUB = (
        "Parallel batch — INTEGRATE is strictly sequential and "
        "kernel-owned."
    )

    def _kernel_content(self):
        return self.KERNEL_PATH.read_text(encoding="utf-8")

    def test_gate_stub_cites_shard_eligibility_predicate(self):
        """GATE stub: one line citing the shard-eligibility predicate
        (docs/conventions.md, "Sharded fan-out" section) -- eligibility is
        decided at GATE, separate from wave eligibility."""
        content = self._kernel_content()
        self.assertIn(self.GATE_STUB, content)
        gate_heading_idx = content.index("### 4. GATE")
        dispatch_heading_idx = content.index("### 5. ROUTE + DISPATCH")
        stub_idx = content.index(self.GATE_STUB)
        self.assertLess(gate_heading_idx, stub_idx)
        self.assertLess(stub_idx, dispatch_heading_idx)

    def test_dispatch_stub_cites_shard_expansion(self):
        """DISPATCH stub: one line citing the shard-expansion protocol
        (parallel-dispatch.md, fg-a10814 "Shard expansion" section) --
        worktree-per-shard, one shared window, #N display."""
        content = self._kernel_content()
        self.assertIn(self.DISPATCH_STUB, content)
        dispatch_heading_idx = content.index("### 5. ROUTE + DISPATCH")
        verify_heading_idx = content.index("### 6. VERIFY")
        stub_idx = content.index(self.DISPATCH_STUB)
        self.assertLess(dispatch_heading_idx, stub_idx)
        self.assertLess(stub_idx, verify_heading_idx)

    def test_integrate_stub_cites_fg_a10815_atomicity(self):
        """INTEGRATE stub (the NEW one, R-D7): states shard INTEGRATE is
        ATOMIC for the task and cites the fg-a10815 atomicity section --
        this cannot piggyback the batch-INTEGRATE stub because batches are
        NOT all-or-nothing while shards ARE atomic."""
        content = self._kernel_content()
        self.assertIn(self.INTEGRATE_STUB, content)
        self.assertIn("ATOMIC", self.INTEGRATE_STUB)
        self.assertIn("fg-a10815", self.INTEGRATE_STUB)
        integrate_heading_idx = content.index("### 7. INTEGRATE")
        learn_heading_idx = content.index("### 8. LEARN")
        stub_idx = content.index(self.INTEGRATE_STUB)
        self.assertLess(integrate_heading_idx, stub_idx)
        self.assertLess(stub_idx, learn_heading_idx)

    def test_three_stub_sites_all_present_and_integrate_distinct_from_batch(self):
        """Structural invariant: all three stub sites exist (GATE,
        DISPATCH, INTEGRATE), and the new shard-INTEGRATE stub is
        textually distinct from -- never a reuse of -- the pre-existing
        parallel-batch INTEGRATE stub, and sits immediately adjacent to it
        (batches are NOT all-or-nothing; shards ARE atomic -- reusing one
        stub for both would silently misstate one of them)."""
        content = self._kernel_content()
        self.assertIn(self.GATE_STUB, content)
        self.assertIn(self.DISPATCH_STUB, content)
        self.assertIn(self.BATCH_INTEGRATE_STUB, content)
        self.assertIn(self.INTEGRATE_STUB, content)
        self.assertNotEqual(self.BATCH_INTEGRATE_STUB, self.INTEGRATE_STUB)

        batch_idx = content.index(self.BATCH_INTEGRATE_STUB)
        shard_idx = content.index(self.INTEGRATE_STUB)
        self.assertLess(
            batch_idx, shard_idx,
            "the shard-INTEGRATE stub must sit AFTER the batch-INTEGRATE "
            "stub, adjacent to it, so a reader sees both semantics side "
            "by side",
        )
        between = content[batch_idx + len(self.BATCH_INTEGRATE_STUB):shard_idx]
        self.assertLess(
            len(between), 400,
            "the shard-INTEGRATE stub must be adjacent to the "
            "batch-INTEGRATE stub, not scattered elsewhere in INTEGRATE",
        )

    def test_kernel_skill_within_char_ceiling(self):
        """Char-ceiling pin (EARS clauses 1 & 4): SKILL.md must stay under
        the 31,617-char ceiling already established and pinned by
        TestFgA10201VerifierFindingFilterPins.test_kernel_skill_within_char_ceiling
        and TestFgA10208IdleWaitPins.test_kernel_skill_within_char_ceiling
        (grep 31617 -- three prior instances). This is NOT a new,
        independent ceiling number: it verifies this task's own three stub
        additions still fit under that SAME pre-existing budget, matching
        the repo's established per-task self-verification pattern for this
        invariant rather than introducing a fourth unrelated constant."""
        content = self._kernel_content()
        self.assertLessEqual(len(content), self.CHAR_CEILING)

    def test_ceiling_measured_by_len_not_wc_bytes(self):
        """EARS clause 2: the ceiling is measured with Python len() --
        character count -- never `wc -c` byte count. None of the three
        pre-existing ceiling pins (grep 31617) document WHY len() is the
        right metric; this pin does. SKILL.md's em-dashes are multibyte in
        UTF-8, so the byte count and the char count provably diverge --
        this test fails red if that divergence ever disappears (e.g. the
        multibyte characters get stripped), which is exactly the signal
        that would mean char-vs-byte stopped mattering here."""
        text = self._kernel_content()
        byte_len = len(text.encode("utf-8"))
        char_len = len(text)
        self.assertGreater(
            byte_len, char_len,
            "expected SKILL.md's UTF-8 byte length to exceed its len() "
            "char length (multibyte em-dashes etc.) -- if equal, the "
            "char-vs-byte distinction this pin documents no longer holds",
        )
        self.assertLessEqual(
            char_len, self.CHAR_CEILING,
            "the CHAR count (len(), not wc -c bytes) must clear the "
            "ceiling -- this is the pinned metric per fg-a10816 EARS "
            "clause 2",
        )




class TestFgA10802GruntPins(unittest.TestCase):
    """Doc-pins for fg-a10802 (Grud, the goblin grunt / forge-grunt): the
    new roster agent's haiku/low + no-craft-skills + refuse-on-judgment
    contract, the canonical "Grud routing" conventions section (routing
    rule, the Grud-vs-Tern boundary, verification inheritance tied to the
    Low-risk predicate -- not a blanket exemption, persona registration),
    the README roster row, the kernel ROUTE citation line + char ceiling,
    and the 19->20 count-surface bump this task rides in on.
    """

    AGENT_PATH = REPO_ROOT / "agents" / "forge-grunt.md"
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    README_PATH = REPO_ROOT / "README.md"
    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617

    GRUD_ROUTE_LINE = (
        "Zero-judgment fully-specified bulk -> forge-grunt haiku/low; "
        "boundary vs migrator: conventions 'Grud routing'. NORMATIVE."
    )

    def _agent_content(self):
        return self.AGENT_PATH.read_text(encoding="utf-8")

    def _conventions_content(self):
        return self.CONVENTIONS_PATH.read_text(encoding="utf-8")

    def _readme_content(self):
        return self.README_PATH.read_text(encoding="utf-8")

    def _kernel_content(self):
        return self.KERNEL_PATH.read_text(encoding="utf-8")

    # -- EARS clause 1: agent file, haiku/low, no craft skills, refuse-on-judgment --

    def test_agent_file_exists(self):
        self.assertTrue(self.AGENT_PATH.is_file())

    def test_agent_frontmatter_model_is_haiku(self):
        content = self._agent_content()
        frontmatter = content.split("---", 2)[1]
        m = re.search(r"^model:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "haiku")

    def test_agent_display_name_is_grud(self):
        content = self._agent_content()
        frontmatter = content.split("---", 2)[1]
        m = re.search(r"^display-name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "Grud")

    def test_agent_default_routing_is_haiku_low_always(self):
        content = self._agent_content()
        section = content.split("## Default routing")[1].split("##")[0]
        self.assertIn("haiku / low, always", section)

    def test_agent_has_no_craft_skills(self):
        content = self._agent_content()
        section = content.split("## Attached skills")[1].split("##")[0]
        self.assertIn("none", section)

    def test_agent_refuses_on_judgment_call(self):
        normalized = re.sub(r"\s+", " ", self._agent_content())
        self.assertIn("REFUSE-AND-RETURN", normalized)
        self.assertIn(
            "if the contract requires ANY judgment call", normalized
        )
        self.assertIn(
            "bounce the whole task back to the kernel unexecuted",
            normalized,
        )

    def test_agent_output_contract_has_refused_result(self):
        content = self._agent_content()
        self.assertIn("RESULT: completed | refused | blocked", content)

    def test_agent_forbidden_actions_never_touch_forge_dir(self):
        content = self._agent_content()
        section = content.split("## Forbidden actions")[1]
        self.assertIn("Never touch `.forge/`.", section)

    # -- EARS clause 4 / boundary: Grud vs Tern, quote-matched wording --

    def test_conventions_has_grud_routing_heading(self):
        content = self._conventions_content()
        self.assertIn("## Grud routing (goblin grunt) \u2014 2026-07-18", content)

    def test_conventions_grud_routing_in_toc(self):
        content = self._conventions_content()
        self.assertIn("- Grud routing (goblin grunt) \u2014 2026-07-18", content)

    def _grud_section(self):
        content = self._conventions_content()
        return content.split("## Grud routing (goblin grunt) \u2014 2026-07-18")[1]

    def test_conventions_routing_rule_present(self):
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn(
            "WHEN the kernel faces fully-specified, zero-judgment bulk "
            "work", normalized,
        )
        self.assertIn(
            "THE SYSTEM SHALL route it to `forge-grunt`, always dispatched "
            "at **haiku/low**", normalized,
        )
        self.assertIn("Grud #1..#N", normalized)

    def test_conventions_boundary_vs_migrator_stated(self):
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn(
            "Grud vs Tern (`forge-migrator`) \u2014 the boundary, stated so "
            "they never overlap", normalized,
        )
        self.assertIn("Judgment about WHAT to change", normalized)
        self.assertIn(
            "Fully specified and only executed", normalized
        )

    def test_conventions_verification_inheritance_not_a_blanket_exemption(self):
        """EARS clause 3 (verify) + the fg-a10815-inherited rule this task
        must quote-match, not paraphrase into a new blanket exemption."""
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn(
            "a mechanical-tier slug does not get a looser bar", normalized
        )
        self.assertIn(
            "never a blanket \"mechanical \u2192 optional verify\" exemption "
            "invented for this persona", normalized,
        )
        self.assertIn(
            "Skip per-shard EARS verify \u2014 tied to Low-risk verification, "
            "not a blanket exemption", normalized,
        )
        self.assertIn("Gates-green \u2260 acceptance-met", normalized)

    def test_conventions_persona_registration(self):
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn('"Grud (grunt)"', normalized)
        self.assertIn('"Grud #1..#N (grunt)"', normalized)
        self.assertIn("| forge-grunt | Grud |", self._grud_section())
        self.assertIn("20th agent", normalized)

    # -- README roster row --

    def test_readme_has_grud_roster_row(self):
        content = self._readme_content()
        self.assertIn(
            "| Grud | `forge-grunt` |", content
        )

    def test_readme_agent_count_is_twenty(self):
        # "20 commands" (not 19): fg-a10904 added commands/banner.md,
        # bumping the count. Same rule as
        # TestFgA10101TelemetryPins.test_readme_lists_telemetry_command --
        # the pin is a hardcoded companion in this test file, not README.md
        # itself, which fg-a10904 does not touch (fg-a10903 owns README
        # this wave, and already carries "20 commands").
        content = self._readme_content()
        self.assertIn("a routed roster of twenty agents", content)
        self.assertIn("**44 skills \u00b7 20 agents \u00b7 20 commands**", content)
        self.assertIn("Twenty routed agents, each spawned by the kernel", content)

    # -- Kernel ROUTE citation line + char ceiling --

    def test_kernel_has_grud_route_line(self):
        content = self._kernel_content()
        self.assertIn(self.GRUD_ROUTE_LINE, content)
        route_heading_idx = content.index("### 5. ROUTE + DISPATCH")
        verify_heading_idx = content.index("### 6. VERIFY")
        line_idx = content.index(self.GRUD_ROUTE_LINE)
        self.assertLess(route_heading_idx, line_idx)
        self.assertLess(line_idx, verify_heading_idx)

    def test_kernel_skill_within_char_ceiling(self):
        """Same pre-existing 31,617-char ceiling as the three/four prior
        instances (grep 31617) -- this task's trim-to-fit addition must
        still clear it, not regress the kernel back toward its
        pre-restructure size."""
        content = self._kernel_content()
        self.assertLessEqual(len(content), self.CHAR_CEILING)

    # -- Count surfaces say 20 --

    def test_agents_dir_has_exactly_twenty_files(self):
        files = sorted((REPO_ROOT / "agents").glob("*.md"))
        self.assertEqual(len(files), 20)


class TestFgA10901VerificationEconomicsPins(unittest.TestCase):
    """Covers fg-a10901's EARS clauses (constitution rule 3): the
    verification-economics policy prose is NORMATIVE protocol, so its
    load-bearing sentences are pinned — a future edit cannot silently drop
    a security trigger, re-serialize dispatch behind verify, or resurrect
    per-task panels without a failing test.
    """

    # The seven named Aegis triggers (docs/conventions.md, "Verification
    # economics — 2026-07-18"). Keyword fragments, not full sentences, so
    # per-file phrasing/separators may differ while the LIST cannot.
    TRIGGERS = [
        "cookie/storage write",
        "raw-HTML",
        "auth/token/",
        "form/redirect",
        "untrusted",
        "new dependency",
        "money/payment",
    ]

    @staticmethod
    def _norm(path):
        # collapse whitespace so pins survive line-wrap changes
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        return " ".join(text.split())

    def test_conventions_section_exists_and_keeps_the_floor(self):
        c = self._norm("docs/conventions.md")
        self.assertIn("## Verification economics — 2026-07-18 (fg-a10901)", c)
        self.assertIn("no task integrates UNVERIFIED", c)
        self.assertIn("gates-inline with zero spawned verifiers", c)

    def test_named_trigger_list_identical_across_all_three_surfaces(self):
        # EARS clause 3 (Aegis): conventions, the agent brief, and ship
        # step 5 must all carry every trigger — no surface may drift.
        for path in (
            "docs/conventions.md",
            "agents/forge-security.md",
            "skills/ship/SKILL.md",
        ):
            content = self._norm(path)
            for trig in self.TRIGGERS:
                self.assertIn(
                    trig, content,
                    f"{path} lost the named security trigger {trig!r}",
                )
        self.assertIn("no named trigger", self._norm("skills/ship/SKILL.md"))

    def test_pipelining_gates_integrate_never_dispatch(self):
        # EARS clause 1: both the kernel stub and the reference mechanics.
        self.assertIn(
            "verification gates INTEGRATE, never the next dispatch",
            self._norm("skills/kernel/SKILL.md"),
        )
        ref = self._norm("skills/kernel/references/parallel-dispatch.md")
        self.assertIn("Build-ahead pipelining (fg-a10901)", ref)
        self.assertIn("Verification gates INTEGRATE, never the next dispatch", ref)
        self.assertIn("rework exposure is judged, not assumed clean", ref)

    def test_wave_end_failure_is_merge_gate_and_composes_with_atomic_shards(self):
        # EARS clause 5.
        c = self._norm("docs/conventions.md")
        self.assertIn("merge-gate failure", c)
        self.assertIn("re-verified, not silently shipped", c)
        self.assertIn("batch-invert rule applies", c)

    def test_delta_only_bounce_reverify(self):
        # EARS clause 6.
        self.assertIn("never a fresh full panel", self._norm("docs/conventions.md"))

    def test_single_re_derivation_owner(self):
        # EARS clause 7: policy + the reviewer consuming, not recomputing.
        self.assertIn("ONE re-derivation owner", self._norm("docs/conventions.md"))
        self.assertIn(
            "do not re-derive the whole table", self._norm("agents/forge-reviewer.md")
        )

    def test_wave_end_rook_with_full_tier_exception(self):
        # EARS clause 3 (Rook).
        c = self._norm("docs/conventions.md")
        self.assertIn("wave-end, not per-task", c)
        self.assertIn("keep the per-task reviewer", c)
        self.assertIn("wave-end by default", self._norm("agents/forge-reviewer.md"))

    def test_contract_first_decomposition_in_spec_skill(self):
        # EARS clause 2.
        self.assertIn(
            "Contract-first decomposition (fg-a10901)", self._norm("skills/spec/SKILL.md")
        )


class TestFgA10909HumanTaskNamePins(unittest.TestCase):
    """fg-a10909: every human surface leads with the task's short name, id
    trailing in parens; ids stay the only load-bearing join key."""

    @staticmethod
    def _norm(path):
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        return " ".join(text.split())

    def test_task_name_amendment_present_and_binding(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Dispatch display labels — task-name amendment — 2026-07-18", c
        )
        self.assertIn("with the id trailing in parens", c)
        self.assertIn("never a bare `fg-xxxx`", c)
        self.assertIn("Ids remain the ONLY join key", c)

    def test_version_skew_nudge_in_status_command(self):
        # fg-a10907 rider: the status surface carries the once-per-session
        # version-skew line, fail-silent.
        s = self._norm("commands/status.md")
        self.assertIn("Version-skew nudge (fg-a10907", s)
        self.assertIn("restart at the next milestone boundary", s)
        self.assertIn("stay silent (fail-silent, zero protocol weight)", s)


class TestFgA10910BoundaryMapPins(unittest.TestCase):
    """fg-a10910: spec-time file-boundary maps (cc-sdd steal-list item 2) —
    every decomposition item computed at spec step 4 carries `Boundary:`/
    `Depends:` annotations, overlapping Boundary claims resolve BEFORE the
    approval ask, an approved item's Boundary carries into the created task
    file as the source the kernel's dispatch-contract file-ownership line
    quotes, and the rule is stated once in a dated conventions section and
    pinned across the spec skill, the spec-writer draft format, and
    conventions itself."""

    @staticmethod
    def _norm(path):
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        # EARS clause 4: dated section, canonical home for the rule.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Spec-time boundary maps — 2026-07-18 (fg-a10910)", c
        )

    def test_toc_lists_the_new_section(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "- Spec-time boundary maps — 2026-07-18 (fg-a10910)", c
        )

    def test_spec_skill_annotation_requirement(self):
        # EARS clause 1: every decomposition item carries Boundary:/Depends:,
        # derived from the design's file structure plan.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn("Boundary/Depends annotations (fg-a10910)", s)
        self.assertIn(
            "carries `Boundary:` (the files/dirs it owns exclusively) and "
            "`Depends:` (the contract tasks it consumes), derived from the "
            "design's file structure plan",
            s,
        )

    def test_spec_skill_composes_with_contract_first(self):
        # EARS clause 1 rider: Boundary/Depends composes with contract-first
        # decomposition (fg-a10901) rather than duplicating it.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "the contract item that Contract-first decomposition (above) "
            "already splits out is exactly what a consumer's `Depends:` "
            "line points at",
            s,
        )

    def test_spec_skill_conflict_resolution_before_approval(self):
        # EARS clause 2: overlapping Boundary paths resolve BEFORE step 5 —
        # a blocked-by edge or a re-split, never a conflicted decomposition
        # presented for approval.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "WHEN two items claim overlapping `Boundary:` paths, resolve it "
            "BEFORE the approval ask in step 5",
            s,
        )
        self.assertIn(
            "never carry an unresolved `Boundary:` conflict into the "
            "approval gate",
            s,
        )

    def test_spec_skill_boundary_carried_into_task_file(self):
        # EARS clause 3: Boundary carries verbatim into the created task
        # file's Execution plan body, pre-seeded rather than left (pending).
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "carries verbatim into the created task file's Execution plan "
            "body",
            s,
        )
        self.assertIn(
            "is the SOURCE the kernel's dispatch-contract SCOPE",
            s,
        )

    def test_conventions_section_states_context_pack_linkage(self):
        # EARS clause 3 rider: the dated section itself states the
        # Boundary -> context-pack linkage, citing fg-a10908 (and the spawn
        # contract template) rather than restating that section's prose.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "Verification infrastructure — 2026-07-18 (fg-a10908)", c
        )
        self.assertIn(
            "is the SOURCE the kernel's dispatch-contract file-ownership "
            "line quotes",
            c,
        )
        self.assertIn(
            "skills/kernel/references/spawn-contract-template.md", c
        )

    def test_conventions_section_conflict_resolution(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "that conflict is resolved BEFORE the approval ask in step 5",
            c,
        )
        self.assertIn(
            "A decomposition with an unresolved `Boundary:` conflict is "
            "never presented for human approval",
            c,
        )

    def test_spec_writer_draft_format_carries_fields(self):
        # forge-spec-writer's draft format emits the two new fields per item.
        w = self._norm("agents/forge-spec-writer.md")
        self.assertIn(
            "Boundary: <files/dirs this item owns exclusively>", w
        )
        self.assertIn(
            "Depends: <none | contract item(s) this item consumes>", w
        )
        self.assertIn(
            "Spec-time boundary maps — 2026-07-18 (fg-a10910)", w
        )

    def test_spec_flow_pins_untouched(self):
        # This task must compose with, not disturb, the existing
        # compute-early/write-late pins in tools/test_pins_spec_flow.py —
        # sanity-check the two load-bearing sentences those pins anchor are
        # still intact after this task's step-4/step-6 edits.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "it writes NOTHING to `.forge/queue/`, now or at any point "
            "before approval.",
            s,
        )
        self.assertIn(
            "After tasks are queued, state the next command in the reply: "
            "`/forge:start`",
            s,
        )


class TestFgA10911SeverityConfidencePins(unittest.TestCase):
    """fg-a10911: P0-P3 severity + confidence per judge finding (oh-my-pi
    steal, scout three-harness audit steal-list item 3) — REQUIRED
    output-contract fields alongside (not replacing) the existing
    MECHANICAL/JUDGMENT tag and each judge's Critical/Important/Minor
    vocabulary, a coherent finding-filter amendment (never-FILTERED-on-
    spot-check-alone for P0/high, never-alone-bounces for P3/low, severity
    is the judge's call), the backward-compatible judge-yield telemetry
    extension, and the dated conventions section + TOC entry."""

    @staticmethod
    def _norm(path):
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Finding severity + confidence — 2026-07-18 (fg-a10911)", c
        )

    def test_toc_lists_the_new_section(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "- Finding severity + confidence — 2026-07-18 (fg-a10911)", c
        )

    def test_output_contract_fields_pinned_in_forge_verifier(self):
        v = self._norm("agents/forge-verifier.md")
        self.assertIn(
            "FAIL NOTES: <if FAIL: P0|P1|P2|P3 confidence: "
            "high|medium|low — MECHANICAL | JUDGMENT — precisely what the "
            "worker must change — or omit>",
            v,
        )

    def test_output_contract_fields_pinned_in_forge_reviewer(self):
        r = self._norm("agents/forge-reviewer.md")
        self.assertIn(
            "- [Critical|Important|Minor] P0|P1|P2|P3 confidence: "
            "high|medium|low — <file:line> — <defect> — <failure scenario: "
            "how it breaks>",
            r,
        )

    def test_output_contract_fields_pinned_in_forge_security(self):
        s = self._norm("agents/forge-security.md")
        self.assertIn(
            "- [Critical|Important|Minor] P0|P1|P2|P3 confidence: "
            "high|medium|low — <file:line> — <vulnerability> — <exploit "
            "scenario>",
            s,
        )

    def test_never_filtered_on_spot_check_alone_rule(self):
        # EARS clause 2 (a): P0/high is never FILTERED on a spot-check
        # alone -- it gets a real re-check first.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "P0/high is never FILTERED on a spot-check alone", c
        )
        self.assertIn(
            "the kernel must complete a REAL re-check first", c
        )
        self.assertIn(
            "when the re-check is inconclusive, the outcome is CHALLENGED, "
            "never FILTERED", c,
        )

    def test_p3_low_never_alone_bounces_rule(self):
        # EARS clause 2 (b): P3/low findings never alone cause a bounce --
        # crisp rule stated with the exact disjunct.
        c = self._norm("docs/conventions.md")
        self.assertIn("P3/low never alone bounces", c)
        self.assertIn(
            "a bounce requires at least one SURVIVING finding that is "
            "EITHER severity `P0`, `P1`, or `P2` (any confidence), OR "
            "JUDGMENT-tagged with `confidence: medium` or `high` at ANY "
            "P-level",
            c,
        )

    def test_severity_is_judges_call_not_downgradable_rule(self):
        # EARS clause 2 (c): severity is the judge's call, the filter may
        # not downgrade it -- it may only FILTER with evidence.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "Severity is the judge's call; the filter never downgrades it",
            c,
        )
        self.assertIn(
            "the kernel's spot-check filter may change a finding's OUTCOME "
            "(SURVIVES/CHALLENGED/FILTERED, per the existing "
            "per-finding-outcome rules) but never its stated severity or "
            "confidence",
            c,
        )

    def test_telemetry_extension_documented_backward_compatibly(self):
        # EARS clause 3: judge-yield telemetry carries severity counts,
        # parser updated in the same change, backward compatible.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "extends BACKWARD-COMPATIBLY with an optional trailing suffix "
            "`p0=A p1=B p2=C p3=D`",
            c,
        )
        self.assertIn(
            "The base shape with no suffix still parses exactly as it "
            "always has",
            c,
        )
        self.assertIn(
            "fails the WHOLE line, which falls into the unparsed tally "
            "rather than a silent partial parse",
            c,
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
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
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
        verifier = (REPO_ROOT / "agents/forge-verifier.md").read_text(
            encoding="utf-8"
        )
        mission_idx = verifier.index("## Mission")
        reuse_idx = verifier.index("## Reuse-first (fg-a10908)")
        self.assertLess(mission_idx, reuse_idx)
        between = verifier[mission_idx:reuse_idx]
        self.assertEqual(between.count("## "), 1)

        ui_verifier = (REPO_ROOT / "agents/forge-ui-verifier.md").read_text(
            encoding="utf-8"
        )
        mission_idx = ui_verifier.index("## Mission")
        reuse_idx = ui_verifier.index("## Reuse-first (fg-a10908)")
        self.assertLess(mission_idx, reuse_idx)
        between = ui_verifier[mission_idx:reuse_idx]
        self.assertEqual(between.count("## "), 1)


class TestFgA10701DebugEscalationPins(unittest.TestCase):
    """Covers fg-a10701's EARS clauses (constitution rule 3): the
    clean-context debug escalation — one auto-dispatched Hex attempt in a
    FRESH context between the 2nd verifier FAIL and the double-bounce
    block, routed through normal (delta-scoped) re-verification, capped at
    exactly one extra attempt — is pinned across docs/conventions.md and
    skills/kernel/SKILL.md so a future edit cannot silently drop the cap,
    the fresh-context requirement, the re-verify routing, or the kernel
    citation.
    """

    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617

    @staticmethod
    def _norm(path):
        # collapse whitespace so pins survive line-wrap changes
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        # EARS clause 3: dated section, canonical home for the rule.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Clean-context debug escalation — 2026-07-18 (fg-a10701)", c
        )

    def test_toc_lists_the_new_section(self):
        # The TOC pin test enforces heading==entry; this is a direct check
        # of the same invariant scoped to this task's own section.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "- Clean-context debug escalation — 2026-07-18 (fg-a10701)", c
        )

    def test_fresh_context_requirement(self):
        # EARS clause 1: dispatch forge-debugger (Hex) in a FRESH context,
        # given the failing diff + both verifier FAIL notes, root-causing
        # from scratch rather than re-poking the same worker.
        c = self._norm("docs/conventions.md")
        self.assertIn("dispatch", c)
        self.assertIn(
            "`forge-debugger` (Hex) in a FRESH context, never the same "
            "worker re-poked with notes appended",
            c,
        )
        self.assertIn(
            "Hex's spawn contract carries the failing diff plus BOTH "
            "verifier FAIL notes as inputs",
            c,
        )
        self.assertIn("root-causes from scratch", c)
        self.assertIn("no memory of the stuck worker's prior attempts", c)

    def test_normal_verification_routing(self):
        # EARS clause 2 (fix path): equal-or-higher tier, delta-scoped
        # re-verify — never a fresh full panel.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "routes through NORMAL verification at the task's original "
            "equal-or-higher tier",
            c,
        )
        self.assertIn("delta-only bounce re-verify", c)
        self.assertIn("never a fresh full panel", c)

    def test_cannot_fix_blocks_with_postmortem_as_today(self):
        # EARS clause 2 (no-fix path): block with the postmortem exactly
        # as today.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "the kernel blocks the task with the postmortem exactly as "
            "today",
            c,
        )

    def test_one_extra_attempt_never_a_loop(self):
        # EARS clause 2 (the cap): exactly one attempt, never an infinite
        # loop — at most one Hex dispatch per task, ever.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "This escalation adds exactly one attempt, never a loop", c
        )
        self.assertIn("at most ONE Hex dispatch per task, ever", c)
        self.assertIn("never a second Hex dispatch", c)

    def test_kernel_cites_the_escalation_before_the_block(self):
        # EARS clause 3: kernel INTEGRATE carries one citing sentence,
        # placed before the double-bounce block it modifies.
        content = self._norm("skills/kernel/SKILL.md")
        self.assertIn(
            'auto-dispatch ONE clean-context Hex attempt: '
            '`docs/conventions.md`, "Clean-context debug escalation — '
            '2026-07-18 (fg-a10701)" — NORMATIVE.',
            content,
        )
        cite_idx = content.index("auto-dispatch ONE clean-context Hex attempt")
        block_idx = content.index(
            "`state: blocked`, `claimed-by: null`, and write a plain-English blocker"
        )
        self.assertLess(
            cite_idx, block_idx,
            "escalation citation must precede the double-bounce block it "
            "modifies",
        )

    def test_kernel_skill_within_char_ceiling(self):
        # Hard ceiling from the task contract: the kernel file must stay
        # under the pre-existing 31,617-char budget after displacement.
        content = self.KERNEL_PATH.read_text(encoding="utf-8")
        self.assertLessEqual(len(content), self.CHAR_CEILING)


if __name__ == "__main__":
    unittest.main()
