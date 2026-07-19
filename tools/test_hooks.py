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
    """fg-doctor-nudge: a git repo with Forge installed but no .forge/ yet
    used to exit silently, so nothing ever suggested onboarding it. The hook
    now nudges toward /forge:onboard instead of staying silent."""

    def test_git_repo_without_forge_dir_recommends_onboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            # Deliberately no .forge/ directory created.

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("hookSpecificOutput", out)
            self.assertIn("/forge:onboard", out)
            self.assertIn("no .forge/ yet", out)

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

    def test_agents_md_present_without_forge_dir_still_shows_onboard_nudge_only(self):
        # Boundary case: AGENTS.md present but .forge/ absent must still take
        # the existing no-.forge-yet onboard path untouched -- the dispatch
        # clause is scoped to the .forge-present branch, never the onboard
        # nudge's own output.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            self._init_repo(tmp_path)
            self._commit_empty(tmp_path, "c0")
            (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8", newline="\n")
            # Deliberately no .forge/ directory created.

            rc, out, _err = self._run(SESSION_START_SCRIPT, tmp_path)
            self.assertEqual(rc, 0)
            self.assertIn("hookSpecificOutput", out)
            self.assertIn("/forge:onboard", out)
            self.assertIn("no .forge/ yet", out)
            self.assertNotIn(self._CLAUSE, out)


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
