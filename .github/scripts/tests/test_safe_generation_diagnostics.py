from __future__ import annotations

import io
import json
import socket
import unittest
import urllib.error
from unittest import mock

import test_generate_documentation_proposal as fixture

G = fixture.GENERATOR
FakeResponse = fixture.FakeResponse
response_envelope = fixture.response_envelope

PRIVATE = "PRIVATE_TICKET_DOCUMENT_PROMPT_RESPONSE_EXCEPTION_HEADER_SECRET"


class SafeGenerationDiagnosticsTests(unittest.TestCase):
    setUp = fixture.DocumentationProposalGeneratorTests.setUp
    tearDown = fixture.DocumentationProposalGeneratorTests.tearDown
    document = fixture.DocumentationProposalGeneratorTests.document
    proposal = fixture.DocumentationProposalGeneratorTests.proposal

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def run_failure(self, stage, state, code, *, transport=None, **kwargs):
        before = self.snapshot()
        with mock.patch.object(G.urllib.request, "urlopen", side_effect=AssertionError("Real HTTP forbidden")), \
             mock.patch.object(G, "apply_changes_atomically") as apply:
            with self.assertRaises(Exception):
                G.generate_and_apply(self.root, self.ticket_file, self.prompt_file, self.report_file,
                                     kwargs.pop("api_key", "fake-key"),
                                     transport=transport or mock.Mock(side_effect=AssertionError("Claude forbidden")),
                                     jira_configuration={}, **kwargs)
        apply.assert_not_called()
        self.assertEqual(before, self.snapshot())
        report = self.read_report(stage, state, code)
        return report

    def read_report(self, stage, state, code):
        raw = self.report_file.read_text(encoding="utf-8")
        self.assertNotIn(PRIVATE, raw)
        report = json.loads(raw)
        self.assertLessEqual(set(report), G.FAILURE_REPORT_FIELDS)
        self.assertEqual("technical_error", report["status"])
        self.assertEqual(stage, report["failure_stage"])
        self.assertEqual(state, report["claude_call_state"])
        self.assertEqual(code, report["error_code"])
        self.assertNotIn("decision", report)
        return report

    def test_stages_before_transport_never_apply_or_publish(self):
        cases = [
            ("configuration", "verify_head", G.ProposalError(PRIVATE, code="base_revision_invalid"), "base_revision_invalid"),
            ("ticket_jira_read", "load_ticket", G.ProposalError(PRIVATE, code="ticket_invalid"), "ticket_invalid"),
            ("documentation_prompt_read", "read_documentation", G.ProposalError(PRIVATE, code="documentation_read_failed"), "documentation_read_failed"),
            ("documentation_prompt_read", "read_prompt", G.ProposalError(PRIVATE, code="prompt_read_failed"), "prompt_read_failed"),
            ("request_construction", "build_request", RuntimeError(PRIVATE), "unclassified_error"),
        ]
        artifacts = self.root.parent / "unpublished-files"
        for stage, function, error, code in cases:
            with self.subTest(stage=stage, function=function), mock.patch.object(G, function, side_effect=error):
                transport = mock.Mock()
                self.run_failure(stage, "not_started", code, transport=transport, image_artifacts=artifacts)
                transport.assert_not_called()
                self.assertFalse(artifacts.exists())
        self.run_failure("configuration", "not_started", "anthropic_key_missing", api_key="")
        # Exercise the real ticket parser, without depending on exception messages.
        self.ticket_file.write_text(PRIVATE, encoding="utf-8")
        self.run_failure("ticket_jira_read", "not_started", "ticket_read_failed")

    def test_image_preparation_boundary(self):
        with mock.patch.object(G.images, "selection", side_effect=G.images.ImageError(PRIVATE, code="image_invalid")):
            self.run_failure("image_preparation", "not_started", "image_invalid")

    def test_jira_http_metadata_from_real_transport(self):
        def jira_transport(*args):
            error = urllib.error.HTTPError("https://" + PRIVATE, 403, PRIVATE, {PRIVATE: PRIVATE}, io.BytesIO(PRIVATE.encode()))
            with mock.patch.object(error, "read", side_effect=AssertionError("Error body forbidden")), \
                 mock.patch.object(G.urllib.request, "urlopen", side_effect=error):
                return G.jira_http_transport(*args)
        self.ticket_file.write_text(json.dumps({"issue_key": "DOC-1", "issue_summary": PRIVATE,
            "issue_description": "DOCUMENTATION_SOURCE_V1\nEPIC_KEY: DOC-2\nTASK_KEYS:\n- DOC-3\n"}), encoding="utf-8")
        # Supply the Jira credentials only to the resolver's configuration reader.
        with mock.patch.object(G, "validate_jira_configuration", return_value=("https://example.invalid", PRIVATE, PRIVATE)):
            report = self.run_failure("ticket_jira_read", "not_started", "jira_http_error", jira_transport=jira_transport)
        self.assertEqual(("jira", 403), (report["service"], report["http_status"]))

    def test_real_claude_transport_states_and_http_metadata(self):
        outcomes = [
            (urllib.error.HTTPError("https://" + PRIVATE, 400, PRIVATE, {PRIVATE: PRIVATE}, io.BytesIO(PRIVATE.encode())),
             "claude_http_transport", "response_received", "claude_http_error"),
            (socket.timeout(PRIVATE), "claude_http_transport", "started_no_response", "claude_timeout"),
            (urllib.error.URLError(PRIVATE), "claude_http_transport", "started_no_response", "claude_connection_failed"),
            (FakeResponse(PRIVATE.encode()), "response_interpretation", "response_received", "claude_envelope_invalid"),
            (FakeResponse(b"[]"), "response_interpretation", "response_received", "claude_envelope_invalid"),
        ]
        for outcome, stage, state, code in outcomes:
            with self.subTest(code=code):
                before = self.snapshot()
                opener = mock.Mock(side_effect=outcome) if isinstance(outcome, Exception) else mock.Mock(return_value=outcome)
                with mock.patch.object(G.urllib.request, "urlopen", opener), \
                     mock.patch.object(G, "RETRY_DELAYS", ()), \
                     mock.patch.object(G, "apply_changes_atomically") as apply:
                    with self.assertRaises(G.ProposalError):
                        # Default transport exercises Request construction, opener, read and decode.
                        G.generate_and_apply(self.root, self.ticket_file, self.prompt_file, self.report_file,
                                             PRIVATE, jira_configuration={})
                apply.assert_not_called()
                self.assertEqual(before, self.snapshot())
                report = self.read_report(stage, state, code)
                if code == "claude_http_error":
                    self.assertEqual(("claude", 400), (report["service"], report["http_status"]))
                else:
                    self.assertNotIn("http_status", report)

    def test_response_received_is_preserved_when_body_read_times_out(self):
        response = FakeResponse(b"")
        response.read = mock.Mock(side_effect=socket.timeout(PRIVATE))
        before = self.snapshot()
        with mock.patch.object(G.urllib.request, "urlopen", return_value=response), \
             mock.patch.object(G, "RETRY_DELAYS", ()), \
             mock.patch.object(G, "apply_changes_atomically") as apply:
            with self.assertRaises(G.ProposalError):
                G.generate_and_apply(self.root, self.ticket_file, self.prompt_file, self.report_file,
                                     PRIVATE, jira_configuration={})
        apply.assert_not_called()
        self.assertEqual(before, self.snapshot())
        self.read_report("claude_http_transport", "response_received", "claude_timeout")

    def test_previous_http_response_is_not_forgotten_after_connection_failure(self):
        progress = {"claude_call_state": "not_started"}
        error = urllib.error.HTTPError("https://" + PRIVATE, 503, PRIVATE, {}, io.BytesIO(PRIVATE.encode()))
        opener = mock.Mock(side_effect=[error, socket.timeout(PRIVATE), socket.timeout(PRIVATE)])
        with mock.patch.object(error, "read", side_effect=AssertionError("Error body forbidden")), \
             self.assertRaises(G.ProposalError):
            G.http_transport("https://example.invalid", PRIVATE, {}, 1,
                             opener=opener, sleeper=lambda _: None, progress=progress)
        self.assertEqual("response_received", progress["claude_call_state"])
        self.assertEqual(3, opener.call_count)

    def test_missing_jira_configuration_is_identified_before_transport(self):
        self.ticket_file.write_text(json.dumps({"issue_key": "DOC-1", "issue_summary": PRIVATE,
            "issue_description": "DOCUMENTATION_SOURCE_V1\nEPIC_KEY: DOC-2\nTASK_KEYS:\n- DOC-3\n"}), encoding="utf-8")
        jira = mock.Mock(side_effect=AssertionError("Jira forbidden"))
        self.run_failure("configuration", "not_started", "jira_configuration_invalid", jira_transport=jira)
        jira.assert_not_called()

    def test_request_construction_inside_transport_does_not_start_call(self):
        with mock.patch.object(G.urllib.request, "Request", side_effect=ValueError(PRIVATE)):
            self.run_failure("claude_http_transport", "not_started", "unclassified_error", transport=G.http_transport)

    def valid_response(self):
        response = json.loads(response_envelope(self.proposal()))
        response["usage"] = {"input_tokens": 100, "output_tokens": 200, PRIVATE: PRIVATE}
        return response

    def test_invalid_response_schema_keeps_usage_without_content(self):
        response = self.valid_response()
        response["content"][0]["text"] = json.dumps({"private": PRIVATE})
        report = self.run_failure("response_interpretation", "response_received", "proposal_schema_invalid",
                                  transport=mock.Mock(return_value=response))
        self.assertEqual("end_turn", report["claude_diagnostics"]["stop_reason"])
        self.assertEqual(100, report["claude_diagnostics"]["input_tokens"])

    def test_failures_after_valid_response_keep_usage_and_do_not_apply(self):
        for function, code in (("prepare_changes", "proposal_preparation_failed"), ("render_agent_report", "report_too_large")):
            with self.subTest(function=function), \
                 mock.patch.object(G, function, side_effect=G.ProposalError(PRIVATE, code=code)):
                report = self.run_failure("change_validation_preparation", "response_received", code,
                                          transport=mock.Mock(return_value=self.valid_response()))
                self.assertEqual(200, report["claude_diagnostics"]["output_tokens"])

    def test_application_failure_rolls_back_and_replaces_content_report(self):
        before = self.snapshot()
        proposal = self.proposal([
            self.document("docs/invitaciones.md", "\n# Invitations\n\n" + PRIVATE + "\n"),
            self.document("docs/archivos-adjuntos.mdx", "\n# Attachments\n\nChanged.\n"),
        ])
        response = json.loads(response_envelope(proposal))
        original_replace = G.os.replace
        calls = 0
        def replace(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError(PRIVATE)
            return original_replace(source, target)
        with mock.patch.object(G.os, "replace", side_effect=replace), \
             mock.patch.object(G.urllib.request, "urlopen", side_effect=AssertionError("Real HTTP forbidden")):
            with self.assertRaises(G.ProposalError):
                G.generate_and_apply(self.root, self.ticket_file, self.prompt_file, self.report_file,
                                     PRIVATE, mock.Mock(return_value=response), jira_configuration={})
        self.assertEqual(2, calls)
        self.assertEqual(before, self.snapshot())
        self.read_report("application", "response_received", "application_failed")

    def test_serializer_rejects_arbitrary_names_fields_types_and_values(self):
        error = G.ProposalError(PRIVATE)
        error.__class__ = type(PRIVATE, (G.ProposalError,), {})
        for value in (PRIVATE, [], {}, True, -1, 2**64):
            error.code = error.service = error.http_status = value
            report = G.technical_failure(error, {"failure_stage": value, "claude_call_state": value, PRIVATE: PRIVATE})
            self.assertEqual({"status": "technical_error", "error_type": "UnclassifiedError",
                              "error_code": "unclassified_error"}, report)
        for value in (True, "403", 99, 600, None):
            report = G.technical_failure(G.ProposalError(PRIVATE, service="jira", http_status=value))
            self.assertNotIn("http_status", report)
        # A message resembling the old HTTP regex cannot set structured metadata.
        report = G.technical_failure(G.images.ImageError("Jira image download returned HTTP 406"))
        self.assertNotIn("http_status", report)
        self.assertEqual("unclassified_error", report["error_code"])


if __name__ == "__main__":
    unittest.main()
