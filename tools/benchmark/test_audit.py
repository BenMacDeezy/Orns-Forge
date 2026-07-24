"""Tests for tools/benchmark/audit.py (fg-a10407, benchmark T7: blinded-audit
harness).

Design ref (docs/plans/2026-07-18-ab-benchmark-design.md, cited not
restated): D5 "Blinded audit: normalize -> shuffle -> sealed key; checklist
frozen at design time", specifically the blinded-auditor consumption half --
"the blinded auditor... receives only: the frozen checklist, the normalized
labeled diffs, and the fixture base... Arm identity is joined back in by
script *after* the auditor's scores are committed."

Three responsibilities under test, matching audit.py's three exports:
  1. build_audit_packet()      -- packaging + two loud-error guards (tamper
                                   check on the checklist hash, fingerprint
                                   tripwire on the presentations).
  2. BlindedScoreLedger.record_scores() -- label-keyed accumulation with
                                   structural score validation.
  3. BlindedScoreLedger.unseal()        -- the only key-reading step, with
                                   the two ordering guards D5 requires
                                   (coverage-before-open, freeze-after-open).
  4. A real metrics.build_pair_rows() round trip through glue.flatten_pair_record,
     proving the unsealed output is genuinely metrics-compatible.

Fixtures use the real, already-frozen tools/benchmark/ground-truth/checklists/
B1.checklist.json so the hash-verification tests exercise the actual frozen
content_sha256 rather than a hand-rolled stand-in, and blinding.shuffle_pair
for the packet-building happy path so the fingerprint tripwire tests run
against genuinely normalized output, not a hand-simulated approximation.
"""
import copy
import json
import pathlib
import tempfile
import unittest

from audit import (
    AuditError,
    BlindedScoreLedger,
    build_audit_packet,
    checklist_content_hash,
    verify_checklist_integrity,
)
from blinding import normalize_diff, shuffle_pair, write_sealed_key
from glue import flatten_pair_record
from metrics import build_pair_rows

_CHECKLIST_DIR = pathlib.Path(__file__).parent / "ground-truth" / "checklists"


def _load_checklist(task_id):
    path = _CHECKLIST_DIR / f"{task_id}.checklist.json"
    return json.loads(path.read_text(encoding="utf-8"))


_RAW_DIFF_A = """\
Fix rounding per fg-a10404 (attempt 2 verify: sonnet/high -> PASS)

diff --git a/src/ledgerkit/money.py b/src/ledgerkit/money.py
index abc123..def456 100644
--- a/src/ledgerkit/money.py
+++ b/src/ledgerkit/money.py
@@ -10,7 +10,10 @@ def split_evenly(total_cents, num_parts):
     share, remainder = divmod(total_cents, num_parts)
     shares = [share] * num_parts
-    return shares
+    for i in range(remainder):
+        shares[i] += 1
+    return shares
"""

_RAW_DIFF_B = """\
diff --git a/src/ledgerkit/money.py b/src/ledgerkit/money.py
index abc123..999999 100644
--- a/src/ledgerkit/money.py
+++ b/src/ledgerkit/money.py
@@ -10,7 +10,11 @@ def split_evenly(total_cents, num_parts):
     share, remainder = divmod(total_cents, num_parts)
     shares = [share] * num_parts
-    return shares
+    i = 0
+    while i < remainder:
+        shares[i] += 1
+        i += 1
+    return shares
"""


def _satisfied_results(checklist):
    return [{"item_id": item["item_id"], "status": "satisfied", "severity": None}
            for item in checklist["items"]]


# ---------------------------------------------------------------------------
# build_audit_packet
# ---------------------------------------------------------------------------

