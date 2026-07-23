"""Tests for tools/update_check.py (fg-a10914).

Pins the security-floor properties from the task's acceptance criteria:
fail-silent on every remote-failure path, the 24h throttle, strict semver
validation of anything remote, and the exact single-line output shape.
Hermetic — the remote is always mocked; these tests never touch the
network or this repo's real cache file.
"""
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import update_check

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "update-nudge.sh"
BASH = shutil.which("bash")


class TestParseSemver(unittest.TestCase):
    def test_accepts_bare_semver(self):
        self.assertEqual(update_check.parse_semver("1.2.3"), (1, 2, 3))

    def test_accepts_v_prefixed_semver(self):
        self.assertEqual(update_check.parse_semver("v1.2.3"), (1, 2, 3))

    def test_rejects_two_segment_version(self):
        self.assertIsNone(update_check.parse_semver("v1.2"))

    def test_rejects_four_segment_version(self):
        self.assertIsNone(update_check.parse_semver("1.2.3.4"))

    def test_rejects_non_numeric_literal(self):
        self.assertIsNone(update_check.parse_semver("latest"))

    def test_rejects_shell_injection_string(self):
        self.assertIsNone(update_check.parse_semver("1.2.3; rm -rf /"))

    def test_rejects_format_string_injection(self):
        self.assertIsNone(update_check.parse_semver("{0.__class__}"))

    def test_rejects_non_string_input(self):
        self.assertIsNone(update_check.parse_semver(None))
        self.assertIsNone(update_check.parse_semver(1.2))

    def test_accepts_surrounding_whitespace(self):
        self.assertEqual(update_check.parse_semver("  v2.0.0\n"), (2, 0, 0))


class UpdateCheckTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache_path = pathlib.Path(self._tmp.name) / "cache-file"

    def _stale_cache(self):
        # A cache file older than the 24h TTL: throttle should NOT apply.
        self.cache_path.write_text("0", encoding="utf-8")
        old = time.time() - update_check.CACHE_TTL_SECONDS - 60
        import os

        os.utime(self.cache_path, (old, old))

    def _fresh_cache(self):
        self.cache_path.write_text(str(time.time()), encoding="utf-8")


class TestThrottle(UpdateCheckTestBase):
    def test_fresh_cache_skips_remote_call_entirely(self):
        self._fresh_cache()
        with patch("update_check._fetch_remote_tags") as fetch:
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        fetch.assert_not_called()
        self.assertIsNone(result)

    def test_stale_cache_allows_remote_call(self):
        self._stale_cache()
        with patch("update_check._fetch_remote_tags", return_value=["v0.10.0"]) as fetch:
            update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        fetch.assert_called_once()

    def test_missing_cache_allows_remote_call_and_writes_cache(self):
        self.assertFalse(self.cache_path.exists())
        with patch("update_check._fetch_remote_tags", return_value=[]):
            update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertTrue(self.cache_path.exists())

    def test_cache_is_written_even_when_remote_call_fails(self):
        # Throttling must cover failed checks too, or a persistently
        # unreachable mirror would be hit on every single session start.
        self.assertFalse(self.cache_path.exists())
        with patch("update_check._fetch_remote_tags", side_effect=RuntimeError("boom")):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertIsNone(result)
        self.assertTrue(self.cache_path.exists())


