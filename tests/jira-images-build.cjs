// Build an isolated article with a selected Jira PNG under production and preview base URLs.
// The Help Center articles and assets are never modified.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {test} = require('node:test');

const root = path.resolve(__dirname, '..');
const cli = require.resolve('@docusaurus/core/bin/docusaurus.mjs');
const pixel = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC', 'base64');
// A valid ancillary chunk keeps the asset above Webpack's inline-image threshold.
const payload = Buffer.from(`fixture\0${'x'.repeat(20000)}`);
const chunk = Buffer.alloc(payload.length + 12);
chunk.writeUInt32BE(payload.length);
chunk.write('tEXt', 4);
payload.copy(chunk, 8);
let crc = 0xffffffff;
for (const byte of chunk.subarray(4, -4)) {
  crc ^= byte;
  for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
}
chunk.writeUInt32BE((crc ^ 0xffffffff) >>> 0, chunk.length - 4);
const png = Buffer.concat([pixel.subarray(0, 33), chunk, pixel.subarray(33)]);

test('Jira Markdown image resolves with production and preview baseUrl', {timeout: 650000}, () => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'jira-image-build-'));
  try {
    const docs = path.join(fixture, 'docs');
    const staticDir = path.join(fixture, 'static');
    const name = `app-2-11-${crypto.createHash('sha256').update(png).digest('hex')}.png`;
    fs.mkdirSync(docs);
    fs.mkdirSync(path.join(staticDir, 'img/jira'), {recursive: true});
    fs.writeFileSync(path.join(staticDir, 'img/jira', name), png);
    fs.writeFileSync(path.join(docs, 'image-fixture.md'),
      `---\ntitle: Imagen seleccionada\nslug: /image-fixture\n---\n\n# Imagen seleccionada\n\n1. Abre el formulario.\n\n![Formulario de acceso](/img/jira/${name})\n`);
    fs.writeFileSync(path.join(docs, 'index.md'), '---\ntitle: Inicio\nslug: /\n---\n\n# Inicio\n');
    for (const baseUrl of ['/documentation-poc/', '/']) {
      const config = path.join(fixture, 'docusaurus.config.cjs');
      const output = path.join(fixture, baseUrl === '/' ? 'preview-build' : 'production-build');
      const settings = {
        title: 'Fixture de imágenes Jira', url: 'https://example.invalid', baseUrl,
        trailingSlash: true,
        staticDirectories: [staticDir], onBrokenLinks: 'throw',
        presets: [[require.resolve('@docusaurus/preset-classic'), {
          docs: {path: docs, routeBasePath: '/', sidebarPath: false}, blog: false,
        }]],
      };
      fs.writeFileSync(config, `module.exports = ${JSON.stringify(settings)};\n`);
      // Minification does not affect image URLs and needlessly slows these two render fixtures.
      const build = spawnSync(process.execPath, [cli, 'build', root, '--config', config, '--out-dir', output, '--no-minify'],
        {cwd: root, encoding: 'utf8', timeout: 300000,
          env: {...process.env, NO_COLOR: '1', NO_UPDATE_NOTIFIER: '1', CI: 'true'}});
      assert.equal(build.status, 0, `${build.error || ''}\n${build.stdout}\n${build.stderr}`);
      const html = fs.readFileSync(path.join(output, 'image-fixture/index.html'), 'utf8');
      const img = html.match(/<img\b[^>]*alt="Formulario de acceso"[^>]*>/);
      assert.ok(img, 'The Markdown image must render with the approved alt');
      const src = img[0].match(/\bsrc="([^"]+)"/)[1];
      assert.ok(src.startsWith(baseUrl), `Image ${src} must respect ${baseUrl}`);
      assert.ok(!html.includes('atlassian.net'), 'No private Jira image URL may be rendered');
      assert.deepEqual(fs.readFileSync(path.join(output, src.slice(baseUrl.length))), png);
      assert.deepEqual(fs.readFileSync(path.join(output, 'img/jira', name)), png);
    }
  } finally {
    assert.equal(path.dirname(fixture), os.tmpdir());
    fs.rmSync(fixture, {recursive: true, force: true});
  }
});
