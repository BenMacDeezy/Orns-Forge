"""Regression tests for the fail-silent bash accelerator hooks (fg-a100).

Drives the actual scripts in hooks/scripts/ via subprocess against scratch
git repos built in tempfile.TemporaryDirectory(). Never touches this repo's
working tree or its .forge/ directory.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
STALENESS_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "staleness-flag.sh"
SESSION_START_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "session-start-inject.sh"
LOOP_GUARD_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "loop-guard.sh"
BUDGET_GUARD_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "budget-guard.sh"
SESSION_END_LEARN_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "session-end-learn.sh"
AGENT_PROVENANCE_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "agent-provenance-flag.sh"
ONBOARD_NUDGE_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "onboard-nudge.sh"
GITATTRIBUTES = REPO_ROOT / ".gitattributes"

BASH = shutil.which("bash")


def _fake_sha(seed):
    # Well-formed 40-hex sha guaranteed not to exist as a git object in a
    # freshly created scratch repo.
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


class HooksTestBase(unittest.TestCase):
    def setUp(self):
        if BASH is None:
            self.skipTest("bash not found on PATH; cannot exercise hook scripts")

    def _run(self, script, project_dir, stdin_text="", extra_env=None):
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            [BASH, str(script)],
            input=stdin_text,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode, result.stdout, result.stderr

    def _init_repo(self, path):
        def git(*args):
            subprocess.run(
                ["git", *args],
                cwd=str(path),
                capture_output=True,
                text=True,
                check=True,
            )

        git("init", "-q")
        git("config", "user.email", "hooks-test@example.com")
        git("config", "user.name", "Hooks Test")
        git("config", "commit.gpgsign", "false")

    def _commit_empty(self, path, message):
        subprocess.run(
            ["git", "commit", "--allow-empty", "-q", "-m", message],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=True,
        )
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()


class TestStalenessFlag(HooksTestBase):
    def test_non_commit_command_exits_early_without_git_repo(self):
        # Criterion 1: the cheap raw-stdin gate must reject non-`git commit`
        # commands before any cd/git work, so it must not require the
        # CLAUDE_PROJECT_DIR to even be a git repo.
        with tempfile.TemporaryDirectory() as tmp:
            stdin = json.dumps({"tool_input": {"command": "ls -la"}})
            rc, out, _err = self._run(STALENESS_SCRIPT, tmp, stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_real_commit_still_advises_on_stale_index_reference(self):
        # Guards against the early-exit ordering change breaking the real
        # advisory-message path for an actual `git commit`.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)

            map_dir = tmp_path / ".forge" / "map"
            map_dir.mkdir(parents=True)
            (map_dir / "index.md").write_text(
                "## Notes\n- notes/tracked.txt: sample section\n",
                encoding="utf-8",
                newline="\n",
            )

            notes_dir = tmp_path / "notes"
            notes_dir.mkdir()
            (notes_dir / "tracked.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "notes/tracked.txt"],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
                check=True,
            )

            stdin = json.dumps({"tool_input": {"command": "git commit -m x"}})
            rc, out, _err = self._run(STALENESS_SCRIPT, tmp_path, stdin)
            self.assertEqual(rc, 0)
            self.assertIn("systemMessage", out)
            self.assertIn("notes/tracked.txt", out)

    def test_git_commit_phrase_outside_command_field_is_not_a_false_trigger(self):
        # M3 hardening: the cheap raw-stdin pre-filter is anchored to the
        # "command" JSON field, not a bare substring match anywhere in the
        # payload -- a description mentioning the phrase "git commit" (but a
        # non-commit actual command) must not trip it.
        with tempfile.TemporaryDirectory() as tmp:
            stdin = json.dumps({
                "tool_input": {
                    "command": "ls -la",
                    "description": "list files before the next git commit",
                },
            })
            rc, out, _err = self._run(STALENESS_SCRIPT, tmp, stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_prefilter_pattern_is_anchored_to_command_field(self):
        # Source-level guard: confirms the M3 hardening actually landed (not
        # just that behavior happens to still be correct via the second,
        # precise-extraction check).
        source = STALENESS_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"command"[[:space:]]*:[[:space:]]*"[^"]*git commit', source)

    def test_changed_filename_starting_with_dash_is_still_flagged(self):
        # M2 hardening: a changed filename that looks like a grep option
        # (leading '-') must be matched as a literal, not parsed as a flag.
        #
        # NOTE: "-weird.txt" is not a reliable pin here -- GNU grep's option
        # bundling happens to absorb "-weird.txt" as "-e ird.txt" even
        # without the `--` guard, so it still matches "weird.txt"-ish text
        # and the test stays green on revert (vacuous). "-i.txt" is chosen
        # instead: without `--`, GNU grep tries to parse it as options and
        # errors out ("unknown option -- .") rather than silently matching,
        # so the guarded `grep -qF -- "$f" "$idx"` genuinely flips this test
        # red if the `--` is removed. Confirmed on this box:
        #   grep -qF -- "-i.txt" idx    -> rc=0 (matches, as intended)
        #   grep -qF    "-i.txt" idx    -> rc=2 (errors, would NOT flag)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)

            map_dir = tmp_path / ".forge" / "map"
            map_dir.mkdir(parents=True)
            (map_dir / "index.md").write_text(
                "## Notes\n- -i.txt: sample section\n",
                encoding="utf-8",
                newline="\n",
            )

            (tmp_path / "-i.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", "-i.txt"],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
                check=True,
            )

            stdin = json.dumps({"tool_input": {"command": "git commit -m x"}})
            rc, out, _err = self._run(STALENESS_SCRIPT, tmp_path, stdin)
            self.assertEqual(rc, 0)
            self.assertIn("systemMessage", out)
            self.assertIn("-i.txt", out)

    def test_dash_prefixed_filename_matching_uses_double_dash_guard(self):
        # M2 hardening, source-level companion (mirrors the M3 pattern in
        # test_prefilter_pattern_is_anchored_to_command_field): confirms the
        # `--` end-of-options guard is actually present in the filename
        # match, independent of any particular grep implementation's option
        # parsing on the box running the tests.
        #
        # fg-a10914: the match itself moved from a raw `grep -qF -- "$f"
        # "$idx"` substring check to a whole-token match (`grep -qxF -- "$f"`
        # against tokens pre-extracted from $idx) so a changed file can no
        # longer false-match as a substring of an unrelated index entry; the
        # `--` end-of-options guard is preserved across that change.
        source = STALENESS_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('grep -qxF -- "$f"', source)

    def test_changed_file_matching_only_as_substring_of_unrelated_entry_is_not_flagged(self):
        # fg-a10914: a changed file whose name is a raw substring of some
        # *other*, unrelated index.md entry must not be treated as
        # "referenced". Here index.md mentions only `old_utils.py`; the
        # changed file is `utils.py`, which is a literal substring of
        # "old_utils.py" but is a wholly different file that index.md never
        # actually documents. Before the fix, `grep -qF -- "$f" "$idx"`
        # matched this substring and spuriously fired the nudge, falsely
        # claiming index.md references utils.py.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)

            map_dir = tmp_path / ".forge" / "map"
            map_dir.mkdir(parents=True)
            (map_dir / "index.md").write_text(
                "## Notes\n- reference old_utils.py somewhere\n",
                encoding="utf-8",
                newline="\n",
            )
            (tmp_path / "utils.py").write_text("print('hi')\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "utils.py"],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
                check=True,
            )

            stdin = json.dumps({"tool_input": {"command": "git commit -m x"}})
            rc, out, _err = self._run(STALENESS_SCRIPT, tmp_path, stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_changed_file_genuinely_referenced_still_flags_nudge(self):
        # fg-a10914 companion: a changed file that is genuinely referenced
        # in index.md (exact whole-token match, e.g. a backtick-wrapped
        # path) must still trigger the advisory nudge exactly as before the
        # substring-match fix.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)

            map_dir = tmp_path / ".forge" / "map"
            map_dir.mkdir(parents=True)
            (map_dir / "index.md").write_text(
                "## Notes\n- reference `utils.py` genuinely here\n",
                encoding="utf-8",
                newline="\n",
            )
            (tmp_path / "utils.py").write_text("print('hi')\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "utils.py"],
                cwd=str(tmp_path),
                capture_output=True,
                text=True,
                check=True,
            )

            stdin = json.dumps({"tool_input": {"command": "git commit -m x"}})
            rc, out, _err = self._run(STALENESS_SCRIPT, tmp_path, stdin)
            self.assertEqual(rc, 0)
            self.assertIn("systemMessage", out)
            self.assertIn("utils.py", out)


class TestSessionStartInjectFreshness(HooksTestBase):
    def _write_architecture(self, project_dir, body):
        map_dir = pathlib.Path(project_dir) / ".forge" / "map"
        map_dir.mkdir(parents=True)
        (map_dir / "architecture.md").write_text(body, encoding="utf-8", newline="\n")

    def test_sha_equal_to_head_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            head = self._commit_empty(tmp_path, "c0")
            self._write_architecture(tmp_path, f"forge-map-commit: {head}\n")

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("repo map is fresh", out)

    def test_sha_two_commits_behind_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            sha0 = self._commit_empty(tmp_path, "c0")
            self._commit_empty(tmp_path, "c1")
            self._commit_empty(tmp_path, "c2")
            self._write_architecture(tmp_path, f"forge-map-commit: {sha0}\n")

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("2 commit(s) behind HEAD", out)

    def test_non_ancestor_sha_reports_diverged_not_fresh(self):
        # THE regression fg-a100 closes: a well-formed sha that is not an
        # ancestor of HEAD (e.g. diverged/rewritten history) must not be
        # reported as fresh. Pre-fix, git rev-list --count on an invalid/
        # non-ancestor sha silently yielded an empty/0 "behind" count, so
        # the old code mislabeled this state "fresh".
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            fake_sha = _fake_sha("fg-a100-non-ancestor-sha")
            self._write_architecture(tmp_path, f"forge-map-commit: {fake_sha}\n")

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("not an ancestor of HEAD", out)
            self.assertNotIn("is fresh", out)

    def test_header_missing_reports_missing_or_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            self._write_architecture(tmp_path, "# Architecture\nNo header line here.\n")

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("header missing or malformed", out)

    def test_header_malformed_sha_reports_missing_or_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            self._write_architecture(tmp_path, "forge-map-commit: zzzz\n")

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("header missing or malformed", out)


class TestSessionStartInjectMemoryFactCount(HooksTestBase):
    """fg-a10915: the "N fact(s)" figure must count only real fact-index
    bullets ("- [name](file.md) - type - desc"), not every top-level "- "
    bulleted line -- a "## Notes" section with its own unrelated bullets
    must not inflate the count."""

    def _write_memory(self, project_dir, body):
        mem_dir = pathlib.Path(project_dir) / ".forge" / "memory"
        mem_dir.mkdir(parents=True)
        (mem_dir / "MEMORY.md").write_text(body, encoding="utf-8", newline="\n")

    _REAL_BULLETS = "\n".join(
        f"- [fact-{i}](fact-{i}.md) — gotcha — description {i}."
        for i in range(1, 7)
    )

    def test_notes_section_bullets_are_not_counted_as_facts(self):
        # 6 real fact-index bullets plus a "## Notes" section with 2
        # unrelated "- " bullets must still report "(6 fact(s))", not 8.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            body = (
                "# Project memory index\n\n"
                f"{self._REAL_BULLETS}\n\n"
                "## Notes\n"
                "- this is an unrelated note bullet\n"
                "- so is this one\n"
            )
            self._write_memory(tmp_path, body)

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("(6 fact(s))", out)
            self.assertNotIn("(8 fact(s))", out)

    def test_only_real_fact_bullets_reports_exact_count(self):
        # No extraneous section: the count must still be exactly correct
        # (no regression in the ordinary/unaffected case).
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            body = "# Project memory index\n\n" + self._REAL_BULLETS + "\n"
            self._write_memory(tmp_path, body)

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("(6 fact(s))", out)


class TestSessionStartInjectOnboardingNudge(HooksTestBase):
    """2026-07-20 consolidation (onboard-offer-nudge): the no-.forge/ onboard
    line moved out of this hook into onboard-nudge.sh (which adds the
    substantial-repo heuristic, once-per-day dedupe, and opt-out Feature).
    This hook now stays SILENT for a repo with no .forge/ -- both hooks
    printing would double-voice the offer every session forever."""

    def test_git_repo_without_forge_dir_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            # Deliberately no .forge/ directory created.

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_non_git_directory_without_forge_dir_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            # Not a git repo at all, and no .forge/ - nothing to nudge about.

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")


class TestSessionStartInjectAgentsMdDispatchNudge(HooksTestBase):
    """fg-b0309: when a repo's root AGENTS.md exists (the onboard-step-6a
    signal it has been through Forge onboarding at least once), the hook
    appends one short clause reinforcing that subagent dispatch routes
    through Forge agents, not ad hoc calls. Absent AGENTS.md, output must
    stay byte-identical to pre-existing behavior."""

    _CLAUSE = "Subagent dispatch in this repo routes through Forge agents, not ad hoc calls."

    def _write_architecture(self, project_dir, body):
        map_dir = pathlib.Path(project_dir) / ".forge" / "map"
        map_dir.mkdir(parents=True)
        (map_dir / "architecture.md").write_text(body, encoding="utf-8", newline="\n")

    def test_agents_md_present_appends_dispatch_clause(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            head = self._commit_empty(tmp_path, "c0")
            self._write_architecture(tmp_path, f"forge-map-commit: {head}\n")
            (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8", newline="\n")

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("repo map is fresh", out)
            self.assertIn(self._CLAUSE, out)

    def test_agents_md_absent_leaves_output_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            head = self._commit_empty(tmp_path, "c0")
            self._write_architecture(tmp_path, f"forge-map-commit: {head}\n")
            # Deliberately no AGENTS.md at root.

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("repo map is fresh", out)
            self.assertNotIn(self._CLAUSE, out)

    def test_agents_md_present_without_forge_dir_stays_silent(self):
        # Boundary case: AGENTS.md present but .forge/ absent -- since the
        # 2026-07-20 consolidation the no-.forge/ path is silent here (the
        # onboard offer lives in onboard-nudge.sh), and the dispatch clause
        # stays scoped to the .forge-present branch.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8", newline="\n")
            # Deliberately no .forge/ directory created.

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")


class TestLoopGuard(HooksTestBase):
    def test_forge_start_prompt_injects_kernel_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdin = json.dumps({"prompt": "/forge:start --max-tasks 3"})
            rc, out, _err = self._run(LOOP_GUARD_SCRIPT, tmp, stdin)
            self.assertEqual(rc, 0)
            self.assertIn("hookSpecificOutput", out)
            self.assertIn("UserPromptSubmit", out)
            self.assertIn("You are the Forge kernel loop", out)
            self.assertIn("follow forge:kernel only", out)

    def test_unrelated_prompt_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdin = json.dumps({"prompt": "please review this diff"})
            rc, out, _err = self._run(LOOP_GUARD_SCRIPT, tmp, stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_prompt_mentioning_forge_start_is_silent(self):
        # Regression for fg-a10913: a prompt that merely MENTIONS
        # /forge:start (e.g. asking about it) must not fire the
        # kernel-identity-reassertion injection - only a genuine invocation
        # (the prompt's own command) should.
        with tempfile.TemporaryDirectory() as tmp:
            stdin = json.dumps({"prompt": "What does /forge:start actually do?"})
            rc, out, _err = self._run(LOOP_GUARD_SCRIPT, tmp, stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_forge_start_invocation_with_args_still_injects(self):
        # Regression for fg-a10913: the real invocation case (prompt starts
        # with /forge:start) must keep firing after the substring-match fix.
        with tempfile.TemporaryDirectory() as tmp:
            stdin = json.dumps({"prompt": "/forge:start --max-tasks 3"})
            rc, out, _err = self._run(LOOP_GUARD_SCRIPT, tmp, stdin)
            self.assertEqual(rc, 0)
            self.assertIn("hookSpecificOutput", out)
            self.assertIn("UserPromptSubmit", out)
            self.assertIn("You are the Forge kernel loop", out)
            self.assertIn("follow forge:kernel only", out)

    def test_empty_stdin_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, _err = self._run(LOOP_GUARD_SCRIPT, tmp, "")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")


class TestBudgetGuard(HooksTestBase):
    """budget-guard.sh is the ONE hook allowed to block (deny decision); it
    must still be fail-silent on anything unexpected."""

    def _write_forge_md(self, project_dir, cap_line):
        forge_dir = pathlib.Path(project_dir) / ".forge"
        forge_dir.mkdir(parents=True)
        (forge_dir / "forge.md").write_text(
            "# Forge config\n\n## Budgets\n"
            f"- {cap_line}\n- session-token-cap: none\n",
            encoding="utf-8",
            newline="\n",
        )

    def _run_guard(self, project_dir, tmpdir, session_id):
        stdin = json.dumps({"session_id": session_id,
                            "tool_name": "Task",
                            "tool_input": {"prompt": "spawn contract"}})
        # Forward slashes so the msys/git-bash script handles the path cleanly.
        extra_env = {"TMPDIR": str(tmpdir).replace("\\", "/")}
        return self._run(BUDGET_GUARD_SCRIPT, project_dir, stdin, extra_env)

    def test_denies_after_cap_exceeded(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as counter_tmp:
            self._write_forge_md(tmp, "max-tasks-per-session: 2")
            sid = "sess-budget-deny"
            for _ in range(2):
                rc, out, _err = self._run_guard(tmp, counter_tmp, sid)
                self.assertEqual(rc, 0)
                self.assertEqual(out, "")
            rc, out, _err = self._run_guard(tmp, counter_tmp, sid)
            self.assertEqual(rc, 0)
            self.assertIn('"permissionDecision":"deny"', out)
            self.assertIn("Forge budget cap reached (2 tasks)", out)

    def test_cap_none_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as counter_tmp:
            self._write_forge_md(tmp, "max-tasks-per-session: none")
            for _ in range(4):
                rc, out, _err = self._run_guard(tmp, counter_tmp, "sess-nocap")
                self.assertEqual(rc, 0)
                self.assertEqual(out, "")

    def test_missing_forge_md_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as counter_tmp:
            rc, out, _err = self._run_guard(tmp, counter_tmp, "sess-noforge")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_sessions_count_independently(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as counter_tmp:
            self._write_forge_md(tmp, "max-tasks-per-session: 1")
            rc, out, _err = self._run_guard(tmp, counter_tmp, "sess-aaaa")
            self.assertEqual(out, "")
            rc, out, _err = self._run_guard(tmp, counter_tmp, "sess-aaaa")
            self.assertIn('"permissionDecision":"deny"', out)
            # A different session id starts from zero.
            rc, out, _err = self._run_guard(tmp, counter_tmp, "sess-bbbb")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_hostile_session_id_with_path_chars_stays_confined_to_tmpdir(self):
        # M1-adjacent regression: a session_id carrying path-traversal chars
        # must not let the counter escape TMPDIR into an arbitrary sibling
        # path. The existing `tr -cd 'A-Za-z0-9._-'` sanitization strips
        # slashes entirely (not path-join them), so confirm the hook still
        # behaves correctly (counts, then denies) and writes only inside
        # counter_tmp, never into a subdirectory or above it.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as counter_tmp:
            self._write_forge_md(tmp, "max-tasks-per-session: 1")
            hostile_sid = "../../../../etc/passwd"
            rc, out, _err = self._run_guard(tmp, counter_tmp, hostile_sid)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            rc, out, _err = self._run_guard(tmp, counter_tmp, hostile_sid)
            self.assertEqual(rc, 0)
            self.assertIn('"permissionDecision":"deny"', out)

            counter_dir = pathlib.Path(counter_tmp)
            entries = list(counter_dir.iterdir())
            # Every counter file the hook created lives directly inside
            # counter_tmp (flat), with no path separators surviving in the
            # filename and nothing written outside counter_tmp.
            self.assertTrue(entries, "expected the hook to create a counter file")
            for entry in entries:
                self.assertTrue(entry.is_file())
                self.assertEqual(entry.parent, counter_dir)
                # Dots survive sanitization (allowed chars) but path
                # separators must not: that's what would let the write
                # escape counter_tmp into a sibling/parent directory.
                self.assertNotIn("/", entry.name)
                self.assertNotIn("\\", entry.name)

    def test_symlinked_counter_target_is_never_written(self):
        # M1: a pre-planted symlink at the predicted counter path must not
        # be followed for the append -- the hook should refuse (fail
        # silent) rather than write through it into an arbitrary target.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as counter_tmp:
            self._write_forge_md(tmp, "max-tasks-per-session: 5")
            sid = "sess-symlink-target"
            counter_dir = pathlib.Path(counter_tmp)
            decoy = counter_dir / "decoy.txt"
            decoy.write_text("", encoding="utf-8")
            counter_path = counter_dir / f"forge-dispatch-count-{sid}"
            try:
                counter_path.symlink_to(decoy)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not permitted in this environment")

            rc, out, _err = self._run_guard(tmp, counter_tmp, sid)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertEqual(decoy.read_text(encoding="utf-8"), "",
                              "hook must not have written through the symlink")

    def _predicted_fallback_key(self, extra_env):
        # Computes the exact fallback key budget-guard.sh derives when
        # stdin carries no session_id (historically "ppid-$PPID-$(date)"),
        # by asking a bash process spawned the same way (subprocess.run,
        # no shell wrapper) what PPID and UTC date it observes. This is
        # independent of budget-guard.sh's own logic, so it stays valid
        # whether or not the hook still uses this formula.
        env = dict(os.environ)
        env.update(extra_env)
        result = subprocess.run(
            [BASH, "-c", 'printf "ppid-%s-%s" "$PPID" "$(date -u +%Y%m%d)"'],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip()

    def test_missing_session_id_does_not_inherit_stale_fallback_counter(self):
        # C-6 regression (inquest maiden tribunal, 2026-07-18): the
        # fallback key used when stdin carries no session_id was
        # "ppid-$PPID-$(date)" - zero session-unique entropy. Pre-seed a
        # counter file at that exact key (simulating a dead/unrelated
        # session's leftover count sitting at the collidable key) and
        # confirm a brand-new session's dispatch, which also has no
        # session_id, is never spuriously denied because of it.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as counter_tmp:
            self._write_forge_md(tmp, "max-tasks-per-session: 1")
            extra_env = {"TMPDIR": str(counter_tmp).replace("\\", "/")}
            fallback_key = self._predicted_fallback_key(extra_env)
            self.assertTrue(fallback_key.startswith("ppid-"), fallback_key)

            counter_path = pathlib.Path(counter_tmp) / f"forge-dispatch-count-{fallback_key}"
            # A stale/dead session's count already sitting at the cap,
            # at the exact key a fresh no-session_id dispatch would use.
            counter_path.write_text("1\n", encoding="utf-8")

            stdin = json.dumps({"tool_name": "Task",
                                "tool_input": {"prompt": "spawn contract"}})
            rc, out, _err = self._run(BUDGET_GUARD_SCRIPT, tmp, stdin, extra_env)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "",
                              "a fresh session with no session_id must not "
                              "inherit a stale session's count via the "
                              "collidable PPID+date fallback key")

    def test_symlink_guard_present_in_source(self):
        # M1, source-level companion (always runs, no platform skip): the
        # behavioral test above requires symlink creation permission and is
        # skipped when unavailable (notably on Windows, where Git-bash
        # symlinks are commonly materialized as plain regular-file copies
        # rather than true symlinks). That skip would silently lose
        # coverage of the fix on such a box, so pin the guard at the source
        # level too -- confirms budget-guard.sh explicitly rejects a
        # symlinked counter path (`-f` alone dereferences symlinks and does
        # NOT catch this; an explicit `-L` check is required) before ever
        # appending to it.
        source = BUDGET_GUARD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('[ -L "$counter" ]', source)


class TestSessionEndLearnQuiescence(HooksTestBase):
    """fg-a10906: the Stop-hook LEARN nudge must stay silent while a Forge
    task is claimed (in-flight background worker/bounce) and must not spend
    the once-per-session debounce marker on that silence -- so the nudge can
    still fire later in the same session once the claim is released."""

    def _run_learn(self, project_dir, marker_tmp, session_id="sess-quiescence-fixed"):
        stdin = json.dumps({"session_id": session_id})
        extra_env = {"TMPDIR": str(marker_tmp).replace("\\", "/")}
        return self._run(SESSION_END_LEARN_SCRIPT, project_dir, stdin, extra_env)

    def _make_dirty_forge_repo(self, tmp_path):
        self._init_repo(tmp_path)
        self._commit_empty(tmp_path, "c0")
        (tmp_path / ".forge").mkdir()
        # An uncommitted change so `git status --porcelain` is dirty.
        (tmp_path / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

    def _write_task(self, tmp_path, task_name, claimed_by):
        tasks_dir = tmp_path / ".forge" / "queue" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (tasks_dir / f"{task_name}.md").write_text(
            "---\n"
            f"id: {task_name}\n"
            "state: ready\n"
            f"claimed-by: {claimed_by}\n"
            "---\n\n## Acceptance criteria\nplaceholder\n",
            encoding="utf-8",
            newline="\n",
        )

    def test_dirty_and_claimed_task_stays_silent_and_leaves_marker_untouched(self):
        # Criterion 1: dirty tree + a claimed in-flight task -> silent, and
        # the once-per-session marker must NOT be written (so the nudge can
        # still fire later once the claim clears).
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as marker_tmp:
            tmp_path = pathlib.Path(tmp)
            self._make_dirty_forge_repo(tmp_path)
            self._write_task(tmp_path, "fg-inflight",
                              "sess-ab12 @ 2026-07-18T12:00:00Z")

            rc, out, _err = self._run_learn(tmp_path, marker_tmp)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

            marker = pathlib.Path(marker_tmp) / "forge-learn-nudge-sess-quiescence-fixed"
            self.assertFalse(marker.exists(),
                              "marker must not be consumed while a task is claimed")

    def test_dirty_and_no_claimed_task_keeps_existing_nag_unchanged(self):
        # Criterion 2: dirty tree + no claimed task -> byte-for-byte existing
        # nag behavior (message + marker write), whether the tasks dir has
        # only unclaimed tasks or is absent entirely.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as marker_tmp:
            tmp_path = pathlib.Path(tmp)
            self._make_dirty_forge_repo(tmp_path)
            self._write_task(tmp_path, "fg-idle", "null")

            rc, out, _err = self._run_learn(tmp_path, marker_tmp)
            self.assertEqual(rc, 0)
            self.assertIn('"hookSpecificOutput"', out)
            self.assertIn('"hookEventName":"Stop"', out)
            self.assertIn(
                "Forge: uncommitted changes present at session end - if this "
                "session learned something durable, run the kernel LEARN "
                "step to file a memory fact before finishing (nudging once; "
                "will stay quiet for the rest of this session).",
                out,
            )

            marker = pathlib.Path(marker_tmp) / "forge-learn-nudge-sess-quiescence-fixed"
            self.assertTrue(marker.exists(), "existing nag path must still write the marker")

    def test_dirty_no_tasks_dir_at_all_keeps_existing_nag_unchanged(self):
        # The tasks dir may not exist at all -- must be treated as "not
        # claimed" and fall through to the existing nag, not error out.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as marker_tmp:
            tmp_path = pathlib.Path(tmp)
            self._make_dirty_forge_repo(tmp_path)
            # No .forge/queue/tasks directory created at all.

            rc, out, _err = self._run_learn(tmp_path, marker_tmp)
            self.assertEqual(rc, 0)
            self.assertIn('"hookSpecificOutput"', out)

    def test_marker_not_consumed_while_claimed_then_nudges_after_release(self):
        # Criterion 3, the debounce-preservation regression: two dirty+claimed
        # calls in a row must both stay silent without touching the marker,
        # and a THIRD dirty call -- after the claim is released -- must still
        # nudge (proving the earlier silent calls never spent the debounce).
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as marker_tmp:
            tmp_path = pathlib.Path(tmp)
            self._make_dirty_forge_repo(tmp_path)
            self._write_task(tmp_path, "fg-inflight",
                              "sess-ab12 @ 2026-07-18T12:00:00Z")

            rc1, out1, _err = self._run_learn(tmp_path, marker_tmp)
            rc2, out2, _err = self._run_learn(tmp_path, marker_tmp)
            self.assertEqual((rc1, out1), (0, ""))
            self.assertEqual((rc2, out2), (0, ""))

            marker = pathlib.Path(marker_tmp) / "forge-learn-nudge-sess-quiescence-fixed"
            self.assertFalse(marker.exists())

            # Claim released.
            self._write_task(tmp_path, "fg-inflight", "null")

            rc3, out3, _err = self._run_learn(tmp_path, marker_tmp)
            self.assertEqual(rc3, 0)
            self.assertIn('"hookSpecificOutput"', out3)
            self.assertTrue(marker.exists())

    def test_claimed_check_failure_falls_through_to_existing_behavior(self):
        # Fail-silent discipline: if the claimed-task dir exists but is
        # unreadable/unusual, the hook must never crash or block the stop --
        # it must fall through to the existing nag behavior.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as marker_tmp:
            tmp_path = pathlib.Path(tmp)
            self._make_dirty_forge_repo(tmp_path)
            tasks_dir = tmp_path / ".forge" / "queue" / "tasks"
            tasks_dir.mkdir(parents=True)
            # A malformed/empty task file with no claimed-by field at all.
            (tasks_dir / "fg-malformed.md").write_text(
                "not even frontmatter\n", encoding="utf-8", newline="\n"
            )

            rc, out, _err = self._run_learn(tmp_path, marker_tmp)
            self.assertEqual(rc, 0)
            self.assertIn('"hookSpecificOutput"', out)


class TestAgentProvenanceFlag(HooksTestBase):
    """fg-b0310 (spec-b71f3a): agent-provenance-flag.sh is a fail-silent,
    NEVER-blocking PreToolUse hook on the Task|Agent matcher. It never
    denies a dispatch -- it only appends a line to
    .forge/telemetry/dispatch-provenance.log when a NAMED, non-generic
    subagent_type resolves to no Forge agent file (roster, project-local,
    or the generic/catch-all archive-tier transport)."""

    LOG_PATH = pathlib.Path(".forge") / "telemetry" / "dispatch-provenance.log"

    def _init_forge(self, project_dir):
        forge_dir = pathlib.Path(project_dir) / ".forge"
        forge_dir.mkdir(parents=True, exist_ok=True)

    def _run_hook(self, project_dir, subagent_type=None, extra_env=None,
                   raw_stdin=None):
        if raw_stdin is None:
            payload = {"tool_name": "Task", "tool_input": {"prompt": "x"}}
            if subagent_type is not None:
                payload["tool_input"]["subagent_type"] = subagent_type
            stdin = json.dumps(payload)
        else:
            stdin = raw_stdin
        return self._run(AGENT_PROVENANCE_SCRIPT, project_dir, stdin, extra_env)

    def _log_lines(self, project_dir):
        log = pathlib.Path(project_dir) / self.LOG_PATH
        if not log.is_file():
            return []
        return [l for l in log.read_text(encoding="utf-8").splitlines() if l]

    def test_forge_roster_dispatch_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as plugin_root:
            self._init_forge(tmp)
            agents_dir = pathlib.Path(plugin_root) / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "forge-worker.md").write_text(
                "# forge-worker\n", encoding="utf-8", newline="\n"
            )
            extra_env = {"CLAUDE_PLUGIN_ROOT": str(plugin_root).replace("\\", "/")}
            rc, out, _err = self._run_hook(tmp, "forge:forge-worker", extra_env)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertEqual(self._log_lines(tmp), [])

    def test_project_local_dispatch_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            local_agents = pathlib.Path(tmp) / ".forge" / "agents"
            local_agents.mkdir(parents=True)
            (local_agents / "acme-fixture-builder.md").write_text(
                "# acme-fixture-builder\n", encoding="utf-8", newline="\n"
            )
            rc, out, _err = self._run_hook(tmp, "acme-fixture-builder")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertEqual(self._log_lines(tmp), [])

    def test_claude_agents_mirror_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            mirror_agents = pathlib.Path(tmp) / ".claude" / "agents"
            mirror_agents.mkdir(parents=True)
            (mirror_agents / "acme-fixture-builder.md").write_text(
                "# acme-fixture-builder\n", encoding="utf-8", newline="\n"
            )
            rc, out, _err = self._run_hook(tmp, "acme-fixture-builder")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertEqual(self._log_lines(tmp), [])

    def test_generic_type_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            for subtype in ("general-purpose", "Explore"):
                rc, out, _err = self._run_hook(tmp, subtype)
                self.assertEqual(rc, 0)
                self.assertEqual(out, "")
            self.assertEqual(self._log_lines(tmp), [])

    def test_named_non_forge_type_flagged(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as plugin_root:
            self._init_forge(tmp)
            # Plugin root exists but has no matching roster file, and no
            # project-local file exists either -- this subagent_type is a
            # named, non-forge dispatch with no backing file anywhere.
            extra_env = {"CLAUDE_PLUGIN_ROOT": str(plugin_root).replace("\\", "/")}
            rc, out, _err = self._run_hook(tmp, "pr-review-toolkit:code-reviewer",
                                            extra_env)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "", "hook must never deny/emit output")
            lines = self._log_lines(tmp)
            self.assertEqual(len(lines), 1)
            self.assertIn("pr-review-toolkit:code-reviewer", lines[0])
            # timestamp + subagent_type, space-separated, single line
            ts = lines[0].split(" ", 1)[0]
            self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_missing_forge_dir_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            # No .forge/ created at all.
            rc, out, _err = self._run_hook(tmp, "pr-review-toolkit:code-reviewer")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertEqual(self._log_lines(tmp), [])

    def test_malformed_stdin_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            rc, out, _err = self._run_hook(tmp, raw_stdin="{not json at all")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertEqual(self._log_lines(tmp), [])

    def test_missing_subagent_type_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            stdin = json.dumps({"tool_name": "Task", "tool_input": {"prompt": "x"}})
            rc, out, _err = self._run_hook(tmp, raw_stdin=stdin)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertEqual(self._log_lines(tmp), [])

    def test_empty_stdin_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            rc, out, _err = self._run_hook(tmp, raw_stdin="")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_log_dir_created_on_first_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            telemetry_dir = pathlib.Path(tmp) / ".forge" / "telemetry"
            self.assertFalse(telemetry_dir.exists())
            rc, out, _err = self._run_hook(tmp, "some-random-plugin:agent")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            self.assertTrue(telemetry_dir.is_dir())
            self.assertEqual(len(self._log_lines(tmp)), 1)

    def test_multiple_flags_append_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            self._run_hook(tmp, "third-party:agent-one")
            self._run_hook(tmp, "third-party:agent-two")
            lines = self._log_lines(tmp)
            self.assertEqual(len(lines), 2)
            self.assertIn("third-party:agent-one", lines[0])
            self.assertIn("third-party:agent-two", lines[1])

    def test_traversal_slash_escapes_agents_dir_is_flagged(self):
        # Bounce fix (verifier P2/high): a subagent_type containing `../`
        # must not be allowed to resolve outside the intended agents
        # directories. Plant a real decoy .md file at the exact path
        # ".forge/agents/../../escapetest/passwd.md" resolves to (which
        # collapses back to "<project>/escapetest/passwd.md") and confirm
        # the traversal-shaped name is flagged, never silently treated as
        # a resolved Forge agent.
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            # .forge/agents/ must actually exist for this repro: MSYS/git-bash
            # `[ -f ]` resolves `..` by really walking the filesystem, so a
            # `../../` escape only succeeds through a directory that is
            # physically present -- exactly the common case in a real Forge
            # repo, which normally has .forge/agents/ once any project-local
            # agent has ever been minted.
            (pathlib.Path(tmp) / ".forge" / "agents").mkdir(parents=True)
            decoy_dir = pathlib.Path(tmp) / "escapetest"
            decoy_dir.mkdir(parents=True)
            (decoy_dir / "passwd.md").write_text("secret\n", encoding="utf-8")
            rc, out, _err = self._run_hook(tmp, "../../escapetest/passwd")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            lines = self._log_lines(tmp)
            self.assertEqual(len(lines), 1)
            self.assertIn("../../escapetest/passwd", lines[0])

    def test_traversal_slash_with_forge_prefix_is_flagged(self):
        # Same escape, but behind the "forge:" prefix -- the prefix strip
        # must not bypass the traversal rejection either.
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            (pathlib.Path(tmp) / ".forge" / "agents").mkdir(parents=True)
            decoy_dir = pathlib.Path(tmp) / "escapetest"
            decoy_dir.mkdir(parents=True)
            (decoy_dir / "passwd.md").write_text("secret\n", encoding="utf-8")
            rc, out, _err = self._run_hook(tmp, "forge:../../escapetest/passwd")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            lines = self._log_lines(tmp)
            self.assertEqual(len(lines), 1)
            self.assertIn("../../escapetest/passwd", lines[0])

    def test_traversal_backslash_is_flagged(self):
        # Windows path separator (this is Git Bash on Windows): a
        # subagent_type using backslash segments (e.g. "a\..\b", which
        # nets to a legitimate-looking "b.md" inside .forge/agents/) must
        # be rejected outright, not resolved via backslash-as-separator.
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            local_agents = pathlib.Path(tmp) / ".forge" / "agents"
            local_agents.mkdir(parents=True)
            (local_agents / "b.md").write_text("secret\n", encoding="utf-8")
            rc, out, _err = self._run_hook(tmp, "a\\..\\b")
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")
            lines = self._log_lines(tmp)
            self.assertEqual(len(lines), 1)
            self.assertIn("b", lines[0])

    def test_never_returns_deny_decision(self):
        # Behavioral pin: even for a clearly-flaggable dispatch, the hook's
        # stdout must never carry a permissionDecision -- budget-guard.sh
        # is the only hook allowed to block.
        with tempfile.TemporaryDirectory() as tmp:
            self._init_forge(tmp)
            rc, out, _err = self._run_hook(tmp, "some-unbacked-type")
            self.assertEqual(rc, 0)
            self.assertNotIn("permissionDecision", out)
            self.assertNotIn("deny", out)


class TestOnboardNudge(HooksTestBase):
    """onboard-offer-nudge: SessionStart, fail-silent, advisory-only offer
    to run /forge:onboard when the current project is a substantial dev
    repo with no .forge/ yet. Never fires twice for the same repo+day, and
    never writes anything into the target repo itself -- its dedupe marker
    lives under an injectable state dir (FORGE_ONBOARD_NUDGE_STATE_DIR),
    kept as a fresh tempdir per test so tests never touch real machine temp
    state or collide with each other."""

    def _run_onboard(self, project_dir, state_dir, plugin_root=None,
                     extra_env=None):
        extra_env = dict(extra_env or {})
        extra_env["FORGE_ONBOARD_NUDGE_STATE_DIR"] = str(state_dir)
        if plugin_root is not None:
            extra_env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root).replace("\\", "/")
        return self._run(ONBOARD_NUDGE_SCRIPT, project_dir, extra_env=extra_env)

    def _snapshot(self, project_dir):
        # Every path under project_dir except .git internals -- used to
        # prove the hook never writes into the target repo.
        out = set()
        for p in pathlib.Path(project_dir).rglob("*"):
            rel = p.relative_to(project_dir)
            if rel.parts and rel.parts[0] == ".git":
                continue
            out.add(rel.as_posix())
        return out

    def test_manifest_repo_without_forge_dir_fires_advisory_line(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "package.json").write_text("{}", encoding="utf-8")
            subprocess.run(["git", "add", "package.json"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")
            # Deliberately no .forge/ directory created.

            before = self._snapshot(tmp_path)
            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertIn("hookSpecificOutput", out)
            self.assertIn("/forge:onboard", out)
            payload = json.loads(out)
            self.assertEqual(
                payload["hookSpecificOutput"]["hookEventName"], "SessionStart"
            )
            # Never writes into the target repo -- only the machine-local
            # state dir (outside the repo) is touched.
            self.assertEqual(self._snapshot(tmp_path), before)

    def test_repeat_same_day_same_repo_is_deduped(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
            subprocess.run(["git", "add", "go.mod"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc1, out1, _ = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc1, 0)
            self.assertIn("/forge:onboard", out1)

            rc2, out2, _ = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc2, 0)
            self.assertEqual(out2, "", "second run same day must be silent")

    def test_dedupe_check_ordered_before_git_and_heuristic(self):
        # 2026-07-20 grouped re-verify P1 (two rounds): the marker-EXISTENCE
        # check must come before EVERY git subprocess, not just the ls-files
        # scan — the two `git rev-parse` calls alone cost ~100ms each here,
        # keeping the deduped path at ~236ms vs the ~60ms .forge-present
        # benchmark. The marker WRITE stays after the heuristic fires.
        raw = ONBOARD_NUDGE_SCRIPT.read_text(encoding="utf-8")
        # Strip comment lines so prose mentioning git doesn't shadow the
        # actual command ordering.
        text = "\n".join(
            line for line in raw.splitlines()
            if not line.lstrip().startswith("#"))
        check_idx = text.index('[ -e "$marker" ] && exit 0')
        git_idx = text.index("git rev-parse")
        scan_idx = text.index("git ls-files")
        write_idx = text.index(': > "$marker"')
        self.assertLess(check_idx, git_idx,
                        "marker existence check must precede all git calls")
        self.assertLess(check_idx, scan_idx,
                        "marker existence check must precede the heuristic scan")
        self.assertLess(scan_idx, write_idx,
                        "marker write must stay after the heuristic fires")

    def test_deduped_repeat_call_forks_no_external_commands(self):
        # Mechanism test for the speed bar (a wall-clock assertion would be
        # flaky in CI; zero-external-forks is the deterministic property the
        # timing depends on — the round-3 re-verify measured EACH fork of
        # git, tr, or date at 45-105ms): first run fires and writes the
        # marker, then git/tr/date are all replaced with poisoned shims
        # that record every invocation — the second run must exit 0, print
        # nothing, and invoke none of them.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir, \
                tempfile.TemporaryDirectory() as bin_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
            subprocess.run(["git", "add", "go.mod"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc1, out1, _ = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc1, 0)
            self.assertIn("/forge:onboard", out1)

            sentinels = {}
            for cmd in ("git", "tr", "date"):
                sentinel = pathlib.Path(bin_dir) / (cmd + "-was-called")
                shim = pathlib.Path(bin_dir) / cmd
                shim.write_text(
                    "#!/bin/sh\n: > '%s'\nexit 1\n"
                    % str(sentinel).replace("\\", "/"),
                    encoding="utf-8", newline="\n")
                shim.chmod(0o755)
                sentinels[cmd] = sentinel

            rc2, out2, _ = self._run_onboard(
                tmp_path, state_dir,
                extra_env={"PATH": bin_dir + os.pathsep + os.environ["PATH"]})
            self.assertEqual(rc2, 0)
            self.assertEqual(out2, "", "second run same day must be silent")
            for cmd, sentinel in sentinels.items():
                self.assertFalse(
                    sentinel.exists(),
                    "deduped repeat call must not invoke " + cmd)

    def test_forge_dir_present_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            (tmp_path / ".forge").mkdir()
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_non_git_directory_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            (tmp_path / "package.json").write_text("{}", encoding="utf-8")
            # Deliberately never git-init'd.

            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_insufficient_source_files_and_no_manifest_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            for i in range(3):
                (tmp_path / f"note{i}.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_ten_tracked_source_files_without_manifest_fires(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            for i in range(10):
                (tmp_path / f"mod{i}.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertIn("/forge:onboard", out)

    def test_non_source_tracked_files_do_not_count_toward_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            for i in range(12):
                (tmp_path / f"doc{i}.md").write_text("# doc\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_opt_out_feature_disables_nudge(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir, \
                tempfile.TemporaryDirectory() as plugin_root:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            plugin_forge_dir = pathlib.Path(plugin_root) / ".forge"
            plugin_forge_dir.mkdir(parents=True)
            (plugin_forge_dir / "forge.md").write_text(
                "# Forge config\n\n## Features\n- onboard-nudge: off\n",
                encoding="utf-8",
            )

            rc, out, _err = self._run_onboard(tmp_path, state_dir, plugin_root)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_opt_out_feature_is_case_insensitive_and_bullet_tolerant(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir, \
                tempfile.TemporaryDirectory() as plugin_root:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            plugin_forge_dir = pathlib.Path(plugin_root) / ".forge"
            plugin_forge_dir.mkdir(parents=True)
            (plugin_forge_dir / "forge.md").write_text(
                "onboard-nudge:   OFF\n", encoding="utf-8"
            )

            rc, out, _err = self._run_onboard(tmp_path, state_dir, plugin_root)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_feature_default_on_when_plugin_forge_md_absent(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir, \
                tempfile.TemporaryDirectory() as plugin_root:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")
            # plugin_root exists but has no .forge/forge.md at all.

            rc, out, _err = self._run_onboard(tmp_path, state_dir, plugin_root)
            self.assertEqual(rc, 0)
            self.assertIn("/forge:onboard", out)

    def test_dedupe_marker_written_outside_target_repo(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "package.json").write_text("{}", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertIn("/forge:onboard", out)
            markers = list(pathlib.Path(state_dir).iterdir())
            self.assertEqual(len(markers), 1)

    def test_never_returns_permission_decision(self):
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as state_dir:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            (tmp_path / "package.json").write_text("{}", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                            capture_output=True)
            self._commit_empty(tmp_path, "c0")

            rc, out, _err = self._run_onboard(tmp_path, state_dir)
            self.assertEqual(rc, 0)
            self.assertNotIn("permissionDecision", out)
            self.assertNotIn('"deny"', out)


class TestGitAttributes(unittest.TestCase):
    def test_sh_files_forced_to_lf(self):
        self.assertTrue(GITATTRIBUTES.is_file(), ".gitattributes must exist at repo root")
        content = GITATTRIBUTES.read_text(encoding="utf-8")
        matches = [
            line for line in content.splitlines()
            if line.strip().startswith("*.sh") and "eol=lf" in line
        ]
        self.assertTrue(
            matches,
            "expected a '*.sh ... eol=lf' line in .gitattributes, got:\n" + content,
        )


if __name__ == "__main__":
    unittest.main()
