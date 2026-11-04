const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {test} = require('node:test');

test('Docusaurus exports real routes for articles, index, slug, baseUrl and trailingSlash', {timeout: 510000}, () => {
  const root = path.resolve(__dirname, '..');
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'preview-routes-'));
  const sha = '965e07bac3fdf8cc08d3f6953023a74d900c41b8';
  try {
    fs.mkdirSync(path.join(fixture, 'docs/category'), {recursive: true});
    fs.mkdirSync(path.join(fixture, 'pages'));
    fs.writeFileSync(path.join(fixture, 'pages/index.js'), 'export default function Home() { return null; }');
    fs.writeFileSync(path.join(fixture, 'docs/new.md'), '---\ntitle: New\nslug: /custom-slug\n---\nNew article.');
    fs.writeFileSync(path.join(fixture, 'docs/updated.mdx'), '---\ntitle: Updated\n---\nUpdated article.');
    fs.writeFileSync(path.join(fixture, 'docs/category/index.md'), '---\ntitle: Category\n---\nIndex.');
    for (const trailingSlash of [true, false]) {
      const baseUrl = trailingSlash ? '/custom/base/' : '/';
      const config = {
        title: 'Preview fixture', url: 'https://example.invalid', baseUrl, trailingSlash,
        plugins: [path.join(root, 'src/plugins/document-preview-routes.cjs')],
        presets: [[require.resolve('@docusaurus/preset-classic'), {
          docs: {path: path.join(fixture, 'docs'), routeBasePath: '/help', sidebarPath: false}, blog: false,
          pages: {path: path.join(fixture, 'pages')},
        }]],
      };
      fs.writeFileSync(path.join(fixture, 'docusaurus.config.cjs'), `module.exports = ${JSON.stringify(config)};`);
      const output = path.join(fixture, `build-${trailingSlash}`);
      const build = spawnSync(process.execPath, [require.resolve('@docusaurus/core/bin/docusaurus.mjs'),
        'build', root, '--config', path.join(fixture, 'docusaurus.config.cjs'), '--out-dir', output, '--no-minify'], {
        cwd: root, encoding: 'utf8', timeout: 240000,
        env: {...process.env, CI: 'true', NO_COLOR: '1', DOCUSAURUS_TELEMETRY_DISABLED: '1', CF_PAGES_COMMIT_SHA: sha},
      });
      assert.equal(build.status, 0, `${build.error || ''}\n${build.stdout}\n${build.stderr}`);
      const manifest = JSON.parse(fs.readFileSync(path.join(output, 'document-preview-routes.json')));
      assert.equal(manifest.commit, sha);
      assert.equal(manifest.baseUrl, baseUrl);
      const suffix = trailingSlash ? '/' : '';
      for (const [source, route] of Object.entries({
        'new.md': 'custom-slug', 'updated.mdx': 'updated', 'category/index.md': 'category',
      })) {
        const key = path.relative(root, path.join(fixture, 'docs', source)).split(path.sep).join('/');
        assert.equal(manifest.routes[key], `${baseUrl}help/${route}${suffix}`);
        const file = trailingSlash ? `help/${route}/index.html` : `help/${route}.html`;
        assert.ok(fs.existsSync(path.join(output, file)), `Published HTML exists: ${file}`);
      }
    }
  } finally {
    assert.equal(path.dirname(fixture), os.tmpdir());
    fs.rmSync(fixture, {recursive: true, force: true});
  }
});
