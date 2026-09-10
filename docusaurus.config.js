// @ts-check

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Centro de Ayuda Beesible',
  tagline: 'Ayuda para utilizar Beesible',
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
          sidebarPath: './sidebars.js',
          exclude: ['production-snapshots/**'],
        },
        blog: false,
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Centro de Ayuda Beesible',
      items: [],
    },
    footer: {
      style: 'dark',
      copyright: `Beesible ${new Date().getFullYear()}`,
    },
  },
};

module.exports = config;
