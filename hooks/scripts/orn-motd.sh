#!/usr/bin/env bash
# Forge welcome-area hook (fg-a10904 SCOPE RESOLUTION, 2026-07-18): shows
# örn in the WELCOME AREA -- the startup scrollback above the input line --
# without burning a single token of model context.
#
# WHY this works where the deleted hooks/scripts/banner.sh's plain-stdout
# approach didn't: a SessionStart hook has TWO output channels, and they do
# very different things.
#   - Plain stdout is the model-CONTEXT channel: invisible to the user,
#     pure token burn every session. That was the original sin this task
#     (fg-a10904) exists to fix.
#   - The JSON field {"systemMessage": "..."} is the user-DISPLAY channel:
#     current Claude Code RENDERS it visibly in the startup area (the same
#     UI slot used for e.g. the MCP-auth notice), at ~zero context cost
#     since it never enters the transcript the model reads. Live-verified
#     via computer-use screenshot on the user's machine, 2026-07-18.
#
# tools/banner.py --hook already builds exactly this payload (small, plain
# ASCII art + tagline + version, wrapped as {"systemMessage": ...}) and
# already respects the `startup-banner: off` Feature toggle in
# .forge/forge.md (same toggle hooks/scripts/banner.sh honored -- see
# commands/banner.md and git history for hooks/scripts/banner.sh). This
# script is a thin resolve-and-invoke wrapper, matching how every other
# forge hook is registered: bash + ${CLAUDE_PLUGIN_ROOT} in hooks.json.
#
# FAIL SILENT, NON-LOAD-BEARING: any problem (python missing, banner.py
# missing, banner.py raising) -> exit 0 with NO stdout at all. banner.py's
# own hook_mode() is already wrapped in try/except for this; the python
# resolution below is the only other failure point, and it degrades to a
# silent no-op rather than ever erroring loudly at session start.
set +e

banner_py="${CLAUDE_PLUGIN_ROOT}/tools/banner.py"
[ -f "$banner_py" ] || exit 0

py=""
for c in python python3 py; do
  command -v "$c" >/dev/null 2>&1 && { py="$c"; break; }
done
[ -z "$py" ] && exit 0

"$py" "$banner_py" --hook 2>/dev/null
exit 0
