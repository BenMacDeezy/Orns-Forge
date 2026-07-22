"""Tests for tools/benchmark/blinding.py (fg-a10404, benchmark T4).

Design ref (docs/plans/2026-07-18-ab-benchmark-design.md, cited not
restated): D5 "Blinded audit: normalize -> shuffle -> sealed key; checklist
frozen at design time", mechanisms 1 (diff normalization) and 2 (label
shuffling + sealed key). Human's 2026-07-18 binding answer to design open
question 3: blinding = accept-and-disclose -- no formatter pass, so these
tests only assert fingerprint-freedom + code-byte-identity, never a
canonicalized/reformatted diff.

Fixtures are inline unified-diff strings mirroring what
tools/benchmark/runner.py's capture_diff() produces (plain `git diff`
output, "diff --git a/... b/..." blocks) per tools/benchmark/test_runner.py,
plus a couple of fixtures with a commit-message preamble and trailer to
prove the normalizer also handles the `git log -p` shape D5 describes
("commit messages", "co-author trailers") -- capture_diff's exact shape is
runner.py's call (T3, out of this task's file ownership), so blinding.py
must not assume away either form.

Bounce 1 (verify FAIL, JUDGMENT) widened this fixture and the fingerprint
term list to the telemetry-recognized grammar a de-blind attack actually
exploited: TIER_RE tokens (`sonnet/high`), VERDICT_RE (`PASS`, including
`PASS-after-filter`), TAG_RE (`MECHANICAL`/`JUDGMENT`), JUDGE_YIELD_RE
lines, free-standing verify/verdict/bounce/judge prose, and an in-comment
`.forge/...` path mention (not just the fg-id embedded in it).
"""
import json
import pathlib
import tempfile
import unittest

from blinding import (
    SEALED_KEY_DIR,
    _neutralize,
    make_label,
    normalize_diff,
    normalize_tree,
    shuffle_pair,
    write_sealed_key,
)


_FORGE_FINGERPRINTED_DIFF = """\
Fix rounding per fg-a10404 (attempt 2 verify: sonnet/high -> PASS. \
WHEN this task runs, THE SYSTEM SHALL conserve the total. The verifier \
should have caught this on attempt 1 via bounce (MECHANICAL). \
judge-yield: forge-reviewer raised=2 survived=1 changed=1)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

diff --git a/src/ledgerkit/money.py b/src/ledgerkit/money.py
index abc123..def456 100644
--- a/src/ledgerkit/money.py
+++ b/src/ledgerkit/money.py
@@ -10,7 +10,10 @@ def split_evenly(total_cents, num_parts):
     share, remainder = divmod(total_cents, num_parts)
     shares = [share] * num_parts
-    return shares
+    # fg-a10404: distribute remainder per forge-verifier Brokk's fix; see
+    # .forge/queue/tasks/fg-a10404-benchmark.md for the task record
+    for i in range(remainder):
+        shares[i] += 1
+    account_name = "Rune Checking"
+    return shares
diff --git a/.forge/queue/tasks/fg-a10404-benchmark.md b/.forge/queue/tasks/fg-a10404-benchmark.md
index 111..222 100644
--- a/.forge/queue/tasks/fg-a10404-benchmark.md
+++ b/.forge/queue/tasks/fg-a10404-benchmark.md
@@ -1,3 +1,3 @@
-state: ready
+state: done
 title: "Benchmark T4"
"""

_FORGE_FINGERPRINT_TERMS = [
    "fg-a10404",
    "forge-verifier",
    "Brokk",
    "THE SYSTEM SHALL",
    "Co-Authored-By",
    "sonnet/high",
    "PASS",
    ".forge/",
    "verifier",
    "bounce",
    "MECHANICAL",
    "judge-yield",
    "raised=2",
]


