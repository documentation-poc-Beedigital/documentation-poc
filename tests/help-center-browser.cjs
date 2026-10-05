// Install Playwright separately or supply PLAYWRIGHT_MODULE; serve the production build first.
// HELP_CENTER_URL and UI_SCREENSHOT_DIR optionally override local defaults.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const url = process.env.HELP_CENTER_URL || 'http://localhost:3000/documentation-poc/';
const screenshots = process.env.UI_SCREENSHOT_DIR;

async function assertNoHorizontalOverflow(page, label) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  assert(
    dimensions.scrollWidth <= dimensions.clientWidth,
    `${label} overflows horizontally: ${dimensions.scrollWidth}px > ${dimensions.clientWidth}px`,
  );
}

(async () => {
  const browser = await chromium.launch({channel: process.env.UI_BROWSER || 'chrome', headless: true});
  try {
    for (const [width, height, viewportName] of [
      [1440, 960, 'desktop'],
      [1280, 720, 'laptop'],
      [390, 844, 'mobile'],
    ]) {
        const context = await browser.newContext({viewport: {width, height}, colorScheme: 'dark'});
        await context.addInitScript(() => localStorage.setItem('theme', 'dark'));
        const page = await context.newPage();
        const external = [];
        const errors = [];
        page.on('request', request => {
          if (new URL(request.url()).origin !== new URL(url).origin) external.push(request.url());
        });
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(url);
        await page.waitForSelector('.bee-navbar-search__trigger');
        assert.equal(await page.locator('html').getAttribute('data-theme'), 'light');
        assert.equal(await page.locator('[class*="colorModeToggle"], [class*="toggleButton"]').count(), 0);
        const sidebar = page.locator('.theme-doc-sidebar-menu');
        assert.equal(await sidebar.locator(':scope > li').count(), 8);
        const categoryRoutes = await sidebar.locator(':scope > li > .menu__list-item-collapsible > a').evaluateAll(links => links.map(link => link.getAttribute('href')));
        assert.equal(categoryRoutes.length, 8);
        assert.equal(await sidebar.locator('a[href="/documentation-poc/"]').count(), 0);
        assert.equal(await page.locator('.help-categories').count(), 0);
        assert.equal(await page.locator('.pagination-nav a').count(), 0);
        if (width >= 600) assert(await sidebar.isVisible());
        if (width < 600) {
          await page.locator('.navbar__toggle').click();
          const mobileSidebar = page.locator('.navbar-sidebar .theme-doc-sidebar-menu');
          await mobileSidebar.waitFor({state: 'visible'});
          assert.equal(await mobileSidebar.locator(':scope > li').count(), 8);
          await mobileSidebar.getByRole('link', {name: 'Visibilidad', exact: true}).click();
          await page.waitForURL(/centro-de-ayuda\/visibilidad\/$/);
          await page.goto(url);
        }
        await assertNoHorizontalOverflow(page, `Home ${viewportName}`);
        if (width >= 997) {
          assert.equal(
            await page.evaluate(() => document.documentElement.scrollHeight <= document.documentElement.clientHeight),
            true,
            `Home ${viewportName} has unnecessary vertical scroll`,
          );
        }
        assert(await page.evaluate(() => document.querySelector('footer').getBoundingClientRect().bottom >= innerHeight - 1));
        const logo = page.locator('.navbar__logo img:visible');
        assert((await logo.getAttribute('src')).includes('beesible-oscuro.svg'));
        const box = await logo.boundingBox();
        assert(Math.abs(box.width / box.height - 126.95 / 25.47) < 0.1);
        if (screenshots) {
          fs.mkdirSync(screenshots, {recursive: true});
          await page.screenshot({path: path.join(screenshots, `home-${viewportName}.png`), fullPage: true});
        }
        const homeSearch = page.getByRole('button', {name: 'Buscar en el Centro de Ayuda'});
        for (let tabs = 0; tabs < 50 && !(await homeSearch.evaluate(el => el === document.activeElement)); tabs++) {
          await page.keyboard.press('Tab');
        }
        assert(await homeSearch.evaluate(el => el === document.activeElement), 'Home search is not keyboard reachable');
        assert.notEqual(await homeSearch.evaluate(el => getComputedStyle(el).outlineStyle), 'none', 'Home search focus is not visible');
        await page.keyboard.press('Enter');
        const input = page.locator('.aa-Input:visible');
        await input.waitFor();
        await assertNoHorizontalOverflow(page, `Expanded home search ${viewportName}`);
        assert.equal(await input.evaluate(el => el === document.activeElement), true, 'Inline search did not receive focus');
        assert.equal(await page.locator('.aa-DetachedOverlay').count(), 0, 'Search rendered a detached overlay');
        assert.equal(await page.locator('body.aa-Detached').count(), 0, 'Search blocked the page in detached mode');
        assert.match(await input.getAttribute('placeholder'), /buscar/i);
        await input.fill('reseñas');
        await page.waitForSelector('.aa-ItemLink');
        const count = await page.locator('.aa-ItemLink').count();
        assert(count > 0 && count <= 8);
        assert.match(await page.locator('.aa-ItemLink').first().innerText(), /reseñas|reputación/i);
        await input.press('ArrowDown');
        await input.press('Enter');
        await page.waitForURL(/centro-de-ayuda/);
        assert(await page.locator('.theme-doc-markdown').isVisible());
        await page.goto(new URL('centro-de-ayuda/inicio-y-acceso/acceder-a-la-plataforma/', url).href);
        const breadcrumbs = page.locator('.breadcrumbs');
        await breadcrumbs.waitFor({state: 'visible'});
        const note = page.locator('.alert--secondary').first();
        await note.waitFor({state: 'visible'});
        assert.equal(await note.locator(':scope > [class*="admonitionHeading"]').count(), 1);
        assert.equal(await note.locator(':scope > [class*="admonitionHeading"]').isVisible(), false);
        assert.match(await note.innerText(), /A tener en cuenta:/);
        const noteIcon = note.locator('.help-icon');
        assert.equal(await noteIcon.count(), 1, 'Semantic note icon was removed');
        assert(await noteIcon.isVisible(), 'Semantic note icon is clipped');
        const noteHeading = note.locator('p').first().locator('strong');
        const [noteBox, iconBox, headingBox, articleClientWidth] = await Promise.all([
          note.boundingBox(),
          noteIcon.boundingBox(),
          noteHeading.boundingBox(),
          page.evaluate(() => document.documentElement.clientWidth),
        ]);
        assert(noteBox && iconBox && iconBox.y >= noteBox.y && iconBox.y < noteBox.y + noteBox.height, 'Semantic note icon falls outside its card');
        assert(noteBox.x >= 0 && noteBox.x + noteBox.width <= articleClientWidth, 'Note card is clipped by the viewport');
        assert(iconBox && headingBox && Math.abs(iconBox.y - headingBox.y) <= 6, 'Semantic note icon is not aligned with the first text line');
        assert.deepEqual(await page.locator('.theme-doc-sidebar-menu > li > .menu__list-item-collapsible > a').evaluateAll(links => links.map(link => link.getAttribute('href'))), categoryRoutes);
        await assertNoHorizontalOverflow(page, `Article with closed search ${viewportName}`);
        assert.deepEqual(external, [], 'Search or page contacted an external service');
        assert.deepEqual(errors, [], 'Browser errors');
        if (screenshots) await page.screenshot({path: path.join(screenshots, `article-${viewportName}.png`), fullPage: true});
        await page.locator('.navbar .bee-navbar-search__trigger').click();
        await assertNoHorizontalOverflow(page, `Article with expanded search ${viewportName}`);
        await page.locator('.aa-Input:visible').fill('zzzxqvnonexistent');
        await page.getByText('No se han encontrado resultados.', {exact: true}).waitFor();
        await page.locator('.aa-Input:visible').press('Escape');
        assert.equal(await page.locator('.aa-Input:visible').count(), 0, 'Escape did not collapse search');
        assert(await page.locator('.navbar .bee-navbar-search__trigger').isVisible());
        await page.goto(new URL('centro-de-ayuda/inicio-y-acceso/cerrar-sesion-en-la-plataforma/', url).href);
        const paginator = page.locator('.bee-pagination');
        await paginator.waitFor({state: 'visible'});
        assert.deepEqual(await paginator.locator('a').allInnerTexts(), ['Anterior', 'Siguiente']);
        assert.match(await paginator.locator('.bee-pagination__link--previous').getAttribute('aria-label'), /^Ir al artículo anterior: .+/);
        assert.match(await paginator.locator('.bee-pagination__link--next').getAttribute('aria-label'), /^Ir al artículo siguiente: .+/);
        await assertNoHorizontalOverflow(page, `Paginated article ${viewportName}`);
        if (width < 600) {
          await page.locator('.navbar__toggle').click();
          await page.locator('.navbar-sidebar .menu:not([inert])').waitFor();
          assert(!(await page.locator('.navbar-sidebar').innerText()).includes('centro-de-ayuda'));
        }
        console.log(`PASS ${width}px light-only: responsive layout, logo, Spanish search, <=8 results, keyboard navigation, local-only requests`);
        await context.close();
    }

    const shortContext = await browser.newContext({viewport: {width: 1280, height: 480}});
    const shortPage = await shortContext.newPage();
    await shortPage.goto(url);
    await assertNoHorizontalOverflow(shortPage, 'Short desktop home');
    const shortHomeScroll = await shortPage.evaluate(() => {
      const root = document.documentElement;
      const overflows = root.scrollHeight > root.clientHeight;
      window.scrollTo(0, root.scrollHeight);
      return {overflows, scrollY: window.scrollY};
    });
    assert(shortHomeScroll.overflows, 'Short desktop fixture no longer exercises vertical overflow');
    assert(shortHomeScroll.scrollY > 0, 'Short desktop home prevents necessary vertical scrolling');
    await shortContext.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
