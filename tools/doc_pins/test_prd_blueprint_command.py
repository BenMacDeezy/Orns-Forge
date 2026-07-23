"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id `prd-blueprint-command`: TestBlueprintCommandPins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
)


class TestBlueprintCommandPins(unittest.TestCase):
    """Doc-pins for prd-blueprint-command: commands/blueprint.md, the new
    `/forge:blueprint` PRD -> advisory wave/parallelization-blueprint
    command, plus the map/README/docs count-surface refresh (24 -> 25
    commands) its addition to commands/*.md required. Every substring below
    is unique to text this task added -- never a phrase court.md, verify.md,
    or telemetry.md already owns in text this task cites but does not
    restate."""

    BLUEPRINT_PATH = REPO_ROOT / "commands" / "blueprint.md"

    def _blueprint(self):
        return _cached_read_text(self.BLUEPRINT_PATH)

    def test_blueprint_command_file_exists(self):
        self.assertTrue(self.BLUEPRINT_PATH.exists())

    def test_blueprint_frontmatter_description_and_argument_hint(self):
        content = self._blueprint()
        self.assertIn(
            "description: Read a full PRD and produce an advisory "
            "wave/agent/parallelization blueprint, an up-front "
            "integrations checklist, and a ranged time estimate",
            content,
        )
        self.assertIn('argument-hint: "<prd-path>"', content)

    def test_blueprint_human_ask_only_like_court_and_inquest(self):
        content = self._blueprint()
        self.assertIn(
            "Like `/forge:court` and `/forge:inquest`, this command\n"
            "  itself is the trigger — never a loop, wave, or "
            "standing-consent toggle.",
            content,
        )

    def test_blueprint_never_names_or_defaults_a_model(self):
        content = self._blueprint()
        self.assertIn(
            "MECHANICAL/JUDGMENT vocabulary\n  only. This command never "
            "names or defaults a model, in any wave, ever.",
            content,
        )

    def test_blueprint_advisory_normative_framing(self):
        content = self._blueprint()
        self.assertIn(
            "**Advisory, not binding — NORMATIVE.** The blueprint produced "
            "below is a\n  hole-poking artifact, not a binding plan and "
            "not spec approval.",
            content,
        )
        self.assertIn(
            "Actual\n  feature execution still routes through "
            "`/forge:spec` ratification, and the\n  blueprint may drift "
            "from reality without ceremony",
            content,
        )

    def test_blueprint_reads_full_prd_never_skims(self):
        content = self._blueprint()
        self.assertIn(
            "read the\n   ENTIRE document — never skim, never sample a "
            "section and infer the rest.",
            content,
        )

    def test_blueprint_one_structured_question_round(self):
        content = self._blueprint()
        self.assertIn(
            "ask ONE structured question\n   (`AskUserQuestion`, per "
            "`docs/conventions.md`, \"Asking the user\n   questions\") "
            "batching every missing constraint into that one round",
            content,
        )
        self.assertIn(
            "skip the question entirely rather than\n   asking for "
            "confirmation of what's already given.",
            content,
        )

    def test_blueprint_derives_waves_from_file_data_boundaries(self):
        content = self._blueprint()
        self.assertIn(
            "**non-overlapping declared file/data scopes**", content,
        )
        self.assertIn(
            "the worktree-wave doctrine this\n   blueprint borrows "
            "unchanged", content,
        )
        self.assertIn(
            "blueprint borrows unchanged). Tasks touching disjoint files "
            "parallelize\n   into the same wave; tasks touching the same "
            "file or the same data\n   (schema, migration, shared config) "
            "serialize into separate waves, even\n   when nothing else "
            "blocks them.",
            content,
        )

    def test_blueprint_dated_file_next_to_prd_or_docs_plans(self):
        content = self._blueprint()
        self.assertIn(
            "`<prd-stem>-blueprint-<YYYY-MM-DD>.md` (same directory), or "
            "under\n   `docs/plans/` when the PRD sits outside a repo",
            content,
        )

    def test_blueprint_file_collision_never_silent_overwrite(self):
        # 2026-07-20 grouped retro-verify P1 fix: same-day re-run must
        # suffix, never clobber the prior blueprint.
        content = self._blueprint()
        self.assertIn("**Blueprint-file collision check — runs before\n"
                      "   the write.**", content)
        self.assertIn("never silently overwrite\n   it", content)
        self.assertIn("<prd-stem>-blueprint-<YYYY-MM-DD>-2.md", content)
        self.assertIn("the prior blueprint\n   stays untouched", content)

    def test_blueprint_waves_table_exact_columns(self):
        content = self._blueprint()
        self.assertIn(
            "| Wave | Tasks | Agent type | Tier | Parallel-safe | "
            "Depends-on | Est. wall-clock |",
            content,
        )

    def test_blueprint_integrations_checklist_credentials_normative(self):
        content = self._blueprint()
        self.assertIn(
            "**NORMATIVE: credentials are always the provider's own "
            "flow — Forge never\ntouches, stores, or proxies them.**",
            content,
        )
        self.assertIn(
            "so the human\nconnects everything ONCE before implementation "
            "starts and the build never\nstalls mid-flight on a missing "
            "connector.",
            content,
        )

    def test_blueprint_time_estimate_assumptions_cited(self):
        content = self._blueprint()
        self.assertIn(
            "**~1.4× adversarial-verify overhead**", content,
        )
        self.assertIn(
            "\"Benchmark-ratified routing —\n  2026-07-20 (fg-a10408)\"",
            content,
        )
        self.assertIn("**~1/3 bounce rate**", content)
        self.assertIn(
            "15 of 52 tasks (28.8%) bounced at least once\n  requiring "
            "rework, per `docs/audits/2026-07-18-protocol-overhead-audit.md`",
            content,
        )
        self.assertIn(
            "these estimates are\n  calibrated on Forge-repo task sizes "
            "and transfer imperfectly to a\n  different codebase, team, "
            "or stack",
            content,
        )
        self.assertIn(
            "docs/audits/2026-07-20-session-economics.md", content,
        )

    def test_blueprint_closes_offering_never_auto_running_court(self):
        content = self._blueprint()
        self.assertIn(
            "Then **offer** — never auto-run —\na `/forge:court` pass on "
            "the PRD as the natural next hole-poking step",
            content,
        )

    def test_readme_lists_blueprint_command_row(self):
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn(
            "| `/forge:blueprint` | PRD → advisory wave/agent/"
            "parallelization blueprint, integrations checklist, time "
            "estimate |",
            content,
        )

    def test_map_architecture_names_blueprint_entry_point_and_count(self):
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(map_path)
        self.assertIn(
            "- `/forge:blueprint <prd-path>` → `commands/blueprint.md`: "
            "PRD → advisory wave/parallelization blueprint.",
            content,
        )
        self.assertIn("twenty-six slash commands", content)
        self.assertIn(
            "Twenty-six thin slash-command entry points",
            content,
        )

    def test_map_architecture_under_char_ceiling(self):
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(map_path)
        self.assertLessEqual(len(content), 8000)

    def test_map_subsystems_commands_names_blueprint(self):
        subsys_path = (
            REPO_ROOT / ".forge" / "map" / "subsystems" / "commands.md"
        )
        if not subsys_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(subsys_path)
        self.assertIn("Twenty-six thin slash-command entry points", content)
        self.assertIn("`blueprint`", content)
        self.assertIn(
            "`blueprint` (`prd-blueprint-command`) reads a full PRD",
            content,
        )

    def test_docs_architecture_names_twenty_five_commands(self):
        content = _read_path("docs/architecture.md")
        self.assertIn(
            "Twenty-six thin slash-command entry points under "
            "`commands/*.md`",
            content,
        )


if __name__ == "__main__":
    unittest.main()
