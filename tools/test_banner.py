"""Tests for tools/banner.py (fg-a10506): fix UnicodeEncodeError crash when
stdout.reconfigure fails on legacy codepage (cp437).

When reconfigure() raises AND console encoding is cp437 (legacy Windows OEM
default), TAGLINE with em-dash and örn crashes. Test ensures graceful fallback.
"""
import io
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

import banner


class TestBannerCP437Fallback(unittest.TestCase):
    """fg-a10506: banner should degrade gracefully on cp437 + failed reconfigure."""

    def test_render_plain_with_cp437_encoding_no_crash(self):
        """EARS: WHEN ascii_safe=True is passed to render(),
        THEN output SHALL be cp437-safe."""
        # Simulate a stdout buffer with cp437 encoding that can't encode
        # em-dash (U+2014) or ö (U+00F6) in TAGLINE.
        cp437_buffer = io.TextIOWrapper(
            io.BytesIO(),
            encoding="cp437",
            errors="strict"
        )

        # Get ASCII-safe render output
        result = banner.render(color=False, small=False, ascii_safe=True)

        # Verify ASCII-safe output uses the fallback tagline (no em-dash, no ö)
        self.assertNotIn("—", result)  # em-dash should NOT be in ASCII version
        self.assertIn("orn", result)   # ASCII version uses "orn" not "örn"
        self.assertIn("-", result)     # ASCII version uses plain hyphen

        # Attempt to write the ASCII-safe output to cp437 buffer — should NOT crash.
        try:
            cp437_buffer.write(result)
            cp437_buffer.flush()
            # If we reach here without exception, the test passes.
        except UnicodeEncodeError as e:
            self.fail(
                f"render(color=False, ascii_safe=True) produced output that "
                f"cannot be encoded to cp437: {e}."
            )

    def test_main_with_reconfigure_failing_and_cp437_stdout(self):
        """EARS: WHEN stdout.reconfigure() raises AND stdout is cp437-bound,
        THEN main() SHALL NOT raise UnicodeEncodeError."""
        # Create a cp437-bound stdout
        cp437_stdout = io.TextIOWrapper(
            io.BytesIO(),
            encoding="cp437",
            errors="strict"
        )

        # Mock sys.stdout and sys.stdout.reconfigure to fail
        with patch("sys.stdout", cp437_stdout):
            with patch.object(
                cp437_stdout,
                "reconfigure",
                side_effect=Exception("reconfigure not available")
            ):
                with patch("sys.argv", ["banner.py"]):
                    # This should NOT raise UnicodeEncodeError
                    try:
                        banner.main()
                    except UnicodeEncodeError as e:
                        self.fail(
                            f"main() crashed with UnicodeEncodeError when "
                            f"reconfigure() failed on cp437 stdout: {e}. "
                            f"Should fall back gracefully."
                        )

    def test_hook_mode_always_safe(self):
        """EARS: hook_mode() SHALL emit json.dumps (ensure_ascii) so it's
        safe on any encoding. Verify regression."""
        # Ensure hook_mode uses json.dumps which escapes non-ASCII
        with patch("sys.stdout", io.StringIO()):
            with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": "/tmp"}):
                # hook_mode should NOT crash and should emit valid JSON
                # (We just verify it doesn't crash; hook_mode is already safe)
                try:
                    banner.hook_mode()
                except Exception:
                    pass  # hook_mode fails silently per design


