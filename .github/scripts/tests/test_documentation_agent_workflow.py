from __future__ import annotations

import unittest
from pathlib import Path


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
        self.assertNotIn("old_text", dispatch)
        self.assertNotIn("new_text", dispatch)

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
            "Generate documentation proposal with Gemini",
            "Validate the generated proposal",
            "Prepare validated pull request publication",
            "Prepare Jira abstention notification",
            "Notify Jira of valid documentation abstention",
            "Publish validated documentation pull request",
            "Notify Slack of new documentation pull request",
        )
        positions = [self.workflow.index(f"- name: {name}") for name in expected_steps]
        self.assertEqual(sorted(positions), positions)

    def test_multi_document_publication_uses_one_commit_and_one_pr_creation(self) -> None:
        self.assertEqual(1, self.workflow.count('git commit -m "${COMMIT_MESSAGE}"'))
        self.assertEqual(1, self.workflow.count("gh pr create"))
        self.assertEqual(1, self.workflow.count("gh pr view"))

    def test_ticket_inputs_are_serialized_before_gemini_and_reused_for_jira(self) -> None:
        serialize = self.workflow.index("Validate and serialize ticket inputs")
        gemini = self.workflow.index("Generate documentation proposal with Gemini")
        jira = self.workflow.index("Prepare Jira abstention notification")
        self.assertLess(serialize, gemini)
        self.assertLess(gemini, jira)
        self.assertIn('--ticket-file "${RUNNER_TEMP}/documentation-ticket.json"', self.workflow)


if __name__ == "__main__":
    unittest.main()