class TestBuildAuditPacket(unittest.TestCase):
    def setUp(self):
        self.checklist = _load_checklist("B1")
        presented, self.sealed_key = shuffle_pair("B1", _RAW_DIFF_A, _RAW_DIFF_B, seed=7)
        self.presentations = presented

    def test_returns_expected_shape(self):
        packet = build_audit_packet("B1", self.presentations, self.checklist)
        self.assertEqual(packet["task_id"], "B1")
        self.assertIsInstance(packet["instructions"], str)
        self.assertTrue(packet["instructions"])
        self.assertEqual(len(packet["presentations"]), 2)
        for entry in packet["presentations"]:
            self.assertIn("label", entry)
            self.assertIn("diff", entry)
        self.assertEqual(len(packet["checklist_items"]), len(self.checklist["items"]))

    def test_checklist_items_carry_only_scoring_fields(self):
        packet = build_audit_packet("B1", self.presentations, self.checklist)
        for item in packet["checklist_items"]:
            self.assertEqual(
                set(item.keys()), {"item_id", "description", "how_to_detect", "severity"}
            )

    def test_presentations_carry_no_arm_identity(self):
        packet = build_audit_packet("B1", self.presentations, self.checklist)
        packaged_labels = {e["label"] for e in packet["presentations"]}
        self.assertEqual(packaged_labels, set(self.sealed_key.keys()))
        # the packet itself is never handed the sealed key
        self.assertNotIn("sealed_key", packet)
        self.assertNotIn("arm", json.dumps(packet["presentations"]))

    def test_raises_on_checklist_hash_tamper(self):
        tampered = copy.deepcopy(self.checklist)
        tampered["items"][0]["description"] = "a different description now"
        with self.assertRaises(AuditError):
            build_audit_packet("B1", self.presentations, tampered)

    def test_raises_on_checklist_missing_hash(self):
        no_hash = copy.deepcopy(self.checklist)
        del no_hash["content_sha256"]
        with self.assertRaises(AuditError):
            build_audit_packet("B1", self.presentations, no_hash)

    def test_raises_on_task_id_mismatch(self):
        with self.assertRaises(AuditError):
            build_audit_packet("B3", self.presentations, self.checklist)

    def test_raises_on_duplicate_labels(self):
        dup = [self.presentations[0], self.presentations[0]]
        with self.assertRaises(AuditError):
            build_audit_packet("B1", dup, self.checklist)

    def test_raises_on_fewer_than_two_presentations(self):
        with self.assertRaises(AuditError):
            build_audit_packet("B1", self.presentations[:1], self.checklist)

    def test_raises_on_surviving_fg_id_fingerprint(self):
        # raw, un-normalized diff text sneaking through -- the tripwire.
        raw_presentations = [("diff-raw1", _RAW_DIFF_A), ("diff-raw2", _RAW_DIFF_B)]
        with self.assertRaises(AuditError):
            build_audit_packet("B1", raw_presentations, self.checklist)

    def test_raises_on_surviving_forge_path_fingerprint(self):
        tainted = normalize_diff(_RAW_DIFF_A) + "\n# see .forge/queue/tasks/fg-x.md\n"
        # strip the fg-id itself so only the .forge/ path pattern remains
        tainted = tainted.replace("fg-x", "task")
        presentations = [("diff-a", tainted), ("diff-b", normalize_diff(_RAW_DIFF_B))]
        with self.assertRaises(AuditError):
            build_audit_packet("B1", presentations, self.checklist)

    def test_normalized_placeholder_tokens_do_not_trip_the_tripwire(self):
        # normalize_diff's own placeholder tokens (e.g. "[task-ref]") must
        # never themselves be treated as a surviving fingerprint.
        packet = build_audit_packet("B1", self.presentations, self.checklist)
        for entry in packet["presentations"]:
            self.assertNotIn("fg-a10404", entry["diff"])


# ---------------------------------------------------------------------------
# checklist_content_hash / verify_checklist_integrity
# ---------------------------------------------------------------------------

class TestChecklistIntegrity(unittest.TestCase):
    def test_hash_matches_frozen_value_for_every_shipped_checklist(self):
        for path in sorted(_CHECKLIST_DIR.glob("*.checklist.json")):
            checklist = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                checklist_content_hash(checklist), checklist["content_sha256"],
                f"{path.name}: recomputed hash does not match stored content_sha256",
            )

    def test_verify_passes_silently_on_untampered_checklist(self):
        verify_checklist_integrity(_load_checklist("B1"))  # must not raise

    def test_verify_raises_on_tampered_severity(self):
        tampered = _load_checklist("B1")
        tampered["items"][0]["severity"] = "minor"
        with self.assertRaises(AuditError):
            verify_checklist_integrity(tampered)


