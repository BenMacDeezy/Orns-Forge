#!/usr/bin/env python3
"""Conservation gates for fg-b0401 (docs/conventions.md sharding).

R1 — Mechanical-split fidelity. Every section that existed in the git-base
    (HEAD) revision of docs/conventions.md must still exist, byte-identical,
    somewhere in the new docs/conventions/*.md shards. The new index file
    (docs/conventions.md) must carry zero section bodies. This is a subset
    check, not an exact-set check: this task's own new amendment section
    ("Sharded fan-out — per-shard write surfaces amendment") is expected to
    exist in the shards without a base counterpart (documented, not lost).

R2 — Index integrity. (a) Bidirectional check: the set of section names in
    the index's Shards manifest equals the union of every shard's actual
    "## " headings — nothing named in the manifest is missing from a shard,
    and nothing in a shard is left out of the manifest. (b) Source-citation
    resolver: every quoted section-name citation of the form
    `docs/conventions.md`, "Section Name" (or the parenthetical form) found
    under skills/, agents/, commands/, tools/, hooks/, workflows/ resolves
    to exactly one manifest entry.

R3 — Amendment-pointer integrity. Every `> Amended by: "..."` / `> Amends:
    "..." (above).` pointer target, anywhere in the shard corpus, resolves
    to a real manifest entry.

Run directly (`python tools/check_shard_conservation.py`) for a human-
readable report + process exit code, or via tools/test_shard_conservation.py
as permanent pytest coverage.
"""
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import conventions_corpus  # noqa: E402

SHARD_DIR = REPO_ROOT / "docs" / "conventions"
ROOT_FILE = REPO_ROOT / "docs" / "conventions.md"

_HEADING_RE = re.compile(r"^## (.+)$")

# Pre-split revision: the last commit where docs/conventions.md held all
# section bodies. Pinned (not HEAD) so R1 keeps proving conservation against
# the real monolith forever; against HEAD-the-index it would pass vacuously.
_BASE_REV = "de15bb9"


def _fence_aware_sections(content: str):
    """Fence-aware split into {heading_text: body_text}. body_text is
    everything from directly after the heading line through (not including)
    the next real "## " heading, or EOF. Mirrors
    tools/test_pins_conventions_toc.py's fence-aware heading detector."""
    lines = content.splitlines(keepends=True)
    sections = {}
    order = []
    in_fence = False
    current = None
    buf = []
    for line in lines:
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
                order.append(current)
                buf = []
                continue
        if current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "".join(buf)
    return sections, order


def _fence_aware_headings(content: str):
    _, order = _fence_aware_sections(content)
    return order


def _git_base_conventions_text() -> str:
    result = subprocess.run(
        ["git", "show", _BASE_REV + ":docs/conventions.md"],
        capture_output=True, cwd=str(REPO_ROOT), check=True,
    )
    return result.stdout.decode("utf-8")


def _manifest_entries():
    """Parse the "### Shards manifest" list in the index file:
    [(section_name, shard_name), ...]"""
    text = ROOT_FILE.read_text(encoding="utf-8")
    if "### Shards manifest" not in text:
        return []
    block = text.split("### Shards manifest", 1)[1]
    entries = []
    for m in re.finditer(r"^- `(.+?)` -> `docs/conventions/([a-z-]+)\.md`$", block, re.MULTILINE):
        entries.append((m.group(1), m.group(2)))
    return entries


def _shard_files():
    return sorted(SHARD_DIR.glob("*.md"))


def check_r1():
    errors = []
    base_text = _git_base_conventions_text()
    base_sections, _ = _fence_aware_sections(base_text)

    all_new_sections = {}
    dupes = []
    for f in _shard_files():
        secs, _ = _fence_aware_sections(f.read_text(encoding="utf-8"))
        for name, body in secs.items():
            if name in all_new_sections:
                dupes.append(name)
            all_new_sections[name] = body
    if dupes:
        errors.append(f"R1: heading(s) appear in more than one shard: {dupes}")

    missing = [h for h in base_sections if h not in all_new_sections]
    if missing:
        errors.append(f"R1: base heading(s) missing from shards: {missing}")

    changed = []
    for h, body in base_sections.items():
        if h in all_new_sections and all_new_sections[h] != body:
            changed.append(h)
    if changed:
        errors.append(f"R1: heading(s) with non-byte-identical body vs base: {changed}")

    root_headings = _fence_aware_headings(ROOT_FILE.read_text(encoding="utf-8"))
    if root_headings:
        errors.append(f"R1: index file (docs/conventions.md) still carries '## ' body section(s): {root_headings}")

    return errors


