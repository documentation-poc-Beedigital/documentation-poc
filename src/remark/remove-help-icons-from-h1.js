module.exports = function removeHelpIconsFromH1() {
  return function transform(tree) {
    function visit(node) {
      if (!node || typeof node !== 'object') return;

      if (node.type === 'heading' && node.depth === 1 && Array.isArray(node.children)) {
        node.children = node.children.filter(
          (child) => !(child.type === 'mdxJsxTextElement' && child.name === 'HelpIcon'),
        );
      }

      if (Array.isArray(node.children)) node.children.forEach(visit);
    }

    visit(tree);
  };
};
