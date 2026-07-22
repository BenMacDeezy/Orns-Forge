"""Tests for the bm-banner-takeover patch engine (tools/banner.py) and the
single-mode install/restore orchestration it powers (tools/banner_install.py).

OWNER DELTA 2026-07-22: `/forge:banner install` is now a SINGLE mode -- there
is no separate splash-only path any more. Every install patches the
installed Claude Code CLI's startup block-art out (same-byte-length swap)
and installs the launcher shim; `/forge:banner --restore` (or `uninstall`)
always byte-exactly restores the binary AND removes every shim/wrapper/
stamp. `TestLegacySplashOnlyPathRemoved` pins the removal.

REAL-MACHINE PROBE FOLLOW-UP (2026-07-21, kernel-run against the real
install on this machine, C:\\Users\\<user>\\.local\\bin\\claude.exe -- a
~248MB NATIVE install, not an npm cli.js shim):
  1. resolve_cli_target_path() must also find a native install (a large
     executable at a known root like ~/.local/bin/claude.exe), not just an
     npm shim -> cli.js. See TestResolveCliTargetPath.
  2. The real binary carries the startup art as TWO different byte forms:
     488 occurrences of the literal 6-ASCII-byte escape TEXT "\\u2580" (and
     siblings), versus only 7 of the UTF-8-encoded 3-byte character. The
     patch engine must detect and handle both, patching whichever
     dominates. See TestDualFormDetectionAndPatching.
  3. Backing up a 248MB file as a full copy is wasteful; the backup is now
     an offsets JOURNAL (small sidecar of (offset, original-bytes) pairs +
     a whole-file hash header), written and fsync'd BEFORE the target is
     touched. --restore replays it and must be byte-identical to the
     original, verified against the journal's own hash before writing
     anything. See TestOffsetsJournalBackupAndRestore.

FLOOR: never run the patch against a real installed `claude` in these
tests. Every fixture is a synthetic in-memory bytes blob or a file under a
tempfile.TemporaryDirectory() standing in for a fake ~/.claude via the
injectable `home=` parameter every real-filesystem function here takes.
Every call that could otherwise fall through to a real `where claude` /
native-root lookup (target_path=None) explicitly mocks
resolve_cli_target_path so it can never resolve a real install on the
machine running these tests.

INCIDENT, CONFIRMED 2026-07-21: the floor above was violated for real. A
test in an earlier revision of this file called apply_patch(target_path=
None, home=<tempdir>) without mocking resolve_cli_target_path. The home=
tempdir only affects the native-install-root FALLBACK check -- the
initial `where claude` PATH search always hits the real system regardless
of home=. That test ran (as part of a backgrounded `pytest tools/
test_banner_takeover.py tools/test_banner_install.py` invocation) before
the fix landed, resolved the user's REAL installed
C:\\Users\\<user>\\.local\\bin\\claude.exe, and apply_patch's own
already-patched/pattern-not-found guard did not save it: the real binary
carried the literal-escape form (488 occurrences) and got same-byte-length
patched for real (488 -> 0 literal escapes, replaced with literal \\u200B
text) before the run was killed. The size/mtime check performed
immediately afterward as "verification" reported nothing suspicious --
which was WRONG as evidence, not right: the patch is same-byte-length BY
DESIGN, so mtime/size are exactly the signal it cannot detect. No journal
or stamp was written on that path (the vulnerable code predated this
file's journal work), so there is no automatic --restore available; the
kernel's call is to leave it (cosmetic only, self-heals on the next Claude
Code update) and never write to the real install again to fix it. The
`_hermeticity_guard` fixture below exists so this exact class of mistake
raises loudly inside the test run itself, instead of silently succeeding
against the live machine and being missed by a same-length-blind
verification check.
"""
import inspect
import io
import json
import pathlib
import sys
import tempfile
import unittest
import unittest.mock

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import banner  # noqa: E402
import banner_install  # noqa: E402


# ---------------------------------------------------------------------------
# MANDATORY hermeticity guard (added after the 2026-07-21 incident above,
# generalized into tools/conftest.py after the 3rd real-machine incident so
# every file in tools/ -- not just this one -- gets it automatically). This
# file used to define its own file-local `_hermeticity_guard` autouse
# fixture; that fixture has been REMOVED from here and its logic moved to
# tools/conftest.py, which now also covers every banner_install.py write
# surface and all registry access (see that module's docstring). This
# file's own meta-test below still pins that the guard actually trips, now
# by exercising the shared conftest fixture instead of a copy of it.
# ---------------------------------------------------------------------------


class TestHermeticityGuardTripsOnRegression(unittest.TestCase):
    """Meta-test: deliberately reproduces the exact 2026-07-21 mistake
    (apply_patch(target_path=None, home=<tempdir>) with an UNMOCKED
    resolve_cli_target_path) and proves the tools/conftest.py guard catches
    it instead of silently walking onto the real machine. If this test
    ever fails (the guard doesn't raise), the hermeticity guard itself is
    broken and must be fixed before anything else in this package can be
    trusted."""

    def test_unmocked_resolve_call_raises_instead_of_touching_real_machine(self):
        # Deliberately the exact vulnerable call shape from the incident:
        # target_path=None, resolve_cli_target_path itself left UNMOCKED.
        # Only the low-level file-existence-checking helper it calls
        # (_resolve_shim_to_bundle) is stubbed to simulate what a machine
        # with a real install produces -- a path under the real home --
        # without ever creating or touching a real file. This keeps the
        # test deterministic regardless of whether the machine actually
        # running the suite has Claude Code installed.
        real_home = pathlib.Path.home().resolve()
        fake_real_target = real_home / "claude.exe"  # never created, never read
        with tempfile.TemporaryDirectory() as home, \
             unittest.mock.patch.object(banner, "_resolve_shim_to_bundle",
                                         return_value=fake_real_target):
            with self.assertRaises(AssertionError) as ctx:
                banner.apply_patch(target_path=None, home=home)
            self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    # F1 (verify-bounce finding, 2026-07-21): a prior revision of this file
    # had a second "belt-and-suspenders" test here that called the RAW,
    # unguarded resolver (`_REAL_RESOLVE_CLI_TARGET_PATH`, captured before
    # the autouse fixture wraps it) directly against the real machine as a
    # "read-only probe". Read-only or not, no test may reach the real
    # machine at all -- that's the bright line this whole guard exists to
    # enforce. That test and the module-level capture it depended on have
    # been deleted; the synthetic-stub regression test above already
    # proves the guard trips, without ever touching anything real.

    def test_resolve_guard_also_rejects_non_home_real_paths(self):
        # verify-bounce P1 fix: the resolver guard used to only reject a
        # result under Path.home() -- a real install under a location like
        # C:\Program Files, an npm global prefix, or /usr/local would have
        # passed through untouched. Prove the guard now rejects ANY
        # resolved path outside the OS temp root, home or not -- simulated
        # here via a synthetic, never-created "Program Files"-shaped path
        # so the test stays deterministic regardless of what's actually
        # installed on the machine running the suite.
        program_files_target = pathlib.Path("C:\\Program Files\\ClaudeCode\\claude.exe")
        with tempfile.TemporaryDirectory() as home, \
             unittest.mock.patch.object(banner, "_resolve_shim_to_bundle",
                                         return_value=program_files_target):
            with self.assertRaises(AssertionError) as ctx:
                banner.apply_patch(target_path=None, home=home)
            self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_write_stamp_direct_call_outside_tmp_is_blocked(self):
        # F1 (P0 verify-bounce finding): _write_stamp used to call
        # Path.write_text() directly, unreachable by the three originally-
        # guarded primitives -- a test calling it directly (or indirectly,
        # through apply_patch/restore_patch) with a non-tmp path must be
        # blocked, not silently succeed against the real machine.
        real_home = pathlib.Path.home().resolve()
        with self.assertRaises(AssertionError) as ctx:
            banner._write_stamp(real_home / "not-a-tmp-path.stamp", {"x": 1})
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_unlink_path_direct_call_outside_tmp_is_blocked(self):
        # F1 (P0 verify-bounce finding): restore_patch used to call
        # Path.unlink() directly on the stamp AND the journal (whose path
        # comes from the STAMP'S OWN CONTENTS, not a passed-in tmp home).
        real_home = pathlib.Path.home().resolve()
        with self.assertRaises(AssertionError) as ctx:
            banner._unlink_path(real_home / "not-a-tmp-path.journal.json")
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_write_stamp_inside_tmp_is_not_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            stamp_path = pathlib.Path(tmp) / "x.stamp"
            banner._write_stamp(stamp_path, {"x": 1})
            self.assertTrue(stamp_path.is_file())


