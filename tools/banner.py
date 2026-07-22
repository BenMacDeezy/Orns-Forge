#!/usr/bin/env python3
"""Forge startup banner: örn, the phoenix on the anvil, in your terminal.

Stdlib-only, like every Forge tool. Modes:

  python tools/banner.py            # auto: truecolor half-block art on a
                                    # capable TTY, plain ASCII otherwise
  python tools/banner.py --plain    # force plain ASCII (no escape codes)
  python tools/banner.py --small    # compact art (38 cols)
  python tools/banner.py --anim     # animated gleam splash: thin-line
                                    # ÖRN'S FORGE wordmark, 30-frame white-
                                    # hot gleam sweep, self-timed (~2.6s) --
                                    # the launcher shims call this INSTEAD
                                    # of a static print + separate sleep.
                                    # Degrades to a static print + ~1.5s
                                    # sleep on any failure (no TTY, etc).
  python tools/banner.py --hook     # SessionStart hook mode: emit JSON
                                    # {"systemMessage": ...} — fail-silent,
                                    # plain art only, respects the
                                    # startup-banner Feature toggle

The color art is pre-rendered from assets/logo-dark.png into
assets/banner.ans (ANSI truecolor half-blocks). The plain fallbacks are
embedded below so the banner works even if assets/ is stripped.
FAIL SILENT in hook mode: any problem -> exit 0 with no output.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# 52-col plain render of the örn mark (bird + anvil, wordmark masked out).
ART = r"""
     *.
     %%
 .*  %@%                   #:
 .@# .@@@.             #. %@.
  @@%.:@@@*           :@:.@@.
* .@@@**%@@%:       . %@#.@@#
%@:.#@@@#%@@@%:    .@ *@@:%@@
 @@%:*%@@@@@@@%**  .@%.%@@#@@#
  #@@@##%@@@@##:@%: #@@#@@@@@@*
*#.:#@@@@@@@@.#.*@@%*:#@@@@@@@@:
 #@@#*#%@@@@@*#@**%@@@#:#@@@@@@@*
  .#@@@@%@@@#:.*@@@@@@@@::@@@@@@@:  :::::**:.
  :*:*#%@@@@@:####@@@@@@@.%@@@@@@#  :@@@@@@%@%#.
   #@@%%%%@@@%:#%@@@@@@@@*:@@@@@@.  %@@@@@@@%#%%.
     :*%@@@@@%::*%%@@@@@@@.#@@@@%  #@@@@@@@.
     :####%%@@@##%%@@@@@@@@:*%@@@.:@@@@@@@@
      :#%@@@@@@@: :#%@@@@@@@%##%@@@@@@@@@@@%
         .:*#%@@@%###*#@@@@@@@@@@@@@@@@@@@@@#
         .*##%%%%@@%::*#*%@@@@@@@@@@@@@@@@@@#
             :#%%%%@@@@*:*:#@@@@@@@@@@@@@@@@#
               .:#%@%@@@@@%@@@@@@@@@@@@@@@@%
                 ..:###%@%@@@@@@@@@@@@@@@@@.
                       . .@@@@@@@@@@@@@@#.
                        :@@@@@@@@@@@@@#.
                     :#@@@@@@@@@@%@@%.
                  .#@@@@@@@@%%@@..#@*
                :%@%%@#####*   #%: :@%:::
         .. ...:##::** *######@@@@@@@@@@@@##########
         :@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%#
           *%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#*:.
             :*##%%@@@@@@@@@@@@@@@@@@@@@#.
            :@@*:#*::***#%@@@@@@@@@@@@%.
           *@@*.@@@.@@.   :@@@@@@@@@@@.
         :%@# .@@@.%@:     @@@@@@@@@@@:
        .:.  *@@#.*#     :%@@@@@@@@@@@@*
           :%%*.      *%@@@@@@@@@@@@@@@@@%#
           .          %@@@@@%*:...:*%@@@@@@.
""".strip("\n")

# 38-col compact render, used by --small and hook mode.
ART_SMALL = r"""
   .*
 . .@:              :
 %# %@*          * %#
 .@%:%@%.       #@.@#
%::@@#%@@#.   *.#@*@@
:@%*#@@@@@%*: *@*@@%@%
::#@@%@@@#**@#:#%@@@@@*
:%##%@@@@#*##@@%##@@@@@*
 .#%%@@@@*:#%%@@@%:@@@@@* .***#*:
 .*#%%%@@%*#%@@@@@*#@@@@: :@@@@@@%#
   :#%%@@@**%@@@@@@:@@@@  @@@@@#  .
    *#%%@@@#*#%@@@@%*#@@*%@@@@@*
     .*#%%@@**##%@@@@@%@@@@@@@@@*
       .*#%%@@#***#@@@@@@@@@@@@@#
         .:##%@@@##*%@@@@@@@@@@@:
            .:*%%@@@@@@@@@@@@@@#
                  :@@@@@@@@@@#.
                .*@@@@@@@@@*.
             .#@@@@@@%@#.%#
            ###%*###. *@*:%%**.
       #%##%%####@@@@@@@@@@@@@@@@@@@@%
       .#%@@@@@@@@@@@@@@@@@@@@@%*:..
         :#*###%@@@@@@@@@@@@@:
        :@%:@%:%. .#@@@@@@@@
      .*#::@@*@*   :@@@@@@@@.
        .*%* :. .:#@@@@@@@@@@*:
        :.      %@@@@#***#%@@@@*
""".strip("\n")

WORDMARK = r"""
 _____ ___  ____   ____ _____
|  ___/ _ \|  _ \ / ___| ____|
| |_ | | | | |_) | |  _|  _|
|  _|| |_| |  _ <| |_| | |___
|_|   \___/|_| \_\\____|_____|
""".strip("\n")

TAGLINE = "örn is at the anvil — the forge is lit."
TAGLINE_ASCII = "orn is at the anvil - the forge is lit."

# fire gradient, top row -> bottom row (yellow -> orange -> deep red)
FIRE = [(255, 200, 40), (255, 160, 20), (250, 120, 20),
        (240, 90, 25), (220, 60, 30), (200, 40, 35)]

# ---------------------------------------------------------------------------
# --anim: the animated gleam splash (fg-a10905), ported from the live-tested
# reference the user-level orn-splash.py. Distinct from ART/WORDMARK/
# FIRE above (the static "auto" banner's örn-bird art + block FORGE
# wordmark) -- this is the kerned slant "ÖRN'S FORGE" thin-line figlet
# wordmark used by the launcher shims, self-timed so the animation itself
# IS the ~2.6s hold (shims no longer sleep separately).
# ---------------------------------------------------------------------------

# Figlet "slant" wordmark (thin lines, FORWARD lean), umlaut dots over the
# O. Matches assets/orn-motd-art.ans letter-for-letter (the user-chosen
# look, 2026-07-18); the 3-D depth comes from a dark ember extrusion layer
# offset (+1,+1) behind the gradient face.
ANIM_ART_RAW = r"""
    ° °
   ____    ____    _   __  _____        ______  ____    ____    ______  ______
  / __ \  / __ \  / | / / / ___/       / ____/ / __ \  / __ \  / ____/ / ____/
 / / / / / /_/ / /  |/ /  \__ \       / /_    / / / / / /_/ / / / __  / __/
