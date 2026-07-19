import pathlib
import unittest

from port_agent import (
    FORMAT_BARE_SYSTEM_PROMPT,
    FORMAT_CLAUDE_SUBAGENT,
    FORMAT_CREWAI_LANGCHAIN,
    FORMAT_UNRECOGNIZED,
    detect_source_format,
)

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "port-agent"
SKILLS_ROOT = FIXTURES / "skills"


class TestDetectClaudeSubagent(unittest.TestCase):
    def test_full_frontmatter_detected(self):
        result = detect_source_format(FIXTURES / "claude-subagent-full.md")
        self.assertEqual(result["format"], FORMAT_CLAUDE_SUBAGENT)

    def test_minimal_frontmatter_detected(self):
        result = detect_source_format(FIXTURES / "claude-subagent-minimal.md")
        self.assertEqual(result["format"], FORMAT_CLAUDE_SUBAGENT)

    def test_malformed_frontmatter_is_unrecognized_not_guessed(self):
        # Has '---' fences but is missing the required `description` field --
        # the detector must not guess a mapping.
        result = detect_source_format(FIXTURES / "claude-subagent-malformed.md")
        self.assertEqual(result["format"], FORMAT_UNRECOGNIZED)


class TestDetectCrewAiLangchain(unittest.TestCase):
    def test_crewai_python_detected(self):
        result = detect_source_format(FIXTURES / "crewai-agent.py")
        self.assertEqual(result["format"], FORMAT_CREWAI_LANGCHAIN)

    def test_crewai_yaml_detected(self):
        result = detect_source_format(FIXTURES / "crewai-agents.yaml")
        self.assertEqual(result["format"], FORMAT_CREWAI_LANGCHAIN)

    def test_langchain_python_detected(self):
        result = detect_source_format(FIXTURES / "langchain-agent.py")
        self.assertEqual(result["format"], FORMAT_CREWAI_LANGCHAIN)


class TestDetectBareSystemPrompt(unittest.TestCase):
    def test_plain_prose_detected(self):
        result = detect_source_format(FIXTURES / "bare-system-prompt.txt")
        self.assertEqual(result["format"], FORMAT_BARE_SYSTEM_PROMPT)


class TestDetectUnrecognized(unittest.TestCase):
    def test_unrelated_json_config_is_unrecognized(self):
        result = detect_source_format(FIXTURES / "unrecognized-config.json")
        self.assertEqual(result["format"], FORMAT_UNRECOGNIZED)

    def test_empty_file_is_unrecognized(self):
        result = detect_source_format(FIXTURES / "unrecognized-empty.txt")
        self.assertEqual(result["format"], FORMAT_UNRECOGNIZED)

    def test_missing_file_is_unrecognized_with_reason(self):
        result = detect_source_format(FIXTURES / "does-not-exist.md")
        self.assertEqual(result["format"], FORMAT_UNRECOGNIZED)
        self.assertIn("not found", result["reason"].lower())


class TestSkillReferenceLoadability(unittest.TestCase):
    """AC2: when the source references a SKILL.md, check whether it is
    directly loadable unmodified before any attach-by-reference decision
    happens in the (out-of-scope-here) mapping stage.
    """

    def test_loadable_skill_reference_is_flagged_loadable(self):
        result = detect_source_format(
            FIXTURES / "claude-subagent-full.md", skills_root=SKILLS_ROOT)
        refs = {r["name"]: r for r in result["skill_references"]}
        self.assertTrue(refs["example-skill"]["loadable"])
        self.assertIsNotNone(refs["example-skill"]["resolved_path"])

    def test_missing_skill_reference_is_not_loadable(self):
        result = detect_source_format(
            FIXTURES / "claude-subagent-full.md", skills_root=SKILLS_ROOT)
        refs = {r["name"]: r for r in result["skill_references"]}
        self.assertFalse(refs["missing-skill"]["loadable"])
        self.assertIsNone(refs["missing-skill"]["resolved_path"])

    def test_broken_skill_missing_description_is_not_loadable(self):
        # broken-skill/SKILL.md exists but lacks the required `description`
        # field, so it fails the "directly loadable unmodified" contract
        # even though the file is present.
        result = detect_source_format(
            FIXTURES / "claude-subagent-full.md", skills_root=SKILLS_ROOT)
        # Not referenced by claude-subagent-full.md's Attached skills list,
        # so exercise the resolver directly via a synthetic reference.
        from port_agent import _resolve_skill
        ref = _resolve_skill("broken-skill", SKILLS_ROOT)
        self.assertFalse(ref["loadable"])
        self.assertIsNotNone(ref["resolved_path"])

    def test_no_skills_root_leaves_references_unresolved(self):
        result = detect_source_format(FIXTURES / "claude-subagent-full.md")
        refs = {r["name"]: r for r in result["skill_references"]}
        self.assertFalse(refs["example-skill"]["loadable"])
        self.assertIsNone(refs["example-skill"]["resolved_path"])

    def test_minimal_agent_has_no_skill_references(self):
        result = detect_source_format(FIXTURES / "claude-subagent-minimal.md")
        self.assertEqual(result["skill_references"], [])

    def test_non_claude_subagent_has_no_skill_references(self):
        result = detect_source_format(FIXTURES / "crewai-agent.py")
        self.assertEqual(result["skill_references"], [])


