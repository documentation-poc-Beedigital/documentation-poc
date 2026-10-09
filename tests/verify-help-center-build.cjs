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
const retiredSource = 'docs/centro-de-ayuda/visibilidad/como-crear-tu-pagina-web.md';
const retiredRoute = 'centro-de-ayuda/visibilidad/como-crear-tu-pagina-web/';
const retiredPath = path.join(root, retiredRoute, 'index.html');
const recoveredSource = 'docs/centro-de-ayuda/visibilidad/tu-pagina-web-creada-automaticamente-por-beesible.md';
function headingText($, element) {
  return $(element).clone().find('a.hash-link').remove().end().text().replace(/\s+/g, ' ').trim();
}
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
  const ids = $('[id]').toArray().map(element => element.attribs.id);
  assert.equal(new Set(ids).size, ids.length, `${relative}: duplicate ids`);
}
const home = pages.get(path.join(root, 'index.html'));
assert.equal(home('.theme-doc-sidebar-menu > li').length, 8);
assert.equal(home('.theme-doc-sidebar-menu a[href="/documentation-poc/"]').length, 0);
assert.equal(home('.help-categories').length, 0);
assert.equal(home('.pagination-nav a').length, 0);
assert.equal(home('.help-search').length, 1);
assert.equal(home('h1').length, 1);
assert.equal(home('h1').text(), '¿Cómo podemos ayudarte?');
const duplicatedSubtitle = pages.get(path.join(root, 'centro-de-ayuda/perfil-de-empresa-en-google/index.html'));
const movedAnchorId = 'conexión-perfil-de-empresa-en-google';
assert.equal(duplicatedSubtitle('h1').length, 1);
assert.equal(duplicatedSubtitle('h2').filter((_, element) => headingText(duplicatedSubtitle, element) === 'Conexión Perfil de Empresa en Google').length, 0);
assert.equal(duplicatedSubtitle('h1').attr('id'), movedAnchorId);
assert.equal(duplicatedSubtitle('h1 > a.hash-link').attr('href'), `#${movedAnchorId}`);
assert.match(duplicatedSubtitle('h1 > a.hash-link').attr('aria-label'), /Conexión Perfil de Empresa en Google/);
assert.deepEqual(
  duplicatedSubtitle('.theme-doc-markdown > p > a').toArray().map(element => duplicatedSubtitle(element).text().trim()),
  ['Cómo conectar tu Perfil de Google', 'Crear un Perfil de Empresa en Google'],
);
const visibility = pages.get(path.join(root, 'centro-de-ayuda/visibilidad/index.html'));
assert.deepEqual(visibility('h2').toArray().map(element => headingText(visibility, element)), ['Google', 'Página Web']);
assert.deepEqual(visibility('h2 > a.hash-link').toArray().map(element => visibility(element).attr('href')), ['#--google', '#-página-web']);
assert.deepEqual(
  visibility('.theme-doc-markdown > p > a').toArray().map(element => ({
    text: visibility(element).text().trim(),
    href: visibility(element).attr('href'),
  })),
  [
    {text: 'Añadir o actualizar información en tu Perfil de Google', href: '/documentation-poc/centro-de-ayuda/visibilidad/anadir-o-actualizar-informacion-en-tu-perfil-de-google/'},
    {text: 'Expansión de tu negocio en otras plataformas', href: '/documentation-poc/centro-de-ayuda/visibilidad/expansion-de-tu-negocio-en-otras-plataformas/'},
    {text: 'Tu página web creada automáticamente por Beelma', href: '/documentation-poc/centro-de-ayuda/visibilidad/tu-pagina-web-creada-automaticamente-por-beesible/'},
  ],
);
const recoveredRoute = recoveredSource.replace(/^docs\//, '').replace(/\.md$/, '/');
const recoveredArticle = pages.get(path.join(root, recoveredRoute, 'index.html'));
const recoveredTitle = 'Tu página web creada automáticamente por Beelma';
assert.equal(headingText(recoveredArticle, recoveredArticle('h1')), recoveredTitle);
assert.equal(visibility(`.theme-doc-sidebar-menu a[href$="/${recoveredRoute}"]`).text().trim(), recoveredTitle);
const importantNotices = recoveredArticle('.alert strong').filter((_, element) => recoveredArticle(element).text().trim() === 'Importante:');
assert.equal(importantNotices.length, 1);
importantNotices.each((_, element) => {
  assert.equal(recoveredArticle(element).prev('svg.help-icon--warning[aria-hidden="true"]').length, 1, 'Important notice must render the warning HelpIcon before its label');
});
assert(!fs.existsSync(retiredPath), `Retired route was generated: ${retiredRoute}`);
for (const [file, $] of pages) {
  assert.equal($(`.theme-doc-sidebar-menu a[href$="/${retiredRoute}"]`).length, 0, `${file}: retired article remains in sidebar`);
  assert.equal($(`.bee-pagination a[href$="/${retiredRoute}"]`).length, 0, `${file}: paginator points to retired article`);
}
const indexes = output.filter(f => /search-index-.*\.json$/.test(f));
assert(indexes.length > 0);
const docs = indexes.flatMap(f => JSON.parse(fs.readFileSync(f)).documents);
assert(docs.length > 24);
assert(!JSON.stringify(docs).match(/project-docs|production-snapshots/));
const corpus = Object.keys(require('./fixtures/public-docs-sha256.json'));
assert(!docs.some(doc => doc.sectionRoute.split('#')[0].endsWith(`/${retiredRoute}`)));
assert(!docs.some(doc => /Cómo crear tu página web/i.test(JSON.stringify(doc))));
const publicSources = [...corpus.filter(source => source !== retiredSource), recoveredSource];
for (const source of publicSources) {
  const route = source.replace(/^docs\//, '').replace(/index\.md$/, '').replace(/\.md$/, '/');
  assert(fs.existsSync(path.join(root, route, 'index.html')), `Public URL changed: ${route}`);
  const indexedRoute = new URL(route, base).pathname;
  assert(docs.some(doc => doc.sectionRoute.split('#')[0] === indexedRoute), `Search index missing: ${route}`);
}
console.log(`Build OK: ${pages.size} HTML pages, ${links} internal links/anchors, ${docs.length} indexed sections, ${publicSources.length} public document URLs and 1 retained draft.`);