# ---------------------------------------------------------------------------
# BlindedScoreLedger.record_scores
# ---------------------------------------------------------------------------

class TestRecordScores(unittest.TestCase):
    def setUp(self):
        self.ledger = BlindedScoreLedger(run_id="bench-run-1")
        self.checklist = _load_checklist("B1")

    def test_accumulates_by_label(self):
        scores = self.ledger.record_scores("diff-aaaa", _satisfied_results(self.checklist))
        self.assertIn("diff-aaaa", scores)
        scores2 = self.ledger.record_scores("diff-bbbb", _satisfied_results(self.checklist))
        self.assertEqual(set(scores2.keys()), {"diff-aaaa", "diff-bbbb"})

    def test_rejects_unknown_status(self):
        with self.assertRaises(AuditError):
            self.ledger.record_scores(
                "diff-aaaa", [{"item_id": "B1-C1", "status": "bogus", "severity": None}]
            )

    def test_rejects_defect_present_without_valid_severity(self):
        with self.assertRaises(AuditError):
            self.ledger.record_scores(
                "diff-aaaa",
                [{"item_id": "B1-C1", "status": "defect-present", "severity": None}],
            )

    def test_accepts_defect_present_with_valid_severity(self):
        self.ledger.record_scores(
            "diff-aaaa",
            [{"item_id": "B1-C1", "status": "defect-present", "severity": "critical"}],
        )  # must not raise

    def test_rejects_additional_defect_without_valid_severity(self):
        with self.assertRaises(AuditError):
            self.ledger.record_scores(
                "diff-aaaa", _satisfied_results(self.checklist),
                additional_defects=[{"description": "surprise bug", "severity": "extreme"}],
            )

    def test_rejects_recording_after_unseal_for_same_run_id(self):
        self.ledger.record_scores("diff-aaaa", _satisfied_results(self.checklist))
        self.ledger.record_scores("diff-bbbb", _satisfied_results(self.checklist))
        with tempfile.TemporaryDirectory() as tmp:
            key_path = pathlib.Path(tmp) / "bench-run-1.sealed.json"
            key_path.write_text(json.dumps({
                "diff-aaaa": {"task": "B1", "arm": "A"},
                "diff-bbbb": {"task": "B1", "arm": "B"},
            }), encoding="utf-8")
            self.ledger.unseal(key_path, run_ids_by_task={"B1": "pairrun-1"})

        with self.assertRaises(AuditError):
            self.ledger.record_scores("diff-cccc", _satisfied_results(self.checklist))


# ---------------------------------------------------------------------------
# BlindedScoreLedger.unseal
# ---------------------------------------------------------------------------