class TestConftestGuardCoversBannerInstallWriteSurfaces(unittest.TestCase):
    """Meta-tests for the WIDENED coverage tools/conftest.py's hermeticity
    guard added for the 3rd real-machine incident (banner_install.py write
    surfaces + all registry access, not just banner.py's patch-engine
    primitives). Each test deliberately reproduces the exact vulnerable
    call shape -- a write/registry call with no injected home/get_fn/set_fn
    -- and proves the guard raises instead of touching the real machine."""

    def test_install_all_confirmed_without_home_is_blocked(self):
        # confirmed=True with no home= means "write against the REAL
        # Path.home()" -- exactly the incident shape. Must raise before any
        # of install_all's own logic (claude-path resolution, shim writes)
        # ever runs.
        with self.assertRaises(AssertionError) as ctx:
            banner_install.install_all(confirmed=True)
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_install_all_preview_without_home_is_not_blocked(self):
        # confirmed=False (the default preview/dry-run) never writes, so it
        # must NOT be blocked even with no home= -- only the confirmed
        # write path is guarded.
        with unittest.mock.patch.object(
                banner_install.banner_patch, "patch_report",
                return_value={"status": "would-patch", "target": "x", "count": 1,
                              "form": "utf8-char", "journal_path": "j", "stamp_path": "s",
                              "message": "would patch"}):
            report = banner_install.install_all(confirmed=False)
        self.assertTrue(any("DRY RUN" in line for line in report))

    def test_restore_all_without_home_is_blocked(self):
        with self.assertRaises(AssertionError) as ctx:
            banner_install.restore_all()
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_install_into_file_outside_tmp_is_blocked(self):
        with self.assertRaises(AssertionError) as ctx:
            banner_install.install_into_file(
                pathlib.Path("C:\\Users\\someone\\not-a-tmp-path\\profile.ps1"), "body")
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_write_shim_file_outside_tmp_is_blocked(self):
        with self.assertRaises(AssertionError) as ctx:
            banner_install.write_shim_file(
                pathlib.Path("C:\\Users\\someone\\not-a-tmp-path\\claude.bat"), "content")
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_unlink_shim_file_outside_tmp_is_blocked(self):
        # F1 (P0 verify-bounce finding): restore_all()'s tagged-shim
        # cleanup used to call Path.unlink() directly on claude.bat/
        # forge-autorun.cmd -- unlink_shim_file is the guardable primitive
        # it now routes through instead.
        with self.assertRaises(AssertionError) as ctx:
            banner_install.unlink_shim_file(
                pathlib.Path("C:\\Users\\someone\\not-a-tmp-path\\claude.bat"))
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_install_into_file_inside_tmp_is_not_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "profile.ps1"
            action = banner_install.install_into_file(path, "function claude { X }")
        self.assertEqual(action, "installed")

    def test_get_autorun_value_is_unconditionally_blocked(self):
        # (c): registry access has no "under tmp" exception -- there is no
        # tmp-equivalent for a single real global registry hive.
        with self.assertRaises(AssertionError) as ctx:
            banner_install.get_autorun_value()
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_set_autorun_value_is_unconditionally_blocked(self):
        with self.assertRaises(AssertionError) as ctx:
            banner_install.set_autorun_value("x")
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    def test_install_autorun_default_lookup_is_also_blocked(self):
        # install_autorun's get_fn/set_fn default to None and resolve
        # get_autorun_value/set_autorun_value via a module-global NAME
        # lookup at call time (not a captured default parameter value) --
        # proving THIS path is blocked too, not just a direct call to
        # get_autorun_value itself, is the actual regression this guards
        # against (a default-argument capture would have silently bypassed
        # the monkeypatch).
        with self.assertRaises(AssertionError) as ctx:
            banner_install.install_autorun('"C:\\shims\\forge-autorun.cmd"')
        self.assertIn("HERMETICITY GUARD TRIPPED", str(ctx.exception))

    # No test here uses @pytest.mark.allow_real_home_access to prove the
    # opt-in marker disables the guard: doing so would require actually
    # exercising a real-machine call (e.g. a real get_autorun_value()
    # registry read) from a test, which is exactly what "no test may touch
    # real HKCU at all" (this task's own requirement) forbids. The marker's
    # wiring (an early `if ... get_closest_marker(...): yield; return` in
    # tools/conftest.py's fixture) is straightforward enough to verify by
    # reading, and is intentionally never exercised here.


# ---------------------------------------------------------------------------
# Synthetic fixtures standing in for a Claude Code CLI bundle -- NEVER the
# real installed file.
# ---------------------------------------------------------------------------

def _real_claude_exe(tmp_dir, name="claude.exe"):
    """A real (if fake-content) file standing in for a resolved claude CLI
    path. build_claude_bat/build_powershell_body/build_bash_body refuse
    (ValueError) a claude_path that is not a real file on disk (the
    placeholder-path guard added for the 3rd real-machine-incident
    hardening), so every test that resolves a claude_path for install_all
    or the shim-body generators must pass a real file under a
    tempfile.TemporaryDirectory(), never a bare placeholder string like the
    old 'C:\\real\\claude.exe' fixture -- that exact literal is what caused
    the real incident this guard prevents."""
    path = pathlib.Path(tmp_dir) / name
    path.write_text("fake claude cli\n", encoding="utf-8")
    return str(path)


def _fake_bundle_bytes(repeat=1):
    """A synthetic minified-JS-shaped blob carrying UTF-8-char-form art
    escapes, like an npm cli.js build might embed. Deliberately mixes art
    bytes with ordinary ASCII JS so a naive replace-everything patch would
    be caught by the length/identity assertions below.

    repeat=1 (the default) yields exactly 30 hits -- used by tests that
    pin an exact count for the pure find/patch primitives, which are NOT
    subject to the low-count plausibility floor (that floor only gates
    patch_report/apply_patch). Tests that exercise apply_patch/patch_report
    and expect a normal "would-patch"/"patched" outcome pass a higher
    repeat (e.g. 4 -> 120 hits) to clear _LOW_COUNT_THRESHOLD."""
    art = "▀▄█░▒▓▌▐▔▕" * repeat  # 10 distinct Block Elements codepoints
    return (
        f'console.log("{art}");\n'
        f'const banner = "{art}{art}";\n'
        'function ok() {{ return 1; }}\n'
    ).encode("utf-8")


