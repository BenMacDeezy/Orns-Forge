# tools/test_shard_task.py
"""Tests for tools/shard_task.py (fg-a10812) pinning each EARS clause of the
task's Acceptance criteria against a real function call -- no mocks, so a
naive/non-deterministic or overlap-blind implementation fails these.

Clause -> test mapping:
  1 (disjoint + exhaustive + deterministic stable-sort/contiguous-chunk) ->
    TestDisjointExhaustive, TestDeterminism
  2 (files source: inline-list/glob only; empty/single -> one slice) ->
    TestFilesAndItemsSource, TestDegenerateCases
  3 (overlapping globs dedupe deterministically) -> TestOverlapDedupe
  4 (stable, indexable list for #1..#N labeling) -> TestIndexableOutput
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import shard_task  # noqa: E402


def _touch(tmp, *names):
    paths = []
    for name in names:
        p = pathlib.Path(tmp) / name
        p.write_text("x", encoding="utf-8")
        paths.append(str(p))
    return paths


class TestDisjointExhaustive(unittest.TestCase):
    """Clause 1: <=N slices, no item in two (disjoint), every item in
    exactly one (exhaustive)."""

    def _assert_disjoint_and_exhaustive(self, slices, all_atoms):
        seen = []
        for s in slices:
            seen.extend(s["items"])
        # Exhaustive: union of slice items equals the full atom set.
        self.assertEqual(sorted(seen), sorted(all_atoms))
        # Disjoint: no duplicates across slices (a repeat would mean one
        # atom landed in two slices).
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(len(seen), len(all_atoms))

    def test_items_split_into_at_most_n_disjoint_exhaustive_slices(self):
        items = [f"item-{i}" for i in range(7)]
        slices = shard_task.split_shards("items", 3, items)
        self.assertLessEqual(len(slices), 3)
        self._assert_disjoint_and_exhaustive(slices, items)

    def test_slice_count_never_exceeds_atom_count(self):
        # max_shards=10 but only 4 atoms -> at most 4 slices, never 10 empty
        # padding slices.
        items = ["a", "b", "c", "d"]
        slices = shard_task.split_shards("items", 10, items)
        self.assertEqual(len(slices), 4)
        self._assert_disjoint_and_exhaustive(slices, items)

    def test_no_atom_appears_in_two_slices(self):
        items = list(range(1, 21))
        slices = shard_task.split_shards("ranges", 6, (1, 20))
        all_items = []
        for s in slices:
            all_items.extend(s["items"])
        # A naive round-robin-without-dedupe or overlapping-window bug would
        # produce duplicates here.
        self.assertEqual(len(all_items), len(set(all_items)))
        self.assertEqual(sorted(all_items), items)

    def test_ranges_source_contiguous_disjoint_exhaustive(self):
        slices = shard_task.split_shards("ranges", 3, (1, 10))
        self._assert_disjoint_and_exhaustive(slices, list(range(1, 11)))
        # Contiguous: each slice's items are a consecutive run.
        for s in slices:
            items = s["items"]
            if len(items) > 1:
                self.assertEqual(items, list(range(items[0], items[0] + len(items))))


class TestDeterminism(unittest.TestCase):
    """Clause 1: same inputs -> identical slices, every run. No
    Date.now/random -- proven with a literal double-run-identical
    assertion, including through the glob resolution path where raw
    directory-enumeration order is not itself guaranteed stable."""

    def test_double_run_identical_for_items(self):
        items = [f"x{i}" for i in range(9)]
        first = shard_task.split_shards("items", 4, items)
        second = shard_task.split_shards("items", 4, items)
        self.assertEqual(first, second)

    def test_double_run_identical_for_ranges(self):
        first = shard_task.split_shards("ranges", 5, (1, 37))
        second = shard_task.split_shards("ranges", 5, (1, 37))
        self.assertEqual(first, second)

    def test_double_run_identical_through_glob_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(tmp, "a.py", "b.py", "c.py", "d.py", "e.py")
            pattern = str(pathlib.Path(tmp) / "*.py")
            first = shard_task.split_shards("files", 3, pattern)
            second = shard_task.split_shards("files", 3, pattern)
            self.assertEqual(first, second)
            # And a third call built independently (fresh glob call) still
            # agrees -- not just object/list identity.
            third = shard_task.split_shards("files", 3, [pattern])
            self.assertEqual(first, third)


class TestFilesAndItemsSource(unittest.TestCase):
    """Clause 2: files/items sources are inline-list or glob ONLY."""

    def test_inline_list_of_literal_paths(self):
        slices = shard_task.split_shards("files", 2, ["z.py", "a.py", "m.py"])
        all_items = [i for s in slices for i in s["items"]]
        self.assertEqual(sorted(all_items), ["a.py", "m.py", "z.py"])

    def test_glob_pattern_string_resolves_matching_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _touch(tmp, "one.txt", "two.txt", "three.txt")
            pattern = str(pathlib.Path(tmp) / "*.txt")
            slices = shard_task.split_shards("files", 2, pattern)
            all_items = [i for s in slices for i in s["items"]]
            self.assertEqual(sorted(all_items), sorted(paths))

    def test_items_source_inline_list_non_path_strings(self):
        # "items" need not be filesystem paths at all -- plain literal
        # strings pass through untouched.
        slices = shard_task.split_shards("items", 2, ["test_a", "test_b", "test_c"])
        all_items = sorted(i for s in slices for i in s["items"])
        self.assertEqual(all_items, ["test_a", "test_b", "test_c"])


class TestDegenerateCases(unittest.TestCase):
    """Clause 2: empty or single-item enumeration -> ONE slice, never an
    error."""

    def test_empty_inline_list_yields_one_slice_not_error(self):
        slices = shard_task.split_shards("files", 5, [])
        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0]["items"], [])
        self.assertEqual(slices[0]["index"], 1)

    def test_single_item_yields_one_slice_regardless_of_max_shards(self):
        slices = shard_task.split_shards("items", 8, ["only-one"])
        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0]["items"], ["only-one"])

    def test_empty_glob_match_yields_one_slice_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            pattern = str(pathlib.Path(tmp) / "*.nonexistent")
            slices = shard_task.split_shards("files", 4, pattern)
            self.assertEqual(len(slices), 1)
            self.assertEqual(slices[0]["items"], [])


class TestOverlapDedupe(unittest.TestCase):
    """Clause 3: overlapping globs resolving one path into two slices ->
    dedupe deterministically so each resolved item lands in exactly one
    slice."""

    def test_overlapping_globs_each_path_lands_in_exactly_one_slice(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _touch(tmp, "alpha.py", "beta.py", "gamma.py")
            broad = str(pathlib.Path(tmp) / "*.py")
            narrow = str(pathlib.Path(tmp) / "alpha.py")
            # `narrow` is a literal path (not a glob pattern) that also
            # happens to be matched by `broad` -- the classic overlap case.
            slices = shard_task.split_shards("files", 2, [broad, narrow])
            all_items = [i for s in slices for i in s["items"]]
            # No duplicate: alpha.py must not appear twice even though it
            # was named by both entries.
            self.assertEqual(len(all_items), len(set(all_items)))
            self.assertEqual(sorted(all_items), sorted(paths))

    def test_two_overlapping_glob_patterns_dedupe(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _touch(tmp, "report_a.csv", "report_b.csv", "summary.csv")
            pattern_1 = str(pathlib.Path(tmp) / "report_*.csv")
            pattern_2 = str(pathlib.Path(tmp) / "*.csv")  # overlaps pattern_1 entirely
            slices = shard_task.split_shards("files", 3, [pattern_1, pattern_2])
            all_items = [i for s in slices for i in s["items"]]
            self.assertEqual(sorted(all_items), sorted(paths))
            self.assertEqual(len(all_items), 3)

    def test_dedupe_is_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _touch(tmp, "x1.log", "x2.log")
            pattern_1 = str(pathlib.Path(tmp) / "x1.log")
            pattern_2 = str(pathlib.Path(tmp) / "x*.log")
            first = shard_task.split_shards("files", 2, [pattern_1, pattern_2])
            second = shard_task.split_shards("files", 2, [pattern_1, pattern_2])
            self.assertEqual(first, second)


class TestIndexableOutput(unittest.TestCase):
    """Clause 4: slices emit as a stable, indexable list so the kernel can
    label swarm members #1..#N by slice index."""

    def test_indices_are_1_based_and_contiguous(self):
        slices = shard_task.split_shards("items", 4, [f"i{i}" for i in range(10)])
        self.assertEqual([s["index"] for s in slices], list(range(1, len(slices) + 1)))

    def test_result_is_a_plain_list(self):
        slices = shard_task.split_shards("items", 3, ["a", "b", "c", "d", "e"])
        self.assertIsInstance(slices, list)
        for s in slices:
            self.assertIsInstance(s, dict)
            self.assertIn("index", s)
            self.assertIn("items", s)

    def test_index_matches_list_position_plus_one(self):
        slices = shard_task.split_shards("items", 5, [f"v{i}" for i in range(12)])
        for position, s in enumerate(slices):
            self.assertEqual(s["index"], position + 1)

    def test_degenerate_single_slice_is_indexable_too(self):
        slices = shard_task.split_shards("items", 5, ["solo"])
        self.assertEqual(slices[0]["index"], 1)


