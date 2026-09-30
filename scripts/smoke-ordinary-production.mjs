import { chromium } from '@playwright/test';

const base = process.env.SMOKE_BASE_URL || 'http://127.0.0.1:4173/';
const browser = await chromium.launch({ headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl'] });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto(`${base}?forceWebGL=1`);
  await page.locator('#startup-new-game').click();
  await page.locator('#dialog-start').click();
  await page.getByRole('heading', { name: /先手.*手番/ }).waitFor();
  const hooks = await page.evaluate(() => ({
    app: '__QUORIDOR_APP_TEST_API__' in window,
    rules: '__QUORIDOR_RULES_TEST_API__' in window,
    session: '__QUORIDOR_SESSION_TEST_API__' in window,
    persistence: '__QUORIDOR_PERSISTENCE_TEST_API__' in window,
    diagnostics: '__QUORIDOR_DIAGNOSTICS__' in window,
  }));
  if (Object.values(hooks).some(Boolean)) throw new Error(`Test/debug global in normal bundle: ${JSON.stringify(hooks)}`);
  await page.locator('#board canvas').focus();
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await page.getByText('1 手目').waitFor();
  await page.getByRole('heading', { name: /後手.*手番/ }).waitFor();
  if (errors.length) throw new Error(`Browser errors: ${errors.join(' | ')}`);
  console.log(`Ordinary production smoke passed: ${base}; keyboard move, no test globals/page errors`);
} finally {
  await browser.close();
}
