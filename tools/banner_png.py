#!/usr/bin/env python3
"""ANSI-to-PNG renderer: regenerates assets/banner-terminal.png from the
CURRENT in-repo terminal art -- a committed, repeatable script instead of
a one-off screenshot (fg-a10919).

Sources of truth (do not hardcode art here -- read it from these):
  - assets/banner.ans      truecolor half-block pixel-bird art (▀/▄ with
                            24-bit SGR fg/bg codes -- each character cell
                            is 2 vertical pixels).
  - tools/banner.py         ANIM_ART_RAW: the kerned slant "ORNS FORGE"
                            wordmark (degree-dot umlaut) + ANIM_STOPS, its
                            left-to-right fire gradient. Imported directly
                            (not copied) so this stays in sync with the
                            terminal --anim splash automatically.

Usage:
    python tools/banner_png.py

Deterministic: same committed sources in -> same PNG out (modulo font
availability -- see _load_font). No version number is baked into the
image (it would stale on every release bump); the taglines are the only
text drawn.

Dependency: Pillow (pip install pillow) -- a dev-machine tool dependency,
not a runtime dependency of the plugin. This module is importable and its
pure-parsing functions are testable without Pillow installed; only
main()/compose() touch PIL, and main() degrades to a clear stderr message
(not a stack trace) if Pillow is missing.
"""
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ANSI_PATH = PLUGIN_ROOT / "assets" / "banner.ans"
OUT_PATH = PLUGIN_ROOT / "assets" / "banner-terminal.png"

TAGLINE_1 = "örn is at the anvil — the forge is lit"
TAGLINE_2 = "queue-driven · adversarially verified"

_ESC_RE = re.compile(r"(\x1b\[[0-9;]*m)")
_UPPER_HALF_BLOCK = "▀"  # ▀
_LOWER_HALF_BLOCK = "▄"  # ▄

_TRANSPARENT = (0, 0, 0, 0)


def _rgba(color):
    return (*color, 255) if color else _TRANSPARENT


def parse_ansi_art(text):
    """Parse truecolor half-block ANSI art into a pixel grid.

    Each source character cell maps to 2 vertical output pixels via SGR
    fg/bg state, mirroring how a terminal renders half-block art:

      - U+2580 UPPER HALF BLOCK ('▀'): fg colors the top pixel, bg the
        bottom pixel.
      - U+2584 LOWER HALF BLOCK ('▄'): bg colors the top pixel, fg the
        bottom pixel.
      - anything else (space, unrecognized glyphs): bg colors both
        pixels flat.

    fg/bg persist across cells until changed or reset (\\x1b[0m), same as
    a real terminal. A color that was never set renders as an (0,0,0,0)
    transparent pixel rather than black, so callers can composite the art
    over their own background.

    Returns a list of pixel rows (2 per input text line), each a list of
    (r, g, b, a) tuples. Rows are NOT padded to a common width here --
    use build_grid_from_ansi_text() for a padded rectangular grid.
    """
    pixel_rows = []
    for line in text.splitlines():
        fg = bg = None
        top_row = []
        bottom_row = []
        for tok in _ESC_RE.split(line):
            if not tok:
                continue
            if tok.startswith("\x1b["):
                params = tok[2:-1].split(";")
                if params in (["0"], [""]):
                    fg = bg = None
                elif len(params) >= 5 and params[0] == "38" and params[1] == "2":
                    fg = (int(params[2]), int(params[3]), int(params[4]))
                elif len(params) >= 5 and params[0] == "48" and params[1] == "2":
                    bg = (int(params[2]), int(params[3]), int(params[4]))
                continue
            for ch in tok:
                if ch == _UPPER_HALF_BLOCK:
                    top, bottom = fg, bg
                elif ch == _LOWER_HALF_BLOCK:
                    top, bottom = bg, fg
                else:
                    top, bottom = bg, bg
                top_row.append(_rgba(top))
                bottom_row.append(_rgba(bottom))
        pixel_rows.append(top_row)
        pixel_rows.append(bottom_row)
    return pixel_rows


def build_grid_from_ansi_text(text):
    """parse_ansi_art() padded to a rectangle. Returns (grid, width, height)."""
    grid = parse_ansi_art(text)
    width = max((len(row) for row in grid), default=0)
    grid = [row + [_TRANSPARENT] * (width - len(row)) for row in grid]
    return grid, width, len(grid)


