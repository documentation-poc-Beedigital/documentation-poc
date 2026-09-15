// Install Playwright separately or supply PLAYWRIGHT_MODULE; serve the production build first.
// HELP_CENTER_URL and UI_SCREENSHOT_DIR optionally override local defaults.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const url = process.env.HELP_CENTER_URL || 'http://localhost:3000/documentation-poc/';
const screenshots = process.env.UI_SCREENSHOT_DIR;

(async () => {
  const browser = await chromium.launch({channel: process.env.UI_BROWSER || 'chrome', headless: true});
  try {
    for (const width of [1440, 390]) {
      for (const theme of ['light', 'dark']) {
        const context = await browser.newContext({viewport: {width, height: 960}, colorScheme: theme});
        await context.addInitScript(value => localStorage.setItem('theme', value), theme);
        const page = await context.newPage();
        const external = [];
        const errors = [];
        page.on('request', request => {
          if (new URL(request.url()).origin !== new URL(url).origin) external.push(request.url());
        });
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(url);
        await page.waitForSelector('.aa-DetachedSearchButton');
        assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
        assert.equal(await page.locator('.help-categories a').count(), 8);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        const logo = page.locator('.navbar__logo img:visible');
        assert((await logo.getAttribute('src')).includes(theme === 'dark' ? 'beesible-claro.svg' : 'beesible-oscuro.svg'));
        const box = await logo.boundingBox();
        assert(Math.abs(box.width / box.height - 126.95 / 25.47) < 0.1);
        if (screenshots) {
          fs.mkdirSync(screenshots, {recursive: true});
          await page.screenshot({path: path.join(screenshots, `home-${width}-${theme}.png`), fullPage: true});
        }
        await page.getByRole('button', {name: 'Buscar en el Centro de Ayuda'}).click();
        const input = page.locator('.aa-Input:visible');
        await input.waitFor();
        assert.match(await input.getAttribute('placeholder'), /buscar/i);
        await input.fill('reseñas');
        await page.waitForSelector('.aa-ItemLink');
        const count = await page.locator('.aa-ItemLink').count();
        assert(count > 0 && count <= 8);
        assert.match(await page.locator('.aa-ItemLink').first().innerText(), /reseñas|reputación/i);
        if (screenshots) await page.screenshot({path: path.join(screenshots, `search-${width}-${theme}.png`)});
        await input.press('Enter');
        await page.waitForURL(/centro-de-ayuda/);
        assert(await page.locator('.theme-doc-markdown').isVisible());
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        assert.deepEqual(external, [], 'Search or page contacted an external service');
        assert.deepEqual(errors, [], 'Browser errors');
        if (screenshots) await page.screenshot({path: path.join(screenshots, `article-${width}-${theme}.png`), fullPage: true});
        await page.locator('.navbar .aa-DetachedSearchButton').click();
        await page.locator('.aa-Input:visible').fill('zzzxqvnonexistent');
        await page.getByText('No se han encontrado resultados.', {exact: true}).waitFor();
        await page.locator('.aa-Input:visible').press('Escape');
        if (width < 600) {
          await page.locator('.navbar__toggle').click();
          await page.locator('.navbar-sidebar .menu:not([inert])').waitFor();
          assert(!(await page.locator('.navbar-sidebar').innerText()).includes('centro-de-ayuda'));
        }
        console.log(`PASS ${width}px ${theme}: layout, logo, Spanish search, <=8 results, keyboard navigation, local-only requests`);
        await context.close();
      }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
