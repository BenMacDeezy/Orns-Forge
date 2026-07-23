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


## ---------------------------------------------------------------------
## Field mapping + compatibility-note generator (spec-6b7c, item 2 /
## fg-b0202). Builds on `detect_source_format` above (item 1 / fg-b0201):
## given a source path, extract its tools/model/persona/output-contract
## and map each to the `.forge/agents/` format fields
## (`docs/conventions/agents-lifecycle.md`, ".forge/agents/ (project-local
## agents)"). Non-1:1 features (unexposed tools, multi-agent crew
## topologies, memory/vector-store dependencies) are listed in a
## compatibility note rather than silently dropped. Embedded credentials
## are detected and stripped before anything is generated; their removal
## is named in the compatibility note, never their value.
##
## Field-mapping table (source field -> `.forge/agents/` field):
##   Claude Code subagent frontmatter:
##     name              -> name
##     description       -> description
##     model             -> model (default "sonnet" + compat note if absent)
##     tools             -> tools (verbatim allowlist)
##     body text         -> Mission (persona/system-prompt body)
##     "## Output contract" section (if present) -> Output contract
##     "## Attached skills" references -> resolved via detect_source_format's
##       skill_references; loadable ones attach by reference (AC2), others
##       -> compat note
##   CrewAI/LangChain-style prompt:
##     role/goal/backstory (or SystemMessage content) -> Mission (persona)
##     llm=<model string>  -> model (mapped to nearest Forge model, default
##       "sonnet"; original value always named in a compat note since there
##       is no exact equivalent)
##     tools=[...] python objects / YAML tool list -> compat note per tool
##       (no Forge tool-name equivalent -- "unexposed tool")
##     Crew(agents=[...]) with >1 agent, or >1 top-level YAML agent key
##       -> compat note ("multi-agent crew topology"; only the first/primary
##       agent is mapped, others named and dropped)
##     memory=/vectorstore markers (Chroma, FAISS, Pinecone, VectorStore)
##       -> compat note ("memory/vector-store dependency")
##   Bare system prompt:
##     whole text -> Mission (persona)
##     (no tools, no model, no output contract in source) -> each absence
##       recorded as a compat note; model defaults to "sonnet"
##
## Compat-note trigger list (non-exhaustive, see functions below):
##   - unrecognized source format (no mapping performed)
##   - source read error (not UTF-8 / missing file)
##   - no model preference in source (defaulted to "sonnet")
##   - no output-contract-like structure found in source
##   - skill reference not directly loadable (missing / malformed SKILL.md)
##   - unexposed tool with no Forge equivalent
##   - source model preference with no exact Forge equivalent
##   - multi-agent crew topology (only primary agent ported)
##   - memory/vector-store dependency (dropped, no Forge equivalent)
##   - embedded credential/API key/token detected and stripped

DEFAULT_FORGE_MODEL = "sonnet"

