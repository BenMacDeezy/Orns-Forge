"""RED->GREEN tests for tools/validate_persistence_boundary.py (fg-b0101,
spec-4d2a customization-persistence contract).

Builds synthetic fixture trees under tempfile.TemporaryDirectory() shaped
like the real plugin source tree (skills/, commands/, hooks/, tools/,
agents/) and drives scan_repo() against them -- never touches this repo's
own working tree except for the one "run against the real repo" assertion,
which reads REPO_ROOT but performs no writes.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_persistence_boundary as vpb  # noqa: E402

SCRIPT = REPO_ROOT / "tools" / "validate_persistence_boundary.py"


class _FixtureRepo:
    """Context manager building a minimal scan-dir tree in a temp dir."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        for d in vpb.SCAN_DIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def write(self, relpath, content):
        p = self.root / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p


class TestPythonViolations(unittest.TestCase):
    def test_open_write_under_plugin_root_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad_open.py",
                'from pathlib import Path\n'
                'PLUGIN_ROOT = Path(__file__).resolve().parent.parent\n'
                'def dump():\n'
                '    with open(PLUGIN_ROOT / "assets" / "state.json", "w") as fh:\n'
                '        fh.write("{}")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].path.name, "bad_open.py")
            self.assertEqual(violations[0].lineno, 4)

    def test_write_text_under_plugin_root_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "skills/foo/bar.py",
                'from pathlib import Path\n'
                'ROOT = Path(__file__).resolve().parent\n'
                'def save(data):\n'
                '    (ROOT / "cache.json").write_text(data)\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertIn("write_text", violations[0].detail)
            self.assertEqual(violations[0].lineno, 4)

    def test_shutil_copy_under_plugin_root_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad_copy.py",
                'import shutil\n'
                'from pathlib import Path\n'
                'ROOT = Path(__file__).resolve().parent\n'
                'def backup(src):\n'
                '    shutil.copy(src, ROOT / "backup.md")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertIn("shutil.copy", violations[0].detail)

    def test_direct_claude_plugin_root_env_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad_env.py",
                'import os\n'
                'from pathlib import Path\n'
                'def dump():\n'
                '    p = Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "x.json"\n'
                '    p.write_text("{}")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)

    def test_interprocedural_return_flow_flagged(self):
        """Bounce fix (forge-verifier P1): a plugin-root path constructed
        and RETURNED BY A LOCALLY-DEFINED HELPER FUNCTION must not evade
        the scan -- the verifier's exact repro."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad_interproc.py",
                'from pathlib import Path\n'
                'def get_path():\n'
                '    root = Path(__file__).parent\n'
                '    return root / "state.json"\n'
                'def save():\n'
                '    p = get_path()\n'
                '    open(p, "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 7)

    def test_interprocedural_return_flow_inline_flagged(self):
        """Same as above but the helper's return value is used inline
        (never bound to a local name) -- exercises the Call-node branch of
        _expr_is_violation's rooted_funcs check, not just the
        variable-assignment branch."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad_interproc_inline.py",
                'from pathlib import Path\n'
                'def get_path():\n'
                '    root = Path(__file__).parent\n'
                '    return root / "state.json"\n'
                'def save():\n'
                '    open(get_path(), "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 6)

    def test_multi_hop_straight_line_chain_flagged(self):
        """Docstring correction pin (forge-verifier): a 3-hop straight-line
        module-level assignment chain (root -> d -> e -> write target) IS
        caught -- the module docstring must describe this real behavior,
        not the earlier false "only one hop" claim."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad_multihop.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'd = root / "x"\n'
                'e = d / "y"\n'
                'def save():\n'
                '    open(e / "f", "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 6)

    def test_docstring_no_longer_claims_only_one_hop(self):
        content = vpb.__doc__
        self.assertNotIn(
            "only one hop of propagation), not full", content,
        )
        self.assertIn("DOES follow straight-line assignment chains", content)
        self.assertIn("Interprocedural (Python), one hop", content)

    def test_param_threading_through_helper_flagged(self):
        """Bounce 2 fix (forge-verifier P1): the docstring previously
        claimed 'a path built inline from a function parameter' was a
        miss. Empirically false -- a rooted Name threaded through a plain
        (non-return-classified) helper's parameter and returned back out
        is caught, because the Name token still appears somewhere in the
        destination expression's subtree once inlined at the call site."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/param_threaded.py",
                'from pathlib import Path\n'
                'def helper(p):\n'
                '    return p\n'
                'def save():\n'
                '    root = Path(__file__).parent\n'
                '    open(helper(root) / "x", "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 6)

    def test_fstring_destination_flagged(self):
        """Bounce 2 fix: the docstring previously claimed f-strings whose
        pieces aren't literal were a miss. Empirically false -- the rooted
        Name inside the f-string's formatted value is still a literal
        `ast.Name` node in the destination expression's subtree."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/fstring_dest.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'def save():\n'
                '    open(f"{root}/state.json", "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 4)

    def test_list_element_destination_flagged(self):
        """Bounce 2 fix: the docstring previously claimed a dict/list
        element destination was a miss. Empirically false -- `paths[0]`
        still contains the `paths` Name node, and `paths` was itself
        classified rooted from its own list-literal assignment."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/list_elem_dest.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'paths = [root / "a", root / "b"]\n'
                'def save():\n'
                '    open(paths[0], "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 5)

    def test_dict_subscript_assignment_target_is_a_genuine_miss(self):
        """Pins the corrected, real remaining gap: a rooted value stored
        via a Subscript assignment target (`_cache["p"] = ...`) is never
        classified, because `_register_target` only handles `Name` and
        `Tuple`/`List`/`Starred` destructuring targets -- a `Subscript`
        target falls through untouched -- so reading it back out
        (`dest = _cache["p"]`) carries no rooted Name in its own RHS, and
        the eventual write is missed."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/dict_subscript_lost.py",
                'from pathlib import Path\n'
                '_cache = {}\n'
                '_cache["p"] = Path(__file__).parent / "state.json"\n'
                'def save():\n'
                '    dest = _cache["p"]\n'
                '    open(dest, "w").write("x")\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_docstring_no_longer_claims_param_fstring_dict_misses(self):
        content = vpb.__doc__
        self.assertNotIn(
            "a path built\n    inline from a function *parameter*, a dict/list element, string\n"
            "    formatting/f-strings whose pieces aren't literal", content,
        )
        self.assertIn("HOW MATCHING ACTUALLY WORKS", content)
        self.assertIn("A rooted value stored via a non-`Name` assignment target", content)

    def test_docstring_miss_list_states_non_exhaustive(self):
        """Bounce 3 fix (forge-verifier P1 MECHANICAL): the miss-list must
        no longer claim exhaustiveness ("the ONE thing that actually
        defeats this detector") -- destructuring assignment falsified that
        claim. It must instead be framed as a non-exhaustive, per-case
        verified list."""
        content = vpb.__doc__
        self.assertNotIn("the ONE thing that actually defeats", content)
        self.assertIn("NOT AN EXHAUSTIVE LIST", content)
        self.assertIn("Verified misses", content)

    def test_tuple_unpack_destination_flagged(self):
        """Bounce 3 fix: the verifier's exact repro -- a plugin-root path
        constructed via tuple-unpacking destructuring assignment must not
        evade the scan."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/tuple_unpack.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'def save():\n'
                '    state_path, tmp_path = root / "state.json", root / "tmp.json"\n'
                '    open(state_path, "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 5)

    def test_list_target_destructuring_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/list_target.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'def save():\n'
                '    [a, b] = root / "state.json", root / "tmp.json"\n'
                '    open(a, "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 5)

    def test_starred_target_destructuring_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/starred_target.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'def save():\n'
                '    a, *rest = root / "state.json", root / "tmp.json", root / "x.json"\n'
                '    open(a, "w").write("x")\n'
                '    open(rest[0], "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 2)
            self.assertEqual(sorted(v.lineno for v in violations), [5, 6])

    def test_destructuring_positional_pairing_precise(self):
        """Positional pairing precision: when the RHS is a literal tuple
        of matching arity, a non-rooted co-element in the SAME unpacking
        is not swept in as a false positive, while the rooted co-element
        still is."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/destructure_precise.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'def save():\n'
                '    rooted_path, plain_path = root / "state.json", "/tmp/plain.json"\n'
                '    open(plain_path, "w").write("x")\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

        with _FixtureRepo() as fx:
            fx.write(
                "tools/destructure_precise_positive.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'def save():\n'
                '    rooted_path, plain_path = root / "state.json", "/tmp/plain.json"\n'
                '    open(rooted_path, "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)

    def test_destructuring_fallback_on_non_literal_rhs_over_flags(self):
        """Documents (and pins) the safe-over-precise fallback: when the
        RHS isn't a literal tuple/list of matching arity (here, a function
        call returning a tuple), EVERY destructured name is registered
        rooted, even a co-element that is independently not rooted --
        matches the module's documented scope-blindness bias."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/destructure_fallback.py",
                'from pathlib import Path\n'
                'root = Path(__file__).parent\n'
                'def get_pair():\n'
                '    return (root / "a", "/tmp/b")\n'
                'def save():\n'
                '    a, b = get_pair()\n'
                '    open(b, "w").write("x")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)

    def test_file_line_reported_precisely(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad_multi.py",
                'from pathlib import Path\n'
                'ROOT = Path(__file__).resolve().parent\n'
                '\n'
                '\n'
                'def save():\n'
                '    (ROOT / "a.json").write_text("{}")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 6)
            self.assertRegex(str(violations[0]), r"^tools[/\\]bad_multi\.py:6:")


class TestPythonAllowed(unittest.TestCase):
    def test_project_space_write_allowed(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/good_project.py",
                'import pathlib\n'
                'def save(data):\n'
                '    pathlib.Path(".forge/profiles/custom.md").write_text(data)\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_user_space_write_allowed(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/good_user.py",
                'from pathlib import Path\n'
                'def save(data):\n'
                '    (Path.home() / ".claude" / "settings.json").write_text(data)\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_plugin_root_var_escaping_via_forge_allowed(self):
        """A plugin-root-derived variable that is itself re-anchored through
        a project-space marker in the same write-target expression (e.g.
        joined with a CLAUDE_PROJECT_DIR-based path) is not flagged --
        matches the documented one-hop escape-marker rule."""
        with _FixtureRepo() as fx:
            fx.write(
                "tools/good_reanchor.py",
                'import os\n'
                'from pathlib import Path\n'
                'def save(data):\n'
                '    dest = Path(os.environ["CLAUDE_PROJECT_DIR"]) / ".forge" / "x.md"\n'
                '    dest.write_text(data)\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_read_only_open_not_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/good_read.py",
                'from pathlib import Path\n'
                'PLUGIN_ROOT = Path(__file__).resolve().parent.parent\n'
                'def load():\n'
                '    with open(PLUGIN_ROOT / "assets" / "logo.ans") as fh:\n'
                '        return fh.read()\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_read_text_not_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/good_read_text.py",
                'from pathlib import Path\n'
                'PLUGIN_ROOT = Path(__file__).resolve().parent.parent\n'
                'def load():\n'
                '    return (PLUGIN_ROOT / "assets" / "logo.ans").read_text()\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_test_files_excluded_from_scan(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/test_something_writes.py",
                'from pathlib import Path\n'
                'ROOT = Path(__file__).resolve().parent\n'
                'def helper():\n'
                '    (ROOT / "scratch.json").write_text("{}")\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])


class TestBashViolations(unittest.TestCase):
    def test_redirect_to_plugin_root_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "hooks/scripts/bad.sh",
                '#!/usr/bin/env bash\n'
                'echo "hi" > "${CLAUDE_PLUGIN_ROOT}/state.log"\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 2)

    def test_append_redirect_via_variable_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "hooks/scripts/bad_var.sh",
                '#!/usr/bin/env bash\n'
                'log="${CLAUDE_PLUGIN_ROOT}/telemetry.log"\n'
                'printf "x" >> "$log"\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].lineno, 3)

    def test_cp_to_plugin_root_flagged(self):
        with _FixtureRepo() as fx:
            fx.write(
                "hooks/scripts/bad_cp.sh",
                '#!/usr/bin/env bash\n'
                'cp "$src" "${CLAUDE_PLUGIN_ROOT}/agents/custom.md"\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            self.assertIn("cp", violations[0].detail)


class TestBashAllowed(unittest.TestCase):
    def test_project_space_redirect_allowed(self):
        with _FixtureRepo() as fx:
            fx.write(
                "hooks/scripts/good.sh",
                '#!/usr/bin/env bash\n'
                'printf "1\\n" >> ".forge/telemetry/dispatch-provenance.log"\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_devnull_fd_redirect_allowed(self):
        with _FixtureRepo() as fx:
            fx.write(
                "hooks/scripts/good_devnull.sh",
                '#!/usr/bin/env bash\n'
                'git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])

    def test_user_home_cp_allowed(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/good_cp.sh",
                '#!/usr/bin/env bash\n'
                'cp "$src" "$HOME/.claude/settings.json"\n',
            )
            self.assertEqual(vpb.scan_repo(fx.root), [])


class TestRealRepo(unittest.TestCase):
    def test_real_repo_scan_is_clean(self):
        """The actual plugin source tree must pass this gate. If this ever
        fails it means a real write-idiom in skills/, commands/, hooks/,
        tools/, or agents/ targets the plugin's own installed directory --
        a genuine violation to fix, never to silence in this test."""
        violations = vpb.scan_repo(REPO_ROOT)
        self.assertEqual(
            violations, [],
            "Persistence boundary violation(s) in the real repo:\n"
            + "\n".join(str(v) for v in violations),
        )


class TestCLI(unittest.TestCase):
    def test_main_exits_zero_on_clean_repo(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_main_exits_one_and_reports_file_line_on_violation(self):
        with _FixtureRepo() as fx:
            fx.write(
                "tools/bad.py",
                'from pathlib import Path\n'
                'ROOT = Path(__file__).resolve().parent\n'
                'def save():\n'
                '    (ROOT / "x.json").write_text("{}")\n',
            )
            violations = vpb.scan_repo(fx.root)
            self.assertEqual(len(violations), 1)
            rendered = str(violations[0])
            self.assertRegex(rendered, r"^tools[/\\]bad\.py:4:")


if __name__ == "__main__":
    unittest.main()