class TestUnseal(unittest.TestCase):
    def setUp(self):
        self.checklist = _load_checklist("B1")
        self.ledger = BlindedScoreLedger(run_id="bench-run-1")

    def _write_key(self, tmp, mapping):
        path = pathlib.Path(tmp) / "bench-run-1.sealed.json"
        path.write_text(json.dumps(mapping), encoding="utf-8")
        return path

    def test_refuses_when_a_keyed_label_has_no_recorded_score(self):
        self.ledger.record_scores("diff-aaaa", _satisfied_results(self.checklist))
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._write_key(tmp, {
                "diff-aaaa": {"task": "B1", "arm": "A"},
                "diff-bbbb": {"task": "B1", "arm": "B"},  # never scored
            })
            with self.assertRaises(AuditError):
                self.ledger.unseal(key_path, run_ids_by_task={"B1": "pairrun-1"})

    def test_produces_arm_attributed_metrics_compatible_records(self):
        self.ledger.record_scores("diff-aaaa", _satisfied_results(self.checklist))
        self.ledger.record_scores("diff-bbbb", _satisfied_results(self.checklist))
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._write_key(tmp, {
                "diff-aaaa": {"task": "B1", "arm": "A"},
                "diff-bbbb": {"task": "B1", "arm": "B"},
            })
            records = self.ledger.unseal(key_path, run_ids_by_task={"B1": "pairrun-1"})

        by_arm = {r["arm"]: r for r in records}
        self.assertEqual(by_arm["A"]["task_id"], "B1")
        self.assertEqual(by_arm["A"]["run_id"], "pairrun-1-A")
        self.assertEqual(by_arm["B"]["run_id"], "pairrun-1-B")
        for r in records:
            self.assertIn("checklist_results", r)
            self.assertIn("additional_defects", r)

    def test_refuses_second_unseal_call(self):
        self.ledger.record_scores("diff-aaaa", _satisfied_results(self.checklist))
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._write_key(tmp, {"diff-aaaa": {"task": "B1", "arm": "A"}})
            self.ledger.unseal(key_path, run_ids_by_task={"B1": "pairrun-1"})
            with self.assertRaises(AuditError):
                self.ledger.unseal(key_path, run_ids_by_task={"B1": "pairrun-1"})

    def test_refuses_unknown_task_id_in_key(self):
        self.ledger.record_scores("diff-aaaa", _satisfied_results(self.checklist))
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._write_key(tmp, {"diff-aaaa": {"task": "B1", "arm": "A"}})
            with self.assertRaises(AuditError):
                self.ledger.unseal(key_path, run_ids_by_task={})  # B1 missing

    def test_refuses_missing_sealed_key_file(self):
        with self.assertRaises(AuditError):
            self.ledger.unseal(
                "does/not/exist.sealed.json", run_ids_by_task={"B1": "pairrun-1"}
            )


# ---------------------------------------------------------------------------
# Full round trip: blinding -> audit ledger -> unseal -> metrics
# ---------------------------------------------------------------------------

class TestMetricsRoundTrip(unittest.TestCase):
    def test_unsealed_scorecards_plus_flattened_run_records_feed_build_pair_rows(self):
        checklist = _load_checklist("B1")
        presented, sealed_key = shuffle_pair("B1", _RAW_DIFF_A, _RAW_DIFF_B, seed=99)

        pair_record = {
            "task_id": "B1",
            "run_id": "pairrun-xyz",
            "base_sha": "deadbeef",
            "seed": 99,
            "arm_order": ["A", "B"],
            "arms": {
                "A": {
                    "wall_clock_seconds": 120.0,
                    "diff": _RAW_DIFF_A,
                    "adapter_result": {
                        "arm": "A",
                        "model_tier": "sonnet/high",
                        "attempts": [
                            {"kind": "dispatch", "tokens": 100, "verdict": None, "fail_item_ids": []},
                            {"kind": "verify", "tokens": 50, "verdict": "PASS", "fail_item_ids": []},
                        ],
                    },
                },
                "B": {
                    "wall_clock_seconds": 60.0,
                    "diff": _RAW_DIFF_B,
                    "adapter_result": {
                        "arm": "B",
                        "model_tier": "sonnet/high",
                        "attempts": [
                            {"kind": "turn", "tokens": 80, "verdict": None, "fail_item_ids": []},
                        ],
                    },
                },
            },
        }
        run_records = flatten_pair_record(pair_record)

        ledger = BlindedScoreLedger(run_id="bench-run-round-trip")
        for label, _diff in presented:
            ledger.record_scores(label, _satisfied_results(checklist))

        with tempfile.TemporaryDirectory() as tmp:
            key_path = write_sealed_key("bench-run-round-trip", sealed_key, base_dir=tmp)
            scorecards = ledger.unseal(
                key_path, run_ids_by_task={"B1": pair_record["run_id"]}
            )

        rows = build_pair_rows(run_records, scorecards)  # must not raise
        self.assertEqual(len(rows), 2)
        arms_seen = {row["arm"] for row in rows}
        self.assertEqual(arms_seen, {"A", "B"})
        for row in rows:
            self.assertEqual(row["defects_escaped_count"], 0)


if __name__ == "__main__":
    unittest.main()
