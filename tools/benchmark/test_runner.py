"""Tests for tools/benchmark/runner.py (fg-a10403, benchmark T3: runner core).

Design refs (docs/plans/2026-07-18-ab-benchmark-design.md, cited not
restated): D4 (fresh git worktree per arm-run from a pinned base, no shared
state) and D8 (script everything deterministic; isolate the model-in-the-loop
step behind an injected adapter callable).

All git operations are exercised against real scratch repos built in
tempfile.TemporaryDirectory() -- never this repo's own working tree --
mirroring the pattern tools/test_hooks.py already uses for git-backed tests.
"""
import json
import pathlib
import subprocess
import tempfile
import unittest

from runner import (
    ARMS,
    ArmRunResult,
    WorktreeError,
    capture_diff,
    create_worktree,
    draw_arm_order,
    remove_worktree,
    run_arm,
    run_pair,
    worktree,
    write_run_record,
)


def _git(args, cwd):
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )


def _init_scratch_repo(path):
    """A minimal real git repo with one committed file. Returns the base SHA."""
    _git(["init", "-q"], path)
    _git(["config", "user.email", "runner-test@example.com"], path)
    _git(["config", "user.name", "Runner Test"], path)
    _git(["config", "commit.gpgsign", "false"], path)
    (path / "a.txt").write_text("base\n", encoding="utf-8", newline="\n")
    _git(["add", "a.txt"], path)
    _git(["commit", "-q", "-m", "base commit"], path)
    base_sha = _git(["rev-parse", "HEAD"], path).stdout.strip()
    return base_sha


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp_ctx.name)
        self.addCleanup(self._tmp_ctx.cleanup)
        self.repo_root = self.tmp / "scratch-repo"
        self.repo_root.mkdir()
        self.base_sha = _init_scratch_repo(self.repo_root)


class TestCreateWorktree(RunnerTestCase):
    def test_checks_out_pinned_base_not_current_head(self):
        # A second commit moves HEAD; the worktree must still reflect the
        # pinned base SHA, not whatever HEAD has drifted to since (D4).
        (self.repo_root / "a.txt").write_text(
            "changed\n", encoding="utf-8", newline="\n")
        _git(["commit", "-aq", "-m", "second commit"], self.repo_root)

        dest = self.tmp / "wt1"
        create_worktree(self.repo_root, self.base_sha, dest)
        self.addCleanup(lambda: remove_worktree(self.repo_root, dest))

        content = (dest / "a.txt").read_text(encoding="utf-8")
        self.assertEqual(content, "base\n")

    def test_creates_dest_directory(self):
        dest = self.tmp / "wt2"
        self.assertFalse(dest.exists())
        create_worktree(self.repo_root, self.base_sha, dest)
        self.addCleanup(lambda: remove_worktree(self.repo_root, dest))
        self.assertTrue(dest.exists())
        self.assertTrue((dest / "a.txt").exists())

    def test_bad_base_sha_raises_worktree_error(self):
        dest = self.tmp / "wt-bad"
        with self.assertRaises(WorktreeError):
            create_worktree(self.repo_root, "0" * 40, dest)


class TestRemoveWorktree(RunnerTestCase):
    def test_removes_directory(self):
        dest = self.tmp / "wt3"
        create_worktree(self.repo_root, self.base_sha, dest)
        self.assertTrue(dest.exists())
        remove_worktree(self.repo_root, dest)
        self.assertFalse(dest.exists())

    def test_idempotent_when_never_created(self):
        dest = self.tmp / "never-existed"
        remove_worktree(self.repo_root, dest)  # must not raise

    def test_idempotent_when_already_removed(self):
        dest = self.tmp / "wt4"
        create_worktree(self.repo_root, self.base_sha, dest)
        remove_worktree(self.repo_root, dest)
        remove_worktree(self.repo_root, dest)  # second call must not raise

    def test_force_removes_worktree_with_uncommitted_changes(self):
        dest = self.tmp / "wt5"
        create_worktree(self.repo_root, self.base_sha, dest)
        (dest / "a.txt").write_text("dirty\n", encoding="utf-8", newline="\n")
        (dest / "new.txt").write_text("new\n", encoding="utf-8", newline="\n")
        remove_worktree(self.repo_root, dest)  # must not raise despite dirt
        self.assertFalse(dest.exists())