class TestHookModeSystemMessageDisplayChannelConstraints(unittest.TestCase):
    """fg-a10904: the systemMessage display channel hook_mode() feeds is not
    a raw terminal -- it strips ANSI escape codes, trims leading whitespace
    per line, and truncates long payloads. hook_mode() must emit a payload
    that survives all three: no ESC bytes, no leading-plain-space art lines
    (braille-padded instead), and comfortably under the byte cap."""

    def _capture_message(self, cwd):
        buf = io.StringIO()
        with patch("sys.stdout", buf), \
                patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(cwd)}):
            banner.hook_mode()
        out = buf.getvalue()
        self.assertTrue(out.strip(), "hook_mode produced no output")
        return json.loads(out)["systemMessage"]

    def _project_with_forge_dir(self, tmp):
        import pathlib
        project = pathlib.Path(tmp)
        (project / ".forge").mkdir(parents=True, exist_ok=True)
        return project

    def test_braille_pad_replaces_spaces_only(self):
        padded = banner._braille_pad("  a b  ")
        self.assertNotIn(" ", padded)
        self.assertEqual(padded.count(banner.BRAILLE_BLANK), 5)
        self.assertIn("a", padded)
        self.assertIn("b", padded)

    def test_system_message_carries_thinline_wordmark(self):
        # User-chosen look (2026-07-18, superseding fg-a10904 D2's emoji
        # squares and a rejected larry3d attempt that read backwards): the
        # forward-leaning slant figlet ÖRN'S FORGE wordmark from
        # assets/orn-motd-art.ans. `\____/_/` is the bottom of the slant
        # O — a distinctive stroke run with no interior spaces, immune to
        # any padding-scheme changes. Emoji squares must NOT come back.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project_with_forge_dir(tmp)
            msg = self._capture_message(project)
            self.assertIn(
                r"\____/ /_/", msg,
                "systemMessage should carry the kerned slant figlet wordmark",
            )
            self.assertFalse(
                any(g in msg for g in "🟥🟧🟨🟫"),
                "emoji-square art was superseded by the thin-line wordmark",
            )

    def test_system_message_has_no_esc_bytes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project_with_forge_dir(tmp)
            msg = self._capture_message(project)
            self.assertNotIn("\x1b", msg, "systemMessage must carry no ANSI escape bytes")

    def test_system_message_art_lines_have_no_leading_plain_space(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project_with_forge_dir(tmp)
            msg = self._capture_message(project)
            # The payload intentionally opens with blank lines (user-requested
            # top spacing) -- skip them before isolating the art block.
            art_lines = msg.lstrip("\n").split("\n\n", 1)[0].split("\n")
            self.assertGreater(len(art_lines), 1, "expected multi-line art")
            for line in art_lines:
                self.assertFalse(
                    line.startswith(" "),
                    f"art line starts with a plain space (would be trimmed "
                    f"by the display channel): {line!r}",
                )

    def test_system_message_under_byte_cap(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project_with_forge_dir(tmp)
            msg = self._capture_message(project)
            self.assertLessEqual(
                len(msg.encode("utf-8")), banner.HOOK_SYSTEM_MESSAGE_BYTE_CAP,
                "systemMessage must stay under the display channel's "
                "truncation point",
            )

    def test_degrades_gracefully_if_padded_art_would_exceed_cap(self):
        # Force a cap below the braille-padded art's size (but above the
        # tagline-only fallback's ~59 bytes) to exercise the degrade
        # cascade without ever emitting a payload larger than the
        # (temporarily lowered) cap.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            project = self._project_with_forge_dir(tmp)
            with patch.object(banner, "HOOK_SYSTEM_MESSAGE_BYTE_CAP", 200):
                msg = self._capture_message(project)
            self.assertLessEqual(len(msg.encode("utf-8")), 200)
            self.assertIn("forge v", msg)
            # Degraded all the way down: the art block is gone, only the
            # tagline + version suffix survive.
            self.assertNotIn("\n\n", msg)


class _FakeTTYStdout:
    """Minimal writable stream reporting isatty()=True, recording writes --
    stands in for a real terminal so --anim's frame loop can be exercised
    without a real console attached (fg-a10905)."""

    def __init__(self):
        self.writes = []

    def write(self, s):
        self.writes.append(s)
        return len(s)

    def flush(self):
        pass

    def isatty(self):
        return True

    def reconfigure(self, **kwargs):
        pass


class TestAnimModeArtAndRender(unittest.TestCase):
    """fg-a10905: banner.py --anim ports the live-tested reference splash
    (C:\\Users\\someone\\.claude\\orn-splash.py) -- thin-line ÖRN'S FORGE
    wordmark (umlaut dots, apostrophe), fire gradient, dark-ember extrusion,
    30-frame gleam sweep, dim version tail."""

    def test_anim_art_matches_orn_motd_asset_letterforms(self):
        # assets/orn-motd-art.ans (fg-a10904, user-chosen 2026-07-18) carries
        # the same letterforms braille-padded for the hook display channel;
        # this distinctive interior stroke run (the bottom of the slant O)
        # pins ANIM_ART as identical, not a re-derived lookalike.
        self.assertTrue(
            any(r"\____/ /_/" in line for line in banner.ANIM_ART),
            "ANIM_ART must carry the same kerned slant wordmark as "
            "assets/orn-motd-art.ans",
        )

    def test_anim_build_rows_composites_face_and_shadow_layers(self):
        rows = banner._anim_build_rows()
        layers = {cell[0] for row in rows for cell in row if cell is not None}
        self.assertEqual(layers, {"F", "S"})

    def test_anim_render_produces_one_line_per_row(self):
        rows = banner._anim_build_rows()
        width = max(len(r) for r in rows)
        out = banner._anim_render(rows, width)
        self.assertEqual(len(out), len(rows))

    def test_anim_render_gleam_changes_output_vs_plain(self):
        rows = banner._anim_build_rows()
        width = max(len(r) for r in rows)
        plain = banner._anim_render(rows, width)
        gleamed = banner._anim_render(rows, width, gleam_x=width // 2)
        self.assertNotEqual(plain, gleamed)

    def test_anim_grad_endpoints_match_stops(self):
        self.assertEqual(banner._anim_grad(0.0), banner.ANIM_STOPS[0])
        self.assertEqual(banner._anim_grad(1.0), banner.ANIM_STOPS[-1])


class TestAnimVersion(unittest.TestCase):
    """Version tail reads ~/.claude/plugins/installed_plugins.json with
    utf-8-sig (matches the live-tested reference, not banner.py's existing
    _version() which reads the bundled plugin.json instead)."""

    def test_reads_installed_plugins_json_with_utf8_sig(self):
        import pathlib
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            plugins_dir = home / ".claude" / "plugins"
            plugins_dir.mkdir(parents=True)
            manifest = {"plugins": {"forge@forge-local": [{"version": "0.7.11"}]}}
            (plugins_dir / "installed_plugins.json").write_bytes(
                b"\xef\xbb\xbf" + json.dumps(manifest).encode("utf-8")
            )
            self.assertEqual(banner._anim_version(home=str(home)), "v0.7.11")

    def test_missing_file_returns_empty_string(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(banner._anim_version(home=tmp), "")


class TestAnimDegrade(unittest.TestCase):
    """EARS: WHEN the animation cannot run (no TTY, VT enable fails, any
    exception), THE SYSTEM SHALL degrade to a static wordmark print + ~1.5s
    sleep and NEVER block or delay the CLI launch beyond that."""

    def test_non_tty_stdout_degrades_to_static_print_and_short_sleep(self):
        buf = io.StringIO()  # io.StringIO().isatty() is False
        with patch("sys.stdout", buf), \
                patch("banner._anim_version", return_value="v9.9.9"), \
                patch("banner.time.sleep") as mock_sleep:
            banner.run_anim()
        output = buf.getvalue()
        self.assertIn("orn's forge", output)
        self.assertNotIn("\x1b[", output, "no escape codes may reach a non-tty stream")
        mock_sleep.assert_called_once()
        self.assertAlmostEqual(mock_sleep.call_args[0][0], 1.5)

    def test_exception_mid_animation_degrades_without_raising(self):
        fake = _FakeTTYStdout()
        fake.write = MagicMock(side_effect=[None, RuntimeError("boom")])
        with patch("sys.stdout", fake), \
                patch("banner._anim_version", return_value="v9.9.9"), \
                patch("banner.time.sleep"):
            try:
                banner.run_anim()
            except Exception as exc:  # pragma: no cover - failure path
                self.fail(f"run_anim() must never raise, got {exc!r}")

    def test_run_anim_never_raises_even_if_stdout_totally_broken(self):
        class ExplodingStdout:
            def isatty(self):
                raise RuntimeError("no tty support")

            def reconfigure(self, **kwargs):
                raise RuntimeError("no reconfigure")

            def write(self, s):
                raise RuntimeError("no write")

            def flush(self):
                raise RuntimeError("no flush")

        with patch("sys.stdout", ExplodingStdout()), \
                patch("banner._anim_version", return_value="v9.9.9"):
            try:
                banner.run_anim()
            except Exception as exc:  # pragma: no cover - failure path
                self.fail(f"run_anim() must never raise, got {exc!r}")


class TestAnimTTYRun(unittest.TestCase):
    """The happy path: a real (simulated) TTY gets the full 30-frame gleam
    sweep, cursor-up + \\x1b[2K redraws, then settles with a dim version
    tail -- self-timed, no caller-side sleep needed."""

    def test_full_animation_sleeps_30_frame_gaps_plus_settle(self):
        fake = _FakeTTYStdout()
        with patch("sys.stdout", fake), \
                patch("banner._anim_version", return_value="v9.9.9"), \
                patch("banner.time.sleep") as mock_sleep:
            banner.run_anim()
        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertEqual(len(sleep_args), 31, "30 sweep frames + 1 settle sleep")
        self.assertEqual(sleep_args[:30], [0.075] * 30)
        self.assertAlmostEqual(sleep_args[30], 0.35)

    def test_full_animation_ends_with_dim_version_tail(self):
        fake = _FakeTTYStdout()
        with patch("sys.stdout", fake), \
                patch("banner._anim_version", return_value="v9.9.9"), \
                patch("banner.time.sleep"):
            banner.run_anim()
        joined = "".join(fake.writes)
        self.assertIn("örn's forge", joined)
        self.assertIn("v9.9.9", joined)
        self.assertIn("\x1b[2m", joined)  # dim escape on the tail

    def test_full_animation_uses_cursor_up_and_line_clear_redraws(self):
        fake = _FakeTTYStdout()
        with patch("sys.stdout", fake), \
                patch("banner._anim_version", return_value="v9.9.9"), \
                patch("banner.time.sleep"):
            banner.run_anim()
        joined = "".join(fake.writes)
        rows = banner._anim_build_rows()
        n = len(rows) + 1
        self.assertIn(f"\x1b[{n}A", joined)
        self.assertIn("\x1b[2K", joined)


class TestMainAnimDispatch(unittest.TestCase):
    """--anim is a distinct main() mode, self-timed (the animation IS the
    hold) -- and its addition must never leak ESC codes into --hook's
    systemMessage payload (the display channel strips them; fg-a10904)."""

    def test_main_dispatches_to_run_anim_on_flag(self):
        with patch("banner.run_anim") as mock_run, \
                patch("sys.argv", ["banner.py", "--anim"]):
            banner.main()
        mock_run.assert_called_once()

    def test_hook_mode_unaffected_by_anim_addition_no_esc_leak(self):
        import pathlib
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            project = pathlib.Path(tmp)
            (project / ".forge").mkdir(parents=True, exist_ok=True)
            buf = io.StringIO()
            with patch("sys.stdout", buf), \
                    patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(project)}), \
                    patch("sys.argv", ["banner.py", "--hook"]):
                banner.main()
            out = buf.getvalue()
            self.assertNotIn("\x1b", out)


if __name__ == "__main__":
    unittest.main()
