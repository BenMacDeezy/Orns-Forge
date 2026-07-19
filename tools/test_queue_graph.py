"""Tests for tools/queue_graph.py (fg-a10202): render the Forge queue as a
mermaid flowchart DAG -- one node per non-done task, blocked-by edges, node
classes by state, done omitted unless --all. Fixtures are inline task-file
strings written to their own tmp dir per test (same pattern as
tools/test_telemetry.py). Read-only: the tool must never modify queue files.
"""
import pathlib
import tempfile
import unittest

from queue_graph import (
    NO_DIAGRAM_MESSAGE,
    build_graph,
    render_mermaid,
)


def _task(id_, title, state, blocked_by=None, tier="standard", malformed=False):
    if malformed:
        return "not even frontmatter, just garbage\n"
    blocked_by = blocked_by or []
    blocked_by_yaml = (
        "[]" if not blocked_by
        else "\n" + "\n".join(f"  - {b}" for b in blocked_by)
    )
    return f"""---
id: {id_}
title: "{title}"
state: {state}
tier: {tier}
priority: 2
spec: null
blocks: []
blocked-by: {blocked_by_yaml}
claimed-by: null
parallel-safe: true
created: 2026-07-18T00:00:00Z
updated: 2026-07-18T00:00:00Z
schema-version: 1
---

## Acceptance criteria
WHEN a fixture runs, THE SYSTEM SHALL do the fixture thing.

## Execution plan
(pending)

## Routing record
(pending)

## Attempt log
(pending)

## Outcome
(pending)
"""


def _write(task_dir, id_, **kw):
    title = kw.pop("title", f"Fixture {id_}")
    (pathlib.Path(task_dir) / f"{id_}-fixture.md").write_text(
        _task(id_, title, **kw), encoding="utf-8"
    )


class QueueGraphTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.task_dir = self._tmp

    def tearDown(self):
        pass  # tempfile dirs are left for the OS to reap; no repo state touched


class TestBlockedByEdge(QueueGraphTestCase):
    def test_blocker_to_blocked_edge_line_exact(self):
        _write(self.task_dir, "fg-aaaa", title="Blocker task", state="ready")
        _write(
            self.task_dir, "fg-bbbb", title="Blocked task", state="blocked",
            blocked_by=["fg-aaaa"],
        )
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        self.assertIn("fg-aaaa --> fg-bbbb", output)

    def test_edge_omitted_when_blocker_node_not_rendered(self):
        # blocker is done (omitted by default) -- edge must not dangle
        _write(self.task_dir, "fg-aaaa", title="Done blocker", state="done")
        _write(
            self.task_dir, "fg-bbbb", title="Blocked task", state="blocked",
            blocked_by=["fg-aaaa"],
        )
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        self.assertNotIn("fg-aaaa --> fg-bbbb", output)


class TestStateClasses(QueueGraphTestCase):
    def test_each_state_gets_its_own_classdef_assignment(self):
        _write(self.task_dir, "fg-r001", title="Ready one", state="ready")
        _write(self.task_dir, "fg-a001", title="Active one", state="active")
        _write(self.task_dir, "fg-b001", title="Blocked one", state="blocked")
        _write(self.task_dir, "fg-k001", title="Backlog one", state="backlog")
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        self.assertIn("classDef ready", output)
        self.assertIn("classDef active", output)
        self.assertIn("classDef blocked", output)
        self.assertIn("classDef backlog", output)
        self.assertIn("class fg-r001 ready", output)
        self.assertIn("class fg-a001 active", output)
        self.assertIn("class fg-b001 blocked", output)
        self.assertIn("class fg-k001 backlog", output)


class TestDoneOmittedByDefault(QueueGraphTestCase):
    def test_done_task_omitted_by_default(self):
        _write(self.task_dir, "fg-d001", title="Done one", state="done")
        _write(self.task_dir, "fg-r002", title="Ready one", state="ready")
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        self.assertNotIn("fg-d001", output)
        self.assertIn("fg-r002", output)

    def test_done_task_included_with_all(self):
        _write(self.task_dir, "fg-d001", title="Done one", state="done")
        _write(self.task_dir, "fg-r002", title="Ready one", state="ready")
        graph = build_graph(self.task_dir, include_done=True)
        output = render_mermaid(graph)
        self.assertIn("fg-d001", output)
        self.assertIn("fg-r002", output)


class TestEmptyOrAllDoneQueue(QueueGraphTestCase):
    def test_empty_queue_says_so_instead_of_empty_diagram(self):
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        self.assertEqual(output, NO_DIAGRAM_MESSAGE)
        self.assertNotIn("```mermaid", output)

    def test_all_done_queue_says_so_instead_of_empty_diagram(self):
        _write(self.task_dir, "fg-d001", title="Done one", state="done")
        _write(self.task_dir, "fg-d002", title="Done two", state="done")
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        self.assertEqual(output, NO_DIAGRAM_MESSAGE)

    def test_all_done_queue_with_all_flag_does_render(self):
        _write(self.task_dir, "fg-d001", title="Done one", state="done")
        graph = build_graph(self.task_dir, include_done=True)
        output = render_mermaid(graph)
        self.assertIn("```mermaid", output)
        self.assertIn("fg-d001", output)


