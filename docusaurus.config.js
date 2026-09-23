// @ts-check

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Centro de Ayuda Beesible',
  tagline: 'Ayuda para utilizar Beesible',
  favicon: 'img/brand/beesible-icon.svg',
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
  plugins: [
    ['@cmfcmf/docusaurus-search-local', {
      indexDocs: true,
      indexBlog: false,
      indexPages: false,
      language: 'es',
      indexDocSidebarParentCategories: 1,
      includeParentCategoriesInPageTitle: true,
      maxSearchResults: 8,
    }],
  ],

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
        theme: {customCss: './src/css/custom.css'},
      },
    ],
  ],

  themeConfig: {
    metadata: [{name: 'description', content: 'Centro de Ayuda Beesible: guías públicas para acceder a tu cuenta, gestionar tu presencia digital y utilizar Beelma.'}],
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Centro de Ayuda',
      logo: {
        alt: 'Beesible — Centro de Ayuda',
        src: 'img/brand/beesible-oscuro.svg',
        href: '/',
      },
      items: [{type: 'search', position: 'right'}],
    },
    footer: {
      style: 'light',
      links: [{title: 'Beesible', items: [{label: 'Conoce Beesible', href: 'https://www.beesible.ai/'}]}],
      copyright: `Beesible ${new Date().getFullYear()}`,
    },
  },
};

module.exports = config;
