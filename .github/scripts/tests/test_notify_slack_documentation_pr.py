from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


NOTIFIER_PATH = (
    Path(__file__).resolve().parents[1] / "notify-slack-documentation-pr.py"
)
SPEC = importlib.util.spec_from_file_location(
    "notify_slack_documentation_pr", NOTIFIER_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load Slack notifier from {NOTIFIER_PATH}")
NOTIFIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = NOTIFIER
SPEC.loader.exec_module(NOTIFIER)


class SlackDocumentationNotificationTests(unittest.TestCase):
    def fields(self, **overrides: object) -> dict[str, object]:
        fields: dict[str, object] = {
            "issue_key": "DOC-32",
            "issue_summary": "Automatizar la activación del agente",
            "documents": [
                {
                    "path": "docs/flujo-agente-documentacion.md",
                    "reason": "Ticket",
                    "evidence": "Docs",
                    "previous_version": "1.0",
                    "proposed_version": "1.1",
                },
                {
                    "path": "docs/invitaciones.md",
                    "reason": "Coherence",
                    "evidence": "Docs",
                    "previous_version": "2.4",
                    "proposed_version": "2.5",
                },
            ],
            "pr_url": "https://github.com/example/docs/pull/42",
        }
        fields.update(overrides)
        return fields

    def main_args(self) -> list[str]:
        fields = self.fields()
        return [
            "send",
            "--issue-key", str(fields["issue_key"]),
            "--issue-summary", str(fields["issue_summary"]),
            "--documents-json", json.dumps(fields["documents"]),
            "--pr-url", str(fields["pr_url"]),
            "--timeout", "7",
        ]

    def test_message_contains_every_required_field(self) -> None:
        message = NOTIFIER.build_message(**self.fields())
        self.assertIn("Nueva propuesta documental pendiente de aprobación", message)
        self.assertIn("DOC-32", message)
        self.assertIn("Automatizar la activación del agente", message)
        self.assertIn("docs/flujo-agente-documentacion.md", message)
        self.assertIn("1.0 → 1.1", message)
        self.assertIn("docs/invitaciones.md", message)
        self.assertIn("2.4 → 2.5", message)
        self.assertIn("https://github.com/example/docs/pull/42", message)
        self.assertIn("requiere aprobación humana", message)

    def test_quotes_accents_and_special_characters_are_valid_json(self) -> None:
        payload = NOTIFIER.build_payload(
            **self.fields(issue_summary='Añadir "revisión" de café, 50% & <segura> ¿ya? <!channel>')
        )
        decoded = json.loads(payload.decode("utf-8"))
        self.assertIn('"revisión"', decoded["text"])
        self.assertIn(
            "café, 50% &amp; &lt;segura&gt; ¿ya?", decoded["text"]
        )
        self.assertNotIn("<!channel>", decoded["text"])
        self.assertIn("&lt;!channel&gt;", decoded["text"])

    def test_missing_webhook_warns_and_continues_without_transport(self) -> None:
        calls: list[object] = []
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(stderr):
            result = NOTIFIER.main(
                self.main_args(), transport=lambda request, timeout: calls.append(request)
            )
        self.assertEqual(0, result)
        self.assertEqual([], calls)
        self.assertEqual(NOTIFIER.MISSING_WEBHOOK_WARNING + "\n", stderr.getvalue())

    def test_timeout_warns_and_does_not_fail_the_completed_pr(self) -> None:
        def timeout_transport(request, timeout):  # type: ignore[no-untyped-def]
            raise TimeoutError("secret transport detail")

        stderr = io.StringIO()
        with mock.patch.dict(
            os.environ,
            {"SLACK_DOCUMENTATION_WEBHOOK_URL": "https://hooks.slack.invalid/private"},
            clear=True,
        ), contextlib.redirect_stderr(stderr):
            result = NOTIFIER.main(self.main_args(), transport=timeout_transport)
        self.assertEqual(0, result)
        self.assertEqual(NOTIFIER.GENERIC_SEND_WARNING + "\n", stderr.getvalue())

    def test_http_error_warns_without_response_details(self) -> None:
        secret = "https://hooks.slack.invalid/services/private-secret"

        def error_transport(request, timeout):  # type: ignore[no-untyped-def]
            raise urllib.error.HTTPError(
                secret, 500, "private error", {}, io.BytesIO(b"private body")
            )

        stderr = io.StringIO()
        with mock.patch.dict(
            os.environ, {"SLACK_DOCUMENTATION_WEBHOOK_URL": secret}, clear=True
        ), contextlib.redirect_stderr(stderr):
            result = NOTIFIER.main(self.main_args(), transport=error_transport)
        self.assertEqual(0, result)
        self.assertEqual(NOTIFIER.GENERIC_SEND_WARNING + "\n", stderr.getvalue())
        self.assertNotIn(secret, stderr.getvalue())

    def test_non_success_http_status_is_an_error(self) -> None:
        with self.assertRaisesRegex(
            NOTIFIER.SlackNotificationError, "Slack notification failed"
        ):
            NOTIFIER.send_notification(
                "https://hooks.slack.invalid/services/test",
                NOTIFIER.build_payload(**self.fields()),
                transport=lambda request, timeout: 503,
            )

    def test_abstention_and_failure_before_pr_do_not_notify(self) -> None:
        self.assertFalse(NOTIFIER.should_notify("abstention", False, None))
        self.assertFalse(NOTIFIER.should_notify("proposal", False, None))
        self.assertFalse(
            NOTIFIER.should_notify(
                "proposal", False, "https://github.com/example/docs/pull/42"
            )
        )

    def test_rerun_reuses_existing_pr_without_second_notification(self) -> None:
        candidates = [
            {
                "title": "DOC-32 [Documentación] Existing proposal",
                "headRefName": "automation/documentation-doc-32-100-1",
                "url": "https://github.com/example/docs/pull/42",
            }
        ]
        url = NOTIFIER.find_existing_pull_request(
            candidates,
            "automation/documentation-doc-32-100-2",
            "DOC-32",
            "example/docs",
        )
        self.assertEqual("https://github.com/example/docs/pull/42", url)
        self.assertFalse(NOTIFIER.should_notify("proposal", False, url))

    def test_exact_branch_is_preferred_over_ticket_match(self) -> None:
        candidates = [
            {
                "title": "DOC-32 [Documentación] Older proposal",
                "headRefName": "automation/other",
                "url": "https://github.com/example/docs/pull/41",
            },
            {
                "title": "OTHER-1 Different title",
                "headRefName": "automation/documentation-doc-32-100-2",
                "url": "https://github.com/example/docs/pull/42",
            },
        ]
        self.assertEqual(
            "https://github.com/example/docs/pull/42",
            NOTIFIER.find_existing_pull_request(
                candidates,
                "automation/documentation-doc-32-100-2",
                "DOC-32",
                "example/docs",
            ),
        )

    def test_webhook_never_appears_in_errors_or_logs(self) -> None:
        secret = "https://hooks.slack.invalid/services/T000/B000/SECRET"
        stderr = io.StringIO()
        with mock.patch.dict(
            os.environ, {"SLACK_DOCUMENTATION_WEBHOOK_URL": secret}, clear=True
        ), contextlib.redirect_stderr(stderr):
            result = NOTIFIER.main(
                self.main_args(),
                transport=lambda request, timeout: (_ for _ in ()).throw(
                    urllib.error.URLError(secret)
                ),
            )
        self.assertEqual(0, result)
        self.assertNotIn(secret, stderr.getvalue())
        self.assertEqual(NOTIFIER.GENERIC_SEND_WARNING + "\n", stderr.getvalue())

    def test_successful_request_uses_json_and_timeout(self) -> None:
        captured: list[tuple[object, float]] = []

        def transport(request, timeout):  # type: ignore[no-untyped-def]
            captured.append((request, timeout))
            return 200

        NOTIFIER.send_notification(
            "https://hooks.slack.invalid/services/test",
            NOTIFIER.build_payload(**self.fields()),
            timeout=9,
            transport=transport,
        )
        request, timeout = captured[0]
        self.assertEqual("POST", request.get_method())
        self.assertEqual(9, timeout)
        self.assertEqual(
            "application/json; charset=utf-8",
            {key.lower(): value for key, value in request.header_items()}[
                "content-type"
            ],
        )
        json.loads(request.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
