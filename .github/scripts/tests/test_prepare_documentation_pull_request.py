from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PREPARER_PATH = (
    Path(__file__).resolve().parents[1] / "prepare-documentation-pull-request.py"
)
SPEC = importlib.util.spec_from_file_location(
    "prepare_documentation_pull_request", PREPARER_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load pull request preparer from {PREPARER_PATH}")
PREPARER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREPARER
SPEC.loader.exec_module(PREPARER)


class DocumentationPullRequestPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "repository with spaces"
        self.root.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Publication Tests")
        self.git("config", "user.email", "publication@example.invalid")
        self.git("config", "core.autocrlf", "false")

        self.document = self.root / "docs" / "invitaciones.md"
        self.document.parent.mkdir()
        self.document.write_text(
            "# Invitations\n\nInvitations expire after 24 hours.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial documentation")
        self.base_sha = self.git("rev-parse", "HEAD").stdout.strip()

        temporary_root = Path(self.temporary_directory.name)
        self.validation_result = temporary_root / "validation-result.json"
        self.ticket_file = temporary_root / "ticket.json"
        self.agent_report = temporary_root / "agent-report.md"
        self.body_file = temporary_root / "pull-request-body.md"
        self.github_output = temporary_root / "github-output.txt"
        self.ticket_file.write_text(
            json.dumps(
                {
                    "issue_key": "DOC-AGENT-1",
                    "issue_summary": "Update invitation expiry",
                    "issue_description": "Production uses 48 hours.",
                }
            ),
            encoding="utf-8",
        )
        self.agent_report.write_text(
            "Decision: proposal\n"
            "Document: docs/invitaciones.md\n"
            "Evidence: production snapshot\n"
            "Previous text: 24 hours\n"
            "Proposed text: 48 hours\n"
            "Reason: align with production\n",
            encoding="utf-8",
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

    def write_validation(
        self,
        *,
        valid: object = True,
        decision: str = "proposal",
        changed_files: list[object] | None = None,
        base_sha: str | None = None,
    ) -> None:
        if changed_files is None:
            changed_files = ["docs/invitaciones.md"] if decision == "proposal" else []
        self.validation_result.write_text(
            json.dumps(
                {
                    "valid": valid,
                    "decision": decision,
                    "base_sha": base_sha or self.base_sha,
                    "changed_files": changed_files,
                    "errors": [],
                }
            ),
            encoding="utf-8",
        )

    def prepare(self) -> dict[str, str]:
        return PREPARER.prepare_publication(
            repo_root=self.root,
            validation_result=self.validation_result,
            ticket_file=self.ticket_file,
            agent_report=self.agent_report,
            body_file=self.body_file,
            base_sha=self.base_sha,
            run_id="123456789",
            run_attempt="2",
            repository="example/documentation-poc",
            server_url="https://github.com",
        )

    def make_valid_proposal(self) -> None:
        self.document.write_text(
            "# Invitations\n\nInvitations expire after 48 hours.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.write_validation()

    def test_valid_proposal_builds_safe_publication_metadata_and_body(self) -> None:
        self.make_valid_proposal()

        plan = self.prepare()

        self.assertEqual("true", plan["publish"])
        self.assertEqual(
            "automation/documentation-doc-agent-1-123456789-2", plan["branch"]
        )
        self.assertEqual("docs/invitaciones.md", plan["document"])
        self.assertEqual(
            "DOC-AGENT-1 Apply validated documentation proposal",
            plan["commit_message"],
        )
        self.assertEqual(
            "DOC-AGENT-1 [Documentación] Update invitation expiry",
            plan["pr_title"],
        )
        body = self.body_file.read_text(encoding="utf-8")
        self.assertIn("DOC-AGENT-1", body)
        self.assertIn("Update invitation expiry", body)
        self.assertIn("Decision: proposal", body)
        self.assertIn(
            "https://github.com/example/documentation-poc/actions/runs/123456789",
            body,
        )
        self.assertIn("generada por Gemini", body)
        self.assertIn("validada determinísticamente", body)

    def test_valid_abstention_skips_publication_and_requires_empty_diff(self) -> None:
        self.write_validation(decision="abstention")

        plan = self.prepare()

        self.assertEqual({"publish": "false", "decision": "abstention"}, plan)
        self.assertFalse(self.body_file.exists())

    def test_valid_must_be_exact_boolean_true(self) -> None:
        self.make_valid_proposal()
        self.write_validation(valid=1)

        with self.assertRaisesRegex(
            PREPARER.PublicationPreparationError, "valid must be exactly true"
        ):
            self.prepare()

    def test_proposal_requires_one_safe_markdown_path(self) -> None:
        self.make_valid_proposal()
        invalid_values = (
            [],
            ["docs/invitaciones.md", "docs/otro.md"],
            ["README.md"],
            ["docs/../README.md"],
            ["docs/invitaciones.md\nmalicioso"],
            ["docs/production-snapshots/state.md"],
        )
        for changed_files in invalid_values:
            with self.subTest(changed_files=changed_files):
                self.write_validation(changed_files=changed_files)
                with self.assertRaises(PREPARER.PublicationPreparationError):
                    self.prepare()

    def test_git_diff_must_match_the_validated_document(self) -> None:
        self.make_valid_proposal()
        self.write_validation(changed_files=["docs/otro.md"])

        with self.assertRaises(PREPARER.PublicationPreparationError):
            self.prepare()

    def test_untracked_files_prevent_publication(self) -> None:
        self.make_valid_proposal()
        (self.root / "unexpected.tmp").write_text("unexpected", encoding="utf-8")

        with self.assertRaisesRegex(
            PREPARER.PublicationPreparationError, "Untracked files prevent publication"
        ):
            self.prepare()

    def test_changed_head_prevents_publication(self) -> None:
        self.make_valid_proposal()
        self.git("add", "docs/invitaciones.md")
        self.git("commit", "--quiet", "-m", "Unexpected commit")

        with self.assertRaisesRegex(
            PREPARER.PublicationPreparationError, "HEAD no longer matches"
        ):
            self.prepare()

    def test_ticket_values_are_revalidated_before_building_commands(self) -> None:
        self.make_valid_proposal()
        ticket = json.loads(self.ticket_file.read_text(encoding="utf-8"))
        ticket["issue_key"] = "DOC-1; touch unsafe"
        self.ticket_file.write_text(json.dumps(ticket), encoding="utf-8")

        with self.assertRaisesRegex(
            PREPARER.PublicationPreparationError, "Jira-style key"
        ):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
