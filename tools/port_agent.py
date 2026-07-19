"""Agent-format source detector for `/forge:port` (spec-6b7c, item 1).

Detects which of the three v1-supported source shapes an existing custom
agent definition is in -- Claude Code subagent frontmatter, CrewAI/
LangChain-style prompt, or bare system prompt -- or reports "unrecognized
format" rather than guessing a mapping (spec-6b7c Non-goals: no universal
"any framework" parser).

Detector stage only: this module does not map fields to the `.forge/agents/`
format or write anything to disk. That is items 2-3's job
(`fg-b0202`/`fg-b0203`); this module establishes the parsing contract they
consume. Zero dependencies (stdlib only, per repo convention).
"""
import json
import pathlib
import re
import sys

FORMAT_CLAUDE_SUBAGENT = "claude-subagent"
FORMAT_CREWAI_LANGCHAIN = "crewai-langchain"
FORMAT_BARE_SYSTEM_PROMPT = "bare-system-prompt"
FORMAT_UNRECOGNIZED = "unrecognized"

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)

# CrewAI: recognized either via its Python SDK (`from crewai import ...` /
# `import crewai`, including aliased imports -- both are `import\s+crewai\b`
# regardless of any `as x` suffix) or its declarative `agents.yaml` shape
# (role/goal/backstory keys, no frontmatter fences). LangChain: recognized
# via its characteristic imports/constructs, including the post-2024
# package split (`langchain_core`, `langchain_openai`, `langchain_community`,
# ...) -- the module-name alternation below is deliberately open-ended
# (`langchain(?:[_.]\w+)*`) rather than a bare `langchain\b`, because '_' is
# a \w character and a trailing `\b` right after "langchain" never finds a
# boundary before "_core"/"_openai"/etc. Either family maps to the single
# "crewai-langchain" source shape the spec names.
_CREWAI_IMPORT_RE = re.compile(r"(?m)^\s*(from|import)\s+crewai\b")
_CREWAI_YAML_KEYS_RE = [
    re.compile(r"(?m)^\s*role:\s"),
    re.compile(r"(?m)^\s*goal:\s"),
    re.compile(r"(?m)^\s*backstory:\s"),
]
_LANGCHAIN_MARKERS_RE = re.compile(
    r"(?m)^\s*(from|import)\s+langchain(?:[_.]\w+)*\b"
    r"|\binitialize_agent\s*\("
    r"|\bAgentExecutor\b"
    r"|\bSystemMessage\s*\(")

# Fenced ``` code blocks are blanked (same technique as validate_spec.py's
# _mask_fences) before the CrewAI/LangChain heuristics run, so a markdown
# DOCUMENT that merely *illustrates* the CrewAI role/goal/backstory shape
# inside a code sample is never mistaken for an actual agent definition in
# that shape -- only content standing at the document's own top level counts.
_FENCE_RE = re.compile(r"^ {0,3}`{3,}")

_ATTACHED_SKILLS_SECTION_RE = re.compile(
    r"(?m)^##\s*Attached skills.*?$\n((?:^[ \t]*-.*\n?)*)")
_SKILL_LIST_ITEM_RE = re.compile(r"^[ \t]*-\s*([A-Za-z0-9][A-Za-z0-9_-]*)")

# Structured config data (YAML/TOML/INI) that isn't a CrewAI/LangChain shape
# must not fall through to "bare system prompt" -- that would hand fg-b0202's
# mapper prompt text that was never a prompt (a guessed mapping AC1 forbids).
_CONFIG_SECTION_HEADER_RE = re.compile(r"^[ \t]*\[[^\]\s][^\]]*\]\s*$")
_CONFIG_KEY_VALUE_RE = re.compile(r"^[ \t]*[A-Za-z_][\w.-]*[ \t]*[:=][ \t]*\S")
_CONFIG_COMMENT_RE = re.compile(r"^[ \t]*[#;]")


def _read_text(path):
    """Return (text, error). error is set (and text is None) for a missing
    file or content that cannot be decoded as UTF-8 text."""
    p = pathlib.Path(path)
    if not p.is_file():
        return None, f"source file not found: {path}"
    try:
        return p.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, f"source file is not UTF-8 text: {path}"


def _parse_frontmatter_fields(block_text):
    """Parse simple 'key: value' scalar lines from a frontmatter block body
    (the text between the '---' fences). Only scalars are needed here --
    detection reads `name`/`description`, never nested structures."""
    fields = {}
    for line in block_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if val and val[0] == val[-1] and val[0] in ("'", '"') and len(val) >= 2:
            val = val[1:-1]
        fields[key] = val
    return fields


