from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


VALIDATOR_PATH = (
    Path(__file__).resolve().parents[1] / "validate-documentation-proposal.py"
)
SPEC = importlib.util.spec_from_file_location(
    "validate_documentation_proposal", VALIDATOR_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


FRONTMATTER = """---
article_id: ART-001
title: Invitations
version: 1.0
status: published
owner: Product
---

"""


class DocumentationProposalValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "repository with spaces"
        self.root.mkdir()

        self.git("init", "--quiet")
        self.git("config", "user.name", "Validator Tests")
        self.git("config", "user.email", "validator@example.invalid")
        self.git("config", "core.autocrlf", "false")

        (self.root / "docs" / "production-snapshots").mkdir(parents=True)
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 24 hours.\n",
        )
        self.write(
            "docs/archivos-adjuntos.md",
            FRONTMATTER.replace("ART-001", "ART-002")
            + "# Attachments\n\nMaximum size is 50 MB.\n",
        )
        self.write(
            "docs/production-snapshots/invitations.json",
            '{"current_production_value_hours": 48}\n',
        )
        self.write("README.md", "# Test repository\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial fixtures")
        self.base_sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.agent_report = Path(self.temporary_directory.name) / "agent-report.md"
        self.write_agent_report(
            decision="abstención",
            document="ninguno",
            previous="no aplica",
            proposed="no aplica",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def write_agent_report(
        self,
        *,
        decision: str,
        document: str,
        evidence: str = "docs and repository evidence",
        previous: str = "old text",
        proposed: str = "new text",
        reason: str = "minimal documented change",
    ) -> None:
        self.agent_report.write_text(
            "\n".join(
                (
                    f"Decisión: {decision}",
                    f"Documento: {document}",
                    f"Evidencia: {evidence}",
                    f"Texto anterior: {previous}",
                    f"Texto propuesto: {proposed}",
                    f"Motivo: {reason}",
                )
            )
            + "\n",
            encoding="utf-8",
        )

    def validate(self) -> dict[str, object]:
        return VALIDATOR.validate_repository(
            self.root,
            self.agent_report,
            self.base_sha,
        )

    def assert_rejected_with(self, expected_text: str) -> None:
        report = self.validate()
        self.assertFalse(report["valid"], report)
        self.assertIn(
            expected_text,
            "\n".join(str(error) for error in report["errors"]),
        )

    def test_valid_proposal_on_one_markdown(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.write_agent_report(
            decision="propuesta",
            document="docs/invitaciones.md",
            previous="Invitations expire after 24 hours.",
            proposed="Invitations expire after 48 hours.",
        )

        report = self.validate()

        self.assertTrue(report["valid"], report)
        self.assertEqual("proposal", report["decision"])
        self.assertEqual(["docs/invitaciones.md"], report["changed_files"])

    def test_changed_head_is_rejected(self) -> None:
        self.write("README.md", "# Changed in a commit\n")
        self.git("add", "README.md")
        self.git("commit", "--quiet", "-m", "Unexpected agent commit")
        self.assert_rejected_with("HEAD changed after the trusted base was captured")

    def test_previous_text_must_exist_in_base_document(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.write_agent_report(
            decision="propuesta",
            document="docs/invitaciones.md",
            previous="Invitations expire after 12 hours.",
            proposed="Invitations expire after 48 hours.",
        )
        self.assert_rejected_with("Texto anterior does not exist in the base document")

    def test_proposed_text_must_exist_in_modified_document(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.write_agent_report(
            decision="propuesta",
            document="docs/invitaciones.md",
            previous="Invitations expire after 24 hours.",
            proposed="Invitations expire after 72 hours.",
        )
        self.assert_rejected_with(
            "Texto propuesto does not exist in the modified document"
        )

    def test_previous_text_must_not_remain_in_modified_document(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER
            + "# Invitations\n\nInvitations expire after 24 hours.\n"
            + "Invitations expire after 48 hours.\n",
        )
        self.write_agent_report(
            decision="propuesta",
            document="docs/invitaciones.md",
            previous="Invitations expire after 24 hours.",
            proposed="Invitations expire after 48 hours.",
        )
        self.assert_rejected_with(
            "Texto anterior still exists in the modified document"
        )

    def test_proposed_text_must_not_exist_in_base_document(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.write_agent_report(
            decision="propuesta",
            document="docs/invitaciones.md",
            previous="Invitations expire after 24 hours.",
            proposed="# Invitations",
        )
        self.assert_rejected_with(
            "Texto propuesto already exists in the base document"
        )

    def test_multiline_replacement_text_is_rejected(self) -> None:
        self.agent_report.write_text(
            "Decisión: propuesta\n"
            "Documento: docs/invitaciones.md\n"
            "Evidencia: repository evidence\n"
            "Texto anterior: first line\nsecond line\n"
            "Texto propuesto: replacement\n"
            "Motivo: test\n",
            encoding="utf-8",
        )
        self.assert_rejected_with("six single-line fields")

    def test_empty_diff_is_valid_abstention(self) -> None:
        report = self.validate()

        self.assertTrue(report["valid"], report)
        self.assertEqual("abstention", report["decision"])
        self.assertEqual([], report["changed_files"])

    def test_proposal_report_with_empty_diff_is_rejected(self) -> None:
        self.write_agent_report(
            decision="propuesta",
            document="docs/invitaciones.md",
        )
        self.assert_rejected_with(
            "A propuesta report requires exactly one modified Markdown file"
        )

    def test_abstention_report_with_changed_markdown_is_rejected(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.assert_rejected_with("An abstención report requires an empty diff")

    def test_report_document_must_match_changed_markdown(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.write_agent_report(
            decision="propuesta",
            document="docs/archivos-adjuntos.md",
        )
        self.assert_rejected_with(
            "Agent report Documento does not match the modified file"
        )

    def test_report_with_missing_field_is_rejected(self) -> None:
        self.agent_report.write_text(
            "Decisión: abstención\n"
            "Documento: ninguno\n"
            "Evidencia: insufficient evidence\n"
            "Texto anterior: no aplica\n"
            "Texto propuesto: no aplica\n",
            encoding="utf-8",
        )
        self.assert_rejected_with("exactly these six single-line fields")

    def test_report_with_extra_field_is_rejected(self) -> None:
        with self.agent_report.open("a", encoding="utf-8") as report:
            report.write("Extra: forbidden\n")
        self.assert_rejected_with("exactly these six single-line fields")

    def test_abstention_report_requires_no_document(self) -> None:
        self.write_agent_report(
            decision="abstención",
            document="docs/invitaciones.md",
            previous="no aplica",
            proposed="no aplica",
        )
        self.assert_rejected_with("must use 'ninguno' as Documento")

    def test_abstention_report_requires_not_applicable_text(self) -> None:
        self.write_agent_report(
            decision="abstención",
            document="ninguno",
            previous="old text",
            proposed="no aplica",
        )
        self.assert_rejected_with("must use 'no aplica' as Texto anterior")

    def test_oversized_report_is_rejected(self) -> None:
        self.write_agent_report(
            decision="abstención",
            document="ninguno",
            evidence="x" * (VALIDATOR.DEFAULT_MAX_REPORT_BYTES + 1),
            previous="no aplica",
            proposed="no aplica",
        )
        self.assert_rejected_with("Agent report is too large")

    def test_change_outside_docs_is_rejected(self) -> None:
        self.write("README.md", "# Changed\n")
        self.assert_rejected_with("outside docs/")

    def test_snapshot_change_is_rejected(self) -> None:
        self.write(
            "docs/production-snapshots/invitations.json",
            '{"current_production_value_hours": 72}\n',
        )
        self.assert_rejected_with("production-snapshots is read-only")

    def test_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "traversal"):
            VALIDATOR.validate_relative_path(self.root, "docs/../README.md")

    def test_multiple_files_are_rejected(self) -> None:
        self.write(
            "docs/invitaciones.md",
            FRONTMATTER + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.write(
            "docs/archivos-adjuntos.md",
            FRONTMATTER.replace("ART-001", "ART-002")
            + "# Attachments\n\nMaximum size is 60 MB.\n",
        )
        self.assert_rejected_with("Exactly one modified file is required")

    def test_frontmatter_change_is_rejected(self) -> None:
        changed_frontmatter = FRONTMATTER.replace("version: 1.0", "version: 2.0")
        self.write(
            "docs/invitaciones.md",
            changed_frontmatter + "# Invitations\n\nInvitations expire after 48 hours.\n",
        )
        self.assert_rejected_with("Frontmatter changes are not allowed")

    def test_new_file_is_rejected(self) -> None:
        self.write("docs/new-document.md", "# New document\n")
        self.assert_rejected_with("Added or untracked files are not allowed")

    def test_deleted_file_is_rejected(self) -> None:
        (self.root / "docs" / "invitaciones.md").unlink()
        self.assert_rejected_with("Only modification status M is allowed")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are not supported")
    def test_symlink_is_rejected_when_supported(self) -> None:
        target = self.root / "outside.md"
        target.write_text("# Outside\n", encoding="utf-8")
        link = self.root / "docs" / "linked.md"
        try:
            os.symlink(target, link)
        except OSError as error:
            self.skipTest(f"could not create a symlink: {error}")

        with self.assertRaisesRegex(VALIDATOR.ValidationError, "Symlinks"):
            VALIDATOR.validate_relative_path(self.root, "docs/linked.md")


if __name__ == "__main__":
    unittest.main()
