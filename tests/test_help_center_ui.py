"""UI contract checks. Run: python -B -m unittest discover -s tests."""
import hashlib
import json
from pathlib import Path
import re
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
        self.assertIn("srcDark: 'img/brand/beesible-claro.svg'", config)
        self.assertIn("customCss: './src/css/custom.css'", config)
        self.assertNotRegex(config, r'(?i)algolia|apiKey|appId|secret')

    def test_local_search_options(self):
        config = (ROOT / 'docusaurus.config.js').read_text(encoding='utf-8')
        self.assertIn("'@cmfcmf/docusaurus-search-local'", config)
        for option in ('indexDocs: true', 'indexBlog: false', 'indexPages: false',
                       "language: 'es'", 'indexDocSidebarParentCategories: 1',
                       'includeParentCategoriesInPageTitle: true', 'maxSearchResults: 8',
                       "type: 'search'"):
            self.assertIn(option, config)

    def test_styles_are_local_and_use_brand_palette(self):
        css = (ROOT / 'src/css/custom.css').read_text(encoding='utf-8')
        for color in ('#18d3d6', '#6818aa', '#373737', '#ebd4fa', '#d2f8f9'):
            self.assertIn(color, css.lower())
        self.assertIn(':focus-visible', css)
        self.assertIn("[data-theme='dark']", css)
        self.assertIn('@media', css)
        self.assertNotRegex(css, r'https?://|@import')

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

    def test_migrated_corpus_matches_baseline(self):
        baseline = json.loads((ROOT / 'tests/fixtures/public-docs-sha256.json').read_text())
        actual = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                  for p in (ROOT / 'docs/centro-de-ayuda').rglob('*.md')}
        self.assertEqual(32, len(actual))
        self.assertEqual(baseline, actual)

    def test_no_private_or_brand_pdf_assets(self):
        self.assertFalse(list((ROOT / 'static').rglob('*.pdf')))
        self.assertFalse((ROOT / 'static/project-docs').exists())
        config = (ROOT / 'docusaurus.config.js').read_text(encoding='utf-8')
        self.assertIn("exclude: ['production-snapshots/**']", config)


if __name__ == '__main__':
    unittest.main()