class TestVerifierBounceFindings(unittest.TestCase):
    """Regression cases for the attempt-2 verifier BOUNCE (three findings).
    Each of these reproduces one of the verifier's attack probes."""

    # Finding 1: langchain_core / langchain_openai / langchain_community
    # (post-package-split imports) must still be detected -- the old regex's
    # \b after "langchain" never matched because '_' is a \w char.
    def test_langchain_core_split_imports_detected(self):
        result = detect_source_format(FIXTURES / "langchain-core-agent.py")
        self.assertEqual(result["format"], FORMAT_CREWAI_LANGCHAIN)

    # Finding 2: a markdown DOC that merely illustrates the CrewAI
    # agents.yaml shape inside a ```yaml fence must not itself classify as
    # crewai-langchain -- the role/goal/backstory keys only exist inside
    # the fence, not at the document's top level.
    def test_doc_with_yaml_fence_is_not_misclassified_as_crewai(self):
        result = detect_source_format(FIXTURES / "crewai-doc-with-yaml-fence.md")
        self.assertNotEqual(result["format"], FORMAT_CREWAI_LANGCHAIN)

    # Finding 3: structured non-agent config data (YAML/TOML/INI) must not
    # fall through to bare-system-prompt -- that would hand fg-b0202's
    # mapper prompt text that was never a prompt, a guessed mapping AC1
    # forbids.
    def test_db_config_yaml_is_unrecognized(self):
        result = detect_source_format(FIXTURES / "unrecognized-db-config.yaml")
        self.assertEqual(result["format"], FORMAT_UNRECOGNIZED)

    def test_db_config_toml_is_unrecognized(self):
        result = detect_source_format(FIXTURES / "unrecognized-db-config.toml")
        self.assertEqual(result["format"], FORMAT_UNRECOGNIZED)

    def test_db_config_ini_is_unrecognized(self):
        result = detect_source_format(FIXTURES / "unrecognized-db-config.ini")
        self.assertEqual(result["format"], FORMAT_UNRECOGNIZED)

    # Self-check probes named in the bounce that should already pass, but
    # are pinned here as explicit regression cases.
    def test_crlf_frontmatter_detected(self):
        result = detect_source_format(FIXTURES / "claude-subagent-crlf.md")
        self.assertEqual(result["format"], FORMAT_CLAUDE_SUBAGENT)

    def test_folded_scalar_description_detected(self):
        result = detect_source_format(
            FIXTURES / "claude-subagent-folded-description.md")
        self.assertEqual(result["format"], FORMAT_CLAUDE_SUBAGENT)

    def test_aliased_crewai_import_detected(self):
        result = detect_source_format(FIXTURES / "crewai-aliased-import.py")
        self.assertEqual(result["format"], FORMAT_CREWAI_LANGCHAIN)

    def test_prose_mentioning_langchain_is_not_misclassified(self):
        result = detect_source_format(FIXTURES / "bare-prompt-mentions-langchain.txt")
        self.assertEqual(result["format"], FORMAT_BARE_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
