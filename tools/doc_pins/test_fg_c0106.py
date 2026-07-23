"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0106`: TestFgC0106CodexJudgePins.
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


class TestFgC0106CodexJudgePins(unittest.TestCase):
    """Doc-pins for fg-c0106 (spec-e8a3, Phase 1 -- external judges,
    read-only): the VERIFY-step stub in skills/kernel/SKILL.md, the new
    skills/kernel/references/provider-judges.md dispatch-mechanics
    reference, and the composition point in skills/spec/SKILL.md. Every
    substring below is unique to text this task added -- never a phrase a
    sibling task (fg-c0101/fg-c0103/fg-c0112) already owns in a file this
    task's content cites but does not restate."""

    KERNEL_SKILL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )
    SPEC_SKILL_PATH = REPO_ROOT / "skills" / "spec" / "SKILL.md"

    def _kernel_skill(self):
        return _cached_read_text(self.KERNEL_SKILL_PATH)

    def _provider_judges(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def _spec_skill(self):
        return _cached_read_text(self.SPEC_SKILL_PATH)

    # -- skills/kernel/SKILL.md VERIFY-step stub --

    def test_kernel_skill_verify_stub_present(self):
        content = self._kernel_skill()
        self.assertIn(
            "- **Provider co-verifier panel-member type (fg-c0106, "
            "spec-e8a3, Phase 1).**",
            content,
        )
        self.assertIn(
            "a codex\n  judge may fill the ONE panel-ceiling slot fg-a10901 "
            "already caps above —\n  never a second, uncapped slot.",
            content,
        )
        self.assertIn(
            "Mechanics, tier resolution, and\n  graceful-degrade: "
            "`skills/kernel/references/provider-judges.md`\n  (NORMATIVE).",
            content,
        )

    # -- skills/kernel/references/provider-judges.md --

    def test_provider_judges_file_exists_with_title(self):
        content = self._provider_judges()
        self.assertIn(
            "# Provider judges — Phase 1 dispatch mechanics (reference)",
            content,
        )

    def test_panel_composition_section_present(self):
        content = self._provider_judges()
        self.assertIn("## 1. Panel-member-type composition (fg-a10901 ceiling unmoved)", content)
        self.assertIn(
            "already caps — as a\nreplacement for, or an addition alongside, "
            "`forge-verifier` within that\nsame single-slot ceiling, never a "
            "second uncapped slot on top of it.",
            content,
        )

    def test_dispatch_shape_command_present(self):
        content = self._provider_judges()
        self.assertIn(
            "codex exec --json -o <output-file> -m <model-slug> "
            "-c model_reasoning_effort=<effort> \\\n    --sandbox read-only "
            "\"<judge prompt>\"",
            content,
        )
        self.assertIn(
            "Phase 1 dispatch NEVER uses `workspace-write` or\n"
            "  `--dangerously-bypass-approvals-and-sandbox`",
            content,
        )

    def test_read_only_contract_sentence_present(self):
        content = self._provider_judges()
        self.assertIn(
            "**Read-only contract.** A Phase 1 codex judge dispatch produces a\n"
            "verdict/findings payload ONLY — it never writes to the worktree, "
            "never\nruns `git commit`/`git add`, and never invokes any codex "
            "subcommand beyond\n`exec` with the flags above.",
            content,
        )

    def test_model_ids_pinned_from_local_cache_not_training_knowledge(self):
        content = self._provider_judges()
        self.assertIn(
            "Codex CLI 0.137.0 ships NO dedicated non-interactive\n"
            "model-listing subcommand", content,
        )
        self.assertIn(
            "$CODEX_HOME/models_cache.json` (`fetched_at: 2026-07-20T18:13:05Z`,\n"
            "`client_version: 0.137.0` in the cache file read for this pin) — a\n"
            "genuine live-CLI artifact, not a value read from spec text, docs, or\n"
            "training-data recall.",
            content,
        )
        self.assertIn("- codex-tier-judgment: gpt-5.5 (model_reasoning_effort=xhigh)", content)
        self.assertIn(
            "- codex-tier-mechanical: gpt-5.4-mini (model_reasoning_effort=medium)",
            content,
        )

    def test_kernel_ruling_role_spec_review_tier_recorded(self):
        content = self._provider_judges()
        self.assertIn(
            "**KERNEL RULING — role-spec-review tier (recorded, not relitigated).**",
            content,
        )
        self.assertIn(
            "**Ruling: spec-review MAY run at\nmechanical tier; co-verifier "
            "and plan-refuter judge roles MUST resolve to\nfrontier/judgment "
            "tier.**",
            content,
        )

    def test_graceful_degrade_note_wording_present(self):
        content = self._provider_judges()
        self.assertIn(
            'e.g. "role-co-verifier: codex configured,\nbut providers is '
            'off — panel ran Claude-only").',
            content,
        )
        self.assertIn(
            "A missing or unavailable\ncodex is NEVER a reason to skip the "
            "gate entirely, and NEVER a reason to\nblock progress waiting "
            "for codex to become available",
            content,
        )

    def test_judge_yield_provider_slug_shape_documented(self):
        content = self._provider_judges()
        self.assertIn(
            "A codex judge's Attempt-log line\nuses a provider-prefixed "
            "slug, `codex:<agent-slug>`", content,
        )
        self.assertIn('`report["judge_yield_by_provider"]`', content)

    # -- skills/spec/SKILL.md composition point --

    def test_spec_skill_composition_heading_present(self):
        content = self._spec_skill()
        self.assertIn(
            "## Provider judge composition (fg-c0106, spec-e8a3, Phase 1)",
            content,
        )

    def test_spec_skill_plan_refuter_composition_sentence_present(self):
        content = self._spec_skill()
        self.assertIn(
            "WHEN the active profile's `role-plan-refuter` resolves to\n"
            "`codex`, the Architect-plan refuter second opinion\n"
            "(`docs/conventions/verification.md`, \"Architect-plan "
            "refuter\") MAY be\ndispatched to codex at its judgment tier "
            "instead of a second Claude\narchitect spawn",
            content,
        )

    def test_spec_skill_spec_review_hook_sentence_present(self):
        content = self._spec_skill()
        self.assertIn(
            "WHEN the active profile's `role-spec-review` resolves to\n"
            "`codex`, step 2's drafted spec gets an additional codex "
            "spec-review pass\nbefore step 3's clarification resolution",
            content,
        )
        self.assertIn(
            "Per the KERNEL RULING\n`provider-judges.md` records, "
            "`role-spec-review` MAY run at codex's\nmechanical tier",
            content,
        )