# Credential detection: matched spans are redacted (never logged/returned)
# before any other extraction runs, so no downstream field -- Mission body,
# tool list, model string -- can ever carry a live credential value through
# to a generated artifact. Patterns cover the common shapes named in the
# spec's Risks mitigation: OpenAI-style `sk-` keys, AWS-style access key
# ids, bearer tokens, and generic `api_key=`/`token:`/`password=`-style
# assignments (covers `.env`-style and YAML/Python kwarg assignments alike).
#
# The assigned-secret pattern's key-name prefix allows an optional leading
# shell-export token (`export ` for POSIX .env-style sourcing, `set ` for
# Windows batch parity -- included for the same reason, so a `.bat`/`.cmd`
# fixture isn't a second silent gap) before the key name itself, so
# `export SECRET_TOKEN=...` / `set API_KEY=...` are caught exactly like a
# bare `SECRET_TOKEN=...` assignment (verifier-reported P0: the old anchor
# required the key name to start immediately after leading whitespace,
# which the `export `/`set ` token broke).
_CREDENTIAL_PATTERNS = [
    ("OpenAI-style API key (sk-...)", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
    ("AWS-style access key ID (AKIA...)", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-_.=]{10,}")),
    ("assigned secret/token/key/password", re.compile(
        r"(?im)^([ \t]*(?:export|set)?[ \t]*[\w.\-]*"
        r"(?:api[_-]?key|secret|token|password|access[_-]?key)"
        r"[\w.\-]*[ \t]*[:=][ \t]*)"
        r"[\"']?([A-Za-z0-9/_\-+.]{8,})[\"']?")),
]

_CREDENTIAL_REDACTION = "[REDACTED-CREDENTIAL]"


def _strip_credentials(text):
    """Detect and redact embedded credentials in `text`.

    Returns (clean_text, findings). `findings` is a list of dicts
    {kind, count} naming what KIND of credential was found and how many
    matches -- never the matched value itself, so a finding is always safe
    to surface verbatim in a compatibility note or a test assertion.
    """
    findings = []
    clean = text
    for kind, pattern in _CREDENTIAL_PATTERNS:
        if pattern.groups:
            # "assigned secret/..." pattern: keep the key/operator prefix
            # (group 1), redact only the value (group 2).
            clean, count = pattern.subn(
                lambda m: m.group(1) + _CREDENTIAL_REDACTION, clean)
        else:
            clean, count = pattern.subn(_CREDENTIAL_REDACTION, clean)
        if count:
            findings.append({"kind": kind, "count": count})
    return clean, findings


def _extract_output_contract(body):
    """Pull an "## Output contract"-like section out of a Claude subagent
    body, if present. Returns (contract_text_or_None, remaining_body)."""
    m = re.search(
        r"(?ms)^##\s*Output contract.*?\n(.*?)(?=^##\s|\Z)", body)
    if not m:
        return None, body
    contract = m.group(1).strip()
    remaining = body[:m.start()] + body[m.end():]
    return (contract or None), remaining


def _map_claude_subagent(text, detection, result):
    m = _FRONTMATTER_RE.match(text)
    fm_fields = _parse_frontmatter_fields(m.group(1))
    body = text[m.end():]

    clean_fm_block, fm_findings = _strip_credentials(m.group(1))
    clean_body, body_findings = _strip_credentials(body)
    for f in fm_findings + body_findings:
        result["credential_findings"].append(f)
        result["compat_notes"].append(
            f"embedded credential detected and removed: {f['kind']} "
            f"({f['count']} occurrence(s)) -- value never carried into "
            f"the generated agent file")

    # Re-parse the frontmatter fields from the redacted block so a
    # credential embedded directly in a frontmatter scalar (e.g.
    # `api_key: sk-...`) can never survive into `result["fields"]`.
    fm_fields = _parse_frontmatter_fields(clean_fm_block)

    contract, remaining_body = _extract_output_contract(clean_body)
    if contract is None:
        result["compat_notes"].append(
            "no output-contract-like structure found in source -- a "
            "human must author an Output contract section for the port")

    model = fm_fields.get("model")
    if not model:
        result["compat_notes"].append(
            f"no model preference in source -- defaulted to "
            f"'{DEFAULT_FORGE_MODEL}'")
        model = DEFAULT_FORGE_MODEL

    for ref in detection["skill_references"]:
        if ref["loadable"]:
            result["compat_notes"].append(
                f"skill '{ref['name']}' is directly loadable unmodified -- "
                f"attach by reference (spec-6b7c AC2) rather than rewriting "
                f"its content")
        else:
            result["compat_notes"].append(
                f"skill '{ref['name']}' referenced but not directly "
                f"loadable -- {ref['reason']}; port manually or drop the "
                f"reference")

    result["fields"] = {
        "name": fm_fields.get("name"),
        "description": fm_fields.get("description"),
        "model": model,
        "tools": fm_fields.get("tools"),
        "mission": remaining_body.strip(),
        "output_contract": contract,
    }


# --- CrewAI / LangChain field extraction helpers -----------------------

def _extract_kv_field(text, key):
    """Best-effort extraction of `key`'s value from either a Python kwarg
    assignment (`key="...")`, a parenthesized concatenated-string kwarg
    (`key=(\"...\" \"...\")`), or a YAML scalar/block-scalar (`key: ...` /
    `key: >` followed by an indented block). Returns a cleaned string or
    None."""
    # Python: key="..." or key='...'
    m = re.search(key + r"\s*=\s*\"([^\"]*)\"", text)
    if m:
        return m.group(1).strip()
    m = re.search(key + r"\s*=\s*'([^']*)'", text)
    if m:
        return m.group(1).strip()
    # Python: key=(\n "..." \n "..." \n)
    m = re.search(key + r"\s*=\s*\(\s*((?:[\"'][^\"']*[\"']\s*)+)\)", text)
    if m:
        parts = re.findall(r"[\"']([^\"']*)[\"']", m.group(1))
        return "".join(parts).strip()
    # YAML block scalar: key: >  (folded) or key: |  (literal), then an
    # indented block of following lines.
    m = re.search(
        r"(?m)^[ \t]*" + key + r":[ \t]*[>|][+-]?[ \t]*\n"
        r"((?:^[ \t]+\S.*\n?)+)", text)
    if m:
        lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
        return " ".join(lines).strip()
    # YAML simple scalar: key: value
    m = re.search(r"(?m)^[ \t]*" + key + r":[ \t]*(.+)$", text)
    if m:
        val = m.group(1).strip()
        if val and val[0] == val[-1] and val[0] in ("'", '"') and len(val) >= 2:
            val = val[1:-1]
        return val.strip() or None
    return None


def _extract_tools_list(text):
    """Extract a CrewAI/LangChain `tools=[...]` (Python) or `tools:` (YAML
    list) block as a list of bare identifier/name strings."""
    m = re.search(r"tools\s*=\s*\[([^\]]*)\]", text)
    if m:
        return [t.strip() for t in m.group(1).split(",") if t.strip()]
    m = re.search(r"(?m)^[ \t]*tools:[ \t]*\n((?:^[ \t]*-.*\n?)+)", text)
    if m:
        return [
            ln.split("-", 1)[1].strip()
            for ln in m.group(1).splitlines()
            if ln.strip().startswith("-")
        ]
    return []


_MEMORY_MARKERS_RE = re.compile(
    r"\b(Chroma|FAISS|Pinecone|VectorStore|vectorstore|memory\s*=)\b")


def _map_crewai_langchain(text, result):
    clean, findings = _strip_credentials(text)
    for f in findings:
        result["credential_findings"].append(f)
        result["compat_notes"].append(
            f"embedded credential detected and removed: {f['kind']} "
            f"({f['count']} occurrence(s)) -- value never carried into "
            f"the generated agent file")

    unfenced = _strip_fenced_code_blocks(clean)

    role = _extract_kv_field(unfenced, "role")
    goal = _extract_kv_field(unfenced, "goal")
    backstory = _extract_kv_field(unfenced, "backstory")
    system_message = None
    m = re.search(r"SystemMessage\s*\(\s*content\s*=\s*\"([^\"]*)\"", unfenced)
    if m:
        system_message = m.group(1).strip()

    persona_parts = []
    if role:
        persona_parts.append(f"Role: {role}")
    if goal:
        persona_parts.append(f"Goal: {goal}")
    if backstory:
        persona_parts.append(f"Backstory: {backstory}")
    if system_message:
        persona_parts.append(system_message)
    mission = "\n\n".join(persona_parts) if persona_parts else None
    if mission is None:
        result["compat_notes"].append(
            "no role/goal/backstory or system message found -- persona "
            "could not be extracted, manual authoring required")

    llm = _extract_kv_field(unfenced, "llm")
    model = DEFAULT_FORGE_MODEL
    if llm:
        result["compat_notes"].append(
            f"source model preference '{llm}' has no exact Forge model "
            f"equivalent -- mapped to default '{DEFAULT_FORGE_MODEL}', "
            f"verify manually")
    else:
        result["compat_notes"].append(
            f"no model preference in source -- defaulted to "
            f"'{DEFAULT_FORGE_MODEL}'")

    tool_names = _extract_tools_list(unfenced)
    for name in tool_names:
        result["compat_notes"].append(
            f"unexposed tool '{name}' referenced in source -- no Forge "
            f"tool-name equivalent, review and remap manually")

    agent_count = 0
    m = re.search(r"agents\s*=\s*\[([^\]]*)\]", unfenced)
    if m:
        agent_count = len([a for a in m.group(1).split(",") if a.strip()])
    else:
        # YAML shape: count distinct top-level (column-0) mapping keys
        # that themselves contain a nested `role:` key -- one per agent.
        top_level_keys = re.findall(r"(?m)^([A-Za-z_][\w-]*):[ \t]*$", unfenced)
        if len(top_level_keys) > 1:
            agent_count = len(top_level_keys)
    if agent_count > 1:
        result["compat_notes"].append(
            f"source defines a multi-agent crew topology ({agent_count} "
            f"agents) -- Forge's single-agent format cannot represent "
            f"multi-agent orchestration; only the primary agent "
            f"('{role or 'unnamed'}') was mapped, the rest were dropped")

    if _MEMORY_MARKERS_RE.search(unfenced):
        result["compat_notes"].append(
            "source has a memory/vector-store dependency (e.g. Chroma/"
            "FAISS/Pinecone/VectorStore) -- no Forge equivalent, dropped "
            "from the port")

    result["fields"] = {
        "name": None,
        "description": goal,
        "model": model,
        "tools": None,
        "mission": mission,
        "output_contract": None,
    }
    result["compat_notes"].append(
        "no output-contract-like structure found in source -- a human "
        "must author an Output contract section for the port")


def _map_bare_system_prompt(text, result):
    clean, findings = _strip_credentials(text)
    for f in findings:
        result["credential_findings"].append(f)
        result["compat_notes"].append(
            f"embedded credential detected and removed: {f['kind']} "
            f"({f['count']} occurrence(s)) -- value never carried into "
            f"the generated agent file")

    result["compat_notes"].append(
        f"no model preference in source -- defaulted to "
        f"'{DEFAULT_FORGE_MODEL}'")
    result["compat_notes"].append(
        "no tools list in source -- ported agent inherits default tools "
        "unless a human adds an allowlist")
    result["compat_notes"].append(
        "no output-contract-like structure found in source -- a human "
        "must author an Output contract section for the port")

    result["fields"] = {
        "name": None,
        "description": None,
        "model": DEFAULT_FORGE_MODEL,
        "tools": None,
        "mission": clean.strip(),
        "output_contract": None,
    }


def map_source_to_agent_fields(path, skills_root=None):
    """Map an existing custom agent definition at `path` to the
    `.forge/agents/` format fields, generating compatibility notes for any
    non-1:1 feature and stripping any embedded credential before it is
    ever placed in a returned field.

    Returns a dict:
      {
        "path": str, "format": one of the FORMAT_* constants,
        "detection_reason": str,
        "fields": {name, description, model, tools, mission,
                    output_contract} (values may be None),
        "compat_notes": [str, ...],
        "credential_findings": [{"kind": str, "count": int}, ...],
      }

    When `format` is FORMAT_UNRECOGNIZED (or the source cannot be read),
    `fields` is left empty and a compat note explains why -- per AC1, no
    mapping is guessed for an unrecognized shape.
    """
    detection = detect_source_format(path, skills_root=skills_root)
    result = {
        "path": detection["path"],
        "format": detection["format"],
        "detection_reason": detection["reason"],
        "fields": {},
        "compat_notes": [],
        "credential_findings": [],
    }
    if detection["format"] == FORMAT_UNRECOGNIZED:
        result["compat_notes"].append(
            f"source format unrecognized ({detection['reason']}) -- no "
            f"field mapping performed, manual conversion required")
        return result

    text, err = _read_text(path)
    if err is not None:
        result["compat_notes"].append(err)
        return result

    if detection["format"] == FORMAT_CLAUDE_SUBAGENT:
        _map_claude_subagent(text, detection, result)
    elif detection["format"] == FORMAT_CREWAI_LANGCHAIN:
        _map_crewai_langchain(text, result)
    elif detection["format"] == FORMAT_BARE_SYSTEM_PROMPT:
        _map_bare_system_prompt(text, result)
    return result


def render_agent_markdown(mapped):
    """Render the `.forge/agents/<name>.md`-shaped markdown content for a
    `map_source_to_agent_fields` result (in-memory only -- writing to disk
    is `/forge:port`'s job, item 3, spec-6b7c). Used here so tests can
    assert that no credential value ever reaches a generated artifact.
    """
    fields = mapped["fields"]
    lines = ["---"]
    lines.append(f"name: {fields.get('name') or '<TODO: name>'}")
    lines.append(
        f"description: {fields.get('description') or '<TODO: description>'}")
    lines.append(f"model: {fields.get('model') or DEFAULT_FORGE_MODEL}")
    if fields.get("tools"):
        lines.append(f"tools: {fields['tools']}")
    lines.append("---")
    lines.append("")
    lines.append("## Mission")
    lines.append(fields.get("mission") or "<TODO: mission>")
    lines.append("")
    lines.append("## Output contract")
    lines.append(fields.get("output_contract") or "<TODO: output contract>")
    if mapped["compat_notes"]:
        lines.append("")
        lines.append("## Provenance")
        lines.append("- ported: yes")
        lines.append("- compatibility notes:")
        for note in mapped["compat_notes"]:
            lines.append(f"  - {note}")
    return "\n".join(lines) + "\n"


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