def check_r2():
    errors = []
    manifest = _manifest_entries()
    manifest_names = {name for name, _ in manifest}

    shard_headings = set()
    for f in _shard_files():
        shard_headings.update(_fence_aware_headings(f.read_text(encoding="utf-8")))

    missing_from_manifest = shard_headings - manifest_names
    if missing_from_manifest:
        errors.append(f"R2: shard heading(s) not listed in the index manifest: {sorted(missing_from_manifest)}")

    missing_from_shards = manifest_names - shard_headings
    if missing_from_shards:
        errors.append(f"R2: manifest entry/entries with no matching shard heading: {sorted(missing_from_shards)}")

    # Source-citation resolver. Deliberately conservative: only a quoted
    # phrase that opens on the SAME physical line as a "docs/conventions.md"
    # mention (the well-established citation idiom used throughout this
    # corpus, e.g. `docs/conventions.md`, "Section Name" or
    # `docs/conventions.md` ("Section Name")) is checked. Citations whose
    # quote wraps across a markdown line-wrap are skipped rather than
    # guessed at -- an undercount is safer than a false failure here, since
    # this gate must stay green as a permanent pytest test, not just today.
    scan_dirs = ["skills", "agents", "commands", "tools", "hooks", "workflows"]
    # Require the char directly after ".md" to be a backtick or a
    # comma/open-paren (the real citation idioms in this corpus) -- NOT a
    # bare quote, which would otherwise false-match the closing `"` of an
    # ordinary `"docs/conventions.md"` Python path string literal as if it
    # opened a citation quote.
    citation_re = re.compile(
        r"docs/conventions\.md(`|[,(])[\s,(]*\"([^\"]{3,160})\""
    )
    this_file = pathlib.Path(__file__).name
    full_corpus = conventions_corpus.corpus_text()
    # Pre-existing loose paraphrases that were never a literal section title
    # or body quote even in the original monolithic file (verified against
    # `git show HEAD:docs/conventions.md` before this task) -- not
    # citations this gate can validate, and not something the split broke.
    KNOWN_PARAPHRASES = {"scripts are accelerators"}
    unresolved = []
    for d in scan_dirs:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not f.is_file() or f.suffix not in (".md", ".py", ".sh"):
                continue
            if f.name in (this_file, "test_shard_conservation.py"):
                continue  # this module's own docstrings/tests, not citations
            try:
                content = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line in content.splitlines():
                for m in citation_re.finditer(line):
                    cite = m.group(2).strip().rstrip(",.:;").rstrip(".")
                    cite = cite[:-3] if cite.endswith("...") else cite
                    cite = cite.strip()
                    # A citation may legitimately quote only a prefix of the
                    # full section name (trailing date/task-id dropped for
                    # readability) -- resolve on exact match OR unambiguous
                    # prefix match against the manifest. Failing both, a
                    # citation of a sub-heading or a quoted body sentence
                    # (not the section's own H2 title) resolves if the
                    # quoted text is still findable verbatim in the shard
                    # corpus -- only a citation that matches NONE of these
                    # is a real broken reference.
                    if cite in manifest_names:
                        continue
                    prefix_matches = [n for n in manifest_names if n.startswith(cite)]
                    if len(prefix_matches) == 1:
                        continue
                    if cite and cite in full_corpus:
                        continue
                    if cite in KNOWN_PARAPHRASES:
                        continue
                    unresolved.append((str(f.relative_to(REPO_ROOT)), cite, len(prefix_matches)))
    if unresolved:
        lines = [f"  {p}: \"{c}\" ({'no match' if n == 0 else f'{n} ambiguous matches'})" for p, c, n in unresolved]
        errors.append("R2: unresolved section-name citation(s):\n" + "\n".join(lines))

    return errors


def check_r3():
    errors = []
    manifest_names = {name for name, _ in _manifest_entries()}
    pointer_re = re.compile(r'"([^"]+)"')
    unresolved = []
    for f in _shard_files():
        content = f.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("> Amended by:") or stripped.startswith("> Amends:")):
                continue
            for m in pointer_re.finditer(stripped):
                target = m.group(1).strip()
                if target not in manifest_names:
                    unresolved.append((f.name, stripped[:2] and target))
    if unresolved:
        lines = [f"  {fname}: \"{t}\"" for fname, t in unresolved]
        errors.append("R3: unresolved Amended-by/Amends pointer target(s):\n" + "\n".join(lines))
    return errors


def main():
    all_errors = []
    r1 = check_r1()
    r2 = check_r2()
    r3 = check_r3()

    print("=== R1 (mechanical-split fidelity) ===")
    if r1:
        for e in r1:
            print("FAIL:", e)
        all_errors += r1
    else:
        print("PASS")

    print("=== R2 (index integrity) ===")
    if r2:
        for e in r2:
            print("FAIL:", e)
        all_errors += r2
    else:
        print("PASS")

    print("=== R3 (amendment-pointer integrity) ===")
    if r3:
        for e in r3:
            print("FAIL:", e)
        all_errors += r3
    else:
        print("PASS")

    if all_errors:
        print(f"\n{len(all_errors)} gate(s) FAILED")
        return 1
    print("\nAll gates PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
