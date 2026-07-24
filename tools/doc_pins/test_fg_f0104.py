"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-f0104`: TestFgF0104SyncCadencePins.
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


class TestFgF0104SyncCadencePins(unittest.TestCase):
    """Doc-pin regression tests for fg-f0104 (sync cadence wiring):
    skills/kernel/SKILL.md's SYNC/INTEGRATE citation lines pointing at
    coordination-gate.md's new §10, and §10's mechanics (pull staging
    before wave/claim, push staging never main at INTEGRATE, diverged-push
    retry via fg-e103's offline-merge convention) plus the multi-operator-
    defaults precedence note -- pinned so a future edit can't silently
    reintroduce a push to `main` or drop the divergence-retry rule."""

    def _skill_content(self):
        return _read_path("skills/kernel/SKILL.md")

    def _gate_content(self):
        return _read_path(
            "skills/kernel/references/coordination-gate.md"
        )

    def test_sync_cites_staging_pull_before_wave_or_claim(self):
        content = self._skill_content()
        self.assertIn(
            "- **Sync cadence.** Pull `staging` before PULL computes a "
            "wave or any task\n  is claimed — `coordination-gate.md` "
            "§10. NORMATIVE.",
            content,
        )

    def test_integrate_cites_staging_push_never_main(self):
        content = self._skill_content()
        self.assertIn(
            "**Sync cadence.** Push the integration commit to `staging` "
            "— never\n  `main` — before the next claim; on divergence, "
            "retry per `fg-e103`'s\n  offline-merge convention — "
            "`coordination-gate.md` §10. NORMATIVE.",
            content,
        )

    def test_gate_has_sync_cadence_section(self):
        content = self._gate_content()
        self.assertIn("## 10. Sync cadence (`fg-f0104`)", content)

    def test_gate_sync_cadence_mechanics_pull_push_retry(self):
        content = self._gate_content()
        self.assertIn(
            "THE SYSTEM SHALL pull `staging` (`CONTRIBUTING.md` §6)\n"
            "before PULL computes a wave or any task is claimed.",
            content,
        )
        self.assertIn(
            "THE SYSTEM SHALL push the integration commit to `staging` —\n"
            "never `main` (`CONTRIBUTING.md` §6) — before the next claim.",
            content,
        )
        self.assertIn(
            "THE SYSTEM SHALL pull, apply `fg-e103`'s\n"
            "offline-merge convention (`docs/conventions/artifact-formats.md`,\n"
            '"Offline merge convention") to any conflicting file, and retry, never\n'
            "force-pushing or dropping the commit.",
            content,
        )

    def test_gate_sync_cadence_precedence_note(self):
        content = self._gate_content()
        self.assertIn(
            "**Precedence.** The above are multi-operator DEFAULTS. An "
            "explicit human\ninstruction to push elsewhere (e.g. this "
            "repo's own standing main+staging\npush) takes precedence "
            "over the `staging`-only default for that push.",
            content,
        )

    def test_gate_non_goals_no_longer_fences_sync_cadence(self):
        content = self._gate_content()
        self.assertNotIn("No sync-cadence mechanics", content)

    def test_contributing_section_6_still_names_staging_and_main(self):
        content = _read_path("CONTRIBUTING.md")
        self.assertIn("## 6. Branch flow", content)
        self.assertIn(
            "**`staging`** is the integration branch: push your work "
            "here",
            content,
        )
        self.assertIn(
            "**`main`** is release-ready at all times: it only moves "
            "by merging a\n    green `staging`",
            content,
        )
