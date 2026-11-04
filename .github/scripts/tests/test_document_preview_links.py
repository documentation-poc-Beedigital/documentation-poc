import importlib.util
import io
import json
import os
import socket
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

SCRIPT = Path(__file__).resolve().parents[1] / 'update-document-preview-links.py'
SPEC = importlib.util.spec_from_file_location('preview_links', SCRIPT)
PREVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREVIEW)
SHA = '965e07bac3fdf8cc08d3f6953023a74d900c41b8'
URL = 'https://591b11de.documentation-poc.pages.dev'


def comment(sha=SHA[:7], status='✅ Deploy successful!', url=URL):
    # Format observed in the actual Cloudflare comment on PR #121.
    return {'id': 1, 'updated_at': '2026-11-03',
            'user': {'id': PREVIEW.BOT_ID}, 'performed_via_github_app': {'id': PREVIEW.APP_ID},
            'body': f'''<table><tr><td><strong>Latest commit:</strong> </td><td>
<code>{sha}</code>
</td></tr>
<tr><td><strong>Status:</strong></td><td>&nbsp;{status}</td></tr>
<tr><td><strong>Preview URL:</strong></td><td>
<a href='{url}'>{url}</a>
</td></tr>
<tr><td><strong>Branch Preview URL:</strong></td><td>
<a href='https://branch.project.pages.dev'>branch alias</a></td></tr></table>'''}


def manifest():
    return {'schema': 1, 'commit': SHA, 'baseUrl': '/custom/', 'routes': {
        'docs/new.md': '/custom/slug-especial/',
        'docs/updated.mdx': '/custom/updated/',
        'docs/category/index.md': '/custom/category/',
    }}


BODY = '''Texto humano antes.
## Documentos creados
### Nuevo

- Ruta: `docs/new.md`
- Versión: `nuevo` → `1.0`
- Motivo: Motivo original.
- Evidencia: Evidencia original.

## Documentos actualizados
### Actualizado

- Ruta: `docs/updated.mdx`
- Versión: `1.0` → `1.1`
- Motivo: Otro motivo.
- Evidencia: Otra evidencia.

Comentario humano entre documentos.

### Índice

- Ruta: `docs/category/index.md`
- Versión: `1.0` → `1.1`
- Motivo: Navegación.
- Evidencia: Ticket.

## Imágenes
Texto humano después.
'''