class TestFailSilent(UpdateCheckTestBase):
    def test_unset_mirror_url_is_a_silent_noop(self):
        self._stale_cache_not_needed = True
        with patch("update_check._fetch_remote_tags") as fetch:
            result = update_check.check_for_update(
                mirror_url="",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        fetch.assert_not_called()
        self.assertIsNone(result)
        # Fail-silent + no side effect: the pre-release no-op must not even
        # touch the throttle cache.
        self.assertFalse(self.cache_path.exists())

    def test_network_timeout_is_silent(self):
        self._stale_cache()
        with patch(
            "update_check._fetch_remote_tags",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=2),
        ):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertIsNone(result)

    def test_fetch_raising_unexpected_exception_is_silent(self):
        self._stale_cache()
        with patch("update_check._fetch_remote_tags", side_effect=OSError("no network")):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertIsNone(result)

    def test_malformed_remote_tags_are_silent(self):
        self._stale_cache()
        with patch(
            "update_check._fetch_remote_tags",
            return_value=["latest", "v1.2", "1.2.3.4", "not-a-version", ""],
        ):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="99.0.0",
            )
        self.assertIsNone(result)

    def test_unreadable_installed_version_is_silent(self):
        # installed_version=None with no override falls back to reading the
        # real plugin.json via _installed_version() -- simulate that file
        # being missing/corrupt (returns None) and confirm the check stays
        # silent rather than crashing or treating it as "always newer".
        self._stale_cache()
        with patch("update_check._fetch_remote_tags", return_value=["v99.0.0"]), patch(
            "update_check._installed_version", return_value=None
        ):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version=None,
            )
        self.assertIsNone(result)

    def test_malformed_installed_version_string_is_silent(self):
        self._stale_cache()
        with patch("update_check._fetch_remote_tags", return_value=["v99.0.0"]):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="not-a-version",
            )
        self.assertIsNone(result)

    def test_real_subprocess_path_swallows_git_missing_or_erroring(self):
        # Exercises _fetch_remote_tags itself (not mocked) against a mirror
        # URL that cannot resolve — the real git process should fail fast
        # and the function must return an empty list, never raise.
        tags = update_check._fetch_remote_tags(
            "https://example.invalid/definitely-does-not-exist.git", timeout=2
        )
        self.assertEqual(list(tags), [])

    def test_blackhole_host_bounds_wallclock_real_subprocess(self):
        # Regression test for fg-a10914 attempt-2 P1 (verifier-proven):
        # example.invalid above is a DNS NXDOMAIN, which fails fast and
        # never exercises the actual bug. 192.0.2.55 is an RFC5737
        # TEST-NET-1 address -- guaranteed never to route on the real
        # internet, needs no network access of its own, and makes no real
        # connection to anything; it just reproduces "packets vanish, TCP
        # sits waiting" the same way a firewalled/unroutable mirror host
        # would. Before the tree-reap fix, git's http transport-helper
        # grandchild kept the stdout pipe open past our own timeout and
        # communicate() blocked ~21s (verifier-measured). The bound below
        # (8s) is generous-but-meaningful slack: comfortably below the old
        # ~21s bug and below hooks.json's 10s hook timeout, while still
        # loosely covering the worst case of this fix's own two extra
        # bounded steps (the initial <=2s communicate, then up to a 3s
        # taskkill call, then a final <=2s drain -- ~7s worst case on
        # Windows; POSIX's os.killpg path has no such extra step).
        start = time.monotonic()
        tags = update_check._fetch_remote_tags(
            "http://192.0.2.55/definitely-a-blackhole.git", timeout=2
        )
        elapsed = time.monotonic() - start
        self.assertEqual(list(tags), [])
        self.assertLess(
            elapsed, 8.0,
            f"_fetch_remote_tags against a blackhole host took {elapsed:.2f}s "
            "(expected well under the 8s bound -- process-tree reap on "
            "timeout may have regressed)",
        )

    def test_blackhole_host_bounds_wallclock_through_check_for_update(self):
        # Same regression, exercised end-to-end through check_for_update()
        # (the actual SessionStart entry point) rather than the lower-level
        # helper directly -- matches how the verifier reproduced the bug.
        self._stale_cache()
        start = time.monotonic()
        result = update_check.check_for_update(
            mirror_url="http://192.0.2.55/definitely-a-blackhole.git",
            cache_path=self.cache_path,
            installed_version="0.10.0",
        )
        elapsed = time.monotonic() - start
        self.assertIsNone(result)
        self.assertLess(
            elapsed, 8.0,
            f"check_for_update against a blackhole host took {elapsed:.2f}s "
            "(expected well under the 8s bound)",
        )


class TestVersionCompare(UpdateCheckTestBase):
    def test_remote_newer_reports_the_newer_version(self):
        self._stale_cache()
        with patch("update_check._fetch_remote_tags", return_value=["v0.9.0", "v0.11.0"]):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertEqual(result, "0.11.0")

    def test_remote_older_reports_nothing(self):
        self._stale_cache()
        with patch("update_check._fetch_remote_tags", return_value=["v0.9.0"]):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertIsNone(result)

    def test_remote_equal_reports_nothing(self):
        self._stale_cache()
        with patch("update_check._fetch_remote_tags", return_value=["v0.10.0"]):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertIsNone(result)

    def test_picks_highest_of_multiple_valid_tags_ignoring_junk(self):
        self._stale_cache()
        with patch(
            "update_check._fetch_remote_tags",
            return_value=["v0.10.1", "not-a-tag", "v0.9.9", "v1.0.0", "v0.10.2"],
        ):
            result = update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        self.assertEqual(result, "1.0.0")


