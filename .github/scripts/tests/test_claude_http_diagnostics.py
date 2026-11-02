from __future__ import annotations

import io
import json
import socket
import traceback
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import test_generate_documentation_proposal as fixture

G = fixture.GENERATOR
PRIVATE = "sk-ant-PRIVATE_SECRET DOC-110 private ticket and editorial text"


def envelope(message, error_type="invalid_request_error", **extra):
    return json.dumps({"type": "error", "error": {"type": error_type, "message": message},
                       **extra}, ensure_ascii=False).encode()


class ClaudeHTTPDiagnosticsTests(unittest.TestCase):
    setUp = fixture.DocumentationProposalGeneratorTests.setUp
    tearDown = fixture.DocumentationProposalGeneratorTests.tearDown

    def reject(self, body, *, status=400, read_error=None):
        stream = io.BytesIO(body)
        error = urllib.error.HTTPError("https://" + PRIVATE, status, PRIVATE,
                                       {"request-id": PRIVATE, "x-api-key": PRIVATE}, stream)
        read = mock.Mock(wraps=error.read) if read_error is None else mock.Mock(side_effect=read_error)
        output = io.StringIO()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with mock.patch.object(error, "read", read), \
             mock.patch.object(G.urllib.request, "urlopen", side_effect=error) as opener, \
             mock.patch.object(G.time, "sleep") as sleep, \
             mock.patch.object(G, "apply_changes_atomically") as apply, \
             redirect_stdout(output), redirect_stderr(output):
            with self.assertRaises(G.ClaudeHTTPError) as caught:
                G.generate_and_apply(self.root, self.ticket_file, self.prompt_file,
                                     self.report_file, PRIVATE, jira_configuration={})
        opener.assert_called_once()
        sleep.assert_not_called()
        apply.assert_not_called()
        read.assert_called_once_with(G.MAX_CLAUDE_ERROR_BYTES + 1)
        self.assertTrue(stream.closed)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        raw = self.report_file.read_text(encoding="utf-8")
        serialized_exception = "".join(traceback.format_exception(caught.exception))
        for text in (raw, output.getvalue(), serialized_exception, repr(vars(caught.exception))):
            for sensitive in (PRIVATE, "sk-ant-", "DOC-110", "private ticket", "editorial text"):
                self.assertNotIn(sensitive, text)
        report = json.loads(raw)
        self.assertEqual("claude_http_transport", report["failure_stage"])
        self.assertEqual("response_received", report["claude_call_state"])
        self.assertEqual("claude", report["service"])
        self.assertEqual(status, report["http_status"])
        self.assertEqual("claude_http_error", report["error_code"])
        self.assertLessEqual(set(report), G.FAILURE_REPORT_FIELDS)
        return report["claude_http_diagnostics"]

    def test_known_schema_rejection_with_untrusted_extra_fields(self):
        for message in ("Schema is too complex for compilation", "Schema is too complex for compilation."):
            with self.subTest(message=message):
                self.assertEqual({"body_state": "parsed", "error_type": "invalid_request_error",
                                  "rejection_code": "schema_too_complex",
                                  "parameter": "output_config.format.schema"},
                                 self.reject(envelope(message, request_id=PRIVATE, body=PRIVATE)))

    def test_known_parameter_rejections_use_only_local_names(self):
        for parameter in sorted(G.CLAUDE_HTTP_PARAMETERS):
            with self.subTest(parameter=parameter):
                diagnostics = self.reject(envelope(parameter + ": Extra inputs are not permitted"))
                self.assertEqual("unexpected_parameter", diagnostics["rejection_code"])
                self.assertEqual(parameter, diagnostics["parameter"])

    def test_unknown_and_sensitive_messages_do_not_match_substrings(self):
        messages = [PRIVATE, "unrecognized rejection", "", "x" * 2049,
                    "Schema is too complex for compilation. " + PRIVATE,
                    PRIVATE + " Schema is too complex for compilation.",
                    "output_config: Extra inputs are not permitted\n" + PRIVATE,
                    PRIVATE + ": Extra inputs are not permitted",
                    "messages.0.content: Extra inputs are not permitted",
                    "schema is too complex for compilation."]
        for message in messages:
            with self.subTest(length=len(message)):
                self.assertEqual({"body_state": "parsed", "error_type": "invalid_request_error",
                                  "rejection_code": "unknown_http_error"}, self.reject(envelope(message)))

    def test_known_message_requires_matching_http_status_and_error_type(self):
        for status, kind in ((403, "invalid_request_error"), (400, "authentication_error"),
                             (400, PRIVATE), (400, "new_future_error")):
            with self.subTest(status=status, kind=kind):
                diagnostics = self.reject(envelope("Schema is too complex for compilation.", kind), status=status)
                self.assertEqual("unknown_http_error", diagnostics["rejection_code"])
                self.assertNotIn("parameter", diagnostics)
                self.assertEqual(kind in G.CLAUDE_HTTP_ERROR_TYPES, "error_type" in diagnostics)

    def test_error_types_are_a_closed_catalogue(self):
        for kind in G.CLAUDE_HTTP_ERROR_TYPES:
            with self.subTest(kind=kind):
                diagnostics = self.reject(envelope(PRIVATE, kind))
                self.assertEqual(kind, diagnostics["error_type"])
                self.assertEqual("unknown_http_error", diagnostics["rejection_code"])

    def test_malformed_bodies_preserve_http_failure(self):
        bodies = [b"", PRIVATE.encode(), b"\xff", b"null", b"[]", b"{}",
                  b'{"type":"error","error":[]}', envelope(None), envelope([]),
                  envelope("message", {}), envelope("message", True),
                  b'{"type":"error","error":{"type":"invalid_request_error","message":"x","message":"Schema is too complex for compilation."}}',
                  b"[" * 2000 + b"]" * 2000]
        for body in bodies:
            with self.subTest(length=len(body)):
                self.assertEqual({"body_state": "malformed", "rejection_code": "unknown_http_error"},
                                 self.reject(body))

    def test_body_limit_is_bytes_and_oversized_prefix_is_never_classified(self):
        prefix = envelope("Schema is too complex for compilation.")
        exact = prefix + b" " * (G.MAX_CLAUDE_ERROR_BYTES - len(prefix))
        self.assertEqual("schema_too_complex", self.reject(exact)["rejection_code"])
        for oversized in (exact + b" ", exact + PRIVATE.encode() * 10000,
                          envelope("\u00e9" * G.MAX_CLAUDE_ERROR_BYTES)):
            self.assertEqual({"body_state": "too_large", "rejection_code": "unknown_http_error"},
                             self.reject(oversized))

    def test_read_failure_does_not_replace_original_http_status_or_retry(self):
        for error in (socket.timeout(PRIVATE), OSError(PRIVATE), G.http.client.IncompleteRead(b"secret")):
            with self.subTest(error_type=type(error).__name__):
                self.assertEqual({"body_state": "unreadable", "rejection_code": "unknown_http_error"},
                                 self.reject(b"", read_error=error))

    def test_report_serializer_revalidates_http_metadata(self):
        error = G.ClaudeHTTPError(400, {})
        for value in (PRIVATE, [], {}, True, 1, None, "x" * 10000):
            error.diagnostics = {field: value for field in
                                 ("body_state", "error_type", "rejection_code", "parameter", PRIVATE)}
            self.assertEqual({}, G.technical_failure(error)["claude_http_diagnostics"])
        error.diagnostics = {"rejection_code": "unknown_http_error", "parameter": "messages"}
        self.assertEqual({"rejection_code": "unknown_http_error"},
                         G.technical_failure(error)["claude_http_diagnostics"])

    def test_cli_keeps_safe_http_metadata_when_rewriting_report(self):
        error = urllib.error.HTTPError("https://" + PRIVATE, 400, PRIVATE, {},
                                       io.BytesIO(envelope(PRIVATE, request_id=PRIVATE)))
        output = io.StringIO()
        with mock.patch.dict(G.os.environ, {"ANTHROPIC_API_KEY": PRIVATE}), \
             mock.patch.object(G, "jira_configuration_from_environment", return_value={}), \
             mock.patch.object(G.urllib.request, "urlopen", side_effect=error) as opener, \
             redirect_stdout(output), redirect_stderr(output):
            result = G.main(["--repo-root", str(self.root), "--ticket-file", str(self.ticket_file),
                             "--prompt-file", str(self.prompt_file), "--agent-report", str(self.report_file)])
        self.assertEqual(1, result)
        opener.assert_called_once()
        raw = self.report_file.read_text(encoding="utf-8")
        self.assertNotIn(PRIVATE, raw + output.getvalue())
        report = json.loads(raw)
        self.assertEqual("unknown_http_error", report["claude_http_diagnostics"]["rejection_code"])
        self.assertEqual("response_received", report["claude_call_state"])
        self.assertEqual("claude_http_transport", report["failure_stage"])
        self.assertEqual(("claude", 400), (report["service"], report["http_status"]))

    def test_actual_http_request_keeps_contract_and_internal_schema(self):
        payload = G.build_request("trusted instructions", {"issue_key": "DOC-1"}, [])
        response = fixture.FakeResponse(b'{"content":[]}')
        with mock.patch.object(G.urllib.request, "urlopen", return_value=response) as opener:
            G.http_transport(G.API_URL, "fake-key", payload, 120)
        request = opener.call_args.args[0]
        self.assertEqual("https://api.anthropic.com/v1/messages", request.full_url)
        self.assertEqual("POST", request.method)
        self.assertEqual({"content-type": "application/json", "x-api-key": "fake-key",
                          "anthropic-version": "2023-06-01"},
                         {key.lower(): value for key, value in request.header_items()})
        sent = json.loads(request.data)
        self.assertEqual({"model", "max_tokens", "system", "messages", "output_config"}, set(sent))
        self.assertEqual("claude-sonnet-5-5", sent["model"])
        self.assertEqual(16384, sent["max_tokens"])
        self.assertEqual({"format": {"type": "json_schema", "schema": G.PROPOSAL_SCHEMA}}, sent["output_config"])
        self.assertEqual(["user"], [message["role"] for message in sent["messages"]])
        self.assertFalse(G.PROPOSAL_SCHEMA["additionalProperties"])
        self.assertFalse(G.DOCUMENT_SCHEMA["additionalProperties"])
        self.assertEqual(G.ROOT_FIELDS, set(G.PROPOSAL_SCHEMA["required"]))
        self.assertEqual(G.DOCUMENT_FIELDS, set(G.DOCUMENT_SCHEMA["required"]))
        self.assertNotIn("sidebar_position", G.DOCUMENT_SCHEMA["required"])


if __name__ == "__main__":
    unittest.main()
