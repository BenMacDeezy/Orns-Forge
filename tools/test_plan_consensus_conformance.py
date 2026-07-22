"""Executable truth-table checks for cross-model consensus AC A--C.

This is intentionally a pure-function conformance mirror, like
test_provider_route_conformance.py: it models the public protocol without
constructing a dispatcher or invoking a provider.
"""
import unittest


def _verdict(manifest, decisions, attempts=1):
    """Build a compact critique fixture; attempts includes malformed retries."""
    return {"manifest": manifest, "decisions": decisions, "attempts": attempts}


def _validate(verdict, manifest):
    ids = [entry["id"] for entry in verdict["decisions"]]
    if set(ids) != set(manifest) or len(ids) != len(set(ids)):
        return None
    if any(entry["verdict"] not in {"ACCEPT", "REJECT"} for entry in verdict["decisions"]):
        return None
    for entry in verdict["decisions"]:
        if entry["verdict"] == "REJECT" and entry.get("severity") not in {"P0", "P1", "P3"}:
            return None
    return verdict["decisions"]


def evaluate(manifest, c1, c2=None):
    """Return protocol outcome, provider tally, and approval eligibility."""
    tally = c1["attempts"] + (c2["attempts"] if c2 else 0)
    c1_entries = _validate(c1, manifest)
    if c1_entries is None:
        return {"outcome": "malformed", "dispatches": tally, "approval": False}

    blocking = [entry["id"] for entry in c1_entries
                if entry["verdict"] == "REJECT" and entry["severity"] in {"P0", "P1"}]
    fixed_inline = [entry["id"] for entry in c1_entries
                    if entry["verdict"] == "REJECT" and entry["severity"] == "P3"]
    if not blocking:
        return {"outcome": "complete", "critiques": 1, "dispatches": tally,
                "fixed_inline": fixed_inline, "approval": True}
    if c2 is None:
        return {"outcome": "unresolved", "critiques": 1, "dispatches": tally,
                "outstanding": blocking, "approval": False}

    c2_entries = _validate(c2, manifest)
    if c2_entries is None:
        return {"outcome": "malformed", "dispatches": tally, "approval": False}
    outstanding = [entry["id"] for entry in c2_entries
                   if entry["verdict"] == "REJECT" and entry["severity"] in {"P0", "P1"}]
    return {"outcome": "unresolved" if outstanding else "complete", "critiques": 2,
            "dispatches": tally, "outstanding": outstanding, "fixed_inline": fixed_inline,
            "approval": not outstanding}


class PlanConsensusConformance(unittest.TestCase):
    MANIFEST = ["scope", "storage"]

    def test_escalate_only_entry_clean_c1_is_one_dispatch_and_complete(self):
        result = evaluate(self.MANIFEST, _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "ACCEPT"},
            {"id": "storage", "verdict": "ACCEPT"},
        ]))
        self.assertEqual(result["outcome"], "complete")
        self.assertEqual(result["critiques"], 1)
        self.assertEqual(result["dispatches"], 1)

    def test_reject_enters_c2_and_the_cap_is_exactly_two(self):
        c1 = _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "REJECT", "severity": "P1"},
            {"id": "storage", "verdict": "ACCEPT"},
        ])
        c2 = _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "REJECT", "severity": "P1"},
            {"id": "storage", "verdict": "ACCEPT"},
        ])
        result = evaluate(self.MANIFEST, c1, c2)
        self.assertEqual((result["outcome"], result["critiques"]), ("unresolved", 2))
        self.assertFalse(result["approval"])
        self.assertEqual(result["outstanding"], ["scope"])

    def test_exact_coverage_missing_or_extra_id_is_malformed(self):
        missing = _verdict(self.MANIFEST, [{"id": "scope", "verdict": "ACCEPT"}])
        extra = _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "ACCEPT"},
            {"id": "storage", "verdict": "ACCEPT"},
            {"id": "invented", "verdict": "ACCEPT"},
        ])
        self.assertEqual(evaluate(self.MANIFEST, missing)["outcome"], "malformed")
        self.assertEqual(evaluate(self.MANIFEST, extra)["outcome"], "malformed")

    def test_p3_fixed_inline_never_gates_c2(self):
        result = evaluate(self.MANIFEST, _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "REJECT", "severity": "P3"},
            {"id": "storage", "verdict": "ACCEPT"},
        ]))
        self.assertEqual(result["critiques"], 1)
        self.assertEqual(result["fixed_inline"], ["scope"])
        self.assertTrue(result["approval"])

    def test_retries_are_provider_invocations_in_the_same_tally(self):
        c1 = _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "REJECT", "severity": "P0"},
            {"id": "storage", "verdict": "ACCEPT"},
        ], attempts=3)  # initial call plus the two allowed re-prompts
        c2 = _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "ACCEPT"},
            {"id": "storage", "verdict": "ACCEPT"},
        ], attempts=2)
        self.assertEqual(evaluate(self.MANIFEST, c1, c2)["dispatches"], 5)

    def test_mid_cap_reject_without_c2_terminates_unresolved_not_erased(self):
        result = evaluate(self.MANIFEST, _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "REJECT", "severity": "P1"},
            {"id": "storage", "verdict": "ACCEPT"},
        ]))
        self.assertEqual(result["outcome"], "unresolved")
        self.assertEqual(result["outstanding"], ["scope"])
        self.assertFalse(result["approval"])

    def test_cap_out_is_pre_approval_until_every_disputed_id_is_resolved(self):
        c1 = _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "REJECT", "severity": "P1"},
            {"id": "storage", "verdict": "ACCEPT"},
        ])
        c2 = _verdict(self.MANIFEST, [
            {"id": "scope", "verdict": "REJECT", "severity": "P0"},
            {"id": "storage", "verdict": "ACCEPT"},
        ])
        result = evaluate(self.MANIFEST, c1, c2)
        self.assertFalse(result["approval"])
        self.assertEqual(result["outstanding"], ["scope"])


if __name__ == "__main__":
    unittest.main()
