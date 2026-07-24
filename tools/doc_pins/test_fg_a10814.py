"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10814`: TestFgA10814ShardDispatchPins.
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


class TestFgA10814ShardDispatchPins(unittest.TestCase):
    """Doc-pins for fg-a10814 (T4a): the "Shard expansion" subsection added
    to skills/kernel/references/parallel-dispatch.md, extending the shipped
    parallel-wave dispatch machinery to cover intra-task shard fan-out
    (fg-a10801). Covers all 4 EARS clauses plus a behavioral pin proving the
    {index, shard_by, items} manifest-key contract the doc pins actually
    matches what tools/shard_task.py (fg-a10812) returns -- this task is the
    first consumer of that splitter, so this is where the keys become
    contract, not just a docstring claim. Does NOT touch
    skills/kernel/SKILL.md (T5/fg-a10816's citation stubs are out of scope
    here) or merge/verify/bisect/atomicity semantics (fg-a10815/T4b).
    """

    REF_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
    )

    def _section(self):
        content = _cached_read_text(self.REF_PATH)
        self.assertIn(
            "## Shard expansion", content,
            "parallel-dispatch.md is missing the fg-a10814 'Shard "
            "expansion' section",
        )
        return content.split("## Shard expansion", 1)[1]

    def _normalized_section(self):
        return re.sub(r"\s+", " ", self._section())

    def test_worktree_isolation_is_mandatory(self):
        """EARS clause 1 (part): worktree isolation per shard is MANDATORY,
        identical-slug workers, under the existing wave machinery."""
        section = self._section()
        self.assertIn('isolation: "worktree"', section)
        self.assertIn("**MANDATORY**", section)
        self.assertIn("identical-slug worker", section)
        self.assertIn("EXISTING parallel-wave machinery", section)

    def test_single_shared_window_and_manifest_keys_documented(self):
        """EARS clause 1 (part): ONE shared sliding-window cap, plus the
        {index, shard_by, items} manifest-key contract is documented."""
        normalized = self._normalized_section()
        self.assertIn("ONE sliding-window concurrency cap", normalized)
        self.assertIn("no second, shard-private window", normalized)
        section = self._section()
        self.assertIn("tools/shard_task.py", section)
        for key in ("index", "shard_by", "items"):
            self.assertIn(f'"{key}"', section)

    def test_nesting_guardrail_single_window_reserved_slot(self):
        """EARS clause 2: wave siblings + all shards count against the one
        window; >=1 slot reserved per distinct wave task (OQ1)."""
        normalized = self._normalized_section()
        self.assertIn(
            "DISPATCH counts wave siblings AND all shards of every nested "
            "task against the single sliding-window cap", normalized,
        )
        self.assertIn("at least 1 slot per distinct wave", normalized)
        self.assertIn("OQ1", normalized)

    def test_attempt_log_sequential_kernel_owned_never_concurrent(self):
        """EARS clause 3 (part): kernel-owned SEQUENTIAL writes on main, one
        task file, N slice results serialized, never concurrent writers."""
        normalized = self._normalized_section()
        self.assertIn("**SEQUENTIAL**", normalized)
        self.assertIn("never concurrent writers", normalized)
        self.assertIn(
            "N shard-jobs map to one task file, never N task files",
            normalized,
        )

    def test_display_format_pinned(self):
        """EARS clause 3 (part): display shows "<Persona> #1..#N (<role>)",
        slug unchanged, instance-number disambiguation, never task-id, per
        fg-a10213."""
        normalized = self._normalized_section()
        self.assertIn('`"<Persona> #1..#N (<role>)"`', normalized)
        self.assertIn("slug itself stays unchanged", normalized)
        self.assertIn("instance number, never by task id", normalized)
        self.assertIn("fg-a10213", normalized)

    def test_sync_sweep_cited_no_new_path(self):
        """EARS clause 4: dead-session shard worktrees are collected by the
        EXISTING SYNC stale-worktree sweep, no new sweep path."""
        normalized = self._normalized_section()
        self.assertIn("EXISTING SYNC stale-worktree sweep", normalized)
        self.assertIn("no new recovery path", normalized)
        self.assertIn("does not need to distinguish the two", normalized)

    def test_forward_pointer_to_t4b_scope_boundary(self):
        """Scope boundary: exactly one forward-pointer line to fg-a10815
        (T4b) for merge/verify/bisect/atomicity semantics -- this section
        must not write those semantics itself."""
        normalized = self._normalized_section()
        self.assertIn(
            "Shards complete → see merge/verify contract in fg-a10815 (T4b)",
            normalized,
        )
        self.assertIn("bisect-on-failure", normalized)

    def test_manifest_keys_documented_match_shipped_splitter(self):
        """Behavioral pin: the {index, shard_by, items} keys pinned in the
        doc as the dispatch contract must be the REAL keys
        tools/shard_task.py (fg-a10812) returns -- red if either the doc's
        pinned keys or the module's actual output drifts.
        """
        section = self._section()
        documented_keys = {"index", "shard_by", "items"}
        for key in documented_keys:
            self.assertIn(f'"{key}"', section)

        slices = shard_task.split_shards("items", 2, ["b", "a", "c"])
        self.assertTrue(slices, "shard_task.split_shards returned no slices")
        for sl in slices:
            self.assertEqual(
                set(sl.keys()), documented_keys,
                f"shard_task.py slice keys {set(sl.keys())} != documented "
                f"{documented_keys}",
            )