/ /_/ / / _, _/ / /|  /  ___/ /      / __/   / /_/ / / _, _/ / /_/ / / /___
\____/ /_/ |_| /_/ |_/  /____/      /_/      \____/ /_/ |_|  \____/ /_____/
"""
ANIM_ART = [row.rstrip() for row in ANIM_ART_RAW.strip("\n").splitlines()]
ANIM_SHADOW_RGB = (110, 30, 8)  # dark ember extrusion layer

# fire gradient stops, left -> right (distinct from FIRE, which is applied
# top-to-bottom to the static örn-bird art rather than left-to-right).
ANIM_STOPS = [(255, 45, 20), (255, 100, 15), (255, 150, 25),
              (255, 200, 60), (255, 230, 120)]


def _anim_lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _anim_grad(t):
    t = max(0.0, min(1.0, t))
    seg = t * (len(ANIM_STOPS) - 1)
    i = min(int(seg), len(ANIM_STOPS) - 2)
    return _anim_lerp(ANIM_STOPS[i], ANIM_STOPS[i + 1], seg - i)


def _anim_build_rows():
    """Composite cell grid: front face + dark extrusion offset (+1,+1).

    Each cell is None (empty), ("F", ch) for the gradient face, or
    ("S", ch) for the shadow layer (same glyph, dark ember, drawn only
    where the face is empty -- reads as 3-D depth without noise).
    """
    w = max(len(r) for r in ANIM_ART)
    cells = [[None] * (w + 2) for _ in range(len(ANIM_ART) + 1)]
    for y, row in enumerate(ANIM_ART):
        for x, ch in enumerate(row):
            if ch != " ":
                cells[y][x] = ("F", ch)
    for y, row in enumerate(ANIM_ART):
        for x, ch in enumerate(row):
            if ch != " " and cells[y + 1][x + 1] is None:
                cells[y + 1][x + 1] = ("S", ch)
    return cells


def _anim_render(rows, width, gleam_x=None, gleam_w=7):
    sr, sg, sb = ANIM_SHADOW_RGB
    out = []
    for row in rows:
        line = ""
        for x, cell in enumerate(row):
            if cell is None:
                line += " "
                continue
            layer, ch = cell
            if layer == "S":
                line += f"\x1b[38;2;{sr};{sg};{sb}m{ch}"
                continue
            r, g, b = _anim_grad(x / max(1, width - 1))
            if gleam_x is not None and abs(x - gleam_x) < gleam_w:
                # gleam: blend toward white-hot by distance from band center
                f = 1.0 - abs(x - gleam_x) / gleam_w
                r, g, b = _anim_lerp((r, g, b), (255, 255, 235), f * 0.95)
            line += f"\x1b[38;2;{r};{g};{b}m{ch}"
        out.append(line.rstrip() + "\x1b[0m")
    return out


def _anim_version(home=None):
    """Version for the --anim tail: read the INSTALLED plugin cache
    (~/.claude/plugins/installed_plugins.json, utf-8-sig -- the file can
    carry a BOM), not the bundled .claude-plugin/plugin.json _version()
    below reads. Mirrors the home= injection pattern banner_install.py's
    _installed_plugin_root() uses, so tests never touch the real home dir."""
    try:
        home = home or os.path.expanduser("~")
        p = os.path.join(home, ".claude", "plugins", "installed_plugins.json")
        with open(p, encoding="utf-8-sig") as f:
            return "v" + json.load(f)["plugins"]["forge@forge-local"][0]["version"]
    except Exception:
        return ""


def _anim_static_fallback(ver):
    """Fail-safe degrade path: plain print of the wordmark + a short sleep,
    never the caller's problem -- swallows everything."""
    try:
        for line in ANIM_ART:
            print(line)
        print("orn's forge " + ver)
        time.sleep(1.5)
    except Exception:
        pass


def run_anim():
    """Self-timed animated splash (~2.6s): the animation IS the launch
    hold, so callers (the launcher shims) need no separate sleep. Any
    failure -- no TTY, VT enable failure, any exception -- degrades to a
    static print + ~1.5s sleep and never raises, never blocks the CLI
    launch beyond that."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    rows = _anim_build_rows()
    width = max(len(r) for r in rows)
    ver = _anim_version()
    tail = f"\x1b[2m  örn's forge {('— ' + ver) if ver else ''}\x1b[0m"
    try:
        if not sys.stdout.isatty():
            raise RuntimeError("--anim requires a real terminal")
        _enable_windows_vt()
        w = sys.stdout.write
        w("\n")
        for line in _anim_render(rows, width):
            w(line + "\n")
        w(tail + "\n")
        sys.stdout.flush()
        n = len(rows) + 1  # art rows + tail line
        frames = 30
        for i in range(frames):
            gx = -8 + (width + 16) * (i / (frames - 1))
            w(f"\x1b[{n}A")  # cursor up
            for line in _anim_render(rows, width, gleam_x=gx):
                w("\x1b[2K" + line + "\n")
            w("\x1b[2K" + tail + "\n")
            sys.stdout.flush()
            time.sleep(0.075)
        # settle on the clean gradient
        w(f"\x1b[{n}A")
        for line in _anim_render(rows, width):
            w("\x1b[2K" + line + "\n")
        w("\x1b[2K" + tail + "\n\n")
        sys.stdout.flush()
        time.sleep(0.35)
    except Exception:
        _anim_static_fallback(ver)


def _version():
    try:
        manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        return json.loads(manifest.read_text(encoding="utf-8")).get("version", "?")
    except Exception:
        return "?"


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*(?:\n|\Z)", re.DOTALL)


def _queue_stats(cwd=None, ascii_safe=False):
    """Count queue tasks by state in the *current project's* .forge, if any."""
    try:
        tasks = Path(cwd or os.getcwd()) / ".forge" / "queue" / "tasks"
        if not tasks.is_dir():
            return None
        counts = {}
        for f in tasks.glob("*.md"):
            text = f.read_text(encoding="utf-8-sig")
            fm_match = _FRONTMATTER_RE.match(text)
            # Scope the state lookup to the YAML frontmatter block only (the
            # text between the leading "---" delimiters) -- a body sentence
            # like "the state: active variant" in an Execution-plan
            # paragraph must never be mistaken for the task's real state.
            frontmatter = fm_match.group(1) if fm_match else ""
            m = re.search(r"^state:\s*(\S+)", frontmatter, re.MULTILINE)
            if m:
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
        if not counts:
            return None
        order = ["ready", "active", "blocked", "backlog", "done", "dropped"]
        sep = " - " if ascii_safe else " · "
        return sep.join(f"{counts[s]} {s}" for s in order if s in counts)
    except Exception:
        return None


def _status_lines(ascii_safe=False):
    tagline = TAGLINE_ASCII if ascii_safe else TAGLINE
    lines = [tagline, f"forge v{_version()}"]
    stats = _queue_stats(ascii_safe=ascii_safe)
    if stats:
        lines.append(f"queue: {stats}")
    return lines


