"""UI contract checks. Run: python -B -m unittest discover -s tests."""
import json
from pathlib import Path
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class HelpCenterUITests(unittest.TestCase):
    def test_brand_assets_and_configuration(self):
        config = (ROOT / 'docusaurus.config.js').read_text(encoding='utf-8')
        for name in ('logo', 'claro', 'oscuro', 'icon'):
            asset = ROOT / f'static/img/brand/beesible-{name}.svg'
            self.assertEqual('{http://www.w3.org/2000/svg}svg', ET.parse(asset).getroot().tag)
        self.assertIn("favicon: 'img/brand/beesible-icon.svg'", config)
        self.assertIn("src: 'img/brand/beesible-oscuro.svg'", config)
        self.assertIn("customCss: './src/css/custom.css'", config)
        self.assertNotRegex(config, r'(?i)algolia|apiKey|appId|secret')

    def test_light_mode_is_the_only_available_mode(self):
        config = (ROOT / 'docusaurus.config.js').read_text(encoding='utf-8')
        self.assertIn("defaultMode: 'light'", config)
        self.assertIn('disableSwitch: true', config)
        self.assertIn('respectPrefersColorScheme: false', config)
        self.assertNotIn("style: 'dark'", config)
        self.assertNotIn('srcDark:', config)

    def test_local_search_options(self):
        config = (ROOT / 'docusaurus.config.js').read_text(encoding='utf-8')
        self.assertIn("'@cmfcmf/docusaurus-search-local'", config)
        for option in ('indexDocs: true', 'indexBlog: false', 'indexPages: false',
                       "language: 'es'", 'indexDocSidebarParentCategories: 1',
                       'includeParentCategoriesInPageTitle: true', 'maxSearchResults: 8',
                       "type: 'search'"):
            self.assertIn(option, config)

    def test_styles_import_only_the_selected_local_tokens(self):
        css = (ROOT / 'src/css/custom.css').read_text(encoding='utf-8')
        tokens = (ROOT / 'src/css/bee-tokens.css').read_text(encoding='utf-8')
        self.assertTrue(css.startswith("@import './bee-tokens.css';"))
        for heading in ('Origen: Bee Design System', 'Fecha de exportación: 2026-09-22',
                        'Modo disponible: Light', 'No editar valores sin validación de Diseño'):
            self.assertIn(heading, tokens)
        for category in ('Brand', 'Background, text and border', 'Button', 'Header', 'Sidebar',
                         'Breadcrumb', 'Input and local search', 'Card', 'Alert', 'Footer',
                         'Focus', 'Spacing', 'Typography', 'Radius and shadows used'):
            self.assertIn(f'/* {category} */', tokens)
        self.assertNotRegex(css, r'#[0-9a-fA-F]{3,8}\b')
        self.assertIn(':focus-visible', css)
        self.assertIn('@media', css)
        self.assertNotRegex(css + tokens, r'https?://')
        self.assertNotIn("[data-theme='dark']", css + tokens)
        definitions = set(re.findall(r'(--bee-[\w-]+)\s*:', tokens))
        references = set(re.findall(r'var\((--bee-[\w-]+)', css + tokens))
        self.assertEqual(definitions, references, 'Every selected Bee token must be used')

    def test_complete_design_system_export_is_local_only(self):
        source = 'design-system/local/bee-design-system.json'
        ignored = subprocess.run(
            ['git', 'check-ignore', '-q', source], cwd=ROOT, check=False
        )
        tracked = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', source], cwd=ROOT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        self.assertEqual(0, ignored.returncode)
        self.assertNotEqual(0, tracked.returncode)

    def test_home_and_category_routes(self):
        home = (ROOT / 'docs/index.md').read_text(encoding='utf-8')
        self.assertIn('article_id: ART-HELP-CENTER-001', home)
        self.assertIn('version: 1.1', home)
        self.assertIn('# ¿Cómo podemos ayudarte?', home)
        categories = []
        for path in (ROOT / 'docs/centro-de-ayuda').glob('*/index.md'):
            content = path.read_text(encoding='utf-8')
            position = int(re.search(r'^sidebar_position: (\d+)$', content, re.M)[1])
            categories.append((position, path.relative_to(ROOT / 'docs').as_posix()))
        links = re.findall(r'\[[^]]+\]\(([^)]+)\)', home)
        self.assertEqual([path for _, path in sorted(categories)], links)
        self.assertEqual(8, len(links))
        roots = [p for p in (ROOT / 'docs').rglob('*') if p.suffix in ('.md', '.mdx')
                 and 'production-snapshots' not in p.parts
                 and re.search(r'^slug: /\s*$', p.read_text(encoding='utf-8'), re.M)]
        self.assertEqual([ROOT / 'docs/index.md'], roots)
        self.assertFalse((ROOT / 'src/pages/index.js').exists())

    def test_original_migrated_corpus_is_still_present(self):
        baseline = json.loads(
            (ROOT / 'tests/fixtures/public-docs-sha256.json').read_text(encoding='utf-8')
        )
        self.assertEqual(32, len(baseline))
        for relative in baseline:
            path = ROOT / relative
            self.assertTrue(path.is_file(), f'Original migrated document missing: {relative}')

    def test_no_private_or_brand_pdf_assets(self):
        self.assertFalse(list((ROOT / 'static').rglob('*.pdf')))
        self.assertFalse((ROOT / 'static/project-docs').exists())
        config = (ROOT / 'docusaurus.config.js').read_text(encoding='utf-8')
        self.assertIn("exclude: ['production-snapshots/**']", config)


if __name__ == '__main__':
    unittest.main()