class TestNormalizeDiffStripsFingerprints(unittest.TestCase):
    def setUp(self):
        self.out = normalize_diff(_FORGE_FINGERPRINTED_DIFF)

    def test_no_fingerprint_term_survives(self):
        for term in _FORGE_FINGERPRINT_TERMS:
            self.assertNotIn(term, self.out, f"fingerprint term leaked: {term!r}")

    def test_forge_dir_hunk_dropped_entirely(self):
        self.assertNotIn(".forge/", self.out)
        self.assertNotIn("state: ready", self.out)
        self.assertNotIn("state: done", self.out)

    def test_code_hunk_lines_stay_byte_identical(self):
        # Every real code/context line -- no fingerprint, no comment -- must
        # survive untouched, proving the normalizer strips metadata and
        # never alters semantics (D5 mechanism 1).
        self.assertIn(
            "     share, remainder = divmod(total_cents, num_parts)", self.out
        )
        self.assertIn("     shares = [share] * num_parts", self.out)
        self.assertIn("-    return shares", self.out)
        self.assertIn("+    for i in range(remainder):", self.out)
        self.assertIn("+        shares[i] += 1", self.out)
        self.assertIn("+    return shares", self.out)

    def test_non_comment_code_containing_a_persona_word_is_untouched(self):
        # "Rune" is a roster persona name (fg-9f0101) but also appears here
        # as an ordinary string literal in real code, not a comment. Persona
        # stripping must be scoped to comments/metadata only, or this line
        # would be mangled and the "never alters semantics" guarantee broken.
        self.assertIn('+    account_name = "Rune Checking"', self.out)

    def test_fingerprinted_comment_line_is_neutralized_not_left_verbatim(self):
        self.assertNotIn(
            "# fg-a10404: distribute remainder per forge-verifier Brokk's fix",
            self.out,
        )

    def test_in_comment_forge_path_mention_fully_stripped(self):
        # Not just the fg-id embedded in the path (bounce 1, finding 2) --
        # the whole ".forge/queue/tasks/" prefix must be gone too.
        self.assertNotIn(".forge/queue/tasks", self.out)

    def test_in_comment_forge_path_mention_backslash_form_fully_stripped(self):
        # Bounce 2 (MECHANICAL): _FORGE_PATH_RE originally accepted only
        # forward slashes, leaving a Windows-style ".forge\queue\tasks\..."
        # reference unstripped -- this repo lives at D:\forge, so a
        # backslash-form comment is just as realistic as the POSIX form.
        out = _neutralize(r"# see .forge\queue\tasks\fg-a10404.md for the record")
        self.assertNotIn(".forge\\queue\\tasks", out)
        self.assertNotIn(".forge\\", out)


class TestNeutralizeTelemetryGrammar(unittest.TestCase):
    """Direct _neutralize() coverage for the exact telemetry-recognized
    token classes bounce 1 named: TIER_RE, VERDICT_RE (+PASS-after-filter),
    TAG_RE, JUDGE_YIELD_RE, and free-standing verify/verdict/bounce/judge
    vocabulary outside the strict Attempt-log grammar.
    """

    def test_verifier_repro_from_bounce_1(self):
        # The exact repro command from the bounce report, run through the
        # public API instead of a subprocess -- must emit no surviving
        # fingerprint term.
        out = _neutralize(
            "# the verifier should have caught this via bounce; "
            "sonnet/high -> PASS"
        )
        for term in ("verifier", "bounce", "sonnet/high", "PASS"):
            self.assertNotIn(term, out, f"fingerprint term leaked: {term!r}")

    def test_tier_token_stripped(self):
        for tier in ("haiku/low", "sonnet/high", "opus/medium", "fable/high"):
            out = _neutralize(f"# routed at {tier} per the router")
            self.assertNotIn(tier, out)

    def test_verdict_tokens_stripped(self):
        for verdict in ("PASS", "FAIL", "ESCALATE"):
            out = _neutralize(f"# outcome: {verdict}")
            self.assertNotIn(verdict, out)

    def test_pass_after_filter_stripped_without_stray_remainder(self):
        out = _neutralize("# verdict: PASS-after-filter (finding filtered)")
        self.assertNotIn("PASS-after-filter", out)
        self.assertNotIn("PASS", out)
        self.assertNotIn("-after-filter", out)

    def test_tag_tokens_stripped(self):
        for tag in ("MECHANICAL", "JUDGMENT"):
            out = _neutralize(f"# bounce reason tag: {tag}")
            self.assertNotIn(tag, out)

    def test_judge_yield_line_stripped(self):
        out = _neutralize(
            "judge-yield: forge-reviewer raised=2 survived=1 changed=1"
        )
        self.assertNotIn("judge-yield", out)
        self.assertNotIn("raised=2", out)
        self.assertNotIn("forge-reviewer", out)

    def test_free_standing_verify_vocabulary_stripped(self):
        out = _neutralize(
            "# the verifier re-verified this and the verdict held after bouncing"
        )
        for term in ("verifier", "re-verified", "verdict", "bouncing"):
            self.assertNotIn(term, out)

    def test_placeholder_tokens_do_not_collide_across_passes(self):
        # Regression for the bounce-1-fix bug caught during self-review:
        # inserting "[verdict]"/"[judge-yield]" as placeholders got
        # re-matched by a later pass (_VOCAB_RE's "verdict"/"judge"
        # entries), double-bracketing to "[[vocab]]". No placeholder this
        # pipeline emits may itself contain a word a later regex flags.
        out = _neutralize("judge-yield: forge-worker raised=1 survived=1 changed=1; PASS")
        self.assertNotIn("[[", out)
        self.assertNotIn("]]", out)


