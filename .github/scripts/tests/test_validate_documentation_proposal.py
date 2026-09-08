from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VALIDATOR_PATH = Path(__file__).resolve().parents[1] / "validate-documentation-proposal.py"
SPEC = importlib.util.spec_from_file_location("validate_documentation_proposal", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

FRONTMATTER = "---\narticle_id: ART-001\ntitle: Invitations\nversion: 1.0\nstatus: published\nowner: Product\n---\n"
BODY_ONE = "\n# Invitations\n\nInvitations expire after 24 hours.\n"
BODY_TWO = "\n# Attachments\n\nMaximum size is 50 MB.\n"


class DocumentationProposalValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "repository with spaces"
        self.root.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Validator Tests")
        self.git("config", "user.email", "validator@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.write("docs/invitaciones.md", FRONTMATTER + BODY_ONE)
        self.write("docs/archivos-adjuntos.md", FRONTMATTER.replace("ART-001", "ART-002").replace("Invitations", "Attachments") + BODY_TWO)
        self.write("docs/production-snapshots/state.json", "{}\n")
        self.write("README.md", "# Fixture\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial fixtures")
        self.base_sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.agent_report = Path(self.temporary_directory.name) / "agent-report.md"
        self.write_report("abstention", [])

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")

    def modify(self, path: str, body: str, version: str = "1.1", **overrides: str) -> dict[str, str]:
        before = self.git("show", f"{self.base_sha}:{path}").stdout
        frontmatter, _ = VALIDATOR.split_frontmatter(before, path)
        updated_frontmatter = frontmatter.replace("version: 1.0", f"version: {version}")
        after = updated_frontmatter + body
        self.write(path, after)
        item = {
            "path": path, "reason": "Ticket requires this change", "evidence": "Ticket and local docs",
            "previous_version": "1.0", "proposed_version": version,
            "proposed_body_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "proposed_document_sha256": hashlib.sha256(after.encode()).hexdigest(),
            "diff": "".join(difflib.unified_diff(
                before.splitlines(keepends=True), after.splitlines(keepends=True),
                fromfile=f"a/{path}", tofile=f"b/{path}",
            )),
        }
        item.update(overrides)
        return item

    def write_report(self, decision: str, documents: list[dict[str, str]], **overrides: object) -> None:
        report: dict[str, object] = {
            "decision": decision, "summary": "Documentation proposal",
            "reason": "Concrete ticket or responsible abstention", "evidence": "Reviewed all relevant docs",
            "documents": documents,
        }
        report.update(overrides)
        self.agent_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def validate(self) -> dict[str, object]:
        return VALIDATOR.validate_repository(self.root, self.agent_report, self.base_sha)

    def assert_rejected(self, message: str) -> None:
        report = self.validate()
        self.assertFalse(report["valid"], report)
        self.assertIn(message, "\n".join(report["errors"]))

    def test_valid_one_document_proposal(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        self.write_report("proposal", [item])
        result = self.validate()
        self.assertTrue(result["valid"], result)
        self.assertEqual(["docs/invitaciones.md"], result["changed_files"])
        self.assertEqual("1.1", result["documents"][0]["proposed_version"])

    def test_valid_multi_document_proposal(self) -> None:
        items = [
            self.modify("docs/invitaciones.md", "\n# Invitations\n\n## Expiry\n\n48 hours.\n"),
            self.modify("docs/archivos-adjuntos.md", "\n# Attachments\n\n| Limit | Value |\n|---|---|\n| Max | 60 MB |\n"),
        ]
        self.write_report("proposal", items)
        result = self.validate()
        self.assertTrue(result["valid"], result)
        self.assertEqual(2, len(result["documents"]))

    def test_empty_diff_is_valid_abstention(self) -> None:
        result = self.validate()
        self.assertTrue(result["valid"], result)
        self.assertEqual("abstention", result["decision"])

    def test_report_must_declare_all_and_only_changed_documents(self) -> None:
        first = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        self.modify("docs/archivos-adjuntos.md", BODY_TWO.replace("50", "60"))
        self.write_report("proposal", [first])
        self.assert_rejected("must match every modified file exactly")

    def test_duplicate_report_paths_are_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        self.write_report("proposal", [item, item])
        self.assert_rejected("duplicate document paths")

    def test_body_document_hash_and_diff_must_match_exactly(self) -> None:
        cases = (
            ("proposed_body_sha256", "0" * 64, "body does not match"),
            ("proposed_document_sha256", "0" * 64, "document does not match"),
            ("diff", "tampered", "Reported diff does not match"),
        )
        for field, value, error in cases:
            with self.subTest(field=field):
                self.git("checkout", "--", "docs/invitaciones.md")
                item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"), **{field: value})
                self.write_report("proposal", [item])
                self.assert_rejected(error)

    def test_frontmatter_change_other_than_minor_increment_is_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        content = (self.root / "docs/invitaciones.md").read_text(encoding="utf-8").replace("owner: Product", "owner: Other")
        self.write("docs/invitaciones.md", content)
        item["proposed_document_sha256"] = hashlib.sha256(content.encode()).hexdigest()
        self.write_report("proposal", [item])
        self.assert_rejected("Only the deterministic MINOR version increment")

    def test_wrong_major_or_minor_version_is_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"), version="2.0")
        self.write_report("proposal", [item])
        self.assert_rejected("Only the deterministic MINOR version increment")

    def test_version_only_noop_is_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE)
        self.write_report("proposal", [item])
        self.assert_rejected("Proposed body is unchanged")

    def test_abstention_with_changes_is_rejected(self) -> None:
        self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        self.write_report("abstention", [])
        self.assert_rejected("requires an empty Git diff")

    def test_outside_snapshot_added_and_deleted_changes_are_rejected(self) -> None:
        scenarios = (
            (lambda: self.write("README.md", "changed\n"), "outside docs"),
            (lambda: self.write("docs/production-snapshots/state.json", '{"changed":true}\n'), "production-snapshots"),
            (lambda: self.write("docs/new.md", "# New\n"), "untracked files"),
            (lambda: (self.root / "docs/invitaciones.md").unlink(), "status D"),
        )
        for action, error in scenarios:
            with self.subTest(error=error):
                self.git("reset", "--hard", self.base_sha)
                action()
                self.write_report("abstention", [])
                self.assert_rejected(error)

    def test_changed_head_is_rejected(self) -> None:
        self.write("README.md", "committed change\n")
        self.git("add", "README.md")
        self.git("commit", "--quiet", "-m", "Unexpected commit")
        self.assert_rejected("HEAD changed after the trusted base")

    def test_malformed_report_and_invalid_path_are_rejected(self) -> None:
        self.agent_report.write_text("not json", encoding="utf-8")
        self.assert_rejected("valid UTF-8 JSON")
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "traversal"):
            VALIDATOR.validate_relative_path(self.root, "docs/../README.md")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are not supported")
    def test_symlink_target_is_rejected(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        link = self.root / "docs" / "linked.md"
        try:
            os.symlink(outside, link)
        except OSError as error:
            self.skipTest(f"could not create symlink: {error}")
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "Symlinks"):
            VALIDATOR.validate_relative_path(self.root, "docs/linked.md")

    def test_report_missing_required_field_is_rejected(self) -> None:
        value = json.loads(self.agent_report.read_text(encoding="utf-8"))
        value.pop("reason")
        self.agent_report.write_text(json.dumps(value), encoding="utf-8")
        self.assert_rejected("unexpected structure")

    def test_report_unexpected_field_is_rejected(self) -> None:
        self.write_report("abstention", [], unexpected=True)
        self.assert_rejected("unexpected structure")

    def test_report_wrong_root_type_is_rejected(self) -> None:
        self.agent_report.write_text("[]", encoding="utf-8")
        self.assert_rejected("unexpected structure")

    def test_report_field_wrong_type_is_rejected(self) -> None:
        self.write_report("abstention", [], summary=["not", "text"])
        self.assert_rejected("safe non-empty single line")

    def test_report_invalid_decision_is_rejected(self) -> None:
        self.write_report("merge", [])
        self.assert_rejected("decision must be proposal or abstention")

    def test_proposal_with_empty_documents_is_rejected(self) -> None:
        self.write_report("proposal", [])
        self.assert_rejected("requires at least one document")

    def test_abstention_with_declared_documents_is_rejected(self) -> None:
        self.write_report("abstention", [{"path": "docs/invitaciones.md"}])
        self.assert_rejected("unexpected structure")

    def test_report_document_wrong_type_is_rejected(self) -> None:
        self.write_report("proposal", ["docs/invitaciones.md"])
        self.assert_rejected("unexpected structure")

    def test_report_document_missing_required_field_is_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        item.pop("evidence")
        self.write_report("proposal", [item])
        self.assert_rejected("unexpected structure")

    def test_declared_document_without_real_change_is_rejected(self) -> None:
        before = self.git("show", f"{self.base_sha}:docs/invitaciones.md").stdout
        frontmatter, body = VALIDATOR.split_frontmatter(before, "docs/invitaciones.md")
        after = frontmatter.replace("version: 1.0", "version: 1.1") + body
        self.write("docs/invitaciones.md", after)
        item = self.modify("docs/invitaciones.md", body)
        self.write_report("proposal", [item])
        self.assert_rejected("Proposed body is unchanged")

    def test_oversized_report_is_rejected_by_configurable_limit(self) -> None:
        config = VALIDATOR.ValidationConfig(max_diff_bytes=262_144, max_report_bytes=10)
        result = VALIDATOR.validate_repository(self.root, self.agent_report, self.base_sha, config)
        self.assertFalse(result["valid"])
        self.assertIn("too large", "\n".join(result["errors"]))

    def test_large_semantically_valid_document_is_not_rejected_by_line_count(self) -> None:
        body = "\n# Invitations\n\n" + "\n".join(f"Rule {index}" for index in range(2501)) + "\n"
        item = self.modify("docs/invitaciones.md", body)
        self.write_report("proposal", [item])
        result = self.validate()
        self.assertTrue(result["valid"], result)
        self.assertNotIn("max_changed_lines", result["limits"])

    def test_frontmatter_owner_modification_is_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        content = (self.root / "docs/invitaciones.md").read_text(encoding="utf-8").replace("owner: Product", "owner: Security")
        self.write("docs/invitaciones.md", content)
        item["proposed_document_sha256"] = hashlib.sha256(content.encode()).hexdigest()
        self.write_report("proposal", [item])
        self.assert_rejected("Only the deterministic MINOR")

    def test_frontmatter_metadata_removal_is_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        content = (self.root / "docs/invitaciones.md").read_text(encoding="utf-8").replace("owner: Product\n", "")
        self.write("docs/invitaciones.md", content)
        item["proposed_document_sha256"] = hashlib.sha256(content.encode()).hexdigest()
        self.write_report("proposal", [item])
        self.assert_rejected("Only the deterministic MINOR")

    def test_frontmatter_metadata_addition_is_rejected(self) -> None:
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        content = (self.root / "docs/invitaciones.md").read_text(encoding="utf-8").replace("owner: Product\n", "owner: Product\nslug: /unsafe\n")
        self.write("docs/invitaciones.md", content)
        item["proposed_document_sha256"] = hashlib.sha256(content.encode()).hexdigest()
        self.write_report("proposal", [item])
        self.assert_rejected("Only the deterministic MINOR")

    def test_absolute_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "absolute path"):
            VALIDATOR.validate_relative_path(self.root, "/etc/passwd")

    def test_path_outside_docs_is_rejected(self) -> None:
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "outside docs"):
            VALIDATOR.validate_relative_path(self.root, "README.md")

    def test_snapshot_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "read-only"):
            VALIDATOR.validate_relative_path(self.root, "docs/production-snapshots/state.json")

    def test_non_markdown_path_is_rejected(self) -> None:
        self.write("docs/data.json", "{}")
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "not Markdown"):
            VALIDATOR.validate_relative_path(self.root, "docs/data.json")

    def test_nonexistent_markdown_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "existing regular file"):
            VALIDATOR.validate_relative_path(self.root, "docs/missing.md")

    def test_created_document_is_rejected(self) -> None:
        self.write("docs/new.md", FRONTMATTER + "\n# New\n")
        self.write_report("abstention", [])
        self.assert_rejected("untracked files")

    def test_deleted_document_is_rejected(self) -> None:
        (self.root / "docs/invitaciones.md").unlink()
        self.write_report("abstention", [])
        self.assert_rejected("status D")

    def test_moved_document_is_rejected_as_delete_and_add(self) -> None:
        (self.root / "docs/invitaciones.md").rename(self.root / "docs/moved.md")
        self.write_report("abstention", [])
        result = self.validate()
        self.assertFalse(result["valid"])
        self.assertIn("untracked files", "\n".join(result["errors"]))
        self.assertIn("status D", "\n".join(result["errors"]))

    def test_renamed_document_is_rejected(self) -> None:
        self.git("mv", "docs/archivos-adjuntos.md", "docs/renamed.md")
        self.write_report("abstention", [])
        result = self.validate()
        self.assertFalse(result["valid"])
        self.assertIn("status D", "\n".join(result["errors"]))

    def test_workflow_modification_is_rejected(self) -> None:
        self.write(".github/workflows/agent.yml", "name: changed\n")
        self.write_report("abstention", [])
        self.assert_rejected("untracked files")

    def test_script_modification_is_rejected(self) -> None:
        self.write("script.py", "print('unsafe')\n")
        self.write_report("abstention", [])
        self.assert_rejected("untracked files")

    def test_complete_rollback_leaves_no_declared_or_undeclared_change(self) -> None:
        original = (self.root / "docs/invitaciones.md").read_bytes()
        item = self.modify("docs/invitaciones.md", BODY_ONE.replace("24", "48"))
        self.write_report("proposal", [item])
        self.git("checkout", "--", "docs/invitaciones.md")
        self.write_report("abstention", [])
        result = self.validate()
        self.assertTrue(result["valid"], result)
        self.assertEqual(original, (self.root / "docs/invitaciones.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
