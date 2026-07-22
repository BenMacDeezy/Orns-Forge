"""Doc-pin regression tests for task `onboard-offer-nudge`: the SessionStart
onboard-offer nudge hook (hooks/scripts/onboard-nudge.sh). Sharded per the
fg-a11040 per-task-id-module convention so this task's pins land in their
own file instead of conflicting with concurrent tasks at a shared tail."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
)


class TestOnboardOfferNudgePins(unittest.TestCase):
    """onboard-offer-nudge: dated conventions.md section (TOC + Shards
    manifest + body), the hook script itself, its hooks.json registration,
    and the README's optional CLAUDE.md pairing snippet."""

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    SHARD_PATH = REPO_ROOT / "docs" / "conventions" / "dispatch-and-routing.md"
    HEADING = "## Onboard-offer nudge hook — 2026-07-20"

    @staticmethod
    def _read(path):
        return _read_path(path)

    def _section(self):
        content = self._read(self.CONVENTIONS_PATH)
        return content.split(self.HEADING, 1)[1].split("\n## ", 1)[0]

    def _norm_section(self):
        return " ".join(self._section().split())

    def test_conventions_corpus_has_dated_heading(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(self.HEADING, content)

    def test_conventions_toc_entry_present(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn("- Onboard-offer nudge hook — 2026-07-20\n", content)

    def test_shards_manifest_maps_to_dispatch_and_routing(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            "- `Onboard-offer nudge hook — 2026-07-20` -> "
            "`docs/conventions/dispatch-and-routing.md`",
            content,
        )

    def test_shard_file_actually_contains_the_section(self):
        shard = _cached_read_text(self.SHARD_PATH)
        self.assertIn(self.HEADING, shard)

    def test_section_cites_task_and_hook_file(self):
        section = self._section()
        self.assertIn(
            ".forge/queue/tasks/onboard-offer-nudge.md", section
        )
        self.assertIn("hooks/scripts/onboard-nudge.sh", section)
        self.assertIn("hooks/hooks.json", section)

    def test_section_states_the_heuristic(self):
        section = self._norm_section()
        self.assertIn("package.json", section)
        self.assertIn("pyproject.toml", section)
        self.assertIn("Cargo.toml", section)
        self.assertIn("go.mod", section)
        self.assertIn("*.sln", section)
        self.assertIn("at least 10 tracked files", section)

    def test_section_states_trust_boundary_never_writes_repo(self):
        section = self._norm_section()
        self.assertIn(
            "Never onboards, installs, or writes into the target repo",
            section,
        )
        self.assertIn("Forge acts only on human intent", section)

    def test_section_states_dedupe_mechanism(self):
        section = self._norm_section()
        self.assertIn("tools/update_check.py", section)
        self.assertIn("_cache_path()", section)
        self.assertIn("FORGE_ONBOARD_NUDGE_STATE_DIR", section)

    def test_section_states_opt_out_feature(self):
        section = self._norm_section()
        self.assertIn("onboard-nudge", section)
        self.assertIn("default `on`", section)
        self.assertIn("tools/banner.py", section)
        self.assertIn("startup-banner", section)

    def test_section_states_single_voice_and_speed_order(self):
        # 2026-07-20 verify fixes: only this hook prints the onboard offer
        # (session-start-inject.sh's ungated line removed), and the dedupe
        # existence check precedes the heuristic scan.
        section = self._norm_section()
        self.assertIn("Single voice + speed order (2026-07-20 verify fixes)",
                      section)
        self.assertIn("session-start-inject.sh", section)
        self.assertIn("double-voice", section)
        self.assertIn("BEFORE the `git ls-files` heuristic scan", section)

    def test_section_states_fail_silent(self):
        section = self._norm_section()
        self.assertIn("Fail-silent, no network, advisory only", section)
        self.assertIn("never blocks", section)
        self.assertIn("never denies", section)

    def test_hook_script_exists_and_registered(self):
        script = REPO_ROOT / "hooks" / "scripts" / "onboard-nudge.sh"
        self.assertTrue(script.is_file())
        hooks_json = _cached_read_text(REPO_ROOT / "hooks" / "hooks.json")
        self.assertIn("onboard-nudge.sh", hooks_json)

    def test_hooks_json_registers_alongside_update_nudge(self):
        hooks_json = _cached_read_text(REPO_ROOT / "hooks" / "hooks.json")
        # Registered in the same "startup|resume" SessionStart group as
        # update-nudge.sh / session-start-inject.sh, not a standalone group.
        update_idx = hooks_json.index("update-nudge.sh")
        onboard_idx = hooks_json.index("onboard-nudge.sh")
        startup_resume_idx = hooks_json.index('"matcher": "startup|resume"')
        matcher_startup_idx = hooks_json.index('"matcher": "startup"')
        self.assertLess(startup_resume_idx, update_idx)
        self.assertLess(update_idx, onboard_idx)
        self.assertLess(onboard_idx, matcher_startup_idx)

    def test_readme_has_recommended_global_setup_section(self):
        readme = _cached_read_text(REPO_ROOT / "README.md")
        self.assertIn("## Recommended global setup", readme)
        self.assertIn("/forge:onboard", readme)
        self.assertIn(
            "BEFORE\ninvoking any planning/brainstorming process skill on "
            "substantial dev work,\nFIRST offer `/forge:onboard` in one "
            "line, once per repo",
            readme,
        )
        self.assertIn("optional", readme.split("## Recommended global setup", 1)[1])


if __name__ == "__main__":
    unittest.main()