def _bird_grid():
    text = ANSI_PATH.read_text(encoding="utf-8")
    return build_grid_from_ansi_text(text)


def _banner_module():
    """Import tools/banner.py for its ANIM_ART_RAW wordmark + gradient --
    the single source of truth so this renderer never drifts from the
    terminal --anim splash's own art."""
    tools_dir = str(Path(__file__).resolve().parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import banner  # local import: keeps this module importable standalone

    return banner


# Small pixel offsets each glyph is redrawn at -- a "poor-man's" stroke
# widening. A single draw.text() of this figlet font's thin strokes
# ('/', '\', '_', '|') survives at native resolution but a Lanczos
# downscale to the README's real display width (360px, vs. this image's
# much larger native width) thins them below one pixel and they vanish
# (fg-a10919 attempt-1 bounce). Redrawing at a ring of +-1px offsets fuses
# adjacent strokes into terminal-like solid letterforms that survive.
_BOLD_OFFSETS = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                 (1, 1), (-1, -1), (1, -1), (-1, 1)]


def _wordmark_image(font_size=34, pack=0.74, dilate=3):
    """Render banner.py's ANIM_ART_RAW wordmark as actual glyphs (not
    per-character solid pixel blocks): the figlet slant font's letterforms
    are carried by the shape of '_', '/', '\\\\', '|' etc, which a filled
    nearest-neighbor cell-per-character grid destroys (spaces ARE the
    letterforms at this resolution -- filling every non-space cell turns
    "ORNS FORGE" into noise, confirmed visually in attempt 1).

    Drawing the real glyphs keeps it legible at native resolution, but a
    plain single-weight draw was still too thin once the README's browser
    scales the image down to its real display width (360px) -- the
    verifier caught this in attempt 1. To survive that downscale this
    uses a bold monospace face, packs cells tighter than the font's
    natural advance (adjacent glyph strokes touch, like a real terminal's
    fixed-width cells), redraws each glyph at a ring of +-1px offsets
    (_BOLD_OFFSETS) to thicken strokes, and finishes with a MaxFilter
    dilation pass on the alpha channel so any remaining hairlines fuse
    into solid, terminal-like letterforms.

    Still the same source characters, the same left-to-right ANIM_STOPS
    gradient (via banner._anim_grad, one draw per glyph so each column
    gets its own gradient color -- mirrors how the terminal splash colors
    it per-cell), and the same dark-ember shadow extrusion for depth."""
    from PIL import Image, ImageDraw, ImageFilter

    banner = _banner_module()
    art = banner.ANIM_ART
    width_chars = max((len(row) for row in art), default=0)
    height_chars = len(art)

    font = _load_font(font_size, bold=True)
    char_w = (font.getlength("W") or font_size * 0.6) * pack
    line_h = font_size * 1.05
    pad = 8
    canvas_w = int(char_w * width_chars) + pad * 2
    canvas_h = int(line_h * height_chars) + pad * 2

    img = Image.new("RGBA", (canvas_w, canvas_h), _TRANSPARENT)
    draw = ImageDraw.Draw(img)
    shadow = (*banner.ANIM_SHADOW_RGB, 255)
    shadow_dx = shadow_dy = 3

    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch == " ":
                continue
            px, py = pad + x * char_w, pad + y * line_h
            for ox, oy in _BOLD_OFFSETS:
                draw.text((px + shadow_dx + ox, py + shadow_dy + oy), ch,
                          font=font, fill=shadow)
    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch == " ":
                continue
            r, g, b = banner._anim_grad(x / max(1, width_chars - 1))
            px, py = pad + x * char_w, pad + y * line_h
            for ox, oy in _BOLD_OFFSETS:
                draw.text((px + ox, py + oy), ch, font=font,
                          fill=(r, g, b, 255))

    if dilate:
        # Dilate on alpha only (not per-channel RGB, which would bleed
        # colors from neighboring gradient columns into each other) --
        # rebuild solid-colored pixels wherever the dilated mask now
        # covers, keeping each pixel's own column gradient color where
        # already opaque and falling back to the nearest drawn color
        # (via a max-filtered copy of each channel) for newly-covered rims.
        r, g, b, a = img.split()
        a2 = a.filter(ImageFilter.MaxFilter(dilate))
        r2 = r.filter(ImageFilter.MaxFilter(dilate))
        g2 = g.filter(ImageFilter.MaxFilter(dilate))
        b2 = b.filter(ImageFilter.MaxFilter(dilate))
        img = Image.merge("RGBA", (r2, g2, b2, a2))
    return img


