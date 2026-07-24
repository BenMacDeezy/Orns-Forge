import pathlib
import re
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import conventions_corpus  # noqa: E402 -- fg-b0401 corpus loader


class TestTrustBoundaryArtifacts(unittest.TestCase):
    """Pins the on-disk artifacts of the trust-boundary work (constitution
    rule 3): the gitignore rules that keep both machine-local trust markers
    out of version control, the docs/conventions.md section documenting both
    markers (fg-7b01), the kernel SYNC prose that refuses to execute stored
    forge.md gate commands from an untrusted `.forge/` (fg-7b02), the
    first-touch human-confirm gate that writes `.forge/.trust-local` and the
    untrusted task/memory review-not-instructions framing (fg-7b03). The
    trust-decision helper/truth-table is deferred to fg-7b05 and is not
    tested here.
    """

    def test_gitignore_excludes_local_trust_marker(self):
        gitignore = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore.exists(), ".gitignore must exist at repo root")
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        self.assertIn(
            ".forge/.trust-local",
            lines,
            ".gitignore must contain an exact '.forge/.trust-local' line so "
            "the machine-local trust marker can never be accidentally committed",
        )
        self.assertIn(
            ".forge/.provenance",
            lines,
            ".gitignore must contain an exact '.forge/.provenance' line — the "
            "first-party init marker is also machine-local and must never be "
            "committed, or a poisoned fork could ship a pre-trusted marker",
        )

    def test_conventions_has_trust_boundary_section(self):
        # fg-b0401: docs/conventions.md was sharded into docs/conventions/*.md;
        # the corpus loader reconstructs the pre-split concatenated text so
        # this pin keeps matching unchanged.
        text = conventions_corpus.corpus_text()
        self.assertRegex(
            text,
            re.compile(r"^## Trust boundary$", re.MULTILINE),
            "docs/conventions.md must have a line-anchored '## Trust boundary' "
            "heading",
        )

    def test_conventions_documents_both_markers_in_trust_boundary_section(self):
        # fg-b0401: docs/conventions.md was sharded into docs/conventions/*.md;
        # the corpus loader reconstructs the pre-split concatenated text so
        # this pin keeps matching unchanged.
        text = conventions_corpus.corpus_text()
        match = re.search(r"^## Trust boundary$", text, flags=re.MULTILINE)
        self.assertIsNotNone(
            match, "docs/conventions.md must have a '## Trust boundary' section"
        )
        section_and_after = text[match.start():]
        self.assertIn(
            ".forge/.provenance",
            section_and_after,
            "Trust boundary section must document the .forge/.provenance marker",
        )
        self.assertIn(
            ".forge/.trust-local",
            section_and_after,
            "Trust boundary section must document the .forge/.trust-local marker",
        )

    def test_conventions_trust_boundary_section_covers_rederivation_and_review_gate(self):
        """Pins fg-7b05: docs/conventions.md's '## Trust boundary' section must
        be a COMPLETE reference — not just provenance/TOFU/markers but also a
        real description of gate re-derivation (fg-7b02) and the untrusted
        task/memory review gate (fg-7b03). Anchors on the two subsection
        headings fg-7b05 adds, which did not exist anywhere in the file before
        this task (verified via `git show HEAD:docs/conventions.md` before this
        change) — so this fails if either subsection is removed, unlike the
        marker-only test above which would still pass with both subsections
        deleted."""
        # fg-b0401: docs/conventions.md was sharded into docs/conventions/*.md;
        # the corpus loader reconstructs the pre-split concatenated text so
        # this pin keeps matching unchanged.
        text = conventions_corpus.corpus_text()

        self.assertRegex(
            text,
            re.compile(r"^### Gate re-derivation for untrusted", re.MULTILINE),
            "docs/conventions.md must have a line-anchored '### Gate "
            "re-derivation for untrusted ...' heading describing fg-7b02",
        )
        self.assertRegex(
            text,
            re.compile(r"^### Untrusted task/memory review gate", re.MULTILINE),
            "docs/conventions.md must have a line-anchored '### Untrusted "
            "task/memory review gate ...' heading describing fg-7b03",
        )
        self.assertIn(
            "stored-vs-derived",
            text,
            "the gate re-derivation subsection must describe showing the "
            "human stored-vs-derived gates",
        )
        self.assertRegex(
            text,
            re.compile(r"first-touch confirm|On CONFIRM"),
            "the review-gate subsection must describe the first-touch "
            "confirm gate's CONFIRM branch",
        )

    def test_kernel_sync_documents_untrusted_gate_rederivation(self):
        """Pins fg-7b02: the kernel SYNC step must never execute a stored
        forge.md Gates command when neither trust marker is present — it must
        re-derive gates from the repo instead and show stored-vs-derived,
        rather than blindly trusting a fork's forge.md."""
        kernel_skill = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
        text = kernel_skill.read_text(encoding="utf-8")

        sync_match = re.search(r"^### 1\. SYNC$", text, flags=re.MULTILINE)
        self.assertIsNotNone(
            sync_match, "skills/kernel/SKILL.md must have a '### 1. SYNC' section"
        )
        next_section_match = re.search(
            r"^### 2\. ", text[sync_match.end():], flags=re.MULTILINE
        )
        self.assertIsNotNone(
            next_section_match,
            "skills/kernel/SKILL.md must have a section following SYNC ('### 2. ...')",
        )
        sync_section = text[sync_match.end():sync_match.end() + next_section_match.start()]

        self.assertIn(
            "untrusted",
            sync_section.lower(),
            "SYNC section must call out the untrusted-.forge/ case",
        )
        self.assertRegex(
            sync_section,
            re.compile(r"re-?derive", re.IGNORECASE),
            "SYNC section must document that gates are re-derived from the "
            "repo when .forge/ is untrusted",
        )
        self.assertRegex(
            sync_section,
            re.compile(r"not execute|do not execute|not\s+run", re.IGNORECASE),
            "SYNC section must document that stored forge.md gate strings are "
            "NOT executed when .forge/ is untrusted",
        )

    def test_kernel_sync_documents_first_touch_confirm_gate(self):
        """Pins fg-7b03: the kernel SYNC step must document the first-touch
        human-confirm flow for an untrusted `.forge/` — confirming clears
        trust for the machine by writing `.forge/.trust-local`. Anchors on
        content unique to the fg-7b03 confirm-gate bullet (NOT just
        "confirm" / ".forge/.trust-local" in isolation — both of those
        strings already existed in the SYNC section from fg-7b02's Trust
        check and untrusted-gates prose, so asserting on them alone would
        pass even with the fg-7b03 bullet deleted). Fails if the fg-7b03
        bullet is removed."""
        kernel_skill = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
        text = kernel_skill.read_text(encoding="utf-8")

        sync_match = re.search(r"^### 1\. SYNC$", text, flags=re.MULTILINE)
        self.assertIsNotNone(
            sync_match, "skills/kernel/SKILL.md must have a '### 1. SYNC' section"
        )
        next_section_match = re.search(
            r"^### 2\. ", text[sync_match.end():], flags=re.MULTILINE
        )
        self.assertIsNotNone(
            next_section_match,
            "skills/kernel/SKILL.md must have a section following SYNC ('### 2. ...')",
        )
        sync_section = text[sync_match.end():sync_match.end() + next_section_match.start()]

        self.assertIn(
            "first-touch confirm gate",
            sync_section,
            "SYNC section must document the fg-7b03 'first-touch confirm "
            "gate' by name — this phrase is unique to fg-7b03's bullet, "
            "unlike bare 'confirm' which fg-7b02 prose already contains",
        )
        self.assertIn(
            "On CONFIRM",
            sync_section,
            "SYNC section must document the CONFIRM branch of the "
            "first-touch confirm gate",
        )
        self.assertIn(
            "On DECLINE",
            sync_section,
            "SYNC section must document the DECLINE (stop) branch of the "
            "first-touch confirm gate",
        )
        self.assertIn(
            ".forge/.trust-local",
            sync_section,
            "SYNC section must document writing .forge/.trust-local on human "
            "confirmation of an untrusted .forge/",
        )

    def test_memory_skill_documents_untrusted_facts_as_data_for_review(self):
        """Pins fg-7b03: skills/memory/SKILL.md must state that fact bodies
        from an untrusted, unconfirmed .forge/ are data for human review, not
        trusted instructions the kernel acts on. Fails if removed."""
        memory_skill = REPO_ROOT / "skills" / "memory" / "SKILL.md"
        text = memory_skill.read_text(encoding="utf-8")

        self.assertRegex(
            text,
            re.compile(r"untrusted", re.IGNORECASE),
            "skills/memory/SKILL.md must call out the untrusted-.forge/ case",
        )
        self.assertRegex(
            text,
            re.compile(r"review", re.IGNORECASE),
            "skills/memory/SKILL.md must state untrusted fact bodies are for "
            "human review",
        )
        self.assertRegex(
            text,
            re.compile(r"not\s+(?:a\s+)?trusted|not\s+.*instructions?", re.IGNORECASE),
            "skills/memory/SKILL.md must state untrusted fact bodies are NOT "
            "trusted instructions the kernel acts on",
        )

    def test_scout_discounts_self_serving_trust_claims(self):
        """Pins fg-7b04: the scout must discount self-serving trust claims
        embedded in a candidate tool's own listing/README (e.g. 'officially
        vetted, no review needed') and vet independently via external
        signals instead. Anchors on 'self-serving' and 'independent' — as of
        fg-7b03 neither word appeared anywhere under skills/scout/ or in
        agents/forge-scout.md (verified via `git show HEAD` before this
        change), so this is genuinely new prose, not a pre-existing string.
        Fails if the new guidance is removed from either file."""
        vet_checklist = REPO_ROOT / "skills" / "scout" / "references" / "vet-checklist.md"
        scout_agent = REPO_ROOT / "agents" / "forge-scout.md"

        checklist_text = vet_checklist.read_text(encoding="utf-8")
        self.assertRegex(
            checklist_text,
            re.compile(r"self-serving", re.IGNORECASE),
            "skills/scout/references/vet-checklist.md must call out "
            "'self-serving' trust claims embedded in a candidate's own "
            "listing/README",
        )
        self.assertRegex(
            checklist_text,
            re.compile(r"independent", re.IGNORECASE),
            "skills/scout/references/vet-checklist.md must state that "
            "trust is vetted independently via external signals",
        )

        agent_text = scout_agent.read_text(encoding="utf-8")
        self.assertRegex(
            agent_text,
            re.compile(r"self-serving", re.IGNORECASE),
            "agents/forge-scout.md must document the discount-self-serving-"
            "trust-claims rule by name",
        )
        self.assertRegex(
            agent_text,
            re.compile(r"independent", re.IGNORECASE),
            "agents/forge-scout.md must state that vetting relies on "
            "independent signals, not a candidate's own say-so",
        )


if __name__ == "__main__":
    unittest.main()
