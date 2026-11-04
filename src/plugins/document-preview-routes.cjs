const fs = require('node:fs/promises');
const path = require('node:path');
const {applyTrailingSlash} = require('@docusaurus/utils-common');

// Use the same metadata that Docusaurus uses to render the site. In particular,
// source filenames are not URLs (slug, index, baseUrl and trailingSlash apply).
module.exports = function documentPreviewRoutes() {
  let routes = {};
  return {
    name: 'document-preview-routes',
    allContentLoaded({allContent}) {
      routes = {};
      for (const content of Object.values(allContent['docusaurus-plugin-content-docs'] || {})) {
        for (const version of content.loadedVersions) {
          for (const doc of version.docs) {
            if (doc.source.startsWith('@site/') && !doc.draft) {
              const source = doc.source.slice('@site/'.length);
              if (routes[source] && routes[source] !== doc.permalink) {
                throw new Error(`Ambiguous preview route: ${source}`);
              }
              routes[source] = doc.permalink;
            }
          }
        }
      }
    },
    async postBuild({outDir, siteConfig}) {
      await fs.writeFile(path.join(outDir, 'document-preview-routes.json'), JSON.stringify({
        schema: 1,
        commit: process.env.CF_PAGES_COMMIT_SHA || null,
        baseUrl: siteConfig.baseUrl,
        routes: Object.fromEntries(Object.entries(routes).map(([source, permalink]) => [
          source, applyTrailingSlash(permalink, {
            baseUrl: siteConfig.baseUrl, trailingSlash: siteConfig.trailingSlash,
          }),
        ])),
      }, null, 2));
    },
  };
};
