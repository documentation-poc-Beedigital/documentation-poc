import importlib.util
import io
import os
import subprocess
import unittest
from contextlib import redirect_stdout
from email.message import Message
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

SCRIPT = Path(__file__).resolve().parents[1] / 'diagnose-preview-manifest.py'
SPEC = importlib.util.spec_from_file_location('diagnose_preview_manifest', SCRIPT)
DIAG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAG)


def headers():
    result = Message()
    for name, value in {'Content-Type': 'text/html', 'Server': 'cloudflare',
                        'cf-ray': 'sample-MAD', 'cf-mitigated': 'challenge',
                        'Set-Cookie': 'PRIVATE_COOKIE', 'Location': 'https://private.invalid/SECRET',
                        'Authorization': 'PRIVATE_TOKEN'}.items():
        result[name] = value
    return result


class DiagnosticTests(unittest.TestCase):
    def test_python_same_opener_does_not_read_body_or_send_headers(self):
        response = Mock(status=200, headers=headers())
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = response
        with patch.object(DIAG, 'build_opener', return_value=opener) as build:
            result = DIAG.python_probe()
        self.assertIsInstance(build.call_args.args[0], DIAG.UPDATER.NoRedirect)
        opener.open.assert_called_once_with(DIAG.URL, timeout=20)
        response.read.assert_not_called()
        self.assertEqual(result['status'], 200)
        self.assertEqual(set(result['headers']), set(DIAG.HEADERS))
        self.assertNotIn('PRIVATE', str(result))

    def test_python_http_error_does_not_read_error_body(self):
        body = Mock()
        opener = Mock()
        opener.open.side_effect = HTTPError(DIAG.URL, 403, 'SECRET', headers(), body)
        with patch.object(DIAG, 'build_opener', return_value=opener):
            result = DIAG.python_probe()
        self.assertEqual(result['status'], 403)
        self.assertEqual(result['headers']['cf-mitigated'], 'challenge')
        body.read.assert_not_called()
        body.close.assert_called_once()
        self.assertNotIn('SECRET', str(result))

    def test_python_redirect_retains_allowed_headers_without_following(self):
        opener = Mock()
        response = Mock()

        def build(handler):
            def open_url(*args, **kwargs):
                handler.redirect_request(None, response, 302, 'SECRET', headers(), 'https://private.invalid')
            opener.open.side_effect = open_url
            return opener

        with patch.object(DIAG, 'build_opener', side_effect=build):
            result = DIAG.python_probe()
        self.assertEqual(result['status'], 302)
        self.assertEqual(result['result'], 'redirect_rejected')
        opener.open.assert_called_once()
        response.close.assert_called_once()
        self.assertNotIn('private.invalid', str(result))

    def test_python_connection_and_timeout(self):
        for error, expected in ((URLError('SECRET'), 'connection_error'), (TimeoutError('SECRET'), 'timeout')):
            opener = Mock()
            opener.open.side_effect = error
            with patch.object(DIAG, 'build_opener', return_value=opener):
                result = DIAG.python_probe()
            self.assertEqual(result['result'], expected)
            self.assertIsNone(result['status'])

    def test_curl_flags_header_filter_and_environment(self):
        raw = (b'HTTP/1.1 200 Connection established\r\nServer: proxy\r\n\r\n'
               b'HTTP/2 403\r\ncontent-type: text/html\r\nserver: cloudflare\r\n'
               b'cf-ray: example-MAD\r\ncf-mitigated: challenge\r\n'
               b'Set-Cookie: PRIVATE_COOKIE\r\nLocation: PRIVATE_LOCATION\r\n\r\n'
               b'\n__HTTP_STATUS__:403\n')
        with patch.dict(os.environ, {'GH_TOKEN': 'PRIVATE', 'GITHUB_TOKEN': 'PRIVATE'}), \
                patch.object(DIAG.subprocess, 'run', return_value=Mock(returncode=0, stdout=raw)) as run:
            result = DIAG.curl_probe()
        self.assertEqual(result['status'], 403)
        self.assertEqual(result['headers']['Server'], 'cloudflare')
        self.assertNotIn('PRIVATE', str(result))
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ['curl', '-q'])
        self.assertNotIn('--location', command)
        self.assertNotIn('-L', command)
        self.assertNotIn('--head', command)
        self.assertEqual(command[command.index('--max-redirs') + 1], '0')
        self.assertEqual(command[command.index('--output') + 1], os.devnull)
        self.assertIn('--no-netrc', command)
        self.assertEqual(command[-1], DIAG.URL)
        self.assertNotIn('GH_TOKEN', run.call_args.kwargs['env'])
        self.assertNotIn('GITHUB_TOKEN', run.call_args.kwargs['env'])
        self.assertEqual(run.call_args.kwargs['stderr'], subprocess.DEVNULL)

    def test_curl_redirect_and_timeout(self):
        process = Mock(returncode=0, stdout=b'HTTP/2 302\r\nLocation: SECRET\r\n\r\n\n__HTTP_STATUS__:302\n')
        with patch.object(DIAG.subprocess, 'run', return_value=process):
            result = DIAG.curl_probe()
        self.assertEqual(result['result'], 'redirect_rejected')
        self.assertNotIn('SECRET', str(result))
        with patch.object(DIAG.subprocess, 'run', return_value=Mock(returncode=28)):
            self.assertEqual(DIAG.curl_probe()['result'], 'timeout')
        with patch.object(DIAG.subprocess, 'run', side_effect=subprocess.TimeoutExpired('SECRET', 25)):
            self.assertEqual(DIAG.curl_probe()['result'], 'timeout')

    def test_comparison_outputs_only_allowed_headers(self):
        result = {'status': 403, 'headers': DIAG.allowed_headers(headers()), 'result': 'http_error'}
        output = io.StringIO()
        with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''}), redirect_stdout(output):
            DIAG.compare(result, result)
        text = output.getvalue()
        for name in DIAG.HEADERS:
            self.assertIn(name, text)
        for private in ('PRIVATE', 'Set-Cookie', 'Location', 'Authorization', 'SECRET'):
            self.assertNotIn(private, text)
        self.assertIn('403', text)
        self.assertIn('no valida el SHA', text)

    def test_verify_pr_is_read_only_and_checks_latest_head(self):
        api = Mock()
        sha = 'c76c8420bcd7ec27ec03cfa7e5c538efb8dd2c2b'
        api.request.return_value = {'head': {'sha': sha}}
        for deployment, expected in ((DIAG.DEPLOYMENT, True), ('https://another.example', False), (None, False)):
            with patch.object(DIAG.UPDATER, 'cloudflare_preview', return_value=('pendiente', deployment)) as select, \
                    patch.object(DIAG, 'emit'):
                self.assertEqual(DIAG.verify_pr(api), expected)
            select.assert_called_with(api.comments.return_value, sha)
        self.assertTrue(all(call.args == ('/pulls/121',) for call in api.request.call_args_list))
        api.comments.assert_called_with(121)

    def test_workflow_is_manual_and_token_is_only_in_github_step(self):
        workflow = SCRIPT.parents[1] / 'workflows/diagnose-preview-manifest.yml'
        text = workflow.read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch:', text)
        self.assertNotIn(': write', text)
        self.assertNotIn('secrets.', text)
        probe = text.split('- name: Compare Python and curl')[1]
        self.assertNotIn('GH_TOKEN', probe)
        self.assertNotIn('github.token', probe)
        self.assertIn('persist-credentials: false', text)


if __name__ == '__main__':
    unittest.main()
