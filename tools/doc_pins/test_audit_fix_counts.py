"""Inventory pins for audit-corrected public facts."""
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestAuditFixCounts(unittest.TestCase):
    def test_readme_command_count_matches_disk(self):
        count = len(list((ROOT / "commands").glob("*.md")))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"{count} commands", readme)

    def test_architecture_plugin_version_matches_manifest(self):
        version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(
            encoding="utf-8"))["version"]
        architecture = (ROOT / ".forge/map/architecture.md").read_text(
            encoding="utf-8")
        self.assertIn(f"version {version}", architecture)

    def test_architecture_toggle_facts_match_schema(self):
        schema = (ROOT / "skills/kernel/references/settings-schema.md").read_text(
            encoding="utf-8")
        features = schema.split("## Features", 1)[1].split("## Budgets", 1)[0]
        feature_rows = re.findall(r"^\| `[^`]+` \| on/off \|", features, re.M)
        architecture = (ROOT / ".forge/map/architecture.md").read_text(
            encoding="utf-8")
        words = {6: "Six", 14: "Fourteen"}
        self.assertIn(f"{words[len(feature_rows)]} toggles", architecture)
        self.assertIn("providers default off", architecture)

    def test_read_only_agent_count_matches_frontmatter(self):
        count = sum(bool(re.search(r"^tools:", (ROOT / "agents" / p.name).read_text(
            encoding="utf-8"), re.M)) for p in (ROOT / "agents").glob("*.md"))
        architecture = (ROOT / ".forge/map/architecture.md").read_text(encoding="utf-8")
        roster = (ROOT / ".forge/map/subsystems/agent-roster.md").read_text(
            encoding="utf-8")
        self.assertIn({14: "fourteen"}[count] + " read-only", architecture)
        self.assertIn(f"**{ {14: 'Fourteen'}[count] } agents carry restricted", roster)


if __name__ == "__main__":
    unittest.main()