class TestInvalidMaxShards(unittest.TestCase):
    """Defensive: max_shards must be an int >= 2 (T1/fg-a10811 owns the
    frontmatter-level validation; this is a belt-and-suspenders guard so the
    splitter never silently mis-chunks on bad input)."""

    def test_max_shards_below_two_raises(self):
        with self.assertRaises(shard_task.ShardError):
            shard_task.split_shards("items", 1, ["a", "b"])

    def test_max_shards_non_int_raises(self):
        with self.assertRaises(shard_task.ShardError):
            shard_task.split_shards("items", "3", ["a", "b"])


class TestNegativeRangeStringForm(unittest.TestCase):
    """The string form "start-end" must handle a negative start the same
    way the tuple form does -- "-" is ambiguously both the sign and the
    separator, so a naive `str.split("-", 1)` can never represent a
    negative start. A regex that captures an optional leading "-" on each
    number fixes this."""

    def test_negative_start_string_form_matches_tuple_form(self):
        string_form = shard_task.split_shards("ranges", 3, "-5-3")
        tuple_form = shard_task.split_shards("ranges", 3, (-5, 3))
        self.assertEqual(string_form, tuple_form)

    def test_negative_start_and_end_string_form_resolves_correctly(self):
        result = shard_task._resolve_range("-10--3")
        self.assertEqual(result, list(range(-10, -2)))

    def test_still_rejects_genuinely_malformed_range_string(self):
        with self.assertRaises(shard_task.ShardError):
            shard_task._resolve_range("not-a-range")


