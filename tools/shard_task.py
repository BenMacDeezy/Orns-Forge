# tools/shard_task.py
"""Deterministic shard splitter (fg-a10812, T2 of the fg-a10801 sharded
fan-out decomposition).

Pure module: given (shard_by, max_shards, shard_key) it resolves a source
set and partitions it into <=max_shards disjoint, exhaustive slices via a
deterministic stable-sort + contiguous-chunk rule. Same inputs -> identical
slices, every run -- no `Date.now()`/wall-clock, no randomness; every input
travels in via function arguments (the same determinism discipline the
sharded-fan-out design (docs/plans/2026-07-18-sharded-fanout-design.md, D2)
borrows from `workflow-executor`).

v1 sources ONLY: an inline list of literal strings, or one or more glob
patterns (matched via `glob.glob`). No `cmd:` source -- that is deferred per
the OQ2 trust-boundary decision in the design doc; this module must never
shell out. `ranges` sources are a plain (start, end) integer pair or
"start-end" string -- no filesystem or process interaction either.

This is a splitter, not a validator: `tools/validate_task.py` (a sibling
task, fg-a10811) shape-checks `shard-by`/`max-shards`/`shard-key` in task
frontmatter. This module trusts its caller to have already validated shape
and focuses only on the disjoint/exhaustive/deterministic partition.
"""
from __future__ import annotations

import glob as _glob
import json
import os
import re
import sys

_GLOB_CHARS = ("*", "?", "[")


class ShardError(ValueError):
    """Raised for a malformed shard_by/max_shards/shard_key input."""


def _is_glob_pattern(entry) -> bool:
    return isinstance(entry, str) and any(c in entry for c in _GLOB_CHARS)


_RANGE_STR_RE = re.compile(r"^(-?\d+)-(-?\d+)$")


def _resolve_range(shard_key):
    """Resolve a `ranges` shard_key -- (start, end) ints or an "start-end"
    string, both inclusive -- into list(range(start, end + 1)). No
    filesystem/process interaction, so this is trivially deterministic.

    The string form is parsed with a regex that captures an optional
    leading `-` sign on each number (rather than a naive
    `str.split("-", 1)`, which always splits on the FIRST `-` and so can
    never represent a negative `start` -- "-5-3" would split into
    "" and "5-3"). This keeps the string form able to express everything
    the tuple form can, including a negative start."""
    if isinstance(shard_key, str):
        m = _RANGE_STR_RE.match(shard_key.strip())
        if not m:
            raise ShardError(f"invalid range shard_key: {shard_key!r}")
        start, end = int(m.group(1)), int(m.group(2))
    else:
        try:
            start, end = shard_key
            start, end = int(start), int(end)
        except (TypeError, ValueError) as exc:
            raise ShardError(f"invalid range shard_key: {shard_key!r}") from exc
    if end < start:
        raise ShardError(f"invalid range (end < start): {shard_key!r}")
    return list(range(start, end + 1))


