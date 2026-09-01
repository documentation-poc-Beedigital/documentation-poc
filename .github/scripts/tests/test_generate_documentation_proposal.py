from __future__ import annotations

import importlib.util
import io
import json
import os
import socket
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path


GENERATOR_PATH = (
    Path(__file__).resolve().parents[1] / "generate-documentation-proposal.py"
)
SPEC = importlib.util.spec_from_file_location(
    "generate_documentation_proposal", GENERATOR_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load generator from {GENERATOR_PATH}")
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
SPEC.loader.exec_module(GENERATOR)


FRONTMATTER = """---
article_id: ART-001
title: Invitations
version: 1.0
status: published
owner: Product
---

"""


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class DocumentationProposalGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "repository with spaces"
        self.root.mkdir()
        (self.root / "docs" / "production-snapshots").mkdir(parents=True)
        self.document = self.root / "docs" / "invitaciones.md"
        self.document.write_text(
            FRONTMATTER + "# Invitations\n\nInvitations expire after 24 hours.\n",
            encoding="utf-8",
            newline="",
        )
        (self.root / "docs" / "production-snapshots" / "invitations.json").write_text(
            '{"current_production_value_hours": 48}\n',
            encoding="utf-8",
            newline="",
        )
        self.ticket_file = Path(self.temporary_directory.name) / "ticket.json"
        self.ticket_file.write_text(
            json.dumps(
                {
                    "issue_key": "DOC-1",
                    "issue_summary": "Update invitation expiry",
                    "issue_description": "Production uses 48 hours.",
                }
            ),
            encoding="utf-8",
        )
        self.prompt_file = Path(self.temporary_directory.name) / "prompt.md"
        self.prompt_file.write_text("Trusted proposal instructions", encoding="utf-8")
        self.report_file = Path(self.temporary_directory.name) / "agent-report.md"
        self.captured_request: dict[str, object] | None = None
        self.captured_key: str | None = None

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def proposal(self, **overrides: str) -> dict[str, str]:
        value = {
            "decision": "proposal",
            "document": "docs/invitaciones.md",
            "old_text": "Invitations expire after 24 hours.",
            "new_text": "Invitations expire after 48 hours.",
            "evidence": "production-snapshots/invitations.json states 48 hours",
            "reason": "align documentation with production",
        }
        value.update(overrides)
        return value

    def response(self, proposal: dict[str, str]) -> dict[str, object]:
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"inlineData": {"mimeType": "ignored/test"}},
                            {"text": json.dumps(proposal, ensure_ascii=False)},
                        ]
                    }
                }
            ],
        }

    def transport_response(self, response: dict[str, object]):
        def transport(
            endpoint: str,
            api_key: str,
            payload: dict[str, object],
            timeout: float,
        ) -> dict[str, object]:
            self.assertEqual(GENERATOR.API_URL, endpoint)
            self.assertGreater(timeout, 0)
            self.captured_key = api_key
            self.captured_request = payload
            return response

        return transport

    def transport_for(self, proposal: dict[str, str]):
        return self.transport_response(self.response(proposal))

    def http_error(self, code: int, message: str) -> urllib.error.HTTPError:
        body = json.dumps({"error": {"message": message}}).encode("utf-8")
        return urllib.error.HTTPError(
            GENERATOR.API_URL,
            code,
            "simulated error",
            None,
            io.BytesIO(body),
        )

    def sequence_opener(self, outcomes: list[object]):
        pending = list(outcomes)
        requests: list[object] = []

        def opener(request: object, timeout: float) -> object:
            self.assertGreater(timeout, 0)
            requests.append(request)
            outcome = pending.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        return opener, requests

    def run_generator(self, proposal: dict[str, str]) -> dict[str, str]:
        return GENERATOR.generate_and_apply(
            repo_root=self.root,
            ticket_file=self.ticket_file,
            prompt_file=self.prompt_file,
            report_file=self.report_file,
            api_key="test-secret-key",
            transport=self.transport_for(proposal),
        )

    def assert_rejected_without_change(
        self,
        proposal: dict[str, str],
        expected_message: str,
    ) -> None:
        before = self.document.read_text(encoding="utf-8")
        with self.assertRaisesRegex(GENERATOR.ProposalError, expected_message):
            self.run_generator(proposal)
        self.assertEqual(before, self.document.read_text(encoding="utf-8"))
        self.assertFalse(self.report_file.exists())

    def test_valid_proposal_applies_one_literal_replacement(self) -> None:
        result = self.run_generator(self.proposal())

        self.assertEqual("proposal", result["decision"])
        content = self.document.read_text(encoding="utf-8")
        self.assertNotIn("Invitations expire after 24 hours.", content)
        self.assertIn("Invitations expire after 48 hours.", content)
        self.assertEqual(
            "Decisión: propuesta\n"
            "Documento: docs/invitaciones.md\n"
            "Evidencia: production-snapshots/invitations.json states 48 hours\n"
            "Texto anterior: Invitations expire after 24 hours.\n"
            "Texto propuesto: Invitations expire after 48 hours.\n"
            "Motivo: align documentation with production\n",
            self.report_file.read_text(encoding="utf-8"),
        )

    def test_abstention_writes_report_without_modifying_docs(self) -> None:
        before = self.document.read_text(encoding="utf-8")
        result = self.run_generator(
            self.proposal(
                decision="abstention",
                document="ninguno",
                old_text="no aplica",
                new_text="no aplica",
                evidence="evidence is contradictory",
                reason="abstain safely",
            )
        )

        self.assertEqual("abstention", result["decision"])
        self.assertEqual(before, self.document.read_text(encoding="utf-8"))
        self.assertIn("Decisión: abstención\n", self.report_file.read_text(encoding="utf-8"))

    def test_request_uses_stable_model_strict_schema_and_no_tools(self) -> None:
        self.run_generator(
            self.proposal(
                decision="abstention",
                document="ninguno",
                old_text="no aplica",
                new_text="no aplica",
            )
        )

        assert self.captured_request is not None
        self.assertEqual(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3.7-flash:generateContent",
            GENERATOR.API_URL,
        )
        self.assertEqual(
            {"systemInstruction", "contents", "generationConfig"},
            set(self.captured_request),
        )
        generation_config = self.captured_request["generationConfig"]
        self.assertEqual(4096, generation_config["maxOutputTokens"])
        response_text = generation_config["responseFormat"]["text"]
        self.assertEqual("APPLICATION_JSON", response_text["mimeType"])
        schema = response_text["schema"]
        self.assertIs(False, schema["additionalProperties"])
        self.assertEqual(sorted(GENERATOR.PROPOSAL_FIELDS), schema["required"])
        contents = self.captured_request["contents"]
        self.assertEqual("user", contents[0]["role"])
        untrusted_input = json.loads(contents[0]["parts"][0]["text"])
        self.assertEqual("DOC-1", untrusted_input["ticket"]["issue_key"])
        self.assertTrue(untrusted_input["documents"])
        system_instruction = self.captured_request["systemInstruction"]
        self.assertNotIn("DOC-1", system_instruction["parts"][0]["text"])
        self.assertNotIn("test-secret-key", json.dumps(self.captured_request))

    def test_generate_content_response_requires_candidates(self) -> None:
        with self.assertRaisesRegex(GENERATOR.ProposalError, "no candidates"):
            GENERATOR.extract_output_text({})

    def test_generate_content_response_requires_text(self) -> None:
        response = {
            "candidates": [
                {"content": {"parts": [{"inlineData": {"data": "ignored"}}]}}
            ]
        }
        with self.assertRaisesRegex(GENERATOR.ProposalError, "no textual content"):
            GENERATOR.extract_output_text(response)

    def test_generate_content_invalid_proposal_json_is_rejected(self) -> None:
        response = {"candidates": [{"content": {"parts": [{"text": "{invalid"}]}}]}
        with self.assertRaisesRegex(GENERATOR.ProposalError, "not valid JSON"):
            GENERATOR.parse_proposal(GENERATOR.extract_output_text(response))

    def test_http_500_is_retried_then_succeeds(self) -> None:
        expected = self.response(self.proposal())
        opener, requests = self.sequence_opener(
            [self.http_error(500, "temporary backend failure"), FakeHTTPResponse(expected)]
        )
        sleeps: list[float] = []

        result = GENERATOR.http_transport(
            GENERATOR.API_URL,
            "test-secret-key",
            {"contents": []},
            15.0,
            opener=opener,
            sleeper=sleeps.append,
        )

        self.assertEqual(expected, result)
        self.assertEqual([2.0], sleeps)
        self.assertEqual(2, len(requests))
        self.assertEqual(
            "test-secret-key", requests[0].get_header("X-goog-api-key")
        )
        self.assertNotIn("test-secret-key", requests[0].full_url)

    def test_transient_http_retries_are_exhausted_after_three_attempts(self) -> None:
        opener, requests = self.sequence_opener(
            [
                self.http_error(500, "first failure"),
                self.http_error(503, "second failure"),
                self.http_error(504, "final failure test-secret-key"),
            ]
        )
        sleeps: list[float] = []

        with self.assertRaises(GENERATOR.ProposalError) as raised:
            GENERATOR.http_transport(
                GENERATOR.API_URL,
                "test-secret-key",
                {"contents": []},
                15.0,
                opener=opener,
                sleeper=sleeps.append,
            )

        message = str(raised.exception)
        self.assertIn("HTTP 504", message)
        self.assertIn("final failure", message)
        self.assertNotIn("test-secret-key", message)
        self.assertEqual([2.0, 5.0], sleeps)
        self.assertEqual(3, len(requests))

    def test_http_401_is_not_retried(self) -> None:
        opener, requests = self.sequence_opener(
            [self.http_error(401, "invalid credential test-secret-key")]
        )
        sleeps: list[float] = []

        with self.assertRaises(GENERATOR.ProposalError) as raised:
            GENERATOR.http_transport(
                GENERATOR.API_URL,
                "test-secret-key",
                {"contents": []},
                15.0,
                opener=opener,
                sleeper=sleeps.append,
            )

        self.assertIn("HTTP 401", str(raised.exception))
        self.assertNotIn("test-secret-key", str(raised.exception))
        self.assertEqual([], sleeps)
        self.assertEqual(1, len(requests))

    def test_read_timeout_is_retried_then_succeeds(self) -> None:
        expected = self.response(self.proposal())
        opener, requests = self.sequence_opener(
            [socket.timeout("read timed out"), FakeHTTPResponse(expected)]
        )
        sleeps: list[float] = []

        result = GENERATOR.http_transport(
            GENERATOR.API_URL,
            "test-secret-key",
            {"contents": []},
            15.0,
            opener=opener,
            sleeper=sleeps.append,
        )

        self.assertEqual(expected, result)
        self.assertEqual([2.0], sleeps)
        self.assertEqual(2, len(requests))

    def test_reads_regular_docs_and_snapshots_as_evidence(self) -> None:
        documents = GENERATOR.read_documentation(self.root)
        paths = {item["path"] for item in documents}
        self.assertIn("docs/invitaciones.md", paths)
        self.assertIn("docs/production-snapshots/invitations.json", paths)

    def test_ignores_symlinks(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.root / "docs" / "linked.txt"
        try:
            os.symlink(outside, link)
        except OSError as error:
            self.skipTest(f"could not create symlink: {error}")

        documents = GENERATOR.read_documentation(self.root)
        paths = {item["path"] for item in documents}
        self.assertNotIn("docs/linked.txt", paths)

    def test_old_text_must_appear_exactly_once(self) -> None:
        self.assert_rejected_without_change(
            self.proposal(old_text="missing text"),
            "old_text must appear exactly once",
        )

        original = self.document.read_text(encoding="utf-8")
        self.document.write_text(
            original + "\nInvitations expire after 24 hours.\n",
            encoding="utf-8",
            newline="",
        )
        self.assert_rejected_without_change(
            self.proposal(),
            "old_text must appear exactly once",
        )

    def test_rejects_document_outside_docs(self) -> None:
        self.assert_rejected_without_change(
            self.proposal(document="README.md"),
            "outside docs/",
        )

    def test_rejects_document_path_traversal(self) -> None:
        self.assert_rejected_without_change(
            self.proposal(document="docs/../README.md"),
            "Unsafe proposal document path",
        )

    def test_rejects_production_snapshot_as_target(self) -> None:
        self.assert_rejected_without_change(
            self.proposal(
                document="docs/production-snapshots/invitations.json",
                old_text='{"current_production_value_hours": 48}',
                new_text='{"current_production_value_hours": 72}',
            ),
            "production-snapshots is read-only",
        )

    def test_rejects_frontmatter_change(self) -> None:
        self.assert_rejected_without_change(
            self.proposal(
                old_text="title: Invitations",
                new_text="title: Updated Invitations",
            ),
            "changes frontmatter",
        )

    def test_rejects_new_text_that_already_exists(self) -> None:
        self.assert_rejected_without_change(
            self.proposal(new_text="# Invitations"),
            "new_text already exists",
        )

    def test_rejects_multiline_replacement_text(self) -> None:
        for field in ("old_text", "new_text"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(GENERATOR.ProposalError, "must be single-line"):
                    GENERATOR.parse_proposal(
                        json.dumps(self.proposal(**{field: "first\nsecond"}))
                    )

    def test_rejects_missing_extra_and_invalid_decision(self) -> None:
        missing = self.proposal()
        del missing["reason"]
        extra = {**self.proposal(), "extra": "not allowed"}
        for value in (missing, extra):
            with self.subTest(keys=sorted(value)):
                with self.assertRaisesRegex(GENERATOR.ProposalError, "required fields"):
                    GENERATOR.parse_proposal(json.dumps(value))

        with self.assertRaisesRegex(GENERATOR.ProposalError, "proposal or abstention"):
            GENERATOR.parse_proposal(
                json.dumps(self.proposal(decision="modify"))
            )

    def test_rejects_invalid_abstention_values(self) -> None:
        with self.assertRaisesRegex(GENERATOR.ProposalError, "ninguno"):
            GENERATOR.parse_proposal(
                json.dumps(self.proposal(decision="abstention"))
            )
        with self.assertRaisesRegex(GENERATOR.ProposalError, "no aplica"):
            GENERATOR.parse_proposal(
                json.dumps(
                    self.proposal(
                        decision="abstention",
                        document="ninguno",
                    )
                )
            )

    def test_api_key_is_not_written_to_repository_or_report(self) -> None:
        self.run_generator(self.proposal())
        for path in self.root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                self.assertNotIn("test-secret-key", path.read_text(encoding="utf-8"))
        self.assertNotIn("test-secret-key", self.report_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
