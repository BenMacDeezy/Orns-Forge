"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10813`: TestFgA10813ShardConventionsPins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
    _CONVENTIONS_PATH_RESOLVED,
    _WORD_TO_INT,
    validate_task,
    shard_task,
    conventions_corpus,
)


class TestFgA10813ShardConventionsPins(unittest.TestCase):
    """Doc-pins for fg-a10813 (T3 of the fg-a10801 sharded fan-out
    decomposition): the ONE canonical dated docs/conventions.md section
    covering the shard-by/max-shards/shard-key frontmatter fields (schema:
    fg-a10811), the shard->dispatch->merge->verify protocol, the mandatory
    worktree-per-shard isolation rule, and the #1..#N/slug-unchanged
    display convention; the shard-eligibility predicate documented as
    SEPARATE from wave eligibility with shard-by:files restricted to
    per-file-local operations; the OQ1 nesting resolution (supported by
    schema+loop, single shared window, "allowed != always-chosen"); and the
    OQ2 cmd: deferral tied to the existing "trust cannot travel" rule. Also
    pins the two refuter-reconciliation invariants: skip-per-shard-verify
    tied to the existing Low-risk verification predicate (not a blanket
    mechanical exemption), and shard INTEGRATE being atomic for the task
    (inverting parallel-batch INTEGRATE).

    Covers all 4 EARS clauses of fg-a10813-shard-conventions.md.
    """

    SECTION_HEADING = "## Sharded fan-out — 2026-07-18"

    def _section(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.SECTION_HEADING, content)
        return content.split(self.SECTION_HEADING, 1)[1]

    def _normalized_section(self):
        return re.sub(r"\s+", " ", self._section())

    # --- EARS clause 1: one canonical section -- frontmatter fields +
    # shard->dispatch->merge->verify protocol + mandatory worktree
    # isolation + #1..#N/slug-unchanged display -------------------------

    def test_conventions_has_toc_entry(self):
        content = conventions_corpus.corpus_text()
        self.assertIn("- Sharded fan-out — 2026-07-18", content)

    def test_section_has_frontmatter_fields(self):
        section = self._section()
        self.assertIn("`shard-by`", section)
        self.assertIn("`max-shards`", section)
        self.assertIn("`shard-key`", section)

    def test_section_has_shard_dispatch_merge_verify_protocol_heading(self):
        section = self._section()
        self.assertIn(
            "### Shard → dispatch → merge → verify protocol", section
        )

    def test_section_states_worktree_isolation_mandatory(self):
        normalized = self._normalized_section()
        self.assertIn(
            "### Worktree-per-shard isolation — MANDATORY", normalized
        )
        self.assertIn(
            'Every shard worker MUST dispatch under Agent-tool '
            '`isolation: "worktree"`.', normalized,
        )
        self.assertIn(
            "Parallel identical-slug workers must never share a mutating "
            "tree", normalized,
        )

    def test_section_states_display_convention(self):
        normalized = self._normalized_section()
        self.assertIn(
            "A sharded swarm displays with the dispatched slug unchanged",
            normalized,
        )
        self.assertIn("`#1..#N`", normalized)
        self.assertIn(
            "disambiguated by instance number, never by task id", normalized,
        )

    # --- EARS clause 2: shard-eligibility predicate SEPARATE from wave
    # eligibility; shard-by:files restricted to per-file-local ops -------

    def test_section_states_wave_eligibility_is_mechanical(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Wave eligibility (\"Parallel dispatch (Waves amendment, "
            "2026-07-17)\", above) is a **mechanical scope-overlap check**",
            normalized,
        )

    def test_section_states_shard_eligibility_adds_conservative_judgment(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Shard eligibility is NOT the same predicate applied at a "
            "smaller grain — it ADDS a conservative judgment call on top",
            normalized,
        )
        self.assertIn("**no cross-slice dependency**", normalized)
        self.assertIn("when uncertain, do NOT shard", normalized)

    def test_section_restricts_files_sharding_to_per_file_local(self):
        normalized = self._normalized_section()
        self.assertIn(
            "`shard-by: files` is RESTRICTED in v1 to provably "
            "per-file-local operations", normalized,
        )
        self.assertIn(
            "**textually-clean-but-semantically-broken**", normalized
        )
        self.assertIn("must NOT be sharded by `files`", normalized)

    # --- EARS clause 3: nesting (OQ1) -- supported by schema+loop, single
    # shared window with >=1 slot reserved per wave task, "allowed !=
    # always-chosen" -----------------------------------------------------

    def test_section_states_nesting_supported_by_schema_and_loop(self):
        normalized = self._normalized_section()
        self.assertIn(
            "nesting is **SUPPORTED by schema and loop from day one**",
            normalized,
        )
        self.assertIn("**SAME single sliding-window cap**", normalized)
        self.assertIn(
            "**≥1 slot reserved per distinct wave task**", normalized
        )

    def test_section_states_allowed_not_always_chosen(self):
        normalized = self._normalized_section()
        self.assertIn('"Allowed ≠ always-chosen."', normalized)
        self.assertIn(
            "does not auto-select a double fan-out where the "
            "no-cross-slice-dependency judgment is unproven", normalized,
        )

    # --- EARS clause 4: cmd: shard sources DEFERRED (OQ2), tied to the
    # existing "trust cannot travel" rule ---------------------------------

    def test_section_states_cmd_deferred_to_future_task(self):
        normalized = self._normalized_section()
        self.assertIn(
            "**v1 ships `inline-list` and glob shard sources only.**",
            normalized,
        )
        self.assertIn(
            "is explicitly deferred to a future task", normalized
        )

    def test_section_ties_cmd_deferral_to_trust_cannot_travel_rule(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Trust cannot travel with content arriving after the first "
            "confirm — merges widen blast radius", normalized,
        )
        self.assertIn(
            "would dispatch on the next `continuous-loop` wave with "
            "**no re-gate**", normalized,
        )

    def test_trust_cannot_travel_phrase_is_the_real_existing_rule(self):
        """The quoted phrase must actually exist in the pre-existing Trust
        boundary section, not just be repeated in the new section -- this
        pin fails if the cited rule's own wording ever drifts out from
        under the citation."""
        content = conventions_corpus.corpus_text()
        boundary_heading = (
            "## Trust boundary — specs + NL scoping amendment (2026-07-17)"
        )
        self.assertIn(boundary_heading, content)
        boundary_section = content.split(boundary_heading, 1)[1].split(
            "## Sharded fan-out", 1
        )[0]
        self.assertIn(
            "Trust cannot travel with content arriving after the first "
            "confirm", boundary_section,
        )

    # --- Extra invariant: "skip per-shard EARS verify" tied to the
    # EXISTING Low-risk verification predicate, not a blanket
    # mechanical -> optional exemption ------------------------------------

    def test_section_ties_skip_verify_to_low_risk_predicate_not_blanket(self):
        normalized = self._normalized_section()
        self.assertIn(
            '"Per-shard verifier spawns are optional for mechanical work" '
            '(above) is **not** a blanket "mechanical work → optional '
            'verify" rule', normalized,
        )
        self.assertIn(
            "It is the EXISTING **Low-risk verification (standard "
            "sub-class) — 2026-07** predicate", normalized,
        )

    # --- Extra invariant: shard INTEGRATE is ATOMIC for the task,
    # inverting parallel-batch INTEGRATE -- and needs its own stub -------

    def test_section_states_shard_integrate_is_atomic(self):
        normalized = self._normalized_section()
        self.assertIn(
            "Parallel-batch INTEGRATE is explicitly **not** all-or-nothing",
            normalized,
        )
        self.assertIn("Shard INTEGRATE **inverts** that rule", normalized)
        self.assertIn(
            "a **second** failure of the same shard blocks the **whole "
            "task**", normalized,
        )

    def test_section_notes_separate_integrate_stub_needed_but_out_of_scope(self):
        normalized = self._normalized_section()
        self.assertIn(
            "why shard dispatch needs its own INTEGRATE kernel stub",
            normalized,
        )
        self.assertIn(
            "That stub is out of scope here (T5, fg-a10816).", normalized
        )

    # --- fg-a10813 bounce-2 fix: max-shards/shard-by is DIRECTIONAL, not
    # both-or-neither -- ties the doc's claim to the real validator
    # (tools/validate_task.py), and guards against the doc re-claiming a
    # symmetric requirement that was never shipped -----------------------

    def test_max_shards_alone_is_accepted_not_rejected_by_validator(self):
        """The doc previously claimed max-shards is "both-or-neither" with
        shard-by (a symmetric/bidirectional requirement). The shipped
        validator only enforces the FORWARD direction -- shard-by present
        requires max-shards -- and accepts max-shards alone with no
        shard-by (fg-a10811's shipped shape check). This pin proves that
        directional behavior against the real validate() entrypoint, and
        separately proves the doc no longer makes the false symmetric
        claim. It must go RED if either the doc reverts to "both-or-neither"
        or the validator changes to reject max-shards-alone."""
        task_text = (
            "---\n"
            "id: fg-3fa9\n"
            "title: Add rate limiting\n"
            "state: ready\n"
            "tier: standard\n"
            "priority: 2\n"
            "spec: null\n"
            "blocks: []\n"
            "blocked-by: []\n"
            "claimed-by: null\n"
            "parallel-safe: true\n"
            "max-shards: 4\n"
            "created: 2026-07-16\n"
            "updated: 2026-07-16\n"
            "---\n\n"
            "## Acceptance criteria\n"
            "- WHEN a client exceeds 10 attempts per minute, THE SYSTEM "
            "SHALL return 429.\n\n"
            "## Execution plan\n(pending)\n\n"
            "## Routing record\n(pending)\n\n"
            "## Attempt log\n(pending)\n\n"
            "## Outcome\n(pending)\n"
        )
        self.assertNotIn("shard-by", task_text)  # no shard-by declared

        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(task_text)
            task_path = f.name

        errors = validate_task.validate(task_path)
        shard_errors = [e for e in errors if "shard" in e]
        self.assertEqual(
            shard_errors, [],
            "max-shards alone (no shard-by) must validate with zero "
            "shard-related errors -- validation is directional, not "
            f"both-or-neither. Got errors: {errors!r}",
        )

        # The doc must not claim a symmetric/bidirectional requirement.
        self.assertNotIn("both-or-neither", self._section())
