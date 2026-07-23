"""Executable mirror of provider-judges.md §1a and §7.1a.

There is intentionally no dispatcher object: these table tests keep the
documented provider gate order executable without pretending prose is code.
"""
import itertools
import unittest


def documented_outcome(feature, toggle, tofu, pilot, cap):
    """Return the first documented gate outcome for one proposed dispatch."""
    if feature == "off":
        return "provider-gate-blocked layer=global-feature"
    if toggle != "on":
        return "provider-gate-blocked layer=provider-toggle"
    if tofu == "absent":
        return "provider-gate-blocked layer=trust-marker"
    if pilot == "not":
        return "pilot-blocked"
    if cap == "numeric-at-limit":
        return "provider-gate-blocked layer=dispatch-cap"
    # cap "none" (the shipped checkpoint model) dispatches like headroom:
    # a checkpoint is a pause-and-report at each cadence multiple, never a
    # block (provider-judges.md §7.6, checkpoint-model amendment).
    return "dispatch allowed"


class TestProviderRouteConformance(unittest.TestCase):
    def test_gate_matrix_exhaustive(self):
        for feature, toggle, tofu, pilot, cap in itertools.product(
                ("on", "off"), ("on", "off", "absent"),
                ("present", "absent"), ("cleared", "not", "n/a"),
                ("none", "numeric-at-limit", "numeric-with-headroom")):
            with self.subTest(feature=feature, toggle=toggle, tofu=tofu,
                              pilot=pilot, cap=cap):
                outcome = documented_outcome(feature, toggle, tofu, pilot, cap)
                self.assertIn(outcome, {
                    "dispatch allowed", "provider-gate-blocked layer=global-feature",
                    "provider-gate-blocked layer=provider-toggle",
                    "provider-gate-blocked layer=trust-marker",
                    "provider-gate-blocked layer=dispatch-cap",
                    "pilot-blocked"})

    def test_precedence_is_layered(self):
        self.assertEqual(documented_outcome("off", "off", "absent", "not", "none"),
                         "provider-gate-blocked layer=global-feature")
        self.assertEqual(documented_outcome("on", "off", "absent", "not", "none"),
                         "provider-gate-blocked layer=provider-toggle")
        self.assertEqual(documented_outcome("on", "on", "absent", "not", "none"),
                         "provider-gate-blocked layer=trust-marker")
        self.assertEqual(documented_outcome("on", "on", "present", "not", "none"),
                         "pilot-blocked")
        self.assertEqual(
            documented_outcome("on", "on", "present", "cleared", "none"),
            "dispatch allowed")
        self.assertEqual(
            documented_outcome("on", "on", "present", "n/a", "numeric-at-limit"),
            "provider-gate-blocked layer=dispatch-cap")


if __name__ == "__main__":
    unittest.main()
