"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0111`: TestFgC0111ProviderWorkerPins.
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


class TestFgC0111ProviderWorkerPins(unittest.TestCase):
    """Doc-pins for fg-c0111 (spec-e8a3, Phase 2 -- external worker
    dispatch): the new "## 7. Phase 2" section appended to
    skills/kernel/references/provider-judges.md, and the ROUTE + DISPATCH
    provider-field-routing stub in skills/kernel/SKILL.md. Every substring
    below is unique to text this task added -- never a phrase a sibling
    task (fg-c0106/fg-c0101/fg-c0112) already owns in a file this task's
    content cites but does not restate."""

    KERNEL_SKILL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )

    def _kernel_skill(self):
        return _cached_read_text(self.KERNEL_SKILL_PATH)

    def _provider_judges(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    # -- skills/kernel/SKILL.md ROUTE + DISPATCH stub --

    def test_kernel_skill_provider_field_routing_stub_present(self):
        content = self._kernel_skill()
        self.assertIn(
            "**Provider routing (Phase 2, fg-c0111).** WHEN the active "
            "profile's\n`role-worker` resolves to a provider — R1 automatic "
            "default; a task's\n`provider:` overrides (§7.1) — read\n"
            "`skills/kernel/references/provider-judges.md` §7 (\"Phase 2 — "
            "external\nworker dispatch\") before dispatching",
            content,
        )
        # R1 live 2026-07-22 (bm-atomic-doc-fix-canonical-route): the stub
        # triggers on role-worker resolution alone (automatic default), no
        # longer requiring a task-carried `provider:` field.
        self.assertIn("R1 automatic default", content)
        # 2026-07-22 audit fix: the stub now cites ALL §7.1a gate layers
        # (toggle incl.), §8 materialization, and the §9 tier map.
        self.assertIn("ALL §7.1a gate layers", content)
        self.assertIn("provider's forge.md toggle — missing = OFF", content)
        self.assertIn("§8 materialization\n(REQUIRED, + INTEGRATE exclusion)",
                      content)
        self.assertIn(
            "Any gate layer\nunmet: routes to a Claude `forge-worker` "
            "exactly as if no `provider:`\nfield were present.",
            content,
        )

    # -- skills/kernel/references/provider-judges.md "## 7." section --

    def test_provider_judges_phase2_heading_present(self):
        content = self._provider_judges()
        self.assertIn(
            "## 7. Phase 2 — external worker dispatch (fg-c0111)", content
        )

    def test_provider_judges_non_goals_updated_not_stale(self):
        content = self._provider_judges()
        self.assertIn(
            "Phase 2 worker dispatch (`provider:` field routing, "
            "worktree-scoped\nmutation) is now built — section 7 below "
            "(`fg-c0111`,\n`bm-provider-worker-dispatch`), not a separate "
            "future task anymore.",
            content,
        )

    def test_route_gate_conditions_present(self):
        content = self._provider_judges()
        self.assertIn(
            "- the active profile's `role-worker` resolves to that "
            "provider (not\n  `claude-only`);",
            content,
        )
        self.assertIn(
            "- for `grok` or `antigravity`, the provider's pilot gate\n"
            "  (`bm-grok-pilot-test` / `bm-antigravity-smoke-test`) has "
            "been\n  human-reviewed and cleared — `codex` carries no such "
            "pilot gate",
            content,
        )

    def test_worktree_hard_rule_4_identical_sentence_present(self):
        content = self._provider_judges()
        self.assertIn(
            "Hard Rule 4 holds identically: the external worker never\n"
            "touches `.forge/`; every `.forge/` write is kernel-only, on "
            "the main\nbranch, never inside the external worker's "
            "worktree.",
            content,
        )

    def test_dispatch_shape_workspace_write_command_present(self):
        content = self._provider_judges()
        self.assertIn(
            "codex exec --json -o <output-file> -m <model-slug> "
            "-c model_reasoning_effort=<effort> \\\n    --sandbox "
            "workspace-write --ask-for-approval never \"<worker prompt>\"",
            content,
        )

    def test_wsl2_caveat_sentence_present(self):
        content = self._provider_judges()
        self.assertIn(
            "WHEN this dispatch runs on Windows, THE\nSYSTEM SHALL prefer "
            "WSL2 for the dispatch, per the Phase 0 research\nverdict that "
            "Codex's native Windows sandbox is EXPERIMENTAL",
            content,
        )
        self.assertIn(
            "never\nsilently treated as equivalent to the WSL2 path.",
            content,
        )

    def test_fallback_kernel_ruling_present(self):
        content = self._provider_judges()
        self.assertIn(
            "**KERNEL RULING — fallback wording (recorded, not "
            "relitigated).**",
            content,
        )
        self.assertIn(
            "That is bounce/blocked handling, NOT an automatic\n"
            "re-dispatch to a Claude worker",
            content,
        )

    def test_verification_floor_unmoved_sentence_present(self):
        content = self._provider_judges()
        self.assertIn(
            "A Phase 2 external worker's diff is verified by a Claude-side\n"
            "`forge-verifier`/`forge-ui-verifier` at the task's normal "
            "equal-or-higher\ntier",
            content,
        )

    def test_provider_dispatch_cap_route_check_present(self):
        content = self._provider_judges()
        self.assertIn(
            "WHEN this repo is at its `max-provider-dispatches-per-session` "
            "cap\n(default 10;", content,
        )
