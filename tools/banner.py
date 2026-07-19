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

import json
import os
import re
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


def main():
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
