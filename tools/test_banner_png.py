"""Tests for tools/banner_png.py — the ANSI-to-PNG terminal banner renderer.

Hermetic: tests the ANSI half-block parser against small synthetic
snippets (not the real assets/banner.ans, whose pixel output is not
compared exactly since fonts/AA are involved in the full composite) and
checks that running the script produces a PNG with sane minimum
dimensions. Also verifies the Pillow-missing path degrades to a clear
stderr message instead of a stack trace.
"""
import builtins
import importlib
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import banner_png  # noqa: E402


def test_parse_upper_half_block_fg_only():
    # "\x1b[38;2;255;0;0m" + upper-half-block + reset: fg on top pixel,
    # bottom pixel transparent (no bg was ever set).
    snippet = "\x1b[38;2;255;0;0m▀\x1b[0m"
    grid = banner_png.parse_ansi_art(snippet)
    assert len(grid) == 2  # one text row -> 2 pixel rows
    assert grid[0] == [(255, 0, 0, 255)]
    assert grid[1] == [(0, 0, 0, 0)]


def test_parse_upper_half_block_fg_and_bg():
    # fg+bg both set before the glyph: ▀ = fg top, bg bottom.
    snippet = "\x1b[38;2;0;255;0m\x1b[48;2;0;0;255m▀\x1b[0m"
    grid = banner_png.parse_ansi_art(snippet)
    assert grid[0] == [(0, 255, 0, 255)]
    assert grid[1] == [(0, 0, 255, 255)]


def test_parse_lower_half_block_swaps_top_and_bottom():
    # ▄ = bg on top, fg on bottom (opposite of ▀).
    snippet = "\x1b[38;2;10;20;30m\x1b[48;2;40;50;60m▄\x1b[0m"
    grid = banner_png.parse_ansi_art(snippet)
    assert grid[0] == [(40, 50, 60, 255)]
    assert grid[1] == [(10, 20, 30, 255)]


def test_parse_space_with_no_color_is_transparent():
    snippet = " "
    grid = banner_png.parse_ansi_art(snippet)
    assert grid[0] == [(0, 0, 0, 0)]
    assert grid[1] == [(0, 0, 0, 0)]


def test_parse_two_columns_positions_line_up():
    # col0: red ▀ on black bg. col1: plain space (transparent).
    snippet = "\x1b[38;2;255;0;0m\x1b[48;2;0;0;0m▀\x1b[0m "
    grid = banner_png.parse_ansi_art(snippet)
    assert grid[0][0] == (255, 0, 0, 255)
    assert grid[1][0] == (0, 0, 0, 255)
    assert grid[0][1] == (0, 0, 0, 0)
    assert grid[1][1] == (0, 0, 0, 0)


def test_parse_multiline_pads_ragged_rows_to_rectangle():
    # Two lines of different visible width -> build_bird_grid style
    # padding is exercised via the grid-building helper, not the raw
    # per-line parse (which legitimately returns ragged rows).
    text = "\x1b[38;2;1;2;3m▀\x1b[0m\n\x1b[38;2;4;5;6m▀▀\x1b[0m"
    grid, width, height = banner_png.build_grid_from_ansi_text(text)
    assert width == 2
    assert height == 4  # 2 text lines * 2 pixel rows
    assert all(len(row) == width for row in grid)
    # first line's second column padded transparent
    assert grid[0][1] == (0, 0, 0, 0)
    assert grid[1][1] == (0, 0, 0, 0)


def test_regenerate_produces_png_with_min_dimensions(tmp_path, monkeypatch):
    out_path = tmp_path / "banner-terminal.png"
    monkeypatch.setattr(banner_png, "OUT_PATH", out_path)
    rc = banner_png.main()
    assert rc == 0
    assert out_path.is_file()
    from PIL import Image
    with Image.open(out_path) as img:
        assert img.width >= 200
        assert img.height >= 200
        assert img.mode in ("RGB", "RGBA")


def test_main_degrades_cleanly_without_pillow(monkeypatch, capsys):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("No module named 'PIL'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    rc = banner_png.main()
    captured = capsys.readouterr()
    assert rc != 0
    assert "pillow" in captured.err.lower() or "pillow" in captured.out.lower()
    assert "Traceback" not in captured.err


def test_no_version_number_in_taglines():
    # Acceptance: no version baked into the image -- guard the tagline
    # constants themselves so a future edit can't reintroduce one.
    import re
    assert not re.search(r"\bv?\d+\.\d+", banner_png.TAGLINE_1)
    assert not re.search(r"\bv?\d+\.\d+", banner_png.TAGLINE_2)
