function isHelpIcon(node) {
  return node?.type === 'mdxJsxTextElement' && node.name === 'HelpIcon';
}

function visibleText(node) {
  if (!node || typeof node !== 'object') return '';
  if (node.type === 'text' || node.type === 'inlineCode') return node.value ?? '';
  if (!Array.isArray(node.children)) return '';
  return node.children.map(visibleText).join('');
}

function normalizeHeadingText(node) {
  return visibleText(node).replace(/\s+/g, ' ').trim();
}

function findHeadingEntries(node, entries = [], parent = null, index = -1) {
  if (!node || typeof node !== 'object') return entries;
  if (node.type === 'heading') entries.push({node, parent, index});
  if (Array.isArray(node.children)) {
    node.children.forEach((child, childIndex) => (
      findHeadingEntries(child, entries, node, childIndex)
    ));
  }
  return entries;
}

module.exports = function normalizeArticleHeadings() {
  return function transform(tree) {
    function removeHelpIcons(node) {
      if (!node || typeof node !== 'object') return;

      if (node.type === 'heading' && node.depth === 1 && Array.isArray(node.children)) {
        node.children = node.children.filter((child) => !isHelpIcon(child));
      }

      if (Array.isArray(node.children)) node.children.forEach(removeHelpIcons);
    }

    removeHelpIcons(tree);

    const headingEntries = findHeadingEntries(tree);
    const titleEntryIndex = headingEntries.findIndex(({node}) => node.depth === 1);
    if (titleEntryIndex < 0) return;
    const subtitleEntry = headingEntries.find(
      ({node}, index) => index > titleEntryIndex && node.depth === 2,
    );
    if (!subtitleEntry?.parent || subtitleEntry.index < 0) return;

    const title = headingEntries[titleEntryIndex].node;
    const subtitle = subtitleEntry.node;
    const titleText = normalizeHeadingText(title);
    if (!titleText || titleText !== normalizeHeadingText(subtitle)) return;

    // Docusaurus assigns heading ids before custom remark plugins. Preserve
    // all of them so MDX whitespace, collision suffixes and later hrefs stay
    // stable after this H2 is removed.
    const headings = headingEntries.map(({node}) => node);
    const ids = headings.map(
      (heading) => heading.data?.hProperties?.id ?? heading.data?.id,
    );
    if (!ids.every(Boolean)) return;
    headings.forEach((heading, index) => {
      const data = heading.data ?? (heading.data = {});
      data.id = ids[index];
      data.hProperties = {...(data.hProperties ?? {}), id: ids[index]};
    });
    const subtitleId = subtitle.data.hProperties.id;

    const titleData = title.data ?? (title.data = {});
    titleData.id = subtitleId;
    titleData.hProperties = {
      ...(titleData.hProperties ?? {}),
      id: subtitleId,
      'data-bee-title-anchor': true,
    };
    subtitleEntry.parent.children.splice(subtitleEntry.index, 1);
  };
};

module.exports.normalizeHeadingText = normalizeHeadingText;
