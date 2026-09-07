// @ts-check

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Documentación BeeDigital',
  tagline: 'Documentación de producto',
  url: 'https://documentation-poc-beedigital.github.io',
  baseUrl: '/documentation-poc/',
  organizationName: 'documentation-poc-Beedigital',
  projectName: 'documentation-poc',
  trailingSlash: true,
  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'es',
    locales: ['es'],
  },

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
          exclude: ['production-snapshots/**'],
        },
        blog: false,
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Documentación BeeDigital',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Documentación',
        },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `BeeDigital ${new Date().getFullYear()}`,
    },
  },
};

module.exports = config;