def _grid_to_image(grid, width, height, scale):
    from PIL import Image

    img = Image.new("RGBA", (width, height), _TRANSPARENT)
    img.putdata([px for row in grid for px in row])
    if scale != 1:
        img = img.resize((width * scale, height * scale), Image.NEAREST)
    return img


def _load_font(size, bold=False):
    """Best-effort monospace TTF for the terminal-window feel; falls back
    to Pillow's built-in bitmap font (no crash) if none is found -- this
    runs on whatever dev machine has Pillow, font availability varies.
    bold=True prefers heavier faces (used for the wordmark, which needs
    thick strokes to survive downscaling -- see _wordmark_image)."""
    from PIL import ImageFont

    names = (
        ("consolab.ttf", "Consolas-Bold.ttf", "courbd.ttf", "DejaVuSansMono-Bold.ttf")
        if bold
        else ("consola.ttf", "Consolas.ttf", "cour.ttf", "DejaVuSansMono.ttf")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def compose(bird_scale=8, wordmark_font_size=34):
    """Composite the dark terminal-window frame: chrome bar -> bird ->
    wordmark -> taglines. The bird (real pixel art, from truecolor
    half-block ANSI) scales with integer nearest-neighbor -- no smoothing.
    The wordmark is rendered as actual glyphs (see _wordmark_image)."""
    from PIL import Image, ImageDraw

    bird_grid, bird_w, bird_h = _bird_grid()
    bird_img = _grid_to_image(bird_grid, bird_w, bird_h, bird_scale)

    wordmark_img = _wordmark_image(wordmark_font_size)

    margin = 40
    chrome_h = 34
    gap_bird_wordmark = 28
    gap_wordmark_tag = 22
    gap_tag_lines = 8

    content_w = max(bird_img.width, wordmark_img.width)
    frame_w = content_w + margin * 2

    font1 = _load_font(17)
    font2 = _load_font(14)
    dummy = Image.new("RGB", (1, 1))
    ddraw = ImageDraw.Draw(dummy)
    tag1_box = ddraw.textbbox((0, 0), TAGLINE_1, font=font1)
    tag2_box = ddraw.textbbox((0, 0), TAGLINE_2, font=font2)
    tag1_h = tag1_box[3] - tag1_box[1]
    tag2_h = tag2_box[3] - tag2_box[1]

    frame_h = (
        chrome_h
        + margin
        + bird_img.height
        + gap_bird_wordmark
        + wordmark_img.height
        + gap_wordmark_tag
        + tag1_h
        + gap_tag_lines
        + tag2_h
        + margin
    )

    bg = (13, 15, 20, 255)
    chrome_bg = (32, 34, 40, 255)
    img = Image.new("RGBA", (frame_w, frame_h), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, frame_w, chrome_h], fill=chrome_bg)
    for i, dot_color in enumerate(
        [(255, 95, 86, 255), (255, 189, 46, 255), (39, 201, 63, 255)]
    ):
        cx, cy, r = 18 + i * 22, chrome_h // 2, 6
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dot_color)

    y = chrome_h + margin
    img.alpha_composite(bird_img, ((frame_w - bird_img.width) // 2, y))
    y += bird_img.height + gap_bird_wordmark
    img.alpha_composite(wordmark_img, ((frame_w - wordmark_img.width) // 2, y))
    y += wordmark_img.height + gap_wordmark_tag

    orange = (250, 150, 40, 255)
    dim = (145, 148, 160, 255)
    tag1_w = tag1_box[2] - tag1_box[0]
    draw.text(
        ((frame_w - tag1_w) // 2 - tag1_box[0], y - tag1_box[1]),
        TAGLINE_1,
        font=font1,
        fill=orange,
    )
    y += tag1_h + gap_tag_lines
    tag2_w = tag2_box[2] - tag2_box[0]
    draw.text(
        ((frame_w - tag2_w) // 2 - tag2_box[0], y - tag2_box[1]),
        TAGLINE_2,
        font=font2,
        fill=dim,
    )

    return img.convert("RGB")


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        print(
            "tools/banner_png.py requires Pillow, which is not installed "
            "in this environment.\nInstall it with: pip install pillow",
            file=sys.stderr,
        )
        return 2

    img = compose()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PATH)
    print(f"wrote {OUT_PATH} ({img.width}x{img.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
