const test = require('node:test');
const assert = require('node:assert/strict');
const plugin = require('../src/remark/remove-help-icons-from-h1');

const text = value => ({type: 'text', value});
const icon = name => ({type: 'mdxJsxTextElement', name, attributes: [], children: []});
const heading = (depth, children, id) => ({
  type: 'heading',
  depth,
  children,
  ...(id ? {data: {id, hProperties: {id}}} : {}),
});

async function apply(children) {
  const tree = {type: 'root', children};
  await plugin()(tree);
  return tree;
}

test('removes only the matching first H2 and moves its exact anchor to the H1', async () => {
  const link = {type: 'paragraph', children: [{type: 'link', url: '/related', children: [text('Relacionado')]}]};
  const list = {type: 'list', children: [{type: 'listItem', children: []}]};
  const laterSameHeading = heading(2, [text('Conexión Perfil de Empresa en Google')], 'conexión-perfil-de-empresa-en-google-2');
  const title = heading(1, [icon('google'), text('Conexión Perfil de Empresa\n en Google')], 'conexión-perfil-de-empresa-en-google');
  const tree = await apply([
    {type: 'mdxJsxFlowElement', name: 'header', attributes: [], children: [title]},
    heading(2, [text('Conexión Perfil de Empresa en Google')], 'conexión-perfil-de-empresa-en-google-1'),
    link,
    list,
    laterSameHeading,
  ]);

  assert.deepEqual(tree.children.map(node => node.type), ['mdxJsxFlowElement', 'paragraph', 'list', 'heading']);
  assert.equal(plugin.normalizeHeadingText(title), 'Conexión Perfil de Empresa en Google');
  assert.equal(title.data.hProperties.id, 'conexión-perfil-de-empresa-en-google-1');
  assert.equal(title.data.hProperties['data-bee-title-anchor'], true);
  assert.equal(tree.children[1], link);
  assert.equal(tree.children[2], list);
  assert.equal(tree.children[3], laterSameHeading);
  assert.equal(laterSameHeading.data.hProperties.id, 'conexión-perfil-de-empresa-en-google-2');
  assert.equal(new Set([title.data.hProperties.id, laterSameHeading.data.hProperties.id]).size, 2);
});

test('keeps non-matching Visibilidad subtitles and their anchors in place', async () => {
  const google = heading(2, [icon('google'), text('  Google')], '-google');
  const website = heading(2, [icon('website'), text(' Página Web')], '-página-web');
  const tree = await apply([
    heading(1, [icon('google'), text(' Visibilidad')], 'visibilidad'),
    google,
    {type: 'paragraph', children: [text('Contenido Google')]},
    website,
  ]);

  assert.deepEqual(tree.children.filter(node => node.type === 'heading'), [tree.children[0], google, website]);
  assert.equal(google.data.hProperties.id, '-google');
  assert.equal(website.data.hProperties.id, '-página-web');
  assert.equal(tree.children[0].data.hProperties['data-bee-title-anchor'], undefined);
});