class TestWorktreeContextManager(RunnerTestCase):
    def test_cleans_up_on_normal_exit(self):
        dest = self.tmp / "wt6"
        with worktree(self.repo_root, self.base_sha, dest) as wt_path:
            self.assertTrue(wt_path.exists())
        self.assertFalse(dest.exists())

    def test_cleans_up_on_exception(self):
        dest = self.tmp / "wt7"
        with self.assertRaises(RuntimeError):
            with worktree(self.repo_root, self.base_sha, dest) as wt_path:
                (wt_path / "a.txt").write_text(
                    "dirty\n", encoding="utf-8", newline="\n")
                raise RuntimeError("boom")
        self.assertFalse(dest.exists())


class TestDrawArmOrder(unittest.TestCase):
    def test_deterministic_for_same_seed(self):
        self.assertEqual(draw_arm_order(42), draw_arm_order(42))

    def test_contains_both_arms_exactly_once(self):
        order = draw_arm_order(1)
        self.assertEqual(tuple(sorted(order)), tuple(sorted(ARMS)))
        self.assertEqual(len(order), 2)

    def test_varies_across_seeds(self):
        orders = {draw_arm_order(seed) for seed in range(20)}
        # Both possible orders must appear somewhere in a 20-seed sample --
        # if this ever comes back with only one order, the draw is broken
        # (constant), not just unlucky.
        self.assertEqual(orders, {("A", "B"), ("B", "A")})


class TestCaptureDiff(RunnerTestCase):
    def setUp(self):
        super().setUp()
        self.dest = self.tmp / "wt-diff"
        create_worktree(self.repo_root, self.base_sha, self.dest)
        self.addCleanup(lambda: remove_worktree(self.repo_root, self.dest))

    def test_empty_when_no_changes(self):
        self.assertEqual(capture_diff(self.dest), "")

    def test_includes_modified_tracked_file(self):
        (self.dest / "a.txt").write_text(
            "modified\n", encoding="utf-8", newline="\n")
        diff = capture_diff(self.dest)
        self.assertIn("a.txt", diff)
        self.assertIn("-base", diff)
        self.assertIn("+modified", diff)

    def test_includes_new_untracked_file_as_addition(self):
        (self.dest / "new_file.txt").write_text(
            "hello\n", encoding="utf-8", newline="\n")
        diff = capture_diff(self.dest)
        self.assertIn("new_file.txt", diff)
        self.assertIn("+hello", diff)

    def test_includes_deleted_file(self):
        (self.dest / "a.txt").unlink()
        diff = capture_diff(self.dest)
        self.assertIn("a.txt", diff)
        self.assertIn("-base", diff)


class TestRunArm(RunnerTestCase):
    def test_captures_wall_clock_diff_and_adapter_result(self):
        dest = self.tmp / "wt-run-arm"

        def adapter(wt_path):
            (wt_path / "a.txt").write_text(
                "adapter-wrote-this\n", encoding="utf-8", newline="\n")
            return {"note": "did the thing"}

        result = run_arm(
            repo_root=self.repo_root,
            base_sha=self.base_sha,
            dest=dest,
            arm="A",
            adapter=adapter,
        )

        self.assertIsInstance(result, ArmRunResult)
        self.assertEqual(result.arm, "A")
        self.assertGreaterEqual(result.wall_clock_seconds, 0)
        self.assertIn("adapter-wrote-this", result.diff)
        self.assertEqual(result.adapter_result, {"note": "did the thing"})

    def test_removes_worktree_after_completion(self):
        dest = self.tmp / "wt-run-arm-cleanup"
        run_arm(
            repo_root=self.repo_root,
            base_sha=self.base_sha,
            dest=dest,
            arm="B",
            adapter=lambda wt_path: None,
        )
        self.assertFalse(dest.exists())

    def test_propagates_adapter_exception_and_still_cleans_up(self):
        dest = self.tmp / "wt-run-arm-fail"

        def bad_adapter(wt_path):
            raise ValueError("adapter blew up")

        with self.assertRaises(ValueError):
            run_arm(
                repo_root=self.repo_root,
                base_sha=self.base_sha,
                dest=dest,
                arm="A",
                adapter=bad_adapter,
            )
        self.assertFalse(dest.exists())


