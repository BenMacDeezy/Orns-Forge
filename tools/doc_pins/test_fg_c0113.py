"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0113`: TestFgC0113ProviderBudgetCapPins.
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


class TestFgC0113ProviderBudgetCapPins(unittest.TestCase):
    """Pins for fg-c0113 (spec-e8a3, "Budget accounting across billing
    currencies", RESOLVED option c): the new `max-provider-dispatches-per-
    session` Budgets key (default 10), the never-fold-into-session-token-cap
    rule, the states-so-in-session-report behavior, its config template
    line, and the kernel's one-line ROUTE-time citation."""

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    TEMPLATE_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references"
        / "forge-config-template.md"
    )
    KERNEL_SKILL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CONFIGURATION_PATH = REPO_ROOT / "docs" / "features" / "configuration.md"

    def _conventions_content(self):
        return _read_path(self.CONVENTIONS_PATH)

    def test_verification_shard_has_external_provider_dispatch_heading(self):
        content = self._conventions_content()
        self.assertIn(
            "## External-provider dispatch rules — 2026-07-19 "
            "(fg-c0112, spec-e8a3)",
            content,
        )

    def test_trust_shard_has_provider_dispatch_security_heading(self):
        content = self._conventions_content()
        self.assertIn(
            "## Provider dispatch security rules — 2026-07-19 "
            "(fg-c0112, spec-e8a3)",
            content,
        )

    def test_json_jsonl_only_phrase(self):
        """(a) JSON/JSONL-only output capture, never a scraped TTY
        transcript — the dispatch helper refuses a CLI without structured
        output."""
        content = self._conventions_content()
        self.assertIn(
            "the dispatch helper refuses to invoke a CLI in a mode that "
            "doesn't offer clean structured output",
            content,
        )

    def test_pin_model_ids_at_implementation_time_phrase(self):
        """(b) Per-provider tier map resolved from the CLI's own live
        model listing, never cutoff-bound knowledge."""
        content = self._conventions_content()
        self.assertIn(
            "pinned at implementation time from each CLI's own live "
            "model-listing command",
            content,
        )

    def test_verification_floor_unmoved_phrase(self):
        """(c) Verification floor unmoved for external output — never
        exempt from adversarial verify; Phase 2 diffs verified by
        Claude-side verifier at equal-or-higher tier."""
        content = self._conventions_content()
        self.assertIn("the verification floor stays unmoved", content)
        self.assertIn(
            "external output is never exempt from adversarial verify",
            content,
        )

    def test_sandbox_pairing_ban_phrase(self):
        """(d) Auto-approve flags pair ONLY with workspace-scoped sandbox,
        NEVER a full-bypass flag — normative for every provider profile."""
        content = self._conventions_content()
        self.assertIn(
            "SHALL NEVER use a "
            "full-bypass flag that disables both sandbox and approval "
            "together",
            content,
        )
        self.assertIn(
            "This rule is normative for every current and future "
            "provider profile",
            content,
        )

    def test_no_credentials_in_env_phrase(self):
        """(e) No credential ever placed in job/env vars readable by
        dispatched work; auth is exclusively the provider CLI's own local
        state."""
        content = self._conventions_content()
        self.assertIn(
            "dispatched worktrees and judge spawns never receive a "
            "provider credential as an injectable value",
            content,
        )

    def test_verification_manifest_row(self):
        content = self._conventions_content()
        self.assertIn(
            "`External-provider dispatch rules — 2026-07-19 (fg-c0112, "
            "spec-e8a3)` -> `docs/conventions/verification.md`",
            content,
        )

    def test_trust_manifest_row(self):
        content = self._conventions_content()
        self.assertIn(
            "`Provider dispatch security rules — 2026-07-19 (fg-c0112, "
            "spec-e8a3)` -> `docs/conventions/trust-and-security.md`",
            content,
        )
    def _kernel_content(self):
        return _cached_read_text(self.KERNEL_SKILL_PATH)

    def test_default_10_phrase_in_conventions(self):
        content = self._conventions_content()
        self.assertIn(
            "`max-provider-dispatches-per-session` (default 10)", content
        )

    def test_default_10_phrase_in_configuration_mirror(self):
        content = _cached_read_text(self.CONFIGURATION_PATH)
        self.assertIn(
            "`max-provider-dispatches-per-session` (default `10`)", content
        )

    def test_never_fold_into_session_token_cap_phrase(self):
        content = self._conventions_content()
        self.assertIn(
            "never folded into `session-token-cap`", content
        )

    def test_states_so_in_session_report_phrase(self):
        content = self._conventions_content()
        self.assertIn(
            "dispatches no further external work and states so in the "
            "session report",
            content,
        )

    def test_config_template_line(self):
        # Amended 2026-07-22 (Provider dispatch checkpoints, owner-
        # ratified): shipped default is now the checkpoint model — cap
        # `none` + checkpoint cadence. The key itself remains, and a
        # numeric value keeps fg-c0113's original hard-cap semantics.
        content = _cached_read_text(self.TEMPLATE_PATH)
        self.assertIn("- max-provider-dispatches-per-session: none",
                      content)
        self.assertIn("- provider-dispatch-checkpoint-every: 10", content)

    def test_kernel_citation_line(self):
        content = self._kernel_content()
        # 2026-07-22 audit fix: the kernel now cites §7.6's checkpoint
        # amendment (shipped default `none` + cadence 10) instead of the
        # superseded 2026-07-19 hard-cap citation.
        self.assertIn(
            "Provider dispatches tally per provider-judges.md §7.6's",
            content,
        )
        self.assertIn(
            "checkpoint amendment: cap `none` + checkpoint every 10",
            content,
        )

    def test_kernel_stays_under_char_budget(self):
        """The kernel delta must be a one-line citation stub, not a
        restatement -- confirm the file is still well under the
        31,617-char ceiling noted in the fg-c0113 contract."""
        content = self._kernel_content()
        self.assertLess(len(content), 31617)
