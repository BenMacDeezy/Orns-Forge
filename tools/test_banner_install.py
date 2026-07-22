"""Tests for the fg-a10904 banner-launcher fix (attempt 1 + the MECHANICAL
bounce that folds in the POST-BUILD FINDING and SCOPE RESOLUTION items).

Things pinned here:

1. The original bug fix: hooks/hooks.json must carry NO banner SessionStart
   entry, and hooks/scripts/banner.sh must not exist. `TestHooksJsonNoBanner
   Hook.test_no_banner_sessionstart_entry` is the regression test -- on the
   pre-fix tree (banner.sh wired into SessionStart) it fails, because the
   hook that burned tokens rendering into model context every session was
   still there. That is the revert-red evidence for this task.

2. tools/banner_install.py, the installer for the opt-in launcher shim that
   replaces the removed hook. Every shell-surface transform (marker-block
   upsert/remove, AutoRun chaining) is pure and tested without touching any
   real file outside a tempfile.TemporaryDirectory() and without ever
   calling into the real Windows registry -- registry access is exercised
   only through injected get_fn/set_fn stubs.

3. BOUNCE SCOPE (fg-a10904, folded in after live UX iteration 2026-07-18):
   (1) the ~1.5s post-banner hold in every generated shim body -- the
   Claude TUI wipes the console on launch, so the hold is the only visible
   window; (2) hooks/scripts/orn-motd.sh, the plugin-shipped welcome-area
   hook that replaces the deleted banner.sh with the systemMessage
   display-channel; (3) dedupe of the hand-wired user-level 'orn-motd'
   SessionStart hook once the plugin's own hook covers the same job.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import banner_install  # noqa: E402

HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"
BANNER_SH = REPO_ROOT / "hooks" / "scripts" / "banner.sh"
ORN_MOTD_SH = REPO_ROOT / "hooks" / "scripts" / "orn-motd.sh"
BANNER_PY = REPO_ROOT / "tools" / "banner.py"


def _real_claude_exe(tmp_dir, name="claude.exe"):
    """A real (if fake-content) file standing in for a resolved claude CLI
    path. build_claude_bat/build_powershell_body/build_bash_body now refuse
    (ValueError) a claude_path that is not a real file on disk (the
    placeholder-path guard added for the 3rd real-machine-incident
    hardening -- the incident's own root artifact was the literal
    TEST-FIXTURE string 'C:\\real\\claude.exe' baked into a real shim), so
    every test exercising those generators must pass a real file under a
    tempfile.TemporaryDirectory(), never a bare placeholder string."""
    path = pathlib.Path(tmp_dir) / name
    path.write_text("fake claude cli\n", encoding="utf-8")
    return str(path)


class TestHooksJsonNoBannerHook(unittest.TestCase):
    """Criterion 1: SessionStart must not inject the banner into model
    context. Revert-red: this test fails on the pre-fix tree, where
    hooks.json wires hooks/scripts/banner.sh into a SessionStart matcher."""

    def test_no_banner_sessionstart_entry(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        session_start = data["hooks"]["SessionStart"]
        for entry in session_start:
            for hook in entry.get("hooks", []):
                self.assertNotIn(
                    "banner.sh", hook.get("command", ""),
                    "hooks.json must not reference banner.sh from SessionStart "
                    "-- SessionStart stdout becomes model context, not "
                    "terminal output, so this hook never had a visual payoff",
                )

    def test_hooks_json_is_valid_json(self):
        # Doesn't raise.
        json.loads(HOOKS_JSON.read_text(encoding="utf-8"))

    def test_other_sessionstart_hooks_intact(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        session_start = data["hooks"]["SessionStart"]
        commands = [
            hook.get("command", "")
            for entry in session_start
            for hook in entry.get("hooks", [])
        ]
        self.assertTrue(
            any("session-start-inject.sh" in c for c in commands),
            "session-start-inject.sh must remain wired -- only the banner "
            "hook is removed, not the whole SessionStart lifecycle",
        )

    def test_other_hook_lifecycles_intact(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        commands = []
        for lifecycle, entries in data["hooks"].items():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    commands.append(hook.get("command", ""))
        for expected in ("loop-guard.sh", "staleness-flag.sh", "budget-guard.sh",
                          "session-end-learn.sh"):
            self.assertTrue(
                any(expected in c for c in commands),
                f"{expected} must remain wired -- unrelated to the banner fix",
            )


class TestBannerShAbsent(unittest.TestCase):
    def test_banner_sh_deleted(self):
        self.assertFalse(
            BANNER_SH.exists(),
            "hooks/scripts/banner.sh should be deleted, not left dangling "
            "unreferenced",
        )


class TestOrnMotdWelcomeAreaHook(unittest.TestCase):
    """BOUNCE SCOPE item 2: hooks/scripts/orn-motd.sh is the display-channel
    replacement for the deleted banner.sh -- registered as a SessionStart
    entry, emits {"systemMessage": ...} (the user-DISPLAY channel), and
    stays fail-silent on any failure (emits nothing, never errors loudly)."""

    def test_orn_motd_script_exists(self):
        self.assertTrue(ORN_MOTD_SH.exists(), "hooks/scripts/orn-motd.sh missing")

    def test_orn_motd_registered_in_sessionstart(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        session_start = data["hooks"]["SessionStart"]
        commands = [
            hook.get("command", "")
            for entry in session_start
            for hook in entry.get("hooks", [])
        ]
        self.assertTrue(
            any("orn-motd.sh" in c for c in commands),
            "hooks.json must wire hooks/scripts/orn-motd.sh into SessionStart "
            "-- it is the systemMessage display-channel replacement for the "
            "deleted stdout-only banner.sh",
        )

    def test_orn_motd_uses_plugin_root_var(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        session_start = data["hooks"]["SessionStart"]
        commands = [
            hook.get("command", "")
            for entry in session_start
            for hook in entry.get("hooks", [])
            if "orn-motd.sh" in hook.get("command", "")
        ]
        self.assertTrue(commands, "orn-motd.sh entry not found")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", commands[0])
        self.assertTrue(commands[0].startswith("bash "))

    @unittest.skipIf(shutil.which("bash") is None, "bash not found on PATH")
    def test_orn_motd_emits_valid_json_with_system_message_live(self):
        # Live run against the real tools/banner.py in this repo -- the
        # actual display-channel payload the welcome area would render.
        env = dict(os.environ)
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
        result = subprocess.run(
            [shutil.which("bash"), str(ORN_MOTD_SH)],
            capture_output=True, text=True, env=env, timeout=15,
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip(), "expected a JSON line on stdout")
        payload = json.loads(result.stdout)
        self.assertIn("systemMessage", payload)
        self.assertTrue(payload["systemMessage"])

    @unittest.skipIf(shutil.which("bash") is None, "bash not found on PATH")
    def test_orn_motd_emits_nothing_when_banner_py_missing(self):
        # Fail-silent contract: point CLAUDE_PLUGIN_ROOT at a fake plugin
        # root with no tools/banner.py at all and confirm zero stdout.
        with tempfile.TemporaryDirectory() as tmp:
            fake_root = pathlib.Path(tmp)
            (fake_root / "tools").mkdir(parents=True)
            env = dict(os.environ)
            env["CLAUDE_PLUGIN_ROOT"] = str(fake_root)
            env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
            result = subprocess.run(
                [shutil.which("bash"), str(ORN_MOTD_SH)],
                capture_output=True, text=True, env=env, timeout=15,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    @unittest.skipIf(shutil.which("bash") is None, "bash not found on PATH")
    def test_orn_motd_respects_startup_banner_off_toggle(self):
        # banner.py's own hook_mode() checks .forge/forge.md for
        # `startup-banner: off` -- confirm the wrapper script surfaces that
        # (no stdout at all) rather than swallowing/overriding it.
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp)
            forge_dir = project / ".forge"
            forge_dir.mkdir(parents=True)
            (forge_dir / "forge.md").write_text(
                "# Forge config\n\n## Features\n- startup-banner: off\n",
                encoding="utf-8", newline="\n",
            )
            env = dict(os.environ)
            env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
            env["CLAUDE_PROJECT_DIR"] = str(project)
            result = subprocess.run(
                [shutil.which("bash"), str(ORN_MOTD_SH)],
                capture_output=True, text=True, env=env, timeout=15,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")


class TestMarkerBlockUpsert(unittest.TestCase):
    """Pure-text-transform tests -- no filesystem I/O."""

    def test_install_on_empty_text_appends_block(self):
        text, action = banner_install.upsert_marker_block("", "body line")
        self.assertEqual(action, "installed")
        self.assertIn(banner_install.MARKER_START, text)
        self.assertIn(banner_install.MARKER_END, text)
        self.assertIn("body line", text)

    def test_reinstall_same_body_is_idempotent(self):
        text1, action1 = banner_install.upsert_marker_block("", "body line")
        text2, action2 = banner_install.upsert_marker_block(text1, "body line")
        self.assertEqual(action1, "installed")
        self.assertEqual(action2, "unchanged")
        self.assertEqual(text1, text2)

    def test_reinstall_different_body_upgrades_in_place(self):
        text1, _ = banner_install.upsert_marker_block("", "old body")
        text2, action = banner_install.upsert_marker_block(text1, "new body")
        self.assertEqual(action, "upgraded")
        self.assertNotIn("old body", text2)
        self.assertIn("new body", text2)
        # Exactly one block survives.
        self.assertEqual(text2.count(banner_install.MARKER_START), 1)

    def test_hand_rolled_block_is_detected_and_upgraded(self):
        # Simulates the 2026-07-18 hand fix: same markers, hand-written body.
        hand_rolled = (
            "# some other profile content\n\n"
            f"{banner_install.MARKER_START}\n"
            "function claude { & 'C:\\hand\\path\\claude.exe' @args }\n"
            f"{banner_install.MARKER_END}\n"
        )
        new_text, action = banner_install.upsert_marker_block(
            hand_rolled, "function claude { <generated> }")
        self.assertEqual(action, "upgraded")
        self.assertNotIn("hand\\path", new_text)
        self.assertIn("<generated>", new_text)
        self.assertIn("# some other profile content", new_text)

    def test_unrelated_content_preserved_around_block(self):
        existing = "Set-Alias foo bar\n\n"
        text, _ = banner_install.upsert_marker_block(existing, "body")
        self.assertIn("Set-Alias foo bar", text)


class TestMarkerBlockRemove(unittest.TestCase):
    def test_remove_present_block(self):
        text, _ = banner_install.upsert_marker_block("prefix\n", "body")
        new_text, removed = banner_install.remove_marker_block(text)
        self.assertTrue(removed)
        self.assertNotIn(banner_install.MARKER_START, new_text)
        self.assertNotIn(banner_install.MARKER_END, new_text)
        self.assertIn("prefix", new_text)

    def test_remove_absent_block_is_noop(self):
        text = "nothing to see here\n"
        new_text, removed = banner_install.remove_marker_block(text)
        self.assertFalse(removed)
        self.assertEqual(new_text, text)

    def test_remove_leaves_unrelated_content_around_block(self):
        existing = "before-line\n"
        with_block, _ = banner_install.upsert_marker_block(existing, "body")
        with_block += "after-line\n"
        new_text, removed = banner_install.remove_marker_block(with_block)
        self.assertTrue(removed)
        self.assertIn("before-line", new_text)
        self.assertIn("after-line", new_text)
        self.assertNotIn(banner_install.MARKER_START, new_text)


class TestInstallUninstallFileRoundTrip(unittest.TestCase):
    """Fixture-based on temp files -- never touches the real $PROFILE."""

    def test_install_twice_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = pathlib.Path(tmp) / "profile.ps1"
            action1 = banner_install.install_into_file(profile, "function claude { X }")
            content1 = profile.read_text(encoding="utf-8")
            action2 = banner_install.install_into_file(profile, "function claude { X }")
            content2 = profile.read_text(encoding="utf-8")
            self.assertEqual(action1, "installed")
            self.assertEqual(action2, "unchanged")
            self.assertEqual(content1, content2)

    def test_uninstall_round_trip_removes_exactly_the_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = pathlib.Path(tmp) / "profile.ps1"
            profile.write_text("# my custom prompt\nSet-Alias ll ls\n", encoding="utf-8")
            banner_install.install_into_file(profile, "function claude { X }")
            self.assertEqual(banner_install.status_of_file(profile), "installed")

            action = banner_install.uninstall_from_file(profile)
            self.assertEqual(action, "removed")
            final = profile.read_text(encoding="utf-8")
            self.assertNotIn(banner_install.MARKER_START, final)
            self.assertIn("# my custom prompt", final)
            self.assertIn("Set-Alias ll ls", final)
            self.assertEqual(banner_install.status_of_file(profile), "not installed")

            # Second uninstall is a clean no-op.
            action2 = banner_install.uninstall_from_file(profile)
            self.assertEqual(action2, "absent")

    def test_uninstall_missing_file_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = pathlib.Path(tmp) / "does-not-exist.ps1"
            self.assertEqual(banner_install.uninstall_from_file(profile), "absent")


class TestAutoRunChainingPureLogic(unittest.TestCase):
    """AutoRun chaining decisions, no registry I/O."""

    def test_empty_existing_value_installs_bare(self):
        result = banner_install.compute_new_autorun(None, '"C:\\shims\\forge-autorun.cmd"')
        self.assertEqual(result, '"C:\\shims\\forge-autorun.cmd"')

        result_empty_str = banner_install.compute_new_autorun("", '"ours.cmd"')
        self.assertEqual(result_empty_str, '"ours.cmd"')

    def test_existing_unrelated_value_is_chained(self):
        result = banner_install.compute_new_autorun(
            "echo hello", '"C:\\shims\\forge-autorun.cmd"')
        self.assertEqual(result, 'echo hello & "C:\\shims\\forge-autorun.cmd"')

    def test_already_ours_is_idempotent(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        existing = f"echo hello & {ours}"
        result = banner_install.compute_new_autorun(existing, ours)
        self.assertEqual(result, existing)  # unchanged, not double-chained

    def test_uninstall_removes_only_our_segment_when_chained(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        existing = f"echo hello & {ours}"
        result = banner_install.compute_autorun_after_uninstall(existing, ours)
        self.assertEqual(result, "echo hello")

    def test_uninstall_when_we_are_the_only_segment_clears_value(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        result = banner_install.compute_autorun_after_uninstall(ours, ours)
        self.assertIsNone(result)

    def test_uninstall_when_ours_is_first_segment(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        existing = f"{ours} & echo hello"
        result = banner_install.compute_autorun_after_uninstall(existing, ours)
        self.assertEqual(result, "echo hello")

    def test_uninstall_when_absent_is_noop(self):
        result = banner_install.compute_autorun_after_uninstall("echo hello", '"ours.cmd"')
        self.assertEqual(result, "echo hello")


class TestAutoRunOrchestrationWithStubbedRegistry(unittest.TestCase):
    """install_autorun/uninstall_autorun exercised end-to-end via injected
    get_fn/set_fn -- the real registry is never touched here."""

    def _stub(self, initial=None):
        state = {"value": initial}

        def get_fn():
            return state["value"]

        def set_fn(value):
            state["value"] = value

        return state, get_fn, set_fn

    def test_install_from_empty_registry(self):
        state, get_fn, set_fn = self._stub(initial=None)
        action, new_value = banner_install.install_autorun(
            "C:\\shims\\forge-autorun.cmd", get_fn=get_fn, set_fn=set_fn)
        self.assertEqual(action, "installed")
        self.assertEqual(state["value"], new_value)
        self.assertIn("forge-autorun.cmd", new_value)

    def test_install_chains_existing_value(self):
        state, get_fn, set_fn = self._stub(initial="echo existing")
        action, new_value = banner_install.install_autorun(
            "C:\\shims\\forge-autorun.cmd", get_fn=get_fn, set_fn=set_fn)
        self.assertEqual(action, "chained")
        self.assertIn("echo existing", new_value)
        self.assertIn("forge-autorun.cmd", new_value)

    def test_reinstall_is_unchanged_and_does_not_double_chain(self):
        state, get_fn, set_fn = self._stub(initial=None)
        banner_install.install_autorun("C:\\shims\\forge-autorun.cmd",
                                        get_fn=get_fn, set_fn=set_fn)
        action2, new_value2 = banner_install.install_autorun(
            "C:\\shims\\forge-autorun.cmd", get_fn=get_fn, set_fn=set_fn)
        self.assertEqual(action2, "unchanged")
        self.assertEqual(new_value2.count("forge-autorun.cmd"), 1)

    def test_uninstall_clears_value_when_we_are_only_occupant(self):
        state, get_fn, set_fn = self._stub(initial=None)
        banner_install.install_autorun("C:\\shims\\forge-autorun.cmd",
                                        get_fn=get_fn, set_fn=set_fn)
        action, new_value = banner_install.uninstall_autorun(
            "C:\\shims\\forge-autorun.cmd", get_fn=get_fn, set_fn=set_fn)
        self.assertEqual(action, "removed")
        self.assertIsNone(new_value)
        self.assertIsNone(state["value"])

    def test_uninstall_on_untouched_registry_is_absent(self):
        state, get_fn, set_fn = self._stub(initial=None)
        action, new_value = banner_install.uninstall_autorun(
            "C:\\shims\\forge-autorun.cmd", get_fn=get_fn, set_fn=set_fn)
        self.assertEqual(action, "absent")


class TestRegistryFunctionsAreImportGuarded(unittest.TestCase):
    """The suite must still pass on non-Windows: winreg-backed functions
    must raise a clean, catchable error rather than an ImportError/NameError
    surfacing from module import (module-level import is already guarded by
    a try/except ImportError at the top of banner_install.py)."""

    def test_module_imports_regardless_of_platform(self):
        # If we got this far, the module-level `import winreg` guard worked.
        self.assertTrue(hasattr(banner_install, "winreg"))

    @unittest.skipIf(os.name == "nt", "only exercises the non-Windows guard path")
    def test_registry_functions_raise_cleanly_without_winreg(self):
        with self.assertRaises(RuntimeError):
            banner_install.get_autorun_value()
        with self.assertRaises(RuntimeError):
            banner_install.set_autorun_value("x")
        with self.assertRaises(RuntimeError):
            banner_install.delete_autorun_value()

    @unittest.skipUnless(os.name == "nt" and banner_install.winreg is not None,
                          "windows registry not available")
    def test_registry_functions_are_callable_on_windows(self):
        # Only asserts the functions exist and are the real (non-None)
        # winreg-backed implementations -- deliberately does NOT call them,
        # per the task's explicit instruction not to touch the real
        # registry from tests.
        self.assertTrue(callable(banner_install.get_autorun_value))
        self.assertTrue(callable(banner_install.set_autorun_value))


class TestSkipPrintLogicInGeneratedShims(unittest.TestCase):
    """-p/--print must be recognized and skip the banner in every
    generated shim, per criterion 2."""

    def test_powershell_body_skips_print_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = banner_install.build_powershell_body(
                _real_claude_exe(tmp), _real_claude_exe(tmp, "python.exe"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("-p", body)
        self.assertIn("--print", body)
        # fg-a10905: python is invoked directly, never piped through
        # Out-Host (piping breaks the --anim cursor-up redraw loop).
        self.assertNotIn("Out-Host", body)
        self.assertIn("try", body)
        self.assertIn("catch", body)

    def test_bash_body_skips_print_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = banner_install.build_bash_body(
                _real_claude_exe(tmp, "claude"), _real_claude_exe(tmp, "python3"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("-p", body)
        self.assertIn("--print", body)

    def test_claude_bat_skips_print_flags_and_fails_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            bat = banner_install.build_claude_bat(
                _real_claude_exe(tmp), _real_claude_exe(tmp, "python.exe"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("-p", bat)
        self.assertIn("--print", bat)
        self.assertIn("2>nul", bat)

    def test_claude_bat_without_resolved_python_still_launches_claude(self):
        # Criterion 4: fall back silently to a plain launch when python or
        # banner.py aren't resolvable -- no banner CALL is generated, and
        # (fg-a10905) there is no separate hold any more to keep either --
        # --anim is self-timed, so an unresolved banner means no visible
        # splash at all, just a plain launch.
        with tempfile.TemporaryDirectory() as tmp:
            claude_path = _real_claude_exe(tmp)
            bat = banner_install.build_claude_bat(claude_path, None, None)
        self.assertIn(claude_path, bat)
        # No banner/recheck CALL is generated -- only the explicit "skipped"
        # comment (F8: matches the PowerShell/bash bodies' own comment) may
        # mention banner.py, never an actual invocation of it.
        self.assertNotIn('"{banner.py}"', bat)
        self.assertIn("REM python/banner.py not resolved at install time; skipped.", bat)
        self.assertNotIn("--anim", bat)
        self.assertNotIn("--recheck-patch", bat)
        self.assertNotIn("ping -n 4 127.0.0.1", bat)  # old separate hold is gone

    def test_powershell_body_without_resolved_python_still_launches_claude(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_path = _real_claude_exe(tmp)
            body = banner_install.build_powershell_body(claude_path, None, None)
        self.assertIn(claude_path, body)
        self.assertIn("not resolved at install time", body)
        self.assertNotIn("--anim", body)
        self.assertNotIn("Start-Sleep", body)  # old separate hold is gone

    def test_build_functions_raise_on_placeholder_claude_path(self):
        # The core 3rd-incident regression test: a claude_path that LOOKS
        # like a real path but does not exist on disk (exactly the
        # 'C:\\real\\claude.exe' shape found on the real machine) must be
        # refused by every shim body generator, not silently baked in.
        for builder in (
            lambda p: banner_install.build_powershell_body(p, None, None),
            lambda p: banner_install.build_bash_body(p, None, None),
            lambda p: banner_install.build_claude_bat(p, None, None),
        ):
            with self.assertRaises(ValueError):
                builder("C:\\real\\claude.exe")

    def test_build_functions_allow_none_claude_path(self):
        # None (never resolved at install time) is a legitimate, expected
        # value -- distinct from a placeholder string -- and must not
        # raise; each generator's own "not resolved" fallback handles it.
        self.assertIsInstance(banner_install.build_powershell_body(None, None, None), str)
        self.assertIsInstance(banner_install.build_bash_body(None, None, None), str)
        self.assertIsInstance(banner_install.build_claude_bat(None, None, None), str)


class TestAnimInvocation(unittest.TestCase):
    """fg-a10905: shims call `python banner.py --anim` INSTEAD of a static
    banner print + separate sleep hold -- the animation is self-timed
    (~2.6s), so it IS the launch-visibility hold fg-a10904's POST-BUILD
    FINDING established was needed (the Claude TUI wipes the console via
    an alternate screen buffer on launch). All three generated shim bodies
    invoke it inside the SAME -p/--print skip-guard as before, and none of
    them carry the old separate hold (Start-Sleep / sleep 3 / ping) any
    more.

    CRITICAL INVARIANT: the PowerShell body invokes python DIRECTLY --
    never through `| Out-Host` -- because piping captures stdout as objects
    and buffers it until the process exits, which breaks the animation's
    cursor-up + \\x1b[2K redraw loop (only the last frame would ever
    render)."""

    def test_powershell_body_invokes_anim_directly_no_pipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = banner_install.build_powershell_body(
                _real_claude_exe(tmp), _real_claude_exe(tmp, "python.exe"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("--anim", body)
        self.assertNotIn("Out-Host", body)
        self.assertNotIn("Start-Sleep", body)
        guard_idx = body.index("if (($args -notcontains '-p')")
        anim_idx = body.index("--anim")
        # The anim call sits after the guard opens and before that guard's
        # own closing brace (the first bare "    }" line after the call).
        close_idx = body.index("\n    }\n", anim_idx)
        self.assertTrue(guard_idx < anim_idx < close_idx)

    def test_bash_body_invokes_anim_inside_skip_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = banner_install.build_bash_body(
                _real_claude_exe(tmp, "claude"), _real_claude_exe(tmp, "python3"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("--anim", body)
        self.assertNotIn("sleep 3", body)
        guard_idx = body.index('if [ "$__forge_skip_banner" -eq 0 ]')
        anim_idx = body.index("--anim")
        fi_idx = body.index("fi", anim_idx)
        self.assertTrue(guard_idx < anim_idx < fi_idx)

    def test_claude_bat_invokes_anim_inside_skip_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            bat = banner_install.build_claude_bat(
                _real_claude_exe(tmp), _real_claude_exe(tmp, "python.exe"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("--anim", bat)
        self.assertNotIn("ping -n 4 127.0.0.1", bat)
        guard_idx = bat.index('if "%FORGE_SKIP_BANNER%"=="0"')
        anim_idx = bat.index("--anim")
        close_idx = bat.index("\r\n)\r\n", anim_idx)
        self.assertTrue(guard_idx < anim_idx < close_idx)

    def test_print_mode_skips_the_anim_call_entirely(self):
        # -p/--print never enter the guard at all -- pins that the anim
        # call is gated by that single condition, nothing else.
        with tempfile.TemporaryDirectory() as tmp:
            claude_path = _real_claude_exe(tmp)
            python_path = _real_claude_exe(tmp, "python.exe")
            banner_py_path = _real_claude_exe(tmp, "banner.py")
            ps_body = banner_install.build_powershell_body(
                claude_path, python_path, banner_py_path)
            guard_line = next(
                line for line in ps_body.splitlines() if "notcontains" in line
            )
            self.assertIn("'-p'", guard_line)
            self.assertIn("'--print'", guard_line)
            bat = banner_install.build_claude_bat(
                claude_path, python_path, banner_py_path)
        block = bat[bat.index('if "%FORGE_SKIP_BANNER%"=="0" ('):]
        block = block[:block.index("\r\n)\r\n") + len("\r\n)\r\n")]
        self.assertIn("--anim", block)


class TestBannerPyResolution(unittest.TestCase):
    def test_falls_back_to_dev_tree_when_no_plugin_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No ~/.claude/plugins/installed_plugins.json under this fake home.
            resolved = banner_install.resolve_banner_py_path(home=tmp)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.name, "banner.py")
            self.assertTrue(resolved.is_file())

    def test_reads_installed_plugin_cache_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            plugins_dir = home / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True)
            fake_install = home / "fake-cache" / "forge" / "0.7.11"
            (fake_install / "tools").mkdir(parents=True)
            banner_py = fake_install / "tools" / "banner.py"
            banner_py.write_text("# fake banner.py\n", encoding="utf-8")
            manifest = {
                "version": 2,
                "plugins": {
                    "forge@forge-local": [
                        {"scope": "user", "installPath": str(fake_install),
                         "version": "0.7.11"}
                    ]
                },
            }
            (plugins_dir / "installed_plugins.json").write_text(
                json.dumps(manifest), encoding="utf-8")

            resolved = banner_install.resolve_banner_py_path(home=home)
            self.assertEqual(resolved, banner_py)

    def test_resolves_orns_forge_key_and_prefers_it_over_forge_local(self):
        # fg-a10916: the marketplace half of the key varies (orns-forge
        # post-rename, forge-local pre-migration, any forge@<marketplace>
        # for a public install) -- resolution must find all three shapes,
        # preferring the current orns-forge identity when both exist.
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            plugins_dir = home / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True)
            new_install = home / "cache-new" / "forge" / "0.11.0"
            old_install = home / "cache-old" / "forge" / "0.10.0"
            for root in (new_install, old_install):
                (root / "tools").mkdir(parents=True)
                (root / "tools" / "banner.py").write_text(
                    "# fake banner.py\n", encoding="utf-8")
            manifest = {
                "version": 2,
                "plugins": {
                    "forge@forge-local": [
                        {"scope": "user", "installPath": str(old_install),
                         "version": "0.10.0"}
                    ],
                    "forge@orns-forge": [
                        {"scope": "user", "installPath": str(new_install),
                         "version": "0.11.0"}
                    ],
                },
            }
            (plugins_dir / "installed_plugins.json").write_text(
                json.dumps(manifest), encoding="utf-8")
            resolved = banner_install.resolve_banner_py_path(home=home)
            self.assertEqual(resolved, new_install / "tools" / "banner.py")

    def test_resolves_any_forge_marketplace_key_as_fallback(self):
        # A public install may use a marketplace name we've never heard of;
        # any forge@<marketplace> key must still resolve.
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            plugins_dir = home / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True)
            fake_install = home / "cache-x" / "forge" / "1.0.0"
            (fake_install / "tools").mkdir(parents=True)
            banner_py = fake_install / "tools" / "banner.py"
            banner_py.write_text("# fake banner.py\n", encoding="utf-8")
            manifest = {
                "version": 2,
                "plugins": {
                    "forge@somebody-elses-marketplace": [
                        {"scope": "user", "installPath": str(fake_install),
                         "version": "1.0.0"}
                    ],
                    "other-plugin@shop": [
                        {"scope": "user", "installPath": str(home / "nope"),
                         "version": "9.9.9"}
                    ],
                },
            }
            (plugins_dir / "installed_plugins.json").write_text(
                json.dumps(manifest), encoding="utf-8")
            resolved = banner_install.resolve_banner_py_path(home=home)
            self.assertEqual(resolved, banner_py)

    def test_malformed_installed_plugins_json_falls_back_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            plugins_dir = home / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True)
            (plugins_dir / "installed_plugins.json").write_text(
                "{ not valid json", encoding="utf-8")
            resolved = banner_install.resolve_banner_py_path(home=home)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.name, "banner.py")


class TestPythonInterpreterHelpers(unittest.TestCase):
    def test_windowsapps_stub_is_identified(self):
        self.assertTrue(banner_install._is_windowsapps_stub(
            "C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe"))
        self.assertFalse(banner_install._is_windowsapps_stub(
            "C:\\Python312\\python.exe"))

    def test_real_running_interpreter_reports_as_runnable(self):
        self.assertTrue(banner_install._python_actually_runs(sys.executable))

    def test_nonexistent_interpreter_reports_as_not_runnable(self):
        self.assertFalse(banner_install._python_actually_runs(
            "C:\\definitely\\not\\a\\real\\path\\python.exe"))


class TestOrnMotdDedupePureLogic(unittest.TestCase):
    """BOUNCE SCOPE item 3: once the plugin ships its own welcome-area hook
    (hooks/scripts/orn-motd.sh), a hand-wired user-level SessionStart entry
    referencing 'orn-motd' (e.g. the 2026-07-18 hand fix at
    C:\\Users\\<user>\\.claude\\orn-motd.py, wired into
    ~/.claude/settings.json) would print the örn art twice. These are pure,
    no-I/O tests of the detection/removal transform, mirroring the
    marker-block and AutoRun pure-logic tests above."""

    def _settings_with_orn_motd(self, extra_lifecycle_hook=None):
        session_start_hooks = [
            {
                "matcher": "startup",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python \"C:\\\\Users\\\\someone\\\\.claude\\\\orn-motd.py\"",
                        "timeout": 10,
                    }
                ],
            }
        ]
        if extra_lifecycle_hook:
            session_start_hooks.append(extra_lifecycle_hook)
        return {
            "hooks": {
                "SessionStart": session_start_hooks,
            }
        }

    def test_find_orn_motd_hook_indices_detects_entry(self):
        data = self._settings_with_orn_motd()
        hits = banner_install.find_orn_motd_hook_indices(data["hooks"])
        self.assertEqual(hits, [("SessionStart", 0, 0)])

    def test_find_orn_motd_hook_indices_empty_when_absent(self):
        data = {"SessionStart": [{"matcher": "startup", "hooks": [
            {"type": "command", "command": "bash unrelated.sh"}
        ]}]}
        self.assertEqual(banner_install.find_orn_motd_hook_indices(data), [])

    def test_remove_orn_motd_hooks_detected_and_removed(self):
        data = self._settings_with_orn_motd()
        new_data, removed = banner_install.remove_orn_motd_hooks(data)
        self.assertEqual(removed, 1)
        self.assertNotIn("SessionStart", new_data.get("hooks", {}))

    def test_remove_orn_motd_hooks_preserves_unrelated_entries(self):
        # A matcher-group with BOTH an orn-motd entry and an unrelated one:
        # only the orn-motd entry is removed, the group and the other hook
        # survive.
        other_hook = {"type": "command", "command": "bash something-else.sh"}
        data = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [
                            {"type": "command",
                             "command": "python orn-motd.py"},
                            other_hook,
                        ],
                    }
                ],
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": "bash unrelated-lifecycle.sh"}]}
                ],
            }
        }
        new_data, removed = banner_install.remove_orn_motd_hooks(data)
        self.assertEqual(removed, 1)
        self.assertEqual(
            new_data["hooks"]["SessionStart"][0]["hooks"], [other_hook]
        )
        self.assertIn("UserPromptSubmit", new_data["hooks"])
        self.assertIn(
            "unrelated-lifecycle.sh",
            new_data["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"],
        )

    def test_remove_orn_motd_hooks_noop_when_absent(self):
        data = {"hooks": {"SessionStart": [
            {"matcher": "startup", "hooks": [
                {"type": "command", "command": "bash session-start-inject.sh"}
            ]}
        ]}}
        new_data, removed = banner_install.remove_orn_motd_hooks(data)
        self.assertEqual(removed, 0)
        self.assertEqual(new_data, data)

    def test_remove_orn_motd_hooks_noop_on_no_hooks_key(self):
        new_data, removed = banner_install.remove_orn_motd_hooks({})
        self.assertEqual(removed, 0)
        self.assertEqual(new_data, {})

    def test_remove_orn_motd_hooks_leaves_other_top_level_keys_untouched(self):
        data = self._settings_with_orn_motd()
        data["someOtherSetting"] = {"nested": True}
        new_data, removed = banner_install.remove_orn_motd_hooks(data)
        self.assertEqual(removed, 1)
        self.assertEqual(new_data["someOtherSetting"], {"nested": True})


class TestDedupeUserLevelOrnMotdOrchestration(unittest.TestCase):
    """dedupe_user_level_orn_motd exercised end-to-end via injected
    read_fn/write_fn (mirrors the AutoRun get_fn/set_fn stub pattern) --
    the real ~/.claude/settings.json is never touched here."""

    def _stub(self, initial):
        state = {"value": initial}

        def read_fn():
            return state["value"]

        def write_fn(new_value):
            state["value"] = new_value

        return state, read_fn, write_fn

    def test_detected_case_removes_and_reports(self):
        initial = {
            "hooks": {
                "SessionStart": [
                    {"matcher": "startup", "hooks": [
                        {"type": "command", "command": "python orn-motd.py"}
                    ]}
                ]
            }
        }
        state, read_fn, write_fn = self._stub(initial)
        report = banner_install.dedupe_user_level_orn_motd(
            read_fn=read_fn, write_fn=write_fn)
        self.assertIn("removed 1", report)
        self.assertNotIn("SessionStart", state["value"].get("hooks", {}))

    def test_preserved_case_when_absent(self):
        initial = {"hooks": {"SessionStart": [
            {"matcher": "startup", "hooks": [
                {"type": "command", "command": "bash session-start-inject.sh"}
            ]}
        ]}}
        state, read_fn, write_fn = self._stub(initial)
        report = banner_install.dedupe_user_level_orn_motd(
            read_fn=read_fn, write_fn=write_fn)
        self.assertIn("none found", report)
        # write_fn must not have been invoked with a mutated value -- state
        # stays exactly as it was (write_fn is simply never called on a
        # no-op, but assert the content is unchanged regardless).
        self.assertEqual(state["value"], initial)

    def test_idempotent_second_call_removes_nothing(self):
        initial = {
            "hooks": {
                "SessionStart": [
                    {"matcher": "startup", "hooks": [
                        {"type": "command", "command": "python orn-motd.py"}
                    ]}
                ]
            }
        }
        state, read_fn, write_fn = self._stub(initial)
        banner_install.dedupe_user_level_orn_motd(read_fn=read_fn, write_fn=write_fn)
        report2 = banner_install.dedupe_user_level_orn_motd(read_fn=read_fn, write_fn=write_fn)
        self.assertIn("none found", report2)

    def test_does_not_delete_the_underlying_script_file(self):
        # Restore-safe contract: dedupe only ever touches the settings.json
        # document handed to it via read_fn/write_fn -- it has no filesystem
        # access to the script path the removed command referenced, so
        # there is no code path by which it could delete
        # C:\Users\<user>\.claude\orn-motd.py.
        with tempfile.TemporaryDirectory() as tmp:
            script = pathlib.Path(tmp) / "orn-motd.py"
            script.write_text("# hand-wired hook\n", encoding="utf-8")
            initial = {
                "hooks": {
                    "SessionStart": [
                        {"matcher": "startup", "hooks": [
                            {"type": "command",
                             "command": f'python "{script}"'}
                        ]}
                    ]
                }
            }
            state, read_fn, write_fn = self._stub(initial)
            banner_install.dedupe_user_level_orn_motd(read_fn=read_fn, write_fn=write_fn)
            self.assertTrue(script.is_file(), "dedupe must never delete the script file")

    def test_missing_settings_file_reports_none_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = pathlib.Path(tmp) / "does-not-exist" / "settings.json"
            report = banner_install.dedupe_user_level_orn_motd(settings_path=missing_path)
            self.assertIn("none found", report)

    def test_real_settings_file_round_trip_via_tempfile(self):
        # Exercises the real (non-injected) file read/write path, but
        # against a tempfile -- never ~/.claude/settings.json.
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = pathlib.Path(tmp) / "settings.json"
            settings_path.write_text(json.dumps({
                "hooks": {
                    "SessionStart": [
                        {"matcher": "startup", "hooks": [
                            {"type": "command", "command": "python orn-motd.py"},
                        ]}
                    ]
                }
            }), encoding="utf-8")
            report = banner_install.dedupe_user_level_orn_motd(settings_path=settings_path)
            self.assertIn("removed 1", report)
            new_data = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertNotIn("SessionStart", new_data.get("hooks", {}))

    def test_install_all_and_uninstall_all_source_call_dedupe(self):
        # install_all()/uninstall_all() do real filesystem/registry I/O
        # (real $PROFILE, real HKCU) and are deliberately never invoked
        # directly by this suite (see every other orchestration test above,
        # which goes through injected get_fn/set_fn/read_fn/write_fn
        # instead). Confirming the dedupe wiring landed is done at the
        # source level instead of by calling either function against this
        # machine's real ~/.claude/settings.json, which -- per this task's
        # own live-debug notes -- may genuinely carry a hand-wired
        # 'orn-motd' entry that must never be mutated by a test run.
        import inspect
        # inspect.unwrap follows __wrapped__ (set by the tools/conftest.py
        # hermeticity guard) through to the real function -- install_all/
        # uninstall_all are monkeypatched to a guarding wrapper for every
        # test in this package, so getsource on the bare attribute would
        # return the wrapper's source, not the real orchestration logic
        # this test actually pins.
        install_src = inspect.getsource(inspect.unwrap(banner_install.install_all))
        uninstall_src = inspect.getsource(inspect.unwrap(banner_install.uninstall_all))
        self.assertIn("dedupe_user_level_orn_motd(home=home)", install_src)
        self.assertIn("dedupe_user_level_orn_motd(home=home)", uninstall_src)


class TestUtf8SigBomHandling(unittest.TestCase):
    """Bug: _installed_plugin_root and dedupe_user_level_orn_motd read JSON
    with plain 'utf-8' instead of 'utf-8-sig'. A BOM'd file (PowerShell's
    default Out-File/Set-Content writes UTF-8-with-BOM) made json.loads
    raise a JSONDecodeError, silently swallowed by a broad except, breaking
    plugin-root resolution and the örn-banner duplicate-hook dedupe."""

    def test_installed_plugin_root_reads_bom_prefixed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            plugins_dir = home / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True)
            manifest = {
                "version": 2,
                "plugins": {
                    "forge@forge-local": [
                        {"scope": "user", "installPath": "C:\\fake\\install",
                         "version": "0.7.11"}
                    ]
                },
            }
            # Written WITH a UTF-8 BOM, exactly as PowerShell's
            # Out-File/Set-Content would produce.
            (plugins_dir / "installed_plugins.json").write_text(
                json.dumps(manifest), encoding="utf-8-sig")

            root = banner_install._installed_plugin_root(home=home)
            self.assertEqual(
                root, pathlib.Path("C:\\fake\\install"),
                "a BOM'd installed_plugins.json must still resolve the "
                "plugin root, not silently fail via the broad except",
            )

    def test_dedupe_user_level_orn_motd_reads_bom_prefixed_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = pathlib.Path(tmp) / "settings.json"
            data = {
                "hooks": {
                    "SessionStart": [
                        {"matcher": "startup", "hooks": [
                            {"type": "command", "command": "python orn-motd.py"},
                        ]}
                    ]
                }
            }
            settings_path.write_text(json.dumps(data), encoding="utf-8-sig")
            report = banner_install.dedupe_user_level_orn_motd(settings_path=settings_path)
            self.assertIn(
                "removed 1", report,
                "a BOM'd settings.json must still be parsed and deduped, "
                "not reported as 'unreadable'",
            )


class TestFileSurfaceBomHandling(unittest.TestCase):
    """Bug: install_into_file/uninstall_from_file read PowerShell profile /
    bash-rc files with plain 'utf-8' -- a BOM'd profile wasn't stripped on
    read, so the leading U+FEFF character survived inside the in-memory
    text and got rewritten verbatim into the file on the next write."""

    def test_install_into_file_strips_bom_on_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = pathlib.Path(tmp) / "profile.ps1"
            profile.write_text("# my custom prompt\n", encoding="utf-8-sig")
            banner_install.install_into_file(profile, "function claude { X }")
            new_text = profile.read_text(encoding="utf-8")
            self.assertFalse(
                new_text.startswith("﻿"),
                "the BOM must be stripped on read, not preserved and "
                "rewritten unnormalized into the profile",
            )
            self.assertIn("# my custom prompt", new_text)
            self.assertIn(banner_install.MARKER_START, new_text)

    def test_uninstall_from_file_strips_bom_on_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = pathlib.Path(tmp) / "profile.ps1"
            body = ("# my custom prompt\n"
                    f"{banner_install.MARKER_START}\n"
                    "function claude { X }\n"
                    f"{banner_install.MARKER_END}\n")
            profile.write_text(body, encoding="utf-8-sig")
            action = banner_install.uninstall_from_file(profile)
            self.assertEqual(action, "removed")
            final = profile.read_text(encoding="utf-8")
            self.assertFalse(
                final.startswith("﻿"),
                "the BOM must be stripped on read, not preserved and "
                "rewritten unnormalized into the profile",
            )
            self.assertIn("# my custom prompt", final)


class TestAutorunLockPreventsConcurrentRace(unittest.TestCase):
    """Bug: install_autorun/uninstall_autorun did an unsynchronized
    registry read-modify-write (get_fn() then set_fn()), so two concurrent
    `/forge:banner install`/`uninstall` invocations could race and clobber
    each other's change (TOCTOU). Demonstrated with real threads and an
    artificially widened read/write gap to make the race reliable."""

    def test_concurrent_installs_do_not_lose_a_write(self):
        state = {"value": None}

        def get_fn():
            time.sleep(0.05)  # widen the race window between read and write
            return state["value"]

        def set_fn(value):
            time.sleep(0.05)
            state["value"] = value

        results = []

        def worker(cmd_path):
            results.append(
                banner_install.install_autorun(cmd_path, get_fn=get_fn, set_fn=set_fn)
            )

        t1 = threading.Thread(target=worker, args=('"C:\\shims\\a-autorun.cmd"',))
        t2 = threading.Thread(target=worker, args=('"C:\\shims\\b-autorun.cmd"',))
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        final = state["value"] or ""
        self.assertIn(
            "a-autorun.cmd", final,
            "concurrent install_autorun calls must not lose either write -- "
            "without serialization, one thread's set_fn can clobber the "
            "other thread's read-before-write",
        )
        self.assertIn("b-autorun.cmd", final)


class TestAutorunLockStalenessDetection(unittest.TestCase):
    """fg-a11031: a lock file left behind by a crashed process (never
    reached __exit__) must be detected as stale (old mtime) and reclaimed --
    otherwise every subsequent caller waits out the full fixed timeout and
    then proceeds via `return self` with `self._fd` still None, running the
    unsynchronized critical section unprotected (reintroducing the TOCTOU
    race the lock exists to prevent)."""

    def test_stale_lock_file_is_reclaimed_not_waited_out(self):
        tmp_dir = tempfile.mkdtemp()
        lock_path = pathlib.Path(tmp_dir) / "stale.lock"
        lock_path.write_text("stale", encoding="utf-8")
        old_time = time.time() - 3600  # 1 hour old -- clearly abandoned
        os.utime(str(lock_path), (old_time, old_time))

        lock = banner_install._AutorunLock(path=lock_path, timeout=5.0)
        start = time.monotonic()
        with lock:
            elapsed = time.monotonic() - start
            self.assertIsNotNone(
                lock._fd,
                "a stale lock must be reclaimed (real mutual exclusion "
                "acquired), not silently skipped over unprotected",
            )
        self.assertLess(
            elapsed, 4.0,
            "a stale lock must be reclaimed promptly, not waited out over "
            "the full 5s timeout",
        )

    def test_fresh_lock_file_is_not_reclaimed(self):
        tmp_dir = tempfile.mkdtemp()
        lock_path = pathlib.Path(tmp_dir) / "fresh.lock"
        lock_path.write_text("fresh", encoding="utf-8")
        # mtime left at "now" -- a live contender's lock, not abandoned.

        lock = banner_install._AutorunLock(path=lock_path, timeout=0.3)
        with lock:
            self.assertIsNone(
                lock._fd,
                "a fresh, actively-held lock must NOT be reclaimed -- must "
                "wait out the timeout unprotected exactly as before",
            )

    def test_concurrent_callers_reclaim_stale_lock_with_mutual_exclusion(self):
        # Three threads all contend against a pre-existing stale lock; the
        # staleness reclaim must still preserve real mutual exclusion (only
        # ever one os.open(O_CREAT|O_EXCL) winner at a time), not just let
        # everyone through unprotected.
        tmp_dir = tempfile.mkdtemp()
        lock_path = pathlib.Path(tmp_dir) / "stale-concurrent.lock"
        lock_path.write_text("stale", encoding="utf-8")
        old_time = time.time() - 3600
        os.utime(str(lock_path), (old_time, old_time))

        active = {"count": 0}
        max_concurrent = {"value": 0}
        lock_state = threading.Lock()

        def worker():
            with banner_install._AutorunLock(path=lock_path, timeout=5.0) as l:
                self.assertIsNotNone(l._fd, "every caller must actually acquire the lock")
                with lock_state:
                    active["count"] += 1
                    max_concurrent["value"] = max(max_concurrent["value"], active["count"])
                time.sleep(0.05)
                with lock_state:
                    active["count"] -= 1

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(
            max_concurrent["value"], 1,
            "reclaiming a stale lock must not let more than one caller into "
            "the critical section at once",
        )


class TestAutorunUninstallRemovesAllOccurrences(unittest.TestCase):
    """Bug: compute_autorun_after_uninstall only removed the FIRST
    occurrence of our_invocation (.replace(variant, "", 1) + break). If it
    appeared twice (e.g. from prior corrupted state), one stale copy
    survived, referencing a shim file that uninstall then deletes -- a
    dangling broken AutoRun entry."""

    def test_duplicate_occurrence_is_fully_removed(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        existing = f"{ours} & {ours}"
        result = banner_install.compute_autorun_after_uninstall(existing, ours)
        self.assertIsNone(
            result,
            "both copies of our invocation must be removed, leaving nothing",
        )

    def test_duplicate_occurrence_with_other_content_leaves_only_the_other(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        existing = f"echo hello & {ours} & {ours}"
        result = banner_install.compute_autorun_after_uninstall(existing, ours)
        self.assertEqual(result, "echo hello")


class TestAutorunUninstallOperatesOnCompleteSegments(unittest.TestCase):
    """Verify-bounce P1 fix: compute_autorun_after_uninstall used to do a
    raw str.replace() of our_invocation as a SUBSTRING anywhere in the
    AutoRun value. An unrelated command that merely embeds our path inside
    a longer command (e.g. a conditional referencing it) is NOT our
    segment and must survive byte-identical -- only a segment that is
    EXACTLY (case-insensitively, quote-normalized) our invocation may be
    removed."""

    def test_our_path_embedded_in_an_unrelated_command_survives_byte_identical(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        unrelated = f'if exist {ours} echo keep'
        result = banner_install.compute_autorun_after_uninstall(unrelated, ours)
        self.assertEqual(
            result, unrelated,
            "a command that merely references our path, rather than BEING "
            "our invocation as its own segment, must be left byte-identical",
        )

    def test_our_path_embedded_in_an_unrelated_segment_among_others_survives(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        unrelated = f'if exist {ours} echo keep'
        existing = f"echo hello & {unrelated} & {ours}"
        result = banner_install.compute_autorun_after_uninstall(existing, ours)
        self.assertEqual(result, f"echo hello & {unrelated}")

    def test_segment_matching_is_case_insensitive_and_quote_normalized(self):
        ours = '"C:\\shims\\forge-autorun.cmd"'
        # Same path, different case and no surrounding quotes -- still
        # recognized as OUR segment (Windows paths are case-insensitive).
        existing = "echo hello & C:\\SHIMS\\Forge-AutoRun.cmd"
        result = banner_install.compute_autorun_after_uninstall(existing, ours)
        self.assertEqual(result, "echo hello")

    def test_uninstall_autorun_leaves_embedded_reference_untouched(self):
        ours_path = "C:\\shims\\forge-autorun.cmd"
        ours = f'"{ours_path}"'
        unrelated = f'if exist {ours} echo keep'
        state = {"value": unrelated}

        def get_fn():
            return state["value"]

        def set_fn(value):
            state["value"] = value

        action, new_value = banner_install.uninstall_autorun(
            ours_path, get_fn=get_fn, set_fn=set_fn)
        self.assertEqual(action, "absent")
        self.assertEqual(new_value, unrelated)
        self.assertEqual(state["value"], unrelated, "must not have written anything")


class TestInstallAllPartialFailureIsolation(unittest.TestCase):
    """Bug: install_all() had no exception handling around the per-surface
    path.write_text(...) calls -- a failure on ONE surface (e.g.
    PermissionError on a locked PowerShell $PROFILE) crashed the entire
    multi-surface operation and every later surface was never attempted."""

    def test_one_failing_profile_does_not_abort_the_rest(self):
        good_profile = pathlib.Path("C:\\fake\\good_profile.ps1")
        bad_profile = pathlib.Path("C:\\fake\\bad_profile.ps1")

        def fake_install_into_file(path, body, marker_start=banner_install.MARKER_START,
                                    marker_end=banner_install.MARKER_END):
            if path == bad_profile:
                raise PermissionError("Access is denied (simulated lock)")
            return "installed"

        with tempfile.TemporaryDirectory() as shim_tmp:
            claude_path = _real_claude_exe(shim_tmp)
            with patch.object(banner_install, "resolve_claude_cli_path",
                               return_value=claude_path), \
                 patch.object(banner_install, "resolve_python_interpreter",
                               return_value=_real_claude_exe(shim_tmp, "python.exe")), \
                 patch.object(banner_install, "resolve_banner_py_path",
                               return_value=pathlib.Path(_real_claude_exe(shim_tmp, "banner.py"))), \
                 patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[("powershell", good_profile),
                                              ("pwsh", bad_profile)]), \
                 patch.object(banner_install, "detect_shell_rc_files", return_value=[]), \
                 patch.object(banner_install, "install_into_file",
                               side_effect=fake_install_into_file), \
                 patch.object(banner_install, "default_shim_dir",
                               return_value=pathlib.Path(shim_tmp)), \
                 patch.object(banner_install, "scan_legacy_artifacts", return_value=[]), \
                 patch.object(banner_install, "install_autorun",
                               return_value=("unchanged", None)), \
                 patch.object(banner_install, "dedupe_user_level_orn_motd",
                               return_value="user-level orn-motd hook: none found"), \
                 patch.object(banner_install.banner_patch, "apply_patch",
                               return_value={"status": "target-not-found", "target": None,
                                              "message": "stubbed for this test"}):
                # must not raise
                report = banner_install.install_all(confirmed=True, home=shim_tmp)

        joined = "\n".join(report)
        self.assertTrue(
            any("good_profile.ps1" in line and "installed" in line for line in report),
            f"the surface after the failing one should still be attempted: {report}",
        )
        self.assertTrue(
            any("bad_profile.ps1" in line and "FAILED" in line for line in report),
            f"the failing surface should be reported, not raised: {report}",
        )
        self.assertIn("Access is denied", joined)


class TestUninstallAllWarnsOnAutorunMismatch(unittest.TestCase):
    """Bug: uninstall_all deleted the claude.bat/autorun_cmd shim files
    unconditionally, without checking whether uninstall_autorun actually
    confirmed removing the registry reference. If uninstall_autorun reports
    'absent' because of a registry-value MISMATCH (not because it was
    genuinely never installed), the files still got deleted silently,
    leaving a dangling AutoRun entry pointing at a now-missing file."""

    def test_mismatch_produces_explicit_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim_dir = pathlib.Path(tmp)
            claude_bat = shim_dir / banner_install.CLAUDE_BAT_NAME
            autorun_cmd = shim_dir / banner_install.AUTORUN_CMD_NAME
            claude_bat.write_text(banner_install.FORGE_BAT_TAG + "\n", encoding="utf-8")
            autorun_cmd.write_text(banner_install.FORGE_AUTORUN_TAG + "\n", encoding="utf-8")

            mismatched_value = "some other doskey macro that is not ours"

            with patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[]), \
                 patch.object(banner_install, "detect_shell_rc_files", return_value=[]), \
                 patch.object(banner_install, "default_shim_dir", return_value=shim_dir), \
                 patch.object(banner_install, "uninstall_autorun",
                               return_value=("absent", mismatched_value)), \
                 patch.object(banner_install, "dedupe_user_level_orn_motd",
                               return_value="user-level orn-motd hook: none found"), \
                 patch.object(banner_install.banner_patch, "restore_patch",
                               return_value={"status": "nothing-to-restore", "target": None,
                                              "message": "stubbed for this test"}):
                report = banner_install.uninstall_all(home=tmp)

        joined = "\n".join(report)
        self.assertIn("WARNING", joined)
        self.assertIn(mismatched_value, joined)

    def test_genuinely_absent_produces_no_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim_dir = pathlib.Path(tmp)
            with patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[]), \
                 patch.object(banner_install, "detect_shell_rc_files", return_value=[]), \
                 patch.object(banner_install, "default_shim_dir", return_value=shim_dir), \
                 patch.object(banner_install, "uninstall_autorun",
                               return_value=("absent", None)), \
                 patch.object(banner_install, "dedupe_user_level_orn_motd",
                               return_value="user-level orn-motd hook: none found"), \
                 patch.object(banner_install.banner_patch, "restore_patch",
                               return_value={"status": "nothing-to-restore", "target": None,
                                              "message": "stubbed for this test"}):
                report = banner_install.uninstall_all(home=tmp)

        joined = "\n".join(report)
        self.assertNotIn("WARNING", joined)


class TestInstallAllRefusesPlaceholderClaudePath(unittest.TestCase):
    """Deliverable 2 (3rd real-machine-incident hardening): install_all
    must refuse the ENTIRE install -- writing nothing -- when the resolved
    claude_path does not exist as a real file, exactly like it already
    refuses when claude_path is None outright (F4's existing whole-install
    refusal, extended)."""

    def test_placeholder_path_refuses_whole_install_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim_dir = pathlib.Path(tmp) / "shims"
            with patch.object(banner_install, "resolve_claude_cli_path",
                               return_value="C:\\real\\claude.exe"), \
                 patch.object(banner_install, "resolve_python_interpreter",
                               return_value=None), \
                 patch.object(banner_install, "resolve_banner_py_path",
                               return_value=None), \
                 patch.object(banner_install, "default_shim_dir",
                               return_value=shim_dir), \
                 patch.object(banner_install.banner_patch, "apply_patch") as mock_apply:
                report = banner_install.install_all(confirmed=True, home=tmp)

        joined = "\n".join(report)
        self.assertIn("does not exist as a real file", joined)
        self.assertIn("refusing the ENTIRE install", joined)
        mock_apply.assert_not_called()
        self.assertFalse(shim_dir.exists(), "nothing should have been written at all")

    def test_real_file_claude_path_proceeds_past_the_guard(self):
        # Sanity check the guard's positive case too: a genuinely real file
        # must NOT be refused by the placeholder check (any refusal here
        # would have to come from something else, e.g. a legacy-artifact
        # finding, which this test keeps clear via scan_legacy_artifacts).
        with tempfile.TemporaryDirectory() as tmp:
            claude_path = _real_claude_exe(tmp)
            shim_dir = pathlib.Path(tmp) / "shims"
            with patch.object(banner_install, "resolve_claude_cli_path",
                               return_value=claude_path), \
                 patch.object(banner_install, "resolve_python_interpreter",
                               return_value=None), \
                 patch.object(banner_install, "resolve_banner_py_path",
                               return_value=None), \
                 patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[]), \
                 patch.object(banner_install, "detect_shell_rc_files",
                               return_value=[]), \
                 patch.object(banner_install, "default_shim_dir",
                               return_value=shim_dir), \
                 patch.object(banner_install, "scan_legacy_artifacts",
                               return_value=[]), \
                 patch.object(banner_install, "install_autorun",
                               return_value=("unchanged", None)), \
                 patch.object(banner_install, "dedupe_user_level_orn_motd",
                               return_value="user-level orn-motd hook: none found"), \
                 patch.object(banner_install.banner_patch, "apply_patch",
                               return_value={"status": "target-not-found", "target": None,
                                              "message": "stubbed"}):
                report = banner_install.install_all(confirmed=True, home=tmp)

            joined = "\n".join(report)
            self.assertNotIn("does not exist as a real file", joined)
            self.assertTrue((shim_dir / banner_install.CLAUDE_BAT_NAME).is_file())


class TestScanLegacyArtifacts(unittest.TestCase):
    """Deliverable 3: report-only detection of broken legacy banner-shim
    artifacts left behind by an unclean prior install/uninstall -- the
    exact shape of the real incident (a claude.bat targeting a since-
    removed path, wired into AutoRun)."""

    def test_no_shim_dir_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = banner_install.scan_legacy_artifacts(
                home=tmp, get_autorun_fn=lambda: None)
        self.assertEqual(findings, [])

    def test_working_shim_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            claude_path = _real_claude_exe(tmp)
            shim_dir = banner_install.default_shim_dir(home=home)
            claude_bat = shim_dir / banner_install.CLAUDE_BAT_NAME
            banner_install.write_shim_file(
                claude_bat, banner_install.build_claude_bat(claude_path, None, None))

            findings = banner_install.scan_legacy_artifacts(
                home=home, get_autorun_fn=lambda: None)
        self.assertEqual(findings, [])

    def test_broken_shim_targeting_missing_claude_is_flagged_and_gating(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            # Build against a real file, THEN delete it -- reproducing the
            # incident shape (a shim that was valid at install time, whose
            # target later disappeared), without ever writing a shim body
            # containing a placeholder string by hand.
            claude_path = pathlib.Path(tmp) / "claude.exe"
            claude_path.write_text("fake\n", encoding="utf-8")
            shim_dir = banner_install.default_shim_dir(home=home)
            claude_bat = shim_dir / banner_install.CLAUDE_BAT_NAME
            banner_install.write_shim_file(
                claude_bat, banner_install.build_claude_bat(str(claude_path), None, None))
            claude_path.unlink()

            findings = banner_install.scan_legacy_artifacts(
                home=home, get_autorun_fn=lambda: None)

        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0]["gating"], "our own tagged shim must gate install")
        self.assertIn("broken legacy shim", findings[0]["message"])
        self.assertIn(str(claude_bat), findings[0]["message"])

    def test_shim_without_forge_tag_is_not_flagged(self):
        # Only ever touches/reports on shims carrying OUR tag -- an
        # unrelated user file that happens to share the name must be left
        # alone entirely.
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            shim_dir = banner_install.default_shim_dir(home=home)
            shim_dir.mkdir(parents=True)
            claude_bat = shim_dir / banner_install.CLAUDE_BAT_NAME
            claude_bat.write_text('@echo off\r\n"C:\\does\\not\\exist.exe" %*\r\n',
                                   encoding="utf-8")

            findings = banner_install.scan_legacy_artifacts(
                home=home, get_autorun_fn=lambda: None)
        self.assertEqual(findings, [])

    def test_broken_autorun_cmd_referencing_missing_bat_is_flagged_and_gating(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            shim_dir = banner_install.default_shim_dir(home=home)
            missing_bat = shim_dir / banner_install.CLAUDE_BAT_NAME  # never created
            autorun_cmd = shim_dir / banner_install.AUTORUN_CMD_NAME
            banner_install.write_shim_file(
                autorun_cmd, banner_install.build_autorun_cmd(missing_bat))

            findings = banner_install.scan_legacy_artifacts(
                home=home, get_autorun_fn=lambda: None)

        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0]["gating"])
        self.assertIn("broken legacy artifact", findings[0]["message"])
        self.assertIn(str(autorun_cmd), findings[0]["message"])

    @unittest.skipUnless(os.name == "nt", "AutoRun registry scan is Windows-only")
    def test_broken_autorun_registry_value_referencing_our_autorun_cmd_is_gating(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            missing_path = str(pathlib.Path(tmp) / "gone" / "forge-autorun.cmd")
            findings = banner_install.scan_legacy_artifacts(
                home=home, get_autorun_fn=lambda: f'"{missing_path}"')

        self.assertEqual(len(findings), 1)
        self.assertTrue(
            findings[0]["gating"],
            "a missing path named forge-autorun.cmd is ours by filename alone",
        )
        self.assertIn("broken AutoRun entry", findings[0]["message"])
        self.assertIn(missing_path, findings[0]["message"])

    @unittest.skipUnless(os.name == "nt", "AutoRun registry scan is Windows-only")
    def test_broken_autorun_registry_value_under_our_shim_dir_is_gating(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            shim_dir = banner_install.default_shim_dir(home=home)
            missing_path = str(shim_dir / "some-other-forge-artifact.cmd")
            findings = banner_install.scan_legacy_artifacts(
                home=home, get_autorun_fn=lambda: f'"{missing_path}"')

        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0]["gating"], "a path under our own shim dir is ours by location")

    @unittest.skipUnless(os.name == "nt", "AutoRun registry scan is Windows-only")
    def test_broken_autorun_registry_value_unrelated_to_forge_is_informational_only(self):
        # Verify-bounce P1 fix (F4): a missing quoted path in HKCU AutoRun
        # that has no connection to forge at all -- neither our filename
        # nor under our shim dir -- must still be REPORTED (so status can
        # surface it) but must NOT gate install, and must not claim restore
        # will clear it.
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            missing_path = "C:\\Program Files\\SomeOtherApp\\launcher.exe"
            findings = banner_install.scan_legacy_artifacts(
                home=home, get_autorun_fn=lambda: f'"{missing_path}"')

        self.assertEqual(len(findings), 1)
        self.assertFalse(
            findings[0]["gating"],
            "an unrelated program's own broken AutoRun entry must not gate our install",
        )
        self.assertIn(missing_path, findings[0]["message"])

    def test_registry_read_failure_degrades_to_no_finding(self):
        # (READ-ONLY registry query, guarded): a blocked/unavailable read
        # (winreg unavailable, the hermeticity guard itself, any other
        # failure) must degrade to "nothing to report", never raise out of
        # a report-only scan.
        def _raise():
            raise AssertionError("registry blocked")

        with tempfile.TemporaryDirectory() as tmp:
            findings = banner_install.scan_legacy_artifacts(home=tmp, get_autorun_fn=_raise)
        self.assertEqual(findings, [])

    def test_install_all_refuses_when_gating_legacy_artifacts_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_path = _real_claude_exe(tmp)
            with patch.object(banner_install, "resolve_claude_cli_path",
                               return_value=claude_path), \
                 patch.object(banner_install, "resolve_python_interpreter",
                               return_value=None), \
                 patch.object(banner_install, "resolve_banner_py_path",
                               return_value=None), \
                 patch.object(banner_install, "scan_legacy_artifacts",
                               return_value=[{"gating": True,
                                               "message": "broken legacy shim: fake finding"}]), \
                 patch.object(banner_install.banner_patch, "apply_patch") as mock_apply:
                report = banner_install.install_all(confirmed=True, home=tmp)

        joined = "\n".join(report)
        self.assertIn("Refusing install", joined)
        self.assertIn("restore", joined)
        self.assertIn("broken legacy shim: fake finding", joined)
        mock_apply.assert_not_called()

    def test_install_all_does_not_refuse_on_informational_only_findings(self):
        # F4: a non-gating (unrelated) finding must never block install.
        with tempfile.TemporaryDirectory() as tmp:
            claude_path = _real_claude_exe(tmp)
            shim_dir = pathlib.Path(tmp) / "shims"
            with patch.object(banner_install, "resolve_claude_cli_path",
                               return_value=claude_path), \
                 patch.object(banner_install, "resolve_python_interpreter",
                               return_value=None), \
                 patch.object(banner_install, "resolve_banner_py_path",
                               return_value=None), \
                 patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[]), \
                 patch.object(banner_install, "detect_shell_rc_files",
                               return_value=[]), \
                 patch.object(banner_install, "default_shim_dir",
                               return_value=shim_dir), \
                 patch.object(banner_install, "scan_legacy_artifacts",
                               return_value=[{"gating": False,
                                               "message": "AutoRun entry (not ours): fake"}]), \
                 patch.object(banner_install, "install_autorun",
                               return_value=("unchanged", None)), \
                 patch.object(banner_install, "dedupe_user_level_orn_motd",
                               return_value="user-level orn-motd hook: none found"), \
                 patch.object(banner_install.banner_patch, "apply_patch",
                               return_value={"status": "target-not-found", "target": None,
                                              "message": "stubbed"}):
                report = banner_install.install_all(confirmed=True, home=tmp)

            joined = "\n".join(report)
            self.assertNotIn("Refusing install", joined)
            self.assertTrue((shim_dir / banner_install.CLAUDE_BAT_NAME).is_file())

    def test_status_all_reports_legacy_scan_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[]), \
                 patch.object(banner_install, "detect_shell_rc_files",
                               return_value=[]), \
                 patch.object(banner_install, "get_autorun_value", return_value=None), \
                 patch.object(banner_install, "scan_legacy_artifacts",
                               return_value=[{"gating": True,
                                               "message": "broken legacy shim: fake finding"}]):
                report = banner_install.status_all(home=tmp)
        joined = "\n".join(report)
        self.assertIn("legacy scan: broken legacy shim: fake finding", joined)

    def test_status_all_reports_informational_findings_distinctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[]), \
                 patch.object(banner_install, "detect_shell_rc_files",
                               return_value=[]), \
                 patch.object(banner_install, "get_autorun_value", return_value=None), \
                 patch.object(banner_install, "scan_legacy_artifacts",
                               return_value=[{"gating": False,
                                               "message": "AutoRun entry (not ours): fake"}]):
                report = banner_install.status_all(home=tmp)
        joined = "\n".join(report)
        self.assertIn("legacy scan (informational, not ours): AutoRun entry (not ours): fake", joined)

    def test_status_all_reports_clean_when_nothing_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(banner_install, "detect_powershell_profiles",
                               return_value=[]), \
                 patch.object(banner_install, "detect_shell_rc_files",
                               return_value=[]), \
                 patch.object(banner_install, "get_autorun_value", return_value=None), \
                 patch.object(banner_install, "scan_legacy_artifacts",
                               return_value=[]):
                report = banner_install.status_all(home=tmp)
        joined = "\n".join(report)
        self.assertIn("legacy scan: no broken legacy banner-shim artifacts found", joined)


if __name__ == "__main__":
    unittest.main()