def _fake_native_bundle_bytes(literal_count=488, utf8_count=7):
    """A synthetic blob mimicking the REAL probe's shape: the literal
    6-ASCII-byte escape-text form dominating (488x observed) with a small
    minority of the UTF-8-char form (7x observed) mixed in -- exactly the
    scenario patch_art() must auto-detect and resolve in favor of the
    literal form."""
    literal_chunk = b'\\u2580\\u2588\\u2591\\u2584' * (literal_count // 4 + 1)
    literal_chunk = literal_chunk[:literal_count * 6]
    utf8_chunk = "▀".encode("utf-8") * utf8_count
    return b'const ART="' + literal_chunk + b'";const X="' + utf8_chunk + b'";'


class TestFindAndPatchBlockArt(unittest.TestCase):
    """Pure byte-level engine: UTF-8-char-form find + same-byte-length
    patch (patch_block_art/find_block_art_sequences)."""

    def test_finds_every_block_element_occurrence(self):
        content = _fake_bundle_bytes()
        hits = banner.find_block_art_sequences(content)
        # 10 distinct art chars in the first string + 20 in the second = 30.
        self.assertEqual(len(hits), 30)

    def test_patch_preserves_byte_length_exactly(self):
        content = _fake_bundle_bytes()
        patched, count = banner.patch_block_art(content)
        self.assertGreater(count, 0)
        self.assertEqual(len(patched), len(content))

    def test_patch_removes_every_art_escape(self):
        content = _fake_bundle_bytes()
        patched, count = banner.patch_block_art(content)
        self.assertEqual(banner.find_block_art_sequences(patched), [])
        self.assertEqual(count, 30)

    def test_patch_leaves_surrounding_ascii_untouched(self):
        content = _fake_bundle_bytes()
        patched, _ = banner.patch_block_art(content)
        self.assertIn(b'console.log("', patched)
        self.assertIn(b'function ok() {{ return 1; }}', patched)

    def test_zero_width_space_is_three_utf8_bytes(self):
        # The whole same-byte-length invariant hinges on this.
        self.assertEqual(len(banner.ZERO_WIDTH_SPACE.encode("utf-8")), 3)

    def test_pattern_not_found_returns_input_unchanged(self):
        content = b'console.log("nothing to see here, plain ASCII only");'
        patched, count = banner.patch_block_art(content)
        self.assertEqual(count, 0)
        self.assertEqual(patched, content)

    def test_patch_is_idempotent_on_already_patched_bytes(self):
        content = _fake_bundle_bytes()
        once, count1 = banner.patch_block_art(content)
        twice, count2 = banner.patch_block_art(once)
        self.assertEqual(twice, once)
        self.assertEqual(count2, 0)
        self.assertGreater(count1, 0)


class TestLiteralEscapeForm(unittest.TestCase):
    """The SECOND art-escape form found in the real probe: literal 6-ASCII-
    byte escape TEXT ("\\u2580" etc, not the encoded character). This is
    the form that dominates in a real native build (488 vs 7)."""

    def test_finds_literal_escape_occurrences(self):
        content = b'const ART="\\u2580\\u2588\\u2591\\u259A";'
        hits = banner.find_literal_escape_sequences(content)
        self.assertEqual(len(hits), 4)

    def test_literal_zwsp_replacement_is_six_ascii_bytes(self):
        self.assertEqual(len(banner._LITERAL_ZWSP_BYTES), 6)
        self.assertEqual(banner._LITERAL_ZWSP_BYTES, b"\\u200B")

    def test_patch_literal_preserves_byte_length(self):
        content = b'const ART="\\u2580\\u2588";'
        patched, count = banner.patch_literal_escapes(content)
        self.assertEqual(count, 2)
        self.assertEqual(len(patched), len(content))

    def test_patch_literal_removes_every_occurrence(self):
        content = b'const ART="\\u2580\\u2588\\u2591";'
        patched, count = banner.patch_literal_escapes(content)
        self.assertEqual(count, 3)
        self.assertEqual(banner.find_literal_escape_sequences(patched), [])
        self.assertIn(b"\\u200B", patched)

    def test_literal_pattern_not_found_returns_input_unchanged(self):
        content = b'const X = "plain ascii only";'
        patched, count = banner.patch_literal_escapes(content)
        self.assertEqual(count, 0)
        self.assertEqual(patched, content)

    def test_does_not_false_positive_on_unrelated_unicode_escapes(self):
        # A ('A') and ሴ are outside the Block Elements range
        # (2580-259F) and must not be mistaken for art escapes.
        content = b'const X = "\\u0041\\u1234\\u25FF";'
        self.assertEqual(banner.find_literal_escape_sequences(content), [])


class TestDualFormDetectionAndPatching(unittest.TestCase):
    """patch_art(): auto-detect which of the two forms dominates a target
    and patch only that one, per the real-probe finding that a native
    build carries mostly the literal form with a handful of UTF-8-char
    stragglers."""

    def test_detect_art_form_counts_reports_both_forms_independently(self):
        content = _fake_native_bundle_bytes(literal_count=488, utf8_count=7)
        counts = banner.detect_art_form_counts(content)
        self.assertEqual(counts["literal"], 488)
        self.assertEqual(counts["utf8"], 7)

    def test_patch_art_picks_the_dominant_literal_form(self):
        content = _fake_native_bundle_bytes(literal_count=488, utf8_count=7)
        patched, count, form, hits, length = banner.patch_art(content)
        self.assertEqual(form, "literal-escape")
        self.assertEqual(count, 488)
        self.assertEqual(length, 6)
        self.assertEqual(len(hits), 488)
        self.assertEqual(len(patched), len(content))
        # The minority UTF-8-char form is left untouched, not patched.
        self.assertEqual(len(banner.find_block_art_sequences(patched)), 7)
        self.assertEqual(banner.find_literal_escape_sequences(patched), [])

    def test_patch_art_picks_the_dominant_utf8_form_when_it_wins(self):
        content = _fake_native_bundle_bytes(literal_count=2, utf8_count=20)
        patched, count, form, hits, length = banner.patch_art(content)
        self.assertEqual(form, "utf8-char")
        self.assertEqual(count, 20)
        self.assertEqual(length, 3)
        # The minority literal form is left untouched.
        self.assertEqual(len(banner.find_literal_escape_sequences(patched)), 2)

    def test_patch_art_ties_go_to_literal_form(self):
        content = b'\\u2580\\u2588' + "▀▄".encode("utf-8")
        counts = banner.detect_art_form_counts(content)
        self.assertEqual(counts["literal"], counts["utf8"])
        _, _, form, _, _ = banner.patch_art(content)
        self.assertEqual(form, "literal-escape")

    def test_patch_art_neither_form_present(self):
        patched, count, form, hits, length = banner.patch_art(b"plain ascii")
        self.assertEqual((count, form, hits, length), (0, None, [], 0))
        self.assertEqual(patched, b"plain ascii")

    def test_patch_art_result_is_byte_length_preserving(self):
        for content in (
            _fake_native_bundle_bytes(literal_count=488, utf8_count=7),
            _fake_bundle_bytes(),
            b'\\u2580' * 50,
        ):
            patched, count, form, hits, length = banner.patch_art(content)
            self.assertEqual(len(patched), len(content))


def _write_large_fake_binary(path, marker=b"@anthropic-ai/claude-code"):
    """A synthetic large-file fixture standing in for a native install --
    sized above _LARGE_BINARY_THRESHOLD_BYTES via seek+write (cheap, no
    real 5MB+ write), optionally embedding a Claude Code identity marker
    (F2) so tests can prove both the accept and reject paths."""
    with open(path, "wb") as f:
        if marker:
            f.write(marker)
            f.write(b"\x00" * 64)
        f.seek(banner._LARGE_BINARY_THRESHOLD_BYTES)
        f.write(b"\x00")


class TestResolveCliTargetPath(unittest.TestCase):
    """resolve_cli_target_path()'s native-install fallback: a real native
    Windows install is a single large executable at a known root
    (~/.local/bin/claude.exe), not an npm cli.js reached via a small shim.
    All subprocess/PATH interaction is mocked -- never touches the real
    PATH or a real claude install."""

    def test_large_file_is_treated_as_the_bundle_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_exe = pathlib.Path(tmp) / "claude.exe"
            _write_large_fake_binary(fake_exe)
            resolved = banner._resolve_shim_to_bundle(fake_exe)
            self.assertEqual(resolved, fake_exe)

    def test_small_non_js_file_with_no_reference_resolves_to_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim = pathlib.Path(tmp) / "claude.cmd"
            shim.write_text("@echo off\necho nothing referenced here\n", encoding="utf-8")
            self.assertIsNone(banner._resolve_shim_to_bundle(shim))

    def test_small_npm_shim_resolves_referenced_cli_js(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            node_modules = tmp_path / "node_modules" / "@anthropic-ai" / "claude-code"
            node_modules.mkdir(parents=True)
            cli_js = node_modules / "cli.js"
            # F2: the referenced cli.js must itself carry a Claude Code
            # identity marker to be accepted -- an empty/generic file
            # named cli.js is not enough.
            cli_js.write_text("console.log('hi'); // @anthropic-ai/claude-code",
                               encoding="utf-8")
            shim = tmp_path / "claude"
            # A realistic shim resolves $basedir at shell-execution time; the
            # static regex scan here only needs a literal relative path to
            # resolve against the shim's own directory.
            shim.write_text(
                '#!/bin/sh\nexec node "node_modules/@anthropic-ai/claude-code/cli.js" "$@"\n',
                encoding="utf-8",
            )
            resolved = banner._resolve_shim_to_bundle(shim)
            self.assertEqual(resolved, cli_js)

    def test_falls_back_to_native_install_root_when_path_search_fails(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = pathlib.Path(home)
            local_bin = home_path / ".local" / "bin"
            local_bin.mkdir(parents=True)
            native_exe = local_bin / ("claude.exe" if banner.os.name == "nt" else "claude")
            _write_large_fake_binary(native_exe)

            # Simulate "where"/"which" finding nothing at all on PATH.
            with unittest.mock.patch.object(banner.subprocess, "run",
                                             side_effect=Exception("no where")), \
                 unittest.mock.patch.object(banner.shutil, "which", return_value=None):
                resolved = banner.resolve_cli_target_path(home=home)

            self.assertEqual(resolved, native_exe)

    def test_returns_none_when_nothing_resolves_at_all(self):
        with tempfile.TemporaryDirectory() as home:
            with unittest.mock.patch.object(banner.subprocess, "run",
                                             side_effect=Exception("no where")), \
                 unittest.mock.patch.object(banner.shutil, "which", return_value=None):
                self.assertIsNone(banner.resolve_cli_target_path(home=home))


class TestClaudeCodeIdentityMarker(unittest.TestCase):
    """F2 (verify-bounce finding): resolution must not accept a large
    binary, a .js file, or a shim-referenced cli.js based on name/size/
    extension alone -- it must contain a Claude-Code-specific content
    marker. Confirmed against a READ-ONLY scan of the real installed
    C:\\Users\\<user>\\.local\\bin\\claude.exe (2026-07-21): 331
    occurrences of b"@anthropic-ai/claude-code", 956 of b"Claude Code"."""

    def test_has_marker_true_for_either_known_marker(self):
        self.assertTrue(banner._has_claude_code_marker(b"...@anthropic-ai/claude-code..."))
        self.assertTrue(banner._has_claude_code_marker(b"...Claude Code...built with love..."))

    def test_has_marker_false_with_neither(self):
        self.assertFalse(banner._has_claude_code_marker(b"just some random binary blob"))

    def test_large_file_without_marker_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_exe = pathlib.Path(tmp) / "claude.exe"
            _write_large_fake_binary(fake_exe, marker=None)
            self.assertIsNone(banner._resolve_shim_to_bundle(fake_exe))

    def test_large_file_with_marker_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_exe = pathlib.Path(tmp) / "claude.exe"
            _write_large_fake_binary(fake_exe, marker=b"Claude Code")
            self.assertEqual(banner._resolve_shim_to_bundle(fake_exe), fake_exe)

    def test_js_file_without_marker_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli_js = pathlib.Path(tmp) / "cli.js"
            cli_js.write_text("console.log('totally unrelated tool');", encoding="utf-8")
            self.assertIsNone(banner._resolve_shim_to_bundle(cli_js))

    def test_js_file_with_marker_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli_js = pathlib.Path(tmp) / "cli.js"
            cli_js.write_text("// @anthropic-ai/claude-code bundle", encoding="utf-8")
            self.assertEqual(banner._resolve_shim_to_bundle(cli_js), cli_js)

    def test_arbitrary_binary_masquerading_as_claude_is_not_patched(self):
        """The core P1 scenario: a large file simply NAMED claude.exe with
        enough incidental block-escape-shaped bytes to clear the low-count
        floor must NOT be accepted as a patch target without the identity
        marker."""
        with tempfile.TemporaryDirectory() as tmp:
            impostor = pathlib.Path(tmp) / "claude.exe"
            _write_large_fake_binary(impostor, marker=None)
            # Salt in plenty of literal escape text so, if identity were
            # never checked, this would otherwise look very patchable.
            with open(impostor, "ab") as f:
                f.write(b'\\u2580' * 200)
            self.assertIsNone(banner._resolve_shim_to_bundle(impostor))


class TestApplyPatchAndRestorePatch(unittest.TestCase):
    """apply_patch()/restore_patch() against a synthetic target file under a
    tempdir-backed fake home -- never the real ~/.claude, never a real
    claude install."""

    def _make_target(self, tmp, content=None):
        target = pathlib.Path(tmp) / "fake-cli.js"
        # repeat=4 -> 120 hits, comfortably clearing _LOW_COUNT_THRESHOLD
        # (100) so this class's default fixture behaves like a normal,
        # plausible art-bearing build; TestLowCountPlausibilityFloor
        # covers the below-threshold behavior explicitly.
        target.write_bytes(content if content is not None else _fake_bundle_bytes(repeat=4))
        return target

    def test_apply_patch_writes_journal_and_stamp(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()

            result = banner.apply_patch(target_path=target, home=home,
                                         cli_version="1.2.3")

            self.assertEqual(result["status"], "patched")
            self.assertGreater(result["count"], 0)
            self.assertEqual(result["form"], "utf8-char")
            self.assertEqual(len(target.read_bytes()), len(original_bytes))
            self.assertNotEqual(target.read_bytes(), original_bytes)

            journal_path = pathlib.Path(result["journal_path"])
            self.assertTrue(journal_path.is_file())
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            self.assertEqual(journal["orig_sha256"], banner._sha256(original_bytes))
            self.assertEqual(journal["form"], "utf8-char")
            self.assertEqual(journal["replacement_length"], 3)
            self.assertGreater(len(journal["replacements"]), 0)

            stamp_path = banner._patch_stamp_path(home)
            self.assertTrue(stamp_path.is_file())
            stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
            self.assertEqual(stamp["target"], str(target))
            self.assertEqual(stamp["version"], "1.2.3")
            self.assertEqual(stamp["journal_path"], str(journal_path))

    def test_apply_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            first = banner.apply_patch(target_path=target, home=home)
            after_first = target.read_bytes()
            second = banner.apply_patch(target_path=target, home=home)

            self.assertEqual(first["status"], "patched")
            self.assertEqual(second["status"], "already-patched")
            self.assertEqual(target.read_bytes(), after_first)  # untouched

    def test_apply_patch_refuses_when_existing_journal_is_tampered(self):
        """F5: a journal already present at the deterministic (orig-hash-
        keyed) path is VALIDATED before being trusted -- a tampered/
        corrupt journal must refuse the patch outright, never be silently
        overwritten and never be silently reused to patch on top of."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()
            banner.apply_patch(target_path=target, home=home)
            patched_bytes = target.read_bytes()
            stamp = json.loads(banner._patch_stamp_path(home).read_text(encoding="utf-8"))
            journal_path = pathlib.Path(stamp["journal_path"])
            journal_path.write_text('{"tampered": true}', encoding="utf-8")

            target.write_bytes(original_bytes)  # target reverted externally
            result = banner.apply_patch(target_path=target, home=home)

            self.assertEqual(result["status"], "journal-invalid")
            # Refuses outright: the tampered journal is untouched, and the
            # target is NOT re-patched over an unreliable recovery record.
            self.assertEqual(journal_path.read_text(encoding="utf-8"), '{"tampered": true}')
            self.assertEqual(target.read_bytes(), original_bytes)
            self.assertNotEqual(target.read_bytes(), patched_bytes)

    def test_apply_patch_reuses_a_valid_existing_journal_without_rewriting_it(self):
        """F5's other half: a journal that IS valid for the current
        original bytes must be reused (not rewritten) -- proven by
        recording its mtime/content, deleting the target's patched state
        via an external restore-like write, then re-patching and checking
        the journal file is byte-identical to before."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()
            first = banner.apply_patch(target_path=target, home=home)
            journal_path = pathlib.Path(first["journal_path"])
            journal_bytes_before = journal_path.read_bytes()

            # Externally revert the target back to its original bytes,
            # then delete only the stamp (simulating a lost stamp, not a
            # lost journal) so apply_patch re-enters the "write" path.
            target.write_bytes(original_bytes)
            banner._patch_stamp_path(home).unlink()

            second = banner.apply_patch(target_path=target, home=home)
            self.assertEqual(second["status"], "patched")
            self.assertEqual(journal_path.read_bytes(), journal_bytes_before)

    def test_apply_patch_target_not_found_degrades_gracefully(self):
        # FLOOR: never let target_path=None fall through to the real
        # resolve_cli_target_path() in a test -- on a machine with Claude
        # Code actually installed that would resolve (and this test would
        # then patch) the REAL binary. Force resolution to fail instead.
        with tempfile.TemporaryDirectory() as home, \
             unittest.mock.patch.object(banner, "resolve_cli_target_path",
                                         return_value=None):
            result = banner.apply_patch(target_path=None, home=home)
            self.assertEqual(result["status"], "target-not-found")

    def test_apply_patch_pattern_not_found_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp, content=b"plain ascii, no art at all")
            before = target.read_bytes()
            result = banner.apply_patch(target_path=target, home=home)

            self.assertEqual(result["status"], "pattern-not-found")
            self.assertEqual(target.read_bytes(), before)  # untouched
            self.assertFalse(banner._patch_stamp_path(home).is_file())

    def test_recheck_patch_is_a_noop_without_a_prior_takeover(self):
        """recheck_patch() is what every generated shim calls on every
        `claude` launch -- it MUST be a complete no-op (no reads/writes
        beyond checking for the stamp) for the overwhelming majority of
        users who never opted in."""
        with tempfile.TemporaryDirectory() as home:
            banner.recheck_patch(home=home)  # must not raise
            self.assertFalse(banner._patch_stamp_path(home).is_file())

    def test_recheck_patch_repatches_after_an_update_changes_the_bundle(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            banner.apply_patch(target_path=target, home=home, cli_version="1.0.0")
            patched_v1 = target.read_bytes()

            # Simulate a Claude Code update: new bundle content, unpatched.
            # Repeated well past _LOW_COUNT_THRESHOLD so this test exercises
            # the "credible art, repatch it" path, not the low-count floor
            # (that's TestLowCountPlausibilityFloor's job).
            new_art = "▙▚▛▜▝▞▟▘" * 15  # 8 * 15 = 120 hits
            target.write_bytes(f'console.log("{new_art}");'.encode("utf-8"))

            banner.recheck_patch(home=home)

            self.assertNotEqual(target.read_bytes(), patched_v1)
            self.assertEqual(banner.find_block_art_sequences(target.read_bytes()), [])
            stamp = json.loads(banner._patch_stamp_path(home).read_text(encoding="utf-8"))
            self.assertEqual(stamp["version"], "1.0.0")

    def test_recheck_patch_never_raises_on_a_missing_target(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            banner.apply_patch(target_path=target, home=home)
            target.unlink()
            banner.recheck_patch(home=home)  # must not raise


class TestOffsetsJournalBackupAndRestore(unittest.TestCase):
    """The journal-based backup strategy (2026-07-21 delta): a sidecar of
    per-offset original bytes + a whole-file hash header, written and
    fsync'd BEFORE the target is patched, replayed on --restore with a
    hash check before anything is written."""

    def _make_target(self, tmp, content=None):
        target = pathlib.Path(tmp) / "fake-cli.exe"
        target.write_bytes(content if content is not None else _fake_native_bundle_bytes())
        return target

    def test_restore_round_trips_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()
            banner.apply_patch(target_path=target, home=home)
            self.assertNotEqual(target.read_bytes(), original_bytes)

            result = banner.restore_patch(home=home)

            self.assertEqual(result["status"], "restored")
            self.assertEqual(target.read_bytes(), original_bytes)  # byte-identical
            self.assertFalse(banner._patch_stamp_path(home).is_file())

    def test_restore_round_trips_byte_identical_for_literal_form(self):
        """Same round-trip, but specifically for the literal-escape form --
        the one that dominates in the real probe."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            content = b'const ART="' + (b'\\u2580\\u2588' * 50) + b'";'
            target = pathlib.Path(tmp) / "fake-cli.exe"
            target.write_bytes(content)

            apply_result = banner.apply_patch(target_path=target, home=home)
            self.assertEqual(apply_result["form"], "literal-escape")
            self.assertNotEqual(target.read_bytes(), content)

            restore_result = banner.restore_patch(home=home)
            self.assertEqual(restore_result["status"], "restored")
            self.assertEqual(target.read_bytes(), content)

    def test_journal_is_written_before_the_target_is_patched(self):
        """The journal-before-patch ordering is what makes a crash mid-
        operation safe: if the journal write happens first (and fsync's),
        a crash before the target write leaves the target untouched.
        Verified here by making the target write raise and confirming the
        journal survived on disk regardless."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()

            with unittest.mock.patch.object(
                    banner, "_atomic_write_bytes",
                    side_effect=RuntimeError("simulated crash writing target")):
                with self.assertRaises(RuntimeError):
                    banner.apply_patch(target_path=target, home=home)

            # Target untouched (the simulated crash happened before/during
            # its write)...
            self.assertEqual(target.read_bytes(), original_bytes)
            # ...but the journal was already written and fsync'd.
            state_dir = banner._patch_state_dir(home)
            journals = list(state_dir.glob("*.journal.json"))
            self.assertEqual(len(journals), 1)
            journal = json.loads(journals[0].read_text(encoding="utf-8"))
            self.assertEqual(journal["orig_sha256"], banner._sha256(original_bytes))

    def test_restore_with_no_stamp_is_a_graceful_noop(self):
        with tempfile.TemporaryDirectory() as home:
            result = banner.restore_patch(home=home)
            self.assertEqual(result["status"], "nothing-to-restore")

    def test_restore_refuses_when_target_changed_unexpectedly(self):
        """If the target file changed to bytes matching neither the
        recorded original nor the recorded patched hash (e.g. a Claude Code
        update landed without a repatch), restore must refuse to overwrite
        rather than clobber the update -- and must leave the journal/stamp
        in place so the situation is diagnosable. This is the hash-
        mismatch-refusal requirement."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            banner.apply_patch(target_path=target, home=home)
            target.write_bytes(b"a completely different, unrelated build")

            result = banner.restore_patch(home=home)

            self.assertEqual(result["status"], "target-changed")
            self.assertTrue(banner._patch_stamp_path(home).is_file())
            self.assertEqual(target.read_bytes(),
                              b"a completely different, unrelated build")

    def test_restore_refuses_and_writes_nothing_on_journal_integrity_error(self):
        """If the journal's own replacements somehow don't reproduce the
        recorded orig_sha256 (corrupted journal, tampering, a bug), restore
        must refuse rather than write bytes it can't verify. Simulated by
        corrupting one recorded original-byte entry after a real patch."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            apply_result = banner.apply_patch(target_path=target, home=home)
            patched_bytes = target.read_bytes()

            journal_path = pathlib.Path(apply_result["journal_path"])
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            # Corrupt the first recorded original-bytes entry.
            journal["replacements"][0][1] = "ffffffffffff"
            journal_path.write_text(json.dumps(journal), encoding="utf-8")

            result = banner.restore_patch(home=home)

            self.assertEqual(result["status"], "journal-integrity-error")
            self.assertEqual(target.read_bytes(), patched_bytes)  # nothing written

    def test_restore_missing_journal_refuses_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            apply_result = banner.apply_patch(target_path=target, home=home)
            pathlib.Path(apply_result["journal_path"]).unlink()

            result = banner.restore_patch(home=home)
            self.assertEqual(result["status"], "journal-missing")

    def test_restore_already_clean_clears_journal_and_stamp(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()
            apply_result = banner.apply_patch(target_path=target, home=home)
            journal_path = pathlib.Path(apply_result["journal_path"])

            target.write_bytes(original_bytes)  # externally restored already

            result = banner.restore_patch(home=home)
            self.assertEqual(result["status"], "already-clean")
            self.assertFalse(banner._patch_stamp_path(home).is_file())
            self.assertFalse(journal_path.is_file())

    def test_journal_does_not_require_a_full_copy_of_the_target(self):
        """The journal only records the bytes that actually changed, not a
        second full copy of the (potentially huge) target -- proven by
        showing the journal is far smaller than the target for a target
        with a small number of replacements relative to its size."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            # A large-ish target with a tiny number of art escapes,
            # mirroring the real probe's 248MB-file/488-hits ratio (here
            # scaled down for test speed).
            padding = b"x" * 200_000
            # 40 repeats * 3 escapes = 120 hits -- above _LOW_COUNT_THRESHOLD
            # (100) so this exercises the normal patch path, still tiny
            # relative to the padding either side of it.
            content = padding + (b'\\u2580\\u2588\\u2591' * 40) + padding
            target = pathlib.Path(tmp) / "fake-cli.exe"
            target.write_bytes(content)

            result = banner.apply_patch(target_path=target, home=home)
            journal_path = pathlib.Path(result["journal_path"])

            self.assertLess(journal_path.stat().st_size, len(content) / 10)


class TestConfirmToWriteBinding(unittest.TestCase):
    """F3 (verify-bounce finding): the confirmed plan (target path + its
    whole-file hash, both surfaced by patch_report/_classify_patch_plan as
    'target' / 'target_sha256') must be bound to the actual write --
    apply_patch(expect_target=..., expect_hash=...) refuses if the
    resolved target or its current hash differs from what was confirmed,
    catching a swap between preview and confirmation rather than
    silently patching a different file than the human approved."""

    def _make_target(self, tmp, content=None):
        target = pathlib.Path(tmp) / "fake-cli.js"
        target.write_bytes(content if content is not None else _fake_bundle_bytes(repeat=4))
        return target

    def test_patch_report_surfaces_target_and_hash_for_binding(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            report = banner.patch_report(target_path=target, home=home)
            self.assertEqual(report["target"], str(target))
            self.assertEqual(report["target_sha256"], banner._sha256(target.read_bytes()))

    def test_apply_patch_succeeds_when_expect_target_and_hash_match(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            preview = banner.patch_report(target_path=target, home=home)

            result = banner.apply_patch(target_path=target, home=home,
                                         expect_target=preview["target"],
                                         expect_hash=preview["target_sha256"])
            self.assertEqual(result["status"], "patched")

    def test_apply_patch_refuses_on_hash_changed_between_preview_and_apply(self):
        """The core F3 scenario: preview the file, something changes it
        (an update, a swap, tampering), then confirm with the STALE hash
        -- apply_patch must refuse, not patch the new content under the
        old approval."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            preview = banner.patch_report(target_path=target, home=home)
            before = target.read_bytes()

            # The file changes after preview, before the confirmed apply.
            target.write_bytes(_fake_bundle_bytes(repeat=5))

            changed_bytes = target.read_bytes()
            result = banner.apply_patch(target_path=target, home=home,
                                         expect_target=preview["target"],
                                         expect_hash=preview["target_sha256"])

            self.assertEqual(result["status"], "hash-mismatch")
            self.assertNotEqual(changed_bytes, before)  # changed by the test setup, not by apply_patch
            self.assertEqual(target.read_bytes(), changed_bytes)  # apply_patch wrote nothing
            self.assertFalse(banner._patch_stamp_path(home).is_file())  # nothing was written

    def test_apply_patch_refuses_on_path_changed_between_preview_and_apply(self):
        """If the resolved target itself is a DIFFERENT file than what was
        confirmed (e.g. resolution now finds a different candidate),
        apply_patch must refuse rather than patch whatever it currently
        resolves to."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            other_target = pathlib.Path(tmp) / "other-cli.js"
            other_target.write_bytes(_fake_bundle_bytes(repeat=4))

            preview = banner.patch_report(target_path=target, home=home)

            # Confirmed apply resolves a DIFFERENT path than was previewed.
            result = banner.apply_patch(target_path=other_target, home=home,
                                         expect_target=preview["target"],
                                         expect_hash=preview["target_sha256"])

            self.assertEqual(result["status"], "target-mismatch")
            self.assertFalse(banner._patch_stamp_path(home).is_file())


class TestStampBoundRecoveryAndTOCTOU(unittest.TestCase):
    """F6 (stampless recovery + crash-window pending stamp) and F7 (single-
    read discipline in apply_patch/recheck_patch)."""

    def _make_target(self, tmp, content=None):
        target = pathlib.Path(tmp) / "fake-cli.js"
        target.write_bytes(content if content is not None else _fake_bundle_bytes(repeat=4))
        return target

    def test_apply_patch_writes_stamp_pending_then_applied(self):
        """F6: the stamp must exist with status 'pending' before the
        target is actually patched, then flip to 'applied' -- proven here
        by intercepting _atomic_write_bytes (the target write) and
        checking the on-disk stamp's status at that exact moment."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            observed = {}
            real_atomic_write = banner._atomic_write_bytes

            def spying_atomic_write(path, data):
                stamp = json.loads(banner._patch_stamp_path(home).read_text(encoding="utf-8"))
                observed["status_at_write_time"] = stamp["status"]
                return real_atomic_write(path, data)

            with unittest.mock.patch.object(banner, "_atomic_write_bytes",
                                             side_effect=spying_atomic_write):
                result = banner.apply_patch(target_path=target, home=home)

            self.assertEqual(result["status"], "patched")
            self.assertEqual(observed["status_at_write_time"], "pending")
            final_stamp = json.loads(banner._patch_stamp_path(home).read_text(encoding="utf-8"))
            self.assertEqual(final_stamp["status"], "applied")

    def test_restore_recovers_from_crash_window_pending_stamp(self):
        """Simulate the exact crash window F6 targets: the target write
        landed (the file IS patched), but the stamp never got its
        'applied' flip (process died in between). restore_patch must
        still recover correctly using the pending stamp + journal, since
        its classification is hash-based, not status-based."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()
            result = banner.apply_patch(target_path=target, home=home)
            self.assertEqual(result["status"], "patched")

            # Roll the stamp back to "pending" -- simulating that the final
            # flip-to-"applied" write never happened, even though the
            # target write (and journal) clearly did.
            stamp_path = banner._patch_stamp_path(home)
            stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
            stamp["status"] = "pending"
            stamp_path.write_text(json.dumps(stamp), encoding="utf-8")

            restore_result = banner.restore_patch(home=home)
            self.assertEqual(restore_result["status"], "restored")
            self.assertEqual(target.read_bytes(), original_bytes)

    def test_restore_discovers_journal_with_no_stamp_at_all(self):
        """F6 stampless recovery: delete the stamp entirely (simulating a
        stamp-write permission failure right after the journal+target
        write) -- restore_patch must still find and use the journal by
        scanning the journal directory."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            original_bytes = target.read_bytes()
            banner.apply_patch(target_path=target, home=home)

            banner._patch_stamp_path(home).unlink()  # stamp gone entirely
            self.assertFalse(banner._patch_stamp_path(home).is_file())

            result = banner.restore_patch(home=home)
            self.assertEqual(result["status"], "restored")
            self.assertIn("recovered without a stamp file", result["message"])
            self.assertEqual(target.read_bytes(), original_bytes)

    def test_apply_patch_does_exactly_one_read_of_the_target(self):
        """F7: apply_patch must call target.read_bytes() exactly once.
        Patched at the Path.read_bytes level (bound method) to count
        invocations against this specific file only."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            call_count = {"n": 0}
            real_read_bytes = pathlib.Path.read_bytes

            def counting_read_bytes(self_path):
                if self_path == target or str(self_path) == str(target):
                    call_count["n"] += 1
                return real_read_bytes(self_path)

            with unittest.mock.patch.object(pathlib.Path, "read_bytes", counting_read_bytes):
                result = banner.apply_patch(target_path=target, home=home)

            self.assertEqual(result["status"], "patched")
            self.assertEqual(call_count["n"], 1)

    def test_apply_patch_journal_hash_matches_the_single_read_buffer(self):
        """F7: the journal's orig_sha256 must be the hash of the EXACT
        buffer apply_patch used to compute the patch -- not a re-read.
        Simulated by making a second (hypothetical) read return different
        bytes and confirming the journal still reflects the FIRST read's
        content, not the second."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            real_content = target.read_bytes()
            real_hash = banner._sha256(real_content)

            call_count = {"n": 0}
            real_read_bytes = pathlib.Path.read_bytes

            def swap_after_first_read(self_path):
                call_count["n"] += 1
                # If apply_patch ever read a SECOND time, this would
                # return DIFFERENT bytes -- proving a real double-read bug.
                return real_read_bytes(self_path)

            with unittest.mock.patch.object(pathlib.Path, "read_bytes", swap_after_first_read):
                result = banner.apply_patch(target_path=target, home=home)

            self.assertEqual(call_count["n"], 1)
            journal = json.loads(pathlib.Path(result["journal_path"]).read_text(encoding="utf-8"))
            self.assertEqual(journal["orig_sha256"], real_hash)

    def test_recheck_patch_uses_its_own_single_read_not_a_stale_report(self):
        """F7 applies equally to recheck_patch's path (it just calls
        apply_patch, so the same single-read discipline holds) -- a
        bundle swapped in since the stamp was written is patched based on
        its OWN current bytes, never a stale cached read."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_target(tmp)
            banner.apply_patch(target_path=target, home=home, cli_version="1.0.0")

            new_content = f'console.log("{"▙▚▛▜▝▞▟▘" * 15}");'.encode("utf-8")
            target.write_bytes(new_content)

            call_count = {"n": 0}
            real_read_bytes = pathlib.Path.read_bytes

            def counting_read_bytes(self_path):
                if self_path == target or str(self_path) == str(target):
                    call_count["n"] += 1
                return real_read_bytes(self_path)

            with unittest.mock.patch.object(pathlib.Path, "read_bytes", counting_read_bytes):
                banner.recheck_patch(home=home)

            self.assertEqual(call_count["n"], 1)
            self.assertEqual(banner.find_block_art_sequences(target.read_bytes()), [])


class TestLowCountPlausibilityFloor(unittest.TestCase):
    """Real-machine incident follow-up (2026-07-21): a re-scan of the
    accidentally-patched real exe found 50 UTF-8-char-form occurrences
    still present even after the real 488-count literal-form art was
    removed -- 50 is not credible as startup art (legitimate UI glyphs,
    e.g. spinners, use the same Unicode block). apply_patch must refuse to
    act on a dominant-form count below _LOW_COUNT_THRESHOLD unless
    force=True is passed explicitly; patch_report must always surface the
    "low-count" status/message rather than silently reporting would-patch
    or silently skipping it."""

    def _make_low_count_target(self, tmp, n=None):
        n = banner._LOW_COUNT_THRESHOLD - 1 if n is None else n
        target = pathlib.Path(tmp) / "fake-cli.exe"
        target.write_bytes(("▀" * n).encode("utf-8"))
        return target

    def test_threshold_constant_is_below_the_real_observed_art_count(self):
        # 488 was the real observed startup-art count; the floor must sit
        # meaningfully below that so legitimate installs still patch, and
        # meaningfully above the 50 that turned out to be spurious.
        self.assertLess(banner._LOW_COUNT_THRESHOLD, 488)
        self.assertGreater(banner._LOW_COUNT_THRESHOLD, 50)

    def test_patch_report_marks_low_count_plan(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_low_count_target(tmp, n=50)
            report = banner.patch_report(target_path=target, home=home)

            self.assertEqual(report["status"], "low-count")
            self.assertEqual(report["count"], 50)
            self.assertIn("low-count", report["message"])
            self.assertIn("likely not startup art", report["message"])

    def test_patch_report_would_patch_at_or_above_threshold(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_low_count_target(tmp, n=banner._LOW_COUNT_THRESHOLD)
            report = banner.patch_report(target_path=target, home=home)
            self.assertEqual(report["status"], "would-patch")

    def test_apply_patch_refuses_low_count_without_force(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_low_count_target(tmp)
            before = target.read_bytes()

            result = banner.apply_patch(target_path=target, home=home)

            self.assertEqual(result["status"], "low-count")
            self.assertEqual(target.read_bytes(), before)  # untouched
            self.assertFalse(banner._patch_stamp_path(home).is_file())

    def test_apply_patch_proceeds_with_explicit_force(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_low_count_target(tmp)
            before = target.read_bytes()

            result = banner.apply_patch(target_path=target, home=home, force=True)

            self.assertEqual(result["status"], "patched")
            self.assertNotEqual(target.read_bytes(), before)
            self.assertTrue(banner._patch_stamp_path(home).is_file())

    def test_recheck_patch_never_force_patches_a_low_count_bundle(self):
        """The shim's --recheck-patch path must treat a low-count re-scan
        as a no-op (like already-patched), never silently force-patching
        it -- proven by patching a bundle once (establishing a stamp),
        then simulating an update that dropped the art count to a
        not-credible level, and confirming recheck_patch leaves it alone."""
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = self._make_low_count_target(
                tmp, n=banner._LOW_COUNT_THRESHOLD + 50)
            banner.apply_patch(target_path=target, home=home, cli_version="1.0.0")

            # Simulate an update that leaves only a low, not-credible count.
            low_count_bytes = self._make_low_count_target(tmp, n=30).read_bytes()
            target.write_bytes(low_count_bytes)

            banner.recheck_patch(home=home)

            self.assertEqual(target.read_bytes(), low_count_bytes)  # untouched


class TestPatchReportDryRun(unittest.TestCase):
    """patch_report() is the side-effect-free preview the confirm step
    (commands/banner.md) is built on -- must never write anything."""

    def test_dry_run_reports_count_form_and_paths_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = pathlib.Path(tmp) / "fake-cli.js"
            target.write_bytes(_fake_bundle_bytes(repeat=4))  # 120 hits, above the low-count floor
            before = target.read_bytes()

            report = banner.patch_report(target_path=target, home=home)

            self.assertEqual(report["status"], "would-patch")
            self.assertEqual(report["count"], 120)
            self.assertEqual(report["form"], "utf8-char")
            self.assertEqual(report["target"], str(target))
            self.assertIn("orn-banner-takeover", report["journal_path"])
            self.assertIn("orn-banner-takeover.stamp", report["stamp_path"])
            # Nothing written: target untouched, no journal, no stamp.
            self.assertEqual(target.read_bytes(), before)
            self.assertFalse(pathlib.Path(report["journal_path"]).exists())
            self.assertFalse(banner._patch_stamp_path(home).exists())

    def test_dry_run_reports_literal_form_when_it_dominates(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = pathlib.Path(tmp) / "fake-cli.exe"
            target.write_bytes(_fake_native_bundle_bytes(literal_count=488, utf8_count=7))
            report = banner.patch_report(target_path=target, home=home)
            self.assertEqual(report["status"], "would-patch")
            self.assertEqual(report["form"], "literal-escape")
            self.assertEqual(report["count"], 488)

    def test_dry_run_pattern_not_found(self):
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as home:
            target = pathlib.Path(tmp) / "fake-cli.js"
            target.write_bytes(b"totally plain ascii")
            report = banner.patch_report(target_path=target, home=home)
            self.assertEqual(report["status"], "pattern-not-found")
            self.assertEqual(report["count"], 0)

    def test_dry_run_target_not_found_when_resolution_fails(self):
        # FLOOR: same hazard as apply_patch above -- force resolution to
        # fail rather than let it walk onto the real machine's install.
        with tempfile.TemporaryDirectory() as home, \
             unittest.mock.patch.object(banner, "resolve_cli_target_path",
                                         return_value=None):
            report = banner.patch_report(target_path=None, home=home)
            self.assertEqual(report["status"], "target-not-found")
            self.assertIsNone(report["target"])

    def test_dry_run_message_mentions_no_changes_would_be_made(self):
        with tempfile.TemporaryDirectory() as home, \
             unittest.mock.patch.object(banner, "resolve_cli_target_path",
                                         return_value=None):
            report = banner.patch_report(target_path=None, home=home)
            self.assertIn("no binary changes would be made", report["message"])


class TestSingleModeInstallOrchestration(unittest.TestCase):
    """banner_install.install_all()/restore_all() -- the single merged
    mode. Everything here stubs banner_install.banner_patch's apply_patch/
    restore_patch/patch_report so no real filesystem write ever happens
    outside the assertions being made about ORCHESTRATION (does install
    call the patch step? does it proceed to shims even when the patch is
    skipped? does confirmed=False write nothing at all?)."""

    def test_install_all_without_confirmation_writes_nothing(self):
        calls = {"apply_patch": 0}

        def fake_apply_patch(**kwargs):
            calls["apply_patch"] += 1
            return {"status": "patched", "target": "x", "message": "should not run"}

        with unittest.mock.patch.object(banner_install.banner_patch, "apply_patch",
                                         side_effect=fake_apply_patch), \
             unittest.mock.patch.object(banner_install.banner_patch, "patch_report",
                                         return_value={
                                             "status": "would-patch", "target": "C:\\fake\\cli.js",
                                             "count": 5, "form": "literal-escape",
                                             "journal_path": "C:\\fake\\journal.json",
                                             "stamp_path": "C:\\fake\\stamp", "message": "would patch 5",
                                         }):
            report = banner_install.install_all(confirmed=False)

        self.assertEqual(calls["apply_patch"], 0)
        joined = "\n".join(report)
        self.assertIn("DRY RUN", joined)
        self.assertIn("C:\\fake\\cli.js", joined)
        self.assertIn("journal", joined.lower())
        self.assertIn("stamp", joined.lower())

    def test_install_all_confirmed_patches_after_shims_succeed(self):
        """F4: write order is shims FIRST, patch LAST."""
        order = []

        def fake_apply_patch(**kwargs):
            order.append("patch")
            return {"status": "patched", "target": "C:\\fake\\cli.js", "count": 3,
                     "form": "literal-escape", "message": "patched 3"}

        def fake_detect_ps():
            order.append("shim-detect")
            return []

        with tempfile.TemporaryDirectory() as shim_tmp, \
             unittest.mock.patch.object(banner_install.banner_patch, "apply_patch",
                                         side_effect=fake_apply_patch), \
             unittest.mock.patch.object(banner_install, "resolve_claude_cli_path",
                                         return_value=_real_claude_exe(shim_tmp)), \
             unittest.mock.patch.object(banner_install, "resolve_python_interpreter",
                                         return_value=None), \
             unittest.mock.patch.object(banner_install, "resolve_banner_py_path",
                                         return_value=None), \
             unittest.mock.patch.object(banner_install, "detect_powershell_profiles",
                                         side_effect=fake_detect_ps), \
             unittest.mock.patch.object(banner_install, "detect_shell_rc_files",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "default_shim_dir",
                                         return_value=pathlib.Path(shim_tmp)), \
             unittest.mock.patch.object(banner_install, "scan_legacy_artifacts",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "install_autorun",
                                         return_value=("unchanged", None)), \
             unittest.mock.patch.object(banner_install, "dedupe_user_level_orn_motd",
                                         return_value="user-level orn-motd hook: none found"):
            report = banner_install.install_all(confirmed=True, home=shim_tmp)

        self.assertEqual(order, ["shim-detect", "patch"])
        self.assertTrue(any("binary patch" in line for line in report))

    def test_install_all_refuses_entire_install_when_claude_cli_not_found(self):
        """F4: no patch-only partials -- if the launcher shim can't be
        installed at all (no `claude` resolvable on PATH), the ENTIRE
        install is refused, including the binary patch that might
        otherwise have been resolvable via the native-root fallback."""
        calls = {"apply_patch": 0}

        def fake_apply_patch(**kwargs):
            calls["apply_patch"] += 1
            return {"status": "patched", "target": "x", "message": "should not run"}

        with tempfile.TemporaryDirectory() as tmp, \
             unittest.mock.patch.object(banner_install.banner_patch, "apply_patch",
                                         side_effect=fake_apply_patch), \
             unittest.mock.patch.object(banner_install, "resolve_claude_cli_path",
                                         return_value=None):
            report = banner_install.install_all(confirmed=True, home=tmp)

        self.assertEqual(calls["apply_patch"], 0)
        joined = "\n".join(report)
        self.assertIn("refusing the ENTIRE install", joined)

    def test_install_all_proceeds_to_shims_even_when_pattern_not_found(self):
        """Owner delta / EARS: pattern-not-found must degrade gracefully --
        skip the patch, still install the splash wrapper."""
        with tempfile.TemporaryDirectory() as tmp, \
             unittest.mock.patch.object(
                banner_install.banner_patch, "apply_patch",
                return_value={"status": "pattern-not-found", "target": "C:\\fake\\cli.js",
                              "message": "no art found"}), \
             unittest.mock.patch.object(banner_install, "resolve_claude_cli_path",
                                         return_value=_real_claude_exe(tmp)), \
             unittest.mock.patch.object(banner_install, "resolve_python_interpreter",
                                         return_value=_real_claude_exe(tmp, "python.exe")), \
             unittest.mock.patch.object(banner_install, "resolve_banner_py_path",
                                         return_value=pathlib.Path(_real_claude_exe(tmp, "banner.py"))), \
             unittest.mock.patch.object(banner_install, "detect_powershell_profiles",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "detect_shell_rc_files",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "default_shim_dir",
                                         return_value=pathlib.Path(tmp)), \
             unittest.mock.patch.object(banner_install, "scan_legacy_artifacts",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "install_autorun",
                                         return_value=("unchanged", None)), \
             unittest.mock.patch.object(banner_install, "dedupe_user_level_orn_motd",
                                         return_value="user-level orn-motd hook: none found"):
            report = banner_install.install_all(confirmed=True, home=tmp)

        joined = "\n".join(report)
        self.assertIn("pattern-not-found", joined)
        # The shim-install pipeline still ran (didn't bail out after the
        # patch step) -- proven by reaching the orn-motd dedupe line that
        # only appears at the tail of the function.
        self.assertIn("user-level orn-motd hook", joined)

    def test_restore_all_restores_binary_and_removes_shims(self):
        with tempfile.TemporaryDirectory() as tmp, \
             unittest.mock.patch.object(
                banner_install.banner_patch, "restore_patch",
                return_value={"status": "restored", "target": "C:\\fake\\cli.js",
                              "message": "restored"}), \
             unittest.mock.patch.object(banner_install, "detect_powershell_profiles",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "detect_shell_rc_files",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "default_shim_dir",
                                         return_value=pathlib.Path(tmp)), \
             unittest.mock.patch.object(banner_install, "uninstall_autorun",
                                         return_value=("absent", None)), \
             unittest.mock.patch.object(banner_install, "dedupe_user_level_orn_motd",
                                         return_value="user-level orn-motd hook: none found"):
            report = banner_install.restore_all(home=tmp)

        joined = "\n".join(report)
        self.assertIn("binary restore", joined)
        self.assertIn("restored", joined)

    def test_status_all_reports_patch_stamp_state(self):
        with tempfile.TemporaryDirectory() as home:
            with unittest.mock.patch.object(banner_install, "detect_powershell_profiles",
                                             return_value=[]), \
                 unittest.mock.patch.object(banner_install, "detect_shell_rc_files",
                                             return_value=[]), \
                 unittest.mock.patch.object(banner_install, "get_autorun_value",
                                             return_value=None):
                report = banner_install.status_all(home=home)
            self.assertTrue(any("binary patch" in line and "not installed" in line
                                 for line in report))

            stamp_path = banner._patch_stamp_path(home)
            stamp_path.parent.mkdir(parents=True, exist_ok=True)
            stamp_path.write_text(json.dumps({"target": "C:\\fake\\cli.js"}), encoding="utf-8")
            with unittest.mock.patch.object(banner_install, "detect_powershell_profiles",
                                             return_value=[]), \
                 unittest.mock.patch.object(banner_install, "detect_shell_rc_files",
                                             return_value=[]), \
                 unittest.mock.patch.object(banner_install, "get_autorun_value",
                                             return_value=None):
                report = banner_install.status_all(home=home)
            self.assertTrue(any("binary patch" in line and "installed" in line
                                 for line in report))


class TestCliConfirmToWriteBindingAndVersionKeying(unittest.TestCase):
    """F3 CLI wiring (--target/--expect-hash REQUIRED with --yes) and F9
    (best-effort CLI version detection forwarded to apply_patch as
    informational metadata, not a correctness key)."""

    def _run_main(self, argv):
        buf = io.StringIO()
        with unittest.mock.patch.object(sys, "stdout", buf):
            banner_install.main(argv)
        return buf.getvalue()

    def test_install_yes_without_target_or_hash_is_refused(self):
        output = self._run_main(["install", "--yes"])
        self.assertIn("Refusing", output)
        self.assertIn("--target", output)
        self.assertIn("--expect-hash", output)

    def test_install_yes_with_only_target_is_refused(self):
        output = self._run_main(["install", "--yes", "--target", "C:\\fake\\cli.js"])
        self.assertIn("Refusing", output)

    def test_install_yes_with_target_and_hash_forwards_to_install_all(self):
        with unittest.mock.patch.object(banner_install, "install_all",
                                         return_value=["ok"]) as mock_install:
            self._run_main(["install", "--yes", "--target", "C:\\fake\\cli.js",
                             "--expect-hash", "deadbeef"])
        mock_install.assert_called_once()
        _, kwargs = mock_install.call_args
        self.assertEqual(kwargs["target"], "C:\\fake\\cli.js")
        self.assertEqual(kwargs["expect_hash"], "deadbeef")
        self.assertTrue(kwargs["confirmed"])

    def test_install_yes_with_none_sentinel_passes_none_through(self):
        with unittest.mock.patch.object(banner_install, "install_all",
                                         return_value=["ok"]) as mock_install:
            self._run_main(["install", "--yes", "--target", "none",
                             "--expect-hash", "NONE"])
        _, kwargs = mock_install.call_args
        self.assertIsNone(kwargs["target"])
        self.assertIsNone(kwargs["expect_hash"])

    def test_install_all_forwards_target_and_hash_to_apply_patch(self):
        captured = {}

        def fake_apply_patch(**kwargs):
            captured.update(kwargs)
            return {"status": "patched", "target": "x", "message": "ok"}

        with tempfile.TemporaryDirectory() as tmp, \
             unittest.mock.patch.object(banner_install.banner_patch, "apply_patch",
                                         side_effect=fake_apply_patch), \
             unittest.mock.patch.object(banner_install, "resolve_claude_cli_path",
                                         return_value=_real_claude_exe(tmp)), \
             unittest.mock.patch.object(banner_install, "resolve_python_interpreter",
                                         return_value=None), \
             unittest.mock.patch.object(banner_install, "resolve_banner_py_path",
                                         return_value=None), \
             unittest.mock.patch.object(banner_install, "detect_powershell_profiles",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "detect_shell_rc_files",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "default_shim_dir",
                                         return_value=pathlib.Path(tmp)), \
             unittest.mock.patch.object(banner_install, "scan_legacy_artifacts",
                                         return_value=[]), \
             unittest.mock.patch.object(banner_install, "install_autorun",
                                         return_value=("unchanged", None)), \
             unittest.mock.patch.object(banner_install, "dedupe_user_level_orn_motd",
                                         return_value="ok"), \
             unittest.mock.patch.object(banner_install, "_detect_claude_cli_version",
                                         return_value="2.1.206"):
            banner_install.install_all(confirmed=True, home=tmp, target="C:\\fake\\cli.js",
                                        expect_hash="deadbeef", force=True)

        self.assertEqual(captured["target_path"], "C:\\fake\\cli.js")
        self.assertEqual(captured["expect_target"], "C:\\fake\\cli.js")
        self.assertEqual(captured["expect_hash"], "deadbeef")
        self.assertTrue(captured["force"])
        self.assertEqual(captured["cli_version"], "2.1.206")

    def test_detect_claude_cli_version_swallows_failures(self):
        with unittest.mock.patch.object(banner_install.subprocess, "run",
                                         side_effect=Exception("no such binary")):
            self.assertIsNone(banner_install._detect_claude_cli_version("C:\\nope\\claude.exe"))


class TestCliRecheckPatchFlagWiredIntoEveryShim(unittest.TestCase):
    """The auto-repatch check must be wired into every generated launcher
    shim body, inside the same skip-guard as --anim, extending the existing
    generators rather than duplicating a parallel shim path."""

    def test_powershell_body_calls_recheck_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = banner_install.build_powershell_body(
                _real_claude_exe(tmp), _real_claude_exe(tmp, "python.exe"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("--recheck-patch", body)
        guard_idx = body.index("if (($args -notcontains '-p')")
        recheck_idx = body.index("--recheck-patch")
        close_idx = body.index("\n    }\n", recheck_idx)
        self.assertTrue(guard_idx < recheck_idx < close_idx)

    def test_bash_body_calls_recheck_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = banner_install.build_bash_body(
                _real_claude_exe(tmp, "claude"), _real_claude_exe(tmp, "python3"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("--recheck-patch", body)

    def test_claude_bat_calls_recheck_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            bat = banner_install.build_claude_bat(
                _real_claude_exe(tmp), _real_claude_exe(tmp, "python.exe"),
                _real_claude_exe(tmp, "banner.py"))
        self.assertIn("--recheck-patch", bat)

    def test_no_recheck_call_when_python_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_path = _real_claude_exe(tmp)
            bat = banner_install.build_claude_bat(claude_path, None, None)
            self.assertNotIn("--recheck-patch", bat)
            body = banner_install.build_powershell_body(claude_path, None, None)
            self.assertNotIn("--recheck-patch", body)

    def test_main_recheck_patch_flag_is_silent_and_never_raises(self):
        """--recheck-patch must produce zero stdout (it is invoked from
        inside a shim on every launch) and must never raise, per
        recheck_patch()'s own fail-silent contract."""
        with tempfile.TemporaryDirectory() as home:
            with unittest.mock.patch.object(banner, "_patch_stamp_path",
                                             return_value=pathlib.Path(home) / "nope.stamp"), \
                 unittest.mock.patch.object(sys, "argv", ["banner.py", "--recheck-patch"]):
                banner.main()  # must not raise, must not print


class TestLegacySplashOnlyPathRemoved(unittest.TestCase):
    """Owner delta 2026-07-22: there is no longer a splash-only install mode
    that skips the binary patch -- install_all() always runs apply_patch()
    as its first step when confirmed. Pins the removal so a future change
    can't silently reintroduce a patch-skipping fast path."""

    def test_install_all_source_calls_apply_patch_unconditionally(self):
        # inspect.unwrap follows __wrapped__ (set by the tools/conftest.py
        # hermeticity guard) through to the real install_all -- the bare
        # attribute is monkeypatched to a guarding wrapper for every test.
        source = inspect.getsource(inspect.unwrap(banner_install.install_all))
        # apply_patch must be called exactly once, and it must not be
        # gated behind any additional flag beyond `confirmed` itself (no
        # second "--takeover"-style opt-in anywhere in this function).
        self.assertEqual(source.count("banner_patch.apply_patch("), 1)
        self.assertNotIn("takeover", source.replace("banner_patch.apply_patch(", ""))

    def test_no_standalone_takeover_flag_exists_on_the_banner_cli(self):
        # The mission's original --takeover/--restore flag pair was
        # superseded before it ever shipped -- confirm neither banner.py
        # nor banner_install.py expose a "--takeover" CLI flag; installing
        # IS taking over now, gated by install_all(confirmed=...).
        banner_source = pathlib.Path(banner.__file__).read_text(encoding="utf-8")
        install_source = pathlib.Path(banner_install.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"--takeover"', banner_source)
        self.assertNotIn('"--takeover"', install_source)

    def test_banner_install_cli_has_no_splash_only_install_choice(self):
        """argparse's `install` action always means the single merged mode
        -- there must be no separate action name (e.g. 'install-splash',
        'shim-only') offering a patch-skipping alternative."""
        source = pathlib.Path(banner_install.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"install-splash"', source)
        self.assertNotIn('"shim-only"', source)
        # "restore" must be a first-class action, not bolted on separately
        # from "install" -- confirms the CLI surface was actually widened,
        # not left as the old three-action (install/uninstall/status) set.
        self.assertIn('"restore"', source)


if __name__ == "__main__":
    unittest.main()
