# tools/test_route_table.py
"""Tests for tools/route_table.py -- the canonical route table
(bm-canonical-route-table, docs/specs/2026-07-22-phase2-external-
workers.md). Asserts: the closed provider enum matches
validate_config.PROVIDER_ENUM (plus the claude-only sentinel), the
precedence chain is exactly the five documented steps in order, and all
seven trigger domains plus all eight R2 rejection categories are present.
"""
import pathlib
import sys
import unittest

_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import validate_config
import route_table


class TestBuilderEnum(unittest.TestCase):
    def test_matches_validate_config_provider_enum_plus_claude_only(self):
        self.assertEqual(
            route_table.BUILDER_ENUM,
            frozenset(validate_config.PROVIDER_ENUM) | {"claude-only"})

    def test_accessor_returns_same_value_as_module_constant(self):
        self.assertEqual(route_table.builder_enum(), route_table.BUILDER_ENUM)

    def test_claude_only_sentinel_present_and_not_an_external_provider(self):
        self.assertIn(route_table.CLAUDE_ONLY, route_table.BUILDER_ENUM)
        self.assertNotIn(route_table.CLAUDE_ONLY, validate_config.PROVIDER_ENUM)

    def test_every_external_provider_present(self):
        for provider in validate_config.PROVIDER_ENUM:
            self.assertIn(provider, route_table.BUILDER_ENUM)

    def test_is_frozen(self):
        self.assertIsInstance(route_table.BUILDER_ENUM, frozenset)


class TestPrecedenceChain(unittest.TestCase):
    EXPECTED_STEP_IDS = (
        "authenticated-human-sensitive-provider-override",
        "sensitive-domain-default-to-claude",
        "provider-gates",
        "matching-profile-role-worker-default",
        "task-shape-tie-break",
    )

    def test_exactly_five_steps(self):
        self.assertEqual(len(route_table.PRECEDENCE_CHAIN), 5)

    def test_steps_are_numbered_1_through_5_in_order(self):
        self.assertEqual(
            [entry["step"] for entry in route_table.PRECEDENCE_CHAIN],
            [1, 2, 3, 4, 5])

    def test_step_ids_match_spec_order_exactly(self):
        self.assertEqual(
            tuple(entry["id"] for entry in route_table.PRECEDENCE_CHAIN),
            self.EXPECTED_STEP_IDS)

    def test_every_step_has_a_non_empty_name_and_summary(self):
        for entry in route_table.PRECEDENCE_CHAIN:
            self.assertTrue(entry["name"].strip())
            self.assertTrue(entry["summary"].strip())

    def test_accessor_returns_same_ordered_tuple(self):
        self.assertEqual(route_table.precedence_chain(), route_table.PRECEDENCE_CHAIN)

    def test_is_a_tuple_not_a_mutable_list(self):
        self.assertIsInstance(route_table.PRECEDENCE_CHAIN, tuple)


class TestTriggerDomains(unittest.TestCase):
    EXPECTED_TRIGGER_IDS = {
        "auth-token-secret",
        "money-payment",
        "cookie-storage-write",
        "raw-html",
        "form-redirect",
        "untrusted-input-parsing",
        "new-dependency",
    }

    def test_all_seven_triggers_present(self):
        ids = {entry["id"] for entry in route_table.TRIGGER_DOMAINS}
        self.assertEqual(ids, self.EXPECTED_TRIGGER_IDS)

    def test_exactly_seven_triggers(self):
        self.assertEqual(len(route_table.TRIGGER_DOMAINS), 7)

    def test_no_duplicate_trigger_ids(self):
        ids = [entry["id"] for entry in route_table.TRIGGER_DOMAINS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_trigger_has_a_label(self):
        for entry in route_table.TRIGGER_DOMAINS:
            self.assertTrue(entry["label"].strip())

    def test_regex_triggers_carry_the_documented_pattern_text(self):
        by_id = {entry["id"]: entry for entry in route_table.TRIGGER_DOMAINS}
        self.assertEqual(by_id["auth-token-secret"]["pattern"],
                         r"auth|token|secret|password|credential")
        self.assertEqual(by_id["money-payment"]["pattern"],
                         r"payment|billing|money|price")
        self.assertEqual(by_id["cookie-storage-write"]["pattern"],
                         r"cookie|session|localStorage|sessionStorage")
        self.assertEqual(by_id["raw-html"]["pattern"],
                         r"dangerouslySetInnerHTML|raw.?html")
        self.assertEqual(by_id["form-redirect"]["pattern"],
                         r"redirect|form.*submit")
        self.assertEqual(by_id["untrusted-input-parsing"]["pattern"],
                         r"parse|deserialize|untrusted|user.?input")

    def test_new_dependency_trigger_has_no_fixed_pattern(self):
        by_id = {entry["id"]: entry for entry in route_table.TRIGGER_DOMAINS}
        self.assertIsNone(by_id["new-dependency"]["pattern"])

    def test_accessor_returns_same_ordered_tuple(self):
        self.assertEqual(route_table.trigger_domains(), route_table.TRIGGER_DOMAINS)


class TestRejectionCategories(unittest.TestCase):
    EXPECTED_REJECTION_IDS = {
        "record-only",
        "wrong-task",
        "wrong-provider",
        "stale",
        "reused-nonce",
        "worker-originated",
        "auto-resolved",
        "headless/no-human",
    }

    def test_all_eight_categories_present(self):
        ids = {entry["id"] for entry in route_table.REJECTION_CATEGORIES}
        self.assertEqual(ids, self.EXPECTED_REJECTION_IDS)

    def test_exactly_eight_categories(self):
        self.assertEqual(len(route_table.REJECTION_CATEGORIES), 8)

    def test_no_duplicate_rejection_ids(self):
        ids = [entry["id"] for entry in route_table.REJECTION_CATEGORIES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_category_has_a_non_empty_summary(self):
        for entry in route_table.REJECTION_CATEGORIES:
            self.assertTrue(entry["summary"].strip())

    def test_accessor_returns_same_ordered_tuple(self):
        self.assertEqual(route_table.rejection_categories(),
                         route_table.REJECTION_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
