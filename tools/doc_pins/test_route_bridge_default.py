"""Doc-pin regression tests for bm-route-bridge-default: R1 automatic-default
ROUTE semantics in skills/kernel/references/provider-judges.md section 7.1.
New module (not a shard of an existing task-id prefix) because this task's
content is new normative text, not an extension of a `fg-*`/`bm-`-prefixed
predecessor's own pin file. Every substring below is unique to text this
task added -- it must never re-pin the four pre-existing gate-condition
bullets verbatim-checked by tools/doc_pins/test_fg_c0111.py's
`test_route_gate_conditions_present` (this task leaves those bullets
byte-identical; that pin stays that pin's own responsibility, not
duplicated here)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestRouteBridgeDefaultPins(unittest.TestCase):
    """Doc-pins for bm-route-bridge-default: role-worker's resolution to a
    provider is the R1 automatic-default BUILDER route for an eligible
    task (no per-task `provider:` field required); `provider:` is an
    override, not a required conjunct; the precedence order is read from
    `tools/route_table.py`, never re-derived; the sensitive-domain default
    (chain step 2) outranks the automatic default (chain step 4)."""

    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )

    def _provider_judges(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def test_section_heading_names_automatic_default_and_override(self):
        content = self._provider_judges()
        self.assertIn(
            "### 7.1 Route gate — role-worker automatic-default (R1), "
            "provider: as override",
            content,
        )

    def test_automatic_default_no_field_required(self):
        content = self._provider_judges()
        self.assertIn("`role-worker`'s resolution to a", content)
        self.assertIn(
            "provider IS the default BUILDER route for an ELIGIBLE task",
            content,
        )
        self.assertIn(
            "`provider:` field is required to activate it.", content
        )

    def test_eligible_defined_via_route_table_steps_2_and_3(self):
        content = self._provider_judges()
        self.assertIn(
            "A task is ELIGIBLE when it", content,
        )
        self.assertIn(
            "passes `tools/route_table.py`'s canonical `precedence_chain()`:"
            " not",
            content,
        )
        self.assertIn(
            "classified sensitive-domain (chain step 2) and passing every "
            "provider",
            content,
        )
        self.assertIn("gate (chain step 3).", content)

    def test_cites_route_table_never_restates_step_order(self):
        content = self._provider_judges()
        self.assertIn(
            "This section states the CONDITIONS below; it never",
            content,
        )
        self.assertIn(
            "restates the chain's STEP ORDER, which lives solely in",
            content,
        )
        self.assertIn(
            "`tools/route_table.py` — read that module, do not re-derive "
            "it here.",
            content,
        )

    def test_provider_field_is_override_not_required_conjunct(self):
        content = self._provider_judges()
        self.assertIn(
            "**`provider:` is an override, never a required conjunct "
            "(chain step",
            content,
        )
        self.assertIn(
            "SHALL treat it as an OVERRIDE of the automatic default above "
            "for that",
            content,
        )
        self.assertIn(
            "task only — NOT as an additional precondition role-worker's "
            "resolution",
            content,
        )
        self.assertIn("needs in order to take effect.", content)

    def test_claude_only_always_wins_no_envelope(self):
        content = self._provider_judges()
        self.assertIn(
            "`provider:\nclaude-only` always forces an in-harness Claude "
            "builder, on any task,",
            content,
        )
        self.assertIn(
            "sensitive or not, with no elevated provenance needed.",
            content,
        )

    def test_sensitive_override_requires_envelope_cited_not_built(self):
        content = self._provider_judges()
        self.assertIn(
            "SHALL require a valid, unconsumed, matching",
            content,
        )
        self.assertIn(
            "un-forgeable authorization envelope before that override can "
            "cross the",
            content,
        )
        self.assertIn("carve-out below", content)
        self.assertIn("`bm-sensitive-override-provenance`", content)

    def test_step2_outranks_step4_safety_story_explicit(self):
        content = self._provider_judges()
        self.assertIn(
            "**Sensitive-domain default outranks the automatic default "
            "(chain step 2",
            content,
        )
        self.assertIn(
            "precedes step 4) — the whole safety story, stated "
            "explicitly.**",
            content,
        )
        self.assertIn(
            "R1's automatic-default therefore NEVER by itself crosses the",
            content,
        )
        self.assertIn("sensitive-domain carve-out", content)
        self.assertIn(
            "Ordinary (non-sensitive-domain)", content,
        )
        self.assertIn(
            "tasks are the only tasks step 4's automatic default ever "
            "resolves.",
            content,
        )

    def test_existing_four_gate_bullets_left_byte_identical(self):
        """This task extends section 7.1's prose but must leave the four
        pre-existing gate-condition bullets (already pinned verbatim by
        test_fg_c0111.py's test_route_gate_conditions_present) untouched --
        confirms this module's own edit did not accidentally reword them."""
        content = self._provider_judges()
        self.assertIn(
            "- the active profile's `role-worker` resolves to that "
            "provider (not\n  `claude-only`);",
            content,
        )
        self.assertIn(
            "- for `grok` or `antigravity`, the provider's pilot gate\n"
            "  (`bm-grok-pilot-test` / `bm-antigravity-smoke-test`) has "
            "been\n  human-reviewed and cleared — `codex` carries no such "
            "pilot gate",
            content,
        )


if __name__ == "__main__":
    unittest.main()
