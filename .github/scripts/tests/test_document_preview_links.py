import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main()
