from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


NOTIFIER_PATH = (
    Path(__file__).resolve().parents[1] / "notify-jira-documentation-abstention.py"
)
SPEC = importlib.util.spec_from_file_location(
    "notify_jira_documentation_abstention", NOTIFIER_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load Jira notifier from {NOTIFIER_PATH}")
NOTIFIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = NOTIFIER
SPEC.loader.exec_module(NOTIFIER)


class JiraAbstentionNotificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.validation_result = self.root / "validation-result.json"
        self.ticket_file = self.root / "ticket.json"
        self.agent_report = self.root / "agent-report.md"
        self.payload_file = self.root / "jira-abstention-payload.json"
        self.github_output = self.root / "github-output.txt"
        self.write_validation()
        self.ticket_file.write_text(
            json.dumps(
                {
                    "issue_key": "DOC-AGENT-1",
                    "issue_summary": "Ticket summary",
                    "issue_description": "Untrusted ticket description",
                }
            ),
            encoding="utf-8",
        )
        self.write_report("No existe evidencia suficiente")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_validation(
        self,
        *,
        valid: object = True,
        decision: str = "abstention",
        changed_files: list[object] | None = None,
    ) -> None:
        if changed_files is None:
            changed_files = [] if decision == "abstention" else ["docs/example.md"]
        self.validation_result.write_text(
            json.dumps(
                {
                    "valid": valid,
                    "decision": decision,
                    "changed_files": changed_files,
                    "errors": [],
                }
            ),
            encoding="utf-8",
        )

    def write_report(self, reason: str) -> None:
        self.agent_report.write_text(
            json.dumps(
                {
                    "decision": "abstention",
                    "summary": "No responsible proposal",
                    "reason": reason,
                    "evidence": "Reviewed docs and snapshots",
                    "documents": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def prepare(self) -> dict[str, str]:
        return NOTIFIER.prepare_notification(
            validation_result=self.validation_result,
            ticket_file=self.ticket_file,
            agent_report=self.agent_report,
            payload_file=self.payload_file,
            expected_issue_key="DOC-AGENT-1",
            server_url="https://github.com",
            repository="example/documentation-poc",
            run_id="123456789",
        )

    def test_valid_payload_contains_only_the_required_values(self) -> None:
        plan = self.prepare()

        self.assertEqual({"notify": "true", "decision": "abstention"}, plan)
        self.assertEqual(
            {
                "issue_key": "DOC-AGENT-1",
                "decision": "abstention",
                "reason": "No existe evidencia suficiente",
                "actions_url": (
                    "https://github.com/example/documentation-poc/"
                    "actions/runs/123456789"
                ),
            },
            json.loads(self.payload_file.read_text(encoding="utf-8")),
        )

    def test_proposal_is_not_notified(self) -> None:
        self.write_validation(decision="proposal")

        self.assertEqual(
            {"notify": "false", "decision": "proposal"}, self.prepare()
        )
        self.assertFalse(self.payload_file.exists())

    def test_rejected_validation_is_not_notified(self) -> None:
        self.write_validation(valid=False)

        self.assertEqual(
            {"notify": "false", "decision": "rejected"}, self.prepare()
        )
        self.assertFalse(self.payload_file.exists())

    def test_abstention_with_changed_files_is_not_notified(self) -> None:
        self.write_validation(changed_files=["docs/example.md"])

        with self.assertRaises(NOTIFIER.JiraNotificationError):
            self.prepare()
        self.assertFalse(self.payload_file.exists())

    def test_invalid_or_mismatched_issue_key_is_rejected(self) -> None:
        ticket = json.loads(self.ticket_file.read_text(encoding="utf-8"))
        ticket["issue_key"] = "DOC-1; unsafe"
        self.ticket_file.write_text(json.dumps(ticket), encoding="utf-8")

        with self.assertRaises(NOTIFIER.JiraNotificationError):
            self.prepare()

    def test_empty_reason_is_rejected(self) -> None:
        self.write_report("")

        with self.assertRaises(NOTIFIER.JiraNotificationError):
            self.prepare()

    def test_multiline_reason_is_rejected(self) -> None:
        self.write_report("Primera línea\nSegunda línea")

        with self.assertRaises(NOTIFIER.JiraNotificationError):
            self.prepare()

    def test_reason_over_1000_characters_is_rejected(self) -> None:
        self.write_report("x" * 1001)

        with self.assertRaises(NOTIFIER.JiraNotificationError):
            self.prepare()

    def test_actions_url_uses_only_trusted_github_values(self) -> None:
        self.assertEqual(
            "https://github.com/example/repository/actions/runs/42",
            NOTIFIER.build_actions_url(
                "https://github.com", "example/repository", "42"
            ),
        )
        with self.assertRaises(NOTIFIER.JiraNotificationError):
            NOTIFIER.build_actions_url(
                "https://attacker.invalid", "example/repository", "42"
            )

    def test_missing_webhook_url_and_token_are_rejected_without_transport(self) -> None:
        self.prepare()
        calls: list[object] = []

        def transport(request, timeout):  # type: ignore[no-untyped-def]
            calls.append((request, timeout))
            return 204

        for webhook_url, webhook_token in (
            ("", "private-token"),
            ("https://jira.example.invalid/webhook", ""),
            ("", ""),
        ):
            with self.subTest(webhook_url=bool(webhook_url), token=bool(webhook_token)):
                with self.assertRaisesRegex(
                    NOTIFIER.JiraNotificationError, NOTIFIER.GENERIC_SEND_ERROR
                ):
                    NOTIFIER.send_notification(
                        self.payload_file,
                        webhook_url,
                        webhook_token,
                        transport=transport,
                    )
        self.assertEqual([], calls)

    def test_http_error_is_sanitized(self) -> None:
        self.prepare()
        secret_url = "https://jira.example.invalid/secret-webhook"
        secret_token = "private-token"

        def transport(request, timeout):  # type: ignore[no-untyped-def]
            raise urllib.error.HTTPError(
                secret_url, 500, "sensitive response", {}, io.BytesIO(b"secret body")
            )

        with self.assertRaises(NOTIFIER.JiraNotificationError) as raised:
            NOTIFIER.send_notification(
                self.payload_file,
                secret_url,
                secret_token,
                transport=transport,
            )
        message = str(raised.exception)
        self.assertEqual(NOTIFIER.GENERIC_SEND_ERROR, message)
        self.assertNotIn(secret_url, message)
        self.assertNotIn(secret_token, message)
        self.assertNotIn("secret body", message)

    def test_successful_post_uses_required_headers_and_payload(self) -> None:
        self.prepare()
        captured: list[tuple[object, float]] = []

        def transport(request, timeout):  # type: ignore[no-untyped-def]
            captured.append((request, timeout))
            return 204

        NOTIFIER.send_notification(
            self.payload_file,
            "https://jira.example.invalid/webhook",
            "private-token",
            timeout=17,
            transport=transport,
        )

        request, timeout = captured[0]
        headers = {name.lower(): value for name, value in request.header_items()}
        self.assertEqual("POST", request.get_method())
        self.assertEqual("application/json", headers["content-type"])
        self.assertEqual("private-token", headers["x-automation-webhook-token"])
        self.assertEqual(self.payload_file.read_bytes(), request.data)
        self.assertEqual(17, timeout)

    def test_secrets_are_absent_from_logs_and_persistent_files(self) -> None:
        self.prepare()
        secret_url = "https://jira.example.invalid/private-hook"
        secret_token = "never-persist-this-token"

        def transport(request, timeout):  # type: ignore[no-untyped-def]
            raise urllib.error.URLError("sensitive network detail")

        stderr = io.StringIO()
        with mock.patch.dict(
            os.environ,
            {
                "JIRA_AUTOMATION_WEBHOOK_URL": secret_url,
                "JIRA_AUTOMATION_WEBHOOK_TOKEN": secret_token,
            },
            clear=False,
        ), contextlib.redirect_stderr(stderr):
            exit_code = NOTIFIER.main(
                ["send", "--payload-file", str(self.payload_file)],
                transport=transport,
            )

        self.assertEqual(1, exit_code)
        self.assertEqual(NOTIFIER.GENERIC_SEND_ERROR + "\n", stderr.getvalue())
        persisted = b"".join(
            path.read_bytes() for path in self.root.iterdir() if path.is_file()
        )
        self.assertNotIn(secret_url.encode(), persisted)
        self.assertNotIn(secret_token.encode(), persisted)


if __name__ == "__main__":
    unittest.main()
