"""Doc-pin regression tests for bm-sensitive-classifier-backstop (spec
decomposition id `bm-pre-dispatch-classifier-post-return-backstop` --
same task, pre-rename spelling; see the naming note at the top of
`skills/kernel/references/sensitive-classifier.md` itself): the fail-closed
PRE-dispatch classifier (concrete inputs, ambiguous-defaults-to-sensitive,
the `new-dependency` `pattern: None` name-match handling) as the PRIMARY
control, and the post-return reject/discard/rebuild backstop -- explicitly
NOT a mid-build halt -- for whatever the classifier misses.

New module (not a shard of an existing task-id prefix) because this task's
content is new normative text in a brand-new reference file, not an
extension of a `fg-*`/`bm-*`-prefixed predecessor's own pin file, matching
the same "new module" rationale `test_route_bridge_default.py`'s own header
states for its sibling task.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestSensitiveClassifierPins(unittest.TestCase):
    """Doc-pins for bm-sensitive-classifier-backstop:
    `skills/kernel/references/sensitive-classifier.md` states the classifier
    inputs, the fail-closed ambiguous-default rule, the honest
    cannot-interrupt-mid-flight limitation, the post-return
    reject/discard/rebuild backstop, and the `new-dependency` domain's
    name-match (not regex) handling -- and cites `tools/route_table.py`'s
    `trigger_domains()` as the canonical trigger-domain data rather than
    restating the seven domains itself."""

    CLASSIFIER_PATH = (
        REPO_ROOT
        / "skills"
        / "kernel"
        / "references"
        / "sensitive-classifier.md"
    )

    def _classifier_doc(self):
        return _cached_read_text(self.CLASSIFIER_PATH)

    def test_file_exists(self):
        self.assertTrue(
            self.CLASSIFIER_PATH.is_file(),
            f"expected {self.CLASSIFIER_PATH} to exist",
        )

    # -- Naming-mismatch note (for bm-atomic-doc-fix to reconcile) --------

    def test_naming_note_cites_both_task_id_spellings(self):
        content = self._classifier_doc()
        self.assertIn("bm-sensitive-classifier-backstop", content)
        self.assertIn(
            "bm-pre-dispatch-classifier-post-return-backstop", content
        )
        self.assertIn("bm-atomic-doc-fix", content)

    # -- Section 2.1: classifier inputs, concrete and exhaustive ----------

    def test_classifier_inputs_enumerated_concretely(self):
        content = self._classifier_doc()
        self.assertIn(
            "### 2.1 Classifier inputs (concrete, exhaustive — no others)",
            content,
        )
        self.assertIn(
            "the task's title and description text;", content
        )
        self.assertIn(
            "its full `## Acceptance criteria` text;", content
        )
        self.assertIn(
            "its `## Execution plan` text, specifically any referenced "
            "file paths or\n  glob patterns named there;",
            content,
        )
        self.assertIn(
            "any named dependency the task's scope introduces.", content
        )
        self.assertIn(
            "No other field, file, or inference source feeds the "
            "classifier",
            content,
        )

    # -- Section 2.2: new-dependency pattern:None handling -----------------

    def test_new_dependency_pattern_none_name_match_handling(self):
        content = self._classifier_doc()
        self.assertIn(
            "**The `new-dependency` domain (`pattern: None`, by design, "
            "not an\n  omission).**",
            content,
        )
        self.assertIn(
            "THE SYSTEM SHALL NOT run this domain through the regex\n"
            "  path at all",
            content,
        )
        self.assertIn(
            "does not already depend on — a name\n"
            "  comparison against the task's current dependency "
            "manifest, never a\n  regex applied to prose",
            content,
        )

    def test_cites_route_table_trigger_domains_never_restates(self):
        content = self._classifier_doc()
        self.assertIn(
            "canonical source is\n  `tools/route_table.py`'s "
            "`trigger_domains()` accessor",
            content,
        )
        self.assertIn(
            "this file never re-types the seven domains or their "
            "patterns.",
            content,
        )

    # -- Section 2.3: fail-closed ambiguous → sensitive hard rule ----------

    def test_ambiguous_defaults_to_sensitive_hard_rule(self):
        content = self._classifier_doc()
        self.assertIn(
            "WHEN classification is AMBIGUOUS", content
        )
        self.assertIn(
            "THE\nSYSTEM SHALL default to sensitive-domain (Claude "
            "builds).",
            content,
        )
        self.assertIn(
            "**when in doubt, Claude.**", content
        )
        self.assertIn(
            "an ambiguous or under-specified task is NEVER the case\n"
            "that gets externally dispatched by default",
            content,
        )

    def test_plausible_match_never_dispatches_externally(self):
        content = self._classifier_doc()
        self.assertIn(
            "THE SYSTEM SHALL classify the task sensitive-domain and it "
            "NEVER\ndispatches externally: Claude builds it, full stop, "
            "with no external\nattempt made at all.",
            content,
        )

    # -- Section 3.1: honest cannot-interrupt-mid-flight limitation --------

    def test_honest_cannot_interrupt_mid_flight_statement(self):
        content = self._classifier_doc()
        self.assertIn(
            "is a single CLI invocation that runs to\ncompletion and "
            "writes its output file before Forge's kernel gets control\n"
            "back.",
            content,
        )
        self.assertIn(
            "There is no mid-flight inspection point at which Forge "
            "could\ninterrupt it, and nothing in this file or the spec "
            "it implements claims\none exists.",
            content,
        )
        self.assertIn(
            "An external provider MAY fully PROCESS a misclassified\n"
            "sensitive task end to end",
            content,
        )

    def test_not_a_mid_build_stop_heading(self):
        content = self._classifier_doc()
        self.assertIn(
            "## 3. BACKSTOP control — post-return rejection, never a "
            "mid-build stop",
            content,
        )

    # -- Section 3.2: reject / discard / rebuild ---------------------------

    def test_reject_discard_rebuild_backstop(self):
        content = self._classifier_doc()
        self.assertIn(
            "1. REJECT the entire external diff outright — discarded, "
            "never partially\n   kept, never integrated in any form",
            content,
        )
        self.assertIn(
            "2. REBUILD the task from scratch on a Claude `forge-worker` "
            "— codex's\n   output for that task is never shipped, in "
            "whole or in part.",
            content,
        )
        self.assertIn(
            "There is no partial-acceptance path", content
        )

    def test_post_return_rejection_attempt_log_note(self):
        content = self._classifier_doc()
        self.assertIn(
            "SHALL record a distinct `post-return-rejection` note in the",
            content,
        )
        self.assertIn(
            "task's Attempt log stating which trigger domain the diff "
            "revealed and", content,
        )
        self.assertIn(
            "that section 2's classifier missed it at dispatch time.",
            content,
        )

    def test_never_claims_worker_halted_before_completion(self):
        content = self._classifier_doc()
        self.assertIn(
            "### 3.4 What this explicitly does NOT claim", content
        )
        self.assertIn(
            "SHALL NOT claim, in this file or in any doc citing it, that "
            "a\nworker is halted before completing a sensitive portion "
            "of its work, that\ndispatch is interrupted mid-flight, or "
            "that Forge inspects a provider's\noutput before the "
            "provider's own CLI call returns.",
            content,
        )


if __name__ == "__main__":
    unittest.main()
