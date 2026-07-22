"""Corpus loader for docs/conventions.md's sharded layout (fg-b0401).

docs/conventions.md was split into per-domain shards under docs/conventions/
(section bodies moved out verbatim; the root file is now index-only: preamble,
TOC, and the Shards manifest). Doc-pin tests written against the old
monolithic file expect a single blob of text to substring-search — this
module reconstructs that blob deterministically so those pins keep working
unchanged against the new layout.

corpus_text() is root_text() followed by every section body, REASSEMBLED IN
ORIGINAL DOCUMENT ORDER (not shard-file order) — sections are grouped into
shards by domain for readability and parallel-write isolation, but several
existing pins scope a substring search with `content.split(HEADING)[1]`
(unbounded — "everything from this heading to the end of the corpus") and
rely on a LATER-dated amendment's content (possibly filed in a different
shard) still appearing after it, exactly as it did in the original
chronological file. Concatenating whole shard files in a fixed shard order
does not preserve that; reassembling by original section order does, and
also keeps "Agent promotion and retention — 2026-07-19 (fg-b0305+fg-b0306,
spec-b71f3a)" — the last section in the original file — the last heading in
corpus_text() automatically, with no special-cased shard ordering needed.

The reassembly order is read from the index file's own "### Shards
manifest" list, which is already in original document order (see
docs/conventions.md).
"""
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CONVENTIONS_ROOT = REPO_ROOT / "docs" / "conventions.md"
SHARD_DIR = REPO_ROOT / "docs" / "conventions"

_HEADING_RE = re.compile(r"^## (.+)$")
_MANIFEST_LINE_RE = re.compile(r"^- `(.+?)` -> `docs/conventions/([a-z-]+)\.md`$", re.MULTILINE)


def root_text() -> str:
    """The index file's own text (preamble + TOC + Shards manifest)."""
    return CONVENTIONS_ROOT.read_text(encoding="utf-8")


def shard_text(name: str) -> str:
    """One shard's text by its bare name (e.g. "trust-and-security", no
    .md suffix, no directory)."""
    return (SHARD_DIR / f"{name}.md").read_text(encoding="utf-8")


def _fence_aware_sections(content: str):
    """Fence-aware {heading_text: body_text} map. body_text runs from
    directly after the heading line through (not including) the next real
    "## " heading, or EOF -- code-fenced "## " lines (body-format examples)
    are never treated as real headings."""
    sections = {}
    in_fence = False
    current = None
    buf = []
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            if current is not None:
                buf.append(line)
            continue
        if not in_fence:
            m = _HEADING_RE.match(stripped)
            if m:
                if current is not None:
                    sections[current] = "".join(buf)
                current = m.group(1)
                buf = [line]
                continue
        if current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "".join(buf)
    return sections


def _manifest_order():
    """[(section_name, shard_name), ...] in original document order, parsed
    from the index file's Shards manifest."""
    text = root_text()
    if "### Shards manifest" not in text:
        return []
    block = text.split("### Shards manifest", 1)[1]
    return [(m.group(1), m.group(2)) for m in _MANIFEST_LINE_RE.finditer(block)]


def corpus_text() -> str:
    """root_text() followed by every section's heading+body, reassembled in
    ORIGINAL DOCUMENT ORDER (see module docstring for why this is not the
    same as concatenating whole shard files). This is the drop-in
    replacement for the old `(docs/conventions.md).read_text()` call in
    doc-pin tests."""
    manifest = _manifest_order()
    shard_names = sorted({shard for _, shard in manifest})
    sections_by_shard = {name: _fence_aware_sections(shard_text(name)) for name in shard_names}

    parts = [root_text()]
    for heading, shard in manifest:
        parts.append(sections_by_shard[shard][heading])
    return "\n\n".join(parts)
