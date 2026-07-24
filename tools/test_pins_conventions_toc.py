"""Doc-pin regression tests for fg-9e0105: docs/conventions.md navigability —
topic-grouped TOC + "Amended by:" cross-links, with a zero-content-change bar
(TOC and amended-by lines are pure additions; no existing prose line changes).

These pins keep future tail-appends to docs/conventions.md honest: a new `##`
section landed without also being added to the TOC fails test_toc_lists_every_section.
"""
import pathlib
import re
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import conventions_corpus  # noqa: E402 -- fg-b0401 corpus loader

TOC_MARKER = "**Table of contents**"

_HEADING_RE = re.compile(r"^## (.+)$")
_TOC_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")


def _real_section_headings(content: str) -> list:
    """Fence-aware `## ` heading extraction.

    docs/conventions.md embeds several literal `## ` lines inside fenced
    code blocks (e.g. the task-file / spec-file / forge.md body-section
    templates) that are example content, not real document sections. A
    naive line-by-line regex would wrongly pick those up. Track fence state
    (``` toggles) and only collect `## ` lines outside a fence.
    """
    headings = []
    in_fence = False
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            headings.append(m.group(1))
    return headings


def _toc_entries(content: str) -> list:
    """Extract the heading text named by each TOC bullet line.

    A couple of TOC lines carry a trailing "(also amends ..., above)"
    cross-reference annotation for amendments that touch two parents —
    strip that back off so the entry compares equal to the real heading
    text it names.
    """
    start = content.index(TOC_MARKER)
    # The TOC list runs from the marker to the next real (non-fenced) `## `
    # heading; slicing to the first heading below is a safe upper bound
    # since the TOC itself contains no `## ` lines.
    heading_match = _HEADING_RE_MULTILINE_SEARCH(content, start)
    block = content[start:heading_match]
    entries = []
    for line in block.splitlines():
        m = _TOC_ITEM_RE.match(line)
        if not m:
            continue
        text = m.group(1)
        text = text.split(" (also amends")[0]
        entries.append(text)
    return entries


def _HEADING_RE_MULTILINE_SEARCH(content: str, after: int) -> int:
    """Index of the first fence-aware `## ` heading appearing after `after`."""
    in_fence = False
    pos = after
    for line in content[after:].splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and _HEADING_RE.match(stripped):
            return pos
        pos += len(line)
    raise AssertionError("no `## ` heading found after the TOC marker")


class TestConventionsTocPins(unittest.TestCase):
    """Pins for fg-9e0105: TOC + amended-by cross-links in docs/conventions.md."""

    def setUp(self):
        # fg-b0401: docs/conventions.md was sharded into docs/conventions/*.md;
        # the corpus loader reconstructs the pre-split concatenated text so
        # every pin below keeps matching unchanged.
        self.content = conventions_corpus.corpus_text()

    def test_toc_block_exists_before_first_section(self):
        """The TOC marker must appear, and it must appear before the file's
        first real `## ` section heading (fence-aware) — a reader hits the
        map before any content."""
        self.assertIn(TOC_MARKER, self.content)
        toc_index = self.content.index(TOC_MARKER)
        first_heading_index = _HEADING_RE_MULTILINE_SEARCH(self.content, 0)
        self.assertLess(
            toc_index,
            first_heading_index,
            "TOC marker must precede the first `## ` section heading",
        )

    def test_toc_lists_every_section(self):
        """Every real `## ` heading in the file (fence-aware — excludes the
        body-section templates shown inside code fences) must appear in the
        TOC, via a plain set-compare. This is the pin that keeps future
        tail-appends honest: a new section missing from the TOC fails here."""
        headings = set(_real_section_headings(self.content))
        toc_entries = set(_toc_entries(self.content))
        missing = headings - toc_entries
        self.assertEqual(
            missing,
            set(),
            f"sections present in the file but missing from the TOC: {missing}",
        )

    def test_trust_boundary_has_amended_by_line(self):
        """The Trust boundary parent section carries an "Amended by:" line
        naming its amending section exactly, directly under its own heading
        (not merely present somewhere in the file)."""
        self.assertIn(
            '## Trust boundary\n\n'
            '> Amended by: "Trust boundary — specs + NL scoping amendment (2026-07-17)"',
            self.content,
        )

    def test_trust_boundary_original_prose_unchanged(self):
        """Zero-deletion property can't be pinned directly in a unittest (no
        base ref to diff against here), so instead pin one known original
        sentence — the first prose line of the Trust boundary section — to
        prove the section was not rewritten, only added-to."""
        self.assertIn(
            "Response to `.forge/specs/2026-07-17-trust-boundary.md` (task fg-7b01,",
            self.content,
        )


if __name__ == "__main__":
    unittest.main()