class _FakeProc:
    """Stand-in for subprocess.Popen's return value, for tests that must
    not spawn a real process. communicate() either returns immediately or
    raises TimeoutExpired once, then returns on the retry -- matching how
    _fetch_remote_tags calls communicate() a second time after killing the
    tree."""

    def __init__(self, stdout="", stderr="", returncode=0, timeout_first=False):
        self.pid = 424242
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self._timeout_first = timeout_first
        self._communicate_calls = 0
        self.killed = False

    def communicate(self, timeout=None):
        self._communicate_calls += 1
        if self._timeout_first and self._communicate_calls == 1:
            raise subprocess.TimeoutExpired(cmd="git", timeout=timeout)
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


class TestFetchRemoteTagsParsing(unittest.TestCase):
    """_fetch_remote_tags uses subprocess.Popen (not subprocess.run) so the
    whole process tree can be reaped on timeout (fg-a10914 attempt-2 P1) --
    these tests mock Popen accordingly rather than spawning real git."""

    def test_parses_ls_remote_output_and_strips_dereferenced_suffix(self):
        fake_stdout = (
            "abc123\trefs/heads/main\n"
            "def456\trefs/tags/v0.10.0\n"
            "ghi789\trefs/tags/v0.10.0^{}\n"
            "jkl012\trefs/tags/v0.11.0\n"
        )
        fake_proc = _FakeProc(stdout=fake_stdout, returncode=0)
        with patch("update_check.subprocess.Popen", return_value=fake_proc):
            tags = update_check._fetch_remote_tags("https://example.invalid/x.git")
        self.assertEqual(set(tags), {"v0.10.0", "v0.11.0"})

    def test_nonzero_returncode_yields_empty_list(self):
        fake_proc = _FakeProc(stdout="", stderr="fatal", returncode=128)
        with patch("update_check.subprocess.Popen", return_value=fake_proc):
            tags = update_check._fetch_remote_tags("https://example.invalid/x.git")
        self.assertEqual(list(tags), [])

    def test_popen_raising_oserror_yields_empty_list(self):
        # git binary missing entirely.
        with patch("update_check.subprocess.Popen", side_effect=OSError("no such file")):
            tags = update_check._fetch_remote_tags("https://example.invalid/x.git")
        self.assertEqual(list(tags), [])

    def test_timeout_kills_process_tree_and_still_returns_empty_list(self):
        # Pins the P1 fix's actual mechanism: on TimeoutExpired,
        # _fetch_remote_tags must call the tree-reap helper (not just
        # proc.kill()) before giving up, and must still return cleanly.
        fake_proc = _FakeProc(stdout="", returncode=-9, timeout_first=True)
        with patch("update_check.subprocess.Popen", return_value=fake_proc), patch(
            "update_check._kill_process_tree"
        ) as kill_tree:
            tags = update_check._fetch_remote_tags("http://192.0.2.55/x.git", timeout=2)
        kill_tree.assert_called_once_with(fake_proc)
        self.assertEqual(list(tags), [])

    def test_kill_process_tree_uses_taskkill_tree_flag_on_windows(self):
        fake_proc = _FakeProc()
        fake_proc.pid = 13579
        with patch("update_check.sys.platform", "win32"), patch(
            "update_check.subprocess.run"
        ) as run_mock:
            update_check._kill_process_tree(fake_proc)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(args[0], "taskkill")
        self.assertIn("/T", args)  # the tree flag -- the whole point of the fix
        self.assertIn("/F", args)
        self.assertIn(str(fake_proc.pid), args)
        self.assertTrue(fake_proc.killed)

    def test_kill_process_tree_never_raises_even_if_taskkill_itself_fails(self):
        fake_proc = _FakeProc()
        with patch("update_check.sys.platform", "win32"), patch(
            "update_check.subprocess.run", side_effect=OSError("taskkill missing")
        ):
            update_check._kill_process_tree(fake_proc)  # must not raise
        self.assertTrue(fake_proc.killed)