class PreviewTests(unittest.TestCase):
    def test_real_comment_immutable_url(self):
        self.assertEqual(PREVIEW.cloudflare_preview([comment()], SHA), ('disponible', URL))

    def test_pending_failure_previous_commit_and_untrusted(self):
        for item, state in [(comment(status='Building...'), 'pendiente'),
                            (comment(status='❌ Deploy failed!'), 'fallido'),
                            (comment(sha='abcdef1'), 'otro commit'),
                            (comment(url='https://branch.project.pages.dev'), 'no reconocida')]:
            with self.subTest(state=state):
                result, url = PREVIEW.cloudflare_preview([item], SHA)
                self.assertIn(state, result)
                self.assertIsNone(url)
        spoof = comment()
        spoof['user']['id'] = 42
        self.assertIsNone(PREVIEW.cloudflare_preview([spoof], SHA)[1])
        newer = comment(status='Building...')
        newer['id'] = 2
        self.assertIsNone(PREVIEW.cloudflare_preview([comment(), newer], SHA)[1])

    def test_new_updated_index_human_text_and_idempotence(self):
        updated = PREVIEW.reconcile(BODY, SHA, 'disponible', URL, manifest())
        for route in manifest()['routes'].values():
            self.assertIn(f'[Ver en preview](<{URL}{route}>)', updated)
        self.assertIn(f'[Ver preview general](<{URL}/custom/>)', updated)
        self.assertEqual(updated.count('[Ver en preview]'), 3)
        self.assertEqual(PREVIEW.reconcile(updated, SHA, 'disponible', URL, manifest()), updated)
        import re
        stripped = re.sub(r'\n*<!-- document-preview:.*?:start -->.*?<!-- document-preview:.*?:end -->\n*',
                          '\n', updated, flags=re.S)
        self.assertEqual(stripped.split(), BODY.split())
        edited = updated.replace('Texto humano después.', 'Edición humana nueva.')
        repeated = PREVIEW.reconcile(edited, SHA, 'disponible', URL, manifest())
        self.assertIn('Edición humana nueva.', repeated)

    def test_new_commit_invalidates_old_links(self):
        previous = PREVIEW.reconcile(BODY, SHA, 'disponible', URL, manifest())
        for state in ('pendiente', 'fallido'):
            updated = PREVIEW.reconcile(previous, 'a' * 40, state)
            self.assertNotIn(URL, updated)
            self.assertEqual(updated.count('Ver en preview:'), 3)
            self.assertIn('Texto humano después.', updated)

    def test_manifest_must_match_full_sha(self):
        data = manifest()
        data['commit'] = 'a' * 40
        with self.assertRaises(ValueError):
            PREVIEW.reconcile(BODY, SHA, 'disponible', URL, data)

    def test_missing_route_is_explicit(self):
        data = manifest()
        del data['routes']['docs/new.md']
        updated = PREVIEW.reconcile(BODY, SHA, 'disponible', URL, data)
        self.assertIn('ruta no publicada', updated)
        self.assertEqual(updated.count('[Ver en preview]'), 2)

    @patch.dict(os.environ, {'GITHUB_REPOSITORY': 'example/repo'})
    def test_update_simulated_api_and_concurrent_edits(self):
        from unittest.mock import Mock
        pr = {'state': 'open', 'head': {'sha': SHA, 'repo': {'full_name': 'example/repo'},
              'ref': 'automation/documentation-doc-1'}, 'user': {'login': 'github-actions[bot]'}, 'body': BODY}
        for concurrent in (False, True):
            api = Mock()
            current = dict(pr, body=BODY + 'Human edit') if concurrent else pr
            api.request.side_effect = [pr, current, {}]
            api.comments.return_value = [comment()]
            with patch.object(PREVIEW, 'fetch_manifest', return_value=manifest()):
                PREVIEW.update(api, 1)
            self.assertEqual(api.request.call_count, 2 if concurrent else 3)

    @patch.dict(os.environ, {'GITHUB_REPOSITORY': 'example/repo'})
    def test_old_manifest_or_unavailable_never_publishes_old_preview(self):
        from unittest.mock import Mock
        body = PREVIEW.reconcile(BODY, SHA, 'disponible', URL, manifest())
        pr = {'state': 'open', 'head': {'sha': 'a' * 40, 'repo': {'full_name': 'example/repo'},
              'ref': 'automation/documentation-doc-1'}, 'user': {'login': 'github-actions[bot]'}, 'body': body}
        for failure in (False, True):
            api = Mock()
            api.request.side_effect = [pr, pr, {}]
            api.comments.return_value = [comment(sha='aaaaaaa')]
            with patch.object(PREVIEW, 'fetch_manifest', side_effect=OSError() if failure else None,
                              return_value=manifest()):
                PREVIEW.update(api, 1)
            self.assertNotIn(URL, api.request.call_args.args[1]['body'])

    def test_http_and_transport_diagnostics_do_not_expose_payloads(self):
        sensitive = 'PRIVATE_RESPONSE_COOKIE_TOKEN'
        cases = [
            (HTTPError(URL, 403, sensitive, {'Set-Cookie': sensitive}, io.BytesIO(sensitive.encode())),
             'http_error: HTTP 403'),
            (HTTPError(URL, 404, sensitive, {}, None), 'http_error: HTTP 404'),
            (HTTPError(URL, 500, sensitive, {}, None), 'http_error: HTTP 500'),
            (HTTPError(URL, 302, sensitive, {'Location': sensitive}, None),
             'redirect_rejected: redirección rechazada (HTTP 302)'),
            (TimeoutError(sensitive), 'timeout: tiempo de espera agotado'),
            (URLError(socket.timeout(sensitive)), 'timeout: tiempo de espera agotado'),
            (URLError(sensitive), 'connection_error: error de conexión'),
            (ConnectionError(sensitive), 'connection_error: error de conexión'),
            (json.JSONDecodeError(sensitive, sensitive, 0), 'invalid_json: JSON inválido'),
            (UnicodeDecodeError('utf8', b'\xff', 0, 1, sensitive), 'invalid_json: JSON inválido'),
            (RuntimeError(sensitive), 'unexpected_error: error no clasificado'),
        ]
        for error, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(PREVIEW.safe_diagnostic(error), expected)
                self.assertNotIn(sensitive, PREVIEW.safe_diagnostic(error))

    def test_redirect_handler_rejects_before_following_location(self):
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code), self.assertRaises(PREVIEW.PreviewError) as raised:
                PREVIEW.NoRedirect().redirect_request(None, None, code, 'PRIVATE',
                                                     {'Set-Cookie': 'PRIVATE'}, 'https://private.invalid/token')
            self.assertEqual(raised.exception.code, 'redirect_rejected')
            self.assertNotIn('PRIVATE', str(raised.exception))
            self.assertNotIn('private.invalid', str(raised.exception))

    def test_fetch_rejects_invalid_json_without_sending_github_token(self):
        for raw in (b'PRIVATE_BODY_NOT_JSON', b'\xff'):
            response = Mock()
            response.geturl.return_value = URL + '/' + PREVIEW.MANIFEST
            response.read.return_value = raw
            opener = Mock()
            opener.open.return_value.__enter__ = Mock(return_value=response)
            opener.open.return_value.__exit__ = Mock(return_value=False)
            with patch.dict(os.environ, {'GH_TOKEN': 'PRIVATE_GITHUB_TOKEN'}), \
                    patch.object(PREVIEW, 'build_opener', return_value=opener) as build:
                with self.assertRaises((json.JSONDecodeError, UnicodeDecodeError)) as raised:
                    PREVIEW.fetch_manifest(URL)
                self.assertEqual(PREVIEW.safe_diagnostic(raised.exception), 'invalid_json: JSON inválido')
            self.assertIs(build.call_args.args[0], PREVIEW.NoRedirect)
            # Plain URL and timeout only: no Request carrying Authorization,
            # Cookie, GitHub headers or environment token is passed to Pages.
            opener.open.assert_called_once_with(URL + '/' + PREVIEW.MANIFEST, timeout=20)
            response.read.assert_called_once_with(2_000_001)

    def test_incompatible_manifests_and_sha_have_separate_codes(self):
        for data in (None, [], {'schema': 2}, dict(manifest(), schema=True),
                     dict(manifest(), routes=[]), dict(manifest(), baseUrl='bad'),
                     dict(manifest(), routes={'docs/new.md': '//private.invalid'})):
            with self.subTest(data=data), self.assertRaises(PREVIEW.PreviewError) as raised:
                PREVIEW.validated_routes(data, SHA)
            self.assertEqual(raised.exception.code, 'incompatible_manifest')
        with self.assertRaises(PREVIEW.PreviewError) as raised:
            PREVIEW.validated_routes(dict(manifest(), commit='a' * 40), SHA)
        self.assertEqual(raised.exception.code, 'sha_mismatch')

    @patch.dict(os.environ, {'GITHUB_REPOSITORY': 'example/repo'})
    def test_summary_reports_verified_pending_failed_and_unverifiable(self):
        secret = 'PRIVATE_RESPONSE_COOKIE_TOKEN'
        pr = {'state': 'open', 'head': {'sha': SHA, 'repo': {'full_name': 'example/repo'},
              'ref': 'automation/documentation-doc-1'}, 'user': {'login': 'github-actions[bot]'}, 'body': BODY}
        cases = [
            (comment(), manifest(), None, 'updated', 'manifiesto verificado'),
            (comment(status='Building...'), None, None, 'pending', 'preview sin verificar'),
            (comment(sha='abcdef1'), None, None, 'pending', 'otro commit'),
            (comment(status='❌ Deploy failed!'), None, None, 'unverified', 'fallido'),
            (comment(), None, HTTPError(URL, 403, secret, {'Set-Cookie': secret}, None),
             'unverified', 'HTTP 403'),
            (comment(), None, HTTPError(URL, 302, secret, {'Location': secret}, None),
             'unverified', 'redirect_rejected'),
            (comment(), None, URLError(secret), 'unverified', 'connection_error'),
            (comment(), None, TimeoutError(secret), 'unverified', 'timeout'),
            (comment(), None, json.JSONDecodeError(secret, secret, 0), 'unverified', 'invalid_json'),
            (comment(), [], None, 'unverified', 'incompatible_manifest'),
            (comment(), dict(manifest(), commit='a' * 40), None, 'unverified', 'sha_mismatch'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            for item, data, error, status, detail in cases:
                with self.subTest(status=status, detail=detail):
                    summary, output = Path(temp) / 'summary.md', Path(temp) / 'output.txt'
                    summary.write_text('', encoding='utf-8')
                    output.write_text('', encoding='utf-8')
                    api = Mock()
                    api.request.side_effect = [pr, pr, {}]
                    api.comments.return_value = [item]
                    logs = io.StringIO()
                    with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(summary), 'GITHUB_OUTPUT': str(output)}), \
                            patch.object(PREVIEW, 'fetch_manifest', return_value=data, side_effect=error) as fetch, \
                            redirect_stdout(logs):
                        PREVIEW.update(api, 1)
                    text = summary.read_text(encoding='utf-8')
                    self.assertIn(detail, text)
                    self.assertIn('El verde del job', text)
                    self.assertIn(f'preview_status={status}\n', output.read_text(encoding='utf-8'))
                    self.assertNotIn(secret, text + logs.getvalue())
                    new_body = api.request.call_args.args[1]['body']
                    if status != 'updated':
                        self.assertNotIn(URL, new_body)
                        self.assertIn('::warning', logs.getvalue())
                    if status == 'pending' or 'fallido' in detail:
                        fetch.assert_not_called()

    @patch.dict(os.environ, {'GITHUB_REPOSITORY': 'example/repo'})
    def test_summary_distinguishes_unchanged_missing_routes_and_concurrent_edit(self):
        body = PREVIEW.reconcile(BODY, SHA, 'disponible', URL, manifest())
        pr = {'state': 'open', 'head': {'sha': SHA, 'repo': {'full_name': 'example/repo'},
              'ref': 'automation/documentation-doc-1'}, 'user': {'login': 'github-actions[bot]'}, 'body': body}
        for concurrent, missing, expected in ((False, False, 'unchanged'),
                                               (True, False, 'skipped'),
                                               (False, True, 'unverified')):
            api = Mock()
            current = dict(pr, body=body + 'Human edit') if concurrent else pr
            api.request.side_effect = [pr, current, {}]
            api.comments.return_value = [comment()]
            data = manifest()
            if missing:
                del data['routes']['docs/new.md']
            with patch.object(PREVIEW, 'fetch_manifest', return_value=data), \
                    patch.object(PREVIEW, 'report') as report:
                PREVIEW.update(api, 1)
            self.assertEqual(report.call_args.args[0], expected)
            self.assertEqual(api.request.call_count, 3 if missing else 2)


if __name__ == '__main__':
    unittest.main()
