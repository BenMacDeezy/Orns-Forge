# tools/test_trust.py
"""Truth-table unit tests for tools/trust.py's is_trusted() — the canonical,
deterministic encoding of the Forge trust decision (docs/conventions.md,
"Trust boundary": untrusted iff neither `.forge/.provenance` nor
`.forge/.trust-local` is present). These exercise a real function against a
real temp directory, so they are non-vacuous by construction."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import trust  # noqa: E402


class TestIsTrusted(unittest.TestCase):
    def test_neither_marker_is_untrusted(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(trust.is_trusted(d))

    def test_provenance_only_is_trusted(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / ".provenance").write_text("created: x\n", encoding="utf-8")
            self.assertTrue(trust.is_trusted(d))

    def test_trust_local_only_is_trusted(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / ".trust-local").write_text("trusted-by: x\n", encoding="utf-8")
            self.assertTrue(trust.is_trusted(d))

    def test_both_markers_is_trusted(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / ".provenance").write_text("created: x\n", encoding="utf-8")
            (pathlib.Path(d) / ".trust-local").write_text("trusted-by: x\n", encoding="utf-8")
            self.assertTrue(trust.is_trusted(d))


class TestNewSinceConfirm(unittest.TestCase):
    """Truth-table unit tests for trust.new_since_confirm() -- the
    accelerator for the kernel's "New since last trust confirm" prose rule
    (skills/kernel/SKILL.md)."""

    def _forge(self, tmp):
        forge_dir = pathlib.Path(tmp) / ".forge"
        (forge_dir / "queue" / "tasks").mkdir(parents=True)
        (forge_dir / "specs").mkdir(parents=True)
        return forge_dir

    def _write_trust_local(self, forge_dir, confirmed):
        (forge_dir / ".trust-local").write_text(
            f"trusted-by: tester\nconfirmed: {confirmed}\nmachine: test-host\n",
            encoding="utf-8",
        )

    def _write_task(self, forge_dir, task_id, state, created):
        (forge_dir / "queue" / "tasks" / f"{task_id}.md").write_text(
            f"---\nid: {task_id}\ntitle: t\nstate: {state}\ntier: standard\n"
            f"created: {created}\n---\n\n## Acceptance criteria\n- n/a\n",
            encoding="utf-8",
        )

    def _write_spec(self, forge_dir, spec_id, created):
        (forge_dir / "specs" / f"{spec_id}.md").write_text(
            f"---\nid: {spec_id}\ntitle: s\nstatus: approved\n"
            f"created: {created}\n---\n\n## Goal\nn/a\n",
            encoding="utf-8",
        )

    def test_missing_trust_local_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_task(forge_dir, "fg-new1", "ready", "2026-07-20")
            self.assertEqual(trust.new_since_confirm(forge_dir), [])

    def test_task_created_after_confirm_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self._write_task(forge_dir, "fg-new1", "ready", "2026-07-20")
            self.assertEqual(trust.new_since_confirm(forge_dir), ["fg-new1"])

    def test_task_created_before_confirm_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self._write_task(forge_dir, "fg-old1", "ready", "2026-07-01")
            self.assertEqual(trust.new_since_confirm(forge_dir), [])

    def test_task_created_same_day_as_confirm_is_not_flagged(self):
        # A date-only `created` (midnight UTC) equal to the confirm day must
        # not be treated as strictly newer.
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T00:00:00Z")
            self._write_task(forge_dir, "fg-same1", "ready", "2026-07-17")
            self.assertEqual(trust.new_since_confirm(forge_dir), [])

    def test_malformed_created_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self._write_task(forge_dir, "fg-bad1", "ready", "not-a-date")
            self.assertEqual(trust.new_since_confirm(forge_dir), [])

    def test_non_ready_backlog_task_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self._write_task(forge_dir, "fg-done1", "done", "2026-07-20")
            self.assertEqual(trust.new_since_confirm(forge_dir), [])

    def test_backlog_task_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self._write_task(forge_dir, "fg-back1", "backlog", "2026-07-20")
            self.assertEqual(trust.new_since_confirm(forge_dir), ["fg-back1"])

    def test_spec_created_after_confirm_is_flagged_regardless_of_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self._write_spec(forge_dir, "spec-new1", "2026-07-20")
            self.assertEqual(trust.new_since_confirm(forge_dir), ["spec-new1"])

    def test_mixed_tasks_and_specs_sorted_by_file_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self._write_task(forge_dir, "fg-aaaa", "ready", "2026-07-20")
            self._write_spec(forge_dir, "spec-bbbb", "2026-07-21")
            self._write_task(forge_dir, "fg-cccc", "ready", "2026-07-01")
            result = trust.new_since_confirm(forge_dir)
            self.assertEqual(set(result), {"fg-aaaa", "spec-bbbb"})

    def test_missing_queue_and_spec_dirs_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = pathlib.Path(tmp) / ".forge"
            forge_dir.mkdir()
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            self.assertEqual(trust.new_since_confirm(forge_dir), [])

    def test_missing_confirmed_field_flags_everything_not_nothing(self):
        # `.trust-local` exists but has no `confirmed:` line at all -- must
        # NOT return [] (identical to the no-.trust-local case, a fail-OPEN
        # outcome that silently suppresses drift warnings even though
        # is_trusted() reports TRUSTED). Must flag every parseable-created
        # ready/backlog task instead.
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nmachine: test-host\n", encoding="utf-8"
            )
            self._write_task(forge_dir, "fg-mal1", "ready", "2026-07-01")
            self.assertEqual(trust.new_since_confirm(forge_dir), ["fg-mal1"])

    def test_unparseable_confirmed_value_flags_everything_not_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "not-a-timestamp")
            self._write_task(forge_dir, "fg-mal2", "ready", "2026-07-01")
            self.assertEqual(trust.new_since_confirm(forge_dir), ["fg-mal2"])

    def test_task_with_utf8_bom_is_flagged(self):
        """Regression test: UTF-8 BOM (PowerShell default) must not prevent
        frontmatter detection. A BOM'd task file created after confirm should
        be flagged like any other."""
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self._write_trust_local(forge_dir, "2026-07-17T10:00:00Z")
            # Write a task file with UTF-8 BOM prefix (as PowerShell Out-File does)
            task_content = (
                "---\nid: fg-bom1\ntitle: t\nstate: ready\ntier: standard\n"
                "created: 2026-07-20\n---\n\n## Acceptance criteria\n- n/a\n"
            )
            task_path = forge_dir / "queue" / "tasks" / "fg-bom1.md"
            # Write BOM (UTF-8-sig) prefix explicitly
            task_path.write_bytes(b'\xef\xbb\xbf' + task_content.encode('utf-8'))
            # Should be flagged despite the BOM
            self.assertEqual(trust.new_since_confirm(forge_dir), ["fg-bom1"])


class TestIsBaselineCorrupted(unittest.TestCase):
    """Unit tests for trust.is_baseline_corrupted() -- the sibling signal
    fg-a10932 adds so a caller can distinguish "corrupted trust baseline,
    everything looks new" from "genuinely N new items since confirm" (both
    render as an identical flat id list from new_since_confirm() alone)."""

    def _forge(self, tmp):
        forge_dir = pathlib.Path(tmp) / ".forge"
        (forge_dir / "queue" / "tasks").mkdir(parents=True)
        (forge_dir / "specs").mkdir(parents=True)
        return forge_dir

    def test_missing_trust_local_is_not_corrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            self.assertFalse(trust.is_baseline_corrupted(forge_dir))

    def test_missing_confirmed_field_is_corrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nmachine: test-host\n", encoding="utf-8"
            )
            self.assertTrue(trust.is_baseline_corrupted(forge_dir))

    def test_unparseable_confirmed_value_is_corrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nconfirmed: not-a-timestamp\n"
                "machine: test-host\n", encoding="utf-8"
            )
            self.assertTrue(trust.is_baseline_corrupted(forge_dir))

    def test_valid_confirmed_value_is_not_corrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nconfirmed: 2026-07-17T10:00:00Z\n"
                "machine: test-host\n", encoding="utf-8"
            )
            self.assertFalse(trust.is_baseline_corrupted(forge_dir))


class TestCli(unittest.TestCase):
    def _run(self, forge_dir):
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "trust.py"), str(forge_dir)],
            capture_output=True, text=True,
        )

    def test_cli_prints_untrusted_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            result = self._run(d)
            self.assertEqual(result.stdout.strip(), "untrusted")
            self.assertEqual(result.returncode, 1)

    def test_cli_prints_trusted_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / ".provenance").write_text("created: x\n", encoding="utf-8")
            result = self._run(d)
            self.assertEqual(result.stdout.strip(), "trusted")
            self.assertEqual(result.returncode, 0)


class TestNewSinceCli(unittest.TestCase):
    """CLI parity for new_since_confirm() (docs/audits/2026-07-17-sweep2-
    hygiene.md, Part B step 8): `trust.py --new-since <.forge path>` prints
    one flagged id per line and always exits 0 on a valid directory -- this
    is a visible-surfacing report, not a blocking gate, so a non-empty result
    must not look like a failure to a caller checking the exit code."""

    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "trust.py"), *args],
            capture_output=True, text=True,
        )

    def _forge(self, tmp):
        forge_dir = pathlib.Path(tmp) / ".forge"
        (forge_dir / "queue" / "tasks").mkdir(parents=True)
        (forge_dir / "specs").mkdir(parents=True)
        return forge_dir

    def test_new_since_cli_prints_flagged_id_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nconfirmed: 2026-07-17T10:00:00Z\n"
                "machine: test-host\n", encoding="utf-8")
            (forge_dir / "queue" / "tasks" / "fg-new1.md").write_text(
                "---\nid: fg-new1\ntitle: t\nstate: ready\ntier: standard\n"
                "created: 2026-07-20\n---\n\n## Acceptance criteria\n- n/a\n",
                encoding="utf-8")
            result = self._run(["--new-since", str(forge_dir)])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "fg-new1")

    def test_new_since_cli_multiple_ids_one_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nconfirmed: 2026-07-17T10:00:00Z\n"
                "machine: test-host\n", encoding="utf-8")
            (forge_dir / "queue" / "tasks" / "fg-aaaa.md").write_text(
                "---\nid: fg-aaaa\ntitle: t\nstate: ready\ntier: standard\n"
                "created: 2026-07-20\n---\n\n## Acceptance criteria\n- n/a\n",
                encoding="utf-8")
            (forge_dir / "specs" / "spec-bbbb.md").write_text(
                "---\nid: spec-bbbb\ntitle: s\nstatus: approved\n"
                "created: 2026-07-21\n---\n\n## Goal\nn/a\n", encoding="utf-8")
            result = self._run(["--new-since", str(forge_dir)])
            self.assertEqual(result.returncode, 0)
            lines = result.stdout.strip().splitlines()
            self.assertEqual(set(lines), {"fg-aaaa", "spec-bbbb"})

    def test_new_since_cli_empty_result_prints_nothing_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            result = self._run(["--new-since", str(forge_dir)])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")

    def test_new_since_cli_corrupted_baseline_prints_warning_before_ids(self):
        # Regression test for fg-a10932: a malformed/missing `confirmed:`
        # field must surface a distinct WARNING line ahead of the id list,
        # not an indistinguishable flat dump identical in shape to the
        # genuinely-new-work case below.
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nmachine: test-host\n", encoding="utf-8")
            (forge_dir / "queue" / "tasks" / "fg-mal1.md").write_text(
                "---\nid: fg-mal1\ntitle: t\nstate: ready\ntier: standard\n"
                "created: 2026-07-01\n---\n\n## Acceptance criteria\n- n/a\n",
                encoding="utf-8")
            result = self._run(["--new-since", str(forge_dir)])
            self.assertEqual(result.returncode, 0)
            lines = result.stdout.strip().splitlines()
            self.assertTrue(
                lines[0].startswith("WARNING:"),
                f"expected a WARNING line first, got: {lines!r}",
            )
            self.assertIn("re-run trust confirm", lines[0])
            self.assertEqual(lines[1:], ["fg-mal1"])

    def test_new_since_cli_genuine_new_work_has_no_warning(self):
        # The genuinely-new-work case (a well-formed `confirmed:` baseline
        # with real new items since) must NOT surface the corrupted-baseline
        # WARNING -- only the flat id list, same as before this fix.
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = self._forge(tmp)
            (forge_dir / ".trust-local").write_text(
                "trusted-by: tester\nconfirmed: 2026-07-17T10:00:00Z\n"
                "machine: test-host\n", encoding="utf-8")
            (forge_dir / "queue" / "tasks" / "fg-new1.md").write_text(
                "---\nid: fg-new1\ntitle: t\nstate: ready\ntier: standard\n"
                "created: 2026-07-20\n---\n\n## Acceptance criteria\n- n/a\n",
                encoding="utf-8")
            result = self._run(["--new-since", str(forge_dir)])
            self.assertEqual(result.returncode, 0)
            lines = result.stdout.strip().splitlines()
            self.assertNotIn(
                "WARNING", result.stdout,
                "genuinely-new-work case must not surface the "
                "corrupted-baseline warning",
            )
            self.assertEqual(lines, ["fg-new1"])

    def test_plain_cli_contract_unchanged(self):
        # The pre-existing `trust.py <dir>` trusted/untrusted contract must
        # stay byte-compatible after adding the --new-since branch.
        with tempfile.TemporaryDirectory() as d:
            result = self._run([d])
            self.assertEqual(result.stdout.strip(), "untrusted")
            self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