class TestRunPair(RunnerTestCase):
    def _adapters(self, calls):
        def make(arm):
            def adapter(wt_path):
                calls.append(arm)
                (wt_path / f"{arm.lower()}.marker").write_text(
                    arm, encoding="utf-8", newline="\n")
                return {"arm": arm}
            return adapter
        return {"A": make("A"), "B": make("B")}

    def test_records_seed_and_arm_order(self):
        calls = []
        work_dir = self.tmp / "bench" / "wt"
        record = run_pair(
            task_id="T-demo",
            repo_root=self.repo_root,
            base_sha=self.base_sha,
            seed=7,
            adapters=self._adapters(calls),
            work_dir=work_dir,
        )
        self.assertEqual(record["seed"], 7)
        self.assertEqual(record["task_id"], "T-demo")
        self.assertEqual(record["base_sha"], self.base_sha)
        self.assertEqual(tuple(sorted(record["arm_order"])), ("A", "B"))
        self.assertEqual(set(calls), {"A", "B"})

    def test_both_arms_present_and_json_serializable(self):
        work_dir = self.tmp / "bench" / "wt"
        record = run_pair(
            task_id="T-demo2",
            repo_root=self.repo_root,
            base_sha=self.base_sha,
            seed=1,
            adapters=self._adapters([]),
            work_dir=work_dir,
        )
        self.assertEqual(set(record["arms"]), {"A", "B"})
        for arm in ARMS:
            arm_rec = record["arms"][arm]
            self.assertIn("wall_clock_seconds", arm_rec)
            self.assertIn("diff", arm_rec)
            self.assertIn(arm, arm_rec["diff"])
            self.assertEqual(arm_rec["adapter_result"], {"arm": arm})
        json.dumps(record)  # must not raise

    def test_rejects_incomplete_adapters_mapping(self):
        work_dir = self.tmp / "bench" / "wt"
        with self.assertRaises(ValueError):
            run_pair(
                task_id="T-bad",
                repo_root=self.repo_root,
                base_sha=self.base_sha,
                seed=1,
                adapters={"A": lambda wt_path: None},
                work_dir=work_dir,
            )

    def test_same_seed_yields_same_arm_order_across_calls(self):
        work_dir = self.tmp / "bench" / "wt"
        record1 = run_pair(
            task_id="T-rep1",
            repo_root=self.repo_root,
            base_sha=self.base_sha,
            seed=99,
            adapters=self._adapters([]),
            work_dir=work_dir,
        )
        record2 = run_pair(
            task_id="T-rep2",
            repo_root=self.repo_root,
            base_sha=self.base_sha,
            seed=99,
            adapters=self._adapters([]),
            work_dir=work_dir,
        )
        self.assertEqual(record1["arm_order"], record2["arm_order"])

    def test_worktrees_removed_after_pair_completes(self):
        work_dir = self.tmp / "bench" / "wt"
        record = run_pair(
            task_id="T-cleanup",
            repo_root=self.repo_root,
            base_sha=self.base_sha,
            seed=3,
            adapters=self._adapters([]),
            work_dir=work_dir,
        )
        run_id = record["run_id"]
        for arm in ARMS:
            dest = work_dir / "T-cleanup" / arm / run_id
            self.assertFalse(dest.exists())


class TestWriteRunRecord(unittest.TestCase):
    def test_writes_utf8_json_with_lf_newlines_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "run-record.json"
            record = {"task_id": "T1", "seed": 5, "arm_order": ["B", "A"]}
            write_run_record(record, path)

            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)

            loaded = json.loads(raw.decode("utf-8"))
            self.assertEqual(loaded, record)


if __name__ == "__main__":
    unittest.main()