class TestNormalizeDiffEdgeCases(unittest.TestCase):
    def test_empty_string_passthrough(self):
        self.assertEqual(normalize_diff(""), "")

    def test_none_passthrough(self):
        self.assertIsNone(normalize_diff(None))

    def test_plain_diff_with_no_preamble_or_forge_content_is_unchanged_apart_from_scrub(self):
        diff = (
            "diff --git a/a.txt b/a.txt\n"
            "index 1..2 100644\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-base\n"
            "+modified\n"
        )
        out = normalize_diff(diff)
        self.assertIn("-base", out)
        self.assertIn("+modified", out)
        self.assertIn("diff --git a/a.txt b/a.txt", out)

    def test_idempotent(self):
        once = normalize_diff(_FORGE_FINGERPRINTED_DIFF)
        twice = normalize_diff(once)
        self.assertEqual(once, twice)

    def test_branch_header_line_dropped(self):
        diff = (
            "Branch: bench/wt/B1/armA/run7\n\n"
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-x\n"
            "+y\n"
        )
        out = normalize_diff(diff)
        self.assertNotIn("bench/wt", out)
        self.assertNotIn("Branch:", out)

    def test_inline_run_path_neutralized_but_surrounding_text_kept(self):
        diff = (
            "see bench/wt/B1/armA/run7 for the run artifacts\n\n"
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-x\n"
            "+y\n"
        )
        out = normalize_diff(diff)
        self.assertNotIn("bench/wt", out)
        self.assertIn("see", out)
        self.assertIn("for the run artifacts", out)


class TestNormalizeTree(unittest.TestCase):
    def test_drops_forge_dir_files(self):
        files = {
            "src/ledgerkit/money.py": "x = 1\n",
            ".forge/queue/tasks/fg-a10404-benchmark.md": "state: done\n",
        }
        out = normalize_tree(files)
        self.assertIn("src/ledgerkit/money.py", out)
        self.assertNotIn(".forge/queue/tasks/fg-a10404-benchmark.md", out)

    def test_scrubs_comment_leaves_code_identical(self):
        files = {
            "src/ledgerkit/money.py": (
                "def split_evenly(total_cents, num_parts):\n"
                "    # fg-a10404 per forge-verifier: fixed by Brokk\n"
                "    account_name = \"Rune Checking\"\n"
                "    return total_cents\n"
            )
        }
        out = normalize_tree(files)["src/ledgerkit/money.py"]
        self.assertNotIn("fg-a10404", out)
        self.assertNotIn("forge-verifier", out)
        self.assertIn("def split_evenly(total_cents, num_parts):", out)
        self.assertIn('    account_name = "Rune Checking"', out)
        self.assertIn("    return total_cents", out)


