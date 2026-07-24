"""Shared helpers for the sharded doc-pin test modules (fg-a11040).

Extracted verbatim (behavior-preserving) from the former monolithic
tools/test_doc_pins.py so every per-task shard module reads the same
REPO_ROOT, the same cached file readers, and the same conventions-corpus
redirect instead of each carrying its own copy.
"""
import functools
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_task  # noqa: E402 -- fg-a10813 bounce-2 max-shards pin
import shard_task  # noqa: E402 -- fg-a10814 manifest-key behavioral pin
import conventions_corpus  # noqa: E402 -- fg-b0401 corpus loader

_CONVENTIONS_PATH_RESOLVED = (REPO_ROOT / "docs" / "conventions.md").resolve()


@functools.lru_cache(maxsize=None)
def _cached_read_text(path):
    """Read a markdown/text file's contents, memoized by resolved path so a
    file pinned by many test methods/classes is only ever read once per
    process (fg-a11040: doc-pin suite condense — kills the O(n) re-read cost
    of hundreds of pin methods each opening the same handful of docs)."""
    return pathlib.Path(path).resolve().read_text(encoding="utf-8")


def _read_path(path):
    """Read a file's text; docs/conventions.md is transparently redirected to
    the fg-b0401 corpus loader (root index + all shards concatenated) so
    every pre-existing pin below keeps matching the sharded layout
    unchanged. `path` may be a string (repo-relative) or a Path."""
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    if p.resolve() == _CONVENTIONS_PATH_RESOLVED:
        return conventions_corpus.corpus_text()
    return _cached_read_text(p)


# Spelled-out number words the Commands prose might use (kept generous —
# only "sixteen" is expected today, but the count will drift as commands
# are added/removed, so cover a realistic range rather than hardcoding one).
_WORD_TO_INT = {
    word: n
    for n, word in enumerate(
        [
            "zero", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve", "thirteen",
            "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen", "twenty", "twenty-one", "twenty-two", "twenty-three",
            "twenty-four", "twenty-five", "twenty-six", "twenty-seven",
            "twenty-eight", "twenty-nine", "thirty", "thirty-one",
            "thirty-two", "thirty-three", "thirty-four", "thirty-five",
            "thirty-six", "thirty-seven", "thirty-eight", "thirty-nine",
            "forty", "forty-one", "forty-two", "forty-three", "forty-four",
            "forty-five", "forty-six", "forty-seven", "forty-eight",
            "forty-nine", "fifty", "fifty-one", "fifty-two", "fifty-three",
            "fifty-four", "fifty-five", "fifty-six", "fifty-seven",
            "fifty-eight", "fifty-nine", "sixty", "sixty-one",
        ]
    )
}
