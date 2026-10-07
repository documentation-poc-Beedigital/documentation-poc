from __future__ import annotations

import io
import json
import os
import re
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / "workflows"
    / "documentation-agent-poc.yml"
)
LEGACY_WORKFLOW = WORKFLOW.with_name("documentation-proposal.yml")


class DocumentationAgentWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_slack_runs_only_for_a_newly_confirmed_pull_request(self) -> None:
        confirmation = self.workflow.index('confirmed_pr_url="$(gh pr view')
        created_output = self.workflow.index("created=true", confirmation)
        slack_step = self.workflow.index(
            "- name: Notify Slack of new documentation pull request"
        )
        self.assertLess(confirmation, created_output)
        self.assertLess(created_output, slack_step)
        self.assertIn(
            "if: steps.pull_request.outputs.created == 'true'",
            self.workflow[slack_step:],
        )

    def test_abstention_and_publication_failures_cannot_reach_slack(self) -> None:
        publication_step = self.workflow.index(
            "- name: Publish validated documentation pull request"
        )
        slack_step = self.workflow.index(
            "- name: Notify Slack of new documentation pull request"
        )
        publication = self.workflow[publication_step:slack_step]
        self.assertIn("if: steps.publication.outputs.publish == 'true'", publication)
        self.assertIn("exit 1", publication)
        self.assertNotIn("created=true", publication[: publication.index("gh pr create")])

    def test_rerun_reuses_url_and_marks_pr_as_not_new(self) -> None:
        self.assertIn("Open pull request reused", self.workflow)
        reused = self.workflow.index("Open pull request reused")
        self.assertIn("created=false", self.workflow[:reused])

    def test_webhook_comes_only_from_the_named_secret(self) -> None:
        assignment = (
            "SLACK_DOCUMENTATION_WEBHOOK_URL: "
            "${{ secrets.SLACK_DOCUMENTATION_WEBHOOK_URL }}"
        )
        self.assertEqual(1, self.workflow.count(assignment))
        self.assertNotIn("hooks.slack.com", self.workflow)

    def test_publication_stages_and_commits_every_validated_document(self) -> None:
        self.assertIn("DOCUMENTS_JSON: ${{ steps.publication.outputs.documents_json }}", self.workflow)
        self.assertIn('git add -- "${documents[@]}"', self.workflow)
        self.assertIn('git commit -m "${COMMIT_MESSAGE}" -- "${documents[@]}"', self.workflow)
        self.assertIn('--documents-json "${DOCUMENTS_JSON}"', self.workflow)
        self.assertNotIn('DOCUMENT: ${{ steps.publication.outputs.document }}', self.workflow)

    def test_jira_input_contract_is_unchanged(self) -> None:
        dispatch = self.workflow[: self.workflow.index("concurrency:")]
        for field in ("issue_key", "issue_summary", "issue_description"):
            self.assertIn(f"      {field}:\n", dispatch)
        self.assertIn("      diagnose_only:\n", dispatch)
        self.assertIn("        type: boolean", dispatch)
        self.assertIn("        default: false", dispatch)
        self.assertNotIn("old_text", dispatch)
        self.assertNotIn("new_text", dispatch)

    def test_diagnostic_job_is_isolated_from_claude_and_publication(self) -> None:
        diagnostic_start = self.workflow.index("  diagnose-jira-context:")
        proposal_start = self.workflow.index("  prepare-proposal:")
        diagnostic = self.workflow[diagnostic_start:proposal_start]
        self.assertIn("if: ${{ inputs.diagnose_only }}", diagnostic)
        self.assertIn("contents: read", diagnostic)
        self.assertIn("--diagnose-jira-context", diagnostic)
        self.assertIn("parse_jira_source_inputs", diagnostic)
        for secret in ("JIRA_BASE_URL", "JIRA_API_EMAIL", "JIRA_API_TOKEN"):
            self.assertIn(f"{secret}: ${{{{ secrets.{secret} }}}}", diagnostic)
        for forbidden in (
            "ANTHROPIC_API_KEY", "Claude", "git commit", "git push", "gh pr create",
            "prepare-documentation-pull-request.py",
            "notify-", "SLACK", "upload-artifact", "contents: write", "pull-requests:",
            "generate_and_apply", "http_transport",
            "ISSUE_SUMMARY:", "ISSUE_DESCRIPTION:", "inputs.issue_summary", "inputs.issue_description",
        ):
            self.assertNotIn(forbidden, diagnostic)
        self.assertIn('persist-credentials: false', diagnostic)
        self.assertNotIn('ref: main', diagnostic)
        self.assertIn('--prompt-file ".github/prompts/documentation-agent-poc.md"', diagnostic)
        self.assertIn('--repo-root "${GITHUB_WORKSPACE}"', diagnostic)
        self.assertIn('--base-sha "${{ steps.base.outputs.sha }}"', diagnostic)
        self.assertIn('os.environ["GITHUB_EVENT_PATH"]', diagnostic)
        serialize = diagnostic.index("Serialize diagnostic ticket input")
        credentials = diagnostic.index("JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}")
        self.assertLess(serialize, credentials)
        proposal_header = self.workflow[proposal_start:self.workflow.index("    steps:", proposal_start)]
        self.assertIn("if: ${{ !inputs.diagnose_only }}", proposal_header)

    def serialization_code(self, step_name: str) -> str:
        step = self.workflow[self.workflow.index(f"- name: {step_name}"):]
        match = re.search(r"python - <<'PY'\n(.*?)\n          PY", step, re.DOTALL)
        self.assertIsNotNone(match)
        return textwrap.dedent(match.group(1))

    def serialize_ticket(self, step_name: str, inputs: dict[str, str]) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as temporary:
            event_file = Path(temporary) / "event.json"
            event_file.write_text(json.dumps({"inputs": {
                name.lower(): value for name, value in inputs.items()
            }}), encoding="utf-8")
            environment = {
                "RUNNER_TEMP": temporary,
                "GITHUB_OUTPUT": str(Path(temporary) / "output"),
                "GITHUB_EVENT_PATH": str(event_file),
                **inputs,
            }
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.object(os, "environ", environment), \
                 mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
                exec(compile(self.serialization_code(step_name), str(WORKFLOW), "exec"), {})
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            return json.loads((Path(temporary) / "documentation-ticket.json").read_text(encoding="utf-8"))

    def test_diagnostic_inputs_are_optional_in_form_and_description_is_optional(self) -> None:
        dispatch = self.workflow[: self.workflow.index("concurrency:")]
        for name in ("issue_description", "jira_epic_key", "jira_task_keys"):
            block = re.split(r"\n      \S", dispatch.split(f"      {name}:\n", 1)[1], maxsplit=1)[0]
            self.assertIn("required: false", block)
            self.assertIn("type: string", block)
        for name in ("issue_key", "issue_summary"):
            block = re.split(r"\n      \S", dispatch.split(f"      {name}:\n", 1)[1], maxsplit=1)[0]
            self.assertIn("required: true", block)

    def test_diagnostic_serialization_accepts_absent_description(self) -> None:
        result = self.serialize_ticket("Serialize diagnostic ticket input", {
            "ISSUE_KEY": "DOC-999", "ISSUE_SUMMARY": "Documentation",
            "JIRA_EPIC_KEY": "DOC-123", "JIRA_TASK_KEYS": " DOC-124 , DOC-125 ",
        })
        self.assertEqual({
            "issue_key": "DOC-999", "issue_summary": "Documentation",
            "issue_description": "",
        }, result)
        self.assertNotIn("\\n", result["issue_description"])

    def test_diagnostic_serialization_rejects_missing_and_invalid_inputs(self) -> None:
        cases = (
            ("", "DOC-124", "must be provided together"),
            ("DOC-123", "", "must be provided together"),
            ("DOC-123", "DOC-124, DOC-124", "duplicate keys"),
            ("DOC-123", "DOC-124,", "empty element at position 2"),
            ("DOC-123", "DOC-124,,DOC-125", "empty element at position 2"),
            ("DOC-123", "DOC-124 PRIVATE_INPUT", "element at position 1"),
            ("DOC-123 PRIVATE_INPUT", "DOC-124", "jira_epic_key must"),
        )
        for epic, tasks, error in cases:
            with self.subTest(epic=epic, tasks=tasks), self.assertRaisesRegex(SystemExit, error) as raised:
                self.serialize_ticket("Serialize diagnostic ticket input", {
                    "ISSUE_KEY": "DOC-999", "ISSUE_SUMMARY": "Documentation",
                    "JIRA_EPIC_KEY": epic, "JIRA_TASK_KEYS": tasks,
                })
            self.assertNotIn("PRIVATE_INPUT", str(raised.exception))

    def test_normal_serialization_preserves_original_inputs_without_diagnostic_fields(self) -> None:
        inputs = {
            "ISSUE_KEY": "DOC-999", "ISSUE_SUMMARY": "Documentation",
            "ISSUE_DESCRIPTION": "Original description\nwith evidence",
        }
        self.assertEqual({
            "issue_key": inputs["ISSUE_KEY"], "issue_summary": inputs["ISSUE_SUMMARY"],
            "issue_description": inputs["ISSUE_DESCRIPTION"],
        }, self.serialize_ticket("Validate and serialize ticket inputs", inputs))
        inputs["JIRA_EPIC_KEY"] = "invalid diagnostic input"
        inputs["JIRA_TASK_KEYS"] = ","
        with self.assertRaisesRegex(SystemExit, "jira_epic_key must"):
            self.serialize_ticket("Validate and serialize ticket inputs", inputs)

    def test_both_jobs_preserve_human_description_and_pass_references_separately(self) -> None:
        inputs = {
            "ISSUE_KEY": "OTHER-999", "ISSUE_SUMMARY": "Documentation",
            "ISSUE_DESCRIPTION": "# PM context\n[Link](https://example.invalid)\n  ",
            "JIRA_EPIC_KEY": "APP-123", "JIRA_TASK_KEYS": " APP-124 , TEAM-125 ",
        }
        normal = self.serialize_ticket("Validate and serialize ticket inputs", inputs)
        diagnostic = self.serialize_ticket("Serialize diagnostic ticket input", inputs)
        self.assertEqual(normal, diagnostic)
        self.assertEqual(inputs["ISSUE_DESCRIPTION"], normal["issue_description"])
        self.assertEqual({"issue_key", "issue_summary", "issue_description"}, set(normal))
        for flag in ('--jira-epic-key "${JIRA_EPIC_KEY}"', '--jira-task-keys "${JIRA_TASK_KEYS}"'):
            self.assertEqual(2, self.workflow.count(flag))

    def test_normal_serialization_rejects_incomplete_invalid_or_duplicate_references(self) -> None:
        for epic, tasks in (("APP-1", ""), ("", "APP-2"), ("app-1", "APP-2"),
                            ("APP-1", "APP-2,"), ("APP-1", "APP-2, APP-2")):
            with self.subTest(epic=epic, tasks=tasks), self.assertRaises(SystemExit):
                self.serialize_ticket("Validate and serialize ticket inputs", {
                    "ISSUE_KEY": "DOC-999", "ISSUE_SUMMARY": "Documentation",
                    "ISSUE_DESCRIPTION": "DOCUMENTATION_SOURCE_V1\nEPIC_KEY: APP-1\nTASK_KEYS:\n- APP-2\n",
                    "JIRA_EPIC_KEY": epic, "JIRA_TASK_KEYS": tasks,
                })

    def test_normal_serialization_still_requires_and_validates_description(self) -> None:
        for description in ("", " \n\t", "x" * 60_001, "bad\x00content"):
            with self.subTest(length=len(description)), self.assertRaisesRegex(SystemExit, "issue_description"):
                self.serialize_ticket("Validate and serialize ticket inputs", {
                    "ISSUE_KEY": "DOC-999", "ISSUE_SUMMARY": "Documentation",
                    "ISSUE_DESCRIPTION": description,
                })

    def test_unsafe_legacy_parallel_workflow_is_removed(self) -> None:
        self.assertFalse(LEGACY_WORKFLOW.exists())

    def test_only_documentation_agent_workflow_has_manual_dispatch(self) -> None:
        workflow_directory = WORKFLOW.parent
        dispatched = [
            path.name
            for path in workflow_directory.glob("*.yml")
            if "workflow_dispatch:" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(["documentation-agent-poc.yml"], dispatched)

    def test_active_workflows_do_not_reference_legacy_workflow(self) -> None:
        for path in WORKFLOW.parent.glob("*.yml"):
            self.assertNotIn("documentation-proposal.yml", path.read_text(encoding="utf-8"))

    def test_current_workflow_contains_complete_agent_pipeline(self) -> None:
        expected_steps = (
            "Generate documentation proposal with Claude",
            "Validate the generated proposal",
            "Prepare validated pull request publication",
            "Prepare Jira abstention notification",
            "Notify Jira of valid documentation abstention",
            "Publish validated documentation pull request",
            "Notify Slack of new documentation pull request",
        )
        positions = [self.workflow.index(f"- name: {name}") for name in expected_steps]
        self.assertEqual(sorted(positions), positions)

    def test_emergency_report_abstains_and_skipped_claude_is_not_validated(self) -> None:
        report_step = self.workflow.index("- name: Ensure an agent report exists")
        validation_step = self.workflow.index("- name: Validate the generated proposal")
        report = self.workflow[report_step:validation_step]
        self.assertIn('"decision": "abstention"', report)
        self.assertNotIn('"decision": "error"', report)
        self.assertIn("El flujo no produjo una propuesta de Claude validable", report)

        validation = self.workflow[
            validation_step:self.workflow.index("- name: Capture generated diff")
        ]
        self.assertIn(
            "if: always() && steps.claude.outcome != 'skipped'", validation
        )

    def test_multi_document_publication_uses_one_commit_and_one_pr_creation(self) -> None:
        self.assertEqual(1, self.workflow.count('git commit -m "${COMMIT_MESSAGE}"'))
        self.assertEqual(1, self.workflow.count("gh pr create"))
        self.assertEqual(1, self.workflow.count("gh pr view"))

    def test_ticket_inputs_are_serialized_before_claude_and_reused_for_jira(self) -> None:
        serialize = self.workflow.index("Validate and serialize ticket inputs")
        claude = self.workflow.index("Generate documentation proposal with Claude")
        jira = self.workflow.index("Prepare Jira abstention notification")
        self.assertLess(serialize, claude)
        self.assertLess(claude, jira)
        self.assertIn('--ticket-file "${RUNNER_TEMP}/documentation-ticket.json"', self.workflow)

    def test_jira_description_limit_is_60000_characters(self) -> None:
        self.assertIn("max_issue_description_characters = 60_000", self.workflow)
        self.assertIn("between 1 and 60000 characters", self.workflow)
        self.assertNotIn("len(issue_description) <= 20_000", self.workflow)

    def test_jira_cloud_secrets_are_scoped_to_the_agent_step(self) -> None:
        claude_step = self.workflow[self.workflow.index("- name: Generate documentation proposal with Claude"):]
        for secret in ("JIRA_BASE_URL", "JIRA_API_EMAIL", "JIRA_API_TOKEN"):
            self.assertIn(f"{secret}: ${{{{ secrets.{secret} }}}}", claude_step)

    def test_end_to_end_pipeline_supports_created_and_updated_files(self) -> None:
        self.assertIn("--base-sha", self.workflow)
        self.assertIn("Validate documentation site after applying proposal", self.workflow)
        self.assertIn("npm run build", self.workflow)
        self.assertIn('[ "${status}" != "M" ] && [ "${status}" != "A" ]', self.workflow)
        self.assertIn('git add -- "${documents[@]}"', self.workflow)
        self.assertEqual(1, self.workflow.count("gh pr create"))


if __name__ == "__main__":
    unittest.main()