class TestMakeLabel(unittest.TestCase):
    def test_deterministic_for_same_inputs(self):
        self.assertEqual(
            make_label("B1", "A", "seed-1"), make_label("B1", "A", "seed-1")
        )

    def test_varies_with_arm(self):
        self.assertNotEqual(
            make_label("B1", "A", "seed-1"), make_label("B1", "B", "seed-1")
        )

    def test_varies_with_seed(self):
        self.assertNotEqual(
            make_label("B1", "A", "seed-1"), make_label("B1", "A", "seed-2")
        )

    def test_opaque_format(self):
        label = make_label("B1", "A", "seed-1")
        self.assertTrue(label.startswith("diff-"))
        self.assertNotIn("B1", label)
        self.assertNotIn("A", label)


class TestShufflePair(unittest.TestCase):
    def test_deterministic_for_same_seed(self):
        p1, k1 = shuffle_pair("B1", "diff-a-text", "diff-b-text", "seed-1")
        p2, k2 = shuffle_pair("B1", "diff-a-text", "diff-b-text", "seed-1")
        self.assertEqual(p1, p2)
        self.assertEqual(k1, k2)

    def test_presented_pair_carries_no_arm_identity(self):
        presented, _sealed = shuffle_pair("B1", "diff-a-text", "diff-b-text", "seed-1")
        self.assertEqual(len(presented), 2)
        for entry in presented:
            self.assertEqual(len(entry), 2)  # (label, diff) only -- no arm field

    def test_sealed_key_maps_labels_back_to_correct_arm_and_content(self):
        presented, sealed = shuffle_pair("B1", "diff-a-text", "diff-b-text", "seed-1")
        presented_map = dict(presented)
        for label, meta in sealed.items():
            self.assertEqual(meta["task"], "B1")
            self.assertIn(meta["arm"], ("A", "B"))
            expected_source = "diff-a-text" if meta["arm"] == "A" else "diff-b-text"
            self.assertEqual(presented_map[label], normalize_diff(expected_source))

    def test_order_is_not_hardcoded_across_seeds(self):
        # If shuffle_pair always presented arm A first, this would only ever
        # see one order across a spread of seeds -- prove genuine
        # randomization, not a fixed order dressed up as "shuffled".
        orders = set()
        for seed in range(30):
            presented, sealed = shuffle_pair("B1", "diff-a-text", "diff-b-text", seed)
            arms_in_order = tuple(sealed[label]["arm"] for label, _diff in presented)
            orders.add(arms_in_order)
        self.assertEqual(orders, {("A", "B"), ("B", "A")})


class TestWriteSealedKey(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base_dir = pathlib.Path(self._tmp.name) / "sealed"

    def test_writes_valid_json_readable_back(self):
        _presented, sealed = shuffle_pair("B1", "diff-a-text", "diff-b-text", "seed-1")
        path = write_sealed_key("run7", sealed, base_dir=self.base_dir)
        self.assertTrue(path.exists())
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk, sealed)

    def test_path_is_runid_scoped(self):
        _presented, sealed = shuffle_pair("B1", "diff-a-text", "diff-b-text", "seed-1")
        path = write_sealed_key("run7", sealed, base_dir=self.base_dir)
        self.assertEqual(path.name, "run7.sealed.json")

    def test_second_pair_merges_rather_than_clobbers(self):
        _p1, sealed1 = shuffle_pair("B1", "diff-a-text", "diff-b-text", "seed-1")
        _p2, sealed2 = shuffle_pair("F1", "diff-c-text", "diff-d-text", "seed-1")
        write_sealed_key("run7", sealed1, base_dir=self.base_dir)
        path = write_sealed_key("run7", sealed2, base_dir=self.base_dir)
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        for label in sealed1:
            self.assertIn(label, on_disk)
        for label in sealed2:
            self.assertIn(label, on_disk)


class TestSealedKeyDenyPath(unittest.TestCase):
    def test_default_sealed_key_dir_is_the_documented_t7_deny_path(self):
        # T7 (blinded-audit harness) must deny exactly this path from the
        # auditor spawn contract (D5: "the auditor spawn's contract
        # excludes that path"). Pinning the literal string here means a
        # future edit to SEALED_KEY_DIR without updating T7's denylist shows
        # up as a failing pin, not a silent blinding leak.
        self.assertEqual(SEALED_KEY_DIR, "tools/benchmark/sealed")


if __name__ == "__main__":
    unittest.main()
