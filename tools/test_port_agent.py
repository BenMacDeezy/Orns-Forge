import pathlib
import unittest

from port_agent import (
    FORMAT_BARE_SYSTEM_PROMPT,
    FORMAT_CLAUDE_SUBAGENT,
    FORMAT_CREWAI_LANGCHAIN,
    FORMAT_UNRECOGNIZED,
    detect_source_format,
    map_source_to_agent_fields,
    render_agent_markdown,
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


class TestMapClaudeSubagentFields(unittest.TestCase):
    """AC1: extracted tools/model/persona/output-contract map to the
    `.forge/agents/` format fields for a Claude Code subagent source."""

    def test_full_frontmatter_maps_all_fields(self):
        mapped = map_source_to_agent_fields(FIXTURES / "claude-subagent-full.md")
        fields = mapped["fields"]
        self.assertEqual(fields["name"], "acme-release-notes")
        self.assertIn("Drafts release notes", fields["description"])
        self.assertEqual(fields["model"], "sonnet")
        self.assertEqual(fields["tools"], "Read, Grep, Glob")
        self.assertIn("release-notes drafter", fields["mission"])
        self.assertIsNotNone(fields["output_contract"])
        self.assertIn("changelog section", fields["output_contract"])
        # The Output contract section is extracted out of Mission, not
        # duplicated inside it.
        self.assertNotIn("## Output contract", fields["mission"])

    def test_minimal_frontmatter_defaults_model_and_notes_it(self):
        mapped = map_source_to_agent_fields(FIXTURES / "claude-subagent-minimal.md")
        fields = mapped["fields"]
        self.assertEqual(fields["name"], "acme-triager")
        self.assertEqual(fields["model"], "sonnet")
        self.assertTrue(any(
            "no model preference in source" in n for n in mapped["compat_notes"]))

    def test_no_output_contract_generates_compat_note(self):
        mapped = map_source_to_agent_fields(
            FIXTURES / "claude-subagent-no-output-contract.md")
        self.assertIsNone(mapped["fields"]["output_contract"])
        self.assertTrue(any(
            "no output-contract-like structure" in n
            for n in mapped["compat_notes"]))

    def test_unrecognized_format_maps_no_fields(self):
        mapped = map_source_to_agent_fields(FIXTURES / "unrecognized-config.json")
        self.assertEqual(mapped["fields"], {})
        self.assertTrue(any(
            "unrecognized" in n for n in mapped["compat_notes"]))

    def test_missing_file_maps_no_fields_with_reason(self):
        mapped = map_source_to_agent_fields(FIXTURES / "does-not-exist.md")
        self.assertEqual(mapped["fields"], {})
        self.assertTrue(mapped["compat_notes"])


class TestMapSkillReferenceCompatNotes(unittest.TestCase):
    """AC2 (skills case): a loadable skill reference is attached by
    reference (noted, not rewritten); an unresolvable one is flagged."""

    def test_loadable_and_missing_skill_both_produce_notes(self):
        mapped = map_source_to_agent_fields(
            FIXTURES / "claude-subagent-full.md", skills_root=SKILLS_ROOT)
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("example-skill", notes)
        self.assertIn("directly loadable", notes)
        self.assertIn("missing-skill", notes)
        self.assertIn("not directly loadable", notes)


class TestMapCrewAiLangchainFields(unittest.TestCase):
    """AC1 + AC2: role/goal/backstory map to persona; tools and model with
    no 1:1 Forge equivalent are named in a compatibility note rather than
    silently dropped."""

    def test_role_goal_backstory_map_to_mission_and_description(self):
        mapped = map_source_to_agent_fields(FIXTURES / "crewai-agent.py")
        fields = mapped["fields"]
        self.assertIn("Senior Research Analyst", fields["mission"])
        self.assertIn("Uncover cutting-edge developments", fields["description"])
        self.assertEqual(fields["model"], "sonnet")

    def test_unexposed_tools_and_model_get_compat_notes(self):
        mapped = map_source_to_agent_fields(FIXTURES / "crewai-agent.py")
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("unexposed tool 'search_tool'", notes)
        self.assertIn("unexposed tool 'browse_tool'", notes)
        self.assertIn("gpt-4", notes)

    def test_yaml_shape_maps_role_goal_backstory(self):
        mapped = map_source_to_agent_fields(FIXTURES / "crewai-agents.yaml")
        fields = mapped["fields"]
        self.assertIn("Senior Research Analyst", fields["mission"])
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("unexposed tool", notes)

    def test_langchain_system_message_maps_to_mission(self):
        mapped = map_source_to_agent_fields(FIXTURES / "langchain-agent.py")
        self.assertIn(
            "helpful research assistant", mapped["fields"]["mission"])

    def test_multi_agent_crew_and_memory_dependency_get_compat_notes(self):
        mapped = map_source_to_agent_fields(FIXTURES / "crewai-multi-agent-crew.py")
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("multi-agent crew topology", notes)
        self.assertIn("memory/vector-store dependency", notes)


class TestCredentialStripping(unittest.TestCase):
    """AC3 (Risks mitigation): an embedded credential/API key/token is
    excluded from every generated field and its removal (never its value)
    is named in the compatibility note. Fixtures use obviously-fake values
    so no real secret can ever appear in a test assertion literal."""

    def _assert_no_credential_leak(self, mapped, forbidden_substrings):
        rendered = render_agent_markdown(mapped)
        haystacks = [
            str(mapped["fields"]),
            " ".join(mapped["compat_notes"]),
            str(mapped["credential_findings"]),
            rendered,
        ]
        for forbidden in forbidden_substrings:
            for haystack in haystacks:
                self.assertNotIn(forbidden, haystack)

    def test_claude_subagent_openai_style_key_stripped(self):
        mapped = map_source_to_agent_fields(
            FIXTURES / "claude-subagent-with-credential.md")
        self._assert_no_credential_leak(
            mapped, ["sk-FAKE1234567890ABCDEFGHIJEXAMPLE"])
        self.assertTrue(mapped["credential_findings"])
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("OpenAI-style API key", notes)

    def test_crewai_aws_style_key_stripped(self):
        mapped = map_source_to_agent_fields(
            FIXTURES / "crewai-agent-with-credential.py")
        self._assert_no_credential_leak(mapped, ["AKIAFAKEEXAMPLE12345"])
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("AWS-style access key ID", notes)

    def test_langchain_generic_secret_assignment_stripped(self):
        mapped = map_source_to_agent_fields(
            FIXTURES / "langchain-agent-with-credential.py")
        self._assert_no_credential_leak(
            mapped, ["sk-FAKEEXAMPLEabcdefghijklmnopqrstuvwxyz012345"])
        self.assertTrue(mapped["credential_findings"])

    def test_bare_prompt_bearer_token_stripped(self):
        mapped = map_source_to_agent_fields(
            FIXTURES / "bare-system-prompt-with-credential.txt")
        self._assert_no_credential_leak(
            mapped, ["FAKE-TOKEN-abcdef1234567890EXAMPLE"])
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("bearer token", notes)

    def test_export_prefixed_env_style_secrets_stripped(self):
        # Verifier-reported P0: a leading `export ` token (shell/.env-style
        # assignment) broke the assigned-secret regex's line-start anchor,
        # letting the raw value leak into fields["mission"] and the
        # rendered markdown. Pinned regression covering both the
        # SECRET_TOKEN and API_KEY variants named in the verdict.
        mapped = map_source_to_agent_fields(
            FIXTURES / "bare-system-prompt-env-style-credential.txt")
        self._assert_no_credential_leak(mapped, [
            "abcdefghijklmnopqrstuvwx1234",
            "zyxwvutsrqponmlkjihgfedcba9876",
        ])
        self.assertTrue(mapped["credential_findings"])
        notes = " ".join(mapped["compat_notes"])
        self.assertIn("assigned secret/token/key/password", notes)

    def test_credential_free_sources_have_no_findings(self):
        mapped = map_source_to_agent_fields(FIXTURES / "claude-subagent-full.md")
        self.assertEqual(mapped["credential_findings"], [])


class TestRenderAgentMarkdown(unittest.TestCase):
    """Sanity checks on the in-memory render used to prove no credential
    reaches a generated artifact (writing to disk is out of scope here --
    that is `/forge:port`'s job, spec-6b7c item 3)."""

    def test_render_includes_mapped_fields(self):
        mapped = map_source_to_agent_fields(FIXTURES / "claude-subagent-full.md")
        rendered = render_agent_markdown(mapped)
        self.assertIn("name: acme-release-notes", rendered)
        self.assertIn("model: sonnet", rendered)
        self.assertIn("## Mission", rendered)
        self.assertIn("## Output contract", rendered)

    def test_render_includes_compat_notes_section_when_present(self):
        mapped = map_source_to_agent_fields(FIXTURES / "crewai-agent.py")
        rendered = render_agent_markdown(mapped)
        self.assertIn("## Provenance", rendered)
        self.assertIn("compatibility notes", rendered)


if __name__ == "__main__":
    unittest.main()