def _supports_color():
    # NO_COLOR convention: mere PRESENCE of the variable disables color,
    # regardless of its value -- NO_COLOR="" (set-but-empty, as PowerShell's
    # `$env:NO_COLOR = ""` or bash's `NO_COLOR= cmd` produce) still counts.
    if "--plain" in sys.argv or "NO_COLOR" in os.environ:
        return False
    if "--color" in sys.argv:
        if os.name == "nt":
            _enable_windows_vt()
        return True
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        _enable_windows_vt()
    return True


def _enable_windows_vt():
    """Enable ANSI escape processing on legacy Windows consoles (no-op on
    Windows Terminal, which is VT-native). ctypes, not a shell."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # VT flag
    except Exception:
        pass


def _fire(text_lines):
    """Apply the fire gradient across a block of text lines."""
    out = []
    n = max(1, len(text_lines) - 1)
    for i, line in enumerate(text_lines):
        r, g, b = FIRE[min(len(FIRE) - 1, i * len(FIRE) // (n + 1))]
        out.append(f"\x1b[38;2;{r};{g};{b}m{line}\x1b[0m")
    return out


def render(color, small=False, ascii_safe=False):
    parts = []
    if color:
        ans = PLUGIN_ROOT / "assets" / "banner.ans"
        if not small and ans.is_file():
            parts.append(ans.read_text(encoding="utf-8"))
        else:
            art = ART_SMALL if small else ART
            parts.extend(_fire(art.split("\n")))
        parts.append("")
        parts.extend(_fire(WORDMARK.split("\n")))
        parts.append("")
        dim, reset = "\x1b[2m", "\x1b[0m"
        orange = "\x1b[38;2;250;120;20m"
        status = _status_lines(ascii_safe=ascii_safe)
        parts.append(f"{orange}{status[0]}{reset}")
        for line in status[1:]:
            parts.append(f"{dim}{line}{reset}")
    else:
        parts.append(ART_SMALL if small else ART)
        parts.append("")
        parts.append(WORDMARK)
        parts.append("")
        parts.extend(_status_lines(ascii_safe=ascii_safe))
    return "\n".join(parts)


BRAILLE_BLANK = "⠀"  # BRAILLE PATTERN BLANK -- visually empty, not whitespace
HOOK_SYSTEM_MESSAGE_BYTE_CAP = 1900  # stay comfortably under the ~2KB point


def _braille_pad(text):
    """Replace ASCII spaces with U+2800 BRAILLE PATTERN BLANK.

    The systemMessage display channel renders plain text but is not a raw
    terminal: it strips ANSI escape codes and trims leading whitespace per
    line, which would collapse this pixel art's left margins and interior
    gaps back together and scramble its alignment. U+2800 looks like blank
    space to the eye but is not whitespace, so it survives the trim.
    """
    return text.replace(" ", BRAILLE_BLANK)


def hook_mode():
    """SessionStart hook: JSON systemMessage, plain compact art, fail-silent.

    The systemMessage display channel this feeds (unlike stdout/model
    context) is NOT a raw terminal: it strips ANSI escape codes, trims
    leading whitespace per line, and truncates long payloads. So this
    always emits plain (no color codes -- ART_SMALL/TAGLINE never carry
    any), braille-padded (alignment-preserving) art, and degrades to
    shorter fallbacks rather than risk emitting something that gets
    truncated mid-art.
    """
    try:
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        if not (project / ".forge").is_dir():
            return
        forge_md = project / ".forge" / "forge.md"
        if forge_md.is_file():
            # Every other forge.md Feature/Budget line is written as a
            # markdown bullet ("- key: value"), not bare "key: value" -- the
            # optional "-?\s*" here is fg-a10904's fix so this toggle
            # actually matches real forge.md files (the original pattern
            # only matched an unbulleted line, which forge.md never uses).
            if re.search(r"^\s*-?\s*startup-banner:\s*off\s*$",
                         forge_md.read_text(encoding="utf-8"),
                         re.MULTILINE | re.IGNORECASE):
                return
        stats = _queue_stats(project)
        suffix = f"  (forge v{_version()}"
        suffix += f" · {stats})" if stats else ")"

        # Preferred payload: the slant figlet ÖRN'S FORGE wordmark
        # (assets/orn-motd-art.ans — the user-chosen look; plain glyphs are
        # deliberate since the display channel strips ANSI anyway). Shipped
        # as a static repo asset, sized under the cap at generation time.
        # Padding: ONE leading braille blank per line (defeats the
        # leading-whitespace trim); interior gaps are REAL spaces — braille
        # interiors render wider than ASCII in the welcome font and
        # stretched the letterforms.
        msg = ""
        try:
            asset = Path(__file__).resolve().parent.parent / "assets" / "orn-motd-art.ans"
            wordmark = asset.read_text(encoding="utf-8").rstrip("\n")
            if wordmark and "\x1b" not in wordmark:
                msg = wordmark + suffix
        except OSError:
            pass
        if not msg or len(msg.encode("utf-8")) > HOOK_SYSTEM_MESSAGE_BYTE_CAP:
            msg = _braille_pad(ART_SMALL) + "\n\n" + TAGLINE + suffix
        if len(msg.encode("utf-8")) > HOOK_SYSTEM_MESSAGE_BYTE_CAP:
            # Degrade rather than risk a mid-art truncation that would
            # garble the display: drop the (larger, braille-padded) art
            # first, then the unpadded art, keeping at least the tagline.
            msg = ART_SMALL + "\n\n" + TAGLINE + suffix
        if len(msg.encode("utf-8")) > HOOK_SYSTEM_MESSAGE_BYTE_CAP:
            msg = TAGLINE + suffix
        print(json.dumps({"systemMessage": msg}))
    except Exception:
        pass  # fail silent, per hooks contract


# ---------------------------------------------------------------------------
# bm-banner-takeover: byte-length-safe patch engine for Claude Code's own
# startup block-art. `/forge:banner install` is now a SINGLE mode -- there is
# no separate splash-only path any more (owner delta 2026-07-22): every
# install patches the installed CLI's startup art out (same-byte-length, so
# file size/offsets never move) AND installs the launcher shim that shows the
# Örn's Forge splash instead. This section is pure/testable byte-manipulation
# and best-effort target resolution; the confirm-before-patch UX lives one
# layer up in commands/banner.md, and the actual install/restore
# orchestration (shim writing, stamp lifecycle) lives in banner_install.py,
# which imports the functions below as a library (same process, no
# subprocess round-trip needed at install time).
#
# NEVER exercised against a real Claude Code install in this repo's tests --
# only synthetic in-memory/tempdir fixtures. Every real-filesystem write
# takes an injectable `home=` (mirrors the _installed_plugin_root(home=...)
# pattern in banner_install.py) so tests never touch the user's actual
# ~/.claude.
# ---------------------------------------------------------------------------

# Unicode "Block Elements" chart (▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏▐░▒▓▔▕▖▗▘▙▚▛▜▝▞▟), U+2580-
# U+259F inclusive -- every codepoint in this block encodes to exactly 3
# UTF-8 bytes, and so does U+200B ZERO WIDTH SPACE, which is what makes the
# same-byte-length patch possible: swap the 3 bytes in place, file size and
# every other offset in the bundle stay identical.
_BLOCK_ELEMENT_START = 0x2580
_BLOCK_ELEMENT_END = 0x259F
ZERO_WIDTH_SPACE = "​"


def _block_art_byte_sequences():
    """The set of 3-byte UTF-8 sequences for every Block Elements codepoint.
    Asserts the same-byte-length invariant the whole patch depends on."""
    zwsp = ZERO_WIDTH_SPACE.encode("utf-8")
    assert len(zwsp) == 3, "ZWSP must be 3 UTF-8 bytes for the patch to be safe"
    seqs = set()
    for cp in range(_BLOCK_ELEMENT_START, _BLOCK_ELEMENT_END + 1):
        b = chr(cp).encode("utf-8")
        assert len(b) == 3, f"U+{cp:04X} is not 3 UTF-8 bytes"
        seqs.add(b)
    return seqs, zwsp


_BLOCK_ART_BYTES, _ZWSP_BYTES = _block_art_byte_sequences()

# A compiled alternation, not a manual byte-by-byte Python loop: a native
# install's target file can be several hundred MB (a 248MB claude.exe was
# observed 2026-07-21), and a pure-Python per-offset membership check over
# that many bytes is minutes-slow -- re's C engine handles it in roughly a
# second. Sorted for determinism only; alternation order doesn't affect
# correctness since every alternative is the same fixed length.
_BLOCK_ART_RE = re.compile(b"|".join(re.escape(b) for b in sorted(_BLOCK_ART_BYTES)))


def find_block_art_sequences(content):
    """Return the byte offsets of every Block Elements UTF-8 sequence found
    in `content` (bytes), in ascending order. Pure, read-only, no I/O."""
    return [m.start() for m in _BLOCK_ART_RE.finditer(content)]


def patch_block_art(content):
    """Same-byte-length patch: every Block Elements 3-byte UTF-8 sequence in
    `content` (bytes) is replaced with the 3-byte UTF-8 ZWSP sequence.
    Returns (patched_bytes, count). Pure -- never writes anything; when
    count == 0, patched_bytes is byte-identical to content (the graceful
    degrade case: caller decides whether/what to write, if anything).

    This is the UTF-8-char-literal form only. Real builds have been found
    (2026-07-21 live probe against a native Windows install,
    C:\\Users\\<user>\\.local\\bin\\claude.exe) to overwhelmingly favor a
    SECOND form instead -- see find_literal_escape_sequences/patch_art
    below, which auto-detects and handles both."""
    hits = find_block_art_sequences(content)
    if not hits:
        return content, 0
    out = bytearray(content)
    for offset in hits:
        out[offset:offset + 3] = _ZWSP_BYTES
    return bytes(out), len(hits)


# ---------------------------------------------------------------------------
# The SECOND art-escape form: the literal 6-ASCII-byte source text
# "▀" (backslash, u, 2, 5, 8, 0) rather than the UTF-8-encoded
# character itself. A live probe against a real native Windows install
# (2026-07-21) found 488 occurrences of this literal form versus only 7 of
# the UTF-8-char form in the same ~248MB binary -- this is the form that
# actually matters in production, not the UTF-8-char one above. Same-byte-
# length patch target: "​" is also exactly 6 ASCII bytes.
# ---------------------------------------------------------------------------

_LITERAL_ESCAPE_RE = re.compile(rb'\\u25[89][0-9A-Fa-f]')
# The 6 literal ASCII bytes: backslash, u, 2, 0, 0, B -- i.e. the source
# TEXT for U+200B, not the encoded character itself. Built from
# b"u200B".encode()-equivalent ASCII pieces (rather than an escape literal
# in this source file) so there is no ambiguity about which of the two
# forms is meant.
_LITERAL_ZWSP_BYTES = b"\\" + b"u200B"
assert _LITERAL_ZWSP_BYTES == b"\x5cu200B"
assert len(_LITERAL_ZWSP_BYTES) == 6


def find_literal_escape_sequences(content):
    """Return the byte offsets of every literal "\\u2580".."\\u259F" ASCII
    escape-text occurrence in `content` (bytes). Pure, read-only, no I/O."""
    return [m.start() for m in _LITERAL_ESCAPE_RE.finditer(content)]


def patch_literal_escapes(content):
    """Same-byte-length patch for the literal-escape-text form: every
    6-ASCII-byte "\\u25xx" occurrence becomes "\\u200B". Returns
    (patched_bytes, count); pure, never writes anything."""
    hits = find_literal_escape_sequences(content)
    if not hits:
        return content, 0
    # A literal callable replacement, not a template string -- re.sub would
    # otherwise try to parse the backslash in _LITERAL_ZWSP_BYTES as a
    # backreference escape (\u is not valid backreference syntax) and raise.
    return _LITERAL_ESCAPE_RE.sub(lambda _m: _LITERAL_ZWSP_BYTES, content), len(hits)


def detect_art_form_counts(content):
    """Count both known art-escape forms in `content` without patching
    anything. Returns {"literal": N, "utf8": N}."""
    return {
        "literal": len(find_literal_escape_sequences(content)),
        "utf8": len(find_block_art_sequences(content)),
    }


def patch_art(content):
    """Dual-form, auto-detecting, same-byte-length patch.

    A real installed CLI may encode its startup art as literal ASCII
    escape TEXT ("\\u2580", 6 bytes) or as the UTF-8-encoded character
    itself (3 bytes) -- or, in principle, a mix of both. This counts both
    forms and patches whichever DOMINATES (has the equal-or-greater
    count) -- ties go to the literal form, since that is the form observed
    in the wild (488 literal vs 7 UTF-8-char in the one real build probed
    so far). Only the dominant form is patched; the other is left alone
    (avoids a single scan-and-replace pass corrupting offsets it wasn't
    asked to touch, and keeps the journal's replacement_length uniform).

    Returns (patched_bytes, count, form, hits, replacement_length) where
    form is "literal-escape" | "utf8-char" | None (neither present) --
    hits/replacement_length are exposed so apply_patch can build an
    offsets journal without re-scanning the (potentially huge) content a
    second time."""
    counts = detect_art_form_counts(content)
    if counts["literal"] == 0 and counts["utf8"] == 0:
        return content, 0, None, [], 0
    if counts["literal"] >= counts["utf8"]:
        hits = find_literal_escape_sequences(content)
        patched, count = patch_literal_escapes(content)
        return patched, count, "literal-escape", hits, 6
    hits = find_block_art_sequences(content)
    patched, count = patch_block_art(content)
    return patched, count, "utf8-char", hits, 3


_CLI_JS_REF_RE = re.compile(r'["\']([^"\']*(?:cli\.js|claude-code[^"\']*\.js))["\']')

# npm shims (claude.cmd/.ps1/posix wrapper) are small text files; a native
# bundled install (e.g. ~/.local/bin/claude.exe, ~248MB observed 2026-07-21)
# packs its own runtime and IS the target directly -- no further shim
# indirection to resolve. Anything at/above this size is treated as the
# bundle itself rather than scanned for a *.js reference.
_LARGE_BINARY_THRESHOLD_BYTES = 5 * 1024 * 1024  # 5MB

# F2 (verify-bounce finding, 2026-07-21): the resolver must not accept ANY
# large binary or *.js file named/shaped like a claude entry point --
# without a content check, "any PATH entry named claude, any .js file, or
# any referenced generic cli.js is accepted... [and] patched" (verdict
# quote). Both marker strings below were confirmed present via a READ-ONLY
# scan of the real installed C:\Users\<user>\.local\bin\claude.exe
# (authorized specifically for this check, 2026-07-21): 331 occurrences of
# the npm package name, 956 of the product name. A file lacking BOTH is
# rejected outright -- resolution degrades to target-not-found rather than
# guessing.
_CLAUDE_CODE_IDENTITY_MARKERS = (
    b"@anthropic-ai/claude-code",
    b"Claude Code",
)


def _has_claude_code_marker(content):
    """Pure: does `content` (bytes) contain at least one Claude-Code-
    specific identity marker? No I/O."""
    return any(marker in content for marker in _CLAUDE_CODE_IDENTITY_MARKERS)


def _file_has_claude_code_marker(path):
    try:
        return _has_claude_code_marker(Path(path).read_bytes())
    except Exception:
        return False


def _resolve_shim_to_bundle(shim_path):
    """Given a `claude` PATH entry, find the actual file to patch.

    Three cases, in order:
    1. shim_path is already a .js file -> it IS the bundle (subject to the
       identity-marker check below).
    2. shim_path is a LARGE file (>= _LARGE_BINARY_THRESHOLD_BYTES) -> a
       native bundled install (e.g. a ~248MB claude.exe observed
       2026-07-21) packs its own runtime and IS the target directly; there
       is no further shim indirection to chase, and reading a file that
       size as text to regex a reference out of it would be both wrong and
       wasteful.
    3. Otherwise (a small npm-generated .cmd/.ps1/posix shim or native
       launcher stub), read it as text and regex out a referenced *.js
       path, resolved relative to the shim's own directory if not
       absolute.

    In every case, the FINAL candidate is only accepted if it actually
    contains a Claude Code identity marker (_has_claude_code_marker) --
    matching on name/size/extension alone is not enough to safely patch an
    arbitrary file. Returns None rather than guess -- callers must degrade
    gracefully (target-not-found) on an unresolved or unverified target,
    never patch blind."""
    try:
        shim_path = Path(shim_path)
        if not shim_path.is_file():
            return None
        if shim_path.suffix.lower() == ".js":
            return shim_path if _file_has_claude_code_marker(shim_path) else None
        if shim_path.stat().st_size >= _LARGE_BINARY_THRESHOLD_BYTES:
            return shim_path if _file_has_claude_code_marker(shim_path) else None
        text = shim_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    match = _CLI_JS_REF_RE.search(text)
    if not match:
        return None
    ref_path = Path(match.group(1))
    if not ref_path.is_absolute():
        ref_path = (shim_path.parent / ref_path).resolve()
    if not ref_path.is_file():
        return None
    return ref_path if _file_has_claude_code_marker(ref_path) else None


def _native_install_candidates(home=None):
    """Known native-install roots, checked independently of `where`/`which`
    PATH resolution order -- a native install's directory is not
    guaranteed to be the FIRST `claude` PATH hit even when it exists (an
    npm shim could shadow it), so this is tried as an explicit fallback,
    not folded into the PATH-search loop."""
    home = Path(home) if home else Path.home()
    if os.name == "nt":
        return [home / ".local" / "bin" / "claude.exe"]
    return [home / ".local" / "bin" / "claude"]


def resolve_cli_target_path(home=None):
    """Best-effort resolution of the installed Claude Code CLI file to
    patch -- either an npm-global bundle (.../cli.js, reached via a small
    claude/claude.cmd/claude.ps1 shim) or a native bundled install (a
    single large executable, e.g. ~/.local/bin/claude.exe on Windows).
    Returns None if it cannot confidently resolve a target; callers must
    treat that as a graceful no-op, never a guess."""
    candidates = []
    if os.name == "nt":
        try:
            result = subprocess.run(["where", "claude"], capture_output=True,
                                     text=True, timeout=10)
            if result.returncode == 0:
                candidates = [line.strip() for line in result.stdout.splitlines()
                              if line.strip()]
        except Exception:
            pass
    else:
        found = shutil.which("claude")
        if found:
            candidates = [found]
    for candidate in candidates:
        target = _resolve_shim_to_bundle(candidate)
        if target is not None:
            return target
    for candidate in _native_install_candidates(home=home):
        target = _resolve_shim_to_bundle(candidate)
        if target is not None:
            return target
    return None


def _patch_state_dir(home=None):
    home = Path(home) if home else Path.home()
    return home / ".claude" / "orn-banner-takeover"


def _patch_stamp_path(home=None):
    home = Path(home) if home else Path.home()
    return home / ".claude" / "orn-banner-takeover.stamp"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _read_stamp(stamp_path):
    try:
        return json.loads(Path(stamp_path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_stamp(stamp_path, data):
    # Routed through _fsync_write_bytes (not a direct write_text) so the
    # tools/conftest.py hermeticity guard's wrap of that one primitive
    # covers this write too -- a direct stamp_path.write_text(...) here
    # would be a second, unguarded writer (P0 finding, 3rd-incident
    # verification bounce).
    payload = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    _fsync_write_bytes(stamp_path, payload)


def _unlink_path(path):
    """The one function that unlinks a stamp/journal file -- restore_patch
    (and any future caller) routes every deletion through here rather than
    calling Path.unlink() directly, so the hermeticity guard has a single,
    stable, mockable delete boundary (mirrors _fsync_write_bytes/
    _atomic_write_bytes for writes). missing_ok semantics match the
    Path.unlink() calls this replaces."""
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


def _journal_path_for(state_dir, orig_hash):
    return state_dir / f"{orig_hash[:16]}.journal.json"


def _fsync_write_bytes(path, data):
    """Write `data` (bytes) to `path` and fsync before returning, so the
    write is durable on disk before the caller does anything that depends
    on it (the journal-before-patch ordering restore_patch's safety relies
    on). Creates parent dirs; overwrites atomically-enough for a sidecar
    metadata file (full O_TRUNC write, not a rename-swap -- reserved for
    the target binary itself, see _atomic_write_bytes)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write_bytes(path, data):
    """Write `data` to `path` via a same-directory temp file + os.replace,
    so a process death mid-write never leaves `path` half-written --
    important when `path` may be a large (hundreds-of-MB) binary."""
    path = Path(path)
    tmp = path.with_name(path.name + ".ornbanner.tmp")
    tmp.write_bytes(data)
    os.replace(str(tmp), str(path))


def _write_journal(journal_path, target, content, hits, replacement_length,
                    orig_hash, patched_hash, form):
    """The offsets journal: a small sidecar recording (offset, original
    bytes) for every single replacement the patch is about to make, plus a
    whole-file hash header for integrity verification on restore. Written
    and fsync'd BEFORE the target is ever touched (see apply_patch) -- a
    full second copy of a several-hundred-MB binary is unnecessary when
    every replacement is a fixed-length same-offset swap; only the changed
    bytes need to be recorded to reconstruct the original exactly."""
    replacements = [[offset, content[offset:offset + replacement_length].hex()]
                     for offset in hits]
    payload = json.dumps({
        "target": str(target),
        "orig_sha256": orig_hash,
        "patched_sha256": patched_hash,
        "form": form,
        "replacement_length": replacement_length,
        "replacements": replacements,
        "timestamp": time.time(),
    }, indent=2) + "\n"
    _fsync_write_bytes(journal_path, payload.encode("utf-8"))


def _read_journal(journal_path):
    try:
        return json.loads(Path(journal_path).read_text(encoding="utf-8"))
    except Exception:
        return None


# Real-machine incident 2026-07-21: a hung test accidentally patched the
# actual installed claude.exe before it could be stopped -- a follow-up
# re-scan found the 488 literal-form startup-art escapes were gone
# (correctly patched), but ALSO found 50 occurrences of the UTF-8-char
# form still present post-patch. 50 is not credible as startup art on a
# build where the real art count was 488 -- it is far more likely to be
# legitimate UI glyphs (spinners/progress indicators use block characters
# too) that happen to share the same Unicode block, OR a build that was
# already patched/re-encoded and is only showing incidental leftovers.
# Treating a low count as "startup art" and patching it anyway risks
# mangling real UI. This floor requires the dominant form's count to clear
# a plausibility threshold before apply_patch will act on it
# automatically; a count below the threshold is still reported (never
# hidden) but refused without an explicit force=True.
_LOW_COUNT_THRESHOLD = 100

DISCLOSURE = (
    "This is an UNOFFICIAL, local, cosmetic patch to your installed Claude "
    "Code CLI files -- not supported or endorsed by Anthropic. A Claude Code "
    "update will change the patched bytes back; the launcher shim installed "
    "alongside this automatically re-checks and re-patches on your next "
    "launch. Official theming/branding settings, if Anthropic ships them, "
    "will replace this patch entirely. Run --restore at any time to undo "
    "everything this installs."
)


def _classify_patch_plan(target, content, state_dir, stamp_path, stamp):
    """Pure classification: given a target path and its ALREADY-READ bytes
    (`content`), decide already-patched / pattern-not-found / low-count /
    would-patch and build the report dict, including target_sha256 (F3 --
    the confirm-to-write binding key) and journal_path. No I/O of its own
    -- shared by patch_report and apply_patch so each does EXACTLY ONE
    read on its own and this classification logic is never duplicated
    against a second, possibly-different read (F7)."""
    current_hash = _sha256(content)
    if stamp and stamp.get("target") == str(target) and stamp.get("patched_sha256") == current_hash:
        return {
            "status": "already-patched",
            "target": str(target),
            "target_sha256": current_hash,
            "count": stamp.get("count", 0),
            "form": stamp.get("form"),
            "journal_path": stamp.get("journal_path"),
            "stamp_path": str(stamp_path),
            "message": "Already patched and up to date.",
        }
    _, count, form, _hits, _length = patch_art(content)
    journal_path = _journal_path_for(state_dir, current_hash)
    if count == 0:
        return {
            "status": "pattern-not-found",
            "target": str(target),
            "target_sha256": current_hash,
            "count": 0,
            "form": None,
            "journal_path": str(journal_path),
            "stamp_path": str(stamp_path),
            "message": ("No block-art escape sequences (either known form) "
                        "found in this build -- degrading gracefully: the "
                        "binary would be left untouched, only the splash "
                        "wrapper would install."),
        }
    if count < _LOW_COUNT_THRESHOLD:
        return {
            "status": "low-count",
            "target": str(target),
            "target_sha256": current_hash,
            "count": count,
            "form": form,
            "journal_path": str(journal_path),
            "stamp_path": str(stamp_path),
            "message": (f"low-count: likely not startup art (already "
                         f"patched or changed encoding) -- only {count} "
                         f"'{form}'-form escape sequence(s) found, below "
                         f"the plausibility floor of {_LOW_COUNT_THRESHOLD}. "
                         "Refusing to patch automatically; apply_patch "
                         "requires force=True to act on a count this low."),
        }
    return {
        "status": "would-patch",
        "target": str(target),
        "target_sha256": current_hash,
        "count": count,
        "form": form,
        "journal_path": str(journal_path),
        "stamp_path": str(stamp_path),
        "message": (f"Would patch {count} '{form}'-form escape sequence(s) "
                     f"in {target}, write an offsets journal to "
                     f"{journal_path}, and write a stamp to {stamp_path}."),
    }


def patch_report(target_path=None, home=None):
    """Structured, side-effect-free preview of what a patch WOULD do: the
    exact target file, its whole-file hash (target_sha256 -- what F3's
    confirm-to-write binding checks apply_patch's expect_hash against),
    which art-escape FORM dominates it and how many occurrences, and where
    the offsets journal/stamp would land. Powers the confirm step in
    commands/banner.md -- called before anything is ever written. Does
    exactly ONE read of the target on its own; this is necessarily a
    SEPARATE read from apply_patch's own (preview and apply are different
    calls, often different processes) -- F3's hash binding, not a shared
    read, is what catches a swap between them."""
    stamp_path = _patch_stamp_path(home)
    state_dir = _patch_state_dir(home)
    target = Path(target_path) if target_path else resolve_cli_target_path(home=home)
    if target is None:
        return {
            "status": "target-not-found",
            "target": None,
            "target_sha256": None,
            "count": 0,
            "form": None,
            "journal_path": None,
            "stamp_path": str(stamp_path),
            "message": ("Could not resolve the installed Claude Code CLI "
                        "file -- no binary changes would be made (the "
                        "splash wrapper still installs normally)."),
        }
    try:
        content = target.read_bytes()  # patch_report's own single read
    except Exception as exc:
        return {
            "status": "unreadable",
            "target": str(target),
            "target_sha256": None,
            "count": 0,
            "form": None,
            "journal_path": None,
            "stamp_path": str(stamp_path),
            "message": f"Could not read {target}: {exc}",
        }
    stamp = _read_stamp(stamp_path)
    return _classify_patch_plan(target, content, state_dir, stamp_path, stamp)


def _validate_journal_schema(journal, expected_orig_hash, content_length):
    """Pure validation (F5): is `journal` a well-formed, matching journal
    for a target whose current bytes hash to expected_orig_hash and whose
    length is content_length? Returns None if valid, else a short
    human-readable reason it is NOT valid (stale, tampered, or corrupt) --
    apply_patch refuses to patch when this returns non-None rather than
    silently overwriting or blindly reusing an unreliable journal."""
    if not isinstance(journal, dict):
        return "journal is not a JSON object"
    required = ("target", "orig_sha256", "patched_sha256", "form",
                "replacement_length", "replacements")
    for key in required:
        if key not in journal:
            return f"journal is missing required field {key!r}"
    if journal["orig_sha256"] != expected_orig_hash:
        return ("journal's recorded pre-patch hash does not match the "
                "current target -- stale or tampered")
    length = journal["replacement_length"]
    if not isinstance(length, int) or length <= 0:
        return "journal replacement_length is invalid"
    replacements = journal["replacements"]
    if not isinstance(replacements, list):
        return "journal replacements is not a list"
    for entry in replacements:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            return "journal replacements entry is malformed"
        offset, orig_hex = entry
        if not isinstance(offset, int) or offset < 0 or offset + length > content_length:
            return "journal replacement offset is out of range"
        try:
            entry_bytes = bytes.fromhex(orig_hex)
        except Exception:
            return "journal replacement original-bytes are not valid hex"
        if len(entry_bytes) != length:
            return "journal replacement original-bytes have the wrong length"
    return None


def apply_patch(target_path=None, home=None, cli_version=None, force=False,
                 expect_target=None, expect_hash=None):
    """Perform the patch: dual-form same-byte-length swap + offsets journal
    + hash-keyed stamp (written PENDING before the target write, flipped
    to APPLIED after -- F6 crash-window evidence). Does EXACTLY ONE read
    of the target (F7): every downstream computation -- count, dominant
    form, patched bytes, journal contents, hashes -- derives from that
    single buffer, eliminating the preview-then-reread TOCTOU window a
    prior revision had (patch_report() followed by an independent second
    target.read_bytes() inside apply_patch itself).

    F3 confirm-to-write binding: if expect_target/expect_hash are given
    (the CLI always supplies both for a confirmed `install --yes`, sourced
    from a PRIOR patch_report() preview -- necessarily a separate read),
    they are checked against THIS call's actual resolved target path and
    hash; a mismatch refuses outright ("target-mismatch"/"hash-mismatch")
    rather than patching a file the human never actually approved.

    F5 stale-journal validation: an existing journal at the deterministic
    (orig-hash-keyed) path is parsed and schema/hash-validated before
    being trusted; invalid/stale/tampered journals refuse the patch
    ("journal-invalid") rather than being silently overwritten or blindly
    reused. A VALID journal for this exact original is reused, not
    rewritten.

    Idempotent -- calling this when already patched (per the stamp, keyed
    by hash -- F9) is a no-op. Degrades gracefully (writes nothing) when
    the target can't be resolved/read, or when no art-escape sequences of
    either known form are found. Also REFUSES a "low-count" plan (see
    _LOW_COUNT_THRESHOLD) unless force=True is passed explicitly."""
    stamp_path = _patch_stamp_path(home)
    state_dir = _patch_state_dir(home)
    target = Path(target_path) if target_path else resolve_cli_target_path(home=home)
    if target is None:
        return {
            "status": "target-not-found",
            "target": None,
            "target_sha256": None,
            "count": 0,
            "form": None,
            "journal_path": None,
            "stamp_path": str(stamp_path),
            "message": ("Could not resolve the installed Claude Code CLI "
                        "file -- no binary changes would be made (the "
                        "splash wrapper still installs normally)."),
        }

    if expect_target is not None and str(target) != str(Path(expect_target)):
        return {
            "status": "target-mismatch",
            "target": str(target),
            "target_sha256": None,
            "count": 0,
            "form": None,
            "journal_path": None,
            "stamp_path": str(stamp_path),
            "message": (f"Resolved target {target} does not match the "
                         f"confirmed target {expect_target} -- refusing to "
                         "patch a different file than the one approved. "
                         "Preview again with `install` (no --yes) and "
                         "re-confirm."),
        }

    try:
        content = target.read_bytes()  # apply_patch's ONE AND ONLY read
    except Exception as exc:
        return {
            "status": "unreadable",
            "target": str(target),
            "target_sha256": None,
            "count": 0,
            "form": None,
            "journal_path": None,
            "stamp_path": str(stamp_path),
            "message": f"Could not read {target}: {exc}",
        }

    current_hash = _sha256(content)
    if expect_hash is not None and current_hash != expect_hash:
        return {
            "status": "hash-mismatch",
            "target": str(target),
            "target_sha256": current_hash,
            "count": 0,
            "form": None,
            "journal_path": None,
            "stamp_path": str(stamp_path),
            "message": (f"{target} has changed since it was previewed "
                         f"(expected hash {expect_hash}, found "
                         f"{current_hash}) -- refusing to patch a file "
                         "that changed between confirm and apply. Preview "
                         "again with `install` (no --yes) and re-confirm."),
        }

    stamp = _read_stamp(stamp_path)
    report = _classify_patch_plan(target, content, state_dir, stamp_path, stamp)
    if report["status"] in ("already-patched", "pattern-not-found"):
        return report
    if report["status"] == "low-count" and not force:
        return report

    orig_hash = report["target_sha256"]
    journal_path = Path(report["journal_path"])
    patched, count, form, hits, replacement_length = patch_art(content)
    patched_hash = _sha256(patched)

    # F5: an existing journal at this deterministic (orig-hash-keyed) path
    # must be validated, not blindly trusted or silently overwritten.
    if journal_path.is_file():
        existing_journal = _read_journal(journal_path)
        error = (_validate_journal_schema(existing_journal, orig_hash, len(content))
                 if existing_journal is not None
                 else "journal could not be parsed as JSON")
        if error:
            return {
                "status": "journal-invalid",
                "target": str(target),
                "target_sha256": orig_hash,
                "count": count,
                "form": form,
                "journal_path": str(journal_path),
                "stamp_path": str(stamp_path),
                "message": (f"Existing journal at {journal_path} is "
                             f"invalid ({error}) -- refusing to patch over "
                             "an unreliable recovery record. Investigate "
                             "or remove that journal file by hand, then "
                             "retry."),
            }
        # Valid and matches this exact original -- it IS the journal for
        # this patch already; reuse it, do not overwrite.
    else:
        # Journal FIRST, fsync'd, before the target is ever written: if
        # the process dies between these two steps, the target is still
        # its original, unpatched self (safe) rather than patched with no
        # recovery path.
        _write_journal(journal_path, target=target, content=content,
                        hits=hits, replacement_length=replacement_length,
                        orig_hash=orig_hash, patched_hash=patched_hash,
                        form=form)

    stamp_fields = {
        "target": str(target),
        "version": cli_version,
        "orig_sha256": orig_hash,
        "patched_sha256": patched_hash,
        "journal_path": str(journal_path),
        "form": form,
        "count": count,
    }

    # F6: stamp written PENDING *before* the target write -- a crash
    # between here and the "applied" flip below leaves the (already
    # fsync'd) journal plus this pending stamp as forensic evidence;
    # restore_patch's hash-based classification handles every
    # interleaving correctly regardless of this label, but the label
    # itself is what a crash-window-recovery test can assert on.
    _write_stamp(stamp_path, {**stamp_fields, "status": "pending",
                               "timestamp": time.time()})

    _atomic_write_bytes(target, patched)

    _write_stamp(stamp_path, {**stamp_fields, "status": "applied",
                               "timestamp": time.time()})

    return {
        "status": "patched",
        "target": str(target),
        "target_sha256": patched_hash,
        "count": count,
        "form": form,
        "journal_path": str(journal_path),
        "stamp_path": str(stamp_path),
        "message": f"Patched {count} '{form}'-form escape sequence(s) in {target}.",
    }


def _find_recoverable_journal(home=None):
    """F6 stampless recovery: scan the journal dir for a journal whose
    recorded target resolves to an existing file and whose patched_sha256
    matches that file's CURRENT bytes -- i.e. a journal for a patch that
    is definitely still live on disk, discoverable even with no stamp (a
    stamp that never got its final 'applied' flip, was deleted, or a
    stamp-write permission failure). Returns a dict with the journal's own
    fields plus 'journal_path', or None if nothing recoverable is found."""
    state_dir = _patch_state_dir(home)
    if not state_dir.is_dir():
        return None
    for journal_file in sorted(state_dir.glob("*.journal.json")):
        journal = _read_journal(journal_file)
        if not journal or "target" not in journal:
            continue
        target = Path(journal["target"])
        try:
            current = target.read_bytes()
        except Exception:
            continue
        if _sha256(current) == journal.get("patched_sha256"):
            found = dict(journal)
            found["journal_path"] = str(journal_file)
            return found
    return None


def restore_patch(home=None):
    """Undo apply_patch: replay the offsets journal to reconstruct the
    original bytes exactly, verify the reconstruction against the
    journal's own whole-file hash BEFORE writing anything, then write it
    back over the patched target and remove the journal + stamp.

    F6: discovers the journal even with NO stamp present, or a stamp whose
    referenced journal is missing, by falling back to scanning the journal
    directory (_find_recoverable_journal) for one whose recorded
    patched-hash matches the target's current bytes.

    Always safe to call, including when nothing was ever patched. Refuses
    (rather than corrupts) if the target changed since patching in a way
    the journal doesn't recognize (e.g. a Claude Code update landed
    without a repatch), or if the replay doesn't reproduce the recorded
    original -- leaves the journal/stamp in place and reports the
    situation instead of guessing."""
    stamp_path = _patch_stamp_path(home)
    stamp = _read_stamp(stamp_path)
    journal = None
    journal_path = None
    stamp_referenced_journal_missing = False

    if stamp and stamp.get("journal_path"):
        candidate_path = Path(stamp["journal_path"])
        if candidate_path.is_file():
            journal = _read_journal(candidate_path)
            journal_path = candidate_path
        else:
            stamp_referenced_journal_missing = True

    discovered_without_stamp = False
    if journal is None:
        recovered = _find_recoverable_journal(home=home)
        if recovered is not None:
            journal = recovered
            journal_path = Path(recovered["journal_path"])
            discovered_without_stamp = not stamp

    if journal is None:
        if stamp_referenced_journal_missing:
            return {
                "status": "journal-missing",
                "target": stamp.get("target"),
                "message": (f"Journal {stamp['journal_path']} referenced "
                             "by the stamp is missing, and no other "
                             "recoverable journal was found -- cannot "
                             "safely restore. Stamp left in place."),
            }
        return {"status": "nothing-to-restore", "target": None,
                "message": "No takeover stamp or recoverable journal found -- nothing to restore."}

    target = Path(journal["target"])

    try:
        current = target.read_bytes()
    except Exception as exc:
        return {"status": "unreadable", "target": str(target),
                "message": f"Could not read {target}: {exc}"}

    current_hash = _sha256(current)
    orig_hash = journal.get("orig_sha256")
    patched_hash = journal.get("patched_sha256")

    if current_hash == orig_hash:
        if stamp_path.is_file():
            _unlink_path(stamp_path)
        _unlink_path(journal_path)
        return {"status": "already-clean", "target": str(target),
                "message": "Target already matches the original -- journal/stamp cleared."}
    if current_hash != patched_hash:
        return {
            "status": "target-changed",
            "target": str(target),
            "message": ("The target file changed since it was patched "
                         "(likely a Claude Code update) -- refusing to "
                         "overwrite it blindly. Journal/stamp left in "
                         "place; run install again to re-patch the new "
                         "build."),
        }

    replacement_length = journal.get("replacement_length", 0)
    restored = bytearray(current)
    for offset, orig_hex in journal.get("replacements", []):
        restored[offset:offset + replacement_length] = bytes.fromhex(orig_hex)
    restored = bytes(restored)

    # Verify the replay actually reproduces the recorded original BEFORE
    # writing anything -- the whole point of the journal's hash header.
    if _sha256(restored) != orig_hash:
        return {
            "status": "journal-integrity-error",
            "target": str(target),
            "message": ("Journal replay did not reproduce the recorded "
                         "original bytes (hash mismatch) -- refusing to "
                         "write. Nothing was changed; journal/stamp left "
                         "in place for inspection."),
        }

    _atomic_write_bytes(target, restored)
    if stamp_path.is_file():
        _unlink_path(stamp_path)
    _unlink_path(journal_path)
    note = " (recovered without a stamp file)" if discovered_without_stamp else ""
    return {"status": "restored", "target": str(target),
            "message": (f"Restored {target} byte-identically from the "
                         f"offsets journal (verified via whole-file hash){note}; "
                         "journal/stamp cleared.")}


def recheck_patch(home=None):
    """Fail-silent auto-repatch check: called from every generated launcher
    shim right alongside the --anim splash call. Opt-in gated -- a total
    no-op unless a takeover stamp already exists (i.e. the user has run
    `/forge:banner install` at least once).

    F9: the stamp is keyed by whole-file HASH (orig_sha256/patched_sha256),
    not by CLI version -- version travels along only as informational
    metadata. If the current target's hash matches the stamped
    patched-hash, it's already patched: apply_patch's own already-patched
    check makes this a no-op. If the hash doesn't match, that means the
    build changed (a Claude Code update) -- this re-runs the FULL
    apply_patch pipeline (resolution, single read, low-count floor,
    journal validation) rather than ever blind-patching; if the new
    build's art count is below the plausibility floor, apply_patch's own
    low-count refusal (force is never passed here) takes over and writes
    nothing.

    Never raises and never prints -- must not risk blocking or noising up
    the real `claude` launch it runs in front of."""
    try:
        stamp = _read_stamp(_patch_stamp_path(home))
        if not stamp or not stamp.get("target"):
            return
        apply_patch(target_path=stamp["target"], home=home,
                    cli_version=stamp.get("version"))
    except Exception:
        pass


def main():
    if "--recheck-patch" in sys.argv:
        recheck_patch()
        return
    if "--anim" in sys.argv:
        run_anim()
        return
    if "--hook" in sys.argv:
        hook_mode()
        return
    small = "--small" in sys.argv
    ascii_safe = False
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        # reconfigure failed; check if current encoding can handle TAGLINE.
        try:
            encoding = sys.stdout.encoding or "utf-8"
            TAGLINE.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            # Can't encode TAGLINE in current encoding; fall back to ASCII.
            ascii_safe = True
    print(render(_supports_color(), small=small, ascii_safe=ascii_safe))


if __name__ == "__main__":
    main()