def _is_claude_subagent(text):
    """Return (fields, body) if `text` has a well-formed Claude Code
    subagent/SKILL.md-shaped frontmatter block (both `name` and
    `description` present and non-empty), else (None, None). A frontmatter
    block that is present but missing a required field is a malformed
    instance of this shape, not a guessable one -- callers must treat that
    as unrecognized rather than falling through to another shape."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None, None, False
    fields = _parse_frontmatter_fields(m.group(1))
    has_fences = True
    if fields.get("name") and fields.get("description"):
        return fields, text[m.end():], has_fences
    return None, None, has_fences


def _strip_fenced_code_blocks(text):
    """Blank the contents of fenced ``` code blocks while preserving line
    count, so a code *sample* illustrating a shape (e.g. a doc's ```yaml
    block showing CrewAI's agents.yaml format) is never mistaken for that
    shape actually being present in the document itself."""
    lines = text.splitlines(keepends=True)
    out = []
    in_fence = False
    for line in lines:
        body = line.rstrip("\r\n")
        ending = line[len(body):]
        if _FENCE_RE.match(body):
            in_fence = not in_fence
            out.append(line)
        elif in_fence:
            out.append(ending)
        else:
            out.append(line)
    return "".join(out)


def _is_crewai_langchain(text):
    unfenced = _strip_fenced_code_blocks(text)
    if _CREWAI_IMPORT_RE.search(unfenced):
        return True
    if _LANGCHAIN_MARKERS_RE.search(unfenced):
        return True
    if all(pat.search(unfenced) for pat in _CREWAI_YAML_KEYS_RE):
        return True
    return False


def _looks_like_config_data(text):
    """Detect INI/TOML/YAML-style structured config -- a run of `key:
    value` / `key = value` lines and/or `[section]` headers with no
    prose -- so it routes to "unrecognized" instead of "bare system
    prompt". Requires every non-blank, non-comment line to be config-shaped
    (a lone stray line elsewhere doesn't count), or the presence of an
    INI/TOML `[section]` header, which is unambiguous on its own."""
    content_lines = [
        line for line in text.splitlines()
        if line.strip() and not _CONFIG_COMMENT_RE.match(line)
    ]
    if not content_lines:
        return False
    has_section = any(_CONFIG_SECTION_HEADER_RE.match(l) for l in content_lines)
    if has_section:
        return True
    if len(content_lines) < 2:
        return False
    return all(
        _CONFIG_SECTION_HEADER_RE.match(l) or _CONFIG_KEY_VALUE_RE.match(l)
        for l in content_lines
    )


def _looks_like_unsupported_structured_data(text):
    """Best-effort check for content that is clearly *some* structured
    format Forge doesn't map (JSON, or an INI/TOML/YAML config) rather
    than natural-language prompt text. Used only to route to
    "unrecognized" instead of misclassifying a non-prompt file as a bare
    system prompt."""
    stripped = text.strip()
    if not stripped:
        return True
    if stripped[0] in "{[":
        try:
            json.loads(stripped)
            return True
        except (json.JSONDecodeError, ValueError):
            pass
    return _looks_like_config_data(text)


def _extract_attached_skill_names(body):
    m = _ATTACHED_SKILLS_SECTION_RE.search(body)
    if not m:
        return []
    names = []
    for line in m.group(1).splitlines():
        item = _SKILL_LIST_ITEM_RE.match(line)
        if item:
            names.append(item.group(1))
    return names


def _resolve_skill(name, skills_root):
    """Check whether skill `name` is directly loadable unmodified from
    `skills_root/<name>/SKILL.md`, per fg-a10702's confirmed jcode/oh-my-pi
    SKILL.md-portability finding (both harnesses load Claude Code SKILL.md
    files by reading the exact `name`/`description` frontmatter contract
    unmodified -- so "loadable" here means the same check they perform).

    Returns a dict: {name, resolved_path, loadable, reason}.
    `resolved_path` is set whenever a SKILL.md file was found on disk, even
    if it turns out not to be loadable (e.g. missing `description`) --
    "found but malformed" is a different, more actionable reason than "not
    found at all".
    """
    if skills_root is None:
        return {
            "name": name,
            "resolved_path": None,
            "loadable": False,
            "reason": "no skills_root supplied -- reference left unresolved",
        }
    candidate = pathlib.Path(skills_root) / name / "SKILL.md"
    if not candidate.is_file():
        return {
            "name": name,
            "resolved_path": None,
            "loadable": False,
            "reason": f"referenced skill file not found: {candidate}",
        }
    text, err = _read_text(candidate)
    if err:
        return {
            "name": name,
            "resolved_path": str(candidate),
            "loadable": False,
            "reason": err,
        }
    fields, _, has_fences = _is_claude_subagent(text)
    if fields is not None:
        return {
            "name": name,
            "resolved_path": str(candidate),
            "loadable": True,
            "reason": "SKILL.md frontmatter (name + description) present -- "
                      "directly loadable unmodified",
        }
    reason = ("SKILL.md frontmatter is missing required `name` and/or "
              "`description` field(s)" if has_fences else
              "SKILL.md has no frontmatter block")
    return {
        "name": name,
        "resolved_path": str(candidate),
        "loadable": False,
        "reason": reason,
    }


def detect_source_format(path, skills_root=None):
    """Detect the source shape of an existing custom agent definition file.

    Returns a dict:
      {
        "path": str(path),
        "format": one of FORMAT_CLAUDE_SUBAGENT / FORMAT_CREWAI_LANGCHAIN /
                  FORMAT_BARE_SYSTEM_PROMPT / FORMAT_UNRECOGNIZED,
        "reason": human-readable explanation of the classification,
        "skill_references": [] unless format is FORMAT_CLAUDE_SUBAGENT and
                  the body has an "## Attached skills" section -- then one
                  entry per referenced skill name, each the dict returned
                  by `_resolve_skill` (name/resolved_path/loadable/reason).
      }

    `skills_root` is the directory containing `<skill-name>/SKILL.md`
    subdirectories (e.g. a repo's `skills/`); pass it to enable the
    loadable-unmodified check from AC2. Without it, skill references are
    still listed but left unresolved (loadable=False, resolved_path=None)
    since there is nowhere to look them up.
    """
    text, err = _read_text(path)
    if err is not None:
        return {
            "path": str(path),
            "format": FORMAT_UNRECOGNIZED,
            "reason": err,
            "skill_references": [],
        }

    fields, body, has_fences = _is_claude_subagent(text)
    if fields is not None:
        skill_refs = [
            _resolve_skill(name, skills_root)
            for name in _extract_attached_skill_names(body)
        ]
        return {
            "path": str(path),
            "format": FORMAT_CLAUDE_SUBAGENT,
            "reason": "frontmatter block with required `name` and "
                      "`description` fields (Claude Code subagent contract)",
            "skill_references": skill_refs,
        }
    if has_fences:
        return {
            "path": str(path),
            "format": FORMAT_UNRECOGNIZED,
            "reason": "has '---' frontmatter fences but is missing the "
                      "required `name` and/or `description` field(s) -- "
                      "not guessed as a Claude Code subagent",
            "skill_references": [],
        }

    if _is_crewai_langchain(text):
        return {
            "path": str(path),
            "format": FORMAT_CREWAI_LANGCHAIN,
            "reason": "matches CrewAI (crewai import / role+goal+backstory "
                      "keys) or LangChain (import / initialize_agent / "
                      "AgentExecutor / SystemMessage) markers",
            "skill_references": [],
        }

    if _looks_like_unsupported_structured_data(text):
        return {
            "path": str(path),
            "format": FORMAT_UNRECOGNIZED,
            "reason": "empty, or structured data (e.g. JSON) that isn't "
                      "any of the three supported source shapes",
            "skill_references": [],
        }

    return {
        "path": str(path),
        "format": FORMAT_BARE_SYSTEM_PROMPT,
        "reason": "plain text with no frontmatter and no CrewAI/LangChain "
                  "markers -- treated as a bare system prompt",
        "skill_references": [],
    }


def main(argv):
    skills_root = None
    paths = []
    it = iter(argv)
    for arg in it:
        if arg == "--skills-root":
            skills_root = next(it, None)
        else:
            paths.append(arg)
    if not paths:
        print("usage: port_agent.py [--skills-root DIR] PATH [PATH ...]")
        return 2
    for p in paths:
        result = detect_source_format(p, skills_root=skills_root)
        print(f"{result['path']}: {result['format']} -- {result['reason']}")
        for ref in result["skill_references"]:
            status = "loadable" if ref["loadable"] else "NOT loadable"
            print(f"  skill '{ref['name']}': {status} ({ref['reason']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