class TestLiteralPathWithGlobMetacharacterNeverSilentlyDropped(unittest.TestCase):
    """A literal filename containing a glob metacharacter (most commonly
    "[", which glob.glob() interprets as a one-character class rather than
    a literal substring) must not silently vanish from the resolved atom
    set just because glob.glob() finds no pattern matches for it."""

    def test_bracketed_literal_filename_recovered_when_glob_finds_no_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            literal_name = "report[2026].csv"
            _touch(tmp, literal_name)
            literal_path = str(pathlib.Path(tmp) / literal_name)
            slices = shard_task.split_shards("files", 2, [literal_path])
            all_items = [i for s in slices for i in s["items"]]
            self.assertEqual(all_items, [literal_path])

    def test_unresolvable_bracket_shaped_item_raises_shard_error_not_silent_drop(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No file by this literal name exists, and the glob (a
            # one-character class matching none of "2026"'s chars against
            # nothing in an empty dir) matches nothing either -- genuinely
            # unresolvable, must raise rather than silently vanish.
            unresolved = str(pathlib.Path(tmp) / "report[2026].csv")
            with self.assertRaises(shard_task.ShardError):
                shard_task.split_shards("files", 2, [unresolved])

    def test_genuine_wildcard_matching_nothing_still_yields_empty_not_error(self):
        # A real "*"/"?" wildcard search that matches nothing is still a
        # legitimate empty result (EARS clause 2: empty enumeration is
        # never an error) -- must not be swept up by the new raise path.
        with tempfile.TemporaryDirectory() as tmp:
            pattern = str(pathlib.Path(tmp) / "*.nonexistent")
            slices = shard_task.split_shards("files", 4, pattern)
            self.assertEqual(len(slices), 1)
            self.assertEqual(slices[0]["items"], [])


class TestUnknownShardBy(unittest.TestCase):
    def test_unknown_shard_by_raises(self):
        with self.assertRaises(shard_task.ShardError):
            shard_task.split_shards("bogus", 3, ["a", "b"])


class TestCli(unittest.TestCase):
    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "shard_task.py"), *args],
            capture_output=True, text=True,
        )

    def test_cli_multiple_shard_key_args_and_exits_zero(self):
        result = self._run(["items", "2", "a", "b", "c"])
        self.assertEqual(result.returncode, 0)
        self.assertIn('"index": 1', result.stdout)

    def test_cli_invalid_max_shards_exits_nonzero(self):
        result = self._run(["items", "1", "a", "b"])
        self.assertEqual(result.returncode, 1)

    def test_cli_non_numeric_max_shards_exits_cleanly_not_a_traceback(self):
        # int("abc") raises ValueError, not ShardError -- before the fix
        # this propagated uncaught out of main() and crashed the CLI with a
        # raw traceback instead of the documented clean "error: ..." + exit
        # 1 shape every other invalid-input path uses.
        result = self._run(["items", "abc", "a", "b"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
