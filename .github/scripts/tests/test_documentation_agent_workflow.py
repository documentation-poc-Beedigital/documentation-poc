from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / "workflows"
    / "documentation-agent-poc.yml"
)


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


if __name__ == "__main__":
    unittest.main()