def resolve_source(shard_by, shard_key):
    """Resolve shard_key into a deterministic, deduped, sorted list of atoms.

    - shard_by == "ranges": see _resolve_range.
    - shard_by in ("files", "items"): shard_key is a single string (one
      literal path/item, or one glob pattern) or a list of strings (any mix
      of literal entries and glob patterns). Every entry containing a glob
      metacharacter (*, ?, [) is expanded via `glob.glob(entry,
      recursive=True)`; everything else is taken as a literal atom. The
      resolved set is deduped via `set()` before sorting, so two glob
      patterns that both resolve the same path collapse to one occurrence
      (the disjointness invariant, EARS clause 3) instead of ever landing in
      two slices.

      A pattern-shaped entry that `glob.glob()` matches nothing for is not
      necessarily a real glob search gone empty: `[` in particular commonly
      appears in ordinary literal filenames (e.g. "report[2026].csv"),
      which `glob.glob()` interprets as a one-character class rather than
      the literal substring, so it silently matches nothing even though the
      file exists. When that happens, the literal string is checked against
      disk (`os.path.exists`) and used as a literal atom if found. A `*`/`?`
      entry that legitimately matches nothing (a real wildcard search over
      an empty/nonexistent set) still yields an empty contribution, never an
      error -- that is the degenerate empty-enumeration case (EARS clause
      2). But a `[`-only entry that resolves neither as a glob match nor as
      a literal path on disk is genuinely unresolvable input, not a
      legitimate empty search, and raises ShardError naming it rather than
      silently vanishing from the resolved set.

    Sorting is what makes this deterministic even though `glob.glob`'s raw
    return order depends on OS directory-enumeration order (not guaranteed
    stable across runs/filesystems) -- the sort removes that as a source of
    nondeterminism.
    """
    if shard_by == "ranges":
        return _resolve_range(shard_key)
    if shard_by not in ("files", "items"):
        raise ShardError(f"unknown shard_by: {shard_by!r} (expected files|items|ranges)")

    entries = [shard_key] if isinstance(shard_key, str) else list(shard_key)
    resolved = set()
    for entry in entries:
        if _is_glob_pattern(entry):
            matches = _glob.glob(entry, recursive=True)
            if matches:
                resolved.update(matches)
            elif os.path.exists(entry):
                resolved.add(entry)
            elif any(c in entry for c in ("*", "?")):
                pass  # a real wildcard search matching nothing is not an error
            else:
                raise ShardError(f"unresolved shard item: {entry!r}")
        else:
            resolved.add(entry)
    return sorted(resolved)


def _chunk(atoms, max_shards, shard_by):
    """Stable-sort (already done by resolve_source) + contiguous-chunk rule.

    Degenerate case (EARS clause 2): zero or one atom always yields exactly
    ONE slice, regardless of max_shards -- never an error, never a fan-out.

    Otherwise: N = min(max_shards, len(atoms)) contiguous, disjoint,
    exhaustive chunks, sized as evenly as possible (the first `remainder`
    chunks get one extra atom) via plain list slicing -- slicing a sequence
    into consecutive, non-overlapping ranges is disjoint and exhaustive by
    construction, with no possibility of an atom landing in two chunks or
    being dropped.
    """
    n_atoms = len(atoms)
    if n_atoms <= 1:
        return [{"index": 1, "shard_by": shard_by, "items": list(atoms)}]

    n = min(max_shards, n_atoms)
    base, remainder = divmod(n_atoms, n)
    slices = []
    start = 0
    for i in range(n):
        size = base + (1 if i < remainder else 0)
        slices.append({
            "index": i + 1,
            "shard_by": shard_by,
            "items": atoms[start:start + size],
        })
        start += size
    return slices


def split_shards(shard_by, max_shards, shard_key):
    """Pure, deterministic splitter: (shard_by, max_shards, shard_key) -> a
    stable, indexable list of <=max_shards disjoint + exhaustive slice
    manifests, each `{"index": i, "shard_by": shard_by, "items": [...]}`
    with 1-based `index` so the kernel can label swarm members #1..#N
    directly off the slice index (EARS clause 4).

    No wall-clock, no randomness -- calling this twice with identical
    arguments always returns identical output (EARS clause 1). All inputs
    travel in via function arguments; nothing is read from global/mutable
    state.
    """
    if not isinstance(max_shards, int) or max_shards < 2:
        raise ShardError(f"max_shards must be an int >= 2, got {max_shards!r}")
    atoms = resolve_source(shard_by, shard_key)
    return _chunk(atoms, max_shards, shard_by)


def main(argv):
    if len(argv) < 3:
        print(
            "usage: shard_task.py <shard_by:files|items|ranges> <max_shards> <shard_key...>",
            file=sys.stderr,
        )
        return 2
    shard_by, max_shards_raw = argv[0], argv[1]
    shard_key = argv[2] if len(argv) == 3 else argv[2:]
    try:
        max_shards = int(max_shards_raw)
        slices = split_shards(shard_by, max_shards, shard_key)
    except (ShardError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(slices, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