class TestOutputShape(unittest.TestCase):
    def test_main_prints_exactly_one_line_when_newer(self):
        with patch("update_check.check_for_update", return_value="0.11.0"):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = update_check.main([])
        self.assertEqual(rc, 0)
        lines = buf.getvalue().splitlines()
        # Lowercase "forge" to match commands/status.md's pin-locked
        # fg-a10907 version-skew nudge wording ("forge v<installed>
        # installed, ...") -- the two version-nudge lines must stay
        # visually consistent, and that one is pin-locked, so this side
        # conforms to it (fg-a10914 attempt-2 bounce, P3).
        self.assertEqual(lines, ["forge v0.11.0 available — run /forge:update"])

    def test_main_prints_nothing_when_not_newer(self):
        with patch("update_check.check_for_update", return_value=None):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = update_check.main([])
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue(), "")


class TestRealPluginJsonIntegration(unittest.TestCase):
    """Uses the real repo plugin.json (read-only) — no mocking of the file
    system layer here, just proof _installed_version reads the real file
    Forge ships."""

    def test_installed_version_reads_real_plugin_json(self):
        version = update_check._installed_version()
        self.assertIsNotNone(version)
        self.assertIsNotNone(update_check.parse_semver(version))

    def test_mirror_url_points_at_the_public_mirror(self):
        # Pins the fg-a10915 activation: the update nudge is live and points
        # at the real public mirror repo, not the pre-release empty
        # placeholder.
        self.assertEqual(
            update_check.MIRROR_URL, "https://github.com/BenMacDeezy/Orns-Forge.git"
        )


class TestNoStrayWrites(UpdateCheckTestBase):
    def test_check_for_update_only_ever_writes_the_cache_file(self):
        before = set(pathlib.Path(self._tmp.name).iterdir())
        with patch("update_check._fetch_remote_tags", return_value=["v0.10.1"]):
            update_check.check_for_update(
                mirror_url="https://example.invalid/forge-mirror.git",
                cache_path=self.cache_path,
                installed_version="0.10.0",
            )
        after = set(pathlib.Path(self._tmp.name).iterdir())
        self.assertEqual(after - before, {self.cache_path})


@unittest.skipIf(BASH is None, "bash not found on PATH; cannot exercise the hook wrapper")
class TestUpdateNudgeHookWrapper(unittest.TestCase):
    """Exercises the real hooks/scripts/update-nudge.sh wrapper: it must
    wrap tools/update_check.py's stdout into a SessionStart
    hookSpecificOutput envelope when there's a line to report, and stay
    completely silent otherwise -- fail-silent, never blocks."""

    def _run(self, fake_plugin_root):
        env = dict(os.environ)
        env["CLAUDE_PLUGIN_ROOT"] = str(fake_plugin_root)
        result = subprocess.run(
            [BASH, str(HOOK_SCRIPT)],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode, result.stdout, result.stderr

    def _fake_plugin_root(self, tmp_path, script_body):
        root = pathlib.Path(tmp_path)
        (root / "tools").mkdir(parents=True, exist_ok=True)
        (root / "tools" / "update_check.py").write_text(script_body, encoding="utf-8")
        return root

    def test_wraps_update_line_into_session_start_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fake_plugin_root(
                tmp, "print('forge v9.9.9 available — run /forge:update')\n"
            )
            rc, out, _err = self._run(root)
        self.assertEqual(rc, 0)
        self.assertIn('"hookSpecificOutput"', out)
        self.assertIn("forge v9.9.9 available", out)
        payload = json.loads(out)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_silent_when_underlying_script_prints_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fake_plugin_root(tmp, "")
            rc, out, _err = self._run(root)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_silent_when_underlying_script_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fake_plugin_root(tmp, "raise RuntimeError('boom')\n")
            rc, out, _err = self._run(root)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_silent_when_script_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)  # no tools/update_check.py at all
            rc, out, _err = self._run(root)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_registered_in_hooks_json(self):
        hooks_json = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for group in hooks_json["hooks"].get("SessionStart", [])
            for hook in group.get("hooks", [])
        ]
        self.assertTrue(
            any("update-nudge.sh" in cmd for cmd in commands),
            "update-nudge.sh must be registered under hooks.json's SessionStart",
        )


if __name__ == "__main__":
    unittest.main()