class TestMalformedTaskFileSkippedWithNote(QueueGraphTestCase):
    def test_malformed_file_skipped_not_crashed_and_noted(self):
        _write(self.task_dir, "fg-r003", title="Ready one", state="ready")
        (pathlib.Path(self.task_dir) / "fg-zzzz-garbage.md").write_text(
            "not even frontmatter, just garbage\n", encoding="utf-8"
        )
        # must not raise
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        self.assertIn("fg-r003", output)
        self.assertIn("1", output)  # note mentions the skipped count
        self.assertIn("skipped", output.lower())


class TestMalformedDependencyFieldNeverSilentlyEmpty(QueueGraphTestCase):
    def test_malformed_blocked_by_inline_list_is_skipped_not_edge_free(self):
        # Unclosed bracket in blocked-by -- validate_task's _parse_frontmatter
        # flags this in fm_errors but still returns a usable fm/body. Before
        # the fix, build_graph discarded fm_errors entirely and the task
        # rendered as a normal, edge-free node with skipped:0 -- the
        # malformation vanished without a trace (fg-a10504).
        _write(self.task_dir, "fg-r004", title="Ready one", state="ready")
        bad = """---
id: fg-bad1
title: "Malformed dep"
state: blocked
tier: standard
priority: 2
spec: null
blocks: []
blocked-by: [fg-r004, fg-r005
claimed-by: null
parallel-safe: true
created: 2026-07-18T00:00:00Z
updated: 2026-07-18T00:00:00Z
schema-version: 1
---

## Acceptance criteria
WHEN a fixture runs, THE SYSTEM SHALL do the fixture thing.

## Execution plan
(pending)

## Routing record
(pending)

## Attempt log
(pending)

## Outcome
(pending)
"""
        (pathlib.Path(self.task_dir) / "fg-bad1-fixture.md").write_text(
            bad, encoding="utf-8"
        )

        graph = build_graph(self.task_dir)

        # The malformed task must surface as a non-zero skip signal, not as
        # a silently edge-free node with skipped:0.
        self.assertEqual(graph["skipped"], 1)
        self.assertNotIn("fg-bad1", [n["id"] for n in graph["nodes"]])

        output = render_mermaid(graph)
        self.assertIn("fg-r004", output)
        self.assertIn("skipped", output.lower())
        self.assertIn("1", output)


class TestReadOnly(QueueGraphTestCase):
    def test_queue_files_byte_identical_after_run(self):
        _write(self.task_dir, "fg-aaaa", title="Blocker task", state="ready")
        _write(
            self.task_dir, "fg-bbbb", title="Blocked task", state="blocked",
            blocked_by=["fg-aaaa"],
        )
        before = {
            p.name: p.read_bytes()
            for p in pathlib.Path(self.task_dir).glob("*.md")
        }
        graph = build_graph(self.task_dir, include_done=True)
        render_mermaid(graph)
        after = {
            p.name: p.read_bytes()
            for p in pathlib.Path(self.task_dir).glob("*.md")
        }
        self.assertEqual(before, after)


class TestTitleTruncationAndEscaping(QueueGraphTestCase):
    def test_long_title_truncated_around_40_chars(self):
        long_title = "A" * 80
        _write(self.task_dir, "fg-long", title=long_title, state="ready")
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        # the raw 80-char title must not appear verbatim
        self.assertNotIn(long_title, output)

    def test_quotes_and_brackets_escaped_in_title(self):
        _write(
            self.task_dir, "fg-esc",
            title='Weird "title" with [brackets]', state="ready",
        )
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        # node line must not contain a raw double-quote inside the label
        # text or raw square brackets that would break mermaid's node syntax
        node_line = next(
            line for line in output.splitlines() if line.strip().startswith("fg-esc[")
        )
        inner = node_line.split("[", 1)[1].rsplit("]", 1)[0]
        self.assertNotIn('"title"', inner)
        self.assertNotIn("[brackets]", inner)


class TestDeterministicOrdering(QueueGraphTestCase):
    def test_nodes_sorted_by_id(self):
        _write(self.task_dir, "fg-c003", title="C", state="ready")
        _write(self.task_dir, "fg-a001", title="A", state="ready")
        _write(self.task_dir, "fg-b002", title="B", state="ready")
        graph = build_graph(self.task_dir)
        output = render_mermaid(graph)
        pos_a = output.index("fg-a001[")
        pos_b = output.index("fg-b002[")
        pos_c = output.index("fg-c003[")
        self.assertTrue(pos_a < pos_b < pos_c)


if __name__ == "__main__":
    unittest.main()
