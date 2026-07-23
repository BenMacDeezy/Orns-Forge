"""Pytest wiring for fg-b0401's shard conservation gates (R1/R2/R3).

See tools/check_shard_conservation.py for the full rationale and
implementation of each gate. This module just exposes them as permanent
suite coverage so a future regression (a shard body edited out of sync with
the index, a dropped Amended-by pointer, a citation left dangling after a
future rename) fails CI instead of silently drifting.
"""
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_shard_conservation as csc  # noqa: E402


class TestShardConservation(unittest.TestCase):
    def test_r1_mechanical_split_fidelity(self):
        errors = csc.check_r1()
        self.assertEqual(errors, [], "\n".join(errors))

    def test_r2_index_integrity(self):
        errors = csc.check_r2()
        self.assertEqual(errors, [], "\n".join(errors))

    def test_r3_amendment_pointer_integrity(self):
        errors = csc.check_r3()
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
