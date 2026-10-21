import { test, expect, type Page } from '@playwright/test';

async function ready(page: Page): Promise<void> {
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__?.phase))
    .toBe('ready');
}
async function home(page: Page): Promise<void> {
  await page.locator('.top-actions .home-link').click();
  await expect(page).toHaveURL(/#\/$/);
  await expect(page.locator('#choose-quoridor')).toBeVisible();
}

test('home loads no game resources and offers both games', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('./?forceWebGL=1');
  await expect(page.locator('#choose-quoridor')).toBeVisible();
  await expect(page.locator('#choose-othello')).toBeVisible();
  expect(requests.some((url) => /wasm|quoridor-|ai.worker|three|\.hdr|\.mp3|\.ogg/.test(url))).toBe(
    false,
  );
  expect(await page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__)).toBeUndefined();
  await page.screenshot({ path: test.info().outputPath('home.png') });
});

test('home stays lazy, existing slot resumes, game teardown and base-path history work', async ({
  page,
}) => {
  const requests: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  await page.goto('./?forceWebGL=1');
  await expect(page.locator('#choose-quoridor')).toBeVisible();
  await expect(page.locator('#choose-othello')).toBeVisible();
  expect(requests.some((url) => /wasm|quoridor-title|\.hdr|\.mp3|\.ogg/.test(url))).toBe(false);
  expect(await page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__)).toBeUndefined();
  const homeStyle = await page.locator('.home-page').evaluate((element) => ({
    font: getComputedStyle(element).fontFamily,
    position: getComputedStyle(element).position,
  }));
  await page.locator('#choose-quoridor').click();
  await ready(page);
  await page.locator('#startup-new-game').click();
  await page.locator('#dialog-start').click();
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase))
    .toBe('humanTurn');
  const before = await page.evaluate(() => {
    const api = window.__QUORIDOR_APP_TEST_API__!;
    // Keep these exact old instance handles to observe disposal after navigation.
    (window as any).oldGame = api;
    return api.exportReplay();
  });
  await home(page);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__)).toBeUndefined();
  expect(await page.evaluate(() => (window as any).oldGame.state().phase)).toBe('disposed');
  expect(await page.evaluate(() => (window as any).oldGame.audio().status)).toBe('disposed');
  await expect(page.locator('canvas, dialog')).toHaveCount(0);
  expect(
    await page.locator('.home-page').evaluate((element) => ({
      font: getComputedStyle(element).fontFamily,
      position: getComputedStyle(element).position,
    })),
  ).toEqual(homeStyle);
  expect(await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1'))).toBeTruthy();
  await page.goBack();
  await ready(page);
  await page.locator('#resume-game-choice').click();
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase))
    .toBe('humanTurn');
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay())).toEqual(
    before,
  );
  await page.goForward();
  await expect(page.locator('#choose-quoridor')).toBeVisible();
  await page.goto('./?forceWebGL=1#/quoridor');
  await ready(page);
  await expect(page.locator('#resume-game-choice')).toBeVisible();
  expect(new URL(page.url()).pathname).toBe('/shell-check/');
  await page.locator('#resume-game-choice').click();
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay())).toEqual(
    before,
  );
});

test('leaving a pending game import cannot mount or report stale failure', async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requested!: () => void;
  const reached = new Promise<void>((resolve) => {
    requested = resolve;
  });
  await page.route('**/assets/*.js', async (route) => {
    // The home entry is the only eager script. Hold the selected game chunk.
    if (route.request().url().includes('/assets/index-')) return route.continue();
    requested();
    await gate;
    await route.continue();
  });
  await page.goto('./?forceWebGL=1');
  await page.locator('#choose-quoridor').click();
  await reached;
  await page.locator('.app-loading a').click();
  await expect(page.locator('#choose-quoridor')).toBeVisible();
  release();
  await page.waitForLoadState('networkidle');
  await expect(page.locator('canvas, .quoridor')).toHaveCount(0);
  expect(await page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__)).toBeUndefined();
});

test('switching during pending AI terminates the old Worker and ignores late results', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const NativeWorker = window.Worker;
    (window as any).workerStops = 0;
    window.Worker = class extends NativeWorker {
      override terminate(): void {
        (window as any).workerStops++;
        super.terminate();
      }
    };
  });
  await page.goto('./?forceWebGL=1#/quoridor');
  await ready(page);
  await page.locator('#startup-new-game').click();
  await page.locator('#match-mode').selectOption('ai');
  await page.locator('#human-side').selectOption('1');
  await page.locator('#ai-budget').selectOption('4096');
  let finish!: () => void;
  const gate = new Promise<void>((resolve) => {
    finish = resolve;
  });
  await page.route('**/*quoridor_ai_bg*.wasm', async (route) => {
    await gate;
    await route.continue();
  });
  await page.locator('#dialog-start').click();
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase))
    .toBe('aiThinking');
  await page.evaluate(() => {
    (window as any).oldGame = window.__QUORIDOR_APP_TEST_API__;
  });
  await home(page);
  finish();
  await page.waitForLoadState('networkidle');
  expect(await page.evaluate(() => (window as any).oldGame.state().phase)).toBe('disposed');
  expect(await page.evaluate(() => (window as any).workerStops)).toBeGreaterThan(0);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__)).toBeUndefined();
  await expect(page.locator('canvas')).toHaveCount(0);
});
