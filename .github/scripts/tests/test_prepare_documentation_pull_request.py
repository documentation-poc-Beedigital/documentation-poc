from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PREPARER_PATH = Path(__file__).resolve().parents[1] / "prepare-documentation-pull-request.py"
SPEC = importlib.util.spec_from_file_location("prepare_documentation_pull_request", PREPARER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load preparer from {PREPARER_PATH}")
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
        self.write("docs/one.md", "---\nversion: 1.0\n---\n\n# One\n")
        self.write("docs/two.mdx", "---\nversion: 2.9\n---\n\n# Two\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial")
        self.base_sha = self.git("rev-parse", "HEAD").stdout.strip()
        temp = Path(self.temporary_directory.name)
        self.validation_result = temp / "validation.json"
        self.ticket_file = temp / "ticket.json"
        self.agent_report = temp / "agent-report.md"
        self.body_file = temp / "body.md"
        self.ticket_file.write_text(json.dumps({
            "issue_key": "DOC-AGENT-1", "issue_summary": "Update related docs",
            "issue_description": "Natural-language change request",
        }), encoding="utf-8")
        self.agent_report.write_text(json.dumps({
            "decision": "proposal", "summary": "Two docs", "reason": "Ticket",
            "evidence": "Docs", "documents": [],
        }, indent=2), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")

    def metadata(self, path: str, previous: str, proposed: str) -> dict[str, str]:
        return {"path": path, "reason": "Affected by ticket", "evidence": "Ticket and docs", "previous_version": previous, "proposed_version": proposed}

    def write_validation(self, decision: str = "proposal", documents: list[dict[str, str]] | None = None, **overrides: object) -> None:
        if documents is None:
            documents = [self.metadata("docs/one.md", "1.0", "1.1")]
        value: dict[str, object] = {
            "valid": True, "decision": decision, "base_sha": self.base_sha,
            "changed_files": [item["path"] for item in documents] if decision == "proposal" else [],
            "documents": documents if decision == "proposal" else [], "errors": [],
        }
        value.update(overrides)
        self.validation_result.write_text(json.dumps(value), encoding="utf-8")
        self.agent_report.write_text(json.dumps({
            "decision": decision,
            "summary": "Update related documents",
            "reason": "Concrete Jira request",
            "evidence": "Ticket and repository docs",
            "documents": documents if decision == "proposal" else [],
        }), encoding="utf-8")

    def prepare(self) -> dict[str, str]:
        return PREPARER.prepare_publication(
            self.root, self.validation_result, self.ticket_file, self.agent_report,
            self.body_file, self.base_sha, "123456789", "2",
            "example/documentation-poc", "https://github.com",
        )

    def test_valid_multi_document_plan_has_one_branch_commit_pr_and_json(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        self.write("docs/two.mdx", "---\nversion: 2.10\n---\n\n# Two changed\n")
        documents = [self.metadata("docs/one.md", "1.0", "1.1"), self.metadata("docs/two.mdx", "2.9", "2.10")]
        self.write_validation(documents=documents)
        plan = self.prepare()
        self.assertEqual("true", plan["publish"])
        self.assertEqual("automation/documentation-doc-agent-1-123456789-2", plan["branch"])
        self.assertEqual("DOC-AGENT-1 Apply validated documentation proposal", plan["commit_message"])
        self.assertEqual(documents, json.loads(plan["documents_json"]))
        body = self.body_file.read_text(encoding="utf-8")
        self.assertIn("Informe del agente", body)
        self.assertIn("actions/runs/123456789", body)

    def test_single_document_remains_supported(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        self.write_validation()
        self.assertEqual(1, len(json.loads(self.prepare()["documents_json"])))

    def test_abstention_skips_publication_with_empty_diff(self) -> None:
        self.write_validation(decision="abstention", documents=[])
        self.assertEqual({"publish": "false", "decision": "abstention"}, self.prepare())

    def test_changed_files_and_metadata_must_match_complete_diff(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        self.write("docs/two.mdx", "---\nversion: 2.10\n---\n\n# Two changed\n")
        self.write_validation()
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "all validated"):
            self.prepare()

    def test_duplicate_unsafe_and_snapshot_paths_are_rejected(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        invalid = (["docs/one.md", "docs/one.md"], ["README.md"], ["docs/../README.md"], ["docs/production-snapshots/state.md"])
        for paths in invalid:
            with self.subTest(paths=paths):
                self.write_validation(changed_files=paths)
                with self.assertRaises(PREPARER.PublicationPreparationError):
                    self.prepare()

    def test_versions_are_independently_verified(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        document = self.metadata("docs/one.md", "1.0", "9.9")
        self.write_validation(documents=[document])
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "versions do not match"):
            self.prepare()

    def test_untracked_file_and_changed_head_prevent_publication(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        self.write_validation()
        self.write("unexpected.tmp", "unexpected")
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "Untracked"):
            self.prepare()
        (self.root / "unexpected.tmp").unlink()
        self.git("add", "docs/one.md")
        self.git("commit", "--quiet", "-m", "Unexpected")
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "HEAD no longer"):
            self.prepare()

    def test_title_normalizes_documentation_prefix(self) -> None:
        self.assertEqual(
            "DOC-22 [Documentación] Update",
            PREPARER.build_pull_request_title("DOC-22", " [DOCUMENTACIÓN] Update"),
        )

    def test_title_adds_documentation_prefix_when_absent(self) -> None:
        self.assertEqual(
            "DOC-22 [Documentación] Update",
            PREPARER.build_pull_request_title("DOC-22", "Update"),
        )

    def test_title_deduplicates_repeated_documentation_prefixes(self) -> None:
        self.assertEqual(
            "DOC-22 [Documentación] Update",
            PREPARER.build_pull_request_title(
                "DOC-22", "[Documentación] [DOCUMENTACIÓN] Update"
            ),
        )

    def test_prefix_only_summary_is_rejected(self) -> None:
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "meaningful text"):
            PREPARER.build_pull_request_title("DOC-22", " [Documentación] ")

    def test_leading_spaces_are_trimmed_only_for_title_not_ticket_content(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        self.ticket_file.write_text(json.dumps({
            "issue_key": "DOC-AGENT-1",
            "issue_summary": "  Preserve intentional source spacing",
            "issue_description": "  Original description spacing",
        }), encoding="utf-8")
        self.write_validation()
        plan = self.prepare()
        self.assertEqual(
            "DOC-AGENT-1 [Documentación] Preserve intentional source spacing",
            plan["pr_title"],
        )
        self.assertEqual(
            "  Original description spacing",
            PREPARER.load_ticket(self.ticket_file)["issue_description"],
        )
        self.assertIn(
            "**Resumen:**   Preserve intentional source spacing",
            self.body_file.read_text(encoding="utf-8"),
        )

    def test_validation_valid_must_be_exact_boolean_true(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        for invalid in (1, "true", False, None):
            with self.subTest(valid=invalid):
                self.write_validation(valid=invalid)
                with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "exactly true"):
                    self.prepare()

    def test_invalid_validation_decision_is_rejected(self) -> None:
        self.write_validation(decision="merge")
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "proposal or abstention"):
            self.prepare()

    def test_jira_issue_key_is_revalidated(self) -> None:
        self.ticket_file.write_text(json.dumps({
            "issue_key": "DOC-1; touch owned", "issue_summary": "Update",
            "issue_description": "Concrete request",
        }), encoding="utf-8")
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "Jira-style key"):
            PREPARER.load_ticket(self.ticket_file)

    def test_jira_summary_is_revalidated(self) -> None:
        self.ticket_file.write_text(json.dumps({
            "issue_key": "DOC-1", "issue_summary": "Unsafe\nsummary",
            "issue_description": "Concrete request",
        }), encoding="utf-8")
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "safe single-line"):
            PREPARER.load_ticket(self.ticket_file)

    def test_jira_description_length_is_revalidated(self) -> None:
        self.ticket_file.write_text(json.dumps({
            "issue_key": "DOC-1", "issue_summary": "Update",
            "issue_description": "x" * 20_001,
        }), encoding="utf-8")
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "safe Jira description"):
            PREPARER.load_ticket(self.ticket_file)

    def test_jira_description_control_characters_are_revalidated(self) -> None:
        self.ticket_file.write_text(json.dumps({
            "issue_key": "DOC-1", "issue_summary": "Update",
            "issue_description": "Unsafe\u0000description",
        }), encoding="utf-8")
        with self.assertRaisesRegex(PREPARER.PublicationPreparationError, "safe Jira description"):
            PREPARER.load_ticket(self.ticket_file)

    def test_shell_metacharacters_in_summary_are_data_not_commands(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        marker = self.root / "owned"
        self.ticket_file.write_text(json.dumps({
            "issue_key": "DOC-1", "issue_summary": "Update $(touch owned); `whoami`",
            "issue_description": "Concrete request",
        }), encoding="utf-8")
        self.write_validation()
        plan = self.prepare()
        self.assertIn("$(touch owned)", plan["pr_title"])
        self.assertFalse(marker.exists())

    def test_pull_request_body_lists_every_document_and_version(self) -> None:
        self.write("docs/one.md", "---\nversion: 1.1\n---\n\n# One changed\n")
        self.write("docs/two.mdx", "---\nversion: 2.10\n---\n\n# Two changed\n")
        documents = [
            self.metadata("docs/one.md", "1.0", "1.1"),
            self.metadata("docs/two.mdx", "2.9", "2.10"),
        ]
        self.write_validation(documents=documents)
        self.prepare()
        body = self.body_file.read_text(encoding="utf-8")
        self.assertIn("`docs/one.md`", body)
        self.assertIn("`1.0` → `1.1`", body)
        self.assertIn("`docs/two.mdx`", body)
        self.assertIn("`2.9` → `2.10`", body)


if __name__ == "__main__":
    unittest.main()
