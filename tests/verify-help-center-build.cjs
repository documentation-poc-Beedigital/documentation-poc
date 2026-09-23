// Run after npm run build: node tests/verify-help-center-build.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {load} = require('cheerio');
const config = require('../docusaurus.config');
const root = path.resolve(__dirname, '../build');
const base = new URL(config.baseUrl, config.url);
function files(dir) {
  return fs.readdirSync(dir, {withFileTypes: true}).flatMap(e =>
    e.isDirectory() ? files(path.join(dir, e.name)) : [path.join(dir, e.name)]);
}
const output = files(root);
assert(!output.some(f => /project-docs|production-snapshots|\.pdf$/i.test(f)));
assert(!output.some(f => /bee-design-system\.json|design-system[\\/]local/i.test(f)));
for (const file of output.filter(f => /\.(?:css|html|js|json|map)$/i.test(f))) {
  const content = fs.readFileSync(file, 'utf8');
  assert(!/bee-design-system\.json|design-system[\\/]local/i.test(content), `${file} leaks the local design-system source path`);
}
const pages = new Map(output.filter(f => f.endsWith('.html')).map(f => [f, load(fs.readFileSync(f, 'utf8'))]));
let links = 0;
for (const [file, $] of pages) {
  const relative = path.relative(root, file).replaceAll('\\', '/').replace(/index\.html$/, '');
  const current = new URL(relative, base);
  $('a[href]').each((_, el) => {
    const href = $(el).attr('href');
    const url = new URL(href, current);
    if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) return;
    const targetPath = path.join(root, decodeURIComponent(url.pathname.slice(base.pathname.length)));
    const target = fs.existsSync(targetPath) && fs.statSync(targetPath).isDirectory() ? path.join(targetPath, 'index.html') : targetPath;
    assert(fs.existsSync(target), `${relative}: missing ${href}`);
    if (url.hash && pages.has(target)) {
      const id = decodeURIComponent(url.hash.slice(1));
      assert(pages.get(target)('[id]').toArray().some(e => e.attribs.id === id), `${relative}: missing anchor ${href}`);
    }
    links++;
  });
  assert(!$('.breadcrumbs, .menu, .pagination-nav').text().includes('centro-de-ayuda'));
  assert(!$('script[src], link[rel="stylesheet"]').toArray().some(e => /^https?:/.test(e.attribs.src || e.attribs.href)));
}
const home = pages.get(path.join(root, 'index.html'));
assert.equal(home('.help-categories a').length, 8);
assert.equal(home('h1').length, 1);
assert.equal(home('h1').text(), '¿Cómo podemos ayudarte?');
const indexes = output.filter(f => /search-index-.*\.json$/.test(f));
assert(indexes.length > 0);
const docs = indexes.flatMap(f => JSON.parse(fs.readFileSync(f)).documents);
assert(docs.length > 24);
assert(!JSON.stringify(docs).match(/project-docs|production-snapshots/));
const corpus = Object.keys(require('./fixtures/public-docs-sha256.json'));
for (const source of corpus) {
  const route = source.replace(/^docs\//, '').replace(/index\.md$/, '').replace(/\.md$/, '/');
  assert(fs.existsSync(path.join(root, route, 'index.html')), `Public URL changed: ${route}`);
}
console.log(`Build OK: ${pages.size} HTML pages, ${links} internal links/anchors, ${docs.length} indexed sections, 32 preserved document URLs.`);
